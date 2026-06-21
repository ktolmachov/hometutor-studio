#!/usr/bin/env python3
"""
prompt_utils.py — Canonical shared library for hometutor workflow scripts.

Shared library for registry-first package discovery (``parse_truth_view_from_registry``),
work-state detection, context extraction, and pipeline metrics. ``parse_truth_view(text)``
parses an in-memory ``## Now`` markdown table (fixtures / tooling only) — workflow routing
never falls back to ``doc/tasklist.md`` for Truth View.

Import pattern (from within scripts/):
    from prompt_utils import (
        parse_truth_view_from_registry, select_package, parse_contract,
        extract_dod_commands, detect_work_state, ...
    )

Or from project root:
    import sys; sys.path.insert(0, "scripts")
    from prompt_utils import ...
"""

from __future__ import annotations

import io
import re
import subprocess
from dataclasses import dataclass
import sys
from collections.abc import Iterable
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root & canonical paths
# ---------------------------------------------------------------------------
# Local note: `epoch-demo` smoke touches this file to satisfy execution hard gate.

ROOT             = Path(__file__).resolve().parents[1]
TASKLIST         = ROOT / "doc" / "tasklist.md"
BACKLOG_REGISTRY = ROOT / "doc" / "backlog_registry.yaml"
CLOSED_ITERS     = ROOT / "doc" / "closed_iterations.md"
CJM_PATH         = ROOT / "doc" / "cjm.md"
US_DIR           = ROOT / "doc" / "user_stories"
TEAM_ARTIFACTS   = ROOT / "archive" / "team_artifacts"
AGENT_PROMPTS    = ROOT / "archive" / "agent_prompts"
PIPELINE_METRICS = ROOT / "archive" / "pipeline_metrics.md"
TEAM_WORKFLOW    = ROOT / "doc" / "team_workflow"
TEAM_WORKFLOW_GUIDES = TEAM_WORKFLOW / "guides"

# Canonical agent vocabulary for workflow scripts.
# `kilo` uses the same file-delivery/orchestration behavior as Cursor today.
AUTONOMOUS_AGENT_CHOICES = ("cursor_ai", "codex", "kilo", "claude_code", "continue")
GUI_TASK_AGENTS = frozenset({"cursor_ai", "codex", "kilo", "continue"})
AGENT_ADAPTER_ALIASES = {
    "kilo": "cursor_ai",
}

# Orchestration agent id → adapter markdown basename (under team_workflow/guides/).
AGENT_ADAPTER_FILES: dict[str, str] = {
    "cursor_ai": "agent_adapter_cursor_ai.md",
    "claude_code": "agent_adapter_claude_code.md",
    "codex": "agent_adapter_codex.md",
    "kilo": "agent_adapter_kilo.md",
    "continue": "agent_adapter_continue.md",
}

# ---------------------------------------------------------------------------
# Canonical status vocabulary
# Ordered by priority: first match wins in select_package().
# Covers both orchestration ('open') and execution ('wip'/'WIP') workflows.
# ---------------------------------------------------------------------------

STATUS_PRIORITY = ["wip", "WIP", "ready", "open", "proposed"]
ACTIVE_STATUSES = frozenset(s.lower() for s in STATUS_PRIORITY)
NOW_STATUSES = frozenset({"wip", "ready"})

# Budget profiles: strict is the default operating mode for prompt generation.
# relaxed keeps the canonical 12k/20k token policy, but allows slightly larger
# injected fragments before spilling to payload.
BUDGET_PROFILES = {
    "strict": {
        "inject_chars": 2200,
        "cursor_task_char_limit": 90_000,
        "cursor_task_line_limit": 250,
        "soft_token_limit": 10_000,
        "hard_token_limit": 16_000,
        "overhead_tokens": 4_000,
        "ui_char_limit": 128_000,
    },
    "relaxed": {
        "inject_chars": 3000,
        "cursor_task_char_limit": 100_000,
        "cursor_task_line_limit": 250,
        "soft_token_limit": 12_000,
        "hard_token_limit": 20_000,
        "overhead_tokens": 3_000,
        "ui_char_limit": 128_000,
    },
}
DEFAULT_BUDGET_PROFILE = "strict"

# Backward-compatible module constants used by existing scripts/tests.
MAX_INJECT_CHARS = BUDGET_PROFILES[DEFAULT_BUDGET_PROFILE]["inject_chars"]
CURSOR_TASK_CHAR_LIMIT = BUDGET_PROFILES[DEFAULT_BUDGET_PROFILE]["cursor_task_char_limit"]


def budget_profile_choices() -> tuple[str, ...]:
    """Return supported budget profile names for CLI choices."""
    return tuple(BUDGET_PROFILES)


def resolve_agent_adapter_name(agent: str) -> str:
    """Map agent aliases to the canonical adapter/runtime identity."""
    normalized = (agent or "").strip().lower()
    return AGENT_ADAPTER_ALIASES.get(normalized, normalized)


def resolve_agent_adapter_file(agent: str, *, root: Path | None = None) -> Path:
    """Return agent adapter markdown path (guides/ canonical, team_workflow/ legacy fallback)."""
    normalized = (agent or "").strip().lower()
    filename = AGENT_ADAPTER_FILES.get(normalized)
    if filename is None:
        canonical = resolve_agent_adapter_name(agent)
        filename = AGENT_ADAPTER_FILES.get(canonical, f"agent_adapter_{canonical}.md")
    base = root or ROOT
    team_workflow = base / "doc" / "team_workflow"
    guides_path = team_workflow / "guides" / filename
    if guides_path.is_file():
        return guides_path
    return team_workflow / filename


def agent_adapters_map(*, root: Path | None = None) -> dict[str, Path]:
    """Registered orchestration agents → resolved adapter file paths."""
    return {
        agent_id: resolve_agent_adapter_file(agent_id, root=root)
        for agent_id in AGENT_ADAPTER_FILES
    }


def normalize_budget_profile(profile: str | None) -> str:
    """Normalize unknown / empty profile names to the default strict mode."""
    if not profile:
        return DEFAULT_BUDGET_PROFILE
    normalized = profile.strip().lower()
    if normalized not in BUDGET_PROFILES:
        return DEFAULT_BUDGET_PROFILE
    return normalized


def get_budget_profile(profile: str | None = None) -> dict[str, int | str]:
    """Return a copy of the resolved budget profile with its name included."""
    name = normalize_budget_profile(profile)
    resolved = dict(BUDGET_PROFILES[name])
    resolved["name"] = name
    return resolved


def write_task_file_for_cursor(
    *,
    no_pause_banner: str,
    body: str,
    footer: str,
    task_path: Path | None = None,
    payload_path: Path | None = None,
    char_limit: int | None = None,
    line_limit: int | None = None,
    budget_profile: str = DEFAULT_BUDGET_PROFILE,
    force_payload: bool = False,
) -> bool:
    """Write ``doc/current_task.md`` for GUI agents with optional context sidecar.

    Returns True when a context sidecar was used (spill), else False.
    """
    tpath = task_path or (ROOT / "doc" / "current_task.md")
    ppath = payload_path or (ROOT / "doc" / "context_pack.md")

    profile = get_budget_profile(budget_profile)
    resolved_limit = int(char_limit) if char_limit is not None else int(profile["cursor_task_char_limit"])
    resolved_line_limit = (
        int(line_limit) if line_limit is not None else int(profile["cursor_task_line_limit"])
    )

    body_norm = body.rstrip() + "\n"
    inline_full = f"{no_pause_banner}{body_norm}{footer}"

    should_spill = (
        force_payload
        or len(inline_full) > resolved_limit
        or len(inline_full.splitlines()) > resolved_line_limit
    )
    if not should_spill:
        if ppath.exists():
            try:
                ppath.unlink()
            except OSError:
                pass
        tpath.write_text(inline_full, encoding="utf-8")
        return False

    ppath.write_text(f"{no_pause_banner}{body_norm}", encoding="utf-8")
    write_set = _extract_markdown_section(body_norm, "Write-Set")
    write_set_block = f"{write_set}\n\n" if write_set else ""
    task_text = (
        f"{no_pause_banner}"
        "## Context Pack\n\n"
        f"See `{ppath.name}`.\n\n"
        f"{write_set_block}"
        f"{footer}"
    )
    tpath.write_text(task_text, encoding="utf-8")
    return True


def _extract_markdown_section(text: str, title: str) -> str:
    """Return a markdown section by title, stopping at the next same-level heading."""
    pattern = re.compile(
        rf"(?ms)^##[ \t]+{re.escape(title)}[ \t]*\n.*?(?=^##[ \t]+|\Z)"
    )
    match = pattern.search(text)
    return match.group(0).rstrip() if match else ""


# ---------------------------------------------------------------------------
# stdio
# ---------------------------------------------------------------------------

def ensure_utf8_stdio() -> None:
    """Re-wrap stdout/stderr as UTF-8 to avoid encoding errors on Windows."""
    # Prefer reconfigure(): it avoids wrapping buffers and the shutdown edge-case
    # "lost sys.stderr" that can happen when replacing sys.stderr with a new TextIOWrapper.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    elif hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", write_through=True)

    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    elif hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", write_through=True)


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def strip_cell(cell: str) -> str:
    """Strip whitespace and surrounding backticks from a table cell."""
    return cell.strip().strip("`").strip()


def clean(v: str) -> str:
    """Strip whitespace and surrounding backticks."""
    return v.strip().strip("`").strip()


def clean_inline(v: str) -> str:
    """Remove all inline backtick markup:  `word` → word."""
    return re.sub(r"`([^`]*)`", r"\1", v.strip()).strip()


def slug(s: str) -> str:
    """Convert a package ID like 'epoch-us7-3' to 'epoch_us7_3' for file matching."""
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


_EVIDENCE_PATH_RE = re.compile(
    r"(?i)\b((?:app|tests|scripts|src|eval_data|data|doc|\.github)/[^\s`,'\"]+\.(?:tsx|jsx|json|yaml|yml|md|py|ts|js))"
)
_EVIDENCE_SHA_RE = re.compile(r"(?im)^\s*[-*]?\s*(?:commit|sha)\s*:\s*`?([0-9a-f]{7,40})\b")
_EVIDENCE_HEADING_RE = re.compile(
    r"(?im)^\s*(?:#+\s*)?(?:pre-existing delivery evidence|evidence_of_preexisting_delivery)\s*:?\s*$"
)
_EVIDENCE_INCONCLUSIVE_MARKER_RE = re.compile(r"(?i)\bevidence_inconclusive_allowed\b")
VERIFICATION_ONLY_POLICY_LINE = "verification-only closure requires commit SHA + concrete file paths."
VERIFICATION_ONLY_INCONCLUSIVE_MARKER_LINE = (
    "If git change-proof is inconclusive, add `evidence_inconclusive_allowed` marker."
)


def verification_only_policy_guidance(indent: str = "") -> str:
    """Return standardized verification-only policy guidance lines."""
    return (
        f"{indent}{VERIFICATION_ONLY_POLICY_LINE}\n"
        f"{indent}{VERIFICATION_ONLY_INCONCLUSIVE_MARKER_LINE}"
    )


def parse_verification_only_evidence(text: str) -> dict[str, object]:
    """Extract structured evidence required for verification-only closure.

    Expected markers inside execution_contract.md:
      Pre-existing delivery evidence:
      - commit: abc1234
      - files: tests/foo.py, scripts/bar.py

    The files line may be omitted if concrete repo paths are listed elsewhere
    in the evidence block. This parser is intentionally tolerant and returns
    whatever it can recover.
    """
    normalized = text or ""
    lowered = normalized.lower()
    has_heading = (
        "pre-existing delivery evidence" in lowered
        or "evidence_of_preexisting_delivery" in lowered
    )
    evidence_text = normalized
    heading_match = _EVIDENCE_HEADING_RE.search(normalized)
    if heading_match:
        evidence_text = normalized[heading_match.end() :]
        next_section = re.search(r"(?m)^\s*(?:---|##\s+)", evidence_text)
        if next_section:
            evidence_text = evidence_text[: next_section.start()]

    commit_match = _EVIDENCE_SHA_RE.search(evidence_text)
    files = [m.group(1) for m in _EVIDENCE_PATH_RE.finditer(evidence_text)]
    return {
        "has_heading": has_heading,
        "commit": commit_match.group(1) if commit_match else None,
        "files": list(dict.fromkeys(files)),
    }


def _git_commit_exists(commit_sha: str, root: Path) -> bool:
    """Return whether commit_sha resolves to a commit in this repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit_sha}^{{commit}}"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except OSError:
        return False
    return result.returncode == 0


def _git_commit_contains_path(commit_sha: str, path: str, root: Path) -> bool:
    """Return whether path existed at commit_sha."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit_sha}:{path}"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except OSError:
        return False
    return result.returncode == 0


def _git_commit_changed_paths(commit_sha: str, root: Path) -> set[str]:
    """Return repo paths changed by commit_sha."""
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()
    stdout = getattr(result, "stdout", "") or ""
    return {line.strip() for line in stdout.splitlines() if line.strip()}


def _git_commit_touches_path_via_name_only(commit_sha: str, path: str, root: Path) -> bool:
    """Best-effort fallback for commits where diff-tree can be empty (root/merge edge cases)."""
    try:
        result = subprocess.run(
            ["git", "show", "--pretty=format:", "--name-only", commit_sha, "--", path],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False
    stdout = getattr(result, "stdout", "") or ""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return path in lines


def validate_verification_only_evidence(text: str, root: Path | None = None) -> tuple[bool, str | None]:
    """Return whether execution_contract.md contains enough audit evidence."""
    parsed = parse_verification_only_evidence(text)
    if not parsed["has_heading"]:
        return False, "missing 'Pre-existing delivery evidence' section"
    if not parsed["commit"]:
        return False, "missing commit SHA for the pre-existing delivery"
    if not parsed["files"]:
        return False, "missing concrete file paths for the pre-existing delivery"
    repo_root = root or ROOT
    commit_sha = str(parsed["commit"])
    if not _git_commit_exists(commit_sha, repo_root):
        return False, f"commit SHA does not resolve to a local git commit: {commit_sha}"
    missing = [
        str(path)
        for path in parsed["files"]
        if not (repo_root / str(path)).exists()
    ]
    if missing:
        return False, "pre-existing delivery evidence references missing file(s): " + ", ".join(missing)
    absent_at_commit = [
        str(path)
        for path in parsed["files"]
        if not _git_commit_contains_path(commit_sha, str(path), repo_root)
    ]
    if absent_at_commit:
        return False, (
            f"commit SHA does not contain referenced pre-existing file(s): {commit_sha} -> "
            + ", ".join(absent_at_commit)
        )
    changed_paths = _git_commit_changed_paths(commit_sha, repo_root)
    if changed_paths:
        changed_evidence = [str(path) for path in parsed["files"] if str(path) in changed_paths]
        if not changed_evidence:
            return False, (
                f"commit SHA does not change any referenced pre-existing file(s): {commit_sha} -> "
                + ", ".join(str(path) for path in parsed["files"])
            )
    else:
        # Fallback: for some commit topologies diff-tree may not report paths as expected.
        touched_via_show = [
            str(path)
            for path in parsed["files"]
            if _git_commit_touches_path_via_name_only(commit_sha, str(path), repo_root)
        ]
        # When diff-tree is inconclusive, git show is a secondary proof method.
        # The explicit marker is required only if both methods stay inconclusive.
        if touched_via_show:
            return True, None
        if not _EVIDENCE_INCONCLUSIVE_MARKER_RE.search(text or ""):
            return False, (
                "git change-proof for referenced files is inconclusive; add "
                "`evidence_inconclusive_allowed` marker to execution_contract.md "
                "or provide a commit where changed paths are explicit"
            )
    return True, None


def verification_evidence_changed_files(text: str, root: Path | None = None) -> set[str]:
    """Return evidence file paths that the referenced delivery commit changed.

    Callers use this after `validate_verification_only_evidence` succeeds to
    distinguish true "nothing had to change" verification from "the agent
    already committed/delivered the write-set before post-agent ran".
    """
    parsed = parse_verification_only_evidence(text)
    commit_sha = parsed.get("commit")
    files = [str(path) for path in parsed.get("files", [])]
    if not commit_sha or not files:
        return set()

    repo_root = root or ROOT
    changed_paths = _git_commit_changed_paths(str(commit_sha), repo_root)
    if changed_paths:
        return {path for path in files if path in changed_paths}

    return {
        path
        for path in files
        if _git_commit_touches_path_via_name_only(str(commit_sha), path, repo_root)
    }


# ---------------------------------------------------------------------------
# Closure mode detection (shared between run_autonomous.py and close_package.py)
# ---------------------------------------------------------------------------

# Longer extensions first so `.json` is not parsed as `.js`.
_CLOSURE_SRC_EXT_RE = re.compile(r"`([^`]+\.(?:tsx|jsx|json|yaml|yml|md|txt|py|ts|js))`")
_CLOSURE_SRC_PATH_RE = re.compile(
    r"(?:^|[\s|,])((?:app|tests|scripts|src|doc|archive)/\S+\.(?:tsx|jsx|json|yaml|yml|md|txt|py|ts|js))"
)
_CLOSURE_SRC_ROOTS = (
    "app/",
    "tests/",
    "scripts/",
    "src/",
    "eval_data/",
    "data/",
    "doc/",
    "archive/",
)


def parse_contract_write_set(contract: dict) -> list[str]:
    """Extract source file paths mentioned anywhere in the contract dict."""
    all_text = "\n".join(str(v) for v in contract.values())
    found: list[str] = []
    for m in _CLOSURE_SRC_EXT_RE.finditer(all_text):
        p = m.group(1)
        if "/" in p:
            found.append(p)
    for m in _CLOSURE_SRC_PATH_RE.finditer(all_text):
        found.append(m.group(1))
    return list(dict.fromkeys(found))


def _changed_src_files(root: Path) -> set[str] | None:
    """Return set of product-source files changed in working tree (staged + unstaged + untracked).

    Returns None on git failure (caller treats as "unknown").
    """
    try:
        res_diff = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            capture_output=True, text=True, cwd=str(root),
        )
        res_status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(root),
        )
    except OSError:
        return None
    changed: set[str] = set(res_diff.stdout.splitlines())
    for line in res_status.stdout.splitlines():
        if len(line) > 3:
            changed.add(line[3:].strip())
    return {f for f in changed if any(f.startswith(r) for r in _CLOSURE_SRC_ROOTS)}


def closure_mode_src_from_git_paths(changed_all: Iterable[str]) -> set[str]:
    """Набор product-путей из списка путей git (тот же фильтр, что и _changed_src_files)."""
    return {f for f in changed_all if any(f.startswith(r) for r in _CLOSURE_SRC_ROOTS)}


def git_head_commit_src_files(root: Path | None = None) -> set[str]:
    """Product-path files changed in HEAD (HEAD~1..HEAD).

    Used when the agent committed delivery before --post-agent / close_package ran,
    leaving ``git diff HEAD`` empty for write-set paths.
    """
    repo_root = root or ROOT
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD", "--name-only"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(repo_root),
        )
        if result.returncode != 0:
            return set()
        return closure_mode_src_from_git_paths(
            line.strip() for line in result.stdout.splitlines() if line.strip()
        )
    except OSError:
        return set()


def detect_closure_mode(
    package_id: str,
    contract: dict,
    root: Path | None = None,
    *,
    precomputed_src_changed: set[str] | None = None,
    precomputed_evidence_valid: bool | None = None,
) -> str:
    """Classify how this package was closed from working-tree git state.

    Returns one of 'execution', 'verification_only', 'unknown'.

    Callers that must handle agents who committed before ``--post-agent`` should
    use ``resolve_closure_mode`` instead — it applies HEAD/evidence upgrades on
    top of this base classifier.

    Hardening rules (stricter than previous substring-only logic):
      * Classifies as 'verification_only' ONLY when execution_contract.md
        passes `validate_verification_only_evidence` — malformed evidence falls
        through to 'unknown', which is blocked by callers.
      * Weak substring markers like "no changes" are NOT sufficient.
    """
    repo_root = root or ROOT
    write_set = parse_contract_write_set(contract)
    if precomputed_src_changed is not None:
        src_changed = set(precomputed_src_changed)
    else:
        src_changed = _changed_src_files(repo_root)
    if src_changed is None:
        return "unknown"

    exec_contract = repo_root / "archive" / "team_artifacts" / package_id / "execution_contract.md"
    if precomputed_evidence_valid is not None:
        evidence_valid = precomputed_evidence_valid
    elif exec_contract.exists():
        text = exec_contract.read_text(encoding="utf-8", errors="replace")
        ok, _reason = validate_verification_only_evidence(text, repo_root)
        evidence_valid = ok
    else:
        evidence_valid = False

    if write_set:
        overlap = src_changed & set(write_set)
        if overlap:
            return "execution"
        # Write-set known but none of those files changed — either pre-existing
        # delivery (requires valid evidence) or not executed.
        if evidence_valid:
            return "verification_only"
        return "unknown"

    # No write-set parsed from contract. We cannot tell whether src changes
    # are related to this package, so we refuse to classify as execution
    # unless there is also a record of intent (exec_contract present). To
    # prevent false-execution closures, require valid evidence OR require
    # src changes AND no exec_contract (likely a sync-agent run without
    # contract parse).
    if evidence_valid:
        return "verification_only"
    if src_changed and not exec_contract.exists():
        return "execution"
    return "unknown"


@dataclass(frozen=True)
class ClosureModeResolution:
    """Result of ``resolve_closure_mode`` — single SSoT for post-agent and close_package."""

    mode: str
    base_mode: str
    delivery_paths: frozenset[str]
    matched_write_set: frozenset[str]
    upgrade_reason: str | None = None


def resolve_closure_mode(
    package_id: str,
    contract: dict,
    root: Path | None = None,
    *,
    precomputed_src_changed: set[str] | None = None,
    precomputed_evidence_valid: bool | None = None,
    exec_contract_text: str | None = None,
) -> ClosureModeResolution:
    """Classify closure mode including pre-commit delivery upgrades.

    ``detect_closure_mode`` only inspects the working tree (``git diff HEAD``).
    Agents often commit before ``--post-agent`` runs, which leaves the working
    tree clean and yields ``unknown``. This helper applies the same upgrades
    everywhere in the pipeline:

      * ``unknown`` + HEAD commit touches write-set → ``execution``
      * ``verification_only`` + evidence commit touches write-set → ``execution``
    """
    repo_root = root or ROOT
    write_set = frozenset(parse_contract_write_set(contract))

    if precomputed_src_changed is not None:
        working_tree_paths = set(precomputed_src_changed)
    else:
        changed = _changed_src_files(repo_root)
        working_tree_paths = set(changed) if changed is not None else set()

    evidence_valid = precomputed_evidence_valid
    if evidence_valid is None:
        text = exec_contract_text
        if text is None:
            exec_contract = (
                repo_root / "archive" / "team_artifacts" / package_id / "execution_contract.md"
            )
            if exec_contract.exists():
                text = exec_contract.read_text(encoding="utf-8", errors="replace")
        if text is not None:
            evidence_valid, _reason = validate_verification_only_evidence(text, repo_root)
        else:
            evidence_valid = False

    base_mode = detect_closure_mode(
        package_id,
        contract,
        repo_root,
        precomputed_src_changed=working_tree_paths,
        precomputed_evidence_valid=evidence_valid,
    )

    delivery_paths = set(working_tree_paths)
    mode = base_mode
    upgrade_reason: str | None = None

    if mode == "unknown" and write_set:
        head_src = git_head_commit_src_files(repo_root)
        head_overlap = head_src & write_set
        if head_overlap:
            mode = "execution"
            upgrade_reason = "head_commit"
            delivery_paths |= head_src

    if (
        mode == "verification_only"
        and evidence_valid
        and write_set
        and exec_contract_text is not None
    ):
        evidence_changed = verification_evidence_changed_files(exec_contract_text, repo_root)
        evidence_overlap = evidence_changed & write_set
        if evidence_overlap:
            mode = "execution"
            upgrade_reason = "evidence_commit"
            delivery_paths |= evidence_changed

    matched = frozenset(delivery_paths & write_set) if write_set else frozenset()
    return ClosureModeResolution(
        mode=mode,
        base_mode=base_mode,
        delivery_paths=frozenset(delivery_paths),
        matched_write_set=matched,
        upgrade_reason=upgrade_reason,
    )


def format_closure_mode_upgrade_notice(
    resolution: ClosureModeResolution,
    *,
    success_prefix: bool = False,
) -> str | None:
    """Human-readable upgrade line when resolve_closure_mode promoted the mode."""
    if not resolution.upgrade_reason or not resolution.matched_write_set:
        return None
    matched = sorted(resolution.matched_write_set)
    prefix = "✅ " if success_prefix else ""
    if resolution.upgrade_reason == "head_commit":
        return (
            f"\n{prefix}[closure] HEAD commit contains write-set paths — "
            "upgrading to execution mode.\n"
            f"  Matched: {matched}\n"
            "  (Agent committed before close; git diff HEAD was empty.)"
        )
    if resolution.upgrade_reason == "evidence_commit":
        return (
            f"\n{prefix}[closure] Evidence commit contains write-set paths — "
            "upgrading to execution mode.\n"
            f"  Matched: {matched}\n"
            "  (Delivery was already present when closure ran.)"
        )
    return None


def extract_list_items(raw: str) -> list[str]:
    """
    Parse bullet-list or comma-separated contract values into a flat item list.

    Examples:
      "- foo\\n- bar" -> ["foo", "bar"]
      "`a`, `b`"     -> ["a", "b"]
      "1. Alpha"     -> ["Alpha"]
    """
    if not raw.strip():
        return []

    items: list[str] = []
    for line in raw.splitlines():
        cleaned = line.strip().strip("`").strip()
        if not cleaned:
            continue
        cleaned = re.sub(r"^(?:[-*]|\d+[.)])\s+", "", cleaned).strip()
        if cleaned:
            items.append(cleaned)

    if len(items) <= 1 and "," in raw:
        return [clean(part) for part in raw.split(",") if clean(part)]
    return items


# ---------------------------------------------------------------------------
# Safe file reading
# ---------------------------------------------------------------------------

def read_safe(path: Path) -> str:
    """Read a file; return '[FILE NOT FOUND: name]' placeholder if missing."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"[FILE NOT FOUND: {path.name}]"


def read_or_none(path: Path) -> str | None:
    """Read a file; return None if missing."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Backlog registry - Truth View / Now / Wave queue
# ---------------------------------------------------------------------------

def load_backlog_registry(path: Path | None = None) -> dict:
    """Load backlog_registry.yaml, returning {} when it is unavailable."""
    registry_path = path or BACKLOG_REGISTRY
    if not registry_path.exists():
        return {}
    try:
        import yaml as _yaml  # noqa: PLC0415
    except ImportError:
        return {}
    try:
        data = _yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - workflow discovery falls back gracefully
        return {}
    return data if isinstance(data, dict) else {}


def _registry_list(value: object) -> list[str]:
    """Normalize registry scalar/list fields into display-safe string lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _registry_status(item: dict) -> str:
    return str(item.get("status", "")).strip().lower()


def _registry_items(registry_data: dict) -> list[dict]:
    items = registry_data.get("items") or []
    return [item for item in items if isinstance(item, dict)]


def _registry_waves(registry_data: dict) -> list[dict]:
    waves = registry_data.get("waves") or []
    return [wave for wave in waves if isinstance(wave, dict)]


def _registry_active_wave(registry_data: dict) -> dict | None:
    """Return active wave using the same priority as backlog_registry_lint."""
    explicit = registry_data.get("active_wave_id")
    waves = _registry_waves(registry_data)
    if explicit:
        for wave in waves:
            if wave.get("id") == explicit and _registry_status(wave) not in {"completed", "frozen"}:
                return wave
    for status in ("wip", "ready", "proposed"):
        for wave in waves:
            if _registry_status(wave) == status:
                return wave
    return None


def normalize_registry_optional_id(value: object) -> str | None:
    """Normalize top-level registry pointers (active_package_id, etc.)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "~"}:
        return None
    return text


def collect_now_ready_wip_package_ids(registry_data: dict) -> list[str]:
    """Package ids whose items[].status is ready or wip (Truth View execution slot)."""
    ids: list[str] = []
    for item in _registry_items(registry_data):
        if _registry_status(item) not in NOW_STATUSES:
            continue
        pid = item.get("id")
        if pid:
            ids.append(str(pid))
    return ids


def lint_active_package_pointer(registry_data: dict) -> list[str]:
    """Validate optional ``active_package_id`` against ready/wip singleton rule.

    Expect ``registry_data`` to already satisfy at most one ready/wip package
    (enforced by backlog_registry_lint / roadmap_sync_check). When multiple
    ready/wip rows exist, this function skips pointer checks (caller reports).
    """
    errors: list[str] = []
    now_ids = collect_now_ready_wip_package_ids(registry_data)
    explicit = normalize_registry_optional_id(registry_data.get("active_package_id"))
    if len(now_ids) > 1:
        return errors
    if len(now_ids) == 1:
        sole = now_ids[0]
        if explicit and explicit != sole:
            errors.append(
                f"active_package_id is {explicit!r} but sole ready/wip package is {sole!r}"
            )
        if explicit:
            item = next(
                (it for it in _registry_items(registry_data) if str(it.get("id")) == explicit),
                None,
            )
            if item is None:
                errors.append(f"active_package_id {explicit!r} does not match any items[].id")
            elif _registry_status(item) not in NOW_STATUSES:
                errors.append(
                    f"active_package_id {explicit!r} points to package status "
                    f"{_registry_status(item)!r}, expected ready or wip"
                )
    elif explicit:
        errors.append(
            f"active_package_id is set ({explicit!r}) but no package has status ready or wip"
        )
    return errors


def resolve_active_package_id(
    registry_path: Path | None = None,
    registry_data: dict | None = None,
) -> str | None:
    """Resolve the execution-focus package id (O(1) pointer when consistent).

    Reads optional top-level ``active_package_id`` plus ready/wip rows.
    Returns ``None`` when ambiguous, missing, or when ``active_package_id`` drifts.
    """
    data = registry_data if registry_data is not None else load_backlog_registry(registry_path)
    if not data:
        return None
    explicit = normalize_registry_optional_id(data.get("active_package_id"))
    now_ids = collect_now_ready_wip_package_ids(data)
    if len(now_ids) > 1:
        return None
    sole = now_ids[0] if now_ids else None
    if sole is None:
        return None
    if explicit and explicit != sole:
        return None
    return sole


def get_backlog_truth_view(
    registry_path: Path | None = None,
    registry_data: dict | None = None,
) -> dict[str, object]:
    """Return registry-derived workflow view for Truth View, Wave queue, and Now.

    This is the canonical read API for current package state. It reads only
    backlog_registry.yaml and does not inspect generated tasklist.md sections.

    Pass ``registry_data`` to avoid re-reading the file when already loaded.
    """
    if registry_data is None:
        registry_data = load_backlog_registry(registry_path)
    priority_map = {status.lower(): i for i, status in enumerate(STATUS_PRIORITY)}
    rows: list[dict[str, str]] = []

    for item in _registry_items(registry_data):
        status = _registry_status(item)
        if status not in ACTIVE_STATUSES:
            continue
        package_id = str(item.get("id", "")).strip()
        if not package_id:
            continue
        user_stories = _registry_list(item.get("user_stories"))
        cjm_moments = _registry_list(item.get("cjm_moments"))
        rows.append(
            {
                "package": package_id,
                "status": status,
                "cjm": ", ".join(cjm_moments) or "-",
                "primary_us": user_stories[0] if user_stories else "-",
                "cjm_moments": cjm_moments,
                "user_stories": user_stories,
                "owner": str(item.get("owner") or "Auto"),
                "notes": str(item.get("notes") or "").replace("\n", " ").strip(),
                "wave_id": str(item.get("wave_id") or ""),
            }
        )
    rows.sort(key=lambda row: (priority_map.get(row["status"].lower(), 999), row["package"]))

    active_wave = _registry_active_wave(registry_data)
    active_wave_id = str(active_wave.get("id", "")) if active_wave else ""
    other_waves: list[dict[str, object]] = []
    for wave in _registry_waves(registry_data):
        if active_wave is not None and wave is active_wave:
            continue
        if _registry_status(wave) in {"proposed", "ready"}:
            other_waves.append(
                {
                    "id": str(wave.get("id", "")),
                    "packages": _registry_list(wave.get("packages")),
                    "kill_switch": str(wave.get("kill_switch") or ""),
                }
            )

    resolved_active = resolve_active_package_id(registry_data=registry_data)

    return {
        "truth_view": [row for row in rows if row["status"] in NOW_STATUSES],
        "now": rows,
        "resolved_active_package": resolved_active,
        "active_wave": active_wave_id or None,
        "wave_queue": {
            "active_wave": active_wave_id or None,
            "queued_same_wave": _registry_list(active_wave.get("packages")) if active_wave else [],
            "queued_other_waves": other_waves,
            "north_star": str(active_wave.get("north_star") or "") if active_wave else "",
            "kill_switch": str(active_wave.get("kill_switch") or "") if active_wave else "",
        },
    }


def active_ready_package_from_registry(registry_path: Path | None = None) -> str | None:
    """Return the highest-priority ready/wip package id from backlog registry."""
    data = load_backlog_registry(registry_path)
    resolved = resolve_active_package_id(registry_data=data)
    if resolved is not None:
        return resolved
    # Invalid explicit pointer — do not fall back to STATUS_PRIORITY guessing.
    if normalize_registry_optional_id(data.get("active_package_id")) is not None:
        return None
    rows = [
        row
        for row in get_backlog_truth_view(registry_data=data).get("now", [])
        if isinstance(row, dict) and row.get("status") in NOW_STATUSES
    ]
    selected = select_package(rows, None)
    return str(selected["package"]) if selected else None


def parse_truth_view_from_registry() -> list[dict[str, str]]:
    """Read current workflow rows directly from backlog_registry.yaml (SSoT)."""
    rows = get_backlog_truth_view().get("now", [])
    return [row for row in rows if isinstance(row, dict)]


def parse_truth_view(text: str) -> list[dict[str, str]]:
    """Parse a ``## Now`` Truth View-style markdown table from a string.

    Used by unit tests and ad-hoc tooling; **not** the operational workflow path
    (that is ``parse_truth_view_from_registry()`` → ``doc/backlog_registry.yaml``).

    ``text`` may be the contents of a generated ``doc/tasklist.md`` or any snippet
    containing the same table shape — this function does not read files.

    Returns row dicts with at least ``package`` and ``status``; other columns
    (cjm, primary_us, owner, notes) are included when present in the header row.
    """
    rows: list[dict[str, str]] = []
    now_section = re.search(r"## Now\b.*", text, re.DOTALL)
    if not now_section:
        return rows
    section = text[now_section.start():]
    nxt = re.search(r"\n## ", section[4:])
    if nxt:
        section = section[: nxt.start() + 4]

    headers: list[str] = []
    header_seen = separator_seen = in_table = False

    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                # Allow visual blank lines inside Truth View tables.
                if stripped == "":
                    continue
                break
            continue
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c != ""]
        if not header_seen:
            lower = [strip_cell(c).lower() for c in cells]
            if "package" in lower and "status" in lower:
                headers = lower
                header_seen = in_table = True
            continue
        if not separator_seen:
            separator_seen = True
            continue
        if len(cells) < 2:
            continue
        row = {headers[i]: strip_cell(cells[i]) for i in range(min(len(headers), len(cells)))}
        if "package" in row and "status" in row:
            rows.append(row)
    return rows


def select_package(rows: list[dict[str, str]], explicit: str | None) -> dict[str, str] | None:
    """
    Select a package row.

    If explicit is given, returns the first row whose 'package' matches.
    Otherwise selects by STATUS_PRIORITY order (first match wins).
    """
    if explicit:
        for r in rows:
            if r.get("package") == explicit:
                return r
        return None
    for prio in STATUS_PRIORITY:
        for r in rows:
            if r.get("status", "").lower() == prio.lower():
                return r
    return None


# ---------------------------------------------------------------------------
# Tasklist — Package contract parsing
# ---------------------------------------------------------------------------

def parse_contract(text: str, package_id: str) -> dict[str, str]:
    """
    Resolve package contract with ``doc/backlog_registry.yaml`` as SSoT.

    Registry entry always wins; no read of ``doc/tasklist.md`` is performed for that.

    If the package is **missing** from the registry, ``text`` may supply an in-memory
    markdown document containing ``### <package_id> Contract`` (unit tests, snippets).
    Pass ``text=""`` in normal tooling so only the registry is used. This embedded-block
    path is **not** a supported operational fallback when the YAML is empty or stale —
    fix or sync the registry instead.
    """
    reg = _load_contract_from_registry(package_id)
    if reg:
        return reg
    if not (text or "").strip():
        return {}
    header = f"### {package_id} Contract"
    start = text.find(header)
    if start == -1:
        return {}

    block = text[start:]
    # Isolate the block (stop at next ## or ### heading)
    end_m = re.search(r"\n(?:## |### )", block[len(header):])
    if end_m:
        block = block[: len(header) + end_m.start()]

    # Detect format by presence of a | Field | Value | metadata table
    if re.search(r"^\s*\|\s*[Ff]ield\s*\|", block, re.MULTILINE):
        contract = _parse_contract_table(block)
    else:
        contract = _parse_contract_bullets(block, package_id)

    # Post-process: extract TARGET_ARTIFACTS from the | Target artifact | ... | content table
    # This table is not in Field/Value format so the main parsers miss it.
    if "TARGET_ARTIFACTS" not in contract or not contract["TARGET_ARTIFACTS"]:
        _artifact_re = re.compile(
            r"^\|\s*`([^`]+\.(?:tsx|jsx|json|yaml|yml|py|ts|js))`",
            re.MULTILINE,
        )
        artifacts = [m.group(1) for m in _artifact_re.finditer(block)]
        if artifacts:
            contract["TARGET_ARTIFACTS"] = "\n".join(artifacts)

    return contract


def _load_contract_from_registry(package_id: str) -> dict[str, str] | None:
    """Best-effort: synthesize a contract dict from `doc/backlog_registry.yaml` (SSoT)."""
    try:
        import yaml as _yaml  # noqa: PLC0415
    except ImportError:
        return None
    registry_path = ROOT / "doc" / "backlog_registry.yaml"
    if not registry_path.exists():
        return None
    try:
        data = _yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("items") or []
    if not isinstance(items, list):
        return None
    targets = {package_id, f"epoch-{package_id}", package_id.removeprefix("epoch-")}
    item = next(
        (
            it
            for it in items
            if isinstance(it, dict) and str(it.get("id", "")).strip() in targets
        ),
        None,
    )
    if not item:
        return None
    canonical_id = str(item.get("id", package_id)).strip()

    dod = item.get("dod_commands") or item.get("dod") or []
    if isinstance(dod, str):
        dod_lines = [dod]
    else:
        dod_lines = [str(x) for x in dod if str(x).strip()]

    blocks = str(item.get("blocks") or "").strip()
    exit_artifact = str(item.get("exit_artifact") or "").strip()
    notes = str(item.get("notes") or "").strip()
    cjm = item.get("cjm_moments") or []
    cjm_text = ", ".join(str(x) for x in cjm) if isinstance(cjm, list) else str(cjm)
    us = item.get("user_stories") or []
    us_text = ", ".join(str(x) for x in us) if isinstance(us, list) else str(us)
    read_set = item.get("read_set_hint") or []
    if isinstance(read_set, str):
        read_set = [read_set]
    read_set_lines = "\n".join(str(x) for x in read_set if str(x).strip())

    outcomes_parts: list[str] = []
    base_out = (blocks or exit_artifact or notes or "").strip()
    if base_out:
        outcomes_parts.append(base_out)
    arch_contract = str(item.get("architectural_contract") or "").strip()
    if arch_contract:
        outcomes_parts.append(arch_contract)
    write_items = item.get("write_set") or []
    if isinstance(write_items, str):
        write_items = [write_items]
    write_bullets = "\n".join(
        f"- `{str(x).strip()}`" for x in write_items if str(x).strip()
    )
    if write_bullets:
        outcomes_parts.append(write_bullets)
    outcomes_merged = "\n\n".join(outcomes_parts) if outcomes_parts else ""

    contract: dict[str, str] = {
        "PACKAGE_ID": canonical_id,
        "PACKAGE_TITLE": (blocks or exit_artifact or notes or canonical_id)[:120],
        "CJM_STAGE": cjm_text or "unknown",
        "USER_STORIES": us_text or "n/a",
        "DOD_COMMANDS": "\n".join(dod_lines) if dod_lines else "",
        "OUTCOMES": outcomes_merged,
        "WRITE_SET_MAX": str(item.get("write_set_max") or 5),
        "TARGET_ARTIFACTS": exit_artifact or "",
        "READ_SET_HINT": read_set_lines,
        "NOTES": notes,
        "WAVE_ID": str(item.get("wave_id") or ""),
        "STATUS": str(item.get("status") or ""),
    }

    # Policy marker required for verification-only closure hard gate in run_autonomous.py
    avo = item.get("allow_verification_only")
    if avo:
        contract["ALLOW_VERIFICATION_ONLY"] = str(avo)

    return contract


# Canonical key aliases: map human-readable bullet keys → script keys
_BULLET_KEY_MAP: dict[str, str] = {
    "title":          "PACKAGE_TITLE",
    "package title":  "PACKAGE_TITLE",
    "cjm":            "CJM_STAGE",
    "cjm stage":      "CJM_STAGE",
    "user story":     "USER_STORIES",
    "user stories":   "USER_STORIES",
    "pain point":     "PAIN_POINT",
    "outcomes":       "OUTCOMES",
    "dod":            "DOD_CHECKLIST",  # checkbox items - [ ] ...
    "dod commands":   "DOD_COMMANDS",   # standalone **DoD commands** heading (executable)
    "dod_commands":   "DOD_COMMANDS",   # inline single-line DoD (executable)
    "exec_constraints":    "EXEC_CONSTRAINTS",
    "write-set max":  "WRITE_SET_MAX",
    "write_set_max":  "WRITE_SET_MAX",
    "rationale":      "RATIONALE",
    "metrics":        "METRICS",
    "target artifacts": "TARGET_ARTIFACTS",
    "read-set hint":  "READ_SET_HINT",
}


def _normalise_bullet_key(raw: str) -> str:
    """Lowercase + strip backticks/asterisks → canonical alias lookup."""
    k = raw.strip().lower().strip("`*").strip()
    return _BULLET_KEY_MAP.get(k, k.upper().replace(" ", "_").replace("-", "_"))


def _parse_contract_table(block: str) -> dict[str, str]:
    """Parse the legacy | Field | Value | table format."""
    contract: dict[str, str] = {}
    in_table = header_seen = separator_seen = False

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c != ""]
        if not header_seen:
            lower = [c.lower() for c in cells]
            if "field" in lower and "value" in lower:
                header_seen = in_table = True
            continue
        if not separator_seen:
            separator_seen = True
            continue
        if len(cells) < 2:
            continue
        contract[strip_cell(cells[0])] = cells[1].strip()
    return contract


def _parse_contract_bullets(block: str, package_id: str) -> dict[str, str]:
    """Parse bullet-list contracts like '- **Key:** value' or '- `KEY`: value'.

    Also handles standalone bold section headers (no leading dash):
        **DoD commands**
        - `pytest ...`

    Multi-line values (indented sub-bullets) are joined into a single string.
    """
    contract: dict[str, str] = {"PACKAGE_ID": package_id}

    # Matches bullet-key lines:
    #   - **Key:** value
    #   - `KEY`: value
    key_re = re.compile(r"^-\s+(?:\*\*([^*:]+):\*\*|`([^`]+)`:)\s*(.*)")

    # Matches standalone bold section headings (no dash, no colon):
    #   **DoD commands**
    #   **Metrics**
    section_re = re.compile(r"^\*\*([^*]+)\*\*\s*$")

    current_key: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_key is None:
            return
        # Join multi-line values; strip backtick fencing per item
        value = "\n".join(
            line.strip().strip("`").rstrip("`").strip()
            for line in current_lines
            if line.strip()
        )
        canon = _normalise_bullet_key(current_key)
        if canon not in contract:
            contract[canon] = value
        elif not contract[canon]:
            # Overwrite empty slots (e.g. key seen twice, second has actual value)
            contract[canon] = value

    for line in block.splitlines():
        m = key_re.match(line)
        if m:
            _flush()
            current_key = (m.group(1) or m.group(2) or "").strip()
            inline_val  = m.group(3).strip().strip("`").strip()
            current_lines = [inline_val] if inline_val else []
        elif s := section_re.match(line):
            # Standalone **Section heading** — treat as a new key with no inline value.
            # This captures patterns like "**DoD commands**" written by agents.
            _flush()
            current_key = s.group(1).strip()
            current_lines = []
        elif current_key is not None and re.match(r"^-\s+", line):
            # Current tasklist format often uses same-level bullets under a key:
            # - `OUTCOMES`:
            # - first item
            # - second item
            current_lines.append(line.strip().lstrip("-").strip())
        elif current_key is not None and (line.startswith("  ") or line.startswith("\t")):
            # Indented continuation / sub-bullet
            current_lines.append(line.strip().lstrip("-").strip())
        elif current_key is not None and line.strip() == "":
            current_lines.append("")
        else:
            # Non-indented, non-key line → end of current field
            if current_key is not None:
                _flush()
                current_key = None
                current_lines = []

    _flush()
    return contract


# ---------------------------------------------------------------------------
# DoD command extraction
# ---------------------------------------------------------------------------

def extract_dod_commands(raw: str) -> list[str]:
    """
    Split DoD commands handling both separators:

    - Semicolon-separated (legacy inline):
        python -m pytest foo.py -v; python scripts/check.py

    - Newline-separated (bullet-list format from generated tasklist.md):
        python -m pytest foo.py -v
        python scripts/check.py

    Semicolons INSIDE quotes are preserved:
        python -c "import json; json.load(...)"

    The heuristic:
    - if there are multiple newline-separated command-looking lines, keep those
    - ignore non-command prose lines that may appear in the same section
    - otherwise fall back to the quote-aware semicolon split
    """
    raw = raw.strip()
    if not raw:
        return []

    # Newline-separated: split if raw contains actual line breaks
    # and none of the lines are wrapped continuations (no trailing backslash)
    lines = [l.strip().strip("`").strip() for l in raw.splitlines()]
    lines = [l for l in lines if l]

    if len(lines) > 1:
        # Each line must look like a command start, not a continuation
        _CMD_START = re.compile(
            r"^(python|pytest|npm|node|rg|grep|git|bash|sh|powershell|"
            r"scripts/|doc/|app/|\.venv[/\\]|\.[/\\])", re.IGNORECASE,
        )
        command_lines = [l for l in lines if _CMD_START.match(l)]
        if command_lines:
            return command_lines

    # Fall back: quote-aware semicolon split (handles python -c "...; ...")
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
        elif ch == ";" and not in_single and not in_double:
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


# ---------------------------------------------------------------------------
# US ID extraction
# ---------------------------------------------------------------------------

def extract_us_ids(raw: str) -> list[str]:
    """Extract all 'US-N.M' identifiers from a string.

    Duplicates are collapsed case-insensitively while the first occurrence
    (and its casing) is preserved.  This prevents double-counting when the
    same story is mentioned multiple times in a contract section.
    """
    seen: set[str] = set()
    out: list[str] = []
    for match in re.findall(r"US-[\d.]+", raw, re.IGNORECASE):
        key = match.lower()
        if key not in seen:
            seen.add(key)
            out.append(match)
    return out


# ---------------------------------------------------------------------------
# Complexity model — continuous composite score
# ---------------------------------------------------------------------------
#
# Design goals (breakthrough over the previous step-function heuristic):
#   1. Log-scaled size signals      — a package with 5 files and one with 50
#                                     must not get the same contribution.
#   2. Excess-over-baseline         — the median package has 2 writes, 1 cmd,
#                                     2 outcomes, 1 story.  Only deviation
#                                     from this baseline adds complexity.
#   3. Shannon entropy over dirs    — 5 files in a single dir ≠ 5 files
#                                     scattered across 5 subsystems.
#   4. Hot-path detection           — schema / migration / auth / config /
#                                     pipeline paths always raise risk.
#   5. Risk keywords                — "breaking", "migrate", "rollback",
#                                     "security", etc. in OUTCOMES/RATIONALE.
#   6. DoD operation atomization    — split &&, || and ; so that a single
#                                     chained command counts as multiple ops.
#   7. Linear constraint density    — 1 vs 10 EXEC_CONSTRAINTS must differ.
#   8. Deduped user stories         — same US mentioned twice counts once.
#   9. Drivers + confidence         — per-signal contribution is auditable,
#                                     distance to threshold reported as
#                                     low / medium / high confidence.
#  10. Override keeps audit trail   — operator override wins for routing,
#                                     but computed label & score are preserved
#                                     so the heuristic can be recalibrated
#                                     against operator judgement over time.
#
# Calibration anchors (unit-tested):
#   compact contract (2 writes, 1 cmd, 2 outcomes, 1 story)  -> "low"
#   broad contract  (5 writes, 3 cmds, 4 outcomes, 2 stories,
#                    5 read-set hints)                       -> "high"

import math
from collections import Counter as _Counter

_HOT_PATH_PATTERNS = re.compile(
    r"(schema|migration|alembic|auth|security|secret|"
    r"config|settings|pipeline|orchestr|workflow|"
    r"core/|contract|tasklist|docker|\.github/|"
    r"pyproject|requirements|routing|router|entrypoint)",
    re.IGNORECASE,
)

_RISK_KEYWORDS = re.compile(
    r"\b(breaking|deprecat\w*|migrat\w*|rewrite|rollback|"
    r"destructive|concurren\w*|async\b|race\s*condition|"
    r"transaction|lock\b|security|authn?|permission|"
    r"regression|perf(?:ormance)?\b|schema\s+change|"
    r"data\s+loss|irreversibl\w*|backfill)\b",
    re.IGNORECASE,
)

# Default baseline (median contract): values equal to or below this
# contribute zero to the composite score.  Calibrated from observed
# compact packages in archive/team_artifacts/.
_BASELINE = {
    "write": 2,
    "dod_ops": 1,
    "outcomes": 2,
    "read_set": 2,
    "stories": 1,
}

# Signal weights chosen so that:
#   compact test contract  -> score ~0.7  (low)
#   broad   test contract  -> score ~4.7  (high)
# Weights reflect *causal impact on review effort* observed empirically.
_WEIGHTS = {
    "write_size":  1.5,  # primary cost driver
    "dod_ops":     1.0,  # verification surface
    "outcomes":    0.5,  # often redundant with stories
    "read_set":    0.5,  # hint only, not authoritative
    "stories":     1.0,  # story count = conceptual fan-in
    "dir_breadth": 1.5,  # cross-subsystem coupling
    "hot_paths":   1.5,  # risk multiplier per hit (linear, saturates at 3)
    "risk_kw":     0.8,  # per distinct keyword (saturates at 4)
    "constraints": 1.0,  # linear per constraint line (saturates at 2.0)
}

# Calibrated thresholds on the composite score.
_T_MEDIUM = 2.0
_T_HIGH   = 4.0


def _atomize_dod(dod_cmds: list[str]) -> int:
    """Count operations, splitting chained commands on &&, || and |.

    A single line like `pytest X && mypy Y && ruff check` contributes 3
    operations even though it was emitted as one command string.
    """
    total = 0
    for cmd in dod_cmds:
        parts = re.split(r"\s+(?:&&|\|\|)\s+", cmd)
        total += max(1, len([p for p in parts if p.strip()]))
    return total


def _write_set_dirs(write_items: list[str]) -> tuple[list[str], int, float]:
    """Return (top_level_dirs, unique_dir_count, Shannon_entropy_bits)."""
    dirs: list[str] = []
    for path in write_items:
        norm = path.strip().strip("`").strip().replace("\\", "/")
        parts = [p for p in norm.split("/") if p]
        dirs.append(parts[0] if parts else "?")
    if not dirs:
        return dirs, 0, 0.0
    counts = _Counter(dirs)
    total = sum(counts.values())
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    # Single-dir case produces -0.0 from Python arithmetic; normalise.
    return dirs, len(counts), abs(entropy)


def _excess(value: int, baseline: int) -> float:
    """log2-excess over baseline, clamped at zero.

    _excess(n, b) = max(0, log2(1+n) - log2(1+b))
    """
    return max(0.0, math.log2(1 + value) - math.log2(1 + baseline))


def _confidence(score: float) -> str:
    """Return 'high' / 'medium' / 'low' based on margin to nearest threshold."""
    margin = min(abs(score - _T_MEDIUM), abs(score - _T_HIGH))
    if margin >= 1.2:
        return "high"
    if margin >= 0.4:
        return "medium"
    return "low"


def classify_package_complexity(contract: dict[str, str]) -> dict[str, object]:
    """
    Estimate delivery complexity from a package contract.

    Returns a dict with the following keys:
      label         : 'low' | 'medium' | 'high'    (final routing label)
      score         : float — continuous composite score
      route         : 'execution_auto' | 'orchestration'
                       orchestration для medium и high; execution_auto для low
      reasons       : top-N human-readable contributors
      drivers       : list[{signal, value, weight, contrib, note}] — per-signal audit
      confidence    : 'low' | 'medium' | 'high' | 'override'
      signals       : flat numeric snapshot of parsed indicators
      computed_label: always the heuristic label (== label unless override fires)

    Optional contract override — wins routing, does not erase audit trail:
      COMPLEXITY: low | medium | high
    """
    override = clean(contract.get("COMPLEXITY", "")).lower()

    write_items = extract_list_items(
        contract.get("WRITE_SET_MAX", "") or contract.get("WRITE_SET", "")
    )
    outcomes = extract_list_items(contract.get("OUTCOMES", ""))
    dod_cmds = extract_dod_commands(contract.get("DOD_COMMANDS", ""))
    dod_ops  = _atomize_dod(dod_cmds)
    us_ids   = extract_us_ids(contract.get("USER_STORIES", ""))
    read_set = extract_list_items(contract.get("READ_SET_HINT", ""))

    exec_raw = clean(contract.get("EXEC_CONSTRAINTS", ""))
    exec_lines = [l for l in exec_raw.splitlines() if l.strip()] if exec_raw else []

    _, unique_dirs, dir_entropy = _write_set_dirs(write_items)
    hot_hits = sum(1 for p in write_items if _HOT_PATH_PATTERNS.search(p))

    risk_blob = " ".join(
        contract.get(k, "") for k in
        ("OUTCOMES", "RATIONALE", "DOD_COMMANDS", "PAIN_POINT", "EXEC_CONSTRAINTS")
    )
    risk_hits = len({m.group(0).lower() for m in _RISK_KEYWORDS.finditer(risk_blob)})

    # --- per-signal values (pre-weight) ---
    v_write  = _excess(len(write_items), _BASELINE["write"])
    v_dod    = _excess(dod_ops,          _BASELINE["dod_ops"])
    v_out    = _excess(len(outcomes),    _BASELINE["outcomes"])
    v_read   = _excess(len(read_set),    _BASELINE["read_set"])
    v_story  = _excess(len(us_ids),      _BASELINE["stories"])
    # Entropy excess: >1 bit means "more than one dir is balanced" — real coupling.
    v_entropy    = max(0.0, dir_entropy - 0.5)
    v_hot        = min(3.0, float(hot_hits))           # linear, saturates at 3
    v_risk       = min(4.0, float(risk_hits))          # linear, saturates at 4
    v_constraint = min(2.0, len(exec_lines) * 0.5)     # 0.5 per line, cap 2.0

    drivers: list[dict[str, object]] = []
    score = 0.0

    def _add(name: str, value: float, weight: float, note: str) -> None:
        nonlocal score
        contrib = value * weight
        score += contrib
        if contrib >= 0.3:  # only surface meaningful drivers
            drivers.append({
                "signal":  name,
                "value":   round(value, 3),
                "weight":  weight,
                "contrib": round(contrib, 3),
                "note":    note,
            })

    _add("write_set_size", v_write,     _WEIGHTS["write_size"],
         f"{len(write_items)} files in WRITE_SET (baseline {_BASELINE['write']})")
    _add("dod_ops",        v_dod,       _WEIGHTS["dod_ops"],
         f"{dod_ops} DoD operations across {len(dod_cmds)} commands")
    _add("outcomes",       v_out,       _WEIGHTS["outcomes"],
         f"{len(outcomes)} outcomes declared")
    _add("read_set",       v_read,      _WEIGHTS["read_set"],
         f"{len(read_set)} read-set hints")
    _add("user_stories",   v_story,     _WEIGHTS["stories"],
         f"{len(us_ids)} distinct user stories")
    _add("dir_breadth",    v_entropy,   _WEIGHTS["dir_breadth"],
         f"write-set spans {unique_dirs} top dirs (entropy {dir_entropy:.2f} bits)")
    _add("hot_paths",      v_hot,       _WEIGHTS["hot_paths"],
         f"{hot_hits} writes hit hot paths (schema/auth/migrations/config/pipeline)")
    _add("risk_keywords",  v_risk,      _WEIGHTS["risk_kw"],
         f"{risk_hits} distinct risk keywords in contract prose")
    _add("exec_constraints", v_constraint, _WEIGHTS["constraints"],
         f"{len(exec_lines)} explicit execution constraints")

    if score >= _T_HIGH:
        computed_label = "high"
    elif score >= _T_MEDIUM:
        computed_label = "medium"
    else:
        computed_label = "low"

    signals = {
        "write_items":      len(write_items),
        "dod_cmds":         len(dod_cmds),
        "dod_ops":          dod_ops,
        "user_stories":     len(us_ids),
        "outcomes":         len(outcomes),
        "read_set":         len(read_set),
        "unique_dirs":      unique_dirs,
        "dir_entropy":      round(dir_entropy, 3),
        "hot_paths":        hot_hits,
        "risk_keywords":    risk_hits,
        "exec_constraints": len(exec_lines),
    }

    # Sort drivers by descending contribution for reasons & readability
    drivers.sort(key=lambda d: -float(d["contrib"]))
    reasons = [f"{d['note']} (+{d['contrib']:.2f})" for d in drivers[:4]]

    if override in {"low", "medium", "high"}:
        # Operator override wins routing, computed audit stays intact.
        return {
            "label":          override,
            "score":          round(score, 2),
            "computed_label": computed_label,
            "route":          "orchestration" if override in {"medium", "high"} else "execution_auto",
            "reasons":        [
                f"contract override: COMPLEXITY={override} "
                f"(computed={computed_label}, score={round(score, 2)})"
            ] + reasons[:2],
            "drivers":        drivers,
            "confidence":     "override",
            "signals":        {**signals, "override": override},
        }

    if not reasons:
        reasons = ["compact contract: suitable for direct execution flow"]

    return {
        "label":          computed_label,
        "score":          round(score, 2),
        "computed_label": computed_label,
        "route":          "orchestration" if computed_label in {"medium", "high"} else "execution_auto",
        "reasons":        reasons,
        "drivers":        drivers,
        "confidence":     _confidence(score),
        "signals":        signals,
    }


# ---------------------------------------------------------------------------
# Work-state detection
# ---------------------------------------------------------------------------

# Use string literals instead of enum to avoid import overhead in callers
WORK_STATE_FRESH          = "fresh"
WORK_STATE_PLANNING_ONLY  = "planning_only"
WORK_STATE_EXECUTION_READY = "execution_ready"


def execution_contract_is_substantive(path: Path) -> bool:
    """True when execution_contract.md is non-empty and not the STARTED sentinel."""
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return bool(text) and text.upper() != "STARTED"


def detect_work_state(package_id: str) -> str:
    """
    Determine how far along a package is.

    Returns one of:
      'fresh'           — no artifacts at all
      'planning_only'   — planning_prompt.md exists, no execution artefacts
      'execution_ready' — substantive execution_contract.md exists
    """
    pkg_dir = TEAM_ARTIFACTS / package_id
    contract = pkg_dir / "execution_contract.md"
    if execution_contract_is_substantive(contract):
        return WORK_STATE_EXECUTION_READY

    if (pkg_dir / "planning_prompt.md").exists():
        return WORK_STATE_PLANNING_ONLY

    return WORK_STATE_FRESH


def list_team_artifacts(package_id: str) -> list[str]:
    """Return filenames in team_artifacts/<package_id>/, sorted."""
    pkg_dir = TEAM_ARTIFACTS / package_id
    if not pkg_dir.exists():
        return []
    return sorted(f.name for f in pkg_dir.iterdir() if f.is_file())


# ---------------------------------------------------------------------------
# Context extraction
# ---------------------------------------------------------------------------

def extract_us_acceptance(us_id: str) -> str:
    """Extract acceptance criteria from doc/user_stories/<us_id>.md."""
    us_path = US_DIR / f"{us_id.lower()}.md"
    text = read_safe(us_path)
    if text.startswith("[FILE NOT FOUND"):
        return text
    m = re.search(r"\*\*Acceptance[^:]*:\*\*(.+?)(?=\n#{1,3} |\Z)", text, re.DOTALL)
    if m:
        return m.group(0).strip()[:MAX_INJECT_CHARS]
    m = re.search(r"#{2,4}[^#\n]*Acceptance[^\n]*\n(.+?)(?=\n#{2,4} |\Z)", text, re.DOTALL)
    if m:
        return m.group(0).strip()[:MAX_INJECT_CHARS]
    return "(Acceptance section not found)"


def extract_cjm_moment(cjm_stage: str) -> str:
    """
    Extract relevant lines from doc/cjm.md for the given CJM stage.
    Uses the first token of cjm_stage for the lookup
    (e.g. '#5' from '#5 — Return next day').
    """
    text = read_safe(CJM_PATH)
    if text.startswith("[FILE NOT FOUND"):
        return text
    # Use only the first meaningful token for lookup
    lookup_key = re.split(r"\s+—\s+|\s+", clean_inline(cjm_stage))[0]
    lines = text.splitlines()
    hits: list[str] = []
    for line in lines:
        if lookup_key.lower() in line.lower():
            hits.append(line)
    result = "\n".join(hits[:8]).strip()
    return result[:MAX_INJECT_CHARS] if result else f"(CJM stage '{lookup_key}' not found in cjm.md)"


def extract_recent_closed(n: int = 2) -> str:
    """Return the last N entries from doc/closed_iterations.md."""
    text = read_safe(CLOSED_ITERS)
    if text.startswith("[FILE NOT FOUND"):
        return text
    sections = re.split(r"\n(?=### )", text)
    entries = [s.strip() for s in sections if s.strip().startswith("### ")]
    recent = entries[-n:] if len(entries) >= n else entries
    return "\n\n".join(recent)[:MAX_INJECT_CHARS]


# ---------------------------------------------------------------------------
# Pipeline metrics
# ---------------------------------------------------------------------------

_METRICS_HEADER = (
    "# Pipeline Metrics\n\n"
    "**Как читать:**\n"
    "- `sp1_verdict` / `sp2_verdict`: PASS / CPASS (conditional) / FAIL→PASS / N/A\n"
    "- `retries`: суммарное число ретраев Developer\n"
    "- `escalations`: число раз, когда оркестратор остановился и спросил пользователя\n"
    "- `deferred`: число items в deferred.md на момент закрытия\n\n"
    "---\n\n"
    "| Package | Date | sp1_verdict | sp2_verdict | retries | escalations | deferred |\n"
    "|---------|------|:-----------:|:-----------:|:-------:|:-----------:|:--------:|\n"
)


def append_pipeline_metrics(
    package_id: str,
    today: str,
    note: str = "",
    *,
    sp1: str = "TBD",
    sp2: str = "TBD",
    retries: int = 0,
    escalations: int = 0,
    deferred: int = 0,
) -> None:
    """
    Append one row to archive/pipeline_metrics.md.

    Deduplication: if a row for package_id already exists, skip silently.
    """
    PIPELINE_METRICS.parent.mkdir(parents=True, exist_ok=True)

    row = f"| {package_id} | {today} | {sp1} | {sp2} | {retries} | {escalations} | {deferred} |"
    if note:
        row += f"  ← {note}"

    if PIPELINE_METRICS.exists():
        text = PIPELINE_METRICS.read_text(encoding="utf-8")
        # Deduplicate: skip if any data row with this package_id already exists
        for line in text.splitlines():
            if line.startswith(f"| {package_id} |") and not line.startswith("| _"):
                return  # already recorded
        PIPELINE_METRICS.write_text(text.rstrip() + "\n" + row + "\n", encoding="utf-8")
    else:
        PIPELINE_METRICS.write_text(_METRICS_HEADER + row + "\n", encoding="utf-8")


def read_pipeline_metrics() -> list[dict[str, str]]:
    """
    Parse archive/pipeline_metrics.md table rows.

    Returns list of dicts with keys: package, date, sp1, sp2, retries, escalations, deferred.
    Skips placeholder rows (_пример_) and TBD-only rows.
    """
    text = read_or_none(PIPELINE_METRICS)
    if not text:
        return []

    rows: list[dict[str, str]] = []
    in_table = header_seen = separator_seen = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                in_table = False
            continue
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c != ""]
        if not header_seen:
            low = [c.lower() for c in cells]
            if "package" in low and "date" in low:
                header_seen = in_table = True
            continue
        if not separator_seen:
            separator_seen = True
            continue
        if len(cells) < 7:
            continue
        pkg = strip_cell(cells[0])
        if pkg.startswith("_") or not pkg:   # skip example row
            continue
        rows.append({
            "package":     pkg,
            "date":        strip_cell(cells[1]),
            "sp1":         strip_cell(cells[2]),
            "sp2":         strip_cell(cells[3]),
            "retries":     strip_cell(cells[4]),
            "escalations": strip_cell(cells[5]),
            "deferred":    strip_cell(cells[6].split("←")[0]),  # strip trailing comment
        })
    return rows


