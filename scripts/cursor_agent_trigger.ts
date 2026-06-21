/**
 * Sends task file contents to Cursor Agent (local) via @cursor/sdk.
 * API key from CURSOR_API_KEY env.
 * Task path: argv[2] | WORKFLOW_CURRENT_TASK_PATH | doc/current_task.md.
 *
 * Exit codes (synced with scripts/workflow.py):
 *   0 — success
 *   1 — local config / I/O
 *   2 — Agent.prompt returned status=error (after retries)
 *   3 — transient SDK error after retries, or started_stalled (only if CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS > 0)
 *   4 — fatal SDK error or unexpected exception
 */
import { Agent, CursorAgentError } from "@cursor/sdk";
import {
  type AgentTriggerConfig,
  type TriggerResult,
  EXIT_TRANSIENT,
  EXIT_SDK_FATAL,
  runTrigger,
  sleep,
  createLogger,
  startHeartbeat,
  stopHeartbeat,
  writeMetric,
  describeContractState,
} from "./_trigger_shared.js";

type AgentPromptResult = Awaited<ReturnType<typeof Agent.prompt>>;

/** Cursor SDK model ids change over time; map deprecated CLI slugs to API ids. */
const CURSOR_MODEL_ALIASES: Record<string, string> = {
  "composer-2-fast": "composer-2",
  "composer-2.5-fast": "composer-2.5",
};

export function resolveCursorModelId(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "composer-2.5";
  return CURSOR_MODEL_ALIASES[trimmed] ?? trimmed;
}

function agentPromptErrorFields(result: AgentPromptResult): Record<string, unknown> {
  const fields: Record<string, unknown> = {
    result_id: result.id,
    result_status: result.status,
    result_preview: String(result.result ?? "").slice(0, 500),
  };
  const rec = result as Record<string, unknown>;
  for (const key of ["error", "errorMessage", "message", "reason", "code", "statusCode"]) {
    if (rec[key] != null && rec[key] !== "") {
      fields[key] = rec[key];
    }
  }
  try {
    fields.result_json = JSON.stringify(result).slice(0, 2000);
  } catch {
    /* ignore circular / non-serializable */
  }
  return fields;
}

async function callCursor(
  prompt: string,
  apiKey: string,
  contractPath: string | null,
  model: string,
): Promise<TriggerResult> {
  const log = createLogger("[cursor_agent_trigger]");
  const effectiveModel = resolveCursorModelId(model);
  if (effectiveModel !== model.trim()) {
    log.log(
      `WARN: CURSOR_MODEL alias ${JSON.stringify(model.trim())} -> ${JSON.stringify(effectiveModel)}`,
    );
  }
  const retryDelays = (process.env.CURSOR_TRIGGER_RETRY_DELAYS_MS ?? "2000,10000,30000")
    .split(",")
    .map((v) => Number(v.trim()))
    .filter((v) => Number.isFinite(v) && v >= 0);
  let retryCount = 0;

  function makeAttempt(): Promise<AgentPromptResult> {
    const heartbeat = startHeartbeat(
      "CURSOR_TRIGGER",
      "Agent.prompt (Cursor)",
      log,
      contractPath,
      Date.now(),
      (elapsedMs) => {
        const finalState = describeContractState(contractPath);
        log.log(
          `ERROR: execution_contract.md stayed STARTED for ${elapsedMs}ms; aborting. ` +
          "Set CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS=0 to disable.",
        );
        writeMetric(
          process.env.CURSOR_TRIGGER_METRICS_PATH ??
            "archive/team_artifacts/_metrics/cursor_agent_trigger.jsonl",
          {
            event: "cursor_agent_prompt",
            status: "started_stalled",
            exit_code: EXIT_TRANSIENT,
            duration_ms: elapsedMs,
            cwd: process.cwd(),
            model: effectiveModel,
            contract_path: contractPath,
            contract_final_state: finalState,
            retry_count: retryCount,
          },
        );
        process.exit(EXIT_TRANSIENT);
      },
      (elapsedMs) => {
        writeMetric(
          process.env.CURSOR_TRIGGER_METRICS_PATH ??
            "archive/team_artifacts/_metrics/cursor_agent_trigger.jsonl",
          {
            event: "cursor_agent_prompt",
            status: "finished_early",
            exit_code: 0,
            duration_ms: elapsedMs,
            cwd: process.cwd(),
            model: effectiveModel,
            contract_path: contractPath,
            contract_final_state: describeContractState(contractPath),
            retry_count: retryCount,
            early_exit_reason: "substantive_execution_contract",
          },
        );
        process.exit(0);
      },
    );
    return Agent.prompt(prompt, {
      apiKey,
      model: { id: effectiveModel },
      local: { cwd: process.cwd() },
    }).finally(() => stopHeartbeat(heartbeat));
  }

  const maxAttempts = retryDelays.length + 1;
  let lastErr: CursorAgentError | null = null;
  let result: AgentPromptResult | null = null;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (attempt > 0) {
      const delayMs = retryDelays[attempt - 1];
      const prev = lastErr?.message ?? "Agent.prompt status=error";
      log.log(`WARN: retryable - retry ${attempt}/${retryDelays.length} after ${delayMs}ms: ${prev}`);
      await sleep(delayMs);
    }
    retryCount = attempt;
    try {
      result = await makeAttempt();
      lastErr = null;
    } catch (err) {
      if (!(err instanceof CursorAgentError)) {
        const msg = err instanceof Error ? err.message : String(err);
        const retryableNetwork =
          /fetch failed|network|econnrefused|etimedout|unavailable|api key exchange/i.test(
            msg,
          );
        if (retryableNetwork) {
          log.log(`WARN: retryable network/SDK error: ${msg}`);
          lastErr = err instanceof Error ? err : new Error(msg);
          result = null;
          continue;
        }
        throw err;
      }
      if (!err.isRetryable) {
        log.log(`ERROR: CursorAgentError (non-retryable): ${err.message}`);
        return {
          status: "error",
          actualModel: effectiveModel,
          retryCount,
          contractContent: null,
          fields: { fatal_error: err.message, retryable: false },
        };
      }
      lastErr = err;
      result = null;
      continue;
    }

    if (result.status === "error") {
      const fields = agentPromptErrorFields(result);
      log.log(
        `WARN: Agent.prompt status=error (attempt ${attempt + 1}/${maxAttempts}): ` +
        `${JSON.stringify(fields)}`,
      );
      if (attempt < maxAttempts - 1) {
        continue;
      }
      return {
        status: "error",
        actualModel: effectiveModel,
        retryCount,
        contractContent: null,
        fields,
      };
    }
    break;
  }

  if (lastErr || !result) {
    log.log(`ERROR: retry failed after ${retryCount} attempt(s): ${lastErr?.message ?? "unknown"}`);
    process.exit(EXIT_TRANSIENT);
  }

  const resultChars =
    typeof result.result === "string" ? result.result.length : null;

  return {
    status: "ok",
    actualModel: effectiveModel,
    retryCount,
    contractContent: null,
    fields: {
      result_id: result.id,
      result_chars: resultChars,
    },
  };
}

const config: AgentTriggerConfig = {
  logLabel: "[cursor_agent_trigger]",
  metricsEvent: "cursor_agent_prompt",
  model: process.env.CURSOR_MODEL ?? "composer-2.5",
  agentLabel: "Agent.prompt (Cursor)",
  pipelineLegend:
    "Вехи всего цикла: [1/3] этот скрипт — task + Agent.prompt (Cursor SDK) | [2/3] workflow.py — watch substantive execution_contract.md | [3/3] workflow.py — post-agent + close_package (пакет закрыт в реестре только после успешного close)",
  defaultMetricsPath:
    "archive/team_artifacts/_metrics/cursor_agent_trigger.jsonl",
  envPrefix: "CURSOR_TRIGGER",
  apiKeyEnvVar: "CURSOR_API_KEY",
  modelEnvVar: "CURSOR_MODEL",
  contractGeneratedBy: "cursor_agent_trigger.ts",
  requireSubstantiveContract: false,
  execute: callCursor,
};

runTrigger(config)
  .then(() => {
    process.exit(0);
  })
  .catch((err) => {
    console.error("[cursor_agent_trigger] fatal:", err);
    process.exit(4);
  });
