"""US-6.2: дельта концептов между сохранениями adaptive daily plan."""
from __future__ import annotations

from app.adaptive_plan import block_concepts_from_plan, compute_plan_concepts_delta


def test_block_concepts_from_plan_extracts_concepts():
    p = {
        "date": "2026-04-10",
        "blocks": [
            {"type": "review", "concept": "alpha"},
            {"type": "gap", "concept": "beta"},
            {"type": "auto_loop"},
        ],
    }
    assert block_concepts_from_plan(p) == ["alpha", "beta"]


def test_compute_plan_concepts_delta_added_removed():
    prev = {
        "date": "2026-04-09",
        "blocks": [{"type": "review", "concept": "a"}, {"type": "gap", "concept": "b"}],
    }
    new = {
        "date": "2026-04-10",
        "blocks": [{"type": "review", "concept": "b"}, {"type": "new", "concept": "c"}],
    }
    d = compute_plan_concepts_delta(prev, new)
    assert d["baseline_date"] == "2026-04-09"
    assert d["added"] == ["c"]
    assert d["removed"] == ["a"]


def test_compute_plan_concepts_delta_no_previous():
    new = {"date": "2026-04-10", "blocks": [{"concept": "x"}]}
    d = compute_plan_concepts_delta(None, new)
    assert d["baseline_date"] is None
    assert d["added"] == ["x"]
    assert d["removed"] == []
