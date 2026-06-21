"""I/O wrapper for running agent-controlled commands through command_guard."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from command_guard import PolicyDoc, check

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "policies" / "agent_sandbox_policy.yaml"


class SandboxViolationError(RuntimeError):
    """Raised when policy blocks an agent-controlled command."""


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> PolicyDoc:
    """Load policy once at orchestration boundary.

    The policy file is YAML-compatible JSON to avoid introducing a parser
    dependency in this control-plane layer.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("agent sandbox policy must be a mapping")
    return data


_POLICY: PolicyDoc | None = None


def _policy() -> PolicyDoc:
    global _POLICY
    if _POLICY is None:
        _POLICY = load_policy()
    return _POLICY


def tokenize_shell_command(command: str) -> list[str]:
    """Best-effort tokenization for legacy contract commands."""
    tokens = shlex.split(command, posix=False)
    return [
        token[1:-1]
        if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"')
        else token
        for token in tokens
    ]


def _validate(cmd: Sequence[str], policy: PolicyDoc | None = None) -> list[str]:
    tokens = [str(part) for part in cmd]
    verdict = check(tokens, policy or _policy())
    if verdict.decision == "BLOCK":
        raise SandboxViolationError(verdict.reason)
    return tokens


def safe_run(
    cmd: list[str],
    *,
    policy: PolicyDoc | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Run a tokenized command after policy validation."""
    if kwargs.get("text") is True or kwargs.get("universal_newlines") is True:
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    return subprocess.run(_validate(cmd, policy), **kwargs)


def _run_win32_npm_family_merged_streams(
    tokens: list[str],
    *,
    policy: PolicyDoc | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Windows/PowerShell: merge child stderr into stdout for npm/npx.

    Playwright and the e2e stack log `[WebServer]` lines to stderr; when stderr is
    inherited, PowerShell 5.1 may surface those as NativeCommandError records and
    confuse tooling that relies on ``$LASTEXITCODE`` / exit propagation.
    """
    validated = _validate(tokens, policy)
    run_kw = {k: v for k, v in kwargs.items() if k in ("cwd", "env", "timeout")}
    cp = subprocess.run(
        validated,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        **run_kw,
    )
    if cp.stdout:
        sys.stdout.write(cp.stdout)
        if not cp.stdout.endswith("\n"):
            sys.stdout.write("\n")
    return cp


def safe_run_shell(
    command: str,
    *,
    policy: PolicyDoc | None = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Run a legacy shell command after validating the parsed command tokens."""
    tokens = tokenize_shell_command(command)
    # Windows: bare `npm` / `npx` fails under subprocess (no npm.exe); PATH has npm.CMD.
    if sys.platform == "win32" and tokens:
        exe = tokens[0].lower()
        if exe in ("npm", "npx"):
            resolved = shutil.which(tokens[0])
            if resolved:
                tokens = [resolved, *tokens[1:]]
        stem = Path(tokens[0]).stem.lower()
        if stem in ("npm", "npx"):
            return _run_win32_npm_family_merged_streams(tokens, policy=policy, **kwargs)
    return safe_run(tokens, policy=policy, **kwargs)
