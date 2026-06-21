"""Graph-augmented retrieval helpers (итерация 17 Core)."""

from app.graph_retrieval import (
    evaluate_composite_graph_gating,
    expand_doc_ids_via_graph,
    extract_doc_ids_from_nodes,
)


def test_expand_doc_ids_via_graph_multi_hop_finds_d3():
    concepts = {
        "T1": {
            "documents": ["d1.md"],
            "related_documents": ["d1.md"],
            "prerequisites": [],
            "related_concepts": ["T2"],
        },
        "T2": {
            "documents": [],
            "related_documents": [],
            "prerequisites": [],
            "related_concepts": ["T3"],
        },
        "T3": {
            "documents": ["d3.md"],
            "related_documents": ["d3.md"],
            "prerequisites": [],
            "related_concepts": [],
        },
    }
    added_1, t1 = expand_doc_ids_via_graph(["d1.md"], concepts, max_extra=5, max_hops=1)
    assert "d3.md" not in added_1
    added_3, t3 = expand_doc_ids_via_graph(["d1.md"], concepts, max_extra=5, max_hops=3)
    assert "d3.md" in added_3
    assert t3.get("hops_applied", 0) >= 2
    assert "T3" in (t3.get("concept_ids_sample") or [])
    assert any(item.get("concept_id") == "T3" for item in (t3.get("concept_route_sample") or []))
    assert any(item.get("doc_id") == "d3.md" for item in (t3.get("added_doc_reason_sample") or []))


def test_expand_doc_ids_via_graph_adds_neighbor_docs():
    concepts = {
        "T1": {
            "documents": ["d1.md"],
            "related_documents": ["d1.md"],
            "prerequisites": [],
            "related_concepts": ["T2"],
        },
        "T2": {
            "documents": ["d2.md"],
            "related_documents": ["d2.md"],
            "prerequisites": ["T1"],
            "related_concepts": [],
        },
    }
    added, trace = expand_doc_ids_via_graph(["d1.md"], concepts, max_extra=5)
    assert "d2.md" in added
    assert trace.get("seed_doc_ids")
    assert "d2.md" in trace.get("added_doc_ids", [])
    assert "T1" in (trace.get("seed_concept_ids_sample") or [])


def test_expand_doc_ids_empty_seed():
    added, trace = expand_doc_ids_via_graph([], {"A": {"documents": ["x"]}}, max_extra=3)
    assert added == []
    assert trace.get("reason") == "empty_seed"


def test_extract_doc_ids_from_nodes_empty():
    assert extract_doc_ids_from_nodes([]) == []


def test_composite_gating_blocked_for_quality_when_baseline_thick():
    ok, reason = evaluate_composite_graph_gating(
        use_composite_graph_gating=True,
        effective_graph_augmented=True,
        classify_confidence=0.92,
        graph_augment_min_confidence=0.7,
        baseline_dedupe_count=12,
        baseline_thin_k=3,
        effective_profile="quality",
    )
    assert ok is False
    assert reason == "composite_gating_baseline"


def test_composite_graph_aware_allows_even_if_baseline_thick():
    ok, reason = evaluate_composite_graph_gating(
        use_composite_graph_gating=True,
        effective_graph_augmented=True,
        classify_confidence=0.92,
        graph_augment_min_confidence=0.7,
        baseline_dedupe_count=20,
        baseline_thin_k=50,
        effective_profile="graph_aware",
    )
    assert ok is True
    assert reason is None


def test_composite_low_confidence_blocks():
    ok, reason = evaluate_composite_graph_gating(
        use_composite_graph_gating=True,
        effective_graph_augmented=True,
        classify_confidence=0.5,
        graph_augment_min_confidence=0.7,
        baseline_dedupe_count=1,
        baseline_thin_k=99,
        effective_profile="quality",
    )
    assert ok is False
    assert reason == "composite_gating_confidence"


def test_graph_evidences_flags_weak_below_threshold():
    from app.graph_retrieval import graph_evidences_from_reason_rows

    evs = graph_evidences_from_reason_rows(
        doc_id="notes/a.md",
        reason_rows=[
            {
                "concept_id": "C2",
                "hop": 4,
                "relation": "related",
                "via_concept": "C1",
            }
        ],
        classify_confidence=0.71,
        weak_threshold=0.60,
        generation_id="gid-test",
    )
    assert len(evs) == 1
    assert evs[0].relation_id
    assert evs[0].evidence_doc_id == "notes/a.md"
    assert evs[0].generation_id == "gid-test"
    assert evs[0].direction == "undirected"
    assert evs[0].weak_evidence is True
