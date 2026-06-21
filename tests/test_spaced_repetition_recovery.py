"""US-7.2: отложение хвоста overdue spaced repetition."""
from __future__ import annotations

import json
from datetime import timedelta, timezone
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "sr.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_defer_overdue_keeps_first_seven_in_queue(isolated_user_db, tmp_path: Path):
    cg = tmp_path / "concept_graph.json"
    cg.write_text(json.dumps({"concepts": {}}, ensure_ascii=False), encoding="utf-8")
    kg = JsonKnowledgeGraph(cg)

    from datetime import datetime

    now = datetime.now(timezone.utc)

    def seed(conn):
        for i in range(10):
            days_ago = 30 - i
            nr = (now - timedelta(days=days_ago)).isoformat()
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, 2.5, 1, 0, ?, ?)
                """,
                (f"c{i}", nr, nr),
            )
        conn.commit()

    _with_db(seed)

    from app.spaced_repetition import count_due_reviews, defer_overdue_reviews_for_recovery, get_due_reviews

    assert count_due_reviews() == 10
    moved = defer_overdue_reviews_for_recovery(kg, keep_limit=7, stagger_days=5)
    assert moved == 3
    assert count_due_reviews() == 7
    assert [row["concept"] for row in get_due_reviews(limit=10)] == [f"c{i}" for i in range(7)]
