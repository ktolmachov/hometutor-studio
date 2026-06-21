"""Evaluation harness scaffold for SSR Level 2 LLM explanations."""

from __future__ import annotations

import json
from pathlib import Path

from app.prompts import SSR_LLM_EXPLANATION_PROMPT, SSR_LLM_EXPLANATION_PROMPT_VERSION
from scripts.eval_ssr_prompts import generate_explanations

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "tests" / "eval" / "ssr_explanation_test_cases.json"
RUBRIC_PATH = ROOT / "doc" / "eval" / "ssr_explanation_rubric.md"
CONTRACT_PATH = ROOT / "archive" / "ml_eval" / "ssr_level2" / "evaluation_contract.yaml"


def _load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def test_ssr_explanation_eval_contract_artifacts_exist() -> None:
    assert CONTRACT_PATH.exists()
    assert RUBRIC_PATH.exists()
    assert CASES_PATH.exists()
    assert "1-5 Likert" in RUBRIC_PATH.read_text(encoding="utf-8")


def test_ssr_explanation_test_set_has_50_local_scenarios() -> None:
    cases = _load_cases()
    assert len(cases) == 50
    assert {case["hint_kind"] for case in cases} >= {
        "cards_due",
        "sm2_due",
        "quiz_failed",
        "answer_ready",
        "mastery_stale",
        "adaptive_plan",
        "tutor_resume",
        "safe_default",
    }
    for case in cases:
        assert case["id"].startswith("ssr-l2-")
        assert case["primary_label_ru"].strip()
        assert case["primary_nav"].strip()
        assert case["why_now_template"].strip()
        assert isinstance(case["context"], dict)
        assert case["must_preserve"]


def test_ssr_explanation_prompt_preserves_routing_contract() -> None:
    case = _load_cases()[0]
    prompt = SSR_LLM_EXPLANATION_PROMPT.format(
        last_session_topic=case["context"]["last_session_topic"],
        last_session_date=case["context"]["last_session_date"],
        quiz_score_last_3=case["context"]["quiz_score_last_3"],
        cards_due_count=case["context"]["cards_due_count"],
        sm2_due_count=case["context"]["sm2_due_count"],
        weak_concepts_list=case["context"]["weak_concepts_list"],
        local_evidence="fixture",
        primary_label_ru=case["primary_label_ru"],
        primary_nav=case["primary_nav"],
        hint_kind=case["hint_kind"],
        why_now_template=case["why_now_template"],
    )
    # Contract phrases (semantics preserved across compression in v1.3):
    # routing immutability, 150-word cap, "Why-now" framing, contrast handling
    # and the actual routing target must be present in the rendered prompt.
    assert "Не меняй рекомендацию и маршрут" in prompt
    assert "150 слов" in prompt
    assert "Контраст" in prompt
    assert "«Почему сейчас»" in prompt
    assert case["primary_nav"] in prompt
    assert SSR_LLM_EXPLANATION_PROMPT_VERSION == "1.4"


def test_ssr_explanation_generation_artifact_shape_offline() -> None:
    artifact = generate_explanations(_load_cases(), offline_template=True, limit=2)
    assert artifact["case_count"] == 2
    assert artifact["prompt_version"] == SSR_LLM_EXPLANATION_PROMPT_VERSION
    assert artifact["llm_role"] == "ssr"
    for row in artifact["records"]:
        assert row["case_id"].startswith("ssr-l2-")
        assert row["generated_explanation"] == row["template_explanation"]
        assert row["used_template_fallback"] is True
        assert row["generated_word_count"] < 150
