# SSR AI Vision — Evaluation Rubrics

**Дата:** 2026-05-08  
**Версия:** 1.0  
**Цель:** Готовые rubrics для human evaluation каждого уровня

---

## 📋 Содержание

- [Level 1: ML Reranking Rubric](#level-1-ml-reranking-rubric)
- [Level 2: LLM Explanation Rubric](#level-2-llm-explanation-rubric)
- [Level 3: Weekly Planner Rubric](#level-3-weekly-planner-rubric)
- [Level 4: Graph Routing Rubric](#level-4-graph-routing-rubric)
- [Level 5: Feedback Loop Rubric](#level-5-feedback-loop-rubric)

---

## Level 1: ML Reranking Rubric

### Evaluation Criteria

| Criterion | Weight | 1 (Poor) | 2 (Fair) | 3 (Good) | 4 (Very Good) | 5 (Excellent) |
|-----------|--------|----------|----------|----------|---------------|---------------|
| **Accuracy** | 40% | Recommendations часто неправильные | Recommendations иногда неправильные | Recommendations обычно правильные | Recommendations почти всегда правильные | Recommendations всегда правильные |
| **Personalization** | 30% | Не учитывает user patterns | Слабо учитывает user patterns | Учитывает основные user patterns | Хорошо учитывает user patterns | Отлично учитывает user patterns |
| **Explainability** | 20% | ML adjustment непонятен | ML adjustment слабо объяснён | ML adjustment объяснён | ML adjustment хорошо объяснён | ML adjustment отлично объяснён |
| **Performance** | 10% | Latency > 100ms | Latency 50-100ms | Latency 20-50ms | Latency 10-20ms | Latency < 10ms |

### Scoring Formula

```
Total Score = (Accuracy × 0.4) + (Personalization × 0.3) + (Explainability × 0.2) + (Performance × 0.1)
```

### Pass Criteria

- **Total Score ≥ 3.5/5** — PASS
- **Total Score < 3.5/5** — FAIL (iterate)

### Test Scenarios (50 cases)

| Scenario | Description | Expected Behavior |
|----------|-------------|-------------------|
| **S1** | User забывает быстро (S=12) | ML снижает приоритет long-interval cards |
| **S2** | User забывает медленно (S=48) | ML повышает приоритет long-interval cards |
| **S3** | User активен утром | ML повышает приоритет morning recommendations |
| **S4** | User активен вечером | ML повышает приоритет evening recommendations |
| **S5** | User провалил quiz 3 раза | ML повышает приоритет quiz_recovery |
| ... | ... | ... |

### Evaluation Template

```markdown
# Level 1 Evaluation — Test Case #1

**Scenario:** User забывает быстро (S=12)

**Input:**
- time_since_last_review: 24 hours
- quiz_score_last_3: 0.6
- cards_due_count: 5

**Expected:** ML adjustment < 0.8 (снизить приоритет)

**Actual:** ML adjustment = 0.65

**Scores:**
- Accuracy: 5/5 (correct adjustment)
- Personalization: 5/5 (учитывает forgetting curve)
- Explainability: 4/5 (показано в evidence ledger)
- Performance: 5/5 (latency 8ms)

**Total:** (5×0.4) + (5×0.3) + (4×0.2) + (5×0.1) = 4.8/5 ✅ PASS
```

---

## Level 2: LLM Explanation Rubric

### Evaluation Criteria

| Criterion | Weight | 1 (Poor) | 2 (Fair) | 3 (Good) | 4 (Very Good) | 5 (Excellent) |
|-----------|--------|----------|----------|----------|---------------|---------------|
| **Clarity** | 35% | Непонятно | Слабо понятно | Понятно | Очень понятно | Кристально понятно |
| **Personalization** | 30% | Generic template | Слабая персонализация | Умеренная персонализация | Хорошая персонализация | Отличная персонализация |
| **Pedagogical Value** | 25% | Нет педагогической ценности | Слабая ценность | Умеренная ценность | Хорошая ценность | Высокая ценность |
| **Accuracy** | 10% | Фактические ошибки | Неточности | Точно | Очень точно | Абсолютно точно |

### Scoring Formula

```
Total Score = (Clarity × 0.35) + (Personalization × 0.30) + (Pedagogical Value × 0.25) + (Accuracy × 0.10)
```

### Pass Criteria

- **Total Score ≥ 4.0/5** — PASS
- **Total Score < 4.0/5** — FAIL (iterate prompt)

### Test Scenarios (50 cases × 3 raters = 150 evaluations)

| Scenario | Template Explanation | LLM Explanation | Expected Improvement |
|----------|---------------------|-----------------|---------------------|
| **S1** | «Локальная очередь SM-2: к повтору 5 карточек» | «Вчера вы изучали "Деревья решений" и ответили на 3 из 5 вопросов верно. Сегодня — идеальный момент для повтора...» | Clarity +1, Personalization +2 |
| **S2** | «Разобрать слабое место» | «Вы провалили quiz по "Линейная алгебра" 2 раза. Давайте разберём ошибки до следующей проверки...» | Pedagogical Value +2 |
| ... | ... | ... | ... |

### Evaluation Template

```markdown
# Level 2 Evaluation — Test Case #1, Rater #1

**Scenario:** cards_due recommendation

**Template Explanation:**
«Локальная очередь SM-2: к повтору 5 карточек — интервал уже наступил.»

**LLM Explanation:**
«Вчера вы изучали "Деревья решений" и ответили на 3 из 5 вопросов верно.
Сегодня — идеальный момент для повтора: по вашему паттерну забывания,
через 24 часа вы помните ~70% материала, а через 48 — только ~40%.
5 карточек по этой теме укрепят память до следующего интервала.»

**Scores:**
- Clarity: 5/5 (кристально понятно)
- Personalization: 5/5 (ссылается на вчерашнюю сессию)
- Pedagogical Value: 5/5 (объясняет forgetting curve)
- Accuracy: 5/5 (факты верны)

**Total:** (5×0.35) + (5×0.30) + (5×0.25) + (5×0.10) = 5.0/5 ✅ PASS
```

---

## Level 3: Weekly Planner Rubric

### Evaluation Criteria

| Criterion | Weight | 1 (Poor) | 2 (Fair) | 3 (Good) | 4 (Very Good) | 5 (Excellent) |
|-----------|--------|----------|----------|----------|---------------|---------------|
| **Completability** | 40% | План невыполним | План сложно выполнить | План выполним | План легко выполнить | План идеально выполним |
| **Balance** | 30% | Нагрузка неравномерная | Нагрузка слабо сбалансирована | Нагрузка сбалансирована | Нагрузка хорошо сбалансирована | Нагрузка идеально сбалансирована |
| **Relevance** | 20% | Items не релевантны | Items слабо релевантны | Items релевантны | Items очень релевантны | Items идеально релевантны |
| **Flexibility** | 10% | План жёсткий | План слабо гибкий | План гибкий | План очень гибкий | План идеально гибкий |

### Scoring Formula

```
Total Score = (Completability × 0.4) + (Balance × 0.3) + (Relevance × 0.2) + (Flexibility × 0.1)
```

### Pass Criteria

- **Total Score ≥ 3.5/5** — PASS
- **Plan Completion Rate ≥ 55%** — PASS (measured over 2 weeks)

### Test Scenarios (30 user profiles × 4 weeks = 120 plans)

| User Profile | Characteristics | Expected Plan |
|--------------|-----------------|---------------|
| **P1** | Busy (30 min/day) | 3-5 items/day, short sessions |
| **P2** | Relaxed (60 min/day) | 8-10 items/day, longer sessions |
| **P3** | Weekend warrior | 2 items weekday, 15 items weekend |
| **P4** | Morning person | Heavy load Mon-Wed morning |
| **P5** | Evening person | Heavy load Thu-Fri evening |
| ... | ... | ... |

### Evaluation Template

```markdown
# Level 3 Evaluation — User Profile #1

**Profile:** Busy (30 min/day available)

**Generated Plan:**
- Monday: 3 items (15 min)
- Wednesday: 4 items (20 min)
- Friday: 3 items (15 min)
- Total: 10 items, 50 min/week

**Scores:**
- Completability: 5/5 (fits 30 min/day constraint)
- Balance: 4/5 (хорошо распределено по дням)
- Relevance: 5/5 (все items актуальны)
- Flexibility: 4/5 (можно сдвинуть дни)

**Total:** (5×0.4) + (4×0.3) + (5×0.2) + (4×0.1) = 4.6/5 ✅ PASS

**Actual Completion (2 weeks):** 9/10 items = 90% ✅ PASS
```

---

## Level 4: Graph Routing Rubric

### Evaluation Criteria

| Criterion | Weight | 1 (Poor) | 2 (Fair) | 3 (Good) | 4 (Very Good) | 5 (Excellent) |
|-----------|--------|----------|----------|----------|---------------|---------------|
| **Prerequisite Awareness** | 50% | Игнорирует prerequisites | Слабо учитывает prerequisites | Учитывает prerequisites | Хорошо учитывает prerequisites | Идеально учитывает prerequisites |
| **Routing Accuracy** | 30% | Recommendations неправильные | Recommendations слабо правильные | Recommendations правильные | Recommendations очень правильные | Recommendations идеально правильные |
| **Explainability** | 15% | Prerequisite chain непонятен | Prerequisite chain слабо понятен | Prerequisite chain понятен | Prerequisite chain очень понятен | Prerequisite chain идеально понятен |
| **Performance** | 5% | Graph query > 200ms | Graph query 100-200ms | Graph query 50-100ms | Graph query 20-50ms | Graph query < 20ms |

### Scoring Formula

```
Total Score = (Prerequisite Awareness × 0.5) + (Routing Accuracy × 0.3) + (Explainability × 0.15) + (Performance × 0.05)
```

### Pass Criteria

- **Total Score ≥ 3.5/5** — PASS
- **Prerequisite Violation Rate ≤ 5%** — PASS

### Test Scenarios (50 user profiles × 20 concept graphs = 1000 cases)

| Scenario | User Mastery | Concept Graph | Expected Routing |
|----------|--------------|---------------|------------------|
| **S1** | A=0.9, B=0.3 | A→B | Recommend B (prerequisite met) |
| **S2** | A=0.3, B=0.9 | A→B | Recommend A (prerequisite unmet) |
| **S3** | A=0.9, B=0.9, C=0.3 | A→B→C | Recommend C (prerequisites met) |
| **S4** | A=0.3, B=0.3, C=0.9 | A→B→C | Recommend A (weakest prerequisite) |
| ... | ... | ... | ... |

### Evaluation Template

```markdown
# Level 4 Evaluation — Test Case #1

**Scenario:** User mastery A=0.3, B=0.9, Graph: A→B

**Expected:** Recommend A (prerequisite unmet)

**Actual:** Recommended A

**Prerequisite Chain Shown:**
```
⚠️ Линейная алгебра (освоено 30% — рекомендуем повторить)
✅ Нейронные сети (освоено 90%)
```

**Scores:**
- Prerequisite Awareness: 5/5 (correct redirect)
- Routing Accuracy: 5/5 (recommended A)
- Explainability: 5/5 (chain показан)
- Performance: 5/5 (graph query 15ms)

**Total:** (5×0.5) + (5×0.3) + (5×0.15) + (5×0.05) = 5.0/5 ✅ PASS
```

---

## Level 5: Feedback Loop Rubric

### Evaluation Criteria

| Criterion | Weight | 1 (Poor) | 2 (Fair) | 3 (Good) | 4 (Very Good) | 5 (Excellent) |
|-----------|--------|----------|----------|----------|---------------|---------------|
| **Adaptation Accuracy** | 40% | Policy не адаптируется | Policy слабо адаптируется | Policy адаптируется | Policy хорошо адаптируется | Policy идеально адаптируется |
| **User Satisfaction** | 30% | User недоволен | User слабо доволен | User доволен | User очень доволен | User в восторге |
| **Explainability** | 20% | Adjustments непонятны | Adjustments слабо понятны | Adjustments понятны | Adjustments очень понятны | Adjustments идеально понятны |
| **Stability** | 10% | Policy нестабильна | Policy слабо стабильна | Policy стабильна | Policy очень стабильна | Policy идеально стабильна |

### Scoring Formula

```
Total Score = (Adaptation Accuracy × 0.4) + (User Satisfaction × 0.3) + (Explainability × 0.2) + (Stability × 0.1)
```

### Pass Criteria

- **Total Score ≥ 4.0/5** — PASS
- **Recommendation Acceptance Rate ≥ 85%** — PASS
- **User Satisfaction Score ≥ 4.2/5** — PASS (post-feedback survey)

### Test Scenarios (50 user profiles × 100 recommendations = 5000 feedbacks)

| Scenario | Feedback Pattern | Expected Adaptation |
|----------|------------------|---------------------|
| **S1** | User отклоняет cards_due 3 раза | Снизить приоритет cards_due для этого user |
| **S2** | User принимает quiz_recovery 5 раз | Повысить приоритет quiz_recovery |
| **S3** | User откладывает sm2_due утром | Снизить приоритет sm2_due утром |
| **S4** | User принимает tutor_resume вечером | Повысить приоритет tutor_resume вечером |
| ... | ... | ... |

### Evaluation Template

```markdown
# Level 5 Evaluation — Test Case #1

**Scenario:** User отклоняет cards_due 3 раза подряд

**Feedback History:**
- Day 1: cards_due → rejected
- Day 2: cards_due → rejected
- Day 3: cards_due → rejected

**Expected:** Снизить приоритет cards_due для этого user

**Actual:** Priority weight adjusted from 1.0 → 0.7

**Evidence Ledger Shown:**
«Приоритет flashcards снижен (3 отклонения)»

**Scores:**
- Adaptation Accuracy: 5/5 (correct adjustment)
- User Satisfaction: 5/5 (user доволен адаптацией)
- Explainability: 5/5 (показано в ledger)
- Stability: 4/5 (weight не слишком резко изменился)

**Total:** (5×0.4) + (5×0.3) + (5×0.2) + (4×0.1) = 4.9/5 ✅ PASS

**Post-Feedback Survey:** 4.5/5 ✅ PASS
```

---

## 🔗 Related Documents

- [`ssr_ai_vision_summary.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md) — Complete roadmap
- [`ssr_ai_vision_level1_prompt.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_level1_prompt.md) — Level 1 details
- [`ssr_ai_vision_level2_prompt.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_level2_prompt.md) — Level 2 details
- [`ssr_ai_vision_level3_prompt.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_level3_prompt.md) — Level 3 details
- [`ssr_ai_vision_level4_prompt.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_level4_prompt.md) — Level 4 details
- [`ssr_ai_vision_level5_prompt.md`](../team_workflow/ssr_ai_vision/ssr_ai_vision_level5_prompt.md) — Level 5 details

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Статус:** Production-ready
