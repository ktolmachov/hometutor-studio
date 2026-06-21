import { describe, it, expect } from "vitest";
import {
  classifyRisk,
  selectStrategy,
  type AvailableCredentials,
} from "../../scripts/trigger_registry.js";

describe("classifyRisk", () => {
  it("returns explicit COMPLEXITY marker when present", () => {
    expect(classifyRisk("COMPLEXITY: high\nSome task text")).toBe("high");
    expect(classifyRisk("COMPLEXITY: low\nSome task")).toBe("low");
  });

  it("returns low for simple infra task", () => {
    expect(classifyRisk("Update changelog and docs")).toBe("low");
  });

  it("returns medium for schema + security task", () => {
    const task = "Modify config.py and add guardrail validation\nwrite-set:\n- app/config.py\n- app/guardrails.py";
    expect(classifyRisk(task)).toBe("medium");
  });

  it("returns high for complex multi-file schema migration", () => {
    const task =
      "Database schema migration with auth changes\n" +
      "sqlite migration script\n" +
      "write-set:\n" +
      "- app/config.py\n" +
      "- app/user_state.py\n" +
      "- app/security.py\n" +
      "- app/guardrails.py\n" +
      "- tests/test_1.py\n" +
      "- tests/test_2.py\n" +
      "- tests/test_3.py\n" +
      "- tests/test_4.py\n" +
      "- tests/test_5.py\n" +
      "DoD: pytest lint check_readset check_llm check_backlog";
    expect(classifyRisk(task)).toBe("high");
  });
});

describe("selectStrategy", () => {
  const CURSOR_ONLY: AvailableCredentials = { cursor: true, deepseekApi: false, deepseekTui: false };
  const DEEPSEEK_TUI_ONLY: AvailableCredentials = { cursor: false, deepseekApi: true, deepseekTui: true };
  const ALL: AvailableCredentials = { cursor: true, deepseekApi: true, deepseekTui: true };
  const NONE: AvailableCredentials = { cursor: false, deepseekApi: false, deepseekTui: false };
  const API_ONLY: AvailableCredentials = { cursor: false, deepseekApi: true, deepseekTui: false };

  it("returns manual_handoff when no executor credentials", () => {
    expect(selectStrategy("low", NONE).name).toBe("manual_handoff");
    expect(selectStrategy("high", NONE).name).toBe("manual_handoff");
  });

  it("returns manual_handoff with API-only (no local executor)", () => {
    expect(selectStrategy("low", API_ONLY).name).toBe("manual_handoff");
  });

  it("returns direct_cursor for low risk with cursor key", () => {
    expect(selectStrategy("low", CURSOR_ONLY).name).toBe("direct_cursor");
  });

  it("returns direct_deepseek_tui for low risk with deepseek TUI", () => {
    expect(selectStrategy("low", DEEPSEEK_TUI_ONLY).name).toBe("direct_deepseek_tui");
  });

  it("prefers cursor over deepseek_tui when both available (low risk)", () => {
    const s = selectStrategy("low", ALL);
    expect(s.name).toBe("direct_cursor");
    expect(s.steps[0].trigger).toBe("cursor");
  });

  it("returns plan_then_execute for medium risk with full credentials", () => {
    const s = selectStrategy("medium", ALL);
    expect(s.name).toBe("plan_then_execute");
    expect(s.steps).toHaveLength(2);
    expect(s.steps[0]).toEqual({ trigger: "deepseek_api", role: "planner" });
    expect(s.steps[1]).toEqual({ trigger: "cursor", role: "executor" });
  });

  it("falls back to direct for medium risk without planner", () => {
    const s = selectStrategy("medium", CURSOR_ONLY);
    expect(s.name).toBe("direct_cursor");
  });

  it("returns review_execute_verify for high risk with full credentials", () => {
    const s = selectStrategy("high", ALL);
    expect(s.name).toBe("review_execute_verify");
    expect(s.steps).toHaveLength(3);
    expect(s.steps[0].role).toBe("planner");
    expect(s.steps[1].role).toBe("executor");
    expect(s.steps[2].role).toBe("verifier");
  });

  it("respects strategy override", () => {
    const s = selectStrategy("low", ALL, "manual_handoff");
    expect(s.name).toBe("manual_handoff");
  });
});
