"""E11-A: детерминированный primary CTA на главной (US-14.1)."""

from app.ui.continuity_bridge import (
    GUIDED_PRIMARY_HOME_CTA_LABELS,
    guided_primary_home_cta_ru,
    guided_primary_reason_line_ru,
)


def test_guided_labels_are_exactly_four_canonical_strings():
    assert len(GUIDED_PRIMARY_HOME_CTA_LABELS) == 4
    for pair in (
        guided_primary_home_cta_ru(
            flashcard_due_n=1, has_tutor_resume=True, due_n=9, has_mastery_gap=True
        ),
        guided_primary_home_cta_ru(has_tutor_resume=False, due_n=2, has_mastery_gap=False),
        guided_primary_home_cta_ru(has_tutor_resume=False, due_n=0, has_mastery_gap=True),
        guided_primary_home_cta_ru(has_tutor_resume=False, due_n=0, has_mastery_gap=False),
    ):
        assert pair[0] in GUIDED_PRIMARY_HOME_CTA_LABELS


def test_priority_flashcard_over_concept_due_and_resume():
    assert (
        guided_primary_home_cta_ru(
            flashcard_due_n=2, has_tutor_resume=True, due_n=9, has_mastery_gap=True
        )[1]
        == "flashcard_due"
    )


def test_priority_concept_due_before_resume():
    assert (
        guided_primary_home_cta_ru(
            flashcard_due_n=0, has_tutor_resume=True, due_n=1, has_mastery_gap=True
        )[1]
        == "due_review"
    )


def test_priority_resume_when_queues_clear():
    assert (
        guided_primary_home_cta_ru(
            flashcard_due_n=0, has_tutor_resume=True, due_n=0, has_mastery_gap=True
        )[1]
        == "resume"
    )


def test_priority_mastery_gap_then_safe_starter():
    assert guided_primary_home_cta_ru(has_tutor_resume=False, due_n=0, has_mastery_gap=True)[1] == "mastery_gap"
    assert guided_primary_home_cta_ru(has_tutor_resume=False, due_n=0, has_mastery_gap=False)[1] == "safe_starter"


def test_sparse_fallback_label():
    label, kind = guided_primary_home_cta_ru(
        has_tutor_resume=False, due_n=0, has_mastery_gap=False
    )
    assert kind == "safe_starter"
    assert label == "Учить эту тему 5 минут"


def test_reason_line_is_present_for_all_kinds():
    for kind in ("flashcard_due", "due_review", "resume", "mastery_gap", "safe_starter"):
        line = guided_primary_reason_line_ru(kind)  # type: ignore[arg-type]
        assert line.startswith("Почему сейчас:")
        assert len(line) > 25
