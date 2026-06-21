from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_lock import PipelineLockError, file_lock, package_run_conflict, read_lock_pid


def test_file_lock_blocks_active_lock(tmp_path: Path) -> None:
    lock = tmp_path / "current_task.md.lock"
    lock.write_text("pid=123\n", encoding="utf-8")

    with pytest.raises(PipelineLockError, match="pid=123"):
        with file_lock(lock):
            pass


def test_file_lock_removes_stale_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock = tmp_path / "current_task.md.lock"
    lock.write_text("pid=123\n", encoding="utf-8")
    monkeypatch.setattr("pipeline_lock.time.time", lambda: lock.stat().st_mtime + 3600)

    with file_lock(lock, ttl_seconds=1, payload="pid=999\n"):
        assert read_lock_pid(lock) == 999

    assert not lock.exists()


def test_package_run_conflict_ignores_current_pid() -> None:
    def _runs_provider(**_kwargs):
        return [
            {"pid": 42, "run_id": "self"},
            {"pid": 99, "run_id": "other"},
        ]

    conflict = package_run_conflict(
        "epoch-demo",
        current_pid=42,
        runs_provider=_runs_provider,
    )

    assert conflict == {"pid": 99, "run_id": "other"}
