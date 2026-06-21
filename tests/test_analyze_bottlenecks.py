"""Tests for scripts/analyze_bottlenecks.py — aggregation, outlier detection, regression detection."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_bottlenecks import (
    _BOTTLENECK_REPORT_DIR,
    PhaseRecord,
    Regression,
    Run,
    Stats,
    _aggregate,
    _categorize,
    _detect_outliers,
    _detect_regressions,
    _load_runs,
    _render_json,
    _render_md,
)


def test_default_report_dir_is_not_cost_logs():
    assert _BOTTLENECK_REPORT_DIR == ROOT / "logs" / "bottlenecks"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_run(run_id: str, script: str, phases: list[tuple[str, float]]) -> Run:
    return Run(
        run_id=run_id,
        script_name=script,
        total=sum(s for _, s in phases),
        phases=[
            PhaseRecord(name=n, seconds=s, rc=0, run_id=run_id, script_name=script)
            for n, s in phases
        ],
    )


def _write_timing_json(tmp_path: Path, run_id: str, script: str, phases: list[tuple[str, float]]) -> Path:
    out = tmp_path / f"{run_id}__{script}.json"
    out.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "script_name": script,
                "total": sum(s for _, s in phases),
                "phases": [{"name": n, "seconds": s, "rc": None} for n, s in phases],
            }
        ),
        encoding="utf-8",
    )
    return out


@pytest.fixture
def slow_run() -> Run:
    return _make_run("111", "run_autonomous", [("agent_execute", 120.0), ("dod_total", 5.0)])


@pytest.fixture
def unstable_run() -> Run:
    return _make_run("222", "run_autonomous", [("agent_execute", 0.5), ("dod_total", 60.0)])


@pytest.fixture
def many_runs() -> list[Run]:
    runs = []
    for i in range(12):
        # agent_execute grows by 2s each run → clear regression
        runs.append(_make_run(
            str(1000 + i),
            "run_autonomous",
            [("agent_execute", float(i * 2)), ("dod_total", 1.0)],
        ))
    return runs


# ---------------------------------------------------------------------------
# Aggregation tests
# ---------------------------------------------------------------------------

class TestAggregate:
    def test_basic_counts(self, slow_run, unstable_run):
        stats = _aggregate([slow_run, unstable_run])
        key_agent = "run_autonomous::agent_execute"
        assert key_agent in stats
        s = stats[key_agent]
        assert s.count == 2
        assert s.mean == pytest.approx((120.0 + 0.5) / 2, abs=1e-6)

    def test_max_reflects_highest_value(self, slow_run, unstable_run):
        stats = _aggregate([slow_run, unstable_run])
        key = "run_autonomous::dod_total"
        assert stats[key].max == pytest.approx(60.0)

    def test_single_run_stddev_is_zero(self, slow_run):
        stats = _aggregate([slow_run])
        key = "run_autonomous::agent_execute"
        assert stats[key].stddev == pytest.approx(0.0)

    def test_category_assignment(self):
        run = _make_run("x", "run_autonomous", [("agent_execute", 1.0), ("git_commit", 0.5)])
        stats = _aggregate([run])
        assert stats["run_autonomous::agent_execute"].category == "agent"
        assert stats["run_autonomous::git_commit"].category == "git"


# ---------------------------------------------------------------------------
# Outlier detection tests
# ---------------------------------------------------------------------------

class TestDetectOutliers:
    def test_max_slow_detected(self, slow_run):
        stats = _aggregate([slow_run])
        outliers = _detect_outliers(stats, threshold_sec=5.0)
        phases = [o.phase for o in outliers]
        assert "run_autonomous::agent_execute" in phases

    def test_mean_slow_detected(self):
        run = _make_run("x", "run_autonomous", [("slow_phase", 3.0)])
        stats = _aggregate([run])
        outliers = _detect_outliers(stats, threshold_sec=10.0)
        # mean=3.0 > 2.0 → mean_slow
        phases = [o.phase for o in outliers]
        assert "run_autonomous::slow_phase" in phases

    def test_high_variance_detected(self):
        runs = [
            _make_run("a", "run_autonomous", [("flaky_phase", 0.1)]),
            _make_run("b", "run_autonomous", [("flaky_phase", 10.0)]),
        ]
        stats = _aggregate(runs)
        outliers = _detect_outliers(stats, threshold_sec=100.0)
        reasons = {o.reason for o in outliers if o.phase == "run_autonomous::flaky_phase"}
        assert "high_variance" in reasons

    def test_no_outliers_for_fast_stable(self):
        runs = [_make_run(str(i), "run_autonomous", [("fast_op", 0.1)]) for i in range(5)]
        stats = _aggregate(runs)
        outliers = _detect_outliers(stats, threshold_sec=5.0)
        phases = [o.phase for o in outliers]
        assert "run_autonomous::fast_op" not in phases


# ---------------------------------------------------------------------------
# Regression detection tests
# ---------------------------------------------------------------------------

class TestDetectRegressions:
    def test_growing_phase_detected(self, many_runs):
        regressions = _detect_regressions(many_runs, min_points=5)
        phases = [r.phase for r in regressions]
        assert "run_autonomous::agent_execute" in phases

    def test_slope_positive(self, many_runs):
        regressions = _detect_regressions(many_runs, min_points=5)
        for r in regressions:
            if r.phase == "run_autonomous::agent_execute":
                assert r.slope > 0.1

    def test_stable_phase_not_regressed(self):
        runs = [_make_run(str(i), "run_autonomous", [("stable", 1.0)]) for i in range(10)]
        regressions = _detect_regressions(runs, min_points=5)
        assert not any(r.phase == "run_autonomous::stable" for r in regressions)

    def test_too_few_points_skipped(self):
        runs = [_make_run(str(i), "run_autonomous", [("growing", float(i * 5))]) for i in range(3)]
        regressions = _detect_regressions(runs, min_points=5)
        assert not regressions


# ---------------------------------------------------------------------------
# Render tests
# ---------------------------------------------------------------------------

class TestRenderMd:
    def test_does_not_crash(self, slow_run):
        stats = _aggregate([slow_run])
        outliers = _detect_outliers(stats)
        regressions = _detect_regressions([slow_run])
        md = _render_md([slow_run], stats, outliers, regressions, threshold_sec=5.0)
        assert "# Pipeline Bottleneck Report" in md
        assert "Top-10" in md

    def test_contains_phase_names(self, slow_run):
        stats = _aggregate([slow_run])
        md = _render_md([slow_run], stats, [], [], threshold_sec=5.0)
        assert "agent_execute" in md


class TestRenderJson:
    def test_is_valid_json(self, slow_run):
        stats = _aggregate([slow_run])
        outliers = _detect_outliers(stats)
        regressions = _detect_regressions([slow_run])
        raw = _render_json([slow_run], stats, outliers, regressions)
        data = json.loads(raw)
        assert "phases" in data
        assert "outliers" in data
        assert "regressions" in data

    def test_schema_stable(self, slow_run):
        stats = _aggregate([slow_run])
        raw = _render_json([slow_run], stats, [], [])
        data = json.loads(raw)
        phase = data["phases"][0]
        assert {"phase", "count", "mean", "median", "p95", "max", "stddev", "category"} <= phase.keys()


# ---------------------------------------------------------------------------
# load_runs tests
# ---------------------------------------------------------------------------

class TestLoadRuns:
    def test_loads_json_files(self, tmp_path):
        _write_timing_json(tmp_path, "100", "run_autonomous", [("agent_execute", 5.0)])
        runs = _load_runs(tmp_path, last_n=10)
        assert len(runs) == 1
        assert runs[0].script_name == "run_autonomous"
        assert len(runs[0].phases) == 1

    def test_respects_last_n(self, tmp_path):
        for i in range(10):
            _write_timing_json(tmp_path, str(1000 + i), "run_autonomous", [("p", float(i))])
        runs = _load_runs(tmp_path, last_n=5)
        assert len(runs) == 5

    def test_empty_dir_returns_empty(self, tmp_path):
        runs = _load_runs(tmp_path, last_n=20)
        assert runs == []

    def test_missing_dir_returns_empty(self, tmp_path):
        runs = _load_runs(tmp_path / "nonexistent", last_n=20)
        assert runs == []

    def test_groups_same_run_id(self, tmp_path):
        """Files from the same run_id should load as separate Run objects (one per script)."""
        _write_timing_json(tmp_path, "999", "run_autonomous", [("a", 1.0)])
        _write_timing_json(tmp_path, "999", "generate_orchestration_prompt", [("b", 2.0)])
        runs = _load_runs(tmp_path, last_n=10)
        assert len(runs) == 2
        scripts = {r.script_name for r in runs}
        assert "run_autonomous" in scripts
        assert "generate_orchestration_prompt" in scripts


def test_cli_creates_parent_directory_for_explicit_out(tmp_path):
    timing_dir = tmp_path / "timing"
    timing_dir.mkdir()
    _write_timing_json(timing_dir, "100", "run_autonomous", [("agent_execute", 1.0)])
    out_path = tmp_path / "reports" / "nested" / "bottleneck_report.md"

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "analyze_bottlenecks.py"),
            "--timing-dir",
            str(timing_dir),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert out_path.exists()
    assert "Report written:" in proc.stdout
