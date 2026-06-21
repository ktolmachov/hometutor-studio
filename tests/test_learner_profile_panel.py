"""US-8.2: бейдж reindex в learner profile panel (без Streamlit)."""

from __future__ import annotations

from app.ui.learner_profile_panel import (
    US_8_2_REINDEX_BADGE_LABEL_RU,
    format_reindex_badge_date_display,
    reindex_profile_badge_parts,
)


def test_reindex_profile_badge_parts_none_without_history_rehydrated() -> None:
    assert reindex_profile_badge_parts(state_migration={}, index_context={}) is None
    assert reindex_profile_badge_parts(state_migration={"index_changed": True}, index_context={}) is None


def test_reindex_profile_badge_parts_when_history_rehydrated() -> None:
    parts = reindex_profile_badge_parts(
        state_migration={
            "history_rehydrated": True,
            "history_rehydrated_row_timestamp": "2026-04-10T12:00:00+00:00",
        },
        index_context={},
    )
    assert parts is not None
    title, date_display = parts
    assert title == US_8_2_REINDEX_BADGE_LABEL_RU
    assert "10.04.2026" in date_display
    assert "UTC" in date_display


def test_reindex_badge_prefers_activated_at_over_row_timestamp() -> None:
    parts = reindex_profile_badge_parts(
        state_migration={
            "history_rehydrated": True,
            "history_rehydrated_row_timestamp": "2026-01-01T00:00:00+00:00",
        },
        index_context={"activated_at": "2026-04-12T15:30:00+00:00"},
    )
    assert parts is not None
    assert "12.04.2026" in parts[1]
    assert "01.01.2026" not in parts[1]


def test_format_reindex_badge_date_display_missing() -> None:
    assert format_reindex_badge_date_display(None) == "не указана"
    assert format_reindex_badge_date_display("") == "не указана"
