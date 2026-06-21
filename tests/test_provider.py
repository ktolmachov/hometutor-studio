"""Тесты единой сборки LLM и embeddings (app.provider)."""
import asyncio
import os

import pytest

from app import llm_guards
import app.provider as provider
import app.provider_openai as provider_openai


def test_raise_for_empty_openai_chat_choices_maps_provider_error():
    """Пустой choices + error в теле ответа — явный RuntimeError (не TypeError из llama-index)."""

    class BadCompletion:
        choices = None
        error = {"message": "Provider returned error", "code": 403}

    with pytest.raises(RuntimeError, match="403"):
        provider._raise_for_empty_openai_chat_choices(BadCompletion())


def test_get_llm_raises_without_api_key(monkeypatch):
    """get_llm() поднимает ValueError, если OPENAI_API_KEY не задан."""
    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = None
    fake.llm_model = "gpt-4"
    fake.openai_api_base = "https://api.example/v1"
    fake.embed_api_base_resolved = "https://api.example/v1"
    fake.embed_model = "embed-1"
    monkeypatch.setattr(provider, "get_settings", lambda: fake)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        provider.get_llm()


def test_get_llm_uses_settings_api_base(monkeypatch):
    """get_llm() передаёт в LLM api_base из настроек."""
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4"
    fake.lmstudio_api_base = "https://llm.example/v1"
    fake.openai_api_base = "https://custom.example/v1"
    fake.embed_api_base_resolved = "https://custom.example/v1"
    fake.embed_model = "embed-1"

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_llm()

    assert captured["api_base"] == "https://llm.example/v1"
    assert captured["model"] == "gpt-4"
    assert captured["api_key"] == "sk-test"


def test_get_llm_normalizes_root_llm_api_base(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "local-model"
    fake.lmstudio_api_base = "http://127.0.0.1:1234"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_llm()

    assert captured["api_base"] == "http://127.0.0.1:1234/v1"


def test_normalize_openai_compatible_api_base_appends_v1_for_root_url():
    assert provider.normalize_openai_compatible_api_base("http://127.0.0.1:8787") == "http://127.0.0.1:8787/v1"
    assert provider.normalize_openai_compatible_api_base("http://127.0.0.1:8787/") == "http://127.0.0.1:8787/v1"
    assert provider.normalize_openai_compatible_api_base("http://127.0.0.1:8787/v1") == "http://127.0.0.1:8787/v1"
    assert provider.normalize_openai_compatible_api_base("http://127.0.0.1:8787/api/v1") == "http://127.0.0.1:8787/api/v1"
    assert provider.normalize_openai_compatible_api_base("https://openrouter.ai/api/v1") == "https://openrouter.ai/api/v1"


def test_get_ssr_llm_uses_dedicated_base_and_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-cloud"
    fake.llm_model = "gpt-4o-mini"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.ssr_llm_api_base = "http://127.0.0.1:8787"
    fake.ssr_llm_api_key = None
    fake.ssr_llm_model = "local-mirror"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)
    monkeypatch.setattr(provider, "ssr_loopback_server_reachable_now", lambda _b: True)

    provider.get_ssr_llm()

    assert captured["api_base"] == "http://127.0.0.1:8787/v1"
    assert captured["model"] == "local-mirror"
    assert captured["api_key"] == "sk-cloud"


def test_get_ssr_llm_allows_localhost_without_openai_key(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = None
    fake.llm_model = "gpt-4o-mini"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.ssr_llm_api_base = "http://127.0.0.1:8787"
    fake.ssr_llm_api_key = None
    fake.ssr_llm_model = None
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)
    monkeypatch.setattr(provider, "ssr_loopback_server_reachable_now", lambda _b: True)

    provider.get_ssr_llm()

    assert captured["api_key"] == "lm-studio"
    assert captured["model"] == "gpt-4o-mini"
    assert captured["api_base"] == "http://127.0.0.1:8787/v1"


def _fake_ssr_settings(*, allow_main_fallback: bool):
    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-main"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.ssr_llm_api_base = "http://127.0.0.1:8787"
    fake.ssr_llm_api_key = None
    fake.ssr_llm_model = "local-should-not-be-used"
    fake.ssr_allow_main_llm_fallback = allow_main_fallback
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0
    return fake


def test_get_ssr_llm_resolved_blocks_main_fallback_by_default_when_loopback_unreachable(monkeypatch):
    fake = _fake_ssr_settings(allow_main_fallback=False)

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "ssr_loopback_server_reachable_now", lambda _b: False)
    monkeypatch.setattr(provider, "get_llm", lambda: pytest.fail("main LLM fallback must be opt-in"))

    with pytest.raises(RuntimeError, match="SSR_ALLOW_MAIN_LLM_FALLBACK"):
        provider.get_ssr_llm_resolved()


def test_get_ssr_llm_resolved_falls_back_to_main_when_explicitly_allowed(monkeypatch):
    class FakeMain:
        marker = "main"

    def fake_get_llm():
        return FakeMain()

    fake = _fake_ssr_settings(allow_main_fallback=True)
    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "ssr_loopback_server_reachable_now", lambda _b: False)
    monkeypatch.setattr(provider, "get_llm", fake_get_llm)

    class BoomOpenAI:
        def __init__(self, *a, **k):
            raise AssertionError("SSR OpenAI should not be constructed")

    monkeypatch.setattr(provider, "OpenAI", BoomOpenAI)

    llm, used_main = provider.get_ssr_llm_resolved()
    assert used_main is True
    assert llm.marker == "main"


def test_get_ssr_llm_resolved_rechecks_loopback_after_main_fallback(monkeypatch):
    class FakeMain:
        marker = "main"

    class FakeSsr:
        marker = "ssr"

        def __init__(self, *a, **kwargs):
            self.model = kwargs["model"]
            self.api_base = kwargs["api_base"]

    fake = _fake_ssr_settings(allow_main_fallback=True)
    reachability = iter([False, True])
    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "ssr_loopback_server_reachable_now", lambda _b: next(reachability))
    monkeypatch.setattr(provider, "get_llm", lambda: FakeMain())
    monkeypatch.setattr(provider, "OpenAI", FakeSsr)

    first_llm, first_used_main = provider.get_ssr_llm_resolved()
    second_llm, second_used_main = provider.get_ssr_llm_resolved()

    assert first_used_main is True
    assert first_llm.marker == "main"
    assert second_used_main is False
    assert second_llm.marker == "ssr"
    assert second_llm.model == "local-should-not-be-used"
    assert second_llm.api_base == "http://127.0.0.1:8787/v1"


def test_get_ssr_llm_raises_when_remote_and_no_keys(monkeypatch):
    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = None
    fake.llm_model = "gpt-4o-mini"
    fake.openai_api_base = "https://api.openai.com/v1"
    fake.ssr_llm_api_base = "https://api.openai.com/v1"
    fake.ssr_llm_api_key = None
    fake.ssr_llm_model = None
    monkeypatch.setattr(provider, "get_settings", lambda: fake)

    with pytest.raises(ValueError, match="SSR_LLM_API_KEY"):
        provider.get_ssr_llm()


def test_ssr_llm_shares_main_api_base_detects_same_endpoint(monkeypatch):
    fake = type("FakeSettings", (), {})()
    fake.lmstudio_api_base = "https://openrouter.ai/api/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.ssr_llm_api_base = ""
    assert provider.ssr_llm_shares_main_api_base(fake) is True

    fake.ssr_llm_api_base = "https://openrouter.ai/api/v1"
    assert provider.ssr_llm_shares_main_api_base(fake) is True

    fake.ssr_llm_api_base = "http://127.0.0.1:8787"
    assert provider.ssr_llm_shares_main_api_base(fake) is False


def test_get_embed_model_raises_without_api_key(monkeypatch):
    """get_embed_model() поднимает ValueError, если OPENAI_API_KEY не задан."""
    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = None
    fake.llm_model = "gpt-4"
    fake.openai_api_base = "https://api.example/v1"
    fake.embed_api_base_resolved = "https://api.example/v1"
    fake.embed_model = "embed-1"
    monkeypatch.setattr(provider, "get_settings", lambda: fake)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        provider.get_embed_model()


def test_get_embed_model_uses_embed_api_base(monkeypatch):
    """get_embed_model() использует embed_api_base_resolved (отдельно от LLM при необходимости)."""
    captured = {}

    class FakeEmbed:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base, **kwargs})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4"
    fake.openai_api_base = "https://llm.example/v1"
    fake.embed_api_base_resolved = "https://embed.example/v1"
    fake.embed_model = "perplexity/pplx-embed-v1-0.6b"
    fake.embed_dimensions = 1024
    fake.embed_batch_size = 64
    fake.embed_num_workers = 4

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAIEmbedding", FakeEmbed)

    provider.get_embed_model()

    assert captured["api_base"] == "https://embed.example/v1"
    assert captured["model"] == "text-embedding-3-small"
    assert captured["model_name"] == "perplexity/pplx-embed-v1-0.6b"
    assert captured["dimensions"] == 1024


def test_get_embed_model_passes_embed_timeouts(monkeypatch):
    captured = {}

    class FakeEmbed:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.embed_model = "text-embedding-3-small"
    fake.embed_dimensions = 0
    fake.embed_api_base_resolved = "https://embed.example/v1"
    fake.llm_max_retries = 2
    fake.embed_request_timeout = 42
    fake.embed_connect_timeout_sec = 9.0
    fake.embed_batch_size = 64
    fake.embed_num_workers = 4

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAIEmbedding", FakeEmbed)

    provider.get_embed_model()

    assert captured["max_retries"] == 2
    assert captured["timeout"] == 42.0
    assert captured["async_http_client"] is not None


def test_get_judge_llm_uses_dedicated_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4"
    fake.eval_judge_llm = "openai/gpt-4o-mini"
    fake.lmstudio_api_base = "https://judge-llm.example/v1"
    fake.openai_api_base = "https://judge.example/v1"

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_judge_llm()

    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["api_base"] == "https://judge.example/v1"


def test_get_rewrite_llm_routes_cloud_role_to_openai_base(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "qwen/qwen3.6-27b"
    fake.rewrite_model = "openai/gpt-4o-mini"
    fake.lmstudio_api_base = "http://127.0.0.1:1234/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_rewrite_llm()

    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["api_base"] == "https://openrouter.ai/api/v1"


def test_get_classifier_llm_routes_cloud_role_to_openai_base(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "qwen/qwen3.6-27b"
    fake.classifier_model = "openai/gpt-4o-mini"
    fake.lmstudio_api_base = "http://127.0.0.1:1234/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_classifier_llm()

    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["api_base"] == "https://openrouter.ai/api/v1"


def test_get_healthcheck_llm_uses_strict_timeout_and_no_retries(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4o-mini"
    fake.lmstudio_api_base = "https://health-llm.example/v1"
    fake.openai_api_base = "https://health.example/v1"

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_healthcheck_llm(timeout_sec=2.5)

    assert captured["model"] == "gpt-4o-mini"
    assert captured["api_key"] == "sk-test"
    assert captured["api_base"] == "https://health-llm.example/v1"
    assert captured["max_retries"] == 0
    assert captured["timeout"] == 2.5
    assert captured["reuse_client"] is False
    assert captured["http_client"] is not None


def test_get_judge_llm_warns_when_falling_back(monkeypatch, caplog):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4"
    fake.eval_judge_llm = None
    fake.lmstudio_api_base = "https://judge-fallback-llm.example/v1"
    fake.openai_api_base = "https://judge.example/v1"

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    import logging

    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level("WARNING"):
            provider.get_judge_llm()
    finally:
        app_logger.removeHandler(caplog.handler)

    assert captured["model"] == "gpt-4"
    assert "falling back to main model" in caplog.text


def test_get_quiz_llm_uses_dedicated_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4"
    fake.quiz_llm_model = "gpt-4o"
    fake.quiz_llm_api_base = None
    fake.lmstudio_api_base = "https://quiz-llm.example/v1"
    fake.openai_api_base = "https://quiz.example/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_quiz_llm()

    assert captured["model"] == "gpt-4o"
    # cloud model → auto-routed to OPENAI_API_BASE (no QUIZ_LLM_API_BASE needed)
    assert captured["api_base"] == "https://quiz.example/v1"


def test_get_quiz_llm_respects_explicit_api_base(monkeypatch):
    """QUIZ_LLM_API_BASE overrides auto-routing even for cloud model names."""
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4"
    fake.quiz_llm_model = "gpt-4o"
    fake.quiz_llm_api_base = "https://custom-quiz-endpoint.example/v1"
    fake.lmstudio_api_base = "http://127.0.0.1:1234/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_quiz_llm()

    assert captured["model"] == "gpt-4o"
    assert captured["api_base"] == "https://custom-quiz-endpoint.example/v1"


def test_get_quiz_llm_falls_back_to_main_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-5-mini"
    fake.quiz_llm_model = None
    fake.quiz_llm_api_base = None
    fake.lmstudio_api_base = "https://quiz-fallback-llm.example/v1"
    fake.openai_api_base = "https://api.example/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_quiz_llm()

    assert captured["model"] == "gpt-5-mini"
    assert captured["api_base"] == "https://quiz-fallback-llm.example/v1"


def test_get_ingestion_llm_uses_dedicated_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4o-mini"
    fake.ingestion_model = "google/gemma-4-31b-it"
    fake.lmstudio_api_base = "https://ingest-llm.example/v1"
    fake.openai_api_base = "https://ingest.example/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_ingestion_llm()

    assert captured["model"] == "google/gemma-4-31b-it"
    assert captured["api_base"] == "https://ingest.example/v1"


def test_get_ingestion_llm_falls_back_to_main_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4o"
    fake.ingestion_model = None
    fake.lmstudio_api_base = "https://ingest-fallback-llm.example/v1"
    fake.openai_api_base = "https://api.example/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_ingestion_llm()

    assert captured["model"] == "gpt-4o"
    assert captured["api_base"] == "https://api.example/v1"


def test_get_evaluate_llm_uses_dedicated_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-4o-mini"
    fake.evaluate_model = "openai/gpt-4o-mini"
    fake.lmstudio_api_base = "https://eval-llm.example/v1"
    fake.openai_api_base = "https://eval.example/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_evaluate_llm()

    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["api_base"] == "https://eval.example/v1"


def test_get_graph_llm_uses_local_graph_base_and_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "qwen/qwen3.6-27b"
    fake.graph_model = "qwen/qwen3.6-27b"
    fake.graph_llm_api_base = "http://127.0.0.1:1234/v1"
    fake.lmstudio_api_base = "http://127.0.0.1:9999/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_graph_llm()

    assert captured["model"] == "qwen/qwen3.6-27b"
    assert captured["api_base"] == "http://127.0.0.1:1234/v1"


def test_get_evaluate_llm_falls_back_to_main_model(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update({"model": model, "api_key": api_key, "api_base": api_base})

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-5-mini"
    fake.evaluate_model = None
    fake.lmstudio_api_base = "https://eval-fallback-llm.example/v1"
    fake.openai_api_base = "https://api.example/v1"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 60

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_evaluate_llm()

    assert captured["model"] == "gpt-5-mini"
    assert captured["api_base"] == "https://eval-fallback-llm.example/v1"


def test_balanced_primary_chat_uses_cloud_fallback_when_local_cb_open(monkeypatch):
    from app import llm_local_circuit

    llm_local_circuit.reset_all()
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update(dict(model=model, api_key=api_key, api_base=api_base))

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "gpt-5-mini"
    fake.lmstudio_api_base = "http://127.0.0.1:7777/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.home_rag_local_profile = "balanced"
    fake.home_rag_data_mode = "demo"
    fake.home_rag_llm_cloud_consent = False
    fake.home_rag_llm_fallback_enabled = True
    fake.home_rag_llm_fallback_api_base = None
    fake.home_rag_llm_fallback_model = "gpt-4o-mini"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 30
    fake.llm_connect_timeout_sec = 10.0
    fake.home_rag_llm_local_hard_timeout_sec = 20.0
    fake.llm_fallback_model = ""
    fake.enable_llm_fallback = False

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    llm_local_circuit.record_failure(
        "http://127.0.0.1:7777/v1",
        error_type="unittest",
        failure_threshold=1,
        failure_window_sec=300.0,
    )
    provider.get_llm()

    assert captured["api_base"] == "https://openrouter.ai/api/v1"
    assert captured["model"] == "gpt-4o-mini"
    assert captured.get("source") is None
    llm_local_circuit.reset_all()


def test_balanced_primary_chat_real_data_without_consent_stays_local(monkeypatch):
    from app import llm_local_circuit

    llm_local_circuit.reset_all()
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update(dict(model=model, api_key=api_key, api_base=api_base))

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "qwen/qwen3.6-27b"
    fake.lmstudio_api_base = "http://127.0.0.1:7777/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.home_rag_local_profile = "balanced"
    fake.home_rag_data_mode = "real"
    fake.home_rag_llm_cloud_consent = False
    fake.home_rag_llm_fallback_enabled = True
    fake.home_rag_llm_fallback_api_base = None
    fake.home_rag_llm_fallback_model = "openai/gpt-4o-mini"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 30
    fake.llm_connect_timeout_sec = 10.0
    fake.home_rag_llm_local_hard_timeout_sec = 20.0
    fake.llm_fallback_model = ""
    fake.enable_llm_fallback = False

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    llm_local_circuit.record_failure(
        "http://127.0.0.1:7777/v1",
        error_type="unittest",
        failure_threshold=1,
        failure_window_sec=300.0,
    )
    llm = provider.get_llm()

    assert captured["api_base"] == "http://127.0.0.1:7777/v1"
    assert captured["model"] == "qwen/qwen3.6-27b"
    assert provider.llm_source_metadata(llm)["llm_source"] == "local"
    assert provider.llm_source_metadata(llm)["fallback_used"] is False
    llm_local_circuit.reset_all()


def test_balanced_primary_chat_real_data_with_consent_uses_cloud_fallback(monkeypatch):
    from app import llm_local_circuit

    llm_local_circuit.reset_all()
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update(dict(model=model, api_key=api_key, api_base=api_base))

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "qwen/qwen3.6-27b"
    fake.lmstudio_api_base = "http://127.0.0.1:7777/v1"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.home_rag_local_profile = "balanced"
    fake.home_rag_data_mode = "real"
    fake.home_rag_llm_cloud_consent = True
    fake.home_rag_llm_fallback_enabled = True
    fake.home_rag_llm_fallback_api_base = None
    fake.home_rag_llm_fallback_model = "openai/gpt-4o-mini"
    fake.llm_max_retries = 3
    fake.llm_request_timeout = 30
    fake.llm_connect_timeout_sec = 10.0
    fake.home_rag_llm_local_hard_timeout_sec = 20.0
    fake.llm_fallback_model = ""
    fake.enable_llm_fallback = False

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    llm_local_circuit.record_failure(
        "http://127.0.0.1:7777/v1",
        error_type="unittest",
        failure_threshold=1,
        failure_window_sec=300.0,
    )
    llm = provider.get_llm()

    assert captured["api_base"] == "https://openrouter.ai/api/v1"
    assert captured["model"] == "openai/gpt-4o-mini"
    assert provider.llm_source_metadata(llm)["llm_source"] == "cloud"
    assert provider.llm_source_metadata(llm)["fallback_used"] is True
    llm_local_circuit.reset_all()


def test_local_strict_primary_chat_raises_when_cb_open(monkeypatch):
    from app import llm_local_circuit

    llm_local_circuit.reset_all()
    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "local-gemma"
    fake.lmstudio_api_base = "http://127.0.0.1:7788/v1"
    fake.home_rag_local_profile = "local_strict"
    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(
        provider,
        "OpenAI",
        lambda **kwargs: pytest.fail("OpenAI should not be constructed in strict CB-open path"),
    )

    llm_local_circuit.record_failure(
        "http://127.0.0.1:7788/v1",
        error_type="unittest",
        failure_threshold=1,
        failure_window_sec=300.0,
    )

    with pytest.raises(ValueError, match="local_strict"):
        provider.get_llm()
    llm_local_circuit.reset_all()


def test_cloud_fast_primary_chat_uses_openai_base(monkeypatch):
    captured = {}

    class FakeLLM:
        def __init__(self, *, model, api_key, api_base, **kwargs):
            captured.update(dict(model=model, api_key=api_key, api_base=api_base))

    fake = type("FakeSettings", (), {})()
    fake.openai_api_key = "sk-test"
    fake.llm_model = "anthropic/claude-3-haiku"
    fake.openai_api_base = "https://openrouter.ai/api/v1"
    fake.lmstudio_api_base = "http://127.0.0.1:1234/v1"
    fake.home_rag_local_profile = "cloud_fast"
    fake.llm_max_retries = 2
    fake.llm_request_timeout = 30
    fake.llm_connect_timeout_sec = 10.0

    monkeypatch.setattr(provider, "get_settings", lambda: fake)
    monkeypatch.setattr(provider, "OpenAI", FakeLLM)

    provider.get_llm()

    assert captured["api_base"] == "https://openrouter.ai/api/v1"


def test_provider_openai_supports_gpt5mini_metadata_alias(monkeypatch):
    # В новых llama_index `gpt-5-mini` может появиться в ALL_AVAILABLE_MODELS — тогда alias не нужен; проверяем ветку alias.
    without_g5 = frozenset(
        m for m in provider.ALL_AVAILABLE_MODELS if str(m).strip().lower() != "gpt-5-mini"
    )
    monkeypatch.setattr(provider_openai, "ALL_AVAILABLE_MODELS", without_g5)

    llm = provider.OpenAI(
        model="gpt-5-mini",
        api_key="sk-test",
        api_base="https://openrouter.example/v1",
    )

    assert llm.model == "gpt-5-mini"
    assert llm._get_model_name() == "gpt-4o-mini"
    assert llm.metadata.is_chat_model is True
    assert llm.metadata.context_window > 0


def test_provider_openai_supports_custom_local_model_metadata_alias(monkeypatch):
    without_local = frozenset(
        m for m in provider.ALL_AVAILABLE_MODELS if str(m).strip().lower() != "qwen2.5-coder-7b-instruct"
    )
    fake_settings = type("FakeSettings", (), {})()
    fake_settings.llamaindex_metadata_fallback_model = "gpt-4o-mini"
    monkeypatch.setattr(provider_openai, "ALL_AVAILABLE_MODELS", without_local)
    monkeypatch.setattr(provider_openai, "get_settings", lambda: fake_settings)

    llm = provider.OpenAI(
        model="qwen2.5-coder-7b-instruct",
        api_key="sk-test",
        api_base="http://127.0.0.1:1234/api/v1",
    )

    assert llm.model == "qwen2.5-coder-7b-instruct"
    assert llm._get_model_name() == "gpt-4o-mini"
    assert llm.metadata.is_chat_model is True
    assert llm.metadata.context_window > 0


def test_provider_blocks_disallowed_model_before_client(monkeypatch):
    logs = []
    llm = provider.OpenAI(
        model="z-ai/glm-5.1",
        api_key="sk-test",
        api_base="https://openrouter.example/v1",
        max_retries=0,
    )

    monkeypatch.setattr(provider_openai, "log_cost_call", lambda **kwargs: logs.append(kwargs))
    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: pytest.fail("provider client must not be created for blocked model"),
    )

    with pytest.raises(provider.BlockedModelError):
        llm._chat([])

    assert logs[0]["status"] == "BLOCKED"
    assert logs[0]["error_type"] == "BlockedModelError"


def test_provider_blocks_hard_token_limit_before_client(monkeypatch):
    logs = []
    llm = provider.OpenAI(
        model="grok-4.1-fast-thinking",
        api_key="sk-test",
        api_base="https://openrouter.example/v1",
        max_retries=0,
    )

    monkeypatch.setattr(provider_openai, "log_cost_call", lambda **kwargs: logs.append(kwargs))
    monkeypatch.setattr(
        provider_openai,
        "estimate_messages_tokens",
        lambda messages, model: 20_001,
    )
    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: pytest.fail("provider client must not be created above hard limit"),
    )

    with pytest.raises(provider.HardLimitExceededError):
        llm._chat([])

    assert logs[0]["status"] == "BLOCKED"
    assert logs[0]["input_tokens"] == 20_001
    assert logs[0]["error_type"] == "HardLimitExceededError"


def test_provider_blocks_unchanged_retry_after_error(monkeypatch):
    llm_guards.reset_error_fingerprints()
    logs = []
    llm = provider.OpenAI(
        model="grok-4.1-fast-thinking",
        api_key="sk-test",
        api_base="https://openrouter.example/v1",
        max_retries=0,
    )
    messages = [{"role": "user", "content": "same payload"}]
    fingerprint = provider.request_fingerprint(
        llm.model,
        messages,
        {"prompt_type": "planning"},
    )

    provider.record_error_fingerprint(fingerprint)
    monkeypatch.setattr(provider_openai, "log_cost_call", lambda **kwargs: logs.append(kwargs))
    monkeypatch.setattr(
        provider_openai, "to_openai_message_dicts", lambda messages, model: messages
    )
    monkeypatch.setattr(
        provider_openai, "estimate_messages_tokens", lambda messages, model: 100
    )
    monkeypatch.setattr(
        provider_openai.TokenValidator,
        "validate_and_trim",
        lambda messages, **kwargs: (messages, 100),
    )
    monkeypatch.setattr(
        llm,
        "_get_client",
        lambda: pytest.fail("provider client must not be created for unchanged retry"),
    )

    with pytest.raises(provider.NoRetryAfterError):
        llm._chat(messages, prompt_type="planning")

    assert logs[0]["status"] == "BLOCKED"
    assert logs[0]["error_type"] == "NoRetryAfterError"
    llm_guards.reset_error_fingerprints()


def test_provider_records_empty_choices_error_for_retry_guard(monkeypatch):
    llm_guards.reset_error_fingerprints()
    logs = []
    call_count = {"value": 0}
    llm = provider.OpenAI(
        model="grok-4.1-fast-thinking",
        api_key="sk-test",
        api_base="https://openrouter.example/v1",
        max_retries=0,
    )
    messages = [{"role": "user", "content": "provider error body"}]

    class BadCompletion:
        choices = None
        error = {"message": "Provider returned error", "code": 403}

    class FakeCompletions:
        def create(self, **kwargs):
            call_count["value"] += 1
            return BadCompletion()

    class FakeClient:
        chat = type("FakeChat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(provider_openai, "log_cost_call", lambda **kwargs: logs.append(kwargs))
    monkeypatch.setattr(
        provider_openai, "to_openai_message_dicts", lambda messages, model: messages
    )
    monkeypatch.setattr(
        provider_openai, "estimate_messages_tokens", lambda messages, model: 100
    )
    monkeypatch.setattr(
        provider_openai.TokenValidator,
        "validate_and_trim",
        lambda messages, **kwargs: (messages, 100),
    )
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClient())

    with pytest.raises(RuntimeError, match="403"):
        llm._chat(messages, prompt_type="planning")

    with pytest.raises(provider.NoRetryAfterError):
        llm._chat(messages, prompt_type="planning")

    assert call_count["value"] == 1
    assert logs[0]["status"] == "ERR"
    assert logs[0]["error_type"] == "RuntimeError"
    assert logs[0]["cost_estimated_after_error"] is True
    assert logs[0]["cost_rub"] == pytest.approx(
        llm_guards.estimate_cost_rub(llm.model, 100, 0)
    )
    assert logs[1]["status"] == "BLOCKED"
    assert logs[1]["error_type"] == "NoRetryAfterError"
    llm_guards.reset_error_fingerprints()


def test_provider_logs_prompt_stats_and_context_length_error(monkeypatch):
    monkeypatch.setenv("KILO_RELAY_UPSTREAM", "http://upstream.test.example")
    relay_upstream_base = os.environ["KILO_RELAY_UPSTREAM"].strip().rstrip("/")
    logs = []
    llm = provider.OpenAI(
        model="grok-4.1-fast-thinking",
        api_key="sk-test",
        api_base="https://api.example/v1",
        max_retries=0,
    )
    messages = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "x" * 120_000},
    ]

    class ApiError(Exception):
        def __init__(self):
            super().__init__(
                "This model doesn't allow input more than 128000 length, but your input is 185816."
            )
            self.status_code = 400
            self.metadata = {"url": f"{relay_upstream_base}/v1/chat/completions"}
            self.responseHeaders = {"content-length": "240"}
            self.responseBody = '{"error":{"message":"too long","code":400}}'

    class FakeCompletions:
        def create(self, **kwargs):
            raise ApiError()

    class FakeClient:
        chat = type("FakeChat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(provider_openai, "log_cost_call", lambda **kwargs: logs.append(kwargs))
    monkeypatch.setattr(
        provider_openai, "to_openai_message_dicts", lambda messages, model: messages
    )
    monkeypatch.setattr(
        provider_openai, "estimate_messages_tokens", lambda messages, model: 15_000
    )
    monkeypatch.setattr(
        provider_openai.TokenValidator,
        "validate_and_trim",
        lambda messages, **kwargs: (messages, 15_000),
    )
    monkeypatch.setattr(llm, "_get_client", lambda: FakeClient())

    with pytest.raises(Exception, match="128000"):
        llm._chat(messages, prompt_type="planning", package_id="epoch-debug")

    assert logs[0]["status"] == "ERR"
    assert logs[0]["prompt_stats"]["messages_count"] == 2
    assert logs[0]["prompt_stats"]["total_chars"] >= 120_000
    assert logs[0]["provider_error"]["error_kind"] == "context_length_exceeded"
    assert logs[0]["provider_error"]["input_char_limit"] == 128000
    assert logs[0]["provider_error"]["input_char_actual"] == 185816


def test_provider_async_records_empty_choices_error_for_retry_guard(monkeypatch):
    llm_guards.reset_error_fingerprints()
    logs = []
    call_count = {"value": 0}
    llm = provider.OpenAI(
        model="grok-4.1-fast-thinking",
        api_key="sk-test",
        api_base="https://openrouter.example/v1",
        max_retries=0,
        reuse_client=True,
    )
    messages = [{"role": "user", "content": "provider error body async"}]

    class BadCompletion:
        choices = None
        error = {"message": "Provider returned error", "code": 403}

    class FakeCompletions:
        async def create(self, **kwargs):
            call_count["value"] += 1
            return BadCompletion()

    class FakeAsyncClient:
        chat = type("FakeChat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr(provider_openai, "log_cost_call", lambda **kwargs: logs.append(kwargs))
    monkeypatch.setattr(
        provider_openai, "to_openai_message_dicts", lambda messages, model: messages
    )
    monkeypatch.setattr(
        provider_openai, "estimate_messages_tokens", lambda messages, model: 100
    )
    monkeypatch.setattr(
        provider_openai.TokenValidator,
        "validate_and_trim",
        lambda messages, **kwargs: (messages, 100),
    )
    monkeypatch.setattr(llm, "_get_aclient", lambda: FakeAsyncClient())

    async def run():
        with pytest.raises(RuntimeError, match="403"):
            await llm._achat(messages, prompt_type="planning")
        with pytest.raises(provider.NoRetryAfterError):
            await llm._achat(messages, prompt_type="planning")

    asyncio.run(run())

    assert call_count["value"] == 1
    assert logs[0]["status"] == "ERR"
    assert logs[0]["cost_estimated_after_error"] is True
    assert logs[1]["status"] == "BLOCKED"
    llm_guards.reset_error_fingerprints()


def test_annotate_llm_source_survives_pydantic_extra_forbid():
    """object.__setattr__ round-trip on a real pydantic-V2 extra=forbid model.

    Regression for BUG-1: plain setattr raised "OpenAI object has no field X",
    making First Session Artifact silently fall back to _noop_retrieve_fn.
    This test uses a minimal pydantic V2 model with the same extra="forbid"
    constraint as llama-index's OpenAI — no network call required.
    """
    from pydantic import BaseModel, ConfigDict

    class StrictModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        value: int = 0

    obj = StrictModel()

    # plain setattr must fail — this is the condition that caused BUG-1
    with pytest.raises((ValueError, TypeError)):
        setattr(obj, "home_rag_llm_source", "primary")

    # _annotate_llm_source must succeed via object.__setattr__
    provider._annotate_llm_source(
        obj,
        source="primary",
        model="test-model",
        api_base="https://x/v1",
        fallback_used=False,
        profile="balanced",
    )

    meta = provider.llm_source_metadata(obj)
    assert meta["llm_source"] == "primary"
    assert meta["llm_model"] == "test-model"
    assert meta["llm_api_base"] == "https://x/v1"
    assert meta["fallback_used"] is False
    assert meta["llm_profile"] == "balanced"
