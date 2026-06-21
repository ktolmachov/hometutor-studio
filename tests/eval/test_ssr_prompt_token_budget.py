"""Token budget guard for SSR_LLM_EXPLANATION_PROMPT.

Cap kept tight (≤320 input tokens for the rendered prompt on a representative
context) so that the prompt stays fast on local CPU models. Use
``app.token_utils.estimate_tokens`` with the gpt-4o tokenizer as the
reference; real local-model tokenizers may produce somewhat different
numbers but the relative budget holds.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.prompts import SSR_LLM_EXPLANATION_PROMPT
from app.token_utils import estimate_tokens

SSR_PROMPT_TOKEN_BUDGET = 320

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "tests" / "eval" / "ssr_explanation_test_cases.json"


def _render(case: dict) -> str:
    ctx = case["context"]
    return SSR_LLM_EXPLANATION_PROMPT.format(
        last_session_topic=ctx["last_session_topic"],
        last_session_date=ctx["last_session_date"],
        quiz_score_last_3=ctx["quiz_score_last_3"],
        cards_due_count=ctx["cards_due_count"],
        sm2_due_count=ctx["sm2_due_count"],
        weak_concepts_list=ctx["weak_concepts_list"],
        local_evidence="Замечена слабость в одном из недавних concept-проверок",
        primary_label_ru=case["primary_label_ru"],
        primary_nav=case["primary_nav"],
        hint_kind=case["hint_kind"],
        why_now_template=case["why_now_template"],
    )


def test_ssr_prompt_typical_render_within_budget() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    sample = cases[0]
    prompt = _render(sample)
    tokens = estimate_tokens(prompt, "gpt-4o")
    assert tokens <= SSR_PROMPT_TOKEN_BUDGET, (
        f"SSR prompt grew to {tokens} tokens (budget {SSR_PROMPT_TOKEN_BUDGET}). "
        "Either compress static text further or raise the budget intentionally."
    )


def test_ssr_prompt_worst_case_render_within_budget_plus_margin() -> None:
    """All 50 eval cases must render within budget + 25% margin for verbose context."""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    margin = int(SSR_PROMPT_TOKEN_BUDGET * 1.25)
    worst: tuple[int, str] = (0, "")
    for case in cases:
        tokens = estimate_tokens(_render(case), "gpt-4o")
        if tokens > worst[0]:
            worst = (tokens, case["id"])
    assert worst[0] <= margin, (
        f"Worst case render {worst[0]} tokens for case {worst[1]} exceeds margin {margin}"
    )
