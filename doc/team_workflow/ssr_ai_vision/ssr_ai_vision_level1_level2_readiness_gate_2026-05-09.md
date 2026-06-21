# SSR AI Vision Level 1/2 Readiness Gate

**Date:** 2026-05-09  
**Scope:** Level 1 Local ML Layer + Level 2 LLM-Enhanced Explanation  
**Gate package:** `ssr-ai-vision-level1-level2-readiness-gate`

## Verdict

| Area | Verdict | Reason |
|---|---|---|
| Level 1 eval contract and harness | GO | Contract, rubric/package artifact, and 100-scenario harness are present and targeted tests pass. |
| Level 1 ML serving rollout | NO-GO | Data collection/training/eval scripts, trained model, and final model report are not present yet. Real-sample gate is still unmet. |
| Level 2 code integration | GO | LLM explanation helper preserves deterministic routing, uses cache/template fallback, and has token-budget fallback tests. |
| Level 2 automatic UI-time rollout | NO-GO | `llm_latency_p95` is reported as 4.11s against the `<2s` rollout gate; human clarity is still pending. |
| Level 3 dependency readiness | CONDITIONAL | Level 3 may start only if it treats Level 1 ML as rule-only baseline and Level 2 LLM as gated explanation, not default automatic routing/planning input. |

## Revision 2026-05-10 (фактическая отгрузка Level 1)

После закрытия `ml-ssr-forgetting-curve-v1` в дереве есть **JSON-weight** путь: `app/ssr_ml_reranking_weights.json`, `app/ssr_ml_reranking.py`, `scripts/ml/train_ssr_forgetting_curve_export.py` (обучение на `tests/eval/ssr_ml_reranking_test_cases.json`), гибрид и аудит в `app/ui/adaptive_plan_card.py`, флаг в `app/config.py` (по умолчанию выкл.). Табличный вердикт выше про **NO-GO** для Level 1 serving относится к **контракту parquet + `models/ssr_forgetting_curve_v1.pkl` + три отдельных scripts/ml/\*.py**; этот контракт в коде **не реализован** — вместо него принят альтернативный ship-path (см. `archive/team_artifacts/ml-ssr-forgetting-curve-v1/execution_contract.md` и обновлённые deliverables в `doc/backlog_registry.yaml`).

## Evidence

- Level 1 SSoT: `archive/ml_eval/ssr_level1/evaluation_contract.yaml`
- Level 1 package contract: `archive/ml_eval/ssr_level1/ml_ssr_local_reranking_v1_package.yaml`
- Level 1 test harness: `tests/eval/test_ssr_ml_reranking.py`
- Level 2 SSoT: `archive/ml_eval/ssr_level2/evaluation_contract.yaml`
- Level 2 rollout report: `archive/ml_eval/ssr_level2/llm_explanation_v1_report.md`
- Level 2 monitoring: `doc/ssr_llm_monitoring.md`
- Level 2 integration: `app/ui/adaptive_plan_card.py::_generate_llm_explanation`

## Gate Rules

### Level 1

ML serving remains blocked until all of these are true:

- `scripts/ml/data_collection_ssr.py`, `scripts/ml/train_ssr_forgetting_curve.py`, and `scripts/ml/eval_ssr_forgetting_curve.py` exist.
- `models/ssr_forgetting_curve_v1.pkl` exists and is `<1MB`.
- `archive/ml_eval/ssr_forgetting_curve_v1_report.md` reports `AUC-ROC >= 0.75`.
- Real training data has `1000+` samples, or the cold-start policy explicitly keeps serving rule-based while synthetic SM-2 samples are used only for bootstrap evaluation.
- `cards_due_completion_rate >= 75%` is measured on the agreed offline/product proxy.

### Level 2

LLM explanations may remain integrated as guarded enhancement, but automatic UI-time default remains blocked until:

- human eval replaces pending clarity/personalization/pedagogical-value cells and `clarity_score >= 4.0/5`;
- `llm_latency_p95 < 2s`;
- `token_cost_p95 < 500`;
- no single shown/cached response exceeds `700` tokens;
- `fallback_rate < 10%`;
- deterministic SSR routing regression remains `0`.

## Recommended Next Move

Start Level 3 only as a baseline-compatible planner:

- use deterministic SSR/rule-based outputs as dependencies;
- consume Level 2 explanations as optional UX copy, not as planning/routing input;
- keep Level 1 ML reranking behind the explicit Level 1 serving gate.

If the owner wants Level 1/2 to become true production defaults before Level 3, the next package should be `ml-ssr-forgetting-curve-v1` for Level 1 and a separate Level 2 latency/human-eval remediation package.
