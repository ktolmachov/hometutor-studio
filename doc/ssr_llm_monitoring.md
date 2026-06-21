# SSR LLM Explanation Monitoring

Package: `llm-ssr-explanation-integration`

## Metrics

| Metric | Target | Source |
|---|---:|---|
| `llm_call_success_rate` | > 95% | successful explanation calls / attempted calls |
| `llm_latency_p95` | < 2s | elapsed generation time |
| `fallback_rate` | < 10% | template fallback count / attempted calls |
| `token_cost_p95` | < 500 tokens | provider usage when available, otherwise prompt estimate |
| `routing_regression` | 0 | SSR deterministic tests |

## Fallback Policy

Use template `why_now_ru` when:

- provider construction or completion fails;
- output is empty;
- output exceeds the 3 second single-call budget;
- provider usage exceeds 700 tokens for the request;
- output fails length or accuracy validation;
- local context is insufficient and the prompt cannot ground the answer.

The fallback preserves the deterministic SSR route and keeps the evidence ledger
visible to the learner.

Usage above 500 tokens but not above 700 is a prompt-compression warning before
rollout. Usage above 700 must not be cached or shown in the UI.

## Cache Policy

Cache key: recommendation fields + local learning context + prompt version.

TTL: 1 hour.

Invalidation: any changed recommendation, changed context, or prompt version
change produces a new key.

## Rollout Gate

Do not enable automatic UI-time generation until the evaluation report in
`archive/ml_eval/ssr_level2/llm_explanation_v1_report.md` shows:

- clarity score >= 4.0;
- p95 latency < 2s;
- token_cost_p95 < 500 and no single response over 700 is shown;
- fallback rate < 10%;
- no SSR routing regression.
