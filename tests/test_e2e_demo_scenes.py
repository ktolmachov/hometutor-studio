from __future__ import annotations

from types import SimpleNamespace

from app.ui.e2e_demo_scenes import e2e_cockpit_enabled


def test_e2e_cockpit_enabled_from_flag_when_offline() -> None:
    settings = SimpleNamespace(rag_course_cockpit_v2=False, home_rag_e2e_offline=True)
    assert e2e_cockpit_enabled(settings) is False


def test_e2e_cockpit_enabled_when_config_on() -> None:
    settings = SimpleNamespace(rag_course_cockpit_v2=True, home_rag_e2e_offline=False)
    assert e2e_cockpit_enabled(settings) is True
