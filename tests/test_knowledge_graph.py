"""JsonKnowledgeGraph: reader API + tutor helpers."""

import json
from pathlib import Path
from types import SimpleNamespace

from app.knowledge_graph import (
    JsonKnowledgeGraph,
    build_graph_payload_from_documents,
    get_knowledge_graph,
    get_personalized_subgraph,
    knowledge_graph,
)


def test_build_graph_payload_sets_provenance():
    docs = [
        SimpleNamespace(
            metadata={
                "doc_id": "lectures/a.md",
                "relative_path": "lectures/a.md",
                "topic": "TopicA",
                "key_concepts": "c1, c2",
            }
        ),
    ]
    payload = build_graph_payload_from_documents(docs, {})
    assert "graph_build_updated_at" in payload
    assert payload["concepts"]
    for _name, c in payload["concepts"].items():
        prov = c.get("provenance")
        assert isinstance(prov, dict)
        assert prov.get("extraction_method") == "heuristic"
        assert "updated_at" in prov


def test_json_kg_load_migrates_missing_provenance(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(
        '{"concepts": {"X": {"description": "", "documents": ["d.md"], "prerequisites": [], "related_concepts": [], "learned": false}}, "documents": {}, "edges": {}}',
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    x = kg.get_concepts().get("X") or {}
    assert x.get("provenance", {}).get("extraction_method") == "legacy"


def test_get_knowledge_graph_default_is_json_reader(tmp_path):
    g = get_knowledge_graph(tmp_path / "g.json")
    assert isinstance(g, JsonKnowledgeGraph)
    assert g.get_concepts() == {}


def test_next_best_action_and_prereqs(tmp_path):
    path = tmp_path / "kg.json"
    data = {
        "concepts": {
            "A": {"description": "", "prerequisites": []},
            "B": {"description": "", "prerequisites": ["A"]},
            "C": {"description": "", "prerequisites": ["A", "B"]},
        },
        "documents": {},
        "edges": {},
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    kg = JsonKnowledgeGraph(path)
    r = kg.next_best_action("A", learned_concepts=[])
    assert r["action"] == "next_concept"
    assert r["concept"] == "B"
    ok, miss = kg.check_prerequisites("C", ["A"])
    assert ok is False
    assert "B" in miss
    ok2, miss2 = kg.check_prerequisites("C", ["A", "B"])
    assert ok2 is True and miss2 == []


def test_recommend_tutor_next_step_is_graph_aware_for_advance(tmp_path):
    path = tmp_path / "kg_recommend.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "RAG": {"description": "", "prerequisites": []},
                    "MultiTurn": {"description": "", "prerequisites": ["RAG"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)

    out = kg.recommend_tutor_next_step(
        current_concept="RAG",
        learned_concepts=["Embedding"],
        route="advance",
    )

    assert out["next_action"] == "Следующий шаг"
    assert "MultiTurn" in out["next_action_reason"]
    assert out["graph_recommendation"]["concept"] == "MultiTurn"


def test_recommend_tutor_next_step_prioritizes_due_review(tmp_path):
    path = tmp_path / "kg_due.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "RAG": {"description": "", "prerequisites": []},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)

    out = kg.recommend_tutor_next_step(
        current_concept="RAG",
        learned_concepts=[],
        route="due_review",
        due_review_preview=["Embeddings"],
    )

    assert out["next_action"] == "Пора повторить"
    assert "Embeddings" in out["next_action_reason"]
    assert out["suggested_ctas"][0] == "Пора повторить"


def test_get_next_best_actions_scores(tmp_path):
    path = tmp_path / "nba.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    pct = {"A": 30.0, "B": 40.0}
    due = {"A": 1.0}
    rows = kg.get_next_best_actions(pct, limit=2, due_priority=due)
    assert len(rows) >= 1
    assert rows[0]["concept"] == "A"


def test_get_graph_summary_empty_and_nonempty(tmp_path):
    empty = JsonKnowledgeGraph(tmp_path / "e.json")
    assert "0%" in empty.get_graph_summary([]) or "нет концептов" in empty.get_graph_summary(
        []
    ).lower()

    p = tmp_path / "k.json"
    p.write_text(
        json.dumps({"concepts": {"X": {"prerequisites": []}}, "documents": {}, "edges": {}}),
        encoding="utf-8",
    )
    g = JsonKnowledgeGraph(p)
    s = g.get_graph_summary(["X"])
    assert "100" in s or "1" in s


def test_module_singleton_is_lazy_proxy():
    assert type(knowledge_graph).__name__ == "_KnowledgeGraphProxy"
    assert callable(knowledge_graph.get_concepts)


def test_get_progress_stats(tmp_path):
    path = tmp_path / "kg.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {
                        "description": "",
                        "prerequisites": [],
                        "learned": True,
                        "learned_at": "2025-01-02T00:00:00",
                        "level": "beginner",
                    },
                    "B": {"description": "", "prerequisites": [], "level": "advanced"},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    s = kg.get_progress_stats()
    assert s["total_concepts"] == 2
    assert s["learned"] == 1
    assert s["mastery_percent"] == 50.0
    assert len(s["recent_timeline"]) >= 1
    assert "beginner" in s["level_distribution"]


def test_mark_concepts_as_learned(tmp_path):
    path = tmp_path / "kg.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    assert kg.mark_concepts_as_learned(["A", "B", "missing"]) == 2
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["concepts"]["A"].get("learned") is True
    assert "learned_at" in data["concepts"]["A"]


def test_rebuild_from_ingestion_documents_uses_metadata_and_preserves_progress(tmp_path):
    path = tmp_path / "kg_ingestion.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "RAG": {"description": "Old", "prerequisites": [], "learned": True, "learned_at": "2025-01-01T00:00:00"}
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)

    stats = kg.rebuild_from_ingestion_documents(
        [
            SimpleNamespace(
                metadata={
                    "doc_id": "course/module/lesson.md",
                    "relative_path": "course/module/lesson.md",
                    "title": "Lesson",
                    "topic": "RAG",
                    "concepts": "Embeddings, Retriever",
                }
            )
        ]
    )

    concepts = kg.get_concepts()
    assert stats["documents"] == 1
    assert stats["concepts"] == 3
    assert "RAG" in concepts
    assert concepts["RAG"]["learned"] is True
    assert concepts["Embeddings"]["prerequisites"] == ["RAG"]
    assert concepts["Retriever"]["prerequisites"] == ["Embeddings"]
    assert "course/module/lesson.md" in concepts["Retriever"]["documents"]


def test_get_personalized_subgraph(tmp_path):
    path = tmp_path / "kg.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "T": {
                        "description": "",
                        "prerequisites": [],
                        "related_concepts": ["R"],
                    },
                    "R": {"description": "", "prerequisites": []},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    s = get_personalized_subgraph(seed_topic="T", limit=4, kg=kg)
    assert s["seed_topic"] == "T"
    assert isinstance(s["nodes"], list) and len(s["nodes"]) >= 1
    assert "mastery" in s


def test_find_prerequisite_cycles_empty():
    kg = JsonKnowledgeGraph.__new__(JsonKnowledgeGraph)
    kg._data = {"concepts": {}, "documents": {}, "edges": {}}
    assert kg.find_prerequisite_cycles([]) == []


def test_find_prerequisite_cycles_two_node_cycle(tmp_path):
    path = tmp_path / "cyc.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": ["B"]},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    cyc = kg.find_prerequisite_cycles(["A", "B"])
    assert len(cyc) == 1
    assert set(cyc[0]) == {"A", "B"}


def test_find_prerequisite_cycles_self_loop(tmp_path):
    path = tmp_path / "loop.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    assert kg.find_prerequisite_cycles(["A"]) == [["A"]]


def test_topological_sort_acyclic_matches_kahn(tmp_path):
    path = tmp_path / "dag.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                    "B": {"description": "", "prerequisites": ["A"]},
                    "C": {"description": "", "prerequisites": ["B"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    order = kg.topological_sort(["A", "B", "C"])
    assert order == ["A", "B", "C"]


def test_topological_sort_cycle_fallback_and_trace(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": ["B"]},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    trace: dict = {}
    out = kg.topological_sort(["A", "B"], trace=trace)
    assert out == ["A", "B"]
    assert trace["topological_order_ok"] is False
    assert trace["fallback"] == "identity_order"
    assert len(trace["prerequisite_cycles"]) >= 1


def test_remove_prerequisite_edge_breaks_cycle(tmp_path):
    path = tmp_path / "fix.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": ["B"]},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {"A": ["B"], "B": ["A"]},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    assert kg.remove_prerequisite_edge("A", "B") is True
    assert kg.find_prerequisite_cycles(["A", "B"]) == []
    assert kg.topological_sort(["A", "B"]) == ["A", "B"]


def test_get_next_best_actions_trace_reports_cycles(tmp_path):
    path = tmp_path / "nba_cyc.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": ["B"]},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    trace: dict = {}
    rows = kg.get_next_best_actions(
        {"A": 50.0, "B": 50.0},
        limit=5,
        due_priority={},
        trace=trace,
    )
    assert isinstance(rows, list)
    assert trace.get("topological_order_ok") is False
    assert trace.get("prerequisite_cycles")


def test_topological_sort_logs_cycle(caplog, tmp_path):
    import logging

    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)

    path = tmp_path / "logcyc.json"
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": ["B"]},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    caplog.set_level(logging.WARNING)
    try:
        kg.topological_sort(["A", "B"])
        assert "topological_sort_prerequisite_cycles" in caplog.text
    finally:
        app_logger.removeHandler(caplog.handler)
