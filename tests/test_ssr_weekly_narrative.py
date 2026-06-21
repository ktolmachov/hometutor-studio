"""Tests for weekly study narrative snapshot builder (sp1)."""

from __future__ import annotations

import importlib
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.ssr_weekly_narrative import (
    WeeklyNarrativeSignals,
    build_weekly_study_narrative_snapshot,
)
from app.user_state_weekly_narrative import count_learning_events_7d


def _rich_signals() -> WeeklyNarrativeSignals:
    return WeeklyNarrativeSignals(
        event_count=5,
        due_trend="up",
        weak_concepts=("граф знаний", "RAG pipeline"),
        dominant_route=("cards_due", "flashcards_review"),
        route_sparse=False,
    )


def _mixed_signals() -> WeeklyNarrativeSignals:
    return WeeklyNarrativeSignals(
        event_count=4,
        due_trend="up",
        weak_concepts=(),
        dominant_route=None,
        route_sparse=True,
    )


def test_rich_week_populated_golden():
    vm = build_weekly_study_narrative_snapshot(inject_signals=_rich_signals())
    assert vm.state == "populated"
    assert vm.event_count == 5
    assert 3 <= len(vm.bullets) <= 5
    assert vm.template_ids[0] == "due_trend_up"
    assert "weak_concepts_named" in vm.template_ids
    assert "route_dominant" in vm.template_ids
    assert vm.bullets[0] == (
        "За неделю очередь повторений выросла — система чаще предлагала закрыть due."
    )
    assert "граф знаний" in vm.bullets[1]
    assert "карточки due" in vm.bullets[2]
    assert vm.word_count <= 120
    assert vm.message_ru == ""


def test_empty_week_insufficient_events():
    vm = build_weekly_study_narrative_snapshot(
        inject_signals=WeeklyNarrativeSignals(event_count=2, due_trend="neutral")
    )
    assert vm.state == "empty"
    assert vm.bullets == ()
    assert vm.template_ids == ("empty_insufficient_data",)
    assert "Пока мало учебных действий" in vm.message_ru


def test_mixed_signals_due_up_sparse_routes():
    vm = build_weekly_study_narrative_snapshot(inject_signals=_mixed_signals())
    assert vm.state == "populated"
    assert vm.template_ids[0] == "due_trend_up"
    assert "weak_concepts_absent" in vm.template_ids
    assert "route_sparse" in vm.template_ids
    assert vm.word_count <= 120
    assert len(vm.bullets) >= 3


def test_build_p95_under_50ms_without_network():
    signals = _rich_signals()
    timings: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        build_weekly_study_narrative_snapshot(inject_signals=signals)
        timings.append((time.perf_counter() - t0) * 1000.0)
    timings.sort()
    p95 = timings[94]
    assert p95 < 50.0, f"p95={p95:.2f}ms"


def test_module_does_not_import_ssr_policy_or_provider():
    import ast

    tree = ast.parse(Path("app/ssr_weekly_narrative.py").read_text(encoding="utf-8"))
    banned = ("smart_study_router", "smart_study_recommendation", "provider")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for b in banned:
                    assert b not in alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for b in banned:
                assert b not in node.module
    mod = importlib.import_module("app.ssr_weekly_narrative")
    assert mod is not None


def test_count_learning_events_dedupes_days(tmp_path, monkeypatch):
    db = tmp_path / "narr.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    import app.user_state as user_state

    user_state.reset_schema_cache_for_tests()
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    day = now.date().isoformat()
    prev = (now - timedelta(days=1)).replace(microsecond=0).isoformat()
    old = (now - timedelta(days=8)).replace(microsecond=0).isoformat()

    def _seed(conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO quiz_results (concept, level, score, timestamp) VALUES (?, ?, ?, ?)",
            ("c1", "recognition", 0.8, f"{day}T10:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO quiz_results (concept, level, score, timestamp) VALUES (?, ?, ?, ?)",
            ("c2", "recognition", 0.7, f"{day}T18:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO micro_quiz_events (topic, feedback_json, next_step_json, created_at) "
            "VALUES (?, ?, ?, ?)",
            ("t", "{}", "{}", prev),
        )
        conn.execute(
            "INSERT INTO ssr_recommendation_feedback "
            "(action, hint_kind, primary_nav, why_now_len, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("accept", "cards_due", "flashcards_review", 0, old),
        )
        conn.commit()

    user_state._with_db(_seed, write=True)  # noqa: SLF001 — test seed via persistence layer

    assert count_learning_events_7d(now_utc=now) == 2
