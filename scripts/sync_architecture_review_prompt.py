"""Sync Architecture Review prompt between documentation files.

Source of truth:
  - doc/agent_workflow_arch_review.md, section "### Шаблон architecture review prompt"

Target:
  - doc/team_workflow/architect.md, section "## Промпт 2: Architecture Review"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "doc" / "agent_workflow_arch_review.md"
TARGET_PATH = ROOT / "doc" / "team_workflow" / "architect.md"

SOURCE_HEADER = "### Шаблон architecture review prompt"
TARGET_HEADER = "## Промпт 2: Architecture Review"
TARGET_NEXT_HEADER = "## Промпт 3: ADR Decision"


def _extract_prompt_block(source_text: str) -> str:
    header_pos = source_text.find(SOURCE_HEADER)
    if header_pos == -1:
        raise ValueError(f"Source header not found: {SOURCE_HEADER}")

    fence_start = source_text.find("```text", header_pos)
    if fence_start == -1:
        raise ValueError("Start of fenced prompt block not found in source")

    fence_end = source_text.find("\n```", fence_start)
    if fence_end == -1:
        raise ValueError("End of fenced prompt block not found in source")

    fence_end += len("\n```")
    return source_text[fence_start:fence_end].strip()


def _build_target_section(prompt_block: str) -> str:
    return (
        f"{TARGET_HEADER}\n\n"
        "Источник истины: `doc/agent_workflow_arch_review.md` "
        '(секция "Architecture Review Prompt").\n'
        "Секция поддерживается скриптом "
        "`python scripts/sync_architecture_review_prompt.py`.\n\n"
        f"{prompt_block}\n\n"
        f"{TARGET_NEXT_HEADER}"
    )


def _replace_target_section(target_text: str, replacement_section: str) -> str:
    pattern = re.compile(
        rf"(?s){re.escape(TARGET_HEADER)}\r?\n.*?\r?\n{re.escape(TARGET_NEXT_HEADER)}"
    )
    new_text, count = pattern.subn(lambda _: replacement_section, target_text, count=1)
    if count != 1:
        raise ValueError(
            "Could not uniquely replace target section "
            f"between '{TARGET_HEADER}' and '{TARGET_NEXT_HEADER}'"
        )
    return new_text


def sync(check_only: bool) -> int:
    source_text = SOURCE_PATH.read_text(encoding="utf-8")
    target_text = TARGET_PATH.read_text(encoding="utf-8")

    prompt_block = _extract_prompt_block(source_text)
    desired_section = _build_target_section(prompt_block)
    synced_target = _replace_target_section(target_text, desired_section)

    if synced_target == target_text:
        print("Architecture review prompt is already in sync.")
        return 0

    if check_only:
        print("Architecture review prompt is out of sync.")
        return 1

    TARGET_PATH.write_text(synced_target, encoding="utf-8")
    print("Synchronized architecture review prompt in target document.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync architecture review prompt docs."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 when files are out of sync.",
    )
    args = parser.parse_args()
    try:
        return sync(check_only=args.check)
    except Exception as exc:  # noqa: BLE001 - CLI should report clear errors.
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
