import importlib
import json

import app.metrics as metrics


def test_get_metrics_includes_percentiles_and_rates():
    module = importlib.reload(metrics)

    module.record_request(
        request_id="r1",
        question="q1",
        query_type="qa",
        total_answer_ms=100.0,
        pipeline_ms=20.0,
        engine_acquire_ms=5.0,
        query_execute_ms=60.0,
        source_count=2,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
        quality_checks={
            "checks": {
                "answer_not_empty": True,
                "has_sources": True,
                "answer_length_in_range": True,
                "no_fallback_with_sources": True,
                "min_source_score_ok": True,
            }
        },
    )
    module.record_request(
        request_id="r2",
        question="q2",
        query_type="qa",
        total_answer_ms=300.0,
        pipeline_ms=40.0,
        engine_acquire_ms=7.0,
        query_execute_ms=120.0,
        source_count=0,
        fallback_applied=True,
        estimated_cost_usd=0.002,
        answer_empty=True,
        quality_checks={
            "checks": {
                "answer_not_empty": False,
                "has_sources": False,
                "answer_length_in_range": True,
                "no_fallback_with_sources": True,
                "min_source_score_ok": False,
            }
        },
    )

    result = module.get_metrics()

    assert result["requests_total"] == 2
    assert result["fallback_total"] == 1
    assert result["fallback_rate"] == 0.5
    assert result["requests_without_sources_total"] == 1
    assert result["requests_without_sources_rate"] == 0.5
    assert result["empty_answers_total"] == 1
    assert result["empty_answers_rate"] == 0.5
    assert result["latency_ms"]["p50_total_answer_ms"] == 100.0
    assert result["latency_ms"]["p95_total_answer_ms"] == 300.0
    assert result["latency_ms"]["p99_total_answer_ms"] == 300.0
    assert result["latency_ms"]["p50_pipeline_ms"] == 20.0
    assert result["estimated_cost_usd"]["total"] == 0.003
    assert result["quality_checks"]["requests_evaluated"] == 2
    assert result["quality_checks"]["failure_counts"]["answer_not_empty"] == 1
    assert result["quality_checks"]["failure_counts"]["has_sources"] == 1
    assert result["quality_checks"]["failure_counts"]["min_source_score_ok"] == 1
    assert result["quality_checks"]["failure_rates"]["answer_not_empty"] == 0.5
    assert result["graph_expansion"]["events_total"] == 0


def test_aggregate_graph_expansion_from_request_events():
    module = importlib.reload(metrics)
    events = [
        {
            "event_type": "request",
            "query_type": "qa",
            "graph_expansion": {"graph_expansion_ms": 10.0, "skipped": True, "reason": "x"},
        },
        {
            "event_type": "request",
            "query_type": "synthesis",
            "graph_expansion": {"ok": True, "graph_expansion_ms": 30.0, "extra_chunk_count": 2},
        },
    ]
    r = module.aggregate_graph_expansion_from_request_events(events)
    assert r["events_total"] == 2
    assert r["skipped_total"] == 1
    assert r["applied_total"] == 1
    assert r["avg_extra_chunks_when_applied"] == 2.0
    assert r["applied_rate"] == 0.5
    assert r["skipped_rate"] == 0.5
    assert r["error_rate"] == 0.0
    assert r["unknown_outcome_rate"] == 0.0
    assert r["skip_reasons"] == {"x": 1}
    assert r["error_types"] == {}
    assert r["by_query_type"]["qa"]["skipped_total"] == 1
    assert r["by_query_type"]["synthesis"]["applied_total"] == 1


def test_evaluate_slo_alerts_includes_learner_rehydrated_rate_alert(monkeypatch, tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store_slo.jsonl"
    module.record_request(
        request_id="slo1",
        question="q",
        query_type="qa",
        total_answer_ms=100.0,
        pipeline_ms=20.0,
        engine_acquire_ms=3.0,
        query_execute_ms=50.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
    )

    class _S:
        slo_max_fallback_rate = None
        slo_min_source_coverage = None
        slo_max_p95_latency_ms = None
        slo_max_avg_cost_usd = None
        slo_min_judge_score = None
        slo_max_learner_rehydrated_rate = 0.2
        slo_anomaly_recent_window = 0
        slo_anomaly_sigma = 2.0
        alert_webhook_url = None
        index_registry_path = "index_registry.json"
        index_registry_lock_path = "index_registry.json.lock"
        active_index_state_path = "active_index.json"
        collection_name = "home_rag"
        summary_collection_name = "home_rag_summaries"
        metrics_store_path = "logs/metrics_store.jsonl"

    monkeypatch.setattr("app.config.get_settings", lambda: _S())
    monkeypatch.setattr(
        "app.learner_model_service.get_learner_profile_migration_metrics",
        lambda limit=20000: {"window_size": 10, "rehydrated_rate": 0.4},
    )

    out = module.evaluate_slo_alerts(limit_events=50)
    assert any(a.get("metric") == "learner_rehydrated_rate" for a in out["alerts"])
    assert out["observed"]["learner_migration"]["rehydrated_rate"] == 0.4


def test_graph_expansion_metrics_latency_and_quality(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_ge.jsonl"

    module.record_request(
        request_id="ge1",
        question="q1",
        query_type="synthesis",
        total_answer_ms=100.0,
        pipeline_ms=20.0,
        engine_acquire_ms=1.0,
        query_execute_ms=50.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
        pipeline_trace={
            "schema_version": 1,
            "effective_query": "x",
            "effective_query_source": "y",
            "graph_expansion": {
                "skipped": True,
                "reason": "query_type",
                "graph_expansion_ms": 12.5,
            },
        },
    )
    module.record_request(
        request_id="ge2",
        question="q2",
        query_type="synthesis",
        total_answer_ms=200.0,
        pipeline_ms=30.0,
        engine_acquire_ms=2.0,
        query_execute_ms=60.0,
        source_count=2,
        fallback_applied=False,
        estimated_cost_usd=0.002,
        answer_empty=False,
        pipeline_trace={
            "schema_version": 1,
            "effective_query": "x",
            "effective_query_source": "y",
            "graph_expansion": {
                "ok": True,
                "graph_expansion_ms": 40.0,
                "extra_chunk_count": 3,
                "concepts_touched": 5,
                "hops_applied": 2,
            },
        },
    )

    gm = module.get_metrics()
    ge = gm["graph_expansion"]
    assert ge["events_total"] == 2
    assert ge["skipped_total"] == 1
    assert ge["applied_total"] == 1
    assert ge["avg_extra_chunks_when_applied"] == 3.0
    assert ge["applied_rate"] == 0.5
    assert ge["skipped_rate"] == 0.5
    assert ge["error_rate"] == 0.0
    assert ge["unknown_outcome_rate"] == 0.0
    assert ge["p50_graph_expansion_ms"] == 12.5
    assert ge["p95_graph_expansion_ms"] == 40.0
    assert ge["skip_reasons"] == {"query_type": 1}
    assert ge["by_query_type"]["synthesis"]["events_total"] == 2
    assert ge["by_query_type"]["synthesis"]["skip_reasons"] == {"query_type": 1}

    summary = module.summarize_metrics_store(limit=10)
    assert summary is not None
    assert summary["graph_expansion"]["events_total"] == 2
    assert summary["graph_expansion"]["applied_total"] == 1
    assert summary["graph_expansion"]["by_query_type"]["synthesis"]["applied_total"] == 1

    lines = module.METRICS_STORE_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    p0 = json.loads(lines[0])
    assert p0.get("graph_expansion", {}).get("skipped") is True
    assert p0["graph_expansion"]["graph_expansion_ms"] == 12.5
    p1 = json.loads(lines[1])
    assert p1["graph_expansion"]["ok"] is True
    assert p1["graph_expansion"]["extra_chunk_count"] == 3


def test_graph_expansion_metrics_capture_error_types_and_query_breakdown(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_ge_errors.jsonl"

    module.record_request(
        request_id="ge-error",
        question="q",
        query_type="learning_plan",
        total_answer_ms=90.0,
        pipeline_ms=15.0,
        engine_acquire_ms=1.0,
        query_execute_ms=45.0,
        source_count=0,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
        pipeline_trace={
            "schema_version": 1,
            "effective_query": "x",
            "effective_query_source": "y",
            "graph_expansion": {
                "ok": False,
                "error": "kg unavailable",
                "error_type": "RuntimeError",
                "graph_expansion_ms": 7.5,
            },
        },
    )

    ge = module.get_metrics()["graph_expansion"]
    assert ge["error_total"] == 1
    assert ge["error_types"] == {"runtimeerror": 1}
    assert ge["by_query_type"]["learning_plan"]["error_total"] == 1


def test_summarize_metrics_store_aggregates_request_events(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_request(
        request_id="r1",
        question="q1",
        query_type="qa",
        total_answer_ms=100.0,
        pipeline_ms=20.0,
        engine_acquire_ms=5.0,
        query_execute_ms=60.0,
        source_count=2,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
        quality_checks={"checks": {"answer_not_empty": True, "has_sources": True}},
    )
    module.record_request(
        request_id="r2",
        question="q2",
        query_type="overview",
        total_answer_ms=300.0,
        pipeline_ms=40.0,
        engine_acquire_ms=7.0,
        query_execute_ms=120.0,
        source_count=0,
        fallback_applied=True,
        estimated_cost_usd=0.002,
        answer_empty=True,
        quality_checks={"checks": {"answer_not_empty": False, "has_sources": False}},
    )

    summary = module.summarize_metrics_store(limit=10)

    assert summary is not None
    assert summary["window_size"] == 2
    assert summary["fallback_rate"] == 0.5
    assert summary["requests_without_sources_rate"] == 0.5
    assert summary["empty_answers_rate"] == 0.5
    assert summary["latency_ms"]["p95_total_answer_ms"] == 300.0
    assert summary["estimated_cost_usd"]["total"] == 0.003
    assert summary["quality_checks"]["requests_evaluated"] == 2
    assert summary["quality_checks"]["failure_counts"]["answer_not_empty"] == 1
    assert summary["quality_checks"]["failure_counts"]["has_sources"] == 1
    assert summary["graph_expansion"]["events_total"] == 0


def test_metrics_store_persists_request_events(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_request(
        request_id="r-store",
        question="hello world",
        query_type="qa",
        total_answer_ms=123.0,
        pipeline_ms=20.0,
        engine_acquire_ms=4.0,
        query_execute_ms=80.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.0001,
        answer_empty=False,
        quality_checks={"checks": {"answer_not_empty": True}},
        pipeline_trace={"classify_step_ms": 5.0},
        token_usage={"stages": {"generation": {"total_tokens": 42}}},
        retrieval_trace={"retrieval_mode": "vector_only", "returned_source_count": 1},
    )

    assert module.METRICS_STORE_PATH.exists()
    lines = module.METRICS_STORE_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["request_id"] == "r-store"
    assert payload["event_type"] == "request"
    assert payload["pipeline_trace"]["classify_step_ms"] == 5.0
    assert payload["retrieval_trace"]["retrieval_mode"] == "vector_only"

    result = module.get_metrics_store(request_id="r-store", limit=5)
    assert result["total"] == 1
    assert result["items"][0]["request_id"] == "r-store"
    assert result["items"][0]["retrieval_trace"]["returned_source_count"] == 1


def test_record_error_tracks_provider_and_runtime_breakdown(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_error(
        request_id="req-provider",
        endpoint="/ask",
        error_kind="provider",
        error_type="ValueError",
        status_code=503,
        message="OPENAI_API_KEY missing",
    )
    module.record_error(
        request_id="req-runtime",
        endpoint="/topics",
        error_kind="runtime",
        error_type="RuntimeError",
        status_code=500,
        message="unexpected failure",
    )

    result = module.get_metrics()

    assert result["errors_total"] == 2
    assert result["error_breakdown"]["by_kind"]["provider"] == 1
    assert result["error_breakdown"]["by_kind"]["runtime"] == 1
    assert result["error_breakdown"]["by_type"]["ValueError"] == 1
    assert result["error_breakdown"]["by_endpoint"]["/ask"] == 1
    assert result["last_error"]["endpoint"] == "/topics"

    store = module.get_metrics_store(limit=10)
    error_items = [item for item in store["items"] if item["event_type"] == "error"]
    assert len(error_items) == 2
    assert error_items[0]["error_kind"] in {"provider", "runtime"}


def test_get_cost_dashboard_groups_by_query_type_and_top_requests(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_request(
        request_id="r1",
        question="cheap qa",
        query_type="qa",
        total_answer_ms=120.0,
        pipeline_ms=20.0,
        engine_acquire_ms=4.0,
        query_execute_ms=80.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
    )
    module.record_request(
        request_id="r2",
        question="expensive synthesis",
        query_type="synthesis",
        total_answer_ms=450.0,
        pipeline_ms=80.0,
        engine_acquire_ms=6.0,
        query_execute_ms=250.0,
        source_count=3,
        fallback_applied=False,
        estimated_cost_usd=0.01,
        answer_empty=False,
    )
    module.record_request(
        request_id="r3",
        question="second qa",
        query_type="qa",
        total_answer_ms=150.0,
        pipeline_ms=30.0,
        engine_acquire_ms=5.0,
        query_execute_ms=95.0,
        source_count=2,
        fallback_applied=False,
        estimated_cost_usd=0.002,
        answer_empty=False,
    )

    result = module.get_cost_dashboard(limit=10, top_n=2)

    assert result["window_size"]["requests"] == 3
    assert result["window_size"]["ingestion_runs"] == 0
    assert result["query_estimated_cost_usd"]["total"] == 0.013
    assert result["query_estimated_cost_usd"]["avg_per_request"] == round(0.013 / 3, 8)
    assert result["query_estimated_cost_usd"]["p95_per_request"] == 0.01
    assert result["by_query_type"]["qa"]["count"] == 2
    assert result["by_query_type"]["qa"]["total_usd"] == 0.003
    assert result["by_query_type"]["synthesis"]["avg_usd"] == 0.01
    assert result["top_expensive_requests"][0]["request_id"] == "r2"
    assert result["ingestion_estimated_cost_usd"]["total"] == 0.0
    assert result["projections"]["per_100_requests_usd"] == round((0.013 / 3) * 100, 6)


def test_get_cost_dashboard_includes_ingestion_runs(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_ingestion_run(
        run_type="full_reindex",
        total_files=10,
        processed_files=10,
        unique_doc_ids=8,
        nodes_count=42,
        summary_documents=8,
        duration_sec=12.5,
        estimated_cost_usd={
            "metadata_enrichment": 0.08,
            "summary_generation": 0.12,
            "total": 0.2,
        },
        token_usage={"total": {"prompt_tokens": 1000, "completion_tokens": 400, "total_tokens": 1400}},
        enrichment_stats={"metadata_enrichment_calls": 8, "summary_calls": 8},
    )

    result = module.get_cost_dashboard(limit=10, top_n=3)

    assert result["window_size"]["ingestion_runs"] == 1
    assert result["window_size"]["reindex_runs"] == 1
    assert result["ingestion_estimated_cost_usd"]["total"] == 0.2
    assert result["ingestion_estimated_cost_usd"]["full_reindex_total"] == 0.2
    assert result["ingestion_estimated_cost_usd"]["last_run"]["run_type"] == "full_reindex"


def test_get_cost_dashboard_rollups_stage_costs(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_request(
        request_id="s1",
        question="q",
        query_type="qa",
        total_answer_ms=100.0,
        pipeline_ms=10.0,
        engine_acquire_ms=2.0,
        query_execute_ms=50.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.01,
        estimated_cost_stages_usd={
            "classify": 0.001,
            "rewrite": 0.002,
            "retrieval": 0.003,
            "generation": 0.004,
            "judge": None,
        },
        answer_empty=False,
    )
    result = module.get_cost_dashboard(limit=10, top_n=3)
    by_stage = result["estimated_cost_by_stage_usd"]
    assert by_stage["classify"]["total_usd"] == 0.001
    assert by_stage["retrieval"]["samples"] == 1
    assert by_stage["generation"]["avg_per_request"] == 0.004


def test_get_quality_metrics_deterministic_and_judge(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_request(
        request_id="q1",
        question="q",
        query_type="qa",
        total_answer_ms=80.0,
        pipeline_ms=10.0,
        engine_acquire_ms=2.0,
        query_execute_ms=40.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.001,
        answer_empty=False,
        quality_checks={
            "checks": {
                "answer_not_empty": True,
                "has_sources": True,
                "answer_length_in_range": True,
                "no_fallback_with_sources": True,
                "min_source_score_ok": True,
            },
            "passed": True,
        },
    )
    module.record_quality_judge(
        request_id="q1",
        scores={"faithfulness": 0.85, "answer_relevancy": 0.9},
        model="gpt-4o-mini",
    )

    qm = module.get_quality_metrics(limit=10)
    assert qm["deterministic"]["requests_with_checks"] == 1
    assert qm["deterministic"]["pass_rate"] == 1.0
    assert qm["judge"]["samples_total"] == 1
    assert qm["judge"]["errors_total"] == 0
    assert qm["judge"]["avg_scores"]["faithfulness"] == 0.85


def test_get_metrics_dashboard_sqlite_buckets_and_cache(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"
    module.METRICS_DASHBOARD_DB_PATH = tmp_path / "metrics_dashboard.db"

    module.record_request(
        request_id="d1",
        question="q1",
        query_type="qa",
        total_answer_ms=100.0,
        pipeline_ms=20.0,
        engine_acquire_ms=1.0,
        query_execute_ms=50.0,
        source_count=2,
        fallback_applied=False,
        estimated_cost_usd=0.01,
        answer_empty=False,
        quality_checks={"checks": {"answer_not_empty": True, "has_sources": True}, "passed": True},
    )
    module.record_request(
        request_id="d2",
        question="q2",
        query_type="qa",
        total_answer_ms=200.0,
        pipeline_ms=30.0,
        engine_acquire_ms=1.0,
        query_execute_ms=80.0,
        source_count=1,
        fallback_applied=False,
        estimated_cost_usd=0.02,
        answer_empty=False,
    )
    module.record_quality_judge(
        request_id="d1",
        scores={"faithfulness": 0.7},
        model="gpt-4o-mini",
    )

    past = {
        "schema_version": 1,
        "event_type": "request",
        "timestamp": "2020-01-01T10:00:00+00:00",
        "request_id": "old",
        "query_type": "qa",
        "question_preview": "old",
        "source_count": 1,
        "fallback_applied": False,
        "answer_empty": False,
        "latency_ms": {"pipeline_ms": 5.0, "total_answer_ms": 50.0},
        "estimated_cost_usd": 0.001,
    }
    with open(module.METRICS_STORE_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(past, ensure_ascii=False) + "\n")

    r1 = module.get_metrics_dashboard(limit_events=50)
    assert r1["summary"]["source"] == "sqlite"
    assert r1["summary"]["events_window_requests"] >= 3
    daily_ids = {b["bucket_id"] for b in r1["daily"]}
    assert len(daily_ids) >= 2
    r2 = module.get_metrics_dashboard(limit_events=50)
    assert r2["daily"] == r1["daily"]

    any_judge = any(b.get("judge_avg_scores") for b in r1["daily"])
    assert any_judge


def test_get_knowledge_workflow_metrics_aggregates(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"

    module.record_knowledge_workflow_event(
        action="qa_answer_with_sources",
        knowledge_product_trace={"documents_used_count": 2},
        payload={"source_nodes": 3},
    )
    module.record_knowledge_workflow_event(
        action="answer_to_topic_open",
        knowledge_product_trace={"topic_id": "t1", "working_set_paths": ["a.md"]},
    )
    module.record_knowledge_workflow_event(
        action="topics_synthesis_start",
        knowledge_product_trace={"synthesis_launch_method": "by_topic"},
    )
    module.record_knowledge_workflow_event(
        action="topics_synthesis_complete",
        knowledge_product_trace={
            "documents_used_count": 4,
            "working_set_paths": ["a.md", "b.md", "c.md", "d.md"],
        },
    )

    out = module.get_knowledge_workflow_metrics(limit_events=100)
    assert out["window_size"] == 4
    assert out["conversion"]["denominator_qa_with_sources"] == 1
    assert out["conversion"]["answer_to_topic_open_rate"] == 1.0
    assert out["topics_synthesis"]["starts"] == 1
    assert out["topics_synthesis"]["completes"] == 1
    assert out["topics_synthesis"]["completion_rate"] == 1.0
    assert out["working_set_documents"]["avg_documents_on_completed_synthesis"] == 4.0


def test_check_pipeline_trace_schema_ok_and_legacy():
    assert metrics.check_pipeline_trace_schema(None)["ok"] is True
    assert metrics.check_pipeline_trace_schema(
        {
            "schema_version": metrics.PIPELINE_TRACE_SCHEMA_VERSION,
            "effective_query": "What is RAG?",
            "effective_query_source": "original",
        }
    )["ok"] is True
    legacy = metrics.check_pipeline_trace_schema({"classify_step_ms": 1.0})
    assert legacy["ok"] is False
    assert legacy["note"] == "missing_schema_version"
    missing_keys = metrics.check_pipeline_trace_schema(
        {"schema_version": metrics.PIPELINE_TRACE_SCHEMA_VERSION}
    )
    assert missing_keys["ok"] is False
    assert missing_keys["note"] == "missing_required_keys"
    assert "effective_query" in missing_keys["missing_keys"]


def test_check_metrics_store_line_schema():
    assert metrics.check_metrics_store_line_schema({"schema_version": metrics.METRICS_STORE_SCHEMA_VERSION})["ok"] is True
    assert metrics.check_metrics_store_line_schema({})["ok"] is False


def test_check_retrieval_trace_schema():
    assert metrics.check_retrieval_trace_schema(
        {
            "schema_version": metrics.RETRIEVAL_TRACE_SCHEMA_VERSION,
            "retrieval_mode": "vector_only",
            "query_type": "qa",
            "effective_query": "What is RAG?",
            "effective_query_source": "original",
            "cache_hit": False,
            "returned_source_count": 1,
        }
    )["ok"] is True
    missing_keys = metrics.check_retrieval_trace_schema(
        {"schema_version": metrics.RETRIEVAL_TRACE_SCHEMA_VERSION}
    )
    assert missing_keys["ok"] is False
    assert missing_keys["note"] == "missing_required_keys"
    assert "retrieval_mode" in missing_keys["missing_keys"]


def test_compact_graph_expansion_preserves_weak_counters():
    from app.metrics_graph_expansion import compact_graph_expansion_for_metrics

    compact = compact_graph_expansion_for_metrics(
        {
            "graph_expansion_ms": 1.1,
            "weak_graph_evidence_count": 2,
            "graph_evidence": [{"relation_id": "ab"}],
        }
    )
    assert compact is not None
    assert compact.get("weak_graph_evidence_count") == 2
    assert compact.get("graph_evidence_items") == 1


def test_route_demotion_aggregate_weighted(tmp_path, monkeypatch):
    import app.metrics_core as metrics_core

    target = tmp_path / "dem.jsonl"
    monkeypatch.setattr(metrics, "METRICS_STORE_PATH", target)
    monkeypatch.setattr(metrics_core, "METRICS_STORE_PATH", target)

    from app.metrics_slo import aggregate_route_demotion_from_store, record_route_demotion_event

    record_route_demotion_event(
        demoted_from="graph_aware",
        demoted_to="quality",
        reason="unit_test",
        route_demotion_count=4,
    )
    agg = aggregate_route_demotion_from_store(limit_lines=500)
    assert agg["events_total"] == 1
    assert agg["weighted_total"] == 4
