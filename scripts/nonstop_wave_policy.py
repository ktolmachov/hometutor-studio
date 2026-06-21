"""Declarative safety policy for run_autonomous --non-stop chains."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "policies" / "nonstop_wave_policy.yaml"
STARTED_AT_ENV = "HOME_RAG_NON_STOP_STARTED_AT"


@dataclass(frozen=True)
class NonStopPolicy:
    enabled: bool = True
    max_next_tasks: int = 50
    max_runtime_seconds: int = 14_400


@dataclass(frozen=True)
class NonStopVerdict:
    ok: bool
    reason: str = ""
    effective_max_next_tasks: int = 50


def _as_policy(data: Mapping[str, Any]) -> NonStopPolicy:
    return NonStopPolicy(
        enabled=bool(data.get("enabled", True)),
        max_next_tasks=max(0, int(data.get("max_next_tasks", 50))),
        max_runtime_seconds=max(0, int(data.get("max_runtime_seconds", 14_400))),
    )


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> NonStopPolicy:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("nonstop wave policy must be a mapping")
    return _as_policy(data)


def ensure_chain_started_at(env: dict[str, str] | None = None) -> str:
    target = env if env is not None else os.environ
    existing = target.get(STARTED_AT_ENV)
    if existing:
        return existing
    value = str(int(time.time()))
    target[STARTED_AT_ENV] = value
    return value


def evaluate(
    *,
    requested_non_stop: bool,
    chain_step: int,
    cli_max_next_tasks: int,
    policy: NonStopPolicy,
    env: Mapping[str, str] | None = None,
    now: float | None = None,
) -> NonStopVerdict:
    """Validate non-stop chain limits without mutating process state."""
    effective_max = min(cli_max_next_tasks, policy.max_next_tasks)
    if not requested_non_stop:
        return NonStopVerdict(True, effective_max_next_tasks=effective_max)
    if not policy.enabled:
        return NonStopVerdict(False, "non-stop mode disabled by policy", effective_max)
    if chain_step < 0:
        return NonStopVerdict(False, "non-stop chain step must be >= 0", effective_max)
    if chain_step > effective_max:
        return NonStopVerdict(
            False,
            f"non-stop chain step {chain_step} exceeds policy max {effective_max}",
            effective_max,
        )
    source_env = env if env is not None else os.environ
    started_raw = source_env.get(STARTED_AT_ENV)
    if started_raw and policy.max_runtime_seconds:
        try:
            started = float(started_raw)
        except ValueError:
            return NonStopVerdict(False, "invalid non-stop started-at timestamp", effective_max)
        elapsed = (now if now is not None else time.time()) - started
        if elapsed > policy.max_runtime_seconds:
            return NonStopVerdict(
                False,
                f"non-stop runtime {int(elapsed)}s exceeds policy max {policy.max_runtime_seconds}s",
                effective_max,
            )
    return NonStopVerdict(True, effective_max_next_tasks=effective_max)
