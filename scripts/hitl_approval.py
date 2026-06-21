"""Human-in-the-loop approval policy helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "policies" / "hitl_approval_policy.yaml"


@dataclass(frozen=True)
class ApprovalVerdict:
    required: bool
    action: str
    reason: str = ""


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("HITL approval policy must be a mapping")
    return dict(data)


def requires_approval(action: str, policy: Mapping[str, Any] | None = None) -> ApprovalVerdict:
    doc = policy or load_policy()
    normalized = action.strip().casefold()
    for item in doc.get("actions", []) or []:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("name", "")).casefold() != normalized:
            continue
        required = bool(item.get("requires_approval", False))
        return ApprovalVerdict(
            required=required,
            action=action,
            reason=str(item.get("reason", "")) if required else "",
        )
    return ApprovalVerdict(required=False, action=action)


def assert_approved(
    action: str,
    *,
    approved: bool,
    policy: Mapping[str, Any] | None = None,
) -> ApprovalVerdict:
    verdict = requires_approval(action, policy)
    if verdict.required and not approved:
        raise PermissionError(f"approval required for {action}: {verdict.reason}")
    return verdict
