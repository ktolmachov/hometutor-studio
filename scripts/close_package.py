#!/usr/bin/env python3
"""
close_package.py — Automated package closure.

Closes a completed package by updating documentation/state files:
  1. doc/backlog_registry.yaml — mark package as closed (SSoT)
  2. doc/tasklist.md           — regenerated via backlog_registry_lint after close (not edited by hand here)
  3. doc/user_stories/*.md     — mark linked US files as closed
  4. doc/user_stories_index.json — update US entries
  5. doc/closed_iterations.md  — append closure summary
  6. doc/changelog.md          — prepend changelog entry

Then runs roadmap_sync_check.py and backlog_registry_lint.py to verify.

Usage:
    python scripts/close_package.py                        # auto-detect from backlog_registry.yaml
    python scripts/close_package.py --package <PACKAGE_ID>
    python scripts/close_package.py --dry-run              # show changes, no writes
    python scripts/close_package.py --verify-only          # run DoD only, no writes
    python scripts/close_package.py --skip-dod             # skip DoD check
    python scripts/close_package.py --skip-team-artifacts-check  # skip orchestrator artifact lint
    python scripts/close_package.py --team-artifacts-strict # warnings fail the gate

При автозакрытии через scripts/run_autonomous.py те же режимы задаются env:
HOME_RAG_TEAM_ARTIFACTS_STRICT / HOME_RAG_SKIP_TEAM_ARTIFACTS_GATE (см. .env.example).

Exit codes:
    0 — closed successfully (or DoD pass in --verify-only)
    1 — DoD failed or package not found
    2 — parse error or inconsistency
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_stdio_utf8 import configure_stdio_utf8  # noqa: E402
from _perf_timer import PhaseTimer  # noqa: E402
from prompt_utils import (  # noqa: E402
    classify_package_complexity,
    closure_mode_src_from_git_paths,
    extract_dod_commands as _extract_dod_commands_from_prompt_utils,
    format_closure_mode_upgrade_notice,
    load_backlog_registry,
    parse_contract_write_set,
    parse_contract as parse_contract_canonical,
    parse_truth_view_from_registry,
    resolve_closure_mode as _resolve_closure_mode,
    select_package,
    validate_verification_only_evidence,
    verification_only_policy_guidance,
)
from agent_sandbox import SandboxViolationError, safe_run, safe_run_shell  # noqa: E402
from hitl_approval import assert_approved  # noqa: E402
from pipeline_events import RUN_ID_ENV  # noqa: E402
from quality_gates import run_all as _run_quality_gates  # noqa: E402
import validate_team_artifact as _team_art  # noqa: E402


@dataclass
class ClosePackageArgs:
    """In-process arguments for run_close_package_impl()."""
    package: str | None = None
    dry_run: bool = False
    verify_only: bool = False
    skip_dod: bool = False
    force: bool = False
    closure_mode: str = "unknown"  # "execution", "verification_only", "unknown"
    skip_sync_checks: bool = False  # skip sync/post-close checks (for smoke runs)
    approve_close_without_dod: bool = False
    skip_team_artifacts_check: bool = False
    team_artifacts_strict: bool = False


ROOT = Path(__file__).resolve().parents[1]
TASKLIST          = ROOT / "doc" / "tasklist.md"
BACKLOG_REGISTRY  = ROOT / "doc" / "backlog_registry.yaml"
US_DIR            = ROOT / "doc" / "user_stories"
US_INDEX          = ROOT / "doc" / "user_stories_index.json"
CLOSED_ITERATIONS = ROOT / "doc" / "closed_iterations.md"
CHANGELOG         = ROOT / "doc" / "changelog.md"
ARCHIVE_DIR       = ROOT / "archive" / "agent_prompts"
TEAM_ARTIFACTS    = ROOT / "archive" / "team_artifacts"
PIPELINE_METRICS  = ROOT / "archive" / "pipeline_metrics.md"

def _parse_contract(text: str, package_id: str) -> dict[str, str]:
    # FIX: Delegate to canonical prompt_utils.py parser since local fallback is broken
    return parse_contract_canonical(text, package_id)


def _registry_item_status(package_id: str) -> str | None:
    """Return backlog item status for ``package_id`` if present in registry."""
    try:
        reg = load_backlog_registry()
    except Exception:
        return None
    for it in reg.get("items") or []:
        if isinstance(it, dict) and it.get("id") == package_id:
            st = it.get("status")
            return str(st) if st is not None else None
    return None


def _select_package(rows: list[dict[str, str]], explicit: str | None) -> dict[str, str] | None:
    """Compatibility wrapper; canonical selector lives in prompt_utils.py."""
    return select_package(rows, explicit)


def _clean(v: str) -> str:
    return v.strip().strip("`").strip()


def _extract_dod_commands(raw: str) -> list[str]:
    """Split DoD commands using prompt_utils.extract_dod_commands (handles newline + semicolon)."""
    return _extract_dod_commands_from_prompt_utils(raw)


def _extract_dod_commands_legacy(raw: str) -> list[str]:
    """Legacy: Split on ';' not inside single/double quotes. Kept for reference."""
    raw = raw.strip()
    commands: list[str] = []
    current: list[str] = []
    in_single = in_double = False
    for ch in raw:
        if ch == "'" and not in_double:
            in_single = not in_single
            current.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            current.append(ch)
        elif ch == ';' and not in_single and not in_double:
            cmd = "".join(current).strip().strip("`").strip()
            if cmd:
                commands.append(cmd)
            current = []
        else:
            current.append(ch)
    cmd = "".join(current).strip().strip("`").strip()
    if cmd:
        commands.append(cmd)
    return commands


def _extract_us_ids(raw: str) -> list[str]:
    return re.findall(r"US-[\d.]+", raw, re.IGNORECASE)


_ROUTER_EVAL_RE = re.compile(r"(^|[\s;&|])(?:python(?:\.exe)?\s+)?scripts/run_router_eval\.py(?:\s|$)", re.IGNORECASE)


def _is_router_eval_command(cmd: str) -> bool:
    normalized = " ".join(cmd.strip().split())
    return bool(_ROUTER_EVAL_RE.search(normalized))


def _extract_dod_commands_from_exec_prompt_archive(text: str) -> list[str]:
    match = re.search(r"(?ms)^Run:\s*\n(?P<body>.*?)(?:^Return:|^After all DoD pass:|\Z)", text)
    if not match:
        return []
    return [line.strip() for line in match.group("body").splitlines() if line.strip()]


def _normalize_command_list(cmds: list[str]) -> list[str]:
    return [" ".join(cmd.strip().split()) for cmd in cmds if cmd.strip()]


def _find_latest_exec_prompt_archive(package_id: str) -> Path | None:
    candidates = sorted(
        ARCHIVE_DIR.glob(f"{package_id.replace('-', '_')}_exec_prompt_quick_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _detect_dod_drift_from_exec_prompt(package_id: str, dod_commands: list[str]) -> tuple[bool, str | None]:
    archived = _find_latest_exec_prompt_archive(package_id)
    if archived is None:
        return False, None
    archived_text = archived.read_text(encoding="utf-8")
    archived_cmds = _normalize_command_list(_extract_dod_commands_from_exec_prompt_archive(archived_text))
    current_cmds = _normalize_command_list(dod_commands)
    if not archived_cmds or not current_cmds or archived_cmds == current_cmds:
        return False, None
    return (
        True,
        f"archived={archived.relative_to(ROOT)} | archived_dod={archived_cmds} | current_dod={current_cmds}",
    )


def _provider_prereq_blockers(package_id: str, dod_commands: list[str]) -> list[str]:
    blockers: list[str] = []
    for cmd in dod_commands:
        if _is_router_eval_command(cmd) and not os.getenv("OPENAI_API_KEY"):
            blockers.append(
                f"{package_id}: '{cmd}' requires OPENAI_API_KEY for live router eval"
            )
    return blockers


def _read_execution_contract(package_id: str) -> str | None:
    path = TEAM_ARTIFACTS / package_id / "execution_contract.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _execution_contract_content_blockers(text: str | None) -> list[str]:
    if text is None:
        return []
    lower = text.lower()
    plan_only_signals = (
        "i'll start",
        "i will start",
        "i\u2019ll start",
        "i\u2018ll start",
        "i`ll start",
        "i'll create",
        "i will create",
        "i'll read",
        "i will read",
        "i'll execute",
        "i will execute",
        "read the orchestration file",
        "cat archive/team_artifacts",
        'echo "started"',
        "echo 'started'",
        "set-content",
        "out-file",
        "get-content",
    )
    if any(signal in lower for signal in plan_only_signals):
        return [
            "execution_contract.md looks like a command plan, not execution proof"
        ]
    return []


def _verification_only_evidence_blockers(
    package_id: str,
    closure_mode: str,
    *,
    precomputed_text: str | None = None,
    precomputed_validation: tuple[bool, str | None] | None = None,
) -> list[str]:
    if closure_mode == "execution":
        return []
    # For both 'verification_only' and 'unknown' we must have valid evidence —
    # otherwise there is no proof the package was actually delivered.
    text = precomputed_text if precomputed_text is not None else _read_execution_contract(package_id)
    if text is None:
        return [f"missing execution proof file: archive/team_artifacts/{package_id}/execution_contract.md"]
    if precomputed_validation is not None:
        ok, reason = precomputed_validation
    else:
        ok, reason = validate_verification_only_evidence(text, ROOT)
    if ok:
        return []
    return [reason or "verification-only evidence is incomplete"]


def _git_changed_paths_once(root: Path) -> set[str] | None:
    """Read changed paths once (diff + status); None when git unavailable/fails."""
    try:
        res_diff = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root),
        )
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root),
        )
    except OSError:
        return None
    if res_diff.returncode != 0 or res_status.returncode != 0:
        return None
    diff_stdout = getattr(res_diff, "stdout", "") or ""
    status_stdout = getattr(res_status, "stdout", "") or ""
    changed: set[str] = {line.strip() for line in diff_stdout.splitlines() if line.strip()}
    for line in status_stdout.splitlines():
        if len(line) > 3:
            changed.add(line[3:].strip())
    return changed


def _extract_json_object(raw: str) -> dict | None:
    stripped = raw.strip()
    if not stripped:
        return None
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        value = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _semantic_claim_blockers(
    contract: dict[str, str],
    dod_results: list[tuple[str, int, str]],
) -> list[str]:
    outcomes_text = " ".join(
        part for part in (contract.get("OUTCOMES", ""), contract.get("PAIN_POINT", ""), contract.get("PACKAGE_TITLE", ""))
        if part
    ).lower()
    if not outcomes_text:
        return []

    eval_report: dict | None = None
    gate_report: dict | None = None
    for cmd, _, output in dod_results:
        payload = _extract_json_object(output)
        if payload is None:
            continue
        if "tests/eval/run_eval.py" in cmd.replace("\\", "/"):
            eval_report = payload
        elif "scripts/eval_ci_gate.py" in cmd.replace("\\", "/"):
            gate_report = payload

    blockers: list[str] = []
    summary = eval_report.get("summary") if isinstance(eval_report, dict) and isinstance(eval_report.get("summary"), dict) else {}
    if any(token in outcomes_text for token in ("quality-метрик", "quality metric", "quality metrics", "groundedness")):
        if summary.get("answer_groundedness") is None:
            blockers.append("claimed groundedness/quality metrics are unproven: eval report has answer_groundedness = null")
    if any(token in outcomes_text for token in ("tutor coherence", "tutor_coherence", "coherence", "когер")):
        if "tutor" in outcomes_text and summary.get("tutor_coherence") is None:
            blockers.append("claimed tutor coherence metric is unproven: eval report has tutor_coherence = null")

    gate_status = gate_report.get("status") if isinstance(gate_report, dict) else None
    if any(token in outcomes_text for token in ("regress", "baseline", "ci gate")) and gate_report is not None:
        comparable = bool(gate_report.get("comparable_to_baseline"))
        if not comparable:
            blockers.append("claimed regression gate is unproven: gate report skipped baseline comparison")
        if gate_status == "warn":
            blockers.append("claimed regression gate is unproven: gate report ended in warn mode")
    if "json-report" in outcomes_text or "json report" in outcomes_text:
        if gate_report is None:
            blockers.append("claimed JSON gate report is unproven: no JSON output was captured from eval_ci_gate.py")

    return blockers


def _slug(package_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", package_id.lower()).strip("_")


# ---------------------------------------------------------------------------
# DoD runner
# ---------------------------------------------------------------------------

def run_dod(commands: list[str]) -> tuple[bool, list[tuple[str, int, str]]]:
    """Run all DoD commands. Returns (all_passed, [(cmd, exit_code, output), ...])."""
    results: list[tuple[str, int, str]] = []
    for cmd in commands:
        print(f"  $ {cmd}")
        try:
            proc = safe_run_shell(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace", cwd=str(ROOT),
            )
            exit_code = proc.returncode
            output = (proc.stdout + proc.stderr).strip()
        except SandboxViolationError as exc:
            exit_code = 2
            output = f"agent sandbox blocked command: {exc}"
        except Exception as exc:
            exit_code = -1
            output = str(exc)
        status = "PASS" if exit_code == 0 else "FAIL"
        print(f"    → {status} (exit {exit_code})")
        if output:
            for line in output.splitlines()[-5:]:
                print(f"       {line}")
        results.append((cmd, exit_code, output))
    all_passed = all(rc == 0 for _, rc, _ in results)
    return all_passed, results


def _compute_complexity_cell(package_id: str) -> str:
    """Return 'label/score' string for pipeline_metrics complexity column.

    Contract source: ``doc/backlog_registry.yaml`` (SSoT) via ``parse_contract``.
    Returns '?/?' on any error so closure never fails due to this helper.
    """
    try:
        contract = parse_contract_canonical("", package_id)
        if not contract:
            return "?/?"
        cx = classify_package_complexity(contract)
        return f"{cx['label']}/{cx['score']}"
    except Exception:  # noqa: BLE001
        return "?/?"


def _read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_jsonl_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _compute_dod_verdict(package_id: str) -> str:
    cache = _read_json_file(TEAM_ARTIFACTS / package_id / "dod_cache.json")
    result = str(cache.get("result") or "").lower()
    if result == "pass":
        return "PASS"
    if result == "fail":
        return "FAIL"
    return "NO_DOD_CACHE"


def _trigger_rows_for_package(package_id: str) -> list[dict]:
    metrics_dir = TEAM_ARTIFACTS / "_metrics"
    rows: list[dict] = []
    for metrics_name in ("cursor_agent_trigger.jsonl", "deepseek_agent_trigger.jsonl"):
        rows.extend(_read_jsonl_file(metrics_dir / metrics_name))
    needle = f"archive/team_artifacts/{package_id}/execution_contract.md"
    needle_alt = needle.replace("/", "\\")
    return [
        row
        for row in rows
        if needle in str(row.get("contract_path") or "")
        or needle_alt in str(row.get("contract_path") or "")
    ]


def _compute_retry_count(package_id: str) -> str:
    rows = _trigger_rows_for_package(package_id)
    if not rows:
        return "n/a"
    return str(sum(int(row.get("retry_count") or 0) for row in rows))


def _compute_escalation_count(package_id: str) -> str:
    rows = _trigger_rows_for_package(package_id)
    if not rows:
        return "n/a"
    return str(
        sum(
            1
            for row in rows
            if row.get("status") != "finished" or int(row.get("exit_code") or 0) != 0
        )
    )


def _compute_deferred_count(package_id: str) -> int:
    path = TEAM_ARTIFACTS / package_id / "execution_contract.md"
    if not path.exists():
        return 0
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return len(re.findall(r"\bdeferred?\b|отлож", text, flags=re.IGNORECASE))


def _append_pipeline_metrics(package_id: str, today: str, closure_mode: str = "unknown") -> None:
    """Добавить или обновить строку закрытия в ``archive/pipeline_metrics.md``.

    Если для ``package_id`` уже есть строка(и), последняя заменяется (дата и ``sp1_verdict``),
    чтобы повторные закрытия не плодили дубликаты.
    Колонка complexity пересчитывается через classify_package_complexity.
    """
    sp1 = closure_mode          # 'execution' | 'verification_only' | 'unknown'
    sp2 = _compute_dod_verdict(package_id)
    retries = _compute_retry_count(package_id)
    escalations = _compute_escalation_count(package_id)
    deferred = _compute_deferred_count(package_id)
    complexity = _compute_complexity_cell(package_id)
    row  = f"| {package_id} | {today} | {sp1} | {sp2} | {retries} | {escalations} | {deferred} | {complexity} |"
    note = ""

    header = (
        "| Package | Date | sp1_verdict | sp2_verdict | retries | escalations | deferred | complexity |\n"
        "|---------|------|:-----------:|:-----------:|:-------:|:-----------:|:--------:|:----------:|\n"
    )

    if not PIPELINE_METRICS.exists():
        PIPELINE_METRICS.parent.mkdir(parents=True, exist_ok=True)
        PIPELINE_METRICS.write_text(
            "# Pipeline Metrics\n\n" + header + f"{row}{note}\n",
            encoding="utf-8",
        )
        print(f"  ✓ Created archive/pipeline_metrics.md")
        return

    text = PIPELINE_METRICS.read_text(encoding="utf-8")
    row_prefix = f"| {package_id} |"

    lines = text.splitlines()
    matching_idx = [i for i, ln in enumerate(lines) if ln.startswith(row_prefix)]
    if matching_idx:
        idx = matching_idx[-1]
        lines[idx] = row.rstrip()
        PIPELINE_METRICS.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  ℹ pipeline_metrics.md: обновлена строка закрытия для {package_id} ({today}, {sp1})")
        return

    PIPELINE_METRICS.write_text(text.rstrip() + "\n" + row + note + "\n", encoding="utf-8")
    print(f"  ✓ Appended closure row to archive/pipeline_metrics.md")


def run_sync_checks() -> bool:
    """Run roadmap_sync_check.py, backlog_registry_lint.py, and drift guard."""
    # SSoT: regenerate tasklist generated blocks from registry BEFORE roadmap sync,
    # otherwise roadmap_sync_check may observe stale Truth View rows.
    _run_post_close_sync()

    checks = [
        subprocess.list2cmdline([sys.executable, str(ROOT / "scripts" / "roadmap_sync_check.py")]),
        subprocess.list2cmdline([sys.executable, str(ROOT / "scripts" / "backlog_registry_lint.py")]),
    ]
    print("\n→ Running sync checks …")
    passed, results = run_dod(checks)

    return passed


def _run_post_close_sync() -> None:
    """Rebuild user_stories_index.json and regenerate cjm/user_stories sections.

    Runs rebuild_user_stories_index.py --write and backlog_registry_lint.py --sync-from-index --write-sync.
    Non-blocking: failures are printed as warnings so they don't prevent package closure.
    """
    sync_steps = [
        [sys.executable, "scripts/rebuild_user_stories_index.py", "--write"],
        [sys.executable, "scripts/backlog_registry_lint.py", "--sync-from-index", "--write-sync"],
    ]
    print("\n→ Post-close sync (rebuild index + regenerate docs) …")
    for cmd in sync_steps:
        print(f"  $ {' '.join(cmd)}")
        try:
            result = safe_run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
            )
            if result.returncode == 0:
                output = (result.stdout + result.stderr).strip()
                if output:
                    for line in output.splitlines()[-3:]:
                        print(f"    {line}")
                print(f"    → PASS")
            else:
                print(f"    ⚠ [non-blocking] exit {result.returncode}: {cmd}")
                for line in (result.stdout + result.stderr).strip().splitlines()[-3:]:
                    print(f"    {line}")
        except Exception as exc:  # noqa: BLE001
            print(f"    ⚠ [non-blocking] sync step failed: {exc}")



def _build_registry_entry(
    package_id: str,
    contract: dict,
    us_ids: list[str],
    today: str,
) -> str:
    """Build a minimal YAML entry for a package that was never pre-registered."""
    cjm_raw = contract.get("CJM", "")
    cjm_list = f'["{cjm_raw}"]' if cjm_raw else "[]"

    us_list = "[" + ", ".join(f'"{u}"' for u in us_ids) + "]" if us_ids else "[]"

    # Use first outcome line as the 'blocks' description
    outcomes_raw = contract.get("OUTCOMES", "") or contract.get("GOAL", "")
    first_outcome = outcomes_raw.splitlines()[0].lstrip("- ").strip() if outcomes_raw else ""
    blocks_text = (first_outcome[:120] + "…") if len(first_outcome) > 120 else first_outcome
    blocks_text = blocks_text.replace('"', "'")

    write_set_raw = contract.get("WRITE_SET_MAX", "5")
    try:
        write_set_num = int(str(write_set_raw).split()[0])
    except (ValueError, AttributeError):
        write_set_num = 5

    return (
        f"\n"
        f"  - id: {package_id}\n"
        f"    status: closed\n"
        f"    cjm_moments: {cjm_list}\n"
        f"    user_stories: {us_list}\n"
        f"    impact: loop-improvement\n"
        f"    blocks: \"{blocks_text}\"\n"
        f"    depends_on: []\n"
        f"    cost_estimate: S\n"
        f"    write_set_max: {write_set_num}\n"
        f"    read_set_hint: []\n"
        f"    exit_artifact: \"doc/closed_iterations.md\"\n"
        f"    re_entry_condition: null\n"
        f"    created: {today}\n"
        f"    last_review: {today}\n"
        f"    notes: \"Auto-registered on close {today} (created by agent in PLAN_NEXT).\"\n"
    )


def update_backlog_registry(
    text: str,
    package_id: str,
    contract: dict | None = None,
    us_ids: list[str] | None = None,
    today: str | None = None,
) -> str:
    """Change status to closed for the matching item.

    If the package is not found (agent-created in PLAN_NEXT), auto-appends a
    minimal closed entry so the registry stays complete.
    """
    lines = text.splitlines(keepends=True)
    in_item = False
    status_updated = False
    found = False
    result: list[str] = []
    for line in lines:
        id_match = re.match(r"(\s*-\s+id:\s*)(.+)", line)
        if id_match:
            # Strip inline comments and whitespace before comparing (BUG-06 fix).
            raw_id = re.split(r"\s*#", id_match.group(2))[0].strip()
            in_item = (
                raw_id == package_id
                or raw_id == f"epoch-{package_id}"
                or raw_id == package_id.removeprefix("epoch-")
            )
            if in_item:
                found = True
            status_updated = False
        if in_item and not status_updated:
            status_match = re.match(r"(\s+status:\s+)(\S+)(.*)", line)
            if status_match and status_match.group(2) != "closed":
                line = f"{status_match.group(1)}closed{status_match.group(3)}\n"
                status_updated = True
        result.append(line)

    if not found:
        # Pre-check via regex: catches comment-trailing or prefix-variant ids
        # that the line-by-line parser may have missed (BUG-06 guard against duplicates).
        _id_variants = {
            package_id,
            f"epoch-{package_id}",
            package_id.removeprefix("epoch-"),
        }
        _pre_pattern = (
            r"^\s*-\s+id:\s+("
            + "|".join(re.escape(v) for v in _id_variants)
            + r")\s*(?:#.*)?$"
        )
        if re.search(_pre_pattern, "".join(result), re.MULTILINE):
            print(
                f"  ⚠ '{package_id}' found in registry via regex scan but status was not "
                f"updated by line parser (trailing comment or whitespace on id: line). "
                f"Manual status update may be needed.",
                file=sys.stderr,
            )
        elif contract is not None and today is not None:
            entry = _build_registry_entry(package_id, contract, us_ids or [], today)
            result.append(entry)
            print(
                f"  ✅ Auto-registered '{package_id}' in backlog_registry.yaml "
                f"(was created by agent in PLAN_NEXT).",
            )
        else:
            print(
                f"  ⚠ [RISK] '{package_id}' not found in backlog_registry.yaml — skipping.\n"
                f"    Cause: package was created by the agent but never pre-registered.\n"
                f"    Fix: add the entry manually to doc/backlog_registry.yaml and re-run lint.",
                file=sys.stderr,
            )
    return "".join(result)


# ---------------------------------------------------------------------------
# User story .md updater
# ---------------------------------------------------------------------------

def _us_frontmatter_field(text: str, key: str) -> str | None:
    """Return a YAML frontmatter scalar value or None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    match = re.search(rf'^{re.escape(key)}:\s*"([^"]*)"', text[3:end], re.MULTILINE)
    return match.group(1).strip() if match else None


def _us_already_covered_by_other(text: str, package_id: str) -> bool:
    """True when US is already closed and owned by a different package."""
    if _us_frontmatter_field(text, "status") != "closed":
        return False
    existing = _us_frontmatter_field(text, "covered_by")
    return bool(existing and existing != package_id)


def update_us_file(text: str, package_id: str, today: str) -> str:
    """Update YAML frontmatter: set status=closed, covered_by, closed_date."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    frontmatter = text[3:end]
    body = text[end:]

    def _set_field(fm: str, key: str, value: str) -> str:
        pattern = re.compile(rf'^({re.escape(key)}:\s*).*$', re.MULTILINE)
        if pattern.search(fm):
            return pattern.sub(rf'\g<1>"{value}"', fm)
        return fm + f'\n{key}: "{value}"'

    frontmatter = _set_field(frontmatter, "status", "closed")
    frontmatter = _set_field(frontmatter, "covered_by", package_id)
    frontmatter = _set_field(frontmatter, "closed_date", today)
    return "---" + frontmatter + body


# ---------------------------------------------------------------------------
# user_stories_index.json updater
# ---------------------------------------------------------------------------

def update_us_index(text: str, us_ids: list[str], package_id: str, today: str) -> str:
    """Update status/covered_by/closed_date for matching US items."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  ⚠ Could not parse user_stories_index.json: {exc}", file=sys.stderr)
        return text

    ids_upper = {uid.upper() for uid in us_ids}
    for item in data.get("items", []):
        if item.get("us_id", "").upper() not in ids_upper:
            continue
        existing = str(item.get("covered_by") or "").strip()
        if item.get("status") == "closed" and existing and existing != package_id:
            continue
        item["status"] = "closed"
        item["covered_by"] = package_id
        item["closed_date"] = today
    data["generated"] = today
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# closed_iterations.md updater
# ---------------------------------------------------------------------------

def _build_closed_entry(
    contract: dict[str, str],
    today: str,
    dod_results: list[tuple[str, int, str]],
    closure_mode: str = "unknown",
) -> str:
    package_id = _clean(contract.get("PACKAGE_ID", ""))
    title = _clean(contract.get("PACKAGE_TITLE", package_id))
    outcomes_raw = _clean(contract.get("OUTCOMES", ""))
    # Build goal line from PAIN_POINT or OUTCOMES
    pain = _clean(contract.get("PAIN_POINT", ""))
    goal_text = pain if pain else (outcomes_raw[:200] if outcomes_raw else title)

    # Verification commands
    dod_cmds = [cmd for cmd, _, _ in dod_results] if dod_results else _extract_dod_commands(contract.get("DOD_COMMANDS", ""))
    dod_inline = ", ".join(f"`{c}`" for c in dod_cmds) if dod_cmds else "(see contract)"

    # Archive references
    pkg_slug = _slug(package_id)
    exec_files = sorted(ARCHIVE_DIR.glob(f"{pkg_slug}*exec*"), key=lambda p: p.stat().st_mtime)
    plan_files = sorted(ARCHIVE_DIR.glob(f"{pkg_slug}*planning*"), key=lambda p: p.stat().st_mtime)
    archive_refs: list[str] = []
    if exec_files:
        archive_refs.append(f"`archive/agent_prompts/{exec_files[-1].name}`")
    if plan_files:
        archive_refs.append(f"`archive/agent_prompts/{plan_files[-1].name}`")
    team_dir = TEAM_ARTIFACTS / package_id
    if team_dir.exists():
        archive_refs.append(f"`archive/team_artifacts/{package_id}/`")

    all_passed = all(rc == 0 for _, rc, _ in dod_results) if dod_results else None
    verification_note = (
        "all DoD commands passed" if all_passed
        else "DoD results mixed — see individual test output"
        if all_passed is False
        else "DoD not run during closure"
    )

    archive_line = (
        f"- Archive: {', '.join(archive_refs)}."
        if archive_refs
        else "- Archive: see `archive/agent_prompts/` and `archive/team_artifacts/`."
    )

    return (
        f"### {package_id} — {today}\n"
        f"\n"
        f"- Goal: {goal_text}\n"
        f"- Delivered: {outcomes_raw[:300] if outcomes_raw else title}\n"
        f"- Mode: {closure_mode}.\n"
        f"- Verification: {verification_note}.\n"
        f"- Verification commands: {dod_inline}.\n"
        f"{archive_line}\n"
    )


def update_closed_iterations(
    text: str,
    contract: dict[str, str],
    today: str,
    dod_results: list[tuple[str, int, str]],
    closure_mode: str = "unknown",
) -> str:
    """Append a new ### entry at the end of closed_iterations.md."""
    package_id = _clean(contract.get("PACKAGE_ID", ""))
    # Deduplicate by package_id only (not date) so re-running --post-agent on a
    # later day does not create a second closure entry for the same package.
    if re.search(rf"^### {re.escape(package_id)} —", text, re.MULTILINE):
        return text
    entry = _build_closed_entry(contract, today, dod_results, closure_mode)
    return text.rstrip() + "\n\n" + entry



# ---------------------------------------------------------------------------
# changelog.md updater
# ---------------------------------------------------------------------------

def update_changelog(text: str, contract: dict[str, str], today: str, us_ids: list[str]) -> str:
    """Prepend a new ## entry after the # header line."""
    package_id = _clean(contract.get("PACKAGE_ID", ""))

    # Do not add if entry for today+package already present
    marker = f"## {today} ({package_id} closure)"
    if marker in text:
        return text

    us_note = (
        f"`{', '.join(us_ids)}` marked closed in `doc/user_stories/`"
        if us_ids else "no linked US files"
    )
    entry = (
        f"{marker}\n"
        f"\n"
        f"- **Roadmap closure:** `{package_id}` moved to closed; contract removed from `doc/tasklist.md`; "
        f"details in `doc/closed_iterations.md`.\n"
        f"- **US lifecycle sync:** {us_note} and `doc/user_stories_index.json`.\n"
        f"- **Registry sync:** `doc/backlog_registry.yaml` marks the package `closed`.\n"
        f"\n"
    )

    # Insert after first # heading
    first_heading_end = text.find("\n", text.find("# ")) + 1
    if first_heading_end <= 0:
        return entry + text

    # Skip blank lines after heading
    insert_at = first_heading_end
    while insert_at < len(text) and text[insert_at] in ("\n",):
        insert_at += 1

    return text[:first_heading_end] + "\n" + entry + text[insert_at:]


def _close_without_dod_approved(args: ClosePackageArgs, *, reason: str) -> bool:
    """Return True if HITL policy allows closing without running DoD."""
    try:
        assert_approved(
            "close_without_dod",
            approved=args.approve_close_without_dod,
        )
    except PermissionError as exc:
        print(
            "\n[BLOCKED] Package closure refused because DoD would be skipped.\n"
            f"  - {reason}\n"
            f"  - {exc}\n"
            "  Fix: add DoD commands to the contract, run closure with DoD, or pass "
            "`--approve-close-without-dod` after explicit human approval.",
            file=sys.stderr,
        )
        return False
    return True


def gate_team_artifacts_for_close(package_id: str, args: ClosePackageArgs) -> int:
    """Validate orchestrator markdown artifacts before closure.

    Returns 0 if OK to proceed, 1 if blocked (unless --force).
    Skips when ``archive/team_artifacts/<id>/`` has no canonical pipeline files.
    """
    if args.skip_team_artifacts_check:
        print("→ Team artifacts gate skipped (--skip-team-artifacts-check)")
        return 0
    team_dir = TEAM_ARTIFACTS / package_id
    if not team_dir.is_dir():
        return 0
    canonical = _team_art.iter_artifact_files(team_dir)
    if not canonical:
        print("→ Team artifacts gate skipped (no canonical pipeline *.md files)")
        return 0
    print("\n→ Team artifacts gate …")
    result = _team_art.validate_artifacts_directory(team_dir)
    for w in result.warnings:
        print(f"  WARN: {w}", file=sys.stderr)
    for e in result.errors:
        print(f"  ERROR: {e}", file=sys.stderr)
    if _team_art.validation_failed(result, strict=args.team_artifacts_strict):
        if args.force:
            print(
                "  ⚠ Team artifacts gate failed; continuing (--force)",
                file=sys.stderr,
            )
            return 0
        print(
            "\nFix team artifact markdown, or pass --skip-team-artifacts-check "
            "(or --force with caution). See: scripts/validate_team_artifact.py",
            file=sys.stderr,
        )
        return 1
    print(f"✓ Team artifacts gate passed ({len(canonical)} file(s))")
    return 0


# ---------------------------------------------------------------------------
# In-process close implementation (callable from run_autonomous)
# ---------------------------------------------------------------------------

def run_close_package_impl(args: ClosePackageArgs) -> int:
    """
    Core close_package logic extracted for in-process calls.

    Args:
        args: ClosePackageArgs with package, dry_run, verify_only, skip_dod, force, closure_mode

    Returns:
        Exit code (0 on success, non-zero on error)
    """
    timer = PhaseTimer()
    try:
        return _run_close_package_impl_timed(args, timer)
    finally:
        timer.flush()


def _run_close_package_impl_timed(args: ClosePackageArgs, timer: PhaseTimer) -> int:
    # ── Preconditions ─────────────────────────────────────────────────────
    if not TASKLIST.exists():
        print(f"ERROR: {TASKLIST} not found", file=sys.stderr)
        return 2

    # ── Select package ────────────────────────────────────────────────────
    rows = parse_truth_view_from_registry()
    if args.package:
        package_id = args.package
        row = _select_package(rows, package_id)
        status = row["status"] if row else (_registry_item_status(package_id) or "unknown")
    else:
        if not rows:
            print(
                "⚠ No active packages (wip/ready/open/proposed) in backlog_registry.yaml Truth View.\n"
                "Specify one with --package <PACKAGE_ID> or sync the registry.",
                file=sys.stderr,
            )
            return 1
        selected = _select_package(rows, None)
        if not selected:
            print(
                "⚠ No ready/WIP/proposed package found in backlog_registry.yaml.\n"
                "Specify one with --package <PACKAGE_ID>.",
                file=sys.stderr,
            )
            return 1
        package_id = selected["package"]
        status = selected["status"]

    print(f"→ Package : {package_id}  (status: {status})")

    # ── Parse contract ────────────────────────────────────────────────────
    contract = _parse_contract("", package_id)
    if not contract:
        print(
            f"ERROR: contract for '{package_id}' not found in backlog_registry.yaml.\n"
            f"Cannot auto-generate closure text without a contract. Use --package to specify a "
            f"different package, or add the package contract to backlog_registry.yaml first.",
            file=sys.stderr,
        )
        return 2

    dod_raw = contract.get("DOD_COMMANDS", "")
    dod_commands = _extract_dod_commands(dod_raw)
    us_raw = contract.get("USER_STORIES", "n/a (infra package)")
    us_ids = _extract_us_ids(us_raw)
    drifted, drift_reason = _detect_dod_drift_from_exec_prompt(package_id, dod_commands)
    provider_blockers = _provider_prereq_blockers(package_id, dod_commands)

    if not dod_raw:
        print(
            "  ⚠ [RISK] DOD_COMMANDS not found in contract — DoD will be skipped.\n"
            "    Ensure the contract uses '- **DoD commands:** `pytest ...`' format.",
            file=sys.stderr,
        )
    if drifted:
        print(
            "\n[BLOCKED] Package closure refused because DoD changed after the execution prompt was generated.\n"
            f"  {drift_reason}\n"
            "  Policy: direct close_package cannot close a package after silent DoD weakening.",
            file=sys.stderr,
        )
        return 2
    if provider_blockers:
        print(
            "\n[BLOCKED] Package closure refused because required provider prerequisites are missing.\n"
            + "\n".join(f"  - {line}" for line in provider_blockers)
            + "\n  Policy: live eval DoD cannot be downgraded during closure.",
            file=sys.stderr,
        )
        return 2
    exec_contract_text = _read_execution_contract(package_id)
    proof_content_blockers = _execution_contract_content_blockers(exec_contract_text)
    if proof_content_blockers:
        print(
            "\n[BLOCKED] Package closure refused because execution proof is not substantive.\n"
            + "\n".join(f"  - {line}" for line in proof_content_blockers),
            file=sys.stderr,
        )
        return 2
    evidence_validation: tuple[bool, str | None] | None = None
    if exec_contract_text is not None:
        evidence_validation = validate_verification_only_evidence(exec_contract_text, ROOT)
    changed_all = _git_changed_paths_once(ROOT)
    pre_src = (
        closure_mode_src_from_git_paths(changed_all)
        if changed_all is not None
        else None
    )

    # Self-detect closure mode from git + contract + execution_contract.md.
    # Do NOT trust the caller's --closure-mode alone: resolve_closure_mode applies
    # the same HEAD/evidence upgrades as run_autonomous --post-agent.
    closure_resolution = _resolve_closure_mode(
        package_id,
        contract,
        ROOT,
        precomputed_src_changed=pre_src,
        precomputed_evidence_valid=evidence_validation[0] if evidence_validation is not None else None,
        exec_contract_text=exec_contract_text,
    )
    detected_mode = closure_resolution.mode
    upgrade_notice = format_closure_mode_upgrade_notice(closure_resolution)
    if upgrade_notice:
        print(upgrade_notice)
    effective_mode = args.closure_mode
    if args.closure_mode == "unknown":
        effective_mode = detected_mode
    elif args.closure_mode == "execution" and detected_mode in ("verification_only", "unknown"):
        print(
            "\n[BLOCKED] Package closure refused: caller claimed --closure-mode=execution\n"
            f"but pipeline self-detection returned '{detected_mode}' "
            f"(base mode: '{closure_resolution.base_mode}').\n"
            "  No write-set files were modified in the working tree, HEAD commit, or\n"
            "  valid pre-existing delivery evidence. Either make the real changes\n"
            "  or supply a verification_only execution_contract.md with a valid commit SHA.",
            file=sys.stderr,
        )
        return 2
    evidence_blockers = _verification_only_evidence_blockers(
        package_id,
        effective_mode,
        precomputed_text=exec_contract_text,
        precomputed_validation=evidence_validation,
    )
    if evidence_blockers:
        print(
            "\n[BLOCKED] Package closure refused because verification-only evidence is incomplete.\n"
            + "\n".join(f"  - {line}" for line in evidence_blockers)
            + "\n  Policy: "
            + verification_only_policy_guidance(indent="  "),
            file=sys.stderr,
        )
        return 2
    run_id = os.environ.get(RUN_ID_ENV, "").strip() or None
    gates = _run_quality_gates(
        package_id=package_id,
        run_id=run_id,
        root=ROOT,
        include_proof=bool(run_id),
    )
    for g in gates:
        if g.ok:
            continue
        if g.name == "pipeline_guard":
            print(g.followup_message or g.reason, file=sys.stderr)
        else:
            print(
                "\n[BLOCKED] Package closure refused because proof bundle validation failed.\n"
                f"  - {g.reason}",
                file=sys.stderr,
            )
        return 2
    # Propagate detected mode back to args so downstream closed_iterations
    # and pipeline_metrics record the truthful mode, not a caller-lied one.
    args.closure_mode = effective_mode
    if not us_ids and "n/a" not in us_raw.lower() and "infra" not in us_raw.lower():
        print(
            f"  ⚠ [RISK] No US-X.Y IDs extracted from USER_STORIES (got: '{us_raw[:60]}').\n"
            f"    User story files will NOT be closed. Check contract format.",
            file=sys.stderr,
        )

    today = date.today().isoformat()
    print(f"→ Date    : {today}")
    print(f"→ US IDs  : {us_ids if us_ids else ['none']}")
    print(f"→ DoD     : {len(dod_commands)} command(s)")

    # ── Run DoD ───────────────────────────────────────────────────────────
    if not args.verify_only:
        if args.skip_dod and not _close_without_dod_approved(
            args, reason="--skip-dod was requested"
        ):
            return 2
        if not args.skip_dod and not dod_commands and not _close_without_dod_approved(
            args, reason="contract has no DOD_COMMANDS"
        ):
            return 2

    dod_results: list[tuple[str, int, str]] = []
    with timer.phase("dod_run") as _dod_ph:
      if args.skip_dod:
        print("→ DoD check skipped (--skip-dod)")
      elif dod_commands:
        print("\n→ Running DoD …")
        all_passed, dod_results = run_dod(dod_commands)
        if all_passed:
            print(f"\n✓ DoD: all {len(dod_commands)} command(s) passed")
        else:
            failed = [cmd for cmd, rc, _ in dod_results if rc != 0]
            print(f"\n✗ DoD FAILED: {len(failed)} of {len(dod_commands)} command(s) failed:", file=sys.stderr)
            for cmd in failed:
                print(f"  - {cmd}", file=sys.stderr)
            if not args.force:
                print(
                    "\nFix the failing DoD before closing, or use --force to close anyway.",
                    file=sys.stderr,
                )
                _dod_ph["rc"] = 1
                return 1
            print("  ⚠ Continuing anyway (--force)", file=sys.stderr)
      else:
        print("→ DoD check skipped (no DOD_COMMANDS in contract)")

    semantic_blockers = _semantic_claim_blockers(contract, dod_results)
    if semantic_blockers:
        print(
            "\n[BLOCKED] Package closure refused because the claimed Delivered outcomes are\n"
            "not supported by the observed DoD artifacts.\n"
            + "\n".join(f"  - {line}" for line in semantic_blockers)
            +             "\n  Policy: structural smoke checks cannot be used to claim delivery of stronger capabilities.",
            file=sys.stderr,
        )
        return 2

    gate_rc = gate_team_artifacts_for_close(package_id, args)
    if gate_rc != 0:
        return gate_rc

    if args.verify_only:
        print("\n(--verify-only: no files modified)")
        return 0

    # ── Apply updates ─────────────────────────────────────────────────────
    print(f"\n→ {'DRY RUN — ' if args.dry_run else ''}Updating files …")
    with timer.phase("doc_updates"):
        changes: list[tuple[str, str, str]] = []  # (path, old_text, new_text)

        # 1. backlog_registry.yaml
        if BACKLOG_REGISTRY.exists():
            br_text = BACKLOG_REGISTRY.read_text(encoding="utf-8")
            new_br = update_backlog_registry(br_text, package_id, contract, us_ids, today)
            changes.append((str(BACKLOG_REGISTRY), br_text, new_br))
        else:
            print(f"  ⚠ {BACKLOG_REGISTRY} not found — skipping")

        # 2. user_stories/*.md
        for us_id in us_ids:
            us_path = US_DIR / f"{us_id.lower()}.md"
            if us_path.exists():
                us_text = us_path.read_text(encoding="utf-8")
                if _us_already_covered_by_other(us_text, package_id):
                    print(
                        f"  ℹ {us_id}: already covered by another package — skipping overwrite"
                    )
                    continue
                new_us = update_us_file(us_text, package_id, today)
                changes.append((str(us_path), us_text, new_us))
            else:
                print(f"  ⚠ {us_path} not found — skipping")

        # 3. user_stories_index.json
        if US_INDEX.exists() and us_ids:
            idx_text = US_INDEX.read_text(encoding="utf-8")
            new_idx = update_us_index(idx_text, us_ids, package_id, today)
            changes.append((str(US_INDEX), idx_text, new_idx))

        # 4. closed_iterations.md
        if CLOSED_ITERATIONS.exists():
            ci_text = CLOSED_ITERATIONS.read_text(encoding="utf-8")
            new_ci = update_closed_iterations(ci_text, contract, today, dod_results, args.closure_mode)
            changes.append((str(CLOSED_ITERATIONS), ci_text, new_ci))

        # 5. changelog.md
        if CHANGELOG.exists():
            cl_text = CHANGELOG.read_text(encoding="utf-8")
            new_cl = update_changelog(cl_text, contract, today, us_ids)
            changes.append((str(CHANGELOG), cl_text, new_cl))

        modified = [(p, o, n) for p, o, n in changes if o != n]
        unchanged = [p for p, o, n in changes if o == n]

        for p, _, _ in modified:
            rel = Path(p).relative_to(ROOT)
            print(f"  {'[DRY] ' if args.dry_run else ''}✓ {rel}")
        for p in unchanged:
            rel = Path(p).relative_to(ROOT)
            print(f"  — {rel} (no change needed)")

        if not args.dry_run:
            for p, _, new_text in modified:
                Path(p).write_text(new_text, encoding="utf-8")

    if args.dry_run:
        print("\n(dry run — no files written)")
        return 0

    # ── Sync checks ───────────────────────────────────────────────────────
    if args.skip_sync_checks:
        print(f"\n✓ Package {package_id} closed successfully (sync checks skipped).")
        _append_pipeline_metrics(package_id, today, args.closure_mode)
        return 0

    with timer.phase("roadmap_sync_check") as _sync_ph:
        sync_ok = run_sync_checks()
        _sync_ph["rc"] = 0 if sync_ok else 2
    if sync_ok:
        print(f"\n✓ Sync checks passed")
        print(f"\n✓ Package {package_id} closed successfully.")
        _append_pipeline_metrics(package_id, today, args.closure_mode)
        print(f"\n  Next: select the next package with:")
        print(f"  python scripts/generate_next_prompt.py --list")
    else:
        print(
            f"\n⚠ Sync checks FAILED after closure. Review the errors above.",
            file=sys.stderr,
        )
        print(f"  The 6 files were already written. Fix sync issues manually.")
        return 2

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package", "-p", help="Explicit PACKAGE_ID (skip auto-detect)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would change; do not write files")
    parser.add_argument("--verify-only", action="store_true", help="Run DoD only; do not modify any files")
    parser.add_argument("--skip-dod", action="store_true", help="Skip DoD check and close immediately")
    parser.add_argument(
        "--approve-close-without-dod",
        action="store_true",
        help="Confirm explicit human approval for closing when DoD is skipped or absent",
    )
    parser.add_argument(
        "--skip-team-artifacts-check",
        action="store_true",
        help="Skip validate_team_artifact gate on archive/team_artifacts/<PACKAGE_ID>/",
    )
    parser.add_argument(
        "--team-artifacts-strict",
        action="store_true",
        help="Treat team artifact warnings as errors (stricter gate)",
    )
    parser.add_argument("--force", action="store_true", help="Close even if DoD fails (use with caution)")
    parser.add_argument(
        "--closure-mode",
        choices=["execution", "verification_only", "unknown"],
        default="unknown",
        help="How the package was closed: execution (code written), verification_only (pre-existing code verified), unknown",
    )
    cli_args = parser.parse_args()

    args = ClosePackageArgs(
        package=cli_args.package,
        dry_run=cli_args.dry_run,
        verify_only=cli_args.verify_only,
        skip_dod=cli_args.skip_dod,
        force=cli_args.force,
        closure_mode=cli_args.closure_mode,
        approve_close_without_dod=cli_args.approve_close_without_dod,
        skip_team_artifacts_check=cli_args.skip_team_artifacts_check,
        team_artifacts_strict=cli_args.team_artifacts_strict,
    )

    return run_close_package_impl(args)


if __name__ == "__main__":
    configure_stdio_utf8()
    sys.exit(main())
