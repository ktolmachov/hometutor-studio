#!/usr/bin/env python3
"""
Отчёт latency/quality по graph expansion: in-process aggregates из JSONL или снимок GET /metrics.

Запуск из корня репозитория:
  python scripts/graph_expansion_benchmark.py
  python scripts/graph_expansion_benchmark.py --jsonl logs/metrics_store.jsonl --limit 500
  python scripts/graph_expansion_benchmark.py --metrics-url http://127.0.0.1:8000/metrics

Переменные окружения: METRICS_STORE_PATH (как в app.metrics), иначе data/logs под BASE_DIR.
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


def _load_request_events_from_jsonl(path: Path, *, limit_last: int | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.is_file():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("event_type") == "request":
                out.append(obj)
    if limit_last is not None and limit_last > 0 and len(out) > limit_last:
        out = out[-limit_last:]
    return out


def _fetch_metrics_json(url: str, *, timeout_sec: float) -> dict[str, Any]:
    try:
        import urllib.error
        import urllib.request
    except ImportError as e:
        raise RuntimeError(str(e)) from e
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _normalize_counter_map(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    pairs: list[tuple[str, int]] = []
    for key, value in raw.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        pairs.append((str(key), count))
    pairs.sort(key=lambda item: (-item[1], item[0]))
    return {key: value for key, value in pairs}


def normalize_graph_expansion_summary(raw: Any) -> dict[str, Any]:
    """Нормализует summary graph expansion и достраивает rate-поля для старых payload."""
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)
    events = _safe_int(out.get("events_total")) or 0
    applied = _safe_int(out.get("applied_total")) or 0
    skipped = _safe_int(out.get("skipped_total")) or 0
    errors = _safe_int(out.get("error_total")) or 0
    unknown = _safe_int(out.get("unknown_outcome_total")) or 0
    out["events_total"] = events
    out["applied_total"] = applied
    out["skipped_total"] = skipped
    out["error_total"] = errors
    out["unknown_outcome_total"] = unknown
    if out.get("applied_rate") is None:
        out["applied_rate"] = _round_rate(applied, events)
    if out.get("skipped_rate") is None:
        out["skipped_rate"] = _round_rate(skipped, events)
    if out.get("error_rate") is None:
        out["error_rate"] = _round_rate(errors, events)
    if out.get("unknown_outcome_rate") is None:
        out["unknown_outcome_rate"] = _round_rate(unknown, events)
    out["skip_reasons"] = _normalize_counter_map(out.get("skip_reasons"))
    out["error_types"] = _normalize_counter_map(out.get("error_types"))
    by_query_type = out.get("by_query_type")
    if isinstance(by_query_type, dict):
        out["by_query_type"] = {
            str(query_type): normalize_graph_expansion_summary(value)
            for query_type, value in sorted(by_query_type.items())
            if isinstance(value, dict)
        }
    return out


def evaluate_quality_gate(
    summary: dict[str, Any],
    *,
    min_events: int | None = None,
    max_p95_ms: float | None = None,
    min_applied_rate: float | None = None,
    max_error_rate: float | None = None,
    min_avg_extra_chunks: float | None = None,
) -> dict[str, Any]:
    normalized = normalize_graph_expansion_summary(summary)
    configured = any(
        value is not None
        for value in (
            min_events,
            max_p95_ms,
            min_applied_rate,
            max_error_rate,
            min_avg_extra_chunks,
        )
    )
    checks: list[dict[str, Any]] = []

    def add_check(metric: str, *, threshold: float, operator: str) -> None:
        actual = _safe_float(normalized.get(metric))
        if actual is None:
            passed = False
        elif operator == ">=":
            passed = actual >= threshold
        elif operator == "<=":
            passed = actual <= threshold
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        checks.append(
            {
                "metric": metric,
                "operator": operator,
                "threshold": threshold,
                "actual": actual,
                "passed": passed,
            }
        )

    if min_events is not None:
        add_check("events_total", threshold=float(min_events), operator=">=")
    if max_p95_ms is not None:
        add_check("p95_graph_expansion_ms", threshold=float(max_p95_ms), operator="<=")
    if min_applied_rate is not None:
        add_check("applied_rate", threshold=float(min_applied_rate), operator=">=")
    if max_error_rate is not None:
        add_check("error_rate", threshold=float(max_error_rate), operator="<=")
    if min_avg_extra_chunks is not None:
        add_check(
            "avg_extra_chunks_when_applied",
            threshold=float(min_avg_extra_chunks),
            operator=">=",
        )

    failed_checks = [item for item in checks if not item["passed"]]
    return {
        "configured": configured,
        "passed": None if not configured else not failed_checks,
        "checks": checks,
        "failed_checks": failed_checks,
    }


def build_report_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    from app.metrics import aggregate_graph_expansion_from_request_events

    rollup = aggregate_graph_expansion_from_request_events(events)
    return normalize_graph_expansion_summary(rollup)


def build_report_from_jsonl_path(path: Path, *, limit_last: int | None) -> tuple[dict[str, Any], int]:
    events = _load_request_events_from_jsonl(path, limit_last=limit_last)
    return build_report_from_events(events), len(events)


def build_report_from_metrics_payload(payload: Any) -> dict[str, Any]:
    ge = payload.get("graph_expansion") if isinstance(payload, dict) else None
    return normalize_graph_expansion_summary(ge)


def main() -> int:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description="Graph expansion latency/quality benchmark report")
    parser.add_argument(
        "--jsonl",
        type=str,
        default=None,
        help="Путь к metrics_store.jsonl (по умолчанию METRICS_STORE_PATH из app.metrics)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2000,
        help="Последние N request-событий из JSONL (0 = все)",
    )
    parser.add_argument(
        "--metrics-url",
        type=str,
        default=None,
        help="Если задан — GET JSON и печать graph_expansion из ответа (in-memory процесса API)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout для --metrics-url",
    )
    parser.add_argument(
        "--json-out",
        action="store_true",
        help="Печать только JSON (без текстового заголовка)",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=None,
        help="Quality gate: минимум request-событий с graph_expansion в окне",
    )
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=None,
        help="Quality gate: максимум p95 latency для graph_expansion_ms",
    )
    parser.add_argument(
        "--min-applied-rate",
        type=float,
        default=None,
        help="Quality gate: минимум applied_rate",
    )
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=None,
        help="Quality gate: максимум error_rate",
    )
    parser.add_argument(
        "--min-avg-extra-chunks",
        type=float,
        default=None,
        help="Quality gate: минимум avg_extra_chunks_when_applied",
    )
    args = parser.parse_args()

    from app.metrics import METRICS_STORE_PATH

    if args.metrics_url:
        try:
            payload = _fetch_metrics_json(args.metrics_url.strip(), timeout_sec=args.timeout)
        except Exception as e:
            print(f"HTTP metrics failed: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
        report = {
            "source": "http",
            "metrics_url": args.metrics_url.strip(),
            "graph_expansion": build_report_from_metrics_payload(payload),
        }
    else:
        path = Path(args.jsonl) if args.jsonl else Path(METRICS_STORE_PATH)
        lim = None if (args.limit is None or args.limit <= 0) else int(args.limit)
        ge_report, event_count = build_report_from_jsonl_path(path, limit_last=lim)
        report = {
            "source": "jsonl",
            "jsonl_path": str(path.resolve()),
            "request_events_in_window": event_count,
            "graph_expansion": ge_report,
        }

    gate = evaluate_quality_gate(
        report.get("graph_expansion") or {},
        min_events=args.min_events,
        max_p95_ms=args.max_p95_ms,
        min_applied_rate=args.min_applied_rate,
        max_error_rate=args.max_error_rate,
        min_avg_extra_chunks=args.min_avg_extra_chunks,
    )
    if gate["configured"]:
        report["quality_gate"] = gate

    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Graph expansion: latency / quality")
        print("=" * 48)
        if gate["configured"]:
            verdict = "PASS" if gate["passed"] else "FAIL"
            print(f"Quality gate: {verdict}")
            if gate["failed_checks"]:
                failed = ", ".join(
                    f"{item['metric']} {item['operator']} {item['threshold']} (actual={item['actual']})"
                    for item in gate["failed_checks"]
                )
                print(f"Failed checks: {failed}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if gate["configured"] and gate["passed"] is False:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
