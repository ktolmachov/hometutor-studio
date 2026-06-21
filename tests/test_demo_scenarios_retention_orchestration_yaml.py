"""YAML contract tests for retention / orchestration / trust demo scenarios.

Retention + orchestration storyboards: audit group 04 (`scenario_06`, `07`, `09`).
Trust drill-down: `scenario_08` / US-2.2 / CJM #10 (audit group 13).
"""

from __future__ import annotations

from pathlib import Path

import yaml

DOC_SCENARIOS = Path("doc/scenarios")


def _assert_scenario_yaml(
    *,
    filename: str,
    expected_top_id: str,
    required_slugs: frozenset[str],
    cjm_anchor: tuple[str, ...],
) -> None:
    path = DOC_SCENARIOS / filename
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"{filename}: root must be a mapping"
    assert raw.get("id") == expected_top_id, f"{filename}: id must be {expected_top_id!r}"

    reqs = raw.get("requires") or {}
    assert isinstance(reqs, dict), f"{filename}: requires must be a mapping"
    assert reqs.get("offline_friendly") is True, (
        f"{filename}: requires.offline_friendly must stay true for e2e demo replay"
    )

    shots = raw.get("shots") or []
    assert isinstance(shots, list) and shots, f"{filename}: shots must be a non-empty list"
    found = {s.get("slug") for s in shots if isinstance(s, dict)}
    missing = required_slugs - found
    assert not missing, f"{filename}: missing shot slugs: {sorted(missing)}"

    blob = (raw.get("why") or "") + (raw.get("wow_moment") or "") + (raw.get("takeaway") or "")
    for needle in cjm_anchor:
        assert needle.lower() in blob.lower(), (
            f"{filename}: narrative must retain CJM anchor {needle!r} for traceability"
        )


def test_scenario_06_spaced_repetition_yaml_contract() -> None:
    """#11 Retain — SRS queue storyboard (US-11.1)."""
    _assert_scenario_yaml(
        filename="scenario_06_spaced_repetition.yaml",
        expected_top_id="scenario_06",
        required_slugs=frozenset(
            {
                "01_home_due_badge",
                "02_review_queue_opened",
                "03_card_flipped_answer",
                "04_grade_selected_state_update",
                "05_queue_progress",
            }
        ),
        cjm_anchor=("повтор", "очеред", "SM-2"),
    )


def test_scenario_07_progress_gaps_yaml_contract() -> None:
    """#7 Progress — dashboard → weak spots → next action."""
    _assert_scenario_yaml(
        filename="scenario_07_progress_gaps.yaml",
        expected_top_id="scenario_07",
        required_slugs=frozenset(
            {
                "01_progress_unified_strip",
                "02_mastery_timeline",
                "03_weak_spots_panel",
                "04_streak_and_next_action",
            }
        ),
        cjm_anchor=("прогрес", "слаб"),
    )


def test_scenario_09_personalized_plan_yaml_contract() -> None:
    """#8 Learning plan — weekly priorities + today's action."""
    _assert_scenario_yaml(
        filename="scenario_09_personalized_plan.yaml",
        expected_top_id="scenario_09",
        required_slugs=frozenset(
            {
                "01_plan_overview",
                "02_plan_derived_from_gaps",
                "03_plan_diff_since_last",
                "04_plan_today_action",
                "05_plan_accepts_adjust",
            }
        ),
        cjm_anchor=("план", "приор"),
    )


def test_scenario_08_source_trust_yaml_contract() -> None:
    """#10 Retrieval trust — confidence, sources, preview, deep link (US-2.2 demo storyboard)."""
    _assert_scenario_yaml(
        filename="scenario_08_source_trust.yaml",
        expected_top_id="scenario_08",
        required_slugs=frozenset(
            {
                "01_answer_with_confidence_chip",
                "02_three_sources_listed",
                "03_source_preview_expanded",
                "04_jump_to_file_at_line",
            }
        ),
        cjm_anchor=("источник", "confidence"),
    )
