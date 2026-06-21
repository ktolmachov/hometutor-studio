"""Resolve local ``tsx`` for DeepSeek trigger pytest suites."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def resolve_tsx_executable(root: Path = ROOT) -> Path | None:
    """Return a runnable tsx binary, preferring repo-local ``node_modules``."""
    candidates: list[Path] = []
    if os.name == "nt":
        candidates.append(root / "node_modules" / ".bin" / "tsx.cmd")
        candidates.append(root / "node_modules" / ".bin" / "tsx")
    else:
        candidates.append(root / "node_modules" / ".bin" / "tsx")

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    for name in ("tsx", "tsx.cmd", "npx", "npx.cmd"):
        found = shutil.which(name)
        if found:
            return Path(found)

    return None


def tsx_available(root: Path = ROOT) -> bool:
    return resolve_tsx_executable(root) is not None


requires_tsx = pytest.mark.skipif(
    not tsx_available(),
    reason="tsx unavailable — run `npm install` in repo root to enable DeepSeek trigger tests",
)


def run_tsx_script(
    script_path: Path,
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: float | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    tsx = resolve_tsx_executable()
    if tsx is None:
        raise RuntimeError(
            "tsx is unavailable: run `npm install` in the repo root (devDependency: tsx)."
        )

    script = script_path.resolve()
    workdir = (cwd or ROOT).resolve()
    command: list[str]
    tsx_name = tsx.name.lower()
    if tsx_name.startswith("npx"):
        command = [str(tsx), "tsx", str(script)]
    else:
        command = [str(tsx), str(script)]

    return subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=workdir,
        timeout=timeout,
        check=check,
    )
