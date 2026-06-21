import app.pipeline_factory as pipeline_factory
import app.query_routing as query_routing
import app.retrieval as retrieval
import app.retrieval_strategies as retrieval_strategies
from app.prompts import select_prompt_id
from app.config import RetrievalSettings
from app.models import QueryContext, QueryOptions
from conftest import patch_retrieval_faq_cache_enabled, patch_retrieval_settings


def _patch_mq_retrieval_settings(monkeypatch, **kwargs):
    import app.config as app_config

    settings = patch_retrieval_settings(monkeypatch, **kwargs)
    monkeypatch.setattr(app_config, "get_retrieval_settings", lambda: settings)
    monkeypatch.setattr("app.multi_query_expansion.get_retrieval_settings", lambda: settings)
    return settings


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


# --- multi_query integration (labeled subset, coverage uplift, latency gate) ---

def _labeled_source_coverage_overlap(retrieved_paths: list[str], expected_sources: list[str]) -> float:
    """Test-local coverage metric: |retrieved ∩ expected| / |expected|."""
    expected = {p for p in expected_sources if p}
    if not expected:
        return 0.0
    retrieved = {p for p in retrieved_paths if p}
    return len(retrieved & expected) / len(expected)


def _node_with_path(chunk_id: str, relative_path: str, score: float):
    from llama_index.core.schema import NodeWithScore, TextNode

    return NodeWithScore(
        node=TextNode(
            text=f"chunk-{chunk_id}",
            id_=chunk_id,
            metadata={"chunk_id": chunk_id, "relative_path": relative_path},
        ),
        score=score,
    )


class _ScenarioRetriever:
    """Return different doc coverage per query string."""

    def __init__(self, mapping: dict[str, list]):
        self.mapping = mapping
        self.calls: list[str] = []

    def retrieve(self, query_bundle):
        query = getattr(query_bundle, "query_str", str(query_bundle))
        self.calls.append(query)
        return list(self.mapping.get(query, []))


LABELED_MULTI_QUERY_FIXTURE = [
    {
        "id": "mq_001",
        "effective_query": "retrieval augmented generation definition",
        "expected_sources": ["docs/rag_intro.md", "docs/rag_faq.md"],
    },
    {
        "id": "mq_002",
        "effective_query": "vector database indexing basics",
        "expected_sources": ["docs/indexing.md", "docs/chroma.md"],
    },
    {
        "id": "mq_003",
        "effective_query": "hybrid search bm25 vector fusion",
        "expected_sources": ["docs/hybrid.md", "docs/rrf.md"],
    },
    {
        "id": "mq_004",
        "effective_query": "query rewriting for rag pipelines",
        "expected_sources": ["docs/rewrite.md", "docs/query_expansion.md"],
    },
    {
        "id": "mq_005",
        "effective_query": "chunk overlap sentence splitter settings",
        "expected_sources": ["docs/chunking.md", "docs/splitter.md"],
    },
    {
        "id": "mq_006",
        "effective_query": "reranker cross encoder top n",
        "expected_sources": ["docs/rerank.md", "docs/bge_reranker.md"],
    },
    {
        "id": "mq_007",
        "effective_query": "lost in middle context reorder",
        "expected_sources": ["docs/lost_in_middle.md", "docs/context_order.md"],
    },
    {
        "id": "mq_008",
        "effective_query": "graph augmented retrieval expansion",
        "expected_sources": ["docs/graph_rag.md", "docs/kg_expansion.md"],
    },
    {
        "id": "mq_009",
        "effective_query": "faq cache eligibility rules",
        "expected_sources": ["docs/faq_cache.md", "docs/cache_policy.md"],
    },
    {
        "id": "mq_010",
        "effective_query": "latency budget query surface hard ms",
        "expected_sources": ["docs/latency_budget.md", "docs/surface_budgets.md"],
    },
]


def _paths_from_nodes(nodes) -> list[str]:
    paths: list[str] = []
    for node in nodes:
        meta = getattr(getattr(node, "node", node), "metadata", {}) or {}
        rel = meta.get("relative_path")
        if rel:
            paths.append(str(rel))
    return paths


def test_multi_query_integration_coverage_uplift_and_dedup(monkeypatch):
    from app.multi_query_expansion import merge_deduped_candidates, run_multi_query_retrieval

    baseline_scores: list[float] = []
    expansion_scores: list[float] = []

    for case in LABELED_MULTI_QUERY_FIXTURE:
        anchor = case["effective_query"]
        alt = f"{anchor} paraphrase"
        expected = case["expected_sources"]
        doc_a, doc_b = expected[0], expected[1]

        mapping = {
            anchor: [_node_with_path(f"{case['id']}-a", doc_a, 0.7)],
            alt: [
                _node_with_path(f"{case['id']}-a-dup", doc_a, 0.6),
                _node_with_path(f"{case['id']}-b", doc_b, 0.8),
            ],
        }
        retriever = _ScenarioRetriever(mapping)

        baseline_nodes = retriever.retrieve(type("QB", (), {"query_str": anchor})())
        baseline_scores.append(_labeled_source_coverage_overlap(_paths_from_nodes(baseline_nodes), expected))

        trace: dict = {}
        variant_results = run_multi_query_retrieval(
            base_retriever=retriever,
            variant_queries=[anchor, alt],
            trace=trace,
        )
        merged = merge_deduped_candidates(variant_results, top_k=4)
        chunk_ids = [
            (getattr(n.node, "metadata", {}) or {}).get("chunk_id")
            for n in merged
        ]
        assert len(chunk_ids) == len(set(chunk_ids))
        expansion_scores.append(_labeled_source_coverage_overlap(_paths_from_nodes(merged), expected))
        assert "variant_retrieval_ms" in trace
        assert "expansion_ms" not in trace or trace.get("expansion_ms") is None or trace.get("expansion_ms") >= 0

    baseline_avg = sum(baseline_scores) / len(baseline_scores)
    expansion_avg = sum(expansion_scores) / len(expansion_scores)
    uplift_pct = ((expansion_avg - baseline_avg) / max(baseline_avg, 0.01)) * 100.0
    assert uplift_pct >= 10.0


def test_multi_query_integration_p95_latency_within_hard_budget(monkeypatch):
    from unittest.mock import MagicMock

    from app.hybrid_retrieval import warm_bm25_cache_if_configured
    from app.latency_budget import _thresholds_for, resolve_query_surface
    from app.multi_query_expansion import run_multi_query_retrieval

    collection = MagicMock()
    collection.count.return_value = 3
    collection.get.return_value = {
        "ids": ["id_0", "id_1", "id_2"],
        "documents": ["First document text", "Second document text", "Third document text"],
        "metadatas": [{"file_name": "doc0.txt"}, {"file_name": "doc1.txt"}, {"file_name": "doc2.txt"}],
    }
    monkeypatch.setattr(
        "app.hybrid_retrieval._load_bm25_from_disk",
        lambda _top_k: None,
    )
    monkeypatch.setattr(
        "app.hybrid_retrieval._build_bm25_retriever",
        lambda nodes, similarity_top_k: MagicMock(),
    )
    warm_bm25_cache_if_configured(collection, "hybrid", 4)

    class _TimedRetriever:
        def retrieve(self, query_bundle):
            import time

            time.sleep(0.001)
            q = getattr(query_bundle, "query_str", "")
            return [_node_with_path(f"id-{hash(q) & 0xFF}", "docs/x.md", 0.5)]

    retriever = _TimedRetriever()
    baseline_latencies: list[float] = []
    expansion_latencies: list[float] = []

    for case in LABELED_MULTI_QUERY_FIXTURE[:5]:
        import time

        t0 = time.perf_counter()
        retriever.retrieve(type("QB", (), {"query_str": case["effective_query"]})())
        baseline_latencies.append((time.perf_counter() - t0) * 1000)

        trace: dict = {}
        t1 = time.perf_counter()
        run_multi_query_retrieval(
            base_retriever=retriever,
            variant_queries=[case["effective_query"], f"{case['effective_query']} alt"],
            trace=trace,
        )
        expansion_latencies.append((time.perf_counter() - t0) * 1000)
        assert trace["variant_retrieval_ms"] >= 0.0

    def _p95(values: list[float]) -> float:
        srt = sorted(values)
        idx = int(round(0.95 * (len(srt) - 1)))
        return srt[idx]

    hard_ms = _thresholds_for(resolve_query_surface(QueryOptions()), "cold").hard_ms
    delta_p95 = _p95(expansion_latencies) - _p95(baseline_latencies)
    assert delta_p95 <= hard_ms


def test_build_query_engine_flag_off_writes_trace_and_skips_expansion(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    _patch_mq_retrieval_settings(monkeypatch, enable_multi_query=False, multi_query_count=3)
    monkeypatch.setenv("ENABLE_REWRITE", "true")
    from app.config import reset_settings_cache

    reset_settings_cache()
    monkeypatch.setattr(
        "app.multi_query_expansion.get_settings",
        lambda: type("S", (), {"enable_rewrite": True})(),
    )

    expand_called = {"n": 0}

    def _expand_guard(*_a, **_k):
        expand_called["n"] += 1
        raise AssertionError("expand_queries must not run when flag off")

    monkeypatch.setattr("app.multi_query_expansion.expand_queries", _expand_guard)

    captured: dict = {}

    class _FakeRetriever:
        pass

    class _FakeEngine:
        _retriever = _FakeRetriever()

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": object(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", lambda cache_key, engine: None)
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: [])
    monkeypatch.setattr(
        retrieval,
        "build_query_engine_for_retrieval_mode",
        lambda **kwargs: captured.setdefault("engine", _FakeEngine()) or _FakeEngine(),
    )

    ctx = QueryContext(original_question="What is RAG?", rewritten_query="RAG overview")
    ctx.query_type = "qa"
    ctx.prompt_key = "qa"

    retrieval.build_query_engine("What is RAG?", QueryOptions(), query_context=ctx)

    mq = ctx.trace.get("multi_query_expansion") or {}
    assert mq.get("expansion_enabled") is False
    assert mq.get("expansion_skipped_reason") == "flag_off"
    assert expand_called["n"] == 0


def test_build_query_engine_multi_query_wraps_retriever_when_enabled(monkeypatch):
    patch_retrieval_faq_cache_enabled(monkeypatch)
    _patch_mq_retrieval_settings(
        monkeypatch,
        enable_multi_query=True,
        multi_query_count=3,
        rag_profile="quality",
        retrieval_mode="hybrid",
    )
    monkeypatch.setattr(
        "app.multi_query_expansion.get_settings",
        lambda: type("S", (), {"enable_rewrite": True})(),
    )
    monkeypatch.setattr(
        "app.multi_query_expansion.expand_queries",
        lambda effective_query, multi_query_count, trace: (
            [effective_query, "variant alt one", "variant alt two"],
            {
                **trace,
                "expansion_enabled": True,
                "expansion_ms": 12.0,
                "variant_count": 3,
                "variant_queries": ["preview"],
                "expansion_degraded": False,
            },
        ),
    )

    class _FakeRetriever:
        pass

    class _FakeEngine:
        def __init__(self):
            self._retriever = _FakeRetriever()

    fake_engine = _FakeEngine()

    monkeypatch.setattr(
        retrieval,
        "get_query_engine_cache_result",
        lambda cache_key: {"engine": None, "cache_latency_ms": 0.0},
    )
    monkeypatch.setattr(
        retrieval,
        "get_base_services",
        lambda: {"index": object(), "llm": object(), "quiz_llm": object(), "collection": object()},
    )
    monkeypatch.setattr(retrieval, "set_cached_query_engine", lambda cache_key, engine: None)
    monkeypatch.setattr(retrieval, "build_postprocessors", lambda params: [])
    monkeypatch.setattr(
        retrieval,
        "build_query_engine_for_retrieval_mode",
        lambda **kwargs: fake_engine,
    )

    ctx = QueryContext(original_question="Explain hybrid retrieval", rewritten_query="hybrid retrieval fusion")
    ctx.query_type = "qa"
    ctx.prompt_key = "qa"

    retrieval.build_query_engine("Explain hybrid retrieval", QueryOptions(), query_context=ctx)

    from app.multi_query_expansion import MultiQueryFusionRetriever

    assert isinstance(fake_engine._retriever, MultiQueryFusionRetriever)
    mq = ctx.trace["multi_query_expansion"]
    assert mq["expansion_enabled"] is True
    assert mq["variant_count"] == 3
    assert mq["expansion_ms"] == 12.0

