"""Unit tests for scripts/ops_triggers.py — Phase 2.5 trigger detection.

Covers the canonical trigger table from
  doc/team_workflow/rag_llm_ops_project_document.md §35

Each case is a pure dict-in, tuple-out check. No subprocess, no file I/O.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ops_triggers import detect_ops_triggers, format_triggered_summary  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _c(**kwargs: str) -> dict[str, str]:
    """Minimal contract with overridable fields."""
    base = {
        "PACKAGE_ID":       "epoch-test",
        "PACKAGE_TITLE":    "test",
        "USER_STORIES":     "",
        "OUTCOMES":         "",
        "WRITE_SET_MAX":    "",
        "DELIVERABLES":     "",
        "READ_SET_HINT":    "",
        "TARGET_ARTIFACTS": "",
        "NOTES":            "",
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Negative / boundary cases
# ---------------------------------------------------------------------------

def test_none_contract_returns_false() -> None:
    gate, roles, matched = detect_ops_triggers(None)
    assert gate is False
    assert roles == []
    assert matched == []


def test_empty_contract_returns_false() -> None:
    gate, roles, matched = detect_ops_triggers({})
    assert gate is False
    assert roles == []
    assert matched == []


def test_contract_with_no_paths_returns_false() -> None:
    """CJM stage names alone must NOT trigger Ops gate (doc rule)."""
    contract = _c(
        PACKAGE_TITLE="Discover stage improvements",
        OUTCOMES="Improve discovery UX for new learners. Add nicer copy.",
        NOTES="CJM: Discover. No code surfaces touched.",
    )
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is False
    assert roles == []
    assert matched == []


# ---------------------------------------------------------------------------
# Single-role triggers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path,expected_role",
    [
        ("app/provider.py",                              "llmops"),
        ("app/tutor_prompts.py",                         "llmops"),
        ("app/prompts/answer_v3.md",                     "llmops"),
        ("app/query_service.py",                         "ragops"),
        ("app/pipeline_steps.py",                        "ragops"),
        ("app/course_cache.py",                          "ragops"),
        ("app/ui/study_scope.py",                        "ragops"),
        ("app/routers/course_upload.py",                 "ragops"),
        ("app/services/course_upload_service.py",        "ragops"),
        ("data/docs/ML-Course/lecture_01.md",            "ragops"),
    ],
)
def test_single_role_trigger(path: str, expected_role: str) -> None:
    contract = _c(WRITE_SET_MAX=path)
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert roles == [expected_role]
    assert path.rstrip("/") in " ".join(matched) or any(
        m.rstrip("/") in path for m in matched
    )


# ---------------------------------------------------------------------------
# Multi-role triggers
# ---------------------------------------------------------------------------

def test_knowledge_graph_triggers_mlops_and_ragops() -> None:
    contract = _c(WRITE_SET_MAX="app/knowledge_graph.py")
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert roles == ["mlops", "ragops"]
    assert matched == ["app/knowledge_graph.py"]


def test_data_indexes_triggers_mlops_and_ragops() -> None:
    """data/indexes/ in the write-set (DELIVERABLES) triggers mlops+ragops."""
    contract = _c(DELIVERABLES="data/indexes/chroma_v12")
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert roles == ["mlops", "ragops"]


def test_local_readiness_triggers_llmops_and_performance() -> None:
    """scripts/local_readiness.py must fire BOTH llmops and performance —
    not just performance via the generic scripts/local_* rule."""
    contract = _c(WRITE_SET_MAX="scripts/local_readiness.py")
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert roles == ["llmops", "performance"]


def test_llm_local_banner_triggers_llmops_and_performance() -> None:
    contract = _c(WRITE_SET_MAX="app/ui/llm_local_banner.py")
    gate, roles, _ = detect_ops_triggers(contract)
    assert gate is True
    assert roles == ["llmops", "performance"]


# ---------------------------------------------------------------------------
# Performance-sole triggers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [
        "scripts/local_status.py",
        "scripts/local_start.ps1",
        ".env.example",
        "Dockerfile",
        ".github/workflows/ci.yml",
    ],
)
def test_performance_sole_triggers(value: str) -> None:
    contract = _c(WRITE_SET_MAX=value)
    gate, roles, _ = detect_ops_triggers(contract)
    assert gate is True
    assert roles == ["performance"], f"expected ['performance'] for {value}, got {roles}"


# ---------------------------------------------------------------------------
# Generic local_* must not steal local_readiness.py
# ---------------------------------------------------------------------------

def test_local_readiness_not_demoted_to_performance_only() -> None:
    """If both specific and generic rules match, llmops MUST stay in roles set."""
    contract = _c(WRITE_SET_MAX="scripts/local_readiness.py\nscripts/local_status.py")
    gate, roles, _ = detect_ops_triggers(contract)
    assert gate is True
    assert "llmops" in roles
    assert "performance" in roles
    assert set(roles) == {"llmops", "performance"}


# ---------------------------------------------------------------------------
# Compound contracts (multiple files in one package)
# ---------------------------------------------------------------------------

def test_compound_contract_unions_roles() -> None:
    contract = _c(
        WRITE_SET_MAX="app/provider.py\napp/query_service.py\napp/knowledge_graph.py",
        READ_SET_HINT="app/config.py",  # read-set — NOT scanned for ops triggers
    )
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    # provider → llmops; query_service → ragops; knowledge_graph → mlops+ragops
    # config.py is in READ_SET_HINT → NOT counted (read-set is intentionally excluded)
    assert roles == ["llmops", "mlops", "ragops"]
    assert len(matched) >= 3


def test_paths_scattered_across_text_fields_all_detected() -> None:
    """Scanned fields: WRITE_SET_MAX, DELIVERABLES, OUTCOMES, TARGET_ARTIFACTS, NOTES.
    READ_SET_HINT is intentionally excluded (read-set files must not trigger ops gate).
    """
    contract = _c(
        OUTCOMES="Update app/provider.py for fallback",
        NOTES="Touches data/docs/ML-Course/ via upload service",
        READ_SET_HINT="app/tutor_prompts.py",  # NOT scanned — read-set
    )
    gate, roles, _ = detect_ops_triggers(contract)
    assert gate is True
    # provider.py in OUTCOMES → llmops; data/docs in NOTES → ragops
    # tutor_prompts.py in READ_SET_HINT → NOT triggered
    assert set(roles) == {"llmops", "ragops"}


# ---------------------------------------------------------------------------
# List-typed fields (registry YAML lists)
# ---------------------------------------------------------------------------

def test_list_typed_field_is_scanned() -> None:
    """If a parser passes a list (not a joined string), still detect."""
    contract = {
        "WRITE_SET_MAX":    ["app/provider.py", "app/query_service.py"],
        "READ_SET_HINT":    [],
        "OUTCOMES":         "",
        "TARGET_ARTIFACTS": "",
        "NOTES":            "",
        "PACKAGE_TITLE":    "",
    }
    gate, roles, _ = detect_ops_triggers(contract)
    assert gate is True
    assert set(roles) == {"llmops", "ragops"}


# ---------------------------------------------------------------------------
# CJM-stage anti-pattern guard
# ---------------------------------------------------------------------------

def test_cjm_stage_keywords_do_not_trigger() -> None:
    """Doc explicitly forbids inferring triggers from CJM stage names alone."""
    contract = _c(
        PACKAGE_TITLE="Retain — improve flashcard graduation",
        OUTCOMES="Graduation, retention, mastery, ingest-friendly UX",
        # No file paths anywhere.
    )
    gate, roles, _ = detect_ops_triggers(contract)
    assert gate is False
    assert roles == []


# ---------------------------------------------------------------------------
# format_triggered_summary
# ---------------------------------------------------------------------------

def test_summary_empty_when_no_roles() -> None:
    assert format_triggered_summary([], []) == "no Ops triggers"


def test_summary_lists_roles_and_first_paths() -> None:
    s = format_triggered_summary(
        ["llmops", "ragops"],
        ["app/provider.py", "app/query_service.py", "data/docs/", "app/config.py"],
    )
    assert "llmops+ragops" in s
    assert "app/provider.py" in s
    assert "+1 more" in s  # 4 paths, preview shows 3


# ---------------------------------------------------------------------------
# Regression tests — Bug fixes 2026-05-29
# ---------------------------------------------------------------------------

def test_read_set_hint_not_scanned_for_ops_triggers() -> None:
    """READ_SET_HINT must NOT trigger ops gate.

    Regression: ops_triggers used to scan READ_SET_HINT, causing false-positive
    mlops+ragops for packages that merely READ app/knowledge_graph.py.
    """
    contract = _c(READ_SET_HINT="app/knowledge_graph.py\napp/query_service.py")
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is False, (
        f"READ_SET_HINT must not trigger ops gate; got roles={roles}, matched={matched}"
    )
    assert roles == []
    assert matched == []


def test_deliverables_field_triggers_ops_gate() -> None:
    """DELIVERABLES (write-set from backlog_registry.yaml) MUST trigger ops gate."""
    contract = _c(DELIVERABLES="app/knowledge_graph.py")
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert roles == ["mlops", "ragops"]
    assert "app/knowledge_graph.py" in matched


def test_false_positive_regression_knowledge_graph_in_read_set() -> None:
    """Exact regression for epoch-ssr-graph-routing-v1 false-positive.

    Package write-set: app/ssr_graph_routing.py, app/smart_study_router.py,
                       app/config.py (non-LLM bool flag), tests/...
    Package read-set:  app/knowledge_graph.py (read-only API)

    Expected: gate=False — config.py has no LLM context, knowledge_graph.py is in
    READ_SET_HINT which is not scanned.
    Before fix: mlops+ragops was falsely triggered by knowledge_graph.py in read-set.
    """
    contract = _c(
        DELIVERABLES=(
            "app/ssr_graph_routing.py\n"
            "app/smart_study_router.py\n"
            "app/config.py\n"
            "tests/test_ssr_graph_routing.py\n"
            "tests/eval/test_ssr_graph_routing.py\n"
            "archive/ml_eval/ssr_level4/contract.yaml"
        ),
        READ_SET_HINT=(
            "app/knowledge_graph.py -- rg \"^class|^def \"\n"
            "app/smart_study_recommendation.py\n"
            "tests/eval/test_ssr_graph_routing.py"
        ),
        OUTCOMES="Runtime prerequisite-aware weak-concept reorder in SSR",
    )
    gate, roles, matched = detect_ops_triggers(contract)
    # config.py in write-set adds a non-LLM bool flag → no LLM keyword in context
    # knowledge_graph.py in read-set → not scanned
    # Result: gate=False (no LLM-context for config.py, no write-set KG)
    assert gate is False, (
        f"Non-LLM config.py + read-set KG must not trigger ops gate; "
        f"got roles={roles}, matched={matched}"
    )
    assert "app/knowledge_graph.py" not in matched


def test_config_py_non_llm_change_does_not_trigger_llmops() -> None:
    """app/config.py with a non-LLM flag must NOT trigger llmops.

    Regression: the old rule fired on any config.py change regardless of context.
    A bool feature flag (e.g. ssr_graph_routing_enabled) is not an LLM ops concern.
    """
    contract = _c(
        DELIVERABLES="app/config.py\napp/smart_study_router.py",
        OUTCOMES="Add ssr_graph_routing_enabled bool feature flag (default off)",
        NOTES="Non-LLM settings gate; no provider/model changes",
    )
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is False, (
        f"Non-LLM config.py change must not trigger llmops; got roles={roles}"
    )


def test_config_py_with_llm_key_triggers_llmops() -> None:
    """app/config.py with LLM/embeddings key changes MUST trigger llmops."""
    contract = _c(
        DELIVERABLES="app/config.py",
        OUTCOMES="Add embeddings_model config key for new sentence-transformers model",
    )
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert "llmops" in roles


def test_config_py_with_openai_key_triggers_llmops() -> None:
    contract = _c(
        DELIVERABLES="app/config.py",
        NOTES="update openai provider_type and model_name for GPT-4o migration",
    )
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert "llmops" in roles


def test_deliverables_and_write_set_max_both_scanned() -> None:
    """Both DELIVERABLES and WRITE_SET_MAX are scanned; their triggers union."""
    contract = _c(
        WRITE_SET_MAX="app/provider.py",
        DELIVERABLES="app/query_service.py",
    )
    gate, roles, matched = detect_ops_triggers(contract)
    assert gate is True
    assert set(roles) == {"llmops", "ragops"}
    assert "app/provider.py" in matched
    assert "app/query_service.py" in matched


# ---------------------------------------------------------------------------
# Regression: PACKAGE_TITLE removed from _SCANNED_FIELDS (H2) — 2026-05-29
# ---------------------------------------------------------------------------

def test_package_title_prose_does_not_trigger_performance() -> None:
    """PACKAGE_TITLE prose must NOT trigger ops when no ops-sensitive files are in write-set.

    Regression: PACKAGE_TITLE was in _SCANNED_FIELDS, so a title like
    'Optimize CI: update Dockerfile and .github/workflows/ci.yml to...' would
    fire a performance trigger even though those files weren't being modified.
    PACKAGE_TITLE is a subset of OUTCOMES (already scanned) — scanning it
    separately caused false positives from prose mentions.
    """
    contract = _c(
        DELIVERABLES="app/smart_study_router.py\ntests/test_smart_study.py",
        OUTCOMES=(
            "Optimize CI pipeline: update Dockerfile and .github/workflows/ci.yml "
            "to speed up builds"
        ),
        PACKAGE_TITLE=(
            "Optimize CI pipeline: update Dockerfile and .github/workflows/ci.yml "
            "to speed up builds"
        ),
    )
    # Deliverables have no ops-sensitive files. Trigger should fire only from OUTCOMES
    # (because Dockerfile is there) — but PACKAGE_TITLE is NOT scanned separately.
    gate, roles, matched = detect_ops_triggers(contract)
    # OUTCOMES contains Dockerfile → performance may fire from OUTCOMES (that's OK).
    # What must NOT happen: duplicate match count from PACKAGE_TITLE+OUTCOMES.
    # The key assertion: PACKAGE_TITLE is not a scan source on its own.
    from ops_triggers import _SCANNED_FIELDS
    assert "PACKAGE_TITLE" not in _SCANNED_FIELDS
