"""Prompt route registry for autonomous workflow decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "policies" / "prompts_registry.yaml"


@dataclass(frozen=True)
class PromptRoute:
    name: str
    template: str


def load_registry(path: Path | str = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("prompt registry must be a mapping")
    return dict(data)


def resolve_route(action: str, registry: Mapping[str, Any] | None = None) -> PromptRoute:
    doc = registry or load_registry()
    normalized = action.strip().casefold()
    for route in doc.get("routes", []) or []:
        if not isinstance(route, Mapping):
            continue
        actions = [str(item).casefold() for item in route.get("actions", []) or []]
        if normalized in actions:
            return PromptRoute(name=str(route["name"]), template=str(route["template"]))
    default_name = str(doc.get("default_route", ""))
    for route in doc.get("routes", []) or []:
        if isinstance(route, Mapping) and str(route.get("name", "")) == default_name:
            return PromptRoute(name=str(route["name"]), template=str(route["template"]))
    raise KeyError(f"no prompt route for action {action!r}")
