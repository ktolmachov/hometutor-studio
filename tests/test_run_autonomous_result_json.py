"""Integration: run_autonomous exit writes result.json + pipeline_state (in-process)."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_AUTO = str(ROOT / "scripts" / "run_autonomous.py")


def test_help_writes_result_and_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pipeline_events as pe
    import pipeline_state as ps

    ar = tmp_path / "autonomous_runs"
    monkeypatch.setattr(pe, "AUTONOMOUS_RUNS_ROOT", ar)
    monkeypatch.setattr(pe, "CURRENT_DIR", ar / "current")
    monkeypatch.setattr(pe, "ORPHAN_DIR", ar / "_orphan")
    monkeypatch.setattr(ps, "AUTONOMOUS_RUNS_ROOT", ar)

    rid = f"pytest-{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("HOME_RAG_RUN_ID", rid)
    monkeypatch.setattr(sys, "argv", [RUN_AUTO, "--help"])

    import run_autonomous as ra

    # main() catches SystemExit from argparse (--help) and returns an exit code
    # after pipeline finalize + result.json (see run_autonomous.main try/finally).
    rc = ra.main()
    assert rc == 0

    run_dir = ar / rid
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    req_r = json.loads((ROOT / "schemas" / "pipeline_result.schema.json").read_text(encoding="utf-8"))[
        "required"
    ]
    for k in req_r:
        assert k in result
    assert result["exit_code"] == 0

    state = json.loads((run_dir / "pipeline_state.json").read_text(encoding="utf-8"))
    req_s = json.loads((ROOT / "schemas" / "pipeline_state.schema.json").read_text(encoding="utf-8"))[
        "required"
    ]
    for k in req_s:
        assert k in state
    assert state["phase"] == "closed"
