"""Дашборд освоения: API /dashboard/mastery и логика рекомендаций."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.quiz_adaptive import update_mastery_after_score
from app.spaced_repetition import update_spaced_repetition
from app.user_state import _with_db, reset_schema_cache_for_tests, set_kv
from app.visualization_service import (
    MasteryDashboard,
    _next_topic_recommendation,
    dashboard,
)


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "us.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _force_concept_due_now(concept: str) -> None:
    def _work(conn):
        conn.execute(
            "UPDATE spaced_repetition SET next_review = ? WHERE concept = ?",
            ("2000-01-01T00:00:00+00:00", concept),
        )
        conn.commit()

    _with_db(_work)


def _minimal_graph(path: Path) -> JsonKnowledgeGraph:
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "a", "prerequisites": []},
                    "B": {"description": "b", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return JsonKnowledgeGraph(path)


def test_next_topic_prefers_due_spaced(tmp_path: Path):
    kg = _minimal_graph(tmp_path / "concept_graph.json")
    overlay = {
        "A": {"level": "recognition"},
        "B": {"level": "recognition"},
    }
    due = [{"concept": "B", "next_review": "2000-01-01T00:00:00+00:00"}]
    rec = _next_topic_recommendation(kg, overlay, due, [])
    assert rec["topic"] == "B"
    assert rec["reason"] == "spaced_repetition_due"


def test_next_topic_quiz_path_when_no_due(tmp_path: Path):
    kg = _minimal_graph(tmp_path / "g.json")
    overlay = {
        "A": {"level": "recognition"},
        "B": {"level": "recognition"},
    }
    rec = _next_topic_recommendation(kg, overlay, [], [])
    assert rec["topic"] == "A"
    assert rec["reason"] == "quiz_mastery_path"


def test_mastery_dashboard_endpoint(isolated_user_db, monkeypatch, tmp_path: Path):
    kg = _minimal_graph(tmp_path / "cg.json")
    monkeypatch.setattr("app.routers.dashboard.dashboard", MasteryDashboard(kg))

    update_spaced_repetition("A", 5)
    _force_concept_due_now("A")

    from app.api import app

    client = TestClient(app)
    resp = client.get("/dashboard/mastery")
    assert resp.status_code == 200
    body = resp.json()
    assert "concepts_mastered" in body
    assert "due_reviews" in body and "prerequisite_graph" in body
    assert body["next_recommendation"]["topic"] == "A"


def test_mastery_dashboard_filters_stale_due_and_quiz_rows(isolated_user_db, tmp_path: Path):
    kg = _minimal_graph(tmp_path / "cg_stale.json")
    update_spaced_repetition("A", 5)
    update_spaced_repetition("legacy", 5)
    _force_concept_due_now("A")
    _force_concept_due_now("legacy")
    update_mastery_after_score("legacy", 0.0)

    data = MasteryDashboard(kg).get_mastery_data()

    due_concepts = [row["concept"] for row in data["due_reviews"]]
    quiz_concepts = [row["concept"] for row in data["quiz_mastery_rows"]]
    assert due_concepts == ["A"]
    assert "legacy" not in quiz_concepts
    assert data["due_count"] == 1


def test_global_dashboard_has_keys():
    d = dashboard.get_mastery_data()
    assert set(d.keys()) >= {
        "concepts_mastered",
        "due_reviews",
        "next_recommendation",
        "prerequisite_graph",
        "weekly_goals",
        "mastery_vector",
        "gamification",
    }


def test_dashboard_adaptive_daily_plan_endpoint(isolated_user_db, tmp_path: Path, monkeypatch):
    kg = _minimal_graph(tmp_path / "concept_graph.json")
    monkeypatch.setattr("app.routers.dashboard.dashboard", MasteryDashboard(kg))
    from app.learning_plan_service import ADAPTIVE_DAILY_PLAN_KV_KEY

    today = datetime.now(timezone.utc).date().isoformat()
    set_kv(
        ADAPTIVE_DAILY_PLAN_KV_KEY,
        json.dumps({"date": today, "blocks": [{"type": "review", "concept": "A"}]}),
    )
    from app.api import app

    client = TestClient(app)
    resp = client.get("/dashboard/adaptive_daily_plan")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("date") == today
    assert isinstance(body.get("blocks"), list)


def test_dashboard_coach_plan_includes_adaptive_daily_plan(isolated_user_db, tmp_path: Path, monkeypatch):
    kg = _minimal_graph(tmp_path / "concept_graph.json")
    monkeypatch.setattr("app.routers.dashboard.dashboard", MasteryDashboard(kg))
    from app.api import app

    client = TestClient(app)
    resp = client.get("/dashboard/coach_plan")
    assert resp.status_code == 200
    body = resp.json()
    assert "adaptive_daily_plan" in body
    assert "daily_plan" in body
