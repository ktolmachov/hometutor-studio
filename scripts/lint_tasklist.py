#!/usr/bin/env python3
"""
lint_tasklist.py — Fast integrity check for doc/tasklist.md.

For each active row in the generated tasklist view, verifies that the
corresponding ### <id> Contract block exists.
Exits 0 (PASS) or 2 (FAIL with actionable message).

Usage:
    python scripts/lint_tasklist.py              # check tasklist.md
    python scripts/lint_tasklist.py --quiet      # only print failures
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKLIST = ROOT / "doc" / "tasklist.md"


def lint(text: str) -> list[str]:
    """Return list of error strings. Empty list = PASS."""
    errors: list[str] = []

    # Extract generated active section
    now_match = re.search(r"(?ms)^## Now\s*\n(?P<body>.*?)(?=^## |\Z)", text)
    if not now_match:
        return ["generated active section not found in tasklist.md"]

    now_body = now_match.group("body")

    # Extract package IDs from Truth View table rows
    # Handles both | pkg | and | `pkg` | formats
    row_re = re.compile(r"^\|\s*`?([a-zA-Z0-9_\-]+)`?\s*\|", re.MULTILINE)
    packages = [
        m.group(1)
        for m in row_re.finditer(now_body)
        if m.group(1).lower() not in ("package", "---")
    ]

    for pkg in packages:
        contract_header = f"### {pkg} Contract"
        if contract_header not in text:
            errors.append(
                f"Package '{pkg}' in generated active view has no contract block '{contract_header}'. "
                f"Regenerate tasklist.md from backlog_registry.yaml."
            )

    return errors


def main() -> int:
    quiet = "--quiet" in sys.argv or "-q" in sys.argv

    if not TASKLIST.exists():
        print(f"ERROR: {TASKLIST} not found", file=sys.stderr)
        return 2

    text = TASKLIST.read_text(encoding="utf-8")
    errors = lint(text)

    if errors:
        print(f"[lint_tasklist] FAIL — {len(errors)} integrity error(s):", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 2

    if not quiet:
        print(f"[lint_tasklist] PASS — generated tasklist active-view integrity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
