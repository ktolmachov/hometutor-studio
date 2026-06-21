"""Deterministic adversarial checks for policy and routing helpers."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from command_guard import check as check_command
from hitl_approval import assert_approved
from pipeline_guard_logic import GateContext
from pipeline_guard_logic import evaluate as evaluate_pipeline_guard
from proof_bundle import validate as validate_proof_bundle
from prompt_routing_registry import resolve_route
from skills_router import recommend
from write_set_check import WriteSetResult

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "policies" / "adversarial_eval_cases.yaml"
DEFAULT_COMMAND_POLICY_PATH = ROOT / "policies" / "agent_sandbox_policy.yaml"
DEFAULT_HITL_POLICY_PATH = ROOT / "policies" / "hitl_approval_policy.yaml"
DEFAULT_PROMPT_POLICY_PATH = ROOT / "policies" / "prompts_registry.yaml"
DEFAULT_SKILLS_POLICY_PATH = ROOT / "policies" / "skills_router.yaml"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    suite: str
    passed: bool
    reason: str


def _load_json_doc(path: Path | str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} must contain a mapping")
    return dict(data)


def _eval_command_guard(case: Mapping[str, Any], policy: Mapping[str, Any]) -> CaseResult:
    command = [str(part) for part in case.get("command", [])]
    expected = str(case.get("expected_decision", "")).upper()
    verdict = check_command(command, policy)
    passed = verdict.decision == expected
    return CaseResult(
        case_id=str(case.get("id", "")),
        suite="command_guard",
        passed=passed,
        reason=f"expected={expected} actual={verdict.decision} reason={verdict.reason}",
    )


def _eval_hitl(case: Mapping[str, Any], policy: Mapping[str, Any]) -> CaseResult:
    expected_required = bool(case.get("expected_required", False))
    expected_error = bool(case.get("expected_error", False))
    action = str(case.get("action", ""))
    approved = bool(case.get("approved", False))
    error = False
    required = False
    try:
        verdict = assert_approved(action, approved=approved, policy=policy)
        required = verdict.required
    except PermissionError:
        error = True
        required = True
    passed = required == expected_required and error == expected_error
    return CaseResult(
        case_id=str(case.get("id", "")),
        suite="hitl_approval",
        passed=passed,
        reason=f"expected_required={expected_required} required={required} expected_error={expected_error} error={error}",
    )


def _eval_skills_router(case: Mapping[str, Any], policy: Mapping[str, Any]) -> CaseResult:
    expected = [str(skill) for skill in case.get("expected_skills", [])]
    actual = [
        item.skill
        for item in recommend(
            paths=[str(path) for path in case.get("paths", [])],
            text=str(case.get("text", "")),
            policy=policy,
        )
    ]
    passed = all(skill in actual for skill in expected)
    return CaseResult(
        case_id=str(case.get("id", "")),
        suite="skills_router",
        passed=passed,
        reason=f"expected_contains={expected} actual={actual}",
    )


def _eval_prompt_routing(case: Mapping[str, Any], registry: Mapping[str, Any]) -> CaseResult:
    action = str(case.get("action", ""))
    expected_route = str(case.get("expected_route", ""))
    try:
        route = resolve_route(action, registry)
        actual_route = route.name
        error = ""
    except (KeyError, ValueError) as exc:
        actual_route = ""
        error = str(exc)
    passed = actual_route == expected_route
    return CaseResult(
        case_id=str(case.get("id", "")),
        suite="prompt_routing",
        passed=passed,
        reason=f"expected_route={expected_route} actual_route={actual_route} error={error}",
    )


def _eval_pipeline_guard(case: Mapping[str, Any]) -> CaseResult:
    violation = str(case.get("violation", ""))
    expected_ok = bool(case.get("expected_ok", False))
    expected_contains = str(case.get("expected_violation_contains", ""))
    policy = {
        "gate_mode": str(case.get("gate_mode", "enforcing")),
        "max_retry_attempts": int(case.get("max_retry_attempts", 1)),
        "result_freshness_seconds": int(case.get("result_freshness_seconds", 7200)),
    }

    with tempfile.TemporaryDirectory(prefix="hometutor_adversarial_guard_") as tmp:
        root = Path(tmp)
        task = root / "doc" / "current_task.md"
        task.parent.mkdir(parents=True, exist_ok=True)
        task.write_text("## Write-Set\n- app/a.py\n", encoding="utf-8")
        ctx = GateContext(
            package_id=str(case.get("package_id", "epoch-adversarial")),
            root=root,
            current_task_path=task,
            changed_paths=["app/a.py"],
        )
        write_set_result = WriteSetResult(("app/a.py",), ("app/a.py",), (), False)

        if violation == "retry_budget":
            ctx = GateContext(
                package_id=ctx.package_id,
                root=root,
                current_task_path=task,
                changed_paths=["app/a.py"],
                attempt=int(case.get("attempt", 2)),
            )
        elif violation == "write_set_drift":
            write_set_result = WriteSetResult(
                ("app/a.py",),
                ("app/b.py",),
                ("app/b.py",),
                False,
            )
        elif violation == "stale_result":
            result = root / "logs" / "autonomous_runs" / "run-1" / "result.json"
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_text(json.dumps({"exit_code": 0}), encoding="utf-8")
            old = time.time() - int(case.get("stale_age_seconds", 10))
            result_freshness = int(case.get("result_freshness_seconds", 1))
            policy["result_freshness_seconds"] = result_freshness
            time.sleep(0.01)
            os.utime(result, (old, old))
            ctx = GateContext(
                package_id=ctx.package_id,
                root=root,
                current_task_path=task,
                result_path=result,
                changed_paths=["app/a.py"],
            )
        else:
            return CaseResult(
                case_id=str(case.get("id", "")),
                suite="pipeline_guard",
                passed=False,
                reason=f"unknown pipeline_guard violation: {violation}",
            )

        verdict = evaluate_pipeline_guard(
            ctx,
            policy=policy,
            write_set_result=write_set_result,
            log_event=False,
        )

    passed = verdict.ok == expected_ok and (
        not expected_contains
        or any(expected_contains in item for item in verdict.violations)
    )
    return CaseResult(
        case_id=str(case.get("id", "")),
        suite="pipeline_guard",
        passed=passed,
        reason=f"expected_ok={expected_ok} actual_ok={verdict.ok} violations={list(verdict.violations)}",
    )


def _eval_proof_bundle(case: Mapping[str, Any]) -> CaseResult:
    expected_ok = bool(case.get("expected_ok", False))
    expected_reason_contains = str(case.get("expected_reason_contains", ""))

    import pipeline_events as pe
    import proof_bundle as pb

    old_pb_root = pb.ROOT
    old_pb_runs_root = pb.AUTONOMOUS_RUNS_ROOT
    old_pe_runs_root = pe.AUTONOMOUS_RUNS_ROOT
    old_pe_current_dir = pe.CURRENT_DIR
    old_pe_orphan_dir = pe.ORPHAN_DIR
    try:
        with tempfile.TemporaryDirectory(prefix="hometutor_adversarial_proof_") as tmp:
            root = Path(tmp)
            runs_root = root / "logs" / "autonomous_runs"
            pb.ROOT = root
            pb.AUTONOMOUS_RUNS_ROOT = runs_root
            pe.AUTONOMOUS_RUNS_ROOT = runs_root
            pe.CURRENT_DIR = runs_root / "current"
            pe.ORPHAN_DIR = runs_root / "_orphan"

            package_id = str(case.get("package_id", "epoch-adversarial"))
            run_id = str(case.get("run_id", "run-proof"))
            exec_contract = (
                root
                / "archive"
                / "team_artifacts"
                / package_id
                / "execution_contract.md"
            )
            exec_contract.parent.mkdir(parents=True, exist_ok=True)
            exec_contract.write_text("proof\n", encoding="utf-8")
            pb.build(run_id, package_id)
            if case.get("tamper_artifact", False):
                exec_contract.write_text("tampered\n", encoding="utf-8")
            actual_ok, reason = validate_proof_bundle(package_id, run_id=run_id)
    finally:
        pb.ROOT = old_pb_root
        pb.AUTONOMOUS_RUNS_ROOT = old_pb_runs_root
        pe.AUTONOMOUS_RUNS_ROOT = old_pe_runs_root
        pe.CURRENT_DIR = old_pe_current_dir
        pe.ORPHAN_DIR = old_pe_orphan_dir

    passed = actual_ok == expected_ok and (
        not expected_reason_contains or expected_reason_contains in reason
    )
    return CaseResult(
        case_id=str(case.get("id", "")),
        suite="proof_bundle",
        passed=passed,
        reason=f"expected_ok={expected_ok} actual_ok={actual_ok} reason={reason}",
    )


def run_cases(
    cases_doc: Mapping[str, Any],
    *,
    command_policy: Mapping[str, Any],
    hitl_policy: Mapping[str, Any],
    prompt_registry: Mapping[str, Any],
    skills_policy: Mapping[str, Any],
) -> dict[str, Any]:
    results: list[CaseResult] = []
    for case in cases_doc.get("cases", []) or []:
        if not isinstance(case, Mapping):
            continue
        suite = str(case.get("suite", ""))
        if suite == "command_guard":
            results.append(_eval_command_guard(case, command_policy))
        elif suite == "hitl_approval":
            results.append(_eval_hitl(case, hitl_policy))
        elif suite == "skills_router":
            results.append(_eval_skills_router(case, skills_policy))
        elif suite == "prompt_routing":
            results.append(_eval_prompt_routing(case, prompt_registry))
        elif suite == "pipeline_guard":
            results.append(_eval_pipeline_guard(case))
        elif suite == "proof_bundle":
            results.append(_eval_proof_bundle(case))
        else:
            results.append(
                CaseResult(
                    case_id=str(case.get("id", "")),
                    suite=suite,
                    passed=False,
                    reason=f"unknown suite: {suite}",
                )
            )

    passed = sum(1 for result in results if result.passed)
    by_suite: dict[str, dict[str, int]] = {}
    for result in results:
        stats = by_suite.setdefault(result.suite, {"passed": 0, "failed": 0})
        stats["passed" if result.passed else "failed"] += 1
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "by_suite": by_suite,
        "results": [result.__dict__ for result in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic adversarial policy evals.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--json", action="store_true", help="Print machine-readable report.")
    args = parser.parse_args(argv)

    report = run_cases(
        _load_json_doc(args.cases),
        command_policy=_load_json_doc(DEFAULT_COMMAND_POLICY_PATH),
        hitl_policy=_load_json_doc(DEFAULT_HITL_POLICY_PATH),
        prompt_registry=_load_json_doc(DEFAULT_PROMPT_POLICY_PATH),
        skills_policy=_load_json_doc(DEFAULT_SKILLS_POLICY_PATH),
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"adversarial eval: {report['passed']}/{report['total']} passed")
        for result in report["results"]:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"- {status} {result['suite']}::{result['case_id']} - {result['reason']}")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
