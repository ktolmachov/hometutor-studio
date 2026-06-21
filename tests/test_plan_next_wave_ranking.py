"""
epoch-wave-contract — Wave ranking formula unit tests.

Tests cover the wave_synergy and scoring logic described in
generate_plan_next_prompt.md Phase 3 wave-ranking formula:

  wave_synergy = min(5, n_unique_us * 0.8 + shared_read_files * 0.4)
  user_visible_impact 35%, wave_synergy 20%, mot_recency_gap 20%,
  dependency_ready 15%, delivery_cost 10%

All scoring functions are pure Python — no DB or file I/O required.
"""

from __future__ import annotations

import math
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Pure scoring functions (extracted from spec § 4.2, tested in isolation)
# ---------------------------------------------------------------------------


def wave_synergy_score(n_unique_us: int, shared_read_files: int) -> float:
    """wave_synergy = min(5, n_us * 0.8 + shared_files * 0.4)"""
    return min(5.0, n_unique_us * 0.8 + shared_read_files * 0.4)


def mot_recency_gap_score(last_touched_date: date | None, today: date | None = None) -> float:
    """≥14d → 5, ≥7d → 3, <3d → 1, null → 3"""
    if today is None:
        today = date.today()
    if last_touched_date is None:
        return 3.0
    days = (today - last_touched_date).days
    if days >= 14:
        return 5.0
    if days >= 7:
        return 3.0
    return 1.0


def delivery_cost_score(cost_estimates: list[str]) -> float:
    """all-S → 5, any-L → 1, otherwise 3 (M or mixed)"""
    if not cost_estimates:
        return 3.0
    if "L" in cost_estimates:
        return 1.0
    if all(c == "S" for c in cost_estimates):
        return 5.0
    return 3.0


def dependency_ready_score(all_deps_closed: bool) -> float:
    return 5.0 if all_deps_closed else 1.0


def wave_total_score(
    user_visible_impact: float,  # 1–5
    synergy: float,              # 1–5
    recency_gap: float,          # 1–5
    dep_ready: float,            # 1–5
    cost: float,                 # 1–5
) -> float:
    return (
        user_visible_impact * 0.35
        + synergy * 0.20
        + recency_gap * 0.20
        + dep_ready * 0.15
        + cost * 0.10
    )


# ---------------------------------------------------------------------------
# wave_synergy_score tests
# ---------------------------------------------------------------------------


class TestWaveSynergyScore:
    def test_single_us_no_shared_files(self):
        score = wave_synergy_score(n_unique_us=1, shared_read_files=0)
        assert score == pytest.approx(0.8)

    def test_four_us_no_shared_files(self):
        score = wave_synergy_score(n_unique_us=4, shared_read_files=0)
        assert score == pytest.approx(3.2)

    def test_four_us_three_shared_files(self):
        score = wave_synergy_score(n_unique_us=4, shared_read_files=3)
        assert score == pytest.approx(min(5.0, 4 * 0.8 + 3 * 0.4))

    def test_capped_at_5(self):
        score = wave_synergy_score(n_unique_us=10, shared_read_files=10)
        assert score == pytest.approx(5.0)

    def test_zero_us_zero_files_gives_zero(self):
        score = wave_synergy_score(n_unique_us=0, shared_read_files=0)
        assert score == pytest.approx(0.0)

    def test_two_us_two_shared_files(self):
        score = wave_synergy_score(n_unique_us=2, shared_read_files=2)
        assert score == pytest.approx(2 * 0.8 + 2 * 0.4)


# ---------------------------------------------------------------------------
# mot_recency_gap_score tests
# ---------------------------------------------------------------------------


class TestMotRecencyGapScore:
    def _ago(self, days: int) -> date:
        return date.today() - timedelta(days=days)

    def test_null_last_touched_gives_3(self):
        assert mot_recency_gap_score(None) == pytest.approx(3.0)

    def test_14_days_gives_5(self):
        assert mot_recency_gap_score(self._ago(14)) == pytest.approx(5.0)

    def test_20_days_gives_5(self):
        assert mot_recency_gap_score(self._ago(20)) == pytest.approx(5.0)

    def test_7_days_gives_3(self):
        assert mot_recency_gap_score(self._ago(7)) == pytest.approx(3.0)

    def test_10_days_gives_3(self):
        assert mot_recency_gap_score(self._ago(10)) == pytest.approx(3.0)

    def test_1_day_gives_1(self):
        assert mot_recency_gap_score(self._ago(1)) == pytest.approx(1.0)

    def test_0_days_gives_1(self):
        assert mot_recency_gap_score(date.today()) == pytest.approx(1.0)

    def test_explicit_today_parameter(self):
        today = date(2026, 4, 22)
        last = date(2026, 4, 1)  # 21 days ago
        assert mot_recency_gap_score(last, today) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# delivery_cost_score tests
# ---------------------------------------------------------------------------


class TestDeliveryCostScore:
    def test_all_s_gives_5(self):
        assert delivery_cost_score(["S", "S", "S"]) == pytest.approx(5.0)

    def test_any_l_gives_1(self):
        assert delivery_cost_score(["S", "L"]) == pytest.approx(1.0)

    def test_mixed_m_s_gives_3(self):
        assert delivery_cost_score(["S", "M"]) == pytest.approx(3.0)

    def test_empty_gives_3(self):
        assert delivery_cost_score([]) == pytest.approx(3.0)

    def test_single_l_gives_1(self):
        assert delivery_cost_score(["L"]) == pytest.approx(1.0)

    def test_single_m_gives_3(self):
        assert delivery_cost_score(["M"]) == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# wave_total_score tests
# ---------------------------------------------------------------------------


class TestWaveTotalScore:
    def test_all_5_gives_5(self):
        score = wave_total_score(5.0, 5.0, 5.0, 5.0, 5.0)
        assert score == pytest.approx(5.0)

    def test_all_1_gives_1(self):
        score = wave_total_score(1.0, 1.0, 1.0, 1.0, 1.0)
        assert score == pytest.approx(1.0)

    def test_weights_sum_to_1(self):
        """Verify that 0.35+0.20+0.20+0.15+0.10 = 1.0 (no leaking)."""
        total = 0.35 + 0.20 + 0.20 + 0.15 + 0.10
        assert total == pytest.approx(1.0)

    def test_high_impact_low_others(self):
        score = wave_total_score(5.0, 1.0, 1.0, 1.0, 1.0)
        assert score == pytest.approx(5.0 * 0.35 + 1.0 * 0.65)

    def test_wave_synergy_20_percent(self):
        """Changing synergy from 1→5 changes score by exactly 20% of range."""
        base = wave_total_score(3.0, 1.0, 3.0, 3.0, 3.0)
        high = wave_total_score(3.0, 5.0, 3.0, 3.0, 3.0)
        assert high - base == pytest.approx((5.0 - 1.0) * 0.20)

    def test_mot_recency_gap_20_percent(self):
        base = wave_total_score(3.0, 3.0, 1.0, 3.0, 3.0)
        high = wave_total_score(3.0, 3.0, 5.0, 3.0, 3.0)
        assert high - base == pytest.approx((5.0 - 1.0) * 0.20)

    def test_user_visible_impact_35_percent(self):
        base = wave_total_score(1.0, 3.0, 3.0, 3.0, 3.0)
        high = wave_total_score(5.0, 3.0, 3.0, 3.0, 3.0)
        assert high - base == pytest.approx((5.0 - 1.0) * 0.35)


# ---------------------------------------------------------------------------
# Integration: rank two waves and verify ordering
# ---------------------------------------------------------------------------


class TestWaveRankingIntegration:
    """Verify that a high-synergy recent wave beats a low-synergy stale wave."""

    def _score_wave_a(self) -> float:
        """wave-a: 4 US, 2 shared files, touched 2 days ago, all deps ready, all S"""
        return wave_total_score(
            user_visible_impact=4.0,
            synergy=wave_synergy_score(4, 2),
            recency_gap=mot_recency_gap_score(date.today() - timedelta(days=2)),
            dep_ready=dependency_ready_score(True),
            cost=delivery_cost_score(["S", "S"]),
        )

    def _score_wave_b(self) -> float:
        """wave-b: 1 US, 0 shared files, touched 20 days ago, dep missing, mixed M"""
        return wave_total_score(
            user_visible_impact=3.0,
            synergy=wave_synergy_score(1, 0),
            recency_gap=mot_recency_gap_score(date.today() - timedelta(days=20)),
            dep_ready=dependency_ready_score(False),
            cost=delivery_cost_score(["M"]),
        )

    def test_high_synergy_recent_wave_beats_stale_wave(self):
        assert self._score_wave_a() > self._score_wave_b()

    def test_scores_are_in_valid_range(self):
        for score in [self._score_wave_a(), self._score_wave_b()]:
            assert 1.0 <= score <= 5.0

    def test_wave_ranking_is_deterministic(self):
        """Same inputs → same score every time."""
        s1 = self._score_wave_a()
        s2 = self._score_wave_a()
        assert s1 == pytest.approx(s2)


import pytest
