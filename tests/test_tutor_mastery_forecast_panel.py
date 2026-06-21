"""Unit tests for tutor dashboard caption helpers (E6.5 surfaces)."""

from app.ui.tutor_mastery_forecast_panel import (
    format_stored_orchestration_caption,
    policy_clamp_reason_label_ru,
)


def test_format_stored_orchestration_caption_empty():
    assert format_stored_orchestration_caption(None) is None
    assert format_stored_orchestration_caption({}) is None


def test_format_stored_orchestration_caption_from_pipeline_and_action():
    snap = {
        "recommended_action": "Повторить концепт",
        "tutor_orchestration_pipeline": {
            "phase": "rag_prepare",
            "decision_source": "rule",
            "selected_agent": "ConceptExplainer",
        },
    }
    t = format_stored_orchestration_caption(snap)
    assert t is not None
    assert "подбор контекста" in t
    assert "правило" in t
    assert "📖 Объясняю" in t
    assert "Повторить" in t


def test_format_stored_orchestration_caption_includes_microquiz_and_policy_clamp():
    snap = {
        "recommended_action": "Сделать micro-quiz",
        "tutor_orchestration_pipeline": {
            "phase": "pre_generate",
            "decision_source": "llm",
            "selected_agent": "MicroQuizGenerator",
            "should_trigger_microquiz": True,
            "policy_clamped": True,
            "policy_clamp_reasons": ["due_review_forced_microquiz"],
        },
    }
    t = format_stored_orchestration_caption(snap)
    assert t is not None
    assert "микро-квиз: да" in t
    assert "политика:" in t
    assert "интервальное повторение" in t
    assert "due_review" not in t


def test_policy_clamp_reason_unknown_is_humanized_not_snake_case():
    assert "some_new_reason_code" not in policy_clamp_reason_label_ru("some_new_reason_code")
    assert "some new reason code" in policy_clamp_reason_label_ru("some_new_reason_code")
