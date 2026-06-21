"""Структура defense eval dataset и результатов."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "eval" / "eval_dataset.json"
RESULTS = ROOT / "eval" / "eval_results_2026-05-20.json"


def test_eval_dataset_has_fifteen_questions():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    questions = data["questions"]
    assert len(questions) == 15
    difficulties = {q["difficulty"] for q in questions}
    assert difficulties >= {"easy", "medium", "hard"}


def test_eval_results_by_mode_present():
    if not RESULTS.is_file():
        pytest.skip("Run scripts/run_defense_eval.py to generate results")
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    for mode in ("vector_only", "hybrid", "bm25_only"):
        assert mode in data["by_mode"]
        assert data["by_mode"][mode]["source_found_rate"] >= 0.0
