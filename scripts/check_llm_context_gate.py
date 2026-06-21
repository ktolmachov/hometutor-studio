#!/usr/bin/env python3
"""CI-friendly gate for recent LLM context-length incidents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from summarize_cost_logs import DEFAULT_COST_LOG_DIR, _build_summary_payload, build_summary, load_cost_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_COST_LOG_DIR)
    parser.add_argument("--limit-files", type=int, default=3, help="Read only the last N daily JSONL files")
    parser.add_argument("--top", type=int, default=3, help="How many incidents/heavy prompts to show")
    parser.add_argument("--json-out", action="store_true", help="Emit machine-readable JSON summary")
    args = parser.parse_args()

    rows = load_cost_rows(args.log_dir, limit_files=args.limit_files)
    payload = _build_summary_payload(rows, topn=args.top) if rows else {
        "records": 0,
        "status_counts": {},
        "top_models": {},
        "context_length_errors": 0,
        "char_limit_warnings": 0,
        "top_by_chars": [],
        "top_by_input_tokens": [],
        "context_length_incidents": [],
    }

    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(build_summary(rows, topn=args.top))

    if payload["context_length_errors"] > 0:
        print("\nFAIL: LLM context gate failed: recent context_length_exceeded incidents detected.")
        return 2

    print("\nPASS: LLM context gate passed: no recent context_length_exceeded incidents detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
