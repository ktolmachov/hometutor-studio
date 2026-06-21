#!/usr/bin/env python3
"""Aggregate demo recorder perf logs from doc/screenshots/<RUN>."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


DEFAULT_SCREENSHOTS = Path("doc/screenshots")


def _latest_run_dir(root: Path) -> Path:
    if not root.exists():
        return root
    runs = sorted(p for p in root.iterdir() if p.is_dir())
    return runs[-1] if runs else root


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_shots(screenshots_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario_dir in sorted(screenshots_dir.glob("scenario_*")):
        perf = scenario_dir / "perf.jsonl"
        if perf.exists():
            for line in perf.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
            continue
        meta_path = scenario_dir / "meta.json"
        if not meta_path.exists():
            continue
        meta = _read_json(meta_path)
        for shot in meta.get("shots") or []:
            rows.append(
                {
                    "scenario_id": meta.get("scenario_id") or scenario_dir.name,
                    "step": shot.get("step"),
                    "slug": shot.get("slug"),
                    "file": shot.get("file"),
                    "timings_ms": shot.get("timings_ms") or {},
                }
            )
    return rows


def _fmt_ms(value: float) -> str:
    return f"{value / 1000:.2f}s"


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(0, min(len(values) - 1, int((len(values) * 0.95 + 0.999999) - 1)))
    return float(values[index])


def _build_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        scenario_id = str(row.get("scenario_id") or "unknown")
        by_scenario.setdefault(scenario_id, []).append(row)

    per_scenario: dict[str, dict[str, Any]] = {}
    all_steps: list[dict[str, Any]] = []
    for scenario_id, scenario_rows in sorted(by_scenario.items()):
        total_values = [float((r.get("timings_ms") or {}).get("total") or 0) for r in scenario_rows]
        shot_values = [float((r.get("timings_ms") or {}).get("screenshot") or 0) for r in scenario_rows]
        per_scenario[scenario_id] = {
            "total_ms": int(sum(total_values)),
            "p95_shot_ms": int(_p95(shot_values)),
        }
        for r in scenario_rows:
            t = r.get("timings_ms") or {}
            all_steps.append(
                {
                    "scenario_id": scenario_id,
                    "step": int(r.get("step") or 0),
                    "slug": str(r.get("slug") or ""),
                    "total_ms": int(float(t.get("total") or 0)),
                }
            )
    top3 = sorted(all_steps, key=lambda item: item["total_ms"], reverse=True)[:3]
    return {
        "per_scenario": per_scenario,
        "top3_slowest_steps": top3,
    }


def _print_summary(rows: list[dict[str, Any]], top: int) -> None:
    phases = ("wait", "streamlit_ready", "screenshot", "total")
    print(f"[demo-perf] shots: {len(rows)}")
    for phase in phases:
        values = [
            float((row.get("timings_ms") or {}).get(phase) or 0)
            for row in rows
        ]
        if not values:
            continue
        print(
            f"[demo-perf] {phase:16s} sum={_fmt_ms(sum(values))} "
            f"avg={_fmt_ms(mean(values))} max={_fmt_ms(max(values))}"
        )
    print()
    print("scenario     step  total   wait    ready   shot    slug")
    print("-----------  ----  ------  ------  ------  ------  -------------------------")
    slowest = sorted(
        rows,
        key=lambda row: float((row.get("timings_ms") or {}).get("total") or 0),
        reverse=True,
    )[:top]
    for row in slowest:
        t = row.get("timings_ms") or {}
        print(
            f"{str(row.get('scenario_id') or ''):11s}  "
            f"{int(row.get('step') or 0):>4d}  "
            f"{_fmt_ms(float(t.get('total') or 0)):>6s}  "
            f"{_fmt_ms(float(t.get('wait') or 0)):>6s}  "
            f"{_fmt_ms(float(t.get('streamlit_ready') or 0)):>6s}  "
            f"{_fmt_ms(float(t.get('screenshot') or 0)):>6s}  "
            f"{str(row.get('slug') or '')[:25]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--screenshots-dir",
        type=Path,
        default=DEFAULT_SCREENSHOTS,
        help="Run directory or doc/screenshots root.",
    )
    parser.add_argument("--top", type=int, default=15, help="Slowest shots to show.")
    parser.add_argument("--baseline", type=Path, default=None, help="Path to demo baseline JSON.")
    parser.add_argument("--update", action="store_true", help="Write baseline JSON to --baseline.")
    args = parser.parse_args()

    screenshots_dir = args.screenshots_dir
    if screenshots_dir == DEFAULT_SCREENSHOTS:
        screenshots_dir = _latest_run_dir(screenshots_dir)
    rows = _iter_shots(screenshots_dir)
    if not rows:
        print(f"[demo-perf] no perf rows found in {screenshots_dir}")
        return 1
    _print_summary(rows, max(1, int(args.top)))
    if args.baseline:
        baseline_data = _build_baseline(rows)
        if args.update:
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            args.baseline.write_text(
                json.dumps(baseline_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"[demo-perf] baseline updated: {args.baseline}")
        else:
            print(json.dumps(baseline_data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
