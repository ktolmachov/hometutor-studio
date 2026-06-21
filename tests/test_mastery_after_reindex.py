"""
US-8.1 + US-8.2 acceptance tests: mastery preservation and badge after reindex.

Tests verify:
  US-8.1 — mastery_vector survives generation change via versioned history rehydration.
  US-8.2 — badge "Профиль обновлён после переиндексации" shown with date when rehydrated.

Architecture under test (learner_model_service.py):
  _rehydrate_mastery_from_profile_history() — core rehydration from KV history
  get_personalized_learner_profile()        — integration path (stale → rehydrate)
  _filter_mastery_vector_for_active_index() — orphan filtering (active concepts only)
  apply_index_activation_hooks()            — calls run_learner_state_lineage_sync()
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module-level imports (fail fast if implementation is missing)
# ---------------------------------------------------------------------------

from app.learner_model_service import (
    PERSONALIZED_LEARNER_HISTORY_KV_KEY,
    PERSONALIZED_LEARNER_KV_KEY,
    PersonalizedLearnerModel,
    _filter_mastery_vector_for_active_index,
    _rehydrate_mastery_from_profile_history,
    get_personalized_learner_profile,
)
from app.ui.learner_profile_panel import (
    US_8_2_REINDEX_BADGE_LABEL_RU,
    format_reindex_badge_date_display,
    reindex_profile_badge_parts,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _history_row(
    *,
    mastery: dict[str, float],
    generation_id: str = "gen-old",
    index_version: int = 1,
    timestamp: str = "2026-04-10T10:00:00+00:00",
) -> dict[str, Any]:
    """Build a versioned history row for PERSONALIZED_LEARNER_HISTORY_KV_KEY."""
    return {
        "timestamp": timestamp,
        "profile_schema_version": 2,
        "index_context": {
            "generation_id": generation_id,
            "index_version": index_version,
            "activated_at": timestamp,
        },
        "state_migration": {"history_rehydrated": False},
        "mastery_vector": mastery,
        "sessions_completed": 3,
        "learning_velocity": 0.12,
        "cognitive_load": 0.4,
        "emotional_state": "neutral",
        "optimal_depth": "intermediate",
    }


# ---------------------------------------------------------------------------
# US-8.1 — _filter_mastery_vector_for_active_index
# ---------------------------------------------------------------------------


class TestFilterMasteryVector:
    """Orphan-free filtering: result only contains active concepts."""

    def test_known_concepts_pass_through(self):
        mv = {"A": 0.8, "B": 0.6, "avg": 0.7}
        result, meta = _filter_mastery_vector_for_active_index(mv, active_concepts={"A", "B"})
        assert result["A"] == pytest.approx(0.8)
        assert result["B"] == pytest.approx(0.6)
        assert 0.0 <= result["avg"] <= 1.0

    def test_unknown_concepts_are_orphaned(self):
        mv = {"OLD_CONCEPT": 0.9, "B": 0.5}
        result, meta = _filter_mastery_vector_for_active_index(mv, active_concepts={"B"})
        assert "OLD_CONCEPT" not in result
        assert "B" in result
        assert meta["orphaned_mastery_concepts"] == 1

    def test_no_orphans_when_all_match(self):
        mv = {"A": 0.9, "B": 0.7}
        _, meta = _filter_mastery_vector_for_active_index(mv, active_concepts={"A", "B", "C"})
        assert meta["orphaned_mastery_concepts"] == 0

    def test_empty_active_concepts_orphans_all(self):
        mv = {"A": 0.9, "B": 0.7}
        result, meta = _filter_mastery_vector_for_active_index(mv, active_concepts=set())
        # When active_concepts is empty, filter is not applied (can't tell what's valid)
        assert meta["filter_applied"] is False
        # avg key may be present
        non_avg = {k: v for k, v in result.items() if k != "avg"}
        # All non-avg keys are retained when filter not applied
        for k in non_avg:
            assert k in mv

    def test_avg_is_recalculated(self):
        mv = {"A": 0.8, "B": 0.4, "avg": 0.0}  # stale avg
        result, _ = _filter_mastery_vector_for_active_index(mv, active_concepts={"A", "B"})
        expected_avg = (0.8 + 0.4) / 2
        assert result["avg"] == pytest.approx(expected_avg)

    def test_values_clamped_to_0_1(self):
        mv = {"A": 1.5, "B": -0.3}
        result, _ = _filter_mastery_vector_for_active_index(mv, active_concepts={"A", "B"})
        assert result["A"] == pytest.approx(1.0)
        assert result["B"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# US-8.1 — _rehydrate_mastery_from_profile_history
# ---------------------------------------------------------------------------


class TestRehydrateMasteryFromHistory:
    """Core rehydration logic: last compatible history entry with overlapping concepts."""

    def test_rehydrates_when_concepts_overlap(self, monkeypatch):
        history = [
            _history_row(mastery={"A": 0.8, "B": 0.6, "avg": 0.7}, generation_id="gen-old"),
        ]
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps(history) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        result, meta = _rehydrate_mastery_from_profile_history(active_concepts={"A", "B"})

        assert result["A"] == pytest.approx(0.8)
        assert result["B"] == pytest.approx(0.6)
        assert meta is not None
        assert meta["history_rehydrated"] is True
        assert int(meta["history_rehydrated_active_mastery_concepts"]) >= 1

    def test_returns_empty_when_no_concept_overlap(self, monkeypatch):
        history = [
            _history_row(mastery={"OLD_X": 0.9, "OLD_Y": 0.7}, generation_id="gen-old"),
        ]
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps(history) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        result, meta = _rehydrate_mastery_from_profile_history(active_concepts={"NEW_A", "NEW_B"})

        assert result == {}
        assert meta is None

    def test_returns_empty_when_history_is_empty(self, monkeypatch):
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps([]) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        result, meta = _rehydrate_mastery_from_profile_history(active_concepts={"A", "B"})

        assert result == {}
        assert meta is None

    def test_prefers_most_recent_compatible_row(self, monkeypatch):
        history = [
            _history_row(
                mastery={"A": 0.3, "avg": 0.3},
                generation_id="gen-old-1",
                timestamp="2026-04-01T10:00:00+00:00",
            ),
            _history_row(
                mastery={"A": 0.9, "avg": 0.9},
                generation_id="gen-old-2",
                timestamp="2026-04-10T10:00:00+00:00",
            ),
        ]
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps(history) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        result, meta = _rehydrate_mastery_from_profile_history(active_concepts={"A"})

        # Should use the LAST (most recent) compatible row
        assert result["A"] == pytest.approx(0.9)

    def test_meta_contains_source_generation_id(self, monkeypatch):
        history = [
            _history_row(mastery={"A": 0.7, "avg": 0.7}, generation_id="gen-source-123"),
        ]
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps(history) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        _, meta = _rehydrate_mastery_from_profile_history(active_concepts={"A"})

        assert meta is not None
        assert meta.get("history_rehydrated_source_generation_id") == "gen-source-123"

    def test_meta_contains_row_timestamp_for_badge(self, monkeypatch):
        ts = "2026-04-15T14:30:00+00:00"
        history = [_history_row(mastery={"A": 0.7}, generation_id="g", timestamp=ts)]
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps(history) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        _, meta = _rehydrate_mastery_from_profile_history(active_concepts={"A"})

        assert meta is not None
        assert meta.get("history_rehydrated_row_timestamp") == ts

    def test_skips_rows_without_mastery_data(self, monkeypatch):
        history = [
            {"timestamp": "2026-04-01", "mastery_vector": None, "index_context": {}},
            _history_row(mastery={"A": 0.8, "avg": 0.8}, generation_id="gen-ok"),
        ]
        monkeypatch.setattr(
            "app.learner_model_service.get_kv",
            lambda key: json.dumps(history) if key == PERSONALIZED_LEARNER_HISTORY_KV_KEY else None,
        )

        result, meta = _rehydrate_mastery_from_profile_history(active_concepts={"A"})

        assert result.get("A", 0) > 0
        assert meta is not None


# ---------------------------------------------------------------------------
# US-8.1 — Integration: get_personalized_learner_profile after generation change
# ---------------------------------------------------------------------------


class TestGetProfileAfterReindex:
    """
    Integration test: When generation_id changes and get_mastery_vector returns
    concepts not in new graph, mastery is rehydrated from history.
    """

    def _mock_kv_factory(self, history: list[dict]) -> dict[str, str]:
        """Build a simple in-memory kv store."""
        return {
            PERSONALIZED_LEARNER_HISTORY_KV_KEY: json.dumps(history),
            PERSONALIZED_LEARNER_KV_KEY: json.dumps({}),
        }

    def test_mastery_rehydrated_after_generation_change(self, monkeypatch):
        """
        Scenario: user had mastery for concepts A/B in gen-old.
        New gen-new is active, with SAME concepts A/B in graph.
        get_mastery_vector returns empty (new graph, no quiz yet).
        Expected: mastery rehydrated from history.
        """
        history = [
            _history_row(mastery={"A": 0.85, "B": 0.65, "avg": 0.75}, generation_id="gen-old"),
        ]
        kv = self._mock_kv_factory(history)

        monkeypatch.setattr("app.learner_model_service.get_kv", lambda key: kv.get(key))
        monkeypatch.setattr("app.learner_model_service.set_kv", lambda key, val: None)
        monkeypatch.setattr(
            "app.learner_model_service._current_index_context",
            lambda: {"generation_id": "gen-new", "index_version": 2, "activated_at": "2026-04-20T12:00:00+00:00"},
        )
        monkeypatch.setattr(
            "app.learner_model_service._active_concept_ids",
            lambda: {"A", "B"},  # same concept IDs in new graph
        )
        monkeypatch.setattr(
            "app.learner_model_service.get_mastery_vector",
            lambda uid: {},  # empty: new graph, no quiz mastery yet
        )
        monkeypatch.setattr(
            "app.learner_model_service.get_session_interaction_messages",
            lambda sid, last_n=10: [],
        )

        profile = get_personalized_learner_profile("local")

        assert profile.mastery_vector.get("A", 0) > 0, "mastery A must be rehydrated from history"
        assert profile.mastery_vector.get("B", 0) > 0, "mastery B must be rehydrated from history"
        assert profile.state_migration.get("history_rehydrated") is True

    def test_mastery_zero_when_no_history_and_new_graph(self, monkeypatch):
        """When there's no history at all, mastery is empty after reindex."""
        kv = {
            PERSONALIZED_LEARNER_HISTORY_KV_KEY: json.dumps([]),
            PERSONALIZED_LEARNER_KV_KEY: json.dumps({}),
        }

        monkeypatch.setattr("app.learner_model_service.get_kv", lambda key: kv.get(key))
        monkeypatch.setattr("app.learner_model_service.set_kv", lambda key, val: None)
        monkeypatch.setattr(
            "app.learner_model_service._current_index_context",
            lambda: {"generation_id": "gen-new", "index_version": 2},
        )
        monkeypatch.setattr("app.learner_model_service._active_concept_ids", lambda: {"A", "B"})
        monkeypatch.setattr("app.learner_model_service.get_mastery_vector", lambda uid: {})
        monkeypatch.setattr(
            "app.learner_model_service.get_session_interaction_messages",
            lambda sid, last_n=10: [],
        )

        profile = get_personalized_learner_profile("local")

        non_avg = {k: v for k, v in profile.mastery_vector.items() if k != "avg"}
        assert non_avg == {}, "no concept mastery when history is empty and quiz mastery is empty"
        assert profile.state_migration.get("history_rehydrated") is not True

    def test_no_orphaned_concepts_in_result(self, monkeypatch):
        """Result mastery must not contain concepts absent from active graph (US-8.1 no orphans)."""
        history = [
            _history_row(
                mastery={"A": 0.8, "OBSOLETE": 0.9, "avg": 0.85},
                generation_id="gen-old",
            ),
        ]
        kv = self._mock_kv_factory(history)

        monkeypatch.setattr("app.learner_model_service.get_kv", lambda key: kv.get(key))
        monkeypatch.setattr("app.learner_model_service.set_kv", lambda key, val: None)
        monkeypatch.setattr(
            "app.learner_model_service._current_index_context",
            lambda: {"generation_id": "gen-new", "index_version": 2},
        )
        monkeypatch.setattr(
            "app.learner_model_service._active_concept_ids",
            lambda: {"A"},  # OBSOLETE not in new graph
        )
        monkeypatch.setattr("app.learner_model_service.get_mastery_vector", lambda uid: {})
        monkeypatch.setattr(
            "app.learner_model_service.get_session_interaction_messages",
            lambda sid, last_n=10: [],
        )

        profile = get_personalized_learner_profile("local")

        assert "OBSOLETE" not in profile.mastery_vector, "orphaned concept must be filtered out"
        assert "A" in profile.mastery_vector, "active concept must be present"

    def test_profile_is_stale_when_generation_changed(self, monkeypatch):
        """is_stale is True when snapshot generation_id differs from current."""
        old_snapshot = {
            "index_context": {"generation_id": "gen-old", "index_version": 1},
            "mastery_vector": {"A": 0.7},
        }
        kv = {
            PERSONALIZED_LEARNER_KV_KEY: json.dumps(old_snapshot),
            PERSONALIZED_LEARNER_HISTORY_KV_KEY: json.dumps([]),
        }

        monkeypatch.setattr("app.learner_model_service.get_kv", lambda key: kv.get(key))
        monkeypatch.setattr("app.learner_model_service.set_kv", lambda key, val: None)
        monkeypatch.setattr(
            "app.learner_model_service._current_index_context",
            lambda: {"generation_id": "gen-new", "index_version": 2},
        )
        monkeypatch.setattr("app.learner_model_service._active_concept_ids", lambda: {"A"})
        monkeypatch.setattr("app.learner_model_service.get_mastery_vector", lambda uid: {"A": 0.7})
        monkeypatch.setattr(
            "app.learner_model_service.get_session_interaction_messages",
            lambda sid, last_n=10: [],
        )

        profile = get_personalized_learner_profile("local")

        assert profile.is_stale is True
        assert profile.state_migration.get("index_changed") is True


# ---------------------------------------------------------------------------
# US-8.2 — Badge acceptance criteria
# ---------------------------------------------------------------------------


class TestReindexBadge:
    """US-8.2: badge shown when history_rehydrated=True, contains Russian text + date."""

    def test_badge_shown_when_history_rehydrated(self):
        parts = reindex_profile_badge_parts(
            state_migration={"history_rehydrated": True},
            index_context={"activated_at": "2026-04-20T12:00:00+00:00"},
        )
        assert parts is not None
        title, date_str = parts
        assert title == US_8_2_REINDEX_BADGE_LABEL_RU
        assert "2026" in date_str or "20.04" in date_str

    def test_badge_not_shown_when_not_rehydrated(self):
        parts = reindex_profile_badge_parts(
            state_migration={"history_rehydrated": False, "index_changed": True},
            index_context={"activated_at": "2026-04-20T12:00:00+00:00"},
        )
        assert parts is None

    def test_badge_not_shown_without_state_migration(self):
        parts = reindex_profile_badge_parts(
            state_migration=None,
            index_context={"activated_at": "2026-04-20T12:00:00+00:00"},
        )
        assert parts is None

    def test_badge_uses_activated_at_date(self):
        parts = reindex_profile_badge_parts(
            state_migration={"history_rehydrated": True},
            index_context={"activated_at": "2026-04-15T08:30:00+00:00"},
        )
        assert parts is not None
        _, date_str = parts
        assert "15.04.2026" in date_str or "15.04" in date_str

    def test_badge_falls_back_to_row_timestamp(self):
        """When activated_at is absent, use history_rehydrated_row_timestamp."""
        parts = reindex_profile_badge_parts(
            state_migration={
                "history_rehydrated": True,
                "history_rehydrated_row_timestamp": "2026-04-10T06:00:00+00:00",
            },
            index_context={},  # no activated_at
        )
        assert parts is not None
        _, date_str = parts
        assert "10.04.2026" in date_str or "10.04" in date_str

    def test_badge_date_unknown_when_no_timestamp(self):
        parts = reindex_profile_badge_parts(
            state_migration={"history_rehydrated": True},
            index_context={},
        )
        assert parts is not None
        _, date_str = parts
        assert "не указана" in date_str

    def test_badge_label_is_exact_us_8_2_text(self):
        """Badge text must match the exact wording from US-8.2 acceptance criteria."""
        parts = reindex_profile_badge_parts(
            state_migration={"history_rehydrated": True},
            index_context={"activated_at": "2026-04-20T00:00:00+00:00"},
        )
        assert parts is not None
        title, _ = parts
        assert title == "Профиль обновлён после переиндексации"


# ---------------------------------------------------------------------------
# Lineage sync: apply_index_activation_hooks calls run_learner_state_lineage_sync
# ---------------------------------------------------------------------------


class TestIndexActivationHooks:
    """US-8.1: lineage synchronises on activation (E5.8)."""

    def test_activation_hooks_call_lineage_sync(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            "app.index_lifecycle.run_learner_state_lineage_sync",
            lambda: called.append(True) or {"synced": True},
        )

        from app.index_lifecycle import apply_index_activation_hooks

        result = apply_index_activation_hooks(reset=False)

        assert len(called) == 1, "run_learner_state_lineage_sync must be called on activation"
        assert "learner_state_lineage" in result

    def test_activation_hooks_result_contains_lineage_key(self, monkeypatch):
        monkeypatch.setattr(
            "app.index_lifecycle.run_learner_state_lineage_sync",
            lambda: {"sync_rows": 5},
        )
        monkeypatch.setattr(
            "app.index_lifecycle.get_settings",
            lambda: MagicMock(clear_faq_on_index_activation=False),
        )

        from app.index_lifecycle import apply_index_activation_hooks

        result = apply_index_activation_hooks(reset=True)

        assert result["learner_state_lineage"] == {"sync_rows": 5}


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------


class TestFormatReindexBadgeDate:
    def test_formats_iso_timestamp_correctly(self):
        out = format_reindex_badge_date_display("2026-04-20T12:30:00+00:00")
        assert "20.04.2026" in out
        assert "12:30" in out
        assert "UTC" in out

    def test_returns_unknown_for_none(self):
        out = format_reindex_badge_date_display(None)
        assert out == "не указана"

    def test_returns_unknown_for_empty_string(self):
        out = format_reindex_badge_date_display("")
        assert out == "не указана"
