#!/usr/bin/env python3
"""
Quality benchmark gate (US-12.1): hit_rate, MRR, answer_relevancy по локальному KB.

Пример:
  python scripts/run_quality_benchmark.py
  python scripts/run_quality_benchmark.py --report-json /tmp/qb.json

Требует OPENAI_API_KEY и доступ к embed/LLM API (как обычная индексация).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for _p in (ROOT, _SCRIPTS):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

DEFAULT_DATASET = ROOT / "eval_data" / "quality_benchmark.json"
DEFAULT_KB = ROOT / "eval_data" / "quality_benchmark_kb"

from script_stdio_utf8 import configure_stdio_utf8, write_stdout_utf8_line


def _load_dataset(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = raw.get("cases") or []
    if len(cases) < 20:
        raise SystemExit(f"Expected at least 20 cases, got {len(cases)}")
    return raw


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Quality benchmark gate: retrieval hit-rate, MRR, answer relevancy (lexical)."
    )
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--kb-dir", type=Path, default=DEFAULT_KB, help="Source markdown tree copied into data/")
    ap.add_argument("--report-json", type=Path, default=None, help="Write full JSON report to this path")
    ap.add_argument("--min-hit-rate", type=float, default=0.45)
    ap.add_argument("--min-mrr", type=float, default=0.28)
    ap.add_argument("--min-relevancy", type=float, default=0.12)
    args = ap.parse_args()
    configure_stdio_utf8()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set; benchmark aborted.", file=sys.stderr)
        return 2

    from tests.integration_paths import apply_integration_layout_for_script

    raw = _load_dataset(args.dataset)
    cases = raw["cases"]

    tmp = Path(tempfile.mkdtemp(prefix="quality_benchmark_"))
    restore = apply_integration_layout_for_script(tmp)
    try:
        data_dir = tmp / "data"
        shutil.copytree(args.kb_dir, data_dir, dirs_exist_ok=True)

        from app.index_diff import update_snapshot_after_index
        from app.ingestion import build_index
        from app.models import QueryOptions
        from app.query_service import answer_question
        from app.retrieval_cache import clear_retrieval_cache

        clear_retrieval_cache()
        build_index(reset=True)
        update_snapshot_after_index()
        clear_retrieval_cache()

        from quality_benchmark_metrics import aggregate_rates, source_hit_and_rr, word_jaccard

        rows: list[dict] = []
        for case in cases:
            q = str(case.get("question") or "")
            ref = str(case.get("reference_answer") or "")
            exp = list(case.get("expected_sources") or [])
            result = answer_question(q, QueryOptions())
            answer = str(result.get("answer") or "")
            sources = list(result.get("sources") or [])
            hit, rr = source_hit_and_rr(sources, exp)
            rel = word_jaccard(answer, ref)
            rows.append(
                {
                    "id": case.get("id"),
                    "source_hit": hit,
                    "reciprocal_rank": rr,
                    "answer_relevancy": rel,
                }
            )

        agg = aggregate_rates(rows)
        passed = (
            agg["hit_rate"] >= args.min_hit_rate
            and agg["mean_reciprocal_rank"] >= args.min_mrr
            and agg["answer_relevancy"] >= args.min_relevancy
        )
        report = {
            "schema_version": raw.get("schema_version", 1),
            "tmp_root": str(tmp),
            "thresholds": {
                "min_hit_rate": args.min_hit_rate,
                "min_mrr": args.min_mrr,
                "min_relevancy": args.min_relevancy,
            },
            "aggregate": agg,
            "pass": passed,
            "cases": rows,
        }
        out = json.dumps(report, ensure_ascii=False, indent=2)
        write_stdout_utf8_line(out)
        if args.report_json:
            args.report_json.write_text(out, encoding="utf-8")
        return 0 if passed else 2
    finally:
        restore()


if __name__ == "__main__":
    raise SystemExit(main())
