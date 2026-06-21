"""Declarative exit-code classification for autonomous pipeline results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "policies" / "failure_classes.yaml"


@dataclass(frozen=True)
class FailureClass:
    exit_code: int
    name: str
    severity: str
    next_action: str
    retryable: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "exit_code": self.exit_code,
            "name": self.name,
            "severity": self.severity,
            "next_action": self.next_action,
            "retryable": self.retryable,
        }


UNKNOWN = FailureClass(-1, "unknown_exit_code", "error", "inspect_pipeline_logs", False)


def _parse_class(exit_code: int, raw: Mapping[str, object]) -> FailureClass:
    missing = {"name", "severity", "next_action", "retryable"} - set(raw)
    if missing:
        raise ValueError(f"failure class {exit_code} missing fields: {sorted(missing)}")
    if not isinstance(raw["retryable"], bool):
        raise ValueError(f"failure class {exit_code} retryable must be boolean")
    return FailureClass(
        exit_code=exit_code,
        name=str(raw["name"]),
        severity=str(raw["severity"]),
        next_action=str(raw["next_action"]),
        retryable=raw["retryable"],
    )


def load_failure_classes(path: Path | str = DEFAULT_POLICY_PATH) -> dict[int, FailureClass]:
    """Load exit-code policy from a YAML-compatible JSON document."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    classes = data.get("classes") if isinstance(data, Mapping) else None
    if not isinstance(classes, Mapping):
        raise ValueError("failure class policy must contain a 'classes' mapping")

    parsed: dict[int, FailureClass] = {}
    for code_raw, class_raw in classes.items():
        if not isinstance(class_raw, Mapping):
            raise ValueError(f"failure class {code_raw!r} must be a mapping")
        parsed[int(code_raw)] = _parse_class(int(code_raw), class_raw)
    return parsed


_CLASSES: dict[int, FailureClass] | None = None


def _classes() -> dict[int, FailureClass]:
    global _CLASSES
    if _CLASSES is None:
        _CLASSES = load_failure_classes()
    return _CLASSES


def classify_exit_code(exit_code: int) -> FailureClass:
    return _classes().get(
        exit_code,
        FailureClass(exit_code, UNKNOWN.name, UNKNOWN.severity, UNKNOWN.next_action, UNKNOWN.retryable),
    )
