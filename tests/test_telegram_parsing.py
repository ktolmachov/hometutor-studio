from aiogram import Router

from app.telegram_handlers import TELEGRAM_HELP_TEXT, parse_quiz_scope_arg, router


def test_parse_quiz_document():
    assert parse_quiz_scope_arg("document:notes/a.md") == ("document", "notes/a.md")


def test_parse_quiz_topic():
    assert parse_quiz_scope_arg("topic:Конденсация RAG") == ("topic", "Конденсация RAG")


def test_parse_quiz_invalid():
    assert parse_quiz_scope_arg("") is None
    assert parse_quiz_scope_arg("nope") is None


def test_telegram_help_mentions_streamlit_and_user_guide():
    low = TELEGRAM_HELP_TEXT.lower()
    assert "streamlit" in low
    assert "user_guide.md" in TELEGRAM_HELP_TEXT


def test_telegram_router_registers_core_aiogram_handlers():
    assert isinstance(router, Router)

    callbacks = {
        getattr(handler.callback, "__name__", "")
        for handler in router.message.handlers
    }
    assert {
        "cmd_start",
        "cmd_help",
        "cmd_ask",
        "cmd_tutor",
        "cmd_quiz",
        "quiz_answer",
    }.issubset(callbacks)
