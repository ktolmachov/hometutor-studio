# Smart Workflow Router — `scripts/workflow.py`

Актуализировано: **2026-05-05** (подсказки человеку в консоли синхронизированы с `scripts/workflow.py`)

Единая точка входа в командный пайплайн. Заменяет необходимость держать матрицу решений в голове: читает состояние реестра, определяет где находится проект и выдаёт готовую команду следующего шага — или запускает весь конвейер в режиме авто-цикла (`--loop`).

Связанные документы: [`workflow_decision_tree.md`](workflow_decision_tree.md) · [`process.md`](process.md) · [`generate_orchestration_prompt.md`](generate_orchestration_prompt.md) · [**`workflow_cursor_sdk_trigger_guide.md`**](guides/workflow_cursor_sdk_trigger_guide.md) · [**`workflow_deepseek_api_trigger_guide.md`**](guides/workflow_deepseek_api_trigger_guide.md) · [**`workflow_deepseek_tui_trigger_guide.md`**](guides/workflow_deepseek_tui_trigger_guide.md)

---

## Быстрый старт

```bash
# Узнать что делать прямо сейчас:
python scripts/workflow.py

# Выполнить следующий шаг автоматически:
python scripts/workflow.py --exec

# Для конкретного агента:
python scripts/workflow.py --agent claude_code

# Только статус без команды (для скриптов/CI):
python scripts/workflow.py --status

# JSON-вывод (для автоматизации):
python scripts/workflow.py --json

# Пропустить паузу на ревью контракта после plan-next (см. раздел «Флаги»):
python scripts/workflow.py --agent cursor_ai --skip-review

# ── Авто-цикл: роутер сам ведёт пакет до closed ──────────────────────────────
python scripts/workflow.py --loop --skip-review --watch-contract --agent cursor_ai

# С автозапуском агента через Cursor SDK (нужны npm-зависимости и CURSOR_API_KEY в env):
.venv\Scripts\python.exe scripts/workflow.py `
    --loop --skip-review --watch-contract `
    --trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts" --agent cursor_ai  --post-agent-no-dod-cache

# Для автоматического выбора триггера (Cursor SDK или DeepSeek TUI) через Smart Orchestrator:
.\.venv\Scripts\python.exe scripts\workflow.py `
    --loop --skip-review --watch-contract `
    --trigger-cmd "npx tsx scripts/trigger_orchestrator.ts" --agent auto
# С явным лимитом итераций (по умолчанию: 20):
python scripts/workflow.py --loop --skip-review --watch-contract \
    --loop-max 10 --agent cursor_ai

# Полный прогон DoD на каждом шаге закрытия (без чтения archive/.../dod_cache.json; только с --loop):
python scripts/workflow.py --loop --skip-review --watch-contract --agent cursor_ai --post-agent-no-dod-cache
```

---

## Промпт для AI-агента

```
Прочитай doc/team_workflow/workflow_router.md
и выполни команду: python scripts/workflow.py --agent cursor_ai

(Вариант без паузы на ревью контракта после plan-next: `python scripts/workflow.py --agent cursor_ai --skip-review`.)

Прочитай вывод и выполни указанное действие.
Если команда начинается с python scripts/ — выполни её через Shell tool.
Если это инструкция вставить промпт в агент — следуй ей дословно.
```

Для другого агента замени `cursor_ai` на `claude_code` или `codex`.

---

## Что делает роутер

1. Читает `doc/backlog_registry.yaml` (SSoT)
2. Определяет активный пакет (приоритет: `wip > ready > open > proposed`)
3. Проверяет артефакты в `archive/team_artifacts/<id>/`
4. Сопоставляет с одним из шести состояний
5. В состоянии `ready_fresh` — оценивает сложность пакета и наличие US/CJM, выбирает маршрут: `orchestration` или `execution_auto`
6. Выдаёт: состояние + следующий шаг + готовую команду

**Инвариант:** `doc/tasklist.md` **не** используется роутером и не должен попадать в read-set при работе с `workflow.py`. Источник маршрутизации — только `doc/backlog_registry.yaml` (SSoT). Производный weekly view обновляют отдельно по [`_common_rules.md`](_common_rules.md) после правок YAML; это вне контура умного роутера.

---

## Шесть состояний пайплайна

| Состояние | Когда | Следующее действие |
|-----------|-------|-------------------|
| `no_package` | Нет пакетов с активным статусом | Вставить в агент инструкцию из `next_hint` (`generate_plan_next_prompt.md`); в конце подсказки — ссылка на этот файл |
| `needs_plan` | Пакет `proposed`/`open` — контракт ещё не принят | То же; при `--skip-review` во `next_hint` — второй шаг `workflow.py … --exec`. В конце — ссылка на этот документ |
| `ready_fresh` | Пакет `ready`/`wip`, нет orchestration и нет артефактов задачи | **Lifecycle routing + complexity** (см. [Маршрутизация `ready_fresh`](#маршрутизация-по-сложности-ready_fresh)): `orchestration` → `generate_orchestration_prompt.py`; `execution_auto` → `run_autonomous.py` напрямую |
| `ready_executing` | `task_started.md` есть, `execution_contract.md` нет | Выполнить `doc/current_task.md` в IDE по промпту из вывода роутера; создать `execution_contract.md`; перезапустить ту же команду `--loop …`. Детали: [ручной шаг](#manual-ready-executing). При повторном запуске с контрактом на диске — авто `--post-agent` |
| `ready_orch` | Пакет `ready`/`wip`, orchestration есть, нет `execution_contract.md` | Нумерованный чеклист во `next_hint` (orch-файл → шаги → `execution_contract.md`) и ссылка на этот документ. С `--loop --watch-contract` — генерируется `current_task.md`, блокирующее ожидание контракта, затем авто `--post-agent` |
| `wip_running` | `execution_contract.md` существует (с orch-файлом или без) | Запустить `run_autonomous.py --post-agent`; в `--loop` — запускается автоматически |

<a id="manual-ready-executing"></a>

### Ручной шаг `ready_executing`, `[PAUSE]` и вывод роутера

1. Если **нет** автоматической команды (`next_cmd == null`), в блоке «СЛЕДУЮЩИЙ ШАГ» роутер даёт **пронумерованные действия**, готовый **промпт для агента** (полная и короткая формулировки) и строку **перезапуска кондуктора**:  
   `.venv\Scripts\python.exe scripts/workflow.py --loop --skip-review --watch-contract --agent <агент>`.
2. Ниже — ссылка на этот документ: путь `doc/team_workflow/workflow_router.md` и строка **«Открыть файл:»** с repo-relative путём от корня проекта.
3. Ориентиры: таблица состояний выше; [граф переходов](#router-graph); [авто-цикл по шагам](#router-loop-steps).
4. В режиме **`--loop`** для `ready_executing` подсказка выводится **один раз** в секции `WORKFLOW STATE` (без повторного дубля в конце итерации).

<a id="canonical-agent-prompt"></a>

#### Канонический промпт (SSoT)

Полный текст блока «Промпт для агента» в консоли собирается в **`scripts/workflow_strings.py`** — функция `format_prompt_execute_current_task_footer(rel_path)`. Роутер подставляет фактический POSIX-путь к `execution_contract.md`; менять формулировки нужно **только** в этом модуле (тест `test_workflow_strings_prompt_footer_matches_sample_path` ловит регрессии).

Иллюстрация с плейсхолдером пакета:

```
«Выполни задачу из doc/current_task.md целиком, включая обязательный финальный шаг:
 создай файл archive/team_artifacts/<PACKAGE_ID>/execution_contract.md.»
```

Краткая строка в коде — константа `SHORT_EXECUTE_CURRENT_TASK_PROMPT_LINE` в том же файле (`«Выполни doc/current_task.md»`).

---

## Флаги

| Флаг | Описание |
|------|----------|
| `--agent {cursor_ai,claude_code,codex,kilo}` | Целевой агент (default: `cursor_ai`) |
| `--package PACKAGE_ID` | Явно указать пакет вместо автовыбора |
| `--status` | Только статус, без раздела "Следующий шаг" |
| `--exec` | Выполнить `next_cmd` напрямую (если есть) |
| `--skip-review` | Пропустить ревью контракта: в `needs_plan` — расширенный `next_hint` (после Phase 7 сразу `workflow.py … --skip-review --exec`); в `ready_fresh` — эквивалентно `--exec` для выбранного маршрута (orchestration или execution_auto) |
| `--loop` | **Авто-цикл**: после каждого шага пересчитывает состояние и продолжает до `no_package`, ошибки или `--loop-max` |
| `--loop-max N` | Лимит итераций цикла (default: `20`) |
| `--watch-contract` | Только с `--loop`. **execution_auto:** без `--trigger-cmd` — после создания `task_started.md` PAUSE (терминал свободен), как раньше; с `--trigger-cmd` — вызывается `run_autonomous`, затем команда триггера, блокирующее ожидание готового `execution_contract.md`, затем `--post-agent`. **ready_orch:** `workflow.py` пишет `current_task.md` со ссылкой на существующий orchestration-файл + при `--trigger-cmd` вызывает триггер перед WATCH + `--post-agent`. WATCH не считает `STARTED` marker готовым контрактом. |
| `--watch-timeout N` | Таймаут ожидания `execution_contract.md` и изменения реестра в секундах (default: `3600`) |
| `--trigger-cmd "…"` | Команда автозапуска агента; передаётся `WORKFLOW_CURRENT_TASK_PATH` к `doc/current_task.md`. Production example: `npx tsx scripts/cursor_agent_trigger.ts` (нужен `CURSOR_API_KEY`). Experimental handoff-only example: `npx tsx scripts/deepseek_agent_trigger.ts` (DeepSeek Chat API, нет локальных file tools). Требует `--loop --watch-contract`, иначе `workflow.py` завершится с rc=2. Без флага — прежний PAUSE / ручной IDE-шаг. |
| `--post-agent-no-dod-cache` | Только с `--loop`. Ко **всем** вызовам `run_autonomous.py --post-agent` внутри кондуктора добавляется `--no-dod-cache`: DoD-команды выполняются заново, без использования `archive/team_artifacts/<id>/dod_cache.json`. Удобно для «жёсткой» верификации волны; по умолчанию кэш DoD включён в `run_autonomous.py` для ускорения. Без `--loop` — rc=2. |
| `--json` | Машиночитаемый JSON-вывод |

**По умолчанию** (`--skip-review` не передан) поведение без изменений: после plan-next агенту даётся пауза на ревью YAML ([`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md), Phase 7).

<a id="router-graph"></a>

### Граф переходов авто-цикла

```
no_package      → стоп (backlog пуст)
needs_plan      → [--skip-review] ждёт изменения реестра → re-route

ready_fresh     → [lifecycle routing + complexity check]
                  ├─ orchestration (has US/CJM OR medium/high complexity)
                  │    → generate_orchestration_prompt.py → re-route (→ ready_orch)
                  └─ execution_auto (low maintenance/infra without US/CJM)
                       → [без --trigger-cmd] task_started.md → 📌 PAUSE — exit 0
                       → [с --trigger-cmd] run_autonomous → current_task.md → триггер (SDK)
                             → WATCH execution_contract.md → --post-agent
                       (повторный запуск без триггера: при контракте на диске — сразу --post-agent)

ready_executing → execution_contract.md появился?
                  ├─ да  → run_autonomous --post-agent → re-route (→ no_package/next)
                  └─ нет → развёрнутый next_hint + exit 0 (в --loop без второго дубля текста)

ready_orch      → current_task.md с ссылкой на существующий orchestration_*.md
                → [--watch-contract] опционально --trigger-cmd (SDK) перед ожиданием
                → ждёт готовый execution_contract.md (не только STARTED marker)
                → run_autonomous --post-agent → re-route

wip_running     → run_autonomous --post-agent → re-route
```

---

## Маршрутизация по сложности (ready_fresh)

Когда пакет переходит в `ready_fresh`, роутер принимает решение в два слоя:

1. **Lifecycle routing:** если активный контракт уже принят как learning-product пакет и содержит явные `user_stories` или `cjm_moments`, следующий шаг — orchestration-first. Это сохраняет handoff Product Owner → Analyst/Architect/Developer даже для компактной задачи.
2. **Mechanical complexity:** `classify_package_complexity` (`scripts/prompt_utils.py`) оценивает размер и риск реализации. Его `route` используется для задач без US/CJM, а также как дополнительный повод включить orchestration для широких/рисковых пакетов.

Важно: `classify_package_complexity` отвечает на вопрос "насколько сложно исполнение?", а conductor `workflow.py` отвечает на вопрос "какой workflow-шаг сейчас нужен?". Поэтому compact product package может иметь `complexity["route"] == "execution_auto"`, но всё равно идти через orchestration из-за `has_us_or_cjm`.

### Правило выбора маршрута

| Условие | Маршрут | Следующая команда |
|---------|---------|------------------|
| Есть `user_stories` или `cjm_moments` у active package | `orchestration` | `generate_orchestration_prompt.py` → orch-файл → агент → `--post-agent` |
| complexity = `medium`/`high`, даже без US/CJM | `orchestration` | то же |
| complexity = `low` **и нет** US/CJM (maintenance/infra) | `execution_auto` | `run_autonomous.py` → `current_task.md` → агент → `--post-agent` |
| Поле `COMPLEXITY: low/medium/high` в контракте | override (приоритет) | по override |

### Сигналы сложности

`classify_package_complexity` оценивает контракт по сигналам:

| Сигнал | Что считает |
|--------|-------------|
| `write_set_size` | Число файлов в write-set |
| `dod_ops` | Число команд DoD (pytest, lint, …) |
| `outcomes` | Число задекларированных outcomes |
| `user_stories` | Число user story |
| `read_set` | Число read-set hints |
| `dir_breadth` | Энтропия директорий write-set |
| `hot_paths` | Попадания в "горячие" пути (schema/auth/config/pipeline) |
| `risk_keywords` | Риск-термины в prose контракта |
| `exec_constraints` | Явные execution constraints |

**Итог complexity layer:** `score` → `low` / `medium` / `high` → `route` (`execution_auto` или `orchestration`). Финальный `use_orchestration` в `workflow.py` дополнительно учитывает `has_us_or_cjm`.

### Разница в pipeline для агента

```
orchestration (product package with US/CJM или тяжёлый пакет):
  generate_orchestration_prompt.py
    → orchestration_cursor_ai.md (8 шагов: PO/Analyst/Architect/Dev/Tester/…)
    → run_autonomous.py (пишет current_task.md из шаблона с MANDATORY FINAL STEP)
    → агент читает current_task.md → пишет execution_contract.md
    → run_autonomous.py --post-agent → close_package

execution_auto (лёгкий maintenance/infra пакет без US/CJM):
  run_autonomous.py (напрямую, пишет current_task.md)
    → агент читает current_task.md → пишет execution_contract.md
    → run_autonomous.py --post-agent → close_package
```

Экономия для `execution_auto`: не создаётся orchestration-файл, нет шагов PO/Analyst/Architect/Designer — реализация и тесты сразу. Поэтому этот маршрут оставлен для компактных maintenance/infra задач без пользовательской истории/CJM; продуктовые learning-loop пакеты проходят orchestration-first.

---

## Авто-цикл (`--loop`) — полная цепочка

Флаг `--loop` переключает роутер из режима «выдай одну команду» в **самостоятельный конвейер**: одна команда в терминале ведёт пакет от `proposed` до `closed`, автоматически делая всё, что не требует решения человека.

**Ручных шагов в нормальном happy path остаётся один** (при использовании `--trigger-cmd` для `execution_auto` / `ready_orch`):

1. Принять контракт (Phase 7 plan-next) — человек должен одобрить *что именно делать*.

Без `--trigger-cmd` по-прежнему нужен второй ручной шаг — выполнить задачу в IDE (Composer) по `doc/current_task.md`. Recovery-шаг также может понадобиться, если trigger/Windows shell прервали родительский `workflow.py`, SDK завершился без создания `execution_contract.md`, или WATCH дошёл до таймаута.

---

### Запуск

```powershell
# Предусловие: реестр консистентен и есть активный пакет
.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict
.venv\Scripts\python.exe scripts/workflow.py --status

# Запуск авто-цикла
.venv\Scripts\python.exe scripts/workflow.py `
    --loop --skip-review --watch-contract --agent cursor_ai

# С явным лимитом (по умолчанию: 20 итераций)
.venv\Scripts\python.exe scripts/workflow.py `
    --loop --skip-review --watch-contract --loop-max 10 --agent cursor_ai

# Строгий DoD без dod_cache на каждом post-agent (опционально)
.venv\Scripts\python.exe scripts/workflow.py `
    --loop --skip-review --watch-contract --agent cursor_ai --post-agent-no-dod-cache
```

---

<a id="router-loop-steps"></a>

### Пошаговая цепочка

**Шаг 1 — `needs_plan`: роутер ждёт контракт**

Роутер опрашивает `backlog_registry.yaml` каждые 5 секунд. Параллельно в новом чате:

```
Прочитай doc/team_workflow/generate_plan_next_prompt.md и выполни инструкции.
```

Phase 0–7: выбрать кандидата, записать контракт (`proposed → ready`), lint PASS.
Роутер обнаружит изменение файла и перейдёт к следующему шагу автоматически. В консоли также может быть строка со ссылкой на этот файл (`workflow_router.md`) и состояние `needs_plan`.

---

**Шаг 2 — `ready_fresh`, маршрут `execution_auto` (лёгкий пакет)**

Роутер вызывает `run_autonomous.py`, который пишет `doc/current_task.md` и `task_started.md`.
Затем **роутер выходит с кодом 0** — терминал свободен:

```
📌 [PAUSE] Пакет '<PACKAGE_ID>': терминал свободен до появления execution_contract.md.

СЛЕДУЮЩИЙ ШАГ:
  1) Откройте doc/current_task.md.
  2) В Cursor Composer (или другом агенте) выполните промпт из блока «Промпт для агента» в консоли.
  3) Убедитесь, что на диске создан файл:
       archive/team_artifacts/<PACKAGE_ID>/execution_contract.md
  4) Перезапустите кондуктора:
       .venv\Scripts\python.exe scripts/workflow.py --loop --skip-review --watch-contract --agent cursor_ai

(+ блок промпта для агента и строка «Открыть файл: file:///…» → этот документ)
```

После выполнения задачи в IDE и создания `execution_contract.md` снова запустите ту же команду `--loop …`.
При повторном запуске роутер видит контракт → `wip_running` → автоматически `--post-agent` → close.

Тот же чеклист и промпты выводятся в одноразовом режиме (`workflow.py` без `--loop`), когда состояние уже **`ready_executing`** (есть `task_started.md`, нет контракта): смотрите блок «СЛЕДУЮЩИЙ ШАГ» в консоли — без второго дубля текста при `--loop`.

Если задан `--trigger-cmd`, этот шаг не освобождает терминал сразу: `run_autonomous.py` сначала генерирует `doc/current_task.md`; при ненулевом rc цикл останавливается без trigger, чтобы не отправить старую задачу. При успешной генерации роутер вызывает trigger, ждёт `execution_contract.md`, затем запускает `--post-agent`.

---

**Шаг 3 — `ready_fresh`, маршрут `orchestration` (тяжёлый пакет)**

Роутер запускает `generate_orchestration_prompt.py` (~20 сек), сохраняет orch-файл и переходит в `ready_orch`.

---

**Шаг 4 — `ready_orch`: роутер ждёт контракт от агента**

Роутер вызывает `run_autonomous.py`, затем печатает краткий план и запускает опрос файла:

```
📋 [LOOP] ready_orch — doc/current_task.md готов.

СЛЕДУЮЩИЙ ШАГ:
  1) Выполните задачу из doc/current_task.md в IDE ...
  2) Либо следуйте шагам из orch-файла ...
  (+ ниже — футер со ссылкой на этот документ, file:///…)

⏳ [WATCH] Жду execution_contract.md ... (опрос каждые 10s)

📌 [WATCH — это не зависание] Следующий шаг — вручную:
   • Кто: вы или Cursor Composer ...
   • Что сделать: ...
   (+ тот же футер документации)
```

Терминал занят до появления файла или таймаута. После выполнения задачи агент создаёт `execution_contract.md`; роутер вызывает `--post-agent`.

Без `--watch-contract` кондуктор напечатает подсказку для ручного STEP 1 из orch-файла и строку документации — см. `next_hint` в выводе `workflow.py`.

---

**Шаг 5 — `--post-agent`: DoD + close**

По умолчанию `run_autonomous.py` может **пропустить повторный DoD**, если не менялись write-set и строки DoD в контракте (см. `archive/team_artifacts/<id>/dod_cache.json`). Чтобы в режиме **`--loop`** на каждом закрытии пакета заново гонять pytest и прочие команды DoD, добавьте к команде кондуктора **`--post-agent-no-dod-cache`** (эквивалент передачи `--no-dod-cache` в каждый `--post-agent`).

```
▶ run_autonomous.py --post-agent --package <ID> ...
  [DoD: pytest, lint, ...]
  [close_package: status → closed]
✅ Package '<ID>' closed successfully.
```

Роутер пересчитывает состояние: если есть следующий пакет — цикл продолжается; иначе — стоп.

---

### Визуальная схема

```
══════════════════════════════════════════════════════════════════════════════════
  ТЕРМИНАЛ (workflow.py --loop)              CURSOR IDE / ЧЕЛОВЕК
══════════════════════════════════════════════════════════════════════════════════

  [LOOP 1]  needs_plan
  ┌─────────────────────────────────┐
  │ ⏳ Жду backlog_registry.yaml   │──── новый чат ──────────────────────────────┐
  │    (опрос каждые 5s)           │                                             │
  │    .  .  .  .  .  .  .  .  .  │     generate_plan_next_prompt.md            │
  │                                │     Phase 0–6: выбор кандидата              │
  │ ✅ registry.yaml изменён       │◄─── Phase 7: proposed→ready, lint PASS ─────┘
  └──────────────┬─────────────────┘
                 │ АВТО
                 ▼
  [LOOP 2]  ready_fresh ──────────────────────────────────────────────────────────
                 │
         ┌───── ┴ ───────────────────────────────────────────────┐
        │ execution_auto (low maintenance/infra)                │ orchestration (US/CJM or medium/high)
         ▼                                                        ▼
  ┌──────────────────────────┐                    ┌──────────────────────────────┐
  │ run_autonomous.py        │                    │ generate_orchestration       │
  │  → current_task.md       │                    │   _prompt.py  (~20s)         │
  │  → task_started.md       │                    │  → orchestration_cursor.md   │
  │                          │                    └──────────────┬───────────────┘
  │ 📌 PAUSE — exit 0        │                                   │ АВТО → [LOOP 3]
  │    терминал свободен     │──── Composer ──────────────────┐  │ ready_orch
  └──────────────────────────┘     Ctrl+I                     │  ▼
                                   'Выполни doc/current_task.md'
                                   → пишет execution_contract.md  ┌──────────────────────────┐
                                                               │  │ run_autonomous.py        │
  [LOOP 3]  перезапуск роутера ◄────────────────────────────────  │  → current_task.md       │
  ready_executing                                                  │                          │
  ┌─────────────────────────────────┐                             │ ⏳ WATCH                 │──── Composer ──┐
  │ execution_contract.md найден?   │                             │    execution_contract.md │     STEP 1–8   │
  │  да → wip_running → post-agent  │                             │    (опрос каждые 10s)   │     orch-файл  │
  │  нет → next_hint в STATE, exit 0 │                             │ .  .  .  .  .  .  .  .  │                │
  └──────────────┬──────────────────┘                             │ ✅ contract обнаружен    │◄───────────────┘
                 │                                                └──────────────┬───────────┘
                 └──────────────────────── АВТО ──────────────────────────────────
                                                                                │
                                                                                ▼
                                                                  [LOOP N]  wip_running
                                                                  ┌──────────────────────────┐
                                                                  │ run_autonomous --post-agent│
                                                                  │ DoD: pytest, lint, ...    │
                                                                  │ close_package             │
                                                                  │ ✅ Package closed         │
                                                                  └──────────────┬────────────┘
                                                                                 │ АВТО
                                                                                 ▼
                                                                  no_package → ℹ Цикл завершён
══════════════════════════════════════════════════════════════════════════════════
  ░ РУЧНОЙ ШАГ   ▓ АВТО
```

---

### Временна́я шкала (один пакет, execution_auto)

```
  ░░░ РУЧНОЙ ШАГ    ▓▓▓ АВТО

  t = 0 min    ▓  запуск workflow.py --loop, опрос registry
  t = 0..15    ░  человек: plan-next, Phase 0–7 (accept контракта)
  t ≈ 15       ▓  registry.yaml изменён → auto re-route
  t ≈ 15:10    ▓  run_autonomous → current_task.md + task_started (+ registry)
  t ≈ 15:10    ▓  [с --trigger-cmd] npx tsx scripts/cursor_agent_trigger.ts → SDK Agent
  t ≈ 15:10    ▓  [без --trigger-cmd] 📌 PAUSE — exit 0, терминал свободен
  t = 15..75   ░  [без триггера] человек: Composer → execution_contract.md
  t = 15..75   ▓  [с триггером] WATCH execution_contract.md (терминал занят)
  t ≈ 75:05    ▓  wip_running → --post-agent: DoD + close (~3 мин)
  t ≈ 78       ▓  ✅ closed, цикл завершён
```

### Временна́я шкала (один пакет, orchestration)

```
  t = 0 min    ▓  запуск workflow.py --loop, опрос registry
  t = 0..15    ░  человек: plan-next, Phase 0–7
  t ≈ 15       ▓  registry.yaml изменён → auto re-route
  t ≈ 15:20    ▓  generate_orchestration_prompt.py (~20s) → orch-файл
  t ≈ 15:40    ▓  run_autonomous → current_task.md; опционально `--trigger-cmd` (SDK)
  t = 15..105  ░  [без триггера] человек: Composer, STEP 1–8 → execution_contract.md
  t = 15..105  ▓  [с триггером] WATCH execution_contract.md после SDK
  t ≈ 105      ▓  contract обнаружен → --post-agent: DoD + close
  t ≈ 108      ▓  ✅ closed, цикл завершён
```

---

### Обработка сбоев

| Ситуация | Поведение |
|---|---|
| Таймаут ожидания реестра (`needs_plan`) | `❌ Реестр не обновлён за N секунд. Стоп.` → exit 1 |
| Ошибка `generate_orchestration_prompt.py` (rc≠0) | `❌ Команда завершилась с rc=N. Стоп.` → exit rc |
| Таймаут ожидания `execution_contract.md` (`ready_orch` / `execution_auto` с `--trigger-cmd`) | `❌ Контракт не появился за N секунд. Стоп.` → exit 1 |
| Ошибка `--trigger-cmd` (rc≠0) | Стоп с **hint по rc** от `cursor_agent_trigger.ts` (см. таблицу кодов в секции SDK trigger) + проверка npm / `@cursor/sdk` |
| `KeyboardInterrupt` / Windows `Terminate batch job` вокруг `npx` | Trigger возвращает rc=130 с recovery hint. Проверить `execution_contract.md`; если файл есть — перезапустить тот же loop для `--post-agent`, если нет — повторить выполнение `doc/current_task.md`/trigger |
| `run_autonomous.py` не сгенерировал `current_task.md` перед trigger | Стоп с rc этой команды; `--trigger-cmd` не вызывается, чтобы не отправить агенту устаревший `doc/current_task.md` |
| `execution_contract.md` содержит только `STARTED` | Это in-progress marker, а не evidence. Роутер не запускает `--post-agent`; нужно выполнить/повторить `doc/current_task.md` и обновить контракт выводами, изменёнными файлами и DoD |
| `--post-agent` видит no current diff, но `Pre-existing delivery evidence` ссылается на commit, который менял write-set | Это delivery-by-evidence: `run_autonomous.py` повышает режим до `execution` и не требует `allow_verification_only`. Если commit не пересекается с write-set, остаётся обычная policy-gated `verification_only` |
| `Agent.prompt` долго не возвращает управление | `cursor_agent_trigger.ts` печатает heartbeat в московском времени примерно каждые 30s. Это не streaming мыслей модели: текущий SDK call возвращает детали только после завершения. В heartbeat указано «STARTED stub» vs «substantive» по тем же правилам, что `_execution_contract_ready_for_post_agent` в `workflow.py` (маленький размер файла после первого действия оркестрации — это нормально, если это только sentinel). Если proof-файл остаётся только `STARTED` дольше `CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS` (default 480000 ms), trigger завершится с rc=3 вместо долгого молчаливого зависания |
| DoD упали (`--post-agent` rc=1) | `❌ --post-agent rc=1. Стоп.` → exit 1 |
| Достигнут `--loop-max` | `⚠ Достигнут лимит итераций. Стоп.` → exit 1 |
| Backlog пуст (`no_package`) | `ℹ Backlog пуст. Цикл завершён.` → exit 0 |
| `execution_auto` PAUSE: контракт не создан | exit 0; перезапустить после выполнения задачи |

После любого exit — реестр и артефакты остаются консистентными; конвейер можно перезапустить с того же места.

---

## Сравнение режимов

| Критерий | Ручной | Авто-цикл (--loop) |
|---|:---:|:---:|
| **Команда запуска** | workflow.py | workflow.py --loop --watch-contract |
| **Зависимости** | Python | Python |
| **Ручных переключений** | Все | 2: принять контракт + выполнить задачу в IDE |
| **Автозапуск generate_orchestration** | ❌ | ✅ |
| **Автозапуск --post-agent** | ❌ | ✅ |
| **Терминал во время задачи** | свободен | execution_auto — PAUSE (свободен); ready_orch — занят |
| **Прозрачность / наблюдаемость** | Полная | Полная |
| **DoD защита** | Вручную | Автоматически (блокирует close при провале) |
| **Подходит для волны пакетов** | Утомительно | ✅ (--loop-max N) |

### Когда какой режим

| Ситуация | Рекомендация |
|---|---|
| Первое знакомство с пайплайном | **Ручной** — полная прозрачность каждого шага |
| Регулярная работа | **Авто-цикл** — экономит переключения, DoD защищает от ошибок |
| Волна из 3+ пакетов | **Авто-цикл** с --loop-max N*3 |
| Пакет с высоким риском (security, schema) | **Ручной** — человек видит каждый артефакт перед merge |

> **Неизменное правило:** принятие контракта (Phase 7 plan-next) — всегда ручной шаг. Человек должен явно одобрить *что именно делать*, прежде чем конвейер уходит в автономный прогон.

## Пример вывода

```
═══════════════════════════════════════════════════════
  WORKFLOW STATE
═══════════════════════════════════════════════════════
  Пакет     : epoch-arch-review-p1-trivial-fixes
  Статус    : ready
  Work state: fresh
  Последний : нет артефактов

  ПРЕДУПРЕЖДЕНИЯ
  ───────────────────────────────────────────────────
  (нет — роутер не использует производный tasklist)

  СЛЕДУЮЩИЙ ШАГ
  ───────────────────────────────────────────────────
  Сгенерировать orchestration для 'epoch-arch-review-p1-trivial-fixes' (агент: cursor_ai)

  .venv\Scripts\python.exe scripts/generate_orchestration_prompt.py --agent cursor_ai --package epoch-arch-review-p1-trivial-fixes
═══════════════════════════════════════════════════════
```

Состояние **`ready_executing`**: полный текст в консоли здесь **не копируется** — его собирают `scripts/workflow.py` и **`scripts/workflow_strings.py`** (`next_label` + многострочный `next_hint`: шаги 1–4, промпт для агента, футер с `file:///…`). Живой пример:

```powershell
.venv\Scripts\python.exe scripts/workflow.py --agent cursor_ai --package <PACKAGE_ID>
```

(когда для пакета уже есть `archive/team_artifacts/<PACKAGE_ID>/task_started.md` и ещё нет `execution_contract.md`). Структура и якоря: [#manual-ready-executing](#manual-ready-executing), [#canonical-agent-prompt](#canonical-agent-prompt).

---

## JSON-схема ответа

```json
{
  "state":            "ready_fresh | ready_executing | wip_running | needs_plan | ready_orch | no_package | unknown",
  "package":          "epoch-arch-review-p1-trivial-fixes | null",
  "status":           "ready | wip | proposed | open | null",
  "work_state":       "fresh | planning_only | execution_ready | null",
  "next_label":       "Человекочитаемое описание следующего шага",
  "next_cmd":         ".venv\\Scripts\\python.exe scripts/... | null",
  "next_hint":        "Инструкция если нет автоматической команды | null",
  "skip_review":      "true | false",
  "last_artifact":    "4_developer_impl.md | null",
  "orch_file":        "archive/team_artifacts/.../orchestration_cursor_ai.md | null",
  "warnings":         [],
  "execution_auto":   "true (execution_auto route) | false (orchestration route) | absent (не ready_fresh)",
  "complexity":       "low | medium | high | absent",
  "complexity_route": "execution_auto | orchestration | absent",
  "has_us_or_cjm":    "true | false | absent"
}
```

`next_cmd` — готовая копипаста команда. `null` если нужно ручное действие (тогда читать многострочный `next_hint`: шаги, промпт агента и футер со ссылкой на этот документ / `file:///…`).

Поля `execution_auto`, `complexity`, `complexity_route`, `has_us_or_cjm` присутствуют только в состоянии `ready_fresh`.

---

## Интеграция с другими инструментами

| Инструмент | Связь |
|-----------|-------|
| `pipeline_status.py` | Детальный дашборд (DoD, метрики, autonomous runs). Роутер — для быстрого следующего шага; pipeline_status — для диагностики |
| `generate_orchestration_prompt.py` | Роутер вызывает его как `next_cmd` в `ready_fresh` для accepted learning-product пакетов с US/CJM, а также для medium/high complexity |
| `run_autonomous.py` | Вызывается в: (1) `ready_fresh/execution_auto` — генерирует `current_task.md` + `task_started.md`; (2) `wip_running`, `ready_executing` и `ready_orch` после готового контракта — `--post-agent`. В `ready_orch` текущая задача пишется самим `workflow.py` как ссылка на существующий `orchestration_*.md`, чтобы не заменить orchestration quick execution prompt'ом |
| `prompt_utils.classify_package_complexity` | Вызывается в `ready_fresh` для mechanical complexity; сигналы: write_set, dod, outcomes, user_stories, dir_breadth, hot_paths, risk_keywords. Его `route` не заменяет lifecycle rule `has_us_or_cjm → orchestration-first` |
| `collect_workflow_metrics.py` | Собирает отчёт по прогону: business metrics (закрытые пакеты, US/CJM, DoD pass), system metrics (timing JSON, closure modes, artifact completeness), model metrics (LLM cost logs и trigger JSONL для Cursor/DeepSeek). Пример: `.\.venv\Scripts\python.exe scripts\collect_workflow_metrics.py --package <id> --write` |
| `backlog_registry_lint.py` | После ручных правок YAML — sync производных (в т.ч. `tasklist.md` для людей); **роутер этот файл не читает и не проверяет** |
| `workflow_strings.py` | SSoT текстов промпта агента и футера со ссылкой на `workflow_router.md`; используется из `workflow.py` |
| `workflow_decision_tree.md` | TL;DR в этом файле теперь ссылается на `workflow.py` как основную команду |

---

## Как роутер определяет активный пакет

1. Проверяет поле `active_package_id` в `backlog_registry.yaml`
2. Если не задано — ищет пакет в `now`-секции реестра по приоритету `wip > ready > open > proposed`
3. Если нет ни одного — состояние `no_package`

Функция: `_find_active_package()` → `active_ready_package_from_registry()` + fallback через `select_package()`.

---

## Тесты

```bash
.venv\Scripts\python.exe -m pytest tests/test_workflow_router.py -v
```

35 тестов покрывают:
- Все 6 состояний `resolve_state()` (включая `ready_executing` и `wip_running` без orch)
- `_package_status()`, `_last_orchestration_step()`
- CLI-флаги `--json`, `--status`, `--agent`, `--exec`, `--skip-review`, `--package`
- `--loop` + `--watch-contract`: переходы (needs_plan, ready_fresh, ready_executing, ready_orch, wip_running)
- Non-blocking pause: sentinel `task_started.md` создаётся; exit 0 без polling
- `workflow_strings.py`: промпт и футер со стабильными якорями; документ `workflow_router.md` ссылается на SSoT
- Doc-санити: TL;DR в decision_tree, структура orchestration_prompt, archive/

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-05-02 | Создан `scripts/workflow.py` (dx-p3-smart-router) |
| 2026-05-02 | Заменил `start_workflow.md` (PS-скрипты) как основной entry point |
| 2026-05-02 | Добавлен `--exec` флаг для автоматического запуска следующего шага |
| 2026-05-03 | Добавлен `--skip-review` — без паузы на ревью контракта между plan-next и `generate_orchestration_prompt.py` |
| 2026-05-03 | Добавлен авто-цикл (`--loop`): `--loop-max`, `--watch-contract`, `--watch-timeout` |
| 2026-05-03 | Non-blocking PAUSE для `execution_auto`: `task_started.md` sentinel, `STATE_READY_EXECUTING`, повторный запуск подхватывает контракт |
| 2026-05-03 | Документ и консольный вывод синхронизированы (пошаговые подсказки, `file:///…`, один проход текста для `ready_executing` в `--loop`) |
| 2026-05-04 | **Надёжность SDK-триггера**: предсказуемые exit codes `cursor_agent_trigger.ts` (1–4), один retry для retryable SDK; в `workflow.py` — подсказки по rc при ошибке `--trigger-cmd`; таблица кодов в этой секции |
| 2026-05-03 | **`--trigger-cmd` + `scripts/cursor_agent_trigger.ts`**: автозапуск Cursor Agent через `@cursor/sdk` в `--loop --watch-contract` для `execution_auto` и `ready_orch`; в env — `CURSOR_API_KEY` (см. `.env.example`) |
| 2026-05-03 | Вынесены канонические строки промпта и футера документации в `scripts/workflow_strings.py`; стабильные якоря в `workflow_router.md` |
| 2026-05-05 | **`--post-agent-no-dod-cache`** (только с `--loop`): каждый `--post-agent` с полным прогоном DoD без `dod_cache.json` |
| 2026-05-17 | Trigger runtime вынесен в `scripts/_trigger_shared.ts`; Cursor и DeepSeek wrapper'ы используют общий heartbeat/metrics/contract gate. Добавлен пример `scripts/deepseek_agent_trigger.ts` для `--trigger-cmd`. |

---

## Trigger wrappers (`--trigger-cmd`)

**Пошаговые инструкции:** [`workflow_cursor_sdk_trigger_guide.md`](guides/workflow_cursor_sdk_trigger_guide.md) · [`workflow_deepseek_api_trigger_guide.md`](guides/workflow_deepseek_api_trigger_guide.md) · [DeepSeek TUI implementation plan](guides/workflow_deepseek_tui_trigger_implementation_plan.md)

Реализовано в пакете **workflow-dx-p6-cursor-sdk-trigger** и расширено общим runtime для нескольких trigger-wrapper'ов:

- Скрипт **`scripts/cursor_agent_trigger.ts`**: читает задачу (argv / `WORKFLOW_CURRENT_TASK_PATH`), вызывает `Agent.prompt`, ключ **`CURSOR_API_KEY`** только из окружения. Использовать с `--agent cursor_ai`.
- Скрипт **`scripts/deepseek_agent_trigger.ts`**: экспериментальный Chat API handoff-only wrapper. Он читает задачу, вызывает DeepSeek OpenAI-compatible Chat API и может записать `BLOCKED: no local tool access`; он не выполняет локальные file/shell operations и не является production executor. Использовать только с `--agent continue` для диагностики/handoff.
- Общий runtime **`scripts/_trigger_shared.ts`**: task path resolution, Moscow timestamps, heartbeat, metrics JSONL, contract readiness gate, final banner.
- Роутер: production path — **`--trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts"`** вместе с **`--loop --watch-contract`**. DeepSeek Chat API path remains experimental handoff-only; target DeepSeek executor is the planned `deepseek_tui_agent_trigger.ts`.
- Перед первым `./.venv/...` прогоном установите зависимости: `npm install` в корне репозитория.

**Коды выхода `scripts/cursor_agent_trigger.ts`:**

| rc | Значение |
|----|----------|
| 0 | Успех |
| 1 | Локальная конфигурация / I/O (`CURSOR_API_KEY`, чтение файла задачи) |
| 2 | `Agent.prompt` вернул `status=error` |
| 3 | Сеть / transient: retryable `CursorAgentError` после **одной** повторной попытки (2s) |
| 4 | Non-retryable SDK или неожиданное исключение |
| 130 | Trigger прерван пользователем или Windows batch prompt (`Terminate batch job` / `KeyboardInterrupt`) |

`scripts/workflow.py` при `rc≠0` печатает краткую подсказку по этой таблице; для произвольной `--trigger-cmd` — нейтральный текст.

Краткая схема:

```
[LOOP] ready_fresh (execution_auto) или ready_orch
  ├─ run_autonomous → doc/current_task.md (rc≠0: stop, trigger не запускается)
  ├─ [если задан --trigger-cmd] subprocess → SDK Agent.local
  ├─ WATCH archive/.../execution_contract.md
  └─ run_autonomous --post-agent → close
```

Если `execution_contract.md` уже есть до триггера, вызов SDK пропускается (защита от повторного запуска).

---

## Идеи для развития

Эти возможности не реализованы — зафиксированы для оценки при планировании будущих пакетов.

Заменить `time.sleep(poll)` в `_wait_for_file` на `watchdog` (inotify/FSEvents),
чтобы реагировать на появление `execution_contract.md` мгновенно, а не с задержкой до 10 сек.

### Параллельные пакеты

Запуск нескольких `execution_auto` пакетов параллельно — каждый в своём агенте Composer.
Потребует изолированных `current_task_<id>.md` и координации `--post-agent` по завершении каждого.
