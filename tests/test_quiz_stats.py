"""quiz_stats.json: счётчики и streak."""

import json
from pathlib import Path

from app.quiz_stats import load_quiz_ui_stats, record_quiz_session_completed


def test_load_quiz_stats_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("app.quiz_stats._STATS_FILE", tmp_path / "none.json")
    s = load_quiz_ui_stats()
    assert s["total_questions_answered"] == 0
    assert s["streak_days"] == 0


def test_record_quiz_session_completed_writes(tmp_path, monkeypatch):
    p = tmp_path / "quiz_ui_stats.json"
    monkeypatch.setattr("app.quiz_stats._STATS_FILE", p)
    out = record_quiz_session_completed(total_questions=5, correct=3)
    assert out["total_questions_answered"] == 5
    assert out["quiz_sessions_completed"] == 1
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["total_questions_answered"] == 5
