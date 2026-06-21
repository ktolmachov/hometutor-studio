"""SSR rule baseline — массовые регрессии приоритета до включения ML reranking.

Покрытие: параметризация по счётчикам очередей и поверхностям + явные граничные кейсы.
"""

from __future__ import annotations

import pytest

from app.ui.adaptive_plan_card import build_smart_study_recommendation

_SURFACES_HOME_TUTOR_FCHUB = ("home", "tutor_chat", "flashcards_hub")


@pytest.mark.parametrize("fc", range(1, 18))
@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_fc_queue_beats_sm2_quiz_tutor_and_qa(surface: str, fc: int) -> None:
    """При любой положительной очереди карточек приоритет всегда cards_due."""
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=fc,
        sm2_due_n=99,
        quiz_feedback_status="failed",
        has_tutor_resume=True,
        tutor_topic="Topic",
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "cards_due"
    assert rec.primary_nav == "flashcards_review"
    assert rec.primary_label_ru.strip()
    assert rec.why_now_ru.strip()
    ids = {s.action_id for s in rec.secondaries}
    assert "quiz_nav" in ids
    assert "progress_go" in ids
    assert 2 <= len(rec.secondaries) <= 4


@pytest.mark.parametrize("due", range(1, 18))
@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_sm2_queue_when_no_fc_beats_lower_signals(surface: str, due: int) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=due,
        quiz_feedback_status="failed",
        has_tutor_resume=True,
        tutor_topic="Topic",
        has_last_answer_qa=True,
        plan_primary_block={"type": "gap", "concept": "RAG"},
    )
    assert rec.hint_kind == "sm2_due"
    assert rec.primary_nav == "sm2_tutor"


@pytest.mark.parametrize(
    "qstat",
    ("fail", "failed", "incorrect", "wrong", "bad", "partial"),
)
@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_quiz_failed_beats_plan_tutor_qa_when_no_queues(surface: str, qstat: str) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status=qstat,
        has_tutor_resume=True,
        tutor_topic="Topic",
        has_last_answer_qa=True,
        plan_primary_block={"type": "gap", "concept": "RAG"},
    )
    assert rec.hint_kind == "quiz_failed"
    # Concept Recovery Ladder step 1: мягкий вход через qa_continue, не сразу quiz_recovery_tutor.
    assert rec.primary_nav == "qa_continue"
    assert "recovery_ladder_step=1" in rec.ml_audit_ru


def test_quiz_failed_beats_tutor_resume_explicit() -> None:
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status="failed",
        has_tutor_resume=True,
        tutor_topic="ResumeTopic",
    )
    assert rec.hint_kind == "quiz_failed"


@pytest.mark.parametrize("surface", ("home", "tutor_chat"))
def test_adaptive_plan_surface_with_block_when_queues_clear(surface: str) -> None:
    rec = build_smart_study_recommendation(
        surface="adaptive_plan",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status=None,
        plan_primary_block={"type": "gap", "concept": "RAG"},
        has_tutor_resume=True,
        tutor_topic="T",
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "adaptive_plan"
    assert rec.primary_nav == "plan_block_tutor"
    _ = surface


def test_home_ignores_plan_block_without_queues_but_prefers_answer_ready() -> None:
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        plan_primary_block={"type": "new", "concept": "X"},
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "answer_ready"


@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_tutor_resume_requires_topic(surface: str) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=0,
        has_tutor_resume=True,
        tutor_topic="   ",
        has_last_answer_qa=False,
        has_reading_resume=False,
        first_weak_concept=None,
    )
    assert rec.hint_kind == "safe_default"


@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_tutor_resume_when_topic_present(surface: str) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=0,
        has_tutor_resume=True,
        tutor_topic="Algebra",
    )
    assert rec.hint_kind == "tutor_resume"
    assert "Algebra" in rec.primary_label_ru


@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_answer_ready_after_resume_signals_cleared(surface: str) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "answer_ready"


@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_mastery_stale_reading_resume_without_weak(surface: str) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=0,
        has_last_answer_qa=False,
        has_reading_resume=True,
        first_weak_concept=None,
    )
    assert rec.hint_kind == "mastery_stale"
    assert "сохранённой теме" in rec.why_now_ru


@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_mastery_stale_weak_concept(surface: str) -> None:
    rec = build_smart_study_recommendation(
        surface=surface,
        flashcard_due_n=0,
        sm2_due_n=0,
        first_weak_concept="Entropy",
    )
    assert rec.hint_kind == "mastery_stale"
    assert "Entropy" in rec.why_now_ru


@pytest.mark.parametrize("surface", _SURFACES_HOME_TUTOR_FCHUB)
def test_safe_default_minimum_signals(surface: str) -> None:
    rec = build_smart_study_recommendation(surface=surface)
    assert rec.hint_kind == "safe_default"
    assert rec.primary_nav == "safe_tutor_5min"


@pytest.mark.parametrize("fc", (-3, -1, 0))
def test_negative_fc_clamped_to_safe_or_lower_priority(fc: int) -> None:
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=fc,
        sm2_due_n=0,
        quiz_feedback_status=None,
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "answer_ready"


@pytest.mark.parametrize("due", (-5, -1))
def test_negative_sm2_clamped(due: int) -> None:
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=due,
        quiz_feedback_status="failed",
    )
    assert rec.hint_kind == "quiz_failed"


def test_flashcards_hub_cards_due_excludes_fc_create() -> None:
    rec = build_smart_study_recommendation(
        surface="flashcards_hub",
        flashcard_due_n=2,
        sm2_due_n=0,
    )
    ids = {s.action_id for s in rec.secondaries}
    assert "fc_create" not in ids


def test_non_home_surfaces_still_cards_due_word_plural() -> None:
    rec = build_smart_study_recommendation(surface="tutor_chat", flashcard_due_n=11)
    assert rec.hint_kind == "cards_due"
    assert "карточек" in rec.why_now_ru


@pytest.mark.parametrize(
    "n, needle",
    [
        (1, "карточка"),
        (2, "карточки"),
        (21, "карточка"),
        (22, "карточки"),
        (111, "карточек"),
    ],
)
def test_ru_flashcard_word_in_why_now(n: int, needle: str) -> None:
    rec = build_smart_study_recommendation(surface="home", flashcard_due_n=n)
    assert needle in rec.why_now_ru


@pytest.mark.parametrize("passthrough", ("pass", "passed", "ok", "correct", "good", None, ""))
def test_quiz_non_failure_does_not_trigger_quiz_failed(passthrough: str | None) -> None:
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=0,
        sm2_due_n=0,
        quiz_feedback_status=passthrough,
        has_last_answer_qa=True,
    )
    assert rec.hint_kind == "answer_ready"


@pytest.mark.parametrize("concept_raw", ("general", "", "QA", "entropy"))
def test_adaptive_plan_placeholder_concepts_still_route(concept_raw: str) -> None:
    rec = build_smart_study_recommendation(
        surface="adaptive_plan",
        flashcard_due_n=0,
        sm2_due_n=0,
        plan_primary_block={"type": "gap", "concept": concept_raw},
    )
    assert rec.hint_kind == "adaptive_plan"


def test_adaptive_plan_named_concept_in_label() -> None:
    rec = build_smart_study_recommendation(
        surface="adaptive_plan",
        flashcard_due_n=0,
        sm2_due_n=0,
        plan_primary_block={"type": "review", "concept": "Bayes"},
    )
    assert "Bayes" in rec.primary_label_ru


@pytest.mark.parametrize("row", range(30))
def test_secondaries_invariants_random_priority_mix_rows(row: int) -> None:
    """Доп. строки параметризации для покрытия смесей без дублирования прод-логики."""
    fc = row % 5
    due = (row // 5) % 4
    rec = build_smart_study_recommendation(
        surface="home",
        flashcard_due_n=fc,
        sm2_due_n=due if fc == 0 else 0,
        has_last_answer_qa=fc == 0 and due == 0 and row % 2 == 0,
    )
    assert 2 <= len(rec.secondaries) <= 4
    ids = {s.action_id for s in rec.secondaries}
    assert "quiz_nav" in ids
    assert "progress_go" in ids
