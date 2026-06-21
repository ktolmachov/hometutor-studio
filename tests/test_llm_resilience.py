"""18 Core: complete_with_resilience + fallback."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.config as config
from app.llm_resilience import complete_with_resilience


class _FailingThenOk:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt: str, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("simulated")
        return SimpleNamespace(text="ok")


class _Fallback:
    def __init__(self) -> None:
        self.used = False

    def complete(self, prompt: str, **kwargs):
        self.used = True
        return SimpleNamespace(text="fallback-body")


class _ConnectionFail:
    def complete(self, prompt: str, **kwargs):
        raise ConnectionError("local endpoint down")


def test_complete_with_resilience_reraises_when_no_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_FALLBACK", "false")
    config.reset_settings_cache()
    llm = _FailingThenOk()
    with pytest.raises(TimeoutError):
        complete_with_resilience(llm, "p", stage="test")
    assert llm.calls == 1
    config.reset_settings_cache()


def test_complete_with_resilience_uses_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_FALLBACK", "true")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config.reset_settings_cache()

    llm = _FailingThenOk()
    fb = _Fallback()

    monkeypatch.setattr("app.provider.get_llm_fallback", lambda: fb)

    out = complete_with_resilience(llm, "prompt", stage="test")
    assert out.text == "fallback-body"
    assert fb.used is True
    assert llm.calls == 1
    config.reset_settings_cache()


def test_complete_with_resilience_skips_fallback_when_disabled_explicitly(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_FALLBACK", "true")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config.reset_settings_cache()

    llm = _FailingThenOk()
    fb = _Fallback()

    monkeypatch.setattr("app.provider.get_llm_fallback", lambda: fb)

    with pytest.raises(TimeoutError):
        complete_with_resilience(llm, "prompt", stage="test", allow_provider_fallback=False)
    assert llm.calls == 1
    assert fb.used is False
    config.reset_settings_cache()


def test_complete_with_resilience_blocks_cross_base_fallback_for_real_without_consent(monkeypatch):
    """Runtime gate: без cloud consent cross-base fallback не вызывается (см. primary_chat_fallback_ready)."""
    monkeypatch.setenv("ENABLE_LLM_FALLBACK", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config.reset_settings_cache()

    settings = config.Settings.model_construct(
        enable_llm_fallback=False,
        llm_fallback_model="",
        home_rag_data_mode="real",
        home_rag_llm_fallback_enabled=True,
        home_rag_llm_cloud_consent=False,
        openai_api_key="test-key",
        openai_api_base="https://example.invalid/v1",
        home_rag_llm_fallback_api_base="https://example.invalid/v1",
        home_rag_llm_fallback_model="openai/gpt-4o-mini",
    )
    monkeypatch.setattr("app.llm_resilience.get_settings", lambda: settings)

    fb = _Fallback()
    monkeypatch.setattr("app.provider.get_home_rag_primary_fallback_llm", lambda: fb)

    with pytest.raises(ConnectionError):
        complete_with_resilience(_ConnectionFail(), "prompt", stage="test")
    assert fb.used is False
    config.reset_settings_cache()


def test_complete_with_resilience_allows_cross_base_fallback_for_demo(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_FALLBACK", "false")
    monkeypatch.setenv("HOME_RAG_DATA_MODE", "demo")
    monkeypatch.setenv("HOME_RAG_LLM_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("HOME_RAG_LLM_FALLBACK_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config.reset_settings_cache()

    fb = _Fallback()
    monkeypatch.setattr("app.provider.get_home_rag_primary_fallback_llm", lambda: fb)

    out = complete_with_resilience(_ConnectionFail(), "prompt", stage="test")
    assert out.text == "fallback-body"
    assert fb.used is True
    config.reset_settings_cache()
