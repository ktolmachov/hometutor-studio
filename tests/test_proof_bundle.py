from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def isolated_proof(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import pipeline_events as pe
    import proof_bundle as pb

    monkeypatch.setattr(pb, "ROOT", tmp_path)
    monkeypatch.setattr(pb, "AUTONOMOUS_RUNS_ROOT", tmp_path / "logs" / "autonomous_runs")
    monkeypatch.setattr(pe, "AUTONOMOUS_RUNS_ROOT", tmp_path / "logs" / "autonomous_runs")
    monkeypatch.setattr(pe, "CURRENT_DIR", tmp_path / "logs" / "autonomous_runs" / "current")
    monkeypatch.setattr(pe, "ORPHAN_DIR", tmp_path / "logs" / "autonomous_runs" / "_orphan")
    return pe, pb, tmp_path


def test_validate_recomputes_sha256(isolated_proof) -> None:
    _pe, pb, root = isolated_proof
    package_id = "epoch-demo"
    run_id = "run-proof"
    exec_contract = root / "archive" / "team_artifacts" / package_id / "execution_contract.md"
    exec_contract.parent.mkdir(parents=True)
    exec_contract.write_text("proof\n", encoding="utf-8")
    run_dir = pb.ensure_run_dir(run_id)
    (run_dir / "event_log.jsonl").write_text('{"event":"x"}\n', encoding="utf-8")

    manifest_path = pb.build(run_id, package_id)
    assert manifest_path.exists()
    assert pb.validate(package_id, run_id=run_id) == (True, "ok")

    exec_contract.write_text("tampered\n", encoding="utf-8")
    ok, reason = pb.validate(package_id, run_id=run_id)
    assert ok is False
    assert "checksum" in reason


def test_orphan_event_on_missing_run_id(isolated_proof) -> None:
    pe, pb, _root = isolated_proof

    ok, reason = pb.validate("epoch-demo", env={})

    assert ok is False
    assert "run_id" in reason
    orphan = pe.orphan_log_path_today()
    last = json.loads(orphan.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["event"] == "PROOF_MISSING"
