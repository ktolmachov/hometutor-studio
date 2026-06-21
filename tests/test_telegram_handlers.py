"""Поведенческие тесты telegram cmd_help / cmd_ask: mock Message, без сети и без реального LLM."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.guardrails import InputGuardrailError
from app.telegram_handlers import TELEGRAM_HELP_TEXT, cmd_ask, cmd_help


def _run(coro):
    return asyncio.run(coro)


def test_cmd_help_sends_configured_help_text():
    message = MagicMock()
    message.answer = AsyncMock()
    _run(cmd_help(message))
    message.answer.assert_awaited_once_with(TELEGRAM_HELP_TEXT)


def test_cmd_ask_without_question_sends_usage():
    message = MagicMock()
    message.text = "/ask"
    message.chat.id = 999
    message.answer = AsyncMock()
    _run(cmd_ask(message))
    message.answer.assert_awaited_once()
    first_arg = message.answer.await_args.args[0]
    assert "Использование" in first_arg
    assert "/ask" in first_arg


def test_cmd_ask_passes_session_and_sends_answer(monkeypatch):
    import app.telegram_handlers as th

    captured: dict = {}

    def fake_run_ask(*, question: str, query_mode, session_id: str | None):
        captured["question"] = question
        captured["query_mode"] = query_mode
        captured["session_id"] = session_id
        return {"answer": "Ответ про RAG."}

    monkeypatch.setattr(th, "_run_ask", fake_run_ask)

    message = MagicMock()
    message.text = "/ask Что такое RAG?"
    message.chat.id = 42
    message.answer = AsyncMock()
    _run(cmd_ask(message))

    assert captured == {
        "question": "Что такое RAG?",
        "query_mode": None,
        "session_id": "tg-42",
    }
    message.answer.assert_awaited()
    assert "RAG" in message.answer.await_args.args[0]


def test_cmd_ask_input_guardrail_rejection(monkeypatch):
    import app.telegram_handlers as th

    def boom(*, question: str, query_mode, session_id: str | None):
        raise InputGuardrailError("blocked", code="test_guardrail")

    monkeypatch.setattr(th, "_run_ask", boom)

    message = MagicMock()
    message.text = "/ask x"
    message.chat.id = 1
    message.answer = AsyncMock()
    _run(cmd_ask(message))

    message.answer.assert_awaited_once()
    assert "отклонён" in message.answer.await_args.args[0]


def test_cmd_ask_surfaces_unexpected_errors(monkeypatch):
    import app.telegram_handlers as th

    def boom(*, question: str, query_mode, session_id: str | None):
        raise RuntimeError("upstream")

    monkeypatch.setattr(th, "_run_ask", boom)

    message = MagicMock()
    message.text = "/ask q"
    message.chat.id = 2
    message.answer = AsyncMock()
    _run(cmd_ask(message))

    message.answer.assert_awaited_once()
    body = message.answer.await_args.args[0]
    assert "Ошибка" in body
    assert "upstream" in body
