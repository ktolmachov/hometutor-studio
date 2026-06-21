#!/usr/bin/env python3
"""
Install local git pre-push hook for US-14.4 loop metrics gate.

The hook runs the same check as ``npm run test:loop-gate``, but invokes
``.venv/Scripts/python.exe`` directly. That avoids Windows/Git-Bash cases
where ``npm`` resolves a different ``python`` on PATH (e.g. PyManager / 3.14).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".git" / "hooks" / "pre-push"

# Full Win32 paths + MSYS2_ARG_CONV_EXCL: avoids broken "cd /d ... && ..." quoting from Git-Bash
# ("The filename, directory name, or volume label is incorrect" from cmd.exe).
HOOK_BODY = r"""#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
if ! command -v cygpath >/dev/null 2>&1; then
  echo "[pre-push] FAIL: cygpath not found (use Git for Windows bash)." >&2
  exit 2
fi
REPO_WIN="$(cygpath -w "$REPO_ROOT")"
PY="${REPO_WIN}\\.venv\\Scripts\\python.exe"
SCR="${REPO_WIN}\\scripts\\check_loop_metrics_gate.py"
export MSYS2_ARG_CONV_EXCL='*'
echo "[pre-push] Running loop metrics gate..."
cmd.exe //c "\"${PY}\" \"${SCR}\""
echo "[pre-push] Loop metrics gate passed."
"""


def _venv_runtime_report() -> tuple[int, str]:
    """Return (exit_code, report) with executable + base_prefix (stdlib home for venv)."""
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_py.is_file():
        return 2, "missing .venv\\Scripts\\python.exe"
    proc = subprocess.run(
        [
            str(venv_py),
            "-c",
            "import sys; base=getattr(sys, 'base_prefix', sys.prefix); "
            "print(sys.executable); print(base)",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode, out


def main() -> int:
    if not (ROOT / ".git").exists():
        print("FAIL: .git directory not found.")
        return 2

    code, exe_out = _venv_runtime_report()
    if code != 0:
        print("FAIL: .venv Python does not run:", exe_out or f"exit {code}")
        return 2
    if "Python314" in exe_out or "pythoncore-3.14" in exe_out.lower():
        print("FAIL: .venv still uses Python 3.14 stdlib (check 2nd line = base_prefix):")
        print(exe_out)
        print("Recreate venv from repo root with Python 3.12 only, e.g.:")
        print(r'  Remove-Item -Recurse -Force .venv')
        print(
            r'  & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv'
        )
        return 2

    HOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    HOOK_PATH.write_text(HOOK_BODY, encoding="utf-8")
    try:
        HOOK_PATH.chmod(0o755)
    except OSError:
        # On some Windows setups chmod is partially supported; best effort.
        pass
    print(f"Installed pre-push hook: {HOOK_PATH}")
    pyvenv = ROOT / ".venv" / "pyvenv.cfg"
    if pyvenv.is_file():
        raw = pyvenv.read_text(encoding="utf-8", errors="replace")
        if "Python314" in raw or "pythoncore-3.14" in raw.lower():
            print(
                "WARN: .venv is tied to Python 3.14 (see .venv/pyvenv.cfg). "
                "Recreate: py -3.12 -m venv .venv --clear"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
