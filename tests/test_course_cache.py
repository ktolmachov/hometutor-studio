from __future__ import annotations

import pytest

from app.course_cache import (
    course_artifact_key,
    course_scope_hash,
    ensure_plan_v2_pace_mode,
    first_session_artifact_path,
    invalidate_first_session_artifact,
    list_course_candidates,
    load_course_artifact,
    load_first_session_artifact_for_scope,
    normalize_source_paths,
    save_course_artifact,
    save_first_session_artifact,
)


def test_normalize_source_paths_deduplicates_and_sorts() -> None:
    assert normalize_source_paths(["b.md", " a.md ", "b.md", ""]) == ["a.md", "b.md"]


def test_course_scope_hash_is_order_independent() -> None:
    left = course_scope_hash(["course/lec2.md", "course/lec1.md"])
    right = course_scope_hash(["course/lec1.md", "course/lec2.md"])

    assert left == right
    assert len(left) == 12


def test_course_artifact_key_includes_model_and_prompt_version() -> None:
    base = ["course/lec1.md"]

    assert course_artifact_key(base, model_id="model-a") != course_artifact_key(base, model_id="model-b")
    assert course_artifact_key(base, model_id="model-a", prompt_version="v1") != course_artifact_key(
        base,
        model_id="model-a",
        prompt_version="v2",
    )


def test_save_and_load_course_artifact(tmp_path) -> None:
    cache_path = tmp_path / "course_artifacts.json"
    docs = ["course/lec2.md", "course/lec1.md"]

    saved = save_course_artifact(
        docs,
        {"learning_plan": {"plan": "Step 1"}, "flashcards_preview": ["Q1"]},
        model_id="test-model",
        cache_path=cache_path,
    )
    loaded = load_course_artifact(docs[::-1], model_id="test-model", cache_path=cache_path)

    assert loaded == saved
    assert loaded["source_paths"] == ["course/lec1.md", "course/lec2.md"]
    assert loaded["learning_plan"]["plan"] == "Step 1"


def test_save_course_artifact_sets_default_pace_mode(tmp_path) -> None:
    cache_path = tmp_path / "course_artifacts.json"
    saved = save_course_artifact(
        ["course/lec1.md"],
        {"learning_plan": {"plan": {"v2": {}}}},
        model_id="test-model",
        cache_path=cache_path,
    )
    assert saved["learning_plan"]["plan"]["v2"]["pace_mode"] == "steady"


def test_list_course_candidates_finds_dense_folders(tmp_path) -> None:
    root = tmp_path / "docs"
    c1 = root / "DenseCourse"
    c1.mkdir(parents=True)
    (c1 / "a.pdf").write_text("x", encoding="utf-8")
    (c1 / "b.md").write_text("y", encoding="utf-8")
    (c1 / "nested").mkdir(parents=True)
    (c1 / "nested" / "c.txt").write_text("z", encoding="utf-8")
    sparse = root / "TooSmall"
    sparse.mkdir()
    (sparse / "one.pdf").write_text("p", encoding="utf-8")
    junk = sparse / "x.bin"
    junk.write_bytes(b"\0")

    found = list_course_candidates(docs_root=root, min_supported_files=3)
    names = [x["folder_rel"] for x in found]
    assert "DenseCourse" in names


def test_ensure_plan_v2_pace_mode_normalizes_values() -> None:
    artifact = {"learning_plan": {"plan": {"v2": {"pace_mode": "DEEP"}}}}
    normalized = ensure_plan_v2_pace_mode(artifact)
    assert normalized["learning_plan"]["plan"]["v2"]["pace_mode"] == "deep"


def test_first_session_save_load_and_scope_gate(tmp_path, monkeypatch) -> None:
    cache_root = tmp_path / "cache" / "real"
    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: cache_root)
    monkeypatch.setattr("app.course_cache._balance_data_mode_tag", lambda _s=None: "real")

    docs = ["Course/lec1.md", "Course/lec2.md"]
    payload = {
        "course_id": "Course",
        "scope_hash": course_scope_hash(docs),
        "baseline_mission": {"title": "Start", "primary_cta": "Go"},
        "seed_questions": [{"q": "Q?", "retrieval_trace": {"source_paths": docs[:1]}}],
    }
    save_first_session_artifact("Course", payload)

    scope_ok = {"folder_rel": "Course", "source_paths": docs}
    loaded = load_first_session_artifact_for_scope(scope_ok)
    assert loaded is not None
    assert loaded["baseline_mission"]["title"] == "Start"

    scope_stale = {"folder_rel": "Course", "source_paths": docs + ["Course/new.md"]}
    assert load_first_session_artifact_for_scope(scope_stale) is None


def test_first_session_data_mode_partition(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.course_cache._balance_data_mode_tag", lambda _s=None: "fixture")
    cache_root = tmp_path / "cache" / "first_session" / "fixture"
    path = first_session_artifact_path("Course", cache_root=cache_root)
    assert path.parent.name == "fixture"
    assert path.name == "Course.json"


def test_first_session_atomic_write_discards_tmp_on_failure(tmp_path, monkeypatch) -> None:
    cache_root = tmp_path / "cache" / "real"
    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: cache_root)
    path = first_session_artifact_path("Broken", cache_root=cache_root)

    def _fail_replace(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr("app.course_cache.os.replace", _fail_replace)

    with pytest.raises(OSError):
        save_first_session_artifact("Broken", {"course_id": "Broken", "scope_hash": "abc"})

    assert not path.exists()
    assert list(cache_root.glob("*.tmp")) == []


def test_invalidate_first_session_artifact(tmp_path, monkeypatch) -> None:
    cache_root = tmp_path / "cache" / "real"
    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: cache_root)
    save_first_session_artifact("Course", {"course_id": "Course", "scope_hash": "x"})
    invalidate_first_session_artifact("Course")
    assert not first_session_artifact_path("Course", cache_root=cache_root).exists()

