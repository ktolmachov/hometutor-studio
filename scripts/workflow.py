#!/usr/bin/env python3
"""
workflow.py — Smart Workflow Router

Определяет текущее состояние пайплайна и выдаёт готовую команду следующего шага.
Заменяет необходимость держать матрицу решений в голове.
Источник для маршрутизации — только ``doc/backlog_registry.yaml``; ``doc/tasklist.md``
не читается и не сравнивается (производный weekly view вне контура роутера).

Usage:
    python scripts/workflow.py                         # состояние + следующий шаг
    python scripts/workflow.py --agent codex           # для конкретного агента
    python scripts/workflow.py --status                # только статус, без команды
    python scripts/workflow.py --exec                  # выполнить следующий шаг сразу
    python scripts/workflow.py --skip-review           # пропустить ревью контракта:
                                                       #   needs_plan → hint включает авто-exec после Phase 7
                                                       #   ready_fresh → автоматически запускает следующий шаг
                                                       #                (orchestration или execution_auto)
    python scripts/workflow.py --skip-review --exec    # полностью автоматический прогон
    python scripts/workflow.py --json                  # машиночитаемый вывод

    # Non-stop loop (conductor mode):
    python scripts/workflow.py --loop --skip-review --watch-contract --agent cursor_ai
    # С автозапуском Cursor Agent через SDK (см. doc/team_workflow/workflow_router.md):
    # python scripts/workflow.py --loop --skip-review --watch-contract \\
    #     --trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts" --agent cursor_ai
    # Полный конвейер от proposed до closed без ручных шагов.
    # --loop         : после каждой команды пересчитывает состояние и продолжает
    # --watch-contract: в execution_auto / ready_orch ждёт execution_contract.md
    #                  (после выполнения doc/current_task.md человеком/IDE-агентом),
    #                  затем автоматически запускает --post-agent.
    #                  Если run_autonomous уже перевёл пакет в status=closed (синхронное
    #                  автозакрытие), триггер и ожидание контракта для этого pkg пропускаются.
    # --watch-timeout: таймаут ожидания контракта в секундах (default: 3600)
    # --loop-max     : лимит итераций (default: 20)
    # --post-agent-no-dod-cache (с --loop): каждый --post-agent с полным прогоном DoD
    #                  без чтения archive/.../dod_cache.json (строже, медленнее).
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_utils import (  # noqa: E402
    ROOT,
    ACTIVE_STATUSES,
    active_ready_package_from_registry,
    classify_package_complexity,
    detect_work_state,
    ensure_utf8_stdio,
    get_backlog_truth_view,
    list_team_artifacts,
    load_backlog_registry,
    select_package,
    write_task_file_for_cursor,
)
from start_workflow import load_state as _load_state  # noqa: E402
from workflow_strings import (  # noqa: E402
    WORKFLOW_ROUTER_DOC_REL,
    format_prompt_execute_current_task_footer,
    format_workflow_router_doc_footer,
)

# ensure_utf8_stdio() только в CLI (main): импорт как библиотеки (tests) не должен ломать pytest capture.

TEAM_ARTIFACTS = ROOT / "archive" / "team_artifacts"
REGISTRY = ROOT / "doc" / "backlog_registry.yaml"

VALID_AGENTS = ("cursor_ai", "claude_code", "codex", "kilo", "continue")

# ── State codes ──────────────────────────────────────────────────────────────

STATE_NO_PACKAGE = "no_package"
STATE_NEEDS_PLAN = "needs_plan"           # proposed/open — контракт ещё не принят
STATE_READY_FRESH = "ready_fresh"         # ready, нет orchestration файла
STATE_READY_EXECUTING = "ready_executing" # task_started.md есть, execution_contract нет
STATE_READY_ORCH = "ready_orch"           # ready, orchestration файл есть
STATE_WIP_RUNNING = "wip_running"         # execution_contract существует → --post-agent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _orch_file(package_id: str, agent: str) -> Path:
    return TEAM_ARTIFACTS / package_id / f"orchestration_{agent}.md"


def _execution_contract(package_id: str) -> Path:
    return TEAM_ARTIFACTS / package_id / "execution_contract.md"


def _decode_text_bytes_best_effort(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _read_execution_contract_text(path: Path) -> str:
    raw = path.read_bytes()
    text = _decode_text_bytes_best_effort(raw)
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw:
        path.write_text(text, encoding="utf-8")
    return text


def _execution_contract_ready_for_post_agent(package_id: str) -> bool:
    """Return True only when execution_contract.md is substantive (not STARTED sentinel).

    Keep semantics aligned with heartbeat text in scripts/cursor_agent_trigger.ts:
    trimming + case-insensitive reject of sole content ``STARTED`` (Orchestration-first handshake).
    """
    path = _execution_contract(package_id)
    if not path.exists():
        return False
    try:
        text = _read_execution_contract_text(path).strip()
    except OSError:
        return False
    return bool(text) and text.upper() != "STARTED"


def _root_relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


_ORCH_STEP_HEADER = re.compile(r"^## STEP ([\d.]+) — (.+?)$", re.MULTILINE)
_ARCHITECT_SP2_HEADING = re.compile(r"(?im)^#{1,6}\s+Package\s+[^\n]*-sp2\b")
_ORCH_SAVE_ARTIFACT = re.compile(
    r"→ archive/team_artifacts/[^/\s]+/([^\s`]+)"
)


@dataclass(frozen=True)
class OrchStep:
    step_id: str
    title: str
    body: str
    artifact_names: tuple[str, ...]
    conditional: bool = False
    skippable: bool = False
    is_full_orchestration: bool = False

    @property
    def is_closure(self) -> bool:
        return self.step_id == "8"


def _extract_orchestration_write_set(orch_text: str) -> list[str]:
    m = re.search(r"^## Write-Set\s*\n(.+?)(?=\n╔|\n## |\Z)", orch_text, re.MULTILINE | re.DOTALL)
    if not m:
        return []
    paths: list[str] = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- `") and line.endswith("`"):
            paths.append(line[3:-1])
    return paths


def _package_has_sp2_subpackage(package_id: str, orch_text: str) -> bool:
    """True when STEP 6–7 must run (sp2 sub-package), not only UI packages.

    Backend sp2 (e.g. router hook) is declared in ``3_architect_contract.md`` as
    ``Package …-sp2`` even when write-set has no ``app/ui/`` paths.
    """
    pkg_dir = TEAM_ARTIFACTS / package_id
    arch_path = pkg_dir / "3_architect_contract.md"
    if arch_path.exists():
        try:
            arch_text = arch_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            arch_text = ""
        if _ARCHITECT_SP2_HEADING.search(arch_text):
            return True
    write_set = _extract_orchestration_write_set(orch_text)
    return any(p.startswith("app/ui/") for p in write_set)


def _parse_orchestration_steps(orch_text: str, package_id: str) -> list[OrchStep]:
    needs_sp2 = _package_has_sp2_subpackage(package_id, orch_text)
    matches = list(_ORCH_STEP_HEADER.finditer(orch_text))
    steps: list[OrchStep] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(orch_text)
        body = orch_text[start:end].strip()
        header_line = body.splitlines()[0] if body else ""
        artifacts = tuple(dict.fromkeys(_ORCH_SAVE_ARTIFACT.findall(body)))
        step_id = match.group(1)
        conditional = "[CONDITIONAL" in header_line
        skippable = step_id in ("6", "7") and not needs_sp2
        steps.append(
            OrchStep(
                step_id=step_id,
                title=match.group(2).strip(),
                body=body,
                artifact_names=artifacts,
                conditional=conditional,
                skippable=skippable,
            )
        )
    return steps


def _step_is_complete(pkg_dir: Path, step: OrchStep) -> bool:
    if step.skippable:
        return True
    if step.step_id == "3.5":
        if (pkg_dir / "3_5_skipped.md").exists():
            return True
        return any(
            p.is_file() and p.name.startswith("3_5_") and p.name.endswith(".md")
            for p in pkg_dir.iterdir()
        )
    if not step.artifact_names:
        return False
    return all((pkg_dir / name).exists() for name in step.artifact_names)


def _step_completion_artifact_names(pkg_dir: Path, step: OrchStep) -> tuple[str, ...]:
    """Return artifact filenames that satisfied step completion (for watch logs)."""
    if step.skippable:
        return ("(skipped — no sp2 sub-package)",)
    if step.step_id == "3.5":
        if (pkg_dir / "3_5_skipped.md").exists():
            return ("3_5_skipped.md",)
        found = sorted(
            p.name
            for p in pkg_dir.iterdir()
            if p.is_file() and p.name.startswith("3_5_") and p.name.endswith(".md")
        )
        return tuple(found)
    return tuple(name for name in step.artifact_names if (pkg_dir / name).exists())


def _resolve_next_orchestration_step(package_id: str, orch_path: Path) -> OrchStep | None:
    """Return the next incomplete orchestration step, or None when proof is ready.

    Stale-proof guard: if execution_contract.md is already substantive but some
    orchestration steps are still incomplete, the contract is from a previous run.
    In that case we log a warning and continue step scanning instead of jumping
    straight to post-agent (which would close the package with incomplete work).
    """
    orch_text = orch_path.read_text(encoding="utf-8")
    steps = _parse_orchestration_steps(orch_text, package_id)
    pkg_dir = TEAM_ARTIFACTS / package_id

    if _execution_contract_ready_for_post_agent(package_id):
        # Stale-proof guard: exclude closure/full-orch steps because their
        # "completion" IS the substantive contract itself (no separate artifact).
        non_deliverable_steps = [
            s for s in steps if not s.is_closure and not s.is_full_orchestration
        ]
        if non_deliverable_steps and not all(
            _step_is_complete(pkg_dir, s) for s in non_deliverable_steps
        ):
            incomplete_ids = [
                s.step_id
                for s in non_deliverable_steps
                if not _step_is_complete(pkg_dir, s)
            ]
            import sys
            print(
                f"⚠  [ORCH] Substantive execution_contract.md detected but step(s) "
                f"{incomplete_ids} are still incomplete — treating contract as stale "
                "(left over from a previous run). Continuing step scan.",
                file=sys.stderr,
            )
        else:
            return None

    if not steps:
        return OrchStep(
            step_id="all",
            title="Full orchestration",
            body=orch_text,
            artifact_names=(),
            is_full_orchestration=True,
        )
    for step in steps:
        if not _step_is_complete(pkg_dir, step):
            return step
    closure = next((s for s in steps if s.is_closure), None)
    if closure:
        return closure
    return OrchStep(
        step_id="8",
        title="Closure",
        body="Replace execution_contract.md with substantive delivery proof.",
        artifact_names=(),
    )


def _write_orchestration_current_task(
    package_id: str,
    agent: str,
    orch_path: Path,
    *,
    step: OrchStep | None = None,
) -> Path:
    """Write doc/current_task.md for ready_orch (one orchestration step per SDK trigger)."""
    contract_path = _execution_contract(package_id)
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    task_path = ROOT / "doc" / "current_task.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    orch_rel = _root_relative(orch_path)
    contract_rel = _root_relative(contract_path)
    resolved = step or _resolve_next_orchestration_step(package_id, orch_path)
    if resolved is None:
        raise ValueError(f"No pending orchestration step for {package_id}")

    if resolved.is_full_orchestration:
        banner = (
            "> **ORCHESTRATION-FIRST TASK -- execute completely in this session.**\n"
            "> **FIRST ACTION:** create/update `"
            f"{contract_rel}"
            "` with exactly `STARTED`, then continue.\n"
            "> Do not generate plan-next and do not replace this with a quick execution prompt.\n\n"
        )
        body = f"""# Execute Orchestration

Package: `{package_id}`
Target agent: `{agent}`
Orchestration file: `{orch_rel}`

Read `{orch_rel}` and execute STEP 1 through the final step from that file. Use the read-set, write-set, DoD commands, and Product Owner handoff recorded there.

This package is already in `ready_orch`: the next action is orchestration execution, not `generate_next_prompt.py --quick`.

"""
    elif resolved.is_closure:
        banner = (
            "> **ORCHESTRATION CLOSURE — write execution proof only.**\n"
            f"> Replace `{contract_rel}` with substantive delivery proof (not `STARTED`).\n"
            "> Do **not** run `close_package.py` or `run_autonomous.py --post-agent` — workflow does that.\n\n"
        )
        body = f"""# Orchestration Step 8 — Closure (proof file only)

Package: `{package_id}`
Target agent: `{agent}`
Orchestration reference: `{orch_rel}`

Your **only** deliverable in this session is **`{contract_rel}`** with substantive execution proof:

- summary of product behavior delivered
- exact product and test file paths changed (sp1 write-set only if applicable)
- DoD commands and results (paste pytest output or reference artifact paths)
- blockers or follow-up risks, if any

Read for context (do not execute shell from STEP 8 closure block):

- `archive/team_artifacts/{package_id}/5a_developer_sp1.md`
- `archive/team_artifacts/{package_id}/6a_tester_sp1.md`
- Developer / tester sections in `{orch_rel}`

**Forbidden in this session:** `close_package.py`, registry edits, `backlog_registry_lint`, post-agent, git commit.
Stop immediately after saving `{contract_rel}`.

"""
    else:
        needs_started = (
            resolved.step_id == "1"
            and not contract_path.exists()
        )
        started_line = (
            f"> **FIRST ACTION:** create `{contract_rel}` with exactly `STARTED`, then continue.\n"
            if needs_started
            else ""
        )
        banner = (
            f"> **ORCHESTRATION STEP TASK — execute ONLY Step {resolved.step_id} in this session.**\n"
            f"{started_line}"
            "> Do not execute other steps. Do not call `generate_next_prompt.py --quick`.\n\n"
        )
        body = f"""# Orchestration Step {resolved.step_id} — {resolved.title}

Package: `{package_id}`
Target agent: `{agent}`
Orchestration file: `{orch_rel}`

Execute ONLY the following section from `{orch_rel}`:

{resolved.body}

After completing this step, stop. The workflow loop will schedule the next step on the following iteration.

"""

    footer = f"""---

## Mandatory Final Step

"""
    if resolved.is_closure:
        footer += f"""Replace `{contract_rel}` with the proof sections above. Do not run package closure scripts.

If blocked, write a `BLOCKED` proof with last completed step and exact blocker.

If delivery was already committed before this closure step (no new working-tree changes), add a machine-parseable evidence block **exactly** as shown (no backticks around SHA or paths, no parenthetical comments on the commit line):

```text
allow_verification_only

## Pre-existing delivery evidence

- commit: <plain 7-40 char SHA, no backticks>
- files: app/your_module.py, tests/test_your_module.py
```

"""
    elif resolved.is_full_orchestration:
        footer += f"""After completing the orchestration file and DoD, replace `{contract_rel}` with concrete execution proof:

- summary of product behavior delivered
- exact product and test file paths changed
- DoD commands and results
- blockers or follow-up risks, if any

If you cannot finish the orchestration in this run, replace `STARTED` with a `BLOCKED` proof that states the last completed step, files touched, and the exact blocker. Never leave `{contract_rel}` as only `STARTED`.

If delivery is already committed before post-agent sees a working-tree diff, include a machine-parseable evidence block exactly like:

```text
Pre-existing delivery evidence:
- commit: <delivery_commit_sha>
- files: app/example.py, tests/test_example.py
```

"""
    else:
        footer += f"""If blocked on this step, replace `{contract_rel}` with a `BLOCKED` proof (last completed step, files touched, exact blocker). Do not leave only `STARTED` unless this is Step 1 and you are still working.

Intermediate steps must NOT write final delivery proof unless blocked — the closure step will update `{contract_rel}`.

"""

    footer += (
        "Do not close the package manually. `scripts/workflow.py --loop --watch-contract` "
        "is watching progress and will run `run_autonomous.py --post-agent` when proof is substantive.\n"
    )
    write_task_file_for_cursor(
        no_pause_banner=banner,
        body=body,
        footer=footer,
        task_path=task_path,
        budget_profile="strict",
    )
    return task_path


def _task_started_marker(package_id: str) -> Path:
    """Sentinel written when current_task.md is generated for a GUI agent.

    Presence means: execution_auto task was handed off to the user;
    no execution_contract.md yet → state = ready_executing.
    """
    return TEAM_ARTIFACTS / package_id / "task_started.md"


def _set_active_package_in_registry(package_id: str) -> bool:
    """Update active_package_id in backlog_registry.yaml (regex, no YAML round-trip).

    Mirrors the approach used in backlog_registry_lint.py to preserve comments/formatting.
    Returns True if the file was changed.
    """
    try:
        text = REGISTRY.read_text(encoding="utf-8")
    except OSError:
        return False
    line = f"active_package_id: {package_id}"
    new_text = re.sub(
        r"^active_package_id:\s*.*$", line, text, count=1, flags=re.MULTILINE
    )
    if new_text != text:
        REGISTRY.write_text(new_text, encoding="utf-8")
        return True
    return False


def _find_active_package(explicit: str | None) -> tuple[str | None, str]:
    """
    Returns (package_id, source) where source is 'registry' or 'fallback'.
    Priority: wip > ready > open > proposed.
    """
    if explicit:
        return explicit, "explicit"

    # Fast path: wip/ready from SSoT pointer
    pkg = active_ready_package_from_registry()
    if pkg:
        return pkg, "registry"

    # Fallback: any active status including open/proposed
    rows = [
        r for r in get_backlog_truth_view().get("now", [])
        if isinstance(r, dict) and r.get("status", "").lower() in ACTIVE_STATUSES
    ]
    selected = select_package(rows, None)
    if selected:
        return str(selected["package"]), "fallback"

    return None, "none"


def _package_status(package_id: str) -> str:
    data = load_backlog_registry()
    for item in data.get("items", []):
        if item.get("id") == package_id:
            return str(item.get("status", "unknown"))
    return "unknown"


def _last_orchestration_step(package_id: str) -> str | None:
    """Find the highest-numbered step artifact (e.g. '4_developer_...')."""
    artifacts = list_team_artifacts(package_id)
    step_files = [a for a in artifacts if a[0].isdigit()]
    return step_files[-1] if step_files else None


_AGENT_WAIT_LABELS: dict[str, str] = {
    "cursor_ai": "Cursor Composer (Ctrl+I) или другой агент в IDE",
    "claude_code": "Claude Code",
    "codex": "Codex CLI",
    "kilo": "Kilo",
    "continue": "Continue.dev (VS Code / JetBrains)",
}


def _workflow_router_doc_footer() -> str:
    return format_workflow_router_doc_footer(ROOT)


def _prompt_execute_current_task_footer(rel_contract_posix: str) -> str:
    return format_prompt_execute_current_task_footer(rel_contract_posix)


WorkflowWatchHintMode = Literal["manual", "after_sdk", "proof_already_ok"]


def _human_hint_execution_contract_wait(
    package_id: str,
    agent: str,
    *,
    watch_mode: WorkflowWatchHintMode = "manual",
) -> str:
    """Краткая инструкция: что означает [WATCH] и какие вехи пайплайна ещё впереди."""
    rel_contract = Path("archive") / "team_artifacts" / package_id / "execution_contract.md"
    who = _AGENT_WAIT_LABELS.get(agent, f"агент {agent}")

    footer = _workflow_router_doc_footer()

    if watch_mode == "proof_already_ok":
        return (
            "\n📌 [WATCH — веха 2/3 workflow.py]\n"
            "   Файл proof уже substantive до начала опроса; кондуктор сразу уйдёт в post-agent, "
            "если gate подтвердится при первой проверке.\n"
            "   Полное завершение пакета — только после успешного шага закрытия в run_autonomous "
            "(в логе обычно «Package … closed successfully»).\n\n"
            + footer
        )
    if watch_mode == "after_sdk":
        return (
            "\n📌 [WATCH — веха 2/3 workflow.py] после успешного --trigger-cmd\n"
            f"   • Веха 1/3 уже сделана: trigger command завершился успешно (см. префикс логов trigger-скрипта).\n"
            "   • Сейчас ждём substantive execution_contract.md (не только строка STARTED).\n"
            "   • Веха 3/3: post-agent → close_package — пакет официально «закрыт» только здесь.\n"
            "   • Повторно открывать doc/current_task.md обычно не нужно, если промпт уже ушёл в агент.\n\n"
            + footer
        )

    lines = [
        "\n📌 [WATCH — это не зависание] Кондуктор опрашивает диск до появления proof.\n",
        f"   Кто действует если триггер не использовали: вы или {who}.\n",
        "   Что нужно:",
        "     1) Откройте doc/current_task.md и выполните задачу целиком.",
        "     2) В начале там указано создать файл доказательства:",
        f"        {rel_contract.as_posix()}",
        "     3) Когда файл на диске станет substantive, роутер сам вызовет run_autonomous --post-agent.\n",
        "   По готовности пакета смотрите завершение run_autonomous (закрытие в реестре).\n",
        footer,
    ]
    return "\n".join(lines)


def _next_step_ready_executing(package_id: str, agent: str) -> str:
    """Пошаговая инструкция человеку: промпт агенту + команда перезапуска + ссылка на doc."""
    rel_contract = (
        Path("archive") / "team_artifacts" / package_id / "execution_contract.md"
    ).as_posix()
    who = _AGENT_WAIT_LABELS.get(agent, f"агент {agent}")
    loop_cmd = (
        f".venv\\Scripts\\python.exe scripts/workflow.py "
        f"--loop --skip-review --watch-contract --agent {agent}"
    )
    parts = [
        "СЛЕДУЮЩИЙ ШАГ — ВРУЧНУЮ (роутер ждёт файл execution_contract.md):",
        "",
        f"  1) Откройте doc/current_task.md — там ТЗ уже сформировано для {who}.",
        f"  2) В {who} вставьте промпт из блока ниже.",
        f"  3) Убедитесь, что на диске создан файл:",
        f"       {rel_contract}",
        "  4) Затем снова выполните в терминале ту же команду кондуктора:",
        f"       {loop_cmd}",
        "",
        _prompt_execute_current_task_footer(rel_contract),
        "",
        _workflow_router_doc_footer(),
    ]
    return "\n".join(parts)


# ── Router ────────────────────────────────────────────────────────────────────

def _plan_next_instruction(agent: str) -> str:
    target = "" if agent == "cursor_ai" else f" TARGET_AGENT: {agent}"
    return (
        "Прочитай doc/team_workflow/generate_plan_next_prompt.md"
        f"{target} и выполни инструкции."
    )


def resolve_state(package_id: str | None, agent: str, skip_review: bool = False) -> dict:
    """Return a state dict describing current position and next action."""

    # Перекрёстные предупреждения (например гигиена реестра). Роутер не читает
    # doc/tasklist.md — для маршрутизации только backlog_registry.yaml.
    warnings: list[str] = []

    # ── No active package ────────────────────────────────────────────────────
    if package_id is None:
        return {
            "state": STATE_NO_PACKAGE,
            "package": None,
            "status": None,
            "work_state": None,
            "next_label": "Backlog пуст — спланировать следующий пакет",
            "next_cmd": None,
            "next_hint": (
                'Вставь в агент:\n'
                f'  "{_plan_next_instruction(agent)}"\n'
                "\n"
                + _workflow_router_doc_footer()
            ),
            "warnings": warnings,
        }

    pkg_status = _package_status(package_id)
    work_state = detect_work_state(package_id)
    orch_file = _orch_file(package_id, agent)
    exec_contract = _execution_contract(package_id)

    # ── Proposed / open — нет принятого контракта ───────────────────────────
    if pkg_status in ("proposed", "open"):
        if skip_review:
            skip_flag = f"--skip-review --agent {agent}"
            if package_id:
                skip_flag += f" --package {package_id}"
            next_hint = (
                'Вставь в агент:\n'
                f'  "{_plan_next_instruction(agent)} После Phase 7 (запись контракта в реестр) '
                'НЕМЕДЛЕННО выполни через Shell:\n'
                f'  .venv\\Scripts\\python.exe scripts/workflow.py {skip_flag} --exec\n'
                '  (ревью контракта пропускается — флаг --skip-review активен)"\n'
                "\n"
                + _workflow_router_doc_footer()
            )
        else:
            next_hint = (
                'Вставь в агент:\n'
                f'  "{_plan_next_instruction(agent)}"\n'
                "\n"
                + _workflow_router_doc_footer()
            )
        return {
            "state": STATE_NEEDS_PLAN,
            "package": package_id,
            "status": pkg_status,
            "work_state": work_state,
            "next_label": f"Пакет {package_id!r} в статусе {pkg_status!r} — нужен принятый контракт",
            "next_cmd": None,
            "next_hint": next_hint,
            "skip_review": skip_review,
            "warnings": warnings,
        }

    # ── Ready, нет orchestration файла ──────────────────────────────────────
    if pkg_status in ("ready", "wip") and not orch_file.exists():

        # execution_contract уже заполнен агентом (повторный запуск цикла) → post-agent.
        # Literal STARTED is only an in-progress marker created by current_task.md.
        if _execution_contract_ready_for_post_agent(package_id):
            cmd = (
                f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                f"--post-agent --package {package_id} --agent {agent} "
                f"--budget-profile strict"
            )
            return {
                "state": STATE_WIP_RUNNING,
                "package": package_id,
                "status": pkg_status,
                "work_state": work_state,
                "last_artifact": None,
                "next_label": "execution_contract.md найден — запустить --post-agent",
                "next_cmd": cmd,
                "next_hint": None,
                "warnings": warnings,
            }

        # task_started.md есть, но контракта нет → агент ещё работает
        task_started = _task_started_marker(package_id)
        if task_started.exists() or exec_contract.exists():
            return {
                "state": STATE_READY_EXECUTING,
                "package": package_id,
                "status": pkg_status,
                "work_state": work_state,
                "next_label": (
                    "Выполнить doc/current_task.md в IDE; создать execution_contract.md; "
                    "перезапустить кондуктор (--loop …)"
                ),
                "next_cmd": None,
                "next_hint": _next_step_ready_executing(package_id, agent),
                "warnings": warnings,
            }

        # Determine execution route via complexity classifier + US/CJM check.
        # Orchestration only for medium/high packages that have US or CJM context;
        # lightweight infra packages go directly to run_autonomous.py.
        _state_data = _load_state(package_id)
        _contract = _state_data.get("contract") or {}
        _rows = _state_data.get("rows") or []
        _row = next((r for r in _rows if r.get("package") == package_id), {})
        _us = _row.get("user_stories") or []
        _cjm = _row.get("cjm_moments") or []
        has_us_or_cjm = bool(_us) or bool(_cjm)

        complexity = classify_package_complexity(_contract)
        # Accepted learning-product contracts with explicit US/CJM context go
        # through orchestration first, even when the mechanical complexity score
        # is low. Direct execution is reserved for compact maintenance packages
        # that do not need the plan-next/orchestration handoff.
        use_orchestration = has_us_or_cjm or complexity["route"] == "orchestration"

        if use_orchestration:
            cmd = (
                f".venv\\Scripts\\python.exe scripts/generate_orchestration_prompt.py "
                f"--agent {agent} --package {package_id}"
            )
            label = (
                f"Сгенерировать orchestration для {package_id!r} "
                f"(сложность: {complexity['label']}, агент: {agent})"
            )
        else:
            cmd = (
                f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                f"--agent {agent} --package {package_id} --budget-profile strict"
            )
            label = (
                f"Прямое выполнение {package_id!r} через run_autonomous "
                f"(сложность: {complexity['label']}, has_us_or_cjm={has_us_or_cjm}, агент: {agent})"
            )

        return {
            "state": STATE_READY_FRESH,
            "package": package_id,
            "status": pkg_status,
            "work_state": work_state,
            "next_label": label,
            "next_cmd": cmd,
            "next_hint": None,
            "skip_review": skip_review,
            "warnings": warnings,
            "execution_auto": not use_orchestration,
            "complexity": complexity["label"],
            "complexity_route": complexity["route"],
            "has_us_or_cjm": has_us_or_cjm,
        }

    # ── Ready / WIP, orchestration файл есть ────────────────────────────────
    if pkg_status in ("ready", "wip") and orch_file.exists():
        last_step = _last_orchestration_step(package_id)

        if _execution_contract_ready_for_post_agent(package_id):
            # Контракт есть — закрытие через --post-agent (не обычный run_autonomous / RESUME)
            cmd = (
                f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                f"--post-agent --package {package_id} --agent {agent} "
                f"--budget-profile strict"
            )
            label = "execution_contract.md найден — запустить --post-agent"
        else:
            # Orchestration есть, контракт ещё не substantive — показать актуальный STEP.
            cmd = None
            try:
                next_orch_step = _resolve_next_orchestration_step(package_id, orch_file)
            except OSError:
                next_orch_step = None

            if next_orch_step is not None:
                label = (
                    f"Выполни STEP {next_orch_step.step_id} — {next_orch_step.title} из:\n"
                    f"  archive/team_artifacts/{package_id}/orchestration_{agent}.md"
                )
                step_hint = (
                    f"  2) Выполните STEP {next_orch_step.step_id} "
                    f"({next_orch_step.title}) в этой сессии; "
                    "следующие шаги — на новых итерациях --loop.\n"
                )
            else:
                label = (
                    f"Замените execution_contract.md substantive proof (closure):\n"
                    f"  archive/team_artifacts/{package_id}/execution_contract.md"
                )
                step_hint = (
                    "  2) STEP 8 (closure): только proof-файл, без close_package в агенте.\n"
                )

            next_hint = (
                "СЛЕДУЮЩИЙ ШАГ:\n"
                f"  1) Откройте файл:\n"
                f"       archive/team_artifacts/{package_id}/orchestration_{agent}.md\n"
                f"{step_hint}"
                "  3) Промежуточные шаги: execution_contract.md может оставаться STARTED; "
                f"финальный proof — archive/team_artifacts/{package_id}/execution_contract.md "
                "(см. doc/current_task.md).\n\n"
                + _workflow_router_doc_footer()
            )

        return {
            "state": (
                STATE_WIP_RUNNING
                if _execution_contract_ready_for_post_agent(package_id)
                else STATE_READY_ORCH
            ),
            "package": package_id,
            "status": pkg_status,
            "work_state": work_state,
            "last_artifact": last_step,
            "next_label": label,
            "next_cmd": cmd,
            "next_hint": None if cmd else next_hint,
            "orch_file": str(orch_file.relative_to(ROOT)),
            "warnings": warnings,
        }

    # ── Fallback ─────────────────────────────────────────────────────────────
    return {
        "state": "unknown",
        "package": package_id,
        "status": pkg_status,
        "work_state": work_state,
        "next_label": "Неизвестное состояние — запусти pipeline_status.py для диагностики",
        "next_cmd": ".venv\\Scripts\\python.exe scripts/pipeline_status.py",
        "next_hint": _workflow_router_doc_footer(),
        "warnings": warnings,
    }


# ── Loop helpers ─────────────────────────────────────────────────────────────

_LOOP_SEP = "─" * 55
_EXIT_NON_STOP_CONTINUE = 10  # зеркало run_autonomous.py
_EXIT_POST_AGENT_CHAT_API_HANDOFF = 11  # run_autonomous.EXIT_POST_AGENT_CHAT_API_HANDOFF


def _post_agent_chat_api_handoff(rc: int) -> bool:
    return rc == _EXIT_POST_AGENT_CHAT_API_HANDOFF


def _print_loop_handoff_pause(
    step: int,
    package_id: str,
    *,
    trigger_rc: int | None,
    contract_found: bool,
    post_agent_rc: int,
) -> None:
    trig = "skipped" if trigger_rc is None else str(trigger_rc)
    contract = "found" if contract_found else "missing"
    contract_path = f"archive/team_artifacts/{package_id}/execution_contract.md"
    print(
        f"\nℹ  [LOOP {step}] пауза: post-agent вернул {_EXIT_POST_AGENT_CHAT_API_HANDOFF} "
        f"(chat-api handoff). Пакет не закрыт.\n"
        f"   package={package_id}, trigger={trig}, contract={contract}.\n"
        f"   Обновите {contract_path} после работы в IDE-агенте;\n"
        "   без этого следующий --loop снова упрётся в тот же BLOCKED-контракт.\n"
        "   Кондуктор остановлен."
    )


def _format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}m {secs:02d}s"


def _describe_file_state(path: Path) -> str:
    try:
        display_path = path.relative_to(ROOT)
    except ValueError:
        display_path = path
    if not path.exists():
        return f"not found ({display_path})"
    try:
        stat = path.stat()
    except OSError as exc:
        return f"exists, stat failed: {exc}"
    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
    return f"found ({display_path}, {stat.st_size} bytes, mtime={mtime})"


def _print_trigger_watch_handoff(path: Path, *, timeout: int, poll: int) -> None:
    print(
        "\nℹ  [TRIGGER] trigger command finished — веха 1/3 этого цикла; "
        "workflow.py переходит на веху 2/3 (ожидание substantive proof).\n"
        "   Полное закрытие пакета (веха 3/3) произойдёт только после успешного post-agent.\n"
        f"   Expected proof: {path.relative_to(ROOT)}\n"
        f"   Poll: every {poll}s, timeout: {timeout}s\n"
        f"   Current state: {_describe_file_state(path)}"
    )


def _print_loop_summary(
    step: int,
    package_id: str,
    *,
    trigger_rc: int | None,
    contract_found: bool,
    post_agent_rc: int,
) -> None:
    trig = "skipped" if trigger_rc is None else str(trigger_rc)
    contract = "found" if contract_found else "missing"
    print(
        f"✅ [LOOP {step}] completed: package={package_id}, "
        f"trigger={trig}, contract={contract}, post-agent={post_agent_rc}, close=success"
    )


def _wait_for_file(
    path: Path,
    *,
    timeout: int,
    poll: int = 10,
    label: str = "",
    human_hint: str | None = None,
    ready_check=None,
) -> bool:
    """Poll for `path` to appear and optionally satisfy a readiness predicate."""
    if human_hint:
        print(human_hint)
    deadline = time.time() + timeout
    started = time.time()
    next_status_at = started
    tag = label or path.name
    print(
        f"\n⏳ [WATCH] Жду {tag} (таймаут {timeout}s, опрос каждые {poll}s)...\n"
        f"   State: {_describe_file_state(path)}"
    )
    try:
        while time.time() < deadline:
            if path.exists():
                if ready_check is None or ready_check():
                    print(f"✅ [WATCH] Обнаружен: {tag} — {_describe_file_state(path)}")
                    return True
                now = time.time()
                if now >= next_status_at:
                    print(
                        f"   [WATCH] {_format_elapsed(now - started)} elapsed; "
                        f"{_describe_file_state(path)}; proof not ready yet"
                    )
                    next_status_at = now + max(30, poll)
            now = time.time()
            if now >= next_status_at:
                print(
                    f"   [WATCH] {_format_elapsed(now - started)} elapsed; "
                    f"{_describe_file_state(path)}"
                )
                next_status_at = now + max(30, poll)
            time.sleep(poll)
    except KeyboardInterrupt:
        print(
            "\n⚠ [WATCH] KeyboardInterrupt received.\n"
            f"   Proof state now: {_describe_file_state(path)}\n"
            "   Recovery: rerun the same workflow.py --loop command. "
            "If the proof exists, the router should resume with --post-agent."
        )
        raise SystemExit(130)
    print(f"⏰ [WATCH] Таймаут {timeout}s — {tag} не появился.")
    return False


def _trigger_cmd_rc_hint(rc: int) -> str:
    """Краткая подсказка по exit-кодам триггера (cursor / deepseek_tui / orchestrator).

    Для произвольной `--trigger-cmd` rc может быть любым — даём нейтральную строку.
    """
    return {
        1: (
            "конфиг/I/O: отсутствует API-ключ, не найден файл задачи, или оркестратор не смог "
            "определить доступные credentials. Проверьте .env (CURSOR_API_KEY / DEEPSEEK_API_KEY / "
            "DEEPSEEK_CLI_CMD) и что WORKFLOW_CURRENT_TASK_PATH ведёт к существующему файлу."
        ),
        2: (
            "агент вернул status=error. Проверьте лог выше — там будет error_reason из trigger_metrics.jsonl. "
            "Для оркестратора: все executors в fallback-цепочке завершились с ошибкой."
        ),
        3: (
            "временный сбой сети/SDK после повторных попыток, "
            "или abort по started_stalled (execution_contract.md слишком долго оставался только STARTED). "
            "Для stall: default для Cursor — CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS=0; "
            "workflow --watch-contract отдельно ждёт substantive proof. "
            "Для SDK/оркестратора: проверьте API и trigger_metrics.jsonl, повторите через несколько минут."
        ),
        4: "фатальная ошибка SDK (non-retryable) или неожиданное исключение — см. лог выше.",
        130: (
            "trigger прерван пользователем (Ctrl+C / Windows batch prompt). "
            "Если агент уже завершил работу, проверьте execution_contract.md и "
            "перезапустите workflow.py --loop."
        ),
    }.get(
        rc,
        "произвольная команда триггера — см. её документацию и вывод выше.",
    )


def _validate_trigger_agent_pair(trigger_cmd: str | None, agent: str) -> str | None:
    if not trigger_cmd:
        return None
    normalized = trigger_cmd.replace("\\", "/").lower()
    if "deepseek_agent_trigger.ts" in normalized and agent != "continue":
        return (
            "--trigger-cmd scripts/deepseek_agent_trigger.ts требует --agent continue. "
            "DeepSeek Chat API trigger является экспериментальным handoff-only мостом и должен использовать "
            "orchestration_continue.md / post-agent attribution continue."
        )
    if "cursor_agent_trigger.ts" in normalized and agent != "cursor_ai":
        return (
            "--trigger-cmd scripts/cursor_agent_trigger.ts требует --agent cursor_ai. "
            "Cursor trigger исполняет задачу через Agent.prompt и должен использовать "
            "orchestration_cursor_ai.md / post-agent attribution cursor_ai."
        )
    return None


def _invoke_trigger_cmd(cmd: str, task_path: Path) -> int:
    """Запуск пользовательской команды триггера (SDK / обёртка).

    Путь к `doc/current_task.md` передаётся в ``WORKFLOW_CURRENT_TASK_PATH`` (и argv — на усмотрение скрипта).
    ``CURSOR_API_KEY`` и прочие секреты — только из окружения процесса, не добавляются роутером.
    """
    env = os.environ.copy()
    env["WORKFLOW_CURRENT_TASK_PATH"] = str(task_path.resolve())
    print(f"\n▶ [TRIGGER] {cmd}\n")
    try:
        return int(subprocess.run(cmd, shell=True, cwd=str(ROOT), env=env).returncode)
    except KeyboardInterrupt:
        print(
            "\n⚠ [TRIGGER] Команда прервана KeyboardInterrupt. "
            "На Windows это часто происходит после Ctrl+C/Terminate batch job вокруг npx. "
            "Если Cursor уже завершил Agent.prompt, проверьте execution_contract.md и "
            "перезапустите кондуктор."
        )
        return 130


def _trigger_retry_limit() -> int:
    raw = os.environ.get("WORKFLOW_TRIGGER_RETRIES", "2")
    try:
        return max(0, int(raw))
    except ValueError:
        return 2


def _orch_step_watch_timeout(total_timeout: int) -> int:
    per_step = int(os.environ.get("WORKFLOW_ORCH_STEP_WATCH_TIMEOUT", "1800"))
    return min(total_timeout, max(60, per_step))


def _invoke_trigger_cmd_with_retries(cmd: str, task_path: Path) -> int:
    """Run trigger; retry rc=2/3/4 (agent error / transient / uncaught SDK network) up to WORKFLOW_TRIGGER_RETRIES."""
    limit = _trigger_retry_limit()
    last_rc = 0
    for attempt in range(limit + 1):
        last_rc = _invoke_trigger_cmd(cmd, task_path)
        if last_rc == 0 or last_rc not in (2, 3, 4):
            return last_rc
        if attempt < limit:
            pause = 5 * (attempt + 1)
            print(
                f"⚠ [LOOP] --trigger-cmd rc={last_rc} "
                f"({attempt + 1}/{limit + 1}); повтор через {pause}s…"
            )
            time.sleep(pause)
    return last_rc


def _wait_for_orch_step_progress(
    package_id: str,
    step: OrchStep,
    *,
    timeout: int,
    poll: int = 10,
    allow_contract_exit: bool = False,
) -> Literal["contract", "step", "timeout"]:
    """Wait for intermediate step artifacts or (optionally) substantive execution_contract.

    ``allow_contract_exit=False`` (default) is intentional for intermediate steps
    (STEP 1–7, 3.5): a substantive contract during these steps indicates a stale
    proof from a previous run. Only pass ``True`` for closure / full-orchestration.
    """
    pkg_dir = TEAM_ARTIFACTS / package_id
    deadline = time.time() + _orch_step_watch_timeout(timeout)
    tag = f"STEP {step.step_id} ({package_id})"
    print(
        f"\n⏳ [WATCH] Жду {tag} (таймаут {_orch_step_watch_timeout(timeout)}s, "
        f"опрос каждые {poll}s)...\n"
    )
    while time.time() < deadline:
        if allow_contract_exit and _execution_contract_ready_for_post_agent(package_id):
            print(f"✅ [WATCH] Substantive execution_contract.md — {_describe_file_state(_execution_contract(package_id))}")
            return "contract"
        if _step_is_complete(pkg_dir, step):
            found = _step_completion_artifact_names(pkg_dir, step)
            print(
                f"✅ [WATCH] STEP {step.step_id} complete"
                + (f" — artifacts: {', '.join(found)}" if found else "")
            )
            return "step"
        time.sleep(poll)
    print(f"⏰ [WATCH] Таймаут — STEP {step.step_id} не завершён.")
    return "timeout"


def _orch_step_needs_substantive_contract_wait(next_step: OrchStep | None) -> bool:
    """Return True when the loop should wait for a substantive execution_contract.md.

    ``None`` means _resolve_next_orchestration_step found no incomplete steps (proof
    already ready) — the loop must wait for the final contract, so True is correct.
    Intermediate role steps (STEP 1–7, 3.5) produce per-role artifact files, NOT the
    final execution_contract.md, so they return False.
    """
    if next_step is None:
        return True  # No pending step → already at closure, need final proof
    return next_step.is_full_orchestration or next_step.is_closure


def _loop_lock_path() -> Path:
    return TEAM_ARTIFACTS / "_locks" / "workflow-loop.lock"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def _read_loop_lock_pid(lock_path: Path) -> int | None:
    try:
        text = lock_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"^pid=(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def _acquire_loop_lock() -> bool:
    """Exclusive lock for --loop (one conductor per repo). Stale locks are reclaimed."""
    lock_path = _loop_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(f"pid={os.getpid()}\nstarted={time.time():.0f}\n")
            return True
        except FileExistsError:
            stale_pid = _read_loop_lock_pid(lock_path)
            if stale_pid is not None and not _pid_alive(stale_pid):
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                if attempt == 0:
                    continue
            holder = stale_pid if stale_pid is not None else "unknown"
            print(
                f"❌ [LOOP] Уже запущен другой workflow.py --loop (lock pid={holder}). "
                f"Остановите его или удалите {_root_relative(lock_path)} если процесс мёртв."
            )
            return False
    return False


def _release_loop_lock() -> None:
    lock_path = _loop_lock_path()
    if not lock_path.exists():
        return
    owner = _read_loop_lock_pid(lock_path)
    if owner is not None and owner != os.getpid():
        return
    try:
        lock_path.unlink()
    except OSError:
        pass


def _continue_after_orch_step(
    package_id: str,
    next_step: OrchStep,
    *,
    source: str,
) -> bool:
    """If step artifacts are on disk, log and signal loop continue."""
    pkg_dir = TEAM_ARTIFACTS / package_id
    if not _step_is_complete(pkg_dir, next_step):
        return False
    names = ", ".join(_step_completion_artifact_names(pkg_dir, next_step)) or "(skip/conditional)"
    print(
        f"✅ [LOOP] STEP {next_step.step_id} complete ({source}) — "
        f"artifacts: {names}. Следующий шаг на новой итерации."
    )
    return True


def _wait_for_registry_change(prev_mtime: float, *, timeout: int, poll: int = 5) -> bool:
    """Wait until backlog_registry.yaml mtime changes (plan-next wrote the contract)."""
    deadline = time.time() + timeout
    print(f"\n⏳ [WATCH] Жду изменений в backlog_registry.yaml (таймаут {timeout}s)...")
    while time.time() < deadline:
        try:
            cur = REGISTRY.stat().st_mtime
        except OSError:
            time.sleep(poll)
            continue
        if cur > prev_mtime + 1:
            print("✅ [WATCH] backlog_registry.yaml обновлён — контракт принят.")
            return True
        time.sleep(poll)
    print(f"⏰ [WATCH] Таймаут {timeout}s — реестр не изменился.")
    return False


def _extend_post_agent_cmd(cmd: str | None, *, post_agent_no_dod_cache: bool) -> str | None:
    """If requested, append ``--no-dod-cache`` to ``run_autonomous.py --post-agent`` invocations."""
    if not cmd or not post_agent_no_dod_cache:
        return cmd
    if "--post-agent" not in cmd:
        return cmd
    if "--no-dod-cache" in cmd:
        return cmd
    return f"{cmd} --no-dod-cache"


# States where watching for execution_contract.md makes sense
_WATCH_CONTRACT_STATES = {STATE_READY_ORCH, STATE_WIP_RUNNING}
# States that require waiting for a human/agent plan before re-routing
_NEEDS_HUMAN_STATES = {STATE_NO_PACKAGE, STATE_NEEDS_PLAN}


def _run_loop(
    initial_package: str | None,
    agent: str,
    *,
    skip_review: bool,
    watch_contract: bool,
    watch_timeout: int,
    loop_max: int,
    trigger_cmd: str | None = None,
    post_agent_no_dod_cache: bool = False,
) -> int:
    """
    Conductor loop: resolve state → execute next_cmd → re-resolve → repeat.

    Transitions handled automatically:
      needs_plan   → (waits for registry change) → ready_fresh
      ready_fresh  → generate_orchestration_prompt → ready_orch
      ready_orch   → [watch_contract] wait execution_contract.md
                   → run_autonomous --post-agent → re-route
      wip_running  → run_autonomous --post-agent (exec contract found)
      no_package   → stop (backlog empty)
    """
    if not _acquire_loop_lock():
        return 1
    try:
        return _run_loop_body(
            initial_package,
            agent,
            skip_review=skip_review,
            watch_contract=watch_contract,
            watch_timeout=watch_timeout,
            loop_max=loop_max,
            trigger_cmd=trigger_cmd,
            post_agent_no_dod_cache=post_agent_no_dod_cache,
        )
    finally:
        _release_loop_lock()


def _run_loop_body(
    initial_package: str | None,
    agent: str,
    *,
    skip_review: bool,
    watch_contract: bool,
    watch_timeout: int,
    loop_max: int,
    trigger_cmd: str | None,
    post_agent_no_dod_cache: bool,
) -> int:
    package_id = initial_package
    step = 0

    while step < loop_max:
        step += 1  # Count before processing so every continue/return path is covered
        package_id, _ = _find_active_package(package_id)
        state = resolve_state(package_id, agent, skip_review=skip_review)
        current = state.get("state")

        print(f"\n{_LOOP_SEP}")
        work_label = state.get("work_state") or ""
        state_display = f"{current}" + (f" / {work_label}" if work_label and work_label != current else "")
        print(f"  [LOOP {step}/{loop_max}] STATE: {state_display}  PACKAGE: {state.get('package') or '—'}")
        print(_LOOP_SEP)
        _print_state(state)

        # ── Backlog пуст ──────────────────────────────────────────────────────
        if current == STATE_NO_PACKAGE:
            print("ℹ  Backlog пуст. Цикл завершён.")
            return 0

        # ── Нужен план (needs_plan) ───────────────────────────────────────────
        if current == STATE_NEEDS_PLAN:
            if not skip_review:
                # Без --skip-review не можем автоматически принять план
                print("⚠  [LOOP] needs_plan без --skip-review: ручное действие.")
                print("   Добавьте --skip-review для автоматического продолжения после Phase 7.")
                print(f"   Справка: {WORKFLOW_ROUTER_DOC_REL} — состояние needs_plan.")
                return 1
            # --skip-review: ждём, пока агент (который выполнит plan-next по hint)
            # запишет контракт в backlog_registry.yaml
            try:
                prev_mtime = REGISTRY.stat().st_mtime
            except OSError:
                prev_mtime = 0.0
            print(
                "\n📋 [LOOP] needs_plan + --skip-review:\n"
                "   Выполните промпт из блока «СЛЕДУЮЩИЙ ШАГ» выше (plan-next).\n"
                "   После Phase 7 роутер продолжит автоматически.\n"
                f"   Справка: {WORKFLOW_ROUTER_DOC_REL} — строка таблицы «needs_plan».\n"
            )
            changed = _wait_for_registry_change(prev_mtime, timeout=watch_timeout)
            if not changed:
                print("❌ [LOOP] Реестр не обновлён за отведённое время. Стоп.")
                return 1
            # Реестр изменился — сбросить package_id, re-route подхватит новый ready
            package_id = None
            continue

        cmd = state.get("next_cmd")

        # ── ready_fresh: orchestration или execution_auto ─────────────────────
        if current == STATE_READY_FRESH:
            if state.get("execution_auto") and watch_contract:
                # GUI-агент + --watch-contract:
                #  • Без --trigger-cmd: sentinel task_started + PAUSE (терминал свободен).
                #  • С --trigger-cmd: генерируем current_task через run_autonomous, SDK-триггер,
                #    блокирующее ожидание execution_contract.md → --post-agent.
                pkg = state["package"]
                marker_path = _task_started_marker(pkg)
                marker_path.parent.mkdir(parents=True, exist_ok=True)
                contract_path = ROOT / "archive" / "team_artifacts" / pkg / "execution_contract.md"
                task_path = ROOT / "doc" / "current_task.md"

                if trigger_cmd:
                    gen_cmd = (
                        f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                        f"--agent {agent} --package {pkg} --budget-profile strict"
                    )
                    print(
                        f"\n▶ [LOOP] execution_auto + --trigger-cmd: "
                        f"генерирую current_task.md:\n{gen_cmd}\n"
                    )
                    rc_gen = subprocess.run(gen_cmd, shell=True, cwd=str(ROOT)).returncode
                    if rc_gen != 0:
                        print(
                            "❌ [LOOP] run_autonomous не смог сгенерировать current_task.md "
                            f"(rc={rc_gen}). Триггер не запускается, чтобы не отправить "
                            "агенту старую задачу. Стоп."
                        )
                        return rc_gen
                    # Синхронный run_autonomous может закрыть пакет до GUI-фазы (пустой промпт +
                    # пройденный DoD). Тогда триггер/watch ждали бы чужой current_task.md и
                    # execution_contract другого пакета — пропускаем цепочку SDK→watch→post-agent.
                    if _package_status(pkg) == "closed":
                        print(
                            "\nℹ  [LOOP] Пакет уже закрыт после run_autonomous "
                            f"({pkg!r}, статус closed). "
                            "Пропуск --trigger-cmd, watch_contract и --post-agent для этого пакета.\n"
                        )
                        package_id = None
                        continue
                    if not marker_path.exists():
                        marker_path.write_text(
                            f"# Task Started\n\nPackage: {pkg}\nAgent: {agent}\n",
                            encoding="utf-8",
                        )
                    if _set_active_package_in_registry(pkg):
                        print(f"   ✓ backlog_registry.yaml → active_package_id: {pkg}")

                    if _execution_contract_ready_for_post_agent(pkg):
                        print(
                            "ℹ  [LOOP] execution_contract.md уже на диске — "
                            "пропуск SDK-триггера."
                        )
                        rc_trig = None
                        watch_mode: WorkflowWatchHintMode = "proof_already_ok"
                    else:
                        rc_trig = _invoke_trigger_cmd_with_retries(trigger_cmd, task_path)
                        if rc_trig != 0:
                            hint = _trigger_cmd_rc_hint(rc_trig)
                            print(
                                "❌ [LOOP] --trigger-cmd завершился с ошибкой "
                                f"(rc={rc_trig}). {hint} "
                                "Проверьте также npm и `@cursor/sdk`. Стоп."
                            )
                            return rc_trig
                        watch_mode = "after_sdk"

                    _print_trigger_watch_handoff(contract_path, timeout=watch_timeout, poll=10)
                    found = _wait_for_file(
                        contract_path,
                        timeout=watch_timeout,
                        label=f"execution_contract.md ({pkg})",
                        human_hint=_human_hint_execution_contract_wait(
                            pkg, agent, watch_mode=watch_mode
                        ),
                        ready_check=lambda pkg=pkg: _execution_contract_ready_for_post_agent(pkg),
                    )
                    if not found:
                        print("❌ [LOOP] Контракт не появился за отведённое время. Стоп.")
                        return 1
                    post_cmd = _extend_post_agent_cmd(
                        (
                            f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                            f"--post-agent --package {pkg} --agent {agent} --budget-profile strict"
                        ),
                        post_agent_no_dod_cache=post_agent_no_dod_cache,
                    )
                    print(f"\n▶ [LOOP] post-agent: {post_cmd}\n")
                    rc = subprocess.run(post_cmd, shell=True, cwd=str(ROOT)).returncode
                    if _post_agent_chat_api_handoff(rc):
                        _print_loop_handoff_pause(
                            step,
                            pkg,
                            trigger_rc=rc_trig,
                            contract_found=found,
                            post_agent_rc=rc,
                        )
                        return 0
                    if rc not in (0, _EXIT_NON_STOP_CONTINUE):
                        print(f"❌ [LOOP] --post-agent rc={rc}. Стоп.")
                        return rc
                    _print_loop_summary(
                        step,
                        pkg,
                        trigger_rc=rc_trig,
                        contract_found=found,
                        post_agent_rc=rc,
                    )
                    package_id = None
                    continue

                if not marker_path.exists():
                    marker_path.write_text(
                        f"# Task Started\n\nPackage: {pkg}\nAgent: {agent}\n",
                        encoding="utf-8",
                    )
                    if _set_active_package_in_registry(pkg):
                        print(f"   ✓ backlog_registry.yaml → active_package_id: {pkg}")

                rel_contract = Path("archive") / "team_artifacts" / pkg / "execution_contract.md"
                rel_posix = rel_contract.as_posix()
                who = _AGENT_WAIT_LABELS.get(agent, f"агент {agent}")
                loop_cmd = (
                    f".venv\\Scripts\\python.exe scripts/workflow.py "
                    f"--loop --skip-review --watch-contract --agent {agent}"
                )
                print(
                    f"\n📌 [PAUSE] Пакет {pkg!r}: терминал свободен до появления "
                    "execution_contract.md.\n\n"
                    "СЛЕДУЮЩИЙ ШАГ:\n"
                    "  1) Откройте doc/current_task.md.\n"
                    f"  2) В {who} выполните промпт из блока ниже.\n"
                    "  3) Убедитесь, что на диске создан файл:\n"
                    f"       {rel_posix}\n"
                    "  4) Перезапустите кондуктора:\n"
                    f"       {loop_cmd}\n\n"
                    + _prompt_execute_current_task_footer(rel_posix)
                    + "\n\n"
                    + _workflow_router_doc_footer()
                    + "\n"
                )
                return 0  # освобождаем терминал; повторный запуск подхватит контракт

            if not cmd:
                print("❌ [LOOP] ready_fresh без next_cmd. Диагностика: pipeline_status.py")
                return 1
            print(f"\n▶ [LOOP] {cmd}\n")
            rc = subprocess.run(cmd, shell=True, cwd=str(ROOT)).returncode
            if rc != 0:
                # rc=2 от close_package (нет execution_contract.md) в режиме execution_auto
                # без --watch-contract означает: задача ещё не выполнена агентом.
                if state.get("execution_auto") and rc == 2:
                    print(
                        "ℹ  [LOOP] execution_auto: DoD пройдены, но пакет требует "
                        "execution_contract.md для закрытия.\n"
                        "   Выполните задачу в агенте, создайте контракт, "
                        "затем перезапустите с --watch-contract.\n"
                        f"   Справка: {WORKFLOW_ROUTER_DOC_REL}."
                    )
                    return 0
                print(f"❌ [LOOP] Команда завершилась с rc={rc}. Стоп.")
                return rc

            if state.get("execution_auto"):
                # execution_auto без --watch-contract: run_autonomous вернул 0.
                print(
                    "ℹ  [LOOP] execution_auto: current_task.md сгенерирован.\n"
                    "   Выполните задачу в агенте, затем запустите --post-agent вручную.\n"
                    "   Либо добавьте --watch-contract для автоматического ожидания контракта.\n"
                    f"   Справка: {WORKFLOW_ROUTER_DOC_REL}."
                )
                return 0
            else:
                # Тяжёлый пакет: orchestration сгенерирован → re-route даст ready_orch
                package_id = state.get("package")
                continue

        # ── ready_executing: task_started.md есть, ждём execution_contract ─────
        if current == STATE_READY_EXECUTING:
            pkg = state["package"]
            contract_path = ROOT / "archive" / "team_artifacts" / pkg / "execution_contract.md"
            if contract_path.exists():
                # Агент завершил задачу между запусками — сразу post-agent
                post_cmd = _extend_post_agent_cmd(
                    (
                        f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                        f"--post-agent --package {pkg} --agent {agent} --budget-profile strict"
                    ),
                    post_agent_no_dod_cache=post_agent_no_dod_cache,
                )
                print(f"\n▶ [LOOP] Contract found, post-agent: {post_cmd}\n")
                rc = subprocess.run(post_cmd, shell=True, cwd=str(ROOT)).returncode
                if _post_agent_chat_api_handoff(rc):
                    _print_loop_handoff_pause(
                        step,
                        pkg,
                        trigger_rc=None,
                        contract_found=True,
                        post_agent_rc=rc,
                    )
                    return 0
                if rc not in (0, _EXIT_NON_STOP_CONTINUE):
                    print(f"❌ [LOOP] --post-agent rc={rc}. Стоп.")
                    return rc
                _print_loop_summary(
                    step,
                    pkg,
                    trigger_rc=None,
                    contract_found=True,
                    post_agent_rc=rc,
                )
                package_id = None
                continue
            # Инструкции уже выведены в блоке СЛЕДУЮЩИЙ ШАГ (_print_state); дублировать не нужно.
            return 0

        # ── ready_orch: orchestration есть, нет execution_contract ───────────
        if current == STATE_READY_ORCH:
            if watch_contract:
                pkg = state["package"]
                contract_path = (
                    ROOT / "archive" / "team_artifacts" / pkg / "execution_contract.md"
                )
                orch_value = state.get("orch_file") or _orch_file(pkg, agent)
                orch_path = _resolve_repo_path(orch_value)
                print(
                    "\n▶ [LOOP] Генерирую current_task.md из orchestration: "
                    f"{_root_relative(orch_path)}\n"
                )
                if not orch_path.exists():
                    print(
                        "❌ [LOOP] orchestration-файл не найден. "
                        "Триггер/WATCH не запускаются, чтобы не работать со старой задачей. Стоп."
                    )
                    return 1
                try:
                    next_step = _resolve_next_orchestration_step(pkg, orch_path)
                    if next_step is not None:
                        print(
                            f"   Orchestration target: STEP {next_step.step_id} — "
                            f"{next_step.title}\n"
                        )
                        task_path = _write_orchestration_current_task(
                            pkg, agent, orch_path, step=next_step
                        )
                    else:
                        task_path = ROOT / "doc" / "current_task.md"
                except (OSError, ValueError) as exc:
                    print(
                        "❌ [LOOP] Не удалось записать doc/current_task.md "
                        f"для orchestration ({exc}). Стоп."
                    )
                    return 1

                rc_trig = None
                watch_mode: WorkflowWatchHintMode = "manual"
                found = False
                contract_substantive = _execution_contract_ready_for_post_agent(pkg)
                ready_for_post_agent = contract_substantive and (
                    next_step is None
                    or next_step.is_closure
                )

                if ready_for_post_agent:
                    found = True
                    print(
                        "ℹ  [LOOP] execution_contract.md уже substantive — "
                        "пропуск SDK-триггера."
                    )
                    watch_mode = "proof_already_ok"
                elif trigger_cmd:
                    rc_trig = _invoke_trigger_cmd_with_retries(trigger_cmd, task_path)
                    if rc_trig != 0:
                        hint = _trigger_cmd_rc_hint(rc_trig)
                        print(
                            "❌ [LOOP] --trigger-cmd завершился с ошибкой "
                            f"(rc={rc_trig}). {hint} "
                            "Проверьте также npm и `@cursor/sdk`. Стоп."
                        )
                        return rc_trig
                    watch_mode = "after_sdk"
                    if (
                        next_step
                        and not _orch_step_needs_substantive_contract_wait(next_step)
                    ):
                        if _continue_after_orch_step(
                            pkg, next_step, source="post-trigger"
                        ):
                            continue
                        _print_trigger_watch_handoff(
                            contract_path, timeout=watch_timeout, poll=10
                        )
                        progress = _wait_for_orch_step_progress(
                            pkg, next_step, timeout=watch_timeout,
                            allow_contract_exit=False,  # intermediate step — stale proof guard
                        )
                        if progress == "step":
                            continue
                        if progress == "timeout":
                            print(
                                "❌ [LOOP] Orchestration step не завершён "
                                "за отведённое время. Стоп."
                            )
                            return 1
                        if progress == "contract":
                            found = True
                    else:
                        _print_trigger_watch_handoff(
                            contract_path, timeout=watch_timeout, poll=10
                        )
                    if (
                        contract_substantive
                        and next_step
                        and next_step.is_closure
                    ):
                        found = True
                        print(
                            "ℹ  [LOOP] substantive execution_contract уже на диске "
                            "после trigger — переход к post-agent."
                        )
                else:
                    print(
                        "\n📋 [LOOP] ready_orch — doc/current_task.md готов.\n"
                        "\nСЛЕДУЮЩИЙ ШАГ:\n"
                        "  1) Выполните задачу из doc/current_task.md в IDE (см. промпт для агента "
                        "в самом файле).\n"
                        "  2) Либо следуйте шагам из orch-файла — но тогда вручную создайте "
                        "execution_contract.md по правилам пакета.\n"
                        "  Роутер ждёт появления execution_contract.md на диске.\n\n"
                        + _workflow_router_doc_footer()
                    )

                if not found:
                    if (
                        next_step
                        and not _orch_step_needs_substantive_contract_wait(next_step)
                    ):
                        if _continue_after_orch_step(
                            pkg, next_step, source="late-check"
                        ):
                            continue
                        print(
                            f"❌ [LOOP] STEP {next_step.step_id} не завершён — "
                            "не переключаюсь на ожидание substantive execution_contract "
                            f"(--watch-timeout {watch_timeout}s). Стоп."
                        )
                        return 1
                    found = _wait_for_file(
                        contract_path,
                        timeout=watch_timeout,
                        label=f"execution_contract.md ({pkg})",
                        human_hint=_human_hint_execution_contract_wait(
                            pkg, agent, watch_mode=watch_mode
                        ),
                        ready_check=lambda pkg=pkg: _execution_contract_ready_for_post_agent(pkg),
                    )
                if not found:
                    print("❌ [LOOP] Контракт не появился за отведённое время. Стоп.")
                    return 1
                # Контракт появился → запускаем --post-agent
                post_cmd = _extend_post_agent_cmd(
                    (
                        f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                        f"--post-agent --package {pkg} --agent {agent} --budget-profile strict"
                    ),
                    post_agent_no_dod_cache=post_agent_no_dod_cache,
                )
                print(f"\n▶ [LOOP] post-agent: {post_cmd}\n")
                rc = subprocess.run(post_cmd, shell=True, cwd=str(ROOT)).returncode
                if _post_agent_chat_api_handoff(rc):
                    _print_loop_handoff_pause(
                        step,
                        pkg,
                        trigger_rc=rc_trig,
                        contract_found=found,
                        post_agent_rc=rc,
                    )
                    return 0
                if rc not in (0, _EXIT_NON_STOP_CONTINUE):
                    print(f"❌ [LOOP] --post-agent rc={rc}. Стоп.")
                    return rc
                _print_loop_summary(
                    step,
                    pkg,
                    trigger_rc=rc_trig,
                    contract_found=found,
                    post_agent_rc=rc,
                )
                package_id = None  # re-route: autodetect следующего пакета
                continue
            else:
                # --watch-contract не задан: показываем инструкцию и выходим
                print("ℹ  [LOOP] ready_orch без --watch-contract: выполните STEP 1 из orch-файла.")
                print("   Добавьте --watch-contract для генерации current_task.md и авто-ожидания.")
                print(_workflow_router_doc_footer())
                return 0

        # ── wip_running: execution_contract есть → next_cmd уже с --post-agent ─
        if current == STATE_WIP_RUNNING:
            if not cmd:
                print("❌ [LOOP] wip_running без next_cmd. Диагностика: pipeline_status.py")
                return 1
            cmd = _extend_post_agent_cmd(cmd, post_agent_no_dod_cache=post_agent_no_dod_cache)
            print(f"\n▶ [LOOP] {cmd}\n")
            rc = subprocess.run(cmd, shell=True, cwd=str(ROOT)).returncode
            if _post_agent_chat_api_handoff(rc):
                _print_loop_handoff_pause(
                    step,
                    state["package"],
                    trigger_rc=None,
                    contract_found=True,
                    post_agent_rc=rc,
                )
                return 0
            if rc not in (0, _EXIT_NON_STOP_CONTINUE):
                print(f"❌ [LOOP] rc={rc}. Стоп.")
                return rc
            _print_loop_summary(
                step,
                state["package"],
                trigger_rc=None,
                contract_found=True,
                post_agent_rc=rc,
            )
            package_id = None
            continue

        # ── Fallback: выполним next_cmd если есть ────────────────────────────
        if cmd:
            cmd = _extend_post_agent_cmd(cmd, post_agent_no_dod_cache=post_agent_no_dod_cache)
            print(f"\n▶ [LOOP] {cmd}\n")
            rc = subprocess.run(cmd, shell=True, cwd=str(ROOT)).returncode
            if rc != 0:
                print(f"❌ [LOOP] rc={rc}. Стоп.")
                return rc
            package_id = state.get("package")
            continue

        print(f"⚠  [LOOP] Состояние {current!r} без next_cmd — нет автоматического шага. Стоп.")
        return 0

    print(f"⚠  [LOOP] Достигнут лимит итераций --loop-max={loop_max}. Стоп.")
    return 1


# ── Output ────────────────────────────────────────────────────────────────────

SEP = "═" * 55

def _print_state(state: dict, show_cmd: bool = True) -> None:
    pkg = state.get("package") or "—"
    status = state.get("status") or "—"
    work = state.get("work_state") or "—"
    last = state.get("last_artifact", "нет артефактов")
    orch = state.get("orch_file")

    print(SEP)
    print("  WORKFLOW STATE")
    print(SEP)
    print(f"  Пакет     : {pkg}")
    print(f"  Статус    : {status}")
    print(f"  Work state: {work}")
    if last:
        print(f"  Последний : {last}")
    if orch:
        print(f"  Orch file : {orch}")

    if state["warnings"]:
        print()
        print("  ПРЕДУПРЕЖДЕНИЯ")
        print("  " + "─" * 51)
        for w in state["warnings"]:
            print(f"  ⚠  {w}")

    if not show_cmd:
        print(SEP)
        return

    print()
    print("  СЛЕДУЮЩИЙ ШАГ")
    print("  " + "─" * 51)
    print(f"  {state['next_label']}")
    print()

    if state.get("next_cmd"):
        print(f"  {state['next_cmd']}")
    elif state.get("next_hint"):
        for line in state["next_hint"].splitlines():
            print(f"  {line}")

    print(SEP)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Smart Workflow Router — следующий шаг без матрицы решений"
    )
    parser.add_argument(
        "--agent", default="cursor_ai", choices=VALID_AGENTS,
        help="Целевой агент (default: cursor_ai)"
    )
    parser.add_argument(
        "--package", default=None,
        help="Явно указать PACKAGE_ID (иначе автовыбор из реестра)"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Показать только статус, без команды"
    )
    parser.add_argument(
        "--exec", action="store_true",
        help="Выполнить следующую команду сразу (только если next_cmd существует)"
    )
    parser.add_argument(
        "--skip-review", dest="skip_review", action="store_true",
        help=(
            "Пропустить ревью контракта: в состоянии needs_plan инструкция агенту "
            "включает авто-вызов workflow.py --exec после Phase 7; "
            "в состоянии ready_fresh действует как --exec"
        )
    )
    parser.add_argument(
        "--loop", action="store_true",
        help=(
            "Conductor mode: после каждого шага пересчитывать состояние и продолжать "
            "до no_package, ошибки или --loop-max итераций"
        )
    )
    parser.add_argument(
        "--loop-max", dest="loop_max", type=int, default=20,
        help="Максимальное число итераций в --loop режиме (default: 20)"
    )
    parser.add_argument(
        "--watch-contract", dest="watch_contract", action="store_true",
        help=(
            "В состоянии ready_orch ждать появления execution_contract.md, "
            "затем автоматически запустить --post-agent (требует --loop)"
        )
    )
    parser.add_argument(
        "--watch-timeout", dest="watch_timeout", type=int, default=3600,
        help=(
            "Таймаут ожидания в секундах для --watch-contract и needs_plan "
            "(default: 3600 = 1 час)"
        )
    )
    parser.add_argument(
        "--trigger-cmd", dest="trigger_cmd", default=None,
        help=(
            "Команда автозапуска агента по doc/current_task.md (только с --loop и "
            "--watch-contract). Пример: "
            'npx tsx scripts/cursor_agent_trigger.ts; экспериментально: npx tsx scripts/deepseek_agent_trigger.ts '
            "(Chat API handoff-only) — передаётся "
            "WORKFLOW_CURRENT_TASK_PATH; provider API key из env. "
            "Без флага — прежний PAUSE для execution_auto / ручная работа в ready_orch."
        ),
    )
    parser.add_argument(
        "--post-agent-no-dod-cache",
        dest="post_agent_no_dod_cache",
        action="store_true",
        help=(
            "Только с --loop: добавить --no-dod-cache ко всем вызовам "
            "run_autonomous.py --post-agent внутри кондуктора (DoD без dod_cache.json)."
        ),
    )
    parser.add_argument(
        "--json", dest="as_json", action="store_true",
        help="Вывод в JSON"
    )
    args = parser.parse_args()

    if args.trigger_cmd and not (args.loop and args.watch_contract):
        print(
            "❌ --trigger-cmd требует одновременных флагов --loop и --watch-contract. "
            "Иначе команда триггера не будет частью контролируемого цикла."
        )
        return 2

    trigger_pair_error = _validate_trigger_agent_pair(args.trigger_cmd, args.agent)
    if trigger_pair_error:
        print(f"❌ {trigger_pair_error}")
        return 2

    if args.post_agent_no_dod_cache and not args.loop:
        print(
            "❌ --post-agent-no-dod-cache имеет смысл только вместе с --loop "
            "(флаг добавляет --no-dod-cache к вызовам --post-agent внутри цикла)."
        )
        return 2

    # ── Conductor loop mode ───────────────────────────────────────────────────
    if args.loop:
        return _run_loop(
            args.package,
            args.agent,
            skip_review=args.skip_review,
            watch_contract=args.watch_contract,
            watch_timeout=args.watch_timeout,
            loop_max=args.loop_max,
            trigger_cmd=args.trigger_cmd,
            post_agent_no_dod_cache=args.post_agent_no_dod_cache,
        )

    # ── Single-shot mode (прежнее поведение) ─────────────────────────────────
    package_id, _source = _find_active_package(args.package)

    state = resolve_state(package_id, args.agent, skip_review=args.skip_review)

    if args.as_json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    _print_state(state, show_cmd=not args.status)

    # --skip-review в ready_fresh автоматически выполняет next_cmd (как --exec)
    exec_now = args.exec or (args.skip_review and state.get("state") == STATE_READY_FRESH)

    if exec_now:
        cmd = state.get("next_cmd")
        if not cmd:
            print("\n⚠  --exec: нет автоматической команды для этого состояния.")
            print("   Следуй инструкции в 'СЛЕДУЮЩИЙ ШАГ' вручную.")
            return 1
        print(f"\n▶ Выполняю: {cmd}\n")
        result = subprocess.run(cmd, shell=True, cwd=str(ROOT))
        return result.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
