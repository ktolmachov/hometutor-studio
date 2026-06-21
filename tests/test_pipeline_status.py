from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pipeline_status as ps


def test_build_runs_timeline_from_autonomous_logs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    (run_dir / "event_log.jsonl").write_text(
        '{"ts":"2026-04-28T10:00:00Z","event":"phase_change"}\n',
        encoding="utf-8",
    )
    (run_dir / "pipeline_state.json").write_text(
        json.dumps({"phase": "closed"}),
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "package_id": "epoch-demo",
                "exit_code": 0,
                "finished_at": "2026-04-28T10:00:03Z",
                "failure_class": {"name": "success"},
            }
        ),
        encoding="utf-8",
    )

    report = ps.build_runs_timeline(tmp_path)

    assert report["runs"][0]["run_id"] == "run-1"
    assert report["runs"][0]["duration_s"] == 3.0
    assert report["runs"][0]["proof_ok"] is True
    assert report["stats"]["closure_success_rate"] == 1.0
    assert report["stats"]["false_closure_rate"] == 0.0


def test_build_runs_timeline_false_closure_from_proof_event(tmp_path: Path) -> None:
    run_dir = tmp_path / "bad-proof"
    run_dir.mkdir()
    (run_dir / "event_log.jsonl").write_text(
        '{"ts":"2026-04-28T11:00:00Z","event":"PROOF_TAMPERED"}\n',
        encoding="utf-8",
    )
    (run_dir / "pipeline_state.json").write_text(
        json.dumps({"phase": "closed"}), encoding="utf-8"
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "bad-proof",
                "package_id": "epoch-demo",
                "exit_code": 0,
                "finished_at": "2026-04-28T11:00:02Z",
            }
        ),
        encoding="utf-8",
    )

    report = ps.build_runs_timeline(tmp_path)
    assert report["runs"][0]["proof_ok"] is False
    assert report["stats"]["false_closure_rate"] == 1.0


def test_build_runs_timeline_skips_service_dirs(tmp_path: Path) -> None:
    orphan = tmp_path / "_orphan" / "nested"
    orphan.mkdir(parents=True)
    (orphan / "result.json").write_text('{"run_id":"x","exit_code":0}', encoding="utf-8")

    real = tmp_path / "real-run"
    real.mkdir()
    (real / "result.json").write_text(
        json.dumps(
            {
                "run_id": "real-run",
                "exit_code": 0,
                "finished_at": "2026-04-28T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    report = ps.build_runs_timeline(tmp_path)
    assert len(report["runs"]) == 1
    assert report["runs"][0]["run_id"] == "real-run"


def test_build_runs_timeline_sandbox_block_rate(tmp_path: Path) -> None:
    run_dir = tmp_path / "with-sb"
    run_dir.mkdir()
    (run_dir / "event_log.jsonl").write_text(
        '{"ts":"2026-04-28T13:00:00Z","event":"SANDBOX_BLOCK"}\n'
        '{"ts":"2026-04-28T13:00:01Z","event":"SANDBOX_ESCAPE"}\n',
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "with-sb",
                "exit_code": 2,
                "finished_at": "2026-04-28T13:00:02Z",
            }
        ),
        encoding="utf-8",
    )

    report = ps.build_runs_timeline(tmp_path)
    assert report["stats"]["sandbox_blocks_total"] == 1
    assert report["stats"]["sandbox_escape_total"] == 1
    assert report["stats"]["prompt_injection_block_rate"] == 0.5


def test_build_runs_timeline_counts_failure_classes(tmp_path: Path) -> None:
    for idx, name in enumerate(["dod_failed", "dod_failed", "success"]):
        run_dir = tmp_path / f"run-{idx}"
        run_dir.mkdir()
        (run_dir / "result.json").write_text(
            json.dumps(
                {
                    "run_id": run_dir.name,
                    "exit_code": idx,
                    "finished_at": f"2026-04-28T14:00:0{idx}Z",
                    "failure_class": {
                        "exit_code": idx,
                        "name": name,
                        "severity": "error",
                        "next_action": "inspect",
                        "retryable": False,
                    },
                }
            ),
            encoding="utf-8",
        )

    report = ps.build_runs_timeline(tmp_path)

    assert report["stats"]["failure_class_counts"] == {
        "dod_failed": 2,
        "success": 1,
    }


def test_validate_observability_report_accepts_timeline_payload(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    (run_dir / "event_log.jsonl").write_text(
        '{"ts":"2026-04-28T15:00:00Z","event":"phase_change"}\n',
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "package_id": "epoch-demo",
                "exit_code": 0,
                "finished_at": "2026-04-28T15:00:01Z",
            }
        ),
        encoding="utf-8",
    )

    report = ps.build_runs_timeline(tmp_path)

    assert ps.validate_observability_report(report) == []


def test_validate_observability_report_rejects_bad_shape() -> None:
    errors = ps.validate_observability_report(
        {
            "runs": [{"run_id": "x", "proof_ok": "yes"}],
            "stats": {"failure_class_counts": {"success": "one"}},
        }
    )

    assert any("missing keys" in error for error in errors)
    assert any("proof_ok must be boolean" in error for error in errors)
    assert any("failure_class_counts" in error for error in errors)


def test_print_report_shows_slo_names_and_failure_counts(capsys) -> None:
    report = {
        "package": None,
        "status": "",
        "complexity": "?",
        "work_state": None,
        "dod": [],
        "task_file": "(none)",
        "stats": {
            "total_runs": 3,
            "closure_success_rate": 0.67,
            "false_closure_rate": 0.0,
            "prompt_injection_block_rate": 1.0,
            "median_duration_s": 2.5,
            "failure_class_counts": {"dod_failed": 2, "success": 1},
        },
        "runs": [],
        "action_desc": "No active package",
        "action_cmd": "python scripts/run_autonomous.py --agent cursor_ai",
        "timestamp": "2026-04-29T00:00:00Z",
    }

    ps.print_report(report)
    out = capsys.readouterr().out

    assert "closure_success_rate=0.67" in out
    assert "prompt_injection_block_rate=1.00" in out
    assert "failure_class_counts:" in out
    assert "dod_failed=2" in out
