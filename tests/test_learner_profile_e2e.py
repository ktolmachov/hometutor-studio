"""E5.4 learner profile round-trip through generation swap."""

from __future__ import annotations

from pathlib import Path

import pytest

import app.index_registry as index_registry
import app.user_state as user_state
from app.config import reset_settings_cache
from app.index_lifecycle import apply_index_activation_hooks
from app.learner_model_service import get_learner_state_health, save_learner_profile
from app.quiz_adaptive import update_mastery_after_score
from app.spaced_repetition import update_spaced_repetition


@pytest.fixture
def isolated_e5(monkeypatch, tmp_path: Path):
    db = tmp_path / "user_state.db"
    reg = tmp_path / "index_registry.json"
    lock = tmp_path / "index_registry.json.lock"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()
    monkeypatch.setattr(index_registry, "REGISTRY_PATH", reg)
    monkeypatch.setattr(index_registry, "REGISTRY_LOCK_PATH", lock)
    monkeypatch.setattr(index_registry, "LEGACY_ACTIVE_INDEX_PATH", tmp_path / "missing_active.json")

    def _active_concepts():
        gid = str(user_state.get_current_learner_state_lineage().get("generation_id") or "")
        return {"A"} if "chunks_a" in gid else {"B"}

    monkeypatch.setattr(user_state, "_active_concept_ids_for_lineage", _active_concepts)
    yield
    reset_settings_cache()
    user_state.reset_schema_cache_for_tests()


def test_learner_profile_round_trip_generation_swap(isolated_e5):
    index_registry.activate_reset_generation(chunks_collection="chunks_a", summaries_collection="summaries_a")
    update_mastery_after_score("A", 1.0)
    update_mastery_after_score("A", 1.0)
    update_spaced_repetition("A", 5)
    save_learner_profile("local", {"mastery_vector": {"A": 0.68, "avg": 0.68}, "sessions_completed": 1})

    index_registry.activate_staging_generation(chunks_collection="chunks_b", summaries_collection="summaries_b")
    hook = apply_index_activation_hooks(reset=False)
    health = get_learner_state_health("local")
    diag = user_state.get_learner_state_diagnostics()
    log = user_state.list_learner_profile_migration_log(limit=5)

    assert hook["learner_state_lineage"]["generation_id"] == health["current_index_context"]["generation_id"]
    assert health["is_stale"] is True
    assert health["status"] == "stale"
    assert diag["archive_counts"]["spaced_repetition"] == 1
    assert diag["archive_counts"]["quiz_mastery"] == 1
    assert log[0]["event_type"] == "generation_rollover"
    assert log[0]["archived_counts"]["spaced_repetition"] == 1
    assert log[0]["archived_counts"]["quiz_mastery"] == 1
