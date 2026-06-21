"""Banner status mapping from /ui/bootstrap llm_local payload."""

from __future__ import annotations

from app.ui.llm_local_banner import _build_status


def test_no_payload_returns_none() -> None:
    assert _build_status(None) is None
    assert _build_status({}) is None


def test_skipped_payload_returns_none() -> None:
    """Cloud provider: probe was skipped → banner must not appear."""
    assert (
        _build_status(
            {"skipped": True, "reason": "ssr_shares_main_base", "reachable": False}
        )
        is None
    )


def test_reachable_and_model_loaded_returns_none() -> None:
    payload = {
        "reachable": True,
        "model_loaded": True,
        "base_url": "http://127.0.0.1:8787",
        "model": "gpt-5-mini",
    }
    assert _build_status(payload) is None


def test_unreachable_returns_warning() -> None:
    payload = {
        "reachable": False,
        "base_url": "http://127.0.0.1:8787",
        "model": "gpt-5-mini",
        "error": "ConnectError: Connection refused",
    }
    status = _build_status(payload)
    assert status is not None
    assert status["kind"] == "warning"
    assert "127.0.0.1:8787" in status["detail"]
    assert "gpt-5-mini" in status["detail"]
    assert "ConnectError" in status["detail"]


def test_reachable_but_model_missing_returns_info() -> None:
    payload = {
        "reachable": True,
        "model_loaded": False,
        "base_url": "http://127.0.0.1:8787",
        "model": "gpt-5-mini",
    }
    status = _build_status(payload)
    assert status is not None
    assert status["kind"] == "info"
    assert "gpt-5-mini" in status["detail"]
    assert "SSR_LLM_MODEL" in status["detail"]


def test_missing_base_url_and_model_uses_dashes() -> None:
    """Defensive: should not crash if probe came back without base/model."""
    status = _build_status({"reachable": False, "error": "no_base_url"})
    assert status is not None
    assert status["base_url"] == "—"
    assert status["model"] == "—"
