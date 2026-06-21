#!/usr/bin/env python3
"""
Localhost latency budget snapshot (Phase 7 Move 2).

Reads ``logs/latency_budget.jsonl``, aggregates rolling p50/p95 and breach counts
for ``mission_load``. Graceful empty output when the log file is missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSONL = Path("logs/latency_budget.jsonl")
MAX_EVENTS = 200
WINDOW_HOURS = 24


def _parse_timestamp(raw: str) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def load_recent_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    rows: list[tuple[datetime, dict[str, Any]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        ts = _parse_timestamp(str(row.get("timestamp") or ""))
        if ts is None or ts < cutoff:
            continue
        rows.append((ts, row))
    rows.sort(key=lambda item: item[0])
    recent = [row for _, row in rows[-MAX_EVENTS:]]
    return recent


def aggregate_mission_load(events: list[dict[str, Any]]) -> dict[str, Any]:
    mission = [row for row in events if row.get("surface") == "mission_load"]
    actual_values = [
        float(row["actual_ms"])
        for row in mission
        if isinstance(row.get("actual_ms"), (int, float))
    ]
    soft_breaches = sum(1 for row in mission if row.get("event") == "surface_breached_soft")
    hard_breaches = sum(1 for row in mission if row.get("event") == "surface_breached_hard")
    return {
        "surface": "mission_load",
        "event_count": len(mission),
        "p50_ms": _percentile(actual_values, 0.50),
        "p95_ms": _percentile(actual_values, 0.95),
        "soft_breach_count": soft_breaches,
        "hard_breach_count": hard_breaches,
    }


def format_summary(summary: dict[str, Any]) -> str:
    if summary["event_count"] == 0:
        return (
            "Latency budget status\n"
            "=====================\n"
            "mission_load: no events in rolling window (last 200 events / 24 h)\n"
            "p50_ms: N/A\n"
            "p95_ms: N/A\n"
            "soft_breach_count: 0\n"
            "hard_breach_count: 0\n"
        )

    def _fmt_ms(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.1f}"

    return (
        "Latency budget status\n"
        "=====================\n"
        f"mission_load events: {summary['event_count']}\n"
        f"p50_ms: {_fmt_ms(summary['p50_ms'])}\n"
        f"p95_ms: {_fmt_ms(summary['p95_ms'])}\n"
        f"soft_breach_count: {summary['soft_breach_count']}\n"
        f"hard_breach_count: {summary['hard_breach_count']}\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jsonl",
        default=str(DEFAULT_JSONL),
        help="Path to latency_budget.jsonl (default: logs/latency_budget.jsonl).",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.jsonl)
    events = load_recent_events(path)
    summary = aggregate_mission_load(events)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_summary(summary), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
