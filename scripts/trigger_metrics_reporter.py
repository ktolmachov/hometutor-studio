#!/usr/bin/env python3
"""
trigger_metrics_reporter.py — Observability dashboard for trigger_metrics.jsonl

Usage:
    python scripts/trigger_metrics_reporter.py
    python scripts/trigger_metrics_reporter.py --summary
    python scripts/trigger_metrics_reporter.py --last 20
    python scripts/trigger_metrics_reporter.py --strategy direct_cursor
    python scripts/trigger_metrics_reporter.py --json

Reads: archive/team_artifacts/_metrics/trigger_metrics.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Force UTF-8 output on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
DEFAULT_METRICS_PATH = ROOT / "archive" / "team_artifacts" / "_metrics" / "trigger_metrics.jsonl"

# ── ANSI colours ──────────────────────────────────────────────────────────────

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"
DIM = "\x1b[2m"
SEP = "=" * 80
HR = "-" * 80


def _color(text: str, *codes: str) -> str:
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + str(text) + RESET


def _status_color(status: str) -> str:
    if status == "finished":
        return _color(status, GREEN)
    if status == "error":
        return _color(status, RED)
    return _color(status, YELLOW)


# ── Data loading ──────────────────────────────────────────────────────────────

def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def orchestrator_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("event") == "trigger_orchestrator"]


# ── Aggregation ───────────────────────────────────────────────────────────────

def aggregate_by_strategy(rows: list[dict]) -> dict[str, dict]:
    agg: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "success": 0, "error": 0,
        "total_ms": 0, "risk_scores": [],
    })
    for r in rows:
        s = r.get("strategy", "unknown")
        agg[s]["total"] += 1
        if r.get("overall_status") == "finished":
            agg[s]["success"] += 1
        else:
            agg[s]["error"] += 1
        agg[s]["total_ms"] += r.get("overall_duration_ms", 0)
        score = r.get("risk_score")
        if score is not None:
            agg[s]["risk_scores"].append(score)
    return dict(agg)


def aggregate_by_trigger(rows: list[dict]) -> dict[str, dict]:
    agg: dict[str, dict] = defaultdict(lambda: {"total": 0, "success": 0, "error": 0, "total_ms": 0})
    for r in rows:
        for step in r.get("steps", []):
            t = step.get("trigger", "unknown")
            agg[t]["total"] += 1
            if step.get("status") == "finished":
                agg[t]["success"] += 1
            else:
                agg[t]["error"] += 1
            agg[t]["total_ms"] += step.get("duration_ms", 0)
    return dict(agg)


# ── Display helpers ───────────────────────────────────────────────────────────

def _rate(success: int, total: int) -> str:
    if total == 0:
        return "n/a"
    pct = success / total * 100
    color = GREEN if pct >= 70 else YELLOW if pct >= 40 else RED
    return _color(f"{pct:.0f}%", color)


def _ms(ms: int) -> str:
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _avg_ms(total_ms: int, n: int) -> str:
    if n == 0:
        return "n/a"
    return _ms(total_ms // n)


# ── Print sections ────────────────────────────────────────────────────────────

def print_recent_table(rows: list[dict], limit: int) -> None:
    subset = rows[-limit:]
    print(_color(f"\n{HR}", DIM))
    print(_color(f"  Recent runs ({len(subset)} of {len(rows)} total)\n", BOLD))
    header = f"  {'Timestamp':<22} {'Strategy':<26} {'Risk':<7} {'Score':<6} {'Status':<12} {'Duration'}"
    print(_color(header, BOLD + CYAN))
    print(_color("  " + "-" * 78, DIM))
    for r in subset:
        ts = str(r.get("timestamp", ""))[:19]
        strategy = r.get("strategy", "?")[:25]
        risk = r.get("risk_level", "?")
        score = str(r.get("risk_score", "?"))
        status = r.get("overall_status", "?")
        duration = _ms(r.get("overall_duration_ms", 0))
        print(f"  {ts:<22} {strategy:<26} {risk:<7} {score:<6} {_status_color(status):<23} {duration}")
    print()


def print_strategy_summary(by_strategy: dict[str, dict]) -> None:
    print(_color(f"\n{HR}", DIM))
    print(_color("  Strategy Success Rates\n", BOLD))
    header = f"  {'Strategy':<28} {'Total':<7} {'Success':<9} {'Error':<7} {'Rate':<8} {'Avg Duration'}"
    print(_color(header, BOLD + CYAN))
    print(_color("  " + "-" * 78, DIM))
    for strategy, d in sorted(by_strategy.items()):
        total = d["total"]
        success = d["success"]
        error = d["error"]
        rate = _rate(success, total)
        avg = _avg_ms(d["total_ms"], total)
        risk_avg = (
            f"(avg risk score: {sum(d['risk_scores'])/len(d['risk_scores']):.1f})"
            if d["risk_scores"] else ""
        )
        print(f"  {strategy:<28} {total:<7} {success:<9} {error:<7} {rate:<20} {avg}  {_color(risk_avg, DIM)}")
    print()


def print_trigger_summary(by_trigger: dict[str, dict]) -> None:
    print(_color(f"\n{HR}", DIM))
    print(_color("  Per-Trigger Step Results\n", BOLD))
    header = f"  {'Trigger':<20} {'Total':<7} {'Success':<9} {'Error':<7} {'Rate':<8} {'Avg Duration'}"
    print(_color(header, BOLD + CYAN))
    print(_color("  " + "-" * 78, DIM))
    for trigger, d in sorted(by_trigger.items()):
        total = d["total"]
        success = d["success"]
        error = d["error"]
        rate = _rate(success, total)
        avg = _avg_ms(d["total_ms"], total)
        print(f"  {trigger:<20} {total:<7} {success:<9} {error:<7} {rate:<20} {avg}")
    print()


def print_adaptive_status(rows: list[dict], window: int = 10) -> None:
    recent = rows[-window:]
    print(_color(f"\n{HR}", DIM))
    print(_color(f"  Adaptive Status (last {window} orchestrator runs)\n", BOLD))
    for trigger in ["cursor", "deepseek_tui"]:
        relevant = [
            r for r in recent
            if any(s.get("trigger") == trigger for s in r.get("steps", []))
        ]
        if not relevant:
            print(f"  {trigger}: no history")
            continue
        successes = sum(1 for r in relevant if r.get("overall_status") == "finished")
        rate = successes / len(relevant)
        rate_str = _rate(successes, len(relevant))
        warn = ""
        if rate < 0.4:
            warn = _color(" <- DEMOTED by adaptive logic", RED + BOLD)
        print(f"  {trigger}: {rate_str} ({successes}/{len(relevant)}){warn}")
    print()


def print_risk_signal_breakdown(rows: list[dict], limit: int = 5) -> None:
    rows_with_signals = [r for r in rows if r.get("risk_signals")]
    if not rows_with_signals:
        return
    print(_color(f"\n{HR}", DIM))
    print(_color(f"  Risk Signal Breakdown (last {limit} runs with signals)\n", BOLD))
    for r in rows_with_signals[-limit:]:
        ts = str(r.get("timestamp", ""))[:19]
        level = r.get("risk_level", "?")
        score = r.get("risk_score", "?")
        sigs = r.get("risk_signals", {})
        active = [k for k, v in sigs.items() if v and k != "explicit_marker" and k != "write_set_lines"]
        explicit = "[explicit_marker]" if sigs.get("explicit_marker") else ""
        ws = f"write_set_lines={sigs.get('write_set_lines', 0)}" if sigs.get("write_set_lines", 0) > 0 else ""
        signal_str = ", ".join(filter(None, [explicit, ws] + active))
        print(f"  {ts}  {_color(level, BOLD):<20} score={score}  signals: {signal_str or 'none'}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="trigger_metrics_reporter.py — Observability dashboard for trigger orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS_PATH),
                        help="Path to trigger_metrics.jsonl")
    parser.add_argument("--last", type=int, default=20,
                        help="Number of recent rows to show (default: 20)")
    parser.add_argument("--summary", action="store_true",
                        help="Show aggregated summary only (no table)")
    parser.add_argument("--strategy", help="Filter to specific strategy name")
    parser.add_argument("--json", action="store_true",
                        help="Output aggregated data as JSON instead of table")
    parser.add_argument("--window", type=int, default=10,
                        help="Window size for adaptive status (default: 10)")
    args = parser.parse_args()

    metrics_path = Path(args.metrics)
    all_rows = load_rows(metrics_path)
    orch_rows = orchestrator_rows(all_rows)

    if not orch_rows:
        print(f"No orchestrator metrics found in: {metrics_path}")
        print("Run a workflow with --trigger-cmd to generate metrics.")
        sys.exit(0)

    if args.strategy:
        orch_rows = [r for r in orch_rows if r.get("strategy") == args.strategy]
        if not orch_rows:
            print(f"No rows found for strategy: {args.strategy}")
            sys.exit(0)

    by_strategy = aggregate_by_strategy(orch_rows)
    by_trigger = aggregate_by_trigger(orch_rows)

    if args.json:
        print(json.dumps({
            "total_runs": len(orch_rows),
            "by_strategy": by_strategy,
            "by_trigger": by_trigger,
        }, indent=2))
        return

    print(_color(f"\n{'═' * 80}", BOLD))
    print(_color("  Trigger Orchestrator - Metrics Report", BOLD + CYAN))
    print(_color(f"  Source: {metrics_path}", DIM))
    print(_color(f"  Total orchestrator events: {len(orch_rows)}", BOLD))
    print(_color(f"{'═' * 80}", BOLD))

    if not args.summary:
        print_recent_table(orch_rows, args.last)

    print_strategy_summary(by_strategy)
    print_trigger_summary(by_trigger)
    print_adaptive_status(orch_rows, args.window)
    print_risk_signal_breakdown(orch_rows)


if __name__ == "__main__":
    main()
