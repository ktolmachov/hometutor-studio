"""Retrieval-mode comparison metrics (recall@k, MRR, hit-rate, latency percentiles)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval_retrieval_comparison import (
    RETRIEVAL_COMPARISON_MODES,
    RetrievalComparisonEngine,
    calculate_hit_rate,
    calculate_mrr,
    calculate_precision_at_k,
    calculate_recall_at_k,
    latency_percentiles_ms,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFENSE_DATASET = REPO_ROOT / "eval_data" / "defense_eval_questions.json"


def test_calculate_recall_at_k_partial_and_full():
    rel = {"a", "b", "c"}
    retrieved = ["x", "a", "b", "y"]
    assert calculate_recall_at_k(rel, retrieved, 1) == 0.0
    assert calculate_recall_at_k(rel, retrieved, 3) == pytest.approx(2 / 3)
    # Top-10 still misses ``c`` → two of three relevant
    assert calculate_recall_at_k(rel, retrieved, 10) == pytest.approx(2 / 3)


def test_calculate_recall_at_k_empty_relevant():
    assert calculate_recall_at_k(set(), ["a", "b"], 5) == 0.0


def test_calculate_precision_at_k_partial_and_full():
    rel = {"a", "b", "c"}
    retrieved = ["x", "a", "b", "y"]
    assert calculate_precision_at_k({"a"}, ["a", "b"], 2) == pytest.approx(0.5)
    assert calculate_precision_at_k(rel, retrieved, 1) == 0.0
    assert calculate_precision_at_k(rel, retrieved, 3) == pytest.approx(2 / 3)
    assert calculate_precision_at_k(rel, retrieved, 10) == pytest.approx(2 / 10)


def test_calculate_precision_at_k_edge_cases():
    assert calculate_precision_at_k(set(), ["a", "b"], 5) == 0.0
    assert calculate_precision_at_k({"a"}, [], 5) == 0.0
    assert calculate_precision_at_k({"a"}, ["a"], 0) == 0.0
    assert calculate_precision_at_k({"a"}, ["a"], -1) == 0.0
    assert calculate_precision_at_k({"a"}, ["a", "a"], 2) == pytest.approx(0.5)


def test_calculate_mrr_first_rank_and_miss():
    rel = {"b"}
    assert calculate_mrr(rel, ["b", "a"]) == 1.0
    assert calculate_mrr(rel, ["a", "b"]) == 0.5
    assert calculate_mrr(rel, ["x", "y"]) == 0.0


def test_calculate_hit_rate_edges():
    assert calculate_hit_rate([]) == 0.0
    assert calculate_hit_rate([True, False, True]) == pytest.approx(2 / 3)


def test_latency_percentiles_ms_sorted_and_single():
    assert latency_percentiles_ms([]) == (0.0, 0.0, 0.0)
    assert latency_percentiles_ms([100.0]) == (100.0, 100.0, 100.0)
    p50, p95, p99 = latency_percentiles_ms([10.0, 20.0, 30.0, 40.0, 50.0])
    assert p50 == pytest.approx(30.0)
    assert p95 >= p50
    assert p99 >= p95


def test_comparison_engine_stub_retriever_winners():
    """Synthetic retrieve: bm25_only ranks relevant doc first for every query."""

    queries = ("q1", "q2")
    relevant = ({"d1", "d2"}, {"d3"})

    def retrieve(mode: str, query: str) -> tuple[list[str], float]:
        base_latency = {
            "vector_only": 80.0,
            "hybrid": 60.0,
            "bm25_only": 40.0,
            "doc_then_chunk": 100.0,
        }[mode]
        if query == "q1":
            order = {
                "vector_only": ["x", "d1", "d2"],
                "hybrid": ["x", "d2", "d1"],
                "bm25_only": ["d1", "d2", "x"],
                "doc_then_chunk": ["y", "d2"],
            }[mode]
            lat = base_latency + 5.0
        else:
            order = {
                "vector_only": ["z", "d3"],
                "hybrid": ["d3", "z"],
                "bm25_only": ["d3", "z"],
                "doc_then_chunk": ["z"],
            }[mode]
            lat = base_latency + 2.0
        return order, lat

    engine = RetrievalComparisonEngine(k_values=(1, 3))
    report = engine.compare_modes(queries, relevant, retrieve)

    assert set(report.results_by_mode) == set(RETRIEVAL_COMPARISON_MODES)
    bm = report.results_by_mode["bm25_only"]
    assert bm.hit_rate == 1.0
    assert bm.recall_at_k[1] >= report.results_by_mode["vector_only"].recall_at_k[1]
    assert bm.precision_at_k[1] >= report.results_by_mode["vector_only"].precision_at_k[1]
    assert "precision@1" in report.winner_by_metric
    assert "precision@3" in report.winner_by_metric
    # Several modes can tie at hit_rate==1.0; winner picks first max in dict walk order.
    assert report.results_by_mode[report.winner_by_metric["hit_rate"]].hit_rate == 1.0
    assert report.winner_by_metric["latency_ms_p50"] == "bm25_only"


def test_compare_modes_length_mismatch_raises():
    engine = RetrievalComparisonEngine()

    def _r(_mode: str, _q: str) -> tuple[list[str], float]:
        return [], 0.0

    with pytest.raises(ValueError):
        engine.compare_modes(["a", "b"], [{"x"}], _r)


def test_defense_dataset_loads_for_comparison_contract():
    """Golden defense JSON exists and yields query ids + characteristics keys."""
    assert DEFENSE_DATASET.is_file(), f"missing {DEFENSE_DATASET}"
    data = json.loads(DEFENSE_DATASET.read_text(encoding="utf-8"))
    categories = data["categories"]
    queries: list[str] = []
    for cat_items in categories.values():
        for item in cat_items:
            queries.append(item["query"])
    assert len(queries) >= 10

    relevant_stub = [{"stub-doc"} for _ in queries]

    def retrieve(mode: str, query: str) -> tuple[list[str], float]:
        _ = mode
        return ["stub-doc"], float(hash(query) % 37)

    engine = RetrievalComparisonEngine()
    report = engine.compare_modes(queries, relevant_stub, retrieve)
    assert len(report.results_by_mode) == len(RETRIEVAL_COMPARISON_MODES)
