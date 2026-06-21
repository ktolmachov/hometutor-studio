"""E24-A sp2: pure helpers for tutor goal copy (no Streamlit)."""

from app.ui.session_state import goal_snapshot_context_to_session_patch
from app.ui.continuity_bridge import (
    e24_active_goal_line_ru,
    e24_five_min_closure_combined_ru,
    e24_goal_closure_goal_phrase_ru,
)


def test_e24_goal_closure_phrase_prefers_outcome():
    s = e24_goal_closure_goal_phrase_ru(desired_outcome="разобрать X", topic="Y")
    assert s and "разобрать" in s.lower()


def test_e24_goal_closure_phrase_truncates_long_outcome():
    long_o = "а" * 200
    s = e24_goal_closure_goal_phrase_ru(desired_outcome=long_o, topic=None)
    assert s and len(s) < 250


def test_e24_active_goal_line_none_when_empty():
    assert (
        e24_active_goal_line_ru(
            current_topic=None,
            tutor_goal_desired_outcome=None,
            tutor_goal_subtopic=None,
            tutor_goal_target_level=None,
            tutor_goal_time_budget_min=None,
        )
        is None
    )


def test_e24_active_goal_line_with_outcome_and_budget():
    t = e24_active_goal_line_ru(
        current_topic="ignored",
        tutor_goal_desired_outcome="Освоить retrieval",
        tutor_goal_subtopic=None,
        tutor_goal_target_level="recall",
        tutor_goal_time_budget_min=5,
    )
    assert t and "Сейчас" in t
    assert "5" in t
    assert "recall" in t


def test_e24_active_goal_line_falls_back_to_topic():
    t = e24_active_goal_line_ru(
        current_topic="Graph",
        tutor_goal_desired_outcome=None,
        tutor_goal_subtopic=None,
        tutor_goal_target_level=None,
        tutor_goal_time_budget_min=None,
    )
    assert t and "Graph" in t


def test_goal_snapshot_context_to_session_patch_maps_goal_context():
    p = goal_snapshot_context_to_session_patch(
        {
            "topic": "algebra",
            "subtopic": "lin",
            "target_level": "recall",
            "desired_outcome": "x",
            "time_budget_min": 10,
            "learning_goal": "exam_prep",
        }
    )
    assert p["tutor_goal_subtopic"] == "lin"
    assert p["tutor_goal_target_level"] == "recall"
    assert p["tutor_goal_desired_outcome"] == "x"
    assert p["tutor_goal_time_budget_min"] == 10
    assert p["learning_goal"] == "exam_prep"
    assert p["current_topic"] == "algebra"


def test_goal_snapshot_context_skips_general_topic():
    p = goal_snapshot_context_to_session_patch({"topic": "general", "subtopic": "s"})
    assert "current_topic" not in p
    assert p["tutor_goal_subtopic"] == "s"


def test_e24_closure_combined_extends_e11():
    snap = {"targets": {"quizzes": 5}, "done": {"quizzes": 1}}
    base = e24_five_min_closure_combined_ru(snap, tutor_goal_desired_outcome=None, current_topic=None)
    rich = e24_five_min_closure_combined_ru(
        snap,
        tutor_goal_desired_outcome="закрепить тему",
        current_topic="RAG",
    )
    assert len(rich) > len(base)
    assert "закрепить" in rich
