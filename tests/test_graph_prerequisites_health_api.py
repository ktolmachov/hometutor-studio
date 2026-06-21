"""GET /kb/graph/prerequisites-health — graph Extension baseline (service + contract)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_learning_plan_graph_baseline_fixture_contract():
    p = REPO_ROOT / "tests" / "fixtures" / "learning_plan_graph_baseline.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) >= 1
    keys = data.get("required_response_keys") or []
    assert len(keys) >= 6
    assert "cycles" in keys


def test_get_graph_prerequisites_health_matches_fixture_keys(monkeypatch, tmp_path):
    from app.knowledge_graph import JsonKnowledgeGraph, get_graph_prerequisites_health

    path = tmp_path / "g.json"
    path.write_text(
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
    kg = JsonKnowledgeGraph(path)

    monkeypatch.setattr("app.knowledge_graph.get_active_knowledge_graph", lambda: kg)

    out = get_graph_prerequisites_health()
    fixture = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "learning_plan_graph_baseline.json").read_text(
            encoding="utf-8"
        )
    )
    for k in fixture["required_response_keys"]:
        assert k in out
    assert out["cycle_count"] == 0
    assert out["topological_order_ok"] is True


def test_nba_graph_baseline_fixture_contract():
    p = REPO_ROOT / "tests" / "fixtures" / "nba_graph_baseline.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) >= 1
    assert len(data.get("required_response_keys") or []) >= 1


def test_get_learning_plan_graph_bundle_matches_baseline_fixture(monkeypatch, tmp_path):
    from app.knowledge_graph import JsonKnowledgeGraph, get_learning_plan_graph_bundle

    path = tmp_path / "bundle.json"
    path.write_text(
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
    kg = JsonKnowledgeGraph(path)
    monkeypatch.setattr("app.knowledge_graph.get_active_knowledge_graph", lambda: kg)
    monkeypatch.setattr(
        "app.quiz_adaptive.get_all_mastery_levels",
        lambda: {"A": "recognition", "B": "recognition"},
    )
    monkeypatch.setattr("app.spaced_repetition.due_priority_by_concept", lambda **_: {})

    out = get_learning_plan_graph_bundle(nba_limit=3, topo_preview_limit=5)
    fixture = json.loads(
        (
            REPO_ROOT / "tests" / "fixtures" / "learning_plan_graph_bundle_baseline.json"
        ).read_text(encoding="utf-8")
    )
    for k in fixture["required_top_level_keys"]:
        assert k in out
    assert out["topological_preview"] == ["A", "B"]


def test_get_next_best_actions_for_user_matches_nba_fixture(monkeypatch, tmp_path):
    from app.knowledge_graph import JsonKnowledgeGraph, get_next_best_actions_for_user

    path = tmp_path / "nba.json"
    path.write_text(
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
    kg = JsonKnowledgeGraph(path)
    monkeypatch.setattr("app.knowledge_graph.get_active_knowledge_graph", lambda: kg)
    monkeypatch.setattr(
        "app.quiz_adaptive.get_all_mastery_levels",
        lambda: {"A": "recognition", "B": "recognition"},
    )
    monkeypatch.setattr("app.spaced_repetition.due_priority_by_concept", lambda **_: {})

    out = get_next_best_actions_for_user(limit=3, due_limit=10)
    fixture = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "nba_graph_baseline.json").read_text(encoding="utf-8")
    )
    for k in fixture["required_response_keys"]:
        assert k in out
    assert out["topological_order_ok"] is True
    assert len(out["actions"]) >= 1
