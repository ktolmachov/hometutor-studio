"""E9.7 Continuity & learn bridge: стабильные строки и session preview metadata."""

from app.ui.continuity_bridge import (
    ask_failure_recovery_hint_ru,
    build_qa_tutor_handoff_context,
    clear_qa_tutor_handoff_context,
    due_reviews_home_teaser_ru,
    home_continue_priority_lines_ru,
    load_qa_tutor_handoff_context,
    continuity_next_step_line_ru,
    qa_to_tutor_bridge_caption_ru,
    store_qa_tutor_handoff_context,
    tutor_reason_line_ru,
)
from app.ui.helpers import ask_failure_recovery_hint_from_exception, format_request_error


def test_home_continue_priority_prefers_resume_when_tutor_and_due():
    m, s = home_continue_priority_lines_ru(
        due_n=5, tutor_topic="RAG", has_last_qa=True, has_reading=True
    )
    assert "тьютор" in m.lower() or "диалог" in m.lower()
    assert s and "очеред" in s.lower()


def test_home_continue_tutor_when_no_due():
    m, _s = home_continue_priority_lines_ru(
        due_n=0, tutor_topic="Graph", has_last_qa=False, has_reading=False
    )
    assert "тьютор" in m.lower() or "диалог" in m.lower()


def test_home_continue_qa_when_only_qa():
    m, _s = home_continue_priority_lines_ru(
        due_n=0, tutor_topic=None, has_last_qa=True, has_reading=False
    )
    assert "ответ" in m.lower() or "баз" in m.lower()


def test_due_teaser_none_when_empty():
    assert due_reviews_home_teaser_ru(0) is None
    assert "повтор" in (due_reviews_home_teaser_ru(3) or "").lower()


def test_qa_to_tutor_bridge_caption_stable():
    t = qa_to_tutor_bridge_caption_ru()
    assert "черновик" in t.lower()
    assert "тьютор" in t.lower()


def test_ask_failure_recovery_hint_timeout():
    h = ask_failure_recovery_hint_ru("ReadTimeout: connection timed out")
    assert "таймаут" in h.lower() or "сузьте" in h.lower()


def test_ask_failure_recovery_hint_api_key():
    h = ask_failure_recovery_hint_ru("Error 401 Unauthorized")
    assert "api" in h.lower() or "ключ" in h.lower()


def test_ask_failure_recovery_from_exception_uses_format_request_error():
    class _Resp:
        def json(self):
            return {"detail": "timeout waiting for peer"}

    err = Exception("fail")
    err.response = _Resp()  # type: ignore[attr-defined]

    hint = ask_failure_recovery_hint_from_exception(err)
    assert len(hint) > 10
    assert format_request_error(err) == "timeout waiting for peer"


def test_store_and_load_handoff_context_valid_payload():
    state: dict[str, object] = {}
    ok = store_qa_tutor_handoff_context(
        state,
        topic="Hybrid Retrieval",
        last_question="Как работает reranking в гибридном поиске?",
        answer_summary="Коротко: sparse+dense, затем rerank.",
        created_at="2026-04-20T09:00:00+00:00",
    )
    assert ok is True
    payload = load_qa_tutor_handoff_context(state)
    assert payload is not None
    assert payload["topic"] == "Hybrid Retrieval"
    assert payload["last_question"].startswith("Как работает reranking")
    assert payload["answer_summary"].startswith("Коротко:")


def test_build_handoff_context_normalizes_partial_payload():
    payload = build_qa_tutor_handoff_context(
        topic="  ",
        last_question="  Объясни backoff retries  ",
        answer_summary=None,
    )
    assert payload is not None
    assert payload["topic"].startswith("Объясни")
    assert payload["last_question"] == "Объясни backoff retries"


def test_store_handoff_context_rejects_empty_question():
    state: dict[str, object] = {}
    ok = store_qa_tutor_handoff_context(
        state,
        topic="RAG",
        last_question="   ",
        answer_summary="что-то",
    )
    assert ok is False
    assert load_qa_tutor_handoff_context(state) is None


def test_handoff_summary_is_compacted_stably():
    long_summary = "a" * 700
    payload = build_qa_tutor_handoff_context(
        topic="Topic",
        last_question="Q",
        answer_summary=long_summary,
    )
    assert payload is not None
    assert len(payload["answer_summary"]) <= 500
    assert payload["answer_summary"].endswith("…")


def test_clear_handoff_context_removes_payload():
    state: dict[str, object] = {}
    store_qa_tutor_handoff_context(state, topic="RAG", last_question="Что это?")
    assert load_qa_tutor_handoff_context(state) is not None
    clear_qa_tutor_handoff_context(state)
    assert load_qa_tutor_handoff_context(state) is None


def test_load_handoff_context_rejects_non_dict_payload():
    state: dict[str, object] = {"qa_tutor_handoff_context": "broken"}  # type: ignore[dict-item]
    assert load_qa_tutor_handoff_context(state) is None


def test_tutor_reason_line_prefers_review_reasons():
    line = tutor_reason_line_ru(policy_clamp_reasons=["due_review_priority"])
    assert "повторение" in line.lower()


def test_tutor_reason_line_fallbacks_to_decision_action():
    line = tutor_reason_line_ru(tutor_decision={"action": {"next_action": "quiz"}})
    assert "проверка" in line.lower()


def test_continuity_next_step_line_matches_reason():
    line = continuity_next_step_line_ru(
        topic="RAG",
        policy_clamp_reasons=["quiz_emphasis"],
    )
    assert "следующий шаг" in line.lower()
    assert "провер" in line.lower()


def test_continuity_next_step_line_is_deterministic_for_same_inputs():
    a = continuity_next_step_line_ru(
        topic="RAG",
        policy_clamp_reasons=["quiz_emphasis"],
    )
    b = continuity_next_step_line_ru(
        topic="RAG",
        policy_clamp_reasons=["quiz_emphasis"],
    )
    assert a == b
