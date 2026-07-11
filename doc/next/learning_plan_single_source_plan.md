# План обучения: единый источник и честные шаги — Implementation Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения и не changelog: перед работой по кандидату проверяй код, тесты и актуальные правки в runtime-репозитории.

Owner: product / learning experience

Source: эволюционный разбор hometutor «План обучения: стол, который забывает, где вы сидите» (`doc/presentations/evolutionary_analyses/07_learning_plan.html`).

Related runtime areas:
- `app/ui/home_hub.py`
- `app/ui/topics_tab_plan_subtab.py`
- `app/learning_plan_state.py`
- `app/knowledge_planning.py`
- `app/learning_plan_generation.py`
- `app/telegram_notifications.py`
- `app/ui/pages/3_Мой_прогресс.py`
- `app/routers/dashboard.py`
- `app/ui/knowledge_graph_d3_analysis.py`
- `app/ssr_weekly_planner.py`

## Как использовать этот документ

Кандидаты ниже — небольшие независимые или почти независимые изменения для runtime-репозитория `hometutor`. Каждый кандидат должен начинаться с короткой проверки evidence: строки могли сместиться, а часть поведения могла быть уже исправлена другой веткой.

Главный принцип волны: не делать еще один «план рядом с планом». Исправления должны уменьшать число конкурирующих источников правды и делать путь ученика проверяемым: цель → таблица → выбранный шаг → завершение → тот же прогресс в сегодняшнем плане.

## Суть разбора

В продукте уже есть сильная заготовка: Adaptive Daily Plan выглядит как хороший эталон ежедневного маршрута, а табличный «План обучения» удобен как формат курса. Но сейчас это разные голоса:

- табличный план генерируется LLM как markdown-таблица;
- прогресс по нему извлекается regex-парсером списков/заголовков, который не понимает строки таблицы;
- Telegram и My Progress могут брать «сегодня» из другого сервиса;
- weekly-панель в графе и `ssr_weekly_planner.py` выглядят как отдельные, слабо связанные источники плана;
- зависимости и бюджет времени присутствуют в тексте, но не подтверждаются структурно.

Цель detail-plan: сохранить красивую таблицу, но сделать ее структурой, а не декорацией.

## Волна-кандидат A: `wave-learning-plan-table-integrity` (P0)

### Кандидат A1 — Парсить markdown-таблицу как шаги плана

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** S · **Риск:** low/medium

**Проблема.** `LEARNING_PLAN_PROMPT` просит модель вернуть markdown-таблицу, но `learning_plan_steps_from_markdown()` извлекает шаги только из списков, нумерации и заголовков. В результате «текущий шаг», resume card и downstream-превью могут видеть не строку плана, а сырой markdown или неправильный фрагмент.

**Evidence:**
- `app/prompts/_impl.py` — prompt задает таблицу `| # | Тема | Документ(ы) | Ключевые концепции | Зависимости | Время (ч) |`.
- `app/learning_plan_state.py` — `learning_plan_steps_from_markdown()` сейчас ориентирован на regex для списков/заголовков.
- `app/ui/topics_tab_plan_subtab.py` — сохраняет `learning_plan_markdown` и использует parsed steps.
- `app/ui/home_hub.py` — resume card показывает текущий шаг из сохраненного плана.

**Proposed change:**
1. Добавить в `app/learning_plan_state.py` распознавание markdown-таблицы с колонками плана.
2. Каждую data-row превращать в отдельный clean step: topic/title как основной текст, документы/концепции/время — как структурные поля или аккуратный summary, без символов `|`.
3. Старый regex-парсер оставить fallback для legacy-планов без таблицы.
4. Добавить targeted-тесты на таблицу, fallback-список и отсутствие raw pipe в step text.

**Files:**
- `app/learning_plan_state.py`
- `tests/test_learning_plan_state.py` или ближайший существующий тест по learning plan state

**DoD:**
- Количество распознанных шагов равно количеству data-row в таблице.
- Step text не содержит markdown-разделителей `|`.
- Старые планы списком/заголовками продолжают парситься.

**Doc-sync:** нет, если UI-визуально не меняется; иначе `docs/user_guide.md`.

**Dependencies:** нет.

### Кандидат A2 — Превью карточек строить из структуры, а не из догадок

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** S/M · **Риск:** medium

**Проблема.** Карточки предпросмотра плана могут наследовать ошибку A1: если source markdown распарсен как сырой блок, карточка становится шумной и перестает быть надежной точкой входа.

**Evidence:**
- `app/ui/topics_tab_plan_subtab.py` — `_preview_cards_from_plan` строит карточки по markdown/steps.
- `app/learning_plan_state.py` — текущий parser не гарантирует table rows как атомарные шаги.

**Proposed change:**
1. После A1 переиспользовать общий parser/row model для `_preview_cards_from_plan`.
2. Для заголовка карточки брать `Тема`.
3. Для вторичного текста брать `Ключевые концепции` или documents, но не сырой markdown.
4. Для времени отображать нормализованное значение из колонки `Время (ч)` при наличии.

**Files:**
- `app/ui/topics_tab_plan_subtab.py`
- `app/learning_plan_state.py` если потребуется общий helper
- targeted UI/state tests

**DoD:**
- Preview cards по markdown-таблице совпадают со строками таблицы.
- В карточках нет raw markdown table syntax.
- Legacy fallback сохраняется.

**Doc-sync:** нет, если меняется только качество представления.

**Dependencies:** A1.

### Кандидат A3 — Один источник «что делать сегодня» для Mission Control, Telegram и My Progress

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** M · **Риск:** medium/high

**Проблема.** Пользователь может видеть один «сегодняшний» план в Mission Control / Adaptive Daily Plan и другой в Telegram или My Progress, потому что каналы используют разные сервисы планирования.

**Evidence:**
- `app/ui/home_hub.py` — `render_adaptive_plan_hub()` показывает Adaptive Daily Plan.
- `app/learning_plan_generation.py` — `DynamicLearningPlan.generate_personalized_plan(days=7)` строит отдельный weekly/dynamic plan.
- `app/telegram_notifications.py` — daily reminder берет план через `plan_service.generate_personalized_plan()` и отправляет `Сегодня: {topic}`.
- `app/routers/dashboard.py` и `app/ui/pages/3_Мой_прогресс.py` — AI Coach / progress могут показывать план из того же отдельного сервиса.

**Proposed change:**
1. Выделить или переиспользовать существующий helper, который возвращает primary item из сохраненного Adaptive Daily Plan / Mission Control.
2. Telegram daily reminder для формулировки «Сегодня» должен брать этот primary item.
3. `coach_plan` можно оставить как weekly analytics, но назвать и отрендерить так, чтобы он не конкурировал с «Планом на сегодня».
4. Добавить тест на совпадение Telegram topic с primary block Mission Control при одинаковом user state.

**Files:**
- `app/telegram_notifications.py`
- `app/routers/dashboard.py` при необходимости уточнить контракт
- `app/ui/pages/3_Мой_прогресс.py` при необходимости уточнить copy/section
- общий helper в уже существующем модуле, если он есть
- targeted tests по notifications/dashboard

**DoD:**
- Один и тот же primary learning item используется для «сегодня» в Mission Control и Telegram.
- Weekly/coach plan не исчезает, но не называется сегодняшним источником правды.
- При отсутствии сохраненного daily plan поведение graceful: fallback явно помечен как fallback.

**Doc-sync:** `docs/user_guide.md` — объяснить разницу «План на сегодня» vs weekly/coach outlook.

**Dependencies:** нет, но лучше после A1/A2.

## Волна-кандидат B: `wave-learning-plan-graph-truth` (P1)

### Кандидат B1 — Зависимости и порядок брать из графа, а не просить LLM угадать

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** M/L · **Риск:** medium

**Проблема.** Колонка «Зависимости» выглядит авторитетно, но для табличного Learning Plan она в основном является текстовым результатом prompt. При этом в системе уже есть graph/topological ordering для dynamic plan.

**Evidence:**
- `app/learning_plan_generation.py` — dynamic plan использует `topological_sort(all_ids)`.
- `app/knowledge_planning.py` — planning context ограничен небольшим числом chunks, что делает LLM-зависимости особенно хрупкими.
- `app/ui/topics_tab_plan_subtab.py` — checkbox «Учитывать прогресс» по evidence был default false.

**Proposed change:**
1. Если knowledge graph доступен, сначала построить deterministic outline: topics, prerequisite links, suggested order.
2. LLM использовать для readable descriptions/key concepts/hours, но не как единственный источник порядка и зависимостей.
3. В UI auto-enable «Учитывать прогресс» при наличии graph/progress state; если пользователь выключает, copy должно объяснять, что это free-form план.
4. Добавить тесты на порядок: зависимый узел не появляется раньше prerequisites.

**Files:**
- `app/knowledge_planning.py`
- `app/learning_plan_generation.py`
- `app/ui/topics_tab_plan_subtab.py`
- `app/prompts/_impl.py` только если нужно изменить prompt contract
- targeted tests по planning/generation

**DoD:**
- При наличии graph зависимости в таблице соответствуют graph edges/toposort.
- LLM не может переставить prerequisite после dependent topic без явного fallback/warning.
- Default UI ведет пользователя к graph-aware плану.

**Doc-sync:** `docs/user_guide.md` — описать, что зависимости основаны на карте знаний, когда она доступна.

**Dependencies:** A1 желательно, но не строго.

### Кандидат B2 — Проверять бюджет времени после генерации

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** M · **Риск:** medium

**Проблема.** Время сейчас может быть только частью prompt: модель видит бюджет, но итоговая таблица не проверяется на сумму часов. В dynamic plan уже есть `_trim_plan_by_budget`, но это не закрывает tabular Learning Plan.

**Evidence:**
- `app/learning_plan_generation.py` — `_trim_plan_by_budget` существует для dynamic plan.
- `app/prompts/_impl.py` — table prompt содержит колонку `Время (ч)`.
- `app/ui/topics_tab_plan_subtab.py` — пользователь задает budget, но post-check для LLM table нужно подтвердить перед реализацией.

**Proposed change:**
1. Переиспользовать table parser из A1 для извлечения `Время (ч)`.
2. Суммировать часы и сравнивать с `time_budget_hours`.
3. Если сумма превышает бюджет: либо показать warning и предложить пересобрать, либо автоматически trim/revise по локальному правилу. Выбрать один UX-путь в задаче реализации.
4. Добавить тест на over-budget и within-budget table.

**Files:**
- `app/learning_plan_state.py`
- `app/ui/topics_tab_plan_subtab.py`
- возможно `app/knowledge_planning.py`
- targeted tests

**DoD:**
- UI не показывает over-budget table как будто она соответствует бюджету.
- Проверка работает без LLM-вызова в тестах.
- Невалидные/пустые значения времени дают graceful warning, а не crash.

**Doc-sync:** `docs/user_guide.md` — коротко описать предупреждение по бюджету.

**Dependencies:** A1.

## Волна-кандидат C: `wave-learning-plan-language-unification` (P2)

### Кандидат C1 — Развести язык «программа курса» и «план на сегодня»

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** M · **Риск:** medium

**Проблема.** В интерфейсе слово «план» используется для разных сущностей: долгосрочная таблица курса, daily adaptive route, coach/weekly outlook. Это создает ощущение, что продукт забывает, где пользователь находится.

**Evidence:**
- `app/ui/topics_tab_plan_subtab.py` — tabular Learning Plan.
- `app/ui/home_hub.py` — Adaptive Daily Plan.
- `app/routers/dashboard.py`, `app/ui/pages/3_Мой_прогресс.py` — coach plan/progress surfaces.

**Proposed change:**
1. В UI-copy закрепить термины: например, «Программа обучения» для table/course plan и «План на сегодня» для daily adaptive plan.
2. Completion выбранного шага программы должен обновлять сигнал, который видит daily plan/mastery loop.
3. Не менять архитектуру за один PR, если можно начать с copy + state bridge для completion signal.

**Files:**
- UI modules above
- state/progress helper only if needed
- targeted tests/snapshots if есть

**DoD:**
- Пользователь видит разные горизонты планирования как связанные, но не взаимозаменяемые.
- Завершение шага программы отражается в следующем daily/adaptive контексте.

**Doc-sync:** `docs/user_guide.md`.

**Dependencies:** A3 желательно.

### Кандидат C2 — Решить судьбу weekly-панели графа и ghost planner

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** M/L · **Риск:** medium

**Проблема.** Weekly-панель в D3 graph и `ssr_weekly_planner.py` выглядят как еще один слой планирования. Если они не подключены к маршруту ученика, они увеличивают шум и недоверие.

**Evidence:**
- `app/ui/knowledge_graph_d3_analysis.py` — `build_weekly_plan` формирует weekly cards.
- `assets/knowledge_graph_d3_template.html` — panel `pp-cards`; click bridge есть для graph nodes, но weekly cards нужно проверить на реальную интерактивность.
- `app/ssr_weekly_planner.py` — `generate_weekly_schedule` существует отдельно.
- `docs/ssr_ml_weekly_planner_archive.md` — архивный статус weekly planner.

**Proposed change:**
1. Выбрать один путь: connect или remove.
2. Connect path: weekly cards кликабельны и ведут в тот же tutor/adaptive flow, используют общий source для topics/progress.
3. Remove path: убрать/скрыть неподключенную панель, оставить граф без ложного обещания weekly route.
4. Для `ssr_weekly_planner.py`: либо подключить к актуальному weekly/coach story, либо удалить/архивировать код согласно conventions.

**Files:**
- `app/ui/knowledge_graph_d3_analysis.py`
- `assets/knowledge_graph_d3_template.html`
- `app/ssr_weekly_planner.py`
- docs archive/user guide as needed
- targeted tests по graph template/planner

**DoD:**
- Нет видимой weekly-панели, которая не ведет к действию.
- Нет активного planner-кода с архивным статусом без явного владельца.
- Пользовательский маршрут не получает четвертый конкурирующий источник плана.

**Doc-sync:** `docs/user_guide.md`; archive docs if code is removed or reclassified.

**Dependencies:** C1 желательно.

## Рекомендованный порядок реализации

1. A1 — сначала сделать таблицу настоящей структурой.
2. A2 — затем привести карточки/preview к той же структуре.
3. A3 — выровнять «сегодня» между Mission Control, Telegram и My Progress.
4. B1 — закрепить порядок и зависимости через graph.
5. B2 — добавить честный контроль бюджета времени.
6. C1 — унифицировать язык горизонтов планирования.
7. C2 — подключить или убрать оставшиеся weekly/ghost surfaces.

## Метрики приемки волны

- 100% generated Voice B plans: recognized steps count equals markdown table data-row count.
- 0 resume/current-step карточек с raw `|` из markdown-таблицы.
- 100% daily Telegram topics match Mission Control primary daily block for the same user/day.
- 0 видимых weekly/plan surfaces без кликабельного действия или явного статуса analytics/fallback.

## Kill switches и ограничения

- Если markdown-table parser встречает нестандартную таблицу, он должен падать в legacy fallback, а не ломать план.
- Если graph отсутствует, B1 должен явно показывать fallback free-form plan, а не имитировать graph-backed зависимости.
- Если unified today source временно недоступен, Telegram должен отправлять graceful fallback без обещания, что это тот же Mission Control item.
- Не смешивать в одном PR архитектурное объединение всех планов и copy cleanup: лучше маленькие проверяемые кандидаты.

## Связанные документы

- `doc/presentations/evolutionary_analyses/07_learning_plan.html`
- `doc/presentations/evolutionary_analyses/README.md`
- `doc/next/infographics_living_map_plan.md` — соседний detail-plan по living map/graph surfaces.
