#!/usr/bin/env python3
"""
Run loop metrics gate and persist timestamped JSON snapshot into logs/.

Usage:
  python scripts/record_loop_metrics_gate_snapshot.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"


def main() -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = LOGS_DIR / f"loop_metrics_gate_{ts}.json"

    cmd = [sys.executable, "scripts/check_loop_metrics_gate.py", "--json-out"]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode not in (0, 2):
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return 3

    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        print("FAIL: gate output is not valid JSON", file=sys.stderr)
        print(proc.stdout)
        return 3

    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = LOGS_DIR / "loop_metrics_gate_latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved gate snapshot: {target.relative_to(ROOT)}")
    print(f"Updated latest snapshot: {latest.relative_to(ROOT)}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
