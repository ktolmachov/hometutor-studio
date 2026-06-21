"""Tests for app.ui.ssr_feedback — misroute widget (accept/reject/defer)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.smart_study_router import build_smart_study_recommendation
from app.ui.ssr_feedback import render_ssr_feedback_widget


@pytest.fixture()
def rec():
    return build_smart_study_recommendation(surface="home", flashcard_due_n=1)


def test_render_widget_shows_done_message_if_already_rated(rec):
    done_key = "_ssr_fb_done_test_prefix"
    fake_st = MagicMock()
    fake_st.session_state = {done_key: True}
    fake_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
    fake_st.button.return_value = False

    with patch("app.ui.ssr_feedback.st", fake_st):
        render_ssr_feedback_widget(rec, key_prefix="test_prefix", why_now_text="x")

    fake_st.caption.assert_called()
    assert "Спасибо" in fake_st.caption.call_args[0][0]


def test_render_widget_triggers_accept(rec):
    fake_st = MagicMock()
    fake_st.session_state = {}
    fake_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
    # three buttons in one row — first click is accept
    fake_st.button.side_effect = [True, False, False]

    with patch("app.ui.ssr_feedback.st", fake_st):
        with patch("app.ssr_feedback_collection.record_ssr_misroute_feedback", autospec=True) as p_record:
            render_ssr_feedback_widget(
                rec, key_prefix="home", why_now_text="why", weak_concept="wc"
            )
            p_record.assert_called_once()
    assert fake_st.session_state.get("_ssr_fb_done_home") is True
