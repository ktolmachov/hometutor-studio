"""Тесты graduation overlay (E30 B1 stub)."""

from unittest.mock import patch

from app.ui.graduation_overlay import graduation_headline, log_concept_graduation_stub


def test_graduation_headline_default():
    assert "концепт" in graduation_headline("")


def test_graduation_headline_custom():
    assert "RAG" in graduation_headline("RAG")


def test_log_concept_graduation_stub_invokes_metrics():
    with patch("app.ui.graduation_overlay.record_course_workflow_event") as m:
        log_concept_graduation_stub({"active": True, "folder_rel": "ml"}, concept_title="X")
        m.assert_called_once()
        args, kwargs = m.call_args
        assert args[0] == "concept_graduation_event"
        assert kwargs["payload"]["stub"] is True
