#!/usr/bin/env python3
"""
Offline graph uplift eval: quality vs graph_aware on graph-shaped dataset.

Writes eval/graph_uplift_report_<run_id>.json and applies demotion tick post-step.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.eval_baseline import build_graph_uplift_regression_gate_payload
from app.eval_uplift import (
    build_graph_uplift_report,
    evaluate_uplift_gate,
    iter_graph_shaped_items,
    load_graph_shaped_dataset,
    LOCAL_UPLIFT_GATE_DEFAULTS,
)
from app.metrics_slo import apply_graph_uplift_demotion_tick


def _resolve_generation_id(explicit: str | None) -> str | None:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    try:
        from app.index_registry import get_active_generation_view

        return str(get_active_generation_view().generation_id or "").strip() or None
    except (ImportError, OSError, ValueError, AttributeError):
        return None


def _fixture_case_result(item: dict[str, Any], profile: str) -> dict[str, Any]:
    """Deterministic offline case payload when live index/corpus unavailable."""
    doc_ids = list(item.get("expected_doc_ids") or [])
    graph_applied = profile == "graph_aware"
    case: dict[str, Any] = {
        "id": item.get("id"),
        "category": item.get("category"),
        "profile": profile,
        "retrieved_doc_ids": doc_ids[:1],
        "sources": [{"relative_path": doc_ids[0]}] if doc_ids else [],
        "latency_ms": 120.0 if profile == "quality" else 150.0,
        "graph_applied": graph_applied,
    }
    if graph_applied:
        case["graph_expansion"] = {
            "ok": True,
            "graph_evidence": [
                {
                    "confidence": 0.85,
                    "relation_type": item.get("expected_characteristics", {}).get("relation_type", "related"),
                }
            ],
        }
    return case


def _run_profile_cases(
    items: list[dict[str, Any]],
    profile: str,
    *,
    fixture_only: bool,
) -> list[dict[str, Any]]:
    if fixture_only:
        return [_fixture_case_result(item, profile) for item in items]

    from app.models import QueryOptions
    from app.query_service import answer_question

    out: list[dict[str, Any]] = []
    for item in items:
        question = str(item.get("question") or item.get("query") or "").strip()
        if not question:
            continue
        t0 = time.perf_counter()
        result = answer_question(
            question,
            QueryOptions(rag_profile=profile),
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        debug = result.get("debug") if isinstance(result.get("debug"), dict) else {}
        routing = debug.get("retrieval_routing") if isinstance(debug.get("retrieval_routing"), dict) else {}
        pt = debug.get("pipeline_trace") if isinstance(debug.get("pipeline_trace"), dict) else {}
        ge = pt.get("graph_expansion") if isinstance(pt.get("graph_expansion"), dict) else {}
        sources = result.get("sources") if isinstance(result.get("sources"), list) else []
        out.append(
            {
                "id": item.get("id"),
                "category": item.get("category"),
                "profile": profile,
                "sources": sources,
                "retrieved_doc_ids": [
                    str(s.get("relative_path") or s.get("file_name") or "")
                    for s in sources
                    if isinstance(s, dict)
                ],
                "latency_ms": round(latency_ms, 2),
                "graph_applied": bool(ge.get("ok")),
                "graph_expansion": ge,
                "retrieval_routing": routing,
            }
        )
    return out


def run_eval(
    *,
    dataset_path: Path | None = None,
    fixture_only: bool = False,
    generation_id: str | None = None,
    run_id: str | None = None,
    uplift_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    os.chdir(ROOT)
    dataset = load_graph_shaped_dataset(dataset_path)
    items = iter_graph_shaped_items(dataset)
    gen = _resolve_generation_id(generation_id)

    if gen:
        from app.graph_generation_paths import generation_bundle_dir
        from app.knowledge_graph_bundle import load_graph_quality_report

        report = load_graph_quality_report(generation_bundle_dir(gen)) or {}
        if not fixture_only and not report:
            fixture_only = True

    quality_cases = _run_profile_cases(items, "quality", fixture_only=fixture_only)
    graph_cases = _run_profile_cases(items, "graph_aware", fixture_only=fixture_only)

    rid = run_id or str(uuid.uuid4())
    uplift_report = build_graph_uplift_report(
        quality_cases=quality_cases,
        graph_aware_cases=graph_cases,
        generation_id=gen,
        dataset_version=str(dataset.get("dataset_version") or ""),
        run_id=rid,
        includes_defense_categories=bool(dataset.get("includes_defense_categories")),
    )
    uplift_gate = evaluate_uplift_gate(
        uplift_report,
        uplift_thresholds or LOCAL_UPLIFT_GATE_DEFAULTS,
        expected_generation_id=gen,
    )
    uplift_report["uplift_gate"] = uplift_gate
    uplift_report["regression_gate"] = build_graph_uplift_regression_gate_payload(uplift_report)

    observed_delta = uplift_report.get("deltas", {}).get("correctness_rate_delta")
    demotion_tick = apply_graph_uplift_demotion_tick(
        observed_delta=float(observed_delta) if observed_delta is not None else None,
    )
    uplift_report["demotion_tick"] = demotion_tick

    out_dir = ROOT / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"graph_uplift_report_{rid}.json"
    out_path.write_text(json.dumps(uplift_report, ensure_ascii=False, indent=2), encoding="utf-8")
    uplift_report["artifact_path"] = str(out_path.resolve())
    return uplift_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run graph uplift eval (quality vs graph_aware)")
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to graph_shaped dataset JSON",
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Use deterministic fixture case results (no live /ask)",
    )
    parser.add_argument("--generation-id", type=str, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset) if args.dataset else None
    report = run_eval(
        dataset_path=dataset_path,
        fixture_only=bool(args.fixture_only),
        generation_id=args.generation_id,
        run_id=args.run_id,
    )
    if args.json_out:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        passed = report.get("uplift_gate", {}).get("passed")
        print(f"Graph uplift eval: {'PASS' if passed else 'FAIL'} run_id={report.get('run_id')}")
        print(f"Artifact: {report.get('artifact_path')}")
    exit_code = int(report.get("uplift_gate", {}).get("exit_code") or 0)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
