"""
Регрессия multi-turn / tutor: session store, condense, knowledge_graph, answer_question.

Контракты: ``answer_question`` → dict; ``QueryOptions.query_mode``; ``run_pipeline`` в
``pipeline_runner``; condense при ``len(history) < 3`` не трогает ``condensed_question``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.condense_step import condense_step
from app.knowledge_graph import JsonKnowledgeGraph
from app.models import Message, QueryContext, QueryOptions
from app.session_store import SessionStore


@pytest.fixture
def test_session(tmp_path):
    """Изолированный SessionStore на tmp_path."""
    sid = "test_multi_turn_123"
    store = SessionStore(db_path=tmp_path / "sessions.db")
    store.delete(sid)
    yield store, sid
    store.delete(sid)


def test_session_store_persistence(test_session):
    store, session_id = test_session
    messages = [
        Message(role="user", content="Что такое RAG?"),
        Message(role="assistant", content="Retrieval-Augmented Generation"),
    ]
    store.save(session_id, messages)
    loaded = store.get(session_id)
    assert len(loaded) == 2
    assert loaded[0].content == "Что такое RAG?"
    assert loaded[1].role == "assistant"


def test_condense_step_short_history(test_session):
    store, session_id = test_session
    ctx = QueryContext(
        original_question="Что дальше?",
        session_id=session_id,
        conversation_history=[Message(role="user", content="Привет")],
    )
    result = condense_step(ctx)
    assert result.trace["condense"] == "skipped_too_short"
    assert result.condensed_question is None
    assert result.rewritten_query is None
    assert result.effective_query == "Что дальше?"


@patch("app.condense_step.get_llm")
def test_condense_step_success(mock_get_llm, test_session):
    store, session_id = test_session
    resp = MagicMock()
    resp.text = "Пользователь спрашивал про RAG и теперь хочет узнать про multi-turn."
    mock_get_llm.return_value.complete.return_value = resp

    ctx = QueryContext(
        original_question="Как это работает в чате?",
        session_id=session_id,
        conversation_history=[
            Message(role="user", content="Что такое RAG?"),
            Message(role="assistant", content="..."),
            Message(role="user", content="А как в чате?"),
        ],
    )
    result = condense_step(ctx)
    assert result.trace["condense"] == "success"
    assert result.condensed_question == resp.text.strip()
    assert result.rewritten_query is None


def test_tutor_mode_next_action(tmp_path):
    """Граф в отдельном файле — без загрязнения глобального concept_graph.json."""
    path = tmp_path / "kg.json"
    kg = JsonKnowledgeGraph(path)
    kg.add_concept("RAG", "Retrieval-Augmented Generation", ["Embedding"])
    kg.add_concept("MultiTurn", "Многошаговые диалоги", ["RAG"])

    action = kg.next_best_action("RAG", ["Embedding"])
    assert action["action"] == "next_concept"
    assert action["concept"] == "MultiTurn"


def test_prerequisites_check(tmp_path):
    path = tmp_path / "kg2.json"
    kg = JsonKnowledgeGraph(path)
    kg.add_concept("MultiTurn", "x", ["RAG"])
    ok, missing = kg.check_prerequisites("MultiTurn", ["Embedding"])
    assert ok is False
    assert "RAG" in missing


def test_answer_question_tutor_debug(monkeypatch, test_session):
    """Полный путь answer_question с моком движка: dict + tutor debug."""
    import app.query_service as query_service
    from conftest import patch_faq_cache_enabled

    patch_faq_cache_enabled(monkeypatch)

    _, session_id = test_session

    class _FakeResponse:
        def __init__(self) -> None:
            self.source_nodes = [
                type(
                    "Node",
                    (),
                    {
                        "metadata": {
                            "file_name": "t.txt",
                            "relative_path": "data/t.txt",
                            "page_label": "1",
                        },
                        "score": 0.85,
                        "text": "chunk",
                    },
                )()
            ]
            self.usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        def __str__(self) -> str:
            return "Развёрнутый ответ про RAG для теста multi-turn."

    class _FakeEngine:
        def query(self, question: str):
            return _FakeResponse()

    def _fake_build(q, options, **kwargs):
        return {
            "engine": _FakeEngine(),
            "cache_hit": False,
            "engine_cache_lookup_ms": 0.1,
            "pipeline_params": {
                "query_type": "qa",
                "retrieval_mode": "vector_only",
                "similarity_top_k": 4,
                "enable_reranker": False,
                "rerank_top_n": 4,
                "homework_mode": options.homework_mode,
                "assistance_level": options.assistance_level,
                "query_engine_cache_policy": "disabled_for_session",
            },
        }

    monkeypatch.setattr(query_service, "build_query_engine", _fake_build)

    opts = QueryOptions(session_id=session_id, query_mode="tutor")
    result = query_service.answer_question("Объясни RAG", opts)
    assert result["debug"].get("session_id") == session_id
    assert result["debug"].get("query_engine_cache_policy") == "disabled_for_session"
    # FAQ: при включённом кэше причина пропуска зависит от порядка политики (non_qa для keyword и т.д.).
    assert result["debug"].get("faq_cache_skip_reason") in ("session_id", "non_qa")
    assert "tutor_next_best_action" in result["debug"]


def test_get_tutor_prompt_smoke():
    from app.tutor_prompts import get_tutor_prompt

    s = get_tutor_prompt("RAG", "ctx", "hist", "Вопрос?")
    assert "RAG" in s and "Вопрос?" in s


def test_multi_turn_two_turns_persist_same_session(monkeypatch, tmp_path):
    """Регрессия: два вызова answer_question с одним session_id накапливают историю."""
    import importlib

    import app.query_service as query_service
    from app.session_store import SessionStore

    isolated = SessionStore(db_path=tmp_path / "mt.db")
    ss_mod = importlib.import_module("app.session_store")
    monkeypatch.setattr(ss_mod, "session_store", isolated)

    class _FakeResponse:
        def __init__(self) -> None:
            self.source_nodes = [
                type(
                    "Node",
                    (),
                    {
                        "metadata": {
                            "file_name": "t.txt",
                            "relative_path": "data/t.txt",
                            "page_label": "1",
                        },
                        "score": 0.85,
                        "text": "chunk",
                    },
                )()
            ]
            self.usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        def __str__(self) -> str:
            return "Answer line."

    class _FakeEngine:
        def query(self, question: str):
            return _FakeResponse()

    def _fake_build(q, options, **kwargs):
        return {
            "engine": _FakeEngine(),
            "cache_hit": False,
            "engine_cache_lookup_ms": 0.0,
            "pipeline_params": {
                "query_type": "qa",
                "retrieval_mode": "vector_only",
                "similarity_top_k": 4,
                "enable_reranker": False,
                "rerank_top_n": 4,
                "homework_mode": options.homework_mode,
                "assistance_level": options.assistance_level,
                "query_engine_cache_policy": "disabled_for_session",
            },
        }

    monkeypatch.setattr(query_service, "build_query_engine", _fake_build)

    sid = "eval-mt-sess"
    opts = QueryOptions(session_id=sid)
    query_service.answer_question("First?", opts)
    query_service.answer_question("Second?", opts)
    hist = isolated.get(sid)
    assert len(hist) == 4
    assert hist[0].role == "user" and hist[0].content == "First?"
    assert hist[2].role == "user" and hist[2].content == "Second?"
