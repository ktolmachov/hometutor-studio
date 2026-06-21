#!/usr/bin/env python3
"""
generate_next_prompt.py

Automates generation of a self-contained planning prompt for the current epoch's
active package. All context (contract, US criteria, CJM moment, recent closed
iterations, planning template) is pre-extracted and injected into the prompt —
the agent receives everything it needs without reading additional files.

Full workflow this script automates:
  Step 1: find PACKAGE_ID (highest-priority ready/WIP/proposed in backlog_registry.yaml)
  Step 2: generate self-contained planning prompt  ← THIS SCRIPT (default mode)
  Step 3: archive the planning prompt              ← --archive flag
  (Step 4: execute planning prompt in THIS session → get Final planning prompt
           → from its output take Copy-paste execution prompt)
  (Step 5: run Copy-paste execution prompt in a SEPARATE session to implement)

Steps 4 and 5 require an agent session and cannot be scripted without an API.

IMPORTANT FOR AGENTS:
  archive/agent_prompts/ is WRITE-ONLY. Never read a prompt from there as a
  substitute for running this script. If this script cannot run (missing Python,
  environment error), report a blocker — do not fall back to an archived file.

Modes:
  default        Self-contained planning prompt (push-based, all context pre-injected)
  --pull         Legacy pull-based planning prompt (agent reads files itself)
  --quick / -q   Bypass planning: generate execution prompt directly from contract

Archive behaviour (new default: always archive unless --no-archive or --dry-run):
  Saves to archive/agent_prompts/ AND initialises archive/team_artifacts/<PACKAGE_ID>/

Usage:
  python scripts/generate_next_prompt.py
  python scripts/generate_next_prompt.py --package <PACKAGE_ID>
  python scripts/generate_next_prompt.py --no-archive
  python scripts/generate_next_prompt.py --quick
  python scripts/generate_next_prompt.py --pull
  python scripts/generate_next_prompt.py --list
  python scripts/generate_next_prompt.py --dry-run

Exit codes:
  0 — prompt generated OK
  1 — no active package found or BLOCK on preflight
  2 — parse error
"""

from __future__ import annotations

import argparse
import io
import re
import string
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_utils import (  # noqa: E402
    MAX_INJECT_CHARS,
    budget_profile_choices,
    get_budget_profile,
    _load_contract_from_registry as _parse_contract_from_registry,
    parse_contract as _parse_contract_resolved,
    parse_truth_view_from_registry as _parse_truth_view_from_registry,
    select_package as _select_package,
)

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = ROOT / "archive" / "agent_prompts"
ARCHIVE_README = ARCHIVE_DIR / "README.md"
TEAM_ARTIFACTS_DIR = ROOT / "archive" / "team_artifacts"


# ---------------------------------------------------------------------------
# Contract field helpers
# ---------------------------------------------------------------------------

def _clean_value(value: str) -> str:
    return value.strip().strip("`").strip()


def _split_list(value: str, sep: str = ",") -> list[str]:
    parts = re.split(rf"\s*{re.escape(sep)}\s*", value)
    return [p.strip().strip("`").strip() for p in parts if p.strip()]


def _extract_write_set(raw: str) -> list[str]:
    raw = raw.strip()
    # Some contracts store only WRITE_SET_MAX as a number (e.g. "5").
    # In that case, the concrete touchpoints must be derived elsewhere (e.g. EXIT_ARTIFACT).
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
    return _split_list(raw, sep=",")


_CONTRACT_PATH_RE = re.compile(
    r"(?:^|[\s|,`])((?:app|tests|scripts|src)/[^\s`,|]+?\.(?:py|ts|js|tsx|jsx|yaml|yml|json|md))"
)


def _extract_contract_paths(text: str) -> list[str]:
    """Extract concrete repo paths from arbitrary contract text."""
    if not text:
        return []
    found = [m.group(1) for m in _CONTRACT_PATH_RE.finditer(text)]
    # de-dup while preserving order
    return list(dict.fromkeys(found))


def _extract_dod_commands(raw: str) -> list[str]:
    """
    Split DoD commands on `;` that are NOT inside single or double quotes.
    Handles commands like: python -c "import json; json.load(...)"; pytest tests/ -v
    """
    raw = raw.strip()
    commands: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(raw):
        ch = raw[i]
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
        i += 1
    # Remaining
    cmd = "".join(current).strip().strip("`").strip()
    if cmd:
        commands.append(cmd)
    return commands


def _extract_outcomes(raw: str) -> list[str]:
    raw = raw.strip()
    parts = re.split(r"\s*\d+[.)]\s+", raw)
    return [p.strip().strip("`") for p in parts if p.strip()]


def _extract_read_set_files(raw: str) -> list[str]:
    raw = raw.strip()
    entries = re.split(r"\s*;\s*", raw)
    files = []
    for entry in entries:
        entry = entry.strip().strip("`")
        path_part = re.split(r"\s+—\s+", entry)[0].strip().strip("`")
        if path_part and not path_part.startswith("#"):
            files.append(path_part)
    return files


def _us_id_to_path(us_id: str) -> str:
    """Convert 'US-7.3' → 'doc/user_stories/us-7.3.md'."""
    return f"doc/user_stories/{us_id.lower()}.md"


def _extract_us_ids(raw: str) -> list[str]:
    """Extract US-* identifiers from USER_STORIES field."""
    return re.findall(r"US-[\d.]+", raw, re.IGNORECASE)


# ---------------------------------------------------------------------------
# Context extraction (push-based injection)
# ---------------------------------------------------------------------------

def _read_file_safe(path: Path) -> str | None:
    """Read file text safely; return None if missing or unreadable."""
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _extract_us_acceptance(us_path: Path) -> str:
    """
    Extract acceptance criteria from a US markdown file.
    Looks for '**Acceptance:**', '## Acceptance', or '## Критерии' sections.
    """
    text = _read_file_safe(us_path)
    if text is None:
        return f"[FILE NOT FOUND: {us_path.name}]"

    # Try to find acceptance block with various heading patterns
    patterns = [
        # **Acceptance:** followed by Given/When/Then bullets
        r'\*\*Acceptance[:\*]+\*?\*?\n?((?:[-*\s]+.*\n?){1,20})',
        # ## Acceptance section
        r'(#+\s*Acceptance\b[^\n]*\n.*?)(?=\n#+\s|\Z)',
        # ## Критерии section
        r'(#+\s*Критерии\b[^\n]*\n.*?)(?=\n#+\s|\Z)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(0).strip()[:MAX_INJECT_CHARS]

    # Fallback: strip frontmatter and return body
    body = re.sub(r'^---.*?---\n', '', text, flags=re.DOTALL).strip()
    return body[:MAX_INJECT_CHARS]


def _extract_cjm_moment(cjm_path: Path, cjm_stage: str) -> str:
    """
    Extract CJM fragments relevant to cjm_stage (e.g. '#5 — Return next day').
    Returns: moments-of-truth table row + Resume stage row from stage table.
    """
    text = _read_file_safe(cjm_path)
    if text is None:
        return f"[FILE NOT FOUND: {cjm_path.name}]"

    m_num = re.search(r'#?(\d+)', cjm_stage)
    if not m_num:
        return text[:MAX_INJECT_CHARS]
    num = m_num.group(1)

    fragments: list[str] = []

    # 1. Row from "Критические моменты" (moments of truth) table
    moments_m = re.search(
        r'(##\s+\d+\.\s+Критические\s+моменты.*?\n.*?)(?=\n##\s|\Z)',
        text, re.DOTALL | re.IGNORECASE,
    )
    if moments_m:
        section = moments_m.group(0)
        row_m = re.search(rf'\|+\s*{re.escape(num)}\s+\|[^\n]+', section)
        if row_m:
            table_header = "| # | Момент | Что должно произойти | Что ломает доверие |"
            table_sep   = "|---|---|---|---|"
            fragments.append(
                f"Критические моменты (момент #{num}):\n"
                f"{table_header}\n{table_sep}\n{row_m.group(0).strip()}"
            )

    # 2. "Resume" row from stage map table (section 3)
    stage_m = re.search(
        r'(##\s+\d+\.\s+Карта по стадиям.*?\n.*?)(?=\n##\s|\Z)',
        text, re.DOTALL | re.IGNORECASE,
    )
    if stage_m:
        section = stage_m.group(0)
        resume_m = re.search(r'\|\s*\*?\*?Resume\*?\*?\s*\|[^\n]+', section)
        if resume_m:
            fragments.append(f"CJM стадия Resume (из таблицы карты пути):\n{resume_m.group(0).strip()}")

    if fragments:
        return ("\n\n".join(fragments))[:MAX_INJECT_CHARS]

    # Fallback: search for stage text in file
    idx = text.find(cjm_stage.lstrip("#").strip())
    if idx == -1:
        idx = text.lower().find("resume")
    if idx != -1:
        return text[max(0, idx - 100) : idx + 1200][:MAX_INJECT_CHARS]

    return text[:MAX_INJECT_CHARS]


def _extract_recent_closed(closed_path: Path, n: int = 2) -> str:
    """
    Extract the last n '### ' subsection entries from closed_iterations.md.
    These represent the most recently closed packages (patterns for agent to follow).
    """
    text = _read_file_safe(closed_path)
    if text is None:
        return f"[FILE NOT FOUND: {closed_path.name}]"

    # Split on '### ' subsection boundaries
    parts = re.split(r'(?=\n### )', text)
    subsections = [p.strip() for p in parts if p.strip().startswith("### ")]

    if not subsections:
        return text[-MAX_INJECT_CHARS * n :]

    recent = subsections[-n:] if len(subsections) >= n else subsections
    combined = "\n\n---\n\n".join(s for s in recent)
    # Cap total size
    return combined[: MAX_INJECT_CHARS * n]


def _extract_planning_template(templates_path: Path) -> str:
    """
    Extract the '### Шаблон planning prompt' section from agent_workflow_templates.md.
    Includes the code block and surrounding notes.
    """
    text = _read_file_safe(templates_path)
    if text is None:
        return f"[FILE NOT FOUND: {templates_path.name}]"

    m = re.search(
        r'(###\s*Шаблон planning prompt.*?)(?=\n###\s|\n##\s)',
        text, re.DOTALL,
    )
    if m:
        return m.group(1).strip()[:MAX_INJECT_CHARS]

    return text[:MAX_INJECT_CHARS]


def _format_contract_text(contract: dict[str, str]) -> str:
    """Format contract dict in canonical field order for injection."""
    key_order = [
        "PACKAGE_ID", "CJM_STAGE", "PAIN_POINT", "USER_STORIES",
        "OUTCOMES", "WRITE_SET_MAX", "DOD_COMMANDS", "READ_SET_HINT",
        "EXEC_CONSTRAINTS", "RATIONALE",
    ]
    lines: list[str] = []
    for key in key_order:
        if key in contract:
            lines.append(f"{key}: {contract[key].strip()}")
    for key, value in contract.items():
        if key not in key_order:
            lines.append(f"{key}: {value.strip()}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def run_preflight(read_set_files: list[str], *, budget_profile: str) -> tuple[str, str]:
    """
    Run check_readset.py --signatures on read-set files.
    Returns (status, output): SAFE / WARN / BLOCK / SKIP.
    """
    if not read_set_files:
        return "SAFE", "(no read-set hint files)"
    check_script = ROOT / "scripts" / "check_readset.py"
    if not check_script.exists():
        return "SKIP", "check_readset.py not found"
    cmd = [
        sys.executable,
        str(check_script),
        "--signatures",
        "--profile",
        budget_profile,
    ] + read_set_files
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=str(ROOT),
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        if result.returncode == 0:
            return "SAFE", output
        elif result.returncode == 1:
            return "WARN", output
        else:
            return "BLOCK", output
    except Exception as e:
        return "SKIP", str(e)


# ---------------------------------------------------------------------------
# Self-contained planning prompt (default mode)
# ---------------------------------------------------------------------------
#
# Uses string.Template ($var syntax) to safely embed fragments that may contain
# Python format-string special chars like { and }.

_SELFCONTAINED_TMPL = string.Template("""\
Ignore prior responses/tools. Fresh context only.

ALL CONTEXT IS PRE-EXTRACTED BELOW.
Do NOT read additional files. Everything needed for planning is here.

---

## Pre-extracted context for `$package_id`

### 1. Planning template (from doc/agent_workflow_templates.md § Шаблон planning prompt)

$planning_template

---

### 2. Contract: $package_id (from doc/backlog_registry.yaml)

```
$contract_text
```

---

### 3. Acceptance criteria: $us_label (from $us_path)

$us_criteria

---

### 4. CJM moment $cjm_stage (from doc/cjm.md)

$cjm_fragment

---

### 5. Recent closed iterations — last 2 entries (from doc/closed_iterations.md)

$recent_closed

---

## Task

Using ONLY the pre-extracted context above (sections 1–5), produce:

**1. Extracted context** — 5–10 bullets
- Facts from the context above only
- Explicitly note any missing or ambiguous inputs

**2. Final planning prompt for `$package_id`** — fully filled, copy-paste ready
- Fill based on the planning template (section 1 above)
- Write-set (fixed): $write_set_inline
- DoD commands (fixed): $dod_inline
- Must begin with: `Ignore prior responses/tools. Fresh context only.`
- Total output: max 400 words

Rules:
- Do not write code. Produce the plan only.
- Do not read additional files beyond what is pre-extracted above.
- Do not invent facts not present in the provided context.
- If `archive/team_artifacts/$package_id/` already exists AND contains `execution_contract.md`, stop and report (resume workflow may apply).
- After producing both outputs, run: `python scripts/lint_agent_prompts.py`
- After the Copy-paste execution prompt is ready (step 4), save it to:
  `archive/team_artifacts/$package_id/execution_contract.md`

Ignore prior responses/tools. Fresh context only.\
""")


def generate_selfcontained_prompt(contract: dict[str, str]) -> str:
    """
    Generate a self-contained planning prompt with all context pre-extracted.
    The agent receives everything it needs; no additional file reads required.
    """
    package_id   = _clean_value(contract.get("PACKAGE_ID", ""))
    cjm_stage    = _clean_value(contract.get("CJM_STAGE", ""))
    us_raw       = contract.get("USER_STORIES", "")
    write_set_raw = contract.get("WRITE_SET_MAX", "")
    dod_raw      = contract.get("DOD_COMMANDS", "")

    us_ids        = _extract_us_ids(us_raw)
    write_set_files = _extract_write_set(write_set_raw)
    dod_commands  = _extract_dod_commands(dod_raw)

    # — Planning template section
    templates_path = ROOT / "doc" / "agent_workflow_templates.md"
    planning_template = _extract_planning_template(templates_path)

    # — Contract text
    contract_text = _format_contract_text(contract)

    # — US acceptance criteria (primary US only)
    if us_ids:
        us_label    = us_ids[0]
        us_path_str = _us_id_to_path(us_ids[0])
        us_criteria = _extract_us_acceptance(ROOT / us_path_str)
    else:
        us_label    = "N/A"
        us_path_str = "N/A"
        us_criteria = "(no user stories linked in contract)"

    # — CJM moment fragment
    cjm_fragment = _extract_cjm_moment(ROOT / "doc" / "cjm.md", cjm_stage)

    # — Recent closed iterations
    recent_closed = _extract_recent_closed(ROOT / "doc" / "closed_iterations.md", n=2)

    # — Inline write-set and DoD for the task section
    write_set_inline = ", ".join(f"`{f}`" for f in write_set_files) if write_set_files else "(see contract)"
    dod_inline = "; ".join(f"`{c}`" for c in dod_commands)         if dod_commands     else "(see contract)"

    # safe_substitute: leaves unmatched $identifier as-is instead of raising ValueError
    # (extracted file content may contain shell/Python $vars)
    return _SELFCONTAINED_TMPL.safe_substitute(
        package_id=package_id,
        planning_template=planning_template,
        contract_text=contract_text,
        us_label=us_label,
        us_path=us_path_str,
        us_criteria=us_criteria,
        cjm_stage=cjm_stage,
        cjm_fragment=cjm_fragment,
        recent_closed=recent_closed,
        write_set_inline=write_set_inline,
        dod_inline=dod_inline,
    )


# ---------------------------------------------------------------------------
# Legacy pull-based planning prompt (--pull mode)
# ---------------------------------------------------------------------------

_PULL_PROMPT_TMPL = """\
Read `AGENTS.md` and obey Token Budget & Retry Safety from:
- `AGENTS.md`
- `doc/agent_workflow_rules.md`
- `doc/token_safety.md`

Task:
Generate a planning prompt for `{package_id}` using the canonical template
`Шаблон planning prompt` from `doc/agent_workflow_templates.md`.

Rules:
- Do not write code.
- Do not invent facts not present in the sources.
- Do not read broad context "just in case".
- Do not read whole files if a targeted fragment is enough.
- If `archive/team_artifacts/{package_id}/` already exists, stop and report that
  `doc/team_workflow/generate_resume_prompt.md` may be the correct workflow.

Token budget:
- Active profile: `{profile_name}`.
- Target: ≤ {soft_limit} input tokens.
- Hard ceiling: some UIs cap one user message at ~{ui_char_limit:,} **characters** — if larger, split read-set, trim, or use an extended-context model.
- If estimated input is {soft_limit}–{hard_limit}, compress history and read-set before continuing.
- If estimated input would exceed {hard_limit}, stop and report a blocker.
- Before finalizing the read-set, run:
  `python scripts/check_readset.py --profile {profile_name} {preflight_files}`
- If a DoD command intentionally validates token/read-set registry files and
  strict profile returns WARN for an otherwise valid read-set, use
  `--profile relaxed` in both the registry contract and archived prompt.
  Do not leave a strict/WARN command that will later trigger post-agent drift.
- After assembling the final prompt, run:
  `python scripts/lint_agent_prompts.py`

Read only minimal relevant fragments from:
1. `doc/agent_workflow_templates.md`
   - Only section: `Шаблон planning prompt`
2. `doc/backlog_registry.yaml`
   - Only the entry for `{package_id}`
{us_read_section}\
4. `doc/closed_iterations.md`
   - Only 1–2 most relevant recent closed items or fragments
5. `doc/cjm.md`
   - Only the fragment directly relevant to `{package_id}` ({cjm_stage})
6. `doc/conventions.md`
   - Only sections directly relevant to `{package_id}`

Do not use as primary sources:
- `doc/agent_workflow.md` for the planning template
- monolithic `user_stories.md`
- full broad reads of `doc/closed_iterations.md`, `doc/cjm.md`, or `doc/epochs/`

Output:
1. `Extracted context`
   - 5–10 short bullets
   - Only facts needed for planning
   - Explicitly note missing or ambiguous inputs

2. `Final planning prompt for {package_id}`
   - Fully filled and ready to copy-paste
   - Based on the current canonical template
   - Safe for a fresh agent session
   - Must include: `Ignore prior responses/tools. Fresh context only.`

Quality bar:
- Specific to `{package_id}`
- Produces a planning contract, not implementation
- Does not encourage broad repo scanning
- Preserves project token-safety rules\
"""


def _format_us_read_section(us_ids: list[str]) -> str:
    if not us_ids:
        return "3. (no user stories linked — skip this step)\n"
    lines = ["3. `doc/user_stories/` — only US files explicitly linked:\n"]
    for us_id in us_ids:
        path = _us_id_to_path(us_id)
        exists = (ROOT / path).exists()
        note = "" if exists else "  ⚠ file not found"
        lines.append(f"   - `{path}` — only acceptance criteria section{note}\n")
    return "".join(lines)


def generate_pull_prompt(contract: dict[str, str], *, budget_profile: dict[str, int | str]) -> str:
    """Generate the legacy pull-based step-2 planning prompt (--pull mode)."""
    package_id   = _clean_value(contract.get("PACKAGE_ID", ""))
    cjm_stage    = _clean_value(contract.get("CJM_STAGE", ""))
    us_raw       = contract.get("USER_STORIES", "")
    read_set_raw = contract.get("READ_SET_HINT", "")

    us_ids = _extract_us_ids(us_raw)
    us_read_section = _format_us_read_section(us_ids)

    preflight_files_list = [_us_id_to_path(uid) for uid in us_ids]
    if read_set_raw:
        preflight_files_list.extend(_extract_read_set_files(read_set_raw))
    preflight_files = " ".join(preflight_files_list) if preflight_files_list else "<file1> <file2>"

    return _PULL_PROMPT_TMPL.format(
        package_id=package_id,
        cjm_stage=cjm_stage,
        us_read_section=us_read_section,
        preflight_files=preflight_files,
        profile_name=budget_profile["name"],
        soft_limit=budget_profile["soft_token_limit"],
        hard_limit=budget_profile["hard_token_limit"],
        ui_char_limit=budget_profile["ui_char_limit"],
    )


# ---------------------------------------------------------------------------
# Quick execution prompt (--quick mode)
# ---------------------------------------------------------------------------

# Template for the Copy-paste execution prompt (quick bypass of planning steps).
# Python format-string placeholders correspond to contract fields:
#   {package_id}        ← PACKAGE_ID
#   {write_set}         ← WRITE_SET_MAX (comma-separated file list)
#   {pain_point}        ← PAIN_POINT
#   {cjm_stage}         ← CJM_STAGE
#   {outcomes_text}     ← OUTCOMES (numbered list)
#   {constraints_block} ← EXEC_CONSTRAINTS (optional; empty string if absent)
#   {dod_commands_logged} ← DOD_COMMANDS wrapped in logging helper
QUICK_EXEC_TEMPLATE = """\
Implement {package_id} only. Stay strictly in write-set:
{write_set}.

## Write-Set
{write_set_bullets}

Goal: {pain_point} ({cjm_stage}).
{outcomes_text}
{constraints_block}
Do not touch: files outside the write-set above.

Before editing:
1. Check whether the requested behavior is already implemented in the current
   codebase.
2. If it is already done, do not make cosmetic rewrites. Run the DoD and close
   as verification-only with strict evidence.
3. Verification-only evidence must include a concrete commit SHA that changed
   at least one referenced product/test file, plus the repo paths it delivered.

Run:
{dod_commands_logged}
Return: product changed files, why, and proof that all DoD branches are covered.
If no product files changed, report this as verification-only and include:

Pre-existing delivery evidence:
- commit: <concrete 7-40 char sha that changed at least one referenced path>
- files:
  - <existing repo path>

After all DoD pass: save this execution prompt (or a summary of decisions made)
to `archive/team_artifacts/{package_id}/execution_contract.md` so the resume
workflow can detect that execution was completed.\
"""


def _format_outcomes(outcomes: list[str]) -> str:
    if not outcomes:
        return ""
    if len(outcomes) == 1:
        return outcomes[0]
    return "\n".join(f"{i}. {o}" for i, o in enumerate(outcomes, 1))


def generate_quick_exec_prompt(contract: dict[str, str]) -> str:
    """Generate execution prompt directly from contract fields (quick mode)."""
    package_id      = _clean_value(contract.get("PACKAGE_ID", ""))
    cjm_stage       = _clean_value(contract.get("CJM_STAGE", ""))
    pain_point      = _clean_value(contract.get("PAIN_POINT", ""))
    write_set_raw   = contract.get("WRITE_SET_MAX", "")
    dod_raw         = contract.get("DOD_COMMANDS", "")
    outcomes_raw    = contract.get("OUTCOMES", "")
    constraints_raw = contract.get("EXEC_CONSTRAINTS", "").strip()

    write_set_files = _extract_write_set(write_set_raw)
    dod_commands    = _extract_dod_commands(dod_raw)
    outcomes        = _extract_outcomes(outcomes_raw)

    write_set_str   = ",\n".join(write_set_files) if write_set_files else "(see contract)"
    write_set_bullets = "\n".join(f"- `{f}`" for f in write_set_files) if write_set_files else "- (see contract)"
    dod_str         = "\n".join(dod_commands)      if dod_commands     else "(see contract)"
    dod_logged_str  = (
        "\n".join(dod_commands)
        if dod_commands else "(see contract)"
    )
    outcomes_text   = _format_outcomes(outcomes)
    constraints_block = f"\n{_clean_value(constraints_raw)}\n" if constraints_raw else ""

    return QUICK_EXEC_TEMPLATE.format(
        package_id=package_id,
        write_set=write_set_str,
        write_set_bullets=write_set_bullets,
        pain_point=pain_point,
        cjm_stage=cjm_stage,
        outcomes_text=outcomes_text,
        constraints_block=constraints_block,
        dod_commands=dod_str,
        dod_commands_logged=dod_logged_str,
    )


# ---------------------------------------------------------------------------
# Work-state detection
# ---------------------------------------------------------------------------

class WorkState:
    """Describes how far along a package is in the workflow."""
    FRESH          = "fresh"           # nothing archived yet
    PLANNING_ONLY  = "planning_only"   # planning_prompt.md in team_artifacts, no exec prompt
    EXECUTION_READY = "execution_ready" # execution_contract.md exists

    def __init__(
        self,
        state: str,
        exec_prompt_file: Path | None = None,
        execution_contract_file: Path | None = None,
        planning_prompt_file: Path | None = None,
    ) -> None:
        self.state = state
        self.exec_prompt_file = exec_prompt_file
        self.execution_contract_file = execution_contract_file
        self.planning_prompt_file = planning_prompt_file


def _detect_work_state(package_id: str) -> WorkState:
    """
    Determine how far along a package is in the workflow by inspecting archives.

    Priority order:
    1. team_artifacts/<ID>/execution_contract.md  → execution was tracked as started
    2. team_artifacts/<ID>/planning_prompt.md only → planning was initiated
    3. Nothing                                      → fresh
    """
    pkg_dir  = TEAM_ARTIFACTS_DIR / package_id

    # 1. Explicit execution contract in team_artifacts
    exec_contract = pkg_dir / "execution_contract.md"
    if exec_contract.exists():
        return WorkState(
            WorkState.EXECUTION_READY,
            execution_contract_file=exec_contract,
            planning_prompt_file=pkg_dir / "planning_prompt.md" if (pkg_dir / "planning_prompt.md").exists() else None,
        )

    # 2. Planning only
    planning_file = pkg_dir / "planning_prompt.md"
    if planning_file.exists():
        return WorkState(WorkState.PLANNING_ONLY, planning_prompt_file=planning_file)

    # 3. Fresh
    return WorkState(WorkState.FRESH)


# ---------------------------------------------------------------------------
# Resume prompt (--resume mode)
# ---------------------------------------------------------------------------

_RESUME_TMPL = string.Template("""\
Ignore prior responses/tools. Fresh context only.

Resume implementation of `$package_id` — work was started in a previous session.

## Known execution artefacts

$exec_ref

## DoD status (pre-run by script)

$dod_status_block

${failing_section}
Constraints:
$constraints_block
Write-set (stay strictly within):
$write_set_block

## Write-Set
$write_set_plain_block

Do not touch: files outside the write-set above.

Return:
- For each failing DoD command: changed files and why, then re-run result
- If all DoD now pass: run `python scripts/close_package.py` to close the package

Ignore prior responses/tools. Fresh context only.
""")


def _run_dod_commands(commands: list[str]) -> list[tuple[str, int]]:
    """Run DoD commands, return [(cmd, exit_code), ...]."""
    results: list[tuple[str, int]] = []
    for cmd in commands:
        normalized_cmd = cmd
        if re.match(r"^\s*python\b", cmd, re.IGNORECASE):
            normalized_cmd = re.sub(
                r"^\s*python\b",
                lambda _m: subprocess.list2cmdline([sys.executable]),
                cmd,
                count=1,
                flags=re.IGNORECASE,
            )

        print(f"    $ {normalized_cmd}")
        try:
            proc = subprocess.run(
                normalized_cmd, shell=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace", cwd=str(ROOT),
            )
            rc = proc.returncode
            # Show last few lines of output
            output = (proc.stdout + proc.stderr).strip()
            for line in output.splitlines()[-4:]:
                print(f"      {line}")
        except Exception as exc:
            rc = -1
            print(f"      ERROR: {exc}")
        status = "✓ PASS" if rc == 0 else "✗ FAIL"
        print(f"      → {status}")
        results.append((normalized_cmd, rc))
    return results


def _resume_with_auto_dod(
    contract: dict[str, str], ws: WorkState, package_id: str
) -> tuple[str, bool]:
    """
    Run DoD automatically before generating the resume prompt.
    Returns (prompt_text, all_dod_green).
    If all DoD pass, the second element is True and the prompt need not be shown.
    """
    dod_raw = contract.get("DOD_COMMANDS", "")
    dod_commands = _extract_dod_commands(dod_raw) if dod_raw else []

    if not dod_commands:
        print("→ DoD auto-check: no DOD_COMMANDS in contract — skipping")
        return generate_resume_prompt(contract, ws), False

    print(f"→ Auto-running DoD ({len(dod_commands)} command(s)) …")
    results = _run_dod_commands(dod_commands)
    all_green = all(rc == 0 for _, rc in results)

    if all_green:
        print(f"\n✓ All {len(dod_commands)} DoD command(s) PASSED")
        return "", True

    failed = [cmd for cmd, rc in results if rc != 0]
    print(f"\n✗ {len(failed)} of {len(dod_commands)} DoD command(s) FAILED")

    # Build targeted resume prompt focused on failing commands
    failing_block = "\n".join(f"  - `{c}`" for c in failed)
    prompt = generate_resume_prompt(contract, ws, failing_commands=failed)
    return prompt, False


def _handle_dod_green_closure(package_id: str) -> int:
    """Called when --resume finds DoD already green. Suggests close_package.py."""
    print(
        f"\n{'=' * 70}\n"
        f"✓ DoD GREEN — {package_id} appears to be complete.\n"
        f"{'=' * 70}\n"
        f"\n"
        f"No implementation needed. Run the closure script to close the package:\n"
        f"\n"
        f"    python scripts/close_package.py\n"
        f"\n"
        f"This will update all 6 documentation files automatically:\n"
        f"  doc/tasklist.md, doc/backlog_registry.yaml, doc/user_stories/*.md,\n"
        f"  doc/user_stories_index.json, doc/closed_iterations.md, doc/changelog.md\n"
        f"\n"
        f"Then run the next package:\n"
        f"  python scripts/generate_next_prompt.py --list\n"
        f"  python scripts/generate_next_prompt.py\n"
    )
    return 0


def generate_resume_prompt(contract: dict[str, str], ws: WorkState,
                            failing_commands: list[str] | None = None) -> str:
    """Generate a continuation prompt for a package whose execution was already started."""
    package_id      = _clean_value(contract.get("PACKAGE_ID", ""))
    write_set_raw   = contract.get("WRITE_SET_MAX", "")
    dod_raw         = contract.get("DOD_COMMANDS", "")
    constraints_raw = contract.get("EXEC_CONSTRAINTS", "").strip()

    write_set_files = _extract_write_set(write_set_raw)
    dod_commands    = _extract_dod_commands(dod_raw)

    # Fallback: if WRITE_SET_MAX is numeric-only, derive concrete touchpoints from other contract fields.
    if not write_set_files and write_set_raw.strip().isdigit():
        touch_text = "\n".join(
            [
                str(contract.get("EXIT_ARTIFACT", "")),
                str(contract.get("NOTES", "")),
                str(contract.get("BLOCKS", "")),
            ]
        )
        write_set_files = _extract_contract_paths(touch_text)
        # Respect write-set max if we have it.
        try:
            max_n = int(write_set_raw.strip())
        except ValueError:
            max_n = 0
        if max_n > 0 and len(write_set_files) > max_n:
            write_set_files = write_set_files[:max_n]

    write_set_block   = "\n".join(f"   - `{f}`" for f in write_set_files) if write_set_files else "   (see contract)"
    write_set_plain_block = "\n".join(f"- `{f}`" for f in write_set_files) if write_set_files else "- (see contract)"
    constraints_block = f"{_clean_value(constraints_raw)}\n" if constraints_raw else "(see contract)\n"

    # DoD status block (shows which commands passed/failed)
    if failing_commands is not None:
        # Auto-DoD was run — show status for each command
        failing_set = set(failing_commands)
        status_lines = []
        for cmd in dod_commands:
            mark = "✗ FAIL" if cmd in failing_set else "✓ PASS"
            status_lines.append(f"  {mark}  `{cmd}`")
        dod_status_block = "\n".join(status_lines) if status_lines else "  (no commands)"
    else:
        # Manual mode — just list commands without status
        dod_status_block = "\n".join(f"  (not run)  `{c}`" for c in dod_commands) if dod_commands else "  (see contract)"

    # Failing section — targeted fix instructions
    if failing_commands:
        failing_lines = "\n".join(f"   - `{c}`" for c in failing_commands)
        failing_section = (
            f"## Task: fix the failing commands\n"
            f"\n"
            f"Only these DoD commands failed:\n"
            f"{failing_lines}\n"
            f"\n"
            f"For each failing command, read ONLY the relevant write-set files\n"
            f"(signatures first: `rg \"^def \" <file>`, then targeted sections).\n"
            f"Fix what is needed. Do not re-implement what already passes.\n"
            f"\n"
        )
    else:
        failing_section = (
            "## Task\n"
            "\n"
            "Run the DoD commands listed above. Fix what fails.\n"
            "For each failing command, read ONLY the relevant write-set files\n"
            "(signatures first, then targeted sections). Do not re-implement what passes.\n"
            "\n"
        )

    # Exec reference block
    exec_lines: list[str] = []
    if ws.execution_contract_file:
        exec_lines.append(f"- Execution contract: `{ws.execution_contract_file.relative_to(ROOT)}`")
    if ws.exec_prompt_file:
        exec_lines.append(f"- Execution prompt  : `{ws.exec_prompt_file.relative_to(ROOT)}`")
    if ws.planning_prompt_file:
        exec_lines.append(f"- Planning prompt   : `{ws.planning_prompt_file.relative_to(ROOT)}`")
    if not exec_lines:
        exec_lines.append("(no specific artefact path found — check archive/agent_prompts/ manually)")
    exec_ref = "\n".join(exec_lines)

    return _RESUME_TMPL.safe_substitute(
        package_id=package_id,
        exec_ref=exec_ref,
        dod_status_block=dod_status_block,
        failing_section=failing_section,
        write_set_block=write_set_block,
        write_set_plain_block=write_set_plain_block,
        constraints_block=constraints_block,
    )


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def _slug(package_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", package_id.lower()).strip("_")


def _find_existing_archive(package_id: str, today: str, suffix: str) -> Path | None:
    """
    Return the first existing archive file for this package+date+suffix, or None.
    Matches both base name and any _v2/_v3 variants.
    """
    base = f"{_slug(package_id)}_{suffix}_{today}"
    # Check base name first
    candidate = ARCHIVE_DIR / f"{base}.md"
    if candidate.exists():
        return candidate
    # Check versioned variants
    n = 2
    while True:
        versioned = ARCHIVE_DIR / f"{base}_v{n}.md"
        if versioned.exists():
            return versioned
        # Stop after a reasonable range
        if n > 20:
            break
        n += 1
    return None


def _make_archive_filename(package_id: str, today: str, suffix: str) -> Path:
    """Generate a new archive filename (never overwrites existing files)."""
    base = f"{_slug(package_id)}_{suffix}_{today}"
    candidate = ARCHIVE_DIR / f"{base}.md"
    n = 1
    while candidate.exists():
        candidate = ARCHIVE_DIR / f"{base}_v{n + 1}.md"
        n += 1
    return candidate


_ARCHIVE_MODE_LABELS = {
    "selfcontained": ("planning_prompt", "Self-contained planning prompt (push-based)"),
    "pull":          ("planning_prompt", "Step-2 pull-based planning prompt"),
    "quick":         ("exec_prompt_quick", "Quick execution prompt (direct from contract)"),
}


def _archive_prompt(prompt: str, package_id: str, contract: dict[str, str], mode: str) -> Path:
    today = date.today().isoformat()
    suffix, source_desc = _ARCHIVE_MODE_LABELS.get(mode, ("prompt", mode))

    # Idempotent: if already archived for this package+date, return existing file
    existing = _find_existing_archive(package_id, today, suffix)
    if existing:
        # Still update team_artifacts (content may have improved)
        if mode in ("selfcontained", "pull"):
            _init_team_artifacts(package_id, prompt, contract, today)
        return existing

    dest = _make_archive_filename(package_id, today, suffix)

    us    = _clean_value(contract.get("USER_STORIES", "—"))
    title = _clean_value(contract.get("PACKAGE_TITLE", package_id))

    if mode == "quick":
        usage_note = "Вставить в новый чат агента напрямую для выполнения задачи."
    else:
        usage_note = (
            "Выполнить prompt в текущей сессии (step 2a).\n"
            "После получения Final planning prompt → выполнить в этой же сессии (step 4).\n"
            "Copy-paste execution prompt → передать пользователю для запуска в ОТДЕЛЬНОЙ сессии (step 5)."
        )

    content = f"""\
# Архив: {source_desc} — {package_id} ({title})

| Поле | Значение |
|------|----------|
| Пакет | **{package_id}** |
| Дата архивирования | {today} |
| User story | {us} |
| Источник | {source_desc} |

{usage_note}

---

```text
{prompt}
```
"""
    dest.write_text(content, encoding="utf-8")

    # Update README index logic has been removed to eliminate duplication of truth

    # Initialise archive/team_artifacts/<PACKAGE_ID>/ for planning prompts only
    if mode in ("selfcontained", "pull"):
        _init_team_artifacts(package_id, prompt, contract, today)

    return dest


def _init_team_artifacts(
    package_id: str, prompt: str, contract: dict[str, str], today: str
) -> Path | None:
    """
    Create archive/team_artifacts/<PACKAGE_ID>/ and save planning_prompt.md there.
    This signals that the planning phase has been initiated for the package.
    Returns the path to the created directory, or None if already exists.
    """
    pkg_dir = TEAM_ARTIFACTS_DIR / package_id
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Always overwrite — team_artifacts/planning_prompt.md is the canonical latest version
    planning_file = pkg_dir / "planning_prompt.md"

    title = _clean_value(contract.get("PACKAGE_TITLE", package_id))
    us    = _clean_value(contract.get("USER_STORIES", "—"))
    write_set_raw = contract.get("WRITE_SET_MAX", "")
    dod_raw = contract.get("DOD_COMMANDS", "")

    header = f"""\
# Planning prompt: {package_id}

| Поле | Значение |
|------|----------|
| Пакет | **{package_id}** |
| Заголовок | {title} |
| User story | {us} |
| Write-set | `{write_set_raw.strip()}` |
| DoD | `{dod_raw.strip()}` |
| Дата | {today} |

Это самодостаточный planning prompt (push-based).
После выполнения агент должен сохранить execution contract в:
`archive/team_artifacts/{package_id}/execution_contract.md`

---

```text
{prompt}
```
"""
    planning_file.write_text(header, encoding="utf-8")

    # Auto-create execution_contract.md skeleton so STATE-A guard doesn't block.
    # The agent fills in the evidence; the skeleton provides the required structure.
    exec_contract = pkg_dir / "execution_contract.md"
    if not exec_contract.exists():
        dod_raw = contract.get("DOD_COMMANDS", "")
        outcomes_raw = contract.get("OUTCOMES", "")
        skeleton = f"""\
# Execution contract: {package_id}

| Field | Value |
|-------|-------|
| Package | **{package_id}** |
| Title | {title} |
| User story | {us} |
| Date | {today} |
| Status | STARTED |

## DoD commands

```
{dod_raw.strip()}
```

## Evidence

_Fill in: paste DoD command output, test results, or explain why verification-only._

## Outcomes delivered

{outcomes_raw.strip() or "- (describe what was implemented or verified)"}

## Changed files

_Pipeline will append verified diff here after --post-agent._
"""
        exec_contract.write_text(skeleton, encoding="utf-8")

    return pkg_dir


# ---------------------------------------------------------------------------
# Inline prompt lint
# ---------------------------------------------------------------------------

def _run_prompt_lint(prompt_text: str, label: str) -> None:
    """Run structural lint on prompt text and print results."""
    lint_script = ROOT / "scripts" / "lint_agent_prompts.py"
    if not lint_script.exists():
        return
    cmd = [sys.executable, str(lint_script), "--no-readset-check", "--prompt-text", prompt_text]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=str(ROOT),
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        status = "OK" if result.returncode == 0 else "FAILED"
        print(f"→ Prompt lint ({label}): {status}")
        if output and output != f"lint_agent_prompts: {status}":
            for line in output.splitlines():
                if line.strip() and "lint_agent_prompts:" not in line:
                    print(f"  {line}")
    except Exception as e:
        print(f"→ Prompt lint: SKIP ({e})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--package", "-p", help="Explicit PACKAGE_ID (skip auto-discovery)")
    parser.add_argument(
        "--no-archive", action="store_true",
        help="Skip archiving (default: always archive to agent_prompts/ and team_artifacts/)",
    )
    parser.add_argument(
        "--archive", "-a", action="store_true",
        help="(deprecated alias; archive is now the default; kept for backward compat)",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="Print prompt but do not archive")
    parser.add_argument(
        "--stdout-mode",
        choices=("launcher", "full"),
        default="launcher",
        help="Console output mode: launcher-only by default, full prompt for internal pipeline capture",
    )
    parser.add_argument("--list", "-l", action="store_true", help="List active packages and exit")
    parser.add_argument("--no-preflight", action="store_true", help="Skip check_readset.py preflight")
    parser.add_argument(
        "--budget-profile",
        choices=budget_profile_choices(),
        default="strict",
        help="Token/message budget profile for prompt generation (default: strict)",
    )
    parser.add_argument(
        "--quick", "-q", action="store_true",
        help="Quick mode: generate execution prompt directly from contract (bypasses planning)",
    )
    parser.add_argument(
        "--pull", action="store_true",
        help="Legacy pull-based planning prompt (agent reads files itself; use default push-based instead)",
    )
    parser.add_argument(
        "--resume", "-r", action="store_true",
        help="Generate a continuation/resume prompt for a package whose execution was already started",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Bypass work-state detection and generate a fresh planning prompt even if execution was started",
    )
    args = parser.parse_args()
    budget_profile = get_budget_profile(args.budget_profile)
    globals()["MAX_INJECT_CHARS"] = int(budget_profile["inject_chars"])

    # Truth View: registry SSoT only (no tasklist.md fallback).
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
            print(f"  [{r['status']:8s}] {r['package']}")
        return 0

    # Select package
    selected = _select_package(rows, args.package)
    if selected is None:
        if args.package:
            print(f"ERROR: package '{args.package}' not found in backlog_registry.yaml active/proposed rows", file=sys.stderr)
        else:
            print(
                "⚠ No ready/WIP/proposed package found in backlog_registry.yaml.\n"
                "Run: Прочитай doc/team_workflow/generate_plan_next_prompt.md\n"
                "to propose and accept a new package first.",
                file=sys.stderr,
            )
        return 1

    package_id = selected["package"]
    status     = selected["status"]

    print(f"→ Selected package: {package_id}  (status: {status})")

    # ── Work-state detection ──────────────────────────────────────────────
    ws = _detect_work_state(package_id)

    if ws.state == WorkState.EXECUTION_READY and not args.force and not args.resume:
        # Execution was already started — do not regenerate planning prompt
        exec_hint = ""
        if ws.execution_contract_file:
            exec_hint = f"\n   Execution contract : {ws.execution_contract_file.relative_to(ROOT)}"
        if ws.exec_prompt_file:
            exec_hint += f"\n   Execution prompt   : {ws.exec_prompt_file.relative_to(ROOT)}"
        print(
            f"\n⛔ STOP: execution artefacts already exist for {package_id}.{exec_hint}\n"
            f"\n   The execution prompt was generated in a previous session.\n"
            f"   Starting a new planning prompt would discard that work.\n"
            f"\n   Options:\n"
            f"   1. Continue unfinished implementation:\n"
            f"      python scripts/generate_next_prompt.py --resume\n"
            f"   2. Restart from scratch (discards previous plan):\n"
            f"      python scripts/generate_next_prompt.py --force\n"
            f"   3. Read the resume workflow:\n"
            f"      doc/team_workflow/generate_resume_prompt.md",
            file=sys.stderr,
        )
        return 1

    if ws.state == WorkState.PLANNING_ONLY and not args.force and not args.resume:
        print(
            f"ℹ  Planning was already initiated ({TEAM_ARTIFACTS_DIR.relative_to(ROOT)}/{package_id}/planning_prompt.md).\n"
            f"   Regenerating planning prompt (use --resume if execution was already started)."
        )

    # ── Determine prompt mode ─────────────────────────────────────────────
    if args.resume:
        mode = "resume"
    elif args.quick:
        mode = "quick"
    elif args.pull:
        mode = "pull"
    else:
        mode = "selfcontained"

    mode_label = {
        "selfcontained": "self-contained planning prompt [push-based, default]",
        "pull":          "pull-based planning prompt [legacy, --pull]",
        "quick":         "quick execution prompt [--quick]",
        "resume":        "resume/continuation prompt [--resume]",
    }[mode]

    print(f"→ Mode: {mode_label}")

    # Parse contract
    contract = _parse_contract_resolved("", package_id)
    if not contract:
        print(
            f"ERROR: contract for '{package_id}' not found in backlog_registry.yaml.\n"
            f"The package must have a full contract before a prompt can be generated.",
            file=sys.stderr,
        )
        return 2

    # Preflight (only for non-selfcontained modes where agent will read files)
    preflight_status = "SKIP"
    if mode in ("pull", "quick") and not args.no_preflight:
        read_set_raw = contract.get("READ_SET_HINT", "")
        read_set_files = _extract_read_set_files(read_set_raw) if read_set_raw else []
        if read_set_files:
            print(f"→ Preflight check_readset on {len(read_set_files)} files …")
            preflight_status, preflight_output = run_preflight(
                read_set_files,
                budget_profile=str(budget_profile["name"]),
            )
            print(f"  Status: {preflight_status}")
            if preflight_output:
                for line in preflight_output.splitlines()[:3]:
                    print(f"  {line}")
            if preflight_status == "BLOCK":
                print(
                    "  ⚠ BLOCK: read-set is large even in signatures mode.\n"
                    "  The agent must use rg/grep and targeted section reads only."
                )
        else:
            print("→ Preflight: skipped (no READ_SET_HINT files found)")
    elif mode == "selfcontained":
        print("→ Preflight: not needed (self-contained — all context pre-extracted)")

    # Generate prompt
    if mode == "selfcontained":
        print("→ Extracting context fragments …")
        prompt = generate_selfcontained_prompt(contract)
    elif mode == "pull":
        prompt = generate_pull_prompt(contract, budget_profile=budget_profile)
    elif mode == "resume":
        prompt, dod_all_green = _resume_with_auto_dod(contract, ws, package_id)
        if dod_all_green:
            # Implementation already complete — close the package
            return _handle_dod_green_closure(package_id)
    else:  # quick
        prompt = generate_quick_exec_prompt(contract)
        _run_prompt_lint(prompt, "quick execution prompt")

    # Archive — always on unless --no-archive or --dry-run (skip for resume mode)
    archived_path: Path | None = None
    do_archive = not args.no_archive and not args.dry_run and mode != "resume"
    if do_archive:
        suffix, _ = _ARCHIVE_MODE_LABELS.get(mode, ("prompt", mode))
        existing = _find_existing_archive(package_id, date.today().isoformat(), suffix)
        archived_path = _archive_prompt(prompt, package_id, contract, mode)
        if existing:
            print(f"→ Archive skipped : already exists → {archived_path.relative_to(ROOT)}")
        else:
            print(f"→ Archived prompt : {archived_path.relative_to(ROOT)}")
        if mode in ("selfcontained", "pull"):
            pkg_dir = TEAM_ARTIFACTS_DIR / package_id
            print(f"→ Team artifacts  : {pkg_dir.relative_to(ROOT)}/planning_prompt.md")

    launcher_ref: str | None = None
    if mode in ("selfcontained", "pull"):
        launcher_ref = f"archive/team_artifacts/{package_id}/planning_prompt.md"
    elif mode == "quick" and archived_path is not None:
        launcher_ref = archived_path.relative_to(ROOT).as_posix()

    # Output
    print()
    if args.stdout_mode == "full":
        if mode == "resume":
            print("=" * 70)
            print("Resume / continuation prompt  — EXECUTE NOW in this session")
            print("=" * 70)
            print()
            print(prompt)
            print()
            print("=" * 70)
            print()
            print("ACTION REQUIRED — execute the resume prompt above immediately.")
            print("After all DoD pass → verify and close the package.")
            print()
            print("⚠  If DoD already pass: the package may be complete.")
            print("   Read doc/team_workflow/generate_resume_prompt.md to close it.")

        elif mode == "selfcontained":
            print("=" * 70)
            print("Self-contained planning prompt  — EXECUTE NOW in this session")
            print("=" * 70)
            print()
            print(prompt)
            print()
            print("=" * 70)
            print()
            print("ACTION REQUIRED — execute the planning prompt above immediately:")
            print("  All context is pre-extracted. No file reads needed.")
            print("  Produce:")
            print("    1. Extracted context (5–10 bullets)")
            print(f"    2. Final planning prompt for {package_id}")
            print()
            print("Do NOT stop here. Do NOT say 'paste into a new session'.")
            print("Execute the planning prompt in this session right now.")
            print()
            print("─" * 70)
            print("After the planning prompt executes → step 4: run the Final planning")
            print("prompt in this same session to get the Copy-paste execution prompt.")
            print()
            print("⚠  Step 5 (Copy-paste execution prompt) must run in a SEPARATE session.")
            print("   Hand it to the user — do not execute it here.")

        elif mode == "pull":
            print("=" * 70)
            print("Pull-based planning prompt  [legacy --pull mode]")
            print("=" * 70)
            print()
            print(prompt)
            print()
            print("=" * 70)
            print()
            print("Note: In pull mode, the agent reads context files itself.")
            print("For better reliability and token safety, use default (push-based) mode.")
            print()
            print("ACTION REQUIRED — execute the planning prompt above in this session.")
            print("After completion → step 4 → Copy-paste execution prompt → SEPARATE session.")

        else:  # quick
            print("=" * 70)
            print("Copy-paste execution prompt  [quick mode — no LLM synthesis]")
            print("=" * 70)
            print()
            print(prompt)
            print()
            print("=" * 70)
            print()
            print("⚠  Quick mode bypasses LLM planning (steps 2–4).")
            print("   Quality depends on EXEC_CONSTRAINTS being complete in the contract.")
            print("   For full synthesis run without --quick.")
            print()
            print("Next step: paste this prompt into a NEW agent session to execute the task.")
    else:
        label = {
            "resume": "Resume launcher",
            "selfcontained": "Planning launcher",
            "pull": "Planning launcher",
            "quick": "Execution launcher",
        }[mode]
        print("=" * 70)
        print(label)
        print("=" * 70)
        print(f"Package: {package_id}")
        print(f"Mode: {mode_label}")
        if launcher_ref:
            print(f"Prompt file: {launcher_ref}")
            print("Next step: open that file in a fresh agent session and execute only that file.")
            print("Do not expand the read-set to backlog/history/workflow docs unless the file explicitly names one.")
            print("If the session already contains long history or tool output, restart before executing.")
        else:
            print("Prompt file: not persisted in this mode.")
            print("Use --stdout-mode full if you need the inline prompt body.")

    if preflight_status == "WARN":
        print("\n⚠  Preflight WARN — agent must compress read-set (see doc/token_safety.md).")
    elif preflight_status == "BLOCK":
        print("\n⛔ Preflight BLOCK — agent must use rg/grep/section reads only (see doc/token_safety.md).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
