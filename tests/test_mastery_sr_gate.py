"""E5.2 mastery + spaced repetition regression gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph, get_mastery_vector, get_next_best_actions_for_user
from app.quiz_adaptive import update_mastery_after_score
from app.spaced_repetition import due_priority_by_concept, update_spaced_repetition
from app.user_state import _with_db, reset_schema_cache_for_tests

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "mastery_sr.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    monkeypatch.setattr(
        "app.user_state.get_current_learner_state_lineage",
        lambda: {"generation_id": "gen-e5", "index_version": 5},
    )
    monkeypatch.setattr("app.user_state._active_concept_ids_for_lineage", lambda: {"A", "B"})
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _force_due(concept: str) -> None:
    def _work(conn):
        conn.execute(
            "UPDATE spaced_repetition SET next_review = ? WHERE concept = ?",
            ("2000-01-01T00:00:00+00:00", concept),
        )
        conn.commit()

    _with_db(_work)


def test_mastery_sr_baseline_fixture_contract():
    data = json.loads((REPO_ROOT / "tests" / "fixtures" / "mastery_sr_baseline.json").read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) == 1
    assert "avg" in data["required_mastery_keys"]
    assert "spaced_component" in data["required_nba_item_keys"]


def test_mastery_sr_gate_matches_baseline(isolated_user_db, monkeypatch, tmp_path: Path):
    graph_path = tmp_path / "mastery_sr_graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            }
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(graph_path)
    monkeypatch.setattr("app.knowledge_graph.get_active_knowledge_graph", lambda: kg)

    update_mastery_after_score("A", 1.0)
    update_mastery_after_score("A", 1.0)
    sr = update_spaced_repetition("A", 5)
    _force_due("A")

    fixture = json.loads((REPO_ROOT / "tests" / "fixtures" / "mastery_sr_baseline.json").read_text(encoding="utf-8"))
    mastery = get_mastery_vector("local")
    due = due_priority_by_concept(limit=10)
    nba = get_next_best_actions_for_user(limit=2, due_limit=10)

    for key in fixture["required_mastery_keys"]:
        assert key in mastery
    for key in fixture["required_spaced_repetition_keys"]:
        assert key in sr

    assert mastery["A"] >= 0.68
    assert due["A"] > 0.0
    assert nba["actions"]
    first = nba["actions"][0]
    for key in fixture["required_nba_item_keys"]:
        assert key in first
    assert any(item["concept"] == "A" and item["spaced_component"] > 0 for item in nba["actions"])
