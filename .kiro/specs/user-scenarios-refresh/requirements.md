# Requirements Document

## Introduction

Этот документ описывает требования к актуализации `doc/user_scenarios.md` на основе закрытых волн из `doc/backlog_registry.yaml`. Проект hometutor прошёл значительный путь развития: закрыто 146+ пакетов, реализованы все 13 моментов истины CJM, проведён большой рефакторинг UI. Однако документ с пользовательскими сценариями содержит только 22 сценария и не отражает многие важные UX-улучшения и функции из закрытых волн.

**Главная цель:** актуализировать `doc/user_scenarios.md`, добавив новые wow-сценарии для важных закрытых user stories и обновив существующие сценарии, которые устарели после рефакторинга.

**Стратегический контракт:**
- **Feature ID:** `user-scenarios-refresh`
- **Status:** `proposed`
- **North Star:** Документ user_scenarios.md полностью отражает текущие возможности продукта и wow-моменты из закрытых волн.
- **Scope shape:** Анализ закрытых волн → выявление gaps → добавление новых сценариев → обновление устаревших.
- **Non-goal:** не переписывать весь документ с нуля, не добавлять сценарии для proposed/deferred волн, не менять структуру существующих сценариев без явной необходимости.

## Glossary

- **User Scenario** — живая история пользователя с конкретной целью и способом системы её решить.
- **Wave** — волна разработки, объединяющая 1-4 связанных пакета с общей north_star метрикой.
- **Closed Wave** — волна со статусом `completed` в `doc/backlog_registry.yaml`.
- **Wow-момент** — ключевой момент пользовательского опыта, который вызывает положительную эмоциональную реакцию.
- **Gap** — важная функция или UX-улучшение из закрытой волны, не описанная в существующих сценариях.
- **MoT (Moment of Truth)** — критическая точка пути пользователя из CJM.
- **SSR (Smart Study Router)** — умный маршрутизатор, показывающий один лучший следующий шаг.
- **Mission Control** — новый главный экран с SSR-баннером и семью destination tiles.

## Requirements

### Requirement 1: Анализ закрытых волн и выявление gaps

**User Story:** Как technical writer, я хочу проанализировать все закрытые волны из backlog_registry.yaml, чтобы выявить важные функции и UX-улучшения, не описанные в user_scenarios.md.

#### Acceptance Criteria

1. THE System SHALL identify all waves with `status: completed` in `doc/backlog_registry.yaml`.
2. FOR EACH closed wave, THE System SHALL extract `theme`, `north_star`, `entry_mot`, `exit_mot`, and `packages`.
3. THE System SHALL compare closed wave themes against existing 22 scenarios in `doc/user_scenarios.md`.
4. THE System SHALL identify gaps: closed waves with significant user-facing impact not covered by existing scenarios.
5. THE System SHALL prioritize gaps by user impact: waves affecting MoT #1-#14, UX breakthrough moments, and cross-loop improvements.
6. THE System SHALL exclude infrastructure-only waves (`entry_mot: "infra"` or `entry_mot: "platform"`) unless they have direct user-visible impact.
7. THE Analysis SHALL produce a structured list of gaps with wave_id, theme, north_star, and recommended scenario type.

### Requirement 2: Новые сценарии для приоритетных gaps

**User Story:** Как learner, я хочу видеть в документации сценарии для всех важных wow-моментов продукта, чтобы понимать, как использовать новые возможности.

#### Acceptance Criteria

1. FOR EACH prioritized gap, THE System SHALL create a new scenario following the existing template structure.
2. EACH new scenario SHALL include: title, context, persona, time estimate, main question, steps, under-the-hood explanation, success signal.
3. NEW scenarios SHALL be inserted in appropriate sections: "Первые шаги", "Учебный ритм", "Мастерство", or "Power user".
4. THE System SHALL assign unique scenario numbers (23, 24, 25...) to new scenarios.
5. THE System SHALL update the navigation table at the beginning of the document with new scenario links.
6. THE System SHALL update the "Карта уровней" table if new scenarios affect level distribution.
7. NEW scenarios SHALL reference related YAML artifacts in `doc/scenarios/` when they exist.

### Requirement 3: Обновление устаревших сценариев

**User Story:** Как learner, я хочу, чтобы существующие сценарии отражали текущее состояние UI после рефакторинга, чтобы не путаться при использовании продукта.

#### Acceptance Criteria

1. THE System SHALL identify scenarios affected by closed waves with UI changes (e.g., `wave-home-mode-selection-v2`, `wave-mission-control-home`).
2. FOR EACH affected scenario, THE System SHALL update steps, screenshots references, and UI element names to match current implementation.
3. THE System SHALL preserve the core narrative and persona of existing scenarios while updating technical details.
4. WHEN a scenario references deprecated UI elements, THE System SHALL replace them with current equivalents.
5. THE System SHALL maintain backward compatibility: old scenario numbers and titles SHALL NOT change unless explicitly required.
6. THE System SHALL add "Обновлено после [wave_id]" notes to significantly changed scenarios.
7. THE System SHALL verify that updated scenarios align with current `app/ui/` implementation.

### Requirement 4: Специальные сценарии для ключевых волн

**User Story:** Как product owner, я хочу выделить wow-моменты из ключевых закрытых волн (UX breakthrough, Smart Study Router, Mission Control), чтобы они стали визитной карточкой продукта.

#### Acceptance Criteria

1. THE System SHALL create dedicated scenarios for these priority waves:
   - `wave-ux-breakthrough-2026-05` (если не полностью покрыт сценарием 15)
   - `wave-smart-study-router` (расширение сценариев 21-22)
   - `wave-mission-control-home` (новый сценарий)
   - `wave-interactive-tour` (проверка покрытия сценарием 16)
   - `wave-course-retention-resilience` (дополнение к сценарию 8)
2. EACH priority scenario SHALL highlight the wow-moment: what changed, why it matters, how it feels.
3. THE System SHALL use comparative language: "До: [old behavior]. После: [new behavior]. Результат: [wow-moment]".
4. PRIORITY scenarios SHALL include visual cues: "Сигнал успеха" with specific UI feedback.
5. THE System SHALL link priority scenarios to demo YAML artifacts when available.
6. PRIORITY scenarios SHALL be placed in prominent positions: early in their level or in a dedicated "Wow-моменты" section.
7. THE System SHALL ensure priority scenarios are referenced in the navigation table with clear labels.

### Requirement 5: Консистентность и качество документа

**User Story:** Как reader, я хочу, чтобы обновлённый документ сохранял единый стиль, структуру и качество повествования, чтобы легко ориентироваться.

#### Acceptance Criteria

1. ALL new and updated scenarios SHALL follow the existing template: Context, Persona, Time, Main Question, Steps, Under the Hood, Success Signal.
2. THE System SHALL maintain consistent tone: живой, практичный, без маркетинговых клише.
3. THE System SHALL use consistent terminology from the Glossary across all scenarios.
4. THE System SHALL preserve the existing section structure: Философия → Навигация → Карта уровней → Сценарии по уровням → Demo-пакеты → Связанные документы.
5. THE System SHALL update the navigation table to include all new scenarios with correct links.
6. THE System SHALL verify that all internal links work correctly after updates.
7. THE System SHALL ensure the document length remains manageable: target 1500-2000 lines, current 1262 lines.

### Requirement 6: Связь с артефактами и тестами

**User Story:** Как developer, я хочу, чтобы сценарии ссылались на соответствующие YAML-артефакты и e2e-тесты, чтобы проверять их актуальность.

#### Acceptance Criteria

1. FOR EACH scenario with a corresponding YAML in `doc/scenarios/`, THE System SHALL add a "Связанные артефакты" section.
2. THE System SHALL reference e2e tests in `tests/e2e/demos/` when they exist for the scenario.
3. THE System SHALL note when a scenario lacks YAML or e2e coverage: "Автотесты: сценарий пока не покрыт...".
4. THE System SHALL verify that referenced YAML files exist before adding links.
5. THE System SHALL maintain the SSoT contract: scenario numbers SHALL match YAML filenames (scenario_NN_*.yaml).
6. THE System SHALL run `scripts/check_scenario_ids.py` to verify consistency after updates.
7. THE System SHALL document any new scenarios that need YAML artifacts in a separate tracking section.

### Приоритетные закрытые волны для анализа

Следующие волны имеют высокий приоритет для включения в сценарии:

#### Высокий приоритет (обязательно покрыть)

1. **wave-mission-control-home** — новый главный экран с SSR и семью destination tiles
2. **wave-smart-study-router** + **wave-smart-study-router-surface-parity** + **wave-smart-study-router-next-level-***  — умный маршрутизатор (расширение сценариев 21-22)
3. **wave-home-mode-selection-v2** — улучшенный выбор режимов на главной (обновление сценария 18)
4. **wave-course-retention-resilience** — recovery, promise, repair для курсов (дополнение к сценарию 8)
5. **wave-interactive-tour** — интерактивный тур (проверка сценария 16)
6. **ssr-ai-vision-wave-1-foundation** + **ssr-ai-vision-wave-2-explainability** + **ssr-ai-vision-wave-2b-l2-reliability** — AI Vision уровни 1-2 (расширение сценария 22)

#### Средний приоритет (желательно покрыть)

7. **wave-course-learning-v2** — Course Cockpit (E30) с graduation overlay и daily briefing
8. **wave-course-homework-playbook** — homework playbook для курсов
9. **wave-flashcard-polish** — улучшения UX колод
10. **wave-first-answer-ux** — примеры на первом экране
11. **wave-plan-visibility** — diff плана (проверка сценария 17)
12. **wave-agentic-tutor-depth** — mastery-adaptive tutoring (проверка сценария 20)

#### Низкий приоритет (опционально)

13. **wave-quality-defense-***  — eval baseline, adversarial tests (для power users)
14. **wave-non-text-corpus-delivery** — OCR/Docling ingest (для advanced use cases)
15. **wave-mot2-perceived-latency** — wait UX, two-stage answer (часть UX breakthrough)

### Cross-Cutting Requirements

1. ALL updates SHALL preserve existing scenario numbers and titles unless explicitly required by major changes.
2. THE System SHALL NOT add scenarios for infrastructure-only waves without user-visible impact.
3. THE System SHALL NOT duplicate content: if a wave is already covered by an existing scenario, update that scenario instead of creating a new one.
4. THE System SHALL maintain the document's narrative flow: scenarios should tell a coherent story of the learner's journey.
5. THE System SHALL use real personas (Аня, Марк, Сергей, Елена, Максим) consistently across scenarios.
6. THE System SHALL avoid technical jargon in scenario descriptions: explain concepts in user-friendly language.
7. THE System SHALL ensure all Russian text uses correct grammar, punctuation, and style.

### Out of Scope

- Создание новых YAML-артефактов в `doc/scenarios/` (это отдельная задача).
- Написание новых e2e-тестов для сценариев (это отдельная задача).
- Перевод документа на другие языки.
- Добавление сценариев для proposed/deferred волн.
- Изменение структуры документа (философия, навигация, уровни).
- Создание видео-демонстраций или скриншотов.

### Verification

После обновления документа необходимо выполнить:

1. Проверить консистентность ID сценариев:
   ```bash
   .\.venv\Scripts\python.exe scripts/check_scenario_ids.py
   ```

2. Проверить, что все внутренние ссылки работают (вручную или через markdown linter).

3. Проверить, что длина документа осталась в разумных пределах (1500-2000 строк).

4. Проверить, что все новые сценарии имеют уникальные номера и правильные ссылки в навигационной таблице.

5. Проверить, что обновлённые сценарии соответствуют текущей реализации в `app/ui/`.
