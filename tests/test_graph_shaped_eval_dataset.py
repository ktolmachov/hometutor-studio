"""Graph-shaped eval dataset schema and category coverage for ИИ Агенты."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval_uplift import GRAPH_SHAPED_CATEGORIES, graph_shaped_dataset_path, load_graph_shaped_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = graph_shaped_dataset_path()


def test_graph_shaped_dataset_file_exists():
    assert DATA_PATH.is_file(), f"missing {DATA_PATH}"


def test_graph_shaped_schema_and_category_coverage():
    data = load_graph_shaped_dataset()
    assert int(data.get("schema_version") or 0) >= 1
    assert data.get("course_scope") == "ИИ Агенты"
    cats = data.get("categories")
    assert isinstance(cats, dict)
    assert set(cats) == set(GRAPH_SHAPED_CATEGORIES)

    all_ids: list[str] = []
    total = 0
    for name in GRAPH_SHAPED_CATEGORIES:
        items = cats[name]
        assert isinstance(items, list) and len(items) >= 4
        for item in items:
            assert isinstance(item.get("id"), str) and item["id"]
            question = item.get("question") or item.get("query")
            assert isinstance(question, str) and question.strip()
            assert item.get("course_scope") == "ИИ Агенты"
            assert item.get("category") == name
            doc_ids = item.get("expected_doc_ids")
            assert isinstance(doc_ids, list) and len(doc_ids) >= 1
            ec = item.get("expected_characteristics")
            assert isinstance(ec, dict) and ec
            all_ids.append(item["id"])
            total += 1

    assert total >= 12
    assert len(all_ids) == len(set(all_ids))


def test_graph_shaped_json_round_trip():
    data = load_graph_shaped_dataset()
    again = json.loads(json.dumps(data, ensure_ascii=False, sort_keys=True))
    assert again == data


@pytest.mark.parametrize("category", sorted(GRAPH_SHAPED_CATEGORIES))
def test_each_graph_category_present(category: str):
    data = load_graph_shaped_dataset()
    assert category in data["categories"]
