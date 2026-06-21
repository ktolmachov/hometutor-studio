#!/usr/bin/env python3
"""Validate team pipeline markdown artifacts (orchestrator handoff gates).

Mirrors checkpoint rules from doc/team_workflow/orchestrator_template.md.
Developer/Tester: WARN if unresolved/failed tests or FAIL verdict without HANDOFF_SIGNAL.

Exit 0 if no errors; exit 1 if any error; warnings alone exit 0 unless --strict.

Examples:
  python scripts/validate_team_artifact.py archive/team_artifacts/E15-A/1_po_package.md
  python scripts/validate_team_artifact.py --artifacts-dir archive/team_artifacts/E15-A
  python scripts/validate_team_artifact.py --artifacts-dir PATH --strict
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


ARTIFACT_KIND_BY_NAME: dict[str, str] = {
    "1_po_package.md": "po",
    "2_analyst_spec.md": "analyst",
    "3_architect_contract.md": "architect",
    "4_designer_ui_spec.md": "designer",
    "5a_developer_sp1.md": "developer_sp1",
    "5b_developer_sp2.md": "developer_sp2",
    "6a_tester_sp1.md": "tester_sp1",
    "6b_tester_sp2.md": "tester_sp2",
}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_po(text: str, result: ValidationResult) -> None:
    if not re.search(
        r"(?im)^#{1,4}\s*CJM\s+Stage\s*$|\bCJM\s+Stage\s*:|\*\*CJM\s+stage",
        text,
    ):
        result.error("PO: нет секции CJM Stage (заголовок или строка «CJM Stage:» / «CJM stage»).")
    if not re.search(r"\bUS-\d", text):
        result.error("PO: нет ссылки на user story (ожидается фрагмент вида US-…).")
    outcome_lines = len(re.findall(r"(?m)^\s*-\s*Outcome\s*:", text))
    outcome_alt = len(re.findall(r"(?m)^\s*Outcome\s*\d+\s*:", text))
    outcome_bold = len(re.findall(r"(?m)^\s*\*\*Outcome\s+\d+", text))
    n_out = max(outcome_lines, outcome_alt, outcome_bold)
    if n_out < 1:
        result.warn("PO: не найдены outcomes (форматы «- Outcome:», «Outcome N:» или «**Outcome N»).")
    elif n_out > 5:
        result.error(f"PO: слишком много outcomes ({n_out}), оркестратор ожидает 1–5.")
    if _po_escalation_stop(text):
        result.error("PO: найден сигнал ESCALATION — остановите пайплайн и эскалируйте вручную.")
    if not re.search(r"(?i)acceptance\s+criteria", text):
        result.warn("PO: не найдено «acceptance criteria» — убедитесь, что AC описаны.")


def _po_escalation_stop(text: str) -> bool:
    """True если ESCALATION — действие, а не отметка «ESCALATION отсутствует»."""
    for line in text.splitlines():
        if "ESCALATION" not in line:
            continue
        low = line.lower()
        if "отсутствует" in low or "absent" in low or "no escalation" in low:
            continue
        return True
    return False


def _line_negates_open_questions_to_po(line: str) -> bool:
    """Checkpoint / escalation line: no outstanding PO questions."""
    if re.search(r"(?i)(?:^|[\s✓✗\-•*]+)(?:no|нет)\s+Open Questions\s*→\s*PO", line):
        return True
    if re.search(
        r"(?i)Open Questions\s*→\s*PO.*\(\s*(?:нет|none|n/a|no)\s*\)",
        line,
    ):
        return True
    if re.search(r"(?i)To\s+PO\s*:\s*(?:нет|none|n/a|no\b)", line):
        return True
    return False


def _analyst_requires_po_on_open_questions(text: str) -> bool:
    for line in text.splitlines():
        if not re.search(r"(?i)Open Questions\s*→\s*PO", line):
            continue
        if _line_negates_open_questions_to_po(line):
            continue
        return True
    return False


def validate_analyst(text: str, result: ValidationResult) -> None:
    if _analyst_requires_po_on_open_questions(text):
        result.error('Analyst: «Open Questions → PO» — стоп, нужен ответ PO.')
    lower = text.lower()
    if "given" not in lower or "when" not in lower or "then" not in lower:
        result.warn("Analyst: нет явных Given/When/Then (таблица или текст).")
    if not re.search(r"(?i)data\s+flow", text):
        result.warn("Analyst: нет секции/упоминания data flow.")


def validate_architect(text: str, result: ValidationResult) -> None:
    if not re.search(r"(?im)Write-set\s*:", text):
        result.error("Architect: нет блока Write-set (ожидается «Write-set:»).")
    if not re.search(r"(?im)Read-set\s*:", text):
        result.warn("Architect: нет блока Read-set.")
    if not re.search(r"(?im)Do-not-touch\s*:|Do not touch\s*:", text):
        result.warn("Architect: нет границ Do-not-touch / Do not touch.")


def validate_designer(text: str, result: ValidationResult) -> None:
    tl = text.lower()
    required = ("loading", "empty", "error", "populated")
    missing = [s for s in required if s not in tl]
    if missing:
        result.warn(
            "Designer: в тексте не найдены состояния loading/empty/error/populated "
            f"(не найдено: {', '.join(missing)})."
        )


_HANDOFF_SIGNAL_LINE = re.compile(r"(?im)^\s*HANDOFF_SIGNAL\s*:")


def _handoff_signal_present(text: str) -> bool:
    return bool(_HANDOFF_SIGNAL_LINE.search(text))


def _unresolved_section_stop_line(line: str) -> bool:
    if re.match(r"^#{1,4}\s+\S", line):
        return True
    if re.match(r"^\*\*Status\b", line, re.IGNORECASE):
        return True
    if _HANDOFF_SIGNAL_LINE.match(line):
        return True
    if re.match(r"^\[.+\]\s+Step\s+\d", line):
        return True
    return False


def _developer_unresolved_non_empty(text: str) -> bool:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not re.match(r"^#{1,4}\s*Unresolved(?:\s+risk)?\s*$", line):
            continue
        chunk: list[str] = []
        for j in range(i + 1, len(lines)):
            next_line = lines[j]
            if _unresolved_section_stop_line(next_line):
                break
            chunk.append(next_line)
        body = "\n".join(chunk).strip()
        if not body:
            return False
        condensed = re.sub(r"\s+", " ", body).strip()
        if re.fullmatch(r"(?i)[\-•*\s]*(none|нет|n/a|-)[.\s]*", condensed):
            return False
        return True
    return False


def _pytest_failed_reported(text: str) -> bool:
    return bool(re.search(r"(?i)\d+\s+failed\b", text))


def _warn_handoff_signal_developer(text: str, result: ValidationResult) -> None:
    if _handoff_signal_present(text):
        return
    hints: list[str] = []
    if _developer_unresolved_non_empty(text):
        hints.append("непустая секция Unresolved / Unresolved risk")
    if _pytest_failed_reported(text):
        hints.append("упоминание failed в отчёте pytest")
    if hints:
        result.warn(
            "Developer: добавьте строку HANDOFF_SIGNAL: … "
            f"({'; '.join(hints)}). См. doc/team_workflow/developer.md."
        )


def _tester_fail_verdict(text: str) -> bool:
    if re.search(r"(?im)^#{1,6}\s*FAIL\s*$", text):
        return True
    if re.search(r"(?i)\bverdict\s*:\s*FAIL\b", text):
        return True
    return bool(re.search(r"(?i)\*\*verdict\*\*\s*:\s*FAIL\b", text))


def _warn_handoff_signal_tester(text: str, result: ValidationResult) -> None:
    if _handoff_signal_present(text):
        return
    if _tester_fail_verdict(text):
        result.warn(
            "Tester: при вердикте FAIL ожидается строка HANDOFF_SIGNAL: … "
            "(doc/team_workflow/tester.md)."
        )


def validate_developer(text: str, result: ValidationResult) -> None:
    has_changed = bool(re.search(r"(?i)changed\s+files\s*:", text))
    has_table = bool(re.search(r"(?m)\|\s*Файл\s*\|", text))
    has_changes_heading = bool(re.search(r"(?im)^#{1,4}\s*Изменения\s*$", text))
    if not (has_changed or has_table or has_changes_heading):
        result.error(
            "Developer: нет списка изменений "
            "(«Changed files:», таблица «| Файл |» или заголовок «Изменения»)."
        )
    if not re.search(r"(?i)pytest|tests\s+run|\bpassed\b", text):
        result.warn("Developer: нет упоминания pytest, «tests run» или результата passed.")
    _warn_handoff_signal_developer(text, result)


def validate_tester(text: str, result: ValidationResult) -> None:
    if not re.search(r"(?i)verdict|\bPASS\b|\bFAIL\b|CONDITIONAL", text):
        result.warn("Tester: нет явного вердикта (Verdict / PASS / FAIL / CONDITIONAL).")
    _warn_handoff_signal_tester(text, result)


VALIDATORS: dict[str, Callable[[str, ValidationResult], None]] = {
    "po": validate_po,
    "analyst": validate_analyst,
    "architect": validate_architect,
    "designer": validate_designer,
    "developer_sp1": validate_developer,
    "developer_sp2": validate_developer,
    "tester_sp1": validate_tester,
    "tester_sp2": validate_tester,
}


def validate_file(path: Path, kind: str | None, result: ValidationResult) -> None:
    if not path.is_file():
        result.error(f"Файл не найден: {path}")
        return
    name = path.name
    resolved = kind or ARTIFACT_KIND_BY_NAME.get(name)
    if not resolved:
        result.error(
            f"Неизвестный артефакт «{name}». Задайте --kind или используйте каноническое имя файла."
        )
        return
    validator = VALIDATORS.get(resolved)
    if not validator:
        result.error(f"Нет валидатора для kind={resolved}")
        return
    try:
        text = _read_text(path)
    except OSError as exc:
        result.error(f"Не удалось прочитать {path}: {exc}")
        return
    validator(text, result)


def iter_artifact_files(artifacts_dir: Path) -> list[Path]:
    known = sorted(
        (artifacts_dir / name for name in ARTIFACT_KIND_BY_NAME if (artifacts_dir / name).is_file()),
        key=lambda p: p.name,
    )
    return known


def validate_artifacts_directory(artifacts_dir: Path) -> ValidationResult:
    """Проверить все канонические файлы в каталоге пакета (ignore missing files)."""
    overall = ValidationResult()
    if not artifacts_dir.is_dir():
        return overall
    for path in iter_artifact_files(artifacts_dir):
        r = ValidationResult()
        validate_file(path, None, r)
        prefix = f"{path.name}: "
        for e in r.errors:
            overall.errors.append(prefix + e)
        for w in r.warnings:
            overall.warnings.append(prefix + w)
    return overall


def validation_failed(result: ValidationResult, *, strict: bool) -> bool:
    if result.errors:
        return True
    return bool(strict and result.warnings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate team_workflow pipeline markdown artifacts.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Файлы артефактов или каталоги (если каталог — все известные файлы внутри).",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Каталог archive/team_artifacts/<PACKAGE_ID> (проверяет все найденные канонические файлы).",
    )
    parser.add_argument(
        "--kind",
        choices=sorted(set(ARTIFACT_KIND_BY_NAME.values())),
        default=None,
        help="Принудительный тип для одиночного файла с нестандартным именем.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Считать предупреждения ошибками (exit 1).",
    )
    args = parser.parse_args(argv)

    files: list[tuple[Path, str | None]] = []
    if args.artifacts_dir:
        ad = args.artifacts_dir
        if not ad.is_dir():
            print(f"ERROR: не каталог: {ad}", file=sys.stderr)
            return 1
        for p in iter_artifact_files(ad):
            files.append((p, None))
    for raw in args.paths:
        p = raw
        if p.is_dir():
            for q in iter_artifact_files(p):
                files.append((q, None))
        else:
            files.append((p, args.kind if len(args.paths) == 1 else None))

    if not files:
        if args.artifacts_dir is not None:
            print("validate_team_artifact: OK (no canonical artifact files in directory)")
            return 0
        parser.error("Укажите путь к файлу, каталог или --artifacts-dir.")

    overall = ValidationResult()
    for path, kind in files:
        r = ValidationResult()
        validate_file(path, kind, r)
        prefix = f"{path}: "
        for e in r.errors:
            overall.errors.append(prefix + e)
        for w in r.warnings:
            overall.warnings.append(prefix + w)

    for w in overall.warnings:
        print(f"WARN: {w}", file=sys.stderr)
    for e in overall.errors:
        print(f"ERROR: {e}", file=sys.stderr)

    errors = list(overall.errors)
    if args.strict:
        errors.extend(overall.warnings)

    if errors:
        print(f"\nvalidate_team_artifact: FAIL ({len(errors)} issue(s))", file=sys.stderr)
        return 1
    print("validate_team_artifact: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
