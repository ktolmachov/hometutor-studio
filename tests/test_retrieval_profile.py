import app.pipeline_factory as pipeline_factory
import app.query_routing as query_routing
import app.retrieval as retrieval
import app.retrieval_strategies as retrieval_strategies
from app.prompts import select_prompt_id
from app.config import RetrievalSettings
from app.models import QueryContext, QueryOptions
from conftest import patch_retrieval_faq_cache_enabled, patch_retrieval_settings


def test_resolve_profile_params_quality(monkeypatch):
    """Параметры quality-профиля: подмена get_retrieval_settings в pipeline_factory."""
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="quality", retrieval_mode="vector_only"),
    )
    params = pipeline_factory.resolve_pipeline_params()
    defaults = RetrievalSettings()

    assert params["profile"] == "quality"
    assert params["similarity_top_k"] == defaults.similarity_top_k
    assert params["enable_reranker"] == defaults.enable_reranker
    assert params["rerank_top_n"] == defaults.rerank_top_n
    assert params["retrieval_mode"] == "vector_only"


def test_resolve_profile_params_fast(monkeypatch):
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )
    params = pipeline_factory.resolve_pipeline_params()
    defaults = RetrievalSettings()

    assert params["profile"] == "fast"
    assert params["similarity_top_k"] <= defaults.similarity_top_k
    assert params["similarity_top_k"] <= 4
    assert params["enable_reranker"] is False
    assert params["rerank_top_n"] == defaults.rerank_top_n
    assert params["retrieval_mode"] == "vector_only"


def test_query_options_rag_profile_overrides_retrieval_settings(monkeypatch):
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    plan = retrieval.resolve_query_execution_plan(
        "What is RAG?",
        QueryOptions(rag_profile="quality"),
    )

    assert plan.profile == "quality"
    assert plan.similarity_top_k == RetrievalSettings().similarity_top_k


def test_build_query_engine_uses_resolved_profile_for_postprocessors(monkeypatch):
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    captured = {}

    class _FakeIndex:
        def as_query_engine(self, **kwargs):
            captured["postprocessors"] = kwargs["node_postprocessors"]
            return object()

    def fake_build_postprocessors(params):
        captured["params"] = params
        return []

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": _FakeIndex(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", lambda cache_key, engine: None)
    monkeypatch.setattr(retrieval, "build_postprocessors", fake_build_postprocessors)

    retrieval.build_query_engine("What is RAG?", QueryOptions())

    assert captured["params"]["profile"] == "fast"
    assert captured["params"]["enable_reranker"] is False
    assert captured["params"]["retrieval_mode"] == "vector_only"


def test_build_query_engine_switches_keyword_queries_to_bm25_only(monkeypatch):
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="quality", retrieval_mode="hybrid", enable_reranker=True),
    )

    captured = {}

    class _FakeCollection:
        pass

    class _FakeRetriever:
        pass

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": object(), "llm": object(), "quiz_llm": object(), "collection": _FakeCollection()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", lambda cache_key, engine: None)
    def fake_build_postprocessors(params):
        captured["params"] = params
        return []

    monkeypatch.setattr(retrieval, "build_postprocessors", fake_build_postprocessors)
    monkeypatch.setattr(
        retrieval_strategies,
        "build_bm25_only_retriever",
        lambda collection, similarity_top_k, filters: _FakeRetriever(),
    )
    monkeypatch.setattr(
        retrieval_strategies,
        "get_response_synthesizer",
        lambda **kwargs: kwargs,
    )

    class _FakeRetrieverQueryEngine:
        def __init__(self, retriever, node_postprocessors, response_synthesizer):
            captured["retriever"] = retriever
            captured["node_postprocessors"] = node_postprocessors
            captured["response_synthesizer"] = response_synthesizer

    monkeypatch.setattr(retrieval_strategies, "RetrieverQueryEngine", _FakeRetrieverQueryEngine)

    result = retrieval.build_query_engine("RFC-2024-003", QueryOptions())

    assert result["pipeline_params"]["query_type"] == query_routing.KEYWORD_QUERY
    assert result["pipeline_params"]["retrieval_mode"] == "bm25_only"
    assert result["pipeline_params"]["enable_reranker"] is False


def test_build_query_engine_disables_shared_cache_for_session_requests(monkeypatch):
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    calls = {"get_cache": 0, "set_cache": 0}

    class _FakeIndex:
        def as_query_engine(self, **kwargs):
            return object()

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: calls.__setitem__("get_cache", calls["get_cache"] + 1) or {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": _FakeIndex(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(
        retrieval,
        "set_cached_query_engine",
        lambda cache_key, engine: calls.__setitem__("set_cache", calls["set_cache"] + 1),
    )
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: [])

    result = retrieval.build_query_engine(
        "What is RAG?",
        QueryOptions(session_id="sess-123"),
    )

    assert calls["get_cache"] == 0
    assert calls["set_cache"] == 0
    assert result["cache_hit"] is False
    assert result["engine_cache_lookup_ms"] == 0.0
    assert result["pipeline_params"]["query_engine_cache_policy"] == "disabled_for_session"


def test_build_query_engine_keeps_shared_cache_for_non_session_requests(monkeypatch):
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    calls = {"get_cache": 0, "set_cache": 0}

    class _FakeIndex:
        def as_query_engine(self, **kwargs):
            return object()

    def _get_cache(cache_key):
        calls["get_cache"] += 1
        return {"engine": None, "cache_latency_ms": 0.0}

    def _set_cache(cache_key, engine):
        calls["set_cache"] += 1

    monkeypatch.setattr(retrieval, "get_query_engine_cache_result", _get_cache)
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": _FakeIndex(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", _set_cache)
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: [])

    result = retrieval.build_query_engine("What is RAG?", QueryOptions())

    assert calls["get_cache"] == 1
    assert calls["set_cache"] == 1
    assert result["pipeline_params"]["query_engine_cache_policy"] == "shared"


def test_resolve_query_execution_plan_centralizes_session_and_faq_policy(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    plan = retrieval.resolve_query_execution_plan(
        "What is RAG?",
        QueryOptions(session_id="sess-42"),
    )

    assert plan.query_type == "qa"
    assert plan.prompt_key == "qa"
    assert plan.retrieval_mode == "vector_only"
    assert plan.query_engine_cache_policy == "disabled_for_session"
    assert plan.faq_cache_eligible is False
    assert plan.faq_cache_skip_reason == "session_id"


def test_resolve_query_execution_plan_boosts_first_turn_vector_only_to_hybrid(monkeypatch):
    """US-3.4: первый user-turn + default vector_only → hybrid."""
    patch_retrieval_faq_cache_enabled(monkeypatch)
    patch_retrieval_settings(monkeypatch, rag_profile="fast", retrieval_mode="vector_only")

    ctx = QueryContext(original_question="Что такое RAG?", query_options=QueryOptions(session_id="sess-a"))
    ctx.query_type = "qa"
    ctx.prompt_key = "qa"
    ctx.retrieval_strategy = "default"
    ctx.metadata["session_user_turns_before"] = 0

    plan = retrieval.resolve_query_execution_plan(
        "Что такое RAG?",
        QueryOptions(session_id="sess-a"),
        query_context=ctx,
    )

    assert plan.retrieval_mode == "hybrid"
    assert ctx.trace.get("smart_default_retrieval", {}).get("applied") is True


def test_resolve_query_execution_plan_no_hybrid_boost_second_turn(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    patch_retrieval_settings(monkeypatch, rag_profile="fast", retrieval_mode="vector_only")

    ctx = QueryContext(original_question="Уточни детали", query_options=QueryOptions(session_id="sess-b"))
    ctx.query_type = "qa"
    ctx.prompt_key = "qa"
    ctx.retrieval_strategy = "default"
    ctx.metadata["session_user_turns_before"] = 1

    plan = retrieval.resolve_query_execution_plan(
        "Уточни детали",
        QueryOptions(session_id="sess-b"),
        query_context=ctx,
    )

    assert plan.retrieval_mode == "vector_only"
    assert "smart_default_retrieval" not in ctx.trace


def test_resolve_query_execution_plan_centralizes_tutor_prompt_and_faq_policy(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    plan = retrieval.resolve_query_execution_plan(
        "Explain retrieval",
        QueryOptions(query_mode="tutor"),
    )

    assert plan.prompt_key == "tutor"
    assert plan.query_engine_cache_policy == "shared"
    assert plan.faq_cache_eligible is False
    assert plan.faq_cache_skip_reason == "tutor_mode"


def test_build_query_engine_returns_plan_derived_pipeline_params(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    fast_settings = RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only")
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: fast_settings,
    )

    class _FakeIndex:
        def as_query_engine(self, **kwargs):
            return object()

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": _FakeIndex(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", lambda cache_key, engine: None)
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: [])

    result = retrieval.build_query_engine(
        "What is RAG?",
        QueryOptions(homework_mode=True, assistance_level="hint"),
    )

    assert result["pipeline_params"] == {
        "profile": "fast",
        "query_type": "qa",
        "prompt_key": "homework",
        "retrieval_mode": "vector_only",
        "enable_reranker": False,
        "similarity_top_k": 2,
        "rerank_top_n": fast_settings.rerank_top_n,
        "rerank_model": fast_settings.rerank_model,
        "split_strategy": "sentence_window",
        "window_size": fast_settings.window_size,
        "doc_top_k": None,
        "homework_mode": True,
        "assistance_level": "hint",
        "query_engine_cache_policy": "shared",
        "faq_cache_eligible": True,
        "faq_cache_skip_reason": None,
        "fallback_used": False,
    }


def test_build_query_engine_uses_tutor_generation_prompt(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    monkeypatch.setattr(
        pipeline_factory,
        "get_retrieval_settings",
        lambda: RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only"),
    )

    captured = {}

    class _FakeIndex:
        def as_query_engine(self, **kwargs):
            captured["text_qa_template"] = kwargs["text_qa_template"]
            return object()

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": _FakeIndex(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", lambda cache_key, engine: None)
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: [])

    result = retrieval.build_query_engine(
        "Explain retrieval",
        QueryOptions(query_mode="tutor"),
    )

    assert result["pipeline_params"]["prompt_key"] == "tutor"
    assert "Socratic Tutor v2" in str(captured["text_qa_template"])


def test_prompt_selector_is_deterministic_for_same_inputs():
    args = {
        "query_type": "overview",
        "profile": "quality",
        "retrieval_mode": "vector_only",
        "graph_augmented": True,
        "learner_state": {"mastery_level": "beginner"},
    }
    assert select_prompt_id(**args) == select_prompt_id(**args)


def test_prompt_selector_forces_keyword_for_bm25_mode():
    assert (
        select_prompt_id(
            query_type="qa",
            profile="fast",
            retrieval_mode="bm25_only",
            graph_augmented=False,
            learner_state=None,
        )
        == "keyword"
    )

