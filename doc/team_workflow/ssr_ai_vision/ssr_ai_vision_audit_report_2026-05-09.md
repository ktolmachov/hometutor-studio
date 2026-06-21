# SSR AI Vision — Audit Report Level 1 & Level 2
## Критические ошибки и корректировки

**Дата аудита:** 2026-05-09  
**Аудитор:** Kiro AI  
**Scope:** Level 1 (Local ML Layer) и Level 2 (LLM Explanation)  
**Статус:** ✅ Аудит завершён, все критические ошибки исправлены

---

## 📊 Executive Summary

**Найдено:** 6 ошибок (2 критические, 4 важные)  
**Исправлено:** 6 ошибок  
**Затронутые файлы:**
- `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md` (4 исправления)
- `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_level1_prompt.md` (2 исправления)
- `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_level2_prompt.md` (2 исправления)

**Общий вердикт:** Level 1 и Level 2 теперь **готовы к execution** после корректировок.

---

## ❌ Критические ошибки (BLOCKER)

### Ошибка #1: Неверные метрики в Summary

**Severity:** 🔴 CRITICAL  
**Файл:** `ssr_ai_vision_summary.md`  
**Проблема:**

В таблице Success Metrics указано:

```markdown
| Metric | Baseline | After Level 1 | After Level 2 |
|--------|----------|---------------|---------------|
| **cards_due completion** | 60% | 75% (+15%) | 75% |
```

**Почему это ошибка:**
- `75% (+15%)` выглядит как **гарантированный результат**, а не target
- Level 1 Prompt говорит: `cards_due completion rate ≥ 75%` (target, не гарантия)
- Это вводит в заблуждение Product Owner: он ожидает +15%, но может получить меньше

**Корректировка:**

```markdown
| Metric | Baseline | After Level 1 (target) | After Level 2 (target) |
|--------|----------|------------------------|------------------------|
| **cards_due completion** | 60% | ≥ 75% (+15% target) | ≥ 75% (no change) |
| **explanation clarity** | 3.2/5 | 3.2/5 (no change) | ≥ 4.0/5 (+0.8 target) |
```

**Добавлено предупреждение:**

> **IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Каждый уровень требует evaluation contract и может не достичь target с первой попытки.

**Статус:** ✅ Исправлено

---

### Ошибка #2: Execution Paths — неверные timing

**Severity:** 🔴 CRITICAL  
**Файл:** `ssr_ai_vision_summary.md`  
**Проблема:**

В Path B (Parallel Waves) указано:

```markdown
Wave 1 (6 weeks):
  - Level 1: Local ML Layer
  - Level 2: LLM Explanation (parallel, no dependency)

Wave 2 (5 weeks):
  - Level 3: Weekly Planner (depends on Wave 1)

Wave 3 (10 weeks, parallel):
  - Level 4: Graph Router (4 weeks, depends on Wave 2)
  - Level 5: Feedback Loop (6 weeks, depends on Wave 2)

Total: 21 weeks (vs 22 sequential)
```

**Почему это ошибка:**
- Wave 1: max(4, 3) = **4 недели** (НЕ 6!)
- Wave 3: max(4, 6) = **6 недель** (НЕ 10!)
- Total: 4 + 5 + 6 = **15 недель** (НЕ 21!)
- Экономия: 22 - 15 = **7 недель** (НЕ 1 неделя!)

**Корректировка:**

```markdown
### Path B: Parallel Waves (Faster) ⚡

Wave 1 (parallel, 4 weeks):
  - Level 1: Local ML Layer (4 weeks)
  - Level 2: LLM Explanation (3 weeks, parallel — depends on baseline only)

Wave 2 (5 weeks):
  - Level 3: Weekly Planner (5 weeks, depends on Wave 1)

Wave 3 (parallel, 6 weeks):
  - Level 4: Graph Router (4 weeks, depends on Wave 2)
  - Level 5: Feedback Loop (6 weeks, depends on Wave 2)

Total: 15 weeks (vs 22 sequential) — экономия 7 недель
```

**Статус:** ✅ Исправлено

---

## ⚠️ Важные ошибки (HIGH)

### Ошибка #3: Level 2 Dependencies — противоречие

**Severity:** 🟡 HIGH  
**Файл:** `ssr_ai_vision_summary.md`  
**Проблема:**

В Quick Reference Table указано:

```markdown
| Level | Dependencies |
|-------|--------------|
| **2** | Level 1 OR baseline |
```

Но в Path B указано:

```markdown
Wave 1 (parallel):
  - Level 2: LLM Explanation (parallel, no dependency)
```

**Противоречие:** Если Level 2 зависит от Level 1 OR baseline, то он **может** быть parallel (т.к. baseline уже есть). Но тогда в таблице должно быть `baseline (Level 1 optional)`, а не `Level 1 OR baseline`.

**Корректировка:**

```markdown
| Level | Dependencies |
|-------|--------------|
| **2** | Baseline SSR (Level 1 optional) |
```

**Статус:** ✅ Исправлено

---

### Ошибка #4: Risks — недостаточная детализация для Level 1

**Severity:** 🟡 HIGH  
**Файл:** `ssr_ai_vision_summary.md`, `ssr_ai_vision_level1_prompt.md`  
**Проблема:**

В Summary (Critical Risks) указано:

```markdown
| Risk | Mitigation |
|------|------------|
| Недостаточно training data | Synthetic data + cold start fallback |
```

**Почему это недостаточно:**
- Сколько synthetic data?
- Как именно работает cold start fallback?
- Когда переключаться с fallback на ML?

**Корректировка:**

```markdown
| Risk | Mitigation |
|------|------------|
| Недостаточно training data (< 1000 samples) | 1. Generate 500+ synthetic samples using SM-2 formula<br>2. Use rule-based priority until 1000+ real samples<br>3. Retrain weekly, switch to ML when AUC-ROC ≥ 0.70 |
```

**Статус:** ✅ Исправлено в Summary и Level 1 Prompt

---

### Ошибка #5: Level 2 Token Cost — нет fallback threshold

**Severity:** 🟡 HIGH  
**Файл:** `ssr_ai_vision_level2_prompt.md`  
**Проблема:**

В Level 2 Prompt указано:

```markdown
Secondary metrics:
  * token_cost < 500 tokens per explanation
```

Но **нет** порога для fallback: что делать, если token cost > 500?

**Корректировка:**

Добавлено в Phase 2: Integration:

```markdown
**Token Budget Guard:**
- If token_cost > 500 → compress prompt (remove examples)
- If token_cost > 700 → fallback to template
- Monitor: token_cost_p95 < 500 (95% of calls)
```

**Статус:** ✅ Исправлено

---

### Ошибка #6: Level 1 AUC-ROC — нет плана для failure case

**Severity:** 🟡 HIGH  
**Файл:** `ssr_ai_vision_level1_prompt.md`  
**Проблема:**

В Level 1 Prompt указано:

```markdown
Primary metric: "AUC-ROC ≥ 0.75"
```

Но **нет** плана, что делать, если AUC-ROC < 0.75 после training.

**Корректировка:**

Добавлено в Phase 3: Evaluation Harness:

```markdown
**Failure Case Plan:**
- If AUC-ROC < 0.70 → BLOCK: недостаточно данных, собрать ещё 1000+ samples
- If 0.70 ≤ AUC-ROC < 0.75 → TRY: upgrade to XGBoost, retrain
- If AUC-ROC ≥ 0.75 → PASS: proceed to integration
```

**Статус:** ✅ Исправлено

---

## ✅ Что работает хорошо

### Level 1: Local ML Layer

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| **Evaluation Contract** | ✅ Excellent | Чёткие метрики, test harness, rubric |
| **ML Package Structure** | ✅ Excellent | 5 phases, data → model → eval → integration → A/B |
| **Scope Type** | ✅ Correct | Hybrid Intelligence (rule + ML) |
| **Hardware Recommendations** | ✅ Excellent | Детальные таблицы для CPU/RAM/inference |
| **Model Recommendations** | ✅ Excellent | Logistic Regression vs XGBoost vs NN comparison |
| **Explainability** | ✅ Excellent | Evidence ledger + feature coefficients |
| **Fallback Strategy** | ✅ Excellent | Rule-based fallback если ML fails |

### Level 2: LLM-Enhanced Explanation

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| **Evaluation Contract** | ✅ Excellent | Clarity rubric, 50 test cases, 3 raters |
| **Prompt Engineering** | ✅ Excellent | 3-5 iterations, A/B test |
| **Scope Type** | ✅ Correct | Standard Feature (LLM не влияет на routing) |
| **Caching Strategy** | ✅ Excellent | 1-hour cache для снижения latency и cost |
| **Fallback Strategy** | ✅ Excellent | Template fallback если LLM fails |
| **Constraint Enforcement** | ✅ Excellent | LLM только для explanation, не для routing |

---

## 📋 Checklist для Product Owner

Перед запуском Level 1 и Level 2, убедитесь:

### Level 1: Local ML Layer

- [ ] **Evaluation contract создан** — `archive/ml_eval/ssr_level1/evaluation_contract.yaml`
- [ ] **Test harness готов** — `tests/eval/test_ssr_ml_reranking.py`
- [ ] **Baseline SSR укреплён** — comprehensive tests, edge cases
- [ ] **Data collection script готов** — `scripts/ml/data_collection_ssr.py`
- [ ] **Training script готов** — `scripts/ml/train_ssr_forgetting_curve.py`
- [ ] **Evaluation script готов** — `scripts/ml/eval_ssr_forgetting_curve.py`
- [ ] **Integration plan готов** — hybrid (rule + ML), fallback, explainability
- [ ] **Failure case plan понятен** — что делать если AUC-ROC < 0.75
- [ ] **Monitoring plan готов** — inference latency, fallback rate, acceptance rate

### Level 2: LLM-Enhanced Explanation

- [ ] **Evaluation contract создан** — `archive/ml_eval/ssr_level2/evaluation_contract.yaml`
- [ ] **Test harness готов** — `tests/eval/test_ssr_llm_explanation.py`
- [ ] **Clarity rubric готов** — `doc/eval/ssr_explanation_rubric.md`
- [ ] **Prompt template готов** — baseline prompt в `app/prompts.py`
- [ ] **Prompt iterations plan готов** — 3-5 versions, A/B test
- [ ] **Integration plan готов** — async, caching, fallback
- [ ] **Token budget guard готов** — compress if > 500, fallback if > 700
- [ ] **Monitoring plan готов** — llm_latency_p95, token_cost_p95, fallback_rate

---

## 🎯 Рекомендации

### Для Level 1

1. **Начать с data collection** — собрать 1000+ samples перед training
2. **Использовать synthetic data** — если real data < 1000, generate 500+ synthetic
3. **Начать с Logistic Regression** — upgrade к XGBoost только если AUC-ROC < 0.75
4. **Мониторить inference latency** — если > 50ms, добавить caching
5. **A/B test обязателен** — control = rule-based, treatment = hybrid

### Для Level 2

1. **Начать с evaluation contract** — clarity rubric, 50 test cases, 3 raters
2. **Итерировать промпты** — 3-5 versions, выбрать лучший по clarity score
3. **Использовать caching** — 1-hour cache для снижения latency и cost
4. **Мониторить token cost** — если > 500, compress prompt
5. **A/B test обязателен** — control = template, treatment = LLM

---

## 📈 Ожидаемые результаты (после корректировок)

### Level 1: Local ML Layer

| Metric | Baseline | Target | Confidence |
|--------|----------|--------|------------|
| **cards_due completion** | 60% | ≥ 75% | 🟢 High (если AUC-ROC ≥ 0.75) |
| **AUC-ROC** | 0.50 | ≥ 0.75 | 🟡 Medium (зависит от data quality) |
| **Inference latency p95** | N/A | < 50ms | 🟢 High (logistic regression быстрый) |
| **Model size** | N/A | < 1MB | 🟢 High (logistic regression компактный) |

### Level 2: LLM-Enhanced Explanation

| Metric | Baseline | Target | Confidence |
|--------|----------|--------|------------|
| **clarity_score** | 3.2/5 | ≥ 4.0/5 | 🟡 Medium (зависит от prompt quality) |
| **llm_latency_p95** | N/A | < 2s | 🟢 High (с caching) |
| **token_cost** | N/A | < 500 | 🟢 High (с compression) |
| **fallback_rate** | N/A | < 10% | 🟢 High (с template fallback) |

---

## 🔗 Связанные документы

- [`ssr_ai_vision_summary.md`](ssr_ai_vision_summary.md) — Complete roadmap (все 5 уровней)
- [`ssr_ai_vision_level1_prompt.md`](ssr_ai_vision_level1_prompt.md) — Level 1: Local ML Layer
- [`ssr_ai_vision_level2_prompt.md`](ssr_ai_vision_level2_prompt.md) — Level 2: LLM Explanation
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (§ Next Level, § Level 1 Deep Dive)

---

**Версия:** 1.0  
**Дата:** 2026-05-09  
**Статус:** ✅ Аудит завершён, все критические ошибки исправлены  
**Next Steps:** Review корректировок → Approve → Start execution
