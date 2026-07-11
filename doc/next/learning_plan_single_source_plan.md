# План обучения: единый источник и честные шаги — Implementation Plan

Updated: 2026-07-11

Status: волны A и B `shipped` (реализованы в runtime-репозитории hometutor
коммитами 165–176, июль 2026), волна C `shipped` (2026-07-11:
C1 copy + bridge, C2 ssr_weekly_planner archived, KG guard confirmed).
Это не SSoT исполнения и не changelog; перед работой по любому пункту
проверяй код, тесты и актуальные правки.

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
- `app/ui/knowledge_graph_d3.py`
- `app/ui/course_prepare_view.py`
- `app/ssr_weekly_planner.py`
- `app/ssr_weekly_narrative.py`

## Как использовать этот документ

Кандидаты ниже — небольшие независимые или почти независимые изменения для runtime-репозитория `hometutor`. Каждый кандидат должен начинаться с короткой проверки evidence: строки могли сместиться, а часть поведения могла быть уже исправлена другой веткой.

Главный принцип волны: не делать еще один «план рядом с планом». Исправления должны уменьшать число конкурирующих источников правды и делать путь ученика проверяемым: цель → таблица → выбранный шаг → завершение → тот же прогресс в сегодняшнем плане.

## Суть разбора

В продукте уже есть сильная заготовка: Adaptive Daily Plan выглядит как хороший эталон ежедневного маршрута, а табличный «План обучения» удобен как формат курса. После волн A/B ключевые проблемы уже закрыты:

- табличный план генерируется LLM как markdown-таблица — структура парсится;
- прогресс извлекается через `learning_plan_table_steps_from_markdown()` с fallback на списки/заголовки для legacy;
- Telegram и My Progress используют общий источник `get_today_primary_learning_item()` (A3 shipped);
- weekly-панель в графе удалена (C2 partial), `ssr_weekly_planner.py` — изолированный analytic-модуль без UI;
- зависимости проверяются через `_reorder_validator()` + `parse_plan_table()` (B1 shipped);
- бюджет проверяется через `check_budget()` / `BudgetCompliance` без LLM (B2 shipped).

Остаются открытыми волна C: унификация языка горизонтов (C1) и финализация судьбы ghost surfaces (C2).

## Волна-кандидат A: `wave-learning-plan-table-integrity` (P0) — SHIPPED

### Кандидат A1 — Парсить markdown-таблицу как шаги плана

**Статус:** `shipped`

**Приоритет:** P0 · **Усилие:** S · **Риск:** low/medium

**Проблема (реализована).** `LEARNING_PLAN_PROMPT` просит модель вернуть
markdown-таблицу. Ранее `learning_plan_steps_from_markdown()` извлекал шаги
только из списков/нумерации/заголовков. Теперь есть слой распознавания таблицы
с грациозным fallback.

**Evidence (реализация):**
- `app/prompts/_impl.py:221` — prompt задаёт **8 колонок**:
  `| # | Тема | Документ(ы) | Ключевые концепции | Практика | Проверка результата | Зависимости | Время (ч) |`.
  Парсер (алиасы в `_COLUMN_ALIASES`) покрывает также сокращённые варианты.
- `app/user_state_core.py:488` — `learning_plan_steps_from_markdown()`,
  вызываемая из UI, первой зовёт `learning_plan_table_steps_from_markdown()` (:493),
  при пустом результате — fallback на списки/абзацы (:496).
- `app/learning_plan_state.py:127` — `parse_plan_table(plan_md) -> list[LearningPlanStep]`,
  `_clean_cell()` (:105) вычищает `|`, `_COLUMN_ALIASES` мапит заголовки.
- `app/learning_plan_state.py:278` — `steps_from_markdown()`, legacy-парсер
  для списков/нумерации, остаётся fallback-путём.
- `tests/test_learning_plan_state.py` — тесты на таблицу, fallback, clean cells.

**DoD — подтверждён:**
- Количество распознанных шагов равно количеству data-row в таблице.
- Step text не содержит `|`.
- Legacy-планы списком/заголовками продолжают парситься (fallback).

**Комментарий реализации:** модуль `app/learning_plan_state.py` содержит полную
реализацию: `parse_plan_table`, `_clean_cell`, `_COLUMN_ALIASES`,
`hours_summary_from_markdown`, `BudgetCompliance`, `check_budget`. UI вызывает
`learning_plan_steps_from_markdown()` из `user_state_core` (которая внутри
делегирует табличному парсеру). Две функции с похожим именем:
`learning_plan_state.steps_from_markdown()` — только legacy,
`user_state_core.learning_plan_steps_from_markdown()` — table-first с fallback.

### Кандидат A2 — Превью карточек строить из структуры, а не из догадок

**Статус:** `shipped`

**Приоритет:** P0 · **Усилие:** S/M · **Риск:** medium

**Проблема (реализована).** Карточки предпросмотра плана наследовали ошибку A1;
теперь они строятся из struct-полей через общий parser.

**Evidence (реализация):**
- `app/ui/course_prepare_view.py:18` импортирует `preview_cards_from_plan_text`
  из `app.learning_plan_state`.
- `app/learning_plan_state.py:207` — `preview_cards_from_plan_text(plan_md)`:
  парсит таблицу, на каждый `LearningPlanStep` формирует карточку с полями
  topic (заголовок), concepts (вторичный текст), hours (нормализованное время).
- `app/ui/course_prepare_view.py:720` — `_preview_cards_from_plan()` вызывает
  `preview_cards_from_plan_text()`, реализация **не** в `topics_tab_plan_subtab.py`.
- При отсутствии таблицы — fallback на chunk-разбиение legacy markdown.

**DoD — подтверждён:**
- Preview cards по markdown-таблице совпадают со строками таблицы.
- В карточках нет raw `|`.
- Legacy fallback сохраняется.

**Dependencies:** A1.

### Кандидат A3 — Один источник «что делать сегодня» для Mission Control, Telegram и My Progress

**Статус:** `shipped` (partial: Telegram + Mission Control unified; coach/weekly
outlook в dashboard и My Progress всё ещё через `generate_personalized_plan`)

**Приоритет:** P0 · **Усилие:** M · **Риск:** medium/high

**Проблема (частично реализована).** Пользователь мог видеть один «сегодняшний»
план в Mission Control / Adaptive Daily Plan и другой в Telegram. Сейчас
Telegram использует общий helper, но dashboard/My Progress — пока нет.

**Evidence (реализация):**
- `app/learning_plan_adaptive.py:100` — `get_today_primary_learning_item()`,
  canonical cross-channel helper. Реэкспортирован через `app/learning_plan_service.py`.
- `app/telegram_notifications.py:47-53` — daily reminder использует
  `get_today_primary_learning_item()`, **не** `plan_service.generate_personalized_plan()`.
- `app/ui/home_hub.py:665` — `render_adaptive_plan_hub()` (определение в
  `app/ui/adaptive_plan_card.py:512` / `adaptive_plan_hub_layout.py`) показывает
  Adaptive Daily Plan.
- `app/routers/dashboard.py:43` и `app/ui/pages/3_Мой_прогресс.py:171` —
  coach/weekly outlook всё ещё через `generate_personalized_plan()`. Это отдельный
  analytic-вызов (не «сегодня»), но copy-разведение из C1 ещё не применено.
- `tests/test_learning_plan_today_source.py` — тест на совпадение Telegram topic
  с Mission Control primary item.

**Что сделано (DoD подтверждён):**
- Один и тот же `get_today_primary_learning_item()` для «сегодня» в Mission Control
  и Telegram.
- Telegram имеет graceful fallback при отсутствии daily plan.
- Weekly/coach plan не исчезает, технически не называется сегодняшним источником.

**Что остаётся (C1 territory):**
- Coach/weekly в dashboard и My Progress всё ещё через `generate_personalized_plan`.
  Это не нарушает today-unification, но copy-разведение «Программа обучения»
  vs «План на сегодня» из C1 сюда ещё не применено.

## Волна-кандидат B: `wave-learning-plan-graph-truth` (P1) — SHIPPED

### Кандидат B1 — Зависимости и порядок брать из графа, а не просить LLM угадать

**Статус:** `shipped`

**Приоритет:** P1 · **Усилие:** M/L · **Риск:** medium

**Проблема (реализована).** Колонка «Зависимости» была текстовым результатом
prompt. Сейчас порядок и зависимости проверяются через `_reorder_validator`,
использующий граф.

**Evidence (реализация):**
- `app/learning_plan_generation.py` — dynamic plan использует `topological_sort(all_ids)`.
- `app/knowledge_planning.py:223-229` — `_reorder_validator()`:
  принимает `parse_plan_table(...)` и `dynamic_plan["plan"]`, возвращает
  `plan_order_warning`. LLM-порядок проверяется/корректируется графом.
- `app/knowledge_planning.py:231-240` — валидация результата через
  `check_budget()` + `hours_summary_from_markdown` (без LLM).
- `app/ui/topics_tab_plan_subtab.py:68` — checkbox «Учитывать прогресс»:
  `value=_graph_has_concepts` — **auto-enable** при наличии графа,
  help-текст объясняет free-form режим. Не default false.

**DoD — подтверждён:**
- При наличии graph зависимости в таблице проверяются через toposort.
- `_reorder_validator` не даёт LLM переставить prerequisite без fallback/warning.
- Default UI ведёт пользователя к graph-aware плану (auto-enable checkbox).

**Dependencies:** A1.

### Кандидат B2 — Проверять бюджет времени после генерации

**Статус:** `shipped`

**Приоритет:** P1 · **Усилие:** M · **Риск:** medium

**Проблема (реализована).** Ранее итоговая таблица не проверялась на сумму часов;
теперь `check_budget()` / `BudgetCompliance` работают без LLM.

**Evidence (реализация):**
- `app/learning_plan_state.py:229` — `hours_summary_from_markdown(plan_md)`
  извлекает часы через table parser (алиасы `Время (ч)` / `hours` / `часы`).
- `app/learning_plan_state.py:250` — класс `BudgetCompliance` с полями
  `total_hours`, `budget_hours`, `is_over_budget`, `warning`.
- `app/learning_plan_state.py:261` — `check_budget(plan_md, time_budget_hours)`
  возвращает `BudgetCompliance | None`.
- `app/ui/topics_tab_plan_subtab.py:215` — UI вызывает `check_budget()` и
  отображает warning при превышении.
- `app/knowledge_planning.py:231-240` — `check_budget()` + `hours_summary_from_markdown`
  в пайплайне генерации, без LLM.

**DoD — подтверждён:**
- UI не показывает over-budget table как соответствующую бюджету.
- Проверка работает без LLM-вызова в тестах.
- Невалидные/пустые значения времени дают graceful warning.

**Dependencies:** A1.

## Волна-кандидат C: `wave-learning-plan-language-unification` (P2)

### Кандидат C1 — Развести язык «программа курса» и «план на сегодня»

**Статус:** `shipped` (2026-07-11: copy unified, bridge added)

**Приоритет:** P2 · **Усилие:** M · **Риск:** medium

**Проблема (решена).** В интерфейсе слово «план» использовалось для разных
сущностей. Теперь: «Программа обучения» = table/course plan,
«План на сегодня» = daily adaptive.

**Evidence (реализация):**
- `app/ui/adaptive_daily_plan_layout.py:238,244` — `"🎯 Adaptive Daily Plan"`
  → `"📅 План на сегодня"` (copy unified).
- `app/adaptive_plan.py:436` — `build_adaptive_daily_plan()` injects
  `learning_plan_context` из `get_latest_learning_plan_resume()` (bridge step → plan).
- `app/ui/adaptive_plan_hub_layout.py:69-84` — UI отображает learning plan context
  (тема, шаг, прогресс) под заголовком «План на сегодня».
- `app/ui/topics_tab_plan_subtab.py` — везде «Программа обучения», не «план».
- `app/ui/adaptive_plan_hub_layout.py` — везде «План на сегодня», не "Adaptive Plan".

**DoD — подтверждён:**
- Пользователь видит разные горизонты планирования: «Программа обучения» =
  долгосрочная таблица, «План на сегодня» = daily adaptive.
- Завершение шага программы обновляет `learning_plan_context`, который видит
  следующий daily план (bridge `get_latest_learning_plan_resume()` →
  `build_adaptive_daily_plan()` → UI).
- Bridge без LLM, без архитектурных изменений.

### Кандидат C2 — Решить судьбу weekly-панели графа и ghost planner

**Статус:** `shipped` (2026-07-11: remove path для ssr_weekly_planner)

**Приоритет:** P2 · **Усилие:** M/L · **Риск:** medium

**Проблема (решена).** `ssr_weekly_planner.py` — ghost surface с 0 внешних
вызовов. `ssr_weekly_narrative.py` активно используется в Progress (не ghost).
Weekly overlay в графе уже удалён (C2 guard).

**Evidence (реализация):**
- `doc/archive/code/ssr_weekly_planner.py` — модуль перемещён в архив
  (C2, 2026-07-11, 0 внешних вызовов).
- `app/ui/knowledge_graph_d3.py:577-579` — weekly plan overlay **удалён**,
  ключ `"weekly_plan": []` с C2-guard комментарием.
- `app/ui/weekly_study_narrative_ui.py` — активно используется в
  `3_Мой_прогресс.py:77` и `dashboards_progress.py:453` (не ghost).
- `scripts/check_dead_modules.py:24,42` — `app.ssr_weekly_planner` закомментирован.

**DoD — подтверждён:**
- `ssr_weekly_planner.py` архивирован — больше не в `app/`.
- Weekly overlay в графе удалён (C2 guard).
- `weekly_study_narrative_ui.py` остаётся активным (Progress surface).
- Нет четвёртого конкурирующего источника плана.

## Рекомендованный порядок реализации (всё выполнено)

1. ~~A1~~ — shipped (table → structure).
2. ~~A2~~ — shipped (cards → structure).
3. ~~A3~~ — shipped (today source unified; coach/weekly отдельно).
4. ~~B1~~ — shipped (graph order + validator).
5. ~~B2~~ — shipped (budget check без LLM).
6. ~~C1~~ — shipped (copy + bridge step→daily plan).
7. ~~C2~~ — shipped (ssr_weekly_planner archived, KG guard confirmed).

## Метрики приемки волны

- ✅ A1: 100% generated Voice B plans — recognized steps count equals markdown table data-row count.
- ✅ A1/A2: 0 resume/current-step карточек с raw `|` из markdown-таблицы.
- ✅ A3: 100% daily Telegram topics match Mission Control primary daily block (тест `test_learning_plan_today_source.py`).
- ✅ C1: Завершение шага программы отображается в learning_plan_context daily plan'а.
- ✅ C2: ssr_weekly_planner.py архивирован; KG weekly overlay удалён.

## Kill switches и ограничения

- Если markdown-table parser встречает нестандартную таблицу, он падает в legacy fallback — реализовано в `learning_plan_state.py:134` graceful fallback.
- Если graph отсутствует, B1 показывает free-form план через `_reorder_validator` — реализовано.
- Если unified today source (`get_today_primary_learning_item`) временно недоступен, Telegram отправляет graceful fallback — реализовано.
- Не смешивать в одном PR архитектурное объединение всех планов и copy cleanup: лучше маленькие проверяемые кандидаты.

## Связанные документы

- `doc/presentations/evolutionary_analyses/07_learning_plan.html`
- `doc/presentations/evolutionary_analyses/README.md`
- `doc/next/infographics_living_map_plan.md` — соседний detail-plan по living map/graph surfaces.
