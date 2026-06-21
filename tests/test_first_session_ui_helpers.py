"""Unit tests for First Session cold-open scope and populated-gate helpers."""

from __future__ import annotations

import pytest

from app.course_cache import (
    first_session_artifact_is_populated,
    load_first_session_artifact_for_scope,
    resolve_first_session_scope_for_home,
    study_scope_from_course_option,
)


def test_study_scope_from_course_option_dict() -> None:
    scope = study_scope_from_course_option(
        {
            "folder_rel": "CourseA",
            "title": "Курс: CourseA",
            "source_paths": ["CourseA/a.md", "CourseA/b.md"],
        }
    )
    assert scope == {
        "folder_rel": "CourseA",
        "title": "Курс: CourseA",
        "source_paths": ["CourseA/a.md", "CourseA/b.md"],
    }


def test_resolve_first_session_scope_active_scope_present() -> None:
    active = {
        "id": "abc",
        "active": True,
        "folder_rel": "ActiveCourse",
        "title": "Active",
        "source_paths": ["ActiveCourse/doc.md"],
    }
    result = resolve_first_session_scope_for_home(
        index_stats={"folder_rel_options": ["Other"], "files": []},
        active_scope=active,
    )
    assert result is active


def test_resolve_first_session_scope_single_candidate() -> None:
    index_stats = {
        "folder_rel_options": ["Solo"],
        "files": ["Solo/lec.md"],
    }
    result = resolve_first_session_scope_for_home(index_stats=index_stats, active_scope=None)
    assert result == {
        "folder_rel": "Solo",
        "title": "Курс: Solo",
        "source_paths": ["Solo/lec.md"],
    }


def test_resolve_first_session_scope_multiple_candidates_first_sorted() -> None:
    index_stats = {
        "folder_rel_options": ["Beta", "Alpha", "Gamma"],
        "files": ["Alpha/a.md", "Beta/b.md", "Gamma/g.md"],
    }
    result = resolve_first_session_scope_for_home(index_stats=index_stats, active_scope=None)
    assert result is not None
    assert result["folder_rel"] == "Alpha"


def test_resolve_first_session_scope_zero_candidates() -> None:
    assert resolve_first_session_scope_for_home(index_stats={}, active_scope=None) is None
    assert resolve_first_session_scope_for_home(index_stats=None, active_scope=None) is None


@pytest.mark.parametrize(
    ("artifact", "expected"),
    [
        (None, False),
        ({}, False),
        ({"baseline_mission": {}}, False),
        ({"baseline_mission": {"title": ""}, "seed_questions": [{"q": "Q?"}]}, False),
        ({"baseline_mission": {"title": "Start"}, "seed_questions": []}, False),
        ({"baseline_mission": {"title": "Start"}, "seed_questions": [{"q": ""}]}, False),
        (
            {
                "baseline_mission": {"title": "Start", "primary_cta": "Go"},
                "seed_questions": [{"q": "What?", "retrieval_trace": {"source_paths": ["a.md"]}}],
            },
            True,
        ),
    ],
)
def test_first_session_artifact_is_populated(artifact, expected) -> None:
    assert first_session_artifact_is_populated(artifact) is expected


def test_load_first_session_artifact_missing_returns_none(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: tmp_path)
    scope = {"folder_rel": "Missing", "source_paths": ["Missing/a.md"]}
    assert load_first_session_artifact_for_scope(scope) is None


def test_load_first_session_artifact_stale_scope_hash_returns_none(tmp_path, monkeypatch) -> None:
    from app.course_cache import course_scope_hash, save_first_session_artifact

    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: tmp_path)
    docs = ["Stale/a.md"]
    save_first_session_artifact(
        "Stale",
        {
            "course_id": "Stale",
            "scope_hash": course_scope_hash(docs),
            "baseline_mission": {"title": "T", "primary_cta": "Go"},
            "seed_questions": [{"q": "Q?", "retrieval_trace": {"source_paths": docs}}],
        },
    )
    scope_stale = {"folder_rel": "Stale", "source_paths": docs + ["Stale/new.md"]}
    assert load_first_session_artifact_for_scope(scope_stale) is None


def test_populated_gate_rejects_loader_result_when_partial(tmp_path, monkeypatch) -> None:
    from app.course_cache import course_scope_hash, save_first_session_artifact

    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: tmp_path)
    docs = ["Course/a.md"]
    save_first_session_artifact(
        "Course",
        {
            "course_id": "Course",
            "scope_hash": course_scope_hash(docs),
            "baseline_mission": {"title": "", "primary_cta": "Go"},
            "seed_questions": [],
        },
    )
    scope = resolve_first_session_scope_for_home(
        index_stats={"folder_rel_options": ["Course"], "files": docs},
        active_scope=None,
    )
    loaded = load_first_session_artifact_for_scope(scope)
    assert loaded is not None
    assert first_session_artifact_is_populated(loaded) is False


def test_valid_artifact_load_and_populated_gate(tmp_path, monkeypatch) -> None:
    from app.course_cache import course_scope_hash, save_first_session_artifact

    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: tmp_path)
    docs = ["Valid/a.md"]
    save_first_session_artifact(
        "Valid",
        {
            "course_id": "Valid",
            "scope_hash": course_scope_hash(docs),
            "baseline_mission": {"title": "Start", "primary_cta": "Go"},
            "seed_questions": [{"q": "Q?", "retrieval_trace": {"source_paths": docs}}],
        },
    )
    scope = resolve_first_session_scope_for_home(
        index_stats={"folder_rel_options": ["Valid"], "files": docs},
        active_scope=None,
    )
    loaded = load_first_session_artifact_for_scope(scope)
    assert loaded is not None
    assert first_session_artifact_is_populated(loaded) is True
