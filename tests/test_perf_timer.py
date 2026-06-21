from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _perf_timer import PhaseTimer, _safe_print, cleanup_old_logs  # noqa: E402


def test_phase_timer_hides_nested_phases_from_summary(capsys):
    timer = PhaseTimer()
    timer.reset()
    with timer.phase("outer") as rc:
        with timer.phase("inner") as rc2:
            rc2["rc"] = 0
        rc["rc"] = 0

    timer.print_summary()
    out = capsys.readouterr().out

    # Summary should show only top-level "outer"
    assert "outer" in out
    assert "inner" not in out.split("TIMING SUMMARY", 1)[-1]
    assert "nested phases hidden from summary" in out


def test_safe_print_does_not_crash_on_non_utf8_stream():
    # Simulate a cp1252 console (cannot encode ⏱) with strict error handling.
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    _safe_print("⏱ test", file=stream)

    # It should have written something (with replacement) and not raised.
    stream.flush()
    assert raw.getvalue()


def test_cleanup_old_logs_respects_env_keep_last(tmp_path, monkeypatch):
    timing_dir = tmp_path / "_timing"
    timing_dir.mkdir()

    # Create files with increasing mtimes.
    paths: list[Path] = []
    for i in range(3):
        p = timing_dir / f"{i}.json"
        p.write_text("{}", encoding="utf-8")
        paths.append(p)
        # Ensure distinct mtimes on Windows.
        time.sleep(0.01)

    monkeypatch.setenv("HOME_RAG_TIMING_KEEP_LAST", "1")
    cleanup_old_logs(timing_dir=timing_dir, keep_last=50)

    remaining = sorted(timing_dir.glob("*.json"))
    assert len(remaining) == 1

