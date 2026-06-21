"""Тесты сводки JSONL-профилей SSR LLM."""

from __future__ import annotations

import pytest

import app.config as config
from app.otel_tracing import trace_ssr_llm_explanation
from app.ssr_llm_profile_summary import (
    format_summary_text,
    summarize_ssr_profile_rows,
)


def test_summarize_ssr_profile_rows_latency_percentiles() -> None:
    rows = [
        {"outcome": "llm_success", "latency_ms": 100.0, "effective_model": "m1", "used_main_chat_client": False},
        {"outcome": "llm_success", "latency_ms": 300.0, "effective_model": "m1", "used_main_chat_client": False},
        {"outcome": "cache_hit", "latency_ms": 0.0, "effective_model": "m1", "used_main_chat_client": False},
        {
            "outcome": "llm_success",
            "latency_ms": 400.0,
            "effective_model": "m2",
            "used_main_chat_client": True,
            "main_llm_model": "gpt-main",
        },
    ]
    p = summarize_ssr_profile_rows(rows)
    assert p["records"] == 4
    assert p["outcome_counts"]["llm_success"] == 3
    assert p["outcome_counts"]["cache_hit"] == 1
    assert p["latency_ms_llm_success_p50"] == 300.0
    assert p["used_main_chat_client_count"] == 1
    assert p["used_main_chat_client_rate"] == 0.25
    assert p["main_llm_model_sample"] == "gpt-main"


def test_format_summary_empty() -> None:
    assert "No SSR" in format_summary_text(summarize_ssr_profile_rows([]))


def test_trace_ssr_llm_explanation_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OTEL_TRACING", "false")
    config.reset_settings_cache()
    with trace_ssr_llm_explanation() as span:
        assert span is None
    config.reset_settings_cache()
