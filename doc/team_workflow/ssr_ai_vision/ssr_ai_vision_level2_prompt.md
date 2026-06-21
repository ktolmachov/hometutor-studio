# SSR AI Vision — Level 2: LLM-Enhanced Explanation
## Copy-Paste Prompt для Product Owner

**Дата:** 2026-05-08  
**Уровень:** 2 из 5  
**Цель:** Персонализированные объяснения SSR-рекомендаций через LLM

---

## 🎯 Что это

**Level 2** заменяет шаблонные `why_now_ru` на персонализированные объяснения, сгенерированные LLM на основе learning history пользователя.

**Baseline (текущее):** Шаблонный текст
```
«Локальная очередь SM-2: к повтору 5 карточек — интервал уже наступил.»
```

**Target (Level 2):** Персонализированное объяснение
```
«Вчера вы изучали "Деревья решений" и ответили на 3 из 5 вопросов верно.
Сегодня — идеальный момент для повтора: по вашему паттерну забывания,
через 24 часа вы помните ~70% материала, а через 48 — только ~40%.
5 карточек по этой теме укрепят память до следующего интервала.»
```

**CRITICAL Constraint:** LLM-вызов **только для explanation**, не для routing decision. Decision остаётся детерминированным (rule-based или Level 1 ML).

---

## 📋 Copy-Paste Prompt

```text
Прочитай doc/team_workflow/archive/product_owner_router_ai_vision_enhancement.md
и doc/smart_study_router.md (§ Next Level — AI Vision, Уровень 2)
и создай полный delivery plan для SSR Level 2: LLM-Enhanced Explanation.

Контекст:
- Текущий SSR: шаблонные why_now_ru (clarity score 3.2/5 по user feedback)
- Цель: персонализированные объяснения через LLM
- Constraint: LLM только для explanation, не для routing; latency < 2s; token budget < 500

Шаги:

1. **Evaluation Contract (ОБЯЗАТЕЛЬНО ПЕРВЫМ):**
   
   Прочитай doc/team_workflow/po_router_evaluation_gate.md
   и создай evaluation contract.
   
   Параметры:
   - Feature: SSR Level 2 — LLM-Enhanced Explanation
   - Baseline metric: explanation_clarity_score = 3.2/5 (текущий шаблонный)
   - Target metric: explanation_clarity_score ≥ 4.0/5
   - Secondary metrics:
     * llm_latency_p95 < 2s
     * token_cost < 500 tokens per explanation
     * explanation_length < 150 words (readability)
     * no regression: SSR routing accuracy сохранена
   
   Test harness:
   - 50 SSR scenarios × 3 human raters
   - Rubric: clarity, personalization, pedagogical value, accuracy
   - Script: tests/eval/test_ssr_llm_explanation.py
   - Test cases: tests/eval/ssr_explanation_test_cases.json
   
   Вывод:
   - evaluation_contract.yaml в archive/ml_eval/ssr_level2/
   - Rubric: doc/eval/ssr_explanation_rubric.md
   - Test cases: 50 scenarios с ground truth explanations

2. **Prompt Engineering Package:**
   
   Создай standard package (не ML package, т.к. нет model training).
   
   Package ID: llm-ssr-explanation-v1
   Type: standard (prompt engineering)
   
   Deliverables:
   
   **Phase 1: Prompt Design**
   - Baseline prompt template:
     ```
     You are explaining why a specific learning action is recommended right now.
     
     User context:
     - Last session: {last_session_topic} ({last_session_date})
     - Quiz performance: {quiz_score_last_3} avg
     - Cards due: {cards_due_count}
     - Weak concepts: {weak_concepts_list}
     
     Recommendation: {primary_label_ru}
     Reason (template): {why_now_template}
     
     Generate a personalized explanation (max 150 words) that:
     1. References user's recent activity
     2. Explains pedagogical timing (why now, not later)
     3. Quantifies expected benefit (retention %, time saved)
     4. Maintains encouraging tone
     
     Output in Russian.
     ```
   
   - Prompt iterations: 3-5 versions
   - A/B test prompts on test set
   - Select best by clarity score
   
   **Phase 2: Integration**
   - Module: app/ui/adaptive_plan_card.py
   - Function: _generate_llm_explanation()
   - Fallback: if LLM fails or latency > 3s → use template
   - Caching: cache explanations for 1 hour (same context → same explanation)
   - Token Budget Guard:
     * If token_cost > 500 → compress prompt (remove examples)
     * If token_cost > 700 → fallback to template
     * Monitor: token_cost_p95 < 500 (95% of calls)
   - Monitoring:
     * llm_call_success_rate > 95%
     * llm_latency_p95 < 2s
     * fallback_rate < 10%
   
   **Phase 3: Evaluation**
   - Run test harness (50 scenarios × 3 raters)
   - Measure clarity score, latency, token cost
   - Compare vs baseline (template)
   - Report: archive/ml_eval/ssr_level2/llm_explanation_v1_report.md
   
   **Phase 4: A/B Test (optional)**
   - Control: template-based explanation
   - Treatment: LLM-enhanced explanation
   - Metric: user engagement (click-through rate on recommendation)
   - Duration: 1 week
   - Sample size: 50 users

3. **Scope Type:**
   
   Прочитай doc/team_workflow/po_router_scope_matrix.md
   и определи scope type.
   
   Ожидаемый результат: **Standard Feature** (не Hybrid Intelligence, т.к. LLM не влияет на routing)
   - Routing: rule-based или Level 1 ML (без изменений)
   - Explanation: LLM-enhanced
   - Fallback: template-based

4. **Wave Planning:**
   
   Создай wave structure для Level 2:
   
   Wave ID: ssr-ai-vision-wave-2-explainability
   Theme: "LLM-Enhanced Explainability"
   
   Packages:
   - llm-ssr-explanation-eval (evaluation contract + test harness)
   - llm-ssr-prompt-engineering (prompt design + iteration)
   - llm-ssr-explanation-integration (integration + fallback + monitoring)
   
   Entry condition: Level 1 closed (ML reranking работает) ИЛИ baseline SSR (если Level 1 skipped)
   Exit condition: clarity_score ≥ 4.0, latency < 2s, no routing regression

5. **Registry Update:**
   
   Запиши в doc/backlog_registry.yaml:
   
   ```yaml
   - package_id: llm-ssr-explanation-eval
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.7
     owner: TBD
     effort: S
     priority: P1
     description: "Evaluation contract для LLM explanations"
     deliverables:
       - archive/ml_eval/ssr_level2/evaluation_contract.yaml
       - doc/eval/ssr_explanation_rubric.md
       - tests/eval/test_ssr_llm_explanation.py
       - tests/eval/ssr_explanation_test_cases.json (50 scenarios)
     dependencies: []
     
   - package_id: llm-ssr-prompt-engineering
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.7
     owner: TBD
     effort: M
     priority: P1
     description: "Prompt design + iteration для personalized explanations"
     deliverables:
       - app/prompts.py (SSR explanation prompts)
       - doc/ssr_prompt_iterations.md (3-5 versions + A/B results)
       - scripts/eval_ssr_prompts.py (prompt evaluation script)
     dependencies:
       - llm-ssr-explanation-eval
     
   - package_id: llm-ssr-explanation-integration
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.7
     owner: TBD
     effort: M
     priority: P1
     description: "Integration + fallback + monitoring"
     deliverables:
       - app/ui/adaptive_plan_card.py (_generate_llm_explanation)
       - tests/test_ssr_llm_integration.py
       - doc/ssr_llm_monitoring.md (metrics, alerts)
     dependencies:
       - llm-ssr-prompt-engineering
     evaluation_contract:
       primary_metric: "clarity_score ≥ 4.0/5"
       secondary_metrics:
         - "llm_latency_p95 < 2s"
         - "token_cost < 500 per explanation"
         - "fallback_rate < 10%"
   ```
   
   Затем:
   ```powershell
   .\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
   ```

Вывод:
1. ✅ Evaluation contract (clarity rubric, 50 test cases)
2. ✅ Prompt engineering package (3-5 iterations)
3. ✅ Integration package (fallback, caching, monitoring)
4. ✅ Wave structure (3 packages)
5. ✅ Registry update + sync

Expected timing: 2-3 недели (1 неделя eval + 1 неделя prompts + 1 неделя integration)
```

---

## 🔍 Ключевые решения

### Почему LLM только для explanation, а не для routing?

| Аспект | LLM Routing | LLM Explanation Only |
|--------|-------------|---------------------|
| Explainability | ❌ «Почему LLM выбрал это?» | ✅ Rule/ML routing + LLM объясняет |
| Latency | ❌ Блокирует UI (2-5s) | ✅ Async, не блокирует |
| Determinism | ❌ Разные результаты | ✅ Routing детерминирован |
| Fallback | ❌ Сложно откатиться | ✅ Template fallback |
| Cost | ❌ Каждый SSR call = LLM call | ✅ Только explanation (cacheable) |

**Решение:** LLM только для explanation. Routing остаётся rule-based/ML.

### Почему caching на 1 час?

- **Без caching:** Каждый SSR render = LLM call → latency + cost
- **С caching:** Same context → same explanation (1 час)
- **Invalidation:** Context change (new quiz, new cards) → cache miss → new LLM call

**Решение:** 1-hour cache для снижения latency и cost.

---

## 📊 Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: clarity_score** | 3.2/5 | ≥ 4.0/5 | Human eval (3 raters × 50 scenarios) |
| **Secondary: llm_latency_p95** | N/A | < 2s | Time to generate explanation |
| **Secondary: token_cost** | N/A | < 500 | Tokens per explanation |
| **Secondary: fallback_rate** | N/A | < 10% | % times LLM fails → template |
| **Secondary: engagement** | Baseline CTR | +10% CTR | Click-through rate on recommendation |

---

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM latency > 2s | High | 1. Async generation + 1-hour caching<br>2. Template fallback if latency > 3s<br>3. Monitor llm_latency_p95 < 2s |
| Token cost > 500 | Medium | 1. Compress prompt if cost > 500 (remove examples)<br>2. Fallback to template if cost > 700<br>3. Monitor token_cost_p95 < 500 |
| LLM hallucination (wrong facts) | High | 1. Strict prompt constraints (no speculation)<br>2. Validation: check facts against user_state<br>3. Fallback to template if validation fails |
| Users prefer template (simpler) | Medium | 1. A/B test (control = template, treatment = LLM)<br>2. Opt-out toggle in settings<br>3. Measure engagement (CTR on recommendation) |
| Routing regression | High | Evaluation contract: no routing changes, only explanation |

---

## 🔗 Related Documents

- [`product_owner_router_ai_vision_enhancement.md`](../archive/product_owner_router_ai_vision_enhancement.md) — Enhancement plan
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (§ Next Level, Уровень 2)
- [`po_router_evaluation_gate.md`](po_router_evaluation_gate.md) — Evaluation contract template
- [`ssr_ai_vision_level1_prompt.md`](ssr_ai_vision_level1_prompt.md) — Level 1 (prerequisite)

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Предыдущий уровень:** [Level 1: Local ML Layer](ssr_ai_vision_level1_prompt.md)  
**Следующий уровень:** [Level 3: Proactive Study Planner](ssr_ai_vision_level3_prompt.md)
