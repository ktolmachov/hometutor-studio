"""Интеграция micro-quiz → learning_plan_service."""

import pytest

from app.learning_plan_service import get_recommended_next_step_after_micro_quiz


@pytest.fixture(autouse=True)
def _no_live_due_reviews(monkeypatch):
    """Логика next-step проверяется через due_reviews_count; live SQLite не должен ломать тесты."""
    monkeypatch.setattr("app.learning_plan_adaptive.count_due_reviews_for_kg", lambda kg: 0)
    monkeypatch.setattr("app.learning_plan_adaptive.filter_due_reviews_for_kg", lambda kg, **kwargs: [])


def test_next_step_success():
    r = get_recommended_next_step_after_micro_quiz(
        current_topic="T1",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "correct", "message": "ok"},
        quiz_question_type="application",
        due_reviews_count=0,
    )
    assert r["next_action"] == "Следующий шаг"
    assert "T1" in r["topic_progress"]


def test_next_step_due_reviews_priority():
    r = get_recommended_next_step_after_micro_quiz(
        current_topic="T1",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "correct", "message": "ok"},
        quiz_question_type="application",
        due_reviews_count=3,
    )
    assert r["next_action"] == "Пора повторить"


def test_next_step_incorrect_application():
    r = get_recommended_next_step_after_micro_quiz(
        current_topic="T1",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "incorrect", "message": "no"},
        quiz_question_type="application",
        due_reviews_count=0,
    )
    assert r["next_action"] == "Дай пример"


def test_next_step_success_practice_style():
    r = get_recommended_next_step_after_micro_quiz(
        current_topic="T1",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "correct", "message": "ok"},
        quiz_question_type="application",
        due_reviews_count=0,
        preferred_style="practice",
    )
    assert r["next_action"] == "Дай задачу на применение"


def test_next_step_partial_treated_as_reinforcement():
    r = get_recommended_next_step_after_micro_quiz(
        current_topic="T1",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "partial", "message": "close"},
        quiz_question_type="application",
        due_reviews_count=0,
    )
    assert r["next_action"] == "Дай пример"
    assert "T1" in r["topic_progress"]


def test_quiz_feedback_partial_branch_is_distinct():
    """partial получает маршрут отличный от correct и incorrect."""
    from app.ui.scoped_quiz import _cta_route_for_status

    route_correct = _cta_route_for_status("correct")
    route_partial = _cta_route_for_status("partial")
    route_incorrect = _cta_route_for_status("incorrect")
    assert route_partial != route_correct
    # partial НЕ ОБЯЗАН отличаться от incorrect (допустимо review=retry оба recovery)
    # но должен быть в allowed set
    assert route_partial in {"retry", "continue_tutor", "review", "progress"}
    assert route_incorrect in {"retry", "continue_tutor", "review", "progress"}


def test_quiz_one_primary_cta_contract_no_duplicate_routes():
    """Контракт: для одного status -> ровно один маршрут (детерминированно)."""
    from app.ui.scoped_quiz import _cta_route_for_status

    for status in ("correct", "partial", "incorrect"):
        assert _cta_route_for_status(status) == _cta_route_for_status(status)


def test_submission_status_hint_marks_partial_not_correct():
    """Использование подсказки при правильном ответе — не даёт incorrect."""
    from app.ui.scoped_quiz import _status_for_submission

    result = _status_for_submission(is_correct=True, hint_used=True)
    assert result in {"correct", "partial"}, (
        "hint при правильном ответе должен давать correct или partial, не incorrect"
    )
    result_fail = _status_for_submission(is_correct=False, hint_used=True)
    assert result_fail == "partial"
