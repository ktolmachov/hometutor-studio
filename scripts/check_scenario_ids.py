#!/usr/bin/env python3
"""Validate scenario IDs shared by ``doc/user_scenarios.md`` and YAML demos."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_HEADING_RE = re.compile(r"^##\s+Сценарий\s+(\d+)\s+—\s+(.+?)\s*$", re.MULTILINE)
YAML_ID_RE = re.compile(r"^id:\s*scenario_(\d{2})\s*$", re.MULTILINE)
YAML_TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)


@dataclass(frozen=True)
class ScenarioDocEntry:
    number: int
    title: str


@dataclass(frozen=True)
class ScenarioYamlEntry:
    number: int
    title: str
    path: Path


def _norm_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace("ё", "е")).strip()


def _load_doc_entries(path: Path) -> dict[int, ScenarioDocEntry]:
    text = path.read_text(encoding="utf-8")
    entries: dict[int, ScenarioDocEntry] = {}
    for match in SCENARIO_HEADING_RE.finditer(text):
        num = int(match.group(1))
        if num in entries:
            raise ValueError(f"Duplicate scenario heading: {num}")
        entries[num] = ScenarioDocEntry(number=num, title=match.group(2).strip())
    return entries


def _load_yaml_entries(path: Path) -> dict[int, ScenarioYamlEntry]:
    entries: dict[int, ScenarioYamlEntry] = {}
    for item in sorted(path.glob("scenario_*.yaml")):
        text = item.read_text(encoding="utf-8")
        id_match = YAML_ID_RE.search(text)
        title_match = YAML_TITLE_RE.search(text)
        if id_match is None or title_match is None:
            raise ValueError(f"{item}: expected id and title fields")
        num = int(id_match.group(1))
        if num in entries:
            raise ValueError(f"Duplicate scenario YAML id: scenario_{num:02d}")
        entries[num] = ScenarioYamlEntry(number=num, title=title_match.group(1).strip(), path=item)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", type=Path, default=ROOT / "doc" / "user_scenarios.md")
    parser.add_argument("--scenarios-dir", type=Path, default=ROOT / "doc" / "scenarios")
    parser.add_argument(
        "--strict-titles",
        action="store_true",
        help="Also require MD scenario headings to match YAML title text exactly after normalization.",
    )
    args = parser.parse_args()

    doc_entries = _load_doc_entries(args.doc)
    yaml_entries = _load_yaml_entries(args.scenarios_dir)

    missing_yaml = sorted(num for num in doc_entries if num not in yaml_entries)
    missing_doc = sorted(num for num in yaml_entries if num not in doc_entries)
    title_mismatches = [
        (num, doc_entries[num].title, yaml_entries[num].title)
        for num in sorted(doc_entries.keys() & yaml_entries.keys())
        if _norm_title(doc_entries[num].title) != _norm_title(yaml_entries[num].title)
    ]

    failed = False
    if missing_yaml:
        failed = True
        print("Missing YAML for MD scenarios:", ", ".join(f"{num:02d}" for num in missing_yaml))
    if missing_doc:
        failed = True
        print("Missing MD headings for YAML scenarios:", ", ".join(f"{num:02d}" for num in missing_doc))
    if args.strict_titles and title_mismatches:
        failed = True
        print("Title mismatches:")
        for num, md_title, yaml_title in title_mismatches:
            print(f"  scenario_{num:02d}: MD={md_title!r}; YAML={yaml_title!r}")
    elif title_mismatches:
        print(f"Title warnings: {len(title_mismatches)} mismatch(es); re-run with --strict-titles to fail.")

    if failed:
        return 1
    print(f"Scenario IDs OK: {len(doc_entries)} MD heading(s), {len(yaml_entries)} YAML file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
