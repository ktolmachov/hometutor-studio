"""Rule-based оценка multiple_choice в evaluate_inline_quiz_answer (без LLM)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import app.quiz_service as quiz_service


@pytest.fixture
def _no_side_effects(monkeypatch):
    monkeypatch.setattr("app.user_state.save_quiz_result", lambda **kw: 1)
    monkeypatch.setattr(
        "app.spaced_repetition.update_spaced_repetition",
        lambda concept, quality, **kw: {"concept": concept, "quality": quality},
    )
    monkeypatch.setattr(
        "app.quiz_adaptive.update_mastery_after_score",
        lambda concept, score, **kw: {"concept": concept, "score": score},
    )


def test_mc_evaluate_skips_llm_when_correct_index(_no_side_effects, monkeypatch):
    llm = MagicMock()
    monkeypatch.setattr(quiz_service, "get_evaluate_llm", lambda: llm)

    q = {
        "type": "multiple_choice",
        "question": "2+2?",
        "concept": "arith",
        "difficulty": "recall",
        "correct_index": 1,
    }
    out = quiz_service.evaluate_inline_quiz_answer(q, "B")
    assert out["score"] == 1.0
    llm.complete.assert_not_called()


def test_mc_wrong_choice_no_llm(_no_side_effects, monkeypatch):
    llm = MagicMock()
    monkeypatch.setattr(quiz_service, "get_evaluate_llm", lambda: llm)

    q = {
        "type": "multiple_choice",
        "question": "2+2?",
        "concept": "arith",
        "difficulty": "recall",
        "correct_index": 0,
    }
    out = quiz_service.evaluate_inline_quiz_answer(q, "1")
    assert out["score"] == 0.0
    llm.complete.assert_not_called()


def test_short_answer_calls_evaluate_llm(_no_side_effects, monkeypatch):
    llm = MagicMock()

    class _Resp:
        text = "0.8"

    llm.complete = MagicMock(return_value=_Resp())
    monkeypatch.setattr(quiz_service, "get_evaluate_llm", lambda: llm)

    q = {
        "type": "short_answer",
        "question": "Что такое RAG?",
        "concept": "rag",
        "difficulty": "recall",
    }
    out = quiz_service.evaluate_inline_quiz_answer(q, "retrieval augmented generation")
    assert out["score"] == pytest.approx(0.8)
    llm.complete.assert_called_once()


def test_mc_missing_correct_key_falls_back_to_llm(_no_side_effects, monkeypatch):
    llm = MagicMock()

    class _Resp:
        text = "0.5"

    llm.complete = MagicMock(return_value=_Resp())
    monkeypatch.setattr(quiz_service, "get_evaluate_llm", lambda: llm)

    q = {
        "type": "multiple_choice",
        "question": "x?",
        "concept": "x",
        "difficulty": "recall",
    }
    out = quiz_service.evaluate_inline_quiz_answer(q, "A")
    assert out["score"] == pytest.approx(0.5)
    llm.complete.assert_called_once()
