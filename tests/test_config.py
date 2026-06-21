import pytest

import app.config as config
from app.config import RetrievalSettings, Settings, get_retrieval_settings, get_settings, reset_settings_cache


def test_paths_are_absolute():
    assert config.BASE_DIR.is_absolute()
    assert config.DATA_DIR.is_absolute()
    assert config.CHROMA_DIR.is_absolute()
    assert config.LOG_DIR.is_absolute()


def test_config_has_expected_types():
    settings = Settings()
    retrieval = RetrievalSettings()

    assert isinstance(settings.llm_api_base, str)
    assert len(settings.llm_api_base) > 0
    assert isinstance(settings.openai_api_base, str)
    assert len(settings.openai_api_base) > 0

    assert isinstance(settings.ui_api_base_url, str)
    assert settings.ui_api_base_url.startswith("http")

    assert isinstance(settings.embed_model, str)
    assert isinstance(settings.llm_model, str)
    assert isinstance(settings.llamaindex_metadata_fallback_model, str)
    assert settings.graph_llm_api_base is None or isinstance(settings.graph_llm_api_base, str)
    assert settings.graph_model is None or isinstance(settings.graph_model, str)

    assert isinstance(retrieval.chunk_size, int)
    assert retrieval.chunk_size > 0

    assert isinstance(retrieval.chunk_overlap, int)
    assert retrieval.chunk_overlap >= 0

    assert isinstance(retrieval.split_strategy, str)
    assert isinstance(retrieval.window_size, int)

    assert isinstance(retrieval.similarity_top_k, int)
    assert retrieval.similarity_top_k > 0

    assert isinstance(retrieval.enable_reranker, bool)
    assert isinstance(retrieval.rerank_top_n, int)

    assert isinstance(settings.collection_name, str)

    assert isinstance(settings.query_engine_cache_size, int)
    assert settings.query_engine_cache_size > 0

    assert isinstance(settings.query_engine_ttl_sec, int)
    assert settings.query_engine_ttl_sec > 0

    assert isinstance(settings.guardrails_max_question_length, int)
    assert settings.guardrails_max_question_length > 0
    assert isinstance(settings.guardrails_block_on_prompt_injection, bool)

    assert isinstance(settings.enable_condense, bool)
    assert isinstance(settings.enable_partial_reindex, bool)
    assert isinstance(settings.clear_faq_on_index_activation, bool)
    assert isinstance(settings.faq_memory_collection_name, str)
    assert len(settings.faq_memory_collection_name) > 0
    assert isinstance(settings.faq_dedup_min_score, float)
    assert 0.0 <= settings.faq_dedup_min_score <= 1.0
    assert isinstance(settings.enable_graph_augmented_retrieval, bool)
    assert isinstance(settings.enable_retrieval_self_correction, bool)
    assert isinstance(settings.graph_augment_max_extra_docs, int)
    assert isinstance(settings.llm_connect_timeout_sec, float)
    assert settings.llm_connect_timeout_sec >= 1.0
    assert isinstance(settings.embed_request_timeout, int)
    assert settings.embed_request_timeout >= 1
    assert isinstance(settings.embed_connect_timeout_sec, float)
    assert settings.embed_connect_timeout_sec >= 1.0
    assert isinstance(settings.enable_llm_fallback, bool)
    assert settings.llm_fallback_model is None or isinstance(settings.llm_fallback_model, str)
    assert isinstance(settings.api_rate_limit_per_minute, int)
    assert settings.api_rate_limit_per_minute >= 0
    assert settings.condense_history_window >= 1
    assert settings.condense_history_window_tutor >= 1
    assert settings.session_history_max_messages >= 0
    assert settings.graph_expand_max_hops >= 1
    assert isinstance(settings.guardrails_require_sources, bool)
    assert settings.slo_max_learner_rehydrated_rate is None or isinstance(
        settings.slo_max_learner_rehydrated_rate, float
    )
    assert isinstance(settings.sr_max_interval_days, int)
    assert settings.sr_max_interval_days >= 1
    assert isinstance(settings.sr_min_quality, int)
    assert 0 <= settings.sr_min_quality <= 5
    assert settings.llm_cost_log_dir == config.LOG_DIR / "cost_logs"


def test_settings_validates_positive_ints():
    with pytest.raises(Exception):
        Settings(query_engine_cache_size=0)
    with pytest.raises(Exception):
        Settings(guardrails_max_question_length=0)
    with pytest.raises(Exception):
        Settings(condense_history_window=0)


def test_retrieval_settings_validates_positive_ints():
    with pytest.raises(Exception):
        RetrievalSettings(chunk_size=0)
    with pytest.raises(Exception):
        RetrievalSettings(similarity_top_k=-1)


def test_retrieval_settings_rag_profile_normalized_to_known():
    r = RetrievalSettings(rag_profile="  unknown  ")
    assert r.rag_profile == "quality"

    r2 = RetrievalSettings(rag_profile="fast")
    assert r2.rag_profile == "fast"

    r3 = RetrievalSettings(rag_profile="quality")
    assert r3.rag_profile == "quality"


def test_get_settings_returns_singleton():
    a = get_settings()
    b = get_settings()
    assert a is b


def test_get_retrieval_settings_returns_singleton():
    a = get_retrieval_settings()
    b = get_retrieval_settings()
    assert a is b


def test_settings_include_guardrails_defaults():
    s = Settings()

    assert s.guardrails_max_question_length > 0
    assert isinstance(s.guardrails_block_on_prompt_injection, bool)
    assert isinstance(s.guardrails_require_sources, bool)
    assert isinstance(s.guardrails_fallback_on_empty_answer, bool)
    assert isinstance(s.guardrails_fallback_on_missing_sources, bool)
    assert isinstance(s.guardrails_fallback_on_suspicious_output, bool)
    assert isinstance(s.guardrails_fallback_on_pii_detected, bool)


def test_cors_default_is_local_only():
    s = Settings(_env_file=None)

    assert s.cors_origins != "*"
    assert "http://127.0.0.1:8501" in s.cors_origins
    assert "http://localhost:8501" in s.cors_origins


def test_cors_wildcard_override_stays_explicit(settings_env):
    from app.api_helpers import cors_origins_list

    s = settings_env({"CORS_ORIGINS": "*"})

    assert s.cors_origins == "*"
    assert cors_origins_list() == ["*"]


def test_reset_settings_cache_recreates_singletons():
    first_settings = get_settings()
    first_retrieval = get_retrieval_settings()

    reset_settings_cache()

    second_settings = get_settings()
    second_retrieval = get_retrieval_settings()

    assert second_settings is not first_settings
    assert second_retrieval is not first_retrieval


def test_settings_env_fixture_overrides_llm_model(settings_env):
    s = settings_env({"LLM_MODEL": "custom-model-from-env"})
    assert s.llm_model == "custom-model-from-env"


def test_settings_env_fixture_overrides_llm_api_base(settings_env):
    s = settings_env({"LLM_API_BASE": "https://llm.example/v1"})
    assert s.llm_api_base == "https://llm.example/v1"


def test_settings_env_fixture_overrides_graph_model_role(settings_env):
    s = settings_env(
        {
            "GRAPH_LLM_API_BASE": "http://127.0.0.1:1234/v1",
            "GRAPH_MODEL": "qwen/qwen3.6-27b",
        }
    )
    assert s.graph_llm_api_base == "http://127.0.0.1:1234/v1"
    assert s.graph_model == "qwen/qwen3.6-27b"


def test_settings_env_fixture_overrides_cloud_consent(settings_env):
    s = settings_env({"HOME_RAG_LLM_CLOUD_CONSENT": "true"})
    assert s.home_rag_llm_cloud_consent is True


def test_settings_env_fixture_overrides_llamaindex_metadata_fallback_model(settings_env):
    s = settings_env({"LLAMAINDEX_METADATA_FALLBACK_MODEL": "gpt-4.1-mini"})
    assert s.llamaindex_metadata_fallback_model == "gpt-4.1-mini"


def test_settings_env_fixture_overrides_llm_cost_log_dir(settings_env, tmp_path):
    s = settings_env({"LLM_COST_LOG_DIR": str(tmp_path / "costs")})
    assert s.llm_cost_log_dir == tmp_path / "costs"


def test_settings_env_fixture_guardrails_bool(settings_env):
    s = settings_env({"GUARDRAILS_REQUIRE_SOURCES": "false"})
    assert s.guardrails_require_sources is False


# ---------------------------------------------------------------------------
# Privacy guard: real data + cloud fallback
# ---------------------------------------------------------------------------

def test_fallback_disabled_by_default(settings_env):
    s = settings_env({})
    assert s.home_rag_llm_fallback_enabled is False


def test_real_data_blocks_fallback_without_consent(settings_env, monkeypatch):
    from pydantic import ValidationError

    monkeypatch.setenv("HOME_RAG_DATA_MODE", "real")
    monkeypatch.setenv("HOME_RAG_LLM_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("HOME_RAG_LLM_CLOUD_CONSENT", "false")
    from app.config import reset_settings_cache, Settings
    reset_settings_cache()
    with pytest.raises(ValidationError, match="HOME_RAG_LLM_FALLBACK_ENABLED"):
        Settings()


def test_real_data_allows_fallback_with_consent(settings_env):
    s = settings_env(
        {
            "HOME_RAG_DATA_MODE": "real",
            "HOME_RAG_LLM_FALLBACK_ENABLED": "true",
            "HOME_RAG_LLM_CLOUD_CONSENT": "true",
        }
    )
    assert s.home_rag_llm_fallback_enabled is True
    assert s.home_rag_llm_cloud_consent is True


def test_real_data_blocks_cloud_fast_without_consent(monkeypatch):
    from pydantic import ValidationError

    monkeypatch.setenv("HOME_RAG_DATA_MODE", "real")
    monkeypatch.setenv("HOME_RAG_LOCAL_PROFILE", "cloud_fast")
    monkeypatch.setenv("HOME_RAG_LLM_CLOUD_CONSENT", "false")
    from app.config import reset_settings_cache, Settings

    reset_settings_cache()
    with pytest.raises(ValidationError, match="HOME_RAG_LOCAL_PROFILE=cloud_fast"):
        Settings()


def test_real_data_allows_cloud_fast_with_consent(settings_env):
    s = settings_env(
        {
            "HOME_RAG_DATA_MODE": "real",
            "HOME_RAG_LOCAL_PROFILE": "cloud_fast",
            "HOME_RAG_LLM_CLOUD_CONSENT": "true",
        }
    )
    assert s.home_rag_local_profile == "cloud_fast"
    assert s.home_rag_llm_cloud_consent is True


def test_demo_mode_allows_fallback_without_consent(settings_env):
    s = settings_env(
        {
            "HOME_RAG_DATA_MODE": "demo",
            "HOME_RAG_LLM_FALLBACK_ENABLED": "true",
        }
    )
    assert s.home_rag_llm_fallback_enabled is True


# ---------------------------------------------------------------------------
# is_cloud_model — prefix-based detection (not substring)
# ---------------------------------------------------------------------------

def test_is_cloud_model_true_for_cloud_prefixes():
    from app.config import is_cloud_model

    assert is_cloud_model("gpt-4o") is True
    assert is_cloud_model("gpt-4-turbo") is True
    assert is_cloud_model("claude-3-5-sonnet") is True
    assert is_cloud_model("gemini-2.0-flash") is True


def test_is_cloud_model_true_for_provider_prefixed_ids():
    from app.config import is_cloud_model

    assert is_cloud_model("openai/gpt-4o") is True
    assert is_cloud_model("anthropic/claude-3-5-sonnet") is True
    assert is_cloud_model("google/gemma-4-31b-it") is True
    assert is_cloud_model("deepseek/deepseek-r1") is True


def test_is_cloud_model_false_for_local_models_with_cloud_substrings():
    from app.config import is_cloud_model

    assert is_cloud_model("qwen3.6-40b-claude-4.6") is False
    assert is_cloud_model("local-gpt-4-finetuned") is False
    assert is_cloud_model("qwen/qwen3.6-27b") is False
    assert is_cloud_model("") is False
    assert is_cloud_model("lmstudio-community/gemma-4-12b") is False


def test_quiz_question_count_local_model_with_claude_substring(settings_env):
    """Model with 'claude' substring but local prefix must get 3 questions, not 5."""
    s = settings_env({"QUIZ_LLM_MODEL": "qwen3.6-40b-claude-4.6"})
    assert s.quiz_interactive_question_count == 3


def test_quiz_question_count_real_cloud_model(settings_env):
    s = settings_env({"QUIZ_LLM_MODEL": "claude-3-5-sonnet"})
    assert s.quiz_interactive_question_count == 5


# ---------------------------------------------------------------------------
# SSR base derives from LMSTUDIO_API_BASE when not set explicitly
# ---------------------------------------------------------------------------

def test_ssr_base_empty_when_unset(settings_env):
    s = settings_env({"SSR_LLM_API_BASE": ""})
    assert s.ssr_llm_api_base == ""


def test_ssr_base_explicit_overrides(settings_env):
    s = settings_env({"SSR_LLM_API_BASE": "http://10.0.0.5:5678"})
    assert s.ssr_llm_api_base == "http://10.0.0.5:5678"
