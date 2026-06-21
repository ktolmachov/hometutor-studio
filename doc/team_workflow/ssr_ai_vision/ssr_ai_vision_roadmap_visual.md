# SSR AI Vision — Visual Roadmap

**Дата:** 2026-05-08  
**Версия:** 1.0  
**Цель:** Визуализация всех 5 уровней AI Vision с зависимостями и timeline

---

## 🗺️ Complete Roadmap (All 5 Levels)

```mermaid
gantt
    title SSR AI Vision — 22 Week Roadmap
    dateFormat YYYY-MM-DD
    section Level 1: ML Layer
    Baseline Hardening           :l1a, 2026-05-15, 1w
    Eval Harness                 :l1b, after l1a, 1w
    Forgetting Curve Model       :l1c, after l1b, 2w
    section Level 2: LLM Explanation
    Explanation Eval             :l2a, after l1c, 1w
    Prompt Engineering           :l2b, after l2a, 1w
    Explanation Integration      :l2c, after l2b, 1w
    section Level 3: Weekly Planner
    Planner Baseline             :l3a, after l2c, 1w
    Plan Optimization (ML)       :l3b, after l3a, 2w
    Plan Integration             :l3c, after l3b, 2w
    section Level 4: Graph Router
    KG Integration Design        :l4a, after l3c, 1w
    Concept Routing              :l4b, after l4a, 2w
    Prerequisite Validation      :l4c, after l4b, 1w
    section Level 5: Feedback Loop
    Feedback Collection          :l5a, after l4c, 1w
    Policy Learning (ML)         :l5b, after l5a, 3w
    Adaptive Weights             :l5c, after l5b, 2w
```

---

## 📊 Dependency Graph (All Levels)

```mermaid
graph TD
    subgraph "Baseline"
        B[SSR v2.0 Baseline<br/>US-20.1–20.12 closed]
    end
    
    subgraph "Level 1: Local ML Layer"
        L1A[ml-ssr-baseline-hardening<br/>M effort, 1 week]
        L1B[ml-ssr-eval-harness<br/>M effort, 1 week]
        L1C[ml-ssr-forgetting-curve-v1<br/>L effort, 2 weeks]
    end
    
    subgraph "Level 2: LLM Explanation"
        L2A[llm-ssr-explanation-eval<br/>S effort, 1 week]
        L2B[llm-ssr-prompt-engineering<br/>M effort, 1 week]
        L2C[llm-ssr-explanation-integration<br/>M effort, 1 week]
    end
    
    subgraph "Level 3: Weekly Planner"
        L3A[ssr-weekly-planner-baseline<br/>M effort, 1 week]
        L3B[ml-ssr-plan-optimization<br/>L effort, 2 weeks]
        L3C[ssr-weekly-plan-integration<br/>M effort, 2 weeks]
    end
    
    subgraph "Level 4: Graph Router"
        L4A[kg-ssr-integration-design<br/>S effort, 1 week]
        L4B[kg-ssr-concept-routing<br/>M effort, 2 weeks]
        L4C[kg-ssr-prerequisite-validation<br/>M effort, 1 week]
    end
    
    subgraph "Level 5: Feedback Loop"
        L5A[ml-ssr-feedback-collection<br/>M effort, 1 week]
        L5B[ml-ssr-policy-learning<br/>L effort, 3 weeks]
        L5C[ml-ssr-adaptive-weights<br/>M effort, 2 weeks]
    end
    
    B --> L1A
    L1A --> L1B
    L1B --> L1C
    
    L1C --> L2A
    L2A --> L2B
    L2B --> L2C
    
    L1C --> L3A
    L2C --> L3A
    L3A --> L3B
    L3B --> L3C
    
    L3C --> L4A
    L4A --> L4B
    L4B --> L4C
    
    L3C --> L5A
    L5A --> L5B
    L5B --> L5C
    
    style B fill:#e1f5e1
    style L1C fill:#ffe1e1
    style L2C fill:#ffe1e1
    style L3C fill:#ffe1e1
    style L4C fill:#ffe1e1
    style L5C fill:#ffe1e1
```

---

## 🔄 Parallel Execution Path

```mermaid
gantt
    title SSR AI Vision — Parallel Path (21 weeks)
    dateFormat YYYY-MM-DD
    section Wave 1 (6 weeks)
    Level 1: ML Layer            :w1a, 2026-05-15, 4w
    Level 2: LLM Explanation     :w1b, 2026-05-15, 3w
    section Wave 2 (5 weeks)
    Level 3: Weekly Planner      :w2, after w1a, 5w
    section Wave 3 (10 weeks, parallel)
    Level 4: Graph Router        :w3a, after w2, 4w
    Level 5: Feedback Loop       :w3b, after w2, 6w
```

**Преимущества:**
- ✅ Быстрее на 1 неделю (21 vs 22)
- ✅ Level 1 и Level 2 параллельно (нет зависимости)
- ✅ Level 4 и Level 5 параллельно (оба зависят от Level 3)

**Недостатки:**
- ⚠️ Требует 2 команды одновременно (Wave 1, Wave 3)
- ⚠️ Сложнее координация

---

## 🎯 MVP-First Path

```mermaid
gantt
    title SSR AI Vision — MVP-First Path (22 weeks)
    dateFormat YYYY-MM-DD
    section Quick Wins
    Level 2: LLM Explanation     :mvp1, 2026-05-15, 3w
    Level 1: ML Layer            :mvp2, after mvp1, 4w
    section Closing Loop
    Level 5: Feedback Loop       :mvp3, after mvp2, 6w
    section Proactive
    Level 3: Weekly Planner      :mvp4, after mvp3, 5w
    section Graph-Aware
    Level 4: Graph Router        :mvp5, after mvp4, 4w
```

**Приоритет по impact/effort:**
1. **Level 2** (3 weeks, M effort) — Быстрый win, высокая user satisfaction
2. **Level 1** (4 weeks, L effort) — Персонализация, +15% completion
3. **Level 5** (6 weeks, L effort) — Замыкает feedback loop
4. **Level 3** (5 weeks, L effort) — Проактивное планирование
5. **Level 4** (4 weeks, M effort) — Prerequisite-aware routing

**Преимущества:**
- ✅ Быстрая value delivery (Level 2 за 3 недели)
- ✅ Feedback loop закрыт раньше (13 недель vs 22)
- ✅ Проще приоритизация (по impact)

**Недостатки:**
- ⚠️ Level 3 и Level 4 в конце (не критично)

---

## 📦 Package Dependencies (Detailed)

```mermaid
graph LR
    subgraph "Level 1"
        L1A[Baseline<br/>Hardening] --> L1B[Eval<br/>Harness]
        L1B --> L1C[Forgetting<br/>Curve]
    end
    
    subgraph "Level 2"
        L2A[Explanation<br/>Eval] --> L2B[Prompt<br/>Engineering]
        L2B --> L2C[Explanation<br/>Integration]
    end
    
    subgraph "Level 3"
        L3A[Planner<br/>Baseline] --> L3B[Plan<br/>Optimization]
        L3B --> L3C[Plan<br/>Integration]
    end
    
    subgraph "Level 4"
        L4A[KG Integration<br/>Design] --> L4B[Concept<br/>Routing]
        L4B --> L4C[Prerequisite<br/>Validation]
    end
    
    subgraph "Level 5"
        L5A[Feedback<br/>Collection] --> L5B[Policy<br/>Learning]
        L5B --> L5C[Adaptive<br/>Weights]
    end
    
    L1C -.-> L2A
    L1C -.-> L3A
    L2C -.-> L3A
    L3C -.-> L4A
    L3C -.-> L5A
    
    style L1C fill:#ffcccc
    style L2C fill:#ccffcc
    style L3C fill:#ccccff
    style L4C fill:#ffffcc
    style L5C fill:#ffccff
```

**Legend:**
- Solid arrows (→) = Hard dependency (must complete before)
- Dotted arrows (-.→) = Soft dependency (recommended before)
- Red = ML package
- Green = Standard package
- Blue = Hybrid package

---

## 🎯 Milestone Timeline

```mermaid
timeline
    title SSR AI Vision Milestones
    section Q2 2026
        Week 1-4 : Level 1 Complete
                 : ML reranking working
                 : +15% cards_due completion
        Week 5-7 : Level 2 Complete
                 : LLM explanations
                 : +0.8 clarity score
    section Q3 2026
        Week 8-12 : Level 3 Complete
                  : Weekly planner
                  : +15% plan completion
        Week 13-16 : Level 4 Complete
                   : Graph-aware routing
                   : -20% prerequisite violations
    section Q4 2026
        Week 17-22 : Level 5 Complete
                   : Feedback loop closed
                   : +15% acceptance rate
                   : AI Vision COMPLETE 🎉
```

---

## 📊 Cumulative Impact Over Time

```mermaid
graph LR
    B[Baseline<br/>60% completion<br/>3.2/5 clarity] --> L1[+Level 1<br/>75% completion<br/>3.2/5 clarity]
    L1 --> L2[+Level 2<br/>75% completion<br/>4.0/5 clarity]
    L2 --> L3[+Level 3<br/>75% completion<br/>4.0/5 clarity<br/>55% plan completion]
    L3 --> L4[+Level 4<br/>75% completion<br/>4.0/5 clarity<br/>55% plan completion<br/>5% violations]
    L4 --> L5[+Level 5<br/>85% completion<br/>4.0/5 clarity<br/>55% plan completion<br/>5% violations<br/>85% acceptance]
    
    style B fill:#e1e1e1
    style L1 fill:#ffe1e1
    style L2 fill:#ffe1cc
    style L3 fill:#ffeecc
    style L4 fill:#ffffcc
    style L5 fill:#ccffcc
```

---

## 🔗 Critical Path Analysis

```mermaid
graph TD
    START[Start] --> L1[Level 1: 4 weeks]
    L1 --> FORK{Parallel?}
    
    FORK -->|Sequential| L2S[Level 2: 3 weeks]
    L2S --> L3S[Level 3: 5 weeks]
    L3S --> L4S[Level 4: 4 weeks]
    L4S --> L5S[Level 5: 6 weeks]
    L5S --> END1[End: 22 weeks]
    
    FORK -->|Parallel| L2P[Level 2: 3 weeks<br/>parallel with L1]
    L2P --> L3P[Level 3: 5 weeks]
    L3P --> FORK2{Parallel?}
    FORK2 --> L4P[Level 4: 4 weeks]
    FORK2 --> L5P[Level 5: 6 weeks<br/>parallel with L4]
    L4P --> END2[End: 21 weeks]
    L5P --> END2
    
    style START fill:#ccffcc
    style END1 fill:#ffcccc
    style END2 fill:#ccffff
```

**Critical Path (Sequential):** L1 → L2 → L3 → L4 → L5 = **22 weeks**

**Critical Path (Parallel):** L1 || L2 → L3 → (L4 || L5) = **21 weeks**

**Bottleneck:** Level 3 (5 weeks) — cannot parallelize

---

## 🚀 Quick Start Paths

### Path A: Full Sequential (Safest)

```
Week 1-4:   Level 1 (ML Layer)
Week 5-7:   Level 2 (LLM Explanation)
Week 8-12:  Level 3 (Weekly Planner)
Week 13-16: Level 4 (Graph Router)
Week 17-22: Level 5 (Feedback Loop)

Total: 22 weeks
Risk: Low (no parallel coordination)
```

### Path B: Parallel Waves (Fastest)

```
Week 1-4:   Level 1 (ML Layer) || Level 2 (LLM Explanation)
Week 5-9:   Level 3 (Weekly Planner)
Week 10-15: Level 4 (Graph Router) || Level 5 (Feedback Loop)

Total: 21 weeks
Risk: Medium (requires 2 teams in Wave 1 and Wave 3)
```

### Path C: MVP-First (Best ROI)

```
Week 1-3:   Level 2 (LLM Explanation) — Quick win
Week 4-7:   Level 1 (ML Layer) — Personalization
Week 8-13:  Level 5 (Feedback Loop) — Close the loop
Week 14-18: Level 3 (Weekly Planner) — Proactive
Week 19-22: Level 4 (Graph Router) — Graph-aware

Total: 22 weeks
Risk: Low (sequential, prioritized by impact)
```

---

## 🔗 Related Documents

- [`ssr_ai_vision_summary.md`](ssr_ai_vision_summary.md) — Complete roadmap summary
- [`product_owner_router.md`](product_owner_router.md) — PO Router
- [`smart_study_router.md`](../smart_study_router.md) — SSR vision

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Статус:** Production-ready
