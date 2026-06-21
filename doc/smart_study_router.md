# Smart Study Router — Killer Feature

> **Статус:** полностью доставлен (US-20.1–20.12, 6 волн, 12 пакетов closed)  
> **Версия:** 2.0 (Next Level)  
> **Актуализировано:** 2026-05-11

---

## 📋 Содержание

- [Что это](#что-это)
- [Почему это killer feature](#почему-это-killer-feature)
- [Архитектура](#архитектура)
- [Сигналы и приоритеты](#сигналы-и-приоритеты)
- [Explainability Engine](#explainability-engine)
- [Trust & Confidence](#trust--confidence)
- [Learner Agency](#learner-agency)
- [Точки входа (Surfaces)](#точки-входа-surfaces)
- [User Stories (Epic 20)](#user-stories-epic-20)
- [Next Level — AI Vision](#next-level--ai-vision)
- [Level 1 Deep Dive: Local ML Layer](#level-1-deep-dive-local-ml-layer--forgetting-curve-model)
- [Связанные документы](#связанные-документы)

---

## Что это

**Smart Study Router (SSR)** — объяснимая подсказка следующего учебного шага по текущему learning state пользователя. Вместо ручного выбора между тьютором, quiz, flashcards или dashboard, система **автоматически определяет** оптимальный следующий шаг и **объясняет**, почему именно он.

### Одна фраза

> «Ваш личный тьютор, который всегда знает, что делать дальше — и объясняет почему.»

### Ключевые свойства

| Свойство | Реализация |
|----------|------------|
| **Детерминированный** | Без LLM-вызова, чистая policy logic на локальных сигналах |
| **Объяснимый** | Каждый шаг: «почему сейчас» + контраст с альтернативой + педагогическая метка |
| **Local-first** | Все данные — на устройстве, нет облачного профилирования |
| **Не скрывает режимы** | Рекомендует, но не прячет tutor/quiz/flashcards/dashboard |
| **Адаптивный** | Steering toggles: «сначала повтор» / «новая тема» / «мягкий режим» |

---

## Почему это killer feature

### Проблема (CJM pain point)

Пользователь открывает приложение и видит 5+ режимов: быстрый ответ, тьютор, quiz, flashcards, прогресс, план. **Cognitive overload** — он не знает, что делать дальше. Выбирает привычное (тьютор), пропускает критичное (просроченные карточки SM-2). Результат: **забывание, потеря прогресса, отток**.

### Решение SSR

```
Learning State → Policy Engine → Recommendation Card
     ↓                                    ↓
  7 сигналов              «Повторить 5 карточек»
  (локальные)             + почему сейчас
                          + лучше, чем X
                          + педагогический тип
                          + evidence ledger
                          + кнопка действия
```

### Benchmark vs конкуренты

| Продукт | Что делает | SSR advantage |
|---------|-----------|---------------|
| **Duolingo** | Линейный путь, нет выбора | SSR: нелинейный, cross-loop, объясняет |
| **Anki** | Только SRS, нет тьютора | SSR: интегрирует SRS + tutor + quiz + план |
| **Khan Academy** | «Рекомендуется для вас» без объяснения | SSR: contrastive explanation + evidence |
| **Notion AI** | Генерация контента, не педагогика | SSR: педагогический маршрут, не просто текст |
| **Coursera** | Линейный курс с дедлайнами | SSR: адаптивный, без внешних дедлайнов |

**Уникальное отличие:** SSR — единственная система, которая объединяет **explainable routing + local evidence + learner agency** без облачного трекинга.

---

## Архитектура

### Модули

```
app/smart_study_router.py             — Core: dataclasses, rule policy, steering, ML hybrid hook
app/ssr_ml_reranking.py               — Local ML reranking inference (optional Level 1 layer)
app/ssr_ml_monitoring.py              — Local ML latency/confidence/fallback metrics
app/ui/adaptive_plan_card.py          — Render/integration surface, LLM explanation substitution
app/ui/tutor_chat_render.py           — Trust overlay, defer logic, trace lines
app/ui/tutor_chat_quiz.py             — Post-quiz SSR trigger
app/ui/resume_cards.py                — Home/adaptive_plan SSR surface, session context
app/user_state_core.py                — Steering preferences persistence
app/orchestrator_router.py            — PedagogicalRouter (LLM-based, separate)
app/router_eval.py                    — Router evaluation harness
tests/test_smart_study_router.py      — Policy tests
tests/e2e/smart_study_router.spec.ts  — E2E Playwright tests
```

### Dataclass

```python
@dataclass(frozen=True)
class SmartStudyRecommendation:
    hint_kind: SmartStudyRouterHintKind    # сигнал-источник
    primary_label_ru: str                   # «Повторить», «Разобрать слабое место»
    why_now_ru: str                         # объяснение «почему сейчас»
    primary_nav: SmartStudyPrimaryNav       # навигация при клике
    secondaries: tuple[SmartStudySecondaryAction, ...]  # 2–4 альтернативы
    route_pedagogy_ru: str                  # US-20.9: тип приоритета
    ml_audit_ru: str = ""                   # audit tail from optional local ML hybrid
```

`SmartStudyRecommendation` intentionally has no `concept` or mutable
`evidence_ledger` field. Evidence is built as a UI-adjacent typed ledger from
local signals (`EvidenceItem`) and rendered with `influenced=True` by default;
the full signal list remains a debug/test mode. ML audit text flows through
`ml_audit_ru`, not by mutating the frozen recommendation.

### Hint Kinds (сигналы)

| Kind | Trigger | Priority |
|------|---------|----------|
| `cards_due` | Flashcards SM-2 queue > 0 | 🔴 **1** (highest) |
| `sm2_due` | Concept SM-2 queue > 0 | 🔴 **2** |
| `quiz_failed` | Last mini-quiz failed | 🟡 **3** |
| `adaptive_plan` | Plan block ready (on plan surface) | 🟡 **4** |
| `tutor_resume` | Unfinished tutor session | 🟢 **5** |
| `answer_ready` | Q&A answer exists locally | 🟢 **6** |
| `mastery_stale` | Weak concept or reading resume | 🟢 **7** |
| `safe_default` | No strong signals | ⚪ **8** (fallback) |

### Primary Navigation Targets

| Nav | Куда ведёт | Когда |
|-----|-----------|-------|
| `flashcards_review` | Flashcards → review queue | cards_due |
| `sm2_tutor` | Tutor chat с prompt «повторить концепт» | sm2_due |
| `quiz_recovery_tutor` | Tutor chat с prompt «разобрать ошибку» | quiz_failed |
| `plan_block_tutor` | Tutor chat по блоку плана | adaptive_plan |
| `tutor_resume` | Tutor chat → продолжить сессию | tutor_resume |
| `qa_continue` | Быстрый ответ | answer_ready, mastery_stale |
| `tutor_weak_gap` | Tutor chat «освоить пробел» | mastery_stale |
| `safe_tutor_5min` | Tutor 5-min session | safe_default |

---

## Сигналы и приоритеты

### Принцип: Retention > Recovery > New Learning > Default

```
1. cards_due        → RETENTION: SM-2 intervals protect long-term memory
2. sm2_due          → RETENTION: concept repetition queue
3. quiz_failed      → RECOVERY: fix misconception before it solidifies
4. adaptive_plan    → STRUCTURED: follow the planned route
5. tutor_resume     → CONTINUITY: don't lose dialogue context
6. answer_ready     → NEW LEARNING: transfer Q&A into deep study
7. mastery_stale    → REINFORCEMENT: refresh weak areas
8. safe_default     → ENTRY: gentle 5-min start when no signals
```

### Pedagogical Labels (US-20.9: Learning Debt Queue)

Каждая рекомендация получает педагогическую метку:

- **Долг удержания** — интервальное повторение снижает забывание
- **Восстановление слабого понятия** — разобрать ошибку до следующей проверки
- **Новое обучение** — перенести материал в освоение темы

---

## Explainability Engine

### Три уровня объяснения

**1. «Почему сейчас» (why_now_ru)**

Текстовое объяснение причины рекомендации, привязанное к конкретному локальному сигналу:

> «Локальная очередь SM-2: к повтору 5 карточек — интервал уже наступил; короткая сессия удержит факты и снижает риск забывания.»

**2. Contrastive Explanation (US-20.7)**

Сравнение с альтернативным действием — «лучше, чем X»:

> «Важнее свободного диалога или quiz без очереди: карточки с интервалами уже ждут повторения.»

**3. Evidence Ledger (US-20.8)**

Компактный список локальных сигналов, на которых основано решение. Runtime UI
показывает только `EvidenceItem.influenced=True`, чтобы не создавать «театр
честности» из строк `нет / 0 / недоступно`. Полный список сигналов остаётся
debug/test режимом.

```
• Очередь flashcards (локально): 5 карточек к повтору
```

> ⚠️ Ledger **никогда** не содержит выдуманной «уверенности» или облачного скоринга — только локальные, проверяемые факты.

---

## Trust & Confidence

### Source Trust Overlay

Если retrieval confidence низкая → SSR корректирует рекомендацию:

```python
apply_source_trust_smart_study_overlay(rec, last_answer, tutor_trust)
```

| Condition | Effect | Audit |
|---|---|---|
| `confidence.level = low` and `sources_used < 2` | `primary_nav=qa_continue`, label «Сверить источники» | `source_trust` influenced |
| `confidence.level = medium` and `coverage_warning=weak` | Prefer Q&A sources before tutor/quiz | `source_trust` influenced |
| `confidence.level = high` and `sources_used >= 2` | Keep SSR recommendation | debug-only signal |

Trust controls показывают trace и позволяют «отложить» без удаления очередей.

### Defer Mechanism (US-20.12: Quiet Mode)

Кнопка «Не сейчас» не убирает рекомендацию навсегда — переключает на мягкую альтернативу:

```
cards_due + «Не сейчас» → safe_tutor_5min (мягкий чат вместо жёсткого повтора)
```

Очередь SM-2 **сохраняется** — пользователь вернётся к ней позже.
Fail-safe: после серии отложенных retention-рекомендаций UI должен снова
показать риск забывания явно и предложить короткий snooze/микро-повтор, а не
бесконечно заменять долг памяти мягким чатом.

---

## Learner Agency

### Steering Toggles (US-20.10)

Пользователь может задать предпочтение, которое SSR учитывает при построении рекомендации:

| Toggle | Эффект | Ограничение |
|--------|--------|------------|
| `review_first` | Добавляет acknowledgement к retention-шагам; если очередей нет, не создаёт фиктивный долг | Не скрывает `quiz_failed` recovery |
| `new_topic` | Поддерживает `answer_ready`/`adaptive_plan`; при retention debt добавляет trade-off line | Retention долг остаётся видимым |
| `gentle` | Для `cards_due`/`tutor_resume` может заменить CTA на `safe_tutor_5min` | `quiz_failed` разбор не отменяется |

**Принцип:** toggles **модифицируют**, но **не отменяют** сильные педагогические сигналы. Если quiz провален — recovery будет показан независимо от toggle.

### Outcome Receipts (US-20.11)

После каждого действия SSR → micro-receipt:

> «Вы повторили 5 карточек. Следующий интервал SM-2: через 3 дня.»

| Outcome | Receipt template |
|---|---|
| Flashcard review completed | «Вы повторили N карточек; очередь изменилась: было X → стало Y.» |
| Partial flashcard session | «Вы начали повторение; осталось N карточек, вернём долг памяти в следующий SSR.» |
| Quiz failed | «Ошибка сохранена как recovery-сигнал; следующий шаг — разобрать слабое место.» |
| Quiz passed | «Проверка закрыта; SSR может перейти к плану/новой теме.» |
| Session abandoned | «Прогресс не потерян; resume-сигнал сохранён для мягкого возврата.» |

---

## Точки входа (Surfaces)

SSR отображается на **4 поверхностях** UI:

| Surface | Где | Поведение |
|---------|-----|-----------|
| `home` | Главный экран | Полная карточка: primary + why + contrast + ledger + secondaries |
| `adaptive_plan` | Адаптивный план | Интеграция с блоками плана, plan_block → tutor |
| `tutor_chat` | После ответа тьютора | Компактная карточка в конце чата + trust controls |
| `flashcards_hub` | Flashcards раздел | Карточка после review session |

### Session Context

```python
@dataclass
class SmartStudyRouterSessionContext:
    flashcard_due_n: int
    sm2_due_n: int
    quiz_feedback_status: str | None
    has_tutor_resume: bool
    tutor_topic: str | None
    has_last_answer_qa: bool
    has_reading_resume: bool
    first_weak_concept: str | None
    plan_primary_block: dict | None
```

`plan_primary_block` остаётся текущим runtime contract, но следующий refactor
должен заменить его typed `PlanBlockRef`, чтобы не протаскивать untyped dict
между policy и UI.

### SSR ↔ PedagogicalRouter contract

```
HomeSurface       → SSR policy                → rec           → UI render
AdaptivePlan      → SSR policy                → rec           → UI render
TutorChatSurface  → PedagogicalRouter (LLM)   → turn type     → tutor step
TutorChatSurface  → SSR policy                → post-turn rec → UI render
router_eval.py    → evaluates PedagogicalRouter harness, not SSR policy
```

SSR выбирает **between-session next step** (`hint_kind`, `primary_nav`).
PedagogicalRouter выбирает **within-session tutor turn**. Они не должны
дублировать приоритеты друг друга; общие контракты выносятся в типы/fixtures,
а не в UI-код.

---

## User Stories (Epic 20)

### Baseline (Waves 1–3: Surface Parity)

| US | Title | Priority | Status |
|----|-------|----------|--------|
| US-20.1 | Объяснимая подсказка следующего учебного шага | P0 | ✅ closed |
| US-20.2 | Explainable Next Step Card | P0 | ✅ closed |
| US-20.3 | Due-review priority | P0 | ✅ closed |
| US-20.4 | Weak-concept recovery route | P0 | ✅ closed |
| US-20.5 | Post-answer learning runway | P0 | ✅ closed |
| US-20.6 | Accessible router and preserved entry points | P1 | ✅ closed |

### Next Level (Waves 4–6: Trust, Pedagogy, Retention)

| US | Title | Priority | Status |
|----|-------|----------|--------|
| US-20.7 | Contrastive Router Explanation | P0 | ✅ closed |
| US-20.8 | Local Route Confidence Ledger | P0 | ✅ closed |
| US-20.9 | Learning Debt Queue | P0 | ✅ closed |
| US-20.10 | Learner Steering Toggles | P1 | ✅ closed |
| US-20.11 | Micro-Outcome Receipt | P1 | ✅ closed |
| US-20.12 | Quiet Mode Route | P1 | ✅ closed |

---

## Next Level — AI Vision

### Текущее состояние: детерминированный policy engine

SSR v2.0 — **rule-based** система. Это хорошо для explainability и local-first, но есть потолок:

- Приоритеты фиксированы (cards_due > sm2_due > quiz_failed > ...)
- Нет учёта **скорости забывания** конкретного пользователя
- Нет **контекста темы** (алгебра vs литература требуют разных стратегий)
- Нет **temporal patterns** (утром лучше новое, вечером — повтор)
- Нет **cross-session learning trajectory** (тренд прогресса за неделю)

### Vision: Hybrid AI Router (post-v2 / Wave 7+)

#### Уровень 1: Local ML Layer (без облака)

```
Сигналы (9)                    Lightweight ML
  ├── cards_due                   ├── Forgetting curve per card
  ├── sm2_due                     ├── Personal retention rate
  ├── quiz_outcomes[]             ├── Concept difficulty model
  ├── session_duration            ├── Time-of-day preference
  ├── time_since_last             ├── Session fatigue estimator
  ├── weak_concepts[]             ├── Topic cluster routing
  ├── tutor_depth                 ├── Depth vs breadth balance
  ├── answer_confidence           └── Priority reranking
  └── steering_preference
```

**Реализация:** lightweight модель (logistic regression / small monotone model), обученная на **локальных** данных пользователя или на bootstrap-наборе с последующей локальной персонализацией. Без облака. Модель хранится локально рядом с user_state/model artifacts.

#### Уровень 2: LLM-Enhanced Explanation

Текущий `why_now_ru` — шаблонный текст. С LLM:

```
БЫЛО:  «Локальная очередь SM-2: к повтору 5 карточек — интервал уже наступил.»
СТАЛО: «Вчера вы изучали "Деревья решений" и ответили на 3 из 5 вопросов верно.
        Сегодня — идеальный момент для повтора: по вашему паттерну забывания,
        через 24 часа вы помните ~70% материала, а через 48 — только ~40%.
        5 карточек по этой теме укрепят память до следующего интервала.»
```

**Constraint:** LLM-вызов **только для explanation**, не для routing decision. Decision остаётся детерминированным.
Рекомендуемый контракт: `explain(rec, evidence) -> Explanation`, где template backend
является базовым, а LLM backend включается только через `ENABLE_SSR_LLM_EXPLANATION`
и не имеет доступа к изменению `hint_kind`/`primary_nav`.

#### Уровень 3: Proactive Study Planner

SSR переходит от **реактивного** (что делать сейчас) к **проактивному** (что делать на этой неделе):

```
Понедельник: «На этой неделе вам стоит:
  1. Повторить 23 карточки (распределение: 8 пн, 7 ср, 8 пт)
  2. Закрыть пробел по "Нейронные сети" (2 сессии тьютора)
  3. Пройти quiz по "Линейная алгебра" (score прошлый раз: 60%)
  Estimated time: 45 мин/день»
```

#### Уровень 4: Concept Graph Router

SSR использует knowledge graph для маршрутизации:

```
Concept A (mastered) ──prerequisite──→ Concept B (weak)
                                          ↓
                              SSR: «Изучите B, потому что
                              вы уже освоили A — это фундамент»
```

**Реализация:** интеграция с `app/knowledge_graph.py` для concept dependencies.

#### Уровень 5: Misroute Feedback Loop

Пользователь может сказать «этот совет был не полезен» → SSR корректирует policy weights:

```
cards_due рекомендован → пользователь отклонил 3 раза подряд
→ если downstream retention outcome подтверждает, что defer был безопасен,
  SSR временно снижает приоритет cards_due для этого пользователя
→ Evidence ledger показывает: «Приоритет flashcards снижен (3 отклонения)»
```

Важное ограничение: feedback loop не должен мутировать retention-политику только
из-за friction/отказов. Вес снижается с decay и только после события результата
(`rec`, `action`, downstream retention event), иначе локальная SRS-защита
размывается.

### 5 Parked Ideas для Wave 4

| ID | Title | Score | Потенциал |
|----|-------|-------|-----------|
| 07 | Misroute Feedback Loop | 4.5 | Замыкает цикл user→system learning; tie-breaker: highest learning-loop impact |
| 10 | Local Route Simulator | 4.5 | «Что если» — preview альтернативного маршрута; tie-breaker: lower safety risk |
| 12 | Source-Coverage Route Guard | 4.5 | Блокирует шаг, если источников < threshold; tie-breaker: trust/compliance impact |
| 08 | Concept Recovery Ladder | 3.0 | Multi-step recovery path для сложных тем |
| 11 | Weekly Study Narrative | 2.0 | Еженедельный отчёт по learning trajectory |

### Принципы развития

1. **AI усиливает, но не заменяет** детерминированную policy
2. **Explainability первична** — каждое AI-решение должно быть объяснимо
3. **Local-first** — ML модель на устройстве, не в облаке
4. **User agency** — пользователь всегда может override рекомендацию
5. **Evidence-based** — никаких выдуманных метрик, только проверяемые факты

---

## Level 1 Deep Dive: Local ML Layer — Forgetting Curve Model

> **Статус:** частично реализованный optional hybrid (`app/ssr_ml_reranking.py`), дальнейшее развитие — post-v2 / Wave 7+  
> **Приоритет:** P0 (первый уровень AI Vision)  
> **Effort:** 4 недели  
> **Цель:** Персонализированные приоритеты SSR на основе forgetting curve

### 🎯 Что это и зачем

**Проблема:** Текущий SSR использует фиксированные приоритеты (cards_due > sm2_due > quiz_failed > ...). Это работает для всех одинаково, но **не учитывает индивидуальные паттерны забывания**.

**Пример:**
- **User A:** Забывает быстро (через 24 часа retention = 50%)
- **User B:** Забывает медленно (через 24 часа retention = 80%)
- **Текущий SSR:** Рекомендует обоим повторить через 24 часа
- **Level 1 SSR:** User A → повторить через 12 часов, User B → через 48 часов

**Решение:** Lightweight ML модель, которая учится на локальных данных пользователя и корректирует приоритеты SSR.

### 📊 Forgetting Curve: Теория

**Кривая забывания Эббингауза (1885):**

```
Retention (%) = 100 × e^(-t/S)

где:
  t = время с момента изучения (hours)
  S = strength of memory (индивидуальный параметр)
```

**Персонализация:**
- **User A:** S = 12 (забывает быстро)
- **User B:** S = 48 (забывает медленно)

В этой формуле `S` — удобная педагогическая метафора силы памяти. Текущий
Level 1 в коде не оценивает `S` напрямую: он использует локальную logistic
regression для `P(remembered | features)` и применяет её как reranking signal.
Если команде нужен именно параметр `S`, следующий вариант модели должен быть
survival/exponential regression; иначе документация и UI должны говорить
«probability of recall», а не «оценка S».

### 🏗️ Архитектура Level 1

```
┌─────────────────────────────────────────────────────────────┐
│                    SSR Level 1 Architecture                  │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  User Activity   │
│  (local data)    │
└────────┬─────────┘
         │
         ├─→ flashcard_reviews (user_state.db)
         ├─→ quiz_outcomes (user_state.db)
         ├─→ tutor_sessions (user_state.db)
         │
         ↓
┌──────────────────────────────────────────────────────────────┐
│              Data Collection & Feature Engineering            │
│  scripts/ml/data_collection_ssr.py                           │
│                                                               │
│  Features:                                                    │
│  - time_since_last_review (hours)                            │
│  - quiz_score_last_3 (avg 0-1)                               │
│  - concept_difficulty (from knowledge_graph)                 │
│  - session_duration_avg (minutes)                            │
│  - time_of_day_sin/cos (cyclic hour encoding)                │
│  - day_of_week_sin/cos (cyclic weekday encoding)             │
│  - cards_due_count                                           │
│  - sm2_due_count                                             │
│  - quiz_failed_recent (bool)                                 │
│                                                               │
│  Target:                                                      │
│  - retention_probability (0-1)                               │
│    = 1 if user remembered (quiz correct / flashcard correct) │
│    = 0 if user forgot (quiz wrong / flashcard wrong)         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                    Model Training                             │
│  scripts/ml/train_ssr_forgetting_curve.py                    │
│                                                               │
│  Algorithm: Logistic Regression (sklearn)                    │
│  Why: Simple, fast, explainable, < 1MB                       │
│                                                               │
│  Training:                                                    │
│  - 80% train, 20% test split                                 │
│  - Cross-validation (5-fold)                                 │
│  - Regularization (L2, alpha=0.01)                           │
│                                                               │
│  Output:                                                      │
│  - models/ssr_forgetting_curve_v1.pkl (< 1MB)                │
│  - Feature coefficients (explainability)                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                    Evaluation Harness                         │
│  tests/eval/test_ssr_ml_reranking.py                         │
│                                                               │
│  Metrics:                                                     │
│  - AUC-ROC ≥ 0.75 (baseline: 0.50 random)                    │
│  - Precision@5 ≥ 0.80                                        │
│  - Recall@5 ≥ 0.70                                           │
│  - Inference latency p95 < 50ms                              │
│                                                               │
│  Test set: 20% holdout from data collection                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                    Integration (Hybrid)                       │
│  app/smart_study_router.py + app/ssr_ml_reranking.py         │
│                                                               │
│  def _apply_ml_priority_reranking(rec, user_state):          │
│      # 1. Get baseline priority (rule-based)                 │
│      baseline_priority = get_baseline_priority(rec.hint_kind)│
│                                                               │
│      # 2. ML reranking (if model available)                  │
│      if ml_model_available():                                │
│          retention_prob = ml_model.predict(                  │
│              time_since_last_review=...,                     │
│              quiz_score_last_3=...,                          │
│              ...                                             │
│          )                                                   │
│          ml_adjustment = retention_prob  # 0-1               │
│      else:                                                   │
│          ml_adjustment = 1.0  # No adjustment                │
│                                                               │
│      # 3. Hybrid priority                                    │
│      risk_factor = 1 + (1 - retention_prob)                  │
│      adjusted_score = baseline_score * risk_factor           │
│                                                               │
│      # 4. Explainability: show adjustment through ml_audit_ru │
│      if retention_prob < 0.8:                                │
│          rec = replace(rec, ml_audit_ru=audit_line)          │
│                                                               │
│      return rec                                              │
│                                                               │
│  Fallback: if ML fails → use baseline priority               │
└──────────────────────────────────────────────────────────────┘
```

### 🔧 Подготовка и использование

#### Шаг 1: Сбор данных (Data Collection)

**Минимальные требования:**
- **1000+ user sessions** с SM-2 outcomes
- **Минимум 2 недели** активности пользователя
- **Минимум 50 flashcard reviews** + **20 quiz attempts**

**Скрипт:**
```bash
# Собрать данные из user_state.db
.\.venv\Scripts\python.exe scripts/ml/data_collection_ssr.py --output data/ml/ssr_forgetting_curve_train.parquet

# Проверить качество данных
.\.venv\Scripts\python.exe scripts/ml/data_collection_ssr.py --validate
```

**Выход:**
- `data/ml/ssr_forgetting_curve_train.parquet` (80% train)
- `data/ml/ssr_forgetting_curve_test.parquet` (20% test)
- `data/ml/ssr_data_quality_report.txt` (статистика)

**Что делать если данных мало:**
1. **Cold start fallback:** использовать rule-based priority до накопления локальных событий.
2. **Small local budget:** разрешить персональный fit с 50–100 событиями, но показывать высокий fallback-rate/low-confidence.
3. **Bootstrap model:** обучить cohort/synthetic baseline офлайн и персонализировать его локальными online-updates. Это предпочтительный путь для local-first: пользователь не обязан ждать 1000+ личных сессий.

#### Шаг 2: Обучение модели (Model Training)

**Скрипт:**
```bash
# Обучить модель
.\.venv\Scripts\python.exe scripts/ml/train_ssr_forgetting_curve.py \
    --train data/ml/ssr_forgetting_curve_train.parquet \
    --test data/ml/ssr_forgetting_curve_test.parquet \
    --output models/ssr_forgetting_curve_v1.pkl

# Проверить размер модели
ls -lh models/ssr_forgetting_curve_v1.pkl
# Ожидаемый размер: < 1MB
```

**Параметры обучения:**
```python
# scripts/ml/train_ssr_forgetting_curve.py

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

# Модель
model = LogisticRegression(
    penalty='l2',           # L2 regularization
    C=100,                  # Inverse of regularization strength
    solver='lbfgs',         # Optimizer
    max_iter=1000,          # Max iterations
    random_state=42         # Reproducibility
)

# Cross-validation
cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
print(f"CV AUC-ROC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# Train final model
model.fit(X_train, y_train)

# Evaluate on test set
y_pred_proba = model.predict_proba(X_test)[:, 1]
auc_roc = roc_auc_score(y_test, y_pred_proba)
print(f"Test AUC-ROC: {auc_roc:.3f}")

# Save model
import joblib
joblib.dump(model, 'models/ssr_forgetting_curve_v1.pkl')
```

**Ожидаемые метрики:**
- **AUC-ROC:** 0.75–0.85 (baseline: 0.50 random)
- **Precision@5:** 0.80+ (top-5 recommendations точны)
- **Recall@5:** 0.70+ (top-5 покрывают важные items)

#### Шаг 3: Evaluation Harness

**Скрипт:**
```bash
# Запустить evaluation harness
.\.venv\Scripts\python.exe scripts/ml/eval_ssr_forgetting_curve.py \
    --model models/ssr_forgetting_curve_v1.pkl \
    --test data/ml/ssr_forgetting_curve_test.parquet \
    --output archive/ml_eval/ssr_forgetting_curve_v1_report.md
```

**Что проверяется:**
1. **AUC-ROC ≥ 0.75** — модель различает remembered vs forgotten
2. **Inference latency p95 < 50ms** — модель быстрая
3. **Model size < 1MB** — модель компактная
4. **Feature importance** — какие features важны (explainability)

**Пример отчёта:**
```markdown
# SSR Forgetting Curve Model v1 — Evaluation Report

**Date:** 2026-05-08
**Model:** models/ssr_forgetting_curve_v1.pkl
**Test set:** 200 samples (20% holdout)

## Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| AUC-ROC | 0.78 | ≥ 0.75 | ✅ PASS |
| Precision@5 | 0.82 | ≥ 0.80 | ✅ PASS |
| Recall@5 | 0.73 | ≥ 0.70 | ✅ PASS |
| Inference latency p95 | 12ms | < 50ms | ✅ PASS |
| Model size | 0.8MB | < 1MB | ✅ PASS |

## Feature Importance

| Feature | Coefficient | Interpretation |
|---------|-------------|----------------|
| time_since_last_review | -0.45 | Longer time → lower retention |
| quiz_score_last_3 | +0.38 | Higher score → higher retention |
| concept_difficulty | -0.22 | Harder concept → lower retention |
| session_duration_avg | +0.15 | Longer sessions → higher retention |
| time_of_day_sin/cos | -0.08 / +0.03 | Cyclic hour signal; raw hour is forbidden |
| day_of_week_sin/cos | model-dependent | Cyclic weekday signal; raw weekday is forbidden |

## Conclusion

Model meets all targets. Ready for integration.
```

#### Шаг 4: Интеграция (Integration)

**Код:**
```python
# app/smart_study_router.py + app/ssr_ml_reranking.py

def _apply_ml_priority_reranking(
    rec: SmartStudyRecommendation,
    feature_profile: dict[str, Any],
) -> SmartStudyRecommendation:
    """Apply local ML reranking without letting ML rewrite routing policy."""

    try:
        probs = predict_hint_probability_map_or_empty(
            feature_profile,
            prior_rule_top_hint_kind=rec.hint_kind,
        )
    except Exception as e:
        # Fallback: ML failed → use rule-only baseline
        logger.warning(f"ML reranking failed: {e}")
        return rec

    best_hint, confidence = pick_allowed_hint(probs)
    if confidence < SSR_ML_CONFIDENCE_MIN or best_hint == rec.hint_kind:
        return replace(rec, ml_audit_ru=f"SSR ML: rule match, p≈{confidence:.2f}")
    return recommendation_for_kind(
        best_hint,
        ml_audit_ru=(
            f"SSR ML: гибридный сдвиг {rec.hint_kind} → {best_hint}; "
            f"rule-baseline сохранён в prior признаках"
        ),
    )
```

#### Шаг 5: Мониторинг (Monitoring)

**Метрики для отслеживания:**
```python
# app/ui/adaptive_plan_card.py

def _log_ml_metrics(
    rec: SmartStudyRecommendation,
    ml_adjustment: float,
    inference_time_ms: float
):
    """Log ML metrics for monitoring."""
    
    metrics = {
        "hint_kind": rec.hint_kind,
        "ml_adjustment": ml_adjustment,
        "inference_time_ms": inference_time_ms,
        "fallback_used": ml_adjustment == 1.0,
        "timestamp": datetime.now().isoformat()
    }
    
    # Log to file
    with open("logs/ssr_ml_metrics.jsonl", "a") as f:
        f.write(json.dumps(metrics) + "\n")
```

**Дашборд (опционально):**
```bash
# Анализ метрик
.\.venv\Scripts\python.exe scripts/ml/analyze_ssr_ml_metrics.py \
    --input logs/ssr_ml_metrics.jsonl \
    --output reports/ssr_ml_dashboard.html
```

### 💻 Рекомендации по локальному железу

#### Минимальные требования

| Компонент | Минимум | Рекомендуется | Почему |
|-----------|---------|---------------|--------|
| **CPU** | 2 cores | 4+ cores | Inference < 50ms |
| **RAM** | 4GB | 8GB+ | Model loading + data processing |
| **Disk** | 100MB | 500MB+ | Model + training data |
| **Python** | 3.10+ | 3.11+ | repo baseline + sklearn compatibility |

#### Inference Performance

| Hardware | Inference Time (p95) | Batch Size | Notes |
|----------|---------------------|------------|-------|
| **Intel i5 (2 cores)** | 15ms | 1 | ✅ Meets target (< 50ms) |
| **Intel i7 (4 cores)** | 8ms | 1 | ✅ Excellent |
| **AMD Ryzen 5** | 12ms | 1 | ✅ Meets target |
| **ARM (M1/M2)** | 6ms | 1 | ✅ Excellent |

**Вывод:** Logistic regression работает на любом современном ПК/ноутбуке.

#### Training Performance

| Hardware | Training Time (1000 samples) | Notes |
|----------|------------------------------|-------|
| **Intel i5 (2 cores)** | 2-3 seconds | ✅ Acceptable |
| **Intel i7 (4 cores)** | 1-2 seconds | ✅ Fast |
| **AMD Ryzen 5** | 1.5 seconds | ✅ Fast |
| **ARM (M1/M2)** | 1 second | ✅ Very fast |

**Вывод:** Training быстрый (< 5 секунд), можно делать offline каждую ночь.

### 🤖 Рекомендации по моделям

#### Почему Logistic Regression?

| Критерий | Logistic Regression | XGBoost | Neural Network |
|----------|-------------------|---------|----------------|
| **Model size** | < 100KB | 1-10MB | 10-100MB |
| **Inference latency** | < 10ms | 10-50ms | 50-200ms |
| **Training time** | < 5s | 10-60s | 60-600s |
| **Explainability** | ✅ Coefficients | ⚠️ Feature importance | ❌ Black box |
| **Data requirements** | 1000+ samples | 5000+ samples | 10k+ samples |
| **Local-first** | ✅ Fits in SQLite | ✅ Fits in SQLite | ⚠️ Requires separate runtime |

**Решение:** Logistic Regression для Level 1. Upgrade к XGBoost/NN только если:
- AUC-ROC < 0.75 (не достигли target)
- Есть 5000+ samples
- Inference latency не критична (можно 50-100ms)

#### Alternative Models (если Logistic Regression не работает)

**Option 1: XGBoost**
```python
from xgboost import XGBClassifier

model = XGBClassifier(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.1,
    random_state=42
)
```

**Pros:**
- Выше accuracy (AUC-ROC 0.80-0.90)
- Handles non-linear patterns

**Cons:**
- Больше model size (1-10MB)
- Медленнее inference (10-50ms)
- Меньше explainability

**Option 2: Small Neural Network (PyTorch)**
```python
import torch
import torch.nn as nn

class ForgettingCurveNN(nn.Module):
    def __init__(self, input_dim=9):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 16)
        self.fc2 = nn.Linear(16, 8)
        self.fc3 = nn.Linear(8, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.sigmoid(self.fc3(x))
        return x
```

**Pros:**
- Highest accuracy (AUC-ROC 0.85-0.95)
- Handles complex patterns

**Cons:**
- Largest model size (10-100MB)
- Slowest inference (50-200ms)
- Black box (no explainability)
- Requires PyTorch runtime

**Рекомендация:** Начать с Logistic Regression. Upgrade только если не достигли target metrics.

### ✅ Плюсы Level 1

| Плюс | Описание | Impact |
|------|----------|--------|
| **Персонализация** | Учитывает индивидуальную forgetting curve | +15% cards_due completion |
| **Local-first** | Модель на устройстве, нет облака | Privacy + offline |
| **Быстрый inference** | < 10ms на любом ПК | No UI lag |
| **Explainable** | Feature coefficients видны | User trust |
| **Малый размер** | < 1MB модель | Fits in SQLite |
| **Hybrid** | Fallback к rule-based если ML fails | Reliability |
| **Incremental** | Можно retrain каждую ночь | Adaptive |

### ❌ Минусы Level 1

| Минус | Описание | Mitigation |
|-------|----------|------------|
| **Cold start** | Персональных событий может быть мало | Rule fallback + small-budget fit + bootstrap baseline |
| **Overfitting risk** | Модель может overfit на одного пользователя | Regularization (L2) + cross-validation |
| **Limited features** | Только 9 features | Достаточно для forgetting curve |
| **Linear model** | Не ловит non-linear patterns | Upgrade к XGBoost если нужно |
| **Maintenance** | Нужно retrain при drift | Автоматический retrain каждую ночь |
| **No multi-user** | Модель per-user, не shared | Local-first constraint |

### 🚀 Next Steps

1. **Прочитать** [`team_workflow/ssr_ai_vision/ssr_ai_vision_level1_prompt.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_level1_prompt.md) — Copy-Paste Prompt
2. **Создать evaluation contract** — metrics, test harness, rubric
3. **Собрать данные** — 1000+ sessions из user_state.db
4. **Обучить модель** — Logistic Regression, AUC-ROC ≥ 0.75
5. **Интегрировать** — hybrid (rule + ML), fallback, explainability
6. **Мониторить** — inference latency, fallback rate, acceptance rate

---

## Связанные документы

### Product & Strategy
- [`product_idea.md`](product_idea.md) — product direction (SSR как ключевое направление)
- [`cjm.md`](cjm.md) — Customer Journey Map (pain points, которые SSR закрывает)
- [`roadmap.md`](roadmap.md) — стратегический roadmap (SSR waves)
- [`future_roadmap.md`](future_roadmap.md) — re-entry rules для Wave 4

### User Stories
- [`user_stories.md`](user_stories.md) — Epic 20 index (12 user stories)
- [`user_stories/us-20.1.md`](user_stories/us-20.1.md) ... [`us-20.12.md`](user_stories/us-20.12.md) — детали

### Planning
- [`team_workflow/product_owner_router.md`](team_workflow/product_owner_router.md) — PO Router (SSR Path section)
- [`team_workflow/archive/product_owner_router_ai_vision_enhancement.md`](team_workflow/archive/product_owner_router_ai_vision_enhancement.md) — AI Vision enhancement plan
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md) — Complete roadmap (все 5 уровней)
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_level1_prompt.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_level1_prompt.md) — Level 1: Local ML Layer (Copy-Paste Prompt)
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_level2_prompt.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_level2_prompt.md) — Level 2: LLM-Enhanced Explanation
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_level3_prompt.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_level3_prompt.md) — Level 3: Proactive Study Planner
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_level4_prompt.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_level4_prompt.md) — Level 4: Concept Graph Router
- [`team_workflow/ssr_ai_vision/ssr_ai_vision_level5_prompt.md`](team_workflow/ssr_ai_vision/ssr_ai_vision_level5_prompt.md) — Level 5: Misroute Feedback Loop
- [`backlog_registry.yaml`](backlog_registry.yaml) — SSoT (6 waves, 12 packages)
- [`closed_iterations.md`](closed_iterations.md) — delivery history

### Code
- [`app/smart_study_router.py`](../app/smart_study_router.py) — Core: dataclass, rule policy, steering, ML hybrid hook
- [`app/ssr_ml_reranking.py`](../app/ssr_ml_reranking.py) — optional Level 1 local ML reranking
- [`app/ui/adaptive_plan_card.py`](../app/ui/adaptive_plan_card.py) — render/integration surface, LLM explanation substitution
- [`app/ui/tutor_chat_render.py`](../app/ui/tutor_chat_render.py) — Trust overlay, defer, trace
- [`app/ui/resume_cards.py`](../app/ui/resume_cards.py) — Home/plan surface, session context
- [`app/user_state_core.py`](../app/user_state_core.py) — Steering persistence

### Ideation
- [`archive/ideation/smart_study_router_next_level_2026-05-08.md`](../archive/ideation/smart_study_router_next_level_2026-05-08.md) — Next Level ideation (12 ideas, 7 accepted, 5 parked)
- [`archive/retrospectives/wave-smart-study-router-next-level-*_retro.yaml`](../archive/retrospectives/) — Wave retrospectives

### Presentations
- [`presentations/defense_killer_feature_smart_assistant.md`](presentations/defense_killer_feature_smart_assistant.md)
- [`presentations/defense_user_router_breakthrough.md`](presentations/defense_user_router_breakthrough.md)
