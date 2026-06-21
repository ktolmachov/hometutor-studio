# Product Owner Router — AI Vision Enhancement Plan

**Дата:** 2026-05-08  
**Версия:** 1.0 (Enhancement Proposal)  
**Цель:** Детальное планирование продуктовых артефактов для реализации всех 5 уровней "Next Level — AI Vision" из Smart Study Router

---

## 📋 Executive Summary

Текущий `product_owner_router.md` v2.1 — отличный orchestration hub для **детерминированных** product workflows. Но для реализации **AI Vision** (5 уровней из `smart_study_router.md`) нужны **новые продуктовые артефакты** и **расширенные decision paths**.

### Ключевые пробелы

| # | Пробел | Почему критично | Решение |
|---|--------|-----------------|---------|
| 1 | Нет AI-specific ideation mode | SSR Next Level требует ML/LLM линз, которых нет в breakthrough | Новый режим `MODE=AI_VISION_IDEATION` |
| 2 | Нет ML/Data artifacts в workflow | Уровни 1-3 требуют datasets, models, eval harness | Новый prompt `generate_ml_package_prompt.md` |
| 3 | Нет evaluation-first planning | AI features требуют eval metrics ДО implementation | Новый gate: `evaluation_contract_gate` |
| 4 | Нет hybrid (rule+AI) decision path | SSR Vision = hybrid router, не чистый ML | Новый scope type: `hybrid_intelligence` |
| 5 | Нет LLM cost/latency constraints | AI features имеют runtime costs | Новые constraint types в ideation |

---

## 🎯 Предлагаемые улучшения

### Enhancement 1: AI Vision Ideation Mode

**Файл:** `doc/team_workflow/generate_breakthrough_ideation_prompt.md`

**Новый режим:** `MODE=AI_VISION_IDEATION`

#### Отличия от базового breakthrough

| Аспект | Базовый breakthrough | AI Vision Ideation |
|--------|---------------------|-------------------|
| **Линзы** | UX, Pedagogy, Engagement | + ML Feasibility, Data Requirements, Inference Cost |
| **Method sources** | Duolingo, Anki, Hook Model | + Academic papers (ML), Hugging Face models, LangChain patterns |
| **Constraints** | Token budget, offline-first | + Latency SLA, model size, training data volume |
| **Effort scale** | S/M/L (dev time) | + Data (rows), Training (GPU-hours), Inference (ms) |
| **Scoring** | impact/effort | + (impact × data_quality) / (effort + inference_cost) |

#### Новые обязательные поля для AI ideas

```yaml
ml_approach:
  type: "lightweight_local | llm_enhanced | hybrid_rule_ml"
  model_size: "< 10MB | 10-100MB | > 100MB"
  training_data: "user_local | synthetic | none (zero-shot)"
  inference_latency: "< 50ms | 50-200ms | > 200ms"
  
data_requirements:
  min_samples: <number>
  features: [list]
  labeling_effort: "none | low | medium | high"
  
evaluation_contract:
  primary_metric: "<metric_name>"
  baseline: "<current_value>"
  target: "<target_value>"
  test_set: "<source>"
```

#### Copy-Paste Prompt для AI Vision

```text
Прочитай doc/team_workflow/generate_breakthrough_ideation_prompt.md
и выполни MODE=AI_VISION_IDEATION.

Параметры:
  TARGET: Smart Study Router — Next Level (Levels 1-5)
  N_IDEAS: 15
  ANGLES: ML_Feasibility, Data_Requirements, Inference_Cost, Explainability
  CONSTRAINTS: 
    - Local-first: model must run on device
    - Latency: inference < 200ms p95
    - Explainability: every AI decision must be traceable
    - Token budget: LLM calls only for explanation, not routing
    - Data privacy: no cloud training on user data

Вывод: артефакт с 15 идеями, каждая с ml_approach + data_requirements + evaluation_contract
```

---

### Enhancement 2: ML Package Planning Prompt

**Новый файл:** `doc/team_workflow/product_owner_plan_ml_package_prompt.md`

#### Зачем отдельный prompt

ML packages отличаются от feature packages:

| Feature Package | ML Package |
|----------------|------------|
| Requirements → Design → Tasks | **Data → Model → Eval → Integration** |
| DoD = tests pass | DoD = **eval metrics hit target** |
| Rollback = revert commit | Rollback = **model version switch** |
| Risk = bugs | Risk = **data drift, model degradation** |

#### Структура ML Package Contract

```yaml
package_id: ml-ssr-forgetting-curve-v1
type: ml_package
status: proposed

# Phase 1: Data Collection & Labeling
data_phase:
  goal: "Collect 1000+ user sessions with SM-2 outcomes"
  sources:
    - user_state.db (flashcard_reviews table)
    - tutor_sessions (quiz outcomes)
  labeling:
    method: "automatic (SM-2 intervals as ground truth)"
    validation: "manual review of 100 samples"
  deliverables:
    - data/ml/ssr_forgetting_curve_train.parquet
    - data/ml/ssr_forgetting_curve_test.parquet
    - scripts/ml/data_collection_ssr.py

# Phase 2: Model Development
model_phase:
  approach: "logistic regression (sklearn)"
  features:
    - time_since_last_review (hours)
    - quiz_score_last_3 (avg)
    - concept_difficulty (from graph)
    - session_duration_avg (minutes)
  target: "retention_probability (0-1)"
  training:
    script: scripts/ml/train_ssr_forgetting_curve.py
    output: models/ssr_forgetting_curve_v1.pkl
    size_limit: "< 1MB"
  
# Phase 3: Evaluation Harness
eval_phase:
  primary_metric: "AUC-ROC"
  baseline: 0.50 (random)
  target: ≥ 0.75
  test_set: "20% holdout from data_phase"
  script: scripts/ml/eval_ssr_forgetting_curve.py
  report: archive/ml_eval/ssr_forgetting_curve_v1_report.md

# Phase 4: Integration
integration_phase:
  module: app/ui/adaptive_plan_card.py
  function: _apply_ml_priority_reranking()
  fallback: "if model fails → use rule-based priority"
  monitoring:
    - inference_latency_p95 < 50ms
    - prediction_confidence > 0.6 for 80% of cases
  
# Phase 5: A/B Test (optional)
ab_test_phase:
  control: "rule-based SSR (current)"
  treatment: "hybrid (rule + ML reranking)"
  metric: "cards_due completion rate"
  duration: "2 weeks"
  sample_size: "100 users (local A/B via user_state flag)"
```

#### Copy-Paste Prompt для ML Package

```text
Прочитай doc/team_workflow/product_owner_plan_ml_package_prompt.md
и создай ML package contract.

Контекст:
  - Idea: SSR Level 1 — Local ML Layer (forgetting curve per card)
  - Target metric: Improve cards_due completion rate from 60% → 75%
  - Constraint: Model < 1MB, inference < 50ms, local-only

Вывод:
  1. 5-phase ML package contract (data → model → eval → integration → A/B)
  2. Evaluation contract с baseline/target
  3. Rollback plan (fallback to rule-based)
  4. Запись в backlog_registry.yaml со статусом proposed
```

---

### Enhancement 3: Evaluation-First Gate

**Файл:** `doc/team_workflow/po_router_evaluation_gate.md` (новый модуль)

#### Принцип

> **Для любого AI feature:** evaluation contract ПЕРЕД implementation contract.

#### Evaluation Contract Template

```yaml
evaluation_contract:
  feature: "SSR Level 2 — LLM-Enhanced Explanation"
  
  # Что измеряем
  metrics:
    primary:
      name: "explanation_clarity_score"
      type: "human_eval (1-5 Likert)"
      baseline: 3.2 (current template-based)
      target: ≥ 4.0
      test_set: "50 SSR recommendations × 3 raters"
    
    secondary:
      - name: "explanation_length"
        target: "< 150 words (readability)"
      - name: "llm_latency"
        target: "< 2s p95"
      - name: "token_cost"
        target: "< 500 tokens per explanation"
  
  # Как измеряем
  test_harness:
    script: tests/eval/test_ssr_llm_explanation.py
    data: tests/eval/ssr_explanation_test_cases.json
    rubric: doc/eval/ssr_explanation_rubric.md
  
  # Когда считаем успехом
  success_criteria:
    - primary metric hits target
    - ALL secondary metrics within bounds
    - no regression on existing SSR metrics (cards_due priority preserved)
  
  # Что делаем при провале
  failure_plan:
    - if clarity < 3.5: iterate prompt engineering (max 3 iterations)
    - if latency > 3s: switch to smaller model or caching
    - if cost > 1000 tokens: abort feature, keep template-based
```

#### Decision Table Update

Добавить в `product_owner_router.md` Decision Table:

| # | Состояние | Следующий шаг | Зачем |
|---|-----------|---------------|-------|
| **13** | **AI feature proposed** | **`po_router_evaluation_gate.md`** | **Eval contract перед impl** |

#### Copy-Paste Prompt для Evaluation Gate

```text
Прочитай doc/team_workflow/po_router_evaluation_gate.md
и создай evaluation contract.

Контекст:
  - Feature: SSR Level 2 — LLM-Enhanced Explanation
  - Current: template-based why_now_ru (clarity score 3.2/5)
  - Goal: personalized explanation using user's learning history

Вывод:
  1. Evaluation contract (metrics, test harness, success criteria)
  2. Test cases (50 SSR scenarios)
  3. Rubric для human eval
  4. Failure plan (что делать если не достигли target)
```

---

### Enhancement 4: Hybrid Intelligence Scope Type

**Файл:** `doc/team_workflow/po_router_scope_matrix.md` (расширение)

#### Новый scope type

Текущие scope types в `po_router_scope_matrix.md`:
- Single idea → single package
- 3+ cohesive ideas → wave
- 3+ low cohesion → separate packages

**Добавить:**

```markdown
### Hybrid Intelligence Scope

**Когда:** Idea требует комбинации rule-based + ML/LLM

**Признаки:**
- Есть детерминированная baseline (rule-based)
- ML/LLM усиливает, но не заменяет baseline
- Нужен fallback при ML failure
- Explainability критична

**Структура package:**

1. **Phase 1: Baseline Hardening**
   - Укрепить rule-based logic
   - Добавить comprehensive tests
   - Измерить baseline metrics

2. **Phase 2: ML/LLM Layer**
   - Evaluation contract (см. Enhancement 3)
   - Model development или prompt engineering
   - Integration с fallback

3. **Phase 3: Hybrid Orchestration**
   - Rule-based → ML reranking → explainability overlay
   - Monitoring (latency, cost, accuracy)
   - A/B test (rule-only vs hybrid)

**Пример:** SSR Level 1 (Local ML Layer)
- Baseline: current priority (cards_due > sm2_due > ...)
- ML layer: rerank based on forgetting curve
- Fallback: if ML fails → use baseline
- Explainability: show both rule priority + ML adjustment
```

#### Copy-Paste Prompt для Hybrid Scope

```text
Прочитай doc/team_workflow/po_router_scope_matrix.md
и определи scope type для идеи.

Контекст:
  - Idea: SSR Level 1 — Local ML Layer
  - Current: rule-based priority (8 hint kinds)
  - Proposal: ML reranking based on user's forgetting curve
  - Constraint: must preserve explainability

Вывод:
  1. Scope type: Hybrid Intelligence
  2. 3-phase structure (baseline → ML → orchestration)
  3. Evaluation contract для Phase 2
  4. Fallback plan
```

---

### Enhancement 5: AI-Specific Constraints

**Файл:** `doc/team_workflow/generate_breakthrough_ideation_prompt.md` (расширение)

#### Новые constraint types

Добавить в § PHASE 0 — INPUTS & VALIDATION:

```markdown
### AI-Specific Constraints

При `MODE=AI_VISION_IDEATION`, дополнительно к базовым constraints:

**Latency Constraints:**
- `inference_latency_p95: < 50ms | < 200ms | < 1s`
- `llm_call_timeout: < 2s | < 5s | < 10s`

**Cost Constraints:**
- `token_budget_per_call: < 500 | < 2000 | < 10000`
- `llm_calls_per_session: < 1 | < 5 | < 20`

**Data Constraints:**
- `training_data_volume: < 1k rows | < 10k | < 100k`
- `labeling_effort: none | low (< 1 hour) | medium (< 1 day) | high (> 1 day)`

**Model Constraints:**
- `model_size: < 1MB | < 10MB | < 100MB`
- `model_type: sklearn_only | pytorch_allowed | llm_allowed`

**Privacy Constraints:**
- `data_location: local_only | cloud_allowed_anonymized | cloud_allowed_full`
- `model_training: on_device | cloud_federated | cloud_centralized`

**Explainability Constraints:**
- `decision_traceability: full | partial | none`
- `user_override: always | sometimes | never`
```

#### Validation в PHASE 2

```python
# Pseudo-code для constraint check
def validate_ai_idea(idea, constraints):
    violations = []
    
    if idea.inference_latency > constraints.inference_latency_p95:
        violations.append(f"Latency {idea.inference_latency} > {constraints.inference_latency_p95}")
    
    if idea.token_budget > constraints.token_budget_per_call:
        violations.append(f"Token budget {idea.token_budget} > {constraints.token_budget_per_call}")
    
    if idea.model_size > constraints.model_size:
        violations.append(f"Model size {idea.model_size} > {constraints.model_size}")
    
    if idea.data_location != "local_only" and constraints.data_location == "local_only":
        violations.append(f"Data location {idea.data_location} violates local_only constraint")
    
    return violations
```

---

## 🗺️ AI Vision Roadmap Integration

### Mapping 5 Levels → Product Artifacts

| Level | SSR Vision | Product Artifacts Needed | Enhancement |
|-------|-----------|-------------------------|-------------|
| **1** | Local ML Layer | ML package (data → model → eval → integration) | Enhancement 2 + 3 |
| **2** | LLM-Enhanced Explanation | Evaluation contract + prompt engineering package | Enhancement 3 |
| **3** | Proactive Study Planner | Hybrid package (rule-based weekly plan + ML optimization) | Enhancement 4 |
| **4** | Concept Graph Router | Integration package (knowledge_graph.py + SSR) | Standard feature package |
| **5** | Misroute Feedback Loop | ML package (feedback collection → model retraining → policy update) | Enhancement 2 + 3 |

### Wave Structure для AI Vision

```yaml
# Предлагаемая структура в backlog_registry.yaml

wave_id: ssr-ai-vision-wave-1
theme: "Hybrid Intelligence Foundation"
packages:
  - ml-ssr-baseline-hardening      # Phase 1: укрепить rule-based
  - ml-ssr-eval-harness            # Phase 2: evaluation infrastructure
  - ml-ssr-forgetting-curve-v1     # Phase 3: Level 1 implementation

wave_id: ssr-ai-vision-wave-2
theme: "LLM-Enhanced Explainability"
packages:
  - llm-ssr-explanation-eval       # Evaluation contract
  - llm-ssr-prompt-engineering     # Prompt iteration
  - llm-ssr-explanation-integration # Integration + fallback

wave_id: ssr-ai-vision-wave-3
theme: "Proactive Planning"
packages:
  - ssr-weekly-planner-baseline    # Rule-based weekly plan
  - ml-ssr-plan-optimization       # ML optimization layer
  - ssr-plan-ab-test               # A/B test

wave_id: ssr-ai-vision-wave-4
theme: "Graph-Aware Routing"
packages:
  - kg-ssr-integration-design      # Design integration
  - kg-ssr-concept-dependencies    # Implement concept routing
  - kg-ssr-prerequisite-checks     # Prerequisite validation

wave_id: ssr-ai-vision-wave-5
theme: "Feedback Loop Closure"
packages:
  - ml-ssr-feedback-collection     # UI + data pipeline
  - ml-ssr-policy-learning         # Model retraining
  - ml-ssr-adaptive-weights        # Dynamic priority adjustment
```

---

## 📝 Updated Decision Table

Добавить в `product_owner_router.md`:

| # | Состояние | Что это значит | Следующий шаг | Зачем |
|---|-----------|----------------|---------------|-------|
| **13** | **AI feature proposed** | **Идея требует ML/LLM** | **`po_router_evaluation_gate.md`** | **Eval contract перед impl** |
| **14** | **Eval contract ready** | **Metrics + test harness** | **`product_owner_plan_ml_package_prompt.md`** | **ML package structure** |
| **15** | **Hybrid scope detected** | **Rule + AI combo** | **`po_router_scope_matrix.md` § Hybrid** | **3-phase structure** |

---

## 🎯 Copy-Paste Prompt для Product Owner (AI Vision)

```text
Прочитай doc/team_workflow/product_owner_router.md
и doc/team_workflow/archive/product_owner_router_ai_vision_enhancement.md
и выбери следующий шаг для AI Vision planning.

Контекст:
- Target: Smart Study Router — Next Level (5 уровней)
- Current SSR: rule-based, детерминированный (v2.0 closed)
- Goal: Hybrid intelligence (rule + ML + LLM)

Шаги:

1. **Ideation (если ещё не сделано):**
   ```
   MODE=AI_VISION_IDEATION
   TARGET=Smart Study Router Next Level
   N_IDEAS=15
   ANGLES=ML_Feasibility, Data_Requirements, Inference_Cost, Explainability
   CONSTRAINTS=local-first, latency<200ms, explainability=full
   ```

2. **Для каждой принятой идеи:**
   
   a. **Evaluation Contract:**
      ```
      Прочитай doc/team_workflow/po_router_evaluation_gate.md
      Feature: <idea_title>
      Baseline: <current_metric>
      Target: <target_metric>
      ```
   
   b. **ML Package (если ML/LLM):**
      ```
      Прочитай doc/team_workflow/product_owner_plan_ml_package_prompt.md
      Idea: <idea_title>
      Approach: <ml_approach>
      Data: <data_requirements>
      ```
   
   c. **Scope Type:**
      ```
      Прочитай doc/team_workflow/po_router_scope_matrix.md
      Idea: <idea_title>
      Type: Hybrid Intelligence | Standard Feature
      ```

3. **Wave Planning:**
   ```
   Прочитай doc/team_workflow/generate_roadmap_epoch_waves_prompt.md
   Ideas: <accepted_ideas_list>
   Theme: <cohesive_theme>
   Structure: 5 waves (Foundation → Explainability → Planning → Graph → Feedback)
   ```

4. **Registry Update:**
   ```
   .\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
   ```

Вывод:
1. Evaluation contracts для всех AI features
2. ML packages для Levels 1, 2, 5
3. Standard packages для Levels 3, 4
4. 5-wave structure в backlog_registry.yaml
5. Sync tasklist.md
```

---

## 🔧 Implementation Checklist

### Phase 1: Documentation (1-2 дня)

- [ ] Создать `doc/team_workflow/po_router_evaluation_gate.md`
- [ ] Создать `doc/team_workflow/product_owner_plan_ml_package_prompt.md`
- [ ] Расширить `doc/team_workflow/generate_breakthrough_ideation_prompt.md` (MODE=AI_VISION_IDEATION)
- [ ] Расширить `doc/team_workflow/po_router_scope_matrix.md` (Hybrid Intelligence)
- [ ] Обновить `doc/team_workflow/product_owner_router.md` (Decision Table rows 13-15)

### Phase 2: Templates & Examples (1 день)

- [ ] Создать `doc/team_workflow/templates/evaluation_contract_template.yaml`
- [ ] Создать `doc/team_workflow/templates/ml_package_template.yaml`
- [ ] Создать `doc/team_workflow/examples/ssr_level1_ml_package_example.yaml`
- [ ] Создать `doc/team_workflow/examples/ssr_level2_eval_contract_example.yaml`

### Phase 3: Scripts (2-3 дня)

- [ ] Создать `scripts/validate_evaluation_contract.py` (проверка eval contract)
- [ ] Создать `scripts/generate_ml_package_scaffold.py` (генерация структуры ML package)
- [ ] Расширить `scripts/backlog_registry_lint.py` (валидация ML packages)
- [ ] Создать `scripts/ml/eval_harness_template.py` (шаблон eval harness)

### Phase 4: Integration (1 день)

- [ ] Обновить `scripts/workflow.py` (поддержка ML packages)
- [ ] Обновить `doc/backlog_registry.yaml` schema (новые поля для ML packages)
- [ ] Обновить `doc/roadmap_governance.md` (правила для AI features)

### Phase 5: Testing (1 день)

- [ ] Прогнать AI Vision Ideation на SSR Next Level (15 идей)
- [ ] Создать evaluation contract для Level 1
- [ ] Создать ML package для Level 1
- [ ] Проверить sync в backlog_registry.yaml

---

## 📊 Success Metrics

### Для Enhancement'ов

| Enhancement | Success Metric | Target |
|------------|---------------|--------|
| 1: AI Vision Ideation | Генерация 15 идей с ML constraints | < 30 мин |
| 2: ML Package Planning | Создание 5-phase ML package | < 20 мин |
| 3: Evaluation Gate | Evaluation contract для AI feature | < 15 мин |
| 4: Hybrid Scope | Определение scope type | < 10 мин |
| 5: AI Constraints | Валидация constraints для идеи | < 5 мин |

### Для AI Vision Roadmap

| Wave | Deliverable | Success Metric |
|------|------------|----------------|
| Wave 1 | ML baseline + eval harness | Eval harness работает, baseline metrics измерены |
| Wave 2 | LLM explanation | Clarity score ≥ 4.0, latency < 2s |
| Wave 3 | Weekly planner | Plan completion rate +15% |
| Wave 4 | Graph routing | Prerequisite-aware recommendations 80% |
| Wave 5 | Feedback loop | Policy weights adapt after 10 feedbacks |

---

## 🚀 Next Steps

1. **Review этого документа** — согласовать с Product Owner
2. **Создать Phase 1 artifacts** — 5 новых/расширенных .md файлов
3. **Запустить AI Vision Ideation** — 15 идей для SSR Next Level
4. **Создать evaluation contracts** — для Levels 1, 2, 5
5. **Упаковать в waves** — 5 waves в backlog_registry.yaml
6. **Sync и commit** — обновить tasklist.md

---

## 📚 Related Documents

- [`product_owner_router.md`](product_owner_router.md) — базовый PO router
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (5 levels)
- [`generate_breakthrough_ideation_prompt.md`](generate_breakthrough_ideation_prompt.md) — ideation prompt
- [`po_router_scope_matrix.md`](po_router_scope_matrix.md) — scope types
- [`backlog_registry.yaml`](../backlog_registry.yaml) — SSoT

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Автор:** AI Enhancement Analysis  
**Статус:** Proposal (ждёт review)
