"""Unit tests for multi-query expansion (variant count, dedup, degradation)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.config import RetrievalSettings, reset_settings_cache
from app.models import QueryContext, QueryExecutionPlan, QueryOptions
from app.multi_query_expansion import (
    expand_queries,
    merge_deduped_candidates,
    prepare_multi_query_expansion,
    should_expand_queries,
)
from app.prompts.multi_query_expansion import parse_multi_query_variants
from app.query_routing import KEYWORD_QUERY
from conftest import patch_retrieval_settings


def _patch_mq_retrieval_settings(monkeypatch, **kwargs) -> RetrievalSettings:
    settings = patch_retrieval_settings(monkeypatch, **kwargs)
    monkeypatch.setattr("app.config.get_retrieval_settings", lambda: settings)
    monkeypatch.setattr("app.multi_query_expansion.get_retrieval_settings", lambda: settings)
    return settings


def _node(chunk_id: str, score: float = 0.5) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        node=SimpleNamespace(
            text=f"text-{chunk_id}",
            id_=chunk_id,
            node_id=chunk_id,
            metadata={"chunk_id": chunk_id},
        ),
    )


def _plan(**kwargs) -> QueryExecutionPlan:
    defaults = dict(
        query_type="qa",
        prompt_key="qa",
        retrieval_mode="hybrid",
        enable_reranker=True,
        similarity_top_k=4,
        rerank_top_n=4,
        rerank_model="test",
        split_strategy="sentence_splitter",
        window_size=2,
        profile="quality",
        homework_mode=False,
        assistance_level=None,
        query_engine_cache_policy="shared",
        faq_cache_eligible=False,
        faq_cache_skip_reason=None,
        doc_top_k=None,
    )
    defaults.update(kwargs)
    return QueryExecutionPlan(**defaults)


def test_parse_multi_query_variants_json_and_newlines():
    raw_json = '["variant one", "variant two", "variant three"]'
    parsed = parse_multi_query_variants(raw_json, max_count=4)
    assert len(parsed) == 3

    raw_lines = "alpha query\nbeta query\nalpha query\n"
    parsed_lines = parse_multi_query_variants(raw_lines, max_count=3)
    assert parsed_lines == ["alpha query", "beta query"]


def test_parse_multi_query_variants_clamps_to_two_four():
    many = parse_multi_query_variants(
        '["a","b","c","d","e"]',
        max_count=4,
    )
    assert 2 <= len(many) <= 4


def test_merge_deduped_candidates_max_score_and_tie_break():
    variant_a = [_node("c1", 0.4), _node("c2", 0.9)]
    variant_b = [_node("c1", 0.8), _node("c3", 0.3)]
    merged = merge_deduped_candidates([variant_a, variant_b])
    ids = [_n.node.metadata["chunk_id"] for _n in merged]
    assert ids == ["c2", "c1", "c3"]
    c1 = next(n for n in merged if n.node.metadata["chunk_id"] == "c1")
    assert c1.score == 0.8


def test_merge_deduped_candidates_zero_duplicate_chunk_id():
    nodes = [_node("dup", 0.5), _node("dup", 0.7), _node("other", 0.2)]
    merged = merge_deduped_candidates([nodes])
    chunk_ids = [_n.node.metadata["chunk_id"] for _n in merged]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_should_expand_queries_gating_matrix(monkeypatch):
    _patch_mq_retrieval_settings(monkeypatch, enable_multi_query=True, multi_query_count=3)
    monkeypatch.setattr("app.multi_query_expansion.get_settings", lambda: SimpleNamespace(enable_rewrite=True))

    ctx = QueryContext(original_question="What is RAG?", rewritten_query="RAG definition")
    ctx.query_type = "qa"

    ok, reason = should_expand_queries(execution_plan=_plan(), query_context=ctx)
    assert ok is True
    assert reason is None

    _patch_mq_retrieval_settings(monkeypatch, enable_multi_query=False, multi_query_count=3)
    ok_off, reason_off = should_expand_queries(execution_plan=_plan(), query_context=ctx)
    assert ok_off is False
    assert reason_off == "flag_off"

    _patch_mq_retrieval_settings(monkeypatch, enable_multi_query=True, multi_query_count=3)
    monkeypatch.setattr("app.multi_query_expansion.get_settings", lambda: SimpleNamespace(enable_rewrite=False))
    ok_rw, reason_rw = should_expand_queries(execution_plan=_plan(), query_context=ctx)
    assert ok_rw is False
    assert reason_rw == "rewrite_off"

    monkeypatch.setattr("app.multi_query_expansion.get_settings", lambda: SimpleNamespace(enable_rewrite=True))
    ok_kw, reason_kw = should_expand_queries(
        execution_plan=_plan(query_type=KEYWORD_QUERY, retrieval_mode="bm25_only"),
        query_context=ctx,
    )
    assert ok_kw is False
    assert reason_kw == "keyword_path"

    ctx_overview = QueryContext(original_question="Overview", rewritten_query="Overview topic")
    ctx_overview.query_type = "overview"
    ctx_overview.subquestions = ["sub1"]
    ok_sub, reason_sub = should_expand_queries(execution_plan=_plan(query_type="overview"), query_context=ctx_overview)
    assert ok_sub is False
    assert reason_sub == "subquestions_active"


def test_expand_queries_dedupes_variant_strings(monkeypatch):
    trace: dict = {}
    monkeypatch.setattr(
        "app.multi_query_expansion.complete_with_resilience",
        lambda *_a, **_k: SimpleNamespace(text='["RAG basics", "rag basics", "retrieval augmented generation"]'),
    )
    monkeypatch.setattr("app.multi_query_expansion.get_rewrite_llm", lambda: object())
    variants, out_trace = expand_queries(
        "What is RAG?",
        multi_query_count=3,
        trace=trace,
    )

    assert variants[0] == "What is RAG?"
    assert out_trace["expansion_enabled"] is True
    assert 2 <= out_trace["variant_count"] <= 4


def test_expand_queries_llm_failure_degrades_to_anchor(monkeypatch):
    trace: dict = {}
    monkeypatch.setattr("app.multi_query_expansion.get_rewrite_llm", lambda: object())

    def _boom(*_a, **_k):
        raise RuntimeError("llm down")

    monkeypatch.setattr("app.multi_query_expansion.complete_with_resilience", _boom)
    variants, out_trace = expand_queries(
        "Anchor question",
        multi_query_count=3,
        trace=trace,
    )
    assert variants == ["Anchor question"]
    assert out_trace["expansion_degraded"] is True
    assert out_trace["expansion_enabled"] is False


def test_prepare_multi_query_expansion_flag_off_passthrough(monkeypatch):
    _patch_mq_retrieval_settings(monkeypatch, enable_multi_query=False, multi_query_count=3)
    monkeypatch.setattr("app.multi_query_expansion.get_settings", lambda: SimpleNamespace(enable_rewrite=True))
    ctx = QueryContext(original_question="Q", rewritten_query="Q rewritten")
    ctx.query_type = "qa"
    variants, trace = prepare_multi_query_expansion(
        execution_plan=_plan(),
        query_context=ctx,
        options=QueryOptions(),
    )
    assert variants is None
    assert trace["expansion_enabled"] is False
    assert trace["expansion_skipped_reason"] == "flag_off"


def test_prepare_multi_query_expansion_budget_precheck_degrades(monkeypatch):
    _patch_mq_retrieval_settings(monkeypatch, enable_multi_query=True, multi_query_count=4)
    monkeypatch.setattr("app.multi_query_expansion.get_settings", lambda: SimpleNamespace(enable_rewrite=True))
    monkeypatch.setattr(
        "app.multi_query_expansion.expand_queries",
        lambda *_a, **_k: (
            ["anchor", "v1", "v2", "v3"],
            {
                "expansion_enabled": True,
                "expansion_ms": 9000.0,
                "variant_count": 4,
            },
        ),
    )
    monkeypatch.setattr(
        "app.multi_query_expansion._budget_allows_variant_fanout",
        lambda *_a, **_k: False,
    )
    ctx = QueryContext(original_question="Q", rewritten_query="Q rewritten")
    ctx.query_type = "qa"
    variants, trace = prepare_multi_query_expansion(
        execution_plan=_plan(),
        query_context=ctx,
        options=QueryOptions(),
    )
    assert variants is None
    assert trace["expansion_skipped_reason"] == "budget_exceeded"
    assert trace["expansion_degraded"] is True


def test_expand_queries_records_expansion_ms_not_llm_stage(monkeypatch):
    """Timing lives in trace expansion_ms (retrieval-tier), separate from primary chat llm_ms."""
    trace: dict = {}
    monkeypatch.setattr("app.multi_query_expansion.get_rewrite_llm", lambda: object())
    monkeypatch.setattr(
        "app.multi_query_expansion.complete_with_resilience",
        lambda *_a, **_k: SimpleNamespace(text='["variant a", "variant b"]'),
    )
    _variants, out_trace = expand_queries(
        "Question",
        multi_query_count=3,
        trace=trace,
    )
    assert "expansion_ms" in out_trace
    assert isinstance(out_trace["expansion_ms"], float)
    reset_settings_cache()
