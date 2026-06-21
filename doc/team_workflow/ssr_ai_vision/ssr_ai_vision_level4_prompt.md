# SSR AI Vision — Level 4: Concept Graph Router
## Copy-Paste Prompt для Product Owner

**Дата:** 2026-05-08  
**Уровень:** 4 из 5  
**Цель:** Маршрутизация на основе knowledge graph (concept dependencies)

---

## 🎯 Что это

**Level 4** интегрирует SSR с knowledge graph для маршрутизации на основе concept dependencies.

**Baseline (текущее):** SSR не знает о связях между концептами
```
Рекомендация: «Изучите "Нейронные сети"»
(Но пользователь не освоил "Линейная алгебра" — prerequisite)
```

**Target (Level 4):** Graph-aware routing
```
Concept A (mastered) ──prerequisite──→ Concept B (weak)
                                          ↓
SSR: «Изучите "Нейронные сети", потому что
вы уже освоили "Линейная алгебра" — это фундамент.
Следующий шаг: "Backpropagation" (зависит от NN).»
```

---

## 📋 Copy-Paste Prompt

```text
Прочитай doc/team_workflow/archive/product_owner_router_ai_vision_enhancement.md
и doc/smart_study_router.md (§ Next Level — AI Vision, Уровень 4)
и создай полный delivery plan для SSR Level 4: Concept Graph Router.

Контекст:
- Текущий SSR: не учитывает concept dependencies
- Текущий KG: app/knowledge_graph.py (граф концептов существует)
- Цель: SSR использует KG для prerequisite-aware routing
- Constraint: graph query < 100ms, local-first

Шаги:

1. **Evaluation Contract (ОБЯЗАТЕЛЬНО ПЕРВЫМ):**
   
   Прочитай doc/team_workflow/po_router_evaluation_gate.md
   и создай evaluation contract.
   
   Параметры:
   - Feature: SSR Level 4 — Concept Graph Router
   - Baseline metric: prerequisite_violation_rate = 25% (SSR рекомендует без учёта prerequisites)
   - Target metric: prerequisite_violation_rate ≤ 5%
   - Secondary metrics:
     * graph_query_latency_p95 < 100ms
     * recommendation_relevance_score ≥ 4.0/5 (human eval)
     * learning_path_coherence ≥ 80% (concepts в правильном порядке)
   
   Test harness:
   - 50 user profiles с разным mastery state
   - 20 concept graphs (разные domains)
   - Metrics: prerequisite violations, relevance, coherence
   - Script: tests/eval/test_ssr_graph_routing.py
   
   Вывод:
   - evaluation_contract.yaml в archive/ml_eval/ssr_level4/
   - Test cases: tests/eval/ssr_graph_routing_scenarios.json

2. **Integration Package Planning:**
   
   Создай standard package (не ML, т.к. graph traversal — детерминированный).
   
   Package ID: kg-ssr-integration-v1
   Type: standard (integration)
   
   Deliverables:
   
   **Phase 1: Design Integration**
   - Design doc: doc/ssr_kg_integration_design.md
   - Вопросы:
     * Как SSR запрашивает KG? (API, direct call)
     * Какие graph queries нужны? (prerequisites, dependents, related)
     * Как обрабатывать циклы в графе?
     * Как fallback если KG недоступен?
   - Deliverables:
     * doc/ssr_kg_integration_design.md
     * API contract: app/knowledge_graph.py (новые методы)
   
   **Phase 2: Implement Concept Routing**
   - Module: app/ui/adaptive_plan_card.py
   - New function: _apply_graph_aware_routing()
   - Algorithm:
     ```python
     def _apply_graph_aware_routing(rec, user_mastery, kg):
         # 1. Get concept from recommendation
         concept = extract_concept_from_rec(rec)
         
         # 2. Check prerequisites
         prerequisites = kg.get_prerequisites(concept)
         unmet_prereqs = [p for p in prerequisites 
                          if user_mastery.get(p) < 0.7]
         
         # 3. If unmet prerequisites → redirect
         if unmet_prereqs:
             weakest_prereq = min(unmet_prereqs, 
                                  key=lambda p: user_mastery.get(p, 0))
             return SmartStudyRecommendation(
                 hint_kind="prerequisite_gap",
                 primary_label_ru=f"Освоить {weakest_prereq}",
                 why_now_ru=f"Это фундамент для {concept}. "
                            f"Вы освоили {concept} на {user_mastery.get(concept, 0):.0%}, "
                            f"но {weakest_prereq} — только {user_mastery.get(weakest_prereq, 0):.0%}.",
                 primary_nav="tutor_prerequisite",
                 ...
             )
         
         # 4. If prerequisites met → suggest next dependent
         dependents = kg.get_dependents(concept)
         next_concept = select_next_by_mastery(dependents, user_mastery)
         
         return rec  # or enhanced rec with next_concept hint
     ```
   - Fallback: if KG query fails → use original rec
   - Tests: tests/test_ssr_graph_routing.py
   
   **Failure Case Plan:**
   - If prerequisite_violation_rate > 15% → BLOCK: KG incomplete, fix graph coverage
   - If 5% < prerequisite_violation_rate ≤ 15% → TRY: improve prerequisite detection algorithm
   - If prerequisite_violation_rate ≤ 5% → PASS: proceed to prerequisite validation
   
   **Phase 3: Prerequisite Validation**
   - Feature: блокировать рекомендации если prerequisites не met
   - UI: показывать prerequisite chain в evidence ledger
   - Example:
     ```
     Рекомендация: «Изучите "Нейронные сети"»
     
     Prerequisite chain:
     ✅ Линейная алгебра (освоено 85%)
     ✅ Производные (освоено 90%)
     ⚠️ Матричное умножение (освоено 60% — рекомендуем повторить)
     ```
   - Deliverables:
     * app/ui/adaptive_plan_card.py (prerequisite validation)
     * app/ui/prerequisite_chain_render.py (UI component)
     * tests/test_prerequisite_validation.py
   
   **Phase 4: E2E Testing**
   - Playwright tests: tests/e2e/ssr_graph_routing.spec.ts
   - Scenarios:
     * User с unmet prerequisites → redirect
     * User с met prerequisites → next concept
     * KG unavailable → fallback to baseline SSR
   - Deliverables:
     * tests/e2e/ssr_graph_routing.spec.ts
     * doc/ssr_graph_routing_e2e.md

3. **Scope Type:**
   
   Ожидаемый результат: **Standard Feature** (integration, не ML)
   - SSR routing: rule-based + graph traversal
   - No ML training
   - Deterministic (graph queries)

4. **Wave Planning:**
   
   Создай wave structure для Level 4:
   
   Wave ID: ssr-ai-vision-wave-4-graph
   Theme: "Graph-Aware Routing"
   
   Packages:
   - kg-ssr-integration-design (design doc + API contract)
   - kg-ssr-concept-routing (implement graph-aware routing)
   - kg-ssr-prerequisite-validation (prerequisite checks + UI)
   
   Entry condition: Level 3 closed (weekly planner) ИЛИ baseline SSR + KG exists
   Exit condition: prerequisite_violation_rate ≤ 5%, graph_query_latency < 100ms

5. **Registry Update:**
   
   Запиши в doc/backlog_registry.yaml:
   
   ```yaml
   - package_id: kg-ssr-integration-design
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.4
     owner: TBD
     effort: S
     priority: P1
     description: "Design integration между SSR и KG"
     deliverables:
       - doc/ssr_kg_integration_design.md
       - app/knowledge_graph.py (API contract: get_prerequisites, get_dependents)
       - tests/test_kg_api.py
     dependencies: []
     
   - package_id: kg-ssr-concept-routing
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.4
     owner: TBD
     effort: M
     priority: P1
     description: "Graph-aware routing: redirect если unmet prerequisites"
     deliverables:
       - app/ui/adaptive_plan_card.py (_apply_graph_aware_routing)
       - tests/test_ssr_graph_routing.py
       - tests/eval/test_ssr_graph_routing.py (evaluation)
     dependencies:
       - kg-ssr-integration-design
     evaluation_contract:
       primary_metric: "prerequisite_violation_rate ≤ 5%"
       secondary_metrics:
         - "graph_query_latency_p95 < 100ms"
         - "recommendation_relevance ≥ 4.0/5"
     
   - package_id: kg-ssr-prerequisite-validation
     status: proposed
     type: standard
     cjm_stage: "#7"
     primary_us: US-20.4
     owner: TBD
     effort: M
     priority: P1
     description: "Prerequisite validation + UI для prerequisite chain"
     deliverables:
       - app/ui/prerequisite_chain_render.py
       - tests/test_prerequisite_validation.py
       - tests/e2e/ssr_graph_routing.spec.ts
     dependencies:
       - kg-ssr-concept-routing
   ```
   
   Затем:
   ```powershell
   .\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
   ```

Вывод:
1. ✅ Evaluation contract (50 user profiles, 20 concept graphs)
2. ✅ Integration package (design → routing → validation)
3. ✅ Scope type: Standard Feature
4. ✅ Wave structure (3 packages)
5. ✅ Registry update + sync

Expected timing: 3-4 недели (1 неделя design + 1 неделя routing + 1 неделя validation + 1 неделя testing)
```

---

## 🔍 Ключевые решения

### Почему не ML для graph routing?

| Approach | Pros | Cons |
|----------|------|------|
| **ML (GNN)** | Может учиться на user patterns | Сложный, требует много данных, black box |
| **Rule-based graph traversal** | Детерминированный, explainable | Не адаптируется к user |

**Решение:** Rule-based для Level 4. ML (GNN) — только если нужна персонализация graph weights.

### Как обрабатывать циклы в графе?

```python
# Пример: A → B → C → A (цикл)
def get_prerequisites_safe(concept, kg, visited=None):
    if visited is None:
        visited = set()
    
    if concept in visited:
        return []  # Цикл detected → stop
    
    visited.add(concept)
    prereqs = kg.get_prerequisites(concept)
    
    return prereqs
```

**Решение:** Track visited nodes, stop при цикле.

---

## 📊 Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Primary: prerequisite_violation_rate** | 25% | ≤ 5% (-20% target) | % recommendations без met prerequisites |
| **Secondary: graph_query_latency_p95** | N/A | < 100ms (target) | Time to query KG |
| **Secondary: recommendation_relevance** | 3.5/5 | ≥ 4.0/5 (target) | Human eval (50 scenarios) |
| **Secondary: learning_path_coherence** | 60% | ≥ 80% (target) | % concepts в правильном порядке |

**IMPORTANT:** Эти метрики — **targets**, не гарантированные результаты. Level 4 требует evaluation contract и может не достичь target с первой попытки.

---

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| KG incomplete (missing prerequisites) | High | 1. Fallback to baseline SSR<br>2. Monitor graph_coverage ≥ 80% (concepts with prerequisites)<br>3. Manual review + graph expansion |
| Graph query > 100ms | Medium | 1. Caching prerequisite chains for 1 hour<br>2. Index optimization (prerequisite lookup)<br>3. Fallback to baseline if latency > 200ms |
| Циклы в графе | Medium | 1. Cycle detection algorithm (visited set)<br>2. Max depth limit = 5 levels<br>3. Log cycles for manual review |
| Users не понимают prerequisite chain | Medium | 1. UI explanation + visual graph<br>2. A/B test: with/without prerequisite chain<br>3. User feedback survey (clarity ≥ 4.0/5) |
| KG unavailable (service down) | High | 1. Fallback to baseline SSR<br>2. Monitor kg_availability ≥ 99%<br>3. Graceful degradation (no prerequisite checks) |

---

## 🔗 Related Documents

- [`product_owner_router_ai_vision_enhancement.md`](../archive/product_owner_router_ai_vision_enhancement.md) — Enhancement plan
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision (§ Next Level, Уровень 4)
- [`ssr_ai_vision_level3_prompt.md`](ssr_ai_vision_level3_prompt.md) — Level 3 (prerequisite)

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Предыдущий уровень:** [Level 3: Proactive Study Planner](ssr_ai_vision_level3_prompt.md)  
**Следующий уровень:** [Level 5: Misroute Feedback Loop](ssr_ai_vision_level5_prompt.md)
