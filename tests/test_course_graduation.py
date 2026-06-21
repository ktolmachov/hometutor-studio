"""Регрессия UX graduation + восстановление `app/course_graduation.py` (чистые хелперы)."""

from __future__ import annotations

from unittest.mock import patch

from app import course_graduation as cg
from app.ui.graduation_overlay import graduation_headline, log_concept_graduation_stub


def test_graduation_headline_fallback_and_trim():
    assert "Демо" in graduation_headline("  Демо  ")
    assert "концепт" in graduation_headline("")


@patch("app.ui.graduation_overlay.record_course_workflow_event")
def test_log_concept_graduation_stub_writes_event(mock_record):
    log_concept_graduation_stub({"k": "v"}, concept_title="  X  ")
    mock_record.assert_called_once_with(
        "concept_graduation_event",
        {"k": "v"},
        payload={"stub": True, "concept_title": "X"},
    )


def test_delight_data_mode_reads_settings(monkeypatch):
    fake = type("S", (), {"home_rag_data_mode": "demo"})()
    monkeypatch.setattr(cg, "get_settings", lambda: fake)
    assert cg.delight_data_mode_is_demo() is True


def test_primary_profile_label_reads_settings(monkeypatch):
    fake = type("S", (), {"home_rag_local_profile": "local_strict"})()
    monkeypatch.setattr(cg, "get_settings", lambda: fake)
    assert cg.primary_profile_label() == "local_strict"


def test_delight_privacy_notice_covers_profiles():
    text = cg.delight_privacy_notice(demo=False, profile_label="cloud_fast")
    assert "cloud" in text.lower()
