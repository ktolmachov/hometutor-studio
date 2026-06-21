"""Unit tests for SSR graph routing helper (epoch-ssr-graph-routing-v1-sp1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.knowledge_graph import JsonKnowledgeGraph
from app.ssr_graph_routing import order_weak_concepts_for_ssr


def _kg_from_graph(graph: dict, tmp_path: Path) -> JsonKnowledgeGraph:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "fixture_graph.json"
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    return JsonKnowledgeGraph(path)


@pytest.fixture
def chain_kg(tmp_path: Path) -> JsonKnowledgeGraph:
    return _kg_from_graph(
        {
            "concepts": {
                "A": {"prerequisites": []},
                "B": {"prerequisites": ["A"]},
                "C": {"prerequisites": ["B"]},
            }
        },
        tmp_path / "chain",
    )


def test_order_weak_concepts_chain_returns_prerequisite_first_head(chain_kg: JsonKnowledgeGraph) -> None:
    assert order_weak_concepts_for_ssr(["C", "A", "B"], chain_kg) == "A"


def test_order_weak_concepts_empty_returns_none(chain_kg: JsonKnowledgeGraph) -> None:
    assert order_weak_concepts_for_ssr([], chain_kg) is None


def test_order_weak_concepts_whitespace_only_returns_none(chain_kg: JsonKnowledgeGraph) -> None:
    assert order_weak_concepts_for_ssr(["  ", "", "\t"], chain_kg) is None


def test_order_weak_concepts_all_absent_returns_none(tmp_path: Path) -> None:
    kg = _kg_from_graph({"concepts": {"A": {"prerequisites": []}}}, tmp_path / "solo")
    assert order_weak_concepts_for_ssr(["X", "Y"], kg) is None


def test_order_weak_concepts_cycle_returns_none(tmp_path: Path) -> None:
    kg = _kg_from_graph(
        {
            "concepts": {
                "A": {"prerequisites": ["B"]},
                "B": {"prerequisites": ["A"]},
            }
        },
        tmp_path / "cycle",
    )
    assert order_weak_concepts_for_ssr(["A", "B"], kg) is None


def test_order_weak_concepts_incomplete_topo_returns_none(tmp_path: Path) -> None:
    kg = _kg_from_graph(
        {
            "concepts": {
                "A": {"prerequisites": ["MISSING"]},
                "B": {"prerequisites": ["A"]},
            }
        },
        tmp_path / "incomplete",
    )
    assert order_weak_concepts_for_ssr(["A", "B"], kg) is None


def test_order_weak_concepts_singleton_returns_member(chain_kg: JsonKnowledgeGraph) -> None:
    assert order_weak_concepts_for_ssr(["A"], chain_kg) == "A"


def test_order_weak_concepts_dedupes_preserving_first_occurrence(chain_kg: JsonKnowledgeGraph) -> None:
    assert order_weak_concepts_for_ssr(["C", "C", "A", "B", "A"], chain_kg) == "A"


def test_order_weak_concepts_tail_appends_absent_ids(chain_kg: JsonKnowledgeGraph) -> None:
    assert order_weak_concepts_for_ssr(["C", "OFF_GRAPH", "A", "B"], chain_kg) == "A"
