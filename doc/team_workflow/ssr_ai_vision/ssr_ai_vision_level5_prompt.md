# SSR AI Vision — Level 5: Misroute Feedback Loop
## Copy-Paste Prompt для Product Owner

**Дата:** 2026-05-08  
**Уровень:** 5 из 5 (финальный)  
**Цель:** Замкнуть feedback loop — SSR учится на отклонениях пользователя

---

## 🎯 Что это

**Level 5** замыкает цикл user→system learning: пользователь может сказать «этот совет был не полезен», и SSR корректирует policy weights.

**Baseline (текущее):** SSR не учится на feedback
```
User: *отклоняет cards_due 3 раза подряд*
SSR: *продолжает рекомендовать cards_due*
```

**Target (Level 5):** Adaptive policy weights
```
User: *отклоняет cards_due 3 раза подряд*
SSR: *снижает приоритет cards_due для этого пользователя*
Evidence ledger: «Приоритет flashcards снижен (3 отклонения)»
```

---

## 📋 Copy-Paste Prompt

```text
Прочитай doc/team_workflow/archive/product_owner_router_ai_vision_enhancement.md
и doc/smart_study_router.md (§ Next Level — AI Vision, Уровень 5)
и создай полный delivery plan для SSR Level 5: Misroute Feedback Loop.

Контекст:
- Текущий SSR: фиксированные приоритеты, не учится на feedback
- Цель: adaptive policy weights на основе user feedback
- Constraint: feedback collection < 1s, model retraining offline, explainability сохранена

Шаги:

1. **Evaluation Contract (ОБЯЗАТЕЛЬНО ПЕРВЫМ):**
   
   Прочитай doc/team_workflow/po_router_evaluation_gate.md
   и создай evaluation contract.
   
   Параметры:
   - Feature: SSR Level 5 — Misroute Feedback Loop
   - Baseline metric: recommendation_acceptance_rate = 70% (текущий)
   - Target metric: recommendation_acceptance_rate ≥ 85% (+15%)
   - Secondary metrics:
     * feedback_collection_latency < 1s
     * policy_adaptation_accuracy ≥ 75% (correct weight adjustments)
     * user_satisfaction_score ≥ 4.2/5 (post-feedback survey)
     * no regression: explainability сохранена
   
   Test harness:
   - 50 user profiles × 100 recommendations each
   - Simulate feedback patterns (accept/reject/defer)
   - Measure: acceptance rate, adaptation accuracy, satisfaction
   - Script: tests/eval/test_ssr_feedback_loop.py
   
   Вывод:
   - evaluation_contract.yaml в archive/ml_eval/ssr_level5/
   - Simulation script: scripts/ml/simulate_feedback_loop.py
   - Test cases: tests/eval/ssr_feedback_scenarios.json

2. **ML Package Planning:**
   
   Прочитай doc/team_workflow/product_owner_plan_ml_package_prompt.md
   и создай 5-phase ML package.
   
   Package ID: ml-ssr-feedback-loop-v1
   Type: ml_package
   
   **Phase 1: Feedback Collection**
   - Goal: собрать user feedback на SSR recommendations
   - UI: кнопки «Полезно» / «Не полезно» / «Не сейчас» на каждой рекомендации
   - Data schema:
     ```python
     @dataclass
     class SSRFeedback:
         recommendation_id: str
         hint_kind: SmartStudyRouterHintKind
         user_action: Literal["accepted", "rejected", "deferred"]
         timestamp: datetime
         context: dict  # user_state snapshot
     ```
   - Storage: user_state.db (new table: ssr_feedback)
   - Deliverables:
     * app/ui/adaptive_plan_card.py (feedback buttons)
     * app/user_state.py (save_ssr_feedback)
     * tests/test_ssr_feedback_collection.py
   
   **Phase 2: Policy Learning Model**
   - Approach: reinforcement learning (contextual bandits) или supervised (XGBoost)
   - Features:
     * hint_kind (cards_due, sm2_due, quiz_failed, ...)
     * user_context (cards_due_count, sm2_due_count, time_of_day, ...)
     * historical_acceptance_rate per hint_kind
     * recent_feedback (last 10 recommendations)
   - Target: acceptance_probability (0-1) per hint_kind
   - Training:
     * Offline: retrain model каждую ночь на accumulated feedback
     * Online: update policy weights in real-time (simple Bayesian update)
   - Output: models/ssr_policy_learner_v1.pkl
   - Deliverables:
     * scripts/ml/train_ssr_policy_learner.py
     * models/ssr_policy_learner_v1.pkl
     * tests/test_ssr_policy_learning.py
   
   **Phase 3: Evaluation Harness**
   - Primary metric: recommendation_acceptance_rate ≥ 85%
   - Secondary metrics:
     * policy_adaptation_accuracy ≥ 75%
     * feedback_to_adaptation_latency < 24 hours (offline retraining)
     * user_satisfaction_score ≥ 4.2/5
   - Test set: 50 user profiles × 100 recommendations
   - Script: scripts/ml/eval_ssr_feedback_loop.py
   - Report: archive/ml_eval/ssr_feedback_loop_v1_report.md
   
   **Failure Case Plan:**
   - If recommendation_acceptance_rate < 75% → BLOCK: недостаточно feedback data, собрать ещё 2+ weeks
   - If 75% ≤ recommendation_acceptance_rate < 85% → TRY: upgrade to contextual bandits (reinforcement learning), retrain
   - If recommendation_acceptance_rate ≥ 85% → PASS: proceed to integration
   
   **Phase 4: Integration**
   - Module: app/ui/adaptive_plan_card.py
   - Function: _apply_adaptive_policy_weights()
   - Algorithm:
     ```python
     def _apply_adaptive_policy_weights(rec, user_feedback_history):
         # 1. Get baseline priority
         baseline_priority = get_baseline_priority(rec.hint_kind)
         
         # 2. Get learned weight adjustment
         if policy_model_available():
             weight_adjustment = policy_model.predict(
                 hint_kind=rec.hint_kind,
                 user_context=get_user_context(),
                 feedback_history=user_feedback_history
             )
         else:
             weight_adjustment = 1.0  # No adjustment
         
         # 3. Apply adjustment
         adjusted_priority = baseline_priority * weight_adjustment
         
         # 4. Explainability: show adjustment in evidence ledger
         if weight_adjustment < 0.8:
             rec.evidence_ledger.append(
                 f"Приоритет {rec.hint_kind} снижен "
                 f"({len([f for f in user_feedback_history if f.user_action == 'rejected'])} отклонений)"
             )
         
         return rec
     ```
   - Fallback: if model fails → baseline priority
   - Monitoring:
     * acceptance_rate per hint_kind
     * weight_adjustment distribution
     * feedback_collection_rate
   - Deliverables:
     * app/ui/adaptive_plan_card.py (_apply_adaptive_policy_weights)
     * tests/test_ssr_adaptive_policy.py
   
   **Phase 5: A/B Test**
   - Control: SSR без feedback loop (baseline priority)
   - Treatment: SSR с feedback loop (adaptive weights)
   - Metric: recommendation_acceptance_rate
   - Duration: 4 weeks
   - Sample size: 200 users (100 control, 100 treatment)
   - Deliverables:
     * scripts/ml/run_ssr_feedback_ab_test.py
     * archive/ml_eval/ssr_feedback_ab_test_report.md

3. **Scope Type:**
   
   Прочитай doc/team_workflow/po_router_scope_matrix.md
   и определи scope type.
   
   Ожидаемый результат: **Hybrid Intelligence**
   - Baseline: rule-based priority (или Level 1 ML)
   - ML layer: adaptive policy weights на основе feedback
   - Fallback: if model fails → baseline
   - Explainability: evidence ledger показывает adjustments

4. **Wave Planning:**
   
   Создай wave structure для Level 5:
   
   Wave ID: ssr-ai-vision-wave-5-feedback
   Theme: "Feedback Loop Closure"
   
   Packages:
   - ml-ssr-feedback-collection (UI + data pipeline)
   - ml-ssr-policy-learning (model training + evaluation)
   - ml-ssr-adaptive-weights (integration + monitoring)
   
   Entry condition: Level 4 closed (graph routing) ИЛИ baseline SSR
   Exit condition: acceptance_rate ≥ 85%, satisfaction ≥ 4.2/5

5. **Registry Update:**
   
   Запиши в doc/backlog_registry.yaml:
   
   ```yaml
   - package_id: ml-ssr-feedback-collection
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: M
     priority: P1
     description: "Feedback collection: UI buttons + data pipeline"
     deliverables:
       - app/ui/adaptive_plan_card.py (feedback buttons)
       - app/user_state.py (save_ssr_feedback, ssr_feedback table)
       - tests/test_ssr_feedback_collection.py
       - tests/e2e/ssr_feedback.spec.ts
     dependencies: []
     
   - package_id: ml-ssr-policy-learning
     status: proposed
     type: ml_package
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: L
     priority: P1
     description: "Policy learning model: adaptive weights на основе feedback"
     deliverables:
       - scripts/ml/train_ssr_policy_learner.py
       - models/ssr_policy_learner_v1.pkl
       - tests/eval/test_ssr_feedback_loop.py
       - archive/ml_eval/ssr_feedback_loop_v1_report.md
     dependencies:
       - ml-ssr-feedback-collection
     evaluation_contract:
       primary_metric: "recommendation_acceptance_rate ≥ 85%"
       secondary_metrics:
         - "policy_adaptation_accuracy ≥ 75%"
         - "user_satisfaction_score ≥ 4.2/5"
         - "feedback_collection_latency < 1s"
     
   - package_id: ml-ssr-adaptive-weights
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: M
     priority: P1
     description: "Integration: adaptive policy weights + explainability"
     deliverables:
       - app/ui/adaptive_plan_card.py (_apply_adaptive_policy_weights)
       - tests/test_ssr_adaptive_policy.py
       - scripts/ml/run_ssr_feedback_ab_test.py
       - archive/ml_eval/ssr_feedback_ab_test_report.md
     dependencies:
       - ml-ssr-policy-learning
   ```
   
   Затем:
   ```powershell
   .\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
   ```

Вывод:
1. ✅ Evaluation contract (50 user profiles, 100 recommendations each)
2. ✅ ML package (5 phases: feedback → learning → eval → integration → A/B)
3. ✅ Scope type: Hybrid Intelligence
4. ✅ Wave structure (3 packages)
5. ✅ Registry update + sync

Expected timing: 5-6 недель (1 неделя feedback UI + 2 недели ML + 1 неделя integration + 2 недели A/B test)
```

---

## 🔍 Ключевые решения

### Почему reinforcement learning, а не supervised?

| Approach | Pros | Cons |
|----------|------|------|
| **Supervised** | Простой, быстрый | Нужны labeled examples (accepted/rejected) |
| **Reinforcement (contextual bandits)** | Учится на feedback в real-time | Сложнее, требует exploration/exploitation balance |

**Решение:** Начать с supervised (XGBoost), если нужна real-time adaptation → contextual bandits.

### Как обрабатывать cold start (новый пользователь)?

```python
def get_policy_weight(hint_kind, user_feedback_history):
    if len(user_feedback_history) < 10:
        # Cold start: use baseline priority
        return 1.0
    else:
        # Warm start: use learned weights
        return policy_model.predict(hint_kind, user_feedback_history)
```

**Решение:** Baseline priority для cold start, learned weights после 10+ feedbacks.

---

## 📊 Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: recommendation_acceptance_rate** | 70% | ≥ 85% (+15% target) | % recommendations accepted by user |
| **Secondary: policy_adaptation_accuracy** | N/A | ≥ 75% (target) | % correct weight adjustments |
| **Secondary: user_satisfaction_score** | 3.8/5 | ≥ 4.2/5 (target) | Post-feedback survey (5-point Likert) |
| **Secondary: feedback_collection_latency** | N/A | < 1s (target) | Time to save feedback |
| **Secondary: explainability preserved** | Baseline | No regression (target) | Evidence ledger shows adjustments |

**IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Level 5 требует evaluation contract и может не достичь target с первой попытки.

---

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users не дают feedback | High | 1. Incentivize feedback (gamification: +10 XP per feedback)<br>2. Implicit feedback (defer = negative, accept = positive)<br>3. Monitor feedback_rate ≥ 30% (target) |
| Model overfits на negative feedback | High | 1. Regularization (L2, alpha=0.01)<br>2. Exploration bonus (ε-greedy, ε=0.1)<br>3. Monitor weight_distribution: clip [0.5, 1.5] |
| Feedback loop создаёт filter bubble | Medium | 1. Exploration/exploitation balance (ε-greedy)<br>2. Periodic baseline reset (every 4 weeks)<br>3. Monitor diversity_score ≥ 0.6 |
| Explainability теряется | High | 1. Evidence ledger показывает adjustments<br>2. Show feedback count per hint_kind<br>3. User can reset weights to baseline |
| Policy weights diverge (unstable) | High | 1. Clip weights [0.5, 1.5]<br>2. Monitor weight_std < 0.3<br>3. Alert if weight_change > 0.2 per week |
| Недостаточно feedback data (< 100 feedbacks) | High | 1. Use baseline priority until 100+ feedbacks<br>2. Synthetic feedback generation (simulate user patterns)<br>3. Retrain weekly, switch to ML when acceptance_rate ≥ 75% |

---

## 🎉 Completion: All 5 Levels

После Level 5, SSR AI Vision **полностью реализован**:

| Level | Feature | Status |
|-------|---------|--------|
| **1** | Local ML Layer | ✅ Forgetting curve, personal retention |
| **2** | LLM-Enhanced Explanation | ✅ Personalized why_now_ru |
| **3** | Proactive Study Planner | ✅ Weekly plan, ML optimization |
| **4** | Concept Graph Router | ✅ Prerequisite-aware routing |
| **5** | Misroute Feedback Loop | ✅ Adaptive policy weights |

**Next Horizon:** Parked ideas (Route Simulator, Source-Coverage Guard, Concept Recovery Ladder, Weekly Narrative)

---

## 🔗 Related Documents

- [`product_owner_router_ai_vision_enhancement.md`](../archive/product_owner_router_ai_vision_enhancement.md) — Enhancement plan
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (§ Next Level, Уровень 5)
- [`po_router_scope_matrix.md`](po_router_scope_matrix.md) — Hybrid Intelligence scope
- [`ssr_ai_vision_level4_prompt.md`](ssr_ai_vision_level4_prompt.md) — Level 4 (prerequisite)

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Предыдущий уровень:** [Level 4: Concept Graph Router](ssr_ai_vision_level4_prompt.md)  
**Статус:** FINAL LEVEL — AI Vision Complete 🎉
