# Epoch-Demo: smoke `run_autonomous --post-agent` (реальный CLI, не unit)

**Назначение:** дать агенту **однозначный порядок действий** для быстрого дымового прогона **настоящего** вызова `scripts/run_autonomous.py` в режиме `--post-agent`. Это **не** замена `pytest` и **не** сценарий «запусти тесты в памяти» — процесс должен пройти через **тот же CLI**, что и у человека в терминале.

**Связанные артефакты**

| Что | Где |
|-----|-----|
| Эталонные тексты (копирка для чата) | [scripts/print_epoch_demo_agent_prompts.py](../../scripts/print_epoch_demo_agent_prompts.py) — `PROMPT_EPOCH_DEMO_PACKAGE`, `PROMPT_POST_AGENT_SMOKE` |
| Авто Step C `closed→ready` для `epoch-demo` | [scripts/reopen_epoch_demo_step_c.py](../../scripts/reopen_epoch_demo_step_c.py) — `--reason "..."` (C.1/C.2/C.6/`current_task`/lint; без git commit; без сброса `prompt_utils`); перед lint прочие `ready`/`wip`→`proposed` для инварианта Truth View (`--no-demote-other-active` отключает) |
| Префлайт reopen / статус в registry | [scripts/print_reopen_package_workflow.py](../../scripts/print_reopen_package_workflow.py) — `--package epoch-demo` |
| Канон Step C (closed → ready) | [reopen_package_step_c_prompt.md](reopen_package_step_c_prompt.md) |
| Сводка в каталоге промптов | [doc/prompts_catalog.md](../prompts_catalog.md#epoch-demo-prompt-post-agent-smoke) |
| Реализация CLI | [scripts/run_autonomous.py](../../scripts/run_autonomous.py) |

**Версия / актуализация:** 2026-05-02 (шаг 7 Follow-up для восстановления боевого пакета после автодемоута Step C)

**Инвариант:** `scripts/run_autonomous.py` **не** переоткрывает `epoch-demo` при `closed`. Переоткрытие и sync registry/tasklist — ответственность исполнителя **до** первого вызова этого скрипта с `--post-agent` / `--smoke`.

---

## Пример промпта для агента (быстрый smoke `--post-agent`)

Вставьте в новый чат исполнителя как есть; подставьте корень репозитория вместо `<REPO_ROOT>`. Эталонная копия (может содержать абсолютный путь машины):  
`.\.venv\Scripts\python.exe scripts/print_epoch_demo_agent_prompts.py smoke`

```text
Цель: выполнить быстрый smoke реального CLI-потока `run_autonomous.py --post-agent` на тестовом пакете `epoch-demo` и вручную проверить UX блокировок (не unit-тесты).

Контекст:
- Репозиторий: <REPO_ROOT> (корень checkout: есть каталоги `app/`, `scripts/`, `doc/`)
- ОС: Windows / PowerShell (или ваш терминал; команды ниже — вид для PowerShell из корня репо)
- Python: .\.venv\Scripts\python.exe из корня репозитория
- Пакет: `epoch-demo` — должен быть в `doc/backlog_registry.yaml`, производный `doc/tasklist.md` синхронизирован, есть `archive/team_artifacts/epoch-demo/execution_contract.md`
- Важно: скрипт `scripts/run_autonomous.py` НЕ переоткрывает пакет автоматически. Если в registry статус `closed`, переоткрытие делает исполнитель этого промпта ДО любого запуска `run_autonomous.py`.

Шаги:

1) Перейди в корень репозитория. Префлайт статуса:
   .\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo

2) Только если префлайт показал `registry status: 'closed'` — сразу выполни **автоматический полный Step C** (до шага 3), одной командой из корня репозитория:
   .\.venv\Scripts\python.exe scripts/reopen_epoch_demo_step_c.py --reason "smoke post-agent: registry closed before --post-agent"
   Скрипт выставляет `epoch-demo` в `ready`, при необходимости переводит **остальные** пакеты со статусом `ready`/`wip` в `proposed` (инвариант «один активный» в Truth View; отключить: `--no-demote-other-active`), правит индексы/changelog/`doc/current_task.md` по канону для smoke-пакета `epoch-demo` и дважды вызывает `backlog_registry_lint.py --sync-from-index --write-sync` (второй раз с `--strict`). Он **не** делает git commit (C.8) и **не** сбрасывает `prompt_utils` / `execution_contract.md` — при необходимости сбрось артефакты по промпту `package` (`scripts/print_epoch_demo_agent_prompts.py package`) **после** успешного скрипта и до `run_autonomous.py`, если сценарий требует «чистый» прогон.
   Если автоматизация не подходит (другой пакет, спорный REASON, нестандартные US) — вручную полный Step C по `doc/team_workflow/reopen_package_step_c_prompt.md`, затем всё равно lint как в каноне.
   Если статус уже `ready`/`wip`, шаг 2 пропускаешь (скрипт при вызове тоже noop с кодом 0); достаточно актуального tasklist и `execution_contract.md`.

3) Только после выполнения шагов 1–2 запусти один реальный вызов:
   .\.venv\Scripts\python.exe scripts/run_autonomous.py --post-agent --package epoch-demo --budget-profile strict

   Опционально (без кэша DoD для этого прогона): добавь `--no-dod-cache`

4) Зафиксируй: exit code; ключевые строки stderr/stdout; ветку (verification_only / unknown / execution hard gate / DoD / другое).

5) UX: понятная причина блокировки; actionable next steps; согласованные подсказки (`allow_verification_only`, `evidence_inconclusive_allowed` где уместно); нет противоречий между сообщениями.

6) Краткий отчёт в чат: Command — Exit code — Branch — Key messages (3–8 строк) — UX PASS или FAIL — при FAIL: что не так и куда смотреть (файл/область).

7) **В конце отчёта** (если в шаге 2 сработал автодемоут боевых пакетов `ready`/`wip`→`proposed`, см. строку лога `Truth View: demoted …`, или ты вручную знаешь затронутый `PACKAGE_ID`): сгенерируй **готовый промпт для следующего чата** в отдельном блоке заголовка `### Follow-up: вернуть боевой пакет в ready`. Этот промпт исполнитель вставит в новый чат как есть (с подставленными значениями). Он должен явно требовать:
   - корень репо, интерпретатор `.\.venv\Scripts\python.exe`;
   - **инвариант Truth View:** в `doc/backlog_registry.yaml` среди `items` не более **одной** строки со статусом `ready` или `wip`; прежде чем возвращать боевой пакет `<PACKAGE_ID>` в `ready`, при необходимости **освободить слот** (например вернуть `epoch-demo` в `closed` и зафиксировать закрытие по канону, либо оставить только один активный пакет — выбрать согласованно с owner);
   - для целевого `<PACKAGE_ID>`: `status: ready` (и при необходимости поля по [reopen_package_step_c_prompt.md](reopen_package_step_c_prompt.md) / owner);
   - затем `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`;
   - затем `.\.venv\Scripts\python.exe scripts/roadmap_sync_check.py` (ожидается PASS);
   - краткий итог: какой пакет снова единственный активный `ready`/`wip`, чем подтверждено.
   Если демоута не было (шаг 2 пропущен или список demoted пуст), шаг 7: одна строка «Follow-up не требуется (активные пакеты не понижались)».

Ограничения: не полный `pytest tests/` как замена этому smoke; без force-push; без несанкционированных правок CI.

Критерий готовности: один реальный запуск `--post-agent` выполнен, результат и UX оценены; при понижении боевых пакетов — в отчёте есть блок **Follow-up** из шага 7 (или явная строка что follow-up не нужен).
```

---

## 1. Что считать smoke

- **Да:** один запуск `run_autonomous.py` с флагом `--post-agent` из корня репозитория, с тем же интерпретатором, что в [AGENTS.md](../../AGENTS.md) (по умолчанию `.\.venv\Scripts\python.exe` на Windows). Переоткрытие `epoch-demo` при `closed` — **до** этого запуска (см. промпт § выше), не внутри `run_autonomous.py`.
- **Удобная обёртка (рекомендуется):** `run_autonomous.py --smoke` печатает эталонный текст smoke и запускает тот же `--post-agent` поток для пакета `epoch-demo` (или `--package`).
- **Нет:** `pytest` (в т.ч. «полный suite»), моки `post_agent` из тестов, «псевдо-вызов» без subprocess — если ваша среда требует именно process-level smoke, запускайте **реальную** команду в терминале (или `run_terminal_cmd` с pass-through в stdout/stderr).

---

## 2. Перед запуском (предусловия)

1. Текущая рабочая директория — **корень** репозитория (где лежат `app/`, `scripts/`, `doc/`).
2. **Префлайт статуса (рекомендуется):**

   ```bash
   .\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo
   ```

   - Если в выводе **`registry status: 'closed'`** — выполни **полный** Step C: предпочтительно автоматически `scripts/reopen_epoch_demo_step_c.py --reason "…"` (см. таблицу в шапке документа), либо вручную по канону [reopen_package_step_c_prompt.md](reopen_package_step_c_prompt.md) (включая [`doc/current_task.md`](../current_task.md)), затем при необходимости раздел **C** из промпта `package` в [print_epoch_demo_agent_prompts.py](../../scripts/print_epoch_demo_agent_prompts.py) (сброс `prompt_utils` / `execution_contract`). Это делается **до** запуска `scripts/run_autonomous.py`; сам скрипт **не** переводит `epoch-demo` из `closed` в `ready`/`wip`. Флаги **`--auto-prepare-epoch-demo`** и минимальный scaffold **не** заменяют этот Step C для пакета, закрытого в registry по аудиту/SSoT.
   - Если статус **`ready`/`wip`** — достаточно synced [doc/tasklist.md](../tasklist.md), [archive/team_artifacts/epoch-demo/execution_contract.md](../../archive/team_artifacts/epoch-demo/execution_contract.md) и при необходимости выравнивания `current_task.md`.
3. **Каркас при отсутствии записи:** если пакета нет в `backlog_registry.yaml` — **авто-подготовка** (см. §6, команда с `--auto-prepare-epoch-demo`) или ручной каркас (§4).

> **Внимание:** для **полного** smoke с `--post-agent` happy-path — успех — **exit `0`** (типичный прогон без `--non-stop`). При **`--non-stop`** на том же вызове post-agent успешное продолжение цепочки кодируется **`10`** (см. `run_autonomous_prompt.md`). Режим **`--run-smoke-check-before-pipeline`** (§3) выполняет только **lightweight** preflight и **не** вызывает `--post-agent`; его `0` не заменяет process-level smoke пост-агента.

---

## 3. Pre-flight перед основным pipeline (Zero-Click)

Перед полным прогоном `run_autonomous.py` (режим оркестрации **без** `--post-agent`) можно включить **облегчённый** smoke **внутри того же процесса**:

```bash
.\.venv\Scripts\python.exe scripts/run_autonomous.py --run-smoke-check-before-pipeline --auto-prepare-epoch-demo …
```

- `--run-smoke-check-before-pipeline` — перед основным циклом вызывается `run_smoke(..., lightweight=True)`: печать канонического промпта + лёгкие проверки состояния **`epoch-demo`**. Это **не** то же самое, что `run_autonomous.py --smoke`: **реальный `--post-agent` здесь не запускается**, побочных эффектов закрытия нет.
- `--auto-prepare-epoch-demo` — совместно с preflight чинит/добавляет минимальный scaffold (`epoch-demo` в registry, блок контракта в производном tasklist, артефакты), чтобы основной pipeline не падал на «ряд в таблице без блока контракта».

Если preflight завершается с ненулевым кодом (например ошибка lint tasklist), основной pipeline **не** стартует.

Для проверки **именно CLI `--post-agent`** используй §6 (`--smoke` или прямой `--post-agent`), а не только этот флаг.

---

## 4. ⛔ Шаг 0 (опционально, ручной) — каркас `epoch-demo`

**Когда нужен:** если вы **не** используете `--auto-prepare-epoch-demo` и пакета нет в `backlog_registry.yaml` / нет `execution_contract.md`.

1. Напечатай **эталонный** текст (константа `PROMPT_EPOCH_DEMO_PACKAGE`):

   ```bash
   .\.venv\Scripts\python.exe scripts/print_epoch_demo_agent_prompts.py package
   ```

2. Выполни сценарий из вывода: [doc/backlog_registry.yaml](../backlog_registry.yaml), regenerated [doc/tasklist.md](../tasklist.md), [archive/team_artifacts/epoch-demo/](../../archive/team_artifacts/epoch-demo/).

3. **Проверь:** `epoch-demo` имеет `ready`/`wip` в `backlog_registry.yaml`, `tasklist.md` синхронизирован, файл `archive/team_artifacts/epoch-demo/execution_contract.md` существует.

**Характерная строка, если пакет не найден:** `❌ Package 'epoch-demo' not found in backlog_registry.yaml`

---

## 5. Шаг A — эталонный текст smoke (опционально)

```bash
.\.venv\Scripts\python.exe scripts/print_epoch_demo_agent_prompts.py smoke
```

Команда `run_autonomous.py --smoke` печатает тот же текст автоматически.

---

## 6. Шаг B — реальный вызов CLI (ядро smoke)

**Рекомендуемая команда** (печать эталона + `post-agent`, с авто-каркасом при необходимости):

```bash
.\.venv\Scripts\python.exe scripts/run_autonomous.py --smoke --auto-prepare-epoch-demo
```

**Минимальный вариант** (без авто-каркаса; нужен готовый registry entry + synced tasklist + `execution_contract.md`):

```bash
.\.venv\Scripts\python.exe scripts/run_autonomous.py --smoke
```

**Прямой вызов** (без обёртки `--smoke`):

```bash
.\.venv\Scripts\python.exe scripts/run_autonomous.py --post-agent --package epoch-demo --budget-profile strict
```

**Отладка flaky DoD / принудительный прогон тестов** (кэш DoD отключён):

```bash
.\.venv\Scripts\python.exe scripts/run_autonomous.py --post-agent --package epoch-demo --budget-profile strict --no-dod-cache
```

- Кэш хранится в `archive/team_artifacts/<package>/dod_cache.json`. Флаг `--no-dod-cache` отключает чтение и запись кэша для этого запуска.

- Запись **кода выхода** обязательна. Семантика **`--post-agent`** (`scripts/run_autonomous.py`, `post_agent`; константы `EXIT_*` в модуле):

  | Exit code | Значение (типично) |
  |-----------|---------------------|
  | `0` | DoD прошли, пакет закрыт; **остановка** non-stop цепочки на этом вызове (не `--non-stop`, лимит цепочки, или финиш без кода продолжения) |
  | `10` | То же успешное закрытие при **`--non-stop`**: продолжай в той же сессии с `doc/current_task.md` (пост-audit цепочка). Не решай только по тексту stdout — по коду процесса |
  | `1` | DoD не прошли или иная ошибка после прохода ранних гейтов (см. stdout/stderr «Fix failing tests») |
  | `2` | Пакет не найден в registry; блокирующие roadmap **sync/quality gates** перед закрытием; рассинхрон derived `tasklist` (preflight lint) |
  | `8` | Неверные CLI-флаги (`--post-agent` без `--package`, конфликт с `--smoke`, отрицательные `--non-stop-*`, non-stop policy). После post-agent при `--fail-on-context-errors`: инциденты context в недавних cost logs |
  | `9` | Lock: живой параллельный `run_autonomous` на тот же `--package`; либо lock `doc/current_task.md` при записи задачи GUI-агента |
  | `3` | Нет `archive/team_artifacts/<package>/execution_contract.md` (пропущена фаза исполнения) |
  | `4` | Расхождение DoD с контрактом после генерации execution prompt (anti-drift) |
  | `5` | Отказ **verification_only**: неполное evidence / нет маркера политики / пустой write-set |
  | `6` | Режим **unknown**: нет ни изменений продукта, ни строгого verification-only evidence |

  > **Подробная расшифровка + recovery-команды для любого кода:**
  > ```bash
  > .\.venv\Scripts\python.exe scripts/run_autonomous.py --explain-exit <N>
  > ```
  | `7` | Жёсткий гейт **execution**: нет пересечения write-set с изменёнными файлами; или недоступен git для проверки; пустой write-set когда требуется execution overlap |

  Отдельно: обёртка **`--smoke --auto-prepare-epoch-demo`** для `epoch-demo` может оставаться на **exit `6`**, если scaffold не может собрать доверительное git-evidence (см. текст в auto-generated `execution_contract.md`) — это ожидаемо в некоторых окружениях без корректного git-дерева.

---

## 7. Шаг C — критерии UX (ручная оценка, не assert)

- Сообщения о **причине** блокировки (если есть) — понятны и **действенны**.
- Нет **взаимно противоречащих** подсказок.

Итог: **UX PASS** или **UX FAIL** + куда в коде смотреть (файл/область), если fail.

---

## 8. Ограничения (для агента-исполнителя)

- Не запускать `pytest tests/` **как** замену этому smoke (узкий `pytest` — только если он явно в DoD пакета).
- Без `git push --force`, без несанкционированных правок CI.

**Порядок:** либо **одна** команда `--smoke --auto-prepare-epoch-demo`, либо вручную: Шаг 0 (§4) → при желании §5 (текст) → §6 (CLI).

---

## 9. Критерий готовности (DoD для отчёта)

Один **успешно завершённый** реальный прогон команды из §6 **или** честный отчёт с **ненулевым** exit code, разобранной веткой и оценкой UX.

**Минимальный отчёт в чат:** Command — Exit code — ветка — ключевые строки — UX PASS|FAIL.

---

## 10. CI (GitHub Actions)

При изменениях `scripts/run_autonomous.py`, `scripts/prompt_utils.py` и лаунчеров в PR/push запускается workflow `.github/workflows/run_autonomous_smoke.yml` с командой:

`python scripts/run_autonomous.py --smoke --auto-prepare-epoch-demo`
