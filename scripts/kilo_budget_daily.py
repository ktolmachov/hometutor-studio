#!/usr/bin/env python3
"""Daily budget health check — one command, honest picture.

By default this is a read-only check against the committed injection fixture.
Optionally it can also compute a calibrated local estimate, and only an
explicit flag is allowed to rewrite the versioned fixture.

Usage:
    python scripts/kilo_budget_daily.py                          # baseline check + save report
    python scripts/kilo_budget_daily.py --use-calibrated-estimate  # add local estimate
    python scripts/kilo_budget_daily.py --write-fixture            # explicitly rewrite fixture
    python scripts/kilo_budget_daily.py --no-save                  # check only, no file write
    python scripts/kilo_budget_daily.py --trend 7                  # show last 7 days of trend

Reports saved to logs/budget_reports/YYYYMMDD.json (one file per day).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _kilo_guard import GuardThresholds  # noqa: E402
from kilo_budget_simulate import load_injection_fixture  # noqa: E402
from kilo_injection_calibrate import discover_sources, build_calibrated_fixture, analyze_launchers  # noqa: E402
from kilo_budget_gate import evaluate_launcher, LAUNCHERS, INJECTION_FIXTURE  # noqa: E402


REPORTS_DIR = ROOT / "logs" / "budget_reports"
LEVEL_ORDER = {"ok": 0, "warn": 1, "soft_block": 2, "hard_block": 3}
STATUS_ORDER = {"ok": 0, "caution": 1, "warn": 2, "soft_block": 3, "hard_block": 4}


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_report(date_str: str) -> dict | None:
    p = REPORTS_DIR / f"{date_str}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _previous_reports(n: int) -> list[dict]:
    if not REPORTS_DIR.exists():
        return []
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)[:n]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


def _summarize_analysis(
    label: str,
    fixture_data: dict,
    thresholds: GuardThresholds,
    *,
    source_kind: str,
    source_note: str,
) -> dict:
    gate_rows = [
        evaluate_launcher(l["name"], l["path"], fixture_data, thresholds, dry_run=True)
        for l in LAUNCHERS
    ]
    launcher_rows = analyze_launchers(fixture_data, thresholds)
    any_regression = any(r["regression"] for r in gate_rows)
    any_absolute = any(r["absolute_fail"] for r in gate_rows)
    guard_level = max(
        (r.get("level", "ok") for r in launcher_rows if not r.get("missing")),
        key=lambda l: LEVEL_ORDER.get(l, 0),
        default="ok",
    )
    tight = [
        r for r in launcher_rows
        if not r.get("missing") and 0 < r.get("gap_to_warn", 99999) < 10000
    ]
    if guard_level in {"soft_block", "hard_block", "warn"}:
        status = guard_level
    elif tight:
        status = "caution"
    else:
        status = "ok"
    return {
        "label": label,
        "fixture_kind": source_kind,
        "source_note": source_note,
        "status": status,
        "guard_level": guard_level,
        "any_regression": any_regression,
        "any_absolute_fail": any_absolute,
        "injection": {
            "total_chars": sum(len(str(m.get("content", ""))) for m in fixture_data.get("messages", []))
            + len(json.dumps(fixture_data.get("tools", []), ensure_ascii=False)),
            "sources": fixture_data.get("_meta", {}).get("sources", []),
        },
        "launchers": launcher_rows,
        "gate": gate_rows,
    }


def _choose_overall_status(analyses: dict[str, dict]) -> str:
    return max(
        (analysis["status"] for analysis in analyses.values()),
        key=lambda status: STATUS_ORDER.get(status, -1),
        default="ok",
    )


def run_check(
    thresholds: GuardThresholds,
    *,
    include_calibrated_estimate: bool,
    write_fixture: bool,
) -> dict:
    analyses: dict[str, dict] = {}

    baseline_fixture = load_injection_fixture(INJECTION_FIXTURE)
    analyses["committed_fixture_gate"] = _summarize_analysis(
        "committed_fixture_gate",
        baseline_fixture,
        thresholds,
        source_kind="committed_fixture",
        source_note="Committed fixture used by the real pre-commit gate.",
    )

    if include_calibrated_estimate or write_fixture:
        sources = discover_sources()
        calibrated_fixture = build_calibrated_fixture(sources)
        calibrated_fixture.setdefault("_meta", {})
        calibrated_fixture["_meta"]["sources"] = [
            {"name": s.name, "chars": s.chars, "type": s.source_type} for s in sources
        ]
        analyses["calibrated_estimate"] = _summarize_analysis(
            "calibrated_estimate",
            calibrated_fixture,
            thresholds,
            source_kind="local_calibrated_estimate",
            source_note="Local approximation rebuilt from readable project sources plus estimates.",
        )
        if write_fixture:
            INJECTION_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            INJECTION_FIXTURE.write_text(
                json.dumps(calibrated_fixture, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return {
        "schema_version": 2,
        "date": _today(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "overall_status": _choose_overall_status(analyses),
        "thresholds": asdict(thresholds),
        "analyses": analyses,
    }


def _format_analysis_block(analysis: dict, prev_analysis: dict | None = None) -> list[str]:
    lines: list[str] = []
    inj = analysis["injection"]
    lines.append(f"{analysis['label']}: {analysis['status'].upper()}  [{analysis['fixture_kind']}]")
    lines.append(f"  Source: {analysis['source_note']}")
    lines.append(f"  Injection size:  {inj['total_chars']:>7,} chars  ({len(inj['sources'])} sources)")
    if prev_analysis:
        prev_inj = prev_analysis.get("injection", {}).get("total_chars", 0)
        delta_inj = inj["total_chars"] - prev_inj
        lines.append(f"    vs {prev_analysis.get('date', 'previous')}: {delta_inj:>+6,} chars  (injection drift)")
    lines.append("")
    lines.append(f"    {'Launcher':<16} {'Level':<12} {'Body':>8}  {'->warn':>8}  {'->soft':>8}")
    lines.append(f"    {'-'*16} {'-'*12} {'-'*8}  {'-'*8}  {'-'*8}")
    for r in analysis["launchers"]:
        if r.get("missing"):
            lines.append(f"    {r['name']:<16} MISSING")
            continue
        mark = " !!" if r["level"] != "ok" else ""
        lines.append(
            f"    {r['name']:<16} {r['level']:<12} {r['body_chars']:>8,}  "
            f"{r['gap_to_warn']:>+8,}  {r['gap_to_soft_block']:>+8,}{mark}"
        )
    if analysis.get("any_regression"):
        lines.append("")
        lines.append("  REGRESSION DETECTED in working tree vs HEAD for this analysis.")
    tight = [
        r for r in analysis["launchers"]
        if not r.get("missing") and 0 < r.get("gap_to_warn", 99999) < 10000
    ]
    lines.append("")
    if analysis["status"] in {"soft_block", "hard_block", "warn"} and not analysis.get("any_regression"):
        lines.append(f"  STATUS: {analysis['status'].upper()} — threshold breach in this analysis.")
    elif analysis["status"] == "caution":
        names = ", ".join(r["name"] for r in tight)
        margins = ", ".join(str(r["gap_to_warn"]) for r in tight)
        lines.append(f"  STATUS: CAUTION — [{names}] margin {margins} chars.")
        lines.append("    Session history can close this gap quickly.")
    else:
        lines.append("  STATUS: OK — all launchers within budget.")
    if inj["sources"]:
        biggest = max(inj["sources"], key=lambda s: s.get("chars", 0))
        lines.append(f"    Biggest injection source: {biggest.get('name')}")
    return lines


def format_report(report: dict, prev: dict | None = None) -> str:
    lines: list[str] = []
    level = report["overall_status"]
    date = report["date"]
    t = report["thresholds"]
    lines.append(f"=== Kilo Budget Health [{date}] === {level.upper()}")
    analyses = report.get("analyses", {})
    baseline_prev = (
        (prev or {}).get("analyses", {}).get("committed_fixture_gate")
        or (prev or {}).get("analyses", {}).get("baseline_gate")
    )
    calibrated_prev = (prev or {}).get("analyses", {}).get("calibrated_estimate")
    if "committed_fixture_gate" in analyses:
        lines.extend(_format_analysis_block(analyses["committed_fixture_gate"], baseline_prev))
    if "calibrated_estimate" in analyses:
        lines.append("")
        lines.extend(_format_analysis_block(analyses["calibrated_estimate"], calibrated_prev))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("  - committed_fixture_gate = committed fixture used by the actual pre-commit gate")
    lines.append("  - calibrated_estimate = local approximation, useful for drift awareness")
    lines.append(f"\nThresholds: warn={t['warn_body_chars']:,}  soft={t['max_body_chars']:,}  "
                 f"hard={t['hard_block_body_chars']:,}  max_msgs={t['max_messages']}")
    return "\n".join(lines)


def format_trend(reports: list[dict]) -> str:
    if not reports:
        return "No trend data found."
    lines = ["=== Budget Trend ===", f"  {'Date':<12} {'Status':<12} {'MaxBody':>9}  {'Injection':>10}"]
    for r in sorted(reports, key=lambda x: x.get("date", "")):
        analyses = r.get("analyses", {})
        baseline = analyses.get("committed_fixture_gate") or analyses.get("baseline_gate", {})
        max_body = max((x.get("body_chars", 0) for x in baseline.get("launchers", []) if not x.get("missing")), default=0)
        inj = baseline.get("injection", {}).get("total_chars", 0)
        lines.append(f"  {r['date']:<12} {r.get('overall_status', 'ok'):<12} {max_body:>9,}  {inj:>10,}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily Kilo budget health check")
    parser.add_argument("--no-save", action="store_true", help="Don't write report file")
    parser.add_argument(
        "--use-calibrated-estimate",
        action="store_true",
        help="Also compute a local calibrated estimate without changing the committed fixture",
    )
    parser.add_argument(
        "--write-fixture",
        action="store_true",
        help="Explicitly rewrite the committed fixture using the calibrated estimate",
    )
    parser.add_argument("--trend", type=int, default=0, metavar="N", help="Show last N days of trend")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--thresholds-from-env", action="store_true")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    if args.trend:
        reports = _previous_reports(args.trend)
        print(format_trend(reports))
        return 0

    thresholds = GuardThresholds.from_env() if args.thresholds_from_env else GuardThresholds()
    report = run_check(
        thresholds,
        include_calibrated_estimate=args.use_calibrated_estimate or args.write_fixture,
        write_fixture=args.write_fixture,
    )

    today_str = _today()
    prev = None
    # Find most recent previous report (before today)
    if REPORTS_DIR.exists():
        prev_files = sorted(
            [f for f in REPORTS_DIR.glob("*.json") if f.stem < today_str],
            reverse=True,
        )
        if prev_files:
            try:
                prev = json.loads(prev_files[0].read_text(encoding="utf-8"))
            except Exception:
                pass

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report, prev))

    if not args.no_save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        out = REPORTS_DIR / f"{today_str}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport saved: {out}")

    level = report["overall_status"]
    return 0 if level in ("ok", "caution", "warn") else 2


if __name__ == "__main__":
    raise SystemExit(main())
