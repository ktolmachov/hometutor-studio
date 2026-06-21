#!/usr/bin/env python3
"""
Smoke runner for tutor regression gate.

Modes:
- healthy: baseline comparison expected to pass
- degraded: baseline comparison expected to fail
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _degrade_baseline(baseline: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(baseline)
    summary = out.get("summary")
    if not isinstance(summary, dict):
        summary = {}
        out["summary"] = summary
    # Делаем baseline заведомо лучше, чтобы compare выдал регрессию по latency/quality.
    summary["avg_tutor_score"] = 0.99
    summary["avg_answer_relevancy"] = 0.99
    summary["avg_context_relevancy"] = 0.99
    summary["avg_faithfulness"] = 0.99
    summary["route_match_rate"] = 0.99
    summary["avg_latency_sec"] = 0.001
    summary["p50_latency_sec"] = 0.001
    summary["p95_latency_sec"] = 0.001
    return out


def generate_tutor_regression_smoke_baseline(
    *,
    baseline_path: str,
    mode: str = "healthy",
    source_baseline_path: str = "eval_data/tutor_regression_baseline.json",
) -> dict[str, Any]:
    os.chdir(ROOT)

    normalized_mode = str(mode or "healthy").strip().lower()
    if normalized_mode not in {"healthy", "degraded"}:
        raise ValueError(f"Unsupported mode: {mode}")

    src = Path(source_baseline_path)
    if not src.is_absolute():
        src = ROOT / src
    if src.exists():
        baseline_payload = json.loads(src.read_text(encoding="utf-8"))
    else:
        baseline_payload = {
            "summary": {
                "avg_tutor_score": 0.6,
                "avg_answer_relevancy": 0.7,
                "avg_context_relevancy": 0.3,
                "avg_faithfulness": 0.8,
                "route_match_rate": 0.3,
                "avg_latency_sec": 5.0,
                "p50_latency_sec": 4.0,
                "p95_latency_sec": 8.0,
            },
            "dataset_version": "smoke_fallback",
            "artifact_version": 1,
        }
    if normalized_mode == "degraded":
        baseline_payload = _degrade_baseline(baseline_payload)

    bp = Path(baseline_path)
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "baseline_path": str(bp),
        "mode": normalized_mode,
        "source_baseline_path": str(src),
    }


def build_smoke_diagnostic_summary(
    *,
    mode: str,
    gate_report: dict[str, Any],
    expected_rc: int,
    actual_rc: int,
    expectation_ok: bool,
    offline: bool,
) -> dict[str, Any]:
    normalized_mode = str(mode or "healthy").strip().lower()
    gate_status = str(gate_report.get("status") or "unknown")
    gate_error_kind = gate_report.get("error_kind")
    if expectation_ok and normalized_mode == "healthy":
        result_label = "healthy_pass"
    elif expectation_ok and normalized_mode == "degraded":
        result_label = "degraded_expected_fail"
    else:
        result_label = "unexpected_outcome"
    triage = gate_report.get("triage") if isinstance(gate_report.get("triage"), dict) else {}
    return {
        "smoke_mode": normalized_mode,
        "offline": offline,
        "expected_rc": expected_rc,
        "actual_rc": actual_rc,
        "expectation_matched": expectation_ok,
        "gate_status": gate_status,
        "gate_error_kind": gate_error_kind,
        "result_label": result_label,
        "recommended_next_action": triage.get("next_action"),
        "recommended_owner_hint": triage.get("owner_hint"),
        "rerun_recommended": triage.get("rerun_recommended"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate tutor regression smoke baseline and run gate")
    parser.add_argument(
        "--mode",
        type=str,
        choices=("healthy", "degraded"),
        default="healthy",
        help="healthy: expected PASS; degraded: expected FAIL",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="tutor_regression.json",
        help="Tutor regression dataset path",
    )
    parser.add_argument(
        "--baseline-path",
        type=str,
        default="logs/tutor_regression_smoke_baseline.json",
        help="Where to write generated smoke baseline",
    )
    parser.add_argument(
        "--source-baseline-path",
        type=str,
        default="eval_data/tutor_regression_baseline.json",
        help="Source baseline file used for deterministic smoke baseline generation",
    )
    parser.add_argument(
        "--offline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use deterministic smoke evaluation without live tutor regression run",
    )
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    from scripts.check_tutor_regression_gate import compute_triage, run_gate

    smoke = generate_tutor_regression_smoke_baseline(
        baseline_path=args.baseline_path,
        mode=args.mode,
        source_baseline_path=args.source_baseline_path,
    )
    if args.offline:
        gate_rc = 0 if args.mode == "healthy" else 2
        st = "pass" if gate_rc == 0 else "regression_fail"
        gate_report = {
            "gate_kind": "tutor_regression",
            "dataset": args.dataset,
            "baseline_path": smoke["baseline_path"],
            "artifact": {"eval_output_path": None},
            "summary": {"smoke_mode": args.mode, "offline": True},
            "baseline_comparison": {"passed": gate_rc == 0},
            "status": st,
            "passed": gate_rc == 0,
            "error_kind": None,
            "error_type": None,
            "error_message": None,
            "triage": compute_triage(status=st, error_kind=None),
        }
    else:
        gate_report, gate_rc = run_gate(dataset=args.dataset, baseline=smoke["baseline_path"])
        if not isinstance(gate_report.get("triage"), dict):
            gate_report = {
                **gate_report,
                "triage": compute_triage(
                    status=str(gate_report.get("status") or "unknown"),
                    error_kind=gate_report.get("error_kind"),
                ),
            }
    expected_rc = 0 if args.mode == "healthy" else 2
    expectation_ok = gate_rc == expected_rc
    rc = 0 if expectation_ok else 2
    diagnostic_summary = build_smoke_diagnostic_summary(
        mode=args.mode,
        gate_report=gate_report,
        expected_rc=expected_rc,
        actual_rc=gate_rc,
        expectation_ok=expectation_ok,
        offline=args.offline,
    )

    payload = {
        "smoke": smoke,
        "gate": gate_report,
        "expectation": {
            "mode": args.mode,
            "expected_rc": expected_rc,
            "actual_rc": gate_rc,
            "matched": expectation_ok,
        },
        "diagnostic_summary": diagnostic_summary,
    }
    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"Tutor regression smoke gate ({args.mode}): {verdict}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
