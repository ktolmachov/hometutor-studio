#!/usr/bin/env python3
"""
Smoke script: генерирует graph expansion request-события через /ask и сразу запускает gate.

Запуск из корня репозитория:
  python scripts/smoke_graph_expansion_gate.py
  python scripts/smoke_graph_expansion_gate.py --profile strict
  python scripts/smoke_graph_expansion_gate.py --jsonl-out logs/graph_expansion_smoke.jsonl --requests 16
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _parse_query_types(raw: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if raw is None:
        return ["synthesis", "learning_plan"]
    if isinstance(raw, str):
        items = raw.split(",")
    else:
        items = list(raw)
    out: list[str] = []
    for item in items:
        text = str(item or "").strip().lower()
        if text and text not in out:
            out.append(text)
    return out or ["synthesis", "learning_plan"]


def _stub_answer_factory(*, graph_mode: str = "on", query_types: list[str] | None = None) -> Any:
    counter = {"value": 0}
    normalized_query_types = _parse_query_types(query_types)

    def _answer_question(question: str, _options: Any) -> dict[str, Any]:
        idx = counter["value"]
        counter["value"] += 1
        mode = str(graph_mode or "on").strip().lower()
        query_type = normalized_query_types[idx % len(normalized_query_types)]
        if mode == "off":
            ge = {
                "skipped": True,
                "reason": "feature_disabled",
                "graph_expansion_ms": 2.0,
                "max_hops": 0,
            }
            total_answer_ms = 52.0
            query_execute_ms = 31.0
        else:
            if query_type not in {"synthesis", "learning_plan"}:
                ge = {
                    "skipped": True,
                    "reason": "query_type",
                    "graph_expansion_ms": 5.0,
                    "max_hops": 3,
                    "seed_doc_ids": ["doc1.md"],
                }
                total_answer_ms = 54.0
                query_execute_ms = 32.0
            else:
                applied = (idx % 4) != 3
                if query_type == "learning_plan":
                    applied = (idx % 3) != 2
                if applied:
                    base_ms = 24.0 if query_type == "synthesis" else 28.0
                    ge = {
                        "ok": True,
                        "graph_expansion_ms": base_ms + float((idx % 5) * 4),
                        "extra_chunk_count": 1 + (idx % 3),
                        "concepts_touched": 4 + (idx % 4),
                        "hops_applied": 1 + (idx % 2),
                        "max_hops": 3,
                        "seed_doc_ids": ["doc1.md"],
                        "added_doc_ids": [f"doc-extra-{(idx % 3) + 1}.md"],
                        "concept_route_sample": [
                            {"concept_id": "TopicA", "hop": 0, "relation": "seed", "via_concept": None},
                            {
                                "concept_id": f"TopicB{(idx % 2) + 1}",
                                "hop": 1,
                                "relation": "related",
                                "via_concept": "TopicA",
                            },
                        ],
                        "added_doc_reason_sample": [
                            {
                                "doc_id": f"doc-extra-{(idx % 3) + 1}.md",
                                "reasons": [
                                    {
                                        "concept_id": f"TopicB{(idx % 2) + 1}",
                                        "hop": 1,
                                        "relation": "related",
                                        "via_concept": "TopicA",
                                    }
                                ],
                            }
                        ],
                    }
                else:
                    ge = {
                        "skipped": True,
                        "reason": "query_type",
                        "graph_expansion_ms": 6.0 if query_type == "synthesis" else 7.0,
                        "max_hops": 3,
                        "seed_doc_ids": ["doc1.md"],
                    }
                total_answer_ms = 56.0 if query_type == "synthesis" else 60.0
                query_execute_ms = 34.0 if query_type == "synthesis" else 37.0
        return {
            "answer": f"Smoke answer for {question}",
            "sources": [
                {
                    "file_name": "doc1.md",
                    "relative_path": "doc1.md",
                    "score": 0.91,
                    "text": "Graph source chunk 1",
                },
                {
                    "file_name": "doc2.md",
                    "relative_path": "doc2.md",
                    "score": 0.84,
                    "text": "Graph source chunk 2",
                },
            ],
            "debug": {
                "query_type": query_type,
                "pipeline_ms": 18.0,
                "engine_acquire_ms": 2.0,
                "query_execute_ms": query_execute_ms,
                "total_answer_ms": total_answer_ms,
                "pipeline_trace": {
                    "schema_version": 1,
                    "effective_query": question,
                    "effective_query_source": f"smoke_graph_expansion_gate:{mode}",
                    "graph_expansion": ge,
                },
                "guardrails": {
                    "input_validated": True,
                    "output_validated": True,
                    "fallback_applied": False,
                },
            },
        }

    return _answer_question


def generate_graph_expansion_smoke_events(
    *,
    jsonl_path: str | Path,
    request_count: int = 12,
    graph_mode: str = "on",
    query_types: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    os.chdir(ROOT)
    import app.api as api
    import app.metrics as metrics
    import app.routers.query as query_router

    path = Path(jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    dashboard_path = path.with_suffix(".dashboard.db")
    if dashboard_path.exists():
        dashboard_path.unlink()

    normalized_mode = str(graph_mode or "on").strip().lower()
    if normalized_mode not in {"on", "off"}:
        raise ValueError(f"Unsupported graph_mode: {graph_mode}")
    normalized_query_types = _parse_query_types(query_types)
    answer_question = _stub_answer_factory(graph_mode=normalized_mode, query_types=normalized_query_types)

    with ExitStack() as stack:
        stack.enter_context(patch.object(metrics, "METRICS_STORE_PATH", path))
        stack.enter_context(patch.object(metrics, "METRICS_DASHBOARD_DB_PATH", dashboard_path))
        stack.enter_context(patch.object(query_router.services, "answer_question", answer_question))
        stack.enter_context(patch.object(query_router.services, "append_history_entry", lambda **_: None))
        stack.enter_context(patch.object(query_router.services.faq_memory, "save_interaction", lambda **_: None))
        stack.enter_context(patch.object(query_router, "schedule_async_quality_judge_if_sampled", lambda **_: None))
        with TestClient(api.app) as client:
            for idx in range(max(1, int(request_count))):
                response = client.post("/ask", json={"question": f"graph smoke request #{idx + 1}"})
                if response.status_code != 200:
                    raise RuntimeError(f"/ask smoke failed: status={response.status_code} body={response.text}")

    return {
        "jsonl_path": str(path.resolve()),
        "request_count": max(1, int(request_count)),
        "graph_mode": normalized_mode,
        "query_types": normalized_query_types,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate smoke graph_expansion traffic and run gate")
    parser.add_argument("--jsonl-out", type=str, default=str(ROOT / "logs" / "graph_expansion_smoke.jsonl"))
    parser.add_argument("--requests", type=int, default=12, help="Сколько smoke-запросов отправить через /ask")
    parser.add_argument(
        "--graph-mode",
        type=str,
        choices=("on", "off"),
        default="on",
        help="Режим smoke trace: on = graph expansion активен, off = feature disabled / skipped",
    )
    parser.add_argument(
        "--query-types",
        type=str,
        default="synthesis,learning_plan",
        help="Comma-separated query_type values for smoke traffic (default: synthesis,learning_plan)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=("local", "strict"),
        default="local",
        help="Профиль порогов для gate после smoke traffic",
    )
    parser.add_argument("--limit", type=int, default=0, help="Окно request-событий для gate (0 = все)")
    parser.add_argument("--min-events", type=int, default=None)
    parser.add_argument("--max-p95-ms", type=float, default=None)
    parser.add_argument("--min-applied-rate", type=float, default=None)
    parser.add_argument("--max-error-rate", type=float, default=None)
    parser.add_argument("--min-avg-extra-chunks", type=float, default=None)
    parser.add_argument("--json-out", action="store_true", help="Печать только JSON")
    args = parser.parse_args()

    from scripts.check_graph_expansion_gate import resolve_thresholds, run_gate

    thresholds = resolve_thresholds(
        profile=args.profile,
        min_events=args.min_events,
        max_p95_ms=args.max_p95_ms,
        min_applied_rate=args.min_applied_rate,
        max_error_rate=args.max_error_rate,
        min_avg_extra_chunks=args.min_avg_extra_chunks,
    )
    requested = max(1, int(args.requests))
    min_events_required = int(thresholds.get("min_events") or 0)
    effective_requests = max(requested, min_events_required)

    smoke = generate_graph_expansion_smoke_events(
        jsonl_path=args.jsonl_out,
        request_count=effective_requests,
        graph_mode=args.graph_mode,
        query_types=args.query_types,
    )

    report, rc = run_gate(
        jsonl_path=smoke["jsonl_path"],
        limit=args.limit,
        profile=args.profile,
        min_events=args.min_events,
        max_p95_ms=args.max_p95_ms,
        min_applied_rate=args.min_applied_rate,
        max_error_rate=args.max_error_rate,
        min_avg_extra_chunks=args.min_avg_extra_chunks,
    )
    payload = {
        "smoke": smoke,
        "gate": report,
    }

    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"Smoke graph expansion gate: {verdict}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
