#!/usr/bin/env python3
"""
regenerate_cjm_pain_table.py — Regenerate generated sections in doc/cjm.md and doc/user_stories.md.

Delegates to backlog_registry_lint.py::sync_docs_from_index() which already handles:
  - doc/cjm.md § 8 pain table
  - doc/user_stories.md Open candidates + Coverage-aware index view

Usage:
    python scripts/regenerate_cjm_pain_table.py         # dry-run: check if regen needed
    python scripts/regenerate_cjm_pain_table.py --write # write regenerated sections to disk

Exit codes:
    0 = OK (no changes needed, or write succeeded)
    1 = CHECK mode: sections are stale
    2 = Error
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backlog_registry_lint import sync_docs_from_index  # noqa: E402
from prompt_utils import ROOT  # noqa: E402, F811


USER_STORIES_INDEX = ROOT / "doc" / "user_stories_index.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--write", "-w", action="store_true",
        help="Write regenerated sections to doc/cjm.md and doc/user_stories.md",
    )
    parser.add_argument(
        "--check", "-c", action="store_true",
        help="Exit 1 if any section is stale; do not write",
    )
    args = parser.parse_args()

    if not USER_STORIES_INDEX.exists():
        print(f"ERROR: {USER_STORIES_INDEX.relative_to(ROOT)} not found. Run rebuild_user_stories_index.py --write first.", file=sys.stderr)
        return 2

    errors, warnings = sync_docs_from_index(
        index_path=USER_STORIES_INDEX,
        write=args.write,
    )

    for msg in errors:
        print(f"FAIL: {msg}")
    for msg in warnings:
        print(f"WARN: {msg}")

    if errors:
        if args.check:
            return 1
        # In non-write mode, sync_docs_from_index reports errors for stale sections.
        # That's expected — regeneration is needed.
        if not args.write:
            print("ℹ Sections are stale. Run with --write to regenerate.")
            return 1
        return 2

    if args.write:
        print("✅ Regenerated sections in doc/cjm.md and doc/user_stories.md")
    else:
        print("✅ All generated sections are up-to-date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
