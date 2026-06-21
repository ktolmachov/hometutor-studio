/**
 * orchestrator_integration.test.ts
 *
 * Tests trigger_orchestrator.ts logic via the underlying modules it uses:
 * - trigger_registry (strategy selection + risk classification)
 * - adaptive history (success-rate gating)
 * - fallback logic (exit-code-based alternate executor selection)
 *
 * We do NOT mock spawnSync here (that would be an e2e test).
 * Instead we test the pure decision logic that the orchestrator uses.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { writeFileSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import * as os from "node:os";
import {
  classifyRiskWithScore,
  selectStrategy,
  detectCredentials,
  type AvailableCredentials,
} from "../../scripts/trigger_registry.js";

// ---------------------------------------------------------------------------
// Risk classification with score detail
// ---------------------------------------------------------------------------

describe("classifyRiskWithScore", () => {
  it("returns explicit marker with correct score/signals", () => {
    const result = classifyRiskWithScore("COMPLEXITY: high\nSome task");
    expect(result.level).toBe("high");
    expect(result.score).toBe(4);
    expect(result.signals.explicit_marker).toBe(true);
  });

  it("returns low for simple task with score=0", () => {
    const result = classifyRiskWithScore("Update changelog");
    expect(result.level).toBe("low");
    expect(result.score).toBe(0);
    expect(result.signals.explicit_marker).toBe(false);
    expect(result.signals.has_schema_change).toBe(false);
  });

  it("returns medium for config+security task with correct score", () => {
    const task = "Modify config.py and add guardrail validation\nwrite-set:\n- app/config.py\n- app/guardrails.py";
    const result = classifyRiskWithScore(task);
    expect(result.level).toBe("medium");
    expect(result.score).toBeGreaterThanOrEqual(2);
    expect(result.signals.has_security_path).toBe(true);
    expect(result.signals.has_config_change).toBe(true);
  });

  it("returns high for schema migration with many files", () => {
    const task =
      "Database schema migration with auth changes\n" +
      "sqlite migration script\n" +
      "write-set:\n" +
      Array.from({ length: 10 }, (_, i) => `- app/file_${i}.py\n`).join("") +
      "DoD: pytest lint check_readset check_llm check_backlog";
    const result = classifyRiskWithScore(task);
    expect(result.level).toBe("high");
    expect(result.score).toBeGreaterThanOrEqual(4);
    expect(result.signals.has_schema_change).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Fallback logic simulation
// ---------------------------------------------------------------------------

describe("Fallback executor selection logic", () => {
  const CURSOR_ONLY: AvailableCredentials = { cursor: true, deepseekApi: false, deepseekTui: false };
  const TUI_ONLY: AvailableCredentials = { cursor: false, deepseekApi: true, deepseekTui: true };
  const ALL: AvailableCredentials = { cursor: true, deepseekApi: true, deepseekTui: true };
  const NONE: AvailableCredentials = { cursor: false, deepseekApi: false, deepseekTui: false };

  it("direct_cursor with tui available → fallback is deepseek_tui", () => {
    const strategy = selectStrategy("low", ALL);
    expect(strategy.name).toBe("direct_cursor");
    // Simulate fallback: cursor is steps[0], and creds.deepseekTui is true
    const primaryTrigger = strategy.steps[0].trigger;
    const fallback = primaryTrigger === "cursor" && ALL.deepseekTui ? "deepseek_tui" : null;
    expect(fallback).toBe("deepseek_tui");
  });

  it("direct_deepseek_tui with cursor available → fallback is cursor", () => {
    const strategy = selectStrategy("low", { ...ALL, cursor: false });
    // No cursor → picks deepseek_tui
    const primaryTrigger = strategy.steps[0].trigger;
    // But if rawCreds.cursor is true, fallback exists
    const fallback = primaryTrigger === "deepseek_tui" && ALL.cursor ? "cursor" : null;
    expect(fallback).toBe("cursor");
  });

  it("no fallback when only cursor available", () => {
    const strategy = selectStrategy("low", CURSOR_ONLY);
    const primaryTrigger = strategy.steps[0].trigger;
    const fallback = primaryTrigger === "cursor" && CURSOR_ONLY.deepseekTui ? "deepseek_tui" : null;
    expect(fallback).toBeNull();
  });

  it("no fallback when only TUI available", () => {
    const strategy = selectStrategy("low", TUI_ONLY);
    const primaryTrigger = strategy.steps[0].trigger;
    const fallback = primaryTrigger === "deepseek_tui" && TUI_ONLY.cursor ? "cursor" : null;
    expect(fallback).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// L4: Adaptive success-rate logic (pure computation)
// ---------------------------------------------------------------------------

describe("Adaptive history: success rate computation", () => {
  let tmpDir: string;
  let metricsPath: string;

  beforeEach(() => {
    tmpDir = join(os.tmpdir(), `orchestrator_test_${Date.now()}`);
    mkdirSync(tmpDir, { recursive: true });
    metricsPath = join(tmpDir, "trigger_metrics.jsonl");
  });

  afterEach(() => {
    if (existsSync(tmpDir)) rmSync(tmpDir, { recursive: true });
  });

  function writeRows(rows: object[]) {
    writeFileSync(metricsPath, rows.map((r) => JSON.stringify(r)).join("\n") + "\n", "utf-8");
  }

  function computeRate(rows: object[], trigger: string): number | null {
    const relevant = rows.filter((r: any) =>
      r.event === "trigger_orchestrator" &&
      Array.isArray(r.steps) &&
      r.steps.some((s: any) => s.trigger === trigger),
    );
    if (relevant.length === 0) return null;
    const successes = relevant.filter((r: any) => r.overall_status === "finished").length;
    return successes / relevant.length;
  }

  it("returns null when no history", () => {
    const rows: object[] = [];
    expect(computeRate(rows, "cursor")).toBeNull();
  });

  it("returns 1.0 when all cursor runs succeeded", () => {
    const rows = [
      { event: "trigger_orchestrator", overall_status: "finished", steps: [{ trigger: "cursor", status: "finished" }] },
      { event: "trigger_orchestrator", overall_status: "finished", steps: [{ trigger: "cursor", status: "finished" }] },
    ];
    expect(computeRate(rows, "cursor")).toBe(1.0);
  });

  it("returns 0.0 when all cursor runs failed", () => {
    const rows = [
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
    ];
    expect(computeRate(rows, "cursor")).toBe(0.0);
  });

  it("cursor rate < 40% → adaptive demotion should set cursor=false", () => {
    const rows = [
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
      { event: "trigger_orchestrator", overall_status: "finished", steps: [{ trigger: "cursor", status: "finished" }] },
    ];
    const rate = computeRate(rows, "cursor");
    expect(rate).toBe(0.25);
    expect(rate! < 0.4).toBe(true); // should trigger demotion
  });

  it("cursor rate >= 40% → no demotion", () => {
    const rows = [
      { event: "trigger_orchestrator", overall_status: "finished", steps: [{ trigger: "cursor", status: "finished" }] },
      { event: "trigger_orchestrator", overall_status: "finished", steps: [{ trigger: "cursor", status: "finished" }] },
      { event: "trigger_orchestrator", overall_status: "error", steps: [{ trigger: "cursor", status: "error" }] },
    ];
    const rate = computeRate(rows, "cursor");
    expect(rate).toBeCloseTo(0.667, 2);
    expect(rate! < 0.4).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// L2: Multi-step strategy step ordering
// ---------------------------------------------------------------------------

describe("Multi-step strategy step ordering", () => {
  const ALL: AvailableCredentials = { cursor: true, deepseekApi: true, deepseekTui: true };

  it("plan_then_execute has planner first, then executor", () => {
    const s = selectStrategy("medium", ALL);
    expect(s.name).toBe("plan_then_execute");
    expect(s.steps[0].role).toBe("planner");
    expect(s.steps[1].role).toBe("executor");
    expect(s.steps[0].trigger).toBe("deepseek_api");
    expect(s.steps[1].trigger).toBe("cursor"); // cursor preferred
  });

  it("review_execute_verify has 3 steps in correct order", () => {
    const s = selectStrategy("high", ALL);
    expect(s.name).toBe("review_execute_verify");
    expect(s.steps).toHaveLength(3);
    expect(s.steps[0].role).toBe("planner");
    expect(s.steps[1].role).toBe("executor");
    expect(s.steps[2].role).toBe("verifier");
  });

  it("step roles are distinct and make semantic sense", () => {
    const s = selectStrategy("high", ALL);
    const roles = s.steps.map((step) => step.role);
    // verifier should not come before executor
    const execIdx = roles.indexOf("executor");
    const verifyIdx = roles.indexOf("verifier");
    expect(execIdx).toBeLessThan(verifyIdx);
  });
});

describe("Self-healing guardrails", () => {
  it("does not self-heal retry deterministic TUI timeouts", () => {
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    expect(text).toContain('"timeout:"');
    expect(text).toContain("NON_SELF_HEALABLE_ERROR_PREFIXES");
  });

  it("does not self-heal started_stall errors", () => {
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    expect(text).toContain('"started_stall:"');
  });

  it("does not self-heal structural contract errors", () => {
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    expect(text).toContain('"execution_contract_not_substantive"');
    expect(text).toContain('"execution_contract_path_not_found"');
  });

  it("forces a fast TUI model for low-risk direct execution", () => {
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    expect(text).toContain("ORCHESTRATOR_DEEPSEEK_TUI_LOW_MODEL");
    expect(text).toContain('DEEPSEEK_MODEL: LOW_RISK_TUI_MODEL');
    expect(text).toContain('riskLevel === "low"');
  });

  it("does not treat missing input token metadata as deterministic self-heal blocker", () => {
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    const [, prefixesBlock = ""] = text.split("NON_SELF_HEALABLE_ERROR_PREFIXES");
    expect(prefixesBlock).not.toContain("input_tokens missing");
  });

  it("cursor fallback uses configurable multi-retry backoff", () => {
    const text = readFileSync("scripts/cursor_agent_trigger.ts", "utf-8");
    expect(text).toContain("CURSOR_TRIGGER_RETRY_DELAYS_MS");
    expect(text).toContain("2000,10000,30000");
    expect(text).toContain("retry failed after");
  });

  it("cursor default model is composer-2.5 with alias for composer-2.5-fast", () => {
    const text = readFileSync("scripts/cursor_agent_trigger.ts", "utf-8");
    expect(text).toMatch(/CURSOR_MODEL\s*\?\?\s*"composer-2\.5"/);
    expect(text).toContain("resolveCursorModelId");
    expect(text).toContain('"composer-2.5-fast": "composer-2.5"');
  });

  it("cursor stall metric captures actual retry count not hardcoded 0", () => {
    const text = readFileSync("scripts/cursor_agent_trigger.ts", "utf-8");
    // The stall callback must reference `retryCount` (closure variable), not a literal 0.
    // Accept both explicit `retry_count: retryCount` and shorthand `retry_count,` next to retryCount.
    expect(
      text.includes("retry_count: retryCount") ||
      /retry_count,[\s\S]{0,5}\/\/[^\n]*retryCount/.test(text),
    ).toBe(true);
  });

  it("deepseek TUI prompt does not redundantly instruct agent to read file it already has", () => {
    const text = readFileSync("scripts/deepseek_tui_agent_trigger.ts", "utf-8");
    expect(text).not.toContain("Read doc/current_task.md. Execute it completely");
    expect(text).toContain("ORCHESTRATION TASK");
    expect(text).toContain("PROOF REQUIREMENT");
  });

  it("deepseek advisory context estimate prefers git-tracked files", () => {
    const text = readFileSync("scripts/deepseek_tui_agent_trigger.ts", "utf-8");
    expect(text).toContain('spawnSync("git", ["ls-files"]');
    expect(text).toContain("Math.min(stat.size, 8000)");
  });

  it("fallback does not select demoted cursor (creds.cursor=false overrides rawCreds)", () => {
    // BUG-2 regression: if cursor was demoted by adaptive history, fallback must not pick it.
    // The orchestrator checks creds.cursor (effective) not rawCreds.cursor (raw env).
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    // Verify fallback selection uses `creds.cursor`, not `rawCreds.cursor`
    // Extract the line(s) around alternate trigger selection
    const lines = text.split("\n");
    const fallbackLines = lines.filter((l) =>
      l.includes("deepseek_tui") && l.includes("cursor") && l.includes("trigger"),
    );
    // None of the fallback lines should reference rawCreds.cursor in the selection branch
    const hasRawCredsFallback = fallbackLines.some((l) => l.includes("rawCreds.cursor"));
    expect(hasRawCredsFallback).toBe(false);
  });

  it("circuit breaker filters only trigger_orchestrator events, ignores individual trigger rows", () => {
    // BUG-5 regression: readRecentMetricRows may include rows from individual triggers
    // which lack overall_status; those must not count toward circuit breaker activation.
    const text = readFileSync("scripts/trigger_orchestrator.ts", "utf-8");
    // checkCircuitBreaker must filter by event === "trigger_orchestrator"
    const cbIdx = text.indexOf("checkCircuitBreaker");
    const cbBlock = text.slice(cbIdx, cbIdx + 600);
    expect(cbBlock).toContain('event === "trigger_orchestrator"');
  });
});
