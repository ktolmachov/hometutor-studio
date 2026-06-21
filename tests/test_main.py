from __future__ import annotations

from pathlib import Path


def test_main_wires_offline_and_config_env_banners() -> None:
    main_py = Path("app/ui/main.py").read_text(encoding="utf-8")

    assert "render_offline_banner as _render_offline_banner" in main_py
    assert "render_config_env_banner as _render_config_env_banner" in main_py
    assert "_render_offline_banner()" in main_py
    assert "_render_config_env_banner()" in main_py


def test_main_initializes_otel_for_direct_tutor_queries() -> None:
    main_py = Path("app/ui/main.py").read_text(encoding="utf-8")

    assert "from app.otel_tracing import init_otel_if_enabled" in main_py
    assert "init_otel_if_enabled()" in main_py


def test_main_has_no_traceback_copy_for_env_flow() -> None:
    main_py = Path("app/ui/main.py").read_text(encoding="utf-8").lower()
    assert "traceback" not in main_py
