# SSR AI Vision — Roadmap Summary
## Актуальный статус уровней 1-5

**Дата:** 2026-06-21  
**Версия:** 2.1  
**Статус:** Levels 1-5 engineering delivered; serving promotion gated by data/rollout gates

Этот файл — обзор roadmap. Source of truth по backlog-статусам остаётся
[`../../backlog_registry.yaml`](../../backlog_registry.yaml), а runtime/eval
факты по ML/LLM — в `archive/ml_eval/ssr_level*/`.

---

## Vision

Smart Study Router развивается от детерминированной rule-based системы к
hybrid learning companion. Правила остаются страховочной сеткой; ML/LLM слои
могут улучшать приоритет, объяснение, планирование и feedback loop только
после eval gates.

```text
Level 1: Local ML Layer           -> personalized retention signal
Level 2: LLM-Enhanced Explanation -> better "why now" text
Level 3: Weekly Planner           -> proactive 7-day plan
Level 4: Concept Graph Router     -> prerequisite-aware routing
Level 5: Misroute Feedback Loop   -> adaptive policy from local feedback
```

**Итог по состоянию на 2026-06-11:** все пять уровней инженерно доставлены.
Открытый вопрос — не «что строить», а «когда промоутить serving»: каждый
уровень сохраняет rule-based fallback и включается полностью только после
своего data/rollout gate.

---

## Status Matrix

| Level | Feature | Registry / artifact status | Product status | Next action |
|---|---|---|---|---|
| **1** | Local ML Layer | Wave 1 packages closed; eval report + rollout gate (`ml-ssr-serving-rollout-gate` closed 2026-05-10) | **Delivered, serving gated**: runtime остаётся `rule_based` до cold-start threshold | Накопить real samples до 1000; затем rollout/A-B gate |
| **2** | LLM Explanation | Wave 2 + `ssr-l2-reliability-v1` (2026-05-14) + `ssr-l2-tiered-explanation-gate-v1` (2026-05-23) closed | **Delivered**: template-first, LLM enrichment только для complex cases; latency NO-GO снят tiered gate (blended p95 < 2s target) | Мониторить production telemetry tier decisions |
| **3** | Weekly Planner | `ssr-weekly-planner-baseline` closed 2026-05-15; `epoch-ssr-weekly-study-narrative-v1` closed 2026-05-31 | **Delivered (rule-based baseline)**: 7-day plan + plan-completion telemetry + weekly narrative на Progress | Накопить 4+ недель planner telemetry перед `ml-ssr-plan-optimization` |
| **4** | Concept Graph Router | `kg-completeness-audit` closed 2026-05-17; eval scaffold closed 2026-05-27; `epoch-ssr-graph-routing-v1` closed 2026-05-29 | **Delivered, feature-flag gated**: prerequisite-aware weak-concept reorder для `quiz_failed` / `mastery_stale`; rule-based fallback при недоступном графе | Course Graph Compiler wave (evidence-backed graph + uplift gate) усиливает граф под L4 |
| **5** | Misroute Feedback Loop | `ssr-misroute-feedback-collection` closed 2026-05-15; `epoch-ssr-misroute-policy-learning-v1` closed 2026-05-30 | **Delivered (offline policy)**: weight adjustments with decay при ≥3 consistent rejects, видимы в evidence ledger; rule fallback при sparse feedback | Накопить feedback data; online/adaptive policy остаётся deferred |

---

## Level Details

### Level 1 — Local ML Layer

**Backlog packages:**  
`ml-ssr-baseline-hardening`, `ml-ssr-eval-harness`, `ml-ssr-forgetting-curve-v1`,
`ml-ssr-serving-rollout-gate` — `closed`.

**Implemented artifacts:**

- `archive/ml_eval/ssr_level1/evaluation_contract.yaml`
- `archive/ml_eval/ssr_level1/ml_ssr_local_reranking_v1_package.yaml`
- `archive/ml_eval/ssr_forgetting_curve_v1_report.md`
- `app/ssr_ml_monitoring.py`
- `data/ml/ssr_forgetting_curve_train.parquet`
- `data/ml/ssr_forgetting_curve_test.parquet`
- `models/ssr_forgetting_curve_v1.pkl`

**Current facts:**

| Metric | Value | Target | Status |
|---|---:|---:|---|
| Holdout Macro AUC-ROC | 0.885 | >= 0.75 | pass |
| Precision@5 | 0.985 | >= 0.80 | pass |
| Recall@5 | 0.985 | >= 0.70 | pass |
| Inference p95 latency | ~0.03 ms | < 50 ms | pass |
| Real samples | 73 _(last verified 2026-05-09)_ | >= 1000 | cold-start |
| Serving mode | `rule_based` | hybrid after gate | gated |

**Verdict:** engineering implementation is complete, but product serving is
intentionally gated. Do not describe Level 1 as "ML enabled by default" until
the cold-start and rollout gates pass.

### Level 2 — LLM-Enhanced Explanation

**Backlog packages:**  
`llm-ssr-explanation-eval`, `llm-ssr-prompt-engineering`,
`llm-ssr-explanation-integration`, `ssr-l2-reliability-v1` (semantic cache +
async pre-generation, closed 2026-05-14), `ssr-l2-tiered-explanation-gate-v1`
(closed 2026-05-23) — `closed`.

**Implemented artifacts:**

- `archive/ml_eval/ssr_level2/evaluation_contract.yaml`
- `archive/ml_eval/ssr_level2/llm_explanation_v1_report.md`
- `doc/ssr_llm_monitoring.md`
- SSR explanation prompt/integration via `app/prompts/` and SSR UI path
- Tiered gate: template-first «why now», LLM enrichment только для complex
  cases (contrastive, ≥3 ledger signals, debt+steering conflict); tier
  decision видим в profiling/trace

**Product boundary:** LLM output may personalize explanation text only. It must
not change route selection, CTA priority, or fallback behavior. Template/rule
fallback remains required on provider failure, unsafe output, latency breach, or
missing data.

**Explanation-quality feedback (already shipped):** `app/ui/ssr_feedback.py`
collects thumbs-up/thumbs-down ratings on the "why now" explanation text,
logging to `logs/ssr_feedback/ssr_feedback_YYYY-MM-DD.jsonl`. This is
**distinct from L5 misroute feedback** — it measures explanation clarity, not
whether the user accepted or rejected the routing recommendation itself.
Analytics on this signal are surfaced in `app/ui/pages/feedback_insights.py`.

**L2 latency status:** `llm_latency_p95=4.11s` NO-GO (2026-05-09) снят двумя
пакетами: `ssr-l2-reliability-v1` (semantic cache + async pre-generation) и
`ssr-l2-tiered-explanation-gate-v1` (template-first; blended-eval target
p95 < 2s при helpful-rate ≥ L2 baseline).

**Verdict:** delivered. Контроль — production telemetry по tier decisions и
helpful-rate, без нового package до появления регрессии.

### Level 3 — Weekly Planner

**Backlog packages closed:**

- `ssr-ai-shared-infra-v1` — closed 2026-05-15 (shared telemetry/eval/fallback)
- `ssr-weekly-planner-baseline` — closed 2026-05-15 (rule-based 7-day plan +
  plan-completion telemetry)
- `ssr-ai-vision-level2-level3-readiness-gate` — closed 2026-05-15
- `epoch-ssr-weekly-study-narrative-v1` — closed 2026-05-31 (collapsible
  «Неделя в обучении» на Progress: 3–5 template bullets из локальных сигналов,
  ≤120 слов, без LLM по умолчанию, честный empty state)

**Contract:** `archive/ml_eval/ssr_level3/contract.yaml`

**Verdict:** rule-based baseline доставлен и виден пользователю.
ML/RL-оптимизация (`ml-ssr-plan-optimization`) остаётся deferred до
накопления 4+ недель planner telemetry.

### Level 4 — Concept Graph Router

**Backlog packages closed:**

- `kg-completeness-audit` — closed 2026-05-17 (graph classified ready)
- `epoch-ssr-graph-routing-eval-scaffold-v1` — closed 2026-05-27 (offline eval
  harness, `archive/ml_eval/ssr_level4/contract.yaml`)
- `epoch-ssr-graph-routing-v1` — closed 2026-05-29: runtime prerequisite-aware
  weak-concept reorder (`app/ssr_graph_routing.py`,
  `order_weak_concepts_for_ssr`) внутри `build_smart_study_recommendation`
  для `hint_kind ∈ {quiz_failed, mastery_stale}`; settings/feature-flag gate;
  rule-based fallback при недоступном графе

**Verdict:** prerequisite-aware routing доставлен за feature flag, без
регрессии hint_kind/primary_nav. Качество графа усилено закрытой волной
`wave-course-graph-evidence-2026-06` (compiler + relation UX + uplift gate,
все 3 пакета closed 2026-06-11); graph-aware retrieval включается только
при измеримом uplift.

### Level 5 — Misroute Feedback Loop

**Backlog packages closed:**

- `ssr-misroute-feedback-collection` — closed 2026-05-15 (accept/reject/defer
  events, local persistence, no PII)
- `epoch-ssr-misroute-policy-learning-v1` — closed 2026-05-30: offline weight
  adjustments with decay при ≥3 consistent rejects, согласованных с
  downstream retention signals; adjustment виден в evidence ledger; rule-based
  fallback при sparse feedback; contract —
  `archive/ml_eval/ssr_level5/policy_learning_contract.yaml`

**Scope boundary vs Level 2:** L5 collects *routing-level* signals — did the
user follow, skip, or defer the recommendation? L2's `ssr_feedback.py`
collects *explanation-quality* signals — was the "why now" text helpful? These
are separate datasets with separate schemas; L5 must not reuse or overwrite
the L2 JSONL logs.

**Verdict:** closed feedback loop с offline policy learning доставлен.
Online/adaptive policy и обучение весов в runtime остаются deferred до
накопления достаточного объёма локального feedback.

---

## Delivered Trust & Control Surface (Wave 4–5 идеи)

Все 5 бывших parked идей SSR доставлены:

| Идея | Package | Closed |
|---|---|---|
| Source-Coverage Route Guard | `epoch-ssr-source-coverage-route-guard-v1` | 2026-05-22 |
| Local Route Simulator (what-if preview) | `epoch-ssr-local-route-simulator-v1` | 2026-05-22 |
| Concept Recovery Ladder (hint → example → tutor → variant quiz → card) | `epoch-ssr-concept-recovery-ladder-v1/v2` | 2026-05-23/24 |
| Misroute Feedback → policy learning | `epoch-ssr-misroute-policy-learning-v1` | 2026-05-30 |
| Weekly Study Narrative | `epoch-ssr-weekly-study-narrative-v1` | 2026-05-31 |

Дополнительно: contrastive «why not others» (2026-05-17), route confidence
ledger v1 (2026-05-18).

---

## Execution Sequence — состояние

Рекомендованная последовательность v1.5 выполнена полностью:

0. ✅ `ssr-l2-reliability-v1` — closed 2026-05-14
1. ✅ `ssr-ai-shared-infra-v1` — closed 2026-05-15
2. ✅ `ssr-weekly-planner-baseline`, `ssr-misroute-feedback-collection` — closed 2026-05-15
3. ✅ `kg-completeness-audit` — closed 2026-05-17
4. ✅ `ssr-ai-vision-level2-level3-readiness-gate` — closed 2026-05-15

Плюс runtime-уровни сверх плана v1.5: graph routing (L4, 2026-05-29) и
misroute policy learning (L5, 2026-05-30).

**Остающиеся deferred model packages (открываются только по данным):**

- `ml-ssr-plan-optimization` — после 4+ недель L3 planner telemetry
- L1 hybrid serving promotion — после cold-start ≥1000 real samples + A/B gate
- L5 online policy learning — после 4+ недель misroute feedback data
- L4 graph-aware retrieval expansion — `course-graph-aware-uplift-gate-v1`
  closed 2026-06-11 (`wave-course-graph-evidence-2026-06` закрыта целиком);
  расширение graph-aware retrieval за feature flag до rollout

---

## Current Registry Map

| Wave | Status | Packages |
|---|---|---|
| `ssr-ai-vision-wave-1-foundation` | completed | `ml-ssr-baseline-hardening`, `ml-ssr-eval-harness`, `ml-ssr-forgetting-curve-v1` |
| `ssr-ai-vision-wave-2-explainability` | completed | `llm-ssr-explanation-eval`, `llm-ssr-prompt-engineering`, `llm-ssr-explanation-integration` |
| `ssr-ai-vision-wave-2b-l2-reliability` | completed | `ssr-l2-reliability-v1` (2026-05-14) |
| `ssr-ai-vision-readiness-gates` | completed | `ssr-ai-vision-level1-level2-readiness-gate` |
| `ssr-ai-vision-wave-3-shared-infra` | completed | `ssr-ai-shared-infra-v1` (2026-05-15) |
| `ssr-ai-vision-wave-3-planner-foundation` | completed | `ssr-weekly-planner-baseline` (2026-05-15) |
| `ssr-ai-vision-wave-3-feedback-foundation` | completed | `ssr-misroute-feedback-collection` (2026-05-15) |
| `ssr-ai-vision-wave-4-graph-prereq` | completed | `kg-completeness-audit` (2026-05-17) |
| `ssr-ai-vision-readiness-gates-next` | completed | `ssr-ai-vision-level2-level3-readiness-gate` (2026-05-15) |
| `ssr-ai-vision-wave-5-explanation-cost` | completed | `ssr-l2-tiered-explanation-gate-v1` (2026-05-23) |
| `wave-ssr-l4-graph-routing-runtime-2026-05` | completed | `epoch-ssr-graph-routing-eval-scaffold-v1`, `epoch-ssr-graph-routing-v1` |
| `wave-ssr-l5-misroute-policy-2026-05` | completed | `epoch-ssr-misroute-policy-learning-v1` |
| `wave-ssr-retention-narrative-2026-05` | completed | `epoch-ssr-weekly-study-narrative-v1` |
| `wave-course-graph-evidence-2026-06` | **closed** | `course-graph-compiler-v1` (closed 2026-06-11), `course-graph-relation-ux-v1` (closed 2026-06-11), `course-graph-aware-uplift-gate-v1` (closed 2026-06-11) — все 3 пакета closed; evidence-backed GraphRAG с uplift gate |

Точные статусы — `doc/backlog_registry.yaml`.

---

## Success Metrics

These are targets, not claims about current production impact.

| Metric | Baseline / current | Target |
|---|---|---|
| cards_due completion | rule-based SSR baseline; L1 ML serving gated (cold-start) | >= 75% after cold-start + rollout gate |
| explanation clarity | tiered gate delivered; tier decisions в trace | >= 4.0/5 |
| weekly plan completion | L3 baseline + narrative delivered; telemetry накапливается | >= 55% after baseline + telemetry |
| prerequisite violations | L4 routing delivered за feature flag | <= 5% after uplift gate + rollout |
| recommendation acceptance | L5 offline policy delivered; feedback накапливается | >= 85% after policy evaluation |

---

## Risks And Gates

| Risk | Affected levels | Current handling |
|---|---|---|
| Not enough real data | 1, 3, 5 | L1 cold-start gate (1000 real samples); L3 plan-optimization и L5 online policy deferred до 4+ недель telemetry |
| LLM latency/cost | 2 | Tiered gate (template-first) + semantic cache + async pre-generation; tier decision в trace |
| KG quality / filename-fallback graph | 4 | `wave-course-graph-evidence-2026-06`: compiler quality gate + uplift gate перед расширением graph-aware retrieval |
| Feedback sparsity | 5 | Rule-based fallback при sparse feedback; offline adjustments только при ≥3 consistent rejects + retention alignment |
| Silent serving promotion | 1, 4, 5 | Каждый уровень за explicit gate/flag; routing remains deterministic-fallback-first |

---

## Verification Commands

```powershell
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict --sync-from-index --write-sync
.\.venv\Scripts\python.exe scripts\workflow.py
.\.venv\Scripts\python.exe -m pytest tests/eval/test_ssr_graph_routing.py tests/test_ssr_misroute_policy.py tests/test_ssr_weekly_narrative.py -q --tb=short
.\.venv\Scripts\python.exe scripts\validate_evaluation_contract.py archive\ml_eval\ssr_level4\contract.yaml
.\.venv\Scripts\python.exe scripts\validate_evaluation_contract.py archive\ml_eval\ssr_level5\policy_learning_contract.yaml
```

Expected workflow result after this update: SSR AI Vision не даёт новых
candidate-пакетов; следующая SSR-работа возникает только из data gates
(serving promotion) или из `course-graph-aware-uplift-gate-v1`.

---

## Related Documents

- [`../product_owner_router.md`](../product_owner_router.md)
- [`../po_router_evaluation_gate.md`](../po_router_evaluation_gate.md)
- [`../product_owner_plan_ml_package_prompt.md`](../product_owner_plan_ml_package_prompt.md)
- [`../po_router_scope_matrix.md`](../po_router_scope_matrix.md)
- [`../../smart_study_router.md`](../../smart_study_router.md)
- [`ssr_ai_vision_level1_prompt.md`](ssr_ai_vision_level1_prompt.md)
- [`ssr_ai_vision_level2_prompt.md`](ssr_ai_vision_level2_prompt.md)
- [`ssr_ai_vision_level3_prompt.md`](ssr_ai_vision_level3_prompt.md)
- [`ssr_ai_vision_level4_prompt.md`](ssr_ai_vision_level4_prompt.md)
- [`ssr_ai_vision_level5_prompt.md`](ssr_ai_vision_level5_prompt.md)
