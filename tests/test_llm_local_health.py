"""Local LLM health probe — never raises, returns structured dict."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app import llm_local_health


def _mock_transport_factory(handler):
    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Allow tests to register a MockTransport via ``request.node.transport``."""
    real_client = httpx.Client

    def _factory(*args: Any, **kwargs: Any) -> httpx.Client:
        transport = getattr(request.node, "transport", None)
        if transport is not None:
            kwargs.setdefault("transport", transport)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _factory)
    yield


def test_probe_skipped_when_shares_main_base() -> None:
    result = llm_local_health.probe_local_llm(
        "https://openrouter.ai/api/v1", "gpt-4o", shares_main_base=True
    )
    assert result["skipped"] is True
    assert result["reachable"] is False  # explicit: skipped never claims reachable


def test_probe_no_base_url_returns_error() -> None:
    result = llm_local_health.probe_local_llm(None, "model")
    assert result["reachable"] is False
    assert result["error"] == "no_base_url"


def test_probe_reachable_and_model_loaded(request: pytest.FixtureRequest) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path.endswith("/v1/models")
        return httpx.Response(
            200, json={"data": [{"id": "gpt-5-mini"}, {"id": "llama3-8b"}]}
        )

    request.node.transport = _mock_transport_factory(handler)
    result = llm_local_health.probe_local_llm(
        "http://127.0.0.1:8787", "gpt-5-mini", timeout_sec=1.0
    )
    assert result["reachable"] is True
    assert result["model_loaded"] is True
    assert result["models_count"] == 2
    assert result["error"] is None


def test_probe_reachable_but_model_missing(request: pytest.FixtureRequest) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "qwen-7b"}]})

    request.node.transport = _mock_transport_factory(handler)
    result = llm_local_health.probe_local_llm(
        "http://127.0.0.1:8787", "gpt-5-mini", timeout_sec=1.0
    )
    assert result["reachable"] is True
    assert result["model_loaded"] is False


def test_probe_connection_error_returns_unreachable(request: pytest.FixtureRequest) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    request.node.transport = _mock_transport_factory(handler)
    result = llm_local_health.probe_local_llm(
        "http://127.0.0.1:8787", "gpt-5-mini", timeout_sec=1.0
    )
    assert result["reachable"] is False
    assert "ConnectError" in result["error"]
    assert result["latency_ms"] is not None


def test_probe_base_url_with_v1_uses_models_suffix(request: pytest.FixtureRequest) -> None:
    seen: dict[str, str] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        return httpx.Response(200, json={"data": []})

    request.node.transport = _mock_transport_factory(handler)
    llm_local_health.probe_local_llm("http://127.0.0.1:8787/v1", None, timeout_sec=1.0)
    assert seen["path"] == "/v1/models"
