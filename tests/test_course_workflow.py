"""Юнит-тесты цепочки course workflow: smart resume (warmup) и continuity артефакта курса."""

from __future__ import annotations

from app.course_cache import (
    course_scope_hash,
    clear_recovery_catch_up_for_scope,
    ensure_plan_v2_pace_mode,
    load_recovery_catch_up_for_scope,
    normalize_source_paths,
    save_recovery_catch_up_for_scope,
)
from app.course_metrics import course_tag, folder_tag
from app.pace_engine import DEFAULT_PACE_MODE
from app.warmup_planner import (
    build_warmup_plan,
    classify_pause_tier,
    overdue_spread_sessions,
    recommended_runway_micro_target,
)


def test_recommended_runway_micro_target_zero_or_clamped():
    assert recommended_runway_micro_target(0) == 0
    assert recommended_runway_micro_target(12, micro_cap=5) == 5
    assert recommended_runway_micro_target(4, micro_cap=5) == 4


def test_recovery_catch_up_cache_roundtrip(tmp_path) -> None:
    scope = {"id": "scope_rb", "source_paths": ["a.md"]}
    cache_path = tmp_path / "course_artifacts.json"
    save_recovery_catch_up_for_scope(scope, catch_up_steps=3, cache_path=cache_path)
    assert load_recovery_catch_up_for_scope(scope, cache_path=cache_path) == 3
    clear_recovery_catch_up_for_scope(scope, cache_path=cache_path)
    assert load_recovery_catch_up_for_scope(scope, cache_path=cache_path) is None


def test_classify_pause_tier_buckets() -> None:
    assert classify_pause_tier(0) == "fast_continue"
    assert classify_pause_tier(1) == "recap_90s"
    assert classify_pause_tier(3) == "recap_90s"
    assert classify_pause_tier(4) == "mini_quiz"
    assert classify_pause_tier(7) == "mini_quiz"
    assert classify_pause_tier(8) == "course_refresher"


def test_build_warmup_plan_fast_continue_one_click() -> None:
    plan = build_warmup_plan(days_since_last_session=0)
    assert plan.tier == "fast_continue"
    assert "один клик" in plan.message.lower()


def test_overdue_spread_sessions_small_backlog_zero() -> None:
    assert overdue_spread_sessions(overdue_count=10, days_since_last_session=10) == 0


def test_overdue_spread_sessions_large_backlog_clamped() -> None:
    spread = overdue_spread_sessions(overdue_count=100, days_since_last_session=10)
    assert 3 <= spread <= 5


def test_ensure_plan_v2_pace_mode_inserts_default() -> None:
    artifact: dict = {"learning_plan": {"plan": {"version": 1}}}
    out = ensure_plan_v2_pace_mode(artifact)
    assert out["learning_plan"]["plan"]["v2"]["pace_mode"] == DEFAULT_PACE_MODE


def test_ensure_plan_v2_pace_mode_keeps_valid_mode() -> None:
    artifact = {"learning_plan": {"plan": {"v2": {"pace_mode": "sprint"}}}}
    out = ensure_plan_v2_pace_mode(artifact)
    assert out["learning_plan"]["plan"]["v2"]["pace_mode"] == "sprint"


def test_course_scope_tags_for_retrieval_continuity() -> None:
    scope = {"id": "c1", "folder_rel": "ml"}
    assert course_tag(scope) == "course:c1"
    assert folder_tag(scope) == "folder:ml"


def test_normalize_source_paths_and_scope_hash_stable() -> None:
    a = normalize_source_paths(["b.md", "a.md", ""])
    b = normalize_source_paths(("a.md", "b.md"))
    assert a == b
    assert course_scope_hash(["x/a.md", "x/b.md"]) == course_scope_hash(("x/b.md", "x/a.md"))


def test_confidence_dip_enters_remediation_after_misses() -> None:
    from app.warmup_planner import confidence_dip_initial_state, confidence_dip_reduce

    s = confidence_dip_initial_state()
    s = confidence_dip_reduce(s, gate_passed=False, confidence_0_1=0.8)
    assert not s["in_remediation"]
    s = confidence_dip_reduce(s, gate_passed=False, confidence_0_1=0.8)
    assert s["in_remediation"]


def test_confidence_dip_exits_after_successful_repairs() -> None:
    from app.warmup_planner import confidence_dip_reduce

    s = {
        "passes": [False, False],
        "in_remediation": True,
        "remediation_success_streak": 0,
        "low_conf_sequence": 0,
    }
    s = confidence_dip_reduce(s, gate_passed=True, confidence_0_1=0.7)
    assert s["in_remediation"]
    assert s["remediation_success_streak"] == 1
    s = confidence_dip_reduce(s, gate_passed=True, confidence_0_1=0.7)
    assert not s["in_remediation"]


def test_confidence_dip_confident_run_skips_reroute() -> None:
    from app.warmup_planner import confidence_dip_reduce

    s = {
        "passes": [True],
        "in_remediation": False,
        "remediation_success_streak": 0,
        "low_conf_sequence": 0,
    }
    s = confidence_dip_reduce(s, gate_passed=True, confidence_0_1=0.9)
    assert not s["in_remediation"]
    assert s["passes"][-2:] == [True, True]


def test_next_session_promise_save_load_and_doc_invalidation(tmp_path) -> None:
    from app.course_cache import (
        load_last_closed_promise,
        load_next_session_promise_for_scope,
        save_next_session_promise,
    )

    cache = tmp_path / "course_artifacts.json"
    scope = {
        "id": "scope01",
        "active": True,
        "folder_rel": "ml",
        "source_paths": ["ml/a.md"],
    }
    out = save_next_session_promise(
        scope,
        promise_text="Продолжить завтра",
        runway_goal_line="g",
        micro_target=2,
        due_today=3,
        active_slot="tutor_chat",
        cache_path=cache,
    )
    assert out.get("promise_text") == "Продолжить завтра"
    got = load_next_session_promise_for_scope(scope, cache_path=cache)
    assert got is not None and got["promise_text"] == "Продолжить завтра"
    last = load_last_closed_promise(cache_path=cache)
    assert last is not None and last["folder_rel"] == "ml"

    scope_new_docs = {**scope, "source_paths": ["ml/b.md"]}
    assert load_next_session_promise_for_scope(scope_new_docs, cache_path=cache) is None
