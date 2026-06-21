"""Регрессии для home hub E13: badge дедлайнов, слоты режимов, порядок строк (US-19.5)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ui import home_hub as hh
from app.ui.helpers import home_mode_preview_lines


class _CM:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def stub_streamlit(monkeypatch):
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.container.side_effect = lambda *a, **k: _CM()
    cols_a = (_CM(), _CM(), _CM())
    cols_b = (_CM(), _CM(), _CM())
    mock_st.columns.side_effect = [cols_a, cols_b]
    monkeypatch.setattr(hh, "st", mock_st)
    return mock_st


def test_mode_card_includes_due_badge_when_positive(stub_streamlit):
    hh._mode_card("🎴", "Flashcards", "Desc", "Flashcards", "k", "Go", badge=7, mode_slot="flashcards")
    html = stub_streamlit.markdown.call_args_list[0][0][0]
    assert 'class="mode-badge"' in html
    assert ">7</div>" in html
    assert 'class="mode-card"' in html


def test_mode_card_hides_badge_when_zero(stub_streamlit):
    hh._mode_card("🎴", "Flashcards", "Desc", "Flashcards", "k", "Go", badge=0, mode_slot="flashcards")
    html = stub_streamlit.markdown.call_args_list[0][0][0]
    assert "mode-badge" not in html


def test_mode_card_includes_best_for_and_preview(stub_streamlit):
    hh._mode_card(
        "🎓",
        "T",
        "D",
        "Чат с тьютором",
        "k",
        "C",
        mode_slot="tutor",
        preview_lines=home_mode_preview_lines("tutor"),
    )
    html = stub_streamlit.markdown.call_args_list[0][0][0]
    assert 'class="mode-best-for"' in html
    assert 'class="mode-preview-details"' in html


def test_render_primary_mode_slot_flashcards_forwards_due_badge():
    captured: dict = {}

    def _capture(*_a, **kw):
        captured.update(kw)

    with patch.object(hh, "_mode_card", side_effect=_capture):
        hh._render_primary_mode_slot("flashcards", fc_due=15)
    assert captured.get("badge") == 15
    assert captured.get("effort_hints") is not None


def test_render_mode_selector_delegates_to_mission_control(stub_streamlit):
    stub_streamlit.session_state = {"_ui_index_stats_tab": {"status": "ok"}}
    with patch("app.ui.mission_control.render_mission_control") as render_mission_control:
        hh.render_mode_selector()
    render_mission_control.assert_called_once_with({"status": "ok"})


def test_ui_theme_preserves_mode_card_focus_visible_summary():
    """Регрессия: видимый фокус клавиатуры на превью режима (не только hover-карточки)."""
    root = Path(__file__).resolve().parents[1]
    css = (root / "app" / "ui_theme.css").read_text(encoding="utf-8")
    assert ".mode-preview-details summary:focus-visible" in css
    assert ".mode-card:hover" in css
