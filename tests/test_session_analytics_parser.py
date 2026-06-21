from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.session_analytics_parser import (
    GradesDistribution,
    RetentionPrediction,
    SessionStatsObject,
    assert_fully_json_serializable,
    export_session_stats_json,
    import_session_stats_json,
    session_stats_to_plain_dict,
    seven_day_schedule_counts,
)


def _session(
    *,
    again: int,
    hard: int,
    good: int,
    easy: int,
    duration_minutes: float,
    predictions: list[RetentionPrediction] | None = None,
) -> SessionStatsObject:
    start = datetime(2026, 5, 5, 10, 0, 0)
    end = start + timedelta(seconds=max(duration_minutes * 60.0, 1.0))
    return SessionStatsObject(
        session_id="s1",
        deck_id=7,
        grades_distribution=GradesDistribution(
            again=again,
            hard=hard,
            good=good,
            easy=easy,
        ),
        start_time=start,
        end_time=end,
        retention_predictions=predictions or [],
    )


def test_session_stats_json_round_trip() -> None:
    """Property 6 — dict/json round-trip."""
    s = _session(again=1, hard=0, good=2, easy=1, duration_minutes=2.0)
    wire = export_session_stats_json(s)
    back = import_session_stats_json(wire)
    assert back.model_dump() == s.model_dump()


def test_grade_percentages_sum_to_hundred_or_zero() -> None:
    """Property 7 — проценты ~100 при ненулевой сессии."""
    g0 = GradesDistribution()
    assert sum(g0.percentages().values()) == pytest.approx(0.0)

    g = GradesDistribution(again=1, hard=1, good=1, easy=1)
    assert sum(g.percentages().values()) == pytest.approx(100.0)


def test_velocity_equals_cards_per_minute() -> None:
    """Property 8 — velocity = reviewed / (duration_minutes)."""
    s = _session(again=2, hard=1, good=0, easy=0, duration_minutes=3.0)
    assert s.grades_distribution.total_reviewed() == 3
    assert s.duration_seconds == pytest.approx(3.0 * 60.0)
    assert s.velocity == pytest.approx(3.0 / 3.0)


def test_retention_predictions_deterministic_order() -> None:
    """Property 9 — детерминированный порядок при тех же входах."""
    preds = [
        RetentionPrediction(day_index=2, due_cards=4),
        RetentionPrediction(day_index=0, due_cards=1),
    ]
    s1 = _session(again=2, hard=0, good=0, easy=3, duration_minutes=1.0, predictions=preds)
    s2 = _session(again=2, hard=0, good=0, easy=3, duration_minutes=1.0, predictions=list(reversed(preds)))
    assert [p.model_dump() for p in s1.retention_predictions] == [
        p.model_dump() for p in s2.retention_predictions
    ]
    assert seven_day_schedule_counts(preds) == [1, 0, 4, 0, 0, 0, 0]
    sched1 = seven_day_schedule_counts(s1.retention_predictions)
    sched2 = seven_day_schedule_counts(s2.retention_predictions)
    assert sched1 == sched2 == [1, 0, 4, 0, 0, 0, 0]


def test_insufficient_data_matches_fewer_than_five() -> None:
    """Property 10 — флаг при <5 карточек."""
    small = _session(again=1, hard=1, good=0, easy=0, duration_minutes=1.0)
    assert small.grades_distribution.total_reviewed() == 2
    assert small.insufficient_data is True

    big = _session(again=1, hard=1, good=1, easy=2, duration_minutes=1.0)
    assert big.insufficient_data is False


def test_analytics_export_json_serializable() -> None:
    """Property 11 — только JSON-serializable."""
    s = _session(again=0, hard=0, good=4, easy=1, duration_minutes=0.5)
    d = session_stats_to_plain_dict(s)
    assert_fully_json_serializable(d)
    assert_fully_json_serializable(json_round := export_session_stats_json(s))
    import_session_stats_json(json_round)
