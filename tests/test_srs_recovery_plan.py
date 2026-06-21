"""
US-7.2 + US-6.3 acceptance tests.

US-7.2 — Soft-recovery после пропуска нескольких дней:
  defer_due_flashcards_for_recovery keeps the first keep_limit due cards
  and staggers the remainder across stagger_days days; returns deferred count.

US-6.3 — Видеть историю перестроения плана:
  plan_snapshot_for_history produces compact snapshots with date/focus/concepts.
  History is capped at _MAX_PLAN_HISTORY (3) and deduplicates entries by date.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.user_state import reset_schema_cache_for_tests


# ---------------------------------------------------------------------------
# Shared DB isolation fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "recovery_plan.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_overdue_cards(n: int, deck_name: str = "test_deck") -> int:
    """Create a deck and insert n overdue flashcards. Returns deck_id."""
    from app.user_state import _with_db, add_flashcard, create_flashcard_deck

    deck_id = create_flashcard_deck(deck_name)
    past = (datetime.now(tz=timezone.utc) - timedelta(days=1)).isoformat()

    for i in range(n):
        add_flashcard(deck_id, f"Q{i}", f"A{i}")

    # Force all cards to be overdue (next_review in the past)
    def _set_past(conn):
        conn.execute(
            "UPDATE flashcards SET next_review = ? WHERE deck_id = ?",
            (past, deck_id),
        )
        conn.commit()

    _with_db(_set_past, write=True)
    return deck_id


def _count_due_now() -> int:
    from app.user_state import get_due_flashcards

    return len(get_due_flashcards(500))


def _count_deferred() -> int:
    """Cards with next_review strictly in the future."""
    from app.user_state import _with_db

    def _work(conn):
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM flashcards WHERE next_review > datetime('now')"
        ).fetchone()
        return int(row["n"]) if row else 0

    return _with_db(_work)


# ---------------------------------------------------------------------------
# US-7.2 — defer_due_flashcards_for_recovery
# ---------------------------------------------------------------------------


class TestDeferDueFlashcardsForRecovery:
    """US-7.2: soft-recovery distributes overdue cards over stagger_days."""

    def test_returns_zero_when_due_lte_keep_limit(self, isolated_db):
        from app.user_state import defer_due_flashcards_for_recovery

        _add_overdue_cards(5, "deck_a")
        deferred = defer_due_flashcards_for_recovery(keep_limit=7, stagger_days=3)
        assert deferred == 0

    def test_returns_zero_when_no_due_cards(self, isolated_db):
        from app.user_state import defer_due_flashcards_for_recovery

        deferred = defer_due_flashcards_for_recovery(keep_limit=7)
        assert deferred == 0

    def test_defers_excess_cards_above_keep_limit(self, isolated_db):
        """US-7.2 core: 20 due cards, keep 7 → 13 deferred."""
        from app.user_state import defer_due_flashcards_for_recovery

        _add_overdue_cards(20, "deck_b")
        assert _count_due_now() == 20

        deferred = defer_due_flashcards_for_recovery(keep_limit=7, stagger_days=5)

        assert deferred == 13
        assert _count_due_now() == 7  # exactly keep_limit remain due now

    def test_deferred_cards_have_future_next_review(self, isolated_db):
        from app.user_state import defer_due_flashcards_for_recovery

        _add_overdue_cards(15, "deck_c")
        defer_due_flashcards_for_recovery(keep_limit=5, stagger_days=3)

        assert _count_deferred() == 10

    def test_stagger_distributes_over_multiple_days(self, isolated_db):
        """Cards should not all land on the same future date."""
        from app.user_state import _with_db, defer_due_flashcards_for_recovery

        _add_overdue_cards(12, "deck_d")
        defer_due_flashcards_for_recovery(keep_limit=2, stagger_days=5)

        def _distinct_dates(conn):
            rows = conn.execute(
                "SELECT DISTINCT date(next_review) AS d FROM flashcards WHERE next_review > datetime('now')"
            ).fetchall()
            return len(rows)

        distinct = _with_db(_distinct_dates)
        assert distinct >= 2  # cards spread across at least 2 different days

    def test_large_overdue_scenario(self, isolated_db):
        """US-7.2 explicit scenario: >20 due, keep first 7."""
        from app.user_state import defer_due_flashcards_for_recovery

        _add_overdue_cards(25, "deck_e")
        deferred = defer_due_flashcards_for_recovery(keep_limit=7, stagger_days=5)

        assert deferred == 18
        assert _count_due_now() == 7

    def test_keep_limit_clamped_to_minimum_1(self, isolated_db):
        """keep_limit=0 is clamped to 1 — at least one card stays due."""
        from app.user_state import defer_due_flashcards_for_recovery

        _add_overdue_cards(10, "deck_f")
        deferred = defer_due_flashcards_for_recovery(keep_limit=0, stagger_days=3)

        assert _count_due_now() == 1
        assert deferred == 9

    def test_default_keep_limit_is_7(self, isolated_db):
        """Default keep_limit=7 per US-7.2 recovery plan."""
        from app.user_state import defer_due_flashcards_for_recovery

        _add_overdue_cards(20, "deck_g")
        deferred = defer_due_flashcards_for_recovery()
        assert deferred == 13
        assert _count_due_now() == 7

    def test_sm2_fields_unchanged_after_deferral(self, isolated_db):
        """Deferral must not modify SM-2 scheduling fields (interval_days, easiness)."""
        from app.user_state import _with_db, defer_due_flashcards_for_recovery

        _add_overdue_cards(10, "deck_h")

        def _snapshot(conn):
            return {
                r["id"]: (r["interval_days"], r["easiness"])
                for r in conn.execute("SELECT id, interval_days, easiness FROM flashcards").fetchall()
            }

        before = _with_db(_snapshot)
        defer_due_flashcards_for_recovery(keep_limit=3, stagger_days=3)
        after = _with_db(_snapshot)

        for card_id, (iv, ef) in before.items():
            assert after[card_id][0] == iv, f"interval_days changed for card {card_id}"
            assert after[card_id][1] == ef, f"easiness changed for card {card_id}"


# ---------------------------------------------------------------------------
# US-6.3 — plan_snapshot_for_history
# ---------------------------------------------------------------------------


class TestPlanSnapshotForHistory:
    """US-6.3: compact snapshots capture date, focus counts, and top concepts."""

    def _make_plan(
        self,
        *,
        date: str = "2026-04-20",
        blocks: list[dict] | None = None,
        motivation: str = "Продолжай в том же духе!",
    ) -> dict:
        return {
            "date": date,
            "blocks": blocks or [],
            "motivation_message": motivation,
            "total_xp_goal": 150,
        }

    def test_snapshot_contains_date(self):
        from app.adaptive_plan import plan_snapshot_for_history

        plan = self._make_plan(date="2026-04-21")
        snap = plan_snapshot_for_history(plan)
        assert snap["date"] == "2026-04-21"

    def test_snapshot_counts_review_gap_new(self):
        from app.adaptive_plan import plan_snapshot_for_history

        plan = self._make_plan(
            blocks=[
                {"concept": "A", "type": "review"},
                {"concept": "B", "type": "gap"},
                {"concept": "C", "type": "gap"},
                {"concept": "D", "type": "new"},
            ]
        )
        snap = plan_snapshot_for_history(plan)
        reviews, gaps, new_c = snap["focus_review_gap_new"]
        assert reviews == 1
        assert gaps == 2
        assert new_c == 1

    def test_snapshot_main_concepts_capped_at_3(self):
        from app.adaptive_plan import plan_snapshot_for_history

        plan = self._make_plan(
            blocks=[{"concept": f"C{i}", "type": "review"} for i in range(6)]
        )
        snap = plan_snapshot_for_history(plan)
        assert len(snap["main_concepts"]) == 3

    def test_snapshot_motivation_excerpt_truncated_at_180(self):
        from app.adaptive_plan import plan_snapshot_for_history

        plan = self._make_plan(motivation="X" * 250)
        snap = plan_snapshot_for_history(plan)
        assert len(snap["motivation_excerpt"]) <= 180

    def test_snapshot_empty_blocks(self):
        from app.adaptive_plan import plan_snapshot_for_history

        snap = plan_snapshot_for_history(self._make_plan(blocks=[]))
        assert snap["focus_review_gap_new"] == [0, 0, 0]
        assert snap["main_concepts"] == []

    def test_snapshot_total_xp_goal_preserved(self):
        from app.adaptive_plan import plan_snapshot_for_history

        plan = self._make_plan(blocks=[{"concept": "A", "type": "review"}])
        plan["total_xp_goal"] = 200
        snap = plan_snapshot_for_history(plan)
        assert snap["total_xp_goal"] == 200


# ---------------------------------------------------------------------------
# US-6.3 — history capping and deduplication
# ---------------------------------------------------------------------------


class TestAdaptivePlanHistory:
    """US-6.3: history is capped at 3 entries; same-date entries are deduplicated."""

    def test_history_capped_at_max_3(self, isolated_db, tmp_path):
        from app.adaptive_plan import (
            AdaptiveDailyPlan,
            _MAX_PLAN_HISTORY,
            get_adaptive_daily_plan_history,
        )
        from app.knowledge_graph import JsonKnowledgeGraph

        kg_path = tmp_path / "kg.json"
        kg_path.write_text(
            json.dumps({
                "concepts": {"A": {"description": "", "prerequisites": []}},
                "documents": {},
                "edges": {},
            }),
            encoding="utf-8",
        )
        kg = JsonKnowledgeGraph(kg_path)

        # Build plan 5 times — history should cap at _MAX_PLAN_HISTORY (3)
        for _ in range(5):
            AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()

        hist = get_adaptive_daily_plan_history()
        assert len(hist) <= _MAX_PLAN_HISTORY

    def test_history_entries_have_required_fields(self, isolated_db, tmp_path):
        from app.adaptive_plan import AdaptiveDailyPlan, get_adaptive_daily_plan_history
        from app.knowledge_graph import JsonKnowledgeGraph

        kg_path = tmp_path / "kg2.json"
        kg_path.write_text(
            json.dumps({
                "concepts": {
                    "X": {"description": "", "prerequisites": []},
                    "Y": {"description": "", "prerequisites": ["X"]},
                },
                "documents": {},
                "edges": {},
            }),
            encoding="utf-8",
        )
        kg = JsonKnowledgeGraph(kg_path)

        AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()
        AdaptiveDailyPlan("local", kg=kg).build_adaptive_daily_plan()

        hist = get_adaptive_daily_plan_history()
        assert len(hist) >= 1
        entry = hist[-1]
        assert "date" in entry and entry["date"]
        assert "focus_review_gap_new" in entry
        assert len(entry["focus_review_gap_new"]) == 3
        assert "main_concepts" in entry
        assert "archived_at" in entry

    def test_history_empty_before_first_rebuild(self, isolated_db):
        from app.adaptive_plan import get_adaptive_daily_plan_history

        assert get_adaptive_daily_plan_history() == []
