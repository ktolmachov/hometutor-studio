import { describe, it, expect } from "vitest";
import { validateTuiExecutionProof } from "../../scripts/_tui_contract_validator.js";

describe("validateTuiExecutionProof", () => {
  it("accepts valid EXECUTION_PROOF with Changed files and Verification", () => {
    const r = validateTuiExecutionProof(
      "EXECUTION_PROOF:\n\n" +
      "Summary: Delivered the requested behavior.\n\n" +
      "Changed files:\n" +
      "- app/smart_study_router.py\n" +
      "- tests/test_smart_study_router.py\n\n" +
      "Verification:\n" +
      "- pytest tests/test_smart_study_router.py: PASS\n",
    );
    expect(r.ok).toBe(true);
  });

  it("rejects STARTED-only contract", () => {
    const r = validateTuiExecutionProof("STARTED");
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("STARTED");
  });

  it("rejects missing EXECUTION_PROOF marker", () => {
    const r = validateTuiExecutionProof(
      "I did some work and changed files.\n" +
      "Changed files:\n- app/foo.py\n" +
      "Verification:\n- pytest: PASS\n",
    );
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("missing EXECUTION_PROOF");
  });

  it("rejects BLOCKED: no local tool access (TUI has tools)", () => {
    const r = validateTuiExecutionProof("BLOCKED: no local tool access");
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("TUI executor has local tools");
  });

  it("accepts plan-like preamble followed by valid EXECUTION_PROOF (NOT rejected for TUI)", () => {
    const r = validateTuiExecutionProof(
      "I'll start by reading the orchestration file.\n" +
      "cat archive/team_artifacts/pkg/orchestration_continue.md\n\n" +
      "EXECUTION_PROOF:\n\n" +
      "Summary: Done.\n\n" +
      "Changed files:\n" +
      "- app/foo.py\n\n" +
      "Verification:\n" +
      "- pytest tests/test_foo.py: PASS\n",
    );
    expect(r.ok).toBe(true);
  });

  it("rejects empty contract", () => {
    const r = validateTuiExecutionProof("");
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("empty");
  });

  it("rejects EXECUTION_PROOF without Changed files section", () => {
    const r = validateTuiExecutionProof(
      "EXECUTION_PROOF:\n\n" +
      "Summary: Did things.\n\n" +
      "Verification:\n" +
      "- pytest: PASS\n",
    );
    expect(r.ok).toBe(false);
    expect(r.reason).toContain("missing Changed files");
  });

  it("accepts Russian section headers", () => {
    const r = validateTuiExecutionProof(
      "EXECUTION_PROOF:\n\n" +
      "Изменённые файлы:\n" +
      "- app/foo.py\n\n" +
      "Проверка:\n" +
      "- pytest: OK\n",
    );
    expect(r.ok).toBe(true);
  });
});
