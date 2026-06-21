from app.models import QueryContext, QueryOptions
from app.retrieval import resolve_query_execution_plan
from app.retrieval_router import (
    build_retrieval_routing_decision,
    resolve_rag_profile_for_pipeline,
)
from conftest import patch_retrieval_settings


def test_profile_resolver_phase_does_not_touch_retrieval_trace():
    """ADR‑021a A1: resolve_rag_profile_for_pipeline без записи retrieval_routing."""
    options = QueryOptions()
    ctx = QueryContext(
        original_question="x",
        query_options=options,
        query_type="qa",
        classify_confidence=0.2,
        classify_method="heuristic",
    )
    resolve_rag_profile_for_pipeline(ctx, options, None)
    assert "retrieval_routing" not in ctx.trace


def test_router_decision_from_resolution_matches_resolve_retrieval_routing_contract():
    options = QueryOptions(rag_profile="graph_aware")
    ctx = QueryContext(
        original_question="Q",
        query_options=options,
        query_type="learning_plan",
        classify_confidence=0.95,
        classify_method="heuristic",
    )
    resolution = resolve_rag_profile_for_pipeline(ctx, options, None)
    decision = build_retrieval_routing_decision(ctx, resolution)
    assert decision.selected_profile == "graph_aware"
    assert decision.effective_retrieval_mode == "hybrid"
    assert decision.graph_augmented_requested is True


def test_explicit_profile_writes_retrieval_routing_trace():
    options = QueryOptions(rag_profile="quality")
    ctx = QueryContext(
        original_question="Explain retrieval",
        query_options=options,
        query_type="qa",
        classify_confidence=0.91,
        classify_method="heuristic",
    )

    plan = resolve_query_execution_plan(ctx.original_question, options, query_context=ctx)

    routing = ctx.trace["retrieval_routing"]
    assert routing["selected_profile"] == "quality"
    assert routing["effective_profile"] == "quality"
    assert routing["effective_retrieval_mode"] == "hybrid"
    assert routing["manual_override"] is True
    assert routing["classify_query_type"] == "qa"
    assert routing["classify_confidence"] == 0.91
    assert plan.profile == "quality"
    assert plan.retrieval_mode == "hybrid"


def test_auto_low_confidence_falls_back_to_quality_trace(monkeypatch):
    patch_retrieval_settings(monkeypatch, rag_profile="fast", retrieval_mode="vector_only")
    options = QueryOptions()
    ctx = QueryContext(
        original_question="Maybe unclear",
        query_options=options,
        query_type="qa",
        classify_confidence=0.2,
        classify_method="llm",
    )

    plan = resolve_query_execution_plan(ctx.original_question, options, query_context=ctx)

    routing = ctx.trace["retrieval_routing"]
    assert routing["selected_profile"] == "fast"
    assert routing["effective_profile"] == "quality"
    assert routing["fallback_reason"] == "low_confidence"
    assert routing["profile_resolved_from"] == "rule"
    assert routing["manual_override"] is False
    assert plan.profile == "quality"


def test_graph_aware_profile_records_disabled_graph_fallback():
    options = QueryOptions(rag_profile="graph_aware")
    ctx = QueryContext(
        original_question="Build a graph-aware plan",
        query_options=options,
        query_type="learning_plan",
        classify_confidence=0.95,
        classify_method="heuristic",
    )

    plan = resolve_query_execution_plan(ctx.original_question, options, query_context=ctx)

    routing = ctx.trace["retrieval_routing"]
    assert routing["selected_profile"] == "graph_aware"
    assert routing["effective_profile"] == "graph_aware"
    assert routing["graph_augmented_requested"] is True
    assert routing["effective_graph_augmented"] is False
    assert routing["fallback_reason"] == "graph_augmented_disabled"
    assert plan.retrieval_mode == "hybrid"
