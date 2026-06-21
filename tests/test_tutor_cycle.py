"""Итерации 19.3–19.5: tutor cycle state и diagnostic mapping."""

from app.quiz_service import process_micro_quiz_outcome
from app.tutor_cycle import (
    build_tutor_cycle_state,
    compute_default_next_step,
    map_quiz_outcome_to_diagnostic,
)


def test_map_quiz_outcome_to_diagnostic_correct_recognition():
    assert map_quiz_outcome_to_diagnostic(is_correct=True, question_type="recognition") == "recognized"


def test_map_quiz_outcome_to_diagnostic_correct_recall():
    assert map_quiz_outcome_to_diagnostic(is_correct=True, question_type="recall") == "recalled"


def test_map_quiz_outcome_to_diagnostic_incorrect_application():
    assert map_quiz_outcome_to_diagnostic(is_correct=False, question_type="application") == "cannot_apply"


def test_map_quiz_outcome_to_diagnostic_incorrect_recognition():
    assert map_quiz_outcome_to_diagnostic(is_correct=False, question_type="recognition") == "misconception"


def test_compute_default_next_step_priority_due():
    assert compute_default_next_step(due_reviews_count=2, auto_quiz_attached=True) == "due_review_first"


def test_compute_default_next_step_micro_quiz():
    assert compute_default_next_step(due_reviews_count=0, auto_quiz_attached=True) == "micro_quiz_first"


def test_build_tutor_cycle_state_has_session_and_phase():
    tc = build_tutor_cycle_state(
        session_id="s1",
        due_reviews_count=0,
        auto_quiz_payload={"quiz": {"questions": [{"q": 1}]}, "show_immediately": True},
        tutor_answer_contract={"next_action": "continue", "next_action_reason": "ok"},
    )
    assert tc["session_id"] == "s1"
    assert tc["phase"] == "micro_quiz_offered"
    assert tc["default_next_step"] == "micro_quiz_first"
    assert tc["recommended_next_action"] == "continue"


def test_process_micro_quiz_outcome_includes_diagnostic_status(monkeypatch):
    q = {
        "question": "Q?",
        "options": ["a", "b", "c", "d"],
        "correct_index": 0,
        "type": "recognition",
        "correct_option": "A",
    }
    out = process_micro_quiz_outcome(
        q,
        "A",
        current_topic="t",
        current_mastery="intermediate",
        session_id=None,
    )
    assert out.get("diagnostic_feedback_status") == "recognized"
