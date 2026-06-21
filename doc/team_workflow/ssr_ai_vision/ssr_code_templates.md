# SSR AI Vision — Code Templates & Scaffolding

**Дата:** 2026-05-08  
**Версия:** 1.0  
**Цель:** Готовые code templates для быстрого старта implementation

---

## 📋 Содержание

- [Level 1: ML Model Template](#level-1-ml-model-template)
- [Level 2: LLM Prompt Template](#level-2-llm-prompt-template)
- [Level 3: Weekly Planner Template](#level-3-weekly-planner-template)
- [Level 4: Graph Router Template](#level-4-graph-router-template)
- [Level 5: Feedback Loop Template](#level-5-feedback-loop-template)

---

## Level 1: ML Model Template

### File: `scripts/ml/train_ssr_forgetting_curve.py`

```python
"""
SSR Level 1: Forgetting Curve Model Training
"""

import argparse
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score
import time

def load_data(train_path: str, test_path: str):
    """Load training and test data."""
    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)
    
    # Features
    feature_cols = [
        'time_since_last_review',
        'quiz_score_last_3',
        'concept_difficulty',
        'session_duration_avg',
        'time_of_day',
        'day_of_week',
        'cards_due_count',
        'sm2_due_count',
        'quiz_failed_recent'
    ]
    
    X_train = train_df[feature_cols]
    y_train = train_df['retention_probability']
    
    X_test = test_df[feature_cols]
    y_test = test_df['retention_probability']
    
    return X_train, y_train, X_test, y_test

def train_model(X_train, y_train):
    """Train Logistic Regression model."""
    model = LogisticRegression(
        penalty='l2',
        C=100,
        solver='lbfgs',
        max_iter=1000,
        random_state=42
    )
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
    print(f"CV AUC-ROC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    
    # Train final model
    model.fit(X_train, y_train)
    
    return model

def evaluate_model(model, X_test, y_test):
    """Evaluate model on test set."""
    # Predict probabilities
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    # Metrics
    auc_roc = roc_auc_score(y_test, y_pred_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    
    print(f"Test AUC-ROC: {auc_roc:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")
    
    # Inference latency
    start = time.time()
    for _ in range(100):
        model.predict_proba(X_test[:1])
    latency_ms = (time.time() - start) / 100 * 1000
    print(f"Inference latency: {latency_ms:.1f}ms")
    
    return {
        'auc_roc': auc_roc,
        'precision': precision,
        'recall': recall,
        'latency_ms': latency_ms
    }

def save_model(model, output_path: str):
    """Save model to disk."""
    joblib.dump(model, output_path)
    
    # Check size
    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Model size: {size_mb:.1f} MB")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', required=True, help='Training data path')
    parser.add_argument('--test', required=True, help='Test data path')
    parser.add_argument('--output', required=True, help='Output model path')
    args = parser.parse_args()
    
    # Load data
    X_train, y_train, X_test, y_test = load_data(args.train, args.test)
    
    # Train model
    model = train_model(X_train, y_train)
    
    # Evaluate model
    metrics = evaluate_model(model, X_test, y_test)
    
    # Check pass criteria
    if metrics['auc_roc'] >= 0.75 and metrics['latency_ms'] < 50:
        print("✅ Model meets all targets")
        save_model(model, args.output)
    else:
        print("❌ Model does not meet targets")
        if metrics['auc_roc'] < 0.75:
            print(f"  - AUC-ROC {metrics['auc_roc']:.3f} < 0.75")
        if metrics['latency_ms'] >= 50:
            print(f"  - Latency {metrics['latency_ms']:.1f}ms >= 50ms")

if __name__ == '__main__':
    main()
```

### File: `app/ui/adaptive_plan_card.py` (Integration)

```python
"""
SSR Level 1: ML Reranking Integration
"""

import joblib
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Model path
MODEL_PATH = Path("models/ssr_forgetting_curve_v1.pkl")
_ml_model = None

def _load_ml_model():
    """Load ML model (once at startup)."""
    global _ml_model
    if _ml_model is None and MODEL_PATH.exists():
        try:
            _ml_model = joblib.load(MODEL_PATH)
            logger.info("✅ ML model loaded")
        except Exception as e:
            logger.error(f"❌ Failed to load ML model: {e}")
    return _ml_model

def _extract_features(rec, user_state):
    """Extract features for ML model."""
    from datetime import datetime
    
    # Get last review time
    last_review = user_state.get_last_review_time(rec.concept)
    time_since_last = (datetime.now() - last_review).total_seconds() / 3600  # hours
    
    # Get quiz scores
    quiz_scores = user_state.get_quiz_scores_last_n(rec.concept, n=3)
    quiz_score_avg = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0.5
    
    # Get concept difficulty
    from app.knowledge_graph import get_difficulty
    concept_difficulty = get_difficulty(rec.concept)
    
    # Get session duration
    session_duration_avg = user_state.get_session_duration_avg()
    
    # Get temporal features
    time_of_day = datetime.now().hour
    day_of_week = datetime.now().weekday()
    
    # Get queue counts
    cards_due_count = len(user_state.get_flashcards_due())
    sm2_due_count = len(user_state.get_sm2_concepts_due())
    
    # Get quiz failed recent
    quiz_failed_recent = user_state.has_quiz_failed_recent()
    
    return [
        time_since_last,
        quiz_score_avg,
        concept_difficulty,
        session_duration_avg,
        time_of_day,
        day_of_week,
        cards_due_count,
        sm2_due_count,
        int(quiz_failed_recent)
    ]

def _apply_ml_priority_reranking(rec, user_state):
    """Apply ML reranking to SSR recommendation."""
    import dataclasses
    
    # 1. Get baseline priority
    baseline_priority = _get_baseline_priority(rec.hint_kind)
    
    # 2. Try ML reranking
    model = _load_ml_model()
    if model is None:
        # Fallback: no ML model available
        return rec
    
    try:
        # 3. Extract features
        features = _extract_features(rec, user_state)
        
        # 4. Predict retention probability
        retention_prob = model.predict_proba([features])[0][1]
        
        # 5. Adjust priority
        ml_adjustment = retention_prob
        adjusted_priority = baseline_priority * ml_adjustment
        
        # 6. Explainability: add to evidence ledger
        if ml_adjustment < 0.8:
            rec = dataclasses.replace(
                rec,
                evidence_ledger=rec.evidence_ledger + (
                    f"ML adjustment: retention risk {1-ml_adjustment:.0%} "
                    f"(based on your forgetting curve)",
                )
            )
        
        return rec
    
    except Exception as e:
        # Fallback: ML failed → use baseline
        logger.warning(f"ML reranking failed: {e}")
        return rec
```

---

## Level 2: LLM Prompt Template

### File: `app/prompts.py`

```python
"""
SSR Level 2: LLM-Enhanced Explanation Prompts
"""

SSR_EXPLANATION_PROMPT = """
You are explaining why a specific learning action is recommended right now.

User context:
- Last session: {last_session_topic} ({last_session_date})
- Quiz performance: {quiz_score_last_3} avg (0-1 scale)
- Cards due: {cards_due_count}
- Weak concepts: {weak_concepts_list}

Recommendation: {primary_label_ru}
Reason (template): {why_now_template}

Generate a personalized explanation (max 150 words) that:
1. References user's recent activity (last session, quiz results)
2. Explains pedagogical timing (why now, not later)
3. Quantifies expected benefit (retention %, time saved)
4. Maintains encouraging tone

Output in Russian.
"""

SSR_EXPLANATION_SYSTEM_PROMPT = """
You are a pedagogical assistant explaining learning recommendations.
Your explanations should be:
- Clear and concise (max 150 words)
- Personalized (reference user's history)
- Pedagogically sound (explain timing and benefit)
- Encouraging (positive tone)
"""
```

### File: `app/ui/adaptive_plan_card.py` (Integration)

```python
"""
SSR Level 2: LLM Explanation Integration
"""

from app.prompts import SSR_EXPLANATION_PROMPT, SSR_EXPLANATION_SYSTEM_PROMPT
from app.provider import get_llm_client
import logging

logger = logging.getLogger(__name__)

def _generate_llm_explanation(rec, user_state):
    """Generate LLM-enhanced explanation."""
    try:
        # Format prompt
        prompt = SSR_EXPLANATION_PROMPT.format(
            last_session_topic=user_state.last_session_topic or "—",
            last_session_date=user_state.last_session_date.strftime("%d.%m.%Y") if user_state.last_session_date else "—",
            quiz_score_last_3=f"{user_state.quiz_score_avg:.1f}" if user_state.quiz_score_avg else "—",
            cards_due_count=len(user_state.flashcards_due),
            weak_concepts_list=", ".join(user_state.weak_concepts[:3]) if user_state.weak_concepts else "—",
            primary_label_ru=rec.primary_label_ru,
            why_now_template=rec.why_now_ru
        )
        
        # Call LLM
        llm_client = get_llm_client()
        response = llm_client.complete(
            prompt=prompt,
            system_prompt=SSR_EXPLANATION_SYSTEM_PROMPT,
            max_tokens=300,
            temperature=0.7
        )
        
        explanation = response.text.strip()
        
        # Validate length
        if len(explanation.split()) > 150:
            logger.warning("LLM explanation too long, truncating")
            explanation = " ".join(explanation.split()[:150]) + "..."
        
        return explanation
    
    except Exception as e:
        # Fallback to template
        logger.warning(f"LLM explanation failed: {e}")
        return rec.why_now_ru
```

---

## Level 3: Weekly Planner Template

### File: `app/ui/weekly_plan_card.py`

```python
"""
SSR Level 3: Weekly Planner
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class WeeklyPlan:
    monday: list
    wednesday: list
    friday: list
    daily_time_estimate: int  # minutes

def generate_weekly_plan_baseline(user_state):
    """Generate baseline weekly plan (rule-based)."""
    # 1. Collect all pending items
    cards_due = get_flashcards_due_next_7_days(user_state)
    sm2_due = get_sm2_concepts_due_next_7_days(user_state)
    weak_concepts = get_weak_concepts(user_state)
    plan_blocks = get_adaptive_plan_blocks(user_state)
    
    # 2. Distribute by priority
    # Monday: cards_due (high priority)
    monday = cards_due[:8] + sm2_due[:2]
    
    # Wednesday: cards_due + weak concepts
    wednesday = cards_due[8:15] + weak_concepts[:1]
    
    # Friday: cards_due + plan blocks
    friday = cards_due[15:23] + plan_blocks[:1]
    
    # 3. Estimate time
    total_items = len(monday) + len(wednesday) + len(friday)
    total_time = total_items * 5  # 5 min per item (average)
    daily_time = total_time / 7
    
    return WeeklyPlan(
        monday=monday,
        wednesday=wednesday,
        friday=friday,
        daily_time_estimate=int(daily_time)
    )

def get_flashcards_due_next_7_days(user_state):
    """Get flashcards due in next 7 days."""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    next_week = now + timedelta(days=7)
    
    return [
        card for card in user_state.flashcards
        if card.next_review_date <= next_week
    ]

def get_sm2_concepts_due_next_7_days(user_state):
    """Get SM-2 concepts due in next 7 days."""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    next_week = now + timedelta(days=7)
    
    return [
        concept for concept in user_state.sm2_concepts
        if concept.next_review_date <= next_week
    ]

def get_weak_concepts(user_state):
    """Get weak concepts (mastery < 0.7)."""
    return [
        concept for concept in user_state.concepts
        if concept.mastery < 0.7
    ]

def get_adaptive_plan_blocks(user_state):
    """Get adaptive plan blocks."""
    return user_state.adaptive_plan_blocks or []
```

---

## Level 4: Graph Router Template

### File: `app/knowledge_graph.py` (Extensions)

```python
"""
SSR Level 4: Graph Router Extensions
"""

def get_prerequisites(concept: str) -> list[str]:
    """Get prerequisites for a concept."""
    query = """
    SELECT prerequisite_concept
    FROM concept_dependencies
    WHERE concept = ?
    ORDER BY strength DESC
    """
    with _get_db() as db:
        rows = db.execute(query, (concept,)).fetchall()
        return [row[0] for row in rows]

def get_dependents(concept: str) -> list[str]:
    """Get concepts that depend on this concept."""
    query = """
    SELECT dependent_concept
    FROM concept_dependencies
    WHERE prerequisite_concept = ?
    ORDER BY strength DESC
    """
    with _get_db() as db:
        rows = db.execute(query, (concept,)).fetchall()
        return [row[0] for row in rows]

def get_prerequisite_chain(concept: str, max_depth: int = 3) -> list[tuple[str, float]]:
    """Get full prerequisite chain with mastery levels."""
    chain = []
    visited = set()
    
    def _traverse(c, depth):
        if depth > max_depth or c in visited:
            return
        visited.add(c)
        
        prereqs = get_prerequisites(c)
        for prereq in prereqs:
            mastery = get_concept_mastery(prereq)
            chain.append((prereq, mastery))
            _traverse(prereq, depth + 1)
    
    _traverse(concept, 0)
    return chain
```

### File: `app/ui/adaptive_plan_card.py` (Integration)

```python
"""
SSR Level 4: Graph-Aware Routing Integration
"""

from app.knowledge_graph import get_prerequisites, get_prerequisite_chain

def _apply_graph_aware_routing(rec, user_state, kg):
    """Apply graph-aware routing to SSR recommendation."""
    # 1. Extract concept from recommendation
    concept = _extract_concept_from_rec(rec)
    if not concept:
        return rec  # No concept → skip graph routing
    
    # 2. Get prerequisites
    prerequisites = kg.get_prerequisites(concept)
    if not prerequisites:
        return rec  # No prerequisites → proceed
    
    # 3. Check which prerequisites are unmet
    unmet_prereqs = [
        p for p in prerequisites
        if user_state.get_mastery(p) < 0.7
    ]
    
    if not unmet_prereqs:
        return rec  # All prerequisites met → proceed
    
    # 4. Redirect to weakest prerequisite
    weakest_prereq = min(
        unmet_prereqs,
        key=lambda p: user_state.get_mastery(p)
    )
    
    weakest_mastery = user_state.get_mastery(weakest_prereq)
    concept_mastery = user_state.get_mastery(concept)
    
    return SmartStudyRecommendation(
        hint_kind="prerequisite_gap",
        primary_label_ru=f"Освоить {weakest_prereq}",
        why_now_ru=(
            f"Это фундамент для {concept}. "
            f"Вы освоили {concept} на {concept_mastery:.0%}, "
            f"но {weakest_prereq} — только {weakest_mastery:.0%}."
        ),
        primary_nav="tutor_prerequisite",
        secondaries=(),
        route_pedagogy_ru="Восстановление слабого понятия"
    )
```

---

## Level 5: Feedback Loop Template

### File: `app/user_state.py` (Extensions)

```python
"""
SSR Level 5: Feedback Collection
"""

import json
from datetime import datetime

def save_ssr_feedback(rec, action: str, user_state):
    """Save SSR feedback to database."""
    query = """
    INSERT INTO ssr_feedback 
    (recommendation_id, hint_kind, user_action, timestamp, context)
    VALUES (?, ?, ?, ?, ?)
    """
    
    context = {
        'cards_due_count': len(user_state.flashcards_due),
        'sm2_due_count': len(user_state.sm2_concepts_due),
        'quiz_failed_recent': user_state.has_quiz_failed_recent(),
        'time_of_day': datetime.now().hour,
        'day_of_week': datetime.now().weekday()
    }
    
    with _get_db() as db:
        db.execute(query, (
            rec.id,
            rec.hint_kind,
            action,
            datetime.now(),
            json.dumps(context)
        ))
        db.commit()

def get_ssr_feedback_history(user_id: str, limit: int = 100):
    """Get SSR feedback history for a user."""
    query = """
    SELECT recommendation_id, hint_kind, user_action, timestamp, context
    FROM ssr_feedback
    WHERE user_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """
    
    with _get_db() as db:
        rows = db.execute(query, (user_id, limit)).fetchall()
        return [
            {
                'recommendation_id': row[0],
                'hint_kind': row[1],
                'user_action': row[2],
                'timestamp': row[3],
                'context': json.loads(row[4])
            }
            for row in rows
        ]
```

### File: `app/ui/adaptive_plan_card.py` (Integration)

```python
"""
SSR Level 5: Feedback UI Integration
"""

import streamlit as st
from app.user_state import save_ssr_feedback

def render_ssr_card_with_feedback(rec, user_state):
    """Render SSR card with feedback buttons."""
    # Render recommendation
    st.markdown(f"### {rec.primary_label_ru}")
    st.markdown(rec.why_now_ru)
    
    # Feedback buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👍 Полезно", key=f"accept_{rec.id}"):
            save_ssr_feedback(rec, "accepted", user_state)
            st.success("Спасибо за feedback!")
            st.rerun()
    
    with col2:
        if st.button("👎 Не полезно", key=f"reject_{rec.id}"):
            save_ssr_feedback(rec, "rejected", user_state)
            st.info("Мы учтём ваш feedback")
            st.rerun()
    
    with col3:
        if st.button("⏰ Не сейчас", key=f"defer_{rec.id}"):
            save_ssr_feedback(rec, "deferred", user_state)
            st.info("Напомним позже")
            st.rerun()
```

---

## 🔗 Related Documents

- [`ssr_ai_vision_summary.md`](ssr_ai_vision_summary.md) — Complete roadmap
- [`ssr_all_levels_quick_start.md`](ssr_all_levels_quick_start.md) — Quick start guides
- [`ssr_evaluation_rubrics.md`](../eval/ssr_evaluation_rubrics.md) — Evaluation rubrics

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Статус:** Production-ready
