/**
 * Sends task file contents to DeepSeek Chat API (OpenAI-compatible).
 * API key from DEEPSEEK_API_KEY env.
 * Task path: argv[2] | WORKFLOW_CURRENT_TASK_PATH | doc/current_task.md.
 *
 * DeepSeek has no local agent SDK (unlike @cursor/sdk), so this uses
 * the OpenAI-compatible REST API. The response is written to
 * execution_contract.md (path extracted from task text).
 *
 * Exit codes (synced with scripts/workflow.py):
 *   0 - success (DeepSeek returned a response; contract written by runTrigger)
 *   1 - local config / I/O (no DEEPSEEK_API_KEY, unreadable task file)
 *   2 - API returned error, empty response, or contract rejected by validateDeepSeekExecutionProof
 *   3 - transient API error after one retry
 *   4 - fatal (non-retryable) or unexpected exception
 */
import {
  type AgentTriggerConfig,
  type ContractValidationResult,
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
  writeExecutionContract,
} from "./_trigger_shared.js";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

const DEEPSEEK_API_BASE =
  process.env.DEEPSEEK_API_BASE ?? "https://api.deepseek.com/v1";

// Planner role: write refined task instead of execution contract
const STEP_ROLE = process.env.ORCHESTRATOR_STEP_ROLE ?? "executor";
const IS_PLANNER = STEP_ROLE === "planner";
const IS_VERIFIER = STEP_ROLE === "verifier";
const REFINED_TASK_PATH = "doc/current_task_refined.md";

function matchesPlanOnlySignals(lower: string): boolean {
  const planOnlySignals = [
    "i’ll start", // straight apostrophe U+0027
    "i will start",
    "i’ll start", // curly/right single quotation mark U+2019 — visually identical to the line above
    "now read the orchestration file",
    "cat archive/team_artifacts",
    "echo \"started\"",
    "echo 'started'",
    "set-content",
    "out-file",
  ];
  const asciiPlanOnlySignals = [
    "i'll start",
    "i will start",
    "i\u2019ll start",
    "i\u2018ll start",
    "i`ll start",
    "i'll create",
    "i will create",
    "i'll read",
    "i will read",
    "i'll execute",
    "i will execute",
    "read the orchestration file",
    "get-content",
  ];
  return (
    planOnlySignals.some((signal) => lower.includes(signal)) ||
    asciiPlanOnlySignals.some((signal) => lower.includes(signal))
  );
}

/** When there is no EXECUTION_PROOF block, a leading `blocked:` line records API/hand-off state (persisted). */
function isBlockedRefusal(text: string): boolean {
  return text.trimStart().toLowerCase().startsWith("blocked:");
}

export function validateDeepSeekExecutionProof(content: string): ContractValidationResult {
  const text = content.trim();

  if (!text) {
    return { ok: false, reason: "empty DeepSeek response" };
  }

  const marker = "EXECUTION_PROOF:";
  const markerIdx = text.indexOf(marker);

  // No proof block — fall back to legacy gates on the full response.
  if (markerIdx < 0) {
    // Chat API cannot touch the repo; honest BLOCKED line is written to execution_contract.md
    // so workflow.py sees substantive content (not STARTED) and can continue / hand off.
    if (isBlockedRefusal(text)) {
      return { ok: true };
    }
    const lower = text.toLowerCase();
    if (matchesPlanOnlySignals(lower)) {
      return {
        ok: false,
        reason: "DeepSeek response looks like a command plan, not execution proof",
      };
    }
    return {
      ok: false,
      reason: "missing EXECUTION_PROOF marker",
    };
  }

  const proofSection = text.slice(markerIdx).trimStart();

  if (!proofSection.startsWith(marker)) {
    return {
      ok: false,
      reason: "missing EXECUTION_PROOF marker",
    };
  }

  const hasChangedFiles =
    /changed files|modified files|touched files|затронутые файлы|измен[её]нные файлы/i.test(proofSection);
  const hasVerification =
    /verification|tests?|pytest|lint|dod|провер/i.test(proofSection);
  if (!hasChangedFiles || !hasVerification) {
    return {
      ok: false,
      reason: "missing changed-files or verification evidence",
    };
  }

  // Reasoning models often emit a planning preamble; substantive proof below the marker is enough.
  return { ok: true };
}

function buildDeepSeekSuccess(
  content: string,
  actualModel: string,
  usage: Record<string, unknown> | null,
  retryCount: number,
): TriggerResult {
  return {
    status: "ok",
    actualModel,
    retryCount,
    contractContent: content,
    fields: {
      content_chars: content.length,
      usage: usage
        ? `${usage.prompt_tokens ?? "?"}p / ${usage.completion_tokens ?? "?"}c / ${usage.total_tokens ?? "?"}t`
        : null,
    },
  };
}

async function callDeepSeek(
  prompt: string,
  apiKey: string,
  contractPath: string | null,
  model: string,
): Promise<TriggerResult> {
  const log = createLogger("[deepseek_agent_trigger]");
  let retryCount = 0;

  async function attempt(): Promise<{ content: string; actualModel: string; usage: Record<string, unknown> | null }> {
    const heartbeat = startHeartbeat(
      "DEEPSEEK_TRIGGER",
      "DeepSeek API",
      log,
      contractPath,
      Date.now(),
      (elapsedMs) => {
        const finalState = describeContractState(contractPath);
        log.log(
          `ERROR: execution_contract.md stayed STARTED for ${elapsedMs}ms; aborting. ` +
          "Set DEEPSEEK_TRIGGER_STARTED_STALL_TIMEOUT_MS=0 to disable.",
        );
        writeMetric(
          process.env.DEEPSEEK_TRIGGER_METRICS_PATH ??
            "archive/team_artifacts/_metrics/deepseek_agent_trigger.jsonl",
          {
            event: "deepseek_agent_prompt",
            status: "started_stalled",
            exit_code: EXIT_TRANSIENT,
            duration_ms: elapsedMs,
            cwd: process.cwd(),
            model,
            contract_path: contractPath,
            contract_final_state: finalState,
            retry_count: retryCount,
          },
        );
        process.exit(EXIT_TRANSIENT);
      },
    );

    try {
      // Choose system message based on orchestrator step role
      let systemMessage: string;
      if (IS_PLANNER) {
        systemMessage =
          "Ты — планировщик для проекта hometutor.\n" +
          "Тебе дана задача. Твоя цель: проанализировать её, выявить риски и неоднозначности, " +
          "и создать УТОЧНЁННЫЙ ПЛАН выполнения, который передашь исполнителю (executor-агенту).\n\n" +
          "Формат ответа (строго):\n" +
          "## Refined Task Plan\n" +
          "### Objective\n(одно предложение)\n" +
          "### Write-set\n(точный список файлов для изменения)\n" +
          "### Steps\n(нумерованные шаги, конкретные команды/функции)\n" +
          "### DoD (Definition of Done)\n(чёткие критерии завершения, команды проверки)\n" +
          "### Risks\n(потенциальные ловушки)\n\n" +
          "Не выполняй задачу сам — только создай план. Никакого кода в ответе.";
      } else if (IS_VERIFIER) {
        systemMessage =
          "Ты — верификатор для проекта hometutor.\n" +
          "Тебе дан execution_contract.md, написанный агентом-исполнителем. " +
          "Проверь его качество и полноту.\n\n" +
          "Ответь строго в формате:\n" +
          "VERIFICATION_RESULT: PASS | FAIL\n" +
          "Issues: (список проблем или 'none')\n" +
          "Missing evidence: (что не задокументировано)\n" +
          "Recommendation: (что нужно исправить или 'none')";
      } else {
        systemMessage =
          "Ты — автономный ассистент разработки для проекта hometutor.\n" +
          "Выполни задачу из файла ниже. После завершения работы предоставь execution proof:\n" +
          "- краткое описание сделанных изменений\n" +
          "- затронутые файлы\n" +
          "- результаты проверок (lint, тесты)\n" +
          "- любые блокеры или риски\n\n" +
          "STRICT EXECUTION PROOF GATE:\n" +
          "В конце ответа обязателен блок proof (можно после краткого размышления): строка EXECUTION_PROOF: и секции Changed files: и Verification:.\n" +
          "Не подставляй вместо proof один лишь план или только команды shell.\n" +
          "Если нет доступа к локальному репозиторию/инструментам и выполнить работу нельзя — верни ровно одну строку: BLOCKED: no local tool access\n\n" +
          "Формат — plain text markdown, пригодный для записи в execution_contract.md.";
      }

      const url = `${DEEPSEEK_API_BASE.replace(/\/+$/, "")}/chat/completions`;
      const body = JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemMessage },
          { role: "user", content: prompt },
        ],
        temperature: 0.3,
        max_tokens: 16384,
        stream: false,
      });

      log.log(`calling DeepSeek API: ${url} model=${model}`);

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body,
        signal: AbortSignal.timeout(300_000),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "(no body)");
        throw new Error(
          `DeepSeek API returned status ${response.status}: ${errorText.slice(0, 500)}`,
        );
      }

      const data = (await response.json()) as {
        choices?: Array<{ message?: { content?: string } }>;
        model?: string;
        usage?: Record<string, unknown>;
        error?: { message: string };
      };

      if (data.error) {
        throw new Error(`DeepSeek API error: ${data.error.message}`);
      }

      const resultContent = data.choices?.[0]?.message?.content ?? "";
      if (!resultContent.trim()) {
        throw new Error("DeepSeek returned empty content");
      }

      return {
        content: resultContent,
        actualModel: data.model ?? model,
        usage: data.usage ?? null,
      };
    } finally {
      stopHeartbeat(heartbeat);
    }
  }

  try {
    const result = await attempt();
    log.log(
      `DeepSeek API finished: model=${result.actualModel}, content=${result.content.length} chars, usage=${result.usage ? JSON.stringify(result.usage) : "unknown"}`,
    );
    // Planner: write refined task file directly (not execution_contract)
    if (IS_PLANNER) {
      try {
        mkdirSync(dirname(REFINED_TASK_PATH), { recursive: true });
        const { writeFileSync } = await import("node:fs");
        writeFileSync(REFINED_TASK_PATH, result.content, "utf-8");
        log.log(`[planner] Refined task written to ${REFINED_TASK_PATH}`);
      } catch (err) {
        log.error(`[planner] Failed to write refined task: ${String(err)}`);
      }
    }
    return buildDeepSeekSuccess(result.content, result.actualModel, result.usage, retryCount);
  } catch (err) {
    if (!(err instanceof Error)) throw err;
    const errMsg = err.message;
    const isNetworkError =
      err instanceof TypeError ||
      errMsg.includes("fetch") ||
      errMsg.includes("ECONNREFUSED") ||
      errMsg.includes("ENOTFOUND") ||
      errMsg.includes("AbortError") ||
      errMsg.includes("aborted");
    const isServerError =
      errMsg.includes("status 5") ||
      errMsg.includes("rate limit") ||
      errMsg.includes("429") ||
      errMsg.includes("timeout") ||
      errMsg.includes("timed out");
    const isRetryable = isNetworkError || isServerError;

    if (!isRetryable) {
      log.log(`ERROR: DeepSeek API call failed (non-retryable): ${errMsg}`);
      process.exit(EXIT_SDK_FATAL);
    }
    log.log(`WARN: retryable API error - retrying after 5s: ${errMsg}`);
    retryCount = 1;
    await sleep(5000);
    try {
      const result = await attempt();
      log.log(
        `DeepSeek API finished (retry): model=${result.actualModel}, content=${result.content.length} chars`,
      );
      return buildDeepSeekSuccess(result.content, result.actualModel, result.usage, retryCount);
    } catch (err2) {
      log.log(`ERROR: retry failed: ${String(err2)}`);
      process.exit(EXIT_TRANSIENT);
    }
  }
}

const config: AgentTriggerConfig = {
  logLabel: "[deepseek_agent_trigger]",
  metricsEvent: "deepseek_agent_prompt",
  model: process.env.DEEPSEEK_MODEL ?? "deepseek-reasoner",
  agentLabel: "DeepSeek API",
  pipelineLegend:
    "Вехи всего цикла: [1/3] этот скрипт — task + DeepSeek Chat API | [2/3] workflow.py — watch substantive execution_contract.md | [3/3] workflow.py — post-agent + close_package (пакет закрыт в реестре только после успешного close)",
  defaultMetricsPath:
    "archive/team_artifacts/_metrics/deepseek_agent_trigger.jsonl",
  envPrefix: "DEEPSEEK_TRIGGER",
  apiKeyEnvVar: "DEEPSEEK_API_KEY",
  modelEnvVar: "DEEPSEEK_MODEL",
  contractGeneratedBy: "deepseek_agent_trigger.ts",
  validateContractContent: validateDeepSeekExecutionProof,
  execute: callDeepSeek,
};

function isMainModule(): boolean {
  const entry = process.argv[1];
  return Boolean(entry) && resolve(entry) === fileURLToPath(import.meta.url);
}

if (isMainModule()) {
  runTrigger(config).catch((err) => {
    console.error("[deepseek_agent_trigger] fatal:", err);
    process.exit(4);
  });
}
