"""Educational metrics aggregation (quiz, retention 7d+, SRS, micro-quiz events)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.educational_metrics_service import get_educational_metrics_report
from app.quiz_adaptive import SUCCESS_THRESHOLD
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "edu_metrics.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _insert_quiz(
    conn,
    *,
    concept: str,
    level: str,
    score: float,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT INTO quiz_results(concept, level, score, timestamp, attempt_number)
        VALUES (?, ?, ?, ?, 1)
        """,
        (concept, level, score, ts),
    )


def test_educational_metrics_retention_and_transfer(isolated_user_db) -> None:
    def _seed(conn):
        _insert_quiz(conn, concept="A", level="recognition", score=0.8, ts="2026-01-01T12:00:00+00:00")
        _insert_quiz(conn, concept="A", level="recognition", score=0.75, ts="2026-01-20T12:00:00+00:00")
        _insert_quiz(conn, concept="B", level="transfer", score=0.85, ts="2026-01-05T12:00:00+00:00")
        _insert_quiz(conn, concept="B", level="transfer", score=0.4, ts="2026-01-22T12:00:00+00:00")
        conn.execute(
            """
            INSERT INTO spaced_repetition(concept, easiness, interval_days, repetitions, next_review, last_review)
            VALUES ('A', 2.5, 5, 3, '2026-02-01T00:00:00+00:00', '2026-01-15T00:00:00+00:00')
            """,
        )
        conn.execute(
            """
            INSERT INTO micro_quiz_events(topic, feedback_json, next_step_json, created_at)
            VALUES ('t', ?, '{}', '2026-01-01T00:00:00+00:00')
            """,
            (json.dumps({"status": "correct"}),),
        )
        conn.commit()

    _with_db(_seed, write=True)

    r = get_educational_metrics_report(limit_quiz_rows=100)
    assert r["schema_version"] == 1
    assert r["quiz_correctness"]["attempts"] == 4
    assert r["retention_after_7d"]["pairs_ge_7d"] == 2
    assert r["retention_after_7d"]["both_successful_rate"] == 0.5
    assert r["transfer_outcomes"]["attempts"] == 2
    assert r["srs_stability"]["concepts_tracked"] == 1
    assert r["micro_quiz_events"]["parsed_attempts"] == 1
    assert r["micro_quiz_events"]["correct_rate"] == 1.0
    assert r["quiz_correctness"]["success_threshold"] == SUCCESS_THRESHOLD


def test_educational_metrics_empty_db(isolated_user_db) -> None:
    r = get_educational_metrics_report()
    assert r["quiz_correctness"]["attempts"] == 0
    assert r["transfer_outcomes"]["attempts"] == 0
