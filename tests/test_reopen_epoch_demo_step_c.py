"""Tests for scripts/reopen_epoch_demo_step_c.py (Truth View singleton helpers)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reopen_epoch_demo_step_c.py"


@pytest.fixture(scope="module")
def reopen_mod():
    spec = importlib.util.spec_from_file_location("reopen_epoch_demo_step_c", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


YAML_TWO_OTHERS = """schema_version: 2
items:
  - id: epoch-demo
    status: ready
    impact: infra
  - id: pkg-a
    status: ready
    impact: infra
  - id: pkg-b
    status: wip
    impact: infra
"""


def test_demote_other_now_packages_moves_ready_wip_to_proposed(reopen_mod):
    text2, ids = reopen_mod._demote_other_now_packages(YAML_TWO_OTHERS, "epoch-demo")
    assert ids == ["pkg-a", "pkg-b"]
    data = yaml.safe_load(text2)
    by_id = {str(it["id"]): str(it["status"]) for it in data["items"]}
    assert by_id["epoch-demo"] == "ready"
    assert by_id["pkg-a"] == "proposed"
    assert by_id["pkg-b"] == "proposed"


def test_iter_other_now_package_ids_sorted_unique(reopen_mod):
    yaml_dup = YAML_TWO_OTHERS + ""
    ids = reopen_mod._iter_other_now_package_ids(yaml_dup, "epoch-demo")
    assert ids == ["pkg-a", "pkg-b"]
