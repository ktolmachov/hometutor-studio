"""Unified Auto-Loop and scoped quiz helpers."""

import json

from app.models import QueryContext, QueryOptions
from app.ui.quiz_panel import (
    _hint_text_from_explanation,
    _status_for_submission as panel_status_for_submission,
    normalize_feedback_status,
    short_feedback_explanation,
)
from app.ui.scoped_quiz import _cta_route_for_status, _status_for_submission
from app.quiz_service import generate_and_attach_micro_quiz, parse_scoped_quiz_json


def test_parse_scoped_quiz_json_accepts_eight_questions():
    raw = []
    for i in range(8):
        raw.append(
            {
                "question": f"Q{i}?",
                "options": ["a", "b", "c", "d"],
                "correct_index": i % 4,
                "difficulty": "recognition" if i < 3 else ("recall" if i < 6 else "transfer"),
                "explanation": "x",
            }
        )
    qs, err = parse_scoped_quiz_json(json.dumps(raw))
    assert err is None
    assert len(qs) == 8
    assert qs[0]["difficulty"] == "recognition"


def test_generate_and_attach_micro_quiz_offline(monkeypatch):
    monkeypatch.setenv("HOME_RAG_MICRO_QUIZ_OFFLINE", "1")
    ctx = QueryContext(original_question="x", query_options=QueryOptions())
    ctx.metadata["current_topic"] = "test topic"
    ctx.metadata["mastery_level"] = "intermediate"
    out = generate_and_attach_micro_quiz(ctx)
    assert out["show_immediately"] is True
    assert len(out["quiz"]["questions"]) == 1
    assert out["quiz"]["questions"][0].get("question")
    assert "auto_" in (out.get("auto_quiz_id") or "")
    assert "проверк" in out["motivational_message"].lower() or "готов" in out["motivational_message"].lower()


def test_generate_and_attach_micro_quiz_uses_orchestrated_target(monkeypatch):
    monkeypatch.setenv("HOME_RAG_MICRO_QUIZ_OFFLINE", "1")
    ctx = QueryContext(original_question="x", query_options=QueryOptions())
    ctx.metadata["current_topic"] = "fallback topic"
    ctx.metadata["orchestrator_quiz_topic"] = "due topic"
    ctx.metadata["mastery_level"] = "intermediate"
    ctx.metadata["learner_profile"] = {"route": "due_review"}

    out = generate_and_attach_micro_quiz(ctx)

    assert out["target_topic"] == "due topic"
    assert out["route"] == "due_review", "Micro-quiz must preserve due_review route for scenario_04 handoff"
    assert "due_review" in (out["motivational_message"] or "")


def test_feedback_status_normalization_contract():
    assert normalize_feedback_status("correct") == "correct"
    assert normalize_feedback_status("partial") == "partial"
    assert normalize_feedback_status("incorrect") == "incorrect"
    assert normalize_feedback_status("UNKNOWN") == "incorrect"
    assert normalize_feedback_status("") == "incorrect"


def test_feedback_explanation_is_short_and_sanitized():
    blocked = "router debug trace payload"
    out_blocked = short_feedback_explanation(
        blocked,
        fallback="Сверьтесь с разбором и сделайте следующий шаг.",
    )
    assert out_blocked == "Сверьтесь с разбором и сделайте следующий шаг."

    verbose = "Это длинный разбор. Вторая часть не должна попасть в короткую версию."
    out_verbose = short_feedback_explanation(verbose, fallback="fallback")
    assert out_verbose == "Это длинный разбор."


def test_status_to_single_cta_route_mapping_contract():
    assert _cta_route_for_status("correct") == "continue_tutor"
    assert _cta_route_for_status("partial") == "review"
    assert _cta_route_for_status("incorrect") == "retry"
    assert _cta_route_for_status("unexpected") == "retry"


def test_submission_status_supports_partial_branch():
    assert _status_for_submission(is_correct=True, hint_used=False) == "correct"
    assert _status_for_submission(is_correct=False, hint_used=True) == "partial"
    assert _status_for_submission(is_correct=False, hint_used=False) == "incorrect"


def test_quiz_panel_submission_status_contract_with_hint():
    assert panel_status_for_submission(is_correct=True, hint_used=False) == "correct"
    assert panel_status_for_submission(is_correct=True, hint_used=True) == "partial"
    assert panel_status_for_submission(is_correct=False, hint_used=True) == "partial"
    assert panel_status_for_submission(is_correct=False, hint_used=False) == "incorrect"


def test_hint_text_is_non_empty_and_truncated():
    hint = _hint_text_from_explanation(
        "Это подробное объяснение ошибки, которое должно показываться в сокращенном виде для подсказки."
    )
    assert hint
    assert len(hint) <= 143
    assert hint.endswith(("...", ".", "!", "?"))


def test_render_stable_feedback_block_imports_exist():
    """render_stable_feedback_block должен быть публичным API quiz_panel."""
    from app.ui.quiz_panel import (
        normalize_feedback_status,
        render_stable_feedback_block,
        short_feedback_explanation,
    )

    assert callable(render_stable_feedback_block)
    assert callable(normalize_feedback_status)
    assert callable(short_feedback_explanation)


def test_normalize_feedback_status_partial_not_overlaps_correct_incorrect():
    """partial не должен перекрываться с correct/incorrect."""
    from app.ui.quiz_panel import normalize_feedback_status

    assert normalize_feedback_status("partial") not in {"correct", "incorrect"}
    assert normalize_feedback_status("correct") not in {"partial", "incorrect"}
    assert normalize_feedback_status("incorrect") not in {"correct", "partial"}


def test_short_feedback_explanation_no_debug_tokens():
    """Заблокированные токены: router, debug, trace, raw."""
    from app.ui.quiz_panel import short_feedback_explanation

    fallback = "Сверьтесь с разбором."
    for blocked_word in ("router", "debug", "trace", "raw"):
        result = short_feedback_explanation(
            f"This answer goes through {blocked_word} pipeline",
            fallback=fallback,
        )
        assert result == fallback, f"Должен вернуть fallback при слове '{blocked_word}'"


def test_cta_labels_cover_all_allowed_routes():
    """_FEEDBACK_CTA_LABELS должен содержать все 4 разрешённых маршрута."""
    from app.ui.quiz_panel import _FEEDBACK_CTA_LABELS

    required_routes = {"retry", "continue_tutor", "review", "progress"}
    assert required_routes <= set(_FEEDBACK_CTA_LABELS.keys()), (
        f"Отсутствуют маршруты: {required_routes - set(_FEEDBACK_CTA_LABELS.keys())}"
    )


def test_short_explanation_missing_source_returns_fallback():
    """Если explanation пустой — возвращается fallback."""
    from app.ui.quiz_panel import short_feedback_explanation

    fallback = "Попробуйте ещё раз."
    assert short_feedback_explanation(None, fallback=fallback) == fallback
    assert short_feedback_explanation("", fallback=fallback) == fallback
    assert short_feedback_explanation("   ", fallback=fallback) == fallback


def test_cta_route_for_status_covers_all_canonical_statuses():
    """Каждый канонический статус должен давать разрешённый маршрут."""
    from app.ui.scoped_quiz import _cta_route_for_status

    allowed_routes = {"retry", "continue_tutor", "review", "progress"}
    for status in ("correct", "partial", "incorrect"):
        route = _cta_route_for_status(status)
        assert route in allowed_routes, (
            f"Status '{status}' вернул недопустимый маршрут '{route}'"
        )


def test_cta_route_fallback_for_unknown_status():
    """Неизвестный статус должен давать безопасный fallback маршрут."""
    from app.ui.scoped_quiz import _cta_route_for_status

    route = _cta_route_for_status("unknown_status_xyz")
    assert route in {"retry", "continue_tutor", "review", "progress"}
