# Workflow Для Агентов — Work Cycle

Часть split-карты [`doc/agent_workflow.md`](agent_workflow.md).
Этот файл содержит: **базовый цикл Scan→Plan→Edit→Verify→Sync, параллелизм, A/B/C split, когда запускать новый поток, критерии "хорошей задачи для агента"**.

Другие части split-карты:
- [`agent_workflow_rules.md`](agent_workflow_rules.md) — Token Budget & Retry Safety
- [`agent_workflow_templates.md`](agent_workflow_templates.md) — planning/verify/contract/task templates
- [`agent_workflow_arch_review.md`](agent_workflow_arch_review.md) — architecture review (5 фаз)
- [`agent_workflow_test_bundles.md`](agent_workflow_test_bundles.md) — test bundles + low-budget fallback

---

## Базовый Цикл Работы

### 1. Scan

Перед правками агент должен:

- найти owner-файлы задачи;
- проверить, нет ли пересечения с активными соседними потоками;
- понять, какие тесты и smoke-команды подтверждают завершение.

Для задач больше одного файла нельзя начинать сразу с редактирования без короткого анализа текущего состояния.

### 2. Plan

Постановка задачи агенту должна включать:

- что именно нужно изменить;
- какие файлы можно менять;
- какие файлы трогать нельзя;
- что считается готовым;
- какие проверки нужно запустить после правок.

Хорошая постановка:

- "Обнови `app/query_service.py` и `app/api_models.py`, не трогай `app/pipeline_steps.py`, после правок прогони `tests/test_query_service.py` и `tests/test_api.py`."

Плохая постановка:

- "Почини tutor path."

### 3. Edit

Во время работы агент должен:

- менять только согласованный write-set;
- не делать попутный refactor в соседних модулях;
- не тащить в задачу unrelated cleanup;
- не переписывать архитектуру без отдельного решения owner'а.

Если для решения задачи нужно выйти за пределы write-set, это уже не "маленькое уточнение", а повод остановиться и пересогласовать split.

### 4. Verify

Любая нетривиальная задача должна заканчиваться проверкой.

Минимум:

- целевые unit/API/UI тесты по owner-файлам;
- smoke/gate-команда, если задача затрагивает regression contour;
- короткая сверка diff на предмет лишних изменений.

Для `hometutor` это особенно важно в зонах:

- tutor orchestration;
- typed API contracts;
- persistence/user state;
- graph/tutor regression scripts;
- Streamlit surfaces.

### 5. Sync Docs

Документацию нужно обновлять, если агент меняет:

- публичный API-контракт;
- UI-поведение, которое видит пользователь;
- roadmap-статус iteration/slice;
- архитектурный источник истины;
- правила разработки или merge-порядок.

Минимальный набор doc-sync зависит от задачи, но обычно это один или несколько файлов из `doc/tasklist.md`, `doc/changelog.md`, `doc/api_reference.md`, `doc/user_guide.md` / `user_guide_details.md`, `doc/conventions.md` (или точечно `conventions_architecture.md` / `conventions_reference.md`).

## Как Безопасно Параллелить Работу

Главное правило: параллелить можно только независимые write-set'ы.

Хорошее распараллеливание:

- Agent A: orchestration core и policy
- Agent B: typed payload, API surfaces, UI read-paths
- Agent C: persistence, CI gate, runbook, docs

Плохое распараллеливание:

- два агента одновременно меняют `app/query_service.py`;
- один агент меняет contract, а второй в это же время меняет тот же contract без handshake;
- UI и backend работают параллельно, но формат payload между ними нигде не зафиксирован.

## Правила Для A/B/C Split

Когда задача делится между несколькими агентами, нужно заранее определить:

- owner-файлы для каждого агента;
- boundary-файлы, которые никто не трогает параллельно;
- handshake-контракт между потоками;
- порядок merge.

Минимальный шаблон split:

- `Agent A`
- зона ответственности: core logic
- можно менять: список файлов
- нельзя менять: список файлов
- отдаёт наружу: конкретный контракт или поле

- `Agent B`
- зона ответственности: read-path/API/UI
- можно менять: список файлов
- нельзя менять: список файлов
- ожидает от A: конкретный контракт или snapshot

- `Agent C`
- зона ответственности: tests/gates/docs/persistence
- можно менять: список файлов
- нельзя менять: список файлов
- блокируется только на: явно указанное событие merge или готовый контракт

## Когда Лучше Запустить Новый Поток

Новый агент или новый чат лучше запускать, если:

- текущий поток уже тащит слишком много исторического контекста;
- агент начал повторно предлагать неверное решение;
- scope задачи поменялся;
- появилась новая owner-зона;
- нужно отдельное review без смешивания с реализацией.

Обычно дешевле перезапустить с хорошим prompt и узким scope, чем продолжать чинить "расползшийся" диалог.

## Что Считать Хорошей Задачей Для Агента

Подходят лучше всего:

- локальный feature slice с понятным DoD;
- точечный bugfix;
- typed contract sync;
- doc sweep по конкретному набору файлов;
- review/regression pass;
- выделение отдельного модуля без cross-cutting rewrite.

Подходят хуже:

- "сделай систему лучше";
- "рефактори всё tutor";
- "разберись, почему проект сложный";
- большие многослойные изменения без owner split.
