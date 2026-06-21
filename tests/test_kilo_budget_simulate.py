"""Tests for the static budget simulator.

Key test beyond individual units: a parity check that feeds a synthetic
request through BOTH `_kilo_guard.evaluate_guard` (as the relay does) and
the simulator's `simulate_payload` — they must produce byte-identical
verdicts. If this ever fails, simulator and runtime have diverged and the
single-source-of-truth invariant is broken.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kilo_budget_simulate as sim  # noqa: E402
from _kilo_guard import GuardThresholds, evaluate_guard, summarize_body  # noqa: E402


CHAT_PATH = "/v1/chat/completions"


@pytest.fixture
def minimal_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "inj.json"
    p.write_text(
        json.dumps(
            {
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "system", "content": "sys-prompt"}],
                "tools": [{"type": "function", "function": {"name": "noop"}}],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_build_payload_appends_launcher_and_user_turn():
    fixture = {"messages": [{"role": "system", "content": "S"}], "tools": []}
    payload, segments = sim.build_payload(
        fixture, launcher_text="LAUNCHER", user_turn="TURN", launcher_label="L.md"
    )
    roles = [m["role"] for m in payload["messages"]]
    assert roles == ["system", "user", "user"]
    labels = [s[0] for s in segments]
    assert labels == ["injection::system#0", "L.md", "user_turn"]
    assert segments[1] == ("L.md", len("LAUNCHER"))


def test_simulate_payload_matches_direct_evaluate_guard():
    """Parity invariant: simulator and relay must compute identical verdicts."""
    payload = {
        "model": "x",
        "messages": [
            {"role": "system", "content": "a" * 60000},
            {"role": "user", "content": "b" * 20000},
        ],
        "tools": [],
    }
    body_text = json.dumps(payload, ensure_ascii=False)
    thresholds = GuardThresholds()

    direct_summary = summarize_body(body_text)
    direct_verdict = evaluate_guard(
        CHAT_PATH, body_text, direct_summary, thresholds=thresholds, mode="warn"
    )

    sim_result = sim.simulate_payload(payload, thresholds=thresholds, mode="warn")

    assert sim_result["verdict"] == asdict(direct_verdict)
    assert sim_result["summary"]["body_chars"] == direct_summary["body_chars"]


def test_attribute_reports_biggest_chunk_first_and_flags_downgrade():
    """Attribution: removing the giant message should downgrade from warn to ok."""
    # Giant user message is sole reason for warn — removing it must downgrade.
    fixture = {"messages": [{"role": "system", "content": "s"}], "tools": []}
    payload, segments = sim.build_payload(
        fixture,
        launcher_text="x" * 71000,  # pushes body over warn_body_chars
        user_turn=None,
        launcher_label="big.md",
    )
    thresholds = GuardThresholds()
    base = sim.simulate_payload(payload, thresholds=thresholds, mode="warn")
    assert base["verdict"]["level"] == "warn"

    rows = sim.attribute(payload, segments, thresholds=thresholds, mode="warn")
    # First row (biggest) is the launcher, and removing it downgrades.
    assert rows[0]["label"] == "big.md"
    assert rows[0]["would_downgrade"] is True
    assert rows[0]["if_removed_level"] == "ok"


def test_cmd_simulate_fail_on_returns_exit_code(tmp_path: Path, capsys, monkeypatch, minimal_fixture):
    """--fail-on soft_block must exit non-zero when level hits soft_block."""
    # Build a launcher file big enough to trigger soft_block (>90k chars body).
    launcher = tmp_path / "big_launcher.md"
    launcher.write_text("x" * 95000, encoding="utf-8")

    rc = sim.main([
        "simulate",
        "--launcher", str(launcher),
        "--injection", str(minimal_fixture),
        "--fail-on", "soft_block",
    ])
    assert rc == 2  # failed on soft_block threshold


def test_cmd_simulate_ok_returns_zero(tmp_path: Path, minimal_fixture):
    launcher = tmp_path / "small.md"
    launcher.write_text("tiny", encoding="utf-8")
    rc = sim.main([
        "simulate",
        "--launcher", str(launcher),
        "--injection", str(minimal_fixture),
        "--fail-on", "soft_block",
    ])
    assert rc == 0


def test_cmd_simulate_json_out_produces_structured_report(tmp_path: Path, minimal_fixture):
    launcher = tmp_path / "small.md"
    launcher.write_text("tiny launcher", encoding="utf-8")
    out = tmp_path / "report.json"
    rc = sim.main([
        "simulate",
        "--launcher", str(launcher),
        "--injection", str(minimal_fixture),
        "--json-out", str(out),
        "--attribute",
    ])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert set(report.keys()) >= {
        "source", "fixture", "thresholds", "verdict", "summary", "attribution", "section_attribution"
    }
    assert report["verdict"]["level"] == "ok"
    assert report["fixture"]["kind"] == "unknown_fixture"
    assert isinstance(report["attribution"], list) and len(report["attribution"]) >= 2


def test_capture_extracts_fixture_from_jsonl(tmp_path: Path):
    """capture subcommand: build a fixture from an existing relay JSONL record."""
    rec_body = {
        "model": "m",
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "[KILO-PROBE: ORCH-LAUNCHER] user turn"},
        ],
        "tools": [{"type": "function", "function": {"name": "t"}}],
    }
    record = {
        "path": CHAT_PATH,
        "request_id": "r1",
        "ts": "2026-04-23T00:00:00+00:00",
        "request": {
            "body_chars": len(json.dumps(rec_body)),
            "body_raw": json.dumps(rec_body),
        },
        "guard": {"level": "ok"},
    }
    jsonl = tmp_path / "relay.jsonl"
    jsonl.write_text(json.dumps(record) + "\n", encoding="utf-8")
    out = tmp_path / "fx.json"
    rc = sim.main([
        "capture",
        "--from-jsonl", str(jsonl),
        "--probe", "ORCH-LAUNCHER",
        "-o", str(out),
    ])
    assert rc == 0
    fixture = json.loads(out.read_text(encoding="utf-8"))
    # Probe user turn was dropped.
    assert [m["role"] for m in fixture["messages"]] == ["system"]
    assert len(fixture["tools"]) == 1
    assert fixture["_meta"]["fixture_kind"] == "captured_relay_fixture"
    assert fixture["_source"]["request_id"] == "r1"


def test_load_injection_fixture_detects_calibrated_fixture_kind(tmp_path: Path):
    fixture_path = tmp_path / "calibrated.json"
    fixture_path.write_text(
        json.dumps(
            {
                "_meta": {
                    "fixture_kind": "calibrated_estimate",
                    "source_note": "offline estimate",
                },
                "messages": [{"role": "system", "content": "sys"}],
                "tools": [],
            }
        ),
        encoding="utf-8",
    )
    fixture = sim.load_injection_fixture(fixture_path)
    assert fixture["_fixture"]["kind"] == "calibrated_estimate"
    assert fixture["_fixture"]["source_note"] == "offline estimate"


def test_replay_detects_no_mismatch_on_self_generated_record(tmp_path: Path):
    """If we fabricate a record with the verdict recomputed from body_raw, replay finds zero mismatches."""
    payload = {
        "model": "x",
        "messages": [{"role": "user", "content": "short"}],
        "tools": [],
    }
    body_text = json.dumps(payload)
    summary = summarize_body(body_text)
    verdict = evaluate_guard(CHAT_PATH, body_text, summary, thresholds=GuardThresholds(), mode="warn")
    record = {
        "path": CHAT_PATH,
        "request_id": "r",
        "request": {"body_raw": body_text, "body_chars": len(body_text)},
        "guard": {"level": verdict.level},
    }
    jsonl = tmp_path / "r.jsonl"
    jsonl.write_text(json.dumps(record) + "\n", encoding="utf-8")
    rc = sim.main(["replay", "--from-jsonl", str(jsonl)])
    assert rc == 0


def test_section_attribute_splits_by_h2():
    launcher = "# Title\n\n## A\ntext-a\n\n## B\ntext-b\n"
    sections = sim.split_launcher_by_sections(launcher, level=2)
    assert sections[0][0] == "(preamble)"
    assert sections[1][0] == "A"
    assert sections[2][0] == "B"


def test_section_attribute_whole_launcher_when_no_headings():
    sections = sim.split_launcher_by_sections("plain text only", level=2)
    assert sections == [("(whole launcher)", "plain text only")]


def test_section_attribute_orders_by_contribution():
    fixture = {"messages": [{"role": "system", "content": "sys"}], "tools": []}
    launcher = "## Big\n" + ("x" * 2000) + "\n## Small\nsmall\n"
    rows = sim.attribute_sections(
        fixture,
        launcher,
        user_turn=None,
        thresholds=GuardThresholds(),
        mode="warn",
        level=2,
    )
    assert rows[0]["section"] in {"Big", "(preamble)"}
    assert rows[0]["contrib_body_chars"] >= rows[-1]["contrib_body_chars"]


def test_capture_default_output_is_captured_fixture():
    parser = sim.build_parser()
    args = parser.parse_args(["capture", "--from-jsonl", "logs/example.jsonl"])
    assert args.output == "fixtures/kilo_injection_captured.json"


def test_replay_detects_mismatch_when_record_lies(tmp_path: Path, capsys):
    body_text = json.dumps({"model": "x", "messages": [{"role": "user", "content": "short"}]})
    record = {
        "path": CHAT_PATH,
        "request_id": "r-lie",
        "request": {"body_raw": body_text, "body_chars": len(body_text)},
        "guard": {"level": "hard_block"},  # lies — short body is actually ok
    }
    jsonl = tmp_path / "r.jsonl"
    jsonl.write_text(json.dumps(record) + "\n", encoding="utf-8")
    rc = sim.main(["replay", "--from-jsonl", str(jsonl)])
    assert rc == 3
    captured = capsys.readouterr().out
    assert "MISMATCH" in captured
