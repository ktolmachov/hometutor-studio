"""analytics_service: smoke без тяжёлых зависимостей от LLM."""

from __future__ import annotations

import json
from pathlib import Path

from app.analytics_service import build_forgetting_curve_points, get_advanced_analytics
from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.quiz_adaptive import update_mastery_after_score
from app.spaced_repetition import update_spaced_repetition
from app.user_state import _with_db, reset_schema_cache_for_tests


def _force_due(concept: str) -> None:
    def _work(conn):
        conn.execute(
            "UPDATE spaced_repetition SET next_review = ? WHERE concept = ?",
            ("2000-01-01T00:00:00+00:00", concept),
        )
        conn.commit()

    _with_db(_work)


def test_advanced_analytics_filters_stale_concepts(monkeypatch, tmp_path: Path):
    db = tmp_path / "analytics.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()

    p = tmp_path / "analytics_graph.json"
    p.write_text(
        json.dumps(
            {"concepts": {"A": {"description": "", "prerequisites": []}}, "documents": {}, "edges": {}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    monkeypatch.setattr("app.analytics_service.get_active_knowledge_graph", lambda: kg)

    update_mastery_after_score("legacy", 0.0)
    update_spaced_repetition("legacy", 5)
    _force_due("legacy")

    data = get_advanced_analytics()

    assert data["weak_concepts"] == []
    assert "legacy" not in data["weekly_ai_recommendation"]


def test_forgetting_curve_has_points():
    pts = build_forgetting_curve_points()
    assert len(pts) == 15
    assert "day" in pts[0] and "retention" in pts[0]


def test_advanced_analytics_returns_keys():
    d = get_advanced_analytics()
    assert "heatmap" in d
    assert "forgetting_curve" in d
    assert "time_roi_text" in d
    assert "weekly_ai_recommendation" in d
    assert "learner_state_diagnostics" in d


def test_advanced_analytics_exposes_archive_diagnostics(monkeypatch, tmp_path: Path):
    db = tmp_path / "analytics_archive.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()

    p = tmp_path / "analytics_archive_graph.json"
    p.write_text(
        json.dumps(
            {"concepts": {"A": {"description": "", "prerequisites": []}}, "documents": {}, "edges": {}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    monkeypatch.setattr("app.analytics_service.get_active_knowledge_graph", lambda: kg)
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-a", "index_version": 1},
    )
    monkeypatch.setattr("app.user_state._active_concept_ids_for_lineage", lambda: {"A"})
    update_mastery_after_score("A", 1.0)
    update_spaced_repetition("A", 5)

    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-b", "index_version": 2},
    )
    data = get_advanced_analytics()
    diag = data["learner_state_diagnostics"]

    assert diag["has_archived_state"] is True
    assert diag["archive_counts"]["total"] == 2
    assert diag["archive_reasons"]["generation_rollover"] == 2
    assert diag["current_lineage"]["generation_id"] == "gen-b"
