"""Smoke and contract tests for scripts/kilo_budget_daily.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kilo_budget_daily as daily  # noqa: E402


def _extract_json_block(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    assert start != -1 and end != -1 and end > start
    return json.loads(text[start : end + 1])


def test_run_check_does_not_crash_without_calibrated_estimate():
    thresholds = daily.GuardThresholds()
    report = daily.run_check(
        thresholds,
        include_calibrated_estimate=False,
        write_fixture=False,
    )
    assert report["overall_status"] in daily.STATUS_ORDER
    assert "committed_fixture_gate" in report["analyses"]
    assert "calibrated_estimate" not in report["analyses"]


def test_run_check_with_calibrated_estimate_produces_both_analyses():
    thresholds = daily.GuardThresholds()
    report = daily.run_check(
        thresholds,
        include_calibrated_estimate=True,
        write_fixture=False,
    )
    assert "committed_fixture_gate" in report["analyses"]
    assert "calibrated_estimate" in report["analyses"]


def test_default_run_is_read_only_for_committed_fixture():
    fixture_path = ROOT / "fixtures" / "kilo_injection_baseline.json"
    before_bytes = fixture_path.read_bytes()
    daily.run_check(
        daily.GuardThresholds(),
        include_calibrated_estimate=False,
        write_fixture=False,
    )
    after_bytes = fixture_path.read_bytes()
    assert before_bytes == after_bytes


def test_main_no_save_returns_non_crashing_exit_code():
    rc = daily.main(["--no-save"])
    assert rc in (0, 2)


def test_main_json_output_contains_overall_status(capsys):
    rc = daily.main(["--no-save", "--json"])
    assert rc in (0, 2)
    captured = capsys.readouterr().out
    payload = _extract_json_block(captured)
    assert "overall_status" in payload
    assert payload["overall_status"] in daily.STATUS_ORDER
    assert "committed_fixture_gate" in payload["analyses"]
