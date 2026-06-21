# Workflow Для Агентов — Prompt Templates

Часть split-карты [`doc/agent_workflow.md`](agent_workflow.md).
Этот файл содержит: **Planning Prompt, Verify Prompt, Контрактный Prompt для ударных пакетов, Шаблон Постановки Задачи, Eval Runbook pointer, архивированные contract prompts**.

Другие части split-карты:
- [`agent_workflow_rules.md`](agent_workflow_rules.md) — Token Budget & Retry Safety
- [`agent_workflow_cycle.md`](agent_workflow_cycle.md) — базовый цикл, параллелизм, A/B/C split
- [`agent_workflow_arch_review.md`](agent_workflow_arch_review.md) — architecture review (5 фаз)
- [`agent_workflow_test_bundles.md`](agent_workflow_test_bundles.md) — test bundles + low-budget fallback

---

## Чек Перед Стартом

- задача сформулирована через результат, а не через общее пожелание;
- write-set ограничен;
- есть список файлов, которые нельзя трогать;
- есть критерий "готово";
- есть команды проверки.

### Planning Prompt — Планирование Следующей Итерации

Системное правило для агентов:
- Отвечать на русском языке.
- Формулировать ответы лаконично: без длинных вступлений и лишней воды.
- Не раздувать итоговые отчёты после рутинных действий.
- Emoji использовать умеренно — только где они реально помогают структуре или навигации (заголовки, списки, предупреждения). Без множества смайликов.

#### Token Budget & Retry Safety

→ Применяется ко всем вызовам. Полные правила: [`agent_workflow_rules.md`](agent_workflow_rules.md).

Перед началом новой эпохи или пакета запускать отдельный planning-поток. Агент **не пишет код**, а выдаёт готовый execution contract.

### Какие файлы читать (Ограничение до 3–5 Файлов)

⚠️ **Читать ровно СТОЛЬКО файлов, СКОЛЬКО явно перечислено в контракте задачи. Лишние файлы запрещены.**

**🚨 ОБЯЗАТЕЛЬНО: если ваш файл из ❌ списка ниже, используйте метод из [doc/token_safety.md](token_safety.md#таблица-безопасного-включения-критические-файлы)**

| Файл | Зачем | Когда читать | ⚠️ ОСТОРОЖНО |
|---|---|---|---|
| **1. Целевой файл кода** (e.g., `app/query_service.py`) | Текущее состояние: signatures, структура | Всегда (если есть пакет) | Если > 600 строк: читайте только signatures, не полное тело |
| **2. Целевой юнит-тест** (e.g., `tests/test_query_service.py`) | Existing patterns, DoD baseline | Всегда (если есть пакет) | Если > 800 строк: читайте только 1–2 теста или fixtures, не весь файл |
| **3. `doc/backlog_registry.yaml` — ТОЛЬКО запись целевого пакета** (не весь файл) | Status, ownership, dependencies | Для планирования только | **НИКОГДА не читайте файл целиком** |
| **4. `doc/user_stories/<US-N>.md` — ТОЛЬКО acceptance criteria** (не вся папка) | Given/When/Then для целевой US | Только если эпоха привязана к US | Читайте **одну** US, не папку целиком |
| **5. `doc/conventions.md` — ТОЛЬКО секция для целевого area** | Инженерные ограничения | Только если нужны инженерные шаблоны | Можно читать целиком (~1k est токенов), но лучше нужную секцию |
| ❌ **ЗАПРЕЩЕНО целиком** | — | — | `app/query_service.py`, `app/knowledge_graph.py`, `tests/test_api.py`, `doc/changelog.md`, `doc/adr.md`, `doc/architecture.md`, `doc/cjm.md`, `doc/epochs/*`, `doc/epochs/e4.md`, сам `doc/agent_workflow.md` как полный @-контекст → см. [token_safety.md](token_safety.md#таблица-безопасного-включения-критические-файлы) |

**Правило:** перед добавлением файла в read-set проверьте его в [token_safety.md](token_safety.md). Если там указано "не целиком" — используйте safe method из таблицы.

**Правило:** для каждого вызова явно выписать Read-set (max 5 файлов) перед промтом. Иные файлы читать запрещено.

### Шаблон planning prompt (Рекомендуемый по умолчанию)

⚠️ **TOKEN SAFETY:** перед добавлением файлов в read-set проверьте их в [doc/token_safety.md](token_safety.md). Если файл помечен как unsafe для full-read, используйте safe method из таблицы (signatures, grep, одна секция, summary).

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: plan <epoch-package> ONLY — produce a detailed execution contract.

Cursor token guard:
- Target <=12k input tokens.
- Soft-limit 12k-20k: compress history/read-set before sending.
- Hard stop >20k input tokens: stop before the call and report blocker.
- Owner/write-set files are not read-set.
- Do not attach full files unless listed below as full-read.
- Do not include previous tool logs; fresh context only.

Read ONLY (max 3–5 файлов, не больше):
1. Целевой файл кода (e.g., app/query_service.py) — signatures only, не полное тело
2. Целевой тест (e.g., tests/test_query_service.py) — existing patterns only, not full file
3. doc/backlog_registry.yaml — ONLY the entry for <target-package>, not entire file

Output format:
- Package goal: 1-2 sentences tied to user pain (no CJM preamble)
- Write-set: 3–5 files max to create or modify
- Read-set: 2–3 files max to inspect but not touch
- Do-not-touch list: explicit, 3–5 items
- DoD: exact pytest/command + observable result (1 line each)
- Copy-paste execution prompt (use Micro-Execute template below)

Rules:
- Do not write code. Only produce the plan.
- Owner/write-set files in the generated execution prompt must not imply full-read.
- Do NOT read doc/epochs/, doc/cjm.md, doc/closed_iterations.md, or other doc files beyond the 3 listed.
- If a file >600 lines and you haven't read it before: grep for signatures first, don't read the full body.
- If a US lacks clear acceptance criteria, ask ONE clarifying question only.
- If write-sets overlap, propose a split but do not design both.
- If you cannot finish the plan without a scope decision from PO or split from Architect: add one line
  HANDOFF_SIGNAL: <gap in one phrase> → layer (scope_po | contract)
  then stop (do not invent write-set).
- Total output: max 400 words.
- **Token budget check:** if estimated input is 12k-20k, compress before sending; if it exceeds 20k tokens BEFORE sending, stop and report blocker (see doc/token_safety.md § Правила Сжатия Контекста).

Ignore prior responses/tools. Fresh context only.
```

Навигация:
- Этот шаблон — planning default для новых потоков.
- Если нужен ultra-low-budget режим, используйте `Micro-Plan` ниже.
- Если файл большой или из unsafe-списка, используйте safe method из `doc/token_safety.md`.

### Принципы

- **Сначала read, потом plan, потом prompt** — агент не планирует без контекста.
- **Plan ≠ code** — явно запретить писать код, иначе агент начнёт реализовывать.
- **Output = contract** — результат планирования — готовый copy-paste prompt для execution.
- **Closed epochs как учитель** — последние закрытые эпохи показывают реальный размер и типичные риски (используй только целевые epoch-файлы, не полный closed_iterations.md).
- **Read-set ≤ 5 файлов** — все лишние файлы исключены. Если контекст растёт → перезапусти с меньшим read-set, не добавляй файлы.

## Verify Prompt — Проверка Выполненного Пакета

После того как агент-исполнитель завершил пакет, запускать верификацию в **отдельном потоке**.

Универсальный шаблон: [`prompts/agent_prompts_verify.md`](prompts/agent_prompts_verify.md).

Заполнить четыре параметра перед запуском:

| Параметр | Пример | Описание |
|---|---|---|
| `CONTRACT_FILE` | `archive/agent_prompts/e14_arch_hardening_2026-04-12.md` | Файл контракта, по которому работал исполнитель |
| `PACKAGE_ID` | `E14-B` | Идентификатор пакета |
| `COMMIT_RANGE` | `HEAD~1..HEAD` | Диапазон коммитов для scope check |
| `PACKAGE_TYPE` | `code` / `doc` / `mixed` | Тип пакета — определяет строгость scope check |

Шаблон выполняет пять шагов: **scope check** → **DoD checklist** → **spot check качества** → **regression check** → **verdict**.

Вердикты:
- **PASS** → закрыть пакет: `backlog_registry.yaml` + regenerated `tasklist.md` + `closed_iterations.md` + `changelog.md`.
- **CONDITIONAL PASS** → принять с follow-up в Deferred таблице **+ выдать fix-prompt** (см. ниже).
- **FAIL** → вернуть исполнителю один конкретный blocker **в виде готового fix-prompt** (см. ниже).

При **FAIL** или **CONDITIONAL PASS**, где есть блокирующий риск для доверия к поставке, добавьте строку **`HANDOFF_SIGNAL: …`** (симптом → слой: contract / ui_spec / impl / tests / flaky_env) — см. [`team_workflow/tester.md`](team_workflow/tester.md). Тот же паттерн у исполнителя: [`team_workflow/developer.md`](team_workflow/developer.md).

### Fix Prompt (обязателен для FAIL и CONDITIONAL PASS)

Verify-агент выдаёт готовый copy-paste prompt для fresh-context сессии исполнителя.
Формат — Контрактный Prompt (см. ниже). Требования:
- Write-set ≤ 5 файлов, строго в рамках исходного контракта пакета.
- DoD — конкретные pytest/rg команды + expected output на каждый blocker.
- Первая строка: `Ignore prior responses/tools. Fresh context only.`
- Ссылка на исходный `CONTRACT_FILE` и `COMMIT_RANGE`, без копирования их тел.
- Token budget:
  - Target <=12k input tokens.
  - Hard stop >20k input tokens.
  - If estimated input is 12k-20k, compress before sending.
  - No retry with unchanged payload.
- Для CONDITIONAL PASS — findings в fix-prompt отмечены как `follow-up`, не блокирующие merge.
- Fix-prompt может включать строку **HANDOFF_SIGNAL** из вердикта verify — чтобы исполнитель понимал слой проблемы без повторного diff всего чата.

⚠️ **TOKEN SAFETY:** при verify, избегайте читать полные большие файлы. Читайте только:
- **commit diff** (обычно <3k токенов);
- **contract file** (~1.5k токенов);
- **DoD критерии** (явно указаны в контракте);
- **точечные тесты** (1–2 specific test case, не весь файл).

Не читайте:
- `doc/changelog.md` целиком (~15.8k est) — только append-target / хвост;
- `tests/test_*.py` целиком — только grep "def test_<pattern>";
- `doc/backlog_registry.yaml` целиком — только целевую запись.

Принципы:
- **Отдельный поток** — верификатор не видит историю исполнителя, смотрит только на контракт и код. **Ignore prior responses/tools. Fresh context only.**
- **Token budget target <=12k (hard stop >20k)** — читать ТОЛЬКО commit diff, DoD-критерии, contract file, не весь проект. В диапазоне 12k-20k обязательно сжать контекст перед отправкой.
- **Verify ≠ fix** — верификатор не правит код; при FAIL возвращает точный blocker.
- **HANDOFF_SIGNAL** при FAIL / блокирующем debt — см. блок вердиктов выше и [`team_workflow/tester.md`](team_workflow/tester.md).
- **Один пакет за раз** — не верифицировать C до закрытия B.

---

## Контрактный Prompt Для Ударных Пакетов

Этот execution prompt обычно генерируется через `Шаблон planning prompt` выше.
Если пакет ещё не оформлен в `write-set` / `DoD` / `do-not-touch`, сначала запускать planning, а не execution.

Для быстрого и экономного выполнения backlog-пакетов начинать новый поток с контрактного запроса, а не с широкого анализа. Один prompt должен закрывать ровно один package/outcome и заранее запрещать расползание в соседние эпохи.

Принципы:

- **WIP=1:** один пакет, один DoD, один проверочный набор.
- **Контекст короткий:** не вставлять весь `backlog_registry.yaml` или `tasklist.md`; дать `epoch-package`, цель, 2-5 файлов и критерий готовности.
- **Scope явный:** перечислить, что менять, что смотреть первым и что не трогать.
- **Выход структурный:** требовать changed files, tests, completed work, unresolved risk; при срыве outcome или падении тестов — строку **HANDOFF_SIGNAL** (как в [`team_workflow/developer.md`](team_workflow/developer.md)).
- **Архив отдельно:** после закрытия пакета обновлять `backlog_registry.yaml`, регенерировать `tasklist.md`, а детали переносить в `closed_iterations.md`.

Короткий шаблон:

```text
Goal: close <epoch-package> only.
Scope: <one concrete outcome>.
Files to inspect first: <file1>, <file2>, <tests>.
DoD: <test/command> green; <observable result>.
Do not touch: <out-of-scope areas>.
Output: changed files + tests + unresolved risk.
If blocked, failing tests, or non-trivial unresolved risk: add one line HANDOFF_SIGNAL: <symptom> → layer (contract | ui_spec | tests | env | scope_po).
```

Полный шаблон:

```text
Goal: close <epoch-package> only.

Context:
<1-2 строки: какую CJM-боль или user-visible outcome закрывает пакет.>

Scope:
<что именно сделать, в 1-3 пунктах.>

Read ONLY / files to inspect first:
- <file/path.py>
- <file/path.py>
- <tests or nearby modules>

DoD:
- <точный критерий готовности>
- <команда проверки>
- <ожидаемый результат>

Do not touch:
- <соседняя эпоха / outcome>
- <нерелевантные файлы или подсистемы>
- <документы, если их нельзя менять>

Working rules:
- Prefer existing patterns.
- Keep changes minimal and scoped to this package.
- Do not refactor unrelated code.
- Owner/write-set files are not read-set; read full files only when explicitly listed under Read ONLY.
- For files >600 lines or known unsafe files, use rg/signatures/one section first.
- If blocked, report the smallest blocker and the exact file/command where it appears.
- If outcome not achieved or you must stop early: in Output add exactly one line:
  HANDOFF_SIGNAL: <visible symptom> → layer (contract | ui_spec | tests | env | scope_po)
- Token budget per LLM call:
  - Target <=12k input tokens.
  - Soft-limit 12k-20k: compress history/read-set before sending.
  - Hard-limit >20k: stop and report blocker.
  - No retry with unchanged payload (max 1 safe retry, then stop and report).

Output:
- Changed files
- Tests run + result
- What was completed
- Unresolved risk / follow-up, if any
```

Пример для текущего roadmap:

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: close E10.2-A only.

Context:
Close the Micro-quiz pain point by making quiz difficulty adapt to the learner mastery vector.

Scope:
Implement adaptive quiz difficulty for micro-quiz and self-check quiz:
- recognition -> beginner
- recall -> intermediate
- transfer -> advanced
- safe fallback when mastery is missing

Read ONLY / files to inspect first:
- app/quiz_service.py
- app/ui/quiz_panel.py
- app/ui/scoped_quiz.py
- tests around quiz behavior

DoD:
- pytest tests/test_quiz_adaptive_difficulty.py green
- 3 difficulty levels covered
- missing mastery fallback covered

Do not touch:
- install / README
- router eval
- progress / graduation
- unrelated UI refactors

Output:
- Changed files
- Tests run + result
- What was completed
- Unresolved risk / follow-up, if any
```

## Шаблон Постановки Задачи Агенту

Этот шаблон предназначен для постановки задачи человеком / owner'ом.
Для planning нового потока по умолчанию используйте `Шаблон planning prompt`, а не этот skeleton.

Ниже шаблон, который можно копировать почти без изменений.

```text
Задача:
<что нужно получить в итоге>

Scope:
<какой slice системы меняем и какой не меняем>

Owner files:
- <файл 1>
- <файл 2>

Read ONLY:
- <2-3 файла или секции; owner files не читать целиком, если они не перечислены здесь>

Do not touch:
- <файл или зона 1>
- <файл или зона 2>

Definition of Done:
- <пользовательский или технический результат 1>
- <контракт/поведение 2>

Verification:
- <pytest или smoke команда 1>
- <pytest или smoke команда 2>

Doc sync:
- <какие doc-файлы обновить, если изменится контракт или статус>
```

Короткий пример:

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Задача:
Расширить typed tutor payload для UI summary.

Scope:
Только read-path и API/UI surfaces, без изменений orchestration core.

Owner files:
- app/query_service.py
- app/api_models.py
- app/tutor_learner_contract.py
- app/ui/helpers.py
- app/ui/main.py

Read ONLY:
- app/query_service.py — signatures only + exact payload builder section
- tests/test_query_service.py — relevant typed payload test only
- doc/backlog_registry.yaml — target package entry only

Do not touch:
- app/pipeline_steps.py
- app/tutor_orchestrator.py
- app/tutor_prompts.py

Definition of Done:
- tutor payload содержит новый typed summary
- UI использует typed fields без опоры на debug

Verification:
- .\.venv\Scripts\python.exe -m pytest tests/test_query_service.py tests/test_api.py tests/test_ui_helpers.py

Doc sync:
- doc/api_reference.md
- doc/user_guide.md / doc/user_guide_details.md
- doc/changelog.md
```

## Eval Experimenter Runbook

Пошаговая инструкция для ручного прогона eval loop с передачей результатов агенту: `doc/eval_experimenter_runbook.md`.

## Архивированные Contract Prompts

Архивные копии contract prompts (Context / Scope / Working rules) живут отдельными файлами в `archive/agent_prompts/` (генерируется скриптами). Индекс: [`prompts/agent_prompts_index.md`](prompts/agent_prompts_index.md).


Чтобы добавить следующий prompt в архив, используйте helper [`prompts/ARCHIVE_ADD_PROMPT.md`](prompts/ARCHIVE_ADD_PROMPT.md): он создаёт отдельный `.md` файл в `archive/agent_prompts/`.
