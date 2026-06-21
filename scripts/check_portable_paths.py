#!/usr/bin/env python3
"""Fail if repository text files contain machine-local command paths."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SKIP_DIRS = {
    ".cursor",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".python",
    "__pycache__",
    "node_modules",
    "dist",
    "chroma_db",
    "eval_data",
    "eval_results",
    "logs",
}

DEFAULT_SKIP_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".pyc",
    ".webp",
    ".zip",
}


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    suggestion: str


RULES = (
    Rule(
        name="absolute workspace path",
        pattern=re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?:[^`'\"\s]+[\\/])*home-rag_v2(?=[\\/`'\"\s]|$)", re.IGNORECASE),
        suggestion="Use a repository-relative path, or say: из корня репозитория.",
    ),
    Rule(
        name="legacy local python executable",
        pattern=re.compile(r"(?:^|(?<![\w.-]))(?:\.?[\\/])?\.python[\\/]python\.exe", re.IGNORECASE),
        suggestion=r"Use .\.venv\Scripts\python.exe from the repository root; fallback to python/py only if .venv is unavailable.",
    ),
)


def _is_skipped(path: Path, skip_dirs: set[str]) -> bool:
    return any(part in skip_dirs for part in path.parts)


def _iter_files(paths: list[Path], skip_dirs: set[str], skip_suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        if not path.exists():
            continue
        if path.is_file():
            rel = path.relative_to(ROOT)
            if not _is_skipped(rel, skip_dirs) and path.suffix.lower() not in skip_suffixes:
                files.append(path)
            continue
        for candidate in path.rglob("*"):
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(ROOT)
            if _is_skipped(rel, skip_dirs):
                continue
            if candidate.suffix.lower() in skip_suffixes:
                continue
            files.append(candidate)
    return sorted(set(files))


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def check(paths: list[Path], skip_dirs: set[str], skip_suffixes: set[str]) -> list[str]:
    findings: list[str] = []
    for path in _iter_files(paths, skip_dirs, skip_suffixes):
        text = _read_text(path)
        if text is None:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for rule in RULES:
                if rule.pattern.search(line):
                    findings.append(f"{rel}:{line_no}: {rule.name}: {rule.suggestion}")
    return findings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[
            Path("AGENTS.md"),
            Path("package.json"),
            Path("app"),
            Path("archive"),
            Path("doc"),
            Path("scripts"),
            Path("tests"),
        ],
        help="Files or directories to scan. Defaults to portable source/documentation paths.",
    )
    parser.add_argument(
        "--skip-dir",
        action="append",
        default=[],
        help="Additional directory name to skip.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    skip_dirs = DEFAULT_SKIP_DIRS | set(args.skip_dir)
    findings = check(args.paths, skip_dirs, DEFAULT_SKIP_SUFFIXES)

    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        print(f"PORTABLE PATHS FAILED: {len(findings)} issue(s)", file=sys.stderr)
        return 1

    print("PORTABLE PATHS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
