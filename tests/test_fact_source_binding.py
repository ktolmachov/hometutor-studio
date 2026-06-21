"""Contract tests for fact-source-binding-v1."""

from __future__ import annotations

import pytest

from app.config import get_settings, reset_settings_cache
from app.fact_source_binding import (
    FactSourceBindingError,
    FactSourceProvenance,
    apply_quiz_outcome_to_learner_state,
    build_quiz_event_provenance,
    is_influencing_provenance_line,
    provenance_to_evidence_line,
    require_fact_provenance,
)
from app.quiz_adaptive import update_mastery_after_score
from app.spaced_repetition import update_spaced_repetition


@pytest.fixture
def binding_enabled(monkeypatch):
    monkeypatch.setenv("FACT_SOURCE_BINDING_ENABLED", "true")
    reset_settings_cache()
    yield
    monkeypatch.setenv("FACT_SOURCE_BINDING_ENABLED", "false")
    reset_settings_cache()


def test_require_fact_provenance_rejects_missing_when_enabled(binding_enabled):
    with pytest.raises(FactSourceBindingError, match="missing provenance"):
        require_fact_provenance(None, operation="test")


def test_require_fact_provenance_accepts_quiz_result(binding_enabled):
    prov = build_quiz_event_provenance(quiz_result_id=7, concept="RAG", level="recall")
    validated = require_fact_provenance(prov, operation="test")
    assert validated.event_id == "7"


def test_quiz_result_requires_event_id(binding_enabled):
    with pytest.raises(FactSourceBindingError, match="event_id"):
        require_fact_provenance(
            FactSourceProvenance(source_type="quiz_result"),
            operation="test",
        )


def test_update_mastery_rejects_without_provenance(binding_enabled):
    with pytest.raises(FactSourceBindingError):
        update_mastery_after_score("BindingTopic", 1.0)


def test_update_spaced_repetition_rejects_without_provenance(binding_enabled):
    with pytest.raises(FactSourceBindingError):
        update_spaced_repetition("BindingTopic", 5)


def test_apply_quiz_outcome_writes_with_provenance(binding_enabled):
    from app.user_state import save_quiz_result

    row_id = save_quiz_result(concept="BindA", level="recall", score=1.0)
    outcome = apply_quiz_outcome_to_learner_state(
        concept="BindA",
        score=1.0,
        level="recall",
        quiz_result_id=row_id,
    )
    assert outcome["provenance"]["source_type"] == "quiz_result"
    assert outcome["provenance"]["event_id"] == str(row_id)
    assert outcome["quiz_adaptive"]["provenance"]["event_id"] == str(row_id)


def test_kill_switch_allows_legacy_writes(monkeypatch):
    monkeypatch.setenv("FACT_SOURCE_BINDING_ENABLED", "false")
    reset_settings_cache()
    result = update_mastery_after_score("LegacyTopic", 1.0)
    assert result["concept"] == "LegacyTopic"


def test_provenance_to_evidence_line_and_influencing():
    prov = build_quiz_event_provenance(quiz_result_id=42, concept="X", level="recall")
    line = provenance_to_evidence_line(prov)
    assert line is not None
    assert "quiz_result #42" in line
    assert is_influencing_provenance_line(line) is True


def test_binding_disabled_by_default_in_test_env():
    assert get_settings().fact_source_binding_enabled is False
