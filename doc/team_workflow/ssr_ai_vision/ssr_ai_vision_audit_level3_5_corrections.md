# SSR AI Vision — Audit Corrections Level 3-5
## Применение паттернов ошибок из Level 1-2

**Дата:** 2026-05-09  
**Scope:** Level 3 (Weekly Planner), Level 4 (Graph Router), Level 5 (Feedback Loop)  
**Базис:** Audit Report Level 1-2 (ssr_ai_vision_audit_report_2026-05-09.md)

---

## 📊 Паттерны ошибок из Level 1-2

Из аудита Level 1-2 выявлены следующие **повторяющиеся паттерны**:

### Паттерн #1: Метрики без "target" маркировки
- **Проблема:** Метрики выглядят как гарантии, а не targets
- **Решение:** Добавить `(target)` и предупреждение

### Паттерн #2: Risks без конкретных порогов
- **Проблема:** Mitigation слишком общие ("synthetic data + fallback")
- **Решение:** Конкретизировать: сколько, когда, как

### Паттерн #3: Отсутствие Failure Case Plan
- **Проблема:** Нет плана, что делать если метрика не достигнута
- **Решение:** Добавить BLOCK/TRY/PASS пороги

### Паттерн #4: Отсутствие fallback thresholds для ML/LLM
- **Проблема:** Нет порогов для fallback (когда переключаться на baseline)
- **Решение:** Добавить конкретные пороги (например, latency > X → fallback)

### Паттерн #5: Dependencies неясные
- **Проблема:** "Level X OR baseline" создаёт путаницу
- **Решение:** Чётко указать "baseline (Level X optional)"

---

## 🔧 Корректировки Level 3: Proactive Study Planner

### Корректировка #3.1: Добавить Failure Case Plan

**Где:** Phase 2: ML Optimization Layer  
**Добавить после:** "Approach: reinforcement learning (Q-learning) или supervised (XGBoost)"

```markdown
**Failure Case Plan:**
- If plan_completion_rate < 45% → BLOCK: недостаточно данных, собрать ещё 4+ weeks user activity
- If 45% ≤ plan_completion_rate < 55% → TRY: upgrade to reinforcement learning (Q-learning), retrain
- If plan_completion_rate ≥ 55% → PASS: proceed to integration
```

### Корректировка #3.2: Детализировать Risks

**Где:** § Risks & Mitigations  
**Заменить:**

```markdown
| Risk | Impact | Mitigation |
|------|--------|------------|
| Plan слишком жёсткий → low completion | High | 1. ML optimization для user patterns<br>2. User override rate < 30% threshold<br>3. A/B test: control = baseline, treatment = ML-optimized |
| Plan слишком мягкий → no structure | Medium | 1. Baseline constraints: min 3 items per day<br>2. Monitor daily_time_estimate ≥ 20 min<br>3. Alert if plan_density < 0.5 |
| ML overfits на прошлое → bad future plans | High | 1. Cross-validation (4-fold temporal split)<br>2. Regularization (L2, alpha=0.01)<br>3. Monitor plan_accuracy ≥ 80% |
| Users игнорируют plan | High | 1. A/B test + engagement metrics<br>2. Gamification (badges for plan completion)<br>3. Weekly reminder notifications |
| Plan generation > 5s | Medium | 1. Caching baseline plan for 24 hours<br>2. Async ML optimization<br>3. Fallback to baseline if latency > 10s |
| Недостаточно training data (< 4 weeks) | High | 1. Use rule-based baseline until 4+ weeks<br>2. Synthetic data generation (simulate user patterns)<br>3. Retrain weekly, switch to ML when plan_completion_rate ≥ 45% |
```

### Корректировка #3.3: Уточнить Success Metrics

**Где:** § Success Metrics  
**Заменить:**

```markdown
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: plan_completion_rate** | 40% | ≥ 55% (+15% target) | % weekly plan items completed |
| **Secondary: plan_accuracy** | N/A | ≥ 80% (target) | % items completed as scheduled (day) |
| **Secondary: user_override_rate** | N/A | < 30% (target) | % times user changes plan |
| **Secondary: weekly_engagement** | Baseline | +20% (target) | Active days per week |
| **Secondary: plan_generation_latency** | N/A | < 5s (target) | Time to generate weekly plan |

**IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Level 3 требует evaluation contract и может не достичь target с первой попытки.
```

---

## 🔧 Корректировки Level 4: Concept Graph Router

### Корректировка #4.1: Добавить Failure Case Plan

**Где:** Phase 2: Implement Concept Routing  
**Добавить после:** "Fallback: if KG query fails → use original rec"

```markdown
**Failure Case Plan:**
- If prerequisite_violation_rate > 15% → BLOCK: KG incomplete, fix graph coverage
- If 5% < prerequisite_violation_rate ≤ 15% → TRY: improve prerequisite detection algorithm
- If prerequisite_violation_rate ≤ 5% → PASS: proceed to prerequisite validation
```

### Корректировка #4.2: Детализировать Risks

**Где:** § Risks & Mitigations  
**Заменить:**

```markdown
| Risk | Impact | Mitigation |
|------|--------|------------|
| KG incomplete (missing prerequisites) | High | 1. Fallback to baseline SSR<br>2. Monitor graph_coverage ≥ 80% (concepts with prerequisites)<br>3. Manual review + graph expansion |
| Graph query > 100ms | Medium | 1. Caching prerequisite chains for 1 hour<br>2. Index optimization (prerequisite lookup)<br>3. Fallback to baseline if latency > 200ms |
| Циклы в графе | Medium | 1. Cycle detection algorithm (visited set)<br>2. Max depth limit = 5 levels<br>3. Log cycles for manual review |
| Users не понимают prerequisite chain | Medium | 1. UI explanation + visual graph<br>2. A/B test: with/without prerequisite chain<br>3. User feedback survey (clarity ≥ 4.0/5) |
| KG unavailable (service down) | High | 1. Fallback to baseline SSR<br>2. Monitor kg_availability ≥ 99%<br>3. Graceful degradation (no prerequisite checks) |
```

### Корректировка #4.3: Уточнить Success Metrics

**Где:** § Success Metrics  
**Заменить:**

```markdown
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: prerequisite_violation_rate** | 25% | ≤ 5% (-20% target) | % recommendations без met prerequisites |
| **Secondary: graph_query_latency_p95** | N/A | < 100ms (target) | Time to query KG |
| **Secondary: recommendation_relevance** | 3.5/5 | ≥ 4.0/5 (target) | Human eval (50 scenarios) |
| **Secondary: learning_path_coherence** | 60% | ≥ 80% (target) | % concepts в правильном порядке |

**IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Level 4 требует evaluation contract и может не достичь target с первой попытки.
```

---

## 🔧 Корректировки Level 5: Misroute Feedback Loop

### Корректировка #5.1: Добавить Failure Case Plan

**Где:** Phase 3: Evaluation Harness  
**Добавить после:** "Report: archive/ml_eval/ssr_feedback_loop_v1_report.md"

```markdown
**Failure Case Plan:**
- If recommendation_acceptance_rate < 75% → BLOCK: недостаточно feedback data, собрать ещё 2+ weeks
- If 75% ≤ recommendation_acceptance_rate < 85% → TRY: upgrade to contextual bandits (reinforcement learning), retrain
- If recommendation_acceptance_rate ≥ 85% → PASS: proceed to integration
```

### Корректировка #5.2: Детализировать Risks

**Где:** § Risks & Mitigations  
**Заменить:**

```markdown
| Risk | Impact | Mitigation |
|------|--------|------------|
| Users не дают feedback | High | 1. Incentivize feedback (gamification: +10 XP per feedback)<br>2. Implicit feedback (defer = negative, accept = positive)<br>3. Monitor feedback_rate ≥ 30% (target) |
| Model overfits на negative feedback | High | 1. Regularization (L2, alpha=0.01)<br>2. Exploration bonus (ε-greedy, ε=0.1)<br>3. Monitor weight_distribution: clip [0.5, 1.5] |
| Feedback loop создаёт filter bubble | Medium | 1. Exploration/exploitation balance (ε-greedy)<br>2. Periodic baseline reset (every 4 weeks)<br>3. Monitor diversity_score ≥ 0.6 |
| Explainability теряется | High | 1. Evidence ledger показывает adjustments<br>2. Show feedback count per hint_kind<br>3. User can reset weights to baseline |
| Policy weights diverge (unstable) | High | 1. Clip weights [0.5, 1.5]<br>2. Monitor weight_std < 0.3<br>3. Alert if weight_change > 0.2 per week |
| Недостаточно feedback data (< 100 feedbacks) | High | 1. Use baseline priority until 100+ feedbacks<br>2. Synthetic feedback generation (simulate user patterns)<br>3. Retrain weekly, switch to ML when acceptance_rate ≥ 75% |
```

### Корректировка #5.3: Уточнить Success Metrics

**Где:** § Success Metrics  
**Заменить:**

```markdown
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: recommendation_acceptance_rate** | 70% | ≥ 85% (+15% target) | % recommendations accepted by user |
| **Secondary: policy_adaptation_accuracy** | N/A | ≥ 75% (target) | % correct weight adjustments |
| **Secondary: user_satisfaction_score** | 3.8/5 | ≥ 4.2/5 (target) | Post-feedback survey (5-point Likert) |
| **Secondary: feedback_collection_latency** | N/A | < 1s (target) | Time to save feedback |
| **Secondary: explainability preserved** | Baseline | No regression (target) | Evidence ledger shows adjustments |

**IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Level 5 требует evaluation contract и может не достичь target с первой попытки.
```

---

## 📋 Checklist применения корректировок

### Level 3: Proactive Study Planner
- [ ] Добавить Failure Case Plan в Phase 2
- [ ] Детализировать Risks (6 конкретных mitigations)
- [ ] Уточнить Success Metrics (добавить "target" + предупреждение)

### Level 4: Concept Graph Router
- [ ] Добавить Failure Case Plan в Phase 2
- [ ] Детализировать Risks (5 конкретных mitigations)
- [ ] Уточнить Success Metrics (добавить "target" + предупреждение)

### Level 5: Misroute Feedback Loop
- [ ] Добавить Failure Case Plan в Phase 3
- [ ] Детализировать Risks (6 конкретных mitigations)
- [ ] Уточнить Success Metrics (добавить "target" + предупреждение)

---

## 🎯 Ожидаемый результат

После применения всех корректировок:

1. **Level 3-5 будут иметь ту же строгость**, что и Level 1-2 после аудита
2. **Failure Case Plans** для всех ML-компонентов (Level 3, Level 5)
3. **Конкретные пороги** для всех risks и mitigations
4. **Чёткие target метрики** с предупреждением о не-гарантированности
5. **Единообразие** всех 5 уровней по качеству документации

---

**Версия:** 1.0  
**Дата:** 2026-05-09  
**Статус:** Ready for application  
**Next Steps:** Применить корректировки к Level 3-5 промптам
