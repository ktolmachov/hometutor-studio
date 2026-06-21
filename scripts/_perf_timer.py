"""Reusable PhaseTimer for pipeline performance instrumentation.

Usage in sub-scripts::

    from _perf_timer import PhaseTimer

    def main() -> int:
        timer = PhaseTimer()
        try:
            with timer.phase("my_phase"):
                do_work()
            return 0
        finally:
            timer.flush()
            timer.total_only_when_top_level()
"""
from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TIMING_DIR = ROOT / "archive" / "team_artifacts" / "_timing"
_LOG_DIR = ROOT / "logs"
_LOG_ROTATE_BYTES = 5 * 1024 * 1024  # 5 MB


def _safe_print(msg: str, *, file=None) -> None:
    """Print without crashing on non-UTF8 Windows consoles."""
    out = file or sys.stdout
    try:
        print(msg, file=out)
    except UnicodeEncodeError:
        enc = getattr(out, "encoding", None) or "utf-8"
        buf = getattr(out, "buffer", None)
        if buf is None:
            # Last resort: strip non-ascii.
            print(msg.encode("ascii", errors="replace").decode("ascii"), file=out)
            return
        buf.write((msg + "\n").encode(enc, errors="replace"))
        try:
            out.flush()
        except Exception:
            pass


class PhaseTimer:
    """Records wall-clock time for named pipeline phases and flushes to JSON."""

    def __init__(self) -> None:
        # True if HOME_RAG_RUN_ID was already in the env when this timer was created,
        # meaning this process is a sub-script running under a parent pipeline.
        self._is_sub_script: bool = "HOME_RAG_RUN_ID" in os.environ
        self.script_name: str = Path(sys.argv[0]).stem if sys.argv else "unknown"
        # Each record is: (name, seconds, rc, depth)
        # Depth>0 means the phase ran nested inside another phase in the same process.
        self.records: list[tuple[str, float, int | None, int]] = []
        self._t0: float = time.perf_counter()
        self._depth: int = 0

    @contextmanager
    def phase(self, name: str):  # type: ignore[override]
        start = time.perf_counter()
        rc_holder: dict[str, int | None] = {"rc": None}
        depth = self._depth
        self._depth += 1
        try:
            yield rc_holder
        finally:
            self._depth = max(0, self._depth - 1)
            elapsed = time.perf_counter() - start
            self.records.append((name, elapsed, rc_holder["rc"], depth))
            _safe_print(
                f"  [{name}] {elapsed:.2f}s"
                + (f" (rc={rc_holder['rc']})" if rc_holder["rc"] is not None else "")
            )

    def total(self) -> float:
        return time.perf_counter() - self._t0

    def reset(self) -> None:
        self.records.clear()
        self._t0 = time.perf_counter()
        self._depth = 0

    def print_summary(self) -> None:
        total = self.total()
        if not self.records:
            return
        _safe_print("\n" + "=" * 70)
        _safe_print(f"TIMING SUMMARY - total wall time: {total:.2f}s")
        _safe_print("=" * 70)
        top_level = [r for r in self.records if r[3] == 0]
        nested = [r for r in self.records if r[3] != 0]
        ranked = sorted(top_level, key=lambda r: r[1], reverse=True)
        width = max(len(r[0]) for r in ranked) if ranked else 10
        for name, sec, rcode, _depth in ranked:
            pct = (sec / total * 100) if total else 0
            rc_str = f" rc={rcode}" if rcode is not None else ""
            bar = "#" * int(pct / 2)  # 50 cols max (ASCII-safe for legacy Windows consoles)
            _safe_print(f"  {name:<{width}} {sec:7.2f}s  {pct:5.1f}%  {bar}{rc_str}")
        if nested:
            nested_sec = sum(r[1] for r in nested)
            _safe_print(
                f"\n  (nested phases hidden from summary: {len(nested)} records, {nested_sec:.2f}s)"
            )
        cats: dict[str, float] = {
            "git": 0.0,
            "subprocess": 0.0,
            "io": 0.0,
            "agent": 0.0,
            "dod": 0.0,
            "generator": 0.0,
            "other": 0.0,
        }
        for name, sec, _, depth in top_level:
            if depth != 0:
                continue
            n = name.lower()
            if "git" in n:
                cats["git"] += sec
            elif "agent" in n:
                cats["agent"] += sec
            elif "dod" in n:
                cats["dod"] += sec
            elif "generat" in n or "prompt" in n:
                cats["generator"] += sec
            elif (
                "subprocess" in n
                or "spawn" in n
                or "close_package" in n
                or "summarize" in n
                or "smoke" in n
            ):
                cats["subprocess"] += sec
            elif "load" in n or "parse" in n or "scaffold" in n:
                cats["io"] += sec
            else:
                cats["other"] += sec
        _safe_print("\n  Category breakdown:")
        for cat, sec in sorted(cats.items(), key=lambda kv: -kv[1]):
            if sec > 0:
                _safe_print(f"    {cat:<12} {sec:7.2f}s  ({sec/total*100:5.1f}%)")
        _safe_print("=" * 70)

    def total_only_when_top_level(self) -> None:
        """Print full summary only when this is the top-level script (not a sub-script)."""
        if not self._is_sub_script:
            self.print_summary()

    def flush(self, timing_dir: Path | None = None) -> None:
        """Write phase records to a JSON file correlated by HOME_RAG_RUN_ID."""
        if not self.records:
            return
        try:
            from pipeline_events import get_or_create_run_id
        except ImportError:  # pragma: no cover
            run_id = os.environ.get("HOME_RAG_RUN_ID") or str(int(time.time()))
        else:
            run_id = get_or_create_run_id()
        dir_ = timing_dir or _TIMING_DIR
        try:
            dir_.mkdir(parents=True, exist_ok=True)
            out_path = dir_ / f"{run_id}__{self.script_name}.json"
            payload: dict = {
                "run_id": run_id,
                "script_name": self.script_name,
                "total": round(self.total(), 3),
                "phases": [
                    {"name": n, "seconds": round(s, 3), "rc": rc, "depth": depth}
                    for n, s, rc, depth in self.records
                ],
            }
            if out_path.exists():
                # Append phases when the same script writes twice under the same run
                existing = json.loads(out_path.read_text(encoding="utf-8"))
                existing.setdefault("phases", []).extend(payload["phases"])
                existing["total"] = round(
                    existing.get("total", 0) + payload["total"], 3
                )
                out_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            else:
                out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            _safe_print(f"Timing log: {out_path.relative_to(ROOT)}")
        except Exception as exc:  # noqa: BLE001 — best-effort timing dump must not mask exit
            _safe_print(f"WARN: Could not write timing log: {exc}", file=sys.stderr)


def cleanup_old_logs(timing_dir: Path | None = None, keep_last: int = 50) -> None:
    """Delete old timing JSON files, keeping only the most recent `keep_last`.

    Also rotates any ``script_runs.log`` files over 5 MB.
    """
    env_keep = os.environ.get("HOME_RAG_TIMING_KEEP_LAST")
    if env_keep:
        try:
            keep_last = max(0, int(env_keep))
        except ValueError:
            _safe_print(
                f"WARN: Invalid HOME_RAG_TIMING_KEEP_LAST={env_keep!r}; using keep_last={keep_last}",
                file=sys.stderr,
            )
    dir_ = timing_dir or _TIMING_DIR
    if dir_.exists():
        files = sorted(dir_.glob("*.json"), key=lambda p: p.stat().st_mtime)
        to_delete = files[: max(0, len(files) - keep_last)]
        for f in to_delete:
            try:
                f.unlink()
            except OSError:
                pass

    if _LOG_DIR.exists():
        for log_file in _LOG_DIR.rglob("script_runs.log"):
            try:
                if log_file.stat().st_size > _LOG_ROTATE_BYTES:
                    rotated = log_file.with_suffix(".log.1")
                    if rotated.exists():
                        rotated.unlink()
                    log_file.rename(rotated)
            except OSError:
                pass
