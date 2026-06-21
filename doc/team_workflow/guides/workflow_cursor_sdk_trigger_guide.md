# Настройка и использование режима Cursor SDK trigger (`--trigger-cmd`)

**Связь:** умный роутер [`workflow_router.md`](../workflow_router.md) · скрипт `scripts/cursor_agent_trigger.ts` · флаг `scripts/workflow.py --trigger-cmd`

> Обновление 2026-05-17: общий runtime находится в `scripts/_trigger_shared.ts`.
> Cursor wrapper (`scripts/cursor_agent_trigger.ts`) только отправляет задачу в `Agent.prompt` и не перезаписывает `execution_contract.md`.
> DeepSeek API trigger описан отдельно: [`workflow_deepseek_api_trigger_guide.md`](workflow_deepseek_api_trigger_guide.md).

---

## 1. Назначение

Кондуктор **`workflow.py --loop --skip-review --watch-contract`** после генерации **`doc/current_task.md`** может вызвать внешнюю команду (**`--trigger-cmd`**), которая через **Cursor TypeScript SDK** (`@cursor/sdk`) передаёт текст задачи **локальному** агенту. Сам trigger только отправляет промпт и возвращает код процесса; признак фактического выполнения задачи — заполненный **`archive/team_artifacts/<PACKAGE_ID>/execution_contract.md`**. Файл, в котором остался только `STARTED`, считается in-progress marker, а не evidence. Далее роутер **ждёт** контракт с содержательным proof и затем запускает **`run_autonomous.py --post-agent`**.

Роутер **не передаёт API-ключ** в аргументах команды: **`CURSOR_API_KEY`** должен быть в **окружении процесса**, из которого запущен `workflow.py` (дочерний процесс наследует `env`).

---

## 2. Предварительные требования

> **Рекомендуется** использовать `trigger_orchestrator.ts` вместо прямого вызова `cursor_agent_trigger.ts`. Оркестратор автоматически выбирает стратегию, поддерживает fallback на DeepSeek TUI, adaptive demotion и circuit breaker. Прямой вызов cursor trigger — только для отладки или принудительного выбора.

1. **Node.js** (LTS) и **npm** доступны в `PATH`.
2. В **корне репозитория** один раз:
   ```powershell
   cd D:\Projects\home-rag_v2
   npm install
   ```
3. **Cursor API key** — ключ для программного доступа (личный или service account), см. [Cloud Agents / API keys](https://cursor.com/dashboard/cloud-agents).

---

## 3. Переменная `CURSOR_API_KEY`

`workflow.py` **не загружает** `.env` сам по себе. Ключ должен быть задан в среде **того терминала**, из которого вы запускаете кондуктор.

### Вариант A — текущая сессия PowerShell

```powershell
$env:CURSOR_API_KEY = "cursor_..."   # без пробелов по краям
```

### Вариант B — постоянно для пользователя Windows

«Параметры → Система → О программе → Дополнительные параметры системы → Переменные среды» → для пользователя создать **`CURSOR_API_KEY`**.

### Связь с `.env`

В **`.env.example`** зафиксирован плейсхолдер. Если ключ хранится только в **`.env`** приложения, для **роутера** всё равно нужно либо экспортировать переменную в shell перед запуском, либо использовать обёртку (раздел 8).

### Быстрая проверка

```powershell
npx tsx scripts/cursor_agent_trigger.ts
```

Без ключа скрипт завершится с сообщением: `CURSOR_API_KEY must be set in the environment.`

---

## 4. Команда кондуктора с триггером

Из **корня репозитория** (пример PowerShell):

```powershell
cd D:\Projects\home-rag_v2
$env:CURSOR_API_KEY = "cursor_..."   # если ещё не задан глобально

# Рекомендованная команда — через оркестратор (автовыбор триггера + fallback):
.\.venv\Scripts\python.exe scripts\workflow.py `
  --loop --skip-review --watch-contract `
  --trigger-cmd "npx tsx scripts/trigger_orchestrator.ts" `
  --agent auto --post-agent-no-dod-cache

# Прямой вызов cursor trigger (без orchestrator — только для отладки):
.\.venv\Scripts\python.exe scripts\workflow.py `
  --loop --skip-review --watch-contract `
  --trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts" `
  --agent cursor_ai --post-agent-no-dod-cache
```

`--trigger-cmd` теперь валиден только вместе с **обоими** флагами `--loop --watch-contract`. Без них `workflow.py` завершится с rc=2, потому что trigger иначе не находится внутри контролируемого цикла `trigger → WATCH → post-agent`.

### Дополнительные флаги

| Флаг | Назначение |
|------|------------|
| `--watch-timeout 3600` | Таймаут ожидания контракта / реестра (секунды), по умолчанию 3600 |
| `--loop-max 20` | Лимит итераций цикла |
| `--package PACKAGE_ID` | Явный пакет вместо автовыбора из `backlog_registry.yaml` |

---

## 5. Что передаётся триггеру

Роутер при вызове `--trigger-cmd` добавляет в `env`:

| Переменная | Смысл |
|------------|--------|
| `WORKFLOW_CURRENT_TASK_PATH` | Абсолютный путь к файлу задачи (обычно `...\doc\current_task.md`) |

Сам `scripts/cursor_agent_trigger.ts` пишет timestamps в зоне **Europe/Moscow** (`+03:00`). Пока `Agent.prompt(...)` не вернул финальный результат, trigger печатает heartbeat с прогрессивным интервалом: 30s → 60s → 120s → 300s (cap). Это подтверждает, что процесс жив, но не содержит скрытые рассуждения модели. Начальный интервал можно переопределить переменной `CURSOR_TRIGGER_HEARTBEAT_MS`; значение `0` отключает heartbeat.

Если `execution_contract.md` слишком долго остаётся ровно `STARTED`, trigger считает это зависанием proof handoff и завершает вызов с rc=3. Таймаут по умолчанию — 480000 ms; переменная `CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS=0` отключает guard для заведомо длинных ручных прогонов.

Скрипт **`scripts/cursor_agent_trigger.ts`** выбирает путь в порядке:

1. первый аргумент командной строки (`argv[2]`, т.к. argv[0]=node, argv[1]=путь к скрипту);
2. иначе `WORKFLOW_CURRENT_TASK_PATH`;
3. иначе относительный путь `doc/current_task.md` от **текущего каталога** (при вызове из роутера `cwd` — **корень репозитория**).

Содержимое файла передаётся в **`Agent.prompt(...)`** с **`local: { cwd: process.cwd() }`** и моделью **`composer-2`** (как в скрипте).

---

## 6. Поведение по состояниям роутера

1. **`ready_fresh` + `execution_auto` + `--watch-contract` + `--trigger-cmd`**  
   - Запуск **`run_autonomous.py`** (генерация `doc/current_task.md`, при необходимости `task_started.md` и обновление `active_package_id`).  
   - Если генерация `doc/current_task.md` завершилась ненулевым rc — цикл останавливается, trigger не вызывается, чтобы не отправить агенту старую задачу.  
   - Если **`execution_contract.md` ещё нет** — выполняется **`--trigger-cmd`**.  
   - Ожидание контракта → **`--post-agent`**.

2. **`ready_orch` + `--watch-contract` + `--trigger-cmd`**  
   - Сначала **`run_autonomous.py`** (тот же `current_task.md`).  
   - Если `run_autonomous.py` не смог сгенерировать задачу — stop с его rc, без trigger/WATCH.  
   - При отсутствии контракта — триггер → ожидание → **`--post-agent`**.

3. **Без `--trigger-cmd`**  
   - Прежнее поведение: для **execution_auto** — PAUSE и ручная работа в IDE; для **ready_orch** — подсказки и ожидание без SDK (см. `workflow_router.md`).

4. **Контракт уже есть** после генерации задачи — вызов SDK **пропускается** (защита от повторного запуска).

---

## 7. Типовой сценарий

1. В **`doc/backlog_registry.yaml`** пакет в рабочем статусе; контракт принят (или пакет уже **ready/wip**).  
2. Задать **`CURSOR_API_KEY`**, выполнить **`npm install`** при необходимости.  
3. Запустить команду из раздела 4.  
4. Убедиться, что агент по **`doc/current_task.md`** создаёт **`execution_contract.md`** в нужном каталоге артефактов.  
5. При ненулевом коде возврата **`--trigger-cmd`** цикл **останавливается** — исправить окружение/SDK и перезапустить кондуктор (см. также состояние `ready_executing` в `workflow_router.md`).

---

## 8. Своя обёртка для `--trigger-cmd`

Можно указать любую shell-команда: она получит **`WORKFLOW_CURRENT_TASK_PATH`**. Пример: PowerShell-скрипт, который читает `.env` и вызывает `npx tsx scripts/cursor_agent_trigger.ts`.

---

## 9. Устранение неполадок

| Симптом | Действия |
|---------|----------|
| `CURSOR_API_KEY must be set` | Задать переменную в **том же** сеансе PowerShell **до** `workflow.py`. |
| `Cannot read task file` | Проверить путь из `WORKFLOW_CURRENT_TASK_PATH`; не удалён ли `current_task.md` до вызова. |
| `CursorAgentError` / 401 | Ключ, пробелы в значении, корректность типа ключа; для local-рантайма — доступ аккаунта Cursor. |
| `Terminate batch job (Y/N)?` / `KeyboardInterrupt` после успешного `Agent.prompt finished` | Windows `npx`/`.cmd` мог прервать родительский `workflow.py` до WATCH. Проверьте, появился ли `archive/team_artifacts/<PACKAGE_ID>/execution_contract.md`; если да — перезапустите ту же команду `workflow.py --loop --skip-review --watch-contract ...`, роутер подхватит `--post-agent`. Если файла нет — повторно выполните `doc/current_task.md` или перезапустите loop с trigger. |
| `execution_contract.md` содержит только `STARTED` | Агент начал задачу, но не записал evidence. Trigger остановит такой run по `CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS` (stall detection); затем повторно выполните `doc/current_task.md` или перезапустите trigger. `--post-agent` не должен запускаться на таком файле. Оркестратор не будет self-heal retry на `started_stall:` — это deterministic prefix. |
| Оркестратор переключился на DeepSeek TUI | Cursor success rate упал ниже 40% — cursor был демотирован. Проверьте `trigger_metrics.jsonl`. Чтобы сбросить дemotion: исправьте причину сбоев и подождите нескольких успешных итераций. |
| `CursorAgentError` с retry backoff | Cursor trigger использует `CURSOR_TRIGGER_RETRY_DELAYS_MS` (default: 2000, 10000, 30000). После всех retry trigger завершается с ненулевым кодом → оркестратор переходит к fallback. |
| `--post-agent` падает на `verification_only` после уже доставленного commit | Проверьте `Pre-existing delivery evidence`: если commit менял хотя бы один path из write-set, `run_autonomous.py` должен повысить режим до `execution`; если пересечения нет, нужен явный `allow_verification_only` в registry. |
| Долго видна строка `calling Agent.prompt ...` | Это ожидание финального ответа Cursor SDK. Trigger должен печатать heartbeat с elapsed; промежуточные размышления IDE Cursor через текущий `Agent.prompt` call в консоль не стримятся. |
| Таймаут WATCH | Увеличить `--watch-timeout`; проверить, что агент пишет **`execution_contract.md`** по инструкции в задаче. |
| `npx` не найден | Проверить `PATH`; при необходимости указать полный путь к `npx` или вызывать глобально установленный `tsx`. |

---

## 10. Пути в IDE (локальная машина)

- Роутер: `D:\Projects\home-rag_v2\doc\team_workflow\workflow_router.md`  
- Этот гайд: `D:\Projects\home-rag_v2\doc\team_workflow\guides\workflow_cursor_sdk_trigger_guide.md`
