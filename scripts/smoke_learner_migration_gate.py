#!/usr/bin/env python3
"""
Smoke script: генерирует learner migration history и сразу запускает gate.

Usage:
  python scripts/smoke_learner_migration_gate.py
  python scripts/smoke_learner_migration_gate.py --profile strict
  python scripts/smoke_learner_migration_gate.py --rows 40 --mode healthy
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


def _build_history_rows(*, rows: int, mode: str) -> list[dict[str, Any]]:
    count = max(1, int(rows))
    normalized_mode = str(mode or "healthy").strip().lower()
    if normalized_mode not in {"healthy", "degraded"}:
        raise ValueError(f"Unsupported mode: {mode}")
    out: list[dict[str, Any]] = []
    for i in range(count):
        if normalized_mode == "healthy":
            rehydrated = (i % 20) == 0
        else:
            rehydrated = (i % 2) == 0
        out.append(
            {
                "timestamp": f"2026-04-08T10:{(i % 60):02d}:00+00:00",
                "profile_schema_version": 2,
                "index_context": {"index_version": 10 + (i // 25), "generation_id": f"gen-{10 + (i // 25)}"},
                "state_migration": {"index_changed": True, "history_rehydrated": rehydrated},
                "mastery_vector": {"A": 0.6, "avg": 0.6},
            }
        )
    return out


def generate_learner_migration_smoke_history(
    *,
    rows: int = 20,
    mode: str = "healthy",
) -> dict[str, Any]:
    os.chdir(ROOT)
    from app.learner_model_service import PERSONALIZED_LEARNER_HISTORY_KV_KEY
    from app.user_state import set_kv

    history = _build_history_rows(rows=rows, mode=mode)
    set_kv(PERSONALIZED_LEARNER_HISTORY_KV_KEY, json.dumps(history, ensure_ascii=False))
    return {
        "rows_written": len(history),
        "mode": str(mode or "healthy").strip().lower(),
        "history_key": PERSONALIZED_LEARNER_HISTORY_KV_KEY,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate learner migration smoke history and run gate")
    parser.add_argument("--rows", type=int, default=20, help="How many history rows to write")
    parser.add_argument(
        "--mode",
        type=str,
        choices=("healthy", "degraded"),
        default="healthy",
        help="healthy: low rehydrated_rate, degraded: high rehydrated_rate",
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=("local", "strict"),
        default="local",
        help="Gate threshold profile",
    )
    parser.add_argument("--limit-history", type=int, default=200)
    parser.add_argument("--max-rehydrated-rate", type=float, default=None)
    parser.add_argument("--min-window", type=int, default=None)
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    from scripts.check_learner_migration_gate import resolve_thresholds, run_gate

    thresholds = resolve_thresholds(
        profile=args.profile,
        max_rehydrated_rate=args.max_rehydrated_rate,
        min_window=args.min_window,
    )
    requested_rows = max(1, int(args.rows))
    min_window_required = int(thresholds.get("min_window") or 0)
    effective_rows = max(requested_rows, min_window_required)

    smoke = generate_learner_migration_smoke_history(rows=effective_rows, mode=args.mode)
    gate_report, rc = run_gate(
        profile=args.profile,
        limit_history=args.limit_history,
        max_rehydrated_rate=args.max_rehydrated_rate,
        min_window=args.min_window,
    )
    payload = {
        "smoke": smoke,
        "gate": gate_report,
    }
    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"Learner migration smoke gate ({args.profile}): {verdict}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

