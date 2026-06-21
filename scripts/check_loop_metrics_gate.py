#!/usr/bin/env python3
"""
Fail-fast gate for 5-minute loop runtime metrics contract (US-14.4).

Usage:
  python scripts/check_loop_metrics_gate.py
  python scripts/check_loop_metrics_gate.py --json-out
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXIT_OK = 0
EXIT_FAIL = 2


def run_gate() -> tuple[int, str]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_e11_learning_loop.py",
        "-k",
        "loop_runtime_metrics_gate_contract or record_loop_transition_emits_dead_end_safe_metric",
        "-v",
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run loop metrics gate (US-14.4)")
    parser.add_argument("--json-out", action="store_true", help="Print JSON payload")
    args = parser.parse_args()

    rc, raw_output = run_gate()
    status = "pass" if rc == 0 else "fail"
    payload = {
        "gate_kind": "loop_metrics_gate",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "passed": rc == 0,
        "exit_code": EXIT_OK if rc == 0 else EXIT_FAIL,
        "command": "python -m pytest tests/test_e11_learning_loop.py -k \"loop_runtime_metrics_gate_contract or record_loop_transition_emits_dead_end_safe_metric\" -v",
        "contract": {
            "dead_end": False,
            "deterministic_next_step": True,
            "completion_primary_cta_count": 1,
        },
    }

    if args.json_out:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"Loop metrics gate: {verdict}")
        print(payload["command"])
        if rc != 0:
            print(raw_output)

    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
