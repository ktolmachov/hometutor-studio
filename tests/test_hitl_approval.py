from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hitl_approval import assert_approved, load_policy, requires_approval


def test_policy_marks_gate_enforcement_as_approval_required() -> None:
    verdict = requires_approval(
        "enable_gate_enforcing",
        policy={
            "actions": [
                {
                    "name": "enable_gate_enforcing",
                    "requires_approval": True,
                    "reason": "blocks runs",
                }
            ]
        },
    )
    assert verdict.required is True
    assert verdict.reason == "blocks runs"


def test_assert_approved_blocks_without_approval() -> None:
    with pytest.raises(PermissionError):
        assert_approved(
            "git_push",
            approved=False,
            policy={"actions": [{"name": "git_push", "requires_approval": True}]},
        )


def test_unknown_action_does_not_require_approval() -> None:
    assert requires_approval("read_status", policy={"actions": []}).required is False


def test_default_policy_loads() -> None:
    policy = load_policy()
    assert policy["actions"]
