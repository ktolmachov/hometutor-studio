#!/usr/bin/env python3
"""
generate_orchestration_prompt.py — Automated orchestration prompt generation.

Replaces the manual Phases 1–5 of generate_orchestration_prompt.md:
  Phase 1:   discover active package from backlog_registry.yaml
  Phase 2:   pre-extract context (US acceptance, CJM moment, recent closed)
  Phase 2.5: detect Ops Impact triggers (RAGOps / LLMOps / MLOps / Performance)
             — sets {{OPS_GATE_NEEDED}} and {{OPS_ROLES_TRIGGERED}}
  Phase 3:   load orchestrator_template.md + agent adapter
  Phase 4:   fill all {{PLACEHOLDERS}} programmatically
  Phase 5:   save + print ready-to-paste orchestration prompt

Usage:
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent claude_code
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent codex
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent continue
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai --package epoch-foo
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai --dry-run
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai --force
    .\.venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --list

Exit codes:
    0 — prompt generated OK
    1 — no active package / work already started (use --force to override)
    2 — parse error or missing required file
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# UTF-8 stdio: только в CLI (main). Импорт модуля из тестов не должен менять sys.stdout (pytest capture).

# Import canonical utilities from shared library (avoids duplicating parsing logic).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _perf_timer import PhaseTimer  # noqa: E402
from ops_triggers import detect_ops_triggers, format_triggered_summary  # noqa: E402
from prompt_utils import (  # noqa: E402
    AUTONOMOUS_AGENT_CHOICES,
    budget_profile_choices,
    ensure_utf8_stdio,
    extract_dod_commands as _extract_dod_commands_canonical,
    detect_work_state   as _detect_work_state_canonical,
    extract_recent_closed,
    get_budget_profile,
    parse_truth_view_from_registry as _parse_truth_view_from_registry_shared,
    agent_adapters_map,
    resolve_agent_adapter_name,
)
ROOT             = Path(__file__).resolve().parents[1]
DISPLAY_PYTHON   = r".\.venv\Scripts\python.exe"
TEMPLATE_PATH    = ROOT / "doc" / "team_workflow" / "orchestrator_template.md"
TEAM_ARTIFACTS   = ROOT / "archive" / "team_artifacts"
AGENT_PROMPTS    = ROOT / "archive" / "agent_prompts"
PIPELINE_METRICS = ROOT / "archive" / "pipeline_metrics.md"

AGENT_ADAPTERS = agent_adapters_map()

# Canonical status priority (matches prompt_utils.STATUS_PRIORITY)
STATUS_PRIORITY = ["wip", "WIP", "ready", "open", "proposed"]

MAX_INJECT_CHARS = 3000


# ---------------------------------------------------------------------------
# Shared parsing (mirrors generate_next_prompt.py — intentionally standalone)
# ---------------------------------------------------------------------------

def _strip_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def _clean(v: str) -> str:
    return v.strip().strip("`").strip()


def _clean_inline(v: str) -> str:
    """Remove all backtick markup (e.g. `word` → word) for display use."""
    return re.sub(r"`([^`]*)`", r"\1", v.strip()).strip()


def _adapter_first_line(v: str) -> str:
    """Return the first non-empty line of a multi-line adapter value (for inline use)."""
    for line in v.strip().splitlines():
        if line.strip():
            return line.strip()
    return v.strip()


def _substitute_adapter_placeholders(value: str, *, package_id: str, artifacts_dir: str) -> str:
    return (
        value
        .replace("{{PACKAGE_ID}}", package_id)
        .replace("{{ARTIFACTS_DIR}}", artifacts_dir)
    )


def _select_package(rows: list[dict[str, str]], explicit: str | None) -> dict[str, str] | None:
    if explicit:
        for r in rows:
            if r["package"] == explicit:
                return r
        return None
    for prio in STATUS_PRIORITY:
        for r in rows:
            if r["status"].lower() == prio:
                return r
    return None


def _parse_contract_from_registry(package_id: str) -> dict[str, str] | None:
    """Build contract dict directly from backlog_registry.yaml (SSoT).

    Returns None if the package is not found in the registry.
    """
    try:
        import yaml as _yaml
    except ImportError:
        return None
    registry_path = ROOT / "doc" / "backlog_registry.yaml"
    if not registry_path.exists():
        return None
    try:
        data = _yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("items") or []
    targets = {package_id, f"epoch-{package_id}", package_id.removeprefix("epoch-")}
    item = next((it for it in items if isinstance(it, dict) and it.get("id") in targets), None)
    if not item:
        return None

    dod_cmds = item.get("dod_commands") or []
    if isinstance(dod_cmds, str):
        dod_cmds = [dod_cmds]
    dod_str = "\n".join(dod_cmds) if dod_cmds else "(add dod_commands to backlog_registry.yaml)"

    outcomes = str(item.get("blocks") or item.get("exit_artifact") or item.get("notes") or "")
    read_set = item.get("read_set_hint") or []
    if isinstance(read_set, str):
        read_set = [read_set]

    us_list = ", ".join(item.get("user_stories") or [])
    cjm_moments = item.get("cjm_moments") or []
    cjm = ", ".join(cjm_moments) if cjm_moments else "unknown"

    deliverables = item.get("deliverables") or []
    if isinstance(deliverables, str):
        deliverables = [deliverables]

    return {
        "PACKAGE_ID":      str(item.get("id", package_id)),
        "PACKAGE_TITLE":   outcomes[:120] or str(item.get("id", "")),
        "USER_STORIES":    us_list,
        "CJM_STAGE":       cjm,
        "PAIN_POINT":      "",
        "DOD_COMMANDS":    dod_str,
        "OUTCOMES":        outcomes,
        "WRITE_SET_MAX":   str(item.get("write_set_max") or 5),
        "DELIVERABLES":    "\n".join(deliverables),
        "TARGET_ARTIFACTS": str(item.get("exit_artifact") or outcomes[:80]),
        "READ_SET_HINT":   "\n".join(read_set),
        "NOTES":           str(item.get("notes") or ""),
        "WAVE_ID":         str(item.get("wave_id") or ""),
        "STATUS":          str(item.get("status") or ""),
    }


def _parse_truth_view_from_registry() -> list[dict[str, str]]:
    """Read current package rows from backlog_registry.yaml (SSoT)."""
    return _parse_truth_view_from_registry_shared()


def _parse_contract(_text: str, package_id: str) -> dict[str, str]:
    """Resolve contract from backlog_registry.yaml only."""
    return _parse_contract_from_registry(package_id) or {}


def _extract_dod_commands(raw: str) -> list[str]:
    """Delegate to canonical parser (handles ';' and newline-separated commands)."""
    return _extract_dod_commands_canonical(raw)


def _extract_us_ids(raw: str) -> list[str]:
    return re.findall(r"US-[\d.]+", raw, re.IGNORECASE)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ---------------------------------------------------------------------------
# Work-state detection (mirrors generate_next_prompt.py)
# ---------------------------------------------------------------------------

def _detect_work_state(package_id: str) -> str:
    """Delegate to canonical work-state detector."""
    return _detect_work_state_canonical(package_id)


# ---------------------------------------------------------------------------
# Context extraction (shared logic from generate_next_prompt.py)
# ---------------------------------------------------------------------------

def _read_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"[FILE NOT FOUND: {path.name}]"


def _extract_us_acceptance(us_path: Path) -> str:
    text = _read_safe(us_path)
    if text.startswith("[FILE NOT FOUND"):
        return text
    m = re.search(r"\*\*Acceptance[^:]*:\*\*(.+?)(?=\n#{1,3} |\Z)", text, re.DOTALL)
    if m:
        return m.group(0).strip()[:MAX_INJECT_CHARS]
    m = re.search(r"#{2,4}[^#\n]*Acceptance[^\n]*\n(.+?)(?=\n#{2,4} |\Z)", text, re.DOTALL)
    if m:
        return m.group(0).strip()[:MAX_INJECT_CHARS]
    return "(Acceptance section not found)"


def _extract_cjm_moment(cjm_path: Path, cjm_stage: str) -> str:
    text = _read_safe(cjm_path)
    if text.startswith("[FILE NOT FOUND"):
        return text
    lines = text.splitlines()
    hits: list[str] = []
    for line in lines:
        if cjm_stage.lower() in line.lower() or re.search(re.escape(cjm_stage), line, re.IGNORECASE):
            hits.append(line)
    result = "\n".join(hits[:8]).strip()
    return result[:MAX_INJECT_CHARS] if result else f"(CJM stage '{cjm_stage}' not found in cjm.md)"


def _extract_recent_closed_local(closed_path: Path, n: int = 2) -> str:
    """Local fallback; canonical version is extract_recent_closed() from prompt_utils."""
    text = _read_safe(closed_path)
    if text.startswith("[FILE NOT FOUND"):
        return text
    sections = re.split(r"\n(?=### )", text)
    entries = [s.strip() for s in sections if s.strip().startswith("### ")]
    recent = entries[-n:] if len(entries) >= n else entries
    return "\n\n".join(recent)[:MAX_INJECT_CHARS]


# ---------------------------------------------------------------------------
# Agent adapter parser
# ---------------------------------------------------------------------------

def _parse_adapter(adapter_path: Path) -> dict[str, str]:
    """
    Parse the ```yaml ... ``` block in an agent adapter file.
    Returns a dict of placeholder_key → value (multi-line values joined).
    """
    text = _read_safe(adapter_path)
    # Extract yaml code block
    m = re.search(r"```yaml\n(.*?)```", text, re.DOTALL)
    if not m:
        return {}
    yaml_block = m.group(1)
    lines = yaml_block.splitlines()

    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    is_literal = False  # whether current value is a `|` block

    def _flush():
        if current_key is None:
            return
        if is_literal:
            # Strip common indent from literal block
            block = "\n".join(current_lines)
            # dedent
            min_indent = min(
                (len(l) - len(l.lstrip()) for l in current_lines if l.strip()),
                default=0,
            )
            dedented = "\n".join(l[min_indent:] for l in current_lines)
            result[current_key] = dedented.strip()
        else:
            result[current_key] = " ".join(current_lines).strip().strip("`").strip()

    for line in lines:
        # Top-level key: value  OR  key: |
        key_match = re.match(r"^([A-Z_]+):\s*(.*)", line)
        if key_match:
            _flush()
            current_key = key_match.group(1)
            val = key_match.group(2).strip()
            if val == "|":
                is_literal = True
                current_lines = []
            else:
                is_literal = False
                current_lines = [val] if val else []
        elif current_key is not None:
            current_lines.append(line)

    _flush()
    return result


# ---------------------------------------------------------------------------
# Template filler
# ---------------------------------------------------------------------------

def _fill_template(template: str, placeholders: dict[str, str]) -> str:
    """Replace all {{KEY}} placeholders in template."""
    result = template
    for key, value in placeholders.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def _split_step3_sequential(template: str, agent: str) -> str:
    """
    For agents with MAX_PARALLEL == 1 (Codex): adjust Step 3 heading to indicate SEQUENTIAL.
    Called BEFORE _fill_template so {{MAX_PARALLEL}} placeholder is still present.
    """
    old_heading = "## STEP 3 — Architect + Designer  [PARALLEL if {{MAX_PARALLEL}} > 1]"
    new_heading = "## STEP 3 — Architect + Designer  [SEQUENTIAL — no native parallel agents; 3a → 3b]"
    # Also remove the trailing " [Architect + Designer]:" from PARALLEL_SYNTAX line
    # to avoid duplicate labeling when the syntax block already explains sequencing
    result = template.replace(old_heading, new_heading)
    result = result.replace("{{PARALLEL_SYNTAX}} [Architect + Designer]:", "{{PARALLEL_SYNTAX}}")
    return result


    # NOTE: _inject_step8_close_script() was removed (2026-04-21).
    # orchestrator_template.md Step 8 now directly references close_package.py.
    # The old function tried to patch the template at runtime but the pattern
    # it searched for no longer exists — it was dead code.


# ---------------------------------------------------------------------------
# Write-set helpers (mirror generate_next_prompt — do NOT import that module here:
# it re-wraps sys.stdout/stderr like this file and breaks nested prints/subprocess.)
# ---------------------------------------------------------------------------

def _orc_split_csv_list(value: str, sep: str = ",") -> list[str]:
    parts = re.split(rf"\s*{re.escape(sep)}\s*", value)
    return [p.strip().strip("`").strip() for p in parts if p.strip()]


def _orc_extract_write_set(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.isdigit():
        return []
    if "\n" in raw:
        items = []
        for line in raw.splitlines():
            value = line.strip()
            if value.startswith(("- ", "* ")):
                value = value[2:].strip()
            value = value.strip("`").strip()
            if value:
                items.append(value)
        return items
    return _orc_split_csv_list(raw, sep=",")


_ORC_CONTRACT_PATH_RE = re.compile(
    r"(?:(?:^|[\s|,])((?:app|tests|scripts|src)/\S+?\.(?:py|ts|js|tsx|jsx|yaml|yml|json|md)))"
)


def _orc_extract_contract_paths(text: str) -> list[str]:
    if not text:
        return []
    found = [m.group(1) for m in _ORC_CONTRACT_PATH_RE.finditer(text)]
    return list(dict.fromkeys(found))


# ---------------------------------------------------------------------------
# Orchestration prompt builder
# ---------------------------------------------------------------------------

def _resolved_write_set_files(contract: dict[str, str]) -> list[str]:
    """Derive bounded file paths from WRITE_SET_MAX and registry-derived contract (same rules as resume/execution prompts)."""
    write_set_raw = str(contract.get("WRITE_SET_MAX", "")).strip()
    files = _orc_extract_write_set(write_set_raw)
    if not files and write_set_raw.isdigit():
        touch_text = "\n".join(
            [
                str(contract.get("TARGET_ARTIFACTS", "")),
                str(contract.get("OUTCOMES", "")),
                str(contract.get("NOTES", "")),
                str(contract.get("READ_SET_HINT", "")),
            ]
        )
        files = _orc_extract_contract_paths(touch_text)
        try:
            max_n = int(write_set_raw)
        except ValueError:
            max_n = 0
        if max_n > 0 and len(files) > max_n:
            files = files[:max_n]
    return files


def _write_set_markdown_block(files: list[str]) -> str:
    bullets = (
        "\n".join(f"- `{f}`" for f in files)
        if files
        else "- _(bounded paths not resolved yet — rely on backlog read_set_hint / exit_artifact)_"
    )
    return f"## Write-Set\n\n{bullets}\n"


def build_orchestration_prompt(
    contract: dict[str, str],
    adapter: dict[str, str],
    template_text: str,
    agent: str,
    context: dict[str, str],
    ops_info: dict[str, object] | None = None,
) -> str:
    """Build the final orchestration prompt.

    Args:
        ops_info: optional dict with keys 'gate_needed' (bool), 'roles' (list[str]),
                  'matched_paths' (list[str]). When None, Phase 2.5 is treated as
                  not-run and placeholders default to gate_needed=false / roles="".
                  Backward-compatible: existing callers without ops_info still work.
    """
    package_id    = _clean(contract.get("PACKAGE_ID", ""))
    package_title = _clean(contract.get("PACKAGE_TITLE", package_id))
    cjm_stage_raw = contract.get("CJM_STAGE", "")
    cjm_stage     = _clean_inline(cjm_stage_raw)        # strips all backtick markup
    pain_point    = _clean_inline(contract.get("PAIN_POINT", ""))
    us_raw        = contract.get("USER_STORIES", "n/a")
    outcomes_raw  = _clean_inline(contract.get("OUTCOMES", ""))
    dod_raw       = contract.get("DOD_COMMANDS", "")

    us_ids        = _extract_us_ids(us_raw)
    user_stories  = ", ".join(us_ids) if us_ids else _clean(us_raw)

    # US_FILES: safe file-path reference for use in BEFORE STARTING sections.
    # For infra packages (no real US IDs), avoid generating a non-existent path.
    if us_ids:
        us_files_lines = "\n".join(f"  Read: doc/user_stories/{uid}.md" for uid in us_ids[:4])
    else:
        us_files_lines = (
            "  (infra package — no direct US files; check doc/cjm.md §8 for US references)"
        )

    dod_commands  = _extract_dod_commands(dod_raw)
    dod_formatted = "\n".join(f"  {c}" for c in dod_commands) if dod_commands else "  (see contract)"

    # Format outcomes as numbered list
    outcomes_parts = re.split(r"\s*\d+[.)]\s+", outcomes_raw)
    outcomes_parts = [p.strip() for p in outcomes_parts if p.strip()]
    if outcomes_parts:
        outcomes_str = "\n".join(f"  {i}. {o}" for i, o in enumerate(outcomes_parts, 1))
    else:
        outcomes_str = f"  {outcomes_raw}"

    artifacts_dir = f"archive/team_artifacts/{package_id}"
    cjm_full      = f"{cjm_stage} — {pain_point}" if pain_point else cjm_stage

    max_parallel  = adapter.get("MAX_PARALLEL", "8").strip()
    try:
        max_parallel_int = int(max_parallel)
    except ValueError:
        max_parallel_int = 8

    write_file_value = _substitute_adapter_placeholders(
        adapter.get("WRITE_FILE", "(see agent adapter)"),
        package_id=package_id,
        artifacts_dir=artifacts_dir,
    )
    run_cmd_value = _substitute_adapter_placeholders(
        adapter.get("RUN_CMD", "(see agent adapter)"),
        package_id=package_id,
        artifacts_dir=artifacts_dir,
    )
    agent_spawn_guide = _substitute_adapter_placeholders(
        adapter.get("AGENT_SPAWN", "(see agent adapter)"),
        package_id=package_id,
        artifacts_dir=artifacts_dir,
    )

    # For SAVE/RUN lines: first meaningful line only (no multi-line bleed into the instruction)
    write_file_inline   = _adapter_first_line(write_file_value)
    run_cmd_inline      = _adapter_first_line(run_cmd_value)

    # PARALLEL_SYNTAX may contain {{PACKAGE_ID}} — pre-substitute before inserting
    # so the single-pass _fill_template doesn't miss nested placeholders.
    parallel_syntax_val = (
        adapter.get("PARALLEL_SYNTAX", "(see agent adapter)")
        .replace("{{PACKAGE_ID}}", package_id)
        .replace("{{ARTIFACTS_DIR}}", artifacts_dir)
    )

    # Ops gate placeholders (Phase 2.5). Defaults preserve backward-compat for
    # callers that don't pass ops_info — they get gate_needed=false / roles="".
    ops_info = ops_info or {}
    ops_roles = ops_info.get("roles") or []
    if not isinstance(ops_roles, (list, tuple)):
        ops_roles = []
    ops_gate_needed = bool(ops_info.get("gate_needed")) and bool(ops_roles)
    ops_gate_needed_str = "true" if ops_gate_needed else "false"
    ops_roles_str = ",".join(str(r) for r in ops_roles)

    # Build placeholders dict
    placeholders: dict[str, str] = {
        "PACKAGE_ID":            package_id,
        "PACKAGE_TITLE":         package_title,
        "CJM_STAGE":             cjm_full,
        "USER_STORIES":          user_stories,
        "US_FILES":              us_files_lines,
        "OUTCOMES":              outcomes_str,
        "ARTIFACTS_DIR":         artifacts_dir,
        "DOD_COMMANDS":          dod_formatted,
        "MAX_PARALLEL":          max_parallel,
        "PARALLEL_SYNTAX":       parallel_syntax_val,
        "WRITE_FILE":            write_file_inline,
        "RUN_CMD":               run_cmd_inline,
        "AGENT_SPAWN":           agent_spawn_guide,
        # Phase 2.5 — Ops Impact Gate
        "OPS_GATE_NEEDED":       ops_gate_needed_str,
        "OPS_ROLES_TRIGGERED":   ops_roles_str,
    }

    # Step 3 sequential split MUST happen before fill_template (while {{MAX_PARALLEL}} is still a placeholder)
    working = template_text
    if max_parallel_int == 1:
        working = _split_step3_sequential(working, agent)

    # Fill template
    filled = _fill_template(working, placeholders)

    # Post-fill integrity check: detect residual placeholders and bad file refs
    _validate_filled_prompt(filled)

    # Prepend pre-extracted context block + orchestrator Write-Set (SSoT for pipeline_guard drift checks)
    context_block = _build_context_block(package_id, contract, context)
    write_set_block = _write_set_markdown_block(_resolved_write_set_files(contract))
    filled = context_block + "\n\n" + write_set_block + "\n" + filled

    return filled


def _validate_filled_prompt(text: str) -> None:
    """Warn about residual {{...}} placeholders and suspicious generated paths."""
    issues: list[str] = []

    # 1. Residual unsubstituted placeholders
    residual = re.findall(r"\{\{([A-Z_]+)\}\}", text)
    if residual:
        seen: set[str] = set()
        for ph in residual:
            if ph not in seen:
                issues.append(f"  ⚠ Residual placeholder: {{{{{ph}}}}}")
                seen.add(ph)

    # 2. Invalid file references generated from n/a USER_STORIES
    bad_paths = re.findall(r"doc/user_stories/[^'\n]*n/a[^'\n]*\.md", text)
    for p in bad_paths[:3]:
        issues.append(f"  ⚠ Invalid US file path: {p.strip()}")

    if issues:
        print("\n⚠ POST-GENERATION VALIDATION WARNINGS:", file=sys.stderr)
        for issue in issues:
            print(issue, file=sys.stderr)
        print(
            f"  Run: {DISPLAY_PYTHON} scripts/workflow.py validate-orch  to check all orchestration files\n",
            file=sys.stderr,
        )


def _build_context_block(
    package_id: str,
    contract: dict[str, str],
    context: dict[str, str],
) -> str:
    us_criteria   = context.get("us_criteria", "(not available)")
    cjm_fragment  = context.get("cjm_fragment", "(not available)")
    recent_closed = context.get("recent_closed", "(not available)")

    # Context freshness metadata — used by validate-orch to detect stale/divergent prompts
    generated_at  = date.today().isoformat()
    # Hash of the recent_closed block so staleness is detectable without diffing full text
    import hashlib
    context_hash  = hashlib.sha256(recent_closed.encode()).hexdigest()[:12]

    return (
        f"<!-- context_generated_at:{generated_at} context_hash:{context_hash} -->\n"
        f"```text\n"
        f"╔══════════════════════════════════════════════════════════════════╗\n"
        f"║  PRE-EXTRACTED CONTEXT — do NOT re-read these files             ║\n"
        f"╚══════════════════════════════════════════════════════════════════╝\n"
        f"\n"
        f"### Acceptance criteria ({contract.get('USER_STORIES', 'n/a')})\n"
        f"{us_criteria}\n"
        f"\n"
        f"### CJM moment ({contract.get('CJM_STAGE', 'n/a')})\n"
        f"{cjm_fragment}\n"
        f"\n"
        f"### Recent closed iterations (last 2)\n"
        f"{recent_closed}\n"
        f"```\n"
    )


# ---------------------------------------------------------------------------
# Pipeline metrics
# ---------------------------------------------------------------------------

def _append_pipeline_metrics(package_id: str, today: str, agent: str) -> None:
    """Append an 'orchestration started' row to pipeline_metrics.md.

    Deduplication: skips if any data row for package_id already exists
    (checked by exact row-start pattern '| <package_id> |').
    """
    row  = f"| {package_id} | {today} | TBD | TBD | 0 | 0 | 0 |"
    note = f"  ← orchestration started via {agent}"
    if not PIPELINE_METRICS.exists():
        PIPELINE_METRICS.parent.mkdir(parents=True, exist_ok=True)
        PIPELINE_METRICS.write_text(
            "# Pipeline Metrics\n\n"
            "| Package | Date | sp1_verdict | sp2_verdict | retries | escalations | deferred |\n"
            "|---------|------|:-----------:|:-----------:|:-------:|:-----------:|:--------:|\n"
            f"{row}{note}\n",
            encoding="utf-8",
        )
        return
    text = PIPELINE_METRICS.read_text(encoding="utf-8")
    # Strict dedup: check for an exact data-row start (not just substring in title/note)
    for line in text.splitlines():
        if line.startswith(f"| {package_id} |"):
            return  # already recorded
    PIPELINE_METRICS.write_text(text.rstrip() + "\n" + row + note + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Planning auto-pivot (no active package in backlog_registry.yaml)
# ---------------------------------------------------------------------------

_PLAN_NEXT_DOC = ROOT / "doc" / "team_workflow" / "generate_plan_next_prompt.md"


def _auto_pivot_to_planning(agent: str) -> int:
    """Called when backlog_registry.yaml has no active package.

    Instead of stopping, automatically outputs the planning workflow prompt
    so the calling agent can pivot immediately — no manual copy-paste needed.

    Returns 0 (success) because a useful prompt was delivered.
    """
    ensure_utf8_stdio()
    _SEP = "═" * 70

    print(
        f"\n⚠  backlog_registry.yaml has no active package — cannot generate orchestration prompt.\n"
        f"   Auto-pivoting to PLANNING WORKFLOW.\n"
        f"   After planning is complete, re-run:\n"
        f"     {DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}\n",
        file=sys.stderr,
    )

    if not _PLAN_NEXT_DOC.exists():
        print(
            f"ERROR: {_PLAN_NEXT_DOC} not found.\n"
            "  Add a package to doc/backlog_registry.yaml first, then regenerate doc/tasklist.md.",
            file=sys.stderr,
        )
        return 1

    print(_SEP)
    print("  AUTO-PIVOT: PLANNING WORKFLOW")
    print(f"  (read the planning file locally, execute it, then re-run orchestration for {agent})")
    print(_SEP)
    print()
    print(
        f"""# PLAN_NEXT launcher

Read `doc/team_workflow/generate_plan_next_prompt.md` and execute it in this same session.

Rules:
- Do not paste the whole planning file into the chat.
- Read the file from disk, follow it, and write the new contract to `doc/backlog_registry.yaml`, then regenerate `doc/tasklist.md`.
- After planning is complete, immediately continue with:

```bash
{DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}
# Fallback (if .venv is unavailable):
python scripts/generate_orchestration_prompt.py --agent {agent}
```

Ignore prior responses/tools. Fresh context only.
"""
    )
    print()
    print(_SEP)
    print(f"  After adding a package to backlog_registry.yaml and regenerating tasklist.md, run:")
    print(f"    {DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}")
    print(_SEP)
    return 0  # success — planning prompt was delivered


# ---------------------------------------------------------------------------
# Clean ASCII launcher
# ---------------------------------------------------------------------------

def _auto_pivot_to_planning_ascii(agent: str) -> int:
    """ASCII-only launcher for the no-active-package orchestration path."""
    ensure_utf8_stdio()
    sep = "=" * 70

    print(
        f"\nWARNING: Now has no active package; cannot generate orchestration prompt.\n"
        f"   Auto-pivoting to PLANNING WORKFLOW.\n"
        f"   After planning is complete, re-run:\n"
        f"     {DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}\n",
        file=sys.stderr,
    )

    if not _PLAN_NEXT_DOC.exists():
        print(
            f"ERROR: {_PLAN_NEXT_DOC} not found.\n"
            "  Add a package to doc/backlog_registry.yaml first, then regenerate doc/tasklist.md.",
            file=sys.stderr,
        )
        return 1

    print(sep)
    print("  AUTO-PIVOT: PLANNING WORKFLOW")
    print(f"  (read the planning file locally, execute it, then re-run orchestration for {agent})")
    print(sep)
    print()
    if agent == "kilo":
        print(
            f"""# PLAN_NEXT launcher

For Kilo: do not continue planning in this same session.

Start a fresh Kilo session and use only this pointer:
- Read `doc/team_workflow/generate_plan_next_prompt.md`
- Do not paste the whole planning file into the chat
- Write the new contract to `doc/backlog_registry.yaml`, then regenerate `doc/tasklist.md`
- Do not open backlog/history docs beyond what that file explicitly requests

After planning is complete, stop that session and start another fresh Kilo session for:

```bash
{DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}
```

Fresh context only. Pointer-only workflow.
"""
        )
    else:
        print(
            f"""# PLAN_NEXT launcher

Read `doc/team_workflow/generate_plan_next_prompt.md` and execute it in this same session.

Rules:
- Do not paste the whole planning file into the chat.
- Read the file from disk, follow it, and write the new contract to `doc/backlog_registry.yaml`, then regenerate `doc/tasklist.md`.
- After planning is complete, immediately continue with:

```bash
{DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}
```

Ignore prior responses/tools. Fresh context only.
"""
        )
    print()
    print(sep)
    print("  After adding a package to Now, run:")
    print(f"    {DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {agent}")
    print(sep)
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ensure_utf8_stdio()
    timer = PhaseTimer()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", "-a", choices=list(AUTONOMOUS_AGENT_CHOICES), required=False,
                        help="Target agent: cursor_ai | codex | kilo | claude_code | continue")
    parser.add_argument("--package", "-p", help="Explicit PACKAGE_ID (skip auto-detect)")
    parser.add_argument(
        "--budget-profile",
        choices=budget_profile_choices(),
        default="strict",
        help="Token/message budget profile for orchestration prompt generation (default: strict)",
    )
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Generate prompt but do not save to disk")
    parser.add_argument(
        "--stdout-mode",
        choices=("launcher", "full"),
        default="launcher",
        help="Console output mode: launcher-only by default, full prompt for internal pipeline capture",
    )
    parser.add_argument("--force", action="store_true",
                        help="Generate even if execution artefacts already exist")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List active packages and exit")
    args = parser.parse_args()

    if not args.agent and not args.list:
        parser.error("--agent is required (cursor_ai | codex | kilo | claude_code | continue)")

    requested_agent = args.agent
    if args.agent and args.agent != "kilo":
        args.agent = resolve_agent_adapter_name(args.agent)

    budget_profile = get_budget_profile(args.budget_profile)
    globals()["MAX_INJECT_CHARS"] = int(budget_profile["inject_chars"])

    try:
      return _main_timed(args, requested_agent, timer)
    finally:
        timer.flush()
        timer.total_only_when_top_level()


def _main_timed(args, requested_agent, timer: PhaseTimer) -> int:  # type: ignore[no-untyped-def]
    """Inner timed logic extracted so try/finally can wrap the whole body."""
    # ── Phase 1: discover active package ──────────────────────────────────
    with timer.phase("phase1_discovery"):
        rows = _parse_truth_view_from_registry()
        if not rows:
            print(
                "ERROR: backlog_registry.yaml has no active workflow rows "
                "(wip/ready/open/proposed). Run plan-next or add a package.",
                file=sys.stderr,
            )
            return 2

        if args.list:
            print("Active packages from backlog_registry.yaml:")
            for r in rows:
                print(f"  [{r['status']:10s}] {r['package']}")
            return 0

        # Package selection + guards + contract parsing are cheap dict lookups —
        # group them inside the same discovery phase for a clean one-phase boundary.
        if args.package:
            selected = _select_package(rows, args.package)
            if not selected:
                # Allow explicit package even if not in Truth View (might be closed)
                selected = {"package": args.package, "status": "explicit"}
        else:
            selected = _select_package(rows, None)

        if not selected:
            return _auto_pivot_to_planning_ascii(agent=requested_agent or args.agent)

        package_id = selected["package"]
        status     = selected["status"]
        today      = date.today().isoformat()

        print(f"→ Package : {package_id}  (status: {status})")
        print(f"→ Agent   : {args.agent}")

        work_state    = _detect_work_state(package_id)
        artifacts_dir = TEAM_ARTIFACTS / package_id
        orch_out      = artifacts_dir / f"orchestration_{args.agent}.md"

        # Guard 1: orchestration for THIS specific agent already exists → require --force
        if orch_out.exists() and not args.force:
            print(
                f"\n⛔ STOP: orchestration_{args.agent}.md already exists for {package_id}.\n"
                f"   Path: archive/team_artifacts/{package_id}/orchestration_{args.agent}.md\n"
                f"\n   Options:\n"
                f"   1. Regenerate:  {DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py --agent {args.agent} --force\n"
                f"   2. Use existing: cat archive/team_artifacts/{package_id}/orchestration_{args.agent}.md",
                file=sys.stderr,
            )
            return 1

        # Guard 2: execution artefacts exist AND no orchestration for any agent yet → warn, don't stop.
        if work_state == "execution_ready" and not args.force:
            existing_orch = list(artifacts_dir.glob("orchestration_*.md"))
            if existing_orch:
                other_agents = [f.stem.replace("orchestration_", "") for f in existing_orch]
                print(
                    f"ℹ  Execution artefacts exist for {package_id}.\n"
                    f"   Orchestration already generated for: {', '.join(other_agents)}\n"
                    f"   Generating orchestration_{args.agent}.md (no --force needed for a new agent)."
                )
            else:
                exec_files = sorted(
                    AGENT_PROMPTS.glob(f"{_slug(package_id)}*exec*"),
                    key=lambda p: p.stat().st_mtime, reverse=True,
                )
                exec_hint = ""
                if exec_files:
                    exec_hint = f"\n   Exec prompt : archive/agent_prompts/{exec_files[0].name}"
                if (artifacts_dir / "execution_contract.md").exists():
                    exec_hint += f"\n   Contract    : archive/team_artifacts/{package_id}/execution_contract.md"

                print(
                    f"\n⛔ STOP: execution artefacts already exist for {package_id}.{exec_hint}\n"
                    f"\n   This package may already be implemented. Options:\n"
                    f"   1. Resume unfinished work:   {DISPLAY_PYTHON} scripts/generate_next_prompt.py --resume\n"
                    f"   2. Close completed package:  {DISPLAY_PYTHON} scripts/close_package.py\n"
                    f"   3. Force orchestration anyway: {DISPLAY_PYTHON} scripts/generate_orchestration_prompt.py"
                    f" --agent {args.agent} --force",
                    file=sys.stderr,
                )
                return 1

        if work_state == "planning_only":
            print(f"ℹ  Planning was initiated — team_artifacts/{package_id}/planning_prompt.md exists.")
            print(f"   Continuing with orchestration generation …")

        contract = _parse_contract_from_registry(package_id)
        if not contract:
            print(
                f"ERROR: contract for '{package_id}' not found in backlog_registry.yaml.\n"
                f"A full contract is required. Run generate_plan_next_prompt.md first.",
                file=sys.stderr,
            )
            return 2

    # ── Phase 3: load template and adapter ────────────────────────────────
    with timer.phase("phase3_template_render"):
        if not TEMPLATE_PATH.exists():
            print(f"ERROR: {TEMPLATE_PATH} not found", file=sys.stderr)
            return 2
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

        # Extract the ```text ... ``` prompt block from the template file
        m = re.search(r"## Шаблон промпта\s*\n\n```text\n(.*?)```", template_text, re.DOTALL)
        if m:
            template_prompt = m.group(1)
        else:
            template_prompt = template_text

        adapter_path = AGENT_ADAPTERS[args.agent]
        if not adapter_path.exists():
            print(f"ERROR: adapter file {adapter_path} not found", file=sys.stderr)
            return 2
        adapter = _parse_adapter(adapter_path)
        if not adapter:
            print(f"ERROR: could not parse YAML block in {adapter_path}", file=sys.stderr)
            return 2

        print(f"→ Adapter : MAX_PARALLEL={adapter.get('MAX_PARALLEL', '?')}")

    # ── Phase 2: pre-extract context ──────────────────────────────────────
    print("→ Extracting context fragments …")
    with timer.phase("phase2_context_load"):
        us_raw        = contract.get("USER_STORIES", "")
        us_ids        = _extract_us_ids(us_raw)
        cjm_stage_raw = contract.get("CJM_STAGE", "")
        cjm_lookup_key = re.split(r"\s+—\s+|\s+", _clean_inline(cjm_stage_raw))[0]

        if us_ids:
            us_path = ROOT / "doc" / "user_stories" / f"{us_ids[0].lower()}.md"
            us_criteria = _extract_us_acceptance(us_path)
        else:
            us_criteria = "(no user stories linked in contract — infra package)"

        cjm_fragment  = _extract_cjm_moment(ROOT / "doc" / "cjm.md", cjm_lookup_key)
        recent_closed = extract_recent_closed()

        context = {
            "us_criteria":   us_criteria,
            "cjm_fragment":  cjm_fragment,
            "recent_closed": recent_closed,
        }

    # ── Phase 2.5: Ops Impact detection ──────────────────────────────────
    # Pure scan against canonical trigger table in ops_triggers.py (kept in
    # sync with doc/team_workflow/rag_llm_ops_project_document.md §35).
    with timer.phase("phase2_5_ops_triggers"):
        gate_needed, ops_roles, ops_matched = detect_ops_triggers(contract)
        ops_info = {
            "gate_needed":   gate_needed,
            "roles":         ops_roles,
            "matched_paths": ops_matched,
        }
        if gate_needed:
            print(f"→ Ops gate: {format_triggered_summary(ops_roles, ops_matched)}")
        else:
            # Mirror the doc's prescribed warning: don't fail, but tell the user
            # the contract had nothing that looked like a known Ops surface.
            print(
                "→ Ops gate: SKIPPED (no Ops triggers in registry text). "
                "If Architect contract reveals affected Ops surfaces in STEP 3, "
                "rerun STEP 3.5 manually."
            )

    # ── Phase 4: fill placeholders ────────────────────────────────────────
    with timer.phase("phase4_placeholders"):
        prompt = build_orchestration_prompt(
            contract, adapter, template_prompt, args.agent, context, ops_info=ops_info,
        )

    # ── Phase 5: save output ──────────────────────────────────────────────
    with timer.phase("phase5_output"):
        if not args.dry_run:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            out_path = artifacts_dir / f"orchestration_{args.agent}.md"
            # Append MANDATORY FINAL STEP so agents reading this file directly
            # (without going through current_task.md) still know to write the
            # execution proof and run --post-agent.
            mandatory_footer = (
                "\n\n---\n\n"
                "## MANDATORY FINAL STEP — execute AFTER all steps above complete\n\n"
                "**Do not skip.** `--post-agent` will exit 3 (blocked) if this file is missing.\n\n"
                "### STEP A — Write execution proof\n\n"
                f"Create/update `archive/team_artifacts/{package_id}/execution_contract.md`:\n"
                "- Which product files were changed (`app/`, `tests/`, `scripts/`)\n"
                "- Why the implementation is correct\n"
                "- Confirmation that all DoD branches are covered\n"
                "- If no product files changed (pre-existing code), add:\n"
                "  ```\n"
                "  Pre-existing delivery evidence:\n"
                "  - commit: <7-40 char SHA of commit that changed referenced paths>\n"
                f"  - files: app/your_module.py\n"
                "  allow_verification_only\n"
                "  ```\n\n"
                "### STEP B — Run post-agent to verify DoD and close package\n\n"
                "```powershell\n"
                f".venv\\Scripts\\python.exe scripts/run_autonomous.py "
                f"--post-agent --package {package_id}\n"
                "```\n"
            )
            out_path.write_text(prompt + mandatory_footer, encoding="utf-8")
            print(f"→ Saved   : {out_path.relative_to(ROOT)}")
            _append_pipeline_metrics(package_id, today, args.agent)
            print(f"→ Metrics : archive/pipeline_metrics.md (row added)")
        else:
            print("→ Dry run — not saving to disk")

    # ── Output ─────────────────────────────────────────────────────────────
    try:
        max_parallel_int = int(adapter.get("MAX_PARALLEL", "8"))
    except ValueError:
        max_parallel_int = 8
    if args.stdout_mode == "full":
        print()
        print("=" * 70)
        print(f"Orchestration prompt for {package_id} on {args.agent}")
        print("=" * 70)
        print()
        print(prompt)
        print()
        print("=" * 70)
        print()
        if max_parallel_int == 1:
            print(f"ℹ  {args.agent}: MAX_PARALLEL=1 — Step 3 is sequential (3a Architect → 3b Designer)")
        else:
            print(f"ℹ  {args.agent}: MAX_PARALLEL={max_parallel_int} — Step 3 runs Architect + Designer in parallel")
        print()
        print("Next step: paste the orchestration prompt above into a fresh agent session.")
        print(f"  TARGET_AGENT: {args.agent}")
        if not args.dry_run:
            print(f"  Prompt also saved: archive/team_artifacts/{package_id}/orchestration_{args.agent}.md")
    else:
        print()
        print("=" * 70)
        print("Orchestration launcher")
        print("=" * 70)
        print(f"Package: {package_id}")
        print(f"Target agent: {args.agent}")
        if max_parallel_int == 1:
            print("Parallelism: sequential Step 3")
        else:
            print(f"Parallelism: MAX_PARALLEL={max_parallel_int}")
        if not args.dry_run:
            print(f"Prompt file: archive/team_artifacts/{package_id}/orchestration_{args.agent}.md")
            print("Next step: open that file in a fresh agent session and execute it there.")
        else:
            print("Dry run: no file saved. Re-run with default settings to persist the prompt file.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
