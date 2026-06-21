"""SM-2 и хранилище spaced_repetition (локальный SQLite)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.spaced_repetition import (
    apply_sm2,
    count_due_reviews,
    due_priority_reason,
    due_priority_by_concept,
    get_due_reviews,
    update_spaced_repetition,
)
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "us.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_apply_sm2_fail_resets():
    e, i, r = apply_sm2(2.5, 6, 2, 2)
    assert r == 0
    assert i == 1


def test_apply_sm2_first_second_third_success():
    e1, i1, r1 = apply_sm2(2.5, 1, 0, 5)
    assert r1 == 1 and i1 == 1
    e2, i2, r2 = apply_sm2(e1, i1, r1, 5)
    assert r2 == 2 and i2 == 6
    e3, i3, r3 = apply_sm2(e2, i2, r2, 5)
    assert r3 == 3
    assert i3 >= 1


def _force_concept_due_now(concept: str) -> None:
    """Для теста: просрочить next_review (иначе интервал 1+ день — не попадает в due сразу)."""

    def _work(conn):
        conn.execute(
            "UPDATE spaced_repetition SET next_review = ? WHERE concept = ?",
            ("2000-01-01T00:00:00+00:00", concept),
        )
        conn.commit()

    _with_db(_work)


def test_due_priority_map(isolated_user_db):
    update_spaced_repetition("P1", 5)
    _force_concept_due_now("P1")
    m = due_priority_by_concept(limit=10)
    assert m.get("P1", 0) > 0.9


def test_due_priority_reason_prefers_quiz_and_mastery_signals():
    row = {
        "concept": "A",
        "easiness": 2.4,
        "repetitions": 2,
        "next_review": "2099-01-01T00:00:00+00:00",
    }
    assert due_priority_reason(row, has_quiz_errors=True) == "ошибки в quiz"
    assert due_priority_reason(row, has_low_mastery_signal=True) == "низкий mastery"


def test_get_due_reviews_ranks_by_days_overdue_times_mastery_gap(isolated_user_db, monkeypatch):
    monkeypatch.setattr(
        "app.spaced_repetition._utc_now",
        lambda: datetime(2026, 4, 28, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )

    def _seed(conn):
        rows = [
            ("recent-hard", 1.4, "2026-04-20T00:00:00+00:00"),
            ("old-easy", 2.8, "2026-04-10T00:00:00+00:00"),
            ("middle", 2.0, "2026-04-15T00:00:00+00:00"),
        ]
        for concept, easiness, next_review in rows:
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, ?, 1, 0, ?, ?)
                """,
                (concept, easiness, next_review, next_review),
            )
        conn.commit()

    _with_db(_seed)

    due = get_due_reviews(limit=10)

    assert [row["concept"] for row in due] == ["middle", "recent-hard", "old-easy"]
    assert due[0]["priority_score"] > due[1]["priority_score"] > due[2]["priority_score"]


def test_get_due_reviews_uses_stable_tie_breakers(isolated_user_db, monkeypatch):
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )

    def _seed(conn):
        rows = [
            ("beta", 2.5, "2026-04-10T00:00:00+00:00"),
            ("alpha", 2.5, "2026-04-10T00:00:00+00:00"),
            ("gamma", 2.5, "2026-04-11T00:00:00+00:00"),
        ]
        for concept, easiness, next_review in rows:
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, ?, 1, 0, ?, ?)
                """,
                (concept, easiness, next_review, next_review),
            )
        conn.commit()

    _with_db(_seed)

    due = get_due_reviews(limit=10)

    assert [row["concept"] for row in due] == ["alpha", "beta", "gamma"]
    assert all("days_overdue" in row and "mastery_gap" in row for row in due)


def test_update_and_due(isolated_user_db):
    r = update_spaced_repetition("ConceptA", 4)
    assert r["concept"] == "ConceptA"
    assert "next_review" in r
    assert count_due_reviews() == 0
    _force_concept_due_now("ConceptA")
    assert count_due_reviews() >= 1
    due = get_due_reviews(limit=10)
    assert any(d["concept"] == "ConceptA" for d in due)


def test_update_uses_sr_config_budget(isolated_user_db, monkeypatch):
    from app import spaced_repetition

    class _S:
        sr_min_quality = 4
        sr_max_interval_days = 3

    monkeypatch.setattr(spaced_repetition, "get_settings", lambda: _S())
    r1 = update_spaced_repetition("Budgeted", 0)
    r2 = update_spaced_repetition("Budgeted", 5)
    r3 = update_spaced_repetition("Budgeted", 5)

    assert r1["quality"] == 4
    assert r3["interval_days"] <= 3
    assert r2["repetitions"] >= 2


def test_review_due_endpoint(isolated_user_db, monkeypatch):
    p = isolated_user_db.parent / "review_graph_active.json"
    p.write_text(
        '{"concepts":{"X":{"description":"","prerequisites":[]}},"documents":{},"edges":{}}',
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    monkeypatch.setattr("app.routers.review.get_active_knowledge_graph", lambda: kg)

    update_spaced_repetition("X", 5)
    _force_concept_due_now("X")
    from app.api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/review/due")
    assert resp.status_code == 200
    data = resp.json()
    assert "due_reviews" in data and "count" in data
    assert data["count"] >= 1


def test_review_due_endpoint_filters_stale_concepts(isolated_user_db, monkeypatch, tmp_path: Path):
    p = tmp_path / "review_graph.json"
    p.write_text(
        '{"concepts":{"A":{"description":"","prerequisites":[]}},"documents":{},"edges":{}}',
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    monkeypatch.setattr("app.routers.review.get_active_knowledge_graph", lambda: kg)

    update_spaced_repetition("A", 5)
    update_spaced_repetition("legacy", 5)
    _force_concept_due_now("A")
    _force_concept_due_now("legacy")

    from app.api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/review/due")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert [row["concept"] for row in data["due_reviews"]] == ["A"]


def test_generation_rollover_archives_spaced_repetition(isolated_user_db, monkeypatch):
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-a", "index_version": 1},
    )
    monkeypatch.setattr("app.user_state._active_concept_ids_for_lineage", lambda: {"A"})
    update_spaced_repetition("A", 5)
    _force_concept_due_now("A")
    assert count_due_reviews() == 1

    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-b", "index_version": 2},
    )
    assert count_due_reviews() == 0

    def _work(conn):
        live = conn.execute(
            "SELECT COUNT(*) AS n FROM spaced_repetition WHERE concept = ?",
            ("A",),
        ).fetchone()
        archived = conn.execute(
            """
            SELECT source_generation_id, target_generation_id, archived_reason
            FROM spaced_repetition_archive
            WHERE concept = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            ("A",),
        ).fetchone()
        return int(live["n"] or 0), dict(archived) if archived else None

    live_count, archived = _with_db(_work)
    assert live_count == 0
    assert archived is not None
    assert archived["source_generation_id"] == "gen-a"
    assert archived["target_generation_id"] == "gen-b"
    assert archived["archived_reason"] == "generation_rollover"


def _seed_ranked_due_concepts(n: int) -> None:
    now = datetime.now(timezone.utc)

    def seed(conn):
        for i in range(n):
            days_ago = max(1, 60 - (i % 60))
            easiness = 1.4 + (i % 10) * 0.1
            nr = (now - timedelta(days=days_ago)).isoformat()
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, ?, 1, 0, ?, ?)
                """,
                (f"due-{i:03d}", easiness, nr, nr),
            )
        conn.commit()

    _with_db(seed)


@pytest.mark.parametrize("due_total", [5, 50, 120], ids=["small_5", "threshold_50", "overflow_120"])
def test_get_due_reviews_top_seven_order_stable(isolated_user_db, monkeypatch, due_total):
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )
    _seed_ranked_due_concepts(due_total)

    first = get_due_reviews(limit=7)
    second = get_due_reviews(limit=7)

    assert len(first) == min(7, due_total)
    assert [row["concept"] for row in first] == [row["concept"] for row in second]
    assert all("priority_score" in row for row in first)
    if len(first) >= 2:
        assert first[0]["priority_score"] >= first[1]["priority_score"]
