# SSR Level 2 Prompt Iterations

Package: `llm-ssr-prompt-engineering`

## Candidate Prompts

### V1: Context-Rich Baseline

Includes recent session, quiz average, due cards, weak concepts, selected route,
and the template reason. The model writes one Russian explanation under 150
words.

Expected strength: high personalization.

Risk: may overuse weak numeric context or invent retention percentages if not
explicitly constrained.

### V2: Evidence-Only Guarded

Adds strict instructions to use only supplied local evidence and to avoid
invented dates, topics, and retention percentages.

Expected strength: accuracy and trust.

Risk: slightly less vivid prose.

### V3: Timing-Focused

Asks for three compact moves in one paragraph: recent signal, why now, next
benefit. Explicitly says the LLM cannot change routing.

Expected strength: clarity and pedagogical value.

Risk: may sound formulaic.

### V4: Minimal Token Budget

Compresses context into a small evidence string and asks for a 2-4 sentence
answer.

Expected strength: cost and latency.

Risk: lower personalization when evidence is sparse.

## Selected Prompt

Selected for initial implementation: **V2 with V3 structure**.

Reason: it best matches the evaluation contract. It keeps routing immutable,
uses only supplied evidence, stays short, and still explains timing.

Implementation source of truth: `SSR_LLM_EXPLANATION_PROMPT` in
`app/prompts/_impl.py`.

## A/B Evaluation Plan

Run `scripts/eval_ssr_prompts.py` against
`tests/eval/ssr_explanation_test_cases.json` after collecting generated outputs.
Human raters use `doc/eval/ssr_explanation_rubric.md`.

Minimum comparison:

| Variant | Target |
|---|---|
| Template baseline | clarity baseline 3.2 |
| V2/V3 selected prompt | clarity >= 4.0 |
| V4 minimal prompt | p95 latency and token budget reserve |
