/**
 * trigger_orchestrator.ts — Smart Trigger Orchestrator (Phase 1)
 *
 * Improvements over Phase 0:
 *   - Fallback chain: if primary executor fails, tries alternate executor (L1)
 *   - Structured error reading from metrics (L1)
 *   - Multi-step execution: plan→execute→verify (L2)
 *   - Risk signals written to metrics for observability (L3)
 *   - Adaptive credential weighting based on recent history (L4)
 */
import { readFileSync, appendFileSync, mkdirSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join, dirname } from "node:path";
import {
  TRIGGER_REGISTRY,
  detectCredentials,
  classifyRiskWithScore,
  selectStrategy,
  type AvailableCredentials,
  type TriggerDef,
} from "./trigger_registry.js";
import { createLogger, findRepoRoot } from "./_trigger_shared.js";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const METRICS_WINDOW = Number(process.env.ORCHESTRATOR_HISTORY_WINDOW ?? "10");
const FALLBACK_RC_CODES = new Set([1, 2, 3]); // retryable exit codes for fallback

// Circuit breaker: if last N orchestrator runs all failed, pause before retrying
const CIRCUIT_BREAKER_THRESHOLD = Number(process.env.ORCHESTRATOR_CIRCUIT_BREAKER_THRESHOLD ?? "3");
const COOLDOWN_SECS = Number(process.env.ORCHESTRATOR_COOLDOWN_SECS ?? "30");

// Self-healing: max retries when execution_contract rejected
const SELF_HEAL_MAX_RETRIES = Number(process.env.ORCHESTRATOR_SELF_HEAL_RETRIES ?? "1");
const LOW_RISK_TUI_MODEL = process.env.ORCHESTRATOR_DEEPSEEK_TUI_LOW_MODEL ?? "deepseek-v4-flash";
const KEEP_DEEPSEEK_MODEL_OVERRIDE = process.env.ORCHESTRATOR_KEEP_DEEPSEEK_MODEL === "1";
const NON_SELF_HEALABLE_ERROR_PREFIXES = [
  "budget_pre_estimate_exceeded:",
  "budget_exceeded:",
  "timeout:",
  "missing_metadata",
  // Structural / state errors — retry won't fix without external intervention
  "started_stall:",
  "execution_contract_not_substantive",
  "execution_contract_path_not_found",
];

// ---------------------------------------------------------------------------
// Task reading
// ---------------------------------------------------------------------------

function getTaskContent(): string {
  const taskPath = process.env.WORKFLOW_CURRENT_TASK_PATH || "doc/current_task.md";
  try {
    return readFileSync(taskPath, "utf-8");
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// L4: Adaptive history — downgrade cursor.success if history shows it failing
// ---------------------------------------------------------------------------

interface MetricRow {
  event?: string;
  strategy?: string;
  overall_status?: string;
  steps?: Array<{ trigger: string; status: string }>;
  error_reason?: string;
  invalid_contract_reason?: string;
  fields?: { error_reason?: string };
}

function readRecentMetricRows(metricsPath: string, n: number): MetricRow[] {
  if (!existsSync(metricsPath)) return [];
  try {
    const lines = readFileSync(metricsPath, "utf-8")
      .split("\n")
      .filter((l) => l.trim())
      .slice(-n);
    return lines.map((l) => {
      try { return JSON.parse(l) as MetricRow; } catch { return {}; }
    });
  } catch {
    return [];
  }
}

function computeSuccessRate(rows: MetricRow[], triggerName: string): number | null {
  const relevant = rows.filter(
    (r) => r.event === "trigger_orchestrator" &&
      Array.isArray(r.steps) &&
      r.steps.some((s) => s.trigger === triggerName),
  );
  if (relevant.length === 0) return null;
  const successes = relevant.filter((r) => r.overall_status === "finished").length;
  return successes / relevant.length;
}

/**
 * Adapt credentials based on recent history.
 * If cursor success rate < 40% over last N runs → treat cursor as unavailable
 * so selectStrategy falls back to deepseek_tui.
 */
function getAdaptedCreds(
  creds: AvailableCredentials,
  metricsPath: string,
): { creds: AvailableCredentials; adaptations: string[] } {
  const adaptations: string[] = [];
  const rows = readRecentMetricRows(metricsPath, METRICS_WINDOW);
  if (rows.length === 0) return { creds, adaptations };

  const cursorRate = computeSuccessRate(rows, "cursor");
  if (cursorRate !== null && cursorRate < 0.4) {
    adaptations.push(
      `cursor success rate ${(cursorRate * 100).toFixed(0)}% < 40% over last ${rows.length} runs — demoting cursor`,
    );
    return { creds: { ...creds, cursor: false }, adaptations };
  }

  return { creds, adaptations };
}

// ---------------------------------------------------------------------------
// Circuit breaker
// ---------------------------------------------------------------------------

async function checkCircuitBreaker(
  metricsPath: string,
  log: ReturnType<typeof createLogger>,
): Promise<void> {
  const rows = readRecentMetricRows(metricsPath, CIRCUIT_BREAKER_THRESHOLD * 3)
    .filter((r) => r.event === "trigger_orchestrator");
  if (rows.length < CIRCUIT_BREAKER_THRESHOLD) return;
  const lastN = rows.slice(-CIRCUIT_BREAKER_THRESHOLD);
  const allFailed = lastN.every((r) => r.overall_status === "error");
  if (!allFailed) return;

  log.log(
    `[circuit-breaker] Last ${CIRCUIT_BREAKER_THRESHOLD} orchestrator runs all failed. ` +
    `Cooling down for ${COOLDOWN_SECS}s before proceeding...`,
  );
  await new Promise((resolve) => setTimeout(resolve, COOLDOWN_SECS * 1000));
  log.log(`[circuit-breaker] Cooldown complete. Proceeding.`);
}

// ---------------------------------------------------------------------------
// L1: Spawn a single trigger step, return exit code
// ---------------------------------------------------------------------------

function spawnTrigger(
  triggerDef: TriggerDef,
  extraEnv: Record<string, string>,
  log: ReturnType<typeof createLogger>,
): { exitCode: number; durationMs: number } {
  const npxCmd = process.platform === "win32" ? "npx.cmd" : "npx";
  log.log(`  → spawning: ${triggerDef.scriptPath}`);
  const startTime = Date.now();
  const child = spawnSync(npxCmd, ["tsx", triggerDef.scriptPath], {
    stdio: "inherit",
    env: { ...process.env, ...extraEnv },
    shell: process.platform === "win32",
  });
  const durationMs = Date.now() - startTime;
  const exitCode = child.status ?? 1;
  log.log(`  ← exit ${exitCode} after ${durationMs}ms`);
  return { exitCode, durationMs };
}

// ---------------------------------------------------------------------------
// L3: Last metrics row for structured error reading
// ---------------------------------------------------------------------------

function readLastMetricRow(metricsPath: string): MetricRow {
  if (!existsSync(metricsPath)) return {};
  try {
    const lines = readFileSync(metricsPath, "utf-8")
      .split("\n")
      .filter((l) => l.trim());
    if (lines.length === 0) return {};
    return JSON.parse(lines[lines.length - 1]) as MetricRow;
  } catch {
    return {};
  }
}

function isSelfHealableError(errorReason: string | undefined): boolean {
  if (!errorReason) return true;
  return !NON_SELF_HEALABLE_ERROR_PREFIXES.some((prefix) => errorReason.startsWith(prefix));
}

function metricErrorReason(row: MetricRow): string | undefined {
  return row.fields?.error_reason ?? row.error_reason ?? row.invalid_contract_reason;
}

function stepModelEnv(
  triggerName: string,
  role: string,
  riskLevel: string,
): Record<string, string> {
  if (
    triggerName === "deepseek_tui" &&
    role === "executor" &&
    riskLevel === "low" &&
    !KEEP_DEEPSEEK_MODEL_OVERRIDE
  ) {
    return { DEEPSEEK_MODEL: LOW_RISK_TUI_MODEL };
  }
  return {};
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const log = createLogger("[orchestrator]");
  log.log("Starting Smart Trigger Orchestrator (Phase 1)...");

  const repoRoot = findRepoRoot(process.cwd()) || process.cwd();
  const metricsPath = join(repoRoot, "archive", "team_artifacts", "_metrics", "trigger_metrics.jsonl");

  // 0. Circuit breaker — pause if last N runs all failed
  await checkCircuitBreaker(metricsPath, log);

  // 1. Read task
  const taskContent = getTaskContent();

  // 2. Classify risk with full score detail (L3)
  const riskDetail = classifyRiskWithScore(taskContent);
  log.log(`Risk classification: ${riskDetail.level} (score=${riskDetail.score})`);
  log.log(`Risk signals: ${JSON.stringify(riskDetail.signals)}`);

  // 3. Detect credentials
  const rawCreds = detectCredentials();
  log.log(`Credentials raw: cursor=${rawCreds.cursor}, deepseekApi=${rawCreds.deepseekApi}, deepseekTui=${rawCreds.deepseekTui}`);

  // 4. L4: Adaptive history adjustment
  const { creds, adaptations } = getAdaptedCreds(rawCreds, metricsPath);
  for (const msg of adaptations) log.log(`[adaptive] ${msg}`);

  // 5. Select strategy
  const strategyNameOverride = process.env.TRIGGER_STRATEGY as any;
  const strategy = selectStrategy(riskDetail.level, creds, strategyNameOverride);
  log.log(`Selected strategy: ${strategy.name}`);
  log.log(`Rationale: ${strategy.description}`);

  // 6. Manual handoff
  if (strategy.name === "manual_handoff" || strategy.steps.length === 0) {
    log.log("Manual handoff required. No executor available for this strategy.");
    console.log(`
=====================================================================
СЛЕДУЮЩИЙ ШАГ — ВРУЧНУЮ (роутер ждёт файл execution_contract.md)
=====================================================================
1. Откройте doc/current_task.md
2. Передайте задачу вашему IDE агенту.
3. Дождитесь создания archive/team_artifacts/.../execution_contract.md
=====================================================================
`);
    process.exit(0);
  }

  // ---------------------------------------------------------------------------
  // L2: Execute steps sequentially with context passing
  // ---------------------------------------------------------------------------

  const stepResults: Array<{
    trigger: string;
    role: string;
    exitCode: number;
    durationMs: number;
    errorReason?: string;
  }> = [];

  let currentTaskPath = process.env.WORKFLOW_CURRENT_TASK_PATH || "doc/current_task.md";
  let overallExitCode = 0;
  const wallStart = Date.now();

  for (let i = 0; i < strategy.steps.length; i++) {
    const step = strategy.steps[i];
    const triggerDef = TRIGGER_REGISTRY.find((t) => t.name === step.trigger);

    if (!triggerDef) {
      log.error(`Step ${i + 1}/${strategy.steps.length}: trigger '${step.trigger}' not found in registry.`);
      overallExitCode = 1;
      break;
    }

    log.log(`\nStep ${i + 1}/${strategy.steps.length}: ${step.role.toUpperCase()} via ${triggerDef.name}`);

    // Build per-step env
    const stepEnv: Record<string, string> = {
      WORKFLOW_CURRENT_TASK_PATH: currentTaskPath,
      ORCHESTRATOR_STEP_INDEX: String(i),
      ORCHESTRATOR_STEP_ROLE: step.role,
      ORCHESTRATOR_STRATEGY: strategy.name,
      ORCHESTRATOR_TOTAL_STEPS: String(strategy.steps.length),
      ...stepModelEnv(step.trigger, step.role, riskDetail.level),
    };

    let exitCode = 1;
    let durationMs = 0;
    let errorReason: string | undefined;

    // Self-healing loop: if exitCode === 2 (validation failed), retry up to SELF_HEAL_MAX_RETRIES
    for (let retry = 0; retry <= SELF_HEAL_MAX_RETRIES; retry++) {
      const runEnv = { ...stepEnv };
      if (retry > 0 && errorReason) {
        runEnv.ORCHESTRATOR_REJECT_REASON = errorReason;
        log.log(`[self-heal] Retry ${retry}/${SELF_HEAL_MAX_RETRIES} with rejection reason: ${errorReason}`);
      }

      const res = spawnTrigger(triggerDef, runEnv, log);
      exitCode = res.exitCode;
      durationMs += res.durationMs;

      // L1: Read structured error from last metrics row
      const lastMetric = readLastMetricRow(metricsPath);
      errorReason = metricErrorReason(lastMetric);

      // Only self-heal if it's a validation error (rc=2). Other errors (rc=1,3,4) either fallback or fail.
      if (exitCode === 2 && !isSelfHealableError(errorReason)) {
        log.log(`[self-heal] Not retrying deterministic error: ${errorReason}`);
        break;
      }
      if (exitCode !== 2) break;
    }

    stepResults.push({ trigger: step.trigger, role: step.role, exitCode, durationMs, errorReason });

    if (exitCode !== 0) {
      log.log(`Step ${i + 1} failed (rc=${exitCode})${errorReason ? `: ${errorReason}` : ""}`);

      // L1: Fallback — if this is an executor step and the next step in the strategy
      // is also an executor, skip to it instead of failing
      if (
        step.role === "executor" &&
        FALLBACK_RC_CODES.has(exitCode) &&
        i + 1 < strategy.steps.length &&
        strategy.steps[i + 1].role === "executor"
      ) {
        log.log(`[fallback] Trying next executor step (${strategy.steps[i + 1].trigger})...`);
        continue; // loop continues to next step
      }

      // L1: If only 1 executor step but we have an alternate executor credential,
      // build an ad-hoc fallback step
      if (
        step.role === "executor" &&
        FALLBACK_RC_CODES.has(exitCode) &&
        strategy.steps.length === 1
      ) {
        const alternateTrigger = step.trigger === "cursor" && creds.deepseekTui
          ? "deepseek_tui"
          : step.trigger === "deepseek_tui" && creds.cursor
            ? "cursor"
            : null;

        if (alternateTrigger) {
          const altDef = TRIGGER_REGISTRY.find((t) => t.name === alternateTrigger)!;
          log.log(`[fallback] Primary executor failed. Trying alternate: ${alternateTrigger}`);
          const fallbackEnv = {
            ...stepEnv,
            ...stepModelEnv(alternateTrigger, "executor", riskDetail.level),
          };
          const fallback = spawnTrigger(altDef, fallbackEnv, log);
          const fallbackMetric = readLastMetricRow(metricsPath);
          const fallbackError = metricErrorReason(fallbackMetric);
          stepResults.push({
            trigger: alternateTrigger,
            role: "executor_fallback",
            exitCode: fallback.exitCode,
            durationMs: fallback.durationMs,
            errorReason: fallbackError,
          });
          overallExitCode = fallback.exitCode;
          if (fallback.exitCode !== 0) {
            log.log(`[fallback] Alternate executor also failed (rc=${fallback.exitCode}).`);
          } else {
            log.log(`[fallback] Alternate executor succeeded.`);
          }
          break; // no more steps after executor+fallback
        }
      }

      overallExitCode = exitCode;
      break; // non-recoverable
    }

    // If planner step succeeded, set refined task path for next step
    if (step.role === "planner") {
      const refinedPath = "doc/current_task_refined.md";
      if (existsSync(refinedPath)) {
        currentTaskPath = refinedPath;
        log.log(`[planner] Refined task written to ${refinedPath} — next step will use it.`);
      }
    }
  }

  const overallDurationMs = Date.now() - wallStart;

  // 7. Write orchestrator metrics (L3: includes risk signals)
  const orchestratorMetric = {
    event: "trigger_orchestrator",
    strategy: strategy.name,
    risk_level: riskDetail.level,
    risk_score: riskDetail.score,
    risk_signals: riskDetail.signals,
    adaptive_adjustments: adaptations,
    credentials_raw: rawCreds,
    credentials_effective: creds,
    steps: stepResults,
    overall_status: overallExitCode === 0 ? "finished" : "error",
    overall_duration_ms: overallDurationMs,
    timestamp: new Date().toISOString(),
  };

  try {
    mkdirSync(dirname(metricsPath), { recursive: true });
    appendFileSync(metricsPath, JSON.stringify(orchestratorMetric) + "\n", "utf-8");
  } catch (err) {
    log.error(`Warning: Failed to write orchestrator metrics to ${metricsPath}:`, err);
  }

  process.exit(overallExitCode);
}

main().catch((err) => {
  console.error("[orchestrator] fatal:", err);
  process.exit(1);
});
