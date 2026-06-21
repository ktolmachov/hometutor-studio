"""E10.2: адаптивная сложность micro-quiz из mastery vector (recognition/recall/transfer)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import reset_settings_cache
from app.quiz_adaptive import (
    SUCCESS_THRESHOLD,
    choose_micro_quiz_difficulty,
    diagnose_quiz_result,
    mastery_label_from_vector_level,
    update_mastery_after_score,
)
from app.user_state import reset_schema_cache_for_tests


@pytest.fixture
def isolated_user_db(monkeypatch, tmp_path: Path):
    db = tmp_path / "qm.db"
    monkeypatch.setenv("USER_STATE_DB", str(db))
    reset_settings_cache()
    reset_schema_cache_for_tests()
    yield db
    reset_settings_cache()
    reset_schema_cache_for_tests()


def test_choose_micro_quiz_difficulty_beginner_fallback():
    assert choose_micro_quiz_difficulty("beginner", []) == "easy"


def test_choose_micro_quiz_difficulty_recognition_in_recent():
    assert choose_micro_quiz_difficulty("intermediate", ["recognition"]) == "easy"


def test_vector_level_maps_to_three_bands():
    assert choose_micro_quiz_difficulty("intermediate", [], vector_level="recognition") == "easy"
    assert choose_micro_quiz_difficulty("intermediate", [], vector_level="recall") == "medium"
    assert choose_micro_quiz_difficulty("intermediate", [], vector_level="transfer") == "hard"


def test_vector_level_takes_priority_over_tutor_advanced():
    """При заданном vector_level полоса из вектора, а не «advanced» тьютора."""
    assert choose_micro_quiz_difficulty("advanced", [], vector_level="recognition") == "easy"


def test_transfer_errors_soften_band():
    assert (
        choose_micro_quiz_difficulty("intermediate", ["transfer"], vector_level="transfer") == "medium"
    )


def test_mastery_label_from_vector_level():
    assert mastery_label_from_vector_level("recognition") == "beginner"
    assert mastery_label_from_vector_level("recall") == "intermediate"
    assert mastery_label_from_vector_level("transfer") == "advanced"
    assert mastery_label_from_vector_level(None) is None


def test_diagnose_quiz_result_correct():
    r = diagnose_quiz_result("B", "B", "application")
    assert r["status"] == "correct"


def test_diagnose_quiz_result_incorrect():
    r = diagnose_quiz_result("A", "B", "recognition")
    assert r["status"] == "incorrect"
    assert "recommended_action" in r


def test_generate_micro_quiz_offline_uses_vector_when_topic_tracked(isolated_user_db, monkeypatch):
    from app import quiz_service

    update_mastery_after_score("TrackedTopic", SUCCESS_THRESHOLD + 0.05)
    update_mastery_after_score("TrackedTopic", SUCCESS_THRESHOLD + 0.05)
    # после двух успехов уровень recall → medium band
    q = quiz_service.generate_micro_quiz(
        "тема",
        "beginner",
        [],
        use_llm=False,
        topic_concept="TrackedTopic",
    )
    assert q["difficulty"] == "medium"

