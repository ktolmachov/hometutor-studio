/**
 * llama.cpp local coding trigger.
 *
 * Phase 1 scope: controlled local patch executor for low-risk tasks.
 * The model proposes a fenced unified diff; this trigger validates write-set,
 * normalizes patch hygiene, applies via git apply, runs targeted tests, and
 * writes execution_contract.md from evidence.
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  type AgentTriggerConfig,
  type TriggerResult,
  runTrigger,
  createLogger,
} from "./_trigger_shared.js";

const DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1";
const DEFAULT_MODEL = "qwen/qwen3-coder-next";
const DEFAULT_MAX_INPUT_TOKENS = 24_000;
const DEFAULT_MAX_OUTPUT_TOKENS = 6_000;
const DEFAULT_TIMEOUT_MS = 900_000;
const DEFAULT_TEMPERATURE = 0.2;
const DEFAULT_TOP_P = 0.9;
const DEFAULT_REPEAT_PENALTY = 1.1;
const DEFAULT_MIN_CONTEXT_TOKENS = 65_536;
const DEFAULT_CONTEXT_MAX_CHARS = 60_000;
const DEFAULT_CONTEXT_FILE_MAX_CHARS = 20_000;
const LOADING_MODEL_RETRY_DELAYS_MS = [3_000, 8_000, 15_000];

export interface ParsedLlamaCppResponse {
  summary: string;
  readSetRaw: string;
  writeSetRaw: string;
  patchRaw: string;
  testsRaw: string;
  risks: string;
  executionContractDraft: string;
}

export interface PatchValidation {
  ok: boolean;
  reason: string | null;
  changedPaths: string[];
  writeSet: string[];
}

export interface PatchNormalizationResult {
  diff: string;
  hunkCountNormalized: boolean;
}

export interface ReadSetContextPack {
  prompt: string;
  readSet: string[];
  contextFilesCount: number;
  contextTruncated: boolean;
  contextChars: number;
}

interface ApplyResult {
  ok: boolean;
  error: string | null;
  recountUsed: boolean;
}

interface RevertResult {
  ok: boolean;
  error: string | null;
}

interface TestRunResult {
  command: string;
  status: number | null;
  stdout: string;
  stderr: string;
}

interface LlamaCppModelInfo {
  aliasMatched: boolean;
  nCtx: number | null;
  raw: unknown;
}

const SECTION_ORDER = [
  "SUMMARY",
  "READ_SET",
  "WRITE_SET",
  "PATCH",
  "TESTS",
  "RISKS",
  "EXECUTION_CONTRACT_DRAFT",
] as const;

type SectionName = (typeof SECTION_ORDER)[number];

function envNumber(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function resolveMinContextTokens(): number {
  return envNumber("LLAMACPP_MIN_CONTEXT_TOKENS", DEFAULT_MIN_CONTEXT_TOKENS);
}

function stripBom(text: string): string {
  return text.replace(/^\uFEFF/, "");
}

export function normalizeLfBom(text: string): string {
  return stripBom(text).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

export function extractMarkdownListSection(markdown: string, headingNames: string[]): string[] {
  const normalized = normalizeLfBom(markdown);
  const headingPattern = headingNames.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const match = normalized.match(new RegExp(`^\\s*(?:#{1,6}\\s*)?(?:${headingPattern})\\s*:?\\s*$`, "im"));
  if (!match || match.index == null) return [];
  const after = normalized.slice(match.index + match[0].length);
  const lines = after.split("\n");
  const items: string[] = [];
  for (const line of lines) {
    if (/^\s*(?:#{1,6}\s*)?[A-Za-zА-Яа-я0-9 _-]+\s*:?\s*$/.test(line) && items.length > 0) break;
    const item = line.match(/^\s*[-*]\s+(.+?)\s*$/);
    if (item) {
      items.push(normalizeRepoPath(item[1]));
      continue;
    }
    if (items.length > 0 && line.trim() === "") break;
  }
  return [...new Set(items.filter(Boolean))];
}

export function buildReadSetContext(
  prompt: string,
  repoRoot: string,
  maxChars: number,
  perFileMaxChars: number,
): ReadSetContextPack {
  const readSet = extractMarkdownListSection(prompt, ["Read-set", "Read set", "READ_SET", "read-set"]);
  const chunks: string[] = [];
  let remaining = maxChars;
  let contextTruncated = false;
  for (const relPath of readSet) {
    if (remaining <= 0) {
      contextTruncated = true;
      continue;
    }
    if (relPath.includes("..") || /^[A-Za-z]:/.test(relPath)) continue;
    const path = join(repoRoot, relPath);
    if (!existsSync(path)) continue;
    let content: string;
    try {
      content = readFileSync(path, "utf-8");
    } catch {
      continue;
    }
    const normalized = normalizeLfBom(content);
    const slice = normalized.slice(0, Math.min(perFileMaxChars, remaining));
    if (slice.length < normalized.length) {
      contextTruncated = true;
    }
    chunks.push(`=== ${relPath} ===\n${slice}${slice.length < normalized.length ? "\n...[truncated]" : ""}`);
    remaining -= slice.length;
  }
  const finalFormatReminder = [
    "END CONTEXT EXCERPTS.",
    "Now answer the original task using exactly these section headings:",
    SECTION_ORDER.join("\n"),
    "PATCH must contain exactly one fenced ```diff block.",
    "If no changes are needed, PATCH must still contain exactly:",
    "```diff\n# NO_CHANGES\n```",
    "Do not return PATCH as plain text.",
  ].join("\n");
  const packedPrompt = chunks.length === 0
    ? prompt
    : `${prompt}\n\nCONTEXT EXCERPTS FROM READ_SET:\n${chunks.join("\n\n")}\n\n${finalFormatReminder}\n`;
  return {
    prompt: packedPrompt,
    readSet,
    contextFilesCount: chunks.length,
    contextTruncated,
    contextChars: packedPrompt.length,
  };
}

export function parseAgentResponse(text: string): ParsedLlamaCppResponse {
  const normalized = normalizeLfBom(text);
  if (/<think>/i.test(normalized) || /<\/think>/i.test(normalized)) {
    throw new Error("response contains <think>");
  }

  const matches = [...normalized.matchAll(/^(SUMMARY|READ_SET|WRITE_SET|PATCH|TESTS|RISKS|EXECUTION_CONTRACT_DRAFT)\s*$/gm)];
  const found = matches.map((m) => m[1] as SectionName);
  const expected = SECTION_ORDER.join(",");
  if (found.join(",") !== expected) {
    throw new Error(`invalid section order: expected ${expected}; got ${found.join(",") || "(none)"}`);
  }

  const sections = new Map<SectionName, string>();
  for (let i = 0; i < matches.length; i++) {
    const name = matches[i][1] as SectionName;
    const start = (matches[i].index ?? 0) + matches[i][0].length;
    const end = i + 1 < matches.length ? matches[i + 1].index ?? normalized.length : normalized.length;
    sections.set(name, normalized.slice(start, end).trim());
  }

  return {
    summary: sections.get("SUMMARY") ?? "",
    readSetRaw: sections.get("READ_SET") ?? "",
    writeSetRaw: sections.get("WRITE_SET") ?? "",
    patchRaw: sections.get("PATCH") ?? "",
    testsRaw: sections.get("TESTS") ?? "",
    risks: sections.get("RISKS") ?? "",
    executionContractDraft: sections.get("EXECUTION_CONTRACT_DRAFT") ?? "",
  };
}

function stripJsonFence(text: string): string {
  const trimmed = text.trim();
  const fenced = trimmed.match(/^```(?:json)?\s*\n([\s\S]*?)\n```$/i);
  return fenced ? fenced[1].trim() : trimmed;
}

function normalizeRepoPath(path: string): string {
  return path
    .trim()
    .replace(/^["']|["']$/g, "")
    .replace(/\\/g, "/")
    .replace(/^(a|b)\//, "")
    .replace(/^\.\//, "");
}

export function parseWriteSet(text: string): string[] {
  const raw = stripJsonFence(text);
  if (!raw || raw === "[]") return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.every((v) => typeof v === "string")) {
      return [...new Set(parsed.map(normalizeRepoPath).filter(Boolean))].sort();
    }
  } catch {
    // Fall through to line parser.
  }
  return [
    ...new Set(
      raw
        .split(/\n/)
        .map((line) => line.replace(/^[-*]\s+/, "").trim())
        .filter(Boolean)
        .map(normalizeRepoPath),
    ),
  ].sort();
}

export function extractFencedDiff(patchRaw: string): string {
  const normalized = normalizeLfBom(patchRaw).trim();
  const match = normalized.match(/```diff\s*\n([\s\S]*?)\n```/i);
  if (!match) {
    throw new Error("PATCH must contain a fenced ```diff block");
  }
  const diff = normalizeLfBom(match[1]).trimEnd();
  if (!diff.trim()) {
    throw new Error("PATCH diff block is empty");
  }
  return `${diff}\n`;
}

export function isNoChangesDiff(diff: string): boolean {
  const lines = normalizeLfBom(diff)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.length === 1 && lines[0] === "# NO_CHANGES";
}

export function extractChangedPathsFromDiff(diff: string): string[] {
  if (isNoChangesDiff(diff)) return [];
  const paths = new Set<string>();
  let pendingOld: string | null = null;
  for (const line of normalizeLfBom(diff).split("\n")) {
    const gitMatch = line.match(/^diff --git a\/(.+?) b\/(.+)$/);
    if (gitMatch) {
      paths.add(normalizeRepoPath(gitMatch[2]));
      pendingOld = null;
      continue;
    }
    const oldMatch = line.match(/^--- (.+)$/);
    if (oldMatch) {
      pendingOld = oldMatch[1] === "/dev/null" ? null : normalizeRepoPath(oldMatch[1]);
      continue;
    }
    const newMatch = line.match(/^\+\+\+ (.+)$/);
    if (newMatch) {
      if (newMatch[1] !== "/dev/null") {
        paths.add(normalizeRepoPath(newMatch[1]));
      } else if (pendingOld) {
        paths.add(pendingOld);
      }
      pendingOld = null;
    }
  }
  return [...paths].filter(Boolean).sort();
}

export function validatePatchAgainstWriteSet(diff: string, writeSetRaw: string): PatchValidation {
  const changedPaths = extractChangedPathsFromDiff(diff);
  const writeSet = parseWriteSet(writeSetRaw);
  if (writeSet.length === 0 && changedPaths.length > 0) {
    return {
      ok: false,
      reason: "WRITE_SET is empty but PATCH contains real changes",
      changedPaths,
      writeSet,
    };
  }
  const allowed = new Set(writeSet);
  const outside = changedPaths.filter((path) => !allowed.has(path));
  if (outside.length > 0) {
    return {
      ok: false,
      reason: `changed paths outside WRITE_SET: ${outside.join(", ")}`,
      changedPaths,
      writeSet,
    };
  }
  return { ok: true, reason: null, changedPaths, writeSet };
}

function parseHunkHeader(line: string): { oldStart: string; newStart: string; suffix: string } | null {
  const match = line.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$/);
  if (!match) return null;
  return { oldStart: match[1], newStart: match[2], suffix: match[3] ?? "" };
}

function countHunk(lines: string[], startIndex: number): { oldCount: number; newCount: number; endIndex: number } {
  let oldCount = 0;
  let newCount = 0;
  let i = startIndex;
  for (; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("@@ ") || line.startsWith("diff --git ") || line.startsWith("--- ")) break;
    if (line.startsWith("\\ No newline")) continue;
    if (line.startsWith(" ")) {
      oldCount++;
      newCount++;
    } else if (line.startsWith("-")) {
      oldCount++;
    } else if (line.startsWith("+")) {
      newCount++;
    }
  }
  return { oldCount, newCount, endIndex: i };
}

export function normalizeHunkCounts(diff: string): PatchNormalizationResult {
  const lines = normalizeLfBom(diff).split("\n");
  let hunkCountNormalized = false;
  for (let i = 0; i < lines.length; i++) {
    const parsed = parseHunkHeader(lines[i]);
    if (!parsed) continue;
    const counts = countHunk(lines, i + 1);
    const nextHeader = `@@ -${parsed.oldStart},${counts.oldCount} +${parsed.newStart},${counts.newCount} @@${parsed.suffix}`;
    if (nextHeader !== lines[i]) {
      lines[i] = nextHeader;
      hunkCountNormalized = true;
    }
  }
  return { diff: lines.join("\n").replace(/\n*$/, "\n"), hunkCountNormalized };
}

export function extractTestCommands(testsRaw: string): string[] {
  const normalized = normalizeLfBom(testsRaw);
  const fenced = [...normalized.matchAll(/```(?:powershell|bash|shell|sh|text)?\s*\n([\s\S]*?)\n```/gi)]
    .map((m) => m[1])
    .join("\n");
  const source = fenced.trim() ? fenced : normalized;
  const unsafeShellSyntax = /[|;&`]/;
  const allowedCommands = [
    /^\.\\\.venv\\Scripts\\python\.exe\s+-m\s+pytest\b/,
    /^npm\.cmd\s+run\s+test:trigger\s+--\s+tests[\\/]+trigger[\\/]+[A-Za-z0-9._-]+\.test\.ts$/,
  ];
  return source
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .filter((line) => !unsafeShellSyntax.test(line))
    .filter((line) => allowedCommands.some((pattern) => pattern.test(line)));
}

function splitCommand(command: string): string[] {
  const parts: string[] = [];
  let current = "";
  let quote: string | null = null;
  for (let i = 0; i < command.length; i++) {
    const ch = command[i];
    if ((ch === '"' || ch === "'") && quote === null) {
      quote = ch;
      continue;
    }
    if (ch === quote) {
      quote = null;
      continue;
    }
    if (ch === " " && quote === null) {
      if (current) {
        parts.push(current);
        current = "";
      }
      continue;
    }
    current += ch;
  }
  if (current) parts.push(current);
  return parts;
}

class HttpJsonError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`HTTP ${status}: ${body.slice(0, 500)}`);
  }
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function isLoadingModelError(error: unknown): boolean {
  return error instanceof HttpJsonError && error.status === 503 && /loading model/i.test(error.body);
}

async function fetchJson(url: string, init: RequestInit, timeoutMs: number): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    const text = await response.text();
    if (!response.ok) {
      throw new HttpJsonError(response.status, text);
    }
    return JSON.parse(text);
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchJsonWithLoadingRetry(url: string, init: RequestInit, timeoutMs: number): Promise<unknown> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fetchJson(url, init, timeoutMs);
    } catch (error) {
      if (!isLoadingModelError(error) || attempt >= LOADING_MODEL_RETRY_DELAYS_MS.length) {
        throw error;
      }
      await sleep(LOADING_MODEL_RETRY_DELAYS_MS[attempt]);
    }
  }
}

function extractModelEntries(raw: unknown): Array<{ id?: string; model?: string; name?: string; aliases?: unknown; meta?: unknown }> {
  if (!raw || typeof raw !== "object") return [];
  const rec = raw as Record<string, unknown>;
  const data = Array.isArray(rec.data) ? rec.data : [];
  const models = Array.isArray(rec.models) ? rec.models : [];
  return [...data, ...models].filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
}

async function checkModelAlias(baseUrl: string, model: string, timeoutMs: number): Promise<LlamaCppModelInfo> {
  const raw = await fetchJson(`${baseUrl.replace(/\/$/, "")}/models`, { method: "GET" }, timeoutMs);
  const entries = extractModelEntries(raw);
  let nCtx: number | null = null;
  const aliasMatched = entries.some((entry) => {
    const aliases = Array.isArray(entry.aliases) ? entry.aliases : [];
    const meta = entry.meta;
    if (meta && typeof meta === "object" && typeof (meta as Record<string, unknown>).n_ctx === "number") {
      nCtx = (meta as Record<string, number>).n_ctx;
    }
    return entry.id === model || entry.model === model || entry.name === model || aliases.includes(model);
  });
  return { aliasMatched, nCtx, raw };
}

function applyPatch(repoRoot: string, diff: string): ApplyResult {
  const tmpDir = mkdtempSync(join(tmpdir(), "llamacpp-agent-patch-"));
  const patchPath = join(tmpDir, "proposal.diff");
  writeFileSync(patchPath, diff, "utf-8");
  try {
    const check = spawnSync("git", ["apply", "--check", patchPath], {
      cwd: repoRoot,
      encoding: "utf-8",
      windowsHide: true,
    });
    let recountUsed = false;
    if (check.status !== 0) {
      const recount = spawnSync("git", ["apply", "--recount", "--check", patchPath], {
        cwd: repoRoot,
        encoding: "utf-8",
        windowsHide: true,
      });
      if (recount.status !== 0) {
        return { ok: false, error: recount.stderr || recount.stdout || check.stderr || "git apply --check failed", recountUsed };
      }
      recountUsed = true;
    }

    const applyArgs = recountUsed ? ["apply", "--recount", patchPath] : ["apply", patchPath];
    const applied = spawnSync("git", applyArgs, {
      cwd: repoRoot,
      encoding: "utf-8",
      windowsHide: true,
    });
    if (applied.status !== 0) {
      return { ok: false, error: applied.stderr || applied.stdout || "git apply failed", recountUsed };
    }
    return { ok: true, error: null, recountUsed };
  } finally {
    rmSync(tmpDir, { recursive: true, force: true });
  }
}

function revertPatch(repoRoot: string, diff: string): RevertResult {
  const tmpDir = mkdtempSync(join(tmpdir(), "llamacpp-agent-revert-"));
  const patchPath = join(tmpDir, "proposal.diff");
  writeFileSync(patchPath, diff, "utf-8");
  try {
    const reverted = spawnSync("git", ["apply", "-R", "--recount", patchPath], {
      cwd: repoRoot,
      encoding: "utf-8",
      windowsHide: true,
    });
    if (reverted.status !== 0) {
      return { ok: false, error: reverted.stderr || reverted.stdout || "git apply -R failed" };
    }
    return { ok: true, error: null };
  } finally {
    rmSync(tmpDir, { recursive: true, force: true });
  }
}

function runTestCommands(repoRoot: string, commands: string[]): TestRunResult[] {
  return commands.map((command) => {
    const parts = splitCommand(command);
    const [bin, ...args] = parts;
    const result = spawnSync(bin, args, {
      cwd: repoRoot,
      encoding: "utf-8",
      windowsHide: true,
    });
    return {
      command,
      status: result.status,
      stdout: result.stdout ?? "",
      stderr: result.stderr ?? (result.error ? result.error.message : ""),
    };
  });
}

function gitChangedFiles(repoRoot: string): string[] {
  const result = spawnSync("git", ["diff", "--name-only"], {
    cwd: repoRoot,
    encoding: "utf-8",
    windowsHide: true,
  });
  if (result.status !== 0) return [];
  return result.stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).sort();
}

function buildExecutionContract(args: {
  parsed: ParsedLlamaCppResponse;
  changedPaths: string[];
  testResults: TestRunResult[];
  hunkCountNormalized: boolean;
  recountUsed: boolean;
  adapterFallbackUsed: boolean;
}): string {
  const tests = args.testResults.length
    ? args.testResults.map((r) => `- ${r.command}: exit ${r.status}`).join("\n")
    : "- Not run: no files changed.";
  const stdoutPreview = args.testResults
    .map((r) => [r.stdout, r.stderr].filter(Boolean).join("\n").trim())
    .filter(Boolean)
    .join("\n\n")
    .slice(0, 3000);
  return [
    "# Llama.cpp Agent Execution Contract",
    "",
    "## Summary",
    args.parsed.summary,
    "",
    "## Changed Files",
    ...(args.changedPaths.length ? args.changedPaths.map((p) => `- ${p}`) : ["- None"]),
    "",
    "## Tests",
    tests,
    "",
    "## Patch Gates",
    `- hunk_count_normalized: ${args.hunkCountNormalized}`,
    `- recount_used: ${args.recountUsed}`,
    `- adapter_fallback_used: ${args.adapterFallbackUsed}`,
    "",
    "## Risks",
    args.parsed.risks || "None reported.",
    "",
    "## Evidence",
    stdoutPreview ? `\`\`\`text\n${stdoutPreview}\n\`\`\`` : "No command output.",
  ].join("\n");
}

async function callLlamaCpp(
  prompt: string,
  _apiKey: string,
  _contractPath: string | null,
  model: string,
): Promise<TriggerResult> {
  const log = createLogger("[llamacpp_agent_trigger]");
  const baseUrl = (process.env.LLAMACPP_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/$/, "");
  const timeoutMs = envNumber("LLAMACPP_TIMEOUT_MS", DEFAULT_TIMEOUT_MS);
  const maxInputTokens = envNumber("LLAMACPP_MAX_INPUT_TOKENS", DEFAULT_MAX_INPUT_TOKENS);
  const maxOutputTokens = envNumber("LLAMACPP_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS);
  const contextMaxChars = envNumber("LLAMACPP_CONTEXT_MAX_CHARS", DEFAULT_CONTEXT_MAX_CHARS);
  const contextFileMaxChars = envNumber("LLAMACPP_CONTEXT_FILE_MAX_CHARS", DEFAULT_CONTEXT_FILE_MAX_CHARS);
  const temperature = envNumber("LLAMACPP_TEMPERATURE", DEFAULT_TEMPERATURE);
  const topP = envNumber("LLAMACPP_TOP_P", DEFAULT_TOP_P);
  const repeatPenalty = envNumber("LLAMACPP_REPEAT_PENALTY", DEFAULT_REPEAT_PENALTY);
  const minContextTokens = resolveMinContextTokens();
  const packedContext = buildReadSetContext(prompt, process.cwd(), contextMaxChars, contextFileMaxChars);
  const contextFields = {
    context_chars: packedContext.contextChars,
    context_files_count: packedContext.contextFilesCount,
    context_truncated: packedContext.contextTruncated,
  };

  const modelInfo = await checkModelAlias(baseUrl, model, Math.min(timeoutMs, 30_000));
  if (!modelInfo.aliasMatched) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: { error_reason: `model_alias_not_found: ${model}`, model_info: modelInfo.raw, ...contextFields },
    };
  }
  if (modelInfo.nCtx !== null && modelInfo.nCtx < minContextTokens) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: `ctx_too_small: ${modelInfo.nCtx} < ${minContextTokens}`,
        n_ctx: modelInfo.nCtx,
        min_context_tokens: minContextTokens,
        ...contextFields,
      },
    };
  }

  const systemPrompt = [
    "You are local llama.cpp coding executor for hometutor.",
    "Mode: narrow patch executor. Do not include <think> or hidden reasoning.",
    "You have no file tools. Use only the task text and CONTEXT EXCERPTS FROM READ_SET.",
    "Do not claim, edit, or cite file content that is absent from the provided context.",
    "If context is insufficient, return no real diff and explain the blocker in RISKS.",
    "Return sections exactly in this order:",
    SECTION_ORDER.join("\n"),
    "Do not write prose outside the required sections.",
    "READ_SET must list only files actually used from the provided context.",
    "PATCH must contain exactly one fenced ```diff block with unified diff paths like --- a/path and +++ b/path.",
    "Use # NO_CHANGES as the only diff content for strict no-op.",
    "If no changes are needed, PATCH must still contain exactly this fenced block:",
    "```diff\n# NO_CHANGES\n```",
    "Do not return PATCH as plain text.",
    "Do not use # NO_CHANGES to hide missing context; describe missing context in RISKS.",
    "WRITE_SET must be a JSON string array.",
    "Changed paths in PATCH must be a subset of WRITE_SET. If WRITE_SET is [], PATCH must be # NO_CHANGES.",
    "Keep patches minimal and preserve existing style and whitespace.",
    "TESTS must list one command per line: either .\\.venv\\Scripts\\python.exe -m pytest <path> or npm.cmd run test:trigger -- tests/trigger/<name>.test.ts.",
    "Do not use pipes, semicolons, backticks, aliases, chained commands, or shell redirection in TESTS.",
  ].join("\n");

  let response: unknown;
  try {
    response = await fetchJsonWithLoadingRetry(
      `${baseUrl}/chat/completions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: packedContext.prompt },
          ],
          temperature,
          top_p: topP,
          repeat_penalty: repeatPenalty,
          max_tokens: maxOutputTokens,
        }),
      },
      timeoutMs,
    );
  } catch (error) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: isLoadingModelError(error) ? "server_loading_timeout" : "chat_completion_failed",
        error_message: error instanceof Error ? error.message : String(error),
        ...contextFields,
      },
    };
  }

  const content = (response as { choices?: Array<{ message?: { content?: string } }> }).choices?.[0]?.message?.content;
  if (!content) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: "empty_model_response",
        response_preview: JSON.stringify(response).slice(0, 1000),
        ...contextFields,
      },
    };
  }

  let parsed: ParsedLlamaCppResponse;
  let diff: string;
  let validation: PatchValidation;
  try {
    parsed = parseAgentResponse(content);
    diff = extractFencedDiff(parsed.patchRaw);
    validation = validatePatchAgainstWriteSet(diff, parsed.writeSetRaw);
  } catch (err) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: `response_validation_failed: ${err instanceof Error ? err.message : String(err)}`,
        ...contextFields,
      },
    };
  }

  if (!validation.ok) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: validation.reason,
        changed_paths: validation.changedPaths,
        write_set: validation.writeSet,
        ...contextFields,
      },
    };
  }

  if (validation.changedPaths.length === 0 && isNoChangesDiff(diff)) {
    return {
      status: "ok",
      contractContent: buildExecutionContract({
        parsed,
        changedPaths: [],
        testResults: [],
        hunkCountNormalized: false,
        recountUsed: false,
        adapterFallbackUsed: false,
      }),
      actualModel: model,
      fields: {
        changed_paths: [],
        write_set: validation.writeSet,
        hunk_count_normalized: false,
        recount_used: false,
        repair_used: false,
        adapter_fallback_used: false,
        tests_run: [],
        tests_status: "not_run_no_changes",
        max_input_tokens: maxInputTokens,
        max_output_tokens: maxOutputTokens,
        ...contextFields,
        n_ctx: modelInfo.nCtx,
      },
    };
  }

  const testCommands = extractTestCommands(parsed.testsRaw);
  if (testCommands.length === 0) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: "no_allowed_targeted_test_commands",
        changed_paths: validation.changedPaths,
        write_set: validation.writeSet,
        ...contextFields,
      },
    };
  }

  const normalizedPatch = normalizeHunkCounts(diff);
  const applyResult = applyPatch(process.cwd(), normalizedPatch.diff);
  if (!applyResult.ok) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: `git_apply_failed: ${applyResult.error}`,
        changed_paths: validation.changedPaths,
        write_set: validation.writeSet,
        hunk_count_normalized: normalizedPatch.hunkCountNormalized,
        recount_used: applyResult.recountUsed,
        ...contextFields,
      },
    };
  }

  log.log(`running targeted tests: ${testCommands.join(" && ")}`);
  const testResults = runTestCommands(process.cwd(), testCommands);
  const testsPassed = testResults.every((r) => r.status === 0);
  if (!testsPassed) {
    const revertResult = revertPatch(process.cwd(), normalizedPatch.diff);
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        error_reason: "targeted_tests_failed",
        test_results: testResults,
        changed_paths: validation.changedPaths,
        reverted_patch: revertResult.ok,
        revert_error: revertResult.error,
        ...contextFields,
      },
    };
  }

  const changedFiles = gitChangedFiles(process.cwd());
  return {
    status: "ok",
    contractContent: buildExecutionContract({
      parsed,
      changedPaths: changedFiles,
      testResults,
      hunkCountNormalized: normalizedPatch.hunkCountNormalized,
      recountUsed: applyResult.recountUsed,
      adapterFallbackUsed: false,
    }),
    actualModel: model,
    fields: {
      changed_paths: changedFiles,
      write_set: validation.writeSet,
      hunk_count_normalized: normalizedPatch.hunkCountNormalized,
      recount_used: applyResult.recountUsed,
      repair_used: false,
      adapter_fallback_used: false,
      tests_run: testCommands,
      tests_status: "passed",
      max_input_tokens: maxInputTokens,
      max_output_tokens: maxOutputTokens,
      ...contextFields,
      n_ctx: modelInfo.nCtx,
    },
  };
}

const config: AgentTriggerConfig = {
  logLabel: "[llamacpp_agent_trigger]",
  metricsEvent: "llamacpp_agent_prompt",
  model: process.env.LLAMACPP_MODEL ?? DEFAULT_MODEL,
  agentLabel: "llama.cpp local model",
  pipelineLegend:
    "Llama.cpp Trigger -> fenced diff -> write-set gate -> git apply --check -> targeted tests -> execution_contract.md",
  defaultMetricsPath: "archive/team_artifacts/_metrics/llamacpp_agent_trigger.jsonl",
  envPrefix: "LLAMACPP_TRIGGER",
  apiKeyEnvVar: "LLAMACPP_API_KEY",
  modelEnvVar: "LLAMACPP_MODEL",
  contractGeneratedBy: "llamacpp_agent_trigger.ts",
  execute: callLlamaCpp,
};

if (!process.env.LLAMACPP_API_KEY) {
  process.env.LLAMACPP_API_KEY = "local-llamacpp";
}

if (require.main === module) {
  runTrigger(config).catch((err) => {
    console.error("[llamacpp_agent_trigger] fatal:", err);
    process.exit(4);
  });
}
