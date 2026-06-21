#!/usr/bin/env python3
"""
Summarize loop metrics gate history from logs/*.json artifacts.

Default pattern:
  logs/loop_metrics_gate*.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_items(pattern: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((ROOT / "logs").glob(pattern)):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        payload["_path"] = str(path.relative_to(ROOT))
        ts = _parse_iso8601(str(payload.get("generated_at_utc") or "")) or datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        )
        payload["_ts"] = ts
        items.append(payload)
    return items


def build_summary(items: list[dict[str, Any]], *, days: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(1, days))
    window = [i for i in items if isinstance(i.get("_ts"), datetime) and i["_ts"] >= cutoff]
    statuses = Counter(str(i.get("status") or "unknown") for i in window)
    fails = [i for i in window if not bool(i.get("passed"))]
    latest = max(window, key=lambda x: x["_ts"], default=None)
    return {
        "gate_kind": "loop_metrics_gate_history",
        "window_days": days,
        "window_total": len(window),
        "pass_count": int(statuses.get("pass", 0)),
        "fail_count": int(statuses.get("fail", 0)),
        "pass_rate": round((int(statuses.get("pass", 0)) / len(window)), 4) if window else 0.0,
        "status_breakdown": dict(statuses),
        "latest": {
            "status": latest.get("status") if latest else None,
            "generated_at_utc": latest.get("_ts").isoformat() if latest else None,
            "path": latest.get("_path") if latest else None,
        },
        "recent_failures": [
            {
                "generated_at_utc": i["_ts"].isoformat(),
                "path": i.get("_path"),
                "exit_code": i.get("exit_code"),
            }
            for i in sorted(fails, key=lambda x: x["_ts"], reverse=True)[:5]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize loop gate history")
    parser.add_argument("--pattern", default="loop_metrics_gate*.json")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json-out", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    parser.add_argument("--min-pass-rate", type=float, default=0.95)
    parser.add_argument("--max-fail-count", type=int, default=0)
    args = parser.parse_args()

    items = _load_items(args.pattern)
    summary = build_summary(items, days=args.days)
    alerts: list[str] = []
    if summary["window_total"] == 0:
        alerts.append("no_gate_snapshots_in_window")
    if float(summary["pass_rate"]) < float(args.min_pass_rate):
        alerts.append("pass_rate_below_threshold")
    if int(summary["fail_count"]) > int(args.max_fail_count):
        alerts.append("fail_count_above_threshold")
    summary["alerts"] = alerts
    summary["enforced_thresholds"] = {
        "min_pass_rate": float(args.min_pass_rate),
        "max_fail_count": int(args.max_fail_count),
    }

    if args.json_out:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Loop metrics gate history")
        print(f"window_days={summary['window_days']} total={summary['window_total']}")
        print(
            f"pass={summary['pass_count']} fail={summary['fail_count']} pass_rate={summary['pass_rate']:.2%}"
        )
        print(f"status_breakdown={summary['status_breakdown']}")
        latest = summary["latest"]
        print(f"latest={latest['status']} at {latest['generated_at_utc']} ({latest['path']})")
        if summary["recent_failures"]:
            print("recent_failures:")
            for row in summary["recent_failures"]:
                print(f"- {row['generated_at_utc']} {row['path']} exit_code={row['exit_code']}")
        if alerts:
            print(f"ALERTS: {', '.join(alerts)}")
    if args.enforce and alerts:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
