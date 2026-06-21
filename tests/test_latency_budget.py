"""Unit tests for surface latency budget registry and with_budget ladder."""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.latency_budget import (
    SURFACE_BUDGETS,
    BudgetMeta,
    classify_mission_load_variant,
    resolve_query_surface,
    with_budget,
)


class _FakeClock:
    def __init__(self, *, elapsed_ms: float = 0.0) -> None:
        self._calls = 0
        self._elapsed_ms = elapsed_ms

    def __call__(self) -> float:
        self._calls += 1
        if self._calls == 1:
            return 0.0
        return self._elapsed_ms / 1000.0


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_empty_scope_fast_path(tmp_path: Path) -> None:
    jsonl = tmp_path / "latency_budget.jsonl"
    result = with_budget(
        "mission_load",
        lambda: (None, "empty"),
        empty_scope=True,
        clock=_FakeClock(),
        jsonl_path=jsonl,
    )
    assert result.result == (None, "empty")
    assert result.meta.actual_ms == 0.0
    assert result.meta.degraded is False
    assert result.meta.event == "budget_completed"
    rows = _read_jsonl(jsonl)
    assert len(rows) == 1
    assert rows[0]["surface"] == "mission_load"


@pytest.mark.parametrize(
    ("elapsed_ms", "expected_step", "expected_event", "degraded"),
    [
        (150.0, 1, "budget_completed", False),
        (900.0, 2, "budget_completed", True),
        (2000.0, 3, "surface_breached_soft", True),
        (4000.0, 4, "surface_breached_hard", True),
    ],
)
def test_cold_ladder_steps(
    tmp_path: Path,
    elapsed_ms: float,
    expected_step: int,
    expected_event: str,
    degraded: bool,
) -> None:
    jsonl = tmp_path / "latency_budget.jsonl"

    def _fn() -> tuple[None, str]:
        return None, "ok"

    result = with_budget(
        "mission_load",
        _fn,
        variant="cold",
        clock=_FakeClock(elapsed_ms=elapsed_ms),
        jsonl_path=jsonl,
    )
    assert result.meta.ladder_step == expected_step
    assert result.meta.event == expected_event
    assert result.meta.degraded is degraded
    assert result.meta.target_ms == SURFACE_BUDGETS["mission_load"]["cold"]["target_ms"]


def test_warm_thresholds(tmp_path: Path) -> None:
    result = with_budget(
        "mission_load",
        lambda: ("artifact", "ok"),
        variant="warm",
        clock=_FakeClock(elapsed_ms=700.0),
        jsonl_path=tmp_path / "latency_budget.jsonl",
    )
    assert result.meta.variant == "warm"
    assert result.meta.ladder_step == 3
    assert result.meta.event == "surface_breached_soft"


def test_hard_breach_maps_ok_to_empty(tmp_path: Path) -> None:
    result = with_budget(
        "mission_load",
        lambda: ({"baseline_mission": {"title": "T"}}, "ok"),
        variant="cold",
        clock=_FakeClock(elapsed_ms=5000.0),
        jsonl_path=tmp_path / "latency_budget.jsonl",
    )
    assert result.meta.event == "surface_breached_hard"
    assert result.result == (None, "empty")


def test_hard_breach_preserves_error_status(tmp_path: Path) -> None:
    result = with_budget(
        "mission_load",
        lambda: (None, "error"),
        variant="cold",
        clock=_FakeClock(elapsed_ms=5000.0),
        jsonl_path=tmp_path / "latency_budget.jsonl",
    )
    assert result.meta.event == "surface_breached_hard"
    assert result.result == (None, "error")


def test_jsonl_write_failure_does_not_block_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jsonl = tmp_path / "latency_budget.jsonl"

    def _raise_on_open(self, *args, **kwargs):  # noqa: ANN001
        raise OSError("disk full")

    monkeypatch.setattr(Path, "open", _raise_on_open)

    result = with_budget(
        "mission_load",
        lambda: (None, "empty"),
        empty_scope=True,
        jsonl_path=jsonl,
    )
    assert result.result == (None, "empty")


def test_classify_mission_load_variant_warm_on_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    scope = {
        "folder_rel": "CourseA",
        "source_paths": ["CourseA/a.md"],
    }
    session = {
        "first_session_artifact_cache": {
            "baseline_mission": {"title": "Start"},
            "seed_questions": [{"q": "Q?"}],
        },
        "first_session_artifact_scope_hash": "hash-a",
        "first_session_course_id": "CourseA",
    }
    monkeypatch.setattr(
        "app.latency_budget.course_scope_hash",
        lambda _paths: "hash-a",
    )
    monkeypatch.setattr(
        "app.latency_budget.first_session_artifact_is_populated",
        lambda artifact: isinstance(artifact, dict),
    )
    assert classify_mission_load_variant(scope, session) == "warm"


def test_classify_mission_load_variant_cold_on_cache_miss() -> None:
    scope = {"folder_rel": "CourseA", "source_paths": ["CourseA/a.md"]}
    session: dict = {}
    assert classify_mission_load_variant(scope, session) == "cold"


@pytest.mark.parametrize(
    "surface",
    ["query", "tutor_turn", "quiz_gen", "quiz_submit"],
)
@pytest.mark.parametrize(
    ("elapsed_ms", "expected_step", "expected_event", "degraded"),
    [
        (100.0, 1, "budget_completed", False),
        (None, 2, "budget_completed", True),
        (None, 3, "surface_breached_soft", True),
        (None, 4, "surface_breached_hard", True),
    ],
)
def test_llm_surface_ladder_steps(
    tmp_path: Path,
    surface: str,
    elapsed_ms: float | None,
    expected_step: int,
    expected_event: str,
    degraded: bool,
) -> None:
    thresholds = SURFACE_BUDGETS[surface]["cold"]
    if elapsed_ms is None:
        if expected_step == 2:
            elapsed_ms = thresholds["target_ms"] + 100.0
        elif expected_step == 3:
            elapsed_ms = thresholds["soft_ms"] + 100.0
        else:
            elapsed_ms = thresholds["hard_ms"] + 100.0

    jsonl = tmp_path / "latency_budget.jsonl"
    result = with_budget(
        surface,
        lambda: {"answer": "ok", "sources": [], "debug": {}},
        clock=_FakeClock(elapsed_ms=elapsed_ms),
        jsonl_path=jsonl,
    )
    assert result.meta.ladder_step == expected_step
    assert result.meta.event == expected_event
    assert result.meta.degraded is degraded
    assert result.meta.surface == surface
    assert result.meta.target_ms == thresholds["target_ms"]


def test_query_hard_breach_does_not_mutate_result(tmp_path: Path) -> None:
    payload = {"answer": "slow but complete", "sources": [{"cite_index": 1}], "debug": {}}
    result = with_budget(
        "query",
        lambda: payload,
        clock=_FakeClock(elapsed_ms=9000.0),
        jsonl_path=tmp_path / "latency_budget.jsonl",
    )
    assert result.meta.event == "surface_breached_hard"
    assert result.result == payload


@pytest.mark.parametrize(
    "surface",
    ["quiz_gen", "quiz_submit"],
)
def test_quiz_surface_hard_breach_does_not_mutate_result(
    tmp_path: Path,
    surface: str,
) -> None:
    if surface == "quiz_gen":
        payload = {"success": True, "questions": [{"question": "Q?", "options": ["a", "b", "c", "d"]}]}
    else:
        payload = {"quiz_feedback": {"status": "correct"}, "recommended_next": {"next_action": "continue"}}
    result = with_budget(
        surface,
        lambda: payload,
        clock=_FakeClock(elapsed_ms=7000.0),
        jsonl_path=tmp_path / "latency_budget.jsonl",
    )
    assert result.meta.event == "surface_breached_hard"
    assert result.meta.surface == surface
    assert result.result == payload


def test_quiz_gen_hard_breach_skips_mission_load_tuple_mutation(tmp_path: Path) -> None:
    artifact = {"baseline_mission": {"title": "T"}}
    result = with_budget(
        "quiz_gen",
        lambda: (artifact, "ok"),
        clock=_FakeClock(elapsed_ms=7000.0),
        jsonl_path=tmp_path / "latency_budget.jsonl",
    )
    assert result.meta.event == "surface_breached_hard"
    assert result.result == (artifact, "ok")


@pytest.mark.parametrize(
    ("query_mode", "expected"),
    [
        ("tutor", "tutor_turn"),
        ("TUTOR", "tutor_turn"),
        ("qa", "query"),
        (None, "query"),
    ],
)
def test_resolve_query_surface_mutex(query_mode: str | None, expected: str) -> None:
    options = SimpleNamespace(query_mode=query_mode)
    assert resolve_query_surface(options) == expected


def test_warm_cache_hit_skips_disk_read(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ui import mission_control as mc
    from app.ui import mission_control_first_session as mc_fs

    scope = {
        "folder_rel": "WarmCourse",
        "source_paths": ["WarmCourse/a.md"],
    }
    artifact = {
        "baseline_mission": {"title": "Start", "primary_cta": "Go"},
        "seed_questions": [{"q": "Q?", "retrieval_trace": {"source_paths": ["WarmCourse/a.md"]}}],
    }
    state: dict = {
        "first_session_artifact_cache": artifact,
        "first_session_artifact_scope_hash": "warm-hash",
        "first_session_course_id": "WarmCourse",
    }
    st = SimpleNamespace(session_state=state)
    monkeypatch.setattr(mc_fs, "st", st)
    monkeypatch.setattr(mc_fs, "course_scope_hash", lambda _paths: "warm-hash")
    monkeypatch.setattr("app.latency_budget.course_scope_hash", lambda _paths: "warm-hash")
    exists_mock = MagicMock(return_value=True)
    monkeypatch.setattr(
        mc_fs,
        "first_session_artifact_path",
        lambda _folder: SimpleNamespace(exists=exists_mock),
    )

    loaded, status = mc.load_first_session_artifact_cached_for_scope(scope)
    assert loaded is artifact
    assert status == "ok"
    exists_mock.assert_not_called()
    assert state.get("latency_budget_last_event", {}).get("variant") == "warm"
