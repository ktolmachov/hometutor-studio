import { describe, it, expect } from "vitest";
import { checkBudgetGate } from "../../scripts/_trigger_shared.js";

describe("checkBudgetGate", () => {
  const MAX = 120_000;
  const WARN = 80_000;

  it("fails when input_tokens exceeds max", () => {
    const r = checkBudgetGate(999_999, MAX, WARN);
    expect(r.ok).toBe(false);
    expect(r.warning).toBe(false);
    expect(r.reason).toContain("exceeds max");
  });

  it("passes with warning when in warning zone", () => {
    const r = checkBudgetGate(95_000, MAX, WARN);
    expect(r.ok).toBe(true);
    expect(r.warning).toBe(true);
    expect(r.reason).toContain("warn threshold");
  });

  it("fails when input_tokens is undefined", () => {
    const r = checkBudgetGate(undefined, MAX, WARN);
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("missing");
  });

  it("passes cleanly when under both thresholds", () => {
    const r = checkBudgetGate(50_000, MAX, WARN);
    expect(r.ok).toBe(true);
    expect(r.warning).toBe(false);
    expect(r.reason).toBeNull();
  });

  it("fails when input_tokens is NaN", () => {
    const r = checkBudgetGate(NaN, MAX, WARN);
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("missing");
  });
});
