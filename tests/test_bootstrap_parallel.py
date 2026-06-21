"""Bootstrap parallelisation: verify response shape and that tasks run concurrently."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

import pytest


def _make_slow(delay: float, value: Any):
    def _fn():
        time.sleep(delay)
        return value

    return _fn


def test_get_ui_bootstrap_returns_required_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bootstrap must always return the four structural keys (even on errors)."""
    from app.api_services import get_ui_bootstrap

    monkeypatch.setattr(
        "app.api_services.get_index_stats",
        lambda: {"doc_count": 10},
    )
    monkeypatch.setattr(
        "app.api_services._bootstrap_readiness",
        lambda: {"sources": 2},
    )
    monkeypatch.setattr(
        "app.api_services._probe_local_llm_for_bootstrap",
        lambda: {"reachable": False, "skipped": True},
    )
    monkeypatch.setattr(
        "app.api_services._bootstrap_kb_and_overview",
        lambda: {"overview": {"topics": 3}},
    )

    result = get_ui_bootstrap()
    assert "index_stats" in result
    assert "kb_overview" in result
    assert "source_readiness" in result
    assert "llm_local" in result


def test_get_ui_bootstrap_parallel_faster_than_sequential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Four 0.15-second tasks in parallel should finish well under 0.5s total
    (sequential would be ≥0.60s). Gives 3× headroom for slow CI."""
    from app.api_services import get_ui_bootstrap

    delay = 0.15
    monkeypatch.setattr("app.api_services.get_index_stats", _make_slow(delay, {"doc_count": 1}))
    monkeypatch.setattr("app.api_services._bootstrap_readiness", _make_slow(delay, {}))
    monkeypatch.setattr(
        "app.api_services._probe_local_llm_for_bootstrap",
        _make_slow(delay, {"reachable": False}),
    )
    monkeypatch.setattr(
        "app.api_services._bootstrap_kb_and_overview",
        _make_slow(delay, {"overview": None}),
    )

    start = time.monotonic()
    get_ui_bootstrap()
    elapsed = time.monotonic() - start

    sequential_floor = delay * 4  # 0.60s
    assert elapsed < sequential_floor, (
        f"Bootstrap took {elapsed:.3f}s — expected parallel (<{sequential_floor:.2f}s), "
        "likely running sequentially."
    )


def test_bootstrap_kb_skips_init_when_services_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When base services aren't warm, _bootstrap_kb_and_overview must return
    {overview: None} immediately without calling get_base_services() at all.
    This prevents a cold-start 13-second block on the first user request."""
    import app.api_services as svc

    calls: list[str] = []

    monkeypatch.setattr(svc, "is_base_services_ready", lambda: False)
    monkeypatch.setattr(svc, "get_base_services", lambda: calls.append("get_base_services") or {})
    monkeypatch.setattr(svc, "get_kb_overview", lambda **_: calls.append("get_kb_overview") or {})

    result = svc._bootstrap_kb_and_overview()

    assert result == {"overview": None}, f"Unexpected result: {result}"
    assert calls == [], f"Should not call any service when not ready; called: {calls}"


def test_bootstrap_kb_returns_overview_when_services_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When services are warm, _bootstrap_kb_and_overview should call through normally."""
    import app.api_services as svc

    monkeypatch.setattr(svc, "is_base_services_ready", lambda: True)
    monkeypatch.setattr("app.knowledge_catalog._catalog_cache_get", lambda: {"topics": []})
    monkeypatch.setattr(svc, "get_kb_overview", lambda *, catalog=None, services=None: {"topics": 5})

    result = svc._bootstrap_kb_and_overview()

    assert result == {"overview": {"topics": 5}}


def test_get_ui_bootstrap_survives_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing subtask must not crash bootstrap; other fields must still be present."""
    from app.api_services import get_ui_bootstrap

    def _raise():
        raise RuntimeError("Chroma exploded")

    monkeypatch.setattr("app.api_services.get_index_stats", lambda: {"doc_count": 5})
    monkeypatch.setattr("app.api_services._bootstrap_readiness", lambda: None)
    monkeypatch.setattr(
        "app.api_services._probe_local_llm_for_bootstrap",
        lambda: {"reachable": False},
    )
    monkeypatch.setattr("app.api_services._bootstrap_kb_and_overview", _raise)

    result = get_ui_bootstrap()
    assert result["index_stats"] == {"doc_count": 5}
    # kb_overview may be None or absent — but bootstrap must not 500.
    assert "kb_overview" in result
