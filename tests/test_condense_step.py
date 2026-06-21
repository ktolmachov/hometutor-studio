"""Condense step: skip rules, LLM path, fallback через run_step_safe."""

from unittest.mock import MagicMock

import pytest

from app.condense_step import condense_step
from app.models import Message, QueryContext, QueryOptions
from app.pipeline_steps import rewrite_step


def _fake_settings():
    s = MagicMock()
    s.enable_rewrite = False
    s.enable_classifier = False
    s.enable_condense = True
    s.condense_history_window = 8
    s.condense_history_window_tutor = 16
    s.llm_model = "gpt-4o-mini"
    return s


def test_condense_skips_without_session(monkeypatch):
    monkeypatch.setattr("app.condense_step.get_settings", _fake_settings)
    ctx = QueryContext(original_question="q")
    ctx.conversation_history = [Message(role="user", content="a")] * 3
    out = condense_step(ctx)
    assert out.trace["condense"] == "skipped_no_session"


def test_condense_skips_when_disabled(monkeypatch):
    def _off():
        s = MagicMock()
        s.enable_condense = False
        return s

    monkeypatch.setattr("app.condense_step.get_settings", _off)
    ctx = QueryContext(original_question="q", session_id="s1")
    ctx.conversation_history = [Message(role="user", content="a")] * 3
    out = condense_step(ctx)
    assert out.trace["condense"] == "skipped_disabled"


def test_condense_trace_window_tutor_vs_default(monkeypatch):
    monkeypatch.setattr("app.condense_step.get_settings", _fake_settings)

    class _Resp:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Resp()),
    )

    ctx = QueryContext(
        original_question="q",
        session_id="s1",
        query_options=QueryOptions(query_mode="tutor"),
    )
    ctx.conversation_history = [
        Message(role="user", content="m1"),
        Message(role="assistant", content="m2"),
        Message(role="user", content="m3"),
    ]
    out = condense_step(ctx)
    assert out.trace["condense"] == "success"
    assert out.trace.get("condense_history_window") == 16

    ctx2 = QueryContext(original_question="q", session_id="s1")
    ctx2.conversation_history = ctx.conversation_history
    out2 = condense_step(ctx2)
    assert out2.trace.get("condense_history_window") == 8


def test_condense_skips_short_history(monkeypatch):
    monkeypatch.setattr("app.condense_step.get_settings", _fake_settings)
    ctx = QueryContext(original_question="q", session_id="s1")
    ctx.conversation_history = [Message(role="user", content="a")] * 2
    out = condense_step(ctx)
    assert out.trace["condense"] == "skipped_too_short"


def test_condense_success_and_sets_metadata(monkeypatch):
    monkeypatch.setattr("app.condense_step.get_settings", _fake_settings)

    class _Resp:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Resp()),
    )

    ctx = QueryContext(original_question="What next?", session_id="s1")
    ctx.conversation_history = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
        Message(role="user", content="explain RAG"),
    ]
    out = condense_step(ctx)
    assert out.trace["condense"] == "success"
    assert "condensed_text" in out.metadata
    assert out.condensed_question == out.metadata["condensed_text"]


def test_condense_does_not_overwrite_existing_rewritten_query(monkeypatch):
    monkeypatch.setattr("app.condense_step.get_settings", _fake_settings)

    class _Resp:
        text = "This is a condensed summary of the dialog with enough length."

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Resp()),
    )

    ctx = QueryContext(
        original_question="What next?",
        session_id="s1",
        rewritten_query="preexisting rewritten query",
    )
    ctx.conversation_history = [
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
        Message(role="user", content="explain RAG"),
    ]

    out = condense_step(ctx)

    assert out.trace["condense"] == "success"
    assert out.condensed_question == _Resp.text
    assert out.rewritten_query == "preexisting rewritten query"


def test_condense_fallback_on_short_llm_output(monkeypatch):
    monkeypatch.setattr("app.condense_step.get_settings", _fake_settings)

    class _Resp:
        text = "short"

    monkeypatch.setattr(
        "app.condense_step.get_llm",
        lambda: MagicMock(complete=lambda prompt, **kw: _Resp()),
    )

    ctx = QueryContext(original_question="q", session_id="s1")
    ctx.conversation_history = [Message(role="user", content="a")] * 3
    out = condense_step(ctx)
    assert out.trace["condense"] == "fallback_original"


def test_rewrite_uses_condensed_text(monkeypatch):
    def _settings_rewrite():
        s = MagicMock()
        s.enable_rewrite = True
        s.rewrite_model = None
        s.llm_model = "gpt-4o-mini"
        return s

    monkeypatch.setattr("app.pipeline_steps.get_settings", _settings_rewrite)

    class _Resp:
        text = "rewritten query"

    llm = MagicMock()
    llm.complete = MagicMock(return_value=_Resp())

    monkeypatch.setattr("app.provider.get_rewrite_llm", lambda: llm)

    ctx = QueryContext(original_question="original", session_id="s1")
    ctx.metadata["condensed_text"] = "condensed base for search"
    ctx.query_type = "qa"
    out = rewrite_step(ctx)
    assert out.rewritten_query == "rewritten query"
    first_prompt = llm.complete.call_args_list[0][0][0]
    assert "condensed base for search" in first_prompt
