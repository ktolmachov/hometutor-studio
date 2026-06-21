# Requirements Document — UX Breakthrough Wave

## Введение

Эта спецификация описывает новую волну UX-улучшений для `home-rag_v2`: локальной учебной платформы над папкой `data/` с FastAPI, Streamlit UI, CLI и Telegram-ботом. Продукт уже достиг MVP feature completeness, но следующий скачок качества зависит не от новых возможностей, а от того, как Learner ощущает скорость, связность, доверие и прогресс.

Главная цель волны — поднять perceived quality в пяти ключевых Moments of Truth без изменения базовой архитектуры и без нарушения инвариантов проекта: local-first, источники в ответах, цикл "ответ → tutor → quiz → spaced repetition → план".

## Стратегический контракт

- **Wave ID:** `wave-ux-breakthrough-2026-05`
- **Status:** `proposed`
- **North Star:** Learner воспринимает систему как быструю, связную, мотивирующую и прозрачную.
- **Scope shape:** 5 исполнимых пакетов вместо одного крупного umbrella-пакета.
- **Non-goal:** не строить новую платформу UI, не добавлять LLM-провайдеры, не менять публичные API без отдельного контракта.

## Пакеты волны

1. `ux-foundation-parsers-contracts` — typed data contracts для ответа, handoff-контекста и analytics.
2. `ux-first-answer-wait-flow` — skeleton/progress/progressive reveal для первого ответа.
3. `epoch-us19-2-tutor-handoff-ux` — бесшовный переход из ответа в tutor с сохранением контекста.
4. `ux-mastery-celebration-analytics` — celebration UX и post-session flashcard analytics.
5. `ux-home-hub-navigation-polish` — визуальная иерархия home hub, resume priority, due badges.

## Глоссарий

- **Learner** — пользователь учебной системы.
- **MoT** — Moment of Truth, критическая точка пути пользователя.
- **Perceived Latency** — субъективное ощущение скорости до первого видимого признака работы.
- **Skeleton Screen** — placeholder, повторяющий будущую структуру ответа.
- **Progressive Reveal** — постепенное раскрытие готового контента.
- **Context Payload** — структурированные данные для перехода из ответа в tutor.
- **Session Analytics** — сводка завершённой flashcard-сессии.
- **Visual Continuity** — сохранение контекста и ориентации при переходе между режимами.
- **Trust Surface** — область UI, где Learner видит источники, confidence и причину следующего шага.

## Requirement 1: Answer, Context and Analytics Contracts

**User Story:** Как developer, я хочу иметь typed parser/serializer контракты для UX-данных, чтобы UI-полировка не держалась на хрупком markdown/string parsing.

### Acceptance Criteria

1. THE System SHALL provide `AnswerObject` with `text`, `sources`, `confidence`, `metadata`.
2. THE System SHALL provide `ContextObject` with `question`, `topic`, `sources`, `confidence`, `learner_state`.
3. THE System SHALL provide `SessionStatsObject` with `grades_distribution`, `duration`, `velocity`, `retention_predictions`, `insufficient_data`.
4. FOR valid objects, serialize → parse SHALL preserve semantic equivalence.
5. WHEN input is malformed, parsers SHALL return descriptive errors or explicit missing fields.
6. Parser modules SHALL not instantiate LLM/embedding clients and SHALL not read env directly.
7. Persistence of analytics SHALL go through `app/user_state.py` APIs and `_with_db()`, not direct SQLite connections in services.

## Requirement 2: Wait UX Improvements (MoT #2 First Answer)

**User Story:** Как Learner, я хочу видеть прогресс во время ожидания первого ответа, чтобы не чувствовать, что система зависла.

### Acceptance Criteria

1. WHEN Learner отправляет вопрос, THE System SHALL show first visible feedback within 100ms.
2. WHILE the answer is being prepared, THE System SHALL display a stage-aware progress indicator.
3. WHEN final answer data is available, THE System SHALL reveal content progressively without layout jump.
4. THE System SHALL target first meaningful content within 2 seconds for normal local scenarios.
5. Typewriter/progressive reveal SHALL have an accessible fallback that can render instantly.
6. Skeleton structure SHALL match the final answer layout enough to preserve visual stability.
7. Errors/timeouts SHALL replace the wait state with a clear retry path, not a silent spinner.

## Requirement 3: Seamless Tutor Handoff (MoT #3 Transition to Tutor)

**User Story:** Как Learner, я хочу плавно переходить от ответа к тьютору с сохранением контекста, чтобы не терять нить обучения.

### Acceptance Criteria

1. WHEN Learner chooses "Учить эту тему 5 минут", THE System SHALL create a validated `ContextObject`.
2. `ContextObject` SHALL include original question, topic/concepts, sources, confidence and learner-state snapshot when available.
3. THE UI SHALL preserve visual continuity during the transition and avoid a blank intermediate state.
4. WHEN tutor mode opens, THE UI SHALL show a concise context summary.
5. THE first tutor step SHALL explicitly connect to the original answer/topic.
6. IF context is incomplete, THE System SHALL ask for only missing information or continue with a transparent degraded state.
7. The handoff SHALL pass through existing guardrails/input validation at the entry point.

## Requirement 4: Celebration UX (MoT #9 Concept Graduation)

**User Story:** Как Learner, я хочу видеть выразительное подтверждение завершения темы, чтобы ощущать достижение и мотивацию продолжать.

### Acceptance Criteria

1. WHEN Learner reaches mastery ≥80% for a concept/topic, THE System SHALL show a graduation surface.
2. The graduation surface SHALL include topic title, final mastery, session count and time spent when available.
3. The UI SHALL create/persist an achievement badge through existing persistence boundaries.
4. Celebration animation SHALL be skippable and SHALL not block the next action.
5. THE System SHALL offer a primary next action: next topic, review weak points, or return home.
6. Missing metric data SHALL degrade to a simpler success surface rather than failing the flow.

## Requirement 5: Flashcard Session Analytics (MoT #12 Flashcard Review)

**User Story:** Как Learner, я хочу видеть понятную статистику после повторения карточек, чтобы понимать прогресс и следующий шаг.

### Acceptance Criteria

1. WHEN a review session ends, THE System SHALL show a session summary.
2. The summary SHALL include Again/Hard/Good/Easy distribution with counts and percentages.
3. The summary SHALL include learning velocity when duration is valid.
4. The summary SHALL include 7-day due timeline when review predictions are available.
5. IF reviewed cards <5, THE System SHALL label advanced analytics as insufficient data.
6. WHEN Again count ≥3, THE System SHALL offer "Разобрать сложные темы".
7. Session analytics history SHALL be available through the Progress surface.

## Requirement 6: Home Hub Visual Hierarchy (MoT #13 Home Mode Selection)

**User Story:** Как Learner, я хочу быстро понимать, куда идти дальше на главном экране, чтобы не тратить усилие на выбор режима.

### Acceptance Criteria

1. THE System SHALL show the core modes in a stable, scan-friendly layout.
2. IF an unfinished session exists, THE System SHALL prioritize a resume card before generic mode selection.
3. IF flashcards are due, THE System SHALL highlight the flashcard action with a due badge.
4. Mode cards/buttons SHALL have clear hover/focus states and keyboard-accessible behavior.
5. Visual hierarchy SHALL use size, position, contrast and labels consistently with existing Streamlit theme.
6. The implementation SHALL avoid decorative clutter and nested card-in-card layouts.

## Cross-Cutting Requirements

1. All implementation tasks SHALL use project configuration through `app/config.py`.
2. LLM and embeddings SHALL remain behind `app/provider.py`.
3. Prompts SHALL stay in `app/prompts.py`.
4. HTTP endpoint logic SHALL remain in `app/routers/*`.
5. No direct SQLite connections outside `app/user_state.py`.
6. No bare `except`; broad `except Exception` requires `# noqa: BLE001` and justification.
7. Streamlit UX changes SHALL preserve graceful fallback for reruns and session-state resets.
8. Targeted tests only; full suite only on explicit request.

## Out of Scope

- New LLM provider integrations.
- Database migrations unless a later implementation package proves existing persistence insufficient.
- Mobile-first redesign.
- A/B testing or telemetry infrastructure.
- Replacing Streamlit with another frontend.
