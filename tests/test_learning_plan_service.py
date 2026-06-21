"""Динамический learning plan (граф + user_state)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph
from app.learning_plan_service import (
    AdaptiveDailyPlan,
    DynamicLearningPlan,
    attach_confidence_dip_metadata,
    get_recommended_next_step_after_micro_quiz,
    plan_service,
)
from app.quiz_adaptive import update_mastery_after_score
from app.spaced_repetition import update_spaced_repetition
from app.user_state import _with_db, reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "lp.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
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


def test_plan_service_disabled_without_user_progress():
    r = plan_service.generate({"user_progress": False, "goal": "x", "time_budget_hours": 10})
    assert r["enabled"] is False
    assert r["plan"] == []


def test_personalized_plan_and_smart_resume(isolated_user_db, tmp_path: Path):
    p = tmp_path / "cg2.json"
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
    update_mastery_after_score("A", 0.0)
    svc = DynamicLearningPlan(kg)
    AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()
    pl = svc.generate_personalized_plan(days=3, user_progress=True)
    assert "daily_plan" in pl and "motivation_tip" in pl
    assert isinstance(pl.get("weak_spots"), list)
    adp = pl.get("adaptive_daily_plan")
    assert isinstance(adp, dict) and adp.get("date")
    assert "blocks" in adp
    resume = svc.get_smart_resume()
    assert isinstance(resume, str) and len(resume) > 0


def test_dynamic_plan_respects_topo_and_due(isolated_user_db, tmp_path: Path):
    p = tmp_path / "cg.json"
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
    update_spaced_repetition("B", 5)
    _force_due("B")

    svc = DynamicLearningPlan(kg)
    out = svc.generate(
        {"goal": "test", "level": "intermediate", "time_budget_hours": 100, "user_progress": True}
    )
    assert out["enabled"] is True
    topics = [x["topic"] for x in out["plan"]]
    assert topics[0] == "B"
    assert "A" in topics


def test_adaptive_daily_plan_smoke(isolated_user_db, tmp_path: Path):
    p = tmp_path / "cg3.json"
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
    out = AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()
    assert out.get("date")
    assert isinstance(out.get("blocks"), list)
    assert out.get("entry_state") in {"actionable", "auto_loop_only", "empty"}
    assert "has_actionable_blocks" in out
    assert "primary_block" in out


def test_dynamic_plan_ignores_due_reviews_outside_active_graph(isolated_user_db, tmp_path: Path):
    p = tmp_path / "cg4.json"
    p.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    update_spaced_repetition("A", 5)
    update_spaced_repetition("legacy", 5)
    _force_due("A")
    _force_due("legacy")

    out = DynamicLearningPlan(kg).generate(
        {"goal": "test", "level": "intermediate", "time_budget_hours": 10, "user_progress": True}
    )

    topics = [x["topic"] for x in out["plan"]]
    assert "A" in topics
    assert "legacy" not in topics
    assert out["next_review_count"] == 1


def test_recommended_next_step_ignores_stale_due_reviews(isolated_user_db, tmp_path: Path):
    p = tmp_path / "cg5.json"
    p.write_text(
        json.dumps(
            {
                "concepts": {
                    "A": {"description": "", "prerequisites": []},
                },
                "documents": {},
                "edges": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    update_spaced_repetition("legacy", 5)
    _force_due("legacy")

    out = get_recommended_next_step_after_micro_quiz(
        current_topic="A",
        mastery_level="intermediate",
        last_quiz_feedback={"status": "correct"},
        kg=kg,
    )

    assert out["next_action"] == "Следующий шаг"


def test_adaptive_daily_plan_primary_block_prefers_non_auto_loop(isolated_user_db, tmp_path: Path):
    p = tmp_path / "cg6.json"
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
    out = AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()

    primary = out.get("primary_block")
    assert isinstance(primary, dict)
    assert primary.get("type") != "auto_loop"
    assert out["entry_state"] == "actionable"
    assert out["has_actionable_blocks"] is True


def test_attach_confidence_dip_metadata_inactive_is_noop():
    base = {"plan": [], "total_steps": 0}
    assert attach_confidence_dip_metadata(base, None) == base
    assert attach_confidence_dip_metadata(base, {}) == base


def test_attach_confidence_dip_metadata_active_sidecar():
    from app.warmup_planner import confidence_dip_reduce, confidence_dip_initial_state

    dip = confidence_dip_initial_state()
    dip = confidence_dip_reduce(dip, gate_passed=False, confidence_0_1=0.2)
    dip = confidence_dip_reduce(dip, gate_passed=False, confidence_0_1=0.2)
    assert dip["in_remediation"]
    out = attach_confidence_dip_metadata({"plan": [1]}, dip)
    meta = out.get("confidence_dip_meta")
    assert isinstance(meta, dict)
    assert meta.get("in_remediation") is True
    assert meta.get("remediation_plan")
