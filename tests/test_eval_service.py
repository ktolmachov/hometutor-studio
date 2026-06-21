import os

import pytest

import app.eval_service as eval_service
from app.config import reset_settings_cache


def test_eval_max_workers_clamped():
    old = os.environ.get("EVAL_MAX_WORKERS")
    try:
        os.environ["EVAL_MAX_WORKERS"] = "99"
        reset_settings_cache()
        assert eval_service._eval_max_workers() == 32
        os.environ["EVAL_MAX_WORKERS"] = "0"
        reset_settings_cache()
        assert eval_service._eval_max_workers() == 1
    finally:
        if old is None:
            os.environ.pop("EVAL_MAX_WORKERS", None)
        else:
            os.environ["EVAL_MAX_WORKERS"] = old
        reset_settings_cache()


def test_build_category_summary_aggregates_route_match():
    results = [
        {
            "category": "overview",
            "latency_sec": 1.0,
            "metrics": {
                "answer_relevancy": 0.8,
                "context_relevancy": 0.7,
                "faithfulness": 0.9,
            },
            "route_match": True,
        },
        {
            "category": "overview",
            "latency_sec": 2.0,
            "metrics": {
                "answer_relevancy": 0.6,
                "context_relevancy": 0.5,
                "faithfulness": 0.8,
            },
            "route_match": False,
        },
        {
            "category": "synthesis",
            "latency_sec": 3.0,
            "metrics": {
                "answer_relevancy": 0.9,
                "context_relevancy": 0.85,
                "faithfulness": 0.95,
            },
            "route_match": True,
        },
    ]

    summary = eval_service._build_category_summary(results)

    assert summary["overview"]["cases"] == 2
    assert summary["overview"]["avg_latency_sec"] == 1.5
    assert summary["overview"]["route_match_rate"] == 0.5
    assert summary["synthesis"]["cases"] == 1
    assert summary["synthesis"]["route_match_rate"] == 1.0


def test_normalize_eval_category_maps_cross_document_to_synthesis():
    assert eval_service._normalize_eval_category("cross_document") == "synthesis"
    assert eval_service._normalize_eval_category("overview") == "overview"


def test_compare_to_baseline_detects_regression():
    summary = {
        "avg_answer_relevancy": 0.7,
        "avg_context_relevancy": 0.8,
        "avg_faithfulness": 0.9,
        "avg_retrieval_recall_at_k": 0.7,
        "avg_retrieval_mrr": 0.5,
        "avg_retrieval_hit_rate": 0.9,
        "route_match_rate": 0.7,
    }
    baseline = {
        "artifact_path": "baseline.json",
        "summary": {
            "avg_answer_relevancy": 0.8,
            "avg_context_relevancy": 0.8,
            "avg_faithfulness": 0.9,
            "avg_retrieval_recall_at_k": 0.7,
            "avg_retrieval_mrr": 0.5,
            "avg_retrieval_hit_rate": 0.9,
            "route_match_rate": 0.8,
        },
    }

    comparison = eval_service._compare_to_baseline(summary, baseline)

    assert comparison is not None
    assert comparison["passed"] is False
    assert "avg_answer_relevancy" in comparison["regressions"]
    assert "route_match_rate" in comparison["regressions"]


def test_compare_to_baseline_passes_when_metrics_are_close():
    summary = {
        "avg_answer_relevancy": 0.79,
        "avg_context_relevancy": 0.81,
        "avg_faithfulness": 0.9,
        "avg_retrieval_recall_at_k": 0.7,
        "avg_retrieval_mrr": 0.5,
        "avg_retrieval_hit_rate": 0.9,
        "route_match_rate": 0.77,
    }
    baseline = {
        "artifact_path": "baseline.json",
        "summary": {
            "avg_answer_relevancy": 0.8,
            "avg_context_relevancy": 0.8,
            "avg_faithfulness": 0.9,
            "avg_retrieval_recall_at_k": 0.7,
            "avg_retrieval_mrr": 0.5,
            "avg_retrieval_hit_rate": 0.9,
            "route_match_rate": 0.8,
        },
    }

    comparison = eval_service._compare_to_baseline(summary, baseline)

    assert comparison is not None
    assert comparison["passed"] is True
    assert comparison["regressions"] == []


def test_build_runtime_eval_link_adds_runtime_context_and_warnings():
    summary = {
        "dataset_version": "eval_questions:v1",
        "cases": 12,
        "avg_answer_relevancy": 0.82,
        "avg_context_relevancy": 0.8,
        "avg_faithfulness": 0.74,
        "route_match_rate": 0.7,
        "p95_latency_sec": 4.2,
    }
    runtime_metrics = {
        "window_size": 25,
        "fallback_rate": 0.28,
        "requests_without_sources_rate": 0.24,
        "empty_answers_rate": 0.08,
        "latency_ms": {"p95_total_answer_ms": 5200.0},
    }

    link = eval_service._build_runtime_eval_link(summary, runtime_metrics)

    assert link is not None
    assert link["runtime_metrics_window"]["window_size"] == 25
    assert link["offline_eval_snapshot"]["dataset_version"] == "eval_questions:v1"
    assert "high_fallback_rate" in link["warnings"]
    assert "high_no_sources_rate" in link["warnings"]
    assert "high_empty_answer_rate" in link["warnings"]
    assert "high_runtime_p95_latency" in link["warnings"]
    assert "low_eval_route_match" in link["warnings"]
    assert "low_eval_faithfulness" in link["warnings"]


def test_run_single_tutor_case_skips_without_question():
    case = {
        "id": "no_q",
        "category": "mastery_dashboard",
        "input": {"endpoint": "/dashboard/mastery"},
    }
    r = eval_service._run_single_tutor_case(case)
    assert r["status"] == "skipped"
    assert r["reason"] == "no_question_in_input"


def test_build_tutor_query_options_homework_and_history():
    inp = {
        "query_mode": "tutor",
        "homework_level": "hint",
        "question": "test",
        "history": "prev",
        "session_id": "s1",
    }
    opts = eval_service._build_tutor_query_options(inp, "case1")
    assert opts.homework_mode is True
    assert opts.assistance_level == "hint"
    assert opts.followup_context == "prev"
    assert opts.session_id == "s1"


def test_tutor_expected_rubric_contains_solution_false():
    rubric = eval_service._tutor_expected_rubric("Краткий ответ без кода", {"contains_solution": False})
    assert rubric is not None
    assert rubric["checks"]["no_code_block"] is True

    rubric_bad = eval_service._tutor_expected_rubric("```py\nx=1\n```", {"contains_solution": False})
    assert rubric_bad is not None
    assert rubric_bad["checks"]["no_code_block"] is False


def test_resolve_reference_text_priority_and_whitespace():
    assert eval_service._resolve_reference_text({"reference": "  ref  "}) == "ref"
    assert eval_service._resolve_reference_text({"reference_answer": "legacy"}) == "legacy"
    assert eval_service._resolve_reference_text({"reference": "win", "reference_answer": "lose"}) == "win"
    assert eval_service._resolve_reference_text({"reference": "   "}) is None
    assert eval_service._resolve_reference_text({}) is None


def test_token_f1_similarity_ordering():
    exact = eval_service._token_f1_similarity("hello world", "hello world")
    partial = eval_service._token_f1_similarity("hello there", "hello world")
    none = eval_service._token_f1_similarity("foo bar", "hello world")
    assert exact == pytest.approx(1.0)
    assert partial > none
    assert none == pytest.approx(0.0)


def test_compute_answer_correctness_none_without_reference():
    assert eval_service._compute_answer_correctness("answer", None) is None
    assert eval_service._compute_answer_correctness("answer", "") is None


def test_compute_retrieval_metrics_includes_precision_at_k():
    sources = [
        {"relative_path": "a.md"},
        {"relative_path": "b.md"},
        {"relative_path": "c.md"},
    ]
    metrics = eval_service._compute_retrieval_metrics(sources, ["a.md", "x.md"])
    assert metrics is not None
    assert metrics["precision_at_k"] == pytest.approx(0.333, abs=1e-3)
    assert metrics["recall_at_k"] == pytest.approx(0.5)


def test_compute_eval_summary_new_metric_keys():
    results = [
        {
            "latency_sec": 1.0,
            "route_match": True,
            "metrics": {
                "answer_relevancy": 0.8,
                "context_relevancy": 0.7,
                "faithfulness": 0.9,
                "answer_correctness": 0.6,
            },
            "retrieval_metrics": {
                "recall_at_k": 0.5,
                "precision_at_k": 0.33,
                "mrr": 1.0,
                "hit_rate": 1.0,
            },
        },
        {
            "latency_sec": 2.0,
            "route_match": False,
            "metrics": {
                "answer_relevancy": 0.6,
                "context_relevancy": 0.5,
                "faithfulness": 0.8,
                "answer_correctness": None,
            },
            "retrieval_metrics": None,
        },
    ]
    summary = eval_service._compute_eval_summary(results, "v1")
    assert summary["avg_retrieval_precision_at_k"] == pytest.approx(0.33)
    assert summary["avg_answer_correctness"] == pytest.approx(0.6)


def test_compare_to_baseline_tracks_new_metrics():
    summary = {
        "avg_answer_relevancy": 0.8,
        "avg_retrieval_precision_at_k": 0.55,
        "avg_answer_correctness": 0.7,
    }
    baseline = {
        "artifact_path": "baseline.json",
        "summary": {
            "avg_answer_relevancy": 0.8,
            "avg_retrieval_precision_at_k": 0.6,
            "avg_answer_correctness": 0.75,
        },
    }
    comparison = eval_service._compare_to_baseline(summary, baseline)
    assert comparison is not None
    assert "avg_retrieval_precision_at_k" in comparison["comparisons"]
    assert "avg_answer_correctness" in comparison["comparisons"]
    assert "avg_retrieval_precision_at_k" in comparison["regressions"]
