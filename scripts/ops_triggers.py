#!/usr/bin/env python3
"""
ops_triggers.py — Phase 2.5 Ops Impact detection for orchestration generation.

Canonical source of truth (must stay in sync):
  - doc/team_workflow/rag_llm_ops_project_document.md §35
  - doc/team_workflow/orchestrator_template.md (STEP 3.5 trigger list)
  - doc/team_workflow/generate_orchestration_prompt.md (Phase 2.5 trigger table)
  - doc/team_workflow/performance_devops.md (perf-only triggers)

Public API:
  detect_ops_triggers(contract: dict[str, str]) -> tuple[bool, list[str], list[str]]
      Returns (gate_needed, sorted_roles, matched_paths).

Design constraints (per doc):
  * NEVER infer Ops triggers from CJM-stage names alone (CJM is too broad).
  * Only match against literal file/dir patterns found in registry text fields.
  * Output is deterministic: roles are returned sorted alphabetically.
  * Empty roles → gate_needed = False (Phase 2.5 emits a one-line warning at
    callsite if ambiguous, not here — this module is pure).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Trigger table — each entry is (regex, roles_set)
# Order matters only for matched_paths reporting; role union is unordered.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Trigger:
    pattern: re.Pattern[str]
    roles: frozenset[str]
    label: str  # human-friendly label for matched_paths reporting


def _t(regex: str, roles: set[str], label: str) -> _Trigger:
    return _Trigger(re.compile(regex), frozenset(roles), label)


# Canonical trigger table.
# Match order: most specific first (so scripts/local_readiness.py is captured
# under llmops+performance before the generic scripts/local_*.py rule sees it).
_TRIGGERS: tuple[_Trigger, ...] = (
    # ── LLMOps ────────────────────────────────────────────────────────────
    _t(r"\bapp/provider\.py\b",               {"llmops"},            "app/provider.py"),
    # app/config.py triggers llmops ONLY when the contract also mentions LLM/embedding
    # keys (specific provider names, model keys, embedding config). A plain bool flag
    # or non-LLM setting in config.py must NOT trigger ops review.
    # Keywords chosen to be specific: no bare "LLM" or "model" (too broad).
    _t(
        r"\bapp/config\.py\b(?=[\s\S]*(?:llm_model|embeddings?_model|openai|anthropic|gemini|llm_provider|profile_key|llm_api|gpt-|claude-))|"
        r"(?:llm_model|embeddings?_model|openai|anthropic|gemini|llm_provider|profile_key|llm_api|gpt-|claude-)[\s\S]*\bapp/config\.py\b",
        {"llmops"},
        "app/config.py (LLM/embeddings key)",
    ),
    _t(r"\bapp/prompts/",                     {"llmops"},            "app/prompts/"),
    _t(r"\bapp/tutor_prompts\.py\b",          {"llmops"},            "app/tutor_prompts.py"),

    # ── RAGOps ────────────────────────────────────────────────────────────
    _t(r"\bapp/query_service\.py\b",          {"ragops"},            "app/query_service.py"),
    _t(r"\bapp/pipeline_steps\.py\b",         {"ragops"},            "app/pipeline_steps.py"),
    _t(r"\bapp/course_cache\.py\b",           {"ragops"},            "app/course_cache.py"),
    _t(r"\bapp/ui/study_scope\.py\b",         {"ragops"},            "app/ui/study_scope.py"),
    _t(r"\bdata/docs/",                       {"ragops"},            "data/docs/"),
    _t(r"\bapp/routers/course_upload\.py\b",  {"ragops"},            "app/routers/course_upload.py"),
    _t(r"\bapp/services/course_upload_service\.py\b", {"ragops"},    "app/services/course_upload_service.py"),

    # ── MLOps + RAGOps (knowledge graph) ──────────────────────────────────
    _t(r"\bapp/knowledge_graph\.py\b",        {"mlops", "ragops"},   "app/knowledge_graph.py"),
    # data/indexes/ writes imply both index versioning (MLOps) and retrieval
    # contract changes (RAGOps).
    _t(r"\bdata/indexes/",                    {"mlops", "ragops"},   "data/indexes/"),

    # ── LLMOps + Performance + Designer-note ──────────────────────────────
    # (Designer note is handled separately at template fill — module returns
    # only the three engineering roles here.)
    _t(r"\bscripts/local_readiness\.(?:py|ps1)\b", {"llmops", "performance"}, "scripts/local_readiness.{py,ps1}"),
    _t(r"\bapp/ui/llm_local_banner\.py\b",    {"llmops", "performance"}, "app/ui/llm_local_banner.py"),

    # ── Performance (sole) ────────────────────────────────────────────────
    # Generic scripts/local_*.py|ps1 — fires after specific local_readiness rule above.
    _t(r"\bscripts/local_[\w-]+\.(?:py|ps1)\b", {"performance"},     "scripts/local_*.{py,ps1}"),
    _t(r"(?:^|[/\s,])\.env\.example\b",       {"performance"},       ".env.example"),
    _t(r"(?:^|[/\s,])Dockerfile\b",           {"performance"},       "Dockerfile"),
    _t(r"\.github/workflows/",                {"performance"},       ".github/workflows/"),
)

_KNOWN_ROLES = frozenset({"ragops", "llmops", "mlops", "performance"})

# Fields we scan in the registry contract dict. Each may be a string or a list
# (when the registry entry uses YAML list syntax). Strings get treated verbatim;
# lists get joined with newlines.
#
# IMPORTANT: READ_SET_HINT is intentionally excluded — ops gate should only fire
# on files being MODIFIED (write-set), not files merely read for context.
# Scanning read-set paths causes false-positive triggers (e.g. knowledge_graph.py
# in read-set fires mlops+ragops even when the write-set has no ops-sensitive files).
# DELIVERABLES contains the actual write-set file list from backlog_registry.yaml.
_SCANNED_FIELDS = (
    "WRITE_SET_MAX",        # numeric count or comma-list of file paths
    "DELIVERABLES",         # newline-joined actual write-set paths from registry
    "OUTCOMES",
    "TARGET_ARTIFACTS",
    "NOTES",
    # PACKAGE_TITLE intentionally excluded: it is outcomes[:120] — a SUBSET of OUTCOMES
    # already covered above. Scanning it separately risks false-positive performance/
    # ops triggers from prose mentions of Dockerfile or .github/workflows/ in the title.
)


def _coerce_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_coerce_text(v) for v in value)
    return str(value)


def detect_ops_triggers(contract: dict[str, object] | None) -> tuple[bool, list[str], list[str]]:
    """Scan registry-derived contract for Ops triggers.

    Args:
        contract: dict produced by _parse_contract_from_registry (or a test fixture
                  with the same shape). Tolerates None and missing keys.

    Returns:
        (gate_needed, roles_sorted, matched_path_labels)
            gate_needed:    True iff any role triggered.
            roles_sorted:   alphabetically sorted list of roles, e.g. ['llmops', 'ragops'].
            matched_path_labels: deduplicated, ordered list of matched trigger labels
                                 (useful for the warning/print path).
    """
    if not contract:
        return False, [], []

    # Concatenate all scanned text fields with a separator that's safe for regex.
    blob_parts: list[str] = []
    for key in _SCANNED_FIELDS:
        blob_parts.append(_coerce_text(contract.get(key)))
    blob = "\n".join(blob_parts)

    if not blob.strip():
        return False, [], []

    triggered_roles: set[str] = set()
    matched_labels: list[str] = []

    for trig in _TRIGGERS:
        if trig.pattern.search(blob):
            # Deduplicate labels but preserve insertion order
            if trig.label not in matched_labels:
                matched_labels.append(trig.label)
            triggered_roles |= trig.roles

    # Defense in depth: ensure we never leak unknown role names downstream.
    unknown = triggered_roles - _KNOWN_ROLES
    assert not unknown, f"ops_triggers: unknown roles detected: {unknown}"

    roles_sorted = sorted(triggered_roles)
    return bool(roles_sorted), roles_sorted, matched_labels


def format_triggered_summary(roles: list[str], matched_paths: list[str]) -> str:
    """One-line summary suitable for the orchestrator console output."""
    if not roles:
        return "no Ops triggers"
    paths_preview = ", ".join(matched_paths[:3])
    if len(matched_paths) > 3:
        paths_preview += f", +{len(matched_paths) - 3} more"
    return f"{'+'.join(roles)} (triggered by: {paths_preview})"


__all__ = ["detect_ops_triggers", "format_triggered_summary"]
