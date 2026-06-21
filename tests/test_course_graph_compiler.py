"""Course Graph Compiler — gate, alias merge, truncated JSON, binding."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.course_graph_compiler import (
    TruncatedExtractionError,
    compile_course_graph,
    evaluate_graph_quality_gate,
    slugify_concept_id,
)
from app.knowledge_graph_bundle import (
    GRAPH_QUALITY_REPORT_NAME,
    load_graph_quality_report,
    load_graph_snapshot_payload,
    retarget_staging_bundle_generation,
    staging_bundle_gate_allows_promote,
    write_bundle_for_staging,
    write_bundle_via_compiler,
)
from app.prompts.course_graph_extraction import is_truncated_llm_response

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "course_graph" / "ii_agenty_mock_extraction.json"


def _load_mock_by_doc() -> dict:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return dict(data.get("by_doc_id") or {})


def _mock_llm_extract(doc_id: str, _rows: list[dict]) -> tuple[dict, None]:
    payload = _load_mock_by_doc().get(doc_id)
    if payload is None:
        return {"concepts": [], "relations": []}, None
    return payload, None


def _mock_docs() -> list[SimpleNamespace]:
    docs = []
    for doc_id, extraction in _load_mock_by_doc().items():
        chunk_ids = {
            str(item.get("source_chunk_id") or "")
            for item in extraction.get("concepts") or []
        } | {
            str(item.get("evidence_chunk_id") or "")
            for item in extraction.get("relations") or []
        }
        for chunk_id in sorted(chunk_id for chunk_id in chunk_ids if chunk_id):
            docs.append(
                SimpleNamespace(
                    text=f"Content for {chunk_id}",
                    metadata={
                        "doc_id": doc_id,
                        "relative_path": doc_id,
                        "file_name": doc_id.split("/")[-1],
                        "title": doc_id,
                        "chunk_id": chunk_id,
                    },
                )
            )
    return docs


def test_slugify_concept_id_transliterates_cyrillic() -> None:
    slug = slugify_concept_id("Цикл агента")
    assert slug.isascii()
    assert slug


def test_is_truncated_llm_response_detects_length_and_invalid_json() -> None:
    assert is_truncated_llm_response("length", '{"concepts": [')
    assert is_truncated_llm_response(None, "")
    assert not is_truncated_llm_response("stop", '{"concepts": [], "relations": []}')


def test_compile_course_graph_gate_pass_mock_ii_agenty() -> None:
    result = compile_course_graph(
        _mock_docs(),
        generation_id="gen_test_001",
        scope_hash="scope123",
        llm_extract_fn=_mock_llm_extract,
    )
    assert result.gate_passed is True
    assert result.concept_count >= 12
    assert result.cross_doc_relations >= 3
    lesson_nodes = [
        cid
        for cid, node in (result.payload.get("concepts") or {}).items()
        if isinstance(node, dict) and node.get("level") == "lesson"
    ]
    assert len(lesson_nodes) == 3
    precedes = [
        rel
        for rel in result.payload.get("typed_relations") or []
        if isinstance(rel, dict) and rel.get("relation_type") == "precedes"
        and (rel.get("extraction_method") or "") == "curriculum_anchor"
    ]
    assert len(precedes) == 2
    typed = result.payload.get("typed_relations") or []
    assert all(rel.get("evidence_chunk_id") for rel in typed)
    concept_ids = set(result.payload.get("concepts") or {})
    assert all(
        prerequisite in concept_ids
        for concept in result.payload["concepts"].values()
        for prerequisite in concept.get("prerequisites") or []
    )
    for rel in typed:
        if rel.get("relation_type") == "related":
            assert rel.get("weak_evidence") is True


def test_lesson_anchors_excluded_from_filename_fallback_metric() -> None:
    result = compile_course_graph(
        _mock_docs(),
        generation_id="gen_lesson_anchor",
        scope_hash="scope_anchor",
        llm_extract_fn=_mock_llm_extract,
    )
    metrics = result.quality_report.metrics
    assert int(metrics.get("filename_fallback_nodes") or 0) == 0


def test_compile_passes_document_text_to_extractor() -> None:
    seen_text: list[str] = []

    def _capture(doc_id: str, rows: list[dict]) -> tuple[dict, None]:
        seen_text.extend(str(row.get("text") or "") for row in rows)
        return _mock_llm_extract(doc_id, rows)

    compile_course_graph(
        _mock_docs(),
        generation_id="gen_text",
        scope_hash="scope_text",
        llm_extract_fn=_capture,
    )
    assert seen_text
    assert all(text.startswith("Content for ") for text in seen_text)


def test_truncated_json_blocks_publication() -> None:
    def _truncated(_doc_id: str, _rows: list[dict]) -> tuple[dict, None]:
        raise TruncatedExtractionError("truncated")

    result = compile_course_graph(
        _mock_docs()[:1],
        generation_id="gen_trunc",
        scope_hash="scope_trunc",
        llm_extract_fn=_truncated,
    )
    assert result.gate_passed is False
    assert result.truncated is True
    assert not result.payload


def test_alias_merge_maps_labels() -> None:
    result = compile_course_graph(
        _mock_docs(),
        generation_id="gen_alias",
        scope_hash="scope_alias",
        llm_extract_fn=_mock_llm_extract,
    )
    assert result.quality_report.concept_id_map


def test_write_bundle_via_compiler_persists_quality_sidecar(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.course_cache.update_course_graph_binding",
        lambda *args, **kwargs: {"generation_id": kwargs.get("generation_id")},
    )
    stats = write_bundle_via_compiler(
        _mock_docs(),
        bundle_dir=tmp_path / "bundle",
        generation_id="gen_bundle",
        scope_hash="scope_bundle",
        source_paths=["agents/lesson1.md", "agents/lesson2.md", "agents/lesson3.md"],
        llm_extract_fn=_mock_llm_extract,
    )
    assert stats["gate_passed"] is True
    assert stats["published"] is True
    report = load_graph_quality_report(tmp_path / "bundle")
    assert report is not None
    assert report.get("gate_passed") is True
    assert (tmp_path / "bundle" / GRAPH_QUALITY_REPORT_NAME).exists()


def test_staging_gate_blocks_promote_when_failed() -> None:
    from app.graph_generation_paths import staging_bundle_dir

    col = "test__staging__gate"
    bundle_dir = staging_bundle_dir(col)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / GRAPH_QUALITY_REPORT_NAME).write_text(
        json.dumps({"gate_passed": False}),
        encoding="utf-8",
    )
    try:
        assert staging_bundle_gate_allows_promote(col) is False
    finally:
        import shutil

        shutil.rmtree(bundle_dir, ignore_errors=True)


def test_staging_gate_blocks_promote_without_sidecar() -> None:
    assert staging_bundle_gate_allows_promote("missing_sidecar_collection") is False


def test_hallucinated_evidence_chunk_blocks_gate() -> None:
    def _hallucinated(doc_id: str, rows: list[dict]) -> tuple[dict, None]:
        payload, _ = _mock_llm_extract(doc_id, rows)
        copied = json.loads(json.dumps(payload))
        for relation in copied.get("relations") or []:
            relation["evidence_chunk_id"] = "missing#chunk"
        return copied, None

    result = compile_course_graph(
        _mock_docs(),
        generation_id="gen_bad_evidence",
        scope_hash="scope_bad_evidence",
        llm_extract_fn=_hallucinated,
    )
    assert result.gate_passed is False
    assert result.quality_report.metrics["relations_with_evidence_pct"] < 100.0


def test_staging_bundle_retargets_generation_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.graph_generation_paths import staging_bundle_dir

    collection = "test__staging__retarget"
    monkeypatch.setattr("app.knowledge_graph_bundle.staging_bundle_dir", lambda _name: staging_bundle_dir(collection))
    bundle_dir = staging_bundle_dir(collection)
    try:
        stats = write_bundle_for_staging(
            _mock_docs(),
            collection,
            {},
            source_paths=["agents/lesson1.md", "agents/lesson2.md", "agents/lesson3.md"],
            source_content_hashes=["h1", "h2", "h3"],
            use_compiler=True,
            llm_extract_fn=_mock_llm_extract,
        )
        assert stats["gate_passed"] is True
        assert retarget_staging_bundle_generation(collection, "gen_actual") is True
        payload = json.loads(load_graph_snapshot_payload(bundle_dir) or "{}")
        report = load_graph_quality_report(bundle_dir) or {}
        assert payload["generation_id"] == "gen_actual"
        assert report["generation_id"] == "gen_actual"
        assert all(
            relation["generation_id"] == "gen_actual"
            for relation in payload.get("typed_relations") or []
        )
    finally:
        import shutil

        shutil.rmtree(bundle_dir, ignore_errors=True)


def test_compiler_bundle_health_resolver_ready_without_health_stubs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import course_cache, knowledge_graph
    from app.knowledge_graph import SqliteBundleKnowledgeGraph

    source_paths = ["agents/lesson1.md", "agents/lesson2.md", "agents/lesson3.md"]
    bundle_dir = tmp_path / "bundle"
    stats = write_bundle_via_compiler(
        _mock_docs(),
        bundle_dir=bundle_dir,
        generation_id="gen_integration",
        scope_hash=course_cache.course_scope_hash(source_paths),
        source_paths=source_paths,
        source_content_hashes=["h1", "h2", "h3"],
        bind_on_publish=False,
        llm_extract_fn=_mock_llm_extract,
    )
    graph = SqliteBundleKnowledgeGraph(bundle_dir)
    monkeypatch.setattr(knowledge_graph, "get_active_knowledge_graph", lambda: graph)

    health = knowledge_graph.get_graph_prerequisites_health()
    assert health["relation_count"] > 0
    view = course_cache.resolve_graph_status(
        source_paths=source_paths,
        index_stats={"files": source_paths},
        graph_refresh=stats,
        active_generation_id="gen_integration",
        graph_probe=lambda: True,
    )
    assert view.status == "ready"


def test_heuristic_path_never_gate_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.course_cache.graph_llm_probe_ok", lambda **kwargs: False)
    from app.knowledge_graph import write_staging_knowledge_graph_bundle

    docs = [
        SimpleNamespace(
            metadata={
                "doc_id": "only.md",
                "relative_path": "only.md",
                "file_name": "only.md",
                "title": "only.md",
            }
        )
    ]
    stats = write_staging_knowledge_graph_bundle(docs, "col_heuristic_test")
    assert stats.get("gate_passed") is False
    assert stats.get("published") is False


def test_evaluate_graph_quality_gate_filename_fallback_fails() -> None:
    metrics = {
        "doc_count": 3,
        "concept_count": 15,
        "semantic_relation_count": 12,
        "cross_doc_relations": 4,
        "docs_participating_pct": 100.0,
        "concepts_with_evidence_pct": 100.0,
        "relations_with_evidence_pct": 100.0,
        "orphan_rate_pct": 10.0,
        "dangling_refs": 0,
        "prerequisite_cycles": 0,
        "filename_fallback_nodes": 2,
    }
    passed, _gates, reasons = evaluate_graph_quality_gate(metrics)
    assert passed is False
    assert reasons
