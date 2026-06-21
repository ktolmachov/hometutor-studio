#!/usr/bin/env python3
"""CLI health report for learner profile, lineage, mastery and spaced repetition."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_report(*, user_id: str = "local", session_id: str | None = None, limit_history: int = 200) -> dict:
    os.chdir(ROOT)
    from app.learner_model_service import get_learner_state_health

    return get_learner_state_health(user_id=user_id, session_id=session_id, limit_history=limit_history)


def main() -> int:
    parser = argparse.ArgumentParser(description="Learner state health report")
    parser.add_argument("--user-id", type=str, default="local")
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--limit-history", type=int, default=200)
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    report = build_report(
        user_id=args.user_id,
        session_id=args.session_id,
        limit_history=args.limit_history,
    )
    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Learner state health: {report.get('status')}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report.get("status") == "stale" else 0


if __name__ == "__main__":
    raise SystemExit(main())
