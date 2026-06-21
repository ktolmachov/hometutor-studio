"""YAML contract tests for learning-loop demo scenarios (audit group 07).

Validates shot slugs and offline-friendly metadata tied to CJM #3 (tutor handoff)
and #4 (first micro-quiz).
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


def test_scenario_03_answer_to_tutor_yaml_contract() -> None:
    """#3 Transition to tutor — Answer → Tutor in one gesture with context."""
    _assert_scenario_yaml(
        filename="scenario_03_answer_to_tutor.yaml",
        expected_top_id="scenario_03",
        required_slugs=frozenset(
            {
                "01_answer_with_learn_cta",
                "02_tutor_context_handoff",
                "03_tutor_topic_plan",
                "04_tutor_simple_explanation",
                "05_tutor_next_step_cta",
            }
        ),
        cjm_anchor=("tutor", "контекст"),
    )


def test_scenario_04_mini_quiz_yaml_contract() -> None:
    """#4 First micro-quiz — formative check with immediate feedback."""
    _assert_scenario_yaml(
        filename="scenario_04_mini_quiz.yaml",
        expected_top_id="scenario_04",
        required_slugs=frozenset(
            {
                "01_quiz_question_presented",
                "02_quiz_answer_selected",
                "03_quiz_feedback_correct_or_hint",
                "04_quiz_next_action_cta",
            }
        ),
        cjm_anchor=("квиз", "мгновенн"),
    )
