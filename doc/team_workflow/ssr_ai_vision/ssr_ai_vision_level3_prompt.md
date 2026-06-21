# SSR AI Vision — Level 3: Proactive Study Planner
## Copy-Paste Prompt для Product Owner

**Дата:** 2026-05-08  
**Уровень:** 3 из 5  
**Цель:** Недельный проактивный план обучения вместо реактивных рекомендаций

---

## 🎯 Что это

**Level 3** переводит SSR от **реактивного** (что делать сейчас) к **проактивному** (что делать на этой неделе).

**Baseline (текущее):** Реактивная рекомендация
```
Сейчас: «Повторить 5 карточек»
```

**Target (Level 3):** Проактивный недельный план
```
Понедельник: «На этой неделе вам стоит:
  1. Повторить 23 карточки (распределение: 8 пн, 7 ср, 8 пт)
  2. Закрыть пробел по "Нейронные сети" (2 сессии тьютора)
  3. Пройти quiz по "Линейная алгебра" (score прошлый раз: 60%)
  Estimated time: 45 мин/день»
```

---

## 📋 Copy-Paste Prompt

```text
Прочитай doc/team_workflow/archive/product_owner_router_ai_vision_enhancement.md
и doc/smart_study_router.md (§ Next Level — AI Vision, Уровень 3)
и создай полный delivery plan для SSR Level 3: Proactive Study Planner.

Контекст:
- Текущий SSR: реактивный (рекомендация при каждом открытии)
- Цель: недельный проактивный план с распределением нагрузки
- Constraint: plan generation < 5s, local-first, user может override

Шаги:

1. **Evaluation Contract (ОБЯЗАТЕЛЬНО ПЕРВЫМ):**
   
   Прочитай doc/team_workflow/po_router_evaluation_gate.md
   и создай evaluation contract.
   
   Параметры:
   - Feature: SSR Level 3 — Proactive Study Planner
   - Baseline metric: plan_completion_rate = 40% (текущий adaptive plan)
   - Target metric: plan_completion_rate ≥ 55% (+15%)
   - Secondary metrics:
     * plan_generation_latency < 5s
     * plan_accuracy: 80% items completed as scheduled
     * user_override_rate < 30% (plan не слишком жёсткий)
     * weekly_engagement: +20% active days per week
   
   Test harness:
   - 30 user profiles × 4 weeks simulation
   - Metrics: completion rate, accuracy, override rate
   - Script: tests/eval/test_ssr_weekly_planner.py
   - Test cases: tests/eval/ssr_weekly_planner_scenarios.json
   
   Вывод:
   - evaluation_contract.yaml в archive/ml_eval/ssr_level3/
   - Simulation script: scripts/ml/simulate_weekly_plan.py
   - Test cases: 30 user profiles

2. **Hybrid Package Planning:**
   
   Прочитай doc/team_workflow/po_router_scope_matrix.md (§ Hybrid Intelligence)
   и создай 3-phase hybrid package.
   
   Package ID: ssr-weekly-planner-v1
   Type: hybrid_intelligence
   
   **Phase 1: Baseline Weekly Planner (Rule-Based)**
   
   Deliverables:
   - app/ui/weekly_plan_card.py (rule-based planner)
   - Algorithm:
     ```python
     def generate_weekly_plan_baseline(user_state):
         # 1. Collect all pending items
         cards_due = get_flashcards_due_next_7_days()
         sm2_due = get_sm2_concepts_due_next_7_days()
         weak_concepts = get_weak_concepts()
         plan_blocks = get_adaptive_plan_blocks()
         
         # 2. Distribute by priority
         monday = cards_due[:8] + sm2_due[:2]
         wednesday = cards_due[8:15] + weak_concepts[:1]
         friday = cards_due[15:23] + plan_blocks[:1]
         
         # 3. Estimate time
         total_time = sum(item.estimated_minutes for item in all_items)
         daily_time = total_time / 7
         
         return WeeklyPlan(
             monday=monday,
             wednesday=wednesday,
             friday=friday,
             daily_time_estimate=daily_time
         )
     ```
   - Tests: tests/test_weekly_plan_baseline.py
   - Baseline metrics measurement
   
   **Phase 2: ML Optimization Layer**
   
   Deliverables:
   - scripts/ml/train_weekly_plan_optimizer.py
   - Model: optimize distribution для max completion rate
   - Features:
     * user_completion_history (past 4 weeks)
     * time_of_day_preference (утро vs вечер)
     * day_of_week_activity (пн-вс patterns)
     * session_duration_avg
     * cards_due_count
     * weak_concepts_count
   - Target: completion_probability per day (0-1)
   - Output: models/weekly_plan_optimizer_v1.pkl
   - Approach: reinforcement learning (Q-learning) или supervised (XGBoost)
   
   **Failure Case Plan:**
   - If plan_completion_rate < 45% → BLOCK: недостаточно данных, собрать ещё 4+ weeks user activity
   - If 45% ≤ plan_completion_rate < 55% → TRY: upgrade to reinforcement learning (Q-learning), retrain
   - If plan_completion_rate ≥ 55% → PASS: proceed to integration
   
   **Phase 3: Hybrid Orchestration**
   
   Deliverables:
   - app/ui/weekly_plan_card.py (hybrid: baseline + ML optimization)
   - Algorithm:
     ```python
     def generate_weekly_plan_hybrid(user_state):
         # 1. Generate baseline plan
         baseline_plan = generate_weekly_plan_baseline(user_state)
         
         # 2. ML optimization (if model available)
         if ml_model_available():
             optimized_plan = ml_optimize_distribution(
                 baseline_plan,
                 user_completion_history
             )
         else:
             optimized_plan = baseline_plan
         
         # 3. Explainability overlay
         for day in optimized_plan.days:
             day.explanation = generate_day_explanation(
                 day.items,
                 user_state,
                 ml_adjustment=optimized_plan.ml_adjusted
             )
         
         return optimized_plan
     ```
   - Fallback: if ML fails → baseline
   - Monitoring: completion_rate, override_rate, ml_adjustment_impact
   - Tests: tests/test_weekly_plan_hybrid.py

3. **Scope Type:**
   
   Ожидаемый результат: **Hybrid Intelligence**
   - Baseline: rule-based weekly distribution
   - ML layer: optimize distribution для user patterns
   - Fallback: if ML fails → baseline
   - Explainability: show baseline + ML adjustments

4. **Wave Planning:**
   
   Создай wave structure для Level 3:
   
   Wave ID: ssr-ai-vision-wave-3-proactive
   Theme: "Proactive Planning"
   
   Packages:
   - ssr-weekly-planner-baseline (rule-based weekly plan)
   - ml-ssr-plan-optimization (ML optimization layer)
   - ssr-weekly-plan-integration (hybrid orchestration + UI)
   
   Entry condition: Level 1 closed (ML reranking) + Level 2 closed (LLM explanation) ИЛИ baseline SSR
   Exit condition: plan_completion_rate ≥ 55%, user_override_rate < 30%

5. **Registry Update:**
   
   Запиши в doc/backlog_registry.yaml:
   
   ```yaml
   - package_id: ssr-weekly-planner-baseline
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: M
     priority: P1
     description: "Rule-based weekly planner: distribute items по дням"
     deliverables:
       - app/ui/weekly_plan_card.py (baseline algorithm)
       - tests/test_weekly_plan_baseline.py
       - doc/ssr_weekly_plan_algorithm.md
     dependencies: []
     
   - package_id: ml-ssr-plan-optimization
     status: proposed
     type: ml_package
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: L
     priority: P1
     description: "ML optimization: распределение для max completion"
     deliverables:
       - scripts/ml/train_weekly_plan_optimizer.py
       - models/weekly_plan_optimizer_v1.pkl
       - tests/eval/test_ssr_weekly_planner.py
       - archive/ml_eval/ssr_level3/plan_optimizer_v1_report.md
     dependencies:
       - ssr-weekly-planner-baseline
     evaluation_contract:
       primary_metric: "plan_completion_rate ≥ 55%"
       secondary_metrics:
         - "plan_generation_latency < 5s"
         - "user_override_rate < 30%"
         - "weekly_engagement +20%"
     
   - package_id: ssr-weekly-plan-integration
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: M
     priority: P1
     description: "Hybrid orchestration + UI для weekly plan"
     deliverables:
       - app/ui/weekly_plan_card.py (hybrid algorithm)
       - app/ui/weekly_plan_render.py (UI component)
       - tests/test_weekly_plan_hybrid.py
       - tests/e2e/weekly_plan.spec.ts (Playwright)
     dependencies:
       - ml-ssr-plan-optimization
   ```
   
   Затем:
   ```powershell
   .\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
   ```

Вывод:
1. ✅ Evaluation contract (30 user profiles, 4-week simulation)
2. ✅ 3-phase hybrid package (baseline → ML → orchestration)
3. ✅ Scope type: Hybrid Intelligence
4. ✅ Wave structure (3 packages)
5. ✅ Registry update + sync

Expected timing: 4-5 недель (1 неделя baseline + 2 недели ML + 1 неделя integration + 1 неделя testing)
```

---

## 🔍 Ключевые решения

### Почему weekly plan, а не daily?

| Horizon | Pros | Cons |
|---------|------|------|
| **Daily** | Простой, реактивный | Нет долгосрочного видения |
| **Weekly** | Баланс планирования и гибкости | Требует ML optimization |
| **Monthly** | Долгосрочное видение | Слишком жёсткий, низкий completion rate |

**Решение:** Weekly для баланса между планированием и гибкостью.

### Почему reinforcement learning, а не supervised?

| Approach | Pros | Cons |
|----------|------|------|
| **Supervised** | Простой, быстрый | Нужны labeled examples (completed plans) |
| **Reinforcement** | Учится на feedback (completion) | Сложнее, требует больше данных |

**Решение:** Начать с supervised (XGBoost), если не хватает данных → reinforcement learning.

---

## 📊 Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: plan_completion_rate** | 40% | ≥ 55% (+15% target) | % weekly plan items completed |
| **Secondary: plan_accuracy** | N/A | ≥ 80% (target) | % items completed as scheduled (day) |
| **Secondary: user_override_rate** | N/A | < 30% (target) | % times user changes plan |
| **Secondary: weekly_engagement** | Baseline | +20% (target) | Active days per week |
| **Secondary: plan_generation_latency** | N/A | < 5s (target) | Time to generate weekly plan |

**IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Level 3 требует evaluation contract и может не достичь target с первой попытки.

---

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Plan слишком жёсткий → low completion | High | 1. ML optimization для user patterns<br>2. User override rate < 30% threshold<br>3. A/B test: control = baseline, treatment = ML-optimized |
| Plan слишком мягкий → no structure | Medium | 1. Baseline constraints: min 3 items per day<br>2. Monitor daily_time_estimate ≥ 20 min<br>3. Alert if plan_density < 0.5 |
| ML overfits на прошлое → bad future plans | High | 1. Cross-validation (4-fold temporal split)<br>2. Regularization (L2, alpha=0.01)<br>3. Monitor plan_accuracy ≥ 80% |
| Users игнорируют plan | High | 1. A/B test + engagement metrics<br>2. Gamification (badges for plan completion)<br>3. Weekly reminder notifications |
| Plan generation > 5s | Medium | 1. Caching baseline plan for 24 hours<br>2. Async ML optimization<br>3. Fallback to baseline if latency > 10s |
| Недостаточно training data (< 4 weeks) | High | 1. Use rule-based baseline until 4+ weeks<br>2. Synthetic data generation (simulate user patterns)<br>3. Retrain weekly, switch to ML when plan_completion_rate ≥ 45% |

---

## 🔗 Related Documents

- [`product_owner_router_ai_vision_enhancement.md`](../archive/product_owner_router_ai_vision_enhancement.md) — Enhancement plan
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (§ Next Level, Уровень 3)
- [`po_router_scope_matrix.md`](po_router_scope_matrix.md) — Hybrid Intelligence scope
- [`ssr_ai_vision_level2_prompt.md`](ssr_ai_vision_level2_prompt.md) — Level 2 (prerequisite)

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Предыдущий уровень:** [Level 2: LLM-Enhanced Explanation](ssr_ai_vision_level2_prompt.md)  
**Следующий уровень:** [Level 4: Concept Graph Router](ssr_ai_vision_level4_prompt.md)
