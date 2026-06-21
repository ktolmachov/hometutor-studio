#!/usr/bin/env python3
"""
run_autonomous.py — Zero-Click Delivery Pipeline

Следующий качественный прорыв автоматизации:
1. Вычисляет сложность пакета (через start_workflow.py).
2. Генерирует готовый промпт.
3. Напрямую спавнит CLI агента (claude-code) ИЛИ создает готовый файл задачи для GUI агентов (Cursor).
4. Запускает Test-Driven Loop: после закрытия агента автоматически прогоняет DoD.
   Если DoD упали — генерирует Resume-промпт и запускает агента заново (для CLI).

Перед автоматическим close_package можно выставить (см. .env.example):
  HOME_RAG_TEAM_ARTIFACTS_STRICT / HOME_RAG_SKIP_TEAM_ARTIFACTS_GATE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _perf_timer import PhaseTimer, cleanup_old_logs
from start_workflow import load_state, decide_next_step
from prompt_utils import (
    AUTONOMOUS_AGENT_CHOICES,
    GUI_TASK_AGENTS,
    ROOT,
    budget_profile_choices,
    closure_mode_src_from_git_paths,
    detect_closure_mode as _shared_detect_closure_mode,
    format_closure_mode_upgrade_notice,
    resolve_closure_mode as _shared_resolve_closure_mode,
    ensure_utf8_stdio,
    extract_dod_commands,
    extract_list_items,
    get_budget_profile,
    resolve_agent_adapter_name,
    validate_verification_only_evidence,
    verification_only_policy_guidance,
    write_task_file_for_cursor,
)
from close_package import run_close_package_impl, ClosePackageArgs
from lint_tasklist import lint as _lint_tasklist
from auto_promote_next_wave_package import find_next_candidate, _update_registry_status as _promote_update_registry
from agent_sandbox import SandboxViolationError, safe_run, safe_run_shell
from pipeline_events import (
    cleanup_stale_pid_registrations,
    emit,
    get_or_create_run_id,
    write_pid_registry,
    write_run_result,
)
from pipeline_lock import PipelineLockError, file_lock, package_run_conflict
from pipeline_state import bootstrap as _pipeline_bootstrap, finalize_for_exit as _pipeline_finalize_for_exit
from proof_bundle import build as _build_proof_bundle
from quality_gates import blocking_results as _blocking_quality_gates
from quality_gates import run_all as _run_quality_gates
from nonstop_wave_policy import ensure_chain_started_at as _ensure_non_stop_started_at
from nonstop_wave_policy import evaluate as _evaluate_non_stop_policy
from nonstop_wave_policy import load_policy as _load_non_stop_policy

# BUG-2 fix: ensure_utf8_stdio() вызывается в __main__ guard (не на уровне модуля),
# чтобы не перехватывать stderr при импорте, py_compile или --help.

PYTHON_EXE = sys.executable or "python"
DISPLAY_PYTHON = r".\.venv\Scripts\python.exe"
TASK_FILE  = ROOT / "doc" / "current_task.md"
TASK_LOCK_FILE = ROOT / "doc" / "current_task.md.lock"
SUMMARIZE_COST_LOGS = ROOT / "scripts" / "summarize_cost_logs.py"
PRINT_EPOCH_DEMO_PROMPTS = ROOT / "scripts" / "print_epoch_demo_agent_prompts.py"

# Exit contract (mirror doc/team_workflow/run_autonomous_prompt.md).
EXIT_SUCCESS = 0
EXIT_NON_STOP_CONTINUE = 10  # post-agent: success, same-session continuation (audit / next task)
# post-agent: execution_contract — DeepSeek/chat bridge BLOCKED (no repo); workflow.py stops looping
EXIT_POST_AGENT_CHAT_API_HANDOFF = 11
EXIT_REGISTRY_OR_SSO_GATE = 2  # registry missing package, roadmap quality gates, derived tasklist/sync
EXIT_CLI_OR_CONTEXT_POLICY = 8  # CLI misuse, incompatible flags, non-stop policy args, LLM context gate
EXIT_LOCK_CONFLICT = 9  # package-run lock / current_task.md lock

_TEAM_ARTIFACTS_SKIP_ENV = "HOME_RAG_SKIP_TEAM_ARTIFACTS_GATE"
_TEAM_ARTIFACTS_STRICT_ENV = "HOME_RAG_TEAM_ARTIFACTS_STRICT"


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def close_package_team_artifact_kwargs_from_env() -> dict[str, bool]:
    """Flags forwarded into ClosePackageArgs for autonomous closes."""
    return {
        "skip_team_artifacts_check": _env_truthy(_TEAM_ARTIFACTS_SKIP_ENV),
        "team_artifacts_strict": _env_truthy(_TEAM_ARTIFACTS_STRICT_ENV),
    }


# Минимальная длина строки, которая выглядит как markdown-промпт
_PROMPT_HINT_RE = re.compile(r"(python|pytest|npm|claude|#|##|###|\*\*|---)", re.IGNORECASE)


_TIMER = PhaseTimer()
_PYTEST_XDIST_AVAILABLE: bool | None = None


def _package_id_from_argv() -> str | None:
    argv = sys.argv
    for i, tok in enumerate(argv):
        if tok in ("--package", "-p") and i + 1 < len(argv):
            return argv[i + 1]
        if tok.startswith("--package="):
            return tok.split("=", 1)[1]
    return None


def _initial_pipeline_phase(args: argparse.Namespace) -> str:
    if args.post_agent:
        return "post_agent"
    if args.smoke:
        return "planning"
    return "execution"


def _budget_flag(profile: str) -> str:
    return f" --budget-profile {profile}" if profile else ""


_IN_PROCESS_DEPTH_ENV = "HOME_RAG_IN_PROCESS_DEPTH"


def _run_autonomous_in_process(cli_args: list[str]) -> int:
    """Invoke this script's CLI logic in-process for non-stop chaining.

    WARNING: Must NOT be called from post_agent() — that path is recursive
    across wave packages and grows the call stack unboundedly.
    Use subprocess.run([PYTHON_EXE, __file__, ...]) there instead.

    Guard: raises RuntimeError on any recursive in-process invocation so
    the bug is caught immediately rather than silently OOM-ing.
    """
    depth = int(os.environ.get(_IN_PROCESS_DEPTH_ENV, "0"))
    if depth >= 1:
        raise RuntimeError(
            "_run_autonomous_in_process called recursively (depth=%d). "
            "Use subprocess.run([PYTHON_EXE, __file__, ...]) for chain calls "
            "from post_agent to avoid unbounded stack growth." % depth
        )
    os.environ[_IN_PROCESS_DEPTH_ENV] = str(depth + 1)
    prev_argv = list(sys.argv)
    try:
        sys.argv = ["run_autonomous.py", *cli_args]
        try:
            return _main_impl()
        except SystemExit as exc:
            code = exc.code
            return int(code) if isinstance(code, int) else 1
    finally:
        sys.argv = prev_argv
        os.environ[_IN_PROCESS_DEPTH_ENV] = str(depth)



@contextmanager
def _current_task_lock(*, ttl_seconds: int = 30 * 60):
    """Best-effort cross-process lock around writes to doc/current_task.md."""
    try:
        with file_lock(TASK_LOCK_FILE, ttl_seconds=ttl_seconds):
            yield
    except PipelineLockError as exc:
        raise RuntimeError(
            f"current_task.md lock is held by another process. {exc}. "
            "Stop the other run or remove doc/current_task.md.lock if it's stale."
        ) from exc


def _contract_allows_pytest_parallel(contract: dict) -> bool:
    text = "\n".join(str(v) for v in contract.values()).lower()
    markers = ("allow_pytest_parallel", "pytest_parallel", "parallel pytest")
    return any(m in text for m in markers)


def _has_pytest_xdist() -> bool:
    global _PYTEST_XDIST_AVAILABLE
    if _PYTEST_XDIST_AVAILABLE is not None:
        return _PYTEST_XDIST_AVAILABLE
    try:
        proc = subprocess.run(
            [PYTHON_EXE, "-c", "import xdist"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        _PYTEST_XDIST_AVAILABLE = proc.returncode == 0
    except OSError:
        _PYTEST_XDIST_AVAILABLE = False
    return _PYTEST_XDIST_AVAILABLE


def _inject_pytest_parallel_flag(cmd: str, contract: dict) -> str:
    """Add `-n auto` to pytest commands when contract allows and xdist exists."""
    if not _contract_allows_pytest_parallel(contract):
        return cmd
    if not _has_pytest_xdist():
        return cmd
    if "-n " in cmd or "--numprocesses" in cmd:
        return cmd
    return re.sub(r"\bpytest\b", "pytest -n auto", cmd, count=1)


def _self_close_footer_execute(
    package_id: str,
    budget_profile: str,
    next_agent: str = "cursor_ai",
    non_stop: bool = False,
    *,
    non_stop_max_next_tasks: int = 50,
    non_stop_chain_step: int = 0,
) -> str:
    budget_flag = _budget_flag(budget_profile)
    non_stop_flag = (
        " --non-stop"
        f" --non-stop-max-next-tasks {non_stop_max_next_tasks}"
        f" --non-stop-chain-step {non_stop_chain_step}"
        if non_stop
        else ""
    )
    step_b_command = (
        f'Invoke-LoggedScript "{DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}{budget_flag}{non_stop_flag}" '
        f"-AllowedExitCodes @(0,1,{EXIT_NON_STOP_CONTINUE}) "
        '-AllowedNonZeroPatterns @("Auto-promoting next package", "Now empty and no ready wave packages found", "No active registry package. Run plan-next when ready.")'
        if non_stop else
        f'Invoke-LoggedScript "{DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}{budget_flag}{non_stop_flag}"'
    )
    if next_agent == "kilo":
        return f"""\

---

## MANDATORY FINAL STEP - run AFTER all DoD tests pass

Use your Shell tool to execute these commands in this Kilo session:

```bash
# Logging (PowerShell): command, params, output, exit code
$logDir = "logs/{package_id}"
New-Item -ItemType Directory -Force $logDir | Out-Null
$logFile = "$logDir/script_runs.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom
$env:PYTHONIOENCODING = "utf-8:replace"
try {{ chcp 65001 | Out-Null }} catch {{ }}
function Invoke-LoggedScript {{
  param([string]$Command)
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $logFile -Value "[$ts] CMD: $Command"
  $output = Invoke-Expression $Command 2>&1 | Tee-Object -FilePath $logFile -Append
  $rc = $LASTEXITCODE
  $tsEnd = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $logFile -Value "[$tsEnd] EXIT: $rc"
  if ($rc -ne 0) {{ throw "Command failed (exit=$rc): $Command" }}
}}

# STEP A - Save execution proof (REQUIRED before --post-agent will allow closure)
# Update archive/team_artifacts/{package_id}/execution_contract.md with your findings:
#   - What product files were changed (app/, tests/, src/)
#   - Why the implementation is correct
#   - Confirmation that all DoD branches are covered
#   - If no product files changed, this is verification-only. ALSO add:
#       Pre-existing delivery evidence:
#       - commit: <concrete 7-40 char sha that changed at least one referenced path>
#       - files: <existing repo paths that already delivered the capability>
#     Vague phrases like "pre-existing in current branch history" are invalid.

# STEP B - Verify DoD, close package, update tasklist/backlog/changelog
Invoke-LoggedScript "{DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}{budget_flag}"
# Optional strict gate for recent LLM context overflows:
# Invoke-LoggedScript "{DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}{budget_flag} --fail-on-context-errors"
```

After Step B succeeds, STOP this Kilo session.
Start a fresh Kilo session before any next-task or planning work.
Do not continue with backlog/history/planning docs in this same session.
"""
    _non_stop_step_c = (
        f"# STEP C — Generate next task AND immediately execute it (NON-STOP MODE)\n"
        f"Invoke-LoggedScript \"{DISPLAY_PYTHON} scripts/run_autonomous.py --agent {next_agent}{budget_flag}{non_stop_flag}\"\n"
        f"# ⚡ After Step C: read doc/current_task.md and execute it NOW in this session.\n"
        f"# Do NOT stop, do NOT ask for confirmation — continue immediately."
        if non_stop else
        f"# STEP C — Pre-generate the next task so the pipeline keeps flowing\n"
        f"Invoke-LoggedScript \"{DISPLAY_PYTHON} scripts/run_autonomous.py --agent {next_agent}{budget_flag}\""
    )
    _non_stop_closing = (
        "\n**NON-STOP MODE:** After Step C, do NOT stop — read `doc/current_task.md` and execute it\n"
        "immediately in this same session. **`--post-agent` exit semantics:** **`10`** = continue the audit / "
        "next-task chain in this session; **`0`** = stop (non-stop limit reached, finisher workflow, "
        "or no continuation). Non-zero exits other than tolerated Step-B patterns remain failures."
        if non_stop else
        "\n**Do not skip any step.** `--post-agent` (Step B) will EXIT 3 and block closure if\n"
        f"`archive/team_artifacts/{package_id}/execution_contract.md` does not exist.\n"
        "If DoD fails, fix the tests first, then re-run Steps B and C."
    )
    return f"""\

---

## MANDATORY FINAL STEP — run AFTER all DoD tests pass

Use your Shell tool to execute these commands **in this same session**:

```bash
# Logging (PowerShell): command, params, output, exit code
$logDir = "logs/{package_id}"
New-Item -ItemType Directory -Force $logDir | Out-Null
$logFile = "$logDir/script_runs.log"
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom
$env:PYTHONIOENCODING = "utf-8:replace"
try {{ chcp 65001 | Out-Null }} catch {{ }}
function Invoke-LoggedScript {{
  param(
    [string]$Command,
    [int[]]$AllowedExitCodes = @(0),
    [string[]]$AllowedNonZeroPatterns = @()
  )
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $logFile -Value "[$ts] CMD: $Command"
  $output = Invoke-Expression $Command 2>&1 | Tee-Object -FilePath $logFile -Append
  $rc = $LASTEXITCODE
  $tsEnd = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  Add-Content -Path $logFile -Value "[$tsEnd] EXIT: $rc"
  if ($AllowedExitCodes -notcontains $rc) {{ throw "Command failed (exit=$rc): $Command" }}
  if ($rc -ne 0) {{
    $text = ($output | Out-String)
    $matched = $false
    foreach ($pattern in $AllowedNonZeroPatterns) {{
      if ($text -like "*$pattern*") {{
        $matched = $true
        break
      }}
    }}
    if (-not $matched) {{ throw "Command failed (exit=$rc) without safe non-stop marker: $Command" }}
  }}
}}

# STEP A — Save execution proof (REQUIRED before --post-agent will allow closure)
# Update archive/team_artifacts/{package_id}/execution_contract.md with your findings:
#   - What product files were changed (app/, tests/, src/)
#   - Why the implementation is correct
#   - Confirmation that all DoD branches are covered
#   - If no product files changed, this is verification-only. ALSO add:
#       Pre-existing delivery evidence:
#       - commit: <concrete 7-40 char sha that changed at least one referenced path>
#       - files: <existing repo paths that already delivered the capability>
#     Vague phrases like "pre-existing in current branch history" are invalid.

# STEP B — Verify DoD, close package, update tasklist/backlog/changelog
{step_b_command}
# Optional strict gate for recent LLM context overflows:
# Invoke-LoggedScript "{DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}{budget_flag}{non_stop_flag} --fail-on-context-errors"

{_non_stop_step_c}
```
{_non_stop_closing}
"""


def _self_close_footer_plan(
    budget_profile: str,
    next_agent: str = "cursor_ai",
    non_stop: bool = False,
    *,
    non_stop_max_next_tasks: int = 5,
    non_stop_chain_step: int = 0,
) -> str:
    budget_flag = _budget_flag(budget_profile)
    non_stop_flag = (
        " --non-stop"
        f" --non-stop-max-next-tasks {non_stop_max_next_tasks}"
        f" --non-stop-chain-step {non_stop_chain_step}"
        if non_stop
        else ""
    )
    plan_chain_stop_rule = (
        "- Only stop when the execution package is CLOSED (`--post-agent` exit **`0`** = stop continuation, "
        "**`10`** = keep going in non-stop). Rely on the numeric exit code, not unrelated stdout substring matches."
        if non_stop
        else "- Only stop when the execution package is CLOSED (`--post-agent` exit **0**)."
    )
    if next_agent == "kilo":
        return f"""\

---

## MANDATORY CHAIN - run AFTER writing the contract to backlog_registry.yaml and syncing tasklist.md

### Step 1 - trigger the pipeline

```bash
{DISPLAY_PYTHON} scripts/run_autonomous.py --agent {next_agent}{budget_flag}
```

### Step 2 - STOP THIS SESSION

The command above writes a new execution task to `doc/current_task.md`.
For Kilo, do not continue in this same session.

Start a fresh Kilo session and follow only this pointer:
- Read only `doc/current_task.md`
- Then read only the single file explicitly pointed to by that task
- Do not open backlog/history/workflow docs unless the task explicitly names one file
- If blocked or the read-set starts expanding, stop and restart from the pointer
"""
    return f"""\

---

## MANDATORY CHAIN — run AFTER writing the contract to backlog_registry.yaml and syncing tasklist.md

### Step 1 — trigger the pipeline

```bash
{DISPLAY_PYTHON} scripts/run_autonomous.py --agent {next_agent}{budget_flag}{non_stop_flag}
```

### Step 2 — ⚠ DO NOT STOP HERE ⚠

The command above writes a new **execution task** to `doc/current_task.md`.
**You MUST immediately read and execute that new task in this same session.**

- This is NOT optional. Do NOT say "task complete" or "pipeline done" after Step 1.
- Do NOT offer to "execute it in the next step" — execute it NOW.
- The new task contains its own MANDATORY FINAL STEP — complete that too.
{plan_chain_stop_rule}
- If this is a GUI agent session, execute `doc/current_task.md` in a fresh session with minimal history.
- Do NOT paste old logs, prior prompts, or long chat history into the new session.

---

## REQUIRED: Canonical contract format (parse_contract must read this)

The package entry in `doc/backlog_registry.yaml` must render a tasklist contract
block with this exact structure so the pipeline can parse DoD commands and user
story IDs automatically.

```markdown
### <package-id> Contract

- **CJM:** #N <stage name>
- **User story:** US-X.Y — <one-line description>
- **DoD commands:** `{DISPLAY_PYTHON} -m pytest tests/test_foo.py -v; {DISPLAY_PYTHON} -m pytest tests/test_bar.py -v`
- **Outcomes:**
  - <outcome 1>
  - <outcome 2>
- **Write-set max:** <number> files
```

Key rules:
- `- **DoD commands:**` — bullet key with colon, backtick-wrapped pytest commands separated by `;`
- `- **User story:**` — must start with `US-` so close_package.py can update the US files
- All keys must be **bullet lines** (`- **Key:** value`), not standalone bold headings (`**Key**`)
- The block must start with `### <package-id> Contract` (exact spacing)
- If a DoD command intentionally validates a token/read-set registry bundle and
  `check_readset.py --profile strict ...` returns WARN for an otherwise valid
  read-set, put `--profile relaxed` in the contract immediately and archive the
  same command. Do not let strict/WARN create post-agent drift.

Deviation from this format causes silent failures: DoD skipped, US not closed, backlog not updated.
"""


def _command_option(command: list[str], name: str) -> str | None:
    try:
        index = command.index(name)
    except ValueError:
        return None
    value_index = index + 1
    if value_index >= len(command):
        return None
    return str(command[value_index])


def _read_existing_orchestration_prompt(
    command: list[str],
    stdout: str | None,
    stderr: str | None,
) -> str | None:
    """Use an existing orchestration prompt when the generator refuses overwrite."""
    if not any("generate_orchestration_prompt.py" in str(part) for part in command):
        return None

    combined = f"{stdout or ''}\n{stderr or ''}"
    if "already exists" not in combined or "orchestration_" not in combined:
        return None

    package_id = _command_option(command, "--package")
    agent = _command_option(command, "--agent") or "cursor_ai"
    if not package_id:
        return None

    path = ROOT / "archive" / "team_artifacts" / package_id / f"orchestration_{agent}.md"
    if not path.exists():
        return None

    print(
        "INFO Existing orchestration prompt found; using it to refresh "
        f"{TASK_FILE.relative_to(ROOT)}: {path.relative_to(ROOT)}"
    )
    return path.read_text(encoding="utf-8").strip()


def capture_generated_prompt(command: list[str], *, allow_empty: bool = False) -> str:
    """Выполняет скрипт генерации и извлекает только сам текст промпта."""
    print(f"⚙ Генерация промпта: {' '.join(command)}")
    res = safe_run(command, capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8")

    if res.returncode != 0:
        existing_orch = _read_existing_orchestration_prompt(command, res.stdout, res.stderr)
        if existing_orch is not None:
            return existing_orch
        # Для resume 0 — DoD success, закрытие. Если ошибка — выводим.
        if "⛔ STOP" in (res.stderr or ""):
            print(res.stderr)
            sys.exit(res.returncode)
        # Иные сбои генератора (нет контракта, preflight BLOCK, и т.д.): не
        # парсим stdout как промпт — иначе «Промпт не распознан» вместо причины.
        err = (res.stderr or "").strip()
        if err:
            print(err, file=sys.stderr)
        out = (res.stdout or "").strip()
        if out:
            print(f"stdout (excerpt): {out[:800]}", file=sys.stderr)
        sys.exit(2)

    if "DoD GREEN" in res.stdout and "No implementation needed" in res.stdout:
        return ""

    out = res.stdout
    parts = re.split(r"[=═]{70,}", out)
    if len(parts) >= 3:
        return parts[2].strip()

    # FIX BUG-4: не возвращаем слепо весь stdout — проверяем, что это похоже на промпт
    stripped = out.strip()
    if not stripped:
        if allow_empty:
            return ""
        print("❌ Генератор вернул пустой вывод. Прерывание.", file=sys.stderr)
        sys.exit(1)
    if "DoD GREEN" in stripped and "No implementation needed" in stripped:
        # Пакет уже готов, промпт не нужен
        return ""
    if not _PROMPT_HINT_RE.search(stripped):
        print(
            "❌ Промпт не распознан (нет признаков markdown/команд). Прерывание.",
            file=sys.stderr,
        )
        print(f"   Первые 300 символов stdout: {stripped[:300]}", file=sys.stderr)
        sys.exit(1)
    return stripped


def run_agent_headless(
    agent_type: str,
    prompt_text: str,
    package_id: str,
    *,
    budget_profile: str,
    non_stop: bool = False,
    non_stop_max_next_tasks: int = 50,
    non_stop_chain_step: int = 0,
) -> bool:
    """
    Запускает агента.
    Возвращает True если агент отработал синхронно (можно прогонять DoD).
    Возвращает False если агент асинхронный (Cursor GUI).
    """
    if not prompt_text.strip():
        print("✅ Промпт пуст (возможно все DoD уже пройдены).")
        return True

    agent_type = resolve_agent_adapter_name(agent_type)

    if agent_type == "claude_code":
        print(f"\n🚀 [AUTONOMOUS] Спавн claude-code для пакета {package_id}...")
        tmp_prompt = ROOT / ".claude_prompt.tmp.md"
        tmp_prompt.write_text(prompt_text, encoding="utf-8")
        try:
            # FIX ARCH-4: передаём промпт через файл, а не inline-строку,
            # чтобы избежать ограничения Windows cmd-line (~32k символов).
            # claude -p принимает "-" как stdin, либо можно использовать --file.
            # Используем stdin-pipe как самый совместимый вариант.
            with _TIMER.phase(f"agent_{agent_type}") as rc:
                result = safe_run(
                    ["claude", "-p", "-"],
                    input=prompt_text,
                    text=True,
                    encoding="utf-8",
                    cwd=str(ROOT),
                )
                rc["rc"] = result.returncode
            return True
        except FileNotFoundError:
            print("❌ CLI 'claude' не найден. (npm install -g @anthropic-ai/claude-code)")
            return False
        finally:
            if tmp_prompt.exists():
                tmp_prompt.unlink()

    elif agent_type in GUI_TASK_AGENTS:
        with _TIMER.phase(f"agent_{agent_type}"):
            print(f"\n🤖 [AUTONOMOUS] Подготовка артефакта задачи для Cursor/Codex ({package_id})...")
            # NOTE: .cursor/ is sandboxed in Cursor IDE — tools cannot read it.
            # Use doc/current_task.md instead so the agent can read it directly.
            if package_id and package_id != "unknown":
                footer = _self_close_footer_execute(
                    package_id,
                    budget_profile,
                    next_agent=agent_type,
                    non_stop=non_stop,
                    non_stop_max_next_tasks=non_stop_max_next_tasks,
                    non_stop_chain_step=non_stop_chain_step,
                )
            else:
                footer = _self_close_footer_plan(
                    budget_profile,
                    next_agent=agent_type,
                    non_stop=non_stop,
                    non_stop_max_next_tasks=non_stop_max_next_tasks,
                    non_stop_chain_step=non_stop_chain_step,
                )
            is_plan_next = not package_id or package_id == "unknown"
            if is_plan_next:
                budget_note = _budget_flag(budget_profile)
                # PLAN_NEXT: no package ID yet — banner must chain into execution, NOT create unknown/ dir
                if agent_type == "kilo":
                    no_pause_banner = (
                        "> **KILO PLAN_NEXT TASK - pointer-first, fresh-session workflow.**\n"
                        ">\n"
                        "> **Phase 1 (this task):** Write the contract to `doc/backlog_registry.yaml`, then regenerate `doc/tasklist.md`.\n"
                        f"> **Phase 2 (outside this session):** After running `run_autonomous.py --agent {agent_type}{budget_note}`,\n"
                        "> the pipeline generates a new execution task in `doc/current_task.md`.\n"
                        "> **Then STOP this session and start a fresh Kilo session.**\n"
                        "> In the fresh session, read only `doc/current_task.md` and only the single file it points to.\n"
                        "> Do not open backlog/history/workflow docs unless the task explicitly names one file.\n"
                        "> Successful closure ends with `--post-agent` exit **0** (stop chain / not non-stop) "
                        "or **10** (continue non-stop in the same session).\n\n"
                    )
                else:
                    no_pause_banner = (
                        "> **⚡ PLAN_NEXT TASK — two-phase, do NOT stop between phases.**\n"
                        ">\n"
                        "> **Phase 1 (this task):** Write the contract to `doc/backlog_registry.yaml`, then regenerate `doc/tasklist.md`.\n"
                        f"> **Phase 2 (mandatory chain):** After running `run_autonomous.py --agent {agent_type}{budget_note}`,\n"
                        "> the pipeline generates a new execution task in `doc/current_task.md`.\n"
                        "> **You MUST read and execute that task immediately. Do NOT stop after Phase 1.**\n"
                        "> **For GUI agents: open a fresh session and avoid carrying long prior history/logs.**\n"
                        "> End the session only after `--post-agent` returns **0** (stop) or **10** (non-stop continuation) "
                        "for the execution package.\n\n"
                    )
            else:
                exec_contract_path = f"archive/team_artifacts/{package_id}/execution_contract.md"
                if agent_type == "kilo":
                    no_pause_banner = (
                        "> **KILO EXECUTION TASK - pointer-only, bounded read-set.**\n"
                        "> **If this session has prior history/logs, restart in a fresh Kilo session before continuing.**\n"
                        ">\n"
                        "> **FIRST ACTION (before any code):** Create `{exec_contract}` now:\n"
                        ">\n"
                        "> ```bash\n"
                        "> # Windows\n"
                        "> New-Item -ItemType Directory -Force archive/team_artifacts/{pkg} | Out-Null\n"
                        "> Set-Content -Path archive/team_artifacts/{pkg}/execution_contract.md -Value 'STARTED' -Encoding utf8\n"
                        "> # Linux/Mac\n"
                        "> mkdir -p archive/team_artifacts/{pkg} && echo 'STARTED' > {exec_contract}\n"
                        "> ```\n"
                        ">\n"
                        "> Then work only from `doc/current_task.md` and the explicit write-set/read-set in this task.\n"
                        "> Do not open backlog/history/workflow docs unless this task explicitly names one file.\n"
                        "> If blocked or the read-set starts expanding, stop instead of broadening context.\n"
                        "> Update this file with your decisions/findings before running `--post-agent`.\n"
                        "> This is the proof of execution - without it, closure is blocked (exit 3).\n\n"
                    ).format(pkg=package_id, exec_contract=exec_contract_path)
                else:
                    no_pause_banner = (
                        "> **⚡ AUTONOMOUS TASK — execute completely in this session. Do NOT stop or ask the user.**\n"
                        "> **If this GUI session is bloated, restart in a fresh session before executing `doc/current_task.md`.**\n"
                        ">\n"
                        "> **FIRST ACTION (before any code):** Create `{exec_contract}` now:\n"
                        ">\n"
                        "> ```bash\n"
                        "> # Windows\n"
                        "> New-Item -ItemType Directory -Force archive/team_artifacts/{pkg} | Out-Null\n"
                        "> Set-Content -Path archive/team_artifacts/{pkg}/execution_contract.md -Value 'STARTED' -Encoding utf8\n"
                        "> # Linux/Mac\n"
                        "> mkdir -p archive/team_artifacts/{pkg} && echo 'STARTED' > {exec_contract}\n"
                        "> ```\n"
                        ">\n"
                        "> Update this file with your decisions/findings before running `--post-agent`.\n"
                        "> This is the **proof of execution** — without it, closure is blocked (exit 3).\n\n"
                    ).format(pkg=package_id, exec_contract=exec_contract_path)
            try:
                with _current_task_lock():
                    used_payload = write_task_file_for_cursor(
                        no_pause_banner=no_pause_banner,
                        body=prompt_text,
                        footer=footer,
                        task_path=TASK_FILE,
                        budget_profile=budget_profile,
                        force_payload=False,
                    )
            except RuntimeError as exc:
                print(
                    "\n[BLOCKED] Could not acquire doc/current_task.md lock.\n"
                    f"   Reason: {exc}\n"
                    "   Action: stop the other pipeline run, or remove "
                    "`doc/current_task.md.lock` if you're sure it's stale.\n",
                    file=sys.stderr,
                )
                raise SystemExit(EXIT_LOCK_CONFLICT)
            print("=" * 70)
            print(f"✅ Задача готова: {TASK_FILE.relative_to(ROOT)}")
            print("👉 Откройте Composer (Ctrl+I) и напишите:")
            print(f"   Выполни {TASK_FILE.relative_to(ROOT)}")
            print("=" * 70)
            return False
    else:
        print(f"⚠ Неизвестный агент: {agent_type}")
        return False


def run_dod_loop(package_id: str, contract: dict, *, use_dod_cache: bool = True) -> bool:
    """Прогоняет DoD команды. Возвращает True если все ок."""
    dod_raw = contract.get("DOD_COMMANDS", "")
    cmds = extract_dod_commands(dod_raw)
    if not cmds:
        # Distinguish: contract has no DoD field at all vs field exists but is empty
        if not dod_raw:
            print(
                "\n⚠ [RISK] DOD_COMMANDS not found in parsed contract for "
                f"'{package_id}'.\n"
                "   This usually means the registry-rendered tasklist contract uses a format\n"
                "   that parse_contract cannot read (e.g. missing '- **DoD commands:**' key).\n"
                "   Package will be closed WITHOUT automated DoD verification.\n"
                "   Audit trail will record 'DoD not run during closure'.\n"
                "   FIX: ensure the contract has a '- **DoD commands:** `pytest ...`' line\n"
                "   or a '**DoD commands**' section followed by bullet-list pytest calls.",
                file=sys.stderr,
            )
        else:
            print("\n✅ Нет DoD команд для проверки.")
        return True

    cache_key: str | None = None
    cache_file: Path | None = None
    if use_dod_cache:
        cache_key = _compute_dod_cache_key(contract, cmds)
        cache_file = ROOT / "archive" / "team_artifacts" / package_id / "dod_cache.json"
        cached = _load_dod_cache(cache_file)
        if cached.get("cache_key") == cache_key:
            if cached.get("result") == "pass":
                print(
                    f"\n✅ [CACHE HIT] DoD skipped for '{package_id}' — write-set and commands unchanged."
                )
                return True
            else:
                print(
                    f"\nℹ  [CACHE MISS] Previous DoD run failed. Re-running to check for fixes."
                )
    else:
        print("\nℹ  DoD cache disabled (--no-dod-cache) — running commands.")

    print(f"\n🔄 [AUTONOMOUS] Проверка DoD ({len(cmds)} команд)...")
    with _TIMER.phase("dod_total"):
        all_passed = True
        for i, cmd in enumerate(cmds):
            cmd = _inject_pytest_parallel_flag(cmd, contract)
            if _is_full_pytest_command(cmd) and not _allow_full_pytest_for_package(package_id, contract):
                print(
                    "\n[BLOCKED] Full pytest suite is forbidden in --post-agent for regular packages.\n"
                    f"   Package: {package_id}\n"
                    f"   Command: {cmd}\n"
                    "   Policy: run only targeted test bundles for changed areas.\n"
                    "   Exceptions: explicit full-regression marker in the contract or special epoch/regression package mode.\n"
                    "   Fix: replace `pytest tests/ ...` with the concrete bundle from AGENTS.md / agent_workflow_test_bundles.md.",
                    file=sys.stderr,
                )
                return False
            if _is_demo_validator_missing_scenario_id(cmd, package_id):
                match = _DEMO_SCENARIO_PACKAGE_RE.match(package_id)
                scenario_num = match.group("num") if match else "??"
                scenario_id = f"scenario_{scenario_num}"
                print(
                    "\n[BLOCKED] Demo validator command is missing --scenario-id.\n"
                    f"   Package: {package_id}\n"
                    f"   Command: {cmd}\n"
                    "   Policy: partial demo runs must validate only the target scenario.\n"
                    f"   Fix: append `--scenario-id {scenario_id}` to this DoD command,\n"
                    "        or regenerate the task/contract with updated run_autonomous.py.",
                    file=sys.stderr,
                )
                return False
            if _is_router_eval_command(cmd) and not os.getenv("OPENAI_API_KEY"):
                print(
                    "\n[BLOCKED] Router eval requires OPENAI_API_KEY for live orchestrator calls.\n"
                    f"   Package: {package_id}\n"
                    f"   Command: {cmd}\n"
                    "   Policy: post-agent cannot silently downgrade live eval DoD during closure.\n"
                    "   Fix: provide OPENAI_API_KEY or reopen planning and approve a different contract before execution.",
                    file=sys.stderr,
                )
                return False
            print(f"   $ {cmd}")
            with _TIMER.phase(f"dod_cmd_{i}") as rc:
                try:
                    res = safe_run_shell(cmd, cwd=str(ROOT))
                    rc["rc"] = res.returncode
                except SandboxViolationError as exc:
                    emit(
                        "SANDBOX_BLOCK",
                        {
                            "package_id": package_id,
                            "command": cmd[:500],
                            "reason": str(exc)[:500],
                        },
                        run_id=get_or_create_run_id(),
                    )
                    print(
                        "\n[BLOCKED] DoD command rejected by agent sandbox.\n"
                        f"   Command: {cmd}\n"
                        f"   Reason: {exc}",
                        file=sys.stderr,
                    )
                    rc["rc"] = 2
                    return False
            if res.returncode != 0:
                all_passed = False
                print(f"   ❌ Упало: {cmd}")
                break

        if all_passed:
            if use_dod_cache and cache_file is not None and cache_key is not None:
                _save_dod_cache(
                    cache_file,
                    {
                        "cache_key": cache_key,
                        "result": "pass",
                        "commands": cmds,
                    },
                )
            print("\n✅ Все DoD пройдены успешно!")
            return True
        if use_dod_cache and cache_file is not None and cache_key is not None:
            _save_dod_cache(
                cache_file,
                {
                    "cache_key": cache_key,
                    "result": "fail",
                    "commands": cmds,
                },
            )
        print("\n⚠ DoD упали.")
        return False


def _compute_dod_cache_key(contract: dict, cmds: list[str]) -> str:
    """Hash DoD commands + write-set file contents + shared test scaffolding + git state."""
    h = hashlib.sha256()
    normalized_cmds = [" ".join(cmd.strip().split()) for cmd in cmds]
    h.update(("\n".join(normalized_cmds)).encode("utf-8"))

    # Include git state to avoid false cache hits when tests/infrastructure changed
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        ).stdout.strip()
    except OSError:
        head = ""
    h.update(f"\nGIT_HEAD:{head}\n".encode("utf-8"))
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        ).stdout
    except OSError:
        status = ""
    h.update(f"GIT_STATUS_SHA:{hashlib.sha256(status.encode('utf-8')).hexdigest()}\n".encode("utf-8"))

    # Include git submodules state to invalidate cache on submodule updates
    try:
        submodule_status = subprocess.run(
            ["git", "submodule", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        ).stdout
        h.update(f"GIT_SUBMODULES:{hashlib.sha256(submodule_status.encode('utf-8')).hexdigest()}\n".encode("utf-8"))
    except OSError:
        pass

    # Include explicit un-tracked or ignored configs that affect tests
    for cfg in [".env", ".env.test", "pytest.ini"]:
        p = ROOT / cfg
        if p.exists():
            h.update(f"CONFIG:{cfg}:{hashlib.sha256(p.read_bytes()).hexdigest()}\n".encode("utf-8"))

    # Include pytest parallel capability (affects injected DoD commands)
    h.update(f"PYTEST_XDIST_AVAILABLE:{_has_pytest_xdist()}\n".encode("utf-8"))
    h.update(f"PYTEST_PARALLEL_ALLOWED:{_contract_allows_pytest_parallel(contract)}\n".encode("utf-8"))

    write_set = sorted(set(_parse_write_set(contract)))
    h.update(f"\nWRITE_SET_COUNT:{len(write_set)}\n".encode("utf-8"))
    for rel in write_set:
        path = ROOT / rel
        h.update(f"PATH:{rel}\n".encode("utf-8"))
        if not path.exists() or not path.is_file():
            h.update(b"MISSING\n")
            continue
        data = path.read_bytes()
        h.update(f"SIZE:{len(data)}\n".encode("utf-8"))
        h.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        h.update(b"\n")

    # Include conftest.py across the repository tests tree (shared fixtures)
    conftests = sorted((ROOT / "tests").rglob("conftest.py")) if (ROOT / "tests").exists() else []
    h.update(f"CONFTEST_COUNT:{len(conftests)}\n".encode("utf-8"))
    for p in conftests:
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        h.update(f"PATH:{rel}\n".encode("utf-8"))
        try:
            data = p.read_bytes()
        except OSError:
            h.update(b"READ_ERROR\n")
            continue
        h.update(f"SIZE:{len(data)}\n".encode("utf-8"))
        h.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _load_dod_cache(cache_file: Path) -> dict:
    if not cache_file.exists():
        return {}
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_dod_cache(cache_file: Path, payload: dict) -> None:
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"⚠ Could not write DoD cache: {exc}")


_SRC_EXT_RE = re.compile(r"`([^`]+\.(?:tsx|jsx|json|yaml|yml|md|txt|py|ts|js))`")
_SRC_PATH_RE = re.compile(
    r"(?:^|[\s|,])((?:app|tests|scripts|src|archive)/\S+\.(?:tsx|jsx|json|yaml|yml|md|txt|py|ts|js))"
)
# Block only directory-wide runs (`pytest tests`, `pytest tests/`, flags on bare tree),
# not targeted files like `pytest tests/test_foo.py` (the old `[\\/]\s*` branch false-positive'd those).
_FULL_PYTEST_RE = re.compile(
    r"(^|[\s;&|])(?:python(?:\.exe)?\s+-m\s+)?pytest\s+tests/?(?:\s|$)",
    re.IGNORECASE,
)
_ROUTER_EVAL_RE = re.compile(r"(^|[\s;&|])(?:python(?:\.exe)?\s+)?scripts/run_router_eval\.py(?:\s|$)", re.IGNORECASE)
_DEMO_SCENARIO_PACKAGE_RE = re.compile(r"epoch-demo-scenario-(?P<num>\d{2})-")
_DEMO_VALIDATE_CMD_RE = re.compile(r"scripts[\\/]+validate_demo_contract\.py", re.IGNORECASE)


def _is_full_pytest_command(cmd: str) -> bool:
    """Return True when the command runs the whole tests tree instead of a targeted bundle."""
    normalized = " ".join(cmd.strip().split())
    return bool(_FULL_PYTEST_RE.search(normalized))


def _is_router_eval_command(cmd: str) -> bool:
    normalized = " ".join(cmd.strip().split())
    return bool(_ROUTER_EVAL_RE.search(normalized))


def _is_demo_validator_missing_scenario_id(cmd: str, package_id: str) -> bool:
    """Detect stale demo validator command without --scenario-id for demo packages."""
    if not _DEMO_SCENARIO_PACKAGE_RE.match(package_id):
        return False
    if not _DEMO_VALIDATE_CMD_RE.search(cmd):
        return False
    normalized = " ".join(cmd.strip().split()).lower()
    return "--scenario-id" not in normalized


def _decode_text_bytes_best_effort(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _normalize_text_file_to_utf8(path: Path) -> None:
    if not path.exists():
        return
    raw = path.read_bytes()
    if not raw:
        return
    if b"\x00" not in raw and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return
    path.write_text(_decode_text_bytes_best_effort(raw), encoding="utf-8")


def _write_post_closure_audit_task(package_id: str, audit_task_content: str) -> Path:
    """Archive the post-closure audit task before updating current_task.md."""
    package_dir = ROOT / "archive" / "team_artifacts" / package_id
    package_dir.mkdir(parents=True, exist_ok=True)
    archive_path = package_dir / "post_closure_audit_task.md"
    archive_path.write_text(audit_task_content, encoding="utf-8")
    TASK_FILE.write_text(audit_task_content, encoding="utf-8")
    return archive_path


def _extract_dod_commands_from_exec_prompt_archive(text: str) -> list[str]:
    match = re.search(r"(?ms)^Run:\s*\n(?P<body>.*?)(?:^Return:|^After all DoD pass:|\Z)", text)
    if not match:
        return []
    return [line.strip() for line in match.group("body").splitlines() if line.strip()]


def _normalize_command_list(cmds: list[str]) -> list[str]:
    return [" ".join(cmd.strip().split()) for cmd in cmds if cmd.strip()]


def _inject_demo_scenario_id_into_prompt(prompt_text: str, package_id: str) -> str:
    """Patch stale demo validator commands in generated prompts/tasks.

    For epoch-demo-scenario-XX-* packages, ensures every validate_demo_contract.py
    command includes `--scenario-id scenario_XX`.
    """
    match = _DEMO_SCENARIO_PACKAGE_RE.match(package_id or "")
    if not match or not prompt_text.strip():
        return prompt_text

    scenario_num = match.group("num")
    scenario_id = f"scenario_{scenario_num}"
    lines = prompt_text.splitlines()
    changed = False
    patched_lines: list[str] = []
    for line in lines:
        if _DEMO_VALIDATE_CMD_RE.search(line) and "--scenario-id" not in line.lower():
            line = line.rstrip() + f" --scenario-id {scenario_id}"
            changed = True
        patched_lines.append(line)
    if changed:
        print(
            f"ℹ Auto-normalized demo validator command in prompt for {package_id}: "
            f"added --scenario-id {scenario_id}"
        )
    return "\n".join(patched_lines)


def _find_latest_exec_prompt_archive(package_id: str) -> Path | None:
    prompt_dir = ROOT / "archive" / "agent_prompts"
    if not prompt_dir.exists():
        return None
    candidates = sorted(
        prompt_dir.glob(f"{package_id.replace('-', '_')}_exec_prompt_quick_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _detect_dod_drift_from_exec_prompt(package_id: str, contract: dict) -> tuple[bool, str | None]:
    archived = _find_latest_exec_prompt_archive(package_id)
    if archived is None:
        return False, None
    archived_text = archived.read_text(encoding="utf-8")
    archived_cmds = _normalize_command_list(_extract_dod_commands_from_exec_prompt_archive(archived_text))
    current_cmds = _normalize_command_list(extract_dod_commands(contract.get("DOD_COMMANDS", "")))
    if not archived_cmds or not current_cmds or archived_cmds == current_cmds:
        return False, None
    reason = (
        f"archived={archived.relative_to(ROOT)} | "
        f"archived_dod={archived_cmds} | current_dod={current_cmds}"
    )
    return True, reason


def _allow_full_pytest_for_package(package_id: str, contract: dict) -> bool:
    """Allow full pytest only for explicit regression flows, not routine package closure."""
    if package_id.startswith("epoch-"):
        return True

    contract_text = "\n".join(str(value) for value in contract.values()).lower()
    markers = (
        "allow_full_pytest",
        "full regression",
        "full suite allowed",
        "epoch close",
        "large merge",
    )
    return any(marker in contract_text for marker in markers)


def _allow_verification_only_for_package(contract: dict) -> bool:
    """Require explicit opt-in marker before allowing verification-only closure."""
    contract_text = "\n".join(str(value) for value in contract.values()).lower()
    markers = (
        "allow_verification_only",
        "verification-only allowed",
        "verification only allowed",
        "pre-existing delivery allowed",
    )
    return any(marker in contract_text for marker in markers)


class _GitWorktreeSnapshot(NamedTuple):
    """Result of one `git diff HEAD --name-only` + `git status --porcelain` pair."""

    all_paths: tuple[str, ...]


_PRODUCT_PATH_ROOTS = ("app/", "tests/", "scripts/", "src/", "archive/")


def _resolve_closure_mode(
    package_id: str,
    contract: dict,
    *,
    precomputed_src_changed: set[str] | None = None,
    precomputed_evidence_valid: bool | None = None,
    exec_contract_text: str | None = None,
):
    """Delegate to prompt_utils.resolve_closure_mode (shared SSoT)."""
    return _shared_resolve_closure_mode(
        package_id,
        contract,
        ROOT,
        precomputed_src_changed=precomputed_src_changed,
        precomputed_evidence_valid=precomputed_evidence_valid,
        exec_contract_text=exec_contract_text,
    )


def _fetch_git_worktree_snapshot() -> _GitWorktreeSnapshot | None:
    """Run git once per post-agent pass; shared by append-diff and closure hard-gate."""
    try:
        res_diff = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
    except OSError:
        return None
    if res_diff.returncode != 0 or res_status.returncode != 0:
        return None
    ordered: list[str] = list(
        dict.fromkeys(
            line.strip() for line in res_diff.stdout.splitlines() if line.strip()
        )
    )
    for line in res_status.stdout.splitlines():
        if len(line) > 3:
            path = line[3:].strip()
            if path not in ordered:
                ordered.append(path)
    return _GitWorktreeSnapshot(all_paths=tuple(ordered))


def _product_paths_from_snapshot(snap: _GitWorktreeSnapshot) -> set[str]:
    return {
        p
        for p in snap.all_paths
        if any(p.startswith(root) for root in _PRODUCT_PATH_ROOTS)
    }


def _current_product_changed_files(
    *,
    snapshot: _GitWorktreeSnapshot | None = None,
) -> set[str] | None:
    """Return changed product files from working tree (staged+unstaged+untracked)."""
    if snapshot is not None:
        return _product_paths_from_snapshot(snapshot)
    snap = _fetch_git_worktree_snapshot()
    if snap is None:
        return None
    return _product_paths_from_snapshot(snap)


def _demo_wave_dod_commands(pkg_id: str, *, run_e2e_demo_all: bool = False) -> str | None:
    match = _DEMO_SCENARIO_PACKAGE_RE.match(pkg_id)
    if not match:
        return None
    scenario_num = match.group("num")
    scenario_id = f"scenario_{scenario_num}"
    run_name = (os.environ.get("DEMO_SHOT_RUN") or "").strip()
    if not run_name:
        # Keep deterministic screenshot folders for scenario packages.
        run_name = f"2026-01-{scenario_num}"
    e2e_cmd = (
        "npm run test:e2e:demo"
        if run_e2e_demo_all
        else f"npm run test:e2e:demo -- --grep '@demo Scenario {scenario_num}'"
    )
    return "; ".join(
        [
            "npm run demo:validate",
            (
                "powershell -NoProfile -Command "
                f"\"$env:DEMO_SHOT_RUN='{run_name}'; "
                f"{e2e_cmd}\""
            ),
            (
                f"{DISPLAY_PYTHON} scripts\\validate_demo_contract.py "
                f"--screenshots-dir doc\\screenshots\\{run_name} "
                "--require-screenshots --strict-captures --require-unique-shots "
                f"--scenario-id {scenario_id}"
            ),
            (
                f"{DISPLAY_PYTHON} scripts\\generate_demo_doc.py "
                f"--screenshots-dir doc\\screenshots\\{run_name} "
                "--output doc\\quickstart_demo.preview.md --no-final-sync"
            ),
        ]
    )


def _wave_package_dod_commands(pkg_id: str, *, run_e2e_demo_all: bool = False) -> str:
    demo_dod = _demo_wave_dod_commands(pkg_id, run_e2e_demo_all=run_e2e_demo_all)
    if demo_dod:
        return demo_dod
    return f"{DISPLAY_PYTHON} scripts/check_backlog_drift.py"


def _parse_write_set(contract: dict) -> list[str]:
    """Extract source file paths mentioned anywhere in the contract dict.

    Handles:
    - Backtick-quoted paths in any field: `app/foo.py`
    - Bare paths after pipe separators in markdown tables: | app/foo.py |
    - TARGET_ARTIFACTS / WRITE_SET_MAX bullet values
    """
    # Concatenate all contract values — write-set paths can appear in TARGET_ARTIFACTS,
    # OUTCOMES, WRITE_SET_MAX, or even inline in the raw block (not always parsed as a field)
    all_text = "\n".join(str(v) for v in contract.values())

    found: list[str] = []
    # Pattern 1: backtick-wrapped paths with source extension
    for m in _SRC_EXT_RE.finditer(all_text):
        p = m.group(1)
        if "/" in p:
            found.append(p)
    # Pattern 2: bare paths starting with known source roots
    for m in _SRC_PATH_RE.finditer(all_text):
        found.append(m.group(1))

    return list(dict.fromkeys(found))  # deduplicate, preserve order


def _detect_closure_mode(
    package_id: str,
    contract: dict,
    *,
    precomputed_src_changed: set[str] | None = None,
    precomputed_evidence_valid: bool | None = None,
) -> str:
    """Classify how this package was closed.

    Delegates to `prompt_utils.detect_closure_mode` (shared helper). See that
    function for the decision matrix. The stricter variant returns
    'verification_only' only when execution_contract.md passes the evidence
    validator; malformed evidence falls through to 'unknown' (which callers
    must block explicitly).
    """
    return _shared_detect_closure_mode(
        package_id,
        contract,
        ROOT,
        precomputed_src_changed=precomputed_src_changed,
        precomputed_evidence_valid=precomputed_evidence_valid,
    )


_CLOSURE_MODE_LABEL = {
    "execution":         "Code changes detected — execution confirmed",
    "verification_only": "No write-set changes — pre-existing implementation verified",
    "unknown":           "Could not determine whether code was written (check git log)",
}

_CLOSURE_MODE_ICON = {
    "execution":         "✅",
    "verification_only": "✅",
    "unknown":           "⚠",
}


def _append_verified_diff_to_exec_contract(
    exec_contract: "Path",
    package_id: str,
    *,
    snapshot: _GitWorktreeSnapshot | None = None,
) -> None:
    """Append a pipeline-verified 'Changed files' section to execution_contract.md.

    Uses one `git diff` + `git status` snapshot (pass `snapshot` from post_agent
    to avoid duplicate subprocess). If `snapshot` is None, runs git here.
    Called before the hard gate check — so the diff is recorded even when the
    agent listed files inaccurately. If the file doesn't exist yet, this is a
    no-op (hard gate will block next).
    """
    if not exec_contract.exists():
        return

    try:
        if snapshot is None:
            snap = _fetch_git_worktree_snapshot()
            if snap is None:
                return
            changed = list(snap.all_paths)
        else:
            changed = list(snapshot.all_paths)

        product_changed = [p for p in changed if any(p.startswith(r) for r in _PRODUCT_PATH_ROOTS)]
        all_changed = changed  # full list for completeness

        section = (
            "\n\n---\n"
            "## Pipeline-verified changed files (auto-appended by --post-agent)\n\n"
            f"**Product files (app/, tests/, src/):** "
            + (", ".join(f"`{p}`" for p in product_changed) if product_changed else "_none_")
            + "\n\n"
            f"**All changed files (`git diff HEAD` + untracked):**\n"
        )
        if all_changed:
            section += "".join(f"- `{p}`\n" for p in all_changed)
        else:
            section += "_No uncommitted changes detected — implementation may have been pre-committed._\n"

        existing = exec_contract.read_bytes().decode("utf-8-sig", errors="replace")
        _MARKER = "## Pipeline-verified changed files"
        if _MARKER not in existing:
            exec_contract.write_text(existing.rstrip() + section, encoding="utf-8")

    except Exception as exc:
        # Non-blocking: the existence gate above already verified the file is present.
        # But emit an event so audit trail failures are visible in pipeline logs.
        print(f"  ⚠ Could not append verified diff to execution_contract.md: {exc}")
        try:
            emit(
                "AUDIT_APPEND_FAILED",
                {"package_id": package_id, "reason": str(exc)[:300]},
                run_id=get_or_create_run_id(),
            )
        except Exception:  # noqa: BLE001 — best-effort event, never block closure
            pass


_EXEC_CONTRACT_FRONTMATTER_RE = re.compile(
    r"^\ufeff?---\s*\r?\n.*?\r?\n---\s*\r?\n",
    re.DOTALL,
)
_PIPELINE_VERIFIED_DIFF_MARKER = "## Pipeline-verified changed files"
_DEEPSEEK_TRIGGER_GENERATED_BY_MARKER = "generated_by: deepseek_agent_trigger.ts"


def _strip_execution_contract_frontmatter(text: str) -> str:
    m = _EXEC_CONTRACT_FRONTMATTER_RE.match(text)
    if m:
        return text[m.end() :]
    return text


def _strip_pipeline_verified_diff_appendix(text: str) -> str:
    idx = text.find(_PIPELINE_VERIFIED_DIFF_MARKER)
    if idx != -1:
        return text[:idx].rstrip()
    return text.rstrip()


def _execution_contract_is_deepseek_chat_api_blocked(exec_text: str) -> bool:
    """True when DeepSeek REST trigger recorded BLOCKED (no local repo access).

    In that case post-agent must not attempt verification-only or unknown-mode closure:
    no delivery happened yet — hand off to an IDE/SDK agent.
    """
    if _DEEPSEEK_TRIGGER_GENERATED_BY_MARKER not in exec_text:
        return False
    body = _strip_pipeline_verified_diff_appendix(
        _strip_execution_contract_frontmatter(exec_text),
    ).strip()
    for line in body.splitlines():
        seg = line.strip()
        if seg:
            return seg.lower().startswith("blocked:")
    return False


def post_agent(
    package_id: str,
    agent: str = "cursor_ai",
    budget_profile: str = "strict",
    non_stop: bool = False,
    *,
    run_e2e_demo_all: bool = False,
    non_stop_max_next_tasks: int = 50,
    non_stop_chain_step: int = 0,
    use_dod_cache: bool = True,
    skip_sync_checks: bool = False,
) -> int:
    """    CLI exit codes — post-agent subset:
    0 = successful closure, stop chain (or non-stop limit); 10 = closure OK, continue non-stop;
    11 = chat-api handoff (DeepSeek BLOCKED contract — package not closed; workflow loop must stop);
    1 = DoD failure; 2 = registry/quality gate; 3–7 closure hard gates; (8/9 from wrappers: context/lock).

    Called after a GUI agent (Cursor/Codex) finishes its task.

    1. HARD GATE: blocks if execution_contract.md is absent (proof of execution).
    2. Detects closure mode (execution | verification_only | unknown).
    3. Runs DoD commands for the package.
    4. If all pass → closes the package with the detected mode recorded.
    5. Pre-generates the NEXT task into doc/current_task.md.

    Usage: .\\.venv\\Scripts\\python.exe scripts/run_autonomous.py --post-agent --package <id>
    """
    state = load_state(package_id)
    if not state.get("package"):
        print(f"❌ Package '{package_id}' not found in backlog_registry.yaml")
        return EXIT_REGISTRY_OR_SSO_GATE

    contract = state["contract"]
    run_id = get_or_create_run_id()

    gates = _run_quality_gates(
        package_id=package_id,
        run_id=run_id,
        root=ROOT,
        current_task_path=TASK_FILE,
        include_proof=False,
    )
    blockers = _blocking_quality_gates(gates)
    if blockers:
        gate = blockers[0]
        print(gate.followup_message or gate.reason, file=sys.stderr)
        return EXIT_REGISTRY_OR_SSO_GATE

    # ── HARD GATE: execution proof required ────────────────────────────────
    exec_contract = ROOT / "archive" / "team_artifacts" / package_id / "execution_contract.md"

    # Gate must come FIRST — before any attempt to read or append to the file.
    # _append_verified_diff_to_exec_contract silently returns when the file is absent,
    # so checking existence after it would never trigger correctly.
    if not exec_contract.exists():
        print(
            f"\n🚫 [BLOCKED] Cannot close '{package_id}' — execution phase was skipped.\n"
            f"\n   Missing: {exec_contract.relative_to(ROOT)}\n"
            f"\n   This file is created by executing the task in doc/current_task.md.\n"
            f"   The pipeline requires proof that the execution phase ran before allowing closure.\n"
            f"\n   ── REQUIRED ACTIONS ──────────────────────────────────────────────────\n"
            f"   1. Read doc/current_task.md\n"
            f"   2. Implement the task  (or verify existing code if implementation pre-exists)\n"
            f"   3. Write your findings to:\n"
            f"        {exec_contract.relative_to(ROOT)}\n"
            f"      (For verification-only: note that implementation pre-existed + tests passed)\n"
            f"   4. Re-run: {DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}\n"
            f"   ────────────────────────────────────────────────────────────────────────"
        )
        return 3

    _normalize_text_file_to_utf8(exec_contract)
    exec_contract_text = exec_contract.read_text(encoding="utf-8", errors="replace").strip()
    if exec_contract_text.upper() == "STARTED":
        print(
            f"\n🚫 [BLOCKED] Cannot close '{package_id}' — execution proof is only a STARTED marker.\n"
            f"\n   File: {exec_contract.relative_to(ROOT)}\n"
            "\n   The initial STARTED marker only proves the task began. Before --post-agent can close\n"
            "   the package, update execution_contract.md with actual execution evidence:\n"
            "   - changed product/test files (or strict verification-only evidence)\n"
            "   - implementation decisions/findings\n"
            "   - DoD command results\n"
            f"\n   Then re-run: {DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}"
        )
        return 3

    with _TIMER.phase("dod_drift_detect"):
        drifted, drift_reason = _detect_dod_drift_from_exec_prompt(package_id, contract)
    if drifted:
        print(
            "\n[BLOCKED] Package closure refused because DoD changed after the execution prompt was generated.\n"
            f"   {drift_reason}\n"
            "   Policy: post-agent cannot close a package after silent DoD weakening.\n"
            "   Fix: restore the original DoD or reopen planning with an explicit contract update.",
            file=sys.stderr,
        )
        return 4

    with _TIMER.phase("git_worktree_query"):
        git_snapshot = _fetch_git_worktree_snapshot()

    # Append a pipeline-verified git diff section so the audit record is accurate.
    # This runs AFTER the existence gate, so exec_contract is guaranteed to exist here.
    with _TIMER.phase("git_diff_append"):
        _append_verified_diff_to_exec_contract(
            exec_contract, package_id, snapshot=git_snapshot
        )

    # Один проход чтения execution_contract + validate; src из уже взятого git snapshot.
    exec_text = exec_contract.read_text(encoding="utf-8", errors="replace")
    if _execution_contract_is_deepseek_chat_api_blocked(exec_text):
        print(
            "\nℹ  [HANDOFF] execution_contract.md помечен как BLOCKED из DeepSeek Chat API "
            "(нет доступа к локальному репозиторию).\n"
            "   Пакет не закрывается. Выполните оркестрацию в агенте с доступом к файлам "
            "(Cursor SDK и т.п.), замените контракт на реальный execution proof и снова запустите:\n"
            f"   {DISPLAY_PYTHON} scripts/run_autonomous.py --post-agent --package {package_id}\n"
        )
        return EXIT_POST_AGENT_CHAT_API_HANDOFF

    evidence_ok, ev_reason = validate_verification_only_evidence(exec_text, ROOT)
    src_pre = (
        closure_mode_src_from_git_paths(git_snapshot.all_paths)
        if git_snapshot is not None
        else None
    )

    # ── Detect closure mode before DoD ─────────────────────────────────────
    with _TIMER.phase("closure_mode_detect"):
        resolution = _resolve_closure_mode(
            package_id,
            contract,
            precomputed_src_changed=src_pre,
            precomputed_evidence_valid=evidence_ok,
            exec_contract_text=exec_text,
        )
    mode = resolution.mode
    verification_policy_allowed = _allow_verification_only_for_package(contract)
    write_set_paths = set(_parse_write_set(contract))

    upgrade_notice = format_closure_mode_upgrade_notice(resolution, success_prefix=True)
    if upgrade_notice:
        print(upgrade_notice)

    icon = _CLOSURE_MODE_ICON[mode]
    label = _CLOSURE_MODE_LABEL[mode]
    print(f"\n{icon} Closure mode: [{mode}] — {label}")
    with _TIMER.phase("git_changed_files"):
        if git_snapshot is not None:
            changed_paths = _product_paths_from_snapshot(git_snapshot)
        else:
            changed_paths = None
    if changed_paths is None:
        changed_paths = set(resolution.delivery_paths)
    else:
        changed_paths = changed_paths | set(resolution.delivery_paths)
    overlap = changed_paths & write_set_paths if write_set_paths else set()

    if mode == "execution" and not verification_policy_allowed:
        if not write_set_paths:
            print(
                "\n[BLOCKED] Execution closure requires concrete write-set paths in contract.\n"
                f"   Package: {package_id}\n"
                "   Policy: verification_only is forbidden by default for execution packages.\n"
                "   Fix: add explicit source paths (app/tests/scripts/src) to contract outcomes/write-set.",
                file=sys.stderr,
            )
            return 7
        if changed_paths is None:
            print(
                "\n[BLOCKED] Could not read git changed-files state for execution hard gate.\n"
                f"   Package: {package_id}\n"
                "   Fix: ensure git is available and rerun post-agent.",
                file=sys.stderr,
            )
            return 7
        if not overlap:
            print(
                "\n[BLOCKED] Execution hard gate failed: no overlap between write-set and changed files.\n"
                f"   Package: {package_id}\n"
                f"   Write-set: {sorted(write_set_paths)}\n"
                f"   Changed product files: {sorted(changed_paths)}\n"
                "   Policy: execution packages must change at least one write-set path.\n"
                "   If this is intentional verification-only, add explicit policy marker "
                "`allow_verification_only` in contract.",
                file=sys.stderr,
            )
            return 7
    if mode == "verification_only":
        blockers: list[str] = []
        if not evidence_ok:
            blockers.append(ev_reason or "verification-only evidence is incomplete")
        write_set_paths = list(write_set_paths)
        if not write_set_paths:
            blockers.append(
                "contract write-set has no concrete source paths (app/tests/scripts/src); "
                "verification-only closure requires explicit target paths"
            )
        if not verification_policy_allowed:
            blockers.append(
                "contract does not explicitly allow verification-only closure "
                "(add allow_verification_only marker)"
            )
        if blockers:
            print(
                "\n[BLOCKED] Verification-only closure refused because the execution proof lacks\n"
                "the required pre-existing delivery evidence.\n"
                + "\n".join(f"   - {item}" for item in blockers)
                + "\n   To allow an intentional verification-only closure, update contract with:\n"
                "   - explicit marker: `allow_verification_only`\n"
                "   - concrete write-set paths (app/tests/scripts/src), e.g. in Outcomes:\n"
                "       - touchpoints: `app/foo.py`, `tests/test_foo.py`\n"
                "   - evidence block in execution_contract.md:\n"
                "       Pre-existing delivery evidence:\n"
                "       - commit: <sha>\n"
                "       - files: app/foo.py, tests/test_foo.py\n"
                "   Otherwise, make the package an execution closure with real write-set changes.",
                file=sys.stderr,
            )
            return 5
        print(
            "   ℹ  Implementation pre-existed. This is a legitimate verification-only closure.\n"
            "      execution_contract.md found — execution phase confirmed.\n"
        )
    elif mode == "unknown":
        print(
            "\n[BLOCKED] Package closure refused because the pipeline cannot confirm\n"
            "whether this was a real execution or a verification-only closure.\n"
            "   execution_contract.md exists, but no product source/test changes were detected\n"
            "   and the proof does not contain strict verification-only evidence.\n"
            "   Add concrete 'Pre-existing delivery evidence' with commit SHA and existing paths.\n"
            f"{verification_only_policy_guidance(indent='   ')}\n"
            "   Or make product/test changes in the package write-set.",
            file=sys.stderr,
        )
        return 6

    # ── DoD ────────────────────────────────────────────────────────────────
    passed = run_dod_loop(package_id, contract, use_dod_cache=use_dod_cache)
    if not passed:
        print(f"\n⚠ Fix failing tests, then re-run:")
        print(
            f"   {DISPLAY_PYTHON} scripts/run_autonomous.py "
            f"--post-agent --package {package_id}{_budget_flag(budget_profile)}"
        )
        print("   Optional strict LLM context gate:")
        print(
            f"   {DISPLAY_PYTHON} scripts/run_autonomous.py "
            f"--post-agent --package {package_id}{_budget_flag(budget_profile)} --fail-on-context-errors"
        )
        return 1

    # ── Close package (with detected mode) ─────────────────────────────────
    with _TIMER.phase("proof_bundle_build"):
        _build_proof_bundle(run_id, package_id)

    print(
        f"\n   Closing [{mode}]: {DISPLAY_PYTHON} scripts/close_package.py "
        f"--package {package_id} --closure-mode {mode} --skip-dod"
    )
    with _TIMER.phase("close_package") as cp_rc:
        close_args = ClosePackageArgs(
            package=package_id,
            skip_dod=True,
            closure_mode=mode,
            skip_sync_checks=skip_sync_checks,
            approve_close_without_dod=True,
            **close_package_team_artifact_kwargs_from_env(),
        )
        rc = run_close_package_impl(close_args)
        cp_rc["rc"] = rc
    if rc != 0:
        return rc

    # Persist incremented chain_step so the next --post-agent invocation reads
    # the correct value even when called with a stale argv value (BUG-05 fix).
    if non_stop:
        _run_id = get_or_create_run_id()
        from pipeline_state import update as _ps_update  # noqa: PLC0415
        _ps_update(_run_id, chain_step=non_stop_chain_step + 1)

    if non_stop and non_stop_chain_step >= non_stop_max_next_tasks:
        print(
            "\n🛑 [NON-STOP LIMIT] Max next-task auto-chain reached "
            f"({non_stop_chain_step}/{non_stop_max_next_tasks})."
        )
        print("   Stopping automatic transition to the next task.")
        return EXIT_SUCCESS

    # ── Wave auto-continue ───────────────────────────────────────────────────
    with _TIMER.phase("wave_continue"):
        wave_next = _wave_auto_continue(package_id, run_e2e_demo_all=run_e2e_demo_all)

    # Instead of running the next wave package immediately, we force the agent
    # to run the SSoT audit prompt for the package it just closed. The continuation
    # command is appended as the MANDATORY FINAL STEP of the audit task.
    next_cmd = ["--agent", agent]
    if wave_next:
        next_cmd.extend(["--package", wave_next])
    next_cmd.extend(["--budget-profile", budget_profile])
    if non_stop:
        next_cmd.extend(
            [
                "--non-stop",
                "--non-stop-max-next-tasks",
                str(non_stop_max_next_tasks),
                "--non-stop-chain-step",
                str(non_stop_chain_step + 1),
            ]
        )
    if not wave_next:
        next_cmd.append("--allow-empty-generator")

    today_str = date.today().isoformat()
    next_cmd_str = f"{DISPLAY_PYTHON} scripts/run_autonomous.py {' '.join(next_cmd)}"

    audit_task_content = f"""# TASK: Post-Closure SSoT Audit for {package_id}

Вы только что успешно закрыли пакет `{package_id}`. Теперь необходимо верифицировать консистентность индексов (SSoT).

## Шаг 1: Генерация промпта аудита
Прочитайте файл `doc/team_workflow/generate_audit_closed_packages_prompt.md` и выполните его инструкции (Phase A1-A4).
Используйте следующие входные параметры:
- `TARGET_AGENT`: {agent}
- `PERIOD`: {today_str}..{today_str}
- `PACKAGE`: {package_id}
- `SCOPE`: closed
- `DEPTH`: index_only

## Шаг 2: Выполнение аудита
Прочитайте и выполните сгенерированный промпт (он будет сохранён в `doc/team_workflow/`).
Выполните шаги A, B, C, D. (Тесты перепроходить не нужно, так как `DEPTH=index_only`).
Сохраните итоговый отчёт (Шаг D).

## MANDATORY FINAL STEP
После того как отчёт сохранён и все индексы проверены, возобновите конвейер (переход к следующей задаче) с помощью команды:

```bash
{next_cmd_str}
```
"""
    audit_archive_path = _write_post_closure_audit_task(package_id, audit_task_content)

    print(f"\n✅ Post-Closure Audit Task ready: {TASK_FILE.relative_to(ROOT)}")
    print(f"   Archived copy: {audit_archive_path.relative_to(ROOT)}")
    if non_stop:
        print("⚡ [NON-STOP] Read doc/current_task.md and execute the audit NOW in this session.")
        print("   Do NOT stop. Do NOT ask for confirmation. Continue immediately.")
        return EXIT_NON_STOP_CONTINUE

    print("👉 Open Composer (Ctrl+I) and type:")
    print(f"   Выполни {TASK_FILE.relative_to(ROOT)}")
    return EXIT_SUCCESS


def _wave_next_package_ready_contract_ok(item: dict) -> tuple[bool, list[str]]:
    """Mirror backlog_registry_lint ready/wip requirements for wave auto-promote."""
    missing: list[str] = []
    if not item.get("dod_commands"):
        missing.append("dod_commands (non-empty list)")
    user_stories = item.get("user_stories", []) or []
    if item.get("impact") != "infra" and not user_stories:
        missing.append("user_stories (at least one, unless impact=infra)")
    return (not missing, missing)


def _wave_auto_continue(closed_package_id: str, *, run_e2e_demo_all: bool = False) -> str | None:
    """Check if closed_package_id belongs to a wave; if so, auto-promote the
    next package in the wave by updating doc/backlog_registry.yaml and regenerating tasklist.md.

    Returns the next package id if promoted, or None if no wave continuation.
    """
    try:
        import yaml
    except ImportError:
        return None

    registry_path = ROOT / "doc" / "backlog_registry.yaml"
    tasklist_path = ROOT / "doc" / "tasklist.md"
    if not registry_path.exists():
        return None

    try:
        with open(registry_path, encoding="utf-8") as f:
            registry = yaml.safe_load(f)
    except Exception:
        return None

    if not isinstance(registry, dict) or registry.get("schema_version", 1) < 2:
        return None

    # Find the closed package in registry items
    items = registry.get("items") or []
    closed_item = next((it for it in items if isinstance(it, dict) and it.get("id") == closed_package_id), None)
    if not closed_item:
        return None

    wave_id = closed_item.get("wave_id")
    if not wave_id:
        return None

    # Find the wave definition
    waves = registry.get("waves") or []
    wave = next((w for w in waves if isinstance(w, dict) and w.get("id") == wave_id), None)
    if not wave:
        return None

    wave_packages = wave.get("packages") or []
    try:
        idx = wave_packages.index(closed_package_id)
    except ValueError:
        return None

    if idx + 1 >= len(wave_packages):
        # Last package in wave — mark wave completed
        _mark_wave_completed(registry_path, wave_id)
        print(f"\n🌊 [WAVE] Completed: {wave_id!r}. North star review pending.")
        print(f"   North star: {wave.get('north_star', '—')}")
        return None

    next_pkg_id = wave_packages[idx + 1]
    next_item = next((it for it in items if isinstance(it, dict) and it.get("id") == next_pkg_id), None)
    if not next_item:
        print(f"\n⚠ [WAVE] Next package {next_pkg_id!r} not found in registry — skipping auto-promote.")
        return None

    print(f"\n🌊 [WAVE] Auto-promoting next package in {wave_id!r}: {next_pkg_id!r}")

    contract_ok, missing_fields = _wave_next_package_ready_contract_ok(next_item)
    prior_status = str(next_item.get("status") or "proposed")

    if contract_ok:
        # Keep doc/backlog_registry.yaml item status as the SSoT for the derived Truth View.
        _set_registry_item_status(registry_path, next_pkg_id, "ready")
    elif prior_status == "ready":
        print(
            f"   ⚠ [WAVE] {next_pkg_id!r} is already ready but registry contract is incomplete: "
            f"{', '.join(missing_fields)}."
        )
        print(
            "   Backfill dod_commands/user_stories in doc/backlog_registry.yaml, then run:\n"
            f"   {DISPLAY_PYTHON} scripts/backlog_registry_lint.py --sync-from-index --write-sync"
        )
    else:
        print(
            f"   ⚠ [WAVE] {next_pkg_id!r} stays {prior_status!r} (not promoted to ready): missing "
            f"{', '.join(missing_fields)}."
        )

    # Mark wave as wip with the new active package (before lint so ACTIVE_WAVE marker is correct)
    _mark_wave_wip(registry_path, wave_id, next_pkg_id)

    # Write active_wave_id to YAML so it's the SSoT (not inferred from wave status)
    _set_registry_active_wave_id(registry_path, wave_id)

    # Regenerate tasklist.md: lint renders Truth View + Wave queue + active contract block from yaml.
    # Skip strict sync when a ready item would fail lint (prevents post-agent CalledProcessError).
    import subprocess

    lint_script = Path(__file__).resolve().parent / "backlog_registry_lint.py"
    sync_safe = contract_ok or prior_status != "ready"
    if lint_script.exists() and sync_safe:
        sync_cmd = [sys.executable, str(lint_script), "--sync-from-index", "--write-sync"]
        proc = subprocess.run(
            sync_cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            err_tail = (proc.stderr or proc.stdout or "").strip()
            if err_tail:
                print(err_tail[-2000:])
            print(
                f"   ⚠ [WAVE] tasklist sync failed (exit {proc.returncode}); "
                "fix registry and re-run backlog_registry_lint --sync-from-index --write-sync"
            )
        else:
            print("   ✓ Regenerated doc/tasklist.md from registry.")
    elif lint_script.exists() and not sync_safe:
        print("   ℹ [WAVE] Skipping tasklist sync until ready contract fields are backfilled.")
    else:
        # Test environments may monkeypatch ROOT to a temp dir without workflow scripts.
        print("   ℹ Skipping tasklist sync (backlog_registry_lint.py not found under ROOT).")

    return next_pkg_id


def _set_registry_active_wave_id(registry_path: Path, wave_id: str) -> None:
    """Write the top-level active_wave_id field to YAML."""
    try:
        text = registry_path.read_text(encoding="utf-8")
        # Replace existing active_wave_id: ... or add new one at top level (after schema_version)
        if re.search(r"^active_wave_id:", text, re.MULTILINE):
            new_text = re.sub(r"^active_wave_id:.*$", f"active_wave_id: {wave_id}", text, flags=re.MULTILINE)
        else:
            # Add after schema_version line
            new_text = re.sub(r"(^schema_version:.*$)", rf"\1\nactive_wave_id: {wave_id}", text, flags=re.MULTILINE)
        if new_text != text:
            registry_path.write_text(new_text, encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        print(f"⚠ Could not set active_wave_id to {wave_id!r}: {exc}")


def _mark_wave_completed(registry_path: Path, wave_id: str) -> None:
    """Update wave status to 'completed' in the registry YAML."""
    try:
        text = registry_path.read_text(encoding="utf-8")
        import re as _re
        # Simple line-level replacement for the wave status
        new_text = _re_replace_wave_status(text, wave_id, "completed")
        registry_path.write_text(new_text, encoding="utf-8")
    except Exception as exc:
        print(f"⚠ Could not mark wave {wave_id!r} as completed: {exc}")


def _mark_wave_wip(registry_path: Path, wave_id: str, active_pkg: str) -> None:
    """Update wave status to 'wip' in the registry YAML."""
    try:
        text = registry_path.read_text(encoding="utf-8")
        new_text = _re_replace_wave_status(text, wave_id, "wip")
        registry_path.write_text(new_text, encoding="utf-8")
    except Exception as exc:
        print(f"⚠ Could not mark wave {wave_id!r} as wip: {exc}")


def _re_replace_wave_status(yaml_text: str, wave_id: str, new_status: str) -> str:
    """Replace the status line of a specific wave block in the YAML text."""
    import re as _re
    # Find the wave block by id and replace its status field
    # Pattern: after "id: <wave_id>", find "  status: <old>" within the same block
    lines = yaml_text.splitlines(keepends=True)
    in_wave = False
    result = []
    for line in lines:
        if _re.match(r"\s*-\s+id:\s+" + _re.escape(wave_id) + r"\s*$", line):
            in_wave = True
        elif in_wave and _re.match(r"\s*-\s+id:", line):
            in_wave = False  # reached next wave
        if in_wave and _re.match(r"\s+status:\s+\w+", line):
            line = _re.sub(r"(status:\s+)\w+", rf"\g<1>{new_status}", line)
            in_wave = False  # only replace the first status occurrence
        result.append(line)
    return "".join(result)


def _re_replace_item_status(yaml_text: str, item_id: str, new_status: str) -> str:
    """Replace the first `status:` in the `items` entry for a given package id (text-based YAML)."""
    lines = yaml_text.splitlines(keepends=True)
    in_item = False
    result: list[str] = []
    for line in lines:
        bare = line.rstrip("\n\r")
        if re.match(rf"\s*-\s+id:\s+{re.escape(item_id)}$", bare):
            in_item = True
        elif in_item and re.match(r"\s*-\s+id:\s", bare):
            in_item = False
        if in_item and re.match(r"\s+status:\s+\S+", bare):
            new_bare = re.sub(r"(status:\s+)\S+", rf"\g<1>{new_status}", bare, count=1)
            eol = line[len(bare) :]  # keep original \n / \r\n
            line = new_bare + eol
            in_item = False
        result.append(line)
    return "".join(result)


def _get_registry_item_status_from_text(yaml_text: str, item_id: str) -> str | None:
    """Return the first ``status`` field value under ``items`` for ``item_id`` (text parse)."""
    lines = yaml_text.splitlines()
    in_item = False
    for line in lines:
        bare = line.rstrip("\n\r")
        if re.match(rf"\s*-\s+id:\s+{re.escape(item_id)}$", bare):
            in_item = True
            continue
        if in_item and re.match(r"\s*-\s+id:\s", bare):
            break
        if in_item:
            m = re.match(r"\s+status:\s+(\S+)", bare)
            if m:
                return m.group(1).strip("\"'")
    return None


def _set_registry_item_status(registry_path: Path, item_id: str, new_status: str) -> None:
    try:
        text = registry_path.read_text(encoding="utf-8")
        existing = _get_registry_item_status_from_text(text, item_id)
        if existing == new_status:
            # Wave packages often ship already ``ready``; rewriting YAML would be a no-op
            # and previously triggered a false-positive drift warning.
            return
        new_text = _re_replace_item_status(text, item_id, new_status)
        if new_text == text:
            print(f"⚠ [WAVE] No items entry or status line found for {item_id!r} — registry Truth View may drift")
            return
        registry_path.write_text(new_text, encoding="utf-8")
    except Exception as exc:  # pragma: no cover - best-effort sync
        print(f"⚠ [WAVE] Could not set registry item {item_id!r} to {new_status!r}: {exc}")


def _print_llm_context_summary(*, fail_on_context_errors: bool) -> int:
    """Run summarize_cost_logs.py after post-agent for quick context-budget triage."""
    if not SUMMARIZE_COST_LOGS.exists():
        print("\nℹ  LLM context summary skipped — scripts/summarize_cost_logs.py not found.")
        return 0

    print("\n📊 LLM context summary (recent cost logs):")
    cmd = [PYTHON_EXE, str(SUMMARIZE_COST_LOGS), "--limit-files", "3", "--top", "3"]
    if fail_on_context_errors:
        cmd.append("--fail-on-context-errors")

    with _TIMER.phase("summarize_cost_logs") as sum_rc:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        sum_rc["rc"] = result.returncode
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if output:
        print(output)
    else:
        print("(no summary output)")

    if fail_on_context_errors and result.returncode == 2:
        print("\n⛔ Context-length incidents detected in recent LLM cost logs.")
        print("   Direct gate command:")
        print(f"   {PYTHON_EXE} scripts/check_llm_context_gate.py --json-out")
        return EXIT_CLI_OR_CONTEXT_POLICY
    if result.returncode not in (0, 2):
        print(f"\n⚠ summarize_cost_logs exited with code {result.returncode}; continuing.")
    return 0


def run_smoke(
    *,
    package_id: str,
    agent: str,
    budget_profile: str,
    auto_prepare_epoch_demo: bool = False,
    lightweight: bool = False,
) -> int:
    """Smoke flow for epoch-demo.

    - full mode: runs real post-agent closure flow.
    - lightweight mode: checks parseability/prompt rendering only (no close_package).
    """
    print("🧪 Smoke mode: epoch-demo " + ("lightweight preflight" if lightweight else "post-agent"))
    print(f"   Package: {package_id}")
    print(f"   Budget profile: {budget_profile}")
    print(f"   Agent: {agent}")
    if auto_prepare_epoch_demo and package_id == "epoch-demo":
        with _TIMER.phase("epoch_demo_scaffold"):
            _ensure_epoch_demo_scaffold()

    if PRINT_EPOCH_DEMO_PROMPTS.exists():
        print("\n📋 Canonical smoke prompt:\n")
        with _TIMER.phase("print_smoke_prompt") as prc:
            prompt_proc = subprocess.run(
                [PYTHON_EXE, str(PRINT_EPOCH_DEMO_PROMPTS), "smoke"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            prc["rc"] = prompt_proc.returncode
        prompt_output = ((prompt_proc.stdout or "") + (prompt_proc.stderr or "")).strip()
        if prompt_output:
            print(prompt_output)
        else:
            print("(prompt output is empty)")
    else:
        print("\nℹ  Prompt printer not found, skipping prompt output.")

    if lightweight:
        print("\n▶ Running lightweight smoke checks (no post-agent side effects)...")
        with _TIMER.phase("smoke_light_state_load"):
            state = load_state(package_id)
        if not state.get("package"):
            print("ℹ  Lightweight smoke: package not active in backlog_registry.yaml, skipping contract parse checks.")
            print("\n🧾 Smoke result: exit_code=0")
            return 0
        contract = state.get("contract", {}) or {}
        cmds = extract_dod_commands(str(contract.get("DOD_COMMANDS", "")))
        if not cmds:
            print("ℹ  Lightweight smoke: DOD_COMMANDS not parsed, but preflight stays non-blocking.")
            print("\n🧾 Smoke result: exit_code=0")
            return 0
        print("✅ Lightweight smoke checks passed.")
        print("\n🧾 Smoke result: exit_code=0")
        return 0

    print("\n▶ Running post-agent smoke command...")
    rc = post_agent(package_id, agent=agent, budget_profile=budget_profile, skip_sync_checks=True)

    print(f"\n🧾 Smoke result: exit_code={rc}")
    if rc == EXIT_REGISTRY_OR_SSO_GATE:
        print(
            "   Hard gate hit (registry/sync). If package is missing, prepare/reopen it first:\n"
            f"   {DISPLAY_PYTHON} scripts/print_epoch_demo_agent_prompts.py package"
        )
    return rc


_SMOKE_EPOCH_DEMO_WRITE_PATH = "scripts/prompt_utils.py"


def _git_last_commit_touching_path(rel_path: str) -> str | None:
    """Return full SHA of the last commit that touched rel_path, or None.

    Используется только smoke-скaffoldом: `prompt_utils.validate_verification_only_evidence`
    требует реальный commit + путь, существующий в дереве и в истории этого коммита.
    Команда: ``git log -1 --format=%H -- <path>`` — SHA **не константа**, при каждом
    auto-prepare подставляется актуальный «последний коммит, затронувший файл».
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", rel_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    sha = (result.stdout or "").strip().splitlines()
    if not sha or len(sha[0]) < 7:
        return None
    return sha[0].strip()


def _write_epoch_demo_smoke_execution_contract(artifact_dir: Path) -> None:
    """Перезаписывает execution_contract.md: без валидного evidence post-agent не даст
    `verification_only` (будет unknown / exit 6). См. блок «Зачем commit» в теле файла.
    """
    rel = _SMOKE_EPOCH_DEMO_WRITE_PATH
    commit = _git_last_commit_touching_path(rel)
    execution_contract = artifact_dir / "execution_contract.md"
    if not commit:
        print(
            "⚠ Auto-prepare: no git commit for "
            f"`{rel}` — smoke may stay blocked (exit 6). Is this a git checkout?"
        )
        return
    # Пояснение для читателей артефакта: SHA динамический, не хардкод в репозитории.
    body = (
        f"# epoch-demo execution contract (smoke)\n\n"
        f"## Зачем поле `commit` и путь к файлу\n\n"
        f"Пайплайн (`prompt_utils.resolve_closure_mode` → `validate_verification_only_evidence`)\n"
        f"должен **доказуемо** сопоставить «код уже был в репо» с конкретным коммитом и\n"
        f"путями. Без этого при чистом рабочем дереве остаётся режим `unknown` и\n"
        f"`--post-agent` / smoke завершается с **exit 6**.\n\n"
        f"Ниже **commit** — это не фиксированная константа в коде: при каждом запуске\n"
        f"`--smoke --auto-prepare-epoch-demo` подставляется результат\n"
        f"`git log -1 --format=%H -- {rel}` (последний коммит, который менял этот файл\n"
        f"в **текущем** клоне). После новых коммитов, затрагивающих `prompt_utils`,\n"
        f"строка обновится.\n\n"
        f"### Что можно улучшить\n\n"
        f"- Shallow clone / урезанная история: `git log` может вести себя иначе; при сбоях\n"
        f"  валидации смотрите `evidence_inconclusive_allowed` в документации контракта.\n"
        f"- Сторонние копии только этого файла без перезапуска scaffold — commit может\n"
        f"  устареть относительно ветки; перегенерируйте auto-prepare на машине, где\n"
        f"  гоняете smoke.\n"
        f"- Долгосрочно: отдельный **lightweight smoke** без реальной `git`‑проверки\n"
        f"  (отдельный пакет/флаг), если нужен CI без полного клона.\n\n"
        f"---\n\n"
        f"Pre-existing delivery evidence:\n"
        f"- commit: {commit}\n"
        f"- files: {rel}\n\n"
        f"Auto-prepared by `run_autonomous.py --smoke --auto-prepare-epoch-demo`.\n"
    )
    try:
        execution_contract.write_text(body, encoding="utf-8")
        print("🛠 Auto-prepare: refreshed execution_contract.md (verification-only evidence).")
    except OSError as exc:
        print(f"⚠ Auto-prepare: could not write execution_contract.md: {exc}")


def _ensure_epoch_demo_scaffold() -> None:
    """Auto-prepare epoch-demo smoke artifacts and regenerate derived ``doc/tasklist.md`` from registry."""
    artifact_dir = ROOT / "archive" / "team_artifacts" / "epoch-demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_epoch_demo_smoke_execution_contract(artifact_dir)

    lint_script = Path(__file__).resolve().parent / "backlog_registry_lint.py"
    if not lint_script.exists():
        print("   ℹ Auto-prepare: backlog_registry_lint.py not found — skipping tasklist sync.")
        return
    try:
        subprocess.run(
            [sys.executable, str(lint_script), "--sync-from-index", "--write-sync"],
            check=True,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print("🛠 Auto-prepare: regenerated doc/tasklist.md from registry (epoch-demo smoke).")
    except subprocess.CalledProcessError as exc:  # pragma: no cover - depends on local_yaml
        out = ((exc.stdout or "") + (exc.stderr or "")).strip()
        print(
            f"⚠ Auto-prepare: backlog_registry_lint failed (exit {exc.returncode}). {out[:500]}",
            file=sys.stderr,
        )


def _main_impl() -> int:
    parser = argparse.ArgumentParser(description="Zero-Click Delivery Pipeline")
    parser.add_argument("--package", "-p", help="Override auto-detected package")
    parser.add_argument(
        "--agent", "-a",
        choices=list(AUTONOMOUS_AGENT_CHOICES),
        default="cursor_ai",
        help="Target agent (default: cursor_ai)",
    )
    parser.add_argument(
        "--max-loops", type=int, default=3, help="Максимум попыток для claude-code TDD loop",
    )
    parser.add_argument(
        "--post-agent", action="store_true",
        help="Run DoD + close package after a GUI agent (Cursor/Codex) finishes its task",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Unified smoke command: print canonical epoch-demo smoke prompt and run "
            "`--post-agent` flow for epoch-demo (or --package override)."
        ),
    )
    parser.add_argument(
        "--auto-prepare-epoch-demo",
        action="store_true",
        help=(
            "For --smoke: refresh epoch-demo team artifacts, then run backlog_registry_lint "
            "to regenerate doc/tasklist.md from backlog_registry.yaml before post-agent smoke."
        ),
    )
    parser.add_argument(
        "--run-smoke-check-before-pipeline",
        action="store_true",
        help=(
            "Before normal pipeline run, execute lightweight epoch-demo smoke preflight "
            "(no post-agent close_package side effects). If smoke fails, stop with same exit code."
        ),
    )
    parser.add_argument(
        "--budget-profile",
        choices=budget_profile_choices(),
        default="strict",
        help="Token/message budget profile for prompt generation (default: strict)",
    )
    parser.add_argument(
        "--fail-on-context-errors",
        action="store_true",
        help="For --post-agent: fail if recent LLM cost logs contain context_length_exceeded incidents",
    )
    parser.add_argument(
        "--non-stop",
        action="store_true",
        dest="non_stop",
        help=(
            "Non-stop auto-execution mode: after --post-agent succeeds and generates the next task, "
            "immediately execute doc/current_task.md without pausing for user input"
        ),
    )
    parser.add_argument(
        "--non-stop-max-next-tasks",
        type=int,
        default=50,
        help=(
            "For --non-stop mode: max number of automatic transitions to the next task "
            "after closing the current one (default: 50)."
        ),
    )
    parser.add_argument(
        "--non-stop-chain-step",
        type=int,
        default=0,
        help=(
            "Internal counter for --non-stop chain depth. "
            "Normally propagated automatically; do not set manually."
        ),
    )
    parser.add_argument(
        "--run-e2e-demo-all",
        "--run_e2e_demo_all",
        action="store_true",
        help=(
            "For demo-wave contracts: use full `npm run test:e2e:demo` instead of "
            "single-scenario grep run."
        ),
    )
    parser.add_argument(
        "--no-dod-cache",
        action="store_true",
        help="Do not read/write DoD cache (dod_cache.json); always run DoD commands.",
    )
    parser.add_argument(
        "--allow-empty-generator",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-auto-promote",
        action="store_true",
        help="Disable automatic wave package promotion when registry has no active ready/wip package",
    )
    parser.add_argument(
        "--explain-exit",
        type=int,
        metavar="N",
        help="Print explanation and recovery steps for exit code N, then exit 0",
    )
    args = parser.parse_args()

    if args.explain_exit is not None:
        _print_exit_explanation(args.explain_exit)
        return 0

    conflict = package_run_conflict(args.package)
    if conflict is not None:
        print(
            "❌ package run lock is held by another live process "
            f"(package={args.package}, pid={conflict.get('pid')}, run_id={conflict.get('run_id')})",
            file=sys.stderr,
        )
        return EXIT_LOCK_CONFLICT
    run_id = get_or_create_run_id()
    _pipeline_bootstrap(
        run_id,
        package_id=args.package,
        initial_phase=_initial_pipeline_phase(args),
    )
    write_pid_registry(run_id, os.getpid(), package_id=args.package)
    if args.non_stop_max_next_tasks < 0:
        print("❌ --non-stop-max-next-tasks must be >= 0", file=sys.stderr)
        return EXIT_CLI_OR_CONTEXT_POLICY
    if args.non_stop_chain_step < 0:
        print("❌ --non-stop-chain-step must be >= 0", file=sys.stderr)
        return EXIT_CLI_OR_CONTEXT_POLICY
    if args.non_stop:
        _ensure_non_stop_started_at()
        non_stop_verdict = _evaluate_non_stop_policy(
            requested_non_stop=True,
            chain_step=args.non_stop_chain_step,
            cli_max_next_tasks=args.non_stop_max_next_tasks,
            policy=_load_non_stop_policy(),
        )
        if not non_stop_verdict.ok:
            print(f"❌ {non_stop_verdict.reason}", file=sys.stderr)
            return EXIT_CLI_OR_CONTEXT_POLICY
        args.non_stop_max_next_tasks = non_stop_verdict.effective_max_next_tasks

    if args.smoke:
        if args.post_agent:
            print("❌ --smoke cannot be combined with --post-agent", file=sys.stderr)
            return EXIT_CLI_OR_CONTEXT_POLICY
        if args.non_stop:
            print("❌ --smoke cannot be combined with --non-stop", file=sys.stderr)
            return EXIT_CLI_OR_CONTEXT_POLICY
        smoke_package = args.package or "epoch-demo"
        with _TIMER.phase("smoke") as smk:
            r_smoke = run_smoke(
                package_id=smoke_package,
                agent=args.agent,
                budget_profile=args.budget_profile,
                auto_prepare_epoch_demo=bool(args.auto_prepare_epoch_demo),
            )
            smk["rc"] = r_smoke
        return r_smoke

    if args.post_agent:
        if not args.package:
            print("❌ --post-agent requires --package <id>", file=sys.stderr)
            return EXIT_CLI_OR_CONTEXT_POLICY
        # Resolve effective chain_step: take max(argv, persisted) so a stale
        # footer command does not bypass the non-stop limit (BUG-05 fix).
        effective_chain_step = args.non_stop_chain_step
        if args.non_stop and run_id:
            from pipeline_state import read_chain_step as _read_chain_step  # noqa: PLC0415
            persisted_step = _read_chain_step(run_id)
            if persisted_step > effective_chain_step:
                print(
                    f"   ℹ [CHAIN] chain_step restored from pipeline_state.json: "
                    f"{args.non_stop_chain_step} (argv) → {persisted_step} (persisted)"
                )
                effective_chain_step = persisted_step
        rc = post_agent(
            args.package,
            agent=args.agent,
            budget_profile=args.budget_profile,
            non_stop=args.non_stop,
            run_e2e_demo_all=bool(args.run_e2e_demo_all),
            non_stop_max_next_tasks=args.non_stop_max_next_tasks,
            non_stop_chain_step=effective_chain_step,
            use_dod_cache=not args.no_dod_cache,
        )
        if rc in (EXIT_SUCCESS, EXIT_NON_STOP_CONTINUE, EXIT_POST_AGENT_CHAT_API_HANDOFF):
            summary_rc = _print_llm_context_summary(
                fail_on_context_errors=bool(args.fail_on_context_errors),
            )
            if summary_rc != 0:
                return summary_rc
            return rc
        return rc

    if args.run_smoke_check_before_pipeline:
        print("🔎 Pre-flight smoke check enabled (--run-smoke-check-before-pipeline).")
        # D10: lint tasklist integrity FIRST (in-process, ≤5ms)
        with _TIMER.phase("lint_tasklist"):
            tasklist_text = (ROOT / "doc" / "tasklist.md").read_text(encoding="utf-8")
            lint_errors = _lint_tasklist(tasklist_text)
        if lint_errors:
            print("\n[lint_tasklist] generated tasklist integrity check FAILED:", file=sys.stderr)
            for err in lint_errors:
                print(f"  ✗ {err}", file=sys.stderr)
            print(
                "\n  Fix: regenerate tasklist.md from backlog_registry.yaml so every active row has\n"
                "  a matching '### <id> Contract' block, or run --auto-prepare-epoch-demo.",
                file=sys.stderr,
            )
            return EXIT_REGISTRY_OR_SSO_GATE
        if args.auto_prepare_epoch_demo:
            # Repair any inconsistent epoch-demo state (row without contract block)
            # BEFORE lightweight smoke reads it. Without this, load_state finds
            # the row, non-blocking lightweight smoke passes, then main pipeline
            # crashes on missing contract block (D4 defect).
            with _TIMER.phase("epoch_demo_scaffold"):
                _ensure_epoch_demo_scaffold()
        with _TIMER.phase("pre_smoke") as pre:
            smoke_rc = run_smoke(
                package_id="epoch-demo",
                agent=args.agent,
                budget_profile=args.budget_profile,
                auto_prepare_epoch_demo=False,
                lightweight=True,
            )
            pre["rc"] = smoke_rc
        if smoke_rc != 0:
            print(
                "\n🛑 Pre-flight smoke check failed. Main pipeline run aborted.",
                file=sys.stderr,
            )
            return smoke_rc

    # FIX BUG-3: отслеживаем resolved package_id между итерациями цикла,
    # чтобы в repeat-итерациях всегда передавать явный --package и не терять контекст.
    resolved_package: str | None = args.package

    loop_count = 0
    while loop_count < args.max_loops:
        loop_count += 1

        with _TIMER.phase("state_load"):
            state = load_state(resolved_package)
        with _TIMER.phase("decide_step"):
            decision = decide_next_step(state, agent=args.agent, package=resolved_package)

        if decision["action"] == "ERROR":
            print(f"❌ Ошибка: {decision['reasons'][0]}")
            return EXIT_REGISTRY_OR_SSO_GATE

        action = decision["action"]
        command = decision["command"]
        package_id = state.get("package", "unknown")

        if (
            "scripts/generate_next_prompt.py" in command
            or "scripts/generate_orchestration_prompt.py" in command
        ) and "--budget-profile" not in command:
            command.extend(["--budget-profile", args.budget_profile])
        if (
            "scripts/generate_next_prompt.py" in command
            or "scripts/generate_orchestration_prompt.py" in command
        ) and "--stdout-mode" not in command:
            command.extend(["--stdout-mode", "full"])

        # FIX BUG-3: сохраняем package_id после первого успешного определения,
        # чтобы последующие итерации (Resume-цикл) работали с тем же пакетом.
        if package_id and package_id != "unknown":
            resolved_package = package_id

        print(f"\n🎯 [LOOP {loop_count}] Action: {action} | Agent: {args.agent}")

        # AUTO-PROMOTE: if registry has no active ready/wip package and action is
        # orchestration (NEXT/PLAN_NEXT), promote the next ready wave package so non-stop
        # can continue without human intervention.
        if (
            not getattr(args, "no_auto_promote", False)
            and not state.get("package")
            and "generate_orchestration_prompt" in " ".join(str(c) for c in command)
        ):
            with _TIMER.phase("auto_promote"):
                # SSoT: find_next_candidate reads registry only, no tasklist markdown.
                candidate = find_next_candidate(verbose=True)
            if candidate:
                contract_id = candidate.contract_id
                package_id_full = candidate.id
                print(f"\n🔀 [AUTO-PROMOTE] No active registry package — promoting {contract_id} from {candidate.wave_id}")

                if _promote_update_registry(candidate, new_status="ready"):
                    print(f"   ✓ Registry updated: {candidate.id} → 'ready'")

                # Lint is the single writer of tasklist.md (derived Truth View + Wave queue + contracts).
                sync_cmd = [sys.executable, "scripts/backlog_registry_lint.py", "--sync-from-index", "--write-sync"]
                subprocess.run(sync_cmd, check=True, cwd=str(ROOT))
                print(f"   ✓ Regenerated doc/tasklist.md from registry (contract block rendered).")

                print(f"   ✓ Promoted {contract_id} in backlog_registry.yaml. Restarting loop iteration...")
                resolved_package = package_id_full
                continue  # Restart loop iteration with updated state
            else:
                # BUG-FIX: registry may already have a ready/wip package.
                # find_next_candidate skips packages whose status is "ready"
                # (treats them as already promoted). Regenerate tasklist.md and
                # restart the loop so load_state() routes the package through
                # classify_package_complexity correctly instead of
                # falling through to PLAN_NEXT which calls generate_orchestration_prompt
                # without --package, bypassing complexity routing entirely.
                from auto_promote_next_wave_package import _get_now_package_ids_from_registry  # noqa: PLC0415
                already_ready = _get_now_package_ids_from_registry()
                if already_ready:
                    print(
                        f"\n🔁 [SYNC-FIX] Registry has ready packages: {already_ready[:3]}\n"
                        "   Regenerating tasklist.md derived view..."
                    )
                    sync_cmd = [sys.executable, "scripts/backlog_registry_lint.py", "--sync-from-index", "--write-sync"]
                    subprocess.run(sync_cmd, check=True, cwd=str(ROOT))
                    resolved_package = already_ready[0]
                    print(f"   ✓ Restarting loop with {resolved_package}")
                    continue
                print(
                    "\nℹ  Registry has no active ready/wip package and no ready wave packages found.\n"
                    "   All wave packages are closed or dependencies pending.\n"
                    "   Run plan-next manually to define the next package.",
                    file=sys.stderr,
                )

        # Для EXECUTION_AUTO форсируем --quick чтобы перепрыгнуть фазу планирования
        if action == "EXECUTION_AUTO" and "--quick" not in command:
            command.append("--quick")

        # Перехват промпта
        with _TIMER.phase("generator_subprocess") as grc:
            prompt_text = capture_generated_prompt(
                command,
                allow_empty=bool(args.allow_empty_generator),
            )
            grc["rc"] = 0
        prompt_text = _inject_demo_scenario_id_into_prompt(prompt_text, package_id)
        if args.allow_empty_generator and not prompt_text.strip():
            return 0

        # Запуск агента
        is_sync = run_agent_headless(
            args.agent,
            prompt_text,
            package_id,
            budget_profile=args.budget_profile,
            non_stop=args.non_stop,
            non_stop_max_next_tasks=args.non_stop_max_next_tasks,
            non_stop_chain_step=args.non_stop_chain_step,
        )

        # Если агент асинхронный (Cursor), скрипт на этом заканчивает работу
        if not is_sync:
            return 0

        # Если агент синхронный (claude_code), автоматически прогоняем DoD
        if state.get("contract"):
            passed = run_dod_loop(
                package_id,
                state["contract"],
                use_dod_cache=not args.no_dod_cache,
            )
            if passed:
                # FIX ARCH-3: передаём --package явно, чтобы при нескольких
                # активных пакетах был закрыт именно нужный.
                git_snap = _fetch_git_worktree_snapshot()
                exec_c = ROOT / "archive" / "team_artifacts" / package_id / "execution_contract.md"
                exec_text: str | None = None
                ev_ok: bool | None = None
                if exec_c.exists():
                    exec_text = exec_c.read_text(encoding="utf-8", errors="replace")
                    ev_ok, _ = validate_verification_only_evidence(exec_text, ROOT)
                src_p = (
                    closure_mode_src_from_git_paths(git_snap.all_paths)
                    if git_snap is not None
                    else None
                )
                with _TIMER.phase("closure_mode_detect"):
                    resolution = _resolve_closure_mode(
                        package_id,
                        state["contract"],
                        precomputed_src_changed=src_p,
                        precomputed_evidence_valid=ev_ok,
                        exec_contract_text=exec_text,
                    )
                    mode = resolution.mode
                    upgrade_notice = format_closure_mode_upgrade_notice(
                        resolution, success_prefix=True
                    )
                    if upgrade_notice:
                        print(upgrade_notice)
                print(
                    f"   Автоматическое закрытие пакета: {DISPLAY_PYTHON} "
                    f"scripts/close_package.py --package {package_id} --closure-mode {mode} --skip-dod"
                )
                with _TIMER.phase("proof_bundle_build"):
                    _build_proof_bundle(get_or_create_run_id(), package_id)
                with _TIMER.phase("close_package") as tdd_cp:
                    close_args = ClosePackageArgs(
                        package=package_id,
                        skip_dod=True,
                        closure_mode=mode,
                        approve_close_without_dod=True,
                        **close_package_team_artifact_kwargs_from_env(),
                    )
                    rc = run_close_package_impl(close_args)
                    tdd_cp["rc"] = rc
                return rc
            else:
                # DoD упали. Идем на следующий круг (будет выбран RESUME,
                # т.к. resolved_package теперь зафиксирован и execution_contract.md существует).
                print("   Инициируем Resume-цикл исправления...")
                continue
        else:
            return 0

    print("❌ Превышен лимит попыток TDD loop.")
    return 1



# ── Exit-code reference table ─────────────────────────────────────────────────

_EXIT_DOCS: dict[int, dict[str, str]] = {
    0: {
        "group": "Успех",
        "summary": "post-agent выполнен, пакет закрыт. Цепочка non-stop остановлена.",
        "symptom": "Нормальное завершение.",
        "fix": "Ничего. Можно запускать следующий пакет: python scripts/workflow.py",
    },
    1: {
        "group": "DoD FAIL",
        "summary": "Тесты упали или TDD-loop исчерпал max-loops.",
        "symptom": "pytest/mypy/ruff вернул ненулевой код. Либо агент превысил --max-loops.",
        "fix": (
            "1. Прочитай stdout/stderr для деталей провала.\n"
            "2. Исправь код и перезапусти:\n"
            "   .venv\\Scripts\\python.exe scripts/run_autonomous.py --post-agent --package <ID>"
        ),
    },
    2: {
        "group": "Registry / SSoT gate",
        "summary": "Пакет не найден в реестре, tasklist не синхронизирован, или roadmap quality gates.",
        "symptom": "Сообщение: 'package not found in registry' или 'Sync checks FAILED'.",
        "fix": (
            "1. Синхронизировать tasklist:\n"
            "   .venv\\Scripts\\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync\n"
            "2. Проверить что пакет есть в doc/backlog_registry.yaml с корректным статусом.\n"
            "3. Убедиться что поле dod_commands не пустое."
        ),
    },
    3: {
        "group": "Контракт отсутствует",
        "summary": "Нет файла archive/team_artifacts/<ID>/execution_contract.md перед закрытием.",
        "symptom": "Сообщение: 'No execution contract found'.",
        "fix": (
            "Вариант A — новая задача:\n"
            "   1. python scripts/workflow.py --exec  # → generate_orchestration_prompt.py\n"
            "   2. Выполни STEP 1–N из orchestration_<agent>.md\n"
            "   3. Агент должен создать execution_contract.md\n\n"
            "Вариант B — verification-only (код уже существует):\n"
            "   Добавь в execution_contract.md блок:\n"
            "     Pre-existing delivery evidence:\n"
            "     - commit: <sha>\n"
            "     - files: app/foo.py, tests/test_foo.py\n"
            "   Затем: .venv\\Scripts\\python.exe scripts/run_autonomous.py --post-agent --package <ID>"
        ),
    },
    4: {
        "group": "DoD drift",
        "summary": "Команды DoD в сохранённом exec-промпте не совпадают с текущим контрактом в реестре.",
        "symptom": "Сообщение: 'DoD changed after execution prompt was generated'.",
        "fix": (
            "Если ослабление DoD законное — обнови контракт в реестре через plan-next, НЕ локально:\n"
            "   .venv\\Scripts\\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai --force\n\n"
            "Если drift случайный — восстанови оригинальный DoD в doc/backlog_registry.yaml\n"
            "и перезапусти без --force."
        ),
    },
    5: {
        "group": "Verification-only policy",
        "summary": "Пакет помечен как verification-only, но нет доказательства pre-existing delivery.",
        "symptom": "Сообщение: 'verification_only is forbidden' или нет evidence block.",
        "fix": (
            "Добавь в execution_contract.md:\n"
            "  Pre-existing delivery evidence:\n"
            "  - commit: <sha 7-40 chars>\n"
            "  - files: <существующие пути в репо>\n"
            "Также добавь в Notes реестра: allow_verification_only — <описание>."
        ),
    },
    6: {
        "group": "Режим закрытия unknown",
        "summary": "closure_mode не удалось определить из git/контракта.",
        "symptom": "Сообщение: 'closure mode unknown'. Нет изменений в git или пустой write-set.",
        "fix": (
            "1. Убедись что агент внёс реальные изменения (git diff HEAD).\n"
            "2. Проверь write-set в doc/backlog_registry.yaml — он не должен быть пустым.\n"
            "3. Если это verification-only — добавь evidence block (см. exit 5)."
        ),
    },
    7: {
        "group": "Write-set mismatch / contract drift",
        "summary": "Нет пересечения git-изменений с write-set контракта. Contract drift.",
        "symptom": "Сообщение: 'write-set mismatch' или 'no changed files for execution'.",
        "fix": (
            "1. Перегенерировать orchestration и привести контракт в соответствие:\n"
            "   .venv\\Scripts\\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai --force\n"
            "2. Либо обнови write-set/Outcomes в doc/backlog_registry.yaml через plan-next.\n"
            "3. Либо убедись что агент изменил файлы из write-set (git diff HEAD)."
        ),
    },
    8: {
        "group": "CLI / Context policy",
        "summary": "Неверные аргументы CLI или нарушение non-stop policy / LLM context gate.",
        "symptom": "argparse error или сообщение о context_length_exceeded.",
        "fix": (
            "1. Проверь аргументы: --post-agent требует --package; --smoke несовместим с --post-agent.\n"
            "2. Если context gate: .venv\\Scripts\\python.exe scripts/check_llm_context_gate.py\n"
            "3. Запусти без --non-stop для изоляции проблемы."
        ),
    },
    9: {
        "group": "Lock / параллельный конфликт",
        "summary": "Другой живой процесс run_autonomous держит lock на пакет.",
        "symptom": "Сообщение: 'package run lock is held by another live process'.",
        "fix": (
            "1. Дождись завершения другого процесса.\n"
            "2. Или принудительно сними lock:\n"
            "   .venv\\Scripts\\python.exe scripts/pipeline_status.py  # найди pid\n"
            "   # затем завершь процесс по pid"
        ),
    },
    10: {
        "group": "Успех — продолжение non-stop",
        "summary": "post-agent успешен, non-stop цепочка продолжается в этой же сессии.",
        "symptom": "Нормальное завершение с инструкцией читать current_task.md.",
        "fix": (
            "Прочитай doc/current_task.md и выполни следующий шаг.\n"
            "Или: python scripts/workflow.py  # покажет текущее состояние."
        ),
    },
    11: {
        "group": "Chat-API handoff (не закрытие)",
        "summary": "Контракт записан триггером DeepSeek Chat API как BLOCKED — локальных правок не было.",
        "symptom": "Сообщение [HANDOFF] и exit 11; workflow.py с loop должен остановиться без повторов.",
        "fix": (
            "Выполни оркестрацию в агенте с доступом к репозиторию; замени execution_contract.md "
            "на реальный proof; затем снова post-agent или workflow --loop."
        ),
    },
}


def _print_exit_explanation(code: int) -> None:
    sep = "─" * 55
    doc = _EXIT_DOCS.get(code)
    if doc is None:
        print(f"Exit code {code}: нет документации для этого кода.")
        print(f"Известные коды: {sorted(_EXIT_DOCS)}")
        return

    print(f"\n{'═' * 55}")
    print(f"  EXIT {code} — {doc['group']}")
    print(f"{'═' * 55}")
    print(f"\n  Что произошло:\n  {doc['summary']}")
    print(f"\n  Симптом:\n  {doc['symptom']}")
    print(f"\n  Как исправить:")
    for line in doc["fix"].splitlines():
        print(f"  {line}")
    print(f"\n{sep}\n")


def main() -> int:
    # Detect chain step from argv to skip cleanup on non-stop continuations
    _chain_step = 0
    if "--non-stop-chain-step" in sys.argv:
        try:
            _chain_step = int(sys.argv[sys.argv.index("--non-stop-chain-step") + 1])
        except (IndexError, ValueError):
            pass

    run_id = get_or_create_run_id()

    if _chain_step == 0:
        cleanup_old_logs()
        cleanup_stale_pid_registrations()

    _TIMER.reset()
    rc = 1
    try:
        rc = _main_impl()
    except SystemExit as exc:
        code = exc.code
        if code is None:
            rc = 0
        elif isinstance(code, int):
            rc = code
        else:
            rc = 1
    finally:
        _pipeline_finalize_for_exit(run_id, exit_code=rc)
        write_run_result(
            run_id=run_id,
            exit_code=rc,
            package_id=_package_id_from_argv(),
            argv=sys.argv,
        )
        _TIMER.print_summary()
        _TIMER.flush()
    return rc


if __name__ == "__main__":
    ensure_utf8_stdio()  # FIX BUG-2: только при прямом запуске
    sys.exit(main())
