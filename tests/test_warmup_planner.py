from app.warmup_planner import (
    build_warmup_plan,
    classify_pause_tier,
    overdue_spread_sessions,
)


def test_classify_pause_tier_boundaries():
    assert classify_pause_tier(0) == "fast_continue"
    assert classify_pause_tier(1) == "recap_90s"
    assert classify_pause_tier(3) == "recap_90s"
    assert classify_pause_tier(4) == "mini_quiz"
    assert classify_pause_tier(7) == "mini_quiz"
    assert classify_pause_tier(8) == "course_refresher"


def test_overdue_spread_sessions_only_when_soft_recovery_overdue():
    assert overdue_spread_sessions(overdue_count=20, days_since_last_session=5) == 0
    assert overdue_spread_sessions(overdue_count=21, days_since_last_session=2) == 0
    assert overdue_spread_sessions(overdue_count=21, days_since_last_session=3) == 3
    assert overdue_spread_sessions(overdue_count=60, days_since_last_session=10) == 5


def test_build_warmup_plan_maps_tiers_and_payload():
    fast = build_warmup_plan(days_since_last_session=0, overdue_count=0)
    assert fast.tier == "fast_continue"
    assert fast.recap_sentences == 0

    recap = build_warmup_plan(days_since_last_session=2, overdue_count=0)
    assert recap.tier == "recap_90s"
    assert recap.recap_sentences == 2
    assert recap.recall_questions == 3

    quiz = build_warmup_plan(days_since_last_session=5, overdue_count=0)
    assert quiz.tier == "mini_quiz"
    assert quiz.mini_quiz_facts == 5

    refresher = build_warmup_plan(days_since_last_session=9, overdue_count=45)
    assert refresher.tier == "course_refresher"
    assert refresher.refresher_minutes == 10
    assert refresher.overdue_spread_sessions >= 3
