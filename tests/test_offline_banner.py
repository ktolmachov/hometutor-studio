from __future__ import annotations

from types import SimpleNamespace

from app.ui import offline_banner


def test_render_offline_banner_shows_missing_env_warning(monkeypatch) -> None:
    messages: list[str] = []

    monkeypatch.setattr(
        offline_banner,
        "st",
        SimpleNamespace(
            warning=lambda msg: messages.append(str(msg)),
            error=lambda _msg: None,
        ),
    )

    class _Settings:
        openai_api_key = ""

    monkeypatch.setattr(
        "app.ui.offline_banner.get_settings",
        lambda: _Settings(),
        raising=False,
    )
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: _Settings(),
        raising=False,
    )
    monkeypatch.setattr(
        "app.offline_service.get_offline_status",
        lambda: {"offline_mode": False, "llm_reachable": True},
    )

    offline_banner.render_offline_banner()

    assert any("OPENAI_API_KEY" in msg for msg in messages)


def test_render_offline_banner_does_not_crash_on_status_exception(monkeypatch) -> None:
    messages: list[str] = []

    monkeypatch.setattr(
        offline_banner,
        "st",
        SimpleNamespace(
            warning=lambda msg: messages.append(str(msg)),
            error=lambda _msg: None,
        ),
    )
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: SimpleNamespace(openai_api_key="sk-test"),
        raising=False,
    )

    def _boom():
        raise RuntimeError("offline probe failed")

    monkeypatch.setattr("app.offline_service.get_offline_status", _boom)

    offline_banner.render_offline_banner()

    assert messages == []
