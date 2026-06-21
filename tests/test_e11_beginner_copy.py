"""E11-B: начальный копирайт без технических терминов в основном тексте (US-14.2)."""

from __future__ import annotations

import re

from app.ui.continuity_bridge import (
    due_reviews_home_teaser_ru,
    home_continue_priority_lines_ru,
    home_sync_transfer_hint_ru,
    guided_primary_reason_line_ru,
    qa_fast_answer_panel_subtitle_ru,
    qa_fast_answer_question_placeholder_ru,
    qa_fast_answer_top_caption_ru,
    qa_tab_after_answer_debug_intro_caption_ru,
    qa_tab_empty_state_callout_html_ru,
    qa_tab_focus_view_caption_ru,
    qa_tab_sources_column_intro_caption_ru,
    sidebar_fast_filters_caption_ru,
    sidebar_focus_view_help_ru,
    sync_transfer_sidebar_expander_label_ru,
    sync_transfer_sidebar_intro_caption_ru,
)


def _assert_no_forbidden_ru_copy(text: str) -> None:
    """router / retrieval / trace / debug — подстроки; eval — отдельное слово (не часть research и т.п.)."""
    low = text.lower()
    for w in ("router", "retrieval", "trace", "debug"):
        assert w not in low, f"unexpected {w!r} in {text!r}"
    assert not re.search(r"\beval\b", low), f"unexpected eval token in {text!r}"


def test_beginner_copy_helpers_exclude_technical_terms():
    for fn in (
        qa_fast_answer_top_caption_ru,
        qa_fast_answer_panel_subtitle_ru,
        qa_fast_answer_question_placeholder_ru,
        qa_tab_after_answer_debug_intro_caption_ru,
        qa_tab_focus_view_caption_ru,
        qa_tab_sources_column_intro_caption_ru,
        sidebar_fast_filters_caption_ru,
        sidebar_focus_view_help_ru,
        sync_transfer_sidebar_expander_label_ru,
        sync_transfer_sidebar_intro_caption_ru,
        home_sync_transfer_hint_ru,
    ):
        _assert_no_forbidden_ru_copy(fn())

    _assert_no_forbidden_ru_copy(qa_tab_empty_state_callout_html_ru())

    assert due_reviews_home_teaser_ru(2) is not None
    _assert_no_forbidden_ru_copy(due_reviews_home_teaser_ru(2) or "")

    for kwargs in (
        dict(due_n=0, tutor_topic="T", has_last_qa=False, has_reading=False),
        dict(due_n=5, tutor_topic="T", has_last_qa=True, has_reading=True),
        dict(due_n=0, tutor_topic=None, has_last_qa=True, has_reading=False),
        dict(due_n=4, tutor_topic=None, has_last_qa=False, has_reading=False),
        dict(due_n=0, tutor_topic=None, has_last_qa=False, has_reading=True),
        dict(due_n=0, tutor_topic=None, has_last_qa=False, has_reading=False),
    ):
        m, s = home_continue_priority_lines_ru(**kwargs)
        _assert_no_forbidden_ru_copy(m)
        if s:
            _assert_no_forbidden_ru_copy(s)

    for kind in ("flashcard_due", "due_review", "resume", "mastery_gap", "safe_starter"):
        _assert_no_forbidden_ru_copy(guided_primary_reason_line_ru(kind))  # type: ignore[arg-type]
