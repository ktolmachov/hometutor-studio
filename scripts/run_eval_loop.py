#!/usr/bin/env python3
"""Unified eval loop for prompt smoke, quality/router evals, judge metrics and SLOs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_INFRA_ERROR = 1
EXIT_FAILED = 2
ALL_PHASES = ("prompt_smoke", "quality_benchmark", "router_eval", "judge_sweep", "latency_by_mode")
PROFILE_PHASES = {
    "ci": ("prompt_smoke", "judge_sweep", "latency_by_mode"),
    "nightly": ALL_PHASES,
    "full": ALL_PHASES,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_from_rc(rc: int) -> str:
    if rc == 0:
        return "pass"
    if rc == EXIT_INFRA_ERROR:
        return "error"
    return "fail"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _log_progress(message: str) -> None:
    print(f"eval_loop: {message}", file=sys.stderr, flush=True)


def _run_phase_script(script: str, extra_args: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="eval_loop_") as tmp:
        report_path = Path(tmp) / "phase.json"
        cmd = [sys.executable, str(ROOT / "scripts" / script), "--report-json", str(report_path)]
        cmd.extend(extra_args or [])
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        started = time.monotonic()
        while True:
            try:
                stdout, _ = proc.communicate(timeout=30)
                break
            except subprocess.TimeoutExpired:
                elapsed = int(time.monotonic() - started)
                _log_progress(f"{script} still running ({elapsed}s elapsed)")
        payload: dict[str, Any] = {}
        if report_path.exists():
            payload = _read_json(report_path)
        else:
            try:
                payload = json.loads(stdout or "")
            except json.JSONDecodeError:
                payload = {}
        if proc.returncode != 0:
            payload.setdefault("error", (stdout or "").strip()[:1000])
        return proc.returncode, payload


def _run_prompt_smoke_offline() -> dict[str, Any]:
    from scripts.run_prompt_smoke import DEFAULT_CASES

    raw = _read_json(DEFAULT_CASES)
    cases = raw.get("cases") or []
    missing_expect = [str(c.get("id") or i) for i, c in enumerate(cases, start=1) if not c.get("expect")]
    return {
        "status": "pass" if cases and not missing_expect else "fail",
        "p95_latency_sec": None,
        "cases_total": len(cases),
        "cases_failed": len(missing_expect),
        "failed_cases": missing_expect,
        "mode": "offline_dataset_check",
    }


def run_prompt_smoke_phase(*, profile: str) -> dict[str, Any]:
    if profile == "ci" and not os.getenv("OPENAI_API_KEY"):
        return _run_prompt_smoke_offline()
    rc, report = _run_phase_script("run_prompt_smoke.py", ["--strict"])
    rows = list(report.get("cases") or [])
    failed = [
        str(r.get("id") or "")
        for r in rows
        if r.get("status") == "error" or (r.get("status") == "completed" and r.get("expect_pass") is False)
    ]
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "status": _status_from_rc(rc),
        "p95_latency_sec": (summary.get("latency_sec") or {}).get("p95"),
        "cases_total": summary.get("cases_total", len(rows)),
        "cases_failed": len(failed),
        "failed_cases": failed,
    }


def run_quality_benchmark_phase() -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        return {"status": "fail", "reason": "OPENAI_API_KEY is not set", "cases_total": 0}
    rc, report = _run_phase_script("run_quality_benchmark.py")
    agg = report.get("aggregate") if isinstance(report.get("aggregate"), dict) else {}
    return {
        "status": _status_from_rc(rc),
        "hit_rate": agg.get("hit_rate"),
        "mrr": agg.get("mean_reciprocal_rank"),
        "relevancy": agg.get("answer_relevancy"),
        "cases_total": len(report.get("cases") or []),
    }


def run_router_eval_phase() -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        return {"status": "fail", "reason": "OPENAI_API_KEY is not set", "cases_total": 0}
    rc, report = _run_phase_script("run_router_eval.py")
    agg = report.get("aggregate") if isinstance(report.get("aggregate"), dict) else {}
    per_category = agg.get("per_category") if isinstance(agg.get("per_category"), dict) else {}
    zero = [
        str(name)
        for name, stats in per_category.items()
        if isinstance(stats, dict) and stats.get("accuracy") == 0
    ]
    regression_pp = None
    if report.get("regression_detail"):
        regression_pp = report.get("regression_detail")
    return {
        "status": _status_from_rc(rc),
        "overall_accuracy": agg.get("overall_accuracy"),
        "regression_pp": regression_pp,
        "zero_accuracy_categories": zero,
        "cases_total": len(report.get("cases") or []),
    }


def _judge_sample_size(metrics_module: Any, *, limit_events: int) -> int:
    path = metrics_module.METRICS_STORE_PATH
    if not path.exists():
        return 0
    total = 0
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("event_type") == "quality_judge" and not item.get("error"):
                total += 1
    return min(total, limit_events)


def run_judge_sweep_phase(*, limit_events: int = 20000) -> dict[str, Any]:
    from app import metrics

    avgs = metrics._collect_judge_score_averages(limit_lines=limit_events)
    sample_size = _judge_sample_size(metrics, limit_events=limit_events)
    return {
        "status": "pass" if sample_size else "skipped",
        "answer_relevancy": avgs.get("answer_relevancy"),
        "faithfulness": avgs.get("faithfulness"),
        "context_relevancy": avgs.get("context_relevancy"),
        "sample_size": sample_size,
    }


def run_latency_by_mode_phase(*, limit_events: int = 20000) -> dict[str, Any]:
    from app.config import get_settings
    from app.metrics import collect_latency_by_query_mode

    return collect_latency_by_query_mode(
        limit_events=limit_events,
        thresholds_ms=get_settings().slo_latency_by_mode,
    )


def _run_slo_alerts(
    *,
    latency_by_mode: dict[str, Any],
    webhook: bool,
    limit_events: int,
) -> dict[str, Any]:
    from app.metrics import evaluate_slo_alerts, evaluate_slo_alerts_and_notify

    out = (
        evaluate_slo_alerts_and_notify(limit_events=limit_events, send_webhook=True)
        if webhook
        else evaluate_slo_alerts(limit_events=limit_events)
    )
    alerts = list(out.get("alerts") or [])
    existing_modes = {
        a.get("query_type")
        for a in alerts
        if a.get("metric") == "p95_total_answer_ms_by_query_type"
    }
    for mode, stats in (latency_by_mode.get("by_mode") or {}).items():
        if stats.get("slo_status") == "fail" and mode not in existing_modes:
            alerts.append(
                {
                    "kind": "slo",
                    "metric": "p95_total_answer_ms_by_query_type",
                    "query_type": mode,
                    "severity": "warning",
                    "observed": stats.get("p95"),
                    "threshold": stats.get("slo_threshold_ms"),
                    "message": f"p95 latency above per-mode SLO for query_type={mode}",
                }
            )
    out["alerts"] = alerts
    return {"alerts": alerts, "anomalies": list(out.get("anomalies") or [])}


def _cost_summary(*, limit_events: int = 20000) -> dict[str, Any] | None:
    from app.metrics import summarize_metrics_store

    summary = summarize_metrics_store(limit=limit_events)
    if not summary:
        return None
    costs = summary.get("estimated_cost_usd") or {}
    return {
        "total_usd": costs.get("total"),
        "per_request_avg_usd": costs.get("avg_per_request"),
    }


def _overall_status(phases: dict[str, Any], slo_alerts: dict[str, Any]) -> str:
    if any(isinstance(p, dict) and p.get("status") in {"error", "fail"} for p in phases.values()):
        return "fail"
    if slo_alerts.get("alerts"):
        return "fail"
    if any(isinstance(p, dict) and p.get("status") == "skipped" for p in phases.values()):
        return "warn"
    return "pass"


def run_eval_loop(
    *,
    profile: str = "full",
    skip_phase: list[str] | None = None,
    webhook: bool = False,
    limit_events: int = 20000,
) -> tuple[dict[str, Any], int]:
    skips = set(skip_phase or [])
    selected = [p for p in PROFILE_PHASES[profile] if p not in skips]
    phases: dict[str, Any] = {name: None for name in ALL_PHASES}

    if "prompt_smoke" in selected:
        _log_progress("starting prompt_smoke")
        phases["prompt_smoke"] = run_prompt_smoke_phase(profile=profile)
        _log_progress(f"finished prompt_smoke status={phases['prompt_smoke'].get('status')}")
    if "quality_benchmark" in selected:
        _log_progress("starting quality_benchmark")
        phases["quality_benchmark"] = run_quality_benchmark_phase()
        _log_progress(f"finished quality_benchmark status={phases['quality_benchmark'].get('status')}")
    if "router_eval" in selected:
        _log_progress("starting router_eval")
        phases["router_eval"] = run_router_eval_phase()
        _log_progress(f"finished router_eval status={phases['router_eval'].get('status')}")
    if "judge_sweep" in selected:
        _log_progress("starting judge_sweep")
        phases["judge_sweep"] = run_judge_sweep_phase(limit_events=limit_events)
        _log_progress(f"finished judge_sweep status={phases['judge_sweep'].get('status')}")
    if "latency_by_mode" in selected:
        _log_progress("starting latency_by_mode")
        phases["latency_by_mode"] = run_latency_by_mode_phase(limit_events=limit_events)
        _log_progress(f"finished latency_by_mode status={phases['latency_by_mode'].get('status')}")

    _log_progress("starting slo_alerts")
    slo_alerts = _run_slo_alerts(
        latency_by_mode=phases.get("latency_by_mode") or {},
        webhook=webhook,
        limit_events=limit_events,
    )
    _log_progress(
        f"finished slo_alerts alerts={len(slo_alerts.get('alerts') or [])} anomalies={len(slo_alerts.get('anomalies') or [])}"
    )
    overall = _overall_status(phases, slo_alerts)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "timestamp": _now_iso(),
        "profile": profile,
        "phases": phases,
        "slo_alerts": slo_alerts,
        "cost_summary": _cost_summary(limit_events=limit_events),
        "overall_status": overall,
    }
    if any(isinstance(p, dict) and p.get("status") == "error" for p in phases.values()):
        return report, EXIT_INFRA_ERROR
    return report, EXIT_OK if overall in {"pass", "warn"} else EXIT_FAILED


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified eval/quality/latency loop.")
    parser.add_argument("--profile", choices=sorted(PROFILE_PHASES), default="full")
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--webhook", action="store_true", help="POST alerts if configured")
    parser.add_argument("--skip-phase", action="append", choices=ALL_PHASES, default=[])
    parser.add_argument("--limit-events", type=int, default=20000)
    args = parser.parse_args()

    try:
        report, rc = run_eval_loop(
            profile=args.profile,
            skip_phase=args.skip_phase,
            webhook=args.webhook,
            limit_events=args.limit_events,
        )
    except Exception as exc:
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "timestamp": _now_iso(),
            "profile": args.profile,
            "phases": {},
            "slo_alerts": {"alerts": [], "anomalies": []},
            "cost_summary": None,
            "overall_status": "fail",
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        rc = EXIT_INFRA_ERROR

    out = json.dumps(report, ensure_ascii=False, indent=2)
    print(out)
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(out, encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
