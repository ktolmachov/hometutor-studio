from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture()
def isolated_recorder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    import pipeline_events as pe
    import pipeline_state as ps
    import run_recorder as rr

    ar = tmp_path / "logs" / "autonomous_runs"
    monkeypatch.setattr(pe, "AUTONOMOUS_RUNS_ROOT", ar)
    monkeypatch.setattr(pe, "CURRENT_DIR", ar / "current")
    monkeypatch.setattr(pe, "ORPHAN_DIR", ar / "_orphan")
    monkeypatch.setattr(ps, "AUTONOMOUS_RUNS_ROOT", ar)
    monkeypatch.setattr(rr, "AUTONOMOUS_RUNS_ROOT", ar)
    return pe, ps, rr


def test_snapshots_monotonic(isolated_recorder) -> None:
    pe, ps, _rr = isolated_recorder
    run_id = "run-1"

    ps.bootstrap(run_id, package_id="epoch-demo", initial_phase="execution")
    ps.update(run_id, phase="post_agent")
    ps.finalize_for_exit(run_id, exit_code=0)

    snapshot_dir = pe.AUTONOMOUS_RUNS_ROOT / run_id / "state_snapshots"
    names = [path.name for path in sorted(snapshot_dir.glob("*.json"))]
    assert [name.split("_", 1)[0] for name in names] == ["0001", "0002", "0003"]
    assert names[-1].endswith("_closed.json")


def test_event_log_append_only(isolated_recorder) -> None:
    pe, ps, _rr = isolated_recorder
    run_id = "run-2"

    ps.bootstrap(run_id, package_id="epoch-demo", initial_phase="execution")
    ps.update(run_id, proof_status="partial")

    event_log = pe.AUTONOMOUS_RUNS_ROOT / run_id / "event_log.jsonl"
    lines = event_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["seq"] for line in lines] == [1, 2]


def test_replay_manifest_structural_validation(isolated_recorder) -> None:
    _pe, ps, rr = isolated_recorder
    run_id = "run-3"

    ps.bootstrap(run_id, package_id="epoch-demo", initial_phase="execution")
    manifest = rr.build_replay_manifest(run_id)

    assert rr.validate_replay_manifest(manifest) == []
    assert manifest["run_id"] == run_id
    assert len(manifest["snapshots"]) == 1


def test_replay_run_dry_run_validates_manifest(isolated_recorder, capsys: pytest.CaptureFixture[str]) -> None:
    _pe, ps, _rr = isolated_recorder
    import replay_run

    run_id = "run-4"
    ps.bootstrap(run_id, package_id="epoch-demo", initial_phase="execution")

    assert replay_run.main(["--run-id", run_id, "--dry-run"]) == 0
    out = capsys.readouterr().out
    manifest = json.loads(out)
    assert manifest["run_id"] == run_id
    assert len(manifest["snapshots"]) == 1
