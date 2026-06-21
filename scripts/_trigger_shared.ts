/**
 * _trigger_shared.ts — Shared runtime for agent trigger scripts.
 *
 * Reduces duplication between cursor_agent_trigger.ts and deepseek_agent_trigger.ts.
 * Each trigger script provides an AgentTriggerConfig + execute callback.
 *
 * Exit codes (synchronised with workflow.py _trigger_cmd_rc_hint):
 *   0 — success
 *   1 — local config / I/O
 *   2 — agent API returned error
 *   3 — transient / retryable failure after one retry
 *   4 — fatal (non‑retryable) or unexpected exception
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AgentTriggerConfig {
  /** Prefix for log lines, e.g. `[cursor_agent_trigger]`. */
  logLabel: string;
  /** Agent name for metrics, e.g. `cursor_agent_prompt`. */
  metricsEvent: string;
  /** Model string to record. */
  model: string;
  /** Human‑readable agent label for heartbeat (e.g. ``Agent.prompt`` / ``DeepSeek API``). */
  agentLabel: string;
  /** Pipeline legend text. */
  pipelineLegend: string;
  /** Default metrics path (env var override via `<PREFIX>_TRIGGER_METRICS_PATH`). */
  defaultMetricsPath: string;
  /** Env‑var prefix for trigger config (e.g. ``CURSOR_TRIGGER_``, ``DEEPSEEK_TRIGGER_``). */
  envPrefix: string;
  /** Env‑var name for the API key. */
  apiKeyEnvVar: string;
  /** Env-var name for the model override (or null). */
  modelEnvVar: string | null;
  /** Name recorded in generated execution_contract.md when the trigger writes it. */
  contractGeneratedBy: string;
  /** Optional trigger-specific validator for generated execution_contract.md content. */
  validateContractContent?: (content: string) => ContractValidationResult;
  /** Require a substantive final execution_contract.md before returning success. */
  requireSubstantiveContract?: boolean;
  /** Callback that performs the actual agent invocation. */
  execute(prompt: string, apiKey: string, contractPath: string | null, model: string): Promise<TriggerResult>;
}

export type ContractValidationResult =
  | { ok: true }
  | { ok: false; reason: string };

export interface TriggerResult {
  status: "ok" | "error";
  /** Machine‑parseable fields for metrics / contract file. */
  fields: Record<string, unknown>;
  /** Content to write to execution_contract.md (may be empty if agent writes its own). */
  contractContent: string | null;
  /** Model string that was actually used (may differ from config.model). */
  actualModel: string;
  /** Number of retry attempts performed by the trigger-specific executor. */
  retryCount?: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const LOG_TIME_ZONE = "Europe/Moscow";

export const EXIT_CONFIG = 1;
export const EXIT_AGENT_STATUS = 2;
export const EXIT_TRANSIENT = 3;
export const EXIT_SDK_FATAL = 4;

const PROMPT_PREVIEW_MAX = 140;
const RESULT_PREVIEW_MAX = 1000;

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function ts(): string {
  const moscowTime = new Intl.DateTimeFormat("sv-SE", {
    timeZone: LOG_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
    .format(new Date())
    .replace(" ", "T");
  return `${moscowTime}+03:00`;
}

export function nowTimestamp(): string {
  return ts();
}

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

export function createLogger(label: string) {
  return {
    log(message: string): void {
      console.log(`${ts()} ${label} ${message}`);
    },
    error(message: string, err?: unknown): void {
      console.error(`${ts()} ${label} ${message}`);
      if (err) console.error(err);
    },
  };
}

export type Logger = ReturnType<typeof createLogger>;

// ---------------------------------------------------------------------------
// Banner
// ---------------------------------------------------------------------------

export function printDoneBanner() {
  const star7 = "*".repeat(7);
  const rule = "*".repeat(72);
  const useColor =
    process.stdout.isTTY &&
    !(process.env.NO_COLOR != null && process.env.NO_COLOR !== "");
  const paint = (s: string): string =>
    useColor ? `\x1b[33;1m${s}\x1b[0m` : s;
  console.log("");
  console.log(paint(rule));
  console.log(paint(`${star7} done (exit 0) ${star7}`));
  console.log(paint(rule));
  console.log("");
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export function writeMetric(metricsPath: string, row: Record<string, unknown>): void {
  try {
    mkdirSync(dirname(metricsPath), { recursive: true });
    appendFileSync(
      metricsPath,
      `${JSON.stringify({ timestamp: ts(), ...row })}\n`,
      "utf-8",
    );
  } catch (err) {
    console.warn(`${ts()} WARN: could not append metrics to ${metricsPath}: ${String(err)}`);
  }
}

// ---------------------------------------------------------------------------
// Token estimation (rough, for logs only)
// ---------------------------------------------------------------------------

export function estimatePromptTokensApprox(text: string): number {
  if (!text) return 0;
  const units = [...text].length;
  return Math.max(1, Math.ceil(units / 3.5));
}

// ---------------------------------------------------------------------------
// Preview helpers
// ---------------------------------------------------------------------------

export function promptPreviewForLog(text: string): string {
  const oneLine = text
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (oneLine.length <= PROMPT_PREVIEW_MAX) return oneLine;
  return `${oneLine.slice(0, PROMPT_PREVIEW_MAX)}…`;
}

export function resultPreviewForLog(value: unknown): string {
  let text: string;
  if (typeof value === "string") {
    text = value;
  } else {
    try {
      text = JSON.stringify(value);
    } catch {
      text = String(value);
    }
  }
  const safe = text
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (safe.length <= RESULT_PREVIEW_MAX) return safe;
  return `${safe.slice(0, RESULT_PREVIEW_MAX)}…`;
}

// ---------------------------------------------------------------------------
// Sleep / elapsed
// ---------------------------------------------------------------------------

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

// ---------------------------------------------------------------------------
// Execution contract path detection
// ---------------------------------------------------------------------------

export function findExecutionContractPath(prompt: string): string | null {
  const envPath = process.env.WORKFLOW_CURRENT_CONTRACT_PATH?.trim();
  if (envPath) return envPath;
  const match = prompt.match(
    /archive[\/\\]team_artifacts[\/\\][^\s`"'<>]+[\/\\]execution_contract\.md/,
  );
  return match?.[0] ?? null;
}

// ---------------------------------------------------------------------------
// Contract gate (mirrors workflow.py::_execution_contract_ready_for_post_agent)
// ---------------------------------------------------------------------------

export function executionContractEligibleForWorkflowPostAgent(path: string | null): boolean {
  if (!path || !existsSync(path)) return false;
  try {
    const t = readFileSync(path, "utf-8").trim();
    return t.length > 0 && t.toUpperCase() !== "STARTED";
  } catch {
    return false;
  }
}

function isStartedOnlyContract(path: string | null): boolean {
  if (!path || !existsSync(path)) return false;
  try {
    return readFileSync(path, "utf-8").trim().toUpperCase() === "STARTED";
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Contract state description
// ---------------------------------------------------------------------------

export function describeContractState(path: string | null): string {
  if (!path) return "execution_contract path not found in task";
  if (!existsSync(path)) return `execution_contract not on disk yet (${path})`;
  try {
    const s = statSync(path);
    const substantive = executionContractEligibleForWorkflowPostAgent(path);
    const gateHint = substantive
      ? "substantive (watch-contract → --post-agent eligible)"
      : isStartedOnlyContract(path)
        ? "STARTED stub only (~8 bytes if LF; workflow ignores until replaced)"
        : "not substantive yet (empty or unreadable)";
    return `${gateHint} (${path}, ${s.size} bytes, mtime=${s.mtime.toISOString()})`;
  } catch (err) {
    return `execution_contract on disk but describe failed (${path}): ${String(err)}`;
  }
}

// ---------------------------------------------------------------------------
// Heartbeat
// ---------------------------------------------------------------------------

export interface HeartbeatHandle {
  stop: () => void;
}

export function startHeartbeat(
  envPrefix: string,
  agentLabel: string,
  logger: Logger,
  contractPath: string | null,
  startedAt: number,
  onStartedStall?: (elapsedMs: number) => void,
  onSubstantiveProof?: (elapsedMs: number) => void,
): HeartbeatHandle | null {
  const intervalEnv = process.env[`${envPrefix}_HEARTBEAT_MS`] ?? "30000";
  const baseIntervalMs = Number(intervalEnv);
  if (!Number.isFinite(baseIntervalMs) || baseIntervalMs <= 0) return null;

  // Cursor + workflow --watch-contract: default off — proof gate is workflow WATCH, not in-flight abort.
  const defaultStallMs = envPrefix === "CURSOR_TRIGGER" ? "0" : "480000";
  const stallEnv = process.env[`${envPrefix}_STARTED_STALL_TIMEOUT_MS`] ?? defaultStallMs;
  const startedStallTimeoutMs = Number(stallEnv);
  const exitEnv =
    process.env[`${envPrefix}_EXIT_ON_SUBSTANTIVE_PROOF`] ??
    (envPrefix === "CURSOR_TRIGGER" ? "1" : "0");
  const exitOnSubstantiveProof = exitEnv !== "0";
  const progressiveCap = 300_000; // 5 min max between heartbeats
  let tickCount = 0;
  let currentIntervalMs = baseIntervalMs;
  let timerId: ReturnType<typeof setTimeout> | null = null;
  let cancelled = false;

  function schedule(fn: () => void, ms: number): void {
    timerId = setTimeout(fn, ms);
    timerId.unref?.();
  }

  function tick() {
    if (cancelled) return;
    tickCount++;
    const elapsedMs = Date.now() - startedAt;
    const proof = describeContractState(contractPath);
    if (tickCount <= 1) {
      const phase =
        "[этот процесс = веха 1/3] агент ещё выполняется; [позже у workflow.py вехи 2-3:] watch substantive proof, post-agent, close.";
      logger.log(
        `${agentLabel}: still waiting (${formatElapsed(elapsedMs)}). ${phase} proof: ${proof}.`,
      );
    } else {
      logger.log(
        `${agentLabel}: still waiting (${formatElapsed(elapsedMs)}). proof: ${proof}.`,
      );
    }

    if (
      Number.isFinite(startedStallTimeoutMs) &&
      startedStallTimeoutMs > 0 &&
      elapsedMs >= startedStallTimeoutMs &&
      isStartedOnlyContract(contractPath)
    ) {
      onStartedStall?.(elapsedMs);
      return;
    }

    if (
      exitOnSubstantiveProof &&
      contractPath &&
      executionContractEligibleForWorkflowPostAgent(contractPath)
    ) {
      cancelled = true;
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
      }
      logger.log(
        `${agentLabel}: substantive execution_contract detected after ${formatElapsed(elapsedMs)}; ` +
        "exiting trigger early (workflow.py --watch-contract → --post-agent). " +
        `Set ${envPrefix}_EXIT_ON_SUBSTANTIVE_PROOF=0 to wait for full Agent.prompt.`,
      );
      onSubstantiveProof?.(elapsedMs);
      return;
    }

    if (cancelled) return;
    currentIntervalMs = Math.min(currentIntervalMs * 2, progressiveCap);
    schedule(tick, currentIntervalMs);
  }

  schedule(tick, currentIntervalMs);

  return {
    stop() {
      cancelled = true;
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
      }
    },
  };
}

export function stopHeartbeat(timer: HeartbeatHandle | null): void {
  timer?.stop();
}

// ---------------------------------------------------------------------------
// Write execution_contract.md (for API‑based triggers; Cursor writes its own)
// ---------------------------------------------------------------------------

export function writeExecutionContract(
  path: string,
  content: string,
  model: string,
  generatedBy: string,
  usage: Record<string, unknown> | null,
): void {
  const dir = dirname(path);
  mkdirSync(dir, { recursive: true });

  const headerLines = [
    "---",
    `generated_by: ${generatedBy}`,
    `model: ${model}`,
    `timestamp: ${ts()}`,
  ];
  if (usage) {
    for (const [k, v] of Object.entries(usage)) {
      headerLines.push(`${k}: ${v ?? "unknown"}`);
    }
  }
  headerLines.push("---", "");

  const fullContent = `${headerLines.join("\n")}${content.trim()}\n`;
  writeFileSync(path, fullContent, "utf-8");
}

// ---------------------------------------------------------------------------
// Task path resolution
// ---------------------------------------------------------------------------

export function resolveTaskPath(): { path: string; source: "argv" | "env" | "default" } {
  const fromArgv = process.argv[2]?.trim();
  if (fromArgv) return { path: fromArgv, source: "argv" };
  const fromEnv = process.env.WORKFLOW_CURRENT_TASK_PATH;
  if (fromEnv) return { path: fromEnv, source: "env" };
  return { path: "doc/current_task.md", source: "default" };
}

// ---------------------------------------------------------------------------
// Main runner — shared entry point for all trigger scripts
// ---------------------------------------------------------------------------

export async function runTrigger(config: AgentTriggerConfig): Promise<void> {
  const log = createLogger(config.logLabel);
  const startedAt = Date.now();
  const metricsPath =
    process.env[`${config.envPrefix}_TRIGGER_METRICS_PATH`] ?? config.defaultMetricsPath;

  log.log(`starting (cwd=${process.cwd()})`);

  process.once("SIGINT", () => {
    log.log(
      "SIGINT received. If the agent completed and wrote execution_contract.md, " +
      "rerun workflow.py --loop to resume post-agent.",
    );
    process.exit(130);
  });

  // ── Resolve task file ──────────────────────────────────────────────────
  const { path: taskPath, source: pathSource } = resolveTaskPath();
  log.log(`task file: ${taskPath} (source: ${pathSource})`);

  const apiKey = process.env[config.apiKeyEnvVar];
  if (!apiKey) {
    log.log(`ERROR: ${config.apiKeyEnvVar} must be set in the environment.`);
    process.exit(EXIT_CONFIG);
  }
  log.log(`${config.apiKeyEnvVar}: present (not logging value)`);

  let prompt: string;
  try {
    prompt = readFileSync(taskPath, "utf-8");
    if (process.env.ORCHESTRATOR_REJECT_REASON) {
      prompt += `\n\n======================================================================\n` +
                `SELF-HEALING RETRY INSTRUCTION:\n` +
                `Your previous attempt was rejected. Reason: ${process.env.ORCHESTRATOR_REJECT_REASON}\n` +
                `Please review the failure reason and correct your execution proof.\n` +
                `======================================================================\n`;
    }
  } catch (err) {
    log.error(`ERROR: cannot read task file: ${taskPath}`, err);
    process.exit(EXIT_CONFIG);
  }
  const promptLines = prompt.split(/\r?\n/).length;
  log.log(`read task OK: ${prompt.length} chars, ${promptLines} lines (content not logged)`);
  log.log(config.pipelineLegend);
  log.log(
    "`[✓ часть 1a]` файл задачи прочитан. Дальше: `[⏳ часть 1b]` отправка промпта в API " +
    "(пакет в реестре ещё не закрывается этим процессом).",
  );

  // ── Pre‑flight ─────────────────────────────────────────────────────────
  const tokEst = estimatePromptTokensApprox(prompt);
  const preview = promptPreviewForLog(prompt);
  const contractPath = findExecutionContractPath(prompt);
  const initialProofState = describeContractState(contractPath);
  log.log(`expected proof file: ${contractPath ?? "(not found in task text)"}`);
  log.log(`initial proof state: ${initialProofState}`);

  const resolvedModel = config.modelEnvVar
    ? (process.env[config.modelEnvVar] ?? config.model)
    : config.model;
  log.log(
    `calling ${config.agentLabel} (model=${resolvedModel}, cwd=${process.cwd()}, ` +
    `~tokens=${tokEst}, preview=${JSON.stringify(preview)})…`,
  );

  // ── Execute agent ──────────────────────────────────────────────────────
  let result: TriggerResult;

  try {
    result = await config.execute(prompt, apiKey, contractPath, resolvedModel);
  } catch (err) {
    // execute() should handle its own retries — anything thrown here is fatal.
    log.error(`ERROR: fatal — ${String(err)}`);
    process.exit(EXIT_SDK_FATAL);
  }

  // ── Status check ───────────────────────────────────────────────────────
  if (result.status === "error") {
    log.log(`ERROR: Agent run failed (status=error)`);
    log.log(`ERROR: result fields: ${resultPreviewForLog(result.fields)}`);
    writeMetric(metricsPath, {
      event: config.metricsEvent,
      status: "error",
      exit_code: EXIT_AGENT_STATUS,
      duration_ms: Date.now() - startedAt,
      cwd: process.cwd(),
      task_path: taskPath,
      prompt_chars: prompt.length,
      prompt_lines: promptLines,
      input_tokens_approx: tokEst,
      model: result.actualModel,
      contract_path: contractPath,
      contract_initial_state: initialProofState,
      contract_final_state: describeContractState(contractPath),
      retry_count: result.retryCount ?? 0,
      ...result.fields,
    });
    process.exit(EXIT_AGENT_STATUS);
  }

  // ── Write contract (if applicable) ──────────────────────────────────────
  if (result.contractContent && contractPath) {
    const validation = config.validateContractContent?.(result.contractContent);
    if (validation && !validation.ok) {
      log.log(`ERROR: generated execution_contract.md rejected: ${validation.reason}`);
      writeMetric(metricsPath, {
        event: config.metricsEvent,
        status: "invalid_contract",
        exit_code: EXIT_AGENT_STATUS,
        duration_ms: Date.now() - startedAt,
        cwd: process.cwd(),
        task_path: taskPath,
        prompt_chars: prompt.length,
        prompt_lines: promptLines,
        input_tokens_approx: tokEst,
        model: result.actualModel,
        contract_path: contractPath,
        contract_initial_state: initialProofState,
        contract_final_state: describeContractState(contractPath),
        invalid_contract_reason: validation.reason,
        retry_count: result.retryCount ?? 0,
        ...result.fields,
      });
      process.exit(EXIT_AGENT_STATUS);
    }

    writeExecutionContract(
      contractPath,
      result.contractContent,
      result.actualModel,
      config.contractGeneratedBy,
      null,
    );
    log.log(`execution_contract.md written: ${contractPath}`);
  }

  const finalProofState = describeContractState(contractPath);
  const proofOk = executionContractEligibleForWorkflowPostAgent(contractPath);
  log.log(
    `final proof state before returning to workflow.py: ${finalProofState}`,
  );
  log.log(
    proofOk
      ? "`[✓ веха 1/3 полностью]` execution_contract уже substantive — родительский workflow.py может сразу признать proof после своего poll и перейти к вехам 2–3."
      : "`[!]` execution_contract ещё не проходит substantive-gate — workflow.py будет ждать (watch) дописывания файла или повторный запуск.",
  );
  log.log(
    "`[важно]` Официально пакет «закрыт полностью» только после успешного шага родителя с close_package / строкой вроде «Package … closed successfully» в логе run_autonomous — это не сообщение этого триггера.",
  );

  const requireSubstantiveContract = config.requireSubstantiveContract ?? true;
  if (requireSubstantiveContract && !proofOk) {
    const reason = contractPath
      ? "execution_contract_not_substantive"
      : "execution_contract_path_not_found";
    log.log(`ERROR: ${reason}; refusing trigger success so orchestrator can fallback or stop.`);
    writeMetric(metricsPath, {
      event: config.metricsEvent,
      status: "invalid_contract",
      exit_code: EXIT_AGENT_STATUS,
      duration_ms: Date.now() - startedAt,
      cwd: process.cwd(),
      task_path: taskPath,
      prompt_chars: prompt.length,
      prompt_lines: promptLines,
      input_tokens_approx: tokEst,
      model: result.actualModel,
      contract_path: contractPath,
      contract_initial_state: initialProofState,
      contract_final_state: finalProofState,
      invalid_contract_reason: reason,
      retry_count: result.retryCount ?? 0,
      ...result.fields,
    });
    process.exit(EXIT_AGENT_STATUS);
  }

  // ── Metrics ────────────────────────────────────────────────────────────
  writeMetric(metricsPath, {
    event: config.metricsEvent,
    status: "finished",
    exit_code: 0,
    duration_ms: Date.now() - startedAt,
    cwd: process.cwd(),
    task_path: taskPath,
    prompt_chars: prompt.length,
    prompt_lines: promptLines,
    input_tokens_approx: tokEst,
    model: result.actualModel,
    contract_path: contractPath,
    contract_initial_state: initialProofState,
    contract_final_state: finalProofState,
    retry_count: result.retryCount ?? 0,
    ...result.fields,
  });

  // ── Done ───────────────────────────────────────────────────────────────
  printDoneBanner();
}

// ---------------------------------------------------------------------------
// Stream JSON parsing (for TUI / child-process triggers)
// ---------------------------------------------------------------------------

export interface StreamEvent {
  type: string;
  [key: string]: unknown;
}

export interface StreamParseResult {
  metadata: Record<string, unknown> | null;
  sessionError: string | null;
  contentPreview: string;
  toolUseCount: number;
  toolErrorCount: number;
  toolSuccessCount: number;
  doneReceived: boolean;
  events: StreamEvent[];
}

export function parseStreamJsonLine(line: string): StreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>;
    if (typeof parsed.type !== "string") return null;
    return parsed as StreamEvent;
  } catch {
    return null;
  }
}

export class StreamJsonAccumulator {
  private _metadata: Record<string, unknown> | null = null;
  private _sessionError: string | null = null;
  private _contentParts: string[] = [];
  private _toolUseCount = 0;
  private _toolErrorCount = 0;
  private _toolSuccessCount = 0;
  private _doneReceived = false;
  private _events: StreamEvent[] = [];

  feed(line: string): void {
    const event = parseStreamJsonLine(line);
    if (!event) return;
    this._events.push(event);

    switch (event.type) {
      case "metadata":
        this._metadata = event;
        break;
      case "error":
        this._sessionError = String(event.message ?? event.error ?? "unknown session error");
        break;
      case "content":
        if (typeof event.content === "string") {
          this._contentParts.push(event.content);
        }
        break;
      case "tool_use":
        this._toolUseCount++;
        break;
      case "tool_result": {
        const hasError =
          event.is_error === true ||
          event.error === true ||
          (typeof event.status === "string" && event.status.toLowerCase() === "error");
        if (hasError) {
          this._toolErrorCount++;
        } else {
          this._toolSuccessCount++;
        }
        break;
      }
      case "done":
        this._doneReceived = true;
        break;
      default:
        break;
    }
  }

  result(): StreamParseResult {
    const fullContent = this._contentParts.join("");
    const preview = fullContent.length <= 500
      ? fullContent
      : `${fullContent.slice(0, 500)}…`;
    return {
      metadata: this._metadata,
      sessionError: this._sessionError,
      contentPreview: preview,
      toolUseCount: this._toolUseCount,
      toolErrorCount: this._toolErrorCount,
      toolSuccessCount: this._toolSuccessCount,
      doneReceived: this._doneReceived,
      events: this._events,
    };
  }
}

// ---------------------------------------------------------------------------
// Repository root detection (for cwd guard)
// ---------------------------------------------------------------------------

export function findRepoRoot(startDir: string): string | null {
  let dir = startDir;
  const { sep } = require("node:path") as typeof import("node:path");
  const { existsSync: exists } = require("node:fs") as typeof import("node:fs");
  const { join } = require("node:path") as typeof import("node:path");

  for (let depth = 0; depth < 20; depth++) {
    if (exists(join(dir, ".git"))) return dir;
    const parent = dir.substring(0, dir.lastIndexOf(sep));
    if (!parent || parent === dir) break;
    dir = parent;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Budget gate (for TUI triggers with token limits)
// ---------------------------------------------------------------------------

export interface BudgetResult {
  ok: boolean;
  warning: boolean;
  reason: string | null;
  inputTokens: number | undefined;
}

export function checkBudgetGate(
  inputTokens: number | undefined,
  maxTokens: number,
  warnTokens: number,
): BudgetResult {
  // Note: callers (deepseek_tui_agent_trigger.ts) guard against undefined inputTokens
  // before calling this function. This branch is a defensive fallback, not reachable
  // in normal flow, but kept for API safety if checkBudgetGate is used elsewhere.
  if (inputTokens === undefined || inputTokens === null || !Number.isFinite(inputTokens)) {
    return { ok: false, warning: false, reason: "input_tokens missing from metadata", inputTokens };
  }
  if (inputTokens > maxTokens) {
    return {
      ok: false,
      warning: false,
      reason: `input_tokens ${inputTokens} exceeds max ${maxTokens}`,
      inputTokens,
    };
  }
  if (inputTokens > warnTokens) {
    return {
      ok: true,
      warning: true,
      reason: `input_tokens ${inputTokens} exceeds warn threshold ${warnTokens}`,
      inputTokens,
    };
  }
  return { ok: true, warning: false, reason: null, inputTokens };
}
