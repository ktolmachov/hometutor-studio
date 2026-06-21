"""Smoke tests for Personalized Learner Model 19.5."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.knowledge_graph import get_mastery_vector
from app.learner_model_service import (
    EMOTIONAL_HEATMAP_KV_KEY,
    PERSONALIZED_LEARNER_HISTORY_KV_KEY,
    PERSONALIZED_LEARNER_KV_KEY,
    PersonalizedLearnerModel,
    get_emotional_heatmap_pivot,
    get_learner_profile_migration_metrics,
    get_learner_state_health,
    get_learner_profile_history,
    get_personalized_learner_profile,
    load_emotional_heatmap_rows,
    merge_personalized_into_learner_profile,
    save_learner_profile,
    save_emotional_snapshot,
)
from app.user_state import get_kv, reset_schema_cache_for_tests, set_kv
from app.config import reset_settings_cache


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "lm.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_get_mastery_vector_has_avg():
    with patch("app.quiz_adaptive.get_all_mastery_levels", return_value={"a": "recognition"}):
        v = get_mastery_vector()
        assert "avg" in v
        assert v["a"] == 0.44
        assert 0.0 <= v["avg"] <= 1.0


def test_merge_preserves_route_from_base():
    base = {"route": "due_review", "focus_topic": "x"}
    with patch(
        "app.learner_model_service.get_personalized_learner_profile",
        return_value=PersonalizedLearnerModel(user_id="local"),
    ):
        m = merge_personalized_into_learner_profile(base, user_id="local", session_id=None)
    assert m["route"] == "due_review"
    assert m["personalized_model_version"] == "19.5"
    assert "style_weights" in m


def test_emotional_snapshot_persists_to_kv(isolated_user_db):
    save_emotional_snapshot("local", "engaged", concept="RAG")
    raw = get_kv(EMOTIONAL_HEATMAP_KV_KEY)
    assert raw and "RAG" in raw and "engaged" in raw
    rows = load_emotional_heatmap_rows()
    assert len(rows) >= 1
    assert rows[-1].get("concept") == "RAG"
    p = get_emotional_heatmap_pivot(last_days=30)
    assert p is not None


def test_profile_filters_orphaned_mastery_for_active_index(isolated_user_db, monkeypatch):
    set_kv(
        PERSONALIZED_LEARNER_KV_KEY,
        json.dumps({"index_context": {"index_version": 6, "generation_id": "gen-6"}}),
    )

    class _KG:
        def get_concepts(self):
            return {"A": {"description": ""}, "B": {"description": ""}}

    monkeypatch.setattr(
        "app.learner_model_service.get_index_version_public",
        lambda: {"index_version": 7, "generation_id": "gen-7", "activated_at": "2026-04-07T10:00:00+00:00"},
    )
    monkeypatch.setattr("app.learner_model_service.get_active_knowledge_graph", lambda: _KG())
    monkeypatch.setattr(
        "app.learner_model_service.get_mastery_vector",
        lambda user_id=None: {"A": 0.44, "legacy": 0.82, "avg": 0.63},
    )

    profile = get_personalized_learner_profile("local")

    assert "legacy" not in profile.mastery_vector
    assert profile.mastery_vector["A"] == pytest.approx(0.44)
    assert profile.index_context["generation_id"] == "gen-7"
    assert profile.state_migration["index_changed"] is True
    assert profile.state_migration["orphaned_mastery_concepts"] == 1
    assert profile.state_migration["orphaned_mastery_sample"] == ["legacy"]
    assert profile.is_stale is True


def test_save_learner_profile_persists_index_context(isolated_user_db, monkeypatch):
    monkeypatch.setattr(
        "app.learner_model_service.get_index_version_public",
        lambda: {"index_version": 3, "generation_id": "gen-3", "activated_at": "2026-04-07T11:00:00+00:00"},
    )

    save_learner_profile("local", {"sessions_completed": 2})

    raw = json.loads(get_kv(PERSONALIZED_LEARNER_KV_KEY) or "{}")
    assert raw["profile_schema_version"] == 2
    assert raw["index_context"]["index_version"] == 3
    assert raw["index_context"]["generation_id"] == "gen-3"


def test_save_learner_profile_appends_versioned_history(isolated_user_db, monkeypatch):
    monkeypatch.setattr(
        "app.learner_model_service.get_index_version_public",
        lambda: {"index_version": 8, "generation_id": "gen-8", "activated_at": "2026-04-08T08:00:00+00:00"},
    )
    save_learner_profile("local", {"sessions_completed": 1, "optimal_depth": "beginner"})
    monkeypatch.setattr(
        "app.learner_model_service.get_index_version_public",
        lambda: {"index_version": 9, "generation_id": "gen-9", "activated_at": "2026-04-08T09:00:00+00:00"},
    )
    save_learner_profile("local", {"sessions_completed": 2, "optimal_depth": "advanced"})

    raw_hist = json.loads(get_kv(PERSONALIZED_LEARNER_HISTORY_KV_KEY) or "[]")
    assert isinstance(raw_hist, list)
    assert len(raw_hist) >= 2
    assert raw_hist[-2]["index_context"]["generation_id"] == "gen-8"
    assert raw_hist[-1]["index_context"]["generation_id"] == "gen-9"
    assert raw_hist[-1]["sessions_completed"] == 2
    assert raw_hist[-1]["profile_schema_version"] == 2

    hist = get_learner_profile_history(limit=1)
    assert len(hist) == 1
    assert hist[0]["index_context"]["generation_id"] == "gen-9"


def test_profile_rehydrates_mastery_from_history_when_current_is_orphaned(isolated_user_db, monkeypatch):
    set_kv(
        PERSONALIZED_LEARNER_HISTORY_KV_KEY,
        json.dumps(
            [
                {
                    "timestamp": "2026-04-08T09:00:00+00:00",
                    "profile_schema_version": 2,
                    "index_context": {"index_version": 4, "generation_id": "gen-4"},
                    "mastery_vector": {"A": 0.66, "legacy": 0.91, "avg": 0.78},
                }
            ]
        ),
    )

    class _KG:
        def get_concepts(self):
            return {"A": {"description": ""}, "B": {"description": ""}}

    monkeypatch.setattr(
        "app.learner_model_service.get_index_version_public",
        lambda: {"index_version": 5, "generation_id": "gen-5", "activated_at": "2026-04-08T10:00:00+00:00"},
    )
    monkeypatch.setattr("app.learner_model_service.get_active_knowledge_graph", lambda: _KG())
    monkeypatch.setattr(
        "app.learner_model_service.get_mastery_vector",
        lambda user_id=None: {"legacy_only": 0.82, "avg": 0.82},
    )

    profile = get_personalized_learner_profile("local")

    assert profile.mastery_vector["A"] == pytest.approx(0.66)
    assert profile.state_migration["history_rehydrated"] is True
    assert profile.state_migration["history_rehydrated_source_generation_id"] == "gen-4"


def test_get_learner_profile_migration_metrics_rollup(isolated_user_db):
    set_kv(
        PERSONALIZED_LEARNER_HISTORY_KV_KEY,
        json.dumps(
            [
                {
                    "index_context": {"generation_id": "gen-8"},
                    "state_migration": {"history_rehydrated": True, "index_changed": True},
                },
                {
                    "index_context": {"generation_id": "gen-9"},
                    "state_migration": {"history_rehydrated": False, "index_changed": True},
                },
            ]
        ),
    )
    out = get_learner_profile_migration_metrics(limit=50)
    assert out["window_size"] == 2
    assert out["rehydrated_total"] == 1
    assert out["rehydrated_rate"] == 0.5
    assert out["index_changed_total"] == 2
    assert out["latest_generation_id"] == "gen-9"
    assert out["by_generation"]["gen-8"] == 1


def test_learner_state_health_reports_stale_profile(isolated_user_db, monkeypatch):
    set_kv(
        PERSONALIZED_LEARNER_KV_KEY,
        json.dumps({"index_context": {"index_version": 1, "generation_id": "gen-old"}}),
    )

    class _KG:
        def get_concepts(self):
            return {"A": {"description": ""}}

    monkeypatch.setattr(
        "app.learner_model_service.get_index_version_public",
        lambda: {"index_version": 2, "generation_id": "gen-new", "activated_at": "2026-04-08T10:00:00+00:00"},
    )
    monkeypatch.setattr("app.learner_model_service.get_active_knowledge_graph", lambda: _KG())
    monkeypatch.setattr("app.learner_model_service.get_mastery_vector", lambda user_id=None: {"A": 0.44, "avg": 0.44})

    out = get_learner_state_health("local", limit_history=20)

    assert out["schema_version"] == 1
    assert out["status"] == "stale"
    assert out["is_stale"] is True
    assert out["state_migration"]["is_stale"] is True


def test_adaptive_plan_module_has_no_cycle():
    """`learner_model_service` and `learning_plan_service` must both pull
    `AdaptiveDailyPlan` from `app.adaptive_plan` instead of importing each
    other inside function bodies."""
    import importlib
    import inspect

    adaptive_plan = importlib.import_module("app.adaptive_plan")
    lms = importlib.import_module("app.learner_model_service")
    lps = importlib.import_module("app.learning_plan_service")

    assert lms.AdaptiveDailyPlan is adaptive_plan.AdaptiveDailyPlan
    assert lps.AdaptiveDailyPlan is adaptive_plan.AdaptiveDailyPlan

    # No function inside learner_model_service may locally import the class
    # from learning_plan_service (the old, cycle-creating pattern).
    src = inspect.getsource(lms)
    assert "from app.learning_plan_service import AdaptiveDailyPlan" not in src

    # The extracted module must not depend on either service at module level.
    ap_src = inspect.getsource(adaptive_plan)
    top_level = ap_src.split("\nclass AdaptiveDailyPlan", 1)[0]
    assert "from app.learner_model_service" not in top_level
    assert "from app.learning_plan_service" not in top_level


def test_concept_recovery_ladder_persist_roundtrip(isolated_user_db):
    from app.learner_model_service import (
        persist_concept_recovery_ladder,
        read_persisted_concept_recovery_ladder,
    )
    from app.smart_study_recovery_ladder import ladder_step_from_resume_v1

    blob = persist_concept_recovery_ladder(3, concept_anchor="RAG basics", scope_id="course-1")
    assert blob is not None
    assert blob["step"] == 3

    loaded = read_persisted_concept_recovery_ladder()
    assert loaded is not None
    assert ladder_step_from_resume_v1(loaded) == 3
    assert loaded.get("scope_id") == "course-1"

    persist_concept_recovery_ladder(1, clear=True)
    assert read_persisted_concept_recovery_ladder() is None
