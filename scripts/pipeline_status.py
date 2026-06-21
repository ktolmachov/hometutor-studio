#!/usr/bin/env python3
"""
pipeline_status.py -- Zero-Click Pipeline Dashboard

Single command to see everything at a glance:
  - Active package + complexity + work-state
  - DoD status (green/red per command)
  - Next recommended action with copy-paste command
  - Recent closures

Usage:
  python scripts/pipeline_status.py
  python scripts/pipeline_status.py --json
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_utils import (  # noqa: E402
    ROOT,
    classify_package_complexity,
    detect_work_state,
    ensure_utf8_stdio,
    extract_dod_commands,
    extract_recent_closed,
    parse_contract,
    parse_truth_view_from_registry,
    select_package,
)

TASK_FILE = ROOT / "doc" / "current_task.md"
AUTONOMOUS_RUNS_ROOT = ROOT / "logs" / "autonomous_runs"

STATUS_ICON = {
    "wip":      "[WIP]  ",
    "ready":    "[READY]",
    "open":     "[OPEN] ",
    "proposed": "[PROP] ",
}
DOD_PASS = "PASS"
DOD_FAIL = "FAIL"
DOD_SKIP = "SKIP"


def _run_dod(cmds: list[str]) -> list[tuple[str, str]]:
    """Run each DoD command, return (cmd, status) pairs."""
    results = []
    for cmd in cmds:
        res = subprocess.run(cmd, shell=True, cwd=str(ROOT),
                             capture_output=True, text=True)
        results.append((cmd, DOD_PASS if res.returncode == 0 else DOD_FAIL))
    return results


def _task_file_info() -> str:
    try:
        age_s = time.time() - TASK_FILE.stat().st_mtime
        age_min = int(age_s / 60)
        return f"doc/current_task.md  (written {age_min} min ago)"
    except OSError:
        return "(none)"


def _next_action(package_id: str | None, work_state: str | None,
                 complexity: str | None, dod_results: list[tuple[str, str]]) -> tuple[str, str]:
    """Return (description, command) for the recommended next action."""
    if not package_id:
        return (
            "No active package -- start plan-next",
            "python scripts/run_autonomous.py --agent cursor_ai",
        )
    all_green = all(s == DOD_PASS for _, s in dod_results) if dod_results else None
    if all_green:
        return (
            f"All DoD green -- close package and pre-generate next task",
            f"python scripts/run_autonomous.py --post-agent --package {package_id}",
        )
    if dod_results and not all_green:
        return (
            "DoD failing -- fix tests then close",
            f"python scripts/run_autonomous.py --post-agent --package {package_id}",
        )
    # DoD not run yet
    if complexity in ("high",):
        return (
            "High complexity -- generate orchestration prompt",
            f"python scripts/run_autonomous.py --agent cursor_ai",
        )
    return (
        "Ready for execution -- generate task file",
        f"python scripts/run_autonomous.py --agent cursor_ai",
    )


def build_report(run_dod: bool = True) -> dict:
    # Truth View + contract: backlog_registry.yaml SSoT only (no tasklist.md fallback).
    rows = parse_truth_view_from_registry()
    row = select_package(rows, None) if rows else None

    package_id = row["package"] if row else None
    status = row.get("status", "") if row else ""
    contract = parse_contract("", package_id) if package_id else {}
    work_state  = detect_work_state(package_id) if package_id else None
    if contract:
        _cx = classify_package_complexity(contract)
        complexity_label = _cx["label"]
    else:
        complexity_label = "?"
    dod_raw     = contract.get("DOD_COMMANDS", "")
    dod_cmds    = extract_dod_commands(dod_raw)
    dod_results: list[tuple[str, str]] = []
    if run_dod and dod_cmds and package_id:
        dod_results = _run_dod(dod_cmds)
    elif dod_cmds:
        dod_results = [(cmd, DOD_SKIP) for cmd in dod_cmds]

    action_desc, action_cmd = _next_action(package_id, work_state, complexity_label, dod_results if run_dod else [])

    recent = extract_recent_closed()

    timeline = build_runs_timeline()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "package": package_id,
        "status": status,
        "complexity": complexity_label,
        "work_state": work_state,
        "dod": dod_results,
        "task_file": _task_file_info(),
        "action_desc": action_desc,
        "action_cmd": action_cmd,
        "recent_closed": recent[:200] if recent else "",
        "runs": timeline["runs"],
        "stats": timeline["stats"],
    }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_log_started_at(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        data = json.loads(first)
    except (OSError, IndexError, json.JSONDecodeError):
        return None
    return data.get("ts") if isinstance(data, dict) else None


def _event_names(path: Path) -> set[str]:
    names: set[str] = set()
    if not path.exists():
        return names
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return names
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = data.get("event") if isinstance(data, dict) else None
        if isinstance(event, str):
            names.add(event)
    return names


def _iter_autonomous_run_dirs(root: Path):
    """Yield run dirs under logs/autonomous_runs/<run_id>/ (skip _orphan, current)."""
    if not root.is_dir():
        return
    skip = frozenset({"_orphan", "current"})
    for child in sorted(root.iterdir(), key=lambda p: p.name, reverse=True):
        if not child.is_dir() or child.name in skip:
            continue
        if (child / "result.json").is_file():
            yield child


def _count_event_types(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not path.exists():
        return counts
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return counts
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        event = data.get("event") if isinstance(data, dict) else None
        if isinstance(event, str):
            counts[event] = counts.get(event, 0) + 1
    return counts


def build_runs_timeline(root: Path = AUTONOMOUS_RUNS_ROOT) -> dict:
    """Aggregate logs/autonomous_runs/<run_id>/ into JSON-friendly runs + stats (Wave 2 observability)."""
    runs: list[dict] = []
    sandbox_blocks_total = 0
    sandbox_escape_total = 0
    failure_class_counts: dict[str, int] = {}

    for run_dir in _iter_autonomous_run_dirs(root):
        result_path = run_dir / "result.json"
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        state_path = run_dir / "pipeline_state.json"
        state: dict = {}
        if state_path.exists():
            try:
                loaded = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                loaded = {}
            if isinstance(loaded, dict):
                state = loaded
        event_log = run_dir / "event_log.jsonl"
        ev_counts = _count_event_types(event_log)
        sandbox_blocks_total += ev_counts.get("SANDBOX_BLOCK", 0)
        sandbox_escape_total += ev_counts.get("SANDBOX_ESCAPE", 0)
        events = _event_names(event_log)
        started_at = _event_log_started_at(event_log)
        finished_at = result.get("finished_at")
        start_dt = _parse_iso(started_at)
        finish_dt = _parse_iso(str(finished_at)) if finished_at else None
        duration_s = 0.0
        if start_dt and finish_dt:
            duration_s = max(0.0, (finish_dt - start_dt).total_seconds())
        failure_class = result.get("failure_class")
        if isinstance(failure_class, dict):
            failure_name = failure_class.get("name")
            if isinstance(failure_name, str) and failure_name:
                failure_class_counts[failure_name] = failure_class_counts.get(failure_name, 0) + 1
        runs.append(
            {
                "run_id": result.get("run_id") or run_dir.name,
                "package_id": result.get("package_id"),
                "exit_code": result.get("exit_code"),
                "duration_s": duration_s,
                "phase": state.get("phase"),
                "proof_ok": "PROOF_TAMPERED" not in events and "PROOF_MISSING" not in events,
                "started_at": started_at,
                "finished_at": finished_at,
                "failure_class": result.get("failure_class"),
            }
        )

    runs.sort(key=lambda item: item.get("finished_at") or "", reverse=True)

    terminal = [r for r in runs if r.get("phase") in ("closed", "failed")]
    if terminal:
        closure_success_rate = sum(
            1
            for r in terminal
            if r.get("phase") == "closed" and r.get("exit_code") == 0
        ) / len(terminal)
    elif runs:
        closure_success_rate = sum(1 for r in runs if r.get("exit_code") == 0) / len(runs)
    else:
        closure_success_rate = 0.0

    exit_ok = [r for r in runs if r.get("exit_code") == 0]
    false_closure_rate = (
        sum(1 for r in exit_ok if r.get("proof_ok") is False) / len(exit_ok) if exit_ok else 0.0
    )

    sb_denom = sandbox_blocks_total + sandbox_escape_total
    if sb_denom > 0:
        prompt_injection_block_rate = sandbox_blocks_total / sb_denom
    elif sandbox_blocks_total > 0:
        prompt_injection_block_rate = 1.0
    else:
        prompt_injection_block_rate = 0.0

    durations = [float(r["duration_s"]) for r in runs if r.get("duration_s")]
    closed = [r for r in runs if r.get("phase") == "closed"]
    stats = {
        "closure_success_rate": closure_success_rate,
        "false_closure_rate": false_closure_rate,
        "prompt_injection_block_rate": prompt_injection_block_rate,
        "median_duration_s": float(statistics.median(durations)) if durations else 0.0,
        "closed_runs": len(closed),
        "total_runs": len(runs),
        "sandbox_blocks_total": sandbox_blocks_total,
        "sandbox_escape_total": sandbox_escape_total,
        "failure_class_counts": dict(sorted(failure_class_counts.items())),
    }
    return {"runs": runs, "stats": stats}


def validate_observability_report(report: dict) -> list[str]:
    """Structural validation for the pipeline_status.py --json observability subset."""
    errors: list[str] = []
    runs = report.get("runs")
    stats = report.get("stats")
    if not isinstance(runs, list):
        errors.append("runs must be a list")
    else:
        required_run_keys = {
            "run_id",
            "package_id",
            "exit_code",
            "duration_s",
            "phase",
            "proof_ok",
            "started_at",
        }
        for idx, run in enumerate(runs):
            if not isinstance(run, dict):
                errors.append(f"runs[{idx}] must be an object")
                continue
            missing = sorted(required_run_keys - set(run))
            if missing:
                errors.append(f"runs[{idx}] missing keys: {missing}")
            if "proof_ok" in run and not isinstance(run["proof_ok"], bool):
                errors.append(f"runs[{idx}].proof_ok must be boolean")
            if "duration_s" in run and not isinstance(run["duration_s"], (int, float)):
                errors.append(f"runs[{idx}].duration_s must be numeric")

    if not isinstance(stats, dict):
        errors.append("stats must be an object")
    else:
        required_stats = {
            "closure_success_rate",
            "false_closure_rate",
            "prompt_injection_block_rate",
            "median_duration_s",
        }
        missing = sorted(required_stats - set(stats))
        if missing:
            errors.append(f"stats missing keys: {missing}")
        for key in required_stats:
            if key in stats and not isinstance(stats[key], (int, float)):
                errors.append(f"stats.{key} must be numeric")
        counts = stats.get("failure_class_counts")
        if counts is not None:
            if not isinstance(counts, dict):
                errors.append("stats.failure_class_counts must be an object")
            else:
                for name, count in counts.items():
                    if not isinstance(name, str) or not isinstance(count, int):
                        errors.append("stats.failure_class_counts must map strings to integers")
                        break
    return errors


def print_report(r: dict) -> None:
    sep  = "=" * 66
    sep2 = "-" * 66
    print(sep)
    print("  PIPELINE STATUS")
    print(sep)

    if r["package"]:
        icon = STATUS_ICON.get(r["status"].lower(), "[?????]")
        print(f"  Package  : {icon}  {r['package']}")
        print(f"  Complexity: {r['complexity']}   Work state: {r['work_state'] or '?'}")
    else:
        print("  Package  : (none -- backlog_registry.yaml has no active package)")

    print()
    print("  DoD")
    print(sep2)
    if not r["dod"]:
        print("  (no DoD commands in contract)")
    else:
        for cmd, status in r["dod"]:
            icon = "OK" if status == DOD_PASS else ("--" if status == DOD_SKIP else "XX")
            short = cmd[:55] + ("..." if len(cmd) > 55 else "")
            print(f"  [{icon}]  {short}")

    print()
    print("  Task file")
    print(sep2)
    print(f"  {r['task_file']}")

    tr = r.get("stats") or {}
    print()
    print("  AUTONOMOUS RUNS (logs/autonomous_runs)")
    print(sep2)
    print(
        f"  total={tr.get('total_runs', 0)}  "
        f"closure_success_rate={tr.get('closure_success_rate', 0):.2f}  "
        f"false_closure_rate={tr.get('false_closure_rate', 0):.2f}  "
        f"prompt_injection_block_rate={tr.get('prompt_injection_block_rate', 0):.2f}  "
        f"median_dur_s={tr.get('median_duration_s', 0):.1f}"
    )
    failure_counts = tr.get("failure_class_counts") or {}
    if failure_counts:
        top_failures = ", ".join(
            f"{name}={count}" for name, count in sorted(failure_counts.items())[:6]
        )
        print(f"  failure_class_counts: {top_failures}")
    for item in (r.get("runs") or [])[:8]:
        rid = item.get("run_id") or "?"
        pkg = item.get("package_id") or "-"
        xc = item.get("exit_code")
        ph = item.get("phase") or "?"
        pr = item.get("proof_ok")
        t0 = (item.get("finished_at") or "")[:19]
        print(f"  {t0}  {rid[:28]:28}  xc={xc}  phase={ph}  proof_ok={pr}  pkg={pkg}")

    print()
    print("  NEXT ACTION")
    print(sep2)
    print(f"  {r['action_desc']}")
    print()
    print(f"    {r['action_cmd']}")

    print()
    print(sep)
    print(f"  {r['timestamp'][:19].replace('T', ' ')} UTC")
    print(sep)


def main() -> int:
    ensure_utf8_stdio()
    p = argparse.ArgumentParser(description="Pipeline status dashboard")
    p.add_argument("--json",     action="store_true", help="Output JSON instead of pretty print")
    p.add_argument("--no-dod",  action="store_true", help="Skip running DoD commands (show SKIP)")
    args = p.parse_args()

    report = build_report(run_dod=not args.no_dod)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)

    # Exit 1 if any DoD failed (useful for CI / hooks)
    if any(s == DOD_FAIL for _, s in report["dod"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
