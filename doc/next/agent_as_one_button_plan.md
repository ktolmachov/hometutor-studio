# Agent as One Button — UI Closure Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения — `backlog_registry.yaml`
этим документом не меняется, промоушен волн/пакетов решает владелец.
Owner: product / learning experience
Source: эволюционный разбор hometutor «Агент как одна кнопка» (2026-07-11), формат —
[`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md).
Полный читаемый разбор:
[`../presentations/evolutionary_analyses/04_agent_as_one_button.html`](../presentations/evolutionary_analyses/04_agent_as_one_button.html)
(тот же контент опубликован как HTML-артефакт сессии).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- hometutor: `docs/agent_roadmap.md` — канонический источник архитектуры и волн Wave 0–5;
  этот план **не заменяет** его, а закрывает один конкретный найденный разрыв (Wave 1A–1C
  реализованы, но не подключены к UI) — не путать с более широкими будущими волнами (Wave 3
  role-геттеры, Wave 5 write-tools/HITL), которые остаются в компетенции `agent_roadmap.md`
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan
  разбора №1 (петля памяти); кандидат B1 того плана («→ в карточку» из ответа тьютора)
  использует тот же `add_flashcard()`, что кандидат B2 этого плана
- [`material_as_product_quality_plan.md`](material_as_product_quality_plan.md) — detail-plan разбора №3
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan разбора №2
- hometutor: `docs/user_guide.md`, `docs/api_reference.md`, `docs/architecture.md`, `CLAUDE.md`

## Как использовать этот документ

Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог
промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной.
Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted
tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне
согласованного write-set. Все evidence-ссылки проверены на `hometutor@60b55f3` (`149`).

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`.

## Суть разбора

Агент оценивается не по автономности, а по разнице усилий: сколько кликов и решений
студента заменяет одна кнопка. Аудит показал редкое соотношение для незавершённой
фичи: харнесс (контракты, stop-controller, три продуктовых сценария, персистентность
прогонов) полностью построен и протестирован golden-кейсами, а UI-путь к нему —
единственный настоящий разрыв — отсутствует полностью. `agent_enabled=False` по
умолчанию делает это безопасным, но и бесполезным: три месяца инженерии заканчиваются
тупиком без двери.

---

## Волна-кандидат A: `wave-agent-door` (P0)

**North star (кандидат):** студент видит одну кнопку с понятным обещанием («Собери мне
занятие по этой теме»); клик даёт черновик за один прогон вместо 3–4 ручных экранов;
команда видит историю прогонов, чтобы отлаживать качество на реальных вопросах.

**Kill switch (кандидат):** если открытая кнопка даёт заметный рост стоимости/задержки
(например, p95 стоимости прогона превышает бюджет `agent_max_run_cost_usd` чаще, чем в
5% случаев, или golden-набор регрессирует ниже текущего baseline), скрыть кнопку обратно
за флагом для всех, кроме тестовой группы, не трогая сам харнесс.

### Кандидат A1 — Одна CTA-кнопка «Собрать учебную сессию»

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое (харнесс и контракт ответа готовы; нужен только UI-путь)

**Проблема.** `query_mode="agent"` — единственный вход в полностью работающий харнесс
(3 сценария, 8 read-only инструментов, честный контракт секций) — не устанавливается
нигде в `app/ui`. Ни одна кнопка, CTA или feature-флаг не подключены к готовому пути.

**Evidence:**
- `app/query_service.py:940` — единственная точка входа:
  `if (options.query_mode or "").strip().lower() == "agent" and get_settings().agent_enabled:`.
- Прогон по `app/ui` на предмет `query_mode=` даёт единственное совпадение —
  `query_mode="tutor"` (`app/ui/tutor_chat_session.py:76`); значения `"agent"` нет нигде.
- `app/ui/feature_registry.py:11-19` (`FeatureSpec`) поддерживает поле `requires:
  tuple[str, ...] = ()`; `feature_registry.py:154-158` уже умеет резолвить требование
  `"agent_enabled"` (`if not get_settings().agent_enabled: ...`). Но ни один элемент
  кортежа `FEATURES` (`feature_registry.py:22-...`) не объявлен с
  `requires=("agent_enabled",)` — механизм видимости готов и просто не используется.
- `app/config.py:523` (`agent_enabled: bool = Field(default=False, ...)`) — флаг
  безопасно выключен по умолчанию; включение — per-deployment или per-group решение
  владельца, не блокер для реализации кнопки.
- `app/ui_client.py:40-47` (`fetch_json`) — уже существующий, используемый по всему UI
  HTTP-клиент к локальному API; естественный транспорт для CTA (`POST /ask` с
  `query_mode="agent"`), без изобретения нового клиента.
- Контракт ответа (`## Диагностика`, `## Что изучать сейчас`, `## План на 10–20 минут`,
  `## Проверочные вопросы`, `## Карточки-кандидаты`, `## Следующие шаги`, `## Источники`)
  уже реализован в `app/agent/scenarios.py` (`build_study_session_answer` и парные
  функции для двух других сценариев) — рендерится как обычный markdown-ответ, без
  специального парсера.

**Proposed change:**
1. Новый `FeatureSpec("action:agent_study_session", "Собрать учебную сессию", <tier>,
   ..., requires=("agent_enabled",))` в `FEATURES` — видимость через уже готовый
   механизм, не через ad hoc проверку в UI-коде.
2. CTA-кнопка в Mission Control (кандидат места: рядом с текущими resume-картами,
   `app/ui/mission_control.py`, тот же паттерн, что `render_kg_mission_card`/
   `render_living_konspekt_mission_card`), видимая только когда feature активна.
3. Клик отправляет текущую тему/курс (то, что уже доступно контекстной строке —
   `build_context_row_segments`, `mission_control.py:889`) через `fetch_json("POST",
   "/ask", json={"question": ..., "query_mode": "agent"})`.
4. Результат рендерится как draft-markdown **без записи в базы** — согласовано с
   контрактом Wave 1A (никакого автосохранения без HITL); карточки-кандидаты остаются
   текстом до кандидата A2/B2 этого плана.

**Files:** `app/ui/feature_registry.py`, `app/ui/mission_control.py`, возможно
`app/ui/tutor_chat.py` (второе естественное место CTA — по решению владельца, не
обязательно в этом пакете), targeted tests
(`tests/test_feature_registry.py`, `tests/test_navigation_visibility.py`).

**DoD:**
- При `agent_enabled=true` кнопка видна на Mission Control; при `false` — не видна ни
  разработчику, ни студенту (совпадает с текущим поведением, флаг не меняет дефолт).
- Клик даёт цельный draft-ответ за один прогон без ошибок парсинга контракта секций.
- Regression test фиксирует: `FeatureSpec` с `requires=("agent_enabled",)` скрыт при
  выключенном флаге.

**Doc-sync:** `docs/user_guide.md` (новая CTA, только если флаг включается хотя бы для
одной среды), `docs/agent_roadmap.md` (обновить статус Wave 1A: UI-поверхность
реализована — сейчас там явно написано «не реализовано»).

**Dependencies:** нет — использует только уже существующие API/контракты.

---

### Кандидат A2 — Минимальный read-роутер прогонов агента

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое

**Проблема.** `agent_runs`/`agent_steps` пишутся при каждом прогоне
(`persist_agent_run`, единственный caller — `app/agent/__init__.py:148`), санитайзинг
чувствительных данных уже реализован, но ничто не читает эти данные вне тестов — нет ни
одного роутера, ни одного UI-потребителя. Команда не может проверить, как агент
справляется в проде, кроме как читать SQLite напрямую.

**Evidence:**
- `app/user_state_agent_runs.py:112-137` (`get_agent_run`), `:140-...` (`list_agent_runs`)
  — обе функции полностью реализованы, санитайзинг встроен
  (`_is_sensitive_key`, `_truncate_text`, `_MAX_ITEMS`), но 0 caller'ов вне
  `app/agent/__init__.py` и тестов.
- `app/user_state_db.py:589-613` — схема таблиц `agent_runs`/`agent_steps` уже
  создаётся в `_ensure_schema`.
- `app/api.py:274-294` — паттерн регистрации роутеров с `dependencies=_protected_dependencies`
  для защищённых эндпоинтов; `docs/agent_roadmap.md:148-151` уже называет будущий
  `app/routers/agent.py` с `GET /agent/runs/{run_id}`, `GET /agent/runs` — этот кандидат
  реализует именно эту, давно описанную, но не сделанную часть (без
  `POST /agent/runs/{run_id}/resume` — это Wave 5 HITL, вне scope).

**Proposed change:**
1. Новый `app/routers/agent.py`: `GET /agent/runs?limit=` → `list_agent_runs(limit=...)`,
   `GET /agent/runs/{run_id}` → `get_agent_run(run_id)` (404 при отсутствии).
2. Регистрация в `app/api.py` через `app.include_router(agent_router,
   dependencies=_protected_dependencies)` — тот же паттерн, что у всех защищённых
   роутеров, без нового auth-механизма.
3. Только чтение — никакого `resume`/`retry`/`cancel` в этом пакете (сознательно
   меньше, чем полный будущий контракт из `agent_roadmap.md`).

**Files:** новый `app/routers/agent.py`, `app/api.py`, targeted tests
(`tests/test_api.py` или ближайший router-test, плюс smoke-тест 404 для отсутствующего run_id).

**DoD:** `GET /agent/runs` и `GET /agent/runs/{run_id}` возвращают персистентные данные
без утечки чувствительных полей (санитайзинг уже в слое персистентности, роутер его не
обходит); эндпоинты защищены той же авторизацией, что остальной API.

**Doc-sync:** `docs/api_reference.md` (новые эндпоинты), `docs/agent_roadmap.md`
(обновить §2.2 — роутер реализован, HITL/resume остаётся Wave 5).

**Dependencies:** независим от A1 — можно реализовать в любом порядке; вместе дают
полный цикл «кнопка → прогон → видимая история».

---

## Волна-кандидат B: `wave-agent-trust` (P1)

**North star (кандидат):** прежде чем открывать кнопку массовому студенту, качество
ответов проверено на представительном наборе; черновик агента можно превратить в
действие одним кликом, не расширяя write-доступ самого агента.

### Кандидат B1 — Golden-набор study_session до 8–10 кейсов

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое–среднее (написание кейсов, не кода)

**Проблема.** `eval_data/agent_scenarios_golden_v1.json` содержит 4 кейса (2
`study_session`, 1 `graph_gap_finder`, 1 `living_konspekt_coach`), тогда как
`docs/agent_roadmap.md` называет целью 8–10 кейсов для одного `study_session`. Открывать
кнопку широкому кругу студентов (A1) до расширения набора — значит проверять качество
на живых людях вместо golden-кейсов.

**Evidence:**
- Прямой подсчёт `eval_data/agent_scenarios_golden_v1.json`:
  `Counter({'study_session': 2, 'graph_gap_finder': 1, 'living_konspekt_coach': 1})`.
- `docs/agent_roadmap.md:301-305` — «golden-набор существует... но на дату аудита
  содержит 2 study_session-кейса, а не целевые 8–10; checks: есть источники, quiz
  соответствует теме, карточки не сохраняются, stop_reason корректен».
- `tests/agent/test_agent_golden_cases.py` — существующий раннер golden-кейсов,
  расширение набора не требует нового раннера, только новых кейсов в существующем JSON.

**Proposed change:**
1. Добавить 6–8 новых `study_session` кейсов, покрывающих разные темы/курсы/уровни
   mastery (используя те же четыре проверки, что уже применяются: источники есть, quiz
   соответствует теме, карточки не сохраняются, `stop_reason` корректен).
2. Не менять раннер/чекеры — только расширить данные.
3. Держать это как предусловие для расширения rollout A1 за пределы тестовой группы
   (gate на выкладку, не на код).

**Files:** `eval_data/agent_scenarios_golden_v1.json`.

**DoD:** ≥8 `study_session` кейсов; `tests/agent/test_agent_golden_cases.py` зелёный на
полном наборе.

**Doc-sync:** `docs/agent_roadmap.md` (снять пометку «частично» у Wave 1A evals).

**Dependencies:** независим от A1/A2 технически, но логически — предусловие для
расширения rollout за пределы тестовой группы.

---

### Кандидат B2 — Кнопка «Сохранить как карточку» поверх черновика агента

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое–среднее

**Проблема.** Инструмент `cards.propose` осознанно read/draft — не сохраняет карточки
сам (правильное решение для Wave 1, никакого автосохранения без HITL). Но черновик,
который нельзя принять одним кликом, обесценивает работу агента: студент увидел
«Карточки-кандидаты» в тексте ответа и должен вручную пересоздать их в разделе
Flashcards.

**Evidence:**
- `docs/agent_roadmap.md:167` — `cards.propose`: «кандидатные flashcards/cloze из
  ответа, конспекта или quiz-контекста; **без сохранения** до Wave 5».
- `app/agent/scenarios.py` (`_card_candidates`, секция «## Карточки-кандидаты» в
  контракте `study_session`) — кандидаты уже структурированы как текст в финальном
  ответе.
- `app/user_state_flashcards.py:475-496` (`add_flashcard`) — тот же существующий
  backend-путь, который кандидат B1 плана [[knowledge_fate_memory_loop_plan]] (разбор
  №1) уже предлагает использовать для кнопки «→ в карточку» из ответа тьютора; этот
  пакет — второй потребитель того же примитива, не новый insert-путь.

**Proposed change:**
1. Парсинг секции «## Карточки-кандидаты» из уже структурированного ответа в список
   `front`/`back` пар (кандидаты уже пронумерованы в тексте — см.
   `_card_candidates`/`_numbered_or_default` в `scenarios.py`).
2. Кнопка «Сохранить» рядом с каждым кандидатом (или одна кнопка «Сохранить все») —
   вызывает `add_flashcard()` тем же путём, что и обычное ручное добавление карточки.
3. Не расширять доступ самого агента (`cards.propose` остаётся read/draft) — сохранение
   инициирует и подтверждает студент в UI, не агент напрямую. Это сознательно НЕ Wave 5
   write-tool, а обычное действие пользователя над уже показанным текстом.

**Files:** UI-модуль, рендерящий агентный ответ (после A1 — тот же компонент), targeted
tests.

**DoD:** студент может превратить карточку-кандидат в сохранённую карточку одним кликом
без похода в раздел Flashcards; агентный код (`cards.propose`) не меняется.

**Doc-sync:** `docs/user_guide.md`.

**Dependencies:** требует A1 (нечего сохранять, пока нет UI-рендера ответа агента).

---

## Волна-кандидат C: `wave-agent-transparency` (P2)

**North star (кандидат):** студент видит, что агент делал для него, тем же языком, что
и остальной продукт — не как diagnostic-панель для разработчика.

### Кандидат C1 — История прогонов на поверхности студента

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** среднее

**Проблема/возможность.** После A2 данные прогонов читаемы через API, но всё ещё не
видны студенту как часть его учебной истории — только как диагностика для разработчика.

**Evidence:**
- `app/user_state_agent_runs.py:140-158` (`list_agent_runs`) — уже даёт компактный
  список без step-деталей, подходящий для ленты (без второго тяжёлого запроса на каждый
  элемент списка).
- Аналогичный паттерн учебного журнала уже существует для других поверхностей
  прогресса (`app/ui/dashboards_progress.py` и соседи) — переиспользовать стиль
  карточки, не изобретать новый визуальный язык.

**Proposed change:** компактная лента «Что агент делал для меня» на экране прогресса —
дата, тема, сценарий (человеческим названием, не `scenario_id`), было ли что-то
сохранено (после B2). Учебный журнал, не debug-панель — тот же принцип
learner-language, что кандидат C2 плана [[material_as_product_quality_plan]] (разбор №3).

**Files:** `app/ui/dashboards_progress.py` или соседний модуль прогресса, использующий
`list_agent_runs` через A2-роутер (не напрямую `user_state_agent_runs`, чтобы UI шёл
через тот же API-контракт, что и внешние потребители).

**DoD:** лента показывает последние N прогонов человеческим языком; пустое состояние
(«агент ещё ничего не собирал для вас») не выглядит как ошибка.

**Doc-sync:** `docs/user_guide.md`.

**Dependencies:** требует A2 (источник данных) и осмысленнее после B2 (есть что
показывать про «сохранено»).

---

## Рекомендованный порядок реализации

1. **A1** — CTA-кнопка; без неё остальной план не имеет смысла проверять на реальных
   студентах.
2. **A2** — read-роутер прогонов; независим от A1, но вместе дают полный цикл
   «кнопка → прогон → видимая история» и открывают путь к отладке качества.
3. **B1** — расширение golden-набора; можно вести параллельно с A1/A2, но как gate
   перед расширением rollout за пределы тестовой группы.
4. **B2** — кнопка «Сохранить как карточку»; требует A1 технически.
5. **C1** — история прогонов на поверхности студента; последним, требует A2 и
   осмысленнее после B2.

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../presentations/evolutionary_analyses/README.md`](../presentations/evolutionary_analyses/README.md) — индекс серии разборов
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan разбора №2 (онбординг)
- [`material_as_product_quality_plan.md`](material_as_product_quality_plan.md) — detail-plan разбора №3 (качество материала)
- hometutor: `docs/agent_roadmap.md` (канонический источник архитектуры агента),
  `docs/user_guide.md`, `docs/api_reference.md`, `CLAUDE.md`
