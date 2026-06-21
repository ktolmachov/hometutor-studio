#!/usr/bin/env python3
"""
Ready-to-run gate for tutor regression contour.

Usage:
  python scripts/check_tutor_regression_gate.py
  python scripts/check_tutor_regression_gate.py --baseline eval_data/tutor_regression_baseline.json
  python scripts/check_tutor_regression_gate.py --dataset tutor_regression.json --json-out
"""

from __future__ import annotations

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_DATASET = "tutor_regression.json"
EXIT_OK = 0
EXIT_REGRESSION = 2
EXIT_INFRA_ERROR = 3
GATE_SCHEMA_VERSION = 2


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_triage(*, status: str, error_kind: str | None) -> dict[str, Any]:
    """
    Machine-readable routing hints for operators/CI (E7.3).
    Stable string values for `next_action` and `owner_hint`.
    """
    st = str(status or "").strip().lower()
    ek = str(error_kind).strip().lower() if error_kind else None

    if st == "pass":
        return {
            "next_action": "noop",
            "owner_hint": "none",
            "rerun_recommended": False,
        }
    if st == "regression_fail":
        return {
            "next_action": "fix_baseline_or_tutor_quality",
            "owner_hint": "tutor_contour_owner",
            "rerun_recommended": False,
        }
    if st == "infra_fail":
        if ek == "dependency_missing":
            return {
                "next_action": "install_missing_dependencies",
                "owner_hint": "repo_ci_owner",
                "rerun_recommended": False,
            }
        if ek == "provider_error":
            return {
                "next_action": "check_provider_keys_quota_policy",
                "owner_hint": "platform_infra",
                "rerun_recommended": True,
            }
        if ek == "infra_transient":
            return {
                "next_action": "retry_ci_job",
                "owner_hint": "ci_operator",
                "rerun_recommended": True,
            }
        return {
            "next_action": "investigate_gate_runtime",
            "owner_hint": "tutor_contour_owner",
            "rerun_recommended": False,
        }
    return {
        "next_action": "unknown",
        "owner_hint": "none",
        "rerun_recommended": False,
    }


def _build_report(
    *,
    dataset: str,
    baseline_path: str | None,
    artifact_path: str | None,
    status: str,
    passed: bool,
    exit_code: int,
    baseline_comparison: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    error_kind: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    triage = compute_triage(status=status, error_kind=error_kind)
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "generated_at_utc": _now_utc_iso(),
        "gate_kind": "tutor_regression",
        "dataset": dataset,
        "baseline_path": baseline_path,
        "status": status,
        "passed": passed,
        "exit_code": exit_code,
        "artifact": {
            "eval_output_path": artifact_path,
        },
        "summary": summary,
        "baseline_comparison": baseline_comparison,
        "error_kind": error_kind,
        "error_type": error_type,
        "error_message": error_message,
        "triage": triage,
    }


def run_gate(
    *,
    dataset: str = DEFAULT_DATASET,
    baseline: str | None = None,
) -> tuple[dict[str, Any], int]:
    os.chdir(ROOT)
    baseline_env = os.environ.get("EVAL_TUTOR_BASELINE_JSON")
    baseline_path = baseline if baseline is not None else baseline_env
    try:
        from app.eval_service import run_tutor_regression

        out_path, output = run_tutor_regression(
            dataset_path=dataset,
            baseline_path=baseline_path,
        )
        comp = output.get("baseline_comparison")
        passed = bool(comp.get("passed")) if isinstance(comp, dict) else True
        rc = EXIT_OK if passed else EXIT_REGRESSION
        report = _build_report(
            dataset=dataset,
            baseline_path=baseline_path,
            artifact_path=str(out_path),
            status="pass" if passed else "regression_fail",
            passed=passed,
            exit_code=rc,
            baseline_comparison=comp if isinstance(comp, dict) else None,
            summary=output.get("summary") if isinstance(output.get("summary"), dict) else None,
        )
        return report, rc
    except Exception as exc:  # pragma: no cover - covered via tests with monkeypatch
        msg = str(exc)
        low = msg.lower()
        if isinstance(exc, ModuleNotFoundError):
            error_kind = "dependency_missing"
        elif any(k in low for k in ("403", "provider", "blocked", "content policy", "no embedding data")):
            error_kind = "provider_error"
        elif any(k in low for k in ("timeout", "timed out", "connection", "network")):
            error_kind = "infra_transient"
        else:
            error_kind = "runtime_error"
        rc = EXIT_INFRA_ERROR
        report = _build_report(
            dataset=dataset,
            baseline_path=baseline_path,
            artifact_path=None,
            status="infra_fail",
            passed=False,
            exit_code=rc,
            error_kind=error_kind,
            error_type=type(exc).__name__,
            error_message=msg,
        )
        return report, rc


def _resolve_baseline_arg(raw: str | None) -> tuple[str | None, bool]:
    if raw is None:
        return None, False
    norm = str(raw).strip()
    if not norm:
        return None, False
    if norm.lower() in {"none", "off", "disabled"}:
        return None, True
    return norm, False


def main() -> int:
    parser = argparse.ArgumentParser(description="Ready-to-use tutor regression gate")
    parser.add_argument(
        "--dataset",
        type=str,
        default=DEFAULT_DATASET,
        help="Tutor regression dataset path (eval_data-relative or absolute)",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Baseline JSON path (overrides EVAL_TUTOR_BASELINE_JSON); use 'none' to disable",
    )
    parser.add_argument("--json-out", action="store_true", help="Output JSON only")
    parser.add_argument(
        "--report-json",
        type=str,
        default=None,
        help="Optional path to persist full gate report JSON",
    )
    args = parser.parse_args()

    baseline, baseline_disabled = _resolve_baseline_arg(args.baseline)
    if baseline_disabled:
        os.environ.pop("EVAL_TUTOR_BASELINE_JSON", None)
    report, rc = run_gate(dataset=args.dataset, baseline=baseline)
    if args.report_json:
        rp = Path(args.report_json)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return rc

    if report.get("summary") is not None:
        print(json.dumps(report.get("summary"), ensure_ascii=False, indent=2))
    comp = report.get("baseline_comparison")
    if isinstance(comp, dict) and comp.get("passed"):
        print("Baseline comparison: OK")
        return rc
    if isinstance(comp, dict) and not comp.get("passed", True):
        print("REGRESSION GATE FAILED:", comp.get("regressions"), file=sys.stderr)
        return rc
    if report.get("status") == "infra_fail":
        print(
            f"TUTOR GATE INFRA FAIL [{report.get('error_kind')}]: {report.get('error_type')}: {report.get('error_message')}",
            file=sys.stderr,
        )
        return rc
    print("No baseline configured; summary only (use --baseline or EVAL_TUTOR_BASELINE_JSON for gating).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
