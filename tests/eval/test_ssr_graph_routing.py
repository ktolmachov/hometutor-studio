"""Offline eval harness for SSR Level 4 concept-graph routing (scaffold)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.knowledge_graph import JsonKnowledgeGraph
from app.smart_study_router import build_smart_study_recommendation

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "eval_data" / "ml_eval" / "ssr_level4" / "contract.yaml"
RUBRIC_PATH = ROOT / "doc" / "eval" / "ssr_graph_routing_rubric.md"
DESIGN_PATH = ROOT / "doc" / "ssr_kg_integration_design.md"
CASES_PATH = Path(__file__).with_name("ssr_graph_routing_cases.json")

REQUIRED_CASE_KEYS = frozenset(
    {
        "id",
        "description",
        "ssr_inputs",
        "graph",
        "expected_weak_order",
        "expected_hint_kind",
        "expected_primary_nav",
        "metric_tags",
    }
)


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _kg_from_inline(graph: dict[str, Any], tmp_path: Path) -> JsonKnowledgeGraph:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "fixture_graph.json"
    path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    return JsonKnowledgeGraph(path)


def _order_weak_by_prerequisites(weak_ids: list[str], kg: JsonKnowledgeGraph) -> list[str]:
    """Test-only L4 helper (see doc/ssr_kg_integration_design.md)."""
    concepts = kg.get_concepts()
    present = [wid for wid in weak_ids if wid in concepts]
    if not present:
        return list(weak_ids)
    ordered = kg.topological_sort(present)
    seen = set(ordered)
    tail = [wid for wid in weak_ids if wid not in seen]
    return ordered + tail


def _pairwise_prerequisite_ordering_accuracy(
    actual_order: list[str],
    expected_weak_order: list[str],
    kg: JsonKnowledgeGraph,
) -> float | None:
    concepts = set(expected_weak_order)
    if len(concepts) < 2:
        return None
    index = {cid: pos for pos, cid in enumerate(actual_order) if cid in concepts}
    total = 0
    correct = 0
    for i, u in enumerate(expected_weak_order):
        for v in expected_weak_order[i + 1 :]:
            total += 1
            iu = index.get(u)
            iv = index.get(v)
            if iu is None or iv is None:
                continue
            if iu < iv:
                if v not in kg.get_prerequisites(u):
                    correct += 1
    if total == 0:
        return None
    return correct / total


def _actual_weak_order(case: dict[str, Any], kg: JsonKnowledgeGraph) -> list[str]:
    weak = case.get("weak_concepts")
    if isinstance(weak, list) and len(weak) > 1:
        return _order_weak_by_prerequisites([str(x) for x in weak], kg)
    inputs = case.get("ssr_inputs") or {}
    first = inputs.get("first_weak_concept")
    return [str(first)] if first else []


@pytest.fixture(autouse=True)
def _rule_only_ssr(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.smart_study_router as router

    monkeypatch.setattr(router, "_apply_ssr_ml_hybrid_if_enabled", lambda rule, **_kw: rule)


def test_ssr_graph_routing_eval_contract_artifacts_exist() -> None:
    assert CONTRACT_PATH.exists()
    assert RUBRIC_PATH.exists()
    assert DESIGN_PATH.exists()
    assert CASES_PATH.exists()
    rubric = RUBRIC_PATH.read_text(encoding="utf-8")
    assert "prerequisite_ordering_accuracy" in rubric
    assert "routing_latency_p95" in rubric
    design = DESIGN_PATH.read_text(encoding="utf-8")
    assert "no learner-visible graph override" in design.lower()


def test_ssr_graph_routing_cases_schema_and_minimum_count() -> None:
    cases = _load_cases()
    assert len(cases) >= 5
    for case in cases:
        missing = REQUIRED_CASE_KEYS - set(case.keys())
        assert not missing, f"{case.get('id')}: missing {missing}"
        assert isinstance(case["metric_tags"], list)


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_ssr_graph_routing_baseline_regression_golden(case: dict[str, Any]) -> None:
    if "baseline_regression" not in case.get("metric_tags", []):
        pytest.skip("not a baseline_regression case")
    inputs = dict(case["ssr_inputs"])
    rec = build_smart_study_recommendation(**inputs)
    assert rec.hint_kind == case["expected_hint_kind"]
    assert rec.primary_nav == case["expected_primary_nav"]


def test_ssr_graph_routing_prerequisite_ordering_accuracy_aggregate(
    tmp_path: Path,
) -> None:
    scores: list[float] = []
    for case in _load_cases():
        if "weak_ordering" not in case.get("metric_tags", []):
            continue
        if case.get("skip_ordering_metric"):
            continue
        expected = case.get("expected_weak_order")
        if not expected or len(expected) < 2:
            continue
        kg = _kg_from_inline(case["graph"], tmp_path / case["id"])
        actual = _actual_weak_order(case, kg)
        score = _pairwise_prerequisite_ordering_accuracy(actual, expected, kg)
        assert score is not None, case["id"]
        scores.append(score)
    assert scores
    aggregate = sum(scores) / len(scores)
    assert aggregate >= 0.85, f"aggregate={aggregate:.3f} scores={scores}"


def test_ssr_graph_routing_fixture_graph_health(tmp_path: Path) -> None:
    for case in _load_cases():
        if "graph_health" not in case.get("metric_tags", []):
            continue
        kg = _kg_from_inline(case["graph"], tmp_path / f"health_{case['id']}")
        concept_ids = list(kg.get_concepts().keys())
        cycles = kg.find_prerequisite_cycles(concept_ids)
        if case["id"] == "incomplete_graph_cycle_fallback":
            assert cycles
        else:
            assert not cycles


def test_ssr_order_weak_by_prerequisites_respects_chain(tmp_path: Path) -> None:
    graph = {
        "concepts": {
            "A": {"prerequisites": []},
            "B": {"prerequisites": ["A"]},
            "C": {"prerequisites": ["B"]},
        }
    }
    kg = _kg_from_inline(graph, tmp_path / "chain")
    assert _order_weak_by_prerequisites(["C", "A", "B"], kg) == ["A", "B", "C"]
