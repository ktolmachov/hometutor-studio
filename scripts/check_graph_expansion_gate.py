#!/usr/bin/env python3
"""
Готовая команда для graph expansion quality gate.

Запуск из корня репозитория:
  python scripts/check_graph_expansion_gate.py
  python scripts/check_graph_expansion_gate.py --profile strict
  python scripts/check_graph_expansion_gate.py --jsonl logs/metrics_store.jsonl --min-events 20
  python scripts/check_graph_expansion_gate.py --uplift-report eval/graph_uplift_report_run.json --generation-id GEN
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOCAL_GATE_DEFAULTS = {
    "min_events": 10,
    "max_p95_ms": 80.0,
    "min_applied_rate": 0.10,
    "max_error_rate": 0.05,
    "min_avg_extra_chunks": 1.0,
}

STRICT_GATE_DEFAULTS = {
    "min_events": 30,
    "max_p95_ms": 60.0,
    "min_applied_rate": 0.15,
    "max_error_rate": 0.02,
    "min_avg_extra_chunks": 1.0,
}

LOCAL_UPLIFT_GATE_DEFAULTS = {
    "min_correctness_delta": 0.02,
    "min_evidence_quality_delta": 0.02,
    "min_citation_correctness_delta": 0.01,
    "max_latency_p95_delta_ms": 40.0,
}

STRICT_UPLIFT_GATE_DEFAULTS = {
    "min_correctness_delta": 0.03,
    "min_evidence_quality_delta": 0.03,
    "min_citation_correctness_delta": 0.02,
    "max_latency_p95_delta_ms": 30.0,
}


def resolve_thresholds(
    *,
    profile: str,
    min_events: int | None = None,
    max_p95_ms: float | None = None,
    min_applied_rate: float | None = None,
    max_error_rate: float | None = None,
    min_avg_extra_chunks: float | None = None,
) -> dict[str, Any]:
    base = STRICT_GATE_DEFAULTS if profile == "strict" else LOCAL_GATE_DEFAULTS
    out = dict(base)
    overrides = {
        "min_events": min_events,
        "max_p95_ms": max_p95_ms,
        "min_applied_rate": min_applied_rate,
        "max_error_rate": max_error_rate,
        "min_avg_extra_chunks": min_avg_extra_chunks,
    }
    for key, value in overrides.items():
        if value is not None:
            out[key] = value
    return out


def resolve_uplift_thresholds(profile: str) -> dict[str, float]:
    return dict(STRICT_UPLIFT_GATE_DEFAULTS if profile == "strict" else LOCAL_UPLIFT_GATE_DEFAULTS)


def _load_uplift_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_gate(
    *,
    jsonl_path: str | Path | None = None,
    limit: int = 2000,
    profile: str = "local",
    min_events: int | None = None,
    max_p95_ms: float | None = None,
    min_applied_rate: float | None = None,
    max_error_rate: float | None = None,
    min_avg_extra_chunks: float | None = None,
    uplift_report_path: str | Path | None = None,
    generation_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    os.chdir(ROOT)
    from app.course_cache import resolve_active_generation_uplift_prerequisites
    from app.eval_uplift import evaluate_uplift_gate
    from app.metrics import METRICS_STORE_PATH
    from scripts import graph_expansion_benchmark as benchmark

    path = Path(jsonl_path) if jsonl_path else Path(METRICS_STORE_PATH)
    lim = None if limit <= 0 else int(limit)
    ge_report, event_count = benchmark.build_report_from_jsonl_path(path, limit_last=lim)
    thresholds = resolve_thresholds(
        profile=profile,
        min_events=min_events,
        max_p95_ms=max_p95_ms,
        min_applied_rate=min_applied_rate,
        max_error_rate=max_error_rate,
        min_avg_extra_chunks=min_avg_extra_chunks,
    )
    gate = benchmark.evaluate_quality_gate(ge_report, **thresholds)
    report: dict[str, Any] = {
        "source": "jsonl",
        "jsonl_path": str(path.resolve()),
        "request_events_in_window": event_count,
        "graph_expansion": ge_report,
        "gate_profile": profile,
        "gate_thresholds": thresholds,
        "quality_gate": gate,
    }

    gates_passed = [bool(gate.get("passed"))]
    rc_parts: list[int] = []

    uplift_path = Path(uplift_report_path) if uplift_report_path else None
    uplift_report: dict[str, Any] | None = None
    if uplift_path is not None:
        uplift_report = _load_uplift_report(uplift_path)
        uplift_thr = resolve_uplift_thresholds(profile)
        uplift_gate = evaluate_uplift_gate(
            uplift_report,
            uplift_thr,
            expected_generation_id=generation_id,
        )
        report["uplift_report_path"] = str(uplift_path.resolve())
        report["uplift_gate"] = uplift_gate
        report["uplift_gate_thresholds"] = uplift_thr
        gates_passed.append(bool(uplift_gate.get("passed")))
        rc_parts.append(int(uplift_gate.get("exit_code") or 0))

    gen = str(generation_id or "").strip()
    if gen or uplift_report is not None:
        prereqs = resolve_active_generation_uplift_prerequisites(gen or None)
        compiler_gate = {
            "generation_id": prereqs.get("generation_id"),
            "gate_passed": prereqs.get("gate_passed"),
            "stale_binding": prereqs.get("stale_binding"),
            "stale_binding_reason": prereqs.get("stale_binding_reason"),
            "passed": bool(prereqs.get("uplift_prerequisites_met")),
        }
        if gen and uplift_report is not None:
            report_gen = str(uplift_report.get("generation_id") or "").strip()
            if report_gen and report_gen != gen:
                compiler_gate["passed"] = False
                compiler_gate["stale_binding"] = True
                compiler_gate["stale_binding_reason"] = "uplift_report_generation_mismatch"
        report["compiler_gate"] = compiler_gate
        gates_passed.append(compiler_gate["passed"])
        if not compiler_gate["passed"]:
            rc_parts.append(2)

    if gate.get("passed") is False:
        rc_parts.append(2)

    rc = 0 if all(gates_passed) else 2
    report["unified_gate_passed"] = rc == 0
    return report, rc


def main() -> int:
    parser = argparse.ArgumentParser(description="Ready-to-use graph expansion quality gate")
    parser.add_argument("--jsonl", type=str, default=None, help="Путь к metrics_store.jsonl")
    parser.add_argument("--limit", type=int, default=2000, help="Последние N request-событий (0 = все)")
    parser.add_argument(
        "--profile",
        type=str,
        choices=("local", "strict"),
        default="local",
        help="Набор рекомендуемых порогов: local или strict",
    )
    parser.add_argument("--min-events", type=int, default=None, help="Переопределить минимум graph_expansion событий")
    parser.add_argument("--max-p95-ms", type=float, default=None, help="Переопределить максимум p95 graph_expansion_ms")
    parser.add_argument("--min-applied-rate", type=float, default=None, help="Переопределить минимум applied_rate")
    parser.add_argument("--max-error-rate", type=float, default=None, help="Переопределить максимум error_rate")
    parser.add_argument(
        "--min-avg-extra-chunks",
        type=float,
        default=None,
        help="Переопределить минимум avg_extra_chunks_when_applied",
    )
    parser.add_argument(
        "--uplift-report",
        type=str,
        default=None,
        help="Путь к serialized graph uplift report JSON",
    )
    parser.add_argument(
        "--generation-id",
        type=str,
        default=None,
        help="Active generation_id for compiler/uplift binding checks",
    )
    parser.add_argument("--json-out", action="store_true", help="Печать только JSON")
    args = parser.parse_args()

    report, rc = run_gate(
        jsonl_path=args.jsonl,
        limit=args.limit,
        profile=args.profile,
        min_events=args.min_events,
        max_p95_ms=args.max_p95_ms,
        min_applied_rate=args.min_applied_rate,
        max_error_rate=args.max_error_rate,
        min_avg_extra_chunks=args.min_avg_extra_chunks,
        uplift_report_path=args.uplift_report,
        generation_id=args.generation_id,
    )

    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"Graph expansion gate ({report['gate_profile']}): {verdict}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
