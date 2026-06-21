#!/usr/bin/env python3
"""
Auto-correct package statuses in doc/backlog_registry.yaml.

Rule:
- If package is present in doc/closed_iterations.md and registry status is not
  "closed", rewrite status to "closed".

Usage:
    python scripts/auto_correct_registry_closed_status.py
    python scripts/auto_correct_registry_closed_status.py --check

Exit codes:
    0 = OK (or changes applied)
    1 = Drift found in --check mode
    2 = Error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "doc" / "backlog_registry.yaml"
CLOSED_ITERATIONS_PATH = ROOT / "doc" / "closed_iterations.md"


def _load_closed_package_ids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    ids: set[str] = set()

    # Canonical heading in closed_iterations.md
    heading_pattern = re.compile(r"^###\s+([A-Za-z0-9][A-Za-z0-9._/-]*)\b", re.MULTILINE)
    ids.update(heading_pattern.findall(text))

    # Fallback for inline references like `epoch-...`
    inline_pattern = re.compile(r"`([A-Za-z0-9][A-Za-z0-9._/-]*)`")
    for package_id in inline_pattern.findall(text):
        if package_id.startswith(("epoch-", "e")):
            ids.add(package_id)

    return ids


def _rewrite_registry_statuses(text: str, closed_ids: set[str]) -> tuple[str, list[str]]:
    lines = text.splitlines(keepends=True)
    current_id: str | None = None
    changed: list[str] = []
    out: list[str] = []

    id_pattern = re.compile(r"^(\s*-\s+id:\s*)(\S+)(\s*(?:#.*)?)$")
    status_pattern = re.compile(r"^(\s+status:\s+)(\S+)(\s*(?:#.*)?)$")

    for line in lines:
        stripped = line.rstrip("\n")
        id_match = id_pattern.match(stripped)
        if id_match:
            current_id = id_match.group(2).strip()
            out.append(line)
            continue

        status_match = status_pattern.match(stripped)
        if status_match and current_id and current_id in closed_ids:
            current_status = status_match.group(2).strip()
            if current_status != "closed":
                changed.append(current_id)
                suffix = status_match.group(3)
                line = f"{status_match.group(1)}closed{suffix}\n"

        out.append(line)

    return "".join(out), changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-correct backlog registry closed statuses.")
    parser.add_argument("--check", action="store_true", help="Fail if correction is needed; do not write.")
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print(f"FAIL: missing file: {REGISTRY_PATH}", file=sys.stderr)
        return 2
    if not CLOSED_ITERATIONS_PATH.exists():
        print(f"FAIL: missing file: {CLOSED_ITERATIONS_PATH}", file=sys.stderr)
        return 2

    closed_ids = _load_closed_package_ids(CLOSED_ITERATIONS_PATH)
    before = REGISTRY_PATH.read_text(encoding="utf-8")
    after, changed = _rewrite_registry_statuses(before, closed_ids)

    if not changed:
        print("PASS: backlog_registry statuses already consistent with closed_iterations")
        return 0

    uniq_changed = sorted(set(changed))
    if args.check:
        print("FAIL: backlog_registry has stale non-closed statuses for closed packages")
        for package_id in uniq_changed:
            print(f" - {package_id}")
        return 1

    REGISTRY_PATH.write_text(after, encoding="utf-8")
    print("FIXED: updated backlog_registry statuses to closed")
    for package_id in uniq_changed:
        print(f" - {package_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
