"""Lightweight doc-sync gate: key roadmap files stay parseable and versioned."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_tasklist_has_review_stamp():
    p = REPO_ROOT / "doc" / "tasklist.md"
    text = p.read_text(encoding="utf-8")
    assert "Актуализировано" in text
    assert re.search(r"\*\*20\d{2}-\d{2}-\d{2}\*\*", text), "tasklist: expected **YYYY-MM-DD**"


def test_vision_has_review_stamp():
    p = REPO_ROOT / "doc" / "vision.md"
    text = p.read_text(encoding="utf-8")
    assert "Актуализировано" in text


def test_graph_eval_baseline_fixture_versioned():
    p = REPO_ROOT / "tests" / "fixtures" / "graph_eval_baseline.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) >= 1
    assert len(data.get("cases") or []) >= 1


def test_learning_plan_graph_baseline_fixture_versioned():
    p = REPO_ROOT / "tests" / "fixtures" / "learning_plan_graph_baseline.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) >= 1
    assert len(data.get("required_response_keys") or []) >= 1


def test_nba_graph_baseline_fixture_versioned():
    p = REPO_ROOT / "tests" / "fixtures" / "nba_graph_baseline.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) >= 1
    assert len(data.get("required_response_keys") or []) >= 1


def test_learning_plan_graph_bundle_baseline_fixture_versioned():
    p = REPO_ROOT / "tests" / "fixtures" / "learning_plan_graph_bundle_baseline.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert int(data.get("schema_version") or 0) >= 1
    assert len(data.get("required_top_level_keys") or []) >= 1


def test_architecture_doc_has_roadmap_dependency_section():
    p = REPO_ROOT / "doc" / "architecture.md"
    text = p.read_text(encoding="utf-8")
    assert "Зависимости delivery-итераций" in text
    assert "18 Core" in text
