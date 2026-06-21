"""Course activation delight — graph resolver and Mission Control merge (sp1)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app import course_cache
from app.path_safety import resolve_data_relative_path, validate_data_relative_path


def _indexed_stats(*paths: str) -> dict:
    return {"files": list(paths), "folder_rel_options": []}


@pytest.mark.parametrize(
    "graph_refresh,health,probe,expected_status",
    [
        (
            {"ok": True},
            {"concept_count": 3, "relation_count": 2, "has_prerequisite_cycles": False},
            True,
            "ready",
        ),
        (
            {"ok": False},
            {"concept_count": 3, "has_prerequisite_cycles": False},
            True,
            "pending",
        ),
        (
            {"ok": True},
            {"concept_count": 0, "has_prerequisite_cycles": False},
            True,
            "pending",
        ),
        (
            {"ok": True},
            {"concept_count": 2, "has_prerequisite_cycles": False},
            False,
            "unavailable",
        ),
    ],
)
def test_resolve_graph_status_parametrized(
    graph_refresh,
    health,
    probe,
    expected_status,
) -> None:
    paths = ["ml/intro.md", "ml/week1.pdf"]
    view = course_cache.resolve_graph_status(
        source_paths=paths,
        index_stats=_indexed_stats(*paths),
        graph_refresh=graph_refresh,
        graph_probe=lambda: probe,
        health_fn=lambda: health,
        bundle_fn=lambda: {"topological_preview": ["c1", "c2"]},
    )
    assert view.status == expected_status
    if expected_status == "ready":
        assert view.testid == "graph-status-badge-ready"
        assert view.prerequisite_labels == ["c1", "c2"]
        assert view.indexed is True


def test_resolve_graph_status_empty_paths_unavailable() -> None:
    view = course_cache.resolve_graph_status(source_paths=[])
    assert view.status == "unavailable"
    assert view.indexed is False


def test_resolve_graph_status_not_indexed_pending() -> None:
    view = course_cache.resolve_graph_status(
        source_paths=["ml/a.md"],
        index_stats={"files": ["other/b.md"]},
        graph_probe=lambda: True,
    )
    assert view.status == "pending"
    assert view.indexed is False
    assert "проиндексируйте" in view.detail_ru


def test_resolve_graph_status_unknown_refresh_pending() -> None:
    view = course_cache.resolve_graph_status(
        source_paths=["c/a.md"],
        index_stats=_indexed_stats("c/a.md"),
        graph_refresh=None,
        graph_probe=lambda: True,
        health_fn=lambda: {"concept_count": 5, "has_prerequisite_cycles": False},
    )
    assert view.status == "pending"


def test_graph_llm_probe_ok_false_on_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise():
        raise ValueError("OPENAI_API_KEY не найден в .env")

    monkeypatch.setattr("app.provider.get_graph_llm", _raise)
    assert course_cache.graph_llm_probe_ok() is False


def test_validate_data_relative_path_rejects_escape(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_data_relative_path(str(outside), data_dir=data_dir)
    with pytest.raises(ValueError):
        resolve_data_relative_path("../secret.md", data_dir=data_dir)


def test_build_mission_control_course_options_merges_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        course_cache,
        "list_course_candidates",
        lambda **kwargs: [{"folder_rel": "HeuristicOnly", "supported_file_count": 4}],
    )
    index_stats = _indexed_stats("Indexed/a.md")
    index_stats["folder_rel_options"] = ["Indexed"]
    options = course_cache.build_mission_control_course_options(index_stats)
    folders = [course_cache._normalize_folder_rel(o["folder_rel"]) for o in options]
    assert "Indexed" in folders
    assert "HeuristicOnly" in folders
    by_rel = {course_cache._normalize_folder_rel(o["folder_rel"]): o for o in options}
    assert by_rel["Indexed"]["needs_reindex"] is False
    assert by_rel["HeuristicOnly"]["needs_reindex"] is True


def test_build_mission_control_course_options_dedupes_by_folder_rel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        course_cache,
        "list_course_candidates",
        lambda **kwargs: [{"folder_rel": "Shared", "supported_file_count": 3}],
    )
    index_stats = _indexed_stats("Shared/x.md")
    index_stats["folder_rel_options"] = ["Shared"]
    options = course_cache.build_mission_control_course_options(index_stats)
    assert len([o for o in options if o["folder_rel"] == "Shared"]) == 1
    assert options[0]["needs_reindex"] is False


def test_resolve_graph_status_gate_fail_pending() -> None:
    paths = ["ml/a.md", "ml/b.md", "ml/c.md"]
    view = course_cache.resolve_graph_status(
        source_paths=paths,
        index_stats=_indexed_stats(*paths),
        graph_refresh={
            "ok": True,
            "gate_passed": False,
            "quality_report": {"fail_reasons": ["Мало междокументных связей"]},
        },
        graph_probe=lambda: True,
        health_fn=lambda: {"concept_count": 12, "relation_count": 10, "has_prerequisite_cycles": False},
    )
    assert view.status == "pending"
    assert "междокументных" in view.detail_ru.lower()


def test_resolve_graph_status_gate_pass_ready() -> None:
    paths = ["ml/a.md", "ml/b.md"]
    view = course_cache.resolve_graph_status(
        source_paths=paths,
        index_stats=_indexed_stats(*paths),
        graph_refresh={"ok": True, "gate_passed": True, "generation_id": "gen_active"},
        graph_probe=lambda: True,
        health_fn=lambda: {"concept_count": 12, "relation_count": 10, "has_prerequisite_cycles": False},
        bundle_fn=lambda: {"topological_preview": ["Concept A"]},
    )
    assert view.status == "ready"


def test_resolve_graph_status_stale_binding_pending() -> None:
    paths = ["ml/a.md", "ml/b.md"]
    view = course_cache.resolve_graph_status(
        source_paths=paths,
        index_stats=_indexed_stats(*paths),
        graph_refresh={"ok": True, "gate_passed": True, "generation_id": "gen_active"},
        artifact_binding={"generation_id": "gen_old", "scope_hash": course_cache.course_scope_hash(paths)},
        active_generation_id="gen_active",
        graph_probe=lambda: True,
        health_fn=lambda: {"concept_count": 12, "relation_count": 10, "has_prerequisite_cycles": False},
    )
    assert view.status == "pending"
    assert "устарела" in view.detail_ru.lower()


def test_detect_stale_graph_binding_generation_mismatch() -> None:
    assert course_cache.detect_stale_graph_binding(
        artifact_generation_id="gen_a",
        active_generation_id="gen_b",
        artifact_scope_hash="same",
        current_scope_hash="same",
    )


def test_update_course_graph_binding_persists_fields(tmp_path) -> None:
    paths = ["course/a.md", "course/b.md"]
    saved = course_cache.update_course_graph_binding(
        paths,
        generation_id="gen_bind",
        scope_hash=course_cache.course_scope_hash(paths),
        graph_quality_summary={"gate_passed": True, "published": True},
        source_content_hashes=["hash1"],
        cache_path=tmp_path / "course_artifacts.json",
    )
    assert saved is not None
    assert saved["generation_id"] == "gen_bind"
    loaded = course_cache.load_course_artifact(paths, cache_path=tmp_path / "course_artifacts.json")
    assert loaded is not None
    assert loaded.get("graph_quality_summary", {}).get("gate_passed") is True


def test_enrichment_disabled_never_calls_get_ingestion_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def _track():
        calls.append("ingestion")
        return MagicMock()

    monkeypatch.setattr("app.provider.get_ingestion_llm", _track)

    class _Settings:
        enable_metadata_enrichment = False

    paths = ["course/a.md"]
    course_cache.resolve_graph_status(
        source_paths=paths,
        index_stats=_indexed_stats("course/a.md"),
        graph_refresh={"ok": True},
        settings=_Settings(),
        graph_probe=lambda: True,
        health_fn=lambda: {"concept_count": 1, "has_prerequisite_cycles": False},
        bundle_fn=lambda: {"topological_preview": ["x"]},
    )
    course_cache.build_mission_control_course_options(_indexed_stats("course/a.md"))
    assert calls == []
