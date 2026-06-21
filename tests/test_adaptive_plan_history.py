"""US-6.3: краткая история adaptive daily plan в KV (отдельный ключ)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adaptive_plan import AdaptiveDailyPlan, get_adaptive_daily_plan_history
from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.user_state import reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "plan_hist.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_plan_history_appends_on_rebuild(isolated_user_db, tmp_path: Path) -> None:
    p = tmp_path / "cg_hist.json"
    p.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                    "B": {"description": "", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    assert get_adaptive_daily_plan_history() == []

    AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()
    assert get_adaptive_daily_plan_history() == []

    AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()
    hist = get_adaptive_daily_plan_history()
    assert len(hist) == 1
    row = hist[0]
    assert "date" in row and row["date"]
    assert isinstance(row.get("focus_review_gap_new"), list) and len(row["focus_review_gap_new"]) == 3
    assert isinstance(row.get("main_concepts"), list)
    assert "archived_at" in row
