#!/usr/bin/env python
"""Summarise SSR explanation quality feedback from JSONL logs.

Usage:
    python scripts/ssr_feedback_summary.py              # all files in default dir
    python scripts/ssr_feedback_summary.py --date 2026-05-13
    python scripts/ssr_feedback_summary.py --last 7     # last N days
    python scripts/ssr_feedback_summary.py --dir path/to/logs/ssr_feedback
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


def _default_log_dir() -> Path:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from app.config import get_settings

        s = get_settings()
        base = getattr(s, "base_dir", None) or Path(".")
        return Path(base) / "logs" / "ssr_feedback"
    except Exception:  # noqa: BLE001
        return Path("logs") / "ssr_feedback"


def _load_rows(log_dir: Path, target_dates: list[str] | None) -> list[dict]:
    rows: list[dict] = []
    if not log_dir.exists():
        return rows
    for f in sorted(log_dir.glob("ssr_feedback_*.jsonl")):
        if target_dates is not None:
            date_part = f.stem.replace("ssr_feedback_", "")
            if date_part not in target_dates:
                continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def _summarise(rows: list[dict]) -> None:
    if not rows:
        print("No feedback records found.")
        return

    total = len(rows)
    up = sum(1 for r in rows if r.get("rating") == 1)
    down = total - up
    pct = round(up / total * 100, 1) if total else 0

    print(f"\n{'─' * 52}")
    print(f"  SSR Explanation Feedback — {total} ratings")
    print(f"{'─' * 52}")
    print(f"  👍 Полезно:      {up:>4}  ({pct}%)")
    print(f"  👎 Не очень:     {down:>4}  ({100 - pct}%)")
    print()

    # By hint_kind
    by_hint: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for r in rows:
        hk = str(r.get("hint_kind") or "unknown")
        if r.get("rating") == 1:
            by_hint[hk]["up"] += 1
        else:
            by_hint[hk]["down"] += 1

    print("  По hint_kind:")
    for hk, counts in sorted(by_hint.items()):
        t = counts["up"] + counts["down"]
        p = round(counts["up"] / t * 100, 1) if t else 0
        print(f"    {hk:<32} 👍 {counts['up']}/{t} ({p}%)")

    # By primary_nav
    by_nav: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for r in rows:
        nav = str(r.get("primary_nav") or "unknown")
        if r.get("rating") == 1:
            by_nav[nav]["up"] += 1
        else:
            by_nav[nav]["down"] += 1

    print("\n  По primary_nav:")
    for nav, counts in sorted(by_nav.items()):
        t = counts["up"] + counts["down"]
        p = round(counts["up"] / t * 100, 1) if t else 0
        print(f"    {nav:<32} 👍 {counts['up']}/{t} ({p}%)")

    # Explanation length correlation
    up_lens = [r.get("why_now_len", 0) for r in rows if r.get("rating") == 1]
    down_lens = [r.get("why_now_len", 0) for r in rows if r.get("rating") != 1]
    if up_lens and down_lens:
        avg_up = round(sum(up_lens) / len(up_lens))
        avg_down = round(sum(down_lens) / len(down_lens))
        print(f"\n  Средняя длина объяснения: 👍 {avg_up} символов  👎 {avg_down} символов")

    print(f"{'─' * 52}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SSR feedback summary")
    parser.add_argument("--date", help="Specific date YYYY-MM-DD")
    parser.add_argument("--last", type=int, help="Last N days")
    parser.add_argument("--dir", help="Override log directory path")
    args = parser.parse_args()

    log_dir = Path(args.dir) if args.dir else _default_log_dir()

    target_dates: list[str] | None = None
    if args.date:
        target_dates = [args.date]
    elif args.last:
        today = date.today()
        target_dates = [(today - timedelta(days=i)).isoformat() for i in range(args.last)]

    rows = _load_rows(log_dir, target_dates)
    _summarise(rows)


if __name__ == "__main__":
    main()
