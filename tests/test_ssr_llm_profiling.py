"""Запись профилей SSR LLM в JSONL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.config as config
from app.ssr_llm_profiling import record_ssr_llm_profile


def test_record_ssr_llm_profile_writes_jsonl_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SSR_LLM_PROFILE_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_SSR_LLM_PROFILING", "true")
    config.reset_settings_cache()

    record_ssr_llm_profile(
        outcome="llm_success",
        latency_ms=12.345,
        used_main_chat_client=False,
        effective_model="test-ssr-model",
        total_tokens=99,
        hint_kind="cards_due",
        primary_nav="fc_go",
    )

    files = list(tmp_path.glob("ssr_llm_profile_*.jsonl"))
    assert len(files) == 1
    line = files[0].read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row["kind"] == "ssr_llm_explanation"
    assert row["outcome"] == "llm_success"
    assert row["effective_model"] == "test-ssr-model"
    assert row["main_llm_model"]
    assert row["used_main_chat_client"] is False
    assert row["latency_ms"] == 12.345
    assert row["total_tokens"] == 99
    assert row["event_id"]
    assert len(row["event_id"]) >= 32
    assert row["primary_nav"] == "fc_go"
    config.reset_settings_cache()


def test_record_ssr_llm_profile_skips_when_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SSR_LLM_PROFILE_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_SSR_LLM_PROFILING", "false")
    config.reset_settings_cache()

    record_ssr_llm_profile(outcome="llm_success", latency_ms=1.0)

    assert list(tmp_path.glob("ssr_llm_profile_*.jsonl")) == []
    config.reset_settings_cache()
