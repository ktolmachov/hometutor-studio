#!/usr/bin/env python3
"""
start_workflow.py — one-command router for the next delivery workflow step.

Decision policy:
  1. No active package in backlog_registry.yaml -> plan-next path
  2. Package status proposed/open (no accepted contract) -> plan-next path
  3. execution_contract already exists       -> resume path
  4. High complexity contract                -> orchestration path
  5. Low/medium complexity contract          -> execution-auto path

Usage:
  python scripts/start_workflow.py
  python scripts/start_workflow.py --agent codex
  python scripts/start_workflow.py --package epoch-foo
  python scripts/start_workflow.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_utils import (  # noqa: E402
    AUTONOMOUS_AGENT_CHOICES,
    WORK_STATE_EXECUTION_READY,
    classify_package_complexity,
    detect_work_state,
    ensure_utf8_stdio,
    load_backlog_registry,
    parse_contract,
    parse_truth_view_from_registry,
    resolve_agent_adapter_name,
    select_package,
)
from agent_sandbox import safe_run  # noqa: E402

# ensure_utf8_stdio() намеренно не вызывается на уровне модуля:
# этот файл импортируется как библиотека (run_autonomous.py, тесты) —
# вызов здесь перехватывает stderr до argparse и ломает --help.
# Вызывается только когда скрипт запущен напрямую (см. main()).

DEFAULT_AGENT = "cursor_ai"
PYTHON_EXE = sys.executable or "python"

_PLAN_NEXT_STATUSES = frozenset({"proposed", "open"})


def _plan_next_command(
    agent: str,
    package_id: str | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> list[str]:
    command = [PYTHON_EXE, "scripts/generate_orchestration_prompt.py", "--agent", agent]
    if package_id:
        command.extend(["--package", str(package_id)])
    if force:
        command.append("--force")
    if dry_run:
        command.append("--dry-run")
    return command


def _state_from_registry_item(explicit_package: str, rows_snapshot: list[dict[str, str]]) -> dict[str, object] | None:
    """Resolve backlog item + contract by id (incl. closed) when Truth View skips the row."""
    reg = load_backlog_registry()
    items = [it for it in (reg.get("items") or []) if isinstance(it, dict)]
    targets = {
        explicit_package,
        f"epoch-{explicit_package}",
        explicit_package.removeprefix("epoch-"),
    }
    item = next((it for it in items if it.get("id") in targets), None)
    if not item:
        return None
    pkg_id = str(item.get("id", explicit_package))
    contract = parse_contract("", pkg_id)
    if not contract:
        return None
    return {
        "rows": rows_snapshot,
        "package": pkg_id,
        "status": str(item.get("status", "?")),
        "contract": contract,
        "work_state": detect_work_state(pkg_id),
    }


def load_state(explicit_package: str | None = None) -> dict[str, object]:
    rows = parse_truth_view_from_registry()
    if not rows and explicit_package:
        hit = _state_from_registry_item(explicit_package, [])
        if hit:
            return hit

    if not rows:
        return {
            "error": (
                "backlog_registry.yaml has no active workflow rows "
                "(wip/ready/open/proposed). Run plan-next or add a package to the registry."
            ),
        }

    row = select_package(rows, explicit_package)
    if not row and explicit_package:
        hit = _state_from_registry_item(explicit_package, rows)
        if hit:
            return hit
    if not row:
        return {"rows": rows, "package": None, "contract": {}, "work_state": None}

    package_id = row["package"]
    contract: dict = parse_contract("", package_id)
    return {
        "rows": rows,
        "package": package_id,
        "status": row.get("status", "?"),
        "contract": contract,
        "work_state": detect_work_state(package_id),
    }


def decide_next_step(
    state: dict[str, object],
    *,
    agent: str = DEFAULT_AGENT,
    package: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, object]:
    requested_agent = agent
    agent = resolve_agent_adapter_name(agent) if agent != "kilo" else "kilo"

    if "error" in state:
        return {"action": "ERROR", "command": [], "reasons": [state["error"]], "complexity": None}

    package_id = package or state.get("package")
    if not package_id:
        return {
            "action": "PLAN_NEXT",
            "command": _plan_next_command(agent, dry_run=dry_run, force=force),
            "reasons": [
                "No active package with status wip/ready/open/proposed.",
                "Delegating to orchestration generator because it auto-pivots into plan-next mode.",
            ],
            "complexity": None,
        }

    pkg_status = str(state.get("status", "")).strip().lower()
    if pkg_status in _PLAN_NEXT_STATUSES:
        return {
            "action": "PLAN_NEXT",
            "command": _plan_next_command(agent, str(package_id), dry_run=dry_run, force=force),
            "reasons": [
                f"Package status is {pkg_status!r} — accepted contract required before execution.",
                "Delegating to orchestration generator (plan-next pivot), aligned with workflow.py.",
            ],
            "complexity": None,
        }

    work_state = state.get("work_state")
    contract = state.get("contract", {}) or {}
    complexity = classify_package_complexity(contract)

    if work_state == WORK_STATE_EXECUTION_READY:
        command = [PYTHON_EXE, "scripts/generate_next_prompt.py", "--resume", "--package", str(package_id)]
        return {
            "action": "RESUME",
            "command": command,
            "reasons": [
                "Execution contract already exists for this package.",
                "Resume is safer than regenerating planning/orchestration from scratch.",
            ],
            "complexity": complexity,
        }

    if complexity["route"] == "orchestration":
        command = [
            PYTHON_EXE,
            "scripts/generate_orchestration_prompt.py",
            "--agent",
            agent,
            "--package",
            str(package_id),
        ]
        if force:
            command.append("--force")
        if dry_run:
            command.append("--dry-run")
        return {
            "action": "ORCHESTRATION",
            "command": command,
            "reasons": [
                f"Complexity classified as {complexity['label']} (score={complexity['score']}).",
                "High-complexity packages benefit from the orchestration path.",
            ],
            "complexity": complexity,
        }

    command = [PYTHON_EXE, "scripts/generate_next_prompt.py", "--package", str(package_id)]
    if force:
        command.append("--force")
    if dry_run:
        command.append("--dry-run")
    return {
        "action": "EXECUTION_AUTO",
        "command": command,
        "reasons": [
            f"Complexity classified as {complexity['label']} (score={complexity['score']}).",
            "Compact package: use the direct automated execution flow.",
        ],
        "complexity": complexity,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", "-p", help="Override auto-detected package")
    parser.add_argument(
        "--agent",
        "-a",
        choices=list(AUTONOMOUS_AGENT_CHOICES),
        default=DEFAULT_AGENT,
        help="Agent for orchestration path (default: cursor_ai)",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="Print command without executing it")
    parser.add_argument("--force", action="store_true", help="Pass --force to delegated generator")
    return parser


def main() -> int:
    ensure_utf8_stdio()  # безопасно здесь: вызывается только при прямом запуске
    args = build_parser().parse_args()
    state = load_state(args.package)
    decision = decide_next_step(
        state,
        agent=args.agent,
        package=args.package,
        dry_run=args.dry_run,
        force=args.force,
    )

    if decision["action"] == "ERROR":
        print(f"ERROR: {decision['reasons'][0]}", file=sys.stderr)
        return 2

    print(f"Action: {decision['action']}")
    if state.get("package"):
        print(f"Package: {state['package']} [{state.get('status', '?')}]")
        print(f"Work state: {state.get('work_state')}")
    else:
        print("Package: none active in backlog_registry.yaml")

    complexity = decision.get("complexity")
    if complexity:
        print(f"Complexity: {complexity['label']} (score={complexity['score']})")
        for reason in complexity.get("reasons", [])[:3]:
            print(f"  - {reason}")

    print("Reasons:")
    for reason in decision["reasons"]:
        print(f"  - {reason}")

    command = decision["command"]
    print(f"Command: {' '.join(command)}")
    if args.dry_run:
        return 0

    result = safe_run(command, cwd=str(Path(__file__).resolve().parents[1]))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
