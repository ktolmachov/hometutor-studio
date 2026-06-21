"""Mastery validation reporting (correlation, graduation cross-check)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.educational_metrics_service import get_mastery_validation_report
from app.knowledge_graph import JsonKnowledgeGraph
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "mastery_val.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _graph_with_graduated(tmp_path: Path) -> JsonKnowledgeGraph:
    p = tmp_path / "kg.json"
    p.write_text(
        json.dumps(
            {
                "concepts": {
                    "Grad1": {
                        "description": "",
                        "prerequisites": [],
                        "graduated": True,
                        "graduation_status": "graduated",
                    },
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return JsonKnowledgeGraph(p)


def test_mastery_validation_correlation_and_false_positive(isolated_user_db, monkeypatch, tmp_path: Path):
    kg = _graph_with_graduated(tmp_path)
    monkeypatch.setattr("app.educational_metrics_service.get_active_knowledge_graph", lambda: kg)

    def _seed(conn):
        conn.execute(
            """
            INSERT INTO quiz_mastery(concept, current_level, success_streak, last_updated)
            VALUES
              ('Grad1', 'transfer', 0, '2026-01-01T00:00:00+00:00'),
              ('Low', 'recognition', 0, '2026-01-01T00:00:00+00:00')
            """,
        )
        conn.execute(
            """
            INSERT INTO spaced_repetition(concept, easiness, interval_days, repetitions, next_review, last_review)
            VALUES
              ('Grad1', 2.5, 10, 4, '2026-02-01T00:00:00+00:00', '2026-01-15T00:00:00+00:00'),
              ('Low', 2.5, 2, 1, '2026-02-01T00:00:00+00:00', '2026-01-15T00:00:00+00:00')
            """,
        )
        conn.execute(
            """
            INSERT INTO quiz_results(concept, level, score, timestamp, attempt_number)
            VALUES ('Grad1', 'transfer', 0.5, '2026-05-01T12:00:00+00:00', 1)
            """,
        )
        conn.commit()

    _with_db(_seed, write=True)

    r = get_mastery_validation_report(limit_quiz_rows=50)
    assert r["schema_version"] == 1
    assert r["mastery_correlation"]["paired_concepts"] == 2
    assert r["mastery_correlation"]["pearson_mastery_pct_vs_interval_days"] is not None
    assert r["transfer_level_state"]["concepts_at_transfer_in_quiz_mastery"] == 1
    assert r["false_positive_graduation"]["weak_recent_transfer_count"] >= 1
    checks = r["false_positive_graduation"]["checks"]
    assert any(c["concept"] == "Grad1" and c["flag"] == "weak_recent_transfer" for c in checks)


def test_mastery_validation_empty_graduated(isolated_user_db, monkeypatch, tmp_path: Path):
    p = tmp_path / "empty_kg.json"
    p.write_text(
        json.dumps({"concepts": {}, "documents": {}, "edges": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.educational_metrics_service.get_active_knowledge_graph",
        lambda: JsonKnowledgeGraph(p),
    )
    r = get_mastery_validation_report()
    assert r["false_positive_graduation"]["graduated_concepts_checked"] == 0
