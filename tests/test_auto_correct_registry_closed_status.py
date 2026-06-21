from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "auto_correct_registry_closed_status.py"


@pytest.fixture(scope="module")
def autocorrect_module():
    spec = importlib.util.spec_from_file_location("auto_correct_registry_closed_status", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_rewrite_closes_only_packages_present_in_closed_iterations(autocorrect_module):
    registry_text = """schema_version: 2
items:
  - id: epoch-a
    status: ready
  - id: epoch-b
    status: wip
  - id: epoch-c
    status: closed
"""
    closed_ids = {"epoch-a", "epoch-c"}

    updated, changed = autocorrect_module._rewrite_registry_statuses(registry_text, closed_ids)

    assert "id: epoch-a\n    status: closed" in updated
    assert "id: epoch-b\n    status: wip" in updated
    assert "id: epoch-c\n    status: closed" in updated
    assert set(changed) == {"epoch-a"}

