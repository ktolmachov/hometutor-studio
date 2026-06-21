"""
US-2.2 + US-13.1 acceptance tests.

US-2.2 — Инкрементальная переиндексация по умолчанию:
  plan_partial_reindex returns use_partial=True when stored hashes match;
  only changed doc_ids appear in dirty_ids; flag enable_partial_reindex=False
  disables partial mode regardless of hash state.

US-13.1 — Quiz адаптируется к моему уровню знаний:
  mastery_label_from_vector_level maps recognition→beginner, recall→intermediate,
  transfer→advanced; choose_micro_quiz_difficulty selects the correct difficulty band
  based on vector mastery level so learners don't get mismatched quiz difficulty.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# US-2.2 — Инкрементальная переиндексация по умолчанию
# ---------------------------------------------------------------------------


class TestIncrementalReindexDefault:
    """US-2.2: partial reindex processes only the delta when existing index present."""

    _EM = "text-embedding-3-small"
    _FP = "fp-v1"

    def _stored(self, hashes: dict) -> dict:
        return {
            "schema_version": 1,
            "embed_model": self._EM,
            "retrieval_fingerprint": self._FP,
            "hashes": hashes,
        }

    def test_partial_reindex_used_when_index_exists(self):
        """US-2.2 core: existing index + unchanged files → use_partial=True."""
        from app.ingestion_content_state import plan_partial_reindex

        current = {"a.md": "hash-a", "b.md": "hash-b"}

        use_partial, unchanged, dirty = plan_partial_reindex(
            reset=False,
            build_to_staging=True,
            enable_partial_reindex=True,
            embed_model=self._EM,
            retrieval_fingerprint=self._FP,
            current_hashes=current,
            stored=self._stored(current),
        )

        assert use_partial is True
        assert "a.md" in unchanged and "b.md" in unchanged
        assert not dirty

    def test_only_new_file_in_dirty_ids(self):
        """US-2.2 core: one new file added → only that file in dirty_ids."""
        from app.ingestion_content_state import plan_partial_reindex

        current = {"existing.md": "hash-x", "new_file.md": "hash-new"}

        use_partial, unchanged, dirty = plan_partial_reindex(
            reset=False,
            build_to_staging=True,
            enable_partial_reindex=True,
            embed_model=self._EM,
            retrieval_fingerprint=self._FP,
            current_hashes=current,
            stored=self._stored({"existing.md": "hash-x"}),
        )

        assert use_partial is True
        assert "new_file.md" in dirty
        assert "existing.md" in unchanged
        assert "existing.md" not in dirty

    def test_changed_file_in_dirty_ids(self):
        """Modified file hash → file appears in dirty, not unchanged."""
        from app.ingestion_content_state import plan_partial_reindex

        _, unchanged, dirty = plan_partial_reindex(
            reset=False,
            build_to_staging=True,
            enable_partial_reindex=True,
            embed_model=self._EM,
            retrieval_fingerprint=self._FP,
            current_hashes={"doc.md": "new-hash"},
            stored=self._stored({"doc.md": "old-hash"}),
        )

        assert "doc.md" in dirty
        assert "doc.md" not in unchanged

    def test_partial_reindex_disabled_triggers_full(self):
        """US-2.2: enable_partial_reindex=False → use_partial=False regardless of hash state."""
        from app.ingestion_content_state import plan_partial_reindex

        current = {"a.md": "hash-a"}
        use_partial, _, _ = plan_partial_reindex(
            reset=False,
            build_to_staging=True,
            enable_partial_reindex=False,
            embed_model=self._EM,
            retrieval_fingerprint=self._FP,
            current_hashes=current,
            stored=self._stored(current),
        )

        assert use_partial is False

    def test_reset_flag_disables_partial(self):
        """reset=True forces full rebuild (safety override)."""
        from app.ingestion_content_state import plan_partial_reindex

        current = {"a.md": "hash-a"}
        use_partial, _, _ = plan_partial_reindex(
            reset=True,
            build_to_staging=True,
            enable_partial_reindex=True,
            embed_model=self._EM,
            retrieval_fingerprint=self._FP,
            current_hashes=current,
            stored=self._stored(current),
        )

        assert use_partial is False

    def test_no_stored_manifest_triggers_full(self):
        """First-time index (no manifest) → use_partial=False."""
        from app.ingestion_content_state import plan_partial_reindex

        use_partial, _, _ = plan_partial_reindex(
            reset=False,
            build_to_staging=True,
            enable_partial_reindex=True,
            embed_model=self._EM,
            retrieval_fingerprint=self._FP,
            current_hashes={"a.md": "hash-a"},
            stored=None,
        )

        assert use_partial is False

    def test_default_config_has_partial_reindex_enabled(self):
        """US-2.2: partial reindex is the default in config."""
        from app.config import get_settings

        settings = get_settings()
        assert settings.enable_partial_reindex is True


# ---------------------------------------------------------------------------
# US-13.1 — Quiz адаптируется к моему уровню знаний
# ---------------------------------------------------------------------------


class TestQuizAdaptsToMasteryLevel:
    """US-13.1: quiz difficulty matches learner's actual mastery level."""

    def test_transfer_mastery_maps_to_advanced(self):
        """US-13.1: mastery level 'transfer' → difficulty band 'advanced'."""
        from app.quiz_adaptive import mastery_label_from_vector_level

        assert mastery_label_from_vector_level("transfer") == "advanced"

    def test_recognition_mastery_maps_to_beginner(self):
        """US-13.1: mastery level 'recognition' → difficulty band 'beginner'."""
        from app.quiz_adaptive import mastery_label_from_vector_level

        assert mastery_label_from_vector_level("recognition") == "beginner"

    def test_recall_mastery_maps_to_intermediate(self):
        from app.quiz_adaptive import mastery_label_from_vector_level

        assert mastery_label_from_vector_level("recall") == "intermediate"

    def test_none_mastery_returns_none(self):
        from app.quiz_adaptive import mastery_label_from_vector_level

        assert mastery_label_from_vector_level(None) is None

    def test_transfer_vector_level_selects_hard_band(self):
        """US-13.1: choose_micro_quiz_difficulty with transfer level → hard band."""
        from app.quiz_adaptive import choose_micro_quiz_difficulty

        band = choose_micro_quiz_difficulty("intermediate", [], vector_level="transfer")
        assert band == "hard"

    def test_recognition_vector_level_selects_easy_band(self):
        """US-13.1: recognition level → easy band (no overload)."""
        from app.quiz_adaptive import choose_micro_quiz_difficulty

        band = choose_micro_quiz_difficulty("intermediate", [], vector_level="recognition")
        assert band == "easy"

    def test_recall_vector_level_selects_medium_band(self):
        from app.quiz_adaptive import choose_micro_quiz_difficulty

        band = choose_micro_quiz_difficulty("intermediate", [], vector_level="recall")
        assert band == "medium"

    def test_vector_level_overrides_tutor_advanced(self):
        """Mastery vector takes priority over tutor profile (avoids false «advanced» quizzes)."""
        from app.quiz_adaptive import choose_micro_quiz_difficulty

        band = choose_micro_quiz_difficulty("advanced", [], vector_level="recognition")
        assert band == "easy"

    def test_all_three_levels_produce_distinct_bands(self):
        """Monotonicity: recognition < recall < transfer maps to easy < medium < hard."""
        from app.quiz_adaptive import choose_micro_quiz_difficulty

        bands = {
            level: choose_micro_quiz_difficulty("intermediate", [], vector_level=level)
            for level in ("recognition", "recall", "transfer")
        }
        assert bands["recognition"] == "easy"
        assert bands["recall"] == "medium"
        assert bands["transfer"] == "hard"
