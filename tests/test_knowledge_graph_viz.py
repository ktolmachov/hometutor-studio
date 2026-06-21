"""Вкладка Knowledge Graph: fallback узлов из quiz_mastery при пустом concept_graph.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.quiz_adaptive import update_mastery_after_score
from app.user_state import reset_schema_cache_for_tests
from app.visualization_service import VisualizationService


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "us.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_kg_nodes_fallback_from_quiz_when_json_empty(isolated_user_db, tmp_path: Path):
    update_mastery_after_score("topic_from_quiz", 0.95)
    path = tmp_path / "concept_graph.json"
    path.write_text(
        json.dumps({"concepts": {}, "documents": {}, "edges": {}}),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(path)
    assert not kg.get_concepts()
    nodes, edges = VisualizationService.get_knowledge_graph_nodes_edges(kg, "all", set())
    assert edges == []
    assert any(getattr(n, "id", None) == "topic_from_quiz" for n in nodes)
