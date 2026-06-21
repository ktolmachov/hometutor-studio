/**
 * _tui_contract_validator.ts — Outcome-based contract validation for TUI triggers.
 *
 * Unlike the Chat API validator (deepseek_agent_trigger.ts::validateDeepSeekExecutionProof),
 * the TUI validator focuses on final outcome shape, not intermediate process signals.
 * A TUI executor legitimately reads files, starts work, and creates artifacts — so
 * phrases like "I'll start" or "cat archive/..." in the body are NOT rejected.
 *
 * Fail criteria:
 *   - empty or whitespace-only
 *   - exactly "STARTED" (agent never wrote proof)
 *   - "BLOCKED: no local tool access" (TUI has tools — this means execution didn't happen)
 *   - missing EXECUTION_PROOF: marker
 *   - missing Changed files: or Verification: sections after the marker
 */
import type { ContractValidationResult } from "./_trigger_shared.js";

export function validateTuiExecutionProof(content: string): ContractValidationResult {
  const text = content.trim();

  if (!text) {
    return { ok: false, reason: "empty contract" };
  }

  if (text.toUpperCase() === "STARTED") {
    return { ok: false, reason: "contract is only STARTED — agent never wrote proof" };
  }

  // TUI has local tools — BLOCKED: no local tool access is a failure
  if (text.toLowerCase().startsWith("blocked: no local tool access")) {
    return { ok: false, reason: "BLOCKED: TUI executor has local tools; this response indicates execution did not happen" };
  }

  const marker = "EXECUTION_PROOF:";
  const markerIdx = text.indexOf(marker);

  if (markerIdx < 0) {
    return { ok: false, reason: "missing EXECUTION_PROOF: marker" };
  }

  const proofSection = text.slice(markerIdx);

  const hasChangedFiles =
    /changed files|modified files|touched files|затронутые файлы|измен[её]нные файлы/i.test(proofSection);
  const hasVerification =
    /verification|tests?|pytest|lint|dod|провер/i.test(proofSection);

  if (!hasChangedFiles || !hasVerification) {
    return { ok: false, reason: "missing Changed files: or Verification: section after EXECUTION_PROOF:" };
  }

  return { ok: true };
}
