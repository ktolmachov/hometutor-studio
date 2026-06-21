"""Unit tests for scripts/local_status.py latency budget aggregation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import local_status


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_aggregate_mission_load_percentiles_and_breaches() -> None:
    now = datetime.now(timezone.utc)
    events = [
        {
            "timestamp": _iso(now),
            "surface": "mission_load",
            "actual_ms": 100.0,
            "event": "budget_completed",
        },
        {
            "timestamp": _iso(now),
            "surface": "mission_load",
            "actual_ms": 200.0,
            "event": "surface_breached_soft",
        },
        {
            "timestamp": _iso(now),
            "surface": "mission_load",
            "actual_ms": 400.0,
            "event": "surface_breached_hard",
        },
        {
            "timestamp": _iso(now),
            "surface": "other_surface",
            "actual_ms": 999.0,
            "event": "budget_completed",
        },
    ]
    summary = local_status.aggregate_mission_load(events)
    assert summary["event_count"] == 3
    assert summary["soft_breach_count"] == 1
    assert summary["hard_breach_count"] == 1
    assert summary["p50_ms"] == pytest.approx(200.0)
    assert summary["p95_ms"] == pytest.approx(380.0, rel=0.01)


def test_load_recent_events_caps_window(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=30)
    path = tmp_path / "latency_budget.jsonl"
    rows = [
        {"timestamp": _iso(old), "surface": "mission_load", "actual_ms": 1, "event": "budget_completed"},
        {"timestamp": _iso(now), "surface": "mission_load", "actual_ms": 2, "event": "budget_completed"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    loaded = local_status.load_recent_events(path)
    assert len(loaded) == 1
    assert loaded[0]["actual_ms"] == 2


def test_main_missing_file_exit_zero(capsys: pytest.CaptureFixture[str]) -> None:
    missing = Path("logs/__missing_latency_budget_test__.jsonl")
    assert local_status.main(["--jsonl", str(missing)]) == 0
    captured = capsys.readouterr()
    assert "no events" in captured.out.lower() or "N/A" in captured.out


def test_main_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    now = datetime.now(timezone.utc)
    path = tmp_path / "latency_budget.jsonl"
    row = {
        "timestamp": _iso(now),
        "surface": "mission_load",
        "actual_ms": 50.0,
        "event": "budget_completed",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert local_status.main(["--jsonl", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["event_count"] == 1
    assert payload["p50_ms"] == pytest.approx(50.0)
