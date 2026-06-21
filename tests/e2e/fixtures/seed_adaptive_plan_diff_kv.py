"""Write adaptive_daily_plan_json into app_kv for offline Playwright (US-6.2 / plan diff)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone

KEY = "adaptive_daily_plan_json"


def build_plan_payload() -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "date": today,
        "recommended_session_length_min": 25,
        "total_xp_goal": 40,
        "blocks": [
            {
                "type": "gap",
                "concept": "E2EAlphaDiff",
                "description": "e2e",
                "duration_min": 10,
                "xp_base": 5,
            },
            {
                "type": "review",
                "concept": "E2EGammaDiff",
                "description": "e2e",
                "duration_min": 5,
                "xp_base": 5,
            },
        ],
        "motivation_message": "E2E plan diff seed.",
        "plan_concepts_delta": {
            "added": ["E2EAlphaDiff"],
            "removed": ["E2EBetaDiff"],
            "baseline_date": "2020-01-01",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("db_path", help="Path to user_state SQLite (.e2e/state-main.db in smoke)")
    args = parser.parse_args()
    plan = build_plan_payload()
    raw = json.dumps(plan, ensure_ascii=False)
    conn = sqlite3.connect(args.db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_kv (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO app_kv(key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """,
            (KEY, raw),
        )
        conn.commit()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
