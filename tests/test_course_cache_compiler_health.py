"""Compiler health resolver for Knowledge Graph D3 diagnostics (sp1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.course_cache import (
    course_scope_hash,
    detect_stale_graph_binding,
    resolve_compiler_health_for_kg,
    save_course_artifact,
    update_course_graph_binding,
)
from app.knowledge_graph_bundle import (
    write_graph_quality_report_sidecar,
    write_graph_snapshot_payload,
)


@pytest.fixture
def patched_generation_dir(tmp_path, monkeypatch):
    def _dir(generation_id: str) -> Path:
        return tmp_path / "generations" / generation_id

    monkeypatch.setattr("app.graph_generation_paths.generation_bundle_dir", _dir)
    return _dir


def test_resolve_compiler_health_for_kg_returns_none_when_sidecar_missing(
    patched_generation_dir,
) -> None:
    assert resolve_compiler_health_for_kg(
        source_paths=["agents/lesson1.md"],
        active_generation_id="gen_missing",
    ) is None


def test_resolve_compiler_health_for_kg_returns_required_keys(
    tmp_path,
    patched_generation_dir,
) -> None:
    generation_id = "gen_health_ok"
    source_paths = ["agents/lesson1.md", "agents/lesson2.md"]
    bundle_dir = patched_generation_dir(generation_id)
    write_graph_quality_report_sidecar(
        bundle_dir,
        {
            "gate_passed": True,
            "generation_id": generation_id,
            "scope_hash": course_scope_hash(source_paths),
            "metrics": {"concept_count": 12, "semantic_relation_count": 10},
            "fail_reasons": [],
            "gates": [],
        },
    )
    write_graph_snapshot_payload(
        bundle_dir,
        json.dumps(
            {
                "typed_relations": [
                    {"relation_type": "precedes", "confidence": 0.6},
                    {"relation_type": "uses", "confidence": 0.8},
                ]
            }
        ),
    )

    result = resolve_compiler_health_for_kg(
        source_paths=source_paths,
        active_generation_id=generation_id,
    )

    assert result is not None
    assert result["generation_id"] == generation_id
    assert result["scope_hash"] == course_scope_hash(source_paths)
    assert result["gate_passed"] is True
    assert result["semantic_relation_count"] == 10
    assert result["confidence_p50"] == pytest.approx(0.7)
    assert result["stale_binding"] is False
    assert result["scope_label"] == "agents"


def test_resolve_compiler_health_for_kg_confidence_p50_null_without_relations(
    patched_generation_dir,
) -> None:
    generation_id = "gen_zero_rel"
    source_paths = ["course/a.md"]
    bundle_dir = patched_generation_dir(generation_id)
    write_graph_quality_report_sidecar(
        bundle_dir,
        {
            "gate_passed": False,
            "generation_id": generation_id,
            "scope_hash": course_scope_hash(source_paths),
            "metrics": {"concept_count": 5, "semantic_relation_count": 0},
            "fail_reasons": ["Мало семантических связей"],
            "gates": [],
        },
    )
    write_graph_snapshot_payload(bundle_dir, json.dumps({"typed_relations": []}))

    result = resolve_compiler_health_for_kg(
        source_paths=source_paths,
        active_generation_id=generation_id,
    )

    assert result is not None
    assert result["confidence_p50"] is None
    assert result["semantic_relation_count"] == 0
    assert result["gate_passed"] is False
    assert result["fail_reasons"] == ["Мало семантических связей"]


def test_resolve_compiler_health_for_kg_stale_binding_on_generation_mismatch(
    tmp_path,
    patched_generation_dir,
    monkeypatch,
) -> None:
    generation_id = "gen_active"
    source_paths = ["agents/lesson1.md", "agents/lesson2.md"]
    bundle_dir = patched_generation_dir(generation_id)
    write_graph_quality_report_sidecar(
        bundle_dir,
        {
            "gate_passed": True,
            "generation_id": generation_id,
            "scope_hash": course_scope_hash(source_paths),
            "metrics": {"concept_count": 12, "semantic_relation_count": 8},
            "fail_reasons": [],
            "gates": [],
        },
    )
    write_graph_snapshot_payload(bundle_dir, json.dumps({"typed_relations": []}))

    cache_path = tmp_path / "course_artifacts.json"
    save_course_artifact(
        source_paths,
        {"learning_plan": {"plan": {}}},
        cache_path=cache_path,
    )
    update_course_graph_binding(
        source_paths,
        generation_id="gen_old",
        scope_hash=course_scope_hash(source_paths),
        graph_quality_summary={"gate_passed": True},
        cache_path=cache_path,
    )
    monkeypatch.setattr(
        "app.course_cache.default_course_cache_path",
        lambda: cache_path,
    )

    result = resolve_compiler_health_for_kg(
        source_paths=source_paths,
        active_generation_id=generation_id,
    )

    assert result is not None
    assert result["stale_binding"] is True
    assert detect_stale_graph_binding(
        artifact_generation_id="gen_old",
        active_generation_id=generation_id,
        artifact_scope_hash=course_scope_hash(source_paths),
        current_scope_hash=course_scope_hash(source_paths),
    )
