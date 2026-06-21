"""E11-D / US-14.4: контракт 5-минутного цикла (offline, без Streamlit/LLM)."""

from __future__ import annotations

import importlib
import pytest

from app.learning_plan_service import get_recommended_next_step_after_micro_quiz
from app.quiz_service import process_micro_quiz_outcome
from app.ui.quiz_panel import _cta_route_for_status
from app.ui.scoped_quiz import _completion_cta_route, _record_loop_transition, _status_for_submission
from app.ui.continuity_bridge import (
    e11_five_min_closure_hint_ru,
    last_assistant_message_index,
    qa_five_min_tutor_bridge_caption_ru,
)


class _Msg:
    __slots__ = ("role",)

    def __init__(self, role: str) -> None:
        self.role = role


def test_last_assistant_message_index_finds_last_assistant():
    msgs = [_Msg("user"), _Msg("assistant"), _Msg("user"), _Msg("assistant")]
    assert last_assistant_message_index(msgs) == 3


def test_last_assistant_message_index_fallback_empty():
    assert last_assistant_message_index([]) == 0


def test_qa_five_min_bridge_caption_non_empty():
    t = qa_five_min_tutor_bridge_caption_ru()
    assert "мини-провер" in t.lower() or "микро" in t.lower()


def test_e11_closure_hint_when_weekly_quiz_goal_met():
    text = e11_five_min_closure_hint_ru(
        {
            "targets": {"quizzes": 1, "reviews": 3, "new_topics": 2},
            "done": {"quizzes": 2, "reviews": 0, "new_topics": 0},
        }
    )
    assert "готово" in text.lower()


def test_e11_closure_hint_when_weekly_quiz_goal_not_met():
    text = e11_five_min_closure_hint_ru(
        {
            "targets": {"quizzes": 5, "reviews": 3, "new_topics": 2},
            "done": {"quizzes": 1, "reviews": 0, "new_topics": 0},
        }
    )
    assert "следующий шаг" in text.lower() or "пауз" in text.lower()


@pytest.fixture(autouse=True)
def _no_live_due_reviews(monkeypatch):
    monkeypatch.setattr("app.learning_plan_adaptive.count_due_reviews_for_kg", lambda kg: 0)
    monkeypatch.setattr("app.learning_plan_adaptive.filter_due_reviews_for_kg", lambda kg, **kwargs: [])


def test_five_min_micro_quiz_loop_contract_progress_and_next_step(monkeypatch):
    """После ответа на мини-квиз: сигнал прогресса (retention_line) + рекомендация шага."""
    q = {
        "question": "Q?",
        "options": ["a", "b", "c", "d"],
        "correct_index": 1,
        "type": "application",
    }
    out = process_micro_quiz_outcome(
        q,
        "B",
        current_topic="TopicA",
        current_mastery="intermediate",
        session_id=None,
    )
    assert out.get("quiz_feedback", {}).get("status") == "correct"
    assert out.get("retention_line")
    rn = out.get("recommended_next") or {}
    assert rn.get("next_action")
    assert "TopicA" in str(rn.get("topic_progress") or "")

    r2 = get_recommended_next_step_after_micro_quiz(
        current_topic="TopicA",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "correct", "message": "ok"},
        quiz_question_type="application",
        due_reviews_count=0,
    )
    assert r2.get("next_action")


def test_five_min_micro_quiz_incorrect_still_has_next_step():
    q = {
        "question": "Q?",
        "options": ["a", "b", "c", "d"],
        "correct_index": 0,
        "type": "application",
    }
    out = process_micro_quiz_outcome(
        q,
        "B",
        current_topic="TopicB",
        current_mastery="intermediate",
        session_id=None,
    )
    assert out.get("quiz_feedback", {}).get("status") == "incorrect"
    rn = out.get("recommended_next") or {}
    assert rn.get("next_action")


@pytest.mark.parametrize("status", ["correct", "partial", "incorrect"])
def test_five_min_micro_quiz_statuses_always_have_next_step(status: str):
    out = get_recommended_next_step_after_micro_quiz(
        current_topic="TopicC",
        mastery_level="intermediate",
        last_quiz_feedback={"status": status, "message": "ok"},
        quiz_question_type="application",
        due_reviews_count=0,
    )
    assert out.get("next_action")


@pytest.mark.parametrize(
    ("status", "expected_route"),
    [("correct", "continue_tutor"), ("partial", "review"), ("incorrect", "retry")],
)
def test_quiz_feedback_status_maps_to_deterministic_cta(status: str, expected_route: str):
    assert _cta_route_for_status(status) == expected_route


def test_scoped_quiz_submission_status_contract():
    assert _status_for_submission(is_correct=True, hint_used=False) == "correct"
    assert _status_for_submission(is_correct=False, hint_used=True) == "partial"
    assert _status_for_submission(is_correct=False, hint_used=False) == "incorrect"


@pytest.mark.parametrize(
    ("pct", "expected_route"),
    [(90, "progress"), (60, "review"), (10, "retry")],
)
def test_scoped_completion_route_is_deterministic(pct: int, expected_route: str):
    assert _completion_cta_route(pct=pct) == expected_route


def test_record_loop_transition_emits_dead_end_safe_metric(monkeypatch):
    captured: list[dict] = []

    def _fake_record_knowledge_workflow_event(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr("app.metrics.record_knowledge_workflow_event", _fake_record_knowledge_workflow_event)
    _record_loop_transition(
        source_key="quiz_topic",
        stage="completion",
        route="review",
        status="partial",
        payload={"primary_cta_count": 1},
    )

    assert len(captured) == 1
    payload = captured[0]
    assert payload.get("action") == "learning_loop.next_step"
    trace = payload.get("knowledge_product_trace") or {}
    assert trace.get("deterministic_next_step") is True
    assert trace.get("dead_end") is False
    event_payload = payload.get("payload") or {}
    assert event_payload.get("stage") == "completion"
    assert event_payload.get("route") == "review"
    assert event_payload.get("primary_cta_count") == 1


def test_loop_runtime_metrics_gate_contract(tmp_path):
    metrics = importlib.reload(__import__("app.metrics", fromlist=["*"]))
    metrics.METRICS_STORE_PATH = tmp_path / "metrics_loop_gate.jsonl"

    _record_loop_transition(
        source_key="topic_a",
        stage="question_feedback",
        route="review",
        status="partial",
        payload={"question_idx": 0},
    )
    _record_loop_transition(
        source_key="topic_a",
        stage="completion",
        route="progress",
        status="correct",
        payload={"primary_cta_count": 1, "submitted_count": 5, "total": 5},
    )

    store = metrics.get_metrics_store(limit=20)
    items = [i for i in store.get("items", []) if i.get("action") == "learning_loop.next_step"]
    assert items, "loop metric events must be present"

    for event in items:
        trace = event.get("knowledge_product_trace") or {}
        payload = event.get("payload") or {}
        assert trace.get("deterministic_next_step") is True
        assert trace.get("dead_end") is False
        assert str(payload.get("route") or "").strip()

    completion_events = [e for e in items if (e.get("payload") or {}).get("stage") == "completion"]
    assert completion_events, "at least one completion metric is required"
    assert all((e.get("payload") or {}).get("primary_cta_count") == 1 for e in completion_events)
