# generate_execution_prompt_auto

Актуализировано: **2026-04-21**

Автоматизированный аналог ручных шагов 1–4 рабочего процесса:
нахождение активного пакета → генерация **self-contained planning prompt** (все фрагменты контекста уже внедрены) → выполнение в текущей сессии → получение Copy-paste execution prompt.

---

> ⛔ **ОБЯЗАТЕЛЬНОЕ ПРАВИЛО ДЛЯ АГЕНТОВ — читать первым:**
>
> `archive/agent_prompts/` — **только для записи**. Читать оттуда prompt запрещено.
>
> - Даже если файл для этого пакета и этой даты уже существует — **всегда запускай скрипт заново**.
> - Скрипт сам создаст новый вариант файла (`_v2`, `_v3` и т.д.) без перезаписи.
> - Если скрипт не запускается (нет Python, ошибка окружения) — это **blocker**: сообщи об этом, не используй архивный файл как замену.
> - Использование archived prompt вместо запуска скрипта — **некорректное выполнение этого workflow**.

---

> Нужно спланировать **новый** пакет (backlog пуст)?
> → [`generate_plan_next_prompt.md`](generate_plan_next_prompt.md)
>
> Работа уже начиналась (есть `archive/team_artifacts/<ID>/`)?
> → [`generate_resume_prompt.md`](generate_resume_prompt.md)
>
> Есть активный `ready`/`WIP` пакет с контрактом — сгенерировать planning prompt?
> → **этот файл** / `scripts/generate_next_prompt.py`

---

## Полная цепочка (ручная vs автоматизированная)

| Шаг | Ручной процесс | Сессия | Что делает агент при этом workflow |
|---|---|---|---|
| 1 | Выбрать пакет из `doc/backlog_registry.yaml` | текущая | Скрипт выбирает `wip` → `ready` → `proposed`; `tasklist.md` только derived display |
| 2 | Составить planning prompt | текущая | `python scripts/generate_next_prompt.py` → self-contained prompt + автоархив в `agent_prompts/` и `team_artifacts/<ID>/` |
| 2а | Выполнить planning prompt | текущая | **Немедленно** выполняет prompt; все нужные фрагменты уже внедрены — дополнительных reads не нужно |
| 3 | Архивировать planning prompt | текущая | Уже сделано автоматически на шаге 2 |
| 4 | Запустить Final planning prompt → взять Copy-paste execution prompt | текущая | Выдаёт готовый Copy-paste execution prompt; сохраняет его в `archive/team_artifacts/<ID>/execution_contract.md` |
| 5 | **Запустить execution prompt для реализации задачи** | ⚠️ **отдельная сессия** | Не выполняется в текущей сессии — только передаётся пользователю |

> **Правило шага 2а:** после того как скрипт вывел planning prompt — выполни его немедленно в этой же сессии. Не останавливайся с сообщением «вставь в новую сессию». Весь контекст pre-extracted — дополнительных file reads не нужно.
>
> **Правило шага 4:** после получения Copy-paste execution prompt — сохрани его в `archive/team_artifacts/<PACKAGE_ID>/execution_contract.md`. Это завершает planning phase.
>
> **Правило шага 5:** Copy-paste execution prompt, полученный на шаге 4, **не выполняется в текущей сессии**. Он передаётся пользователю для запуска в отдельной сессии, где будет реализована задача.

---

## Использование

```bash
# Дефолтный режим: self-contained planning prompt (push-based, весь контекст pre-extracted)
# Архивирование включено по умолчанию — создаёт archive/agent_prompts/ и archive/team_artifacts/<ID>/
# ⚠ Если для пакета уже есть execution prompt → СТОП (предлагает --resume или --force)
python scripts/generate_next_prompt.py

# Указать пакет явно
python scripts/generate_next_prompt.py --package <PACKAGE_ID>

# Список активных пакетов
python scripts/generate_next_prompt.py --list

# ─── Режимы работы с незавершённой реализацией ───

# --resume: сгенерировать prompt продолжения (для пакета с уже существующим exec prompt)
# Запускает DoD, показывает что осталось доделать
python scripts/generate_next_prompt.py --resume

# --force: принудительно сгенерировать новый planning prompt (игнорировать exec artefacts)
# Использовать только если нужен полный перезапуск планирования
python scripts/generate_next_prompt.py --force

# ─── Дополнительные флаги ───

# Без архивирования (только вывод промпта)
python scripts/generate_next_prompt.py --no-archive

# Dry-run: не архивировать, только показать промпт
python scripts/generate_next_prompt.py --dry-run

# --quick: обойти шаги 2–4, сгенерировать execution prompt прямо из контракта
python scripts/generate_next_prompt.py --quick

# --pull: legacy pull-based режим (агент читает файлы сам; предпочти дефолт)
python scripts/generate_next_prompt.py --pull
```

---

## Режимы

### Обнаружение состояния работы (work-state detection)

Перед генерацией промпта скрипт проверяет, было ли уже начато выполнение пакета:

| Состояние | Сигнал | Поведение скрипта |
|-----------|--------|-------------------|
| **Fresh** | Нет артефактов в архиве | Генерирует planning prompt |
| **Planning only** | `team_artifacts/<ID>/planning_prompt.md` есть, exec prompt нет | Предупреждение + продолжает генерацию |
| **Execution started** | `team_artifacts/<ID>/execution_contract.md` ИЛИ **недавний** `agent_prompts/*exec*` для пакета | ⛔ **СТОП** — предлагает `--resume` или `--force` |

Это предотвращает случайный перезапуск работы с нуля, если execution prompt уже существует.

> Примечание: `archive/agent_prompts/` может содержать очень старые файлы. Для work-state detection
> учитываются только **недавние** execution prompts (окно по умолчанию — 14 дней; override через
> `HOME_RAG_AGENT_PROMPT_MAX_AGE_DAYS`).

---

### Дефолтный режим: self-contained planning prompt (push-based)

Скрипт **сам извлекает** нужные фрагменты контекста и **инъектирует** их в prompt:

| Секция | Источник | Что извлекается |
|--------|----------|-----------------|
| Planning template | `doc/agent_workflow_templates.md` | Секция `§ Шаблон planning prompt` |
| Contract | `doc/backlog_registry.yaml` | Поля package entry; `doc/tasklist.md` можно сверять только как regenerated view |
| Acceptance criteria | `doc/user_stories/<us-N>.md` | Блок `**Acceptance:**` |
| CJM moment | `doc/cjm.md` | Строка из таблицы "Критические моменты" + строка Resume из таблицы стадий |
| Recent closed | `doc/closed_iterations.md` | Последние 2 `### ` секции |

**Агент получает полностью готовый prompt** — никаких file reads при выполнении не требуется. Это делает работу детерминированной, token-safe и аудируемой.

### Quick mode (`--quick`)

Обходит шаги 2–4 целиком: execution prompt генерируется **механически из полей контракта**,
без агентской сессии.

Требования для качественного результата:
- поле `EXEC_CONSTRAINTS` заполнено в контракте
- остальные поля (`PAIN_POINT`, `OUTCOMES`, `DOD_COMMANDS`, `WRITE_SET_MAX`) актуальны

### Legacy pull mode (`--pull`)

Исходный pull-based режим: агент сам читает файлы контекста при выполнении промпта.
Использовать только если нужна диагностика или сравнение с push-based.
Может давать BLOCK на preflight из-за большого read-set.

---

## Как скрипт выбирает пакет

Приоритет статусов в Truth View `## Now`:

| Приоритет | Статус |
|-----------|--------|
| 1 (высший) | `WIP` |
| 2 | `ready` |
| 3 | `proposed` |

**Предусловие:** у пакета должна быть полная запись в `doc/backlog_registry.yaml`.

Обязательные поля: `PACKAGE_ID`, `WRITE_SET_MAX`, `DOD_COMMANDS`, `OUTCOMES`, `CJM_STAGE`, `PAIN_POINT`, `USER_STORIES`.

Опциональное поле: `EXEC_CONSTRAINTS` — agent-facing ограничения. Включаются дословно в execution prompt (`--quick`); при push-based режиме содержатся в pre-extracted контракте.

---

## Шаблон self-contained prompt (плейсхолдеры заменяются скриптом)

Скрипт подставляет извлечённые фрагменты вместо `$variable` плейсхолдеров:

```text
Ignore prior responses/tools. Fresh context only.

ALL CONTEXT IS PRE-EXTRACTED BELOW.
Do NOT read additional files. Everything needed for planning is here.

---

## Pre-extracted context for `$package_id`

### 1. Planning template (from doc/agent_workflow_templates.md § Шаблон planning prompt)
$planning_template

### 2. Contract: $package_id (from doc/backlog_registry.yaml)
$contract_text

### 3. Acceptance criteria: $us_label (from $us_path)
$us_criteria

### 4. CJM moment $cjm_stage (from doc/cjm.md)
$cjm_fragment

### 5. Recent closed iterations — last 2 entries (from doc/closed_iterations.md)
$recent_closed

---

## Task

Using ONLY the pre-extracted context above (sections 1–5), produce:

1. Extracted context — 5–10 bullets
2. Final planning prompt for `$package_id` — fully filled, copy-paste ready
   - Write-set (fixed): $write_set_inline
   - DoD commands (fixed): $dod_inline
   - Must begin with: Ignore prior responses/tools. Fresh context only.
   - Total output: max 400 words

Rules: Do not write code. Do not read files. Do not invent facts.
```

### Quick execution prompt (шаблон `--quick` режима)

Используется только при `--quick`. Плейсхолдеры заменяются прямо из контракта:

```text
Implement <PACKAGE_ID> only. Stay strictly in write-set:
<WRITE_SET_MAX файлы>.

Goal: <PAIN_POINT> (<CJM_STAGE>).
<OUTCOMES, пронумерованные>

<EXEC_CONSTRAINTS — если поле задано в контракте>

Do not touch: files outside the write-set above.

Before editing:
1. Check whether the requested behavior is already implemented in the current
   codebase.
2. If it is already done, do not make cosmetic rewrites. Run the DoD and close
   as verification-only with strict evidence.
3. Verification-only evidence must include a concrete commit SHA that changed
   at least one referenced product/test file, plus the repo paths it delivered.

Run:
<DOD_COMMANDS, по одному в строку>
Return: product changed files, why, and proof that all DoD branches are covered.
If no product files changed, report this as verification-only and include
`Pre-existing delivery evidence` with a concrete commit SHA that changed at
least one referenced path plus existing repo paths that already delivered the
capability. Vague claims such as
"pre-existing in current branch history" are invalid and must be blocked by
`--post-agent`.
```

`EXEC_CONSTRAINTS` — опциональное поле. Если отсутствует, блок пропускается.

---

## Preflight

В дефолтном (push-based) режиме preflight не запускается — всё нужное уже pre-extracted.

В `--quick` и `--pull` режимах скрипт автоматически запускает:
```bash
python scripts/check_readset.py --signatures <READ_SET_HINT files>
```

| Результат | Поведение |
|-----------|-----------|
| `SAFE` | Prompt выводится без предупреждений |
| `WARN` | Prompt + предупреждение "compress read-set" |
| `BLOCK` | Prompt + предупреждение "use rg/grep and section reads only" |

---

## Архивирование

> ⛔ `archive/agent_prompts/` — **только для записи**. Никогда не читать оттуда prompt для повторного использования.

Архивирование включено **по умолчанию** (используй `--no-archive` или `--dry-run` для отключения).

При каждом запуске в дефолтном или `--pull` режиме скрипт создаёт:

```
archive/agent_prompts/<package_slug>_planning_prompt_<YYYY-MM-DD>.md     ← prompt
archive/team_artifacts/<PACKAGE_ID>/planning_prompt.md                   ← инициализация папки пакета
```

Для `--quick`:
```
archive/agent_prompts/<package_slug>_exec_prompt_quick_<YYYY-MM-DD>.md
```

Существующие файлы не перезаписываются — добавляются суффиксы `_v2`, `_v3`.
Также обновляет `archive/agent_prompts/README.md`.

### Execution contract (после шага 4)

После того как агент выполнит Final planning prompt и получит Copy-paste execution prompt,
он должен сохранить его в:
```
archive/team_artifacts/<PACKAGE_ID>/execution_contract.md
```

Это делает execution prompt доступным для execution-агента (шаг 5) и сигнализирует,
что планирование завершено. Если этот файл уже существует — применяется resume workflow.

---

## Пример вывода (дефолтный push-based режим)

Параметры при генерации (подставлены вместо $плейсхолдеров):

| Плейсхолдер | Значение |
|---|---|
| `$package_id` | `epoch-us7-3-resume-card` |
| `$us_label` / `$us_path` | `US-7.3` / `doc/user_stories/us-7.3.md` |
| `$cjm_stage` | `#5 — Return next day` |

```
→ Selected package: epoch-us7-3-resume-card  (status: ready)
→ Mode: self-contained planning prompt [push-based, default]
→ Preflight: not needed (self-contained — all context pre-extracted)
→ Extracting context fragments …

======================================================================
Self-contained planning prompt  — EXECUTE NOW in this session
======================================================================

Ignore prior responses/tools. Fresh context only.

ALL CONTEXT IS PRE-EXTRACTED BELOW.
...

### 2. Contract: epoch-us7-3-resume-card (from doc/backlog_registry.yaml)
PACKAGE_ID: epoch-us7-3-resume-card
CJM_STAGE: #5 — Return next day
PAIN_POINT: Пользователь возвращается и не понимает, где был вчера...
...

### 3. Acceptance criteria: US-7.3 (from doc/user_stories/us-7.3.md)
**Acceptance:**
- Given существует `tutor_learning_resume` с session_id и topic,
- When я открываю UI,
- Then в hero виден resume card с topic, last_action, due_count и кнопкой "Продолжить".

### 4. CJM moment #5 — Return next day (from doc/cjm.md)
Критические моменты (момент #5):
| 5 | Возврат на следующий день | Resume card видна сразу | "Где я был вчера?" |

### 5. Recent closed iterations — last 2 entries
### epoch-17-1-ux-tail — 2026-04-20
- Goal: finish UX-tail polish...
### epoch-micro-quiz-feedback-tail — 2026-04-20
- Goal: remove CJM #4 micro-quiz flow break...

---

## Task
...Write-set (fixed): `app/ui/resume_cards.py`, `app/ui/home_hub.py`, ...
...DoD commands (fixed): `python -m pytest tests/test_resume_cards.py -v`...
```

---

## Ограничения и когда НЕ использовать

- Скрипт работает только если у пакета есть **полная запись** в `doc/backlog_registry.yaml`.
- Для пакетов без контракта — сначала запусти `generate_plan_next_prompt.md`.
- `--quick` без заполненного `EXEC_CONSTRAINTS` даёт неполный execution prompt.
- Если скрипт не запускается — **сообщи о blockerе** (причина + команда), не бери prompt из архива.
- `archive/agent_prompts/` — только для записи результатов, не источник для повторного чтения.

---

## Связанные файлы

- [`generate_plan_next_prompt.md`](generate_plan_next_prompt.md) — когда backlog пуст
- [`generate_orchestration_prompt.md`](generate_orchestration_prompt.md) — полная командная оркестрация
- [`generate_resume_prompt.md`](generate_resume_prompt.md) — продолжение с точки остановки
- [`doc/backlog_registry.yaml`](../backlog_registry.yaml) — источник контрактов и статусов
- [`doc/tasklist.md`](../tasklist.md) — производное отображение после sync
- [`scripts/generate_next_prompt.py`](../../scripts/generate_next_prompt.py) — скрипт
- [`scripts/check_readset.py`](../../scripts/check_readset.py) — preflight token guard
- [`archive/agent_prompts/`](../../archive/agent_prompts/) — архив сгенерированных prompts
