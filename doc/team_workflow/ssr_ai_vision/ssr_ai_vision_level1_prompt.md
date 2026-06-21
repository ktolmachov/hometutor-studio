# SSR AI Vision — Level 1: Local ML Layer
## Copy-Paste Prompt для Product Owner

**Дата:** 2026-05-08  
**Уровень:** 1 из 5  
**Цель:** Lightweight ML модель для персонализированного reranking приоритетов SSR

---

## 🎯 Что это

**Level 1** добавляет локальную ML-модель, которая учится на паттернах конкретного пользователя и корректирует приоритеты SSR-рекомендаций.

**Baseline (текущее):** Фиксированные приоритеты (cards_due > sm2_due > quiz_failed > ...)

**Target (Level 1):** ML reranking на основе:
- Forgetting curve per card (скорость забывания)
- Personal retention rate (индивидуальная память)
- Concept difficulty model (сложность тем)
- Time-of-day preference (утро vs вечер)
- Session fatigue estimator (усталость в сессии)

---

## 📋 Copy-Paste Prompt

```text
Прочитай doc/team_workflow/archive/product_owner_router_ai_vision_enhancement.md
и doc/smart_study_router.md (§ Next Level — AI Vision, Уровень 1)
и создай полный delivery plan для SSR Level 1: Local ML Layer.

Контекст:
- Текущий SSR: rule-based, детерминированный (8 hint kinds, фиксированные приоритеты)
- Цель: добавить ML reranking без замены baseline
- Constraint: local-first, модель < 1MB, inference < 50ms, explainability сохранена

Шаги:

1. **Evaluation Contract (ОБЯЗАТЕЛЬНО ПЕРВЫМ):**
   
   Прочитай doc/team_workflow/po_router_evaluation_gate.md
   и создай evaluation contract.
   
   Параметры:
   - Feature: SSR Level 1 — Local ML Layer
   - Baseline metric: cards_due completion rate = 60% (текущий)
   - Target metric: cards_due completion rate ≥ 75%
   - Secondary metrics:
     * inference_latency_p95 < 50ms
     * model_size < 1MB
     * explainability: каждое ML-решение traceable
   
   Вывод:
   - evaluation_contract.yaml в archive/ml_eval/ssr_level1/
   - Test harness script: tests/eval/test_ssr_ml_reranking.py
   - Test cases: 100 SSR scenarios с ground truth
   - Rubric: doc/eval/ssr_ml_reranking_rubric.md

2. **ML Package Planning:**
   
   Прочитай doc/team_workflow/product_owner_plan_ml_package_prompt.md
   и создай 5-phase ML package.
   
   Параметры:
   - Package ID: ml-ssr-local-reranking-v1
   - Approach: logistic regression (sklearn)
   - Features: 9 сигналов из SSR + temporal features
   - Target: retention_probability (0-1)
   - Training data: user_state.db (flashcard_reviews, quiz_outcomes, tutor_sessions)
   
   Phases:
   
   **Phase 1: Data Collection & Labeling**
   - Goal: 1000+ user sessions с SM-2 outcomes
   - Sources: user_state.db (flashcard_reviews, quiz_outcomes)
   - Labeling: automatic (SM-2 intervals as ground truth)
   - Deliverables:
     * data/ml/ssr_forgetting_curve_train.parquet
     * data/ml/ssr_forgetting_curve_test.parquet
     * scripts/ml/data_collection_ssr.py
   
   **Phase 2: Model Development**
   - Approach: logistic regression (sklearn)
   - Features:
     * time_since_last_review (hours)
     * quiz_score_last_3 (avg)
     * concept_difficulty (from knowledge_graph)
     * session_duration_avg (minutes)
     * time_of_day (hour)
     * day_of_week (0-6)
     * cards_due_count
     * sm2_due_count
     * quiz_failed_recent (bool)
   - Target: retention_probability (0-1)
   - Training script: scripts/ml/train_ssr_forgetting_curve.py
   - Output: models/ssr_forgetting_curve_v1.pkl (< 1MB)
   
   **Phase 3: Evaluation Harness**
   - Primary metric: AUC-ROC ≥ 0.75 (baseline: 0.50 random)
   - Secondary metrics:
     * Precision@5 ≥ 0.80
     * Recall@5 ≥ 0.70
     * Inference latency p95 < 50ms
   - Test set: 20% holdout from Phase 1
   - Script: scripts/ml/eval_ssr_forgetting_curve.py
   - Report: archive/ml_eval/ssr_forgetting_curve_v1_report.md
   
   **Failure Case Plan:**
   - If AUC-ROC < 0.70 → BLOCK: недостаточно данных, собрать ещё 1000+ samples
   - If 0.70 ≤ AUC-ROC < 0.75 → TRY: upgrade to XGBoost, retrain
   - If AUC-ROC ≥ 0.75 → PASS: proceed to integration
   
   **Phase 4: Integration**
   - Module: app/ui/adaptive_plan_card.py
   - Function: _apply_ml_priority_reranking()
   - Fallback: if model fails → use rule-based priority
   - Explainability: show both rule priority + ML adjustment in evidence ledger
   - Monitoring:
     * inference_latency_p95 < 50ms
     * prediction_confidence > 0.6 for 80% of cases
     * fallback_rate < 5%
   
   **Phase 5: A/B Test (optional)**
   - Control: rule-based SSR (current)
   - Treatment: hybrid (rule + ML reranking)
   - Metric: cards_due completion rate
   - Duration: 2 weeks
   - Sample size: 100 users (local A/B via user_state flag)

3. **Scope Type:**
   
   Прочитай doc/team_workflow/po_router_scope_matrix.md
   и определи scope type.
   
   Ожидаемый результат: **Hybrid Intelligence**
   - Baseline: rule-based priority (укрепить тесты)
   - ML layer: reranking based on forgetting curve
   - Fallback: if ML fails → baseline
   - Explainability: evidence ledger показывает оба слоя

4. **Wave Planning:**
   
   Создай wave structure для Level 1:
   
   Wave ID: ssr-ai-vision-wave-1-foundation
   Theme: "Hybrid Intelligence Foundation"
   
   Packages:
   - ml-ssr-baseline-hardening (укрепить rule-based, добавить тесты)
   - ml-ssr-eval-harness (evaluation infrastructure)
   - ml-ssr-forgetting-curve-v1 (Level 1 implementation)
   
   Entry condition: US-20.1–20.12 closed (SSR v2.0 baseline)
   Exit condition: AUC-ROC ≥ 0.75, cards_due completion ≥ 75%

5. **Registry Update:**
   
   Запиши в doc/backlog_registry.yaml:
   
   ```yaml
   - package_id: ml-ssr-baseline-hardening
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: M
     priority: P0
     description: "Укрепить rule-based SSR: comprehensive tests, edge cases, monitoring"
     deliverables:
       - tests/test_smart_study_router_comprehensive.py (100+ test cases)
       - app/ui/adaptive_plan_card.py (refactor for testability)
       - doc/ssr_baseline_metrics.md (baseline measurements)
     dependencies: []
     
   - package_id: ml-ssr-eval-harness
     status: proposed
     type: ml_package
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: M
     priority: P0
     description: "Evaluation infrastructure для ML features"
     deliverables:
       - tests/eval/test_ssr_ml_reranking.py
       - doc/eval/ssr_ml_reranking_rubric.md
       - archive/ml_eval/ssr_level1/ (test cases, reports)
     dependencies:
       - ml-ssr-baseline-hardening
     
   - package_id: ml-ssr-forgetting-curve-v1
     status: proposed
     type: ml_package
     cjm_stage: "#7"
     primary_us: US-20.1
     owner: TBD
     effort: L
     priority: P0
     description: "Local ML Layer: forgetting curve model + reranking"
     deliverables:
       - data/ml/ssr_forgetting_curve_train.parquet
       - scripts/ml/train_ssr_forgetting_curve.py
       - models/ssr_forgetting_curve_v1.pkl
       - app/ui/adaptive_plan_card.py (_apply_ml_priority_reranking)
       - tests/test_ssr_ml_integration.py
     dependencies:
       - ml-ssr-eval-harness
     evaluation_contract:
       primary_metric: "AUC-ROC ≥ 0.75"
       secondary_metrics:
         - "inference_latency_p95 < 50ms"
         - "model_size < 1MB"
         - "cards_due_completion_rate ≥ 75%"
   ```
   
   Затем:
   ```powershell
   .\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
   ```

Вывод:
1. ✅ Evaluation contract (archive/ml_eval/ssr_level1/evaluation_contract.yaml)
2. ✅ ML package (5 phases, data → model → eval → integration → A/B)
3. ✅ Scope type: Hybrid Intelligence
4. ✅ Wave structure (3 packages)
5. ✅ Registry update + sync

Expected timing: 3-4 недели (1 неделя baseline + 1 неделя eval + 2 недели ML)
```

---

## 🔍 Ключевые решения

### Почему logistic regression, а не deep learning?

| Критерий | Logistic Regression | Deep Learning |
|----------|-------------------|---------------|
| Model size | < 100KB | > 10MB |
| Inference latency | < 10ms | > 100ms |
| Training data | 1000+ samples | 10k+ samples |
| Explainability | Coefficients traceable | Black box |
| Local-first | ✅ Fits in SQLite | ❌ Requires separate runtime |

**Решение:** Logistic regression для Level 1. Deep learning — только если baseline не достигает target.

### Почему hybrid (rule + ML), а не pure ML?

| Аспект | Pure ML | Hybrid (Rule + ML) |
|--------|---------|-------------------|
| Explainability | ❌ Сложно объяснить | ✅ Rule baseline + ML adjustment |
| Fallback | ❌ Нет fallback | ✅ Rule-based fallback |
| Cold start | ❌ Нет данных → плохие рекомендации | ✅ Rule-based работает сразу |
| User trust | ❌ «Почему так?» | ✅ Evidence ledger показывает оба слоя |

**Решение:** Hybrid для сохранения explainability и user agency.

---

## 📊 Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: cards_due completion rate** | 60% | ≥ 75% | % users who complete cards_due recommendation |
| **Secondary: AUC-ROC** | 0.50 (random) | ≥ 0.75 | Model discrimination ability |
| **Secondary: Inference latency p95** | N/A | < 50ms | Time to rerank priorities |
| **Secondary: Model size** | N/A | < 1MB | Disk space |
| **Secondary: Fallback rate** | N/A | < 5% | % times ML fails → rule-based |

---

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Недостаточно training data (< 1000 samples) | High | 1. Generate 500+ synthetic samples using SM-2 formula<br>2. Use rule-based priority until 1000+ real samples<br>3. Retrain weekly, switch to ML when AUC-ROC ≥ 0.70 |
| Model overfits на одного пользователя | Medium | Regularization (L2, C=100) + cross-validation (5-fold) |
| Inference latency > 50ms | High | 1. Model compression (logistic regression < 100KB)<br>2. Caching predictions for 5 minutes<br>3. Fallback to rule-based if latency > 100ms |
| Explainability теряется | High | Evidence ledger показывает rule + ML adjustment + feature coefficients |
| Users не доверяют ML | Medium | 1. A/B test (control = rule-based, treatment = hybrid)<br>2. Opt-out toggle in settings<br>3. Show ML adjustment in evidence ledger |
| AUC-ROC < 0.75 | High | 1. If < 0.70 → BLOCK, collect more data<br>2. If 0.70-0.75 → upgrade to XGBoost<br>3. If ≥ 0.75 → PASS |

---

## 🔗 Related Documents

- [`product_owner_router_ai_vision_enhancement.md`](../archive/product_owner_router_ai_vision_enhancement.md) — Enhancement plan
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (§ Next Level, Уровень 1)
- [`po_router_evaluation_gate.md`](po_router_evaluation_gate.md) — Evaluation contract template
- [`product_owner_plan_ml_package_prompt.md`](product_owner_plan_ml_package_prompt.md) — ML package structure

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Следующий уровень:** [Level 2: LLM-Enhanced Explanation](ssr_ai_vision_level2_prompt.md)
