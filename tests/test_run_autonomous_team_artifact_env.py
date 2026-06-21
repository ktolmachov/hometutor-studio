"""HOME_RAG_* env forwarded into ClosePackageArgs from run_autonomous."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture()
def ra(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import run_autonomous

    return run_autonomous


def test_team_artifact_env_defaults_cleared(ra, monkeypatch):
    monkeypatch.delenv("HOME_RAG_SKIP_TEAM_ARTIFACTS_GATE", raising=False)
    monkeypatch.delenv("HOME_RAG_TEAM_ARTIFACTS_STRICT", raising=False)

    k = ra.close_package_team_artifact_kwargs_from_env()

    assert k == {"skip_team_artifacts_check": False, "team_artifacts_strict": False}


@pytest.mark.parametrize("truthy", ["1", "true", "yes", "on"])
def test_team_artifact_strict_env(truthy, ra, monkeypatch):
    monkeypatch.delenv("HOME_RAG_SKIP_TEAM_ARTIFACTS_GATE", raising=False)
    monkeypatch.setenv("HOME_RAG_TEAM_ARTIFACTS_STRICT", truthy)

    assert ra.close_package_team_artifact_kwargs_from_env()["team_artifacts_strict"] is True


def test_team_artifact_skip_env(ra, monkeypatch):
    monkeypatch.delenv("HOME_RAG_TEAM_ARTIFACTS_STRICT", raising=False)
    monkeypatch.setenv("HOME_RAG_SKIP_TEAM_ARTIFACTS_GATE", "1")

    assert ra.close_package_team_artifact_kwargs_from_env()["skip_team_artifacts_check"] is True
