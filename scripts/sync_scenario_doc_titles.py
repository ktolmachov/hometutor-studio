#!/usr/bin/env python3
"""Align ``doc/user_scenarios.md`` scenario headings with YAML ``title`` fields."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOC = ROOT / "doc" / "user_scenarios.md"
DEFAULT_SCENARIOS = ROOT / "doc" / "scenarios"

YAML_ID_RE = re.compile(r"^id:\s*scenario_(\d{2})\s*$", re.MULTILINE)
YAML_TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)
HEADING_RE = re.compile(r"^(##\s+Сценарий\s+(\d+)\s+—\s+)(.+?)\s*$", re.MULTILINE)
NAV_LINK_RE = re.compile(r"\[([^\]]*)\]\(#(сценарий-\d+--[^)]+)\)")


def _anchor(num: int, title: str) -> str:
    value = f"Сценарий {num} — {title}"
    return (
        value.lower()
        .replace(" ", "-")
        .replace("—", "")
        .replace(":", "")
        .replace(".", "")
        .replace(",", "")
        .replace("_", "-")
        .replace("→", "")
        .replace("«", "")
        .replace("»", "")
        .strip("-")
    )


def _load_yaml_titles(scenarios_dir: Path) -> dict[int, str]:
    titles: dict[int, str] = {}
    for path in sorted(scenarios_dir.glob("scenario_*.yaml")):
        text = path.read_text(encoding="utf-8")
        id_match = YAML_ID_RE.search(text)
        title_match = YAML_TITLE_RE.search(text)
        if id_match is None or title_match is None:
            raise ValueError(f"{path}: expected id and title fields")
        titles[int(id_match.group(1))] = title_match.group(1).strip()
    return titles


def sync_doc_titles(doc_path: Path, scenarios_dir: Path, *, dry_run: bool = False) -> tuple[int, int]:
    titles = _load_yaml_titles(scenarios_dir)
    text = doc_path.read_text(encoding="utf-8")

    def repl_heading(match: re.Match[str]) -> str:
        num = int(match.group(2))
        return f"{match.group(1)}{titles[num]}"

    new_text, heading_count = HEADING_RE.subn(repl_heading, text)
    if heading_count != len(titles):
        raise ValueError(f"expected {len(titles)} heading updates, got {heading_count}")

    nav_updates = 0
    for match in NAV_LINK_RE.finditer(new_text):
        num_match = re.search(r"Сценарий\s+(\d+)", match.group(1))
        if num_match is None:
            continue
        num = int(num_match.group(1))
        new_anchor = _anchor(num, titles[num])
        old_anchor = match.group(2)
        if old_anchor != new_anchor:
            new_text = new_text.replace(f"](#{old_anchor})", f"](#{new_anchor})", 1)
            nav_updates += 1

    if not dry_run:
        doc_path.write_text(new_text, encoding="utf-8")
    return heading_count, nav_updates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--scenarios-dir", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    heading_count, nav_updates = sync_doc_titles(args.doc, args.scenarios_dir, dry_run=args.dry_run)
    print(f"headings={heading_count} nav_anchors={nav_updates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
