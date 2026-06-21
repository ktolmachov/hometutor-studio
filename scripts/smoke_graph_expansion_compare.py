#!/usr/bin/env python3
"""
Smoke-runner для graph off/on сравнения: сам генерирует два окна и печатает compare-report.

Запуск из корня репозитория:
  python scripts/smoke_graph_expansion_compare.py
  python scripts/smoke_graph_expansion_compare.py --requests 32 --json-out
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _generate_smoke_events_quietly(*, json_out: bool, **kwargs: object) -> dict[str, object]:
    from scripts.smoke_graph_expansion_gate import generate_graph_expansion_smoke_events

    if not json_out:
        return generate_graph_expansion_smoke_events(**kwargs)
    with io.StringIO() as stdout_buffer, io.StringIO() as stderr_buffer:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            return generate_graph_expansion_smoke_events(**kwargs)


def main() -> int:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description="Generate smoke off/on windows and compare graph expansion deltas")
    parser.add_argument("--requests", type=int, default=32, help="Сколько request-событий сгенерировать на каждую сторону")
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(ROOT / "logs"),
        help="Каталог для smoke JSONL off/on",
    )
    parser.add_argument("--baseline-label", type=str, default="graph_off")
    parser.add_argument("--candidate-label", type=str, default="graph_on")
    parser.add_argument(
        "--preset",
        type=str,
        default=None,
        help="Готовый сценарий compare-gate; см. graph_expansion_compare.py --preset",
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=("local", "strict"),
        default=None,
        help="Профиль compare-gate для delta latency/quality",
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
    parser.add_argument(
        "--query-types",
        type=str,
        default="synthesis,learning_plan",
        help="Comma-separated query_type values for smoke traffic (default: synthesis,learning_plan)",
    )
    args = parser.parse_args()

    from scripts.graph_expansion_compare import (
        _parse_gate_query_type_profiles,
        _normalize_query_type,
        resolve_compare_gate_preset,
        build_compare_report,
        build_summary_from_jsonl_path,
        evaluate_compare_gate,
        resolve_compare_gate_thresholds,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = out_dir / "graph_expansion_smoke_off.jsonl"
    candidate_path = out_dir / "graph_expansion_smoke_on.jsonl"
    requests = max(1, int(args.requests))

    baseline_smoke = _generate_smoke_events_quietly(
        json_out=args.json_out,
        jsonl_path=baseline_path,
        request_count=requests,
        graph_mode="off",
        query_types=args.query_types,
    )
    candidate_smoke = _generate_smoke_events_quietly(
        json_out=args.json_out,
        jsonl_path=candidate_path,
        request_count=requests,
        graph_mode="on",
        query_types=args.query_types,
    )

    baseline = build_summary_from_jsonl_path(Path(baseline_smoke["jsonl_path"]), limit_last=None)
    candidate = build_summary_from_jsonl_path(Path(candidate_smoke["jsonl_path"]), limit_last=None)
    report = build_compare_report(
        baseline=baseline,
        candidate=candidate,
        baseline_label=args.baseline_label,
        candidate_label=args.candidate_label,
    )
    try:
        preset = resolve_compare_gate_preset(args.preset)
        parsed_profile_map = _parse_gate_query_type_profiles(args.gate_query_type_profile)
    except ValueError as e:
        print(f"smoke compare failed: {type(e).__name__}: {e}", file=sys.stderr)
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
    query_type_profile_map = {
        **(
            dict(preset.get("gate_query_type_profiles") or {})
            if isinstance(preset.get("gate_query_type_profiles"), dict)
            else {}
        ),
        **parsed_profile_map,
    }
    gate_query_types: list[str] = []
    for item in preset.get("gate_query_types") or []:
        normalized = _normalize_query_type(item)
        if normalized and normalized not in gate_query_types:
            gate_query_types.append(normalized)
    for item in args.gate_query_type or []:
        normalized = _normalize_query_type(item)
        if normalized and normalized not in gate_query_types:
            gate_query_types.append(normalized)
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
    compare_gate = evaluate_compare_gate(
        report,
        gate_query_types=gate_query_types,
        query_type_threshold_overrides=query_type_threshold_overrides,
        **thresholds,
    )
    report["compare_gate_preset"] = args.preset
    report["compare_gate_profile"] = effective_profile
    report["compare_gate_thresholds"] = thresholds
    report["compare_gate_query_types"] = gate_query_types
    report["compare_gate_query_type_profiles"] = query_type_profile_map
    report["compare_gate"] = compare_gate
    payload = {
        "baseline_smoke": baseline_smoke,
        "candidate_smoke": candidate_smoke,
        "compare": report,
    }

    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Smoke graph compare: {args.baseline_label} -> {args.candidate_label}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.enforce_gate and not compare_gate.get("passed"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
