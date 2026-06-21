"""Tests for learner_state_scope due-queue summary contract."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.learner_state_scope import due_reviews_summary_for_kg, filter_due_reviews_for_kg
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "scope.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "", "index_version": None},
    )
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _kg_with_concepts(tmp_path: Path, n: int) -> JsonKnowledgeGraph:
    concepts = {
        f"c{i}": {"description": "", "prerequisites": []}
        for i in range(n)
    }
    path = tmp_path / f"kg_{n}.json"
    path.write_text(
        json.dumps({"concepts": concepts, "documents": {}, "edges": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return JsonKnowledgeGraph(path)


def _seed_due_concepts(n: int) -> None:
    now = datetime.now(timezone.utc)

    def seed(conn):
        for i in range(n):
            days_ago = max(1, 30 - (i % 30))
            nr = (now - timedelta(days=days_ago)).isoformat()
            conn.execute(
                """
                INSERT INTO spaced_repetition(
                    concept, easiness, interval_days, repetitions, next_review, last_review
                ) VALUES (?, 2.5, 1, 0, ?, ?)
                """,
                (f"c{i}", nr, nr),
            )
        conn.commit()

    _with_db(seed)


@pytest.mark.parametrize(
    ("total", "expected_preview_len", "expected_deferred", "expected_overflow_mode", "expect_caption"),
    [
        (5, 5, 0, False, False),
        (50, 7, 43, False, True),
        (120, 7, 113, True, True),
    ],
    ids=["small_5", "threshold_50", "overflow_120"],
)
def test_due_reviews_summary_for_kg_overflow_contract(
    isolated_user_db,
    tmp_path: Path,
    total,
    expected_preview_len,
    expected_deferred,
    expected_overflow_mode,
    expect_caption,
):
    kg = _kg_with_concepts(tmp_path, total)
    _seed_due_concepts(total)

    summary = due_reviews_summary_for_kg(kg)

    assert summary["count"] == total
    assert len(summary["preview_concepts"]) == expected_preview_len
    assert summary["deferred_count"] == expected_deferred
    assert summary["overflow_mode"] is expected_overflow_mode
    if expect_caption:
        assert summary["overflow_caption"] == f"ещё {expected_deferred} отложено"
        assert summary["overflow_caption"] in (summary["hint"] or "")
    else:
        assert summary["overflow_caption"] == ""
        assert "отложено" not in (summary["hint"] or "")


def test_due_reviews_summary_for_kg_overflow_120_exact_copy(isolated_user_db, tmp_path: Path):
    kg = _kg_with_concepts(tmp_path, 120)
    _seed_due_concepts(120)

    summary = due_reviews_summary_for_kg(kg)

    assert summary["preview_concepts"] == [
        row["concept"] for row in filter_due_reviews_for_kg(kg, limit=7)
    ]
    assert summary["deferred_count"] == 113
    assert summary["overflow_caption"] == "ещё 113 отложено"
    assert summary["overflow_mode"] is True
