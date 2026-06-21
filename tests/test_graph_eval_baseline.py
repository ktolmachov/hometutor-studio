"""Graph retrieval eval baseline: versioned fixture, no external LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.graph_retrieval import expand_doc_ids_via_graph

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "graph_eval_baseline.json"


def _load_fixture() -> dict:
    raw = _FIXTURE.read_text(encoding="utf-8")
    return json.loads(raw)


def test_graph_eval_baseline_fixture_schema():
    data = _load_fixture()
    assert int(data.get("schema_version") or 0) >= 3
    cases = data.get("cases") or []
    assert len(cases) >= 1
    for c in cases:
        assert "id" in c
        assert "seed_doc_ids" in c
        assert "concepts" in c


@pytest.mark.parametrize("case", _load_fixture()["cases"], ids=lambda c: c["id"])
def test_graph_eval_baseline_cases(case: dict):
    """Regression gate for graph expansion: expectations live in graph_eval_baseline.json."""
    added, trace = expand_doc_ids_via_graph(
        list(case["seed_doc_ids"]),
        case["concepts"],
        max_extra=int(case.get("max_extra", 5)),
        max_hops=int(case.get("max_hops", 1)),
    )
    for doc_id in case.get("expect_added_contains", []):
        assert doc_id in added, f"case={case['id']!r} added={added!r}"
    exp_reason = case.get("expect_trace_reason")
    if exp_reason is not None:
        assert trace.get("reason") == exp_reason, f"case={case['id']!r}"
    for key in case.get("expect_trace_keys", []):
        assert key in trace, f"case={case['id']!r} trace_keys={list(trace.keys())}"
