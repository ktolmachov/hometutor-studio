#!/usr/bin/env python3
"""
Check whether doc/roadmap.md is fresh enough for product planning.

Usage:
    python scripts/check_roadmap_health.py

Exit codes:
    0 = OK
    2 = WARNINGS
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP_PATH = ROOT / "doc" / "roadmap.md"


@dataclass(frozen=True)
class RoadmapHealth:
    warnings: list[str]
    last_update: date | None
    platform_share: float | None
    user_facing_share: float | None
    cjm_moment_count: int
    candidate_count: int


def _extract_last_update(text: str) -> date | None:
    match = re.search(r"Актуализировано:\s*\*\*(\d{4}-\d{2}-\d{2})\*\*", text)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def _section(text: str, heading_pattern: str) -> str:
    match = re.search(heading_pattern, text)
    if not match:
        return ""
    start = match.start()
    next_heading = re.search(r"\n##\s+", text[match.end() :])
    if not next_heading:
        return text[start:]
    return text[start : match.end() + next_heading.start()]


def _extract_wave_type_shares(text: str) -> tuple[float | None, float | None]:
    section = _section(text, r"### 6\.1 Распределение по типам")
    if not section:
        return None, None

    shares: dict[str, float] = {}
    for line in section.splitlines():
        match = re.match(r"\|\s*(?P<type>.+?)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(?P<share>\d+(?:\.\d+)?)%", line)
        if not match:
            continue
        wave_type = match.group("type")
        share = float(match.group("share"))
        if "Platform" in wave_type:
            shares["platform"] = share
        else:
            shares["user_facing"] = shares.get("user_facing", 0.0) + share

    return shares.get("platform"), shares.get("user_facing")


def _count_cjm_moments(text: str) -> int:
    section = _section(text, r"### 6\.3 Связь волн с CJM моментами истины")
    return sum(1 for line in section.splitlines() if re.match(r"\|\s*\*\*#\d+\s", line))


def _count_candidate_rows(text: str) -> int:
    section = _section(text, r"### 8\.3 Примеры прорывных направлений")
    return sum(1 for line in section.splitlines() if re.match(r"\|\s*\d+\s*\|", line))


def check_roadmap_health(
    roadmap_path: Path = ROADMAP_PATH,
    *,
    today: date | None = None,
) -> RoadmapHealth:
    text = roadmap_path.read_text(encoding="utf-8")
    today = today or date.today()
    warnings: list[str] = []

    last_update = _extract_last_update(text)
    if last_update is None:
        warnings.append("roadmap.md has no 'Актуализировано: **YYYY-MM-DD**' marker")
    elif (today - last_update).days > 30:
        warnings.append(f"roadmap.md is stale: last update is {last_update.isoformat()}")

    platform_share, user_facing_share = _extract_wave_type_shares(text)
    if platform_share is None or user_facing_share is None:
        warnings.append("roadmap.md has no readable §6.1 wave type balance table")
    else:
        if platform_share > 50.0:
            warnings.append(f"wave type balance is platform-heavy: Platform={platform_share:.1f}%")
        if not 60.0 <= user_facing_share <= 80.0:
            warnings.append(
                f"user-facing wave balance is outside 60-80%: user-facing={user_facing_share:.1f}%"
            )

    cjm_moment_count = _count_cjm_moments(text)
    if cjm_moment_count < 13:
        warnings.append(f"CJM coverage is incomplete: found {cjm_moment_count}/13 moments")

    candidate_count = _count_candidate_rows(text)
    if candidate_count < 5:
        warnings.append(f"CANDIDATE_TABLE is too small: found {candidate_count} rows")

    return RoadmapHealth(
        warnings=warnings,
        last_update=last_update,
        platform_share=platform_share,
        user_facing_share=user_facing_share,
        cjm_moment_count=cjm_moment_count,
        candidate_count=candidate_count,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=ROADMAP_PATH,
        help="Path to roadmap.md",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    health = check_roadmap_health(args.roadmap)

    print("Roadmap health")
    print(f"- last_update: {health.last_update}")
    print(f"- platform_share: {health.platform_share}")
    print(f"- user_facing_share: {health.user_facing_share}")
    print(f"- cjm_moment_count: {health.cjm_moment_count}")
    print(f"- candidate_count: {health.candidate_count}")

    if health.warnings:
        print("\nWarnings:")
        for warning in health.warnings:
            print(f"- {warning}")
        return 2

    print("\nOK: roadmap.md is healthy for planning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
