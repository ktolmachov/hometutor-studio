import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import {
  type AgentTriggerConfig,
  type TriggerResult,
  runTrigger,
  createLogger,
  startHeartbeat,
  stopHeartbeat,
  findRepoRoot,
  StreamJsonAccumulator,
  checkBudgetGate,
  executionContractEligibleForWorkflowPostAgent,
} from "./_trigger_shared.js";
import { validateTuiExecutionProof } from "./_tui_contract_validator.js";

// ── Config from env ──
const MAX_INPUT_TOKENS = Number(process.env.DEEPSEEK_TUI_MAX_INPUT_TOKENS ?? "120000");
const WARN_INPUT_TOKENS = Number(process.env.DEEPSEEK_TUI_WARN_INPUT_TOKENS ?? "80000");
const TIMEOUT_MS = Number(process.env.DEEPSEEK_TUI_TIMEOUT_MS ?? "900000");
const TIMEOUT_KILL_GRACE_MS = Number(process.env.DEEPSEEK_TUI_TIMEOUT_KILL_GRACE_MS ?? "5000");
const PROOF_POLL_MS = Number(process.env.DEEPSEEK_TUI_PROOF_POLL_MS ?? "5000");
const EXIT_ON_SUBSTANTIVE_CONTRACT =
  (process.env.DEEPSEEK_TUI_EXIT_ON_SUBSTANTIVE_CONTRACT ?? "1") !== "0";

/**
 * Split DEEPSEEK_CLI_CMD into executable + leading args (supports quoted paths with spaces).
 * Examples:
 *   "python.exe C:\path\script.py"          → { bin: "python.exe", prefixArgs: ["C:\path\script.py"] }
 *   '"C:\path with spaces\python.exe" a.py' → { bin: "C:\path with spaces\python.exe", prefixArgs: ["a.py"] }
 *   "deepseek"                               → { bin: "deepseek", prefixArgs: [] }
 */
export function parseDeepseekCliCmd(cmdStr: string): { bin: string; prefixArgs: string[] } {
  const trimmed = cmdStr.trim();
  if (!trimmed) return { bin: "deepseek", prefixArgs: [] };

  const parts: string[] = [];
  let i = 0;
  while (i < trimmed.length) {
    if (trimmed[i] === " ") {
      i++;
      continue;
    }
    if (trimmed[i] === '"') {
      const end = trimmed.indexOf('"', i + 1);
      if (end < 0) {
        // Unclosed quote: consume rest of string
        parts.push(trimmed.slice(i + 1));
        break;
      }
      parts.push(trimmed.slice(i + 1, end));
      i = end + 1;
      continue;
    }
    const start = i;
    while (i < trimmed.length && trimmed[i] !== " ") i++;
    parts.push(trimmed.slice(start, i));
  }

  return { bin: parts[0] ?? "deepseek", prefixArgs: parts.slice(1) };
}

/**
 * Decide whether to use shell: true when spawning a binary on Windows.
 * Shell is required for bare command names (e.g. "deepseek" → resolves to deepseek.cmd)
 * and explicit .cmd/.bat paths. Direct executables (.exe, .py, paths with separators)
 * are spawned directly to avoid CMD quoting issues.
 */
export function needsWindowsShell(bin: string): boolean {
  if (process.platform !== "win32") return false;
  if (/\.(cmd|bat)$/i.test(bin)) return true;
  // Bare name without extension or path separators → likely a .cmd wrapper installed by npm/pip
  const isBareCmd = !bin.includes("/") && !bin.includes("\\") && !/\.\w+$/.test(bin);
  return isBareCmd;
}

function terminateProcessTree(
  child: ReturnType<typeof spawn>,
  log: ReturnType<typeof createLogger>,
): void {
  if (!child.pid) {
    child.kill("SIGKILL");
    return;
  }

  if (process.platform === "win32") {
    const result = spawnSync(
      "taskkill.exe",
      ["/PID", String(child.pid), "/T", "/F"],
      { stdio: "ignore" },
    );
    if (result.error) {
      log.log(`taskkill failed: ${result.error.message}; falling back to child.kill(SIGKILL).`);
      child.kill("SIGKILL");
    }
    return;
  }

  child.kill("SIGKILL");
}

function closeChildPipes(child: ReturnType<typeof spawn>): void {
  child.stdout?.destroy();
  child.stderr?.destroy();
  child.stdin?.destroy();
  child.unref();
}

// ── Pre-run context estimation ──
function estimateRepoContextTokens(cwd: string): number {
  const gitFiles = spawnSync("git", ["ls-files"], {
    cwd,
    encoding: "utf-8",
    windowsHide: true,
  });
  if (!gitFiles.error && gitFiles.status === 0 && gitFiles.stdout.trim()) {
    const skipPath = /(^|\/)(archive|data|dist|build|htmlcov|coverage|logs|eval_data)\//;
    const skipExt = /\.(png|jpe?g|gif|webp|ico|pdf|zip|gz|7z|sqlite|db|bin|onnx|pkl|mp4|mov|wav)$/i;
    let approxChars = 0;
    for (const relPath of gitFiles.stdout.split(/\r?\n/)) {
      if (!relPath || skipPath.test(relPath) || skipExt.test(relPath)) continue;
      try {
        const stat = statSync(join(cwd, relPath));
        if (stat.isFile()) {
          // Cap each file so a few generated docs cannot dominate the advisory estimate.
          approxChars += Math.min(stat.size, 8000);
        }
      } catch {
        // ignore files removed between git ls-files and stat
      }
    }
    return Math.ceil(approxChars / 4);
  }

  let fileCount = 0;
  const excludeDirs = new Set([
    ".git", "node_modules", ".venv", "__pycache__", "chroma_db", ".pytest_cache",
    "archive", "data", "dist", "build", ".vscode", ".idea", "htmlcov", "coverage", ".gemini",
    ".python", "logs", ".agents", ".kiro", "eval_data"
  ]);

  function walk(dir: string) {
    try {
      const entries = readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory()) {
          if (!excludeDirs.has(entry.name)) {
            walk(join(dir, entry.name));
          }
        } else if (entry.isFile()) {
          fileCount++;
        }
      }
    } catch {
      // ignore unreadable dirs
    }
  }

  walk(cwd);
  return fileCount * 200; // rough heuristic: 200 tokens per tracked file
}

// ── Main executor ──
async function callDeepSeekTui(
  prompt: string,
  apiKey: string,
  contractPath: string | null,
  model: string,
): Promise<TriggerResult> {
  const log = createLogger("[deepseek_tui_trigger]");

  // 1. Verify cwd = repo root
  const repoRoot = findRepoRoot(process.cwd());
  let cwdVerified = false;
  if (repoRoot && repoRoot !== process.cwd()) {
    log.log(`Warning: process.cwd() is not repo root. Changing directory to ${repoRoot}`);
    process.chdir(repoRoot);
    cwdVerified = true;
  } else if (repoRoot === process.cwd()) {
    cwdVerified = true;
  } else {
    log.log("Warning: Could not detect repo root (.git missing). Proceeding with current cwd.");
  }

  // 2. Pre-run estimation. This is intentionally advisory: the rough repo-file
  // heuristic can be very pessimistic, while the real budget is enforced below
  // from DeepSeek stream metadata after the CLI reports actual input_tokens.
  const estimate = estimateRepoContextTokens(process.cwd());
  log.log(`Pre-run context estimation: ~${estimate} tokens`);
  if (estimate > MAX_INPUT_TOKENS * 2) {
    log.log(
      `Warning: Pre-run context estimate (${estimate} tokens) exceeds ` +
      `2 × MAX_INPUT_TOKENS (${MAX_INPUT_TOKENS * 2}). ` +
      "Add a .deepseekignore to reduce repo context, or raise DEEPSEEK_TUI_MAX_INPUT_TOKENS. " +
      "Continuing — hard budget is enforced on actual stream metadata input_tokens.",
    );
  } else if (estimate > MAX_INPUT_TOKENS) {
    log.log(
      `Warning: Pre-run context estimate (${estimate} tokens) exceeds threshold ` +
      `(${MAX_INPUT_TOKENS}), but this estimate is advisory. Continuing and enforcing ` +
      "the hard budget against actual stream metadata.",
    );
  }

  const budgetWarning = estimate > WARN_INPUT_TOKENS;
  if (budgetWarning) {
    log.log(`Warning: Pre-run context estimate (${estimate} tokens) is high (warning threshold: ${WARN_INPUT_TOKENS}).`);
  }

  if (!existsSync(".deepseekignore") && !existsSync(".deepseek/config.json")) {
    log.log("WARN: no .deepseekignore found — DeepSeek TUI may scan all repo files. Consider creating one to reduce input token cost.");
  }

  // Frame the prompt for TUI execution. Do NOT add "Read doc/current_task.md" here —
  // `prompt` already IS the full task content; repeating the read instruction wastes
  // tokens and confuses the agent into reading the file a second time.
  const compactPrompt = [
    `ORCHESTRATION TASK — execute completely in this session (repository cwd: ${process.cwd()}).`,
    `Constraints: use only the task read-set/write-set/DoD rules listed below.`,
    `PROOF REQUIREMENT: replace ${contractPath ?? "execution_contract.md"} STARTED stub with the full execution proof before exiting.`,
    ``,
    `TASK:`,
    prompt,
  ].join("\n");

  // 3. Spawn deepseek exec
  log.log(`Spawning deepseek exec with model ${model}...`);
  const deepseekBinStr = process.env.DEEPSEEK_CLI_CMD ?? "deepseek";
  const { bin, prefixArgs } = parseDeepseekCliCmd(deepseekBinStr);
  const spawnArgs = [...prefixArgs, "exec", "--auto", "--output-format", "stream-json", compactPrompt];
  const spawnEnv = { ...process.env, DEEPSEEK_MODEL: model };
  let child: ReturnType<typeof spawn>;
  if (needsWindowsShell(bin)) {
    const quotedBin = bin.includes(" ") ? `"${bin}"` : bin;
    const shellCmd = [quotedBin, ...spawnArgs.map((a) => JSON.stringify(a))].join(" ");
    child = spawn(shellCmd, [], { cwd: process.cwd(), env: spawnEnv, shell: true });
  } else {
    child = spawn(bin, spawnArgs, { cwd: process.cwd(), env: spawnEnv });
  }

  const accumulator = new StreamJsonAccumulator();
  const heartbeat = startHeartbeat(
    "DEEPSEEK_TUI_TRIGGER",
    "DeepSeek TUI",
    log,
    contractPath,
    Date.now(),
    () => {
      requestChildStop("started_stall");
    },
  );
  let processExitCode: number | null = null;
  let processExitSignal: string | null = null;
  let stopReason: "timeout" | "proof_ready" | "started_stall" | null = null;
  let forcedReturn = false;
  let killGraceId: ReturnType<typeof setTimeout> | null = null;
  let proofMonitorId: ReturnType<typeof setInterval> | null = null;
  let resolveChildClose: (() => void) | null = null;

  function requestChildStop(reason: "timeout" | "proof_ready" | "started_stall"): void {
    if (stopReason) return;
    stopReason = reason;
    const message =
      reason === "timeout"
        ? `Timeout ${TIMEOUT_MS}ms exceeded. Killing child process...`
        : reason === "proof_ready"
          ? "execution_contract.md is substantive; stopping DeepSeek TUI and returning to workflow."
          : "execution_contract.md stayed STARTED past stall timeout; stopping DeepSeek TUI.";
    log.log(message);
    stopHeartbeat(heartbeat);
    if (proofMonitorId) {
      clearInterval(proofMonitorId);
      proofMonitorId = null;
    }
    terminateProcessTree(child, log);
    killGraceId = setTimeout(() => {
      if (resolveChildClose) {
        forcedReturn = true;
        processExitCode = processExitCode ?? -1;
        processExitSignal = processExitSignal ?? reason.toUpperCase();
        log.log(
          `Child process did not close within ${TIMEOUT_KILL_GRACE_MS}ms after ${reason}; returning control to orchestrator.`,
        );
        closeChildPipes(child);
        const resolve = resolveChildClose;
        resolveChildClose = null;
        resolve();
      }
    }, TIMEOUT_KILL_GRACE_MS);
  }

  // 4. Stream-parse stdout
  if (child.stdout) {
    const rl = createInterface({ input: child.stdout });
    rl.on("line", (line) => {
      accumulator.feed(line);
    });
  } else {
    log.log("WARN: child.stdout is null (shell spawn edge case); stream parsing disabled.");
  }

  if (child.stderr) {
    child.stderr.on("data", (data: Buffer) => {
      // Log stderr for debugging, but don't accumulate as stream-json
      log.log(`[stderr] ${data.toString().trim()}`);
    });
  }

  // 5. Setup proof-aware fast exit, timeout, and wait for exit
  if (
    EXIT_ON_SUBSTANTIVE_CONTRACT &&
    contractPath &&
    Number.isFinite(PROOF_POLL_MS) &&
    PROOF_POLL_MS > 0
  ) {
    proofMonitorId = setInterval(() => {
      if (executionContractEligibleForWorkflowPostAgent(contractPath)) {
        requestChildStop("proof_ready");
      }
    }, PROOF_POLL_MS);
  }

  const timeoutId = setTimeout(() => {
    requestChildStop("timeout");
  }, TIMEOUT_MS);

  await new Promise<void>((resolve) => {
    resolveChildClose = resolve;
    child.on("close", (code, signal) => {
      if (killGraceId) clearTimeout(killGraceId);
      resolveChildClose = null;
      processExitCode = code;
      processExitSignal = signal;
      resolve();
    });
    child.on("error", (err) => {
      log.log(`Child process error: ${err.message}`);
      if (killGraceId) clearTimeout(killGraceId);
      resolveChildClose = null;
      processExitCode = -1;
      resolve();
    });
  });

  clearTimeout(timeoutId);
  if (proofMonitorId) clearInterval(proofMonitorId);
  stopHeartbeat(heartbeat);

  const parsed = accumulator.result();
  
  const fields = {
    budget_warning: budgetWarning,
    pre_run_token_estimate: estimate,
    tool_use_count: parsed.toolUseCount,
    tool_error_count: parsed.toolErrorCount,
    tool_success_count: parsed.toolSuccessCount,
    cwd_verified: cwdVerified,
    repo_root: repoRoot ?? process.cwd(),
    session_id: parsed.metadata?.session_id as string | undefined,
    process_exit_code: processExitCode,
    process_exit_signal: processExitSignal,
    timed_out: stopReason === "timeout",
    started_stalled: stopReason === "started_stall",
    proof_ready_return: stopReason === "proof_ready",
    forced_return: forcedReturn,
    budget_input_tokens_missing: false,
    budget_warning_reason: budgetWarning ? "pre_run_estimate_high" : null,
    duration_ms: (parsed.metadata?.duration_ms as number) ?? 0, // Fallback if missing
  };

  // 6. After exit: check outcomes
  if (stopReason === "proof_ready") {
     return {
        status: "ok",
        contractContent: null,
        actualModel: model,
        fields: {
           ...fields,
           content_preview: parsed.contentPreview,
           input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
           output_tokens: (parsed.metadata?.output_tokens as number) ?? 0,
        },
     };
  }

  if (stopReason === "started_stall") {
     return {
        status: "error",
        contractContent: null,
        actualModel: model,
        fields: {
           ...fields,
           error_reason: "started_stall: execution_contract remained STARTED",
           input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
           output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
        },
     };
  }

  if (stopReason === "timeout") {
     return {
        status: "error",
        contractContent: null,
        actualModel: model,
        fields: {
           ...fields,
           error_reason: `timeout: exceeded ${TIMEOUT_MS}ms`,
           input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
           output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
        },
     };
  }

  if (processExitCode !== 0) {
     return {
        status: "error",
        contractContent: null,
        actualModel: model,
        fields: {
           ...fields,
           error_reason: parsed.sessionError ?? `Process exited with code ${processExitCode} (signal: ${processExitSignal})`,
           input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
           output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
        },
     };
  }

  if (parsed.sessionError) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        ...fields,
        error_reason: `agent_error: ${parsed.sessionError}`,
        input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
        output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
      },
    };
  }

  if (!parsed.metadata) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        ...fields,
        error_reason: "missing_metadata",
      },
    };
  }

  const agentStatus = parsed.metadata.status ?? (processExitCode === 0 ? "completed" : "failed");
  if (agentStatus !== "completed") {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        ...fields,
        error_reason: `agent_failed: metadata status is ${parsed.metadata.status}`,
        input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
        output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
      },
    };
  }

  if (!parsed.doneReceived) {
    return {
      status: "error",
      contractContent: null,
      actualModel: model,
      fields: {
        ...fields,
        error_reason: "missing_done: stream closed before 'done' event",
        input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
        output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
      },
    };
  }

  const actualInputTokens = parsed.metadata.input_tokens as number | undefined;
  if (typeof actualInputTokens === "number" && Number.isFinite(actualInputTokens)) {
    const budgetResult = checkBudgetGate(
      actualInputTokens,
      MAX_INPUT_TOKENS,
      WARN_INPUT_TOKENS,
    );

    fields.budget_warning = fields.budget_warning || budgetResult.warning;
    fields.budget_warning_reason = budgetResult.reason ?? fields.budget_warning_reason;

    if (!budgetResult.ok) {
      return {
        status: "error",
        contractContent: null,
        actualModel: model,
        fields: {
          ...fields,
          error_reason: `budget_exceeded: ${budgetResult.reason}`,
          input_tokens: (parsed.metadata?.input_tokens as number) ?? undefined,
          output_tokens: (parsed.metadata?.output_tokens as number) ?? undefined,
        },
      };
    }
  } else {
    fields.budget_warning = true;
    fields.budget_input_tokens_missing = true;
    fields.budget_warning_reason = "input_tokens missing from metadata";
    log.log(
      "Warning: DeepSeek stream metadata did not include input_tokens; " +
      "treating budget as unknown instead of failing the completed session.",
    );
  }

  if (parsed.toolErrorCount > 0) {
     log.log(`Note: Agent encountered ${parsed.toolErrorCount} tool errors, but session completed successfully.`);
  }

  // 7. Return TriggerResult — TUI agent writes contract itself via local file access
  return {
    status: "ok",
    contractContent: null,
    actualModel: model,
    fields: {
      ...fields,
      content_preview: parsed.contentPreview,
      input_tokens: actualInputTokens,
      output_tokens: (parsed.metadata.output_tokens as number) ?? 0,
    },
  };
}

const config: AgentTriggerConfig = {
  logLabel: "[deepseek_tui_trigger]",
  metricsEvent: "deepseek_tui_agent_prompt",
  model: process.env.DEEPSEEK_MODEL ?? "deepseek-v4-flash",
  agentLabel: "DeepSeek TUI",
  pipelineLegend: "TUI Trigger -> workflow",
  defaultMetricsPath: "archive/team_artifacts/_metrics/trigger_metrics.jsonl",
  envPrefix: "DEEPSEEK_TUI_TRIGGER",
  apiKeyEnvVar: "DEEPSEEK_API_KEY",
  modelEnvVar: "DEEPSEEK_MODEL",
  contractGeneratedBy: "deepseek_tui_agent_trigger.ts",
  validateContractContent: validateTuiExecutionProof,
  execute: callDeepSeekTui,
};

// If run directly, start the trigger loop
if (require.main === module) {
  runTrigger(config).catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
