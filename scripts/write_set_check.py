"""Write-set parsing and pre-commit drift checks for current_task.md."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WriteSetResult:
    write_set: tuple[str, ...]
    changed_paths: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    missing_write_set: bool = False


def parse_write_set(task_text: str) -> list[str]:
    """Parse markdown bullets under `## Write-Set` from current_task.md."""
    lines = task_text.splitlines()
    in_section = False
    paths: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped.casefold() == "## write-set"
            continue
        if not in_section:
            continue
        if stripped.startswith(("- ", "* ")):
            value = stripped[2:].strip().strip("`")
            if value:
                paths.append(value.replace("\\", "/"))
    return paths


def _git_status_paths(root: Path = ROOT) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root),
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    paths: list[str] = []
    for line in (result.stdout or "").splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1]
        paths.append(path.replace("\\", "/"))
    return paths


def _in_scope(path: str, allowed: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for item in allowed:
        prefix = item.rstrip("/")
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
    return False


def check_current_task(
    task_path: Path | None = None,
    *,
    root: Path = ROOT,
    changed_paths: list[str] | None = None,
) -> WriteSetResult:
    """Return modified/untracked files outside the current task write-set."""
    path = task_path or root / "doc" / "current_task.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return WriteSetResult((), tuple(changed_paths or _git_status_paths(root)), (), True)

    write_set = parse_write_set(text)
    changed = changed_paths if changed_paths is not None else _git_status_paths(root)
    if not write_set:
        return WriteSetResult((), tuple(changed), tuple(changed), True)
    out = [p for p in changed if not _in_scope(p, write_set)]
    return WriteSetResult(tuple(write_set), tuple(changed), tuple(out), False)
