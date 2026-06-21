#!/usr/bin/env python3
"""
Defense eval: сравнение retrieval-режимов по eval/eval_dataset.json.

Метрики (retrieval-only, без вызова LLM):
  - source_found: ожидаемый файл в top-3 узлов
  - faithfulness_pass: null (нужна ручная проверка ответа; см. faithfulness_note)
  - latency_sec: только retrieve

Требует demo_chroma_db/ (scripts/build_demo_chroma.py) и OPENAI_API_KEY для эмбеддингов при первой сборке.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for candidate in (ROOT, _SCRIPTS):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from dotenv import load_dotenv
from llama_index.core.schema import QueryBundle

from script_stdio_utf8 import configure_stdio_utf8, write_stdout_utf8_line
from quality_benchmark_metrics import source_hit_and_rr

load_dotenv(ROOT / ".env")

DEFAULT_DATASET = ROOT / "eval" / "eval_dataset.json"
DEMO_DATA = ROOT / "demo_data"
DEMO_CHROMA = ROOT / "demo_chroma_db"
MODES = ("vector_only", "hybrid", "bm25_only")


def _load_dataset(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _node_source_name(node: Any) -> str:
    inner = getattr(node, "node", node)
    meta = getattr(inner, "metadata", None) or {}
    if isinstance(meta, dict):
        for key in ("file_name", "relative_path", "source_file"):
            val = meta.get(key)
            if val:
                return str(val).replace("\\", "/")
    return ""


def _retrieve_top_sources(
    question: str,
    *,
    retrieval_mode: str,
) -> tuple[list[dict[str, str]], float]:
    from app.models import PipelineOverrides, QueryOptions
    from app.pipeline_runner import run_pipeline
    from app.retrieval import build_query_engine, resolve_query_execution_plan

    ctx = run_pipeline(question, QueryOptions())
    overrides = PipelineOverrides(retrieval_mode=retrieval_mode, enable_reranker=False)
    plan = resolve_query_execution_plan(
        question,
        QueryOptions(),
        query_context=ctx,
        overrides=overrides,
    )
    t0 = time.perf_counter()
    built = build_query_engine(
        ctx.effective_query,
        QueryOptions(),
        query_context=ctx,
        overrides=overrides,
        execution_plan=plan,
    )
    engine = built["engine"]
    retriever = getattr(engine, "retriever", None)
    if retriever is None:
        raise RuntimeError(f"No retriever on engine for mode={retrieval_mode}")
    nodes = retriever.retrieve(QueryBundle(ctx.effective_query))
    latency = time.perf_counter() - t0
    sources: list[dict[str, str]] = []
    for node in nodes[:10]:
        name = _node_source_name(node)
        if name:
            sources.append({"file_name": name, "relative_path": name})
    return sources, latency


def _run_case(
    question: str,
    expected_source: str | None,
    *,
    retrieval_mode: str,
) -> dict[str, Any]:
    sources, latency = _retrieve_top_sources(question, retrieval_mode=retrieval_mode)
    if not expected_source:
        hit = False
    else:
        hit, _rr = source_hit_and_rr(sources, [expected_source])
    return {
        "source_found": hit,
        "faithfulness_pass": None,
        "latency_sec": round(latency, 2),
        "source_files_top3": [s.get("file_name", "") for s in sources[:3]],
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    with_source = [r for r in rows if r.get("expected_source")]
    ns = len(with_source) or 1
    latencies = [float(r["latency_sec"]) for r in rows if r.get("latency_sec") is not None]
    return {
        "total_questions": len(rows),
        "source_found_count": sum(1 for r in with_source if r.get("source_found")),
        "source_found_rate": round(
            sum(1 for r in with_source if r.get("source_found")) / ns, 2
        ),
        "faithfulness_pass_count": None,
        "faithfulness_pass_rate": None,
        "avg_latency_sec": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Defense retrieval-mode eval (retrieval-only)")
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    configure_stdio_utf8()

    if not DEMO_DATA.is_dir():
        write_stdout_utf8_line(f"Missing {DEMO_DATA}")
        return 2

    raw = _load_dataset(args.dataset)
    questions = raw.get("questions") or []
    if len(questions) < 10:
        write_stdout_utf8_line("Dataset must have at least 10 questions.")
        return 2

    from tests.integration_paths import apply_integration_layout_for_script

    tmp = Path(tempfile.mkdtemp(prefix="defense_eval_"))
    restore = apply_integration_layout_for_script(tmp)
    os.environ["ENABLE_RERANKER"] = "false"
    try:
        data_dir = tmp / "data"
        chroma_dir = tmp / "chroma_db"
        shutil.copytree(DEMO_DATA, data_dir, dirs_exist_ok=True)
        if DEMO_CHROMA.is_dir():
            shutil.copytree(DEMO_CHROMA, chroma_dir, dirs_exist_ok=True)
        elif os.getenv("OPENAI_API_KEY"):
            from app.index_diff import update_snapshot_after_index
            from app.ingestion import build_index
            from app.retrieval_cache import clear_retrieval_cache

            write_stdout_utf8_line("demo_chroma_db missing — building index …")
            clear_retrieval_cache()
            build_index(reset=True)
            update_snapshot_after_index()
            clear_retrieval_cache()
        else:
            write_stdout_utf8_line("demo_chroma_db missing and OPENAI_API_KEY unset.")
            return 2

        by_mode: dict[str, list[dict[str, Any]]] = {m: [] for m in MODES}
        for item in questions:
            qid = str(item.get("id") or "")
            qtext = str(item.get("question") or "").strip()
            exp_src = item.get("ground_truth_source")
            for mode in MODES:
                row = _run_case(
                    qtext,
                    str(exp_src) if exp_src else None,
                    retrieval_mode=mode,
                )
                row["id"] = qid
                row["mode"] = mode
                row["expected_source"] = exp_src
                by_mode[mode].append(row)
                write_stdout_utf8_line(f"  {qid} {mode}: hit={row['source_found']} {row['latency_sec']}s")

        summary_by_mode = {m: _aggregate(by_mode[m]) for m in MODES}
        run_id = f"eval-{date.today().isoformat()}"
        out = {
            "run_id": run_id,
            "eval_type": "retrieval_only",
            "dataset": str(args.dataset.relative_to(ROOT)).replace("\\", "/"),
            "corpus": raw.get("corpus", "demo_data"),
            "faithfulness_note": "faithfulness_pass требует ручного прогона с LLM; здесь только source_found@3",
            "summary": {
                "total_questions": len(questions),
                "faithfulness_pass": None,
                "source_found": None,
                "avg_confidence": None,
            },
            "by_mode": summary_by_mode,
            "cases": {m: by_mode[m] for m in MODES},
        }
        out_path = args.output or (ROOT / "eval" / f"eval_results_{date.today().isoformat()}.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        write_stdout_utf8_line(f"Wrote {out_path}")
        return 0
    finally:
        restore()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
