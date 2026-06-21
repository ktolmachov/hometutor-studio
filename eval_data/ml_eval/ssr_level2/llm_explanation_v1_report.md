# SSR Level 2 LLM Explanation v1 Report

Status: generated explanations collected, pending human evaluation.

## Evaluation Contract

- Feature: SSR Level 2 — LLM-Enhanced Explanation
- Baseline: template `why_now_ru`, clarity score 3.2/5
- Target: clarity score >= 4.0/5
- Test set: 50 SSR scenarios x 3 human raters
- Rubric: `doc/eval/ssr_explanation_rubric.md`

## Current Implementation

- Prompt source: `app/prompts/_impl.py`
- Integration helper: `app/ui/adaptive_plan_card.py::_generate_llm_explanation`
- Fallback: original deterministic `why_now_ru`
- Cache: 1 hour for identical recommendation + context + prompt version

## Results

| Metric | Target | Current |
|---|---:|---|
| clarity score | >= 4.0 | pending |
| personalization score | >= 4.0 | pending |
| pedagogical value | >= 4.0 | pending |
| accuracy | no rating below 3 | pending |
| llm latency p95 | < 2s | 4.11s (machine run, classifier role) |
| token cost | < 500 | probe: 489 total tokens; full-run aggregate pending |
| fallback rate | < 10% | 0/50 |
| routing regression | 0 | covered by SSR tests |

Generated explanations artifact:
`archive/ml_eval/ssr_level2/generated_explanations_v1.json`

Machine summary from 2026-05-09 run:

- LLM role: `classifier`
- Records: 50
- Fallbacks: 0
- Errors: 0
- Average generated length: 84.24 words
- Maximum generated length: 93 words
- p95 latency: 4.11s

## Next Evaluation Step

Run the harness:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_llm_explanation.py tests/test_smart_study_router.py -v --tb=short
```

Then run 3-rater human evaluation and replace the pending cells above with
measured values. Latency is currently above the rollout gate, so automatic UI
enablement remains blocked even if human clarity passes.
