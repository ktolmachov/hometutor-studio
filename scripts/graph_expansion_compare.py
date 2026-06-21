#!/usr/bin/env python3
"""
Сравнение двух прогонов / окон по graph expansion и общей latency.

Запуск из корня репозитория:
  python scripts/graph_expansion_compare.py --baseline-jsonl logs/off.jsonl --candidate-jsonl logs/on.jsonl
  python scripts/graph_expansion_compare.py --baseline-metrics-url http://127.0.0.1:8000/metrics --candidate-jsonl logs/on.jsonl
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

LOCAL_COMPARE_GATE_DEFAULTS = {
    "min_events_each": 10,
    "max_p95_total_answer_regression_pct": 10.0,
    "min_applied_rate_lift": 0.10,
    "max_error_rate_increase": 0.02,
}

STRICT_COMPARE_GATE_DEFAULTS = {
    "min_events_each": 30,
    "max_p95_total_answer_regression_pct": 5.0,
    "min_applied_rate_lift": 0.20,
    "max_error_rate_increase": 0.01,
}

COMPARE_GATE_PRESETS = {
    "overall-local": {
        "profile": "local",
        "gate_query_types": [],
        "gate_query_type_profiles": {},
    },
    "overall-strict": {
        "profile": "strict",
        "gate_query_types": [],
        "gate_query_type_profiles": {},
    },
    "synthesis-local": {
        "profile": "local",
        "gate_query_types": ["synthesis"],
        "gate_query_type_profiles": {"synthesis": "local"},
    },
    "synthesis-strict": {
        "profile": "local",
        "gate_query_types": ["synthesis"],
        "gate_query_type_profiles": {"synthesis": "strict"},
    },
    "learning-plan-local": {
        "profile": "local",
        "gate_query_types": ["learning_plan"],
        "gate_query_type_profiles": {"learning_plan": "local"},
    },
    "learning-plan-strict": {
        "profile": "local",
        "gate_query_types": ["learning_plan"],
        "gate_query_type_profiles": {"learning_plan": "strict"},
    },
    "dual-local": {
        "profile": "local",
        "gate_query_types": ["synthesis", "learning_plan"],
        "gate_query_type_profiles": {"synthesis": "local", "learning_plan": "local"},
    },
    "dual-strict": {
        "profile": "local",
        "gate_query_types": ["synthesis", "learning_plan"],
        "gate_query_type_profiles": {"synthesis": "strict", "learning_plan": "strict"},
    },
}


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(round(percentile * (len(ordered) - 1)))
    return round(ordered[idx], 3)


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _normalize_query_type(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_gate_query_type_profiles(values: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in values or []:
        text = str(raw or "").strip()
        if not text:
            continue
        if "=" in text:
            query_type, profile = text.split("=", 1)
        elif ":" in text:
            query_type, profile = text.split(":", 1)
        else:
            raise ValueError(f"Invalid gate query-type profile: {raw!r}")
        normalized_query_type = _normalize_query_type(query_type)
        normalized_profile = str(profile or "").strip().lower()
        if not normalized_query_type or normalized_profile not in {"local", "strict"}:
            raise ValueError(f"Invalid gate query-type profile: {raw!r}")
        out[normalized_query_type] = normalized_profile
    return out


def resolve_compare_gate_preset(name: str | None) -> dict[str, Any]:
    if not name:
        return {}
    preset = COMPARE_GATE_PRESETS.get(str(name).strip().lower())
    if not isinstance(preset, dict):
        raise ValueError(f"Unknown compare gate preset: {name!r}")
    return {
        "profile": preset.get("profile"),
        "gate_query_types": list(preset.get("gate_query_types") or []),
        "gate_query_type_profiles": dict(preset.get("gate_query_type_profiles") or {}),
    }


def summarize_request_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    from scripts import graph_expansion_benchmark as benchmark

    total_answer_latencies = [
        float(latency.get("total_answer_ms"))
        for item in events
        if isinstance(item, dict)
        and isinstance((latency := (item.get("latency_ms") or {})), dict)
        and latency.get("total_answer_ms") is not None
    ]
    pipeline_latencies = [
        float(latency.get("pipeline_ms"))
        for item in events
        if isinstance(item, dict)
        and isinstance((latency := (item.get("latency_ms") or {})), dict)
        and latency.get("pipeline_ms") is not None
    ]
    return {
        "request_events_in_window": len(events),
        "latency_ms": {
            "avg_total_answer_ms": _avg(total_answer_latencies),
            "p95_total_answer_ms": _percentile(total_answer_latencies, 0.95),
            "avg_pipeline_ms": _avg(pipeline_latencies),
            "p95_pipeline_ms": _percentile(pipeline_latencies, 0.95),
        },
        "graph_expansion": benchmark.build_report_from_events(events),
    }


def build_summary_from_jsonl_path(path: Path, *, limit_last: int | None) -> dict[str, Any]:
    from scripts import graph_expansion_benchmark as benchmark

    events = benchmark._load_request_events_from_jsonl(path, limit_last=limit_last)
    summary = summarize_request_events(events)
    summary["source"] = "jsonl"
    summary["jsonl_path"] = str(path.resolve())
    return summary


def build_summary_from_metrics_payload(payload: Any, *, metrics_url: str) -> dict[str, Any]:
    from scripts import graph_expansion_benchmark as benchmark

    latency = payload.get("latency_ms") if isinstance(payload, dict) else None
    if not isinstance(latency, dict):
        latency = {}
    summary = {
        "source": "http",
        "metrics_url": metrics_url,
        "request_events_in_window": payload.get("requests_total") if isinstance(payload, dict) else None,
        "latency_ms": {
            "avg_total_answer_ms": _safe_float(latency.get("avg_total_answer_ms")),
            "p95_total_answer_ms": _safe_float(latency.get("p95_total_answer_ms")),
            "avg_pipeline_ms": _safe_float(latency.get("avg_pipeline_ms")),
            "p95_pipeline_ms": _safe_float(latency.get("p95_pipeline_ms")),
        },
        "graph_expansion": benchmark.build_report_from_metrics_payload(payload),
    }
    return summary


def _metric_delta(
    baseline: Any,
    candidate: Any,
    *,
    higher_is_better: bool,
) -> dict[str, Any]:
    b = _safe_float(baseline)
    c = _safe_float(candidate)
    if b is None or c is None:
        return {
            "baseline": b,
            "candidate": c,
            "delta_abs": None,
            "delta_pct": None,
            "verdict": "n/a",
        }
    delta_abs = round(c - b, 4)
    delta_pct = round(((c - b) / b) * 100.0, 2) if b != 0 else None
    if delta_abs == 0:
        verdict = "same"
    elif (delta_abs > 0 and higher_is_better) or (delta_abs < 0 and not higher_is_better):
        verdict = "better"
    else:
        verdict = "worse"
    return {
        "baseline": b,
        "candidate": c,
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
        "verdict": verdict,
    }


def _graph_expansion_metric_deltas(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "events_total": _metric_delta(
            baseline.get("events_total"),
            candidate.get("events_total"),
            higher_is_better=True,
        ),
        "p95_graph_expansion_ms": _metric_delta(
            baseline.get("p95_graph_expansion_ms"),
            candidate.get("p95_graph_expansion_ms"),
            higher_is_better=False,
        ),
        "applied_rate": _metric_delta(
            baseline.get("applied_rate"),
            candidate.get("applied_rate"),
            higher_is_better=True,
        ),
        "skipped_rate": _metric_delta(
            baseline.get("skipped_rate"),
            candidate.get("skipped_rate"),
            higher_is_better=False,
        ),
        "error_rate": _metric_delta(
            baseline.get("error_rate"),
            candidate.get("error_rate"),
            higher_is_better=False,
        ),
        "avg_extra_chunks_when_applied": _metric_delta(
            baseline.get("avg_extra_chunks_when_applied"),
            candidate.get("avg_extra_chunks_when_applied"),
            higher_is_better=True,
        ),
    }


def _counter_compare(
    baseline: Any,
    candidate: Any,
    *,
    higher_is_better: bool = False,
) -> dict[str, dict[str, Any]]:
    bmap = baseline if isinstance(baseline, dict) else {}
    cmap = candidate if isinstance(candidate, dict) else {}
    keys = sorted({str(key) for key in bmap.keys()} | {str(key) for key in cmap.keys()})
    out: dict[str, dict[str, Any]] = {}
    for key in keys:
        out[key] = _metric_delta(bmap.get(key), cmap.get(key), higher_is_better=higher_is_better)
    return out


def _query_type_compare(
    baseline_ge: dict[str, Any],
    candidate_ge: dict[str, Any],
) -> dict[str, Any]:
    bq = baseline_ge.get("by_query_type") if isinstance(baseline_ge.get("by_query_type"), dict) else {}
    cq = candidate_ge.get("by_query_type") if isinstance(candidate_ge.get("by_query_type"), dict) else {}
    out: dict[str, Any] = {}
    for query_type in sorted({str(key) for key in bq.keys()} | {str(key) for key in cq.keys()}):
        b_bucket = bq.get(query_type) if isinstance(bq.get(query_type), dict) else {}
        c_bucket = cq.get(query_type) if isinstance(cq.get(query_type), dict) else {}
        out[query_type] = {
            "baseline": b_bucket,
            "candidate": c_bucket,
            "delta": _graph_expansion_metric_deltas(b_bucket, c_bucket),
            "counter_compare": {
                "skip_reasons": _counter_compare(b_bucket.get("skip_reasons"), c_bucket.get("skip_reasons")),
                "error_types": _counter_compare(b_bucket.get("error_types"), c_bucket.get("error_types")),
            },
        }
    return out


def build_compare_report(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_label: str,
    candidate_label: str,
) -> dict[str, Any]:
    b_lat = baseline.get("latency_ms") or {}
    c_lat = candidate.get("latency_ms") or {}
    b_ge = baseline.get("graph_expansion") or {}
    c_ge = candidate.get("graph_expansion") or {}
    delta = {
        "latency_ms": {
            "p95_total_answer_ms": _metric_delta(
                b_lat.get("p95_total_answer_ms"),
                c_lat.get("p95_total_answer_ms"),
                higher_is_better=False,
            ),
            "avg_total_answer_ms": _metric_delta(
                b_lat.get("avg_total_answer_ms"),
                c_lat.get("avg_total_answer_ms"),
                higher_is_better=False,
            ),
        },
        "graph_expansion": _graph_expansion_metric_deltas(b_ge, c_ge),
    }
    return {
        "baseline_label": baseline_label,
        "candidate_label": candidate_label,
        "baseline": baseline,
        "candidate": candidate,
        "delta": delta,
        "graph_expansion_counter_compare": {
            "skip_reasons": _counter_compare(b_ge.get("skip_reasons"), c_ge.get("skip_reasons")),
            "error_types": _counter_compare(b_ge.get("error_types"), c_ge.get("error_types")),
        },
        "query_type_compare": _query_type_compare(b_ge, c_ge),
    }


def resolve_compare_gate_thresholds(
    *,
    profile: str,
    min_events_each: int | None = None,
    max_p95_total_answer_regression_pct: float | None = None,
    min_applied_rate_lift: float | None = None,
    max_error_rate_increase: float | None = None,
) -> dict[str, Any]:
    base = STRICT_COMPARE_GATE_DEFAULTS if profile == "strict" else LOCAL_COMPARE_GATE_DEFAULTS
    out = dict(base)
    overrides = {
        "min_events_each": min_events_each,
        "max_p95_total_answer_regression_pct": max_p95_total_answer_regression_pct,
        "min_applied_rate_lift": min_applied_rate_lift,
        "max_error_rate_increase": max_error_rate_increase,
    }
    for key, value in overrides.items():
        if value is not None:
            out[key] = value
    return out


def evaluate_compare_gate(
    report: dict[str, Any],
    *,
    min_events_each: int,
    max_p95_total_answer_regression_pct: float,
    min_applied_rate_lift: float,
    max_error_rate_increase: float,
    gate_query_types: list[str] | None = None,
    query_type_threshold_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base_thresholds = {
        "min_events_each": int(min_events_each),
        "max_p95_total_answer_regression_pct": float(max_p95_total_answer_regression_pct),
        "min_applied_rate_lift": float(min_applied_rate_lift),
        "max_error_rate_increase": float(max_error_rate_increase),
    }

    def _evaluate_scope(
        *,
        baseline_ge: dict[str, Any],
        candidate_ge: dict[str, Any],
        latency_delta: dict[str, Any],
        applied_delta: dict[str, Any],
        error_delta: dict[str, Any],
        thresholds: dict[str, Any],
    ) -> dict[str, Any]:
        baseline_events = int(baseline_ge.get("events_total") or 0)
        candidate_events = int(candidate_ge.get("events_total") or 0)
        applied_lift = _safe_float(applied_delta.get("delta_abs"))
        p95_regression_pct = _safe_float(latency_delta.get("delta_pct"))
        error_rate_increase = _safe_float(error_delta.get("delta_abs"))

        sufficient_events = baseline_events >= int(thresholds["min_events_each"]) and candidate_events >= int(
            thresholds["min_events_each"]
        )
        p95_regression_within_budget = (
            p95_regression_pct is not None
            and p95_regression_pct <= float(thresholds["max_p95_total_answer_regression_pct"])
        )
        applied_lift_justifies_regression = (
            applied_lift is not None and applied_lift >= float(thresholds["min_applied_rate_lift"])
        )
        error_rate_within_budget = (
            error_rate_increase is None or error_rate_increase <= float(thresholds["max_error_rate_increase"])
        )

        checks = {
            "events_each": {
                "passed": sufficient_events,
                "baseline_events": baseline_events,
                "candidate_events": candidate_events,
                "min_required": int(thresholds["min_events_each"]),
            },
            "p95_total_answer_regression": {
                "passed": bool(p95_regression_within_budget or applied_lift_justifies_regression),
                "delta_pct": p95_regression_pct,
                "max_regression_pct": float(thresholds["max_p95_total_answer_regression_pct"]),
                "applied_rate_lift": applied_lift,
                "min_applied_rate_lift": float(thresholds["min_applied_rate_lift"]),
                "justified_by_applied_rate_lift": bool(
                    not p95_regression_within_budget and applied_lift_justifies_regression
                ),
            },
            "error_rate_increase": {
                "passed": error_rate_within_budget,
                "delta_abs": error_rate_increase,
                "max_increase": float(thresholds["max_error_rate_increase"]),
            },
        }
        return {
            "passed": all(item.get("passed") for item in checks.values()),
            "checks": checks,
            "latency_scope": "overall_window",
            "thresholds": dict(thresholds),
        }

    baseline = report.get("baseline") or {}
    candidate = report.get("candidate") or {}
    baseline_ge = baseline.get("graph_expansion") or {}
    candidate_ge = candidate.get("graph_expansion") or {}
    delta = report.get("delta") or {}
    overall = _evaluate_scope(
        baseline_ge=baseline_ge,
        candidate_ge=candidate_ge,
        latency_delta=(delta.get("latency_ms") or {}).get("p95_total_answer_ms") or {},
        applied_delta=(delta.get("graph_expansion") or {}).get("applied_rate") or {},
        error_delta=(delta.get("graph_expansion") or {}).get("error_rate") or {},
        thresholds=base_thresholds,
    )

    normalized_query_types: list[str] = []
    for item in gate_query_types or []:
        text = _normalize_query_type(item)
        if text and text not in normalized_query_types:
            normalized_query_types.append(text)

    query_type_results: dict[str, Any] = {}
    query_type_compare = report.get("query_type_compare") if isinstance(report.get("query_type_compare"), dict) else {}
    for query_type in normalized_query_types:
        scoped = query_type_compare.get(query_type) if isinstance(query_type_compare.get(query_type), dict) else {}
        thresholds = dict(base_thresholds)
        if isinstance(query_type_threshold_overrides, dict) and isinstance(
            query_type_threshold_overrides.get(query_type), dict
        ):
            thresholds.update(query_type_threshold_overrides[query_type])
        query_type_results[query_type] = _evaluate_scope(
            baseline_ge=scoped.get("baseline") if isinstance(scoped.get("baseline"), dict) else {},
            candidate_ge=scoped.get("candidate") if isinstance(scoped.get("candidate"), dict) else {},
            latency_delta=(delta.get("latency_ms") or {}).get("p95_total_answer_ms") or {},
            applied_delta=(scoped.get("delta") or {}).get("applied_rate") or {},
            error_delta=(scoped.get("delta") or {}).get("error_rate") or {},
            thresholds=thresholds,
        )

    passed = overall.get("passed") is True and all(item.get("passed") is True for item in query_type_results.values())
    return {
        "passed": passed,
        "checks": overall["checks"],
        "thresholds": overall["thresholds"],
        "query_type_checks": query_type_results,
        "gate_query_types": normalized_query_types,
    }


def _load_summary(
    *,
    jsonl_path: str | None,
    metrics_url: str | None,
    limit: int,
    timeout_sec: float,
) -> dict[str, Any]:
    from scripts import graph_expansion_benchmark as benchmark

    if bool(jsonl_path) == bool(metrics_url):
        raise ValueError("Specify exactly one of jsonl_path or metrics_url for each side")
    if jsonl_path:
        lim = None if limit <= 0 else int(limit)
        return build_summary_from_jsonl_path(Path(jsonl_path), limit_last=lim)
    payload = benchmark._fetch_metrics_json(str(metrics_url).strip(), timeout_sec=timeout_sec)
    return build_summary_from_metrics_payload(payload, metrics_url=str(metrics_url).strip())


def main() -> int:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description="Compare graph expansion quality and latency between two runs/windows")
    parser.add_argument("--baseline-jsonl", type=str, default=None)
    parser.add_argument("--candidate-jsonl", type=str, default=None)
    parser.add_argument("--baseline-metrics-url", type=str, default=None)
    parser.add_argument("--candidate-metrics-url", type=str, default=None)
    parser.add_argument("--baseline-limit", type=int, default=2000)
    parser.add_argument("--candidate-limit", type=int, default=2000)
    parser.add_argument("--baseline-label", type=str, default="baseline")
    parser.add_argument("--candidate-label", type=str, default="candidate")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--preset",
        type=str,
        choices=tuple(sorted(COMPARE_GATE_PRESETS.keys())),
        default=None,
        help="Готовый сценарий compare-gate: overall/local/strict, synthesis/local/strict, learning-plan/local/strict, dual-local, dual-strict",
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=("local", "strict"),
        default=None,
        help="Профиль compare-gate; используется вместе с --enforce-gate или для печати compare_gate в JSON",
    )
    parser.add_argument("--min-events-each", type=int, default=None)
    parser.add_argument("--max-p95-total-answer-regression-pct", type=float, default=None)
    parser.add_argument("--min-applied-rate-lift", type=float, default=None)
    parser.add_argument("--max-error-rate-increase", type=float, default=None)
    parser.add_argument(
        "--gate-query-type",
        action="append",
        default=None,
        help="Дополнительно валидировать compare-gate для конкретного query_type; можно повторять",
    )
    parser.add_argument(
        "--gate-query-type-profile",
        action="append",
        default=None,
        help="Профиль для targeted gate в формате query_type=local|strict; можно повторять",
    )
    parser.add_argument("--enforce-gate", action="store_true")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    try:
        baseline = _load_summary(
            jsonl_path=args.baseline_jsonl,
            metrics_url=args.baseline_metrics_url,
            limit=args.baseline_limit,
            timeout_sec=args.timeout,
        )
        candidate = _load_summary(
            jsonl_path=args.candidate_jsonl,
            metrics_url=args.candidate_metrics_url,
            limit=args.candidate_limit,
            timeout_sec=args.timeout,
        )
    except Exception as e:
        print(f"compare failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    report = build_compare_report(
        baseline=baseline,
        candidate=candidate,
        baseline_label=args.baseline_label,
        candidate_label=args.candidate_label,
    )
    compare_gate = None
    if args.profile or args.enforce_gate or args.preset or args.gate_query_type or args.gate_query_type_profile:
        try:
            preset = resolve_compare_gate_preset(args.preset)
            query_type_profile_map = _parse_gate_query_type_profiles(args.gate_query_type_profile)
        except ValueError as e:
            print(f"compare failed: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
        effective_profile = (
            str(args.profile).strip().lower()
            if args.profile
            else str(preset.get("profile") or "local").strip().lower()
        )
        thresholds = resolve_compare_gate_thresholds(
            profile=effective_profile,
            min_events_each=args.min_events_each,
            max_p95_total_answer_regression_pct=args.max_p95_total_answer_regression_pct,
            min_applied_rate_lift=args.min_applied_rate_lift,
            max_error_rate_increase=args.max_error_rate_increase,
        )
        gate_query_types: list[str] = []
        for item in preset.get("gate_query_types") or []:
            normalized = _normalize_query_type(item)
            if normalized and normalized not in gate_query_types:
                gate_query_types.append(normalized)
        for item in args.gate_query_type or []:
            normalized = _normalize_query_type(item)
            if normalized and normalized not in gate_query_types:
                gate_query_types.append(normalized)
        preset_profile_map = preset.get("gate_query_type_profiles") if isinstance(
            preset.get("gate_query_type_profiles"), dict
        ) else {}
        query_type_profile_map = {**preset_profile_map, **query_type_profile_map}
        for query_type in query_type_profile_map.keys():
            if query_type not in gate_query_types:
                gate_query_types.append(query_type)
        query_type_threshold_overrides = {
            query_type: resolve_compare_gate_thresholds(
                profile=profile,
                min_events_each=args.min_events_each,
                max_p95_total_answer_regression_pct=args.max_p95_total_answer_regression_pct,
                min_applied_rate_lift=args.min_applied_rate_lift,
                max_error_rate_increase=args.max_error_rate_increase,
            )
            for query_type, profile in query_type_profile_map.items()
        }
        report["compare_gate_preset"] = args.preset
        report["compare_gate_profile"] = effective_profile
        report["compare_gate_thresholds"] = thresholds
        report["compare_gate_query_types"] = gate_query_types
        report["compare_gate_query_type_profiles"] = query_type_profile_map
        compare_gate = evaluate_compare_gate(
            report,
            gate_query_types=gate_query_types,
            query_type_threshold_overrides=query_type_threshold_overrides,
            **thresholds,
        )
        report["compare_gate"] = compare_gate
    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Graph expansion compare: {args.baseline_label} -> {args.candidate_label}")
        print("=" * 64)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.enforce_gate and compare_gate and not compare_gate.get("passed"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
