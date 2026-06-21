"""Tests for baseline weekly SSR planner (fixtures + US-20.9 branches)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.ssr_weekly_planner import (
    WeeklyPlannerProfile,
    generate_weekly_study_plan,
    load_weekly_planner_fixtures,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_fixtures_count_and_seven_days() -> None:
    profiles = load_weekly_planner_fixtures()
    assert len(profiles) == 30
    for raw in profiles:
        with patch("app.ssr_weekly_planner.record_ssr_ai_auxiliary_event"):
            plan = generate_weekly_study_plan(raw, emit_telemetry=True)
        assert plan["profile_id"] == raw["profile_id"]
        assert len(plan["days"]) == 7
        for d in plan["days"]:
            assert d["day_index"] in range(7)
            assert d["primary_label"] in (
                "retention_debt",
                "weak_concept_recovery",
                "new_learning_or_continuation",
            )
            used = sum(int(s.get("minutes") or 0) for s in d["sessions"])
            assert used <= d["budget_minutes"] + 1  # int rounding


def test_retention_dominates_when_due_large() -> None:
    prof = WeeklyPlannerProfile(
        profile_id="t_ret",
        due_flashcard_count=800,
        overdue_days_max=4.0,
        quiz_failure_active=False,
        weak_concepts=[],
        mastery_avg=0.97,
        continuation_queue_min=0,
        minutes_available_per_day=[60, 60, 60, 60, 60, 60, 60],
    )
    with patch("app.ssr_weekly_planner.record_ssr_ai_auxiliary_event"):
        plan = generate_weekly_study_plan(prof)
    assert plan["summary"]["router_signal"] == "retention_debt"
    assert all(d["primary_label"] == "retention_debt" for d in plan["days"])
    ret_minutes = sum(
        sum(int(s["minutes"]) for s in d["sessions"] if s.get("kind") == "retention")
        for d in plan["days"]
    )
    assert ret_minutes == sum(prof.minutes_available_per_day)


def test_recovery_dominates_with_quiz_failure() -> None:
    prof = WeeklyPlannerProfile(
        profile_id="t_rec",
        due_flashcard_count=0,
        quiz_failure_active=True,
        weak_concepts=["alpha", "beta", "gamma"],
        mastery_avg=0.5,
        continuation_queue_min=5,
        minutes_per_weak_concept=25.0,
        minutes_available_per_day=[90, 90, 90, 90, 90, 90, 90],
    )
    with patch("app.ssr_weekly_planner.record_ssr_ai_auxiliary_event"):
        plan = generate_weekly_study_plan(prof)
    assert plan["summary"]["router_signal"] == "weak_concept_recovery"


def test_new_learning_or_continuation_when_no_debt_signals() -> None:
    prof = WeeklyPlannerProfile(
        profile_id="t_new",
        due_flashcard_count=0,
        quiz_failure_active=False,
        weak_concepts=[],
        mastery_avg=0.95,
        continuation_queue_min=40,
        minutes_available_per_day=[50, 50, 50, 50, 50, 50, 50],
    )
    with patch("app.ssr_weekly_planner.record_ssr_ai_auxiliary_event"):
        plan = generate_weekly_study_plan(prof)
    assert plan["summary"]["router_signal"] == "new_learning_or_continuation"


def test_truncation_reports_unmet() -> None:
    prof = WeeklyPlannerProfile(
        profile_id="t_trunc",
        due_flashcard_count=200,
        quiz_failure_active=True,
        weak_concepts=["x"],
        mastery_avg=0.2,
        continuation_queue_min=300,
        minutes_available_per_day=[10, 10, 10, 10, 10, 10, 10],
    )
    with patch("app.ssr_weekly_planner.record_ssr_ai_auxiliary_event"):
        plan = generate_weekly_study_plan(prof)
    assert plan["summary"]["completion_feasibility_ratio"] < 1.0
    unmet = plan["summary"]["pools_unmet_minutes"]
    assert unmet["retention"] > 0 or unmet["recovery"] > 0 or unmet["continuation"] > 0


def test_telemetry_swallow_errors() -> None:
    prof = WeeklyPlannerProfile(
        profile_id="t_tel",
        due_flashcard_count=1,
        minutes_available_per_day=[30, 30, 30, 30, 30, 30, 30],
    )
    with patch(
        "app.ssr_weekly_planner.record_ssr_ai_auxiliary_event",
        side_effect=RuntimeError("kv down"),
    ):
        plan = generate_weekly_study_plan(prof, emit_telemetry=True)
    assert len(plan["days"]) == 7


def test_fixture_path_override() -> None:
    p = REPO_ROOT / "eval_data" / "ml_eval" / "ssr_level3" / "ssr_weekly_plan_fixtures.json"
    loaded = load_weekly_planner_fixtures(p)
    assert len(loaded) == 30
