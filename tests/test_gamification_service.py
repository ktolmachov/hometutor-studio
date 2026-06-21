"""Тесты геймификации (KV-состояние)."""

from __future__ import annotations

import json

import pytest

from app import gamification_service as gs


@pytest.fixture(autouse=True)
def _isolated_kv(monkeypatch):
    store: dict[str, str] = {}

    def _get(k: str) -> str | None:
        return store.get(k)

    def _set(k: str, v: str) -> None:
        store[k] = v

    monkeypatch.setattr(gs, "get_kv", _get)
    monkeypatch.setattr(gs, "set_kv", _set)
    yield
    store.clear()


def test_record_quiz_activity_awards_xp_and_updates_streak():
    r1 = gs.record_quiz_activity(score_0_1=0.9, scope="micro")
    assert r1["xp_gained"] >= 5
    assert r1["total_xp"] >= r1["xp_gained"]
    assert r1["level"] >= 1
    assert r1["daily_streak"] >= 1

    r2 = gs.record_quiz_activity(score_0_1=0.8, scope="topic")
    assert r2["total_xp"] > r1["total_xp"]


def test_get_snapshot_matches_state():
    gs.record_quiz_activity(score_0_1=1.0, scope="micro")
    snap = gs.get_snapshot()
    assert "total_xp" in snap
    assert "level_title" in snap
    assert "xp_in_level" in snap
    assert "daily_streak" in snap


def test_level_title_bands():
    assert gs.level_title(1) == "Newbie"
    assert gs.level_title(3) == "Apprentice"
    assert gs.level_title(7) == "Scholar"
    assert gs.level_title(15) == "Expert"
    assert gs.level_title(25) == "Master"


def test_get_xp_history_length():
    h = gs.get_xp_history(days=7)
    assert len(h) == 7
    assert all("date" in row and "xp" in row for row in h)


def test_award_xp_for_block_and_dedup(monkeypatch):
    from app.learner_model_service import PersonalizedLearnerModel

    def _gp(uid=None, session_id=None):
        return PersonalizedLearnerModel(
            user_id=uid or "local",
            emotional_state="neutral",
            learning_velocity=0.1,
        )

    monkeypatch.setattr("app.learner_model_service.get_personalized_learner_profile", _gp)

    r = gs.award_xp_for_block(
        "local",
        {"type": "review", "concept": "c1", "duration_min": 10, "xp_base": 25},
        block_index=0,
        plan_date="2099-01-01",
    )
    assert r["ok"] is True
    assert r.get("already_awarded") is not True
    assert int(r["xp_earned"]) >= 1
    assert gs.get_total_xp() == int(r["new_total"])

    r2 = gs.award_xp_for_block(
        "local",
        {"type": "review", "concept": "c1", "duration_min": 10, "xp_base": 25},
        block_index=0,
        plan_date="2099-01-01",
    )
    assert r2.get("already_awarded") is True
    assert int(r2.get("xp_earned") or 0) == 0


def test_count_completed_plan_blocks_uses_current_fingerprints(monkeypatch):
    from app.learner_model_service import PersonalizedLearnerModel

    def _gp(uid=None, session_id=None):
        return PersonalizedLearnerModel(
            user_id=uid or "local",
            emotional_state="neutral",
            learning_velocity=0.1,
        )

    monkeypatch.setattr("app.learner_model_service.get_personalized_learner_profile", _gp)

    blocks = [
        {"type": "review", "concept": "c1", "duration_min": 10, "xp_base": 25},
        {"type": "gap", "concept": "c2", "duration_min": 10, "xp_base": 40},
    ]
    gs.award_xp_for_block("local", blocks[0], block_index=0, plan_date="2099-01-01")

    assert gs.count_completed_plan_blocks(plan_date="2099-01-01", blocks=blocks) == 1
    assert gs.count_completed_plan_blocks(plan_date="2099-01-02", blocks=blocks) == 0
