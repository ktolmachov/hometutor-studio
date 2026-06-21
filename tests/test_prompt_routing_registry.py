from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prompt_routing_registry import load_registry, resolve_route


def test_resolve_route_by_action() -> None:
    route = resolve_route(
        "ORCHESTRATION",
        registry={
            "routes": [
                {"name": "orchestration", "actions": ["ORCHESTRATION"], "template": "orch.md"}
            ]
        },
    )
    assert route.name == "orchestration"
    assert route.template == "orch.md"


def test_resolve_route_uses_default() -> None:
    route = resolve_route(
        "UNKNOWN",
        registry={
            "default_route": "execution_auto",
            "routes": [
                {"name": "execution_auto", "actions": ["EXECUTION_AUTO"], "template": "exec.py"}
            ],
        },
    )
    assert route.name == "execution_auto"


def test_default_registry_loads() -> None:
    registry = load_registry()
    assert registry["routes"]
