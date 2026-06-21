"""Small lock primitives for autonomous pipeline coordination."""

from __future__ import annotations

import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from pipeline_events import current_runs


class PipelineLockError(RuntimeError):
    """Raised when a pipeline lock cannot be acquired."""


def read_lock_pid(lock_path: Path) -> int | None:
    try:
        text = lock_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text:
        return None
    match = re.search(r"\bpid=(\d+)\b", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


@contextmanager
def file_lock(
    lock_path: Path,
    *,
    ttl_seconds: int = 30 * 60,
    payload: str | None = None,
) -> Iterator[None]:
    """Acquire a simple cross-process lock via atomic file creation."""
    body = payload or f"pid={os.getpid()}\nargv={' '.join(sys.argv)}\ncreated_ts={int(time.time())}\n"
    for _attempt in range(2):
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open("x", encoding="utf-8", errors="replace") as fh:
                fh.write(body)
            break
        except FileExistsError as exc:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                age = 0
            if age > ttl_seconds:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            pid = read_lock_pid(lock_path)
            raise PipelineLockError(
                f"lock is held by another process (pid={pid}): {lock_path}"
            ) from exc
    else:
        raise PipelineLockError(f"could not acquire lock: {lock_path}")

    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


def package_run_conflict(
    package_id: str | None,
    *,
    current_pid: int | None = None,
    runs_provider: Callable[..., list[dict[str, Any]]] = current_runs,
) -> dict[str, Any] | None:
    """Return another live run for the same package, if one exists."""
    if not package_id:
        return None
    self_pid = os.getpid() if current_pid is None else current_pid
    for run in runs_provider(package_id=package_id):
        try:
            pid = int(run.get("pid", -1))
        except (TypeError, ValueError):
            pid = -1
        if pid != self_pid:
            return run
    return None
