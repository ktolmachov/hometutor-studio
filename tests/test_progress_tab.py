"""E10.4-B: контракт сводки Progress (MasteryDashboard / GET /dashboard/mastery)."""

from __future__ import annotations

import json
import importlib
from pathlib import Path

import pytest

from app import metrics
from app.config import reset_settings_cache
from app.course_metrics import collect_course_progress, record_course_workflow_event
from app.knowledge_graph import JsonKnowledgeGraph
from app.user_state import (
    create_flashcard_deck,
    reset_schema_cache_for_tests,
    save_flashcards_to_deck,
    set_kv,
)
from app.ui.progress_visuals import build_course_filter_label
from app.visualization_service import MasteryDashboard, dashboard


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "us.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def _minimal_graph(path: Path) -> JsonKnowledgeGraph:
    path.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "a", "prerequisites": []},
                    "B": {"description": "b", "prerequisites": ["A"]},
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return JsonKnowledgeGraph(path)


def test_progress_contract_includes_surface_fields(isolated_user_db, tmp_path: Path):
    kg = _minimal_graph(tmp_path / "cg_progress.json")
    data = MasteryDashboard(kg).get_mastery_data()

    assert "weekly_goals" in data
    wg = data["weekly_goals"]
    assert isinstance(wg, dict)
    assert "week_id" in wg and "targets" in wg and "done" in wg

    assert "mastery_vector" in data
    mv = data["mastery_vector"]
    assert isinstance(mv, dict)
    assert "avg" in mv

    gam = data.get("gamification") or {}
    assert "daily_streak" in gam
    assert "quiz_streak" in gam

    pg = data.get("prerequisite_graph") or {}
    assert "nodes" in pg and "edges" in pg and "mastery_overlay" in pg
    assert len(pg["nodes"]) == 2

    assert "due_reviews" in data and "due_count" in data
    assert "quiz_mastery_rows" in data and "concepts_mastered" in data


def test_progress_focus_section_anchor_consumed_once():
    from app.ui.dashboards_progress import _consume_progress_focus_section
    from app.ui.session_state import PROGRESS_FOCUS_SECTION_KEY, PROGRESS_FOCUS_STREAK_WEEKLY

    session = {PROGRESS_FOCUS_SECTION_KEY: PROGRESS_FOCUS_STREAK_WEEKLY}
    expand, focus = _consume_progress_focus_section(session)
    assert expand is True
    assert focus == PROGRESS_FOCUS_STREAK_WEEKLY
    assert PROGRESS_FOCUS_SECTION_KEY not in session

    expand2, focus2 = _consume_progress_focus_section(session)
    assert expand2 is False
    assert focus2 is None


def test_micro_quiz_progress_cta_sets_deferred_nav_keys():
    from app.ui.tutor_chat_quiz import apply_micro_quiz_progress_deferred_nav
    from app.ui.session_state import (
        PENDING_CURRENT_VIEW_KEY,
        PROGRESS_FOCUS_SECTION_KEY,
        PROGRESS_FOCUS_STREAK_WEEKLY,
    )

    session: dict = {}
    apply_micro_quiz_progress_deferred_nav(session)
    assert session[PENDING_CURRENT_VIEW_KEY] == "Прогресс обучения"
    assert session[PROGRESS_FOCUS_SECTION_KEY] == PROGRESS_FOCUS_STREAK_WEEKLY


def test_progress_weekly_goals_roundtrip_kv(isolated_user_db):
    set_kv(
        "weekly_goals_json",
        json.dumps(
            {
                "week_id": "2099-W01",
                "targets": {"new_topics": 2, "reviews": 3, "quizzes": 1},
                "done": {"new_topics": 1, "reviews": 0, "quizzes": 0},
            },
            ensure_ascii=False,
        ),
    )
    d = dashboard.get_mastery_data()
    wg = d.get("weekly_goals") or {}
    # get_weekly_goals_state пересчитывает неделю — ожидаем валидную структуру, не обязательно 2099.
    assert isinstance(wg.get("targets"), dict)
    assert isinstance(wg.get("done"), dict)


def test_progress_mastery_vector_empty_graph_uses_global_quiz_rows(isolated_user_db, tmp_path: Path):
    """Пустой граф: вектор строится по всем строкам quiz_mastery (как в get_mastery_vector)."""
    empty = tmp_path / "empty.json"
    empty.write_text(
        json.dumps({"concepts": {}, "documents": {}, "edges": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(empty)
    data = MasteryDashboard(kg).get_mastery_data()
    mv = data.get("mastery_vector") or {}
    assert "avg" in mv
    assert isinstance(data.get("quiz_mastery_rows"), list)


def test_progress_empty_kg_prerequisite_snapshot_structure(isolated_user_db, tmp_path: Path):
    """Пустой KG: снимок prerequisites остаётся валидным (пустые списки, без падений UI/API)."""
    empty = tmp_path / "empty_cg.json"
    empty.write_text(
        json.dumps({"concepts": {}, "documents": {}, "edges": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(empty)
    data = MasteryDashboard(kg).get_mastery_data()
    pg = data.get("prerequisite_graph") or {}
    assert pg.get("nodes") == []
    assert pg.get("edges") == []
    assert isinstance(pg.get("mastery_overlay"), dict)


def test_course_progress_summary_filters_active_course_cards(isolated_user_db):
    scope = {
        "id": "course123",
        "title": "ML Course",
        "folder_rel": "ml",
        "source_paths": ["ml/lec1.md", "ml/lec2.md"],
        "active": True,
    }
    course_deck = create_flashcard_deck(
        "ML Course deck",
        "course",
        json.dumps({"course_id": "course123", "folder_rel": "ml"}),
    )
    save_flashcards_to_deck(
        course_deck,
        [
            {"front": "What is gradient descent?", "back": "Optimizer", "tags": "course:external-id, folder:ml"},
            {"front": "What is overfitting?", "back": "Poor generalization", "tags": "course:external-id, folder:ml"},
        ],
    )
    other_deck = create_flashcard_deck("Other deck", "document", "other.md")
    save_flashcards_to_deck(
        other_deck,
        [{"front": "Out of scope", "back": "No", "tags": "folder:other"}],
    )

    summary = collect_course_progress(scope, last_topic="gradient descent")

    assert summary["active"] is True
    assert summary["documents"] == 2
    assert summary["cards_total"] == 2
    assert summary["due_today"] == 2
    assert summary["last_topic"] == "gradient descent"
    assert summary["gaps"] == ["What is gradient descent?", "What is overfitting?"]
    assert build_course_filter_label(scope) == "Только активный курс: ML Course"


def test_course_workflow_event_uses_course_workspace_label(tmp_path):
    module = importlib.reload(metrics)
    module.METRICS_STORE_PATH = tmp_path / "metrics_store.jsonl"
    scope = {
        "id": "course123",
        "title": "ML Course",
        "folder_rel": "ml",
        "source_paths": ["ml/lec1.md"],
        "active": True,
    }

    record_course_workflow_event(
        "flashcards_batch",
        scope,
        scenario="flashcards_batch",
        latency_ms=1200.0,
        payload={"cards_total": 5},
    )

    store = module.get_metrics_store(limit=10)
    assert store["total"] == 1
    item = store["items"][0]
    assert item["action"] == "course_workspace.flashcards_batch"
    assert item["payload"]["metrics_label"] == "course_workspace"
    assert item["knowledge_product_trace"]["workflow_label"] == "course_workspace"
    assert item["knowledge_product_trace"]["slo_status"] == "pass"
