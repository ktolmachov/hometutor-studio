"""Property graph bundle per generation (итерация 16 tail / ADR-020)."""

import json
from pathlib import Path

from app.graph_generation_paths import promote_staging_bundle
from app.knowledge_graph import (
    SqliteBundleKnowledgeGraph,
    build_graph_payload_from_documents,
    invalidate_knowledge_graph_singleton,
)
from app.knowledge_graph_bundle import (
    KG_SQLITE_NAME,
    PROPERTY_GRAPH_STORE_NAME,
    persist_graph_bundle_to_dir,
    write_graph_quality_report_sidecar,
)


def test_build_graph_payload_counts_relations():
    class Doc:
        def __init__(self, meta):
            self.metadata = meta

    payload = build_graph_payload_from_documents(
        [
            Doc(
                {
                    "doc_id": "a.md",
                    "relative_path": "a.md",
                    "title": "T",
                    "topic": "A",
                    "concepts": "B, C",
                }
            )
        ],
        {},
    )
    assert int(payload.pop("_relation_count", 0)) >= 1
    assert "A" in payload["concepts"]
    assert "B" in payload["concepts"]


def test_persist_and_load_sqlite_bundle_roundtrip(tmp_path):
    data = {
        "concepts": {"X": {"description": "d", "prerequisites": [], "related_concepts": [], "documents": [], "related_documents": [], "learned": False}},
        "documents": {},
        "edges": {},
        "generated_at": "t",
        "source_doc_count": 0,
        "source_concept_count": 1,
    }
    persist_graph_bundle_to_dir(tmp_path, data)
    assert (tmp_path / KG_SQLITE_NAME).exists()
    assert (tmp_path / PROPERTY_GRAPH_STORE_NAME).exists()

    kg = SqliteBundleKnowledgeGraph(tmp_path)
    assert "X" in kg.get_concepts()


def test_promote_moves_staging_to_generation(tmp_path, monkeypatch):
    from app import graph_generation_paths as gp

    monkeypatch.setattr(gp, "GRAPH_GENERATIONS_ROOT", tmp_path / "gg")
    monkeypatch.setattr(gp, "STAGING_ROOT", gp.GRAPH_GENERATIONS_ROOT / "staging")
    monkeypatch.setattr(gp, "BY_GENERATION_ROOT", gp.GRAPH_GENERATIONS_ROOT / "by_generation")

    staging = gp.staging_bundle_dir("col__staging__abc")
    staging.mkdir(parents=True)
    payload = {"concepts": {}, "documents": {}, "edges": {}}
    import sqlite3

    p = staging / "kg.sqlite"
    conn = sqlite3.connect(str(p))
    conn.execute("CREATE TABLE graph_snapshot (id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)")
    conn.execute(
        "INSERT INTO graph_snapshot VALUES (1, ?)",
        (json.dumps(payload),),
    )
    conn.commit()
    conn.close()
    write_graph_quality_report_sidecar(staging, {"gate_passed": True})

    ok = promote_staging_bundle("col__staging__abc", "gen_xyz")
    assert ok is True
    assert not staging.exists()
    dst = gp.generation_bundle_dir("gen_xyz")
    assert (dst / "kg.sqlite").exists()

    invalidate_knowledge_graph_singleton()
