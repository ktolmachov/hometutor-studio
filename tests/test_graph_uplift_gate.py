"""Graph uplift metrics, gate evaluation, demotion router integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval_uplift import (
    build_graph_uplift_report,
    case_correctness_pass,
    evaluate_uplift_gate,
    LOCAL_UPLIFT_GATE_DEFAULTS,
)
from app.models import QueryContext, QueryOptions
from app.retrieval import resolve_query_execution_plan
from app.retrieval_router import (
    build_retrieval_routing_decision,
    resolve_rag_profile_for_pipeline,
)
from conftest import patch_retrieval_settings


def _sample_cases(profile: str, graph_applied: bool) -> list[dict]:
    base = {
        "id": "rel_001",
        "expected_doc_ids": ["ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md"],
        "retrieved_doc_ids": ["ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md"],
        "sources": [{"relative_path": "ИИ Агенты/урок 1 Введение в концепцию AI-агентов.md"}],
        "latency_ms": 100.0,
        "profile": profile,
        "graph_applied": graph_applied,
    }
    if graph_applied:
        base["graph_expansion"] = {
            "graph_evidence": [{"confidence": 0.9, "relation_type": "related"}],
        }
    return [base]


def test_uplift_gate_pass_and_fail_messages():
    quality = _sample_cases("quality", False)
    quality[0]["retrieved_doc_ids"] = []
    quality[0]["sources"] = []
    graph = _sample_cases("graph_aware", True)
    report = build_graph_uplift_report(
        quality_cases=quality,
        graph_aware_cases=graph,
        generation_id="gen_a",
        dataset_version="1.0",
        run_id="run_test",
    )
    gate_pass = evaluate_uplift_gate(report, LOCAL_UPLIFT_GATE_DEFAULTS, expected_generation_id="gen_a")
    assert gate_pass["passed"] is True

    weak_graph = _sample_cases("graph_aware", True)
    weak_graph[0]["latency_ms"] = 500.0
    report_fail = build_graph_uplift_report(
        quality_cases=quality,
        graph_aware_cases=weak_graph,
        generation_id="gen_a",
        run_id="run_fail",
    )
    gate_fail = evaluate_uplift_gate(report_fail, LOCAL_UPLIFT_GATE_DEFAULTS, expected_generation_id="gen_a")
    assert gate_fail["passed"] is False
    failed = gate_fail["failed_checks"]
    assert failed
    assert any(item.get("metric") for item in failed)
    assert any(item.get("threshold") is not None for item in failed)


def test_stale_generation_binding_fails_gate():
    report = build_graph_uplift_report(
        quality_cases=_sample_cases("quality", False),
        graph_aware_cases=_sample_cases("graph_aware", True),
        generation_id="gen_old",
        run_id="stale",
    )
    gate = evaluate_uplift_gate(report, LOCAL_UPLIFT_GATE_DEFAULTS, expected_generation_id="gen_new")
    assert gate["passed"] is False
    assert any(item.get("reason_key") == "stale_generation_binding" for item in gate["failed_checks"])


def test_case_correctness_rule():
    case = {
        "expected_doc_ids": ["ИИ Агенты/урок_2_как_агент_думает_и_действует.md"],
        "retrieved_doc_ids": ["data/ИИ Агенты/урок_2_как_агент_думает_и_действует.md"],
    }
    assert case_correctness_pass(case) is True


def test_demotion_latch_forces_quality_profile(monkeypatch, tmp_path):
    from app import config as app_config
    from app.metrics_slo import load_graph_route_demotion_state

    state_path = tmp_path / "graph_route_demotion_state.json"
    state_path.write_text(json.dumps({"demoted": True, "consecutive_failures": 3}), encoding="utf-8")
    monkeypatch.setattr(app_config, "DATA_DIR", tmp_path)

    assert load_graph_route_demotion_state()["demoted"] is True

    options = QueryOptions()
    ctx = QueryContext(
        original_question="Graph plan",
        query_options=options,
        query_type="learning_plan",
        classify_confidence=0.95,
        classify_method="heuristic",
    )
    patch_retrieval_settings(monkeypatch, rag_profile="graph_aware")
    plan = resolve_query_execution_plan(ctx.original_question, options, query_context=ctx)
    routing = ctx.trace["retrieval_routing"]
    assert routing["selected_profile"] == "graph_aware"
    assert routing["effective_profile"] == "quality"
    assert routing["fallback_reason"] == "graph_no_uplift_below_delta"
    assert routing["effective_graph_augmented"] is False
    assert plan.profile == "quality"


def test_route_demotion_skipped_on_manual_override(monkeypatch, tmp_path):
    from app import config as app_config
    from app.metrics_slo import record_route_demotion_skipped_event

    state_path = tmp_path / "graph_route_demotion_state.json"
    state_path.write_text(json.dumps({"demoted": True, "consecutive_failures": 3}), encoding="utf-8")
    monkeypatch.setattr(app_config, "DATA_DIR", tmp_path)

    events: list[dict] = []

    def _capture(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(
        "app.metrics_slo.record_route_demotion_skipped_event",
        lambda **kwargs: events.append(kwargs),
    )

    options = QueryOptions(rag_profile="graph_aware")
    ctx = QueryContext(
        original_question="Override graph",
        query_options=options,
        query_type="learning_plan",
        classify_confidence=0.95,
        classify_method="heuristic",
    )
    resolution = resolve_rag_profile_for_pipeline(ctx, options, None)
    decision = build_retrieval_routing_decision(ctx, resolution)
    assert decision.manual_override is True
    assert decision.selected_profile == "graph_aware"
    assert events


def test_corrupt_demotion_state_fail_safe(monkeypatch, tmp_path):
    from app import config as app_config
    from app.metrics_slo import load_graph_route_demotion_state

    state_path = tmp_path / "graph_route_demotion_state.json"
    state_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(app_config, "DATA_DIR", tmp_path)

    state = load_graph_route_demotion_state()
    assert state["demoted"] is False
    assert state.get("corrupt") is True

    options = QueryOptions()
    ctx = QueryContext(
        original_question="x",
        query_options=options,
        query_type="qa",
        classify_confidence=0.9,
        classify_method="heuristic",
    )
    resolution = resolve_rag_profile_for_pipeline(ctx, options, None)
    decision = build_retrieval_routing_decision(ctx, resolution)
    assert decision.signals.get("demotion_state_corrupt") is True


def test_profile_deadline_exceeded_demotes_to_quality():
    options = QueryOptions()
    ctx = QueryContext(
        original_question="slow",
        query_options=options,
        query_type="learning_plan",
        classify_confidence=0.95,
        classify_method="heuristic",
    )
    ctx.trace["profile_deadline_exceeded"] = True
    resolution = resolve_rag_profile_for_pipeline(ctx, options, None)
    decision = build_retrieval_routing_decision(ctx, resolution)
    assert decision.effective_profile == "quality"
    assert decision.fallback_reason == "profile_deadline_exceeded"


def test_check_gate_stale_generation_binding(tmp_path):
    from scripts import check_graph_expansion_gate as gate

    jsonl = tmp_path / "metrics.jsonl"
    jsonl.write_text(
        json.dumps(
            {
                "event_type": "request",
                "graph_expansion": {"ok": True, "graph_expansion_ms": 40.0, "extra_chunk_count": 2},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    uplift_path = tmp_path / "uplift.json"
    report = build_graph_uplift_report(
        quality_cases=_sample_cases("quality", False),
        graph_aware_cases=_sample_cases("graph_aware", True),
        generation_id="gen_report",
        run_id="gate_run",
    )
    uplift_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    out, rc = gate.run_gate(
        jsonl_path=jsonl,
        limit=0,
        profile="local",
        uplift_report_path=uplift_path,
        generation_id="gen_other",
    )
    assert rc == 2
    assert out["uplift_gate"]["passed"] is False
