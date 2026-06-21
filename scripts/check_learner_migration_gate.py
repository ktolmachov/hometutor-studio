#!/usr/bin/env python3
"""
Ready-to-run gate for learner migration health (E5.5).

Usage:
  python scripts/check_learner_migration_gate.py
  python scripts/check_learner_migration_gate.py --profile strict
  python scripts/check_learner_migration_gate.py --max-rehydrated-rate 0.15 --min-window 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOCAL_GATE_DEFAULTS = {
    "max_rehydrated_rate": 0.35,
    "min_window": 10,
}

STRICT_GATE_DEFAULTS = {
    "max_rehydrated_rate": 0.2,
    "min_window": 30,
}


def resolve_thresholds(
    *,
    profile: str,
    max_rehydrated_rate: float | None = None,
    min_window: int | None = None,
) -> dict[str, Any]:
    base = STRICT_GATE_DEFAULTS if profile == "strict" else LOCAL_GATE_DEFAULTS
    out = dict(base)
    if max_rehydrated_rate is not None:
        out["max_rehydrated_rate"] = float(max_rehydrated_rate)
    if min_window is not None:
        out["min_window"] = int(min_window)
    return out


def evaluate_gate(metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    passed = True
    window = int(metrics.get("window_size") or 0)
    rr = metrics.get("rehydrated_rate")
    min_window = int(thresholds["min_window"])
    max_rr = float(thresholds["max_rehydrated_rate"])

    ok_window = window >= min_window
    checks.append(
        {
            "metric": "window_size",
            "observed": window,
            "operator": ">=",
            "threshold": min_window,
            "passed": ok_window,
        }
    )
    if not ok_window:
        passed = False

    if rr is None:
        ok_rr = False
        observed_rr = None
    else:
        observed_rr = float(rr)
        ok_rr = observed_rr <= max_rr
    checks.append(
        {
            "metric": "rehydrated_rate",
            "observed": observed_rr,
            "operator": "<=",
            "threshold": max_rr,
            "passed": ok_rr,
        }
    )
    if not ok_rr:
        passed = False

    return {"passed": passed, "checks": checks}


def run_gate(
    *,
    profile: str = "local",
    limit_history: int = 200,
    max_rehydrated_rate: float | None = None,
    min_window: int | None = None,
) -> tuple[dict[str, Any], int]:
    os.chdir(ROOT)
    from app.learner_model_service import get_learner_profile_migration_metrics

    thresholds = resolve_thresholds(
        profile=profile,
        max_rehydrated_rate=max_rehydrated_rate,
        min_window=min_window,
    )
    metrics = get_learner_profile_migration_metrics(limit=limit_history)
    gate = evaluate_gate(metrics, thresholds)
    report = {
        "source": "learner_profile_history",
        "history_limit": limit_history,
        "gate_profile": profile,
        "gate_thresholds": thresholds,
        "learner_profile_migration": metrics,
        "quality_gate": gate,
    }
    return report, (0 if gate.get("passed") else 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ready-to-use learner migration quality gate")
    parser.add_argument(
        "--profile",
        type=str,
        choices=("local", "strict"),
        default="local",
        help="Threshold preset",
    )
    parser.add_argument("--limit-history", type=int, default=200, help="History window")
    parser.add_argument("--max-rehydrated-rate", type=float, default=None, help="Override max rehydrated_rate")
    parser.add_argument("--min-window", type=int, default=None, help="Override minimum history window size")
    parser.add_argument("--json-out", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    report, rc = run_gate(
        profile=args.profile,
        limit_history=args.limit_history,
        max_rehydrated_rate=args.max_rehydrated_rate,
        min_window=args.min_window,
    )
    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"Learner migration gate ({report['gate_profile']}): {verdict}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

