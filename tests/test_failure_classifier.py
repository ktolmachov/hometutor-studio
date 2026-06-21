from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from failure_classifier import classify_exit_code, load_failure_classes


def test_exit_zero_is_success() -> None:
    cls = classify_exit_code(0)
    assert cls.name == "success"
    assert cls.next_action == "noop"
    assert cls.retryable is False


def test_execution_proof_missing_has_actionable_next_step() -> None:
    cls = classify_exit_code(3)
    assert cls.name == "execution_proof_missing"
    assert "execution_contract" in cls.next_action
    assert cls.retryable is True


def test_policy_extended_exit_codes_eight_nine_ten_eleven() -> None:
    assert classify_exit_code(10).name == "post_agent_success_continue_non_stop"
    assert classify_exit_code(10).severity == "info"
    assert classify_exit_code(11).name == "post_agent_chat_api_handoff_pause"
    assert classify_exit_code(11).severity == "info"
    assert classify_exit_code(9).name == "pipeline_lock_conflict"
    assert classify_exit_code(8).name == "cli_validation_or_context_gate_failed"


def test_unknown_exit_code_is_still_serializable() -> None:
    payload = classify_exit_code(99).as_dict()
    assert payload["exit_code"] == 99
    assert payload["name"] == "unknown_exit_code"


def test_load_failure_classes_from_policy_file(tmp_path: Path) -> None:
    policy = tmp_path / "failure_classes.yaml"
    policy.write_text(
        """
{
  "classes": {
    "9": {
      "name": "custom_gate",
      "severity": "warning",
      "next_action": "ask_human_to_review",
      "retryable": false
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    classes = load_failure_classes(policy)

    assert classes[9].name == "custom_gate"
    assert classes[9].next_action == "ask_human_to_review"


def test_policy_rejects_non_boolean_retryable(tmp_path: Path) -> None:
    policy = tmp_path / "failure_classes.yaml"
    policy.write_text(
        """
{
  "classes": {
    "9": {
      "name": "custom_gate",
      "severity": "warning",
      "next_action": "ask_human_to_review",
      "retryable": "false"
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    try:
        load_failure_classes(policy)
    except ValueError as exc:
        assert "retryable must be boolean" in str(exc)
    else:
        raise AssertionError("policy with string retryable must fail")
