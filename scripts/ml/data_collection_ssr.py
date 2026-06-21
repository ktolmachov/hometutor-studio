"""Collect SSR forgetting-curve training data from local user_state.db.

The contract requires 1000+ real samples before serving ML by default. When the
local DB has fewer examples, this script writes a deterministic SM-2 synthetic
bootstrap so the offline pipeline can still be evaluated without enabling ML in
production.
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timezone
from typing import Any

from ssr_forgetting_curve_common import (
    CONTRACT_CASES_PATH,
    MIN_REAL_SAMPLES,
    SYNTHETIC_BOOTSTRAP_MIN,
    TEST_PATH,
    TRAIN_PATH,
    load_contract_cases,
    split_rows,
    write_manifest,
    write_rows,
)


def _float_or(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _hours_since(value: Any, *, now: datetime) -> float:
    if not value:
        return 24.0 * 30.0
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 24.0 * 30.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 3600.0)


def _label_from_row(row: dict[str, Any]) -> tuple[str, int]:
    repetitions = int(row.get("repetitions") or 0)
    interval_days = int(row.get("interval_days") or 0)
    easiness = _float_or(row.get("easiness"), 2.5)
    if repetitions <= 0 or interval_days <= 0:
        return "cards_due", 1
    if interval_days <= 2:
        return "sm2_due", 1
    if easiness < 2.0:
        return "mastery_stale", 0
    return "safe_default", 1


def collect_real_rows() -> list[dict[str, Any]]:
    from app.user_state import _with_db

    now = datetime.now(timezone.utc)

    def _read(conn) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT
                id,
                easiness,
                interval_days,
                repetitions,
                next_review,
                last_review,
                updated_at
            FROM flashcards
            ORDER BY updated_at DESC
            """
        ).fetchall()
        quiz_rows = conn.execute("SELECT score FROM quiz_results ORDER BY timestamp DESC LIMIT 3").fetchall()
        quiz_avg = sum(float(r["score"]) for r in quiz_rows) / max(1, len(quiz_rows)) if quiz_rows else 0.7
        due_count = conn.execute(
            "SELECT COUNT(*) AS n FROM flashcards WHERE next_review IS NULL OR next_review <= datetime('now')"
        ).fetchone()["n"]
        sm2_due = conn.execute(
            "SELECT COUNT(*) AS n FROM spaced_repetition WHERE next_review IS NULL OR next_review <= datetime('now')"
        ).fetchone()["n"]
        out: list[dict[str, Any]] = []
        for row in rows:
            label, retention = _label_from_row(dict(row))
            hours = _hours_since(row["last_review"], now=now)
            out.append(
                {
                    "time_since_last_review_hours": round(hours, 3),
                    "quiz_score_last_3_avg": round(quiz_avg, 3),
                    "concept_difficulty": round(max(0.0, min(1.0, (2.5 - _float_or(row["easiness"], 2.5)) / 1.3)), 3),
                    "session_duration_avg_minutes": 18.0,
                    "time_of_day_hour": now.hour,
                    "day_of_week": now.weekday(),
                    "cards_due_count": int(due_count),
                    "sm2_due_count": int(sm2_due),
                    "quiz_failed_recent": quiz_avg < 0.55,
                    "session_fatigue": 0.25,
                    "mastery_gap_score": round(1.0 - quiz_avg, 3),
                    "adaptive_plan_backlog_signals": 0.0,
                    "tutor_stub_active": False,
                    "prior_rule_top_hint_kind": label,
                    "ground_truth_best_hint_kind": label,
                    "retention_probability_label": retention,
                    "sample_source": "user_state_db",
                    "source_id": f"flashcard:{row['id']}",
                }
            )
        return out

    return _with_db(_read)


def synthetic_bootstrap_rows(*, count: int, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    hints = ["cards_due", "sm2_due", "quiz_failed", "mastery_stale", "adaptive_plan", "answer_ready", "tutor_resume", "safe_default"]
    for i in range(count):
        hint = hints[i % len(hints)]
        quiz_score = rng.uniform(0.25, 0.95)
        cards_due = rng.randint(0, 28)
        sm2_due = rng.randint(0, 20)
        quiz_failed = hint == "quiz_failed" or quiz_score < 0.45
        mastery_gap = rng.uniform(0.0, 1.0)
        if hint == "cards_due":
            cards_due = max(cards_due, 4)
        if hint == "sm2_due":
            sm2_due = max(sm2_due, 3)
        rows.append(
            {
                "time_since_last_review_hours": round(rng.uniform(1.0, 24.0 * 21.0), 3),
                "quiz_score_last_3_avg": round(quiz_score, 3),
                "concept_difficulty": round(rng.uniform(0.05, 0.95), 3),
                "session_duration_avg_minutes": round(rng.uniform(5.0, 55.0), 3),
                "time_of_day_hour": rng.randint(6, 23),
                "day_of_week": rng.randint(0, 6),
                "cards_due_count": cards_due,
                "sm2_due_count": sm2_due,
                "quiz_failed_recent": quiz_failed,
                "session_fatigue": round(rng.uniform(0.0, 1.0), 3),
                "mastery_gap_score": round(mastery_gap, 3),
                "adaptive_plan_backlog_signals": rng.randint(0, 5),
                "tutor_stub_active": hint == "tutor_resume",
                "prior_rule_top_hint_kind": hint,
                "ground_truth_best_hint_kind": hint,
                "retention_probability_label": 1 if hint in {"cards_due", "sm2_due", "adaptive_plan"} else int(quiz_score >= 0.5),
                "sample_source": "synthetic_sm2_bootstrap",
                "source_id": f"synthetic:{i:04d}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-count", type=int, default=SYNTHETIC_BOOTSTRAP_MIN)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    real_rows = collect_real_rows()
    synthetic_count = 0 if len(real_rows) >= MIN_REAL_SAMPLES else max(args.synthetic_count, SYNTHETIC_BOOTSTRAP_MIN)
    rows = real_rows + synthetic_bootstrap_rows(count=synthetic_count, seed=args.seed) + load_contract_cases()
    train_rows, test_rows = split_rows(rows, seed=args.seed, test_ratio=0.2)
    write_rows(TRAIN_PATH, train_rows)
    write_rows(TEST_PATH, test_rows)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "real_samples": len(real_rows),
        "synthetic_samples": synthetic_count,
        "contract_cases": str(CONTRACT_CASES_PATH.relative_to(CONTRACT_CASES_PATH.parents[2])).replace("\\", "/"),
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "cold_start_policy": {
            "minimum_real_samples": MIN_REAL_SAMPLES,
            "serving_mode": "rule_based" if len(real_rows) < MIN_REAL_SAMPLES else "eligible_for_eval_gate",
        },
    }
    write_manifest(TRAIN_PATH.parent / "ssr_forgetting_curve_manifest.json", manifest)
    print(f"Wrote {TRAIN_PATH} ({len(train_rows)} rows)")
    print(f"Wrote {TEST_PATH} ({len(test_rows)} rows)")
    print(f"real_samples={len(real_rows)} synthetic_samples={synthetic_count}")


if __name__ == "__main__":
    main()
