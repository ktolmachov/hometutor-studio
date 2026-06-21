#!/usr/bin/env python3
"""Сводка по JSONL-профилям SSR LLM (сравнение с основным чатом).

Пример::

    python scripts/summarize_ssr_llm_profiles.py
    python scripts/summarize_ssr_llm_profiles.py --dir logs/ssr_llm_profiles --last-files 3 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ssr_llm_profile_summary import (  # noqa: E402
    format_summary_text,
    load_ssr_profile_rows,
    summarize_ssr_profile_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize SSR LLM profile JSONL files.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=ROOT / "logs" / "ssr_llm_profiles",
        help="Directory with ssr_llm_profile_*.jsonl",
    )
    parser.add_argument(
        "--last-files",
        type=int,
        default=None,
        help="Use only last N daily files (sorted by name)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    rows = load_ssr_profile_rows(args.dir, limit_files=args.last_files)
    payload = summarize_ssr_profile_rows(rows)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_summary_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
