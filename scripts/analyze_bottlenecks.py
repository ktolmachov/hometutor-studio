#!/usr/bin/env python3
"""
analyze_bottlenecks.py — Pipeline bottleneck analyzer.

Reads timing JSON files from archive/team_artifacts/_timing/, aggregates
per-phase statistics, detects outliers and regressions, and produces a
markdown or JSON report.

Usage:
    python scripts/analyze_bottlenecks.py [--last N] [--threshold-sec X] [--format md|json] [--out PATH]
    python scripts/analyze_bottlenecks.py --last 5 --format md
    python scripts/analyze_bottlenecks.py --last 20 --format json --emit-prompt

Exit codes:
    0 — report generated OK
    1 — no timing data found
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_TIMING_DIR = ROOT / "archive" / "team_artifacts" / "_timing"
_BOTTLENECK_REPORT_DIR = ROOT / "logs" / "bottlenecks"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PhaseRecord:
    name: str
    seconds: float
    rc: int | None
    run_id: str
    script_name: str


@dataclass
class Stats:
    phase: str
    count: int
    total: float
    mean: float
    median: float
    p95: float
    max: float
    stddev: float
    category: str = "other"


@dataclass
class Outlier:
    phase: str
    reason: str
    value: float
    threshold: float


@dataclass
class Regression:
    phase: str
    slope: float  # seconds per run
    recent_mean: float


@dataclass
class Run:
    run_id: str
    script_name: str
    total: float
    phases: list[PhaseRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def _load_runs(timing_dir: Path, last_n: int = 20) -> list[Run]:
    """Load the most recent `last_n` runs from the timing directory."""
    if not timing_dir.exists():
        return []
    files = sorted(timing_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    # Group files by run_id (prefix before __)
    runs_by_id: dict[str, list[Path]] = {}
    for f in files:
        parts = f.stem.split("__", 1)
        run_id = parts[0]
        runs_by_id.setdefault(run_id, []).append(f)

    # Sort run_ids by the mtime of their newest file
    sorted_run_ids = sorted(
        runs_by_id.keys(),
        key=lambda rid: max(f.stat().st_mtime for f in runs_by_id[rid]),
    )
    selected = sorted_run_ids[-last_n:]

    runs: list[Run] = []
    for run_id in selected:
        for f in runs_by_id[run_id]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            script_name = data.get("script_name", f.stem.split("__", 1)[-1])
            run = Run(
                run_id=run_id,
                script_name=script_name,
                total=float(data.get("total", 0)),
                phases=[
                    PhaseRecord(
                        name=p["name"],
                        seconds=float(p.get("seconds", 0)),
                        rc=p.get("rc"),
                        run_id=run_id,
                        script_name=script_name,
                    )
                    for p in data.get("phases", [])
                ],
            )
            runs.append(run)

    return runs


def _categorize(phase_name: str, script_name: str) -> str:
    n = phase_name.lower()
    if "git" in n:
        return "git"
    if "agent" in n:
        return "agent"
    if "dod" in n:
        return "dod"
    if "generat" in n or "prompt" in n or "phase" in n:
        return "generator"
    if (
        "subprocess" in n
        or "spawn" in n
        or "close_package" in n
        or "summarize" in n
        or "smoke" in n
    ):
        return "subprocess"
    if "load" in n or "parse" in n or "scaffold" in n or "yaml" in n or "sync" in n:
        return "io"
    # Sub-script phases
    if script_name not in ("run_autonomous",):
        return f"subscript:{script_name}"
    return "other"


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = (len(sorted_v) - 1) * p / 100
    lo = int(idx)
    hi = min(lo + 1, len(sorted_v) - 1)
    frac = idx - lo
    return sorted_v[lo] * (1 - frac) + sorted_v[hi] * frac


def _aggregate(runs: list[Run]) -> dict[str, Stats]:
    """Compute per-phase statistics across all runs."""
    phase_times: dict[str, list[float]] = {}
    phase_script: dict[str, str] = {}

    for run in runs:
        for rec in run.phases:
            key = f"{rec.script_name}::{rec.name}"
            phase_times.setdefault(key, []).append(rec.seconds)
            phase_script[key] = rec.script_name

    result: dict[str, Stats] = {}
    for key, times in phase_times.items():
        n = len(times)
        mean = sum(times) / n
        median = _percentile(times, 50)
        p95 = _percentile(times, 95)
        max_v = max(times)
        variance = sum((t - mean) ** 2 for t in times) / n if n > 1 else 0.0
        stddev = math.sqrt(variance)
        script = phase_script[key]
        phase_name = key.split("::", 1)[-1]
        result[key] = Stats(
            phase=key,
            count=n,
            total=sum(times),
            mean=mean,
            median=median,
            p95=p95,
            max=max_v,
            stddev=stddev,
            category=_categorize(phase_name, script),
        )
    return result


def _detect_outliers(
    stats: dict[str, Stats],
    threshold_sec: float = 5.0,
) -> list[Outlier]:
    """Identify phases that are slow, high-variance, or growing."""
    outliers: list[Outlier] = []
    for key, s in stats.items():
        if s.max > threshold_sec:
            outliers.append(Outlier(
                phase=key, reason="max_slow",
                value=s.max, threshold=threshold_sec,
            ))
        elif s.mean > 2.0:
            outliers.append(Outlier(
                phase=key, reason="mean_slow",
                value=s.mean, threshold=2.0,
            ))
        if s.mean > 0 and s.stddev / s.mean > 0.5:
            outliers.append(Outlier(
                phase=key, reason="high_variance",
                value=s.stddev / s.mean, threshold=0.5,
            ))
    return sorted(outliers, key=lambda o: -o.value)


def _detect_regressions(runs: list[Run], min_points: int = 5) -> list[Regression]:
    """Linear regression on phase timing over the last N runs to find growing phases."""
    # Collect per-phase time series in run order
    phase_series: dict[str, list[float]] = {}
    for run in runs:
        for rec in run.phases:
            key = f"{rec.script_name}::{rec.name}"
            phase_series.setdefault(key, []).append(rec.seconds)

    regressions: list[Regression] = []
    for key, series in phase_series.items():
        if len(series) < min_points:
            continue
        tail = series[-10:]  # last 10 observations
        n = len(tail)
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = sum(tail) / n
        denom = sum((x - mean_x) ** 2 for x in xs)
        if denom == 0:
            continue
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, tail)) / denom
        if slope > 0.1:  # > 0.1 s/run growth
            regressions.append(Regression(
                phase=key,
                slope=round(slope, 3),
                recent_mean=round(mean_y, 3),
            ))
    return sorted(regressions, key=lambda r: -r.slope)


def _render_md(
    runs: list[Run],
    stats: dict[str, Stats],
    outliers: list[Outlier],
    regressions: list[Regression],
    threshold_sec: float,
) -> str:
    today = date.today().isoformat()
    lines: list[str] = [
        f"# Pipeline Bottleneck Report — {today}",
        "",
        f"Analyzed **{len(runs)}** run(s), **{len(stats)}** unique phases.",
        "",
    ]

    # Top-10 by mean
    top10 = sorted(stats.values(), key=lambda s: -s.mean)[:10]
    lines += [
        "## Top-10 Phases by Mean Duration",
        "",
        "| Phase | Calls | Mean | Median | p95 | Max | Stddev | Category |",
        "|-------|-------|------|--------|-----|-----|--------|----------|",
    ]
    for s in top10:
        lines.append(
            f"| `{s.phase}` | {s.count} | {s.mean:.2f}s | {s.median:.2f}s"
            f" | {s.p95:.2f}s | {s.max:.2f}s | {s.stddev:.2f}s | {s.category} |"
        )
    lines.append("")

    # Outliers
    if outliers:
        lines += ["## Outliers", ""]
        seen: set[str] = set()
        for o in outliers[:5]:
            if o.phase in seen:
                continue
            seen.add(o.phase)
            s = stats.get(o.phase)
            extra = f" (mean={s.mean:.2f}s, max={s.max:.2f}s)" if s else ""
            lines.append(f"- **{o.phase}** — {o.reason}: {o.value:.2f} > {o.threshold:.2f}{extra}")
        lines.append("")
    else:
        lines += ["## Outliers", "", "None detected.", ""]

    # Category breakdown
    cat_totals: dict[str, float] = {}
    for s in stats.values():
        cat_totals[s.category] = cat_totals.get(s.category, 0) + s.total
    if cat_totals:
        lines += ["## Category Breakdown", ""]
        for cat, total in sorted(cat_totals.items(), key=lambda kv: -kv[1]):
            lines.append(f"- **{cat}**: {total:.1f}s total")
        lines.append("")

    # Regressions
    if regressions:
        lines += ["## Growing Phases (regression)", ""]
        for r in regressions[:5]:
            lines.append(
                f"- **{r.phase}**: slope={r.slope:+.3f}s/run, recent_mean={r.recent_mean:.2f}s"
            )
        lines.append("")
    else:
        lines += ["## Growing Phases (regression)", "", "None detected.", ""]

    return "\n".join(lines)


def _render_json(
    runs: list[Run],
    stats: dict[str, Stats],
    outliers: list[Outlier],
    regressions: list[Regression],
) -> str:
    return json.dumps(
        {
            "run_count": len(runs),
            "phases": [
                {
                    "phase": s.phase,
                    "count": s.count,
                    "mean": round(s.mean, 3),
                    "median": round(s.median, 3),
                    "p95": round(s.p95, 3),
                    "max": round(s.max, 3),
                    "stddev": round(s.stddev, 3),
                    "category": s.category,
                }
                for s in sorted(stats.values(), key=lambda x: -x.mean)
            ],
            "outliers": [
                {
                    "phase": o.phase,
                    "reason": o.reason,
                    "value": round(o.value, 3),
                    "threshold": o.threshold,
                }
                for o in outliers
            ],
            "regressions": [
                {
                    "phase": r.phase,
                    "slope": r.slope,
                    "recent_mean": r.recent_mean,
                }
                for r in regressions
            ],
        },
        indent=2,
    )


_LLM_PROMPT_TEMPLATE = """
---

## Скопируй в LLM для получения рекомендаций

**Role:** Ты Performance Engineer для Python CLI пайплайна hometutor.

**Task:** Проанализируй данные о производительности ниже и предложи actionable
рекомендации по устранению узких мест. Следуй правилам из `doc/conventions.md`.

**Output schema:**
1. **Executive summary** — 3 строки: общее wall time, топ-3 фазы по impact.
2. **Critical bottlenecks** (P0/P1/P2): name, current cost, root cause hypothesis,
   proposed fix (file:line ссылки), estimated win, risk.
3. **Stability issues** — фазы с высоким CV (stddev/mean > 0.5).
4. **Regressions** — растущие фазы.
5. **Action checklist** — список задач для backlog.

**Constraints:**
- Не предлагай параллельность там, где возможны race conditions.
- Не предлагай кэш без явного анализа invalidation.
- Уважай архитектурные границы из `doc/conventions_architecture.md`.

**Data:**
```json
{json_data}
```
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--last", type=int, default=20, metavar="N",
                        help="Analyze last N runs (default: 20)")
    parser.add_argument("--threshold-sec", type=float, default=5.0, metavar="X",
                        help="Outlier threshold in seconds (default: 5.0)")
    parser.add_argument("--format", choices=("md", "json"), default="md",
                        help="Output format (default: md)")
    parser.add_argument("--out", type=Path, default=None, metavar="PATH",
                        help="Output path (default: logs/bottlenecks/bottleneck_report_<date>.md)")
    parser.add_argument("--timing-dir", type=Path, default=_TIMING_DIR, metavar="DIR",
                        help="Directory with timing JSON files")
    parser.add_argument("--emit-prompt", action="store_true",
                        help="Append LLM prompt block to the markdown output")
    args = parser.parse_args()

    runs = _load_runs(args.timing_dir, last_n=args.last)
    if not runs:
        print(f"No timing data found in {args.timing_dir}", file=sys.stderr)
        return 1

    stats = _aggregate(runs)
    outliers = _detect_outliers(stats, threshold_sec=args.threshold_sec)
    regressions = _detect_regressions(runs)

    if args.format == "json" or args.emit_prompt:
        json_str = _render_json(runs, stats, outliers, regressions)

    if args.format == "md":
        report = _render_md(runs, stats, outliers, regressions, args.threshold_sec)
        if args.emit_prompt:
            report += _LLM_PROMPT_TEMPLATE.format(json_data=json_str)
    else:
        report = json_str

    if args.out:
        out_path = args.out
    elif args.format == "md":
        _BOTTLENECK_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = _BOTTLENECK_REPORT_DIR / f"bottleneck_report_{date.today().isoformat()}.md"
    else:
        out_path = None

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        try:
            display_path = out_path.relative_to(ROOT)
        except ValueError:
            display_path = out_path
        print(f"Report written: {display_path}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
