#!/usr/bin/env python3
"""Cursor stop hook thin wrapper around scripts.pipeline_guard_logic."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from quality_gates import blocking_results as _blocking_quality_gates  # noqa: E402
from quality_gates import run_all as _run_quality_gates  # noqa: E402
from quality_gates import summarize as _summarize_quality_gates  # noqa: E402
from prompt_utils import active_ready_package_from_registry  # noqa: E402

TASK_FILE = ROOT / "doc" / "current_task.md"


def _active_ready_package() -> str | None:
    return active_ready_package_from_registry()


def main() -> None:
    try:
        json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - hook input is best-effort
        pass

    gates = _run_quality_gates(
        package_id=_active_ready_package(),
        root=ROOT,
        current_task_path=TASK_FILE,
        include_proof=False,
    )
    summary = _summarize_quality_gates(gates)
    blockers = _blocking_quality_gates(gates)
    if blockers:
        first = blockers[0]
        print(
            json.dumps(
                {
                    "followup_message": first.followup_message or first.reason,
                    "quality_gates": summary,
                }
            )
        )
    else:
        print(json.dumps({"quality_gates": summary}))


if __name__ == "__main__":
    main()
