#!/usr/bin/env python3
"""Build a redacted home-rag eval dataset from an offline Langfuse export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.langfuse_dataset import build_eval_dataset, load_trace_export, write_eval_dataset


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Offline Langfuse JSON or JSONL export")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "eval_data" / "langfuse_eval_dataset.json",
    )
    parser.add_argument(
        "--include-successful",
        action="store_true",
        help="Include successful traces; default keeps only failed traces",
    )
    parser.add_argument(
        "--run-eval",
        action="store_true",
        help="Explicitly run the existing eval service after building the dataset",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "eval_results" / "langfuse_eval_report_latest.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.export.is_file():
        print(
            f"Langfuse export not found: {args.export.resolve()}\n"
            "Export traces from Langfuse as JSON/JSONL, then pass the real file path, for example:\n"
            r"  .\.venv\Scripts\python.exe scripts\build_langfuse_eval_dataset.py C:\Downloads\langfuse-traces.json",
            file=sys.stderr,
        )
        return 2

    try:
        traces = load_trace_export(args.export)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Could not read Langfuse export {args.export}: {exc}", file=sys.stderr)
        return 2
    cases = build_eval_dataset(traces, failed_only=not args.include_successful)
    write_eval_dataset(args.output, cases)
    print(f"wrote {len(cases)} eval cases to {args.output}")

    if not args.run_eval:
        return 0
    try:
        relative_dataset = args.output.resolve().relative_to((ROOT / "eval_data").resolve())
    except ValueError:
        print("--run-eval requires --output inside eval_data/", file=sys.stderr)
        return 2

    from app.eval_service import run_eval

    report = run_eval(str(relative_dataset))
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"wrote eval report to {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
