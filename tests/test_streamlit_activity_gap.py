"""Парсинг разрыва между сессиями (US-7.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.ui.streamlit_activity import gap_days_from_iso


def test_gap_days_from_iso_none():
    assert gap_days_from_iso(None) is None
    assert gap_days_from_iso("") is None


def test_gap_days_from_iso_reasonable():
    prev = (datetime.now(timezone.utc) - timedelta(days=4, hours=2)).isoformat()
    g = gap_days_from_iso(prev)
    assert g is not None
    assert 3.9 < g < 4.2
