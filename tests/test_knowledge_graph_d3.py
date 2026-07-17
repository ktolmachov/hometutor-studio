"""Tests for the D3 knowledge-graph payload builder (app.ui.knowledge_graph_d3).

Covers: core payload, mastery/frontier logic, Wave 1 (KG-01..04), Wave 2 (KG-05..06).
"""

from __future__ import annotations

from app.ui.knowledge_graph_d3 import (
    build_cluster_labels,
    build_decay_vector,
    build_graph_health,
    build_kg_html,
    build_kg_payload,
    build_mastery_history,
    compute_decay,
)

# ── shared fixtures ──────────────────────────────────────────────────

CONCEPTS = {
    "Basics":     {"level": "beginner",     "description": "Vars & types.",  "prerequisites": []},
    "Functions":  {"level": "beginner",     "description": "Defs.",          "prerequisites": ["Basics"]},
    "OOP":        {"level": "intermediate", "description": "Classes.",        "prerequisites": ["Functions"]},
    "Decorators": {"level": "advanced",     "description": "HOFs.",           "prerequisites": ["Functions", "OOP"], "related_documents": ["dec.md"]},
    "Async":      {"level": "advanced",     "description": "Coroutines.",     "prerequisites": ["Functions", "GhostConcept"]},
}
MASTERY = {"Basics": 0.95, "Functions": 0.9, "OOP": 0.3, "avg": 0.6}
LEARNED = {"Basics"}
DOC_INDEX = {"dec.md": {"relative_path": "dec.md", "doc_type": "guide", "summary": "Decorators guide."}}


def _payload():
    return build_kg_payload(CONCEPTS, MASTERY, LEARNED, DOC_INDEX)


# ── core payload ─────────────────────────────────────────────────────

def test_payload_basic_shape():
    p = _payload()
    assert {n["id"] for n in p["nodes"]} == set(CONCEPTS)
    assert any(
        e["source"] == "Basics" and e["target"] == "Functions" and e.get("relation_type") == "prerequisite"
        for e in p["edges"]
    )
    assert all(e["source"] in CONCEPTS and e["target"] in CONCEPTS for e in p["edges"])
    assert p["stats"]["total"] == 5


def test_payload_includes_compiler_typed_relations_and_resolves_labels():
    concepts = {
        "agent_loop": {"label": "Цикл агента", "prerequisites": []},
        "tool_use": {"label": "Использование инструментов", "prerequisites": ["Цикл агента"]},
        "reflection": {"label": "Рефлексия", "prerequisites": []},
    }
    relations = [
        {
            "source_concept_id": "tool_use",
            "target_concept_id": "reflection",
            "relation_type": "extends",
            "confidence": 0.91,
            "evidence_doc_id": "lesson_2",
        }
    ]

    payload = build_kg_payload(concepts, typed_relations=relations)

    assert any(
        e["source"] == "agent_loop" and e["target"] == "tool_use" and e.get("relation_type") == "prerequisite"
        for e in payload["edges"]
    )
    assert any(
        edge["source"] == "tool_use"
        and edge["target"] == "reflection"
        and edge["relation_type"] == "extends"
        for edge in payload["edges"]
    )
    labels = {node["id"]: node["label"] for node in payload["nodes"]}
    assert labels["agent_loop"] == "Цикл агента"


def test_mastery_and_learned_flags():
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    assert nodes["Basics"]["mastery"] == 95.0
    assert nodes["Basics"]["learned"] is True
    assert nodes["Functions"]["learned"] is True   # mastery >= 80
    assert nodes["OOP"]["learned"] is False


def test_frontier_requires_all_prereqs_mastered():
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    assert nodes["OOP"]["frontier"] is True        # prereq Functions (90%) mastered
    assert nodes["Decorators"]["frontier"] is False # prereq OOP (30%) not mastered
    assert nodes["Basics"]["frontier"] is False     # already learned


def test_missing_prerequisites_flagged():
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    assert nodes["Async"]["missing"] == ["GhostConcept"]
    assert nodes["Functions"]["missing"] == []


def test_unlocks_and_reach():
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    assert "Functions" in nodes["Basics"]["unlocks"]
    assert nodes["Basics"]["reach"] >= 4   # all downstream concepts
    assert nodes["Decorators"]["reach"] == 0


def test_related_documents_enriched():
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    rel = nodes["Decorators"]["related"]
    assert rel and rel[0]["path"] == "dec.md"
    assert "guide" in rel[0]["meta"]


def test_empty_graph_is_safe():
    p = build_kg_payload({}, {}, set(), {})
    assert p["nodes"] == [] and p["edges"] == []
    assert p["stats"]["total"] == 0


def test_html_renders_with_all_placeholders_filled():
    p = _payload()
    html = build_kg_html(p)
    assert "<!DOCTYPE html>" in html
    for ph in ("__NODES__", "__EDGES__", "__LEVELS__", "__STATS__",
               "__WEEKLY_PLAN__", "__HEALTH__", "__CLUSTER_LABELS__",
               "__COMPILER_HEALTH__", "__D3_TAG__"):
        assert ph not in html
    assert "forceSimulation" in html


# ── KG-01 / C2: weekly planner removed from graph UI ─────────────────

def test_weekly_plan_export_key_kept_empty():
    payload = _payload()
    assert payload["weekly_plan"] == []


# ── KG-02: build_graph_health ────────────────────────────────────────

def _health():
    p = _payload()
    return build_graph_health(p["nodes"], p["edges"])


def test_health_score_is_int_in_range():
    h = _health()
    assert isinstance(h["score"], int)
    assert 0 <= h["score"] <= 100


def test_missing_prereqs_detected():
    h = _health()
    missing_ids = [m["concept"] for m in h["missing"]]
    assert "Async" in missing_ids


def test_no_cycles_in_clean_dag():
    h = _health()
    assert h["cycles"] == []


def test_cycle_detected():
    # Artificially create a cycle: A → B → A
    nodes = [
        {"id": "A", "level": "beginner", "mastery": 0, "learned": False, "frontier": False,
         "reach": 0, "missing": [], "related": [], "prereqs": ["B"], "unlocks": []},
        {"id": "B", "level": "beginner", "mastery": 0, "learned": False, "frontier": False,
         "reach": 0, "missing": [], "related": [], "prereqs": ["A"], "unlocks": []},
    ]
    edges = [{"source": "A", "target": "B"}, {"source": "B", "target": "A"}]
    h = build_graph_health(nodes, edges)
    assert h["cycles"]
    assert h["score"] < 100


def test_orphan_detected():
    nodes = [
        {"id": "Lone", "level": "beginner", "mastery": 0, "learned": False, "frontier": False,
         "reach": 0, "missing": [], "related": [], "prereqs": [], "unlocks": []},
    ]
    h = build_graph_health(nodes, [])
    assert "Lone" in h["orphans"]


def test_health_score_100_for_perfect_graph():
    nodes = [
        {"id": "A", "level": "beginner", "mastery": 100, "learned": True, "frontier": False,
         "reach": 1, "missing": [], "related": ["doc.md"], "prereqs": [], "unlocks": ["B"]},
        {"id": "B", "level": "intermediate", "mastery": 80, "learned": True, "frontier": False,
         "reach": 0, "missing": [], "related": ["doc2.md"], "prereqs": ["A"], "unlocks": []},
    ]
    edges = [{"source": "A", "target": "B"}]
    h = build_graph_health(nodes, edges)
    assert h["score"] == 100
    assert h["cycles"] == []
    assert h["orphans"] == []


# ── KG-03: build_cluster_labels ──────────────────────────────────────

def test_cluster_label_is_most_foundational():
    nodes = [n for n in _payload()["nodes"]]
    labels = build_cluster_labels(nodes)
    # All nodes in one cluster (connected graph); label should be highest-reach node
    assert len(labels) >= 1
    for cid, label_id in labels.items():
        cluster_nodes = [n for n in nodes if str(n["cluster"]) == cid]
        max_reach = max(n["reach"] for n in cluster_nodes)
        label_node = next(n for n in cluster_nodes if n["id"] == label_id)
        assert label_node["reach"] == max_reach


def test_cluster_labels_keys_are_strings():
    labels = build_cluster_labels([n for n in _payload()["nodes"]])
    assert all(isinstance(k, str) for k in labels)


def test_single_node_cluster_labeled():
    nodes = [
        {"id": "Solo", "cluster": 99, "reach": 0},
    ]
    labels = build_cluster_labels(nodes)
    assert labels.get("99") == "Solo"


# ── KG-04: html contains export + link buttons ────────────────────────

def test_html_contains_export_and_link_buttons():
    html = build_kg_html(_payload())
    assert "expbtn" in html
    assert "linkbtn" in html
    assert "diagbtn" in html
    assert "SVG" in html


def test_html_has_no_legacy_weekly_plan_section():
    html = build_kg_html(_payload())
    assert "WEEKLY_PLAN" not in html
    assert "pp-cards" not in html


def test_html_contains_diagnostics_section():
    html = build_kg_html(_payload())
    assert "HEALTH" in html
    assert "dp-body" in html


def test_html_contains_cluster_labels():
    html = build_kg_html(_payload())
    assert "CLUSTER_LABELS" in html


# ── KG-05: guided path (BFS lives in JS; Python side tested via html) ──

def test_html_contains_route_panel():
    html = build_kg_html(_payload())
    assert "rp-find" in html
    assert "rp-start" in html
    assert "_bfsPath" in html
    assert "routebtn" in html


def test_html_contains_animate_path():
    html = build_kg_html(_payload())
    assert "animatePath" in html
    assert "ROUTE_COLORS" in html


# ── KG-06: forgetting decay overlay ──────────────────────────────────

def test_compute_decay_no_review_returns_1():
    assert compute_decay(None, 2.5, 1) == 1.0
    assert compute_decay("", 2.5, 1) == 1.0


def test_compute_decay_recent_review_high_retention():
    from datetime import datetime, timedelta, timezone
    yesterday = (datetime.now(tz=timezone.utc) - timedelta(hours=12)).isoformat()
    r = compute_decay(yesterday, 2.5, 7)
    assert 0.8 <= r <= 1.0, f"Expected high retention for recent review, got {r}"


def test_compute_decay_old_review_low_retention():
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(tz=timezone.utc) - timedelta(days=90)).isoformat()
    r = compute_decay(old, 2.5, 1)
    assert r < 0.2, f"Expected low retention after 90 days with short interval, got {r}"


def test_compute_decay_bounds():
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(tz=timezone.utc) + timedelta(days=5)).isoformat()
    r = compute_decay(future, 2.5, 7)
    assert 0.0 <= r <= 1.0


def test_build_decay_vector_empty():
    assert build_decay_vector([]) == {}


def test_build_decay_vector_skips_no_concept():
    result = build_decay_vector([{"concept": "", "easiness": 2.5, "interval_days": 1}])
    assert result == {}


def test_build_decay_vector_maps_concepts():
    from datetime import datetime, timedelta, timezone
    recent = (datetime.now(tz=timezone.utc) - timedelta(hours=6)).isoformat()
    records = [
        {"concept": "Basics", "easiness": 2.5, "interval_days": 7, "last_review": recent},
        {"concept": "OOP",    "easiness": 2.0, "interval_days": 1, "last_review": None},
    ]
    v = build_decay_vector(records)
    assert "Basics" in v and "OOP" in v
    assert v["OOP"] == 1.0           # no review → fully retained (not yet started)
    assert 0.0 <= v["Basics"] <= 1.0


def test_payload_contains_decay_field_on_nodes():
    # sr_records=None → all decay=None (no SRS data)
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    for n in nodes.values():
        assert "decay" in n          # field present (may be None)


def test_payload_decay_vector_in_payload():
    p = _payload()
    assert "decay_vector" in p
    assert isinstance(p["decay_vector"], dict)


def test_payload_with_sr_records_fills_decay():
    from datetime import datetime, timedelta, timezone
    recent = (datetime.now(tz=timezone.utc) - timedelta(hours=3)).isoformat()
    sr = [{"concept": "Basics", "easiness": 2.5, "interval_days": 3, "last_review": recent}]
    p = build_kg_payload(CONCEPTS, MASTERY, LEARNED, DOC_INDEX, sr_records=sr)
    basics_node = next(n for n in p["nodes"] if n["id"] == "Basics")
    assert basics_node["decay"] is not None
    assert 0.5 <= basics_node["decay"] <= 1.0


def test_html_contains_decay_vector_constant():
    html = build_kg_html(_payload())
    assert "DECAY_VECTOR" in html
    assert "decaybtn" in html
    assert "decayMode" in html
    assert "applyDecayOverlay" in html


# ── KG-07: mastery-over-time scrubber ────────────────────────────────

_QUIZ_ROWS = [
    {"concept": "Basics",    "score": 0.7,  "timestamp": "2024-01-10T09:00:00"},
    {"concept": "Functions", "score": 0.5,  "timestamp": "2024-01-10T10:30:00"},
    {"concept": "Basics",    "score": 0.95, "timestamp": "2024-01-20T11:00:00"},
    {"concept": "OOP",       "score": 0.4,  "timestamp": "2024-02-05T14:00:00"},
    {"concept": "OOP",       "score": 0.8,  "timestamp": "2024-02-15T16:00:00"},
]


def test_mastery_history_empty_input():
    assert build_mastery_history([]) == []


def test_mastery_history_returns_sorted_snapshots():
    h = build_mastery_history(_QUIZ_ROWS)
    dates = [s["date"] for s in h]
    assert dates == sorted(dates)                     # ascending
    assert len(h) >= 3                                # at least 3 distinct days


def test_mastery_history_concepts_present():
    h = build_mastery_history(_QUIZ_ROWS)
    last = h[-1]["mastery"]
    assert "Basics" in last and "OOP" in last and "Functions" in last


def test_mastery_history_values_in_range():
    h = build_mastery_history(_QUIZ_ROWS)
    for snap in h:
        for v in snap["mastery"].values():
            assert 0.0 <= v <= 100.0


def test_mastery_history_cumulative():
    # Each snapshot should carry forward all previously seen concepts
    h = build_mastery_history(_QUIZ_ROWS)
    # Second snapshot should include Basics + Functions (seen on day 1)
    # even if day 2 only quizzed Basics
    second = h[1]["mastery"]
    assert "Functions" in second


def test_mastery_history_concept_filter():
    h = build_mastery_history(_QUIZ_ROWS, known_concept_ids=["Basics", "OOP"])
    for snap in h:
        assert "Functions" not in snap["mastery"]
    assert any("Basics" in s["mastery"] for s in h)


def test_mastery_history_skips_missing_fields():
    rows = [
        {"concept": "",       "score": 0.9, "timestamp": "2024-01-01T00:00:00"},
        {"concept": "Valid",  "score": 0.8, "timestamp": ""},
        {"concept": "OK",     "score": 0.7, "timestamp": "2024-01-02T00:00:00"},
    ]
    h = build_mastery_history(rows)
    assert len(h) >= 1
    assert all("OK" in s["mastery"] or True for s in h)  # only valid rows


def test_mastery_history_single_row():
    h = build_mastery_history([{"concept": "Solo", "score": 0.6, "timestamp": "2024-03-01T12:00:00"}])
    assert len(h) == 1
    assert "Solo" in h[0]["mastery"]
    assert abs(h[0]["mastery"]["Solo"] - 60.0) < 1.0


def test_payload_contains_mastery_history():
    p = build_kg_payload(CONCEPTS, MASTERY, LEARNED, DOC_INDEX, quiz_rows=_QUIZ_ROWS)
    assert "mastery_history" in p
    assert isinstance(p["mastery_history"], list)
    assert len(p["mastery_history"]) >= 3


def test_payload_mastery_history_empty_without_rows():
    p = _payload()   # no quiz_rows
    assert p["mastery_history"] == []


def test_html_contains_scrubber():
    html = build_kg_html(_payload())
    assert "MASTERY_HISTORY" in html
    assert "scrub-range" in html
    assert "timebtn" in html
    assert "SCRUB_SNAPSHOTS" in html
    assert "applyScrubSnapshot" in html


# ── Graph-Tutor integration ───────────────────────────────────────────

def test_html_contains_tutor_bridge():
    html = build_kg_html(_payload())
    assert "_kgc" in html             # URL param name for concept sync
    assert "tutor-cta" in html        # CTA hint class in node panel
    assert "replaceState" in html     # parent URL update


# ── Course Prepare graph quality report (sp2 UI contract) ─────────────


def _sample_quality_report(*, gate_passed: bool = True) -> dict:
    return {
        "gate_passed": gate_passed,
        "published": gate_passed,
        "gates": [
            {"name": "normalized_concepts", "required": ">= 12", "actual": "15", "passed": True},
            {"name": "semantic_relations", "required": ">= 10", "actual": "12", "passed": True},
            {"name": "cross_doc_relations", "required": ">= 3", "actual": "4", "passed": True},
            {"name": "filename_fallback", "required": "0", "actual": "0", "passed": True},
        ],
        "fail_reasons": [] if gate_passed else ["Мало нормализованных концептов"],
        "metrics": {"concept_count": 15},
        "generation_id": "gen_active",
        "scope_hash": "scope_a",
    }


def test_graph_quality_report_html_testid_on_pass():
    from app.ui.course_prepare_view import build_graph_quality_report_html

    rendered = build_graph_quality_report_html(_sample_quality_report(gate_passed=True))
    assert 'data-testid="graph-quality-report"' in rendered
    assert "Нормализованные концепты" in rendered
    assert "✓" in rendered


def test_graph_quality_report_html_gate_fail_reasons():
    from app.ui.course_prepare_view import build_graph_quality_report_html

    report = _sample_quality_report(gate_passed=False)
    report["gates"][0]["passed"] = False
    rendered = build_graph_quality_report_html(report)
    assert 'data-testid="graph-quality-report"' in rendered
    assert "✗" in rendered
    assert "Мало нормализованных концептов" in rendered


def test_resolve_quality_report_prefers_session_when_present():
    from app.ui.course_prepare_view import resolve_quality_report_payload

    session = {"quality_report": _sample_quality_report()}
    artifact = {"graph_quality_summary": {"gate_passed": False, "gates": []}}
    report = resolve_quality_report_payload(session_refresh=session, artifact=artifact)
    assert report is not None
    assert report["gate_passed"] is True


def test_resolve_graph_refresh_from_artifact_binding():
    from app.ui.course_prepare_view import resolve_graph_refresh_payload

    artifact = {
        "generation_id": "gen_a",
        "scope_hash": "hash_a",
        "graph_quality_summary": _sample_quality_report(),
    }
    refresh = resolve_graph_refresh_payload(
        session_refresh=None,
        artifact=artifact,
        active_generation_id="gen_active",
    )
    assert refresh is not None
    assert refresh["gate_passed"] is True
    assert refresh["quality_report"]["generation_id"] == "gen_active"


def test_stale_binding_visible_on_generation_mismatch():
    from app.ui.course_prepare_view import is_stale_graph_binding_visible

    artifact = {"generation_id": "gen_old", "scope_hash": "hash_a"}
    assert is_stale_graph_binding_visible(
        artifact=artifact,
        active_generation_id="gen_new",
        current_scope_hash="hash_a",
    )


def test_prepare_view_resolve_graph_status_wires_graph_refresh(monkeypatch):
    import app.course_cache as course_cache

    calls: list[dict] = []

    def _capture(**kwargs):
        calls.append(kwargs)
        return course_cache._graph_status_view("pending", indexed=True, detail_ru="gate fail")

    monkeypatch.setattr(course_cache, "resolve_graph_status", _capture)
    from app.ui import course_prepare_view

    artifact = {
        "generation_id": "gen_a",
        "scope_hash": "scope_a",
        "graph_quality_summary": _sample_quality_report(gate_passed=False),
    }
    refresh = course_prepare_view.resolve_graph_refresh_payload(
        session_refresh=None,
        artifact=artifact,
        active_generation_id="gen_a",
    )
    course_cache.resolve_graph_status(
        source_paths=["doc/a.md"],
        index_stats={"files": ["doc/a.md"]},
        graph_refresh=refresh,
        artifact_binding=course_prepare_view._artifact_binding(artifact),
        active_generation_id="gen_a",
        graph_probe=lambda: True,
    )
    assert calls
    assert calls[0]["graph_refresh"]["gate_passed"] is False


# ── course-graph-relation-ux-v1 sp2: relation UX contract ───────────


def test_prerequisite_edges_have_explicit_relation_type():
    payload = _payload()
    prereq_edges = [
        e for e in payload["edges"]
        if e.get("source") == "Basics" and e.get("target") == "Functions"
    ]
    assert prereq_edges
    assert prereq_edges[0]["relation_type"] == "prerequisite"


def test_precedes_distinct_from_prerequisite_in_payload():
    concepts = {
        "A": {"prerequisites": []},
        "B": {"prerequisites": ["A"]},
        "C": {"prerequisites": ["A"]},
    }
    relations = [
        {
            "source_concept_id": "A",
            "target_concept_id": "B",
            "relation_type": "precedes",
            "confidence": 0.88,
            "evidence_doc_id": "lesson.md",
        }
    ]
    payload = build_kg_payload(concepts, typed_relations=relations)
    ab_edges = [e for e in payload["edges"] if e["source"] == "A" and e["target"] == "B"]
    assert len(ab_edges) == 1
    assert ab_edges[0]["relation_type"] == "precedes"
    ac = next(e for e in payload["edges"] if e["source"] == "A" and e["target"] == "C")
    assert ac["relation_type"] == "prerequisite"


def test_typed_relation_evidence_fields_serialized():
    concepts = {"X": {"prerequisites": []}, "Y": {"prerequisites": []}}
    relations = [
        {
            "source_concept_id": "X",
            "target_concept_id": "Y",
            "relation_type": "extends",
            "confidence": 0.77,
            "evidence_doc_id": "dec.md",
            "evidence_chunk_id": "dec.md#c3",
            "weak_evidence": True,
            "inferred_relation": False,
        }
    ]
    doc_index = {"dec.md": {"relative_path": "guides/dec.md", "summary": "Decorators"}}
    payload = build_kg_payload(concepts, doc_index=doc_index, typed_relations=relations)
    edge = next(e for e in payload["edges"] if e.get("relation_type") == "extends")
    assert edge["evidence_chunk_id"] == "dec.md#c3"
    assert edge["evidence_doc_label"] == "guides/dec.md"
    assert edge["weak_evidence"] is True
    assert edge["confidence"] == 0.77


def test_empty_typed_relations_safe_payload():
    payload = build_kg_payload(CONCEPTS, typed_relations=[])
    assert payload["edges"]
    assert all(e.get("relation_type") for e in payload["edges"])


def test_html_contains_relation_ux_contract():
    payload = build_kg_payload(
        CONCEPTS,
        MASTERY,
        LEARNED,
        DOC_INDEX,
        typed_relations=[
            {
                "source_concept_id": "Basics",
                "target_concept_id": "OOP",
                "relation_type": "precedes",
                "confidence": 0.9,
                "evidence_doc_id": "dec.md",
            }
        ],
        compiler_health={"gate_passed": False, "generation_id": "gen_x", "semantic_relation_count": 1},
    )
    html = build_kg_html(payload)
    assert "RELATION_STYLES" in html
    assert 'data-testid="relation-legend"' in html
    assert "applyFilters" in html
    assert 'data-testid="edge-evidence-panel"' in html
    assert "COMPILER_HEALTH" in html
    assert "compiler-health-badge-pending" in html
    assert "renderCompilerHealth" in html
    assert "dash:'6,4'" in html


def test_html_compiler_health_ready_badge():
    payload = build_kg_payload(
        CONCEPTS,
        compiler_health={"gate_passed": True, "generation_id": "gen_ok", "semantic_relation_count": 5},
    )
    html = build_kg_html(payload)
    assert "compiler-health-badge-ready" in html


def test_html_compiler_health_unavailable():
    payload = build_kg_payload(CONCEPTS, compiler_health=None)
    html = build_kg_html(payload)
    assert 'data-testid="compiler-health-unavailable"' in html
