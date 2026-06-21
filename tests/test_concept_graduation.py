"""E10.4-A: concept graduation from stable transfer mastery."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.adaptive_plan import AdaptiveDailyPlan, block_concepts_from_plan
from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.quiz_adaptive import SUCCESS_THRESHOLD, update_mastery_after_score
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "concept_graduation.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _write_graph(path: Path) -> JsonKnowledgeGraph:
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "Gap": {
                        "description": "",
                        "prerequisites": [],
                        "related_concepts": ["StableTransfer", "YoungTransfer", "UndatedTransfer"],
                    },
                    "StableTransfer": {"description": "", "prerequisites": []},
                    "YoungTransfer": {"description": "", "prerequisites": []},
                    "UndatedTransfer": {"description": "", "prerequisites": []},
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return JsonKnowledgeGraph(path)


def _promote_to_transfer(concept: str) -> None:
    for _ in range(4):
        update_mastery_after_score(concept, SUCCESS_THRESHOLD + 0.05)


def _set_mastery_timestamp(concept: str, value: str) -> None:
    def _work(conn):
        conn.execute(
            "UPDATE quiz_mastery SET last_updated = ? WHERE concept = ?",
            (value, concept),
        )
        conn.commit()

    _with_db(_work)


def test_refresh_concept_graduation_marks_only_stable_transfer(isolated_user_db, tmp_path: Path):
    kg = _write_graph(tmp_path / "concept_graph.json")
    now = datetime(2026, 4, 11, tzinfo=timezone.utc)
    rows = [
        {
            "concept": "StableTransfer",
            "current_level": "transfer",
            "last_updated": (now - timedelta(days=8)).isoformat(),
        },
        {
            "concept": "YoungTransfer",
            "current_level": "transfer",
            "last_updated": (now - timedelta(days=2)).isoformat(),
        },
        {"concept": "UndatedTransfer", "current_level": "transfer", "last_updated": "not-a-date"},
    ]

    statuses = kg.refresh_concept_graduation(rows, now=now)
    concepts = kg.get_concepts()

    assert statuses == {
        "StableTransfer": "graduated",
        "YoungTransfer": "not graduated yet",
        "UndatedTransfer": "not graduated yet",
    }
    assert concepts["StableTransfer"]["graduated"] is True
    assert concepts["StableTransfer"]["graduation_status"] == "graduated"
    assert concepts["YoungTransfer"]["graduated"] is False
    assert concepts["UndatedTransfer"]["graduation_status"] == "not graduated yet"


def test_adaptive_plan_excludes_graduated_concepts(isolated_user_db, tmp_path: Path):
    kg = _write_graph(tmp_path / "concept_graph.json")
    update_mastery_after_score("Gap", SUCCESS_THRESHOLD + 0.05)
    _promote_to_transfer("StableTransfer")
    _promote_to_transfer("YoungTransfer")
    _promote_to_transfer("UndatedTransfer")

    now = datetime.now(timezone.utc)
    _set_mastery_timestamp("StableTransfer", (now - timedelta(days=8)).isoformat())
    _set_mastery_timestamp("YoungTransfer", (now - timedelta(days=2)).isoformat())
    _set_mastery_timestamp("UndatedTransfer", "not-a-date")

    plan = AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()
    block_concepts = block_concepts_from_plan(plan)
    concepts = kg.get_concepts()

    assert plan["concept_graduation"]["StableTransfer"] == "graduated"
    assert plan["concept_graduation"]["YoungTransfer"] == "not graduated yet"
    assert plan["concept_graduation"]["UndatedTransfer"] == "not graduated yet"
    assert "StableTransfer" not in block_concepts
    assert "Gap" in block_concepts
    assert concepts["StableTransfer"]["graduated"] is True
