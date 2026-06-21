#!/usr/bin/env python3
"""Validate generated smart lecture konspekt Markdown files.

The gate is intentionally deterministic and offline. It checks structure,
provenance metadata, known URL regressions, and cloud-only learning blocks.

Examples:
  python scripts/validate_smart_konspekt.py path/to/konspekt.md
  python scripts/validate_smart_konspekt.py path/to/konspekt.md --profile local
  python scripts/validate_smart_konspekt.py path/to/konspekt.md --expect-presentation
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


GENERIC_URL_FALLBACKS = (
    "лучше добавить после отдельного поиска",
    "лучше добавить их после отдельного поиска",
    "проверенные конкретные url на видео",
    "ручная проверка качества",
    "в текущем режиме не добавлены",
)

AGENT_LOOP_MARKERS = (
    "react",
    "agentic loop",
    "stop condition",
    "stop-controller",
    "no-progress",
    "no progress",
    "plan-execute",
    "observation",
)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _extract_front_matter(text: str) -> tuple[dict[str, str], str | None]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, None
    values: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return values, "\n".join(lines[1:index])
        if ":" not in line or line.startswith((" ", "\t", "-")):
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values, None


def _has_heading(text: str, heading: str) -> bool:
    pattern = rf"(?im)^##\s+.*{re.escape(heading)}\s*$"
    return bool(re.search(pattern, text))


def _has_section_title(text: str, title: str) -> bool:
    return bool(re.search(rf"(?im)^#+\s+.*{re.escape(title)}", text))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _markdown_links(text: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", text)


def _validate_front_matter(
    meta: dict[str, str],
    raw_front_matter: str | None,
    args: argparse.Namespace,
    result: ValidationResult,
) -> None:
    if raw_front_matter is None:
        result.error("YAML: нет корректного front matter между --- и ---.")
        return
    if "self_eval" in meta or re.search(r"(?im)^\s*self_eval\s*:", raw_front_matter):
        result.error("YAML: self_eval запрещен; оценки должны быть только в рубрике качества.")
    for key in ("source", "generated", "type", "tags"):
        if key not in meta:
            result.error(f"YAML: отсутствует обязательное поле {key}.")
    if meta.get("type") and meta["type"] != "konspekt":
        result.warn(f"YAML: type={meta['type']!r}, ожидалось 'konspekt'.")
    tags = meta.get("tags", "")
    if _has_heading(args._text, "Agentic Loop и условия выхода") and "Agentic Loop" not in tags:
        result.warn("YAML: есть раздел Agentic Loop, но тег Agentic Loop отсутствует.")
    if args.expect_source_sha and "source_sha256" not in meta:
        result.error("YAML: ожидался source_sha256, но поле отсутствует.")
    if args.expect_presentation and "presentation" not in meta:
        result.error("YAML: ожидалось поле presentation, но оно отсутствует.")
    if args.expect_presentation_sha and "presentation_sha256" not in meta:
        result.error("YAML: ожидался presentation_sha256, но поле отсутствует.")


def _validate_cloud_sections(text: str, result: ValidationResult) -> None:
    required = (
        "Объяснение внешнего эксперта простыми словами",
        "Проверка точности и неточности",
        "Каркас знаний",
        "Учебные артефакты для повторения",
        "Рубрика качества конспекта",
        "Дополнительные материалы для глубокого изучения",
    )
    for title in required:
        if not _has_heading(text, title):
            result.error(f"Cloud: отсутствует раздел ## {title}.")
    for title in ("Flashcards", "Quiz", "Spaced repetition plan"):
        if not _has_section_title(text, title):
            result.error(f"Cloud: в учебных артефактах отсутствует блок {title}.")
    if not _has_section_title(text, "Видео"):
        result.error("Cloud: отсутствует блок видео.")
    if not _has_section_title(text, "Русскоязычные материалы"):
        result.warn("Cloud: нет отдельного блока русскоязычных материалов.")


def _validate_agent_loop(text: str, result: ValidationResult) -> None:
    if not _contains_any(text, AGENT_LOOP_MARKERS):
        return
    if not _has_heading(text, "Agentic Loop и условия выхода"):
        result.error("Agentic Loop: тема есть в тексте, но нет отдельного раздела.")
    for phrase in ("Условия успешного выхода", "Ограничительные условия выхода"):
        if phrase not in text:
            result.error(f"Agentic Loop: отсутствует блок «{phrase}».")


def _validate_presentation(text: str, meta: dict[str, str], args: argparse.Namespace, result: ValidationResult) -> None:
    has_presentation = args.expect_presentation or "presentation" in meta or "presentation_sha256" in meta
    if not has_presentation:
        return
    if not _has_heading(text, "Что важно из презентации"):
        result.error("Презентация: отсутствует раздел ## Что важно из презентации.")
    for phrase in ("Как читать визуалы", "Мини-проверка по презентации"):
        if phrase not in text:
            result.error(f"Презентация: отсутствует active-recall блок «{phrase}».")


def _validate_urls(text: str, args: argparse.Namespace, result: ValidationResult) -> None:
    lowered = text.lower()
    for fallback in GENERIC_URL_FALLBACKS:
        if fallback in lowered:
            result.error(f"URL: найден общий fallback вместо проверенного материала: {fallback!r}.")
    if "anthropic.com/research/building-effective-agents" in lowered:
        result.error("URL: Anthropic Building Effective Agents должен быть /engineering/building-effective-agents.")
    if not args.allow_direct_youtube and re.search(r"https?://(?:www\.)?youtube\.com/watch\?v=", text):
        result.error("URL: прямые youtube.com/watch?v= запрещены без явной проверки (--allow-direct-youtube).")
    if not args.allow_direct_youtube and "youtu.be/" in lowered:
        result.error("URL: прямые youtu.be ссылки запрещены без явной проверки (--allow-direct-youtube).")

    links = _markdown_links(text)
    if args.profile == "cloud" and _has_section_title(text, "Дополнительные материалы"):
        if len(links) < 3:
            result.warn("URL: мало внешних ссылок для cloud-конспекта.")


def validate(path: Path, args: argparse.Namespace) -> ValidationResult:
    result = ValidationResult()
    text = _read_text(path)
    args._text = text
    meta, raw_front_matter = _extract_front_matter(text)
    _validate_front_matter(meta, raw_front_matter, args, result)
    if args.profile == "cloud":
        _validate_cloud_sections(text, result)
    _validate_agent_loop(text, result)
    _validate_presentation(text, meta, args, result)
    _validate_urls(text, args, result)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="Generated smart konspekt Markdown file.")
    parser.add_argument(
        "--profile",
        choices=("cloud", "local"),
        default="cloud",
        help="Validation profile. Cloud requires deep-learning sections; local is lighter.",
    )
    parser.add_argument("--expect-source-sha", action="store_true", help="Require source_sha256 in YAML.")
    parser.add_argument("--expect-presentation", action="store_true", help="Require presentation metadata and section.")
    parser.add_argument("--expect-presentation-sha", action="store_true", help="Require presentation_sha256 in YAML.")
    parser.add_argument(
        "--allow-direct-youtube",
        action="store_true",
        help="Allow direct youtube.com/watch?v= and youtu.be links after external verification.",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.file.is_file():
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        return 1
    result = validate(args.file, args)
    for message in result.errors:
        print(f"ERROR: {message}")
    for message in result.warnings:
        print(f"WARN: {message}")
    if result.errors or (args.strict and result.warnings):
        print("validate_smart_konspekt: FAIL")
        return 1
    print("validate_smart_konspekt: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
