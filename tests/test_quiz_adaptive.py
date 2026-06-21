"""Адаптивная сложность quiz (quiz_mastery)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.quiz_adaptive import (
    SUCCESS_THRESHOLD,
    get_all_mastery_levels,
    get_recommended_difficulty,
    get_weak_concepts,
    list_quiz_mastery_state,
    update_mastery_after_score,
)
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "qm.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_default_level(isolated_user_db):
    assert get_recommended_difficulty("NewConcept") == "recognition"


def test_promote_after_two_successes(isolated_user_db):
    c = "Alpha"
    update_mastery_after_score(c, SUCCESS_THRESHOLD + 0.05)
    assert get_recommended_difficulty(c) == "recognition"
    r = update_mastery_after_score(c, SUCCESS_THRESHOLD + 0.05)
    assert r["current_level"] == "recall"
    assert r["success_streak"] == 0


def test_fail_drops_level(isolated_user_db):
    c = "Beta"
    update_mastery_after_score(c, 1.0)
    update_mastery_after_score(c, 1.0)
    assert get_recommended_difficulty(c) == "recall"
    r = update_mastery_after_score(c, 0.0)
    assert r["current_level"] == "recognition"
    assert r["success_streak"] == 0


def test_get_all_mastery_levels_and_list_state(isolated_user_db):
    update_mastery_after_score("Gamma", 1.0)
    lv = get_all_mastery_levels()
    assert lv.get("Gamma") == "recognition"
    rows = list_quiz_mastery_state()
    assert any(r.get("concept") == "Gamma" for r in rows)


def test_get_weak_concepts_threshold(isolated_user_db):
    update_mastery_after_score("WeakOne", 1.0)
    w = get_weak_concepts(threshold=60, limit=5)
    assert "WeakOne" in w


def test_generation_rollover_archives_quiz_mastery(isolated_user_db, monkeypatch):
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-a", "index_version": 1},
    )
    monkeypatch.setattr("app.user_state._active_concept_ids_for_lineage", lambda: {"Gamma"})
    update_mastery_after_score("Gamma", 1.0)

    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-b", "index_version": 2},
    )
    assert get_recommended_difficulty("Gamma") == "recognition"

    def _work(conn):
        live = conn.execute(
            "SELECT COUNT(*) AS n FROM quiz_mastery WHERE concept = ?",
            ("Gamma",),
        ).fetchone()
        archived = conn.execute(
            """
            SELECT source_generation_id, target_generation_id, archived_reason
            FROM quiz_mastery_archive
            WHERE concept = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            ("Gamma",),
        ).fetchone()
        return int(live["n"] or 0), dict(archived) if archived else None

    live_count, archived = _with_db(_work)
    assert live_count == 0
    assert archived is not None
    assert archived["source_generation_id"] == "gen-a"
    assert archived["target_generation_id"] == "gen-b"
    assert archived["archived_reason"] == "generation_rollover"
