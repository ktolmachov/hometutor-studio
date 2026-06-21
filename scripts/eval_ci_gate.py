#!/usr/bin/env python3
"""CI gate for the answer-quality eval report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS_EVAL_DIR = ROOT / "tests" / "eval"
DEFAULT_RUNNER = TESTS_EVAL_DIR / "run_eval.py"
DEFAULT_THRESHOLDS = TESTS_EVAL_DIR / "thresholds.json"
DEFAULT_BASELINE = TESTS_EVAL_DIR / "results" / "baseline.json"
SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INFRA_ERROR = 2

SCRIPTS_DIR = ROOT / "scripts"
for candidate in (ROOT, SCRIPTS_DIR):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from script_stdio_utf8 import configure_stdio_utf8


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _metric_component(metric: str) -> str:
    if metric == "tutor_coherence":
        return "tutor_coherence"
    if metric == "latency_sec":
        return "latency"
    if metric == "source_precision_at_3":
        return "retrieval"
    if metric == "trivial_in_corpus_avg_precision":
        return "retrieval"
    return "generation"


def _run_eval_command(
    *,
    runner_path: Path,
    dataset_path: Path | None,
    thresholds_path: Path,
    force_mock: bool,
    eval_corpus_path: Path | None,
) -> tuple[int, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="answer_quality_gate_") as tmp_dir:
        report_path = Path(tmp_dir) / "eval_report.json"
        cmd = [
            sys.executable,
            str(runner_path),
            "--thresholds",
            str(thresholds_path),
            "--report-json",
            str(report_path),
            "--quiet",
        ]
        if dataset_path is not None:
            cmd.extend(["--dataset", str(dataset_path)])
        if force_mock:
            cmd.append("--mock")
        if eval_corpus_path is not None and eval_corpus_path.exists():
            cmd.extend(["--eval-corpus", str(eval_corpus_path)])
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        payload: dict[str, Any]
        if report_path.exists():
            payload = _read_json(report_path)
        else:
            try:
                payload = json.loads(completed.stdout or "")
            except json.JSONDecodeError:
                payload = {}
        if completed.returncode not in (0, 2):
            payload.setdefault("runner_stdout", completed.stdout[-1000:])
            payload.setdefault("runner_stderr", completed.stderr[-1000:])
        return completed.returncode, payload


def _threshold_failures(report: dict[str, Any], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    threshold_values = thresholds.get("thresholds") if isinstance(thresholds.get("thresholds"), dict) else thresholds
    failures: list[dict[str, Any]] = []
    checks = (
        ("source_precision_at_3", "retrieval", "min"),
        ("answer_groundedness", "generation", "min"),
        ("tutor_coherence", "tutor_coherence", "min"),
        ("latency_p95_sec", "latency", "max"),
        ("trivial_in_corpus_avg_precision", "retrieval", "min"),
    )
    for metric, component, mode in checks:
        expected = threshold_values.get(metric)
        observed = summary.get(metric)
        if expected is None or observed is None:
            continue
        observed_value = float(observed)
        expected_value = float(expected)
        failed = observed_value < expected_value if mode == "min" else observed_value > expected_value
        if failed:
            relation = "<" if mode == "min" else ">"
            failures.append(
                {
                    "scope": "summary",
                    "case_id": None,
                    "component": component,
                    "metric": metric,
                    "observed": observed_value,
                    "baseline": None,
                    "threshold": expected_value,
                    "detail": f"{metric} {observed_value:.3f} {relation} threshold {expected_value:.3f}",
                }
            )
    return failures


def _case_regressions(
    report: dict[str, Any],
    baseline: dict[str, Any] | None,
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    if not baseline:
        return []
    if not report.get("comparable_to_baseline") or not baseline.get("comparable_to_baseline"):
        return []
    tolerances = thresholds.get("baseline_tolerance") if isinstance(thresholds.get("baseline_tolerance"), dict) else {}
    source_drop = float(tolerances.get("source_precision_at_3_drop", 0.0))
    grounded_drop = float(tolerances.get("answer_groundedness_drop", 0.25))
    tutor_drop = float(tolerances.get("tutor_coherence_drop", 0.25))
    latency_increase = float(tolerances.get("per_case_latency_sec_increase", 1.0))

    baseline_cases = {
        str(item.get("id")): item
        for item in (baseline.get("cases") or [])
        if isinstance(item, dict) and item.get("id") is not None
    }
    regressions: list[dict[str, Any]] = []
    for case in report.get("cases") or []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("id") or "")
        baseline_case = baseline_cases.get(case_id)
        if not baseline_case:
            continue

        current_precision = case.get("source_precision_at_3")
        baseline_precision = baseline_case.get("source_precision_at_3")
        if current_precision is not None and baseline_precision is not None:
            if float(current_precision) < float(baseline_precision) - source_drop:
                regressions.append(
                    {
                        "scope": "case",
                        "case_id": case_id,
                        "question": case.get("question"),
                        "component": _metric_component("source_precision_at_3"),
                        "metric": "source_precision_at_3",
                        "observed": float(current_precision),
                        "baseline": float(baseline_precision),
                        "threshold": source_drop,
                        "detail": f"retrieval regressed on {case_id}",
                    }
                )

        current_grounded = case.get("answer_groundedness")
        baseline_grounded = baseline_case.get("answer_groundedness")
        if current_grounded is not None and baseline_grounded is not None:
            if float(current_grounded) < float(baseline_grounded) - grounded_drop:
                regressions.append(
                    {
                        "scope": "case",
                        "case_id": case_id,
                        "question": case.get("question"),
                        "component": _metric_component("answer_groundedness"),
                        "metric": "answer_groundedness",
                        "observed": float(current_grounded),
                        "baseline": float(baseline_grounded),
                        "threshold": grounded_drop,
                        "detail": f"generation regressed on {case_id}",
                    }
                )

        current_tutor = case.get("tutor_coherence")
        baseline_tutor = baseline_case.get("tutor_coherence")
        if current_tutor is not None and baseline_tutor is not None:
            if float(current_tutor) < float(baseline_tutor) - tutor_drop:
                regressions.append(
                    {
                        "scope": "case",
                        "case_id": case_id,
                        "question": case.get("question"),
                        "component": _metric_component("tutor_coherence"),
                        "metric": "tutor_coherence",
                        "observed": float(current_tutor),
                        "baseline": float(baseline_tutor),
                        "threshold": tutor_drop,
                        "detail": f"tutor coherence regressed on {case_id}",
                    }
                )

        current_latency = case.get("latency_sec")
        baseline_latency = baseline_case.get("latency_sec")
        if current_latency is not None and baseline_latency is not None:
            if float(current_latency) > float(baseline_latency) + latency_increase:
                regressions.append(
                    {
                        "scope": "case",
                        "case_id": case_id,
                        "question": case.get("question"),
                        "component": _metric_component("latency_sec"),
                        "metric": "latency_sec",
                        "observed": float(current_latency),
                        "baseline": float(baseline_latency),
                        "threshold": latency_increase,
                        "detail": f"latency regressed on {case_id}",
                    }
                )
    return regressions


def _summary_regressions(
    report: dict[str, Any],
    baseline: dict[str, Any] | None,
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    if not baseline:
        return []
    if not report.get("comparable_to_baseline") or not baseline.get("comparable_to_baseline"):
        return []

    report_summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    baseline_summary = baseline.get("summary") if isinstance(baseline.get("summary"), dict) else {}
    tolerances = thresholds.get("baseline_tolerance") if isinstance(thresholds.get("baseline_tolerance"), dict) else {}
    source_drop = float(tolerances.get("source_precision_at_3_drop", 0.0))
    grounded_drop = float(tolerances.get("answer_groundedness_drop", 0.25))
    tutor_drop = float(tolerances.get("tutor_coherence_drop", 0.25))
    latency_increase = float(tolerances.get("latency_p95_sec_increase", 0.0))

    checks = (
        ("source_precision_at_3", "retrieval", "min", source_drop),
        ("answer_groundedness", "generation", "min", grounded_drop),
        ("tutor_coherence", "tutor_coherence", "min", tutor_drop),
        ("latency_p95_sec", "latency", "max", latency_increase),
    )

    regressions: list[dict[str, Any]] = []
    for metric, component, mode, tolerance in checks:
        current = report_summary.get(metric)
        baseline_value = baseline_summary.get(metric)
        if current is None or baseline_value is None:
            continue
        current_value = float(current)
        baseline_float = float(baseline_value)
        failed = (
            current_value < baseline_float - tolerance
            if mode == "min"
            else current_value > baseline_float + tolerance
        )
        if failed:
            relation = "<" if mode == "min" else ">"
            regressions.append(
                {
                    "scope": "summary",
                    "case_id": None,
                    "component": component,
                    "metric": metric,
                    "observed": current_value,
                    "baseline": baseline_float,
                    "threshold": tolerance,
                    "detail": f"{metric} {current_value:.3f} {relation} baseline {baseline_float:.3f} with tolerance {tolerance:.3f}",
                }
            )
    return regressions


def evaluate_gate(
    *,
    report: dict[str, Any],
    baseline: dict[str, Any] | None,
    thresholds: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    threshold_failures = _threshold_failures(report, thresholds)
    summary_regressions = _summary_regressions(report, baseline, thresholds)
    regression_failures = _case_regressions(report, baseline, thresholds)
    comparable = bool(report.get("comparable_to_baseline")) and bool(
        baseline and baseline.get("comparable_to_baseline")
    )

    if report.get("mode") == "mock" or not comparable:
        status = "warn" if not threshold_failures else "fail"
        payload = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "status": status,
            "comparable_to_baseline": False,
            "threshold_failures": threshold_failures,
            "summary_regression_failures": [],
            "regression_failures": [],
            "note": (
                "Eval report is mock/incomparable; baseline delta checks skipped."
                if report.get("mode") == "mock" or baseline
                else "Baseline missing; baseline delta checks skipped."
            ),
            "summary": report.get("summary"),
            "eval_report": report,
        }
        return payload, EXIT_FAILED if threshold_failures else EXIT_OK

    failures = [*threshold_failures, *summary_regressions, *regression_failures]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "status": "fail" if failures else "pass",
        "comparable_to_baseline": True,
        "threshold_failures": threshold_failures,
        "summary_regression_failures": summary_regressions,
        "regression_failures": regression_failures,
        "summary": report.get("summary"),
        "eval_report": report,
    }
    return payload, EXIT_FAILED if failures else EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description="Run answer-quality eval and compare it with baseline.")
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--mock", action="store_true", help="Force mock mode for the eval runner.")
    parser.add_argument("--eval-corpus", type=Path, default=TESTS_EVAL_DIR / "corpus", help="Path to eval corpus directory for synthetic eval.")
    args = parser.parse_args()
    configure_stdio_utf8()

    try:
        runner_rc, report = _run_eval_command(
            runner_path=args.runner,
            dataset_path=args.dataset,
            thresholds_path=args.thresholds,
            force_mock=args.mock,
            eval_corpus_path=args.eval_corpus,
        )
        if runner_rc not in (0, 2):
            output = {
                "schema_version": SCHEMA_VERSION,
                "generated_at": _now_iso(),
                "status": "error",
                "error": "eval runner failed to produce a comparable report",
                "eval_report": report,
            }
            rc = EXIT_INFRA_ERROR
        else:
            baseline = _read_json(args.baseline) if args.baseline.exists() else None
            thresholds = _read_json(args.thresholds)
            output, rc = evaluate_gate(report=report, baseline=baseline, thresholds=thresholds)
    except Exception as exc:  # noqa: BLE001 - gate must serialize heterogeneous CI/runtime failures.
        output = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "status": "error",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        rc = EXIT_INFRA_ERROR

    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(rendered, encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
