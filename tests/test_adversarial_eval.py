from __future__ import annotations

import json

import adversarial_eval as ae


def test_run_cases_reports_by_suite() -> None:
    cases = {
        "cases": [
            {
                "id": "block-reset",
                "suite": "command_guard",
                "command": ["git", "reset", "--hard"],
                "expected_decision": "BLOCK",
            },
            {
                "id": "needs-approval",
                "suite": "hitl_approval",
                "action": "dangerous",
                "approved": False,
                "expected_required": True,
                "expected_error": True,
            },
            {
                "id": "route-plan-next",
                "suite": "prompt_routing",
                "action": "PLAN_NEXT",
                "expected_route": "plan_next",
            },
            {
                "id": "gate-retry-budget",
                "suite": "pipeline_guard",
                "violation": "retry_budget",
                "attempt": 2,
                "expected_ok": False,
                "expected_violation_contains": "retry budget exceeded",
            },
            {
                "id": "proof-tampered",
                "suite": "proof_bundle",
                "tamper_artifact": True,
                "expected_ok": False,
                "expected_reason_contains": "checksum",
            },
        ]
    }

    report = ae.run_cases(
        cases,
        command_policy={
            "blocked_commands": [{"prefix": ["git", "reset", "--hard"], "reason": "no"}]
        },
        hitl_policy={
            "actions": [
                {
                    "name": "dangerous",
                    "requires_approval": True,
                    "reason": "manual review",
                }
            ]
        },
        prompt_registry={
            "routes": [
                {
                    "name": "plan_next",
                    "actions": ["PLAN_NEXT"],
                    "template": "doc/team_workflow/generate_plan_next_prompt.md",
                }
            ],
            "default_route": "plan_next",
        },
        skills_policy={"rules": []},
    )

    assert report["failed"] == 0
    assert report["by_suite"]["command_guard"] == {"passed": 1, "failed": 0}
    assert report["by_suite"]["hitl_approval"] == {"passed": 1, "failed": 0}
    assert report["by_suite"]["prompt_routing"] == {"passed": 1, "failed": 0}
    assert report["by_suite"]["pipeline_guard"] == {"passed": 1, "failed": 0}
    assert report["by_suite"]["proof_bundle"] == {"passed": 1, "failed": 0}


def test_main_json_uses_default_policies(capsys) -> None:
    rc = ae.main(["--json"])
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert rc == 0
    assert report["failed"] == 0
    assert report["total"] >= 11
    assert report["by_suite"]["pipeline_guard"]["passed"] >= 3
    assert report["by_suite"]["proof_bundle"]["passed"] >= 1
