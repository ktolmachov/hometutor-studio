"""Golden defense eval dataset: schema, coverage, round-trip JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = REPO_ROOT / "eval_data" / "defense_eval_questions.json"
EVAL_ROOT = REPO_ROOT / "eval_data"

REQUIRED_CATEGORIES = (
    "qa",
    "keyword",
    "overview",
    "synthesis",
    "negative",
    "injection",
)


def _load_dataset() -> dict:
    raw = DATA_PATH.read_text(encoding="utf-8")
    return json.loads(raw)


def test_defense_eval_dataset_file_exists():
    assert DATA_PATH.is_file(), f"missing {DATA_PATH}"


def test_defense_eval_schema_and_coverage():
    data = _load_dataset()
    assert data.get("version") == "1.0"
    assert isinstance(data.get("created_at"), str) and len(data["created_at"]) >= 10
    cats = data.get("categories")
    assert isinstance(cats, dict)
    assert set(cats) == set(REQUIRED_CATEGORIES)

    all_ids: list[str] = []
    total = 0
    for name in REQUIRED_CATEGORIES:
        items = cats[name]
        assert isinstance(items, list) and len(items) >= 3
        for it in items:
            assert isinstance(it, dict)
            assert isinstance(it.get("id"), str) and it["id"]
            assert isinstance(it.get("query"), str) and it["query"].strip()
            ec = it.get("expected_characteristics")
            assert isinstance(ec, dict) and ec
            if name == "injection":
                inj = it.get("injected_document")
                assert isinstance(inj, str) and inj.strip()
                ref = EVAL_ROOT / inj
                assert ref.is_file(), f"injection fixture missing: {ref}"
            all_ids.append(it["id"])
        total += len(items)

    assert total >= 20
    assert len(all_ids) == len(set(all_ids))


def test_defense_eval_json_round_trip_preserves_structure():
    data = _load_dataset()
    dumped = json.dumps(data, ensure_ascii=False, sort_keys=True)
    again = json.loads(dumped)
    assert again == data


def test_defense_eval_round_trip_with_indent_matches_semantics():
    """Parse → serialize with indent → parse yields equal document tree."""
    data = _load_dataset()
    blob = json.dumps(data, ensure_ascii=False, indent=2)
    assert json.loads(blob) == data


@pytest.mark.parametrize("category", REQUIRED_CATEGORIES)
def test_each_required_category_documented_in_name(category):
    """Dataset scope is tied to category keys (defense golden eval)."""
    data = _load_dataset()
    assert category in data["categories"]
