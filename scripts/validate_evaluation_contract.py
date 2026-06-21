#!/usr/bin/env python3
"""Validate PO Router evaluation-contract YAML files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "doc" / "team_workflow" / "templates" / "evaluation_contract_template.yaml"

REQUIRED_PATHS = (
    "evaluation_contract.feature",
    "evaluation_contract.owner_decision",
    "evaluation_contract.metrics.primary.name",
    "evaluation_contract.metrics.primary.type",
    "evaluation_contract.metrics.primary.baseline",
    "evaluation_contract.metrics.primary.target",
    "evaluation_contract.metrics.primary.test_set",
    "evaluation_contract.metrics.secondary",
    "evaluation_contract.test_harness.script",
    "evaluation_contract.test_harness.data",
    "evaluation_contract.test_harness.command",
    "evaluation_contract.success_criteria",
    "evaluation_contract.failure_plan",
    "evaluation_contract.fallback.mode",
    "evaluation_contract.fallback.trigger",
    "evaluation_contract.fallback.user_visible_trace",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: pip install pyyaml")
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


def _get_path(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def validate_contract(data: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors."""
    errors: list[str] = []
    for dotted_path in REQUIRED_PATHS:
        value = _get_path(data, dotted_path)
        if value in (None, "", [], {}):
            errors.append(f"missing or empty: {dotted_path}")

    secondary = _get_path(data, "evaluation_contract.metrics.secondary")
    if isinstance(secondary, list):
        for index, metric in enumerate(secondary):
            if not isinstance(metric, dict):
                errors.append(f"metrics.secondary[{index}] must be a mapping")
                continue
            for key in ("name", "target"):
                if not metric.get(key):
                    errors.append(f"metrics.secondary[{index}] missing {key}")

    failure_plan = _get_path(data, "evaluation_contract.failure_plan")
    if isinstance(failure_plan, list):
        for index, item in enumerate(failure_plan):
            if not isinstance(item, dict):
                errors.append(f"failure_plan[{index}] must be a mapping")
                continue
            for key in ("condition", "action"):
                if not item.get(key):
                    errors.append(f"failure_plan[{index}] missing {key}")

    return errors


def validate_file(path: Path, template_path: Path = DEFAULT_TEMPLATE) -> list[str]:
    """Validate a contract file and make sure the reference template is readable."""
    if not template_path.exists():
        return [f"template not found: {template_path}"]
    _load_yaml(template_path)
    return validate_contract(_load_yaml(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an evaluation-contract YAML file.")
    parser.add_argument("contract", type=Path, help="Path to evaluation-contract YAML.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    args = parser.parse_args(argv)

    errors = validate_file(args.contract, args.template)
    if errors:
        print(f"FAIL {args.contract}")
        for error in errors:
            print(f"- {error}")
        return 2
    print(f"OK {args.contract}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
