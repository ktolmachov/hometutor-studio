# SSR AI Vision — Quick Start Guide (All Levels)

**Дата:** 2026-05-08  
**Цель:** Быстрый старт для каждого уровня (5-10 минут)

---

## 📋 Содержание

- [Level 1: Local ML Layer](#level-1-local-ml-layer-5-минут)
- [Level 2: LLM-Enhanced Explanation](#level-2-llm-enhanced-explanation-10-минут)
- [Level 3: Proactive Study Planner](#level-3-proactive-study-planner-10-минут)
- [Level 4: Concept Graph Router](#level-4-concept-graph-router-5-минут)
- [Level 5: Misroute Feedback Loop](#level-5-misroute-feedback-loop-10-минут)

---

## Level 1: Local ML Layer (5 минут)

### Quick Steps

```powershell
# 1. Собрать данные
.\.venv\Scripts\python.exe scripts/ml/data_collection_ssr.py \
    --output data/ml/ssr_forgetting_curve_train.parquet

# 2. Обучить модель
.\.venv\Scripts\python.exe scripts/ml/train_ssr_forgetting_curve.py \
    --train data/ml/ssr_forgetting_curve_train.parquet \
    --output models/ssr_forgetting_curve_v1.pkl

# 3. Evaluation
.\.venv\Scripts\python.exe scripts/ml/eval_ssr_forgetting_curve.py \
    --model models/ssr_forgetting_curve_v1.pkl \
    --output archive/ml_eval/ssr_forgetting_curve_v1_report.md

# 4. Done! Model автоматически загрузится в SSR
```

### Success Criteria

- ✅ AUC-ROC ≥ 0.75
- ✅ Inference latency < 50ms
- ✅ Model size < 1MB

### Full Guide

[`ssr_level1_quick_start.md`](ssr_level1_quick_start.md)

---

## Level 2: LLM-Enhanced Explanation (10 минут)

### Quick Steps

```powershell
# 1. Создать prompt template
# Открыть app/prompts.py и добавить:

SSR_EXPLANATION_PROMPT = """
You are explaining why a specific learning action is recommended right now.

User context:
- Last session: {last_session_topic} ({last_session_date})
- Quiz performance: {quiz_score_last_3} avg
- Cards due: {cards_due_count}

Recommendation: {primary_label_ru}

Generate a personalized explanation (max 150 words) in Russian.
"""

# 2. Интегрировать в SSR
# Открыть app/ui/adaptive_plan_card.py и добавить:

def _generate_llm_explanation(rec, user_state):
    try:
        prompt = SSR_EXPLANATION_PROMPT.format(
            last_session_topic=user_state.last_session_topic,
            last_session_date=user_state.last_session_date,
            quiz_score_last_3=user_state.quiz_score_avg,
            cards_due_count=len(user_state.flashcards_due),
            primary_label_ru=rec.primary_label_ru
        )
        
        response = llm_client.complete(prompt, max_tokens=300)
        return response.text
    except Exception as e:
        # Fallback to template
        return rec.why_now_ru

# 3. Тестировать
.\.venv\Scripts\python.exe tests/eval/test_ssr_llm_explanation.py

# 4. Done!
```

### Success Criteria

- ✅ Clarity score ≥ 4.0/5 (human eval)
- ✅ LLM latency < 2s
- ✅ Token cost < 500 per explanation

### Full Guide

[`ssr_ai_vision_level2_prompt.md`](ssr_ai_vision_level2_prompt.md)

---

## Level 3: Proactive Study Planner (10 минут)

### Quick Steps

```powershell
# 1. Создать baseline weekly planner
# Открыть app/ui/weekly_plan_card.py и добавить:

def generate_weekly_plan_baseline(user_state):
    # Collect pending items
    cards_due = get_flashcards_due_next_7_days()
    sm2_due = get_sm2_concepts_due_next_7_days()
    weak_concepts = get_weak_concepts()
    
    # Distribute by day
    monday = cards_due[:8] + sm2_due[:2]
    wednesday = cards_due[8:15] + weak_concepts[:1]
    friday = cards_due[15:23]
    
    return WeeklyPlan(
        monday=monday,
        wednesday=wednesday,
        friday=friday,
        daily_time_estimate=45  # minutes
    )

# 2. Render в UI
# Добавить в app/ui/resume_cards.py:

def render_weekly_plan_card(user_state):
    plan = generate_weekly_plan_baseline(user_state)
    
    st.markdown("### 📅 План на неделю")
    st.markdown(f"**Понедельник:** {len(plan.monday)} items")
    st.markdown(f"**Среда:** {len(plan.wednesday)} items")
    st.markdown(f"**Пятница:** {len(plan.friday)} items")
    st.markdown(f"**Время:** ~{plan.daily_time_estimate} мин/день")

# 3. Тестировать
.\.venv\Scripts\python.exe tests/test_weekly_plan_baseline.py

# 4. Done! (ML optimization — optional, см. Full Guide)
```

### Success Criteria

- ✅ Plan completion rate ≥ 55%
- ✅ User override rate < 30%
- ✅ Plan generation latency < 5s

### Full Guide

[`ssr_ai_vision_level3_prompt.md`](ssr_ai_vision_level3_prompt.md)

---

## Level 4: Concept Graph Router (5 минут)

### Quick Steps

```powershell
# 1. Добавить graph queries в knowledge_graph.py

def get_prerequisites(concept: str) -> list[str]:
    """Get prerequisites for a concept."""
    query = """
    SELECT prerequisite_concept
    FROM concept_dependencies
    WHERE concept = ?
    """
    return db.execute(query, (concept,)).fetchall()

def get_dependents(concept: str) -> list[str]:
    """Get concepts that depend on this concept."""
    query = """
    SELECT dependent_concept
    FROM concept_dependencies
    WHERE prerequisite_concept = ?
    """
    return db.execute(query, (concept,)).fetchall()

# 2. Интегрировать в SSR
# Открыть app/ui/adaptive_plan_card.py и добавить:

def _apply_graph_aware_routing(rec, user_state, kg):
    concept = extract_concept_from_rec(rec)
    
    # Check prerequisites
    prerequisites = kg.get_prerequisites(concept)
    unmet_prereqs = [p for p in prerequisites 
                     if user_state.mastery.get(p, 0) < 0.7]
    
    if unmet_prereqs:
        # Redirect to weakest prerequisite
        weakest = min(unmet_prereqs, 
                      key=lambda p: user_state.mastery.get(p, 0))
        return SmartStudyRecommendation(
            hint_kind="prerequisite_gap",
            primary_label_ru=f"Освоить {weakest}",
            why_now_ru=f"Это фундамент для {concept}",
            ...
        )
    
    return rec  # Prerequisites met

# 3. Тестировать
.\.venv\Scripts\python.exe tests/test_ssr_graph_routing.py

# 4. Done!
```

### Success Criteria

- ✅ Prerequisite violation rate ≤ 5%
- ✅ Graph query latency < 100ms
- ✅ Recommendation relevance ≥ 4.0/5

### Full Guide

[`ssr_ai_vision_level4_prompt.md`](ssr_ai_vision_level4_prompt.md)

---

## Level 5: Misroute Feedback Loop (10 минут)

### Quick Steps

```powershell
# 1. Добавить feedback UI
# Открыть app/ui/adaptive_plan_card.py и добавить:

def render_ssr_card_with_feedback(rec, user_state):
    # Render recommendation
    st.markdown(f"### {rec.primary_label_ru}")
    st.markdown(rec.why_now_ru)
    
    # Feedback buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("👍 Полезно"):
            save_ssr_feedback(rec, "accepted", user_state)
    with col2:
        if st.button("👎 Не полезно"):
            save_ssr_feedback(rec, "rejected", user_state)
    with col3:
        if st.button("⏰ Не сейчас"):
            save_ssr_feedback(rec, "deferred", user_state)

# 2. Сохранить feedback в DB
# Добавить в app/user_state.py:

def save_ssr_feedback(rec, action, user_state):
    query = """
    INSERT INTO ssr_feedback 
    (recommendation_id, hint_kind, user_action, timestamp, context)
    VALUES (?, ?, ?, ?, ?)
    """
    db.execute(query, (
        rec.id,
        rec.hint_kind,
        action,
        datetime.now(),
        json.dumps(user_state.to_dict())
    ))

# 3. Обучить policy model (offline, каждую ночь)
.\.venv\Scripts\python.exe scripts/ml/train_ssr_policy_learner.py \
    --feedback data/user_state.db \
    --output models/ssr_policy_learner_v1.pkl

# 4. Интегрировать adaptive weights
# См. Full Guide для деталей

# 5. Done!
```

### Success Criteria

- ✅ Recommendation acceptance rate ≥ 85%
- ✅ Policy adaptation accuracy ≥ 75%
- ✅ User satisfaction score ≥ 4.2/5

### Full Guide

[`ssr_ai_vision_level5_prompt.md`](ssr_ai_vision_level5_prompt.md)

---

## 🎯 Recommended Order

### Sequential (Safest)

```
1. Level 1 (5 min) → Test → Deploy
2. Level 2 (10 min) → Test → Deploy
3. Level 3 (10 min) → Test → Deploy
4. Level 4 (5 min) → Test → Deploy
5. Level 5 (10 min) → Test → Deploy

Total: 40 minutes setup time
```

### MVP-First (Best ROI)

```
1. Level 2 (10 min) → Quick win, high satisfaction
2. Level 1 (5 min) → Personalization
3. Level 5 (10 min) → Close feedback loop
4. Level 3 (10 min) → Proactive planning
5. Level 4 (5 min) → Graph-aware

Total: 40 minutes setup time
```

---

## 🔗 Full Documentation

- [`ssr_ai_vision_summary.md`](ssr_ai_vision_summary.md) — Complete roadmap
- [`ssr_ai_vision_level1_prompt.md`](ssr_ai_vision_level1_prompt.md) — Level 1 details
- [`ssr_ai_vision_level2_prompt.md`](ssr_ai_vision_level2_prompt.md) — Level 2 details
- [`ssr_ai_vision_level3_prompt.md`](ssr_ai_vision_level3_prompt.md) — Level 3 details
- [`ssr_ai_vision_level4_prompt.md`](ssr_ai_vision_level4_prompt.md) — Level 4 details
- [`ssr_ai_vision_level5_prompt.md`](ssr_ai_vision_level5_prompt.md) — Level 5 details

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Total Setup Time:** 40 минут (все 5 уровней)
