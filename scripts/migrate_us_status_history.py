#!/usr/bin/env python3
"""Backfill `## Status History` for closed user stories.

Reads frontmatter from `doc/user_stories/us-*.md` and appends a canonical
history entry for closed stories when missing.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
US_DIR = ROOT / "doc" / "user_stories"
HISTORY_HEADING = "## Status History"


def _extract_frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end], text[end:]


def _get_field(frontmatter: str, key: str) -> str | None:
    pattern = re.compile(rf'^{re.escape(key)}:\s*"?(.*?)"?\s*$', re.MULTILINE)
    match = pattern.search(frontmatter)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _append_history(body: str, entry: str) -> tuple[str, bool]:
    if entry in body:
        return body, False
    if HISTORY_HEADING in body:
        if not body.endswith("\n"):
            body += "\n"
        return body + entry + "\n", True
    new_body = body.rstrip() + "\n\n" + HISTORY_HEADING + "\n\n" + entry + "\n"
    return new_body, True


def migrate_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = _extract_frontmatter(text)
    if parts is None:
        return False
    frontmatter, body = parts
    status = (_get_field(frontmatter, "status") or "").strip().lower()
    if status != "closed":
        return False

    covered_by = _get_field(frontmatter, "covered_by")
    closed_date = _get_field(frontmatter, "closed_date")
    if not covered_by or not closed_date:
        return False

    entry = (
        f"- {closed_date} | status: `closed` | "
        f"covered_by: `{covered_by}` | closed_date: `{closed_date}`"
    )
    new_body, changed = _append_history(body, entry)
    if not changed:
        return False
    path.write_text("---" + frontmatter + new_body, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Apply changes to files.")
    args = parser.parse_args()

    if not US_DIR.exists():
        print(f"[us-history] ERROR: missing directory {US_DIR}")
        return 2

    files = sorted(US_DIR.glob("us-*.md"))
    changed_paths: list[Path] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        parts = _extract_frontmatter(text)
        if parts is None:
            continue
        frontmatter, body = parts
        status = (_get_field(frontmatter, "status") or "").strip().lower()
        if status != "closed":
            continue
        covered_by = _get_field(frontmatter, "covered_by")
        closed_date = _get_field(frontmatter, "closed_date")
        if not covered_by or not closed_date:
            continue
        entry = (
            f"- {closed_date} | status: `closed` | "
            f"covered_by: `{covered_by}` | closed_date: `{closed_date}`"
        )
        if entry in body:
            continue
        changed_paths.append(path)

    print(f"[us-history] candidates: {len(changed_paths)}")
    for path in changed_paths:
        print(f"  - {path.relative_to(ROOT)}")

    if not args.write:
        print("[us-history] dry-run only. Use --write to apply changes.")
        return 0

    applied = 0
    for path in changed_paths:
        if migrate_file(path):
            applied += 1
    print(f"[us-history] updated: {applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
