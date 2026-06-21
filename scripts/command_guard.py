"""Pure command policy checks for agent-controlled subprocess calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

Decision = Literal["ALLOW", "BLOCK"]
PolicyDoc = Mapping[str, Any]


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    reason: str

    def __iter__(self):
        yield self.decision
        yield self.reason


def _norm(value: object) -> str:
    return str(value).strip().lower().replace("\\", "/")


def _matches_prefix(cmd: Sequence[str], prefix: Sequence[object]) -> bool:
    if len(cmd) < len(prefix):
        return False
    return [_norm(part) for part in cmd[: len(prefix)]] == [_norm(part) for part in prefix]


def check(cmd: list[str], policy: PolicyDoc) -> Verdict:
    """Return ALLOW/BLOCK for one already-tokenized command.

    This function intentionally does no file or environment I/O; callers provide
    the policy document explicitly.
    """
    if not cmd or not str(cmd[0]).strip():
        return Verdict("BLOCK", "empty command")

    for rule in policy.get("blocked_commands", []):
        if not isinstance(rule, Mapping):
            continue
        prefix = rule.get("prefix", [])
        if isinstance(prefix, list) and _matches_prefix(cmd, prefix):
            return Verdict("BLOCK", str(rule.get("reason") or "blocked command"))

    normalized_args = [_norm(arg) for arg in cmd]
    for token in policy.get("blocked_shell_tokens", []):
        needle = str(token)
        if needle and any(needle in str(arg) for arg in cmd):
            return Verdict("BLOCK", f"blocked shell control token: {token}")

    for fragment in policy.get("blocked_arg_fragments", []):
        needle = _norm(fragment)
        if needle and any(needle in arg for arg in normalized_args):
            return Verdict("BLOCK", f"blocked sensitive path fragment: {fragment}")

    return Verdict("ALLOW", "allowed")
