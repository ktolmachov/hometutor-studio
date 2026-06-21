# generate_audit_closed_packages_prompt

Актуализировано: **2026-04-29**

Генератор промпта **периодического аудита закрытых пакетов** — запускается раз в месяц
или за **любой заданный период** (диапазон месяцев или календарных дат), чтобы верифицировать:
пакеты со статусом `closed` в SSoT действительно прошли DoD и связанные индексы консистентны.

Связанные файлы:
- [`_common_rules.md`](_common_rules.md) — краткий канон (SSoT, sync после YAML, терминал, token budget)
- `[generate_orchestration_prompt.md](generate_orchestration_prompt.md)` — старт с нуля
- `[generate_resume_prompt.md](generate_resume_prompt.md)` — продолжение прерванной работы
- `[generate_plan_next_prompt.md](generate_plan_next_prompt.md)` — планирование следующего пакета
- `[tester.md](tester.md)` — DoD-чеклист и Regression Suite (используется в Step B)
- `scripts/audit_closed_packages_helpers.py` — парсинг `PERIOD` и выборка пакетов (синхронно с Phase A2)

---

## Когда использовать

| Ситуация | Что запускать |
|----------|--------------|
| Backlog пустой / нужен новый контракт | `generate_plan_next_prompt.md` |
| Есть `ready`/`wip` пакет в `backlog_registry.yaml` | `generate_orchestration_prompt.md` |
| Работа по `PACKAGE_ID` уже начиналась | `generate_resume_prompt.md` |
| **Аудит закрытых за период / месяц / диапазоном дат — верификация SSoT** | **`generate_audit_closed_packages_prompt.md`** ← вы здесь |

---

## Как использовать

Вставить в AI-агент (Claude Code, Cursor AI, Codex):

```
Прочитай doc/team_workflow/generate_audit_closed_packages_prompt.md
и выполни инструкции.
TARGET_AGENT: claude_code
PERIOD: 2026-04
DEPTH: index_only
```

Полный аудит с re-run тестов:

```
Прочитай doc/team_workflow/generate_audit_closed_packages_prompt.md
TARGET_AGENT: claude_code
PERIOD: 2026-04
DEPTH: dod_replay
SCOPE: closed
```

---

## Входные параметры

| Параметр | Default | Варианты | Описание |
|----------|---------|----------|---------|
| `TARGET_AGENT` | (обязательный) | `claude_code`, `cursor_ai`, `codex` | Адаптер синтаксиса |
| `PERIOD` | текущий календарный месяц как `YYYY-MM` | см. таблицу ниже | **Окно аудита** (включительно) |
| `MONTH` | — | `YYYY-MM` | **Alias для `PERIOD`:** если `PERIOD` не задан, использовать `PERIOD=$MONTH` |
| `SCOPE` | `closed` | `closed`, `closed,wip` | Какие **статусы из `doc/backlog_registry.yaml`** включаются в список пакетов за `PERIOD` (см. ниже § SCOPE и переоткрытие). Отдельного значения вида «reopen-all» нет — переоткрытие идёт через Step C промпта при FAIL/STALE. |
| `DEPTH` | `dod_replay` | `dod_replay`, `index_only` | `index_only` — только сверка индексов без re-run тестов |
| `COVERAGE_FIX` | `true` | `true`, `false` | Проверять полноту DoD тестового покрытия по связке `package ↔ CJM ↔ US`. Если `true` и покрытие неполное — добавить недостающие unit/e2e тесты и команды в DoD, не меняя product-код. |

### SCOPE и переоткрытие закрытых пакетов

- **`SCOPE` — только фильтр выборки.** Строки передаются в `scripts/audit_closed_packages_helpers.py` (`parse_scope_csv`), в итератор попадают пакеты, у которых `status` совпадает с одним из перечисленных значений (на практике `closed`, при необходимости вместе с незакрытыми **`wip`** через `closed,wip`). Это задаёт «кого аудировать за период», а не отдельный режим массового revert.
- **Корректное переоткрытие** уже закрытого пакета (перевод **`closed` → `ready`** с сохранением SSoT) выполняется **только** по подтверждённому сбою в **Step A** (индекс) или **Step B** (DoD), через **STEP C — REVERT PROCEDURE** в сгенерированном промпте — не в обход этого шага и не руками только в одном файле.
- **Чек-лист согласованности при переоткрытии** (один `<id>` за раз, см. текст Step C ниже):

  | Шаг | Артефакт / действие |
  |-----|---------------------|
  | C.1 | `doc/backlog_registry.yaml` — статус, `re_entry_condition`, `last_review` |
  | C.2 | `doc/closed_iterations.md` — правка блока Индекс / пометки в Recent, **не** удаляя историю Goal/Delivered |
  | C.3 | `doc/user_stories_index.json` — снять «закрытие» там, где `covered_by` и дата попали под окно аудита |
  | C.4 | `doc/user_stories/<US>.md` — только frontmatter в затронутых US |
  | C.5 | `doc/cjm.md` — синхронизация меток MoT при необходимости |
  | C.6 | `doc/changelog.md` — **только хвост**, новая запись о переоткрытии |
  | C.7–C.8 | Регенерация `doc/tasklist.md` и производных: команды — [**_common_rules.md** § Sync](_common_rules.md); затем один коммит на пакет |

- После переоткрытия пакеты снова ведут через конвейер: **`generate_orchestration_prompt.md`** (см. § Next Actions в шаблоне аудита).
- **Готовый промпт для ручного Step C одного пакета** (без генерации полного audit-промпта): [`reopen_package_step_c_prompt.md`](reopen_package_step_c_prompt.md) — использовать только при подтверждённом сбое Step A/B и с заполненным `REASON`.

**Запрещено для согласованности:** переоткрывать пакет, меняя только `backlog_registry.yaml` или только `tasklist.md`, без остальных шагов из Step C и без lint/sync канона [`_common_rules.md`](_common_rules.md).

### Форматы `PERIOD`

| Формат | Пример | Смысл |
|--------|--------|--------|
| Один месяц | `2026-04` | с 1-го по последнее число месяца |
| Несколько месяцев | `2026-03..2026-05` | с 1-го дня начального месяца по последний день конечного |
| Точные даты | `2026-04-10..2026-04-28` | включительно по дням |

Поля `last_review` / `closed_date` в формате **`YYYY-MM` без дня** сопоставляются как **пересечение целого календарного месяца** с интервалом `PERIOD`.

Парсинг и фильтрация: `scripts/audit_closed_packages_helpers.py` (`parse_period`, `iter_closed_packages_for_period`, `find_closed_iteration_headings_for_period`, `user_stories_by_package_for_period`).

**Имя файлов отчёта:** `PERIOD_SLUG` = `PERIOD` с заменой `..` → `__` (например `2026-04-10__2026-04-28`).

---

## Инструкции для AI-агента

```text
Goal: generate a self-contained AUDIT PROMPT for periodic verification
      of packages with status "closed" (and optionally "wip") whose closure/review
      dates fall in PERIOD.
      The audit prompt is saved and printed for paste into a new agent chat.

INPUTS:
  TARGET_AGENT: <claude_code | cursor_ai | codex>     (required)
  PERIOD:       <see formats above; default = current calendar month as YYYY-MM>
  MONTH:        (optional alias) if PERIOD omitted, same as PERIOD for YYYY-MM only
  PACKAGE:      <specific package ID> (optional) filters the audit to a single package, ignoring PERIOD
  SCOPE:        <closed | closed,wip — default closed> filters backlog_registry statuses for the audit list only; coherent reopen(closed→ready) is STEP C of the emitted prompt, not a separate scope value (see prose section above).
  DEPTH:        <dod_replay | index_only, default = dod_replay>
  COVERAGE_FIX: <true | false, default = true> verifies DoD test coverage against package CJM/US intent; when true, missing tests must be added before PASS.

  Bindings for the generated prompt:
    $PERIOD      — literal period string
    $PERIOD_SLUG — filesystem-safe (.. → __)
    $START_ISO   — inclusive start YYYY-MM-DD (from parse_period)
    $END_ISO     — inclusive end YYYY-MM-DD

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE A1 — READ AGENT ADAPTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read doc/team_workflow/guides/agent_adapter_<TARGET_AGENT>.md
Extract:
  TOOL_SYNTAX      — how the agent invokes shell/read tools
  TOOL_READ        — how to read a file
  TOOL_WRITE       — how to write a file
  TOKEN_BUDGET     — max tokens per call for this agent
  THINKING_BUDGET  — extended thinking / reasoning budget (if any)

Before Phase A2: resolve PERIOD = MONTH if PERIOD unset. Compute ($START_ISO,$END_ISO) = parse_period(PERIOD) using scripts/audit_closed_packages_helpers.py (or equivalent date logic).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE A2 — DISCOVER CLOSED PACKAGES FOR $PERIOD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOKEN SAFETY: never full-read large files; use grep/yq/head as specified.

Implementation reference (single source of truth): `scripts/audit_closed_packages_helpers.py` — тесты: `pytest tests/test_audit_closed_packages_helpers.py`.

Preferred (repo root, one process):

  python -c "
  from pathlib import Path
  import sys, yaml
  ROOT = Path('.').resolve()
  sys.path.insert(0, str(ROOT))
  from scripts import audit_closed_packages_helpers as ach
  PERIOD = '$PERIOD'
  SCOPE = '$SCOPE'
  PACKAGE = '$PACKAGE'
  scopes = ach.parse_scope_csv(SCOPE)
  data = yaml.safe_load((ROOT / 'doc/backlog_registry.yaml').read_text(encoding='utf-8'))
  start, end = ach.parse_period(PERIOD)
  for row in ach.iter_closed_packages_for_period(data, start, end, scopes):
      if PACKAGE and PACKAGE != '$PACKAGE' and row['id'] != PACKAGE: continue
      print(row['id'], '|', row['title'], '|', row['date_for_display'], '|', row['exit_artifact'])
  "

  Collect: REGISTRY_PACKAGES = list of {id, title, last_review, exit_artifact}

Step A2.2 — closed_iterations.md (INDEX ONLY — do not full-read)
  Run: python -c "
  from pathlib import Path
  import sys
  ROOT = Path('.').resolve()
  sys.path.insert(0, str(ROOT))
  from scripts import audit_closed_packages_helpers as ach
  PERIOD = '$PERIOD'
  PACKAGE = '$PACKAGE'
  content = (ROOT / 'doc/closed_iterations.md').read_text(encoding='utf-8')
  start, end = ach.parse_period(PERIOD)
  found = ach.find_closed_iteration_headings_for_period(content, start, end)
  if not found:
      print('NO_PACKAGE_HEADINGS_FOR_PERIOD')
  for pkg, ymd in found:
      if PACKAGE and PACKAGE != '$PACKAGE' and pkg != PACKAGE: continue
      print(pkg, '|', ymd)
  "
  Collect: CI_ENTRIES = list of package IDs from `###` headings whose date ∈ [START_ISO, END_ISO]

Step A2.3 — user_stories_index.json
  Run: python -c "
  from pathlib import Path
  import sys, json
  ROOT = Path('.').resolve()
  sys.path.insert(0, str(ROOT))
  from scripts import audit_closed_packages_helpers as ach
  PERIOD = '$PERIOD'
  PACKAGE = '$PACKAGE'
  data = json.load(open(ROOT / 'doc/user_stories_index.json', encoding='utf-8'))
  start, end = ach.parse_period(PERIOD)
  by_pkg = ach.user_stories_by_package_for_period(data, start, end)
  for pkg, ids in sorted(by_pkg.items()):
      if PACKAGE and PACKAGE != '$PACKAGE' and pkg != PACKAGE: continue
      print(pkg, '|', ','.join(ids))
  "
  Collect: US_BY_PACKAGE = dict {pkg_id → [us_ids]}

Step A2.4 — CROSS-REFERENCE CHECK (before audit)
  For each id in REGISTRY_PACKAGES:
    - present in CI_ENTRIES?       → CI_SYNC: OK | MISSING
    - present in US_BY_PACKAGE?    → US_SYNC: OK | MISSING
  For each id in CI_ENTRIES not in REGISTRY_PACKAGES:
    → flag ORPHAN_IN_CI (in closed_iterations but not registry)
  Print pre-audit sync table:
    "━━━━ Pre-Audit Index Sync: $PERIOD ($START_ISO .. $END_ISO) ━━━━
     | Package ID | Registry | CI Entries | US Index | Pre-check |
     |------------|----------|------------|----------|-----------|
     | <id>       | OK       | OK/MISSING | OK/MISS  | PASS/WARN |"
  Collect: DESYNC_LIST = packages with any MISSING

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE A3 — BUILD AUDIT PROMPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Assemble the audit prompt using the inline-table of packages
discovered in Phase A2. The prompt is self-contained: it does NOT
require re-running this generator.

Use TOOL_SYNTAX from agent adapter for all shell/read instructions
inside the generated prompt.

Insert PERIOD, START_ISO, END_ISO, DEPTH, SCOPE, TARGET_AGENT as literals (not variables).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE A4 — OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Save generated prompt to:
  doc/team_workflow/audit_prompt_${PERIOD_SLUG}_$TARGET_AGENT.md

This generator creates only the main closed-package audit prompt.
For a standalone DoD coverage-completion prompt, run:
  doc/team_workflow/generate_audit_packages_coverage_prompt.md
after the audit group files exist.
If the generated audit workflow creates
  doc/team_workflow/audit_groups_${PERIOD_SLUG}_$TARGET_AGENT/run_next_group_coverage_audit.md,
its `Next Action` block must point directly to the next unresolved
`group_<NN>_*.md` prompt by filename, not back to a master prompt.

Print to user:
  "Audit prompt ready.
   Period: $PERIOD ($START_ISO .. $END_ISO) | Depth: $DEPTH | Scope: $SCOPE | Agent: $TARGET_AGENT
   Packages found: N (REGISTRY) / CI_match: N / Desyncs: N
   Saved to: doc/team_workflow/audit_prompt_${PERIOD_SLUG}_$TARGET_AGENT.md"

Then print the full generated prompt for copy-paste.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GENERATOR RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NEVER full-read doc/closed_iterations.md — only Индекс section + last 30 lines.
- NEVER full-read doc/cjm.md — grep by pkg-id or US-id only.
- NEVER full-read doc/backlog_registry.yaml — yq/python filter by status only.
- For US files: read only frontmatter (head -20 lines).
- Token budget for this generator phase: ≤ 10 000 tokens total.
- Windows: if `python -c` prints Unicode and the console throws `UnicodeEncodeError`, set `PYTHONIOENCODING=utf-8` (or use UTF-8 code page) before running the one-liners.
- Run python scripts/check_readset.py before emitting the final prompt to verify
  the generated prompt itself won't exceed safe read limits.
```

---

## Generated Prompt — Audit Workflow

Ниже — структура промпта, который генерируется фазой A3 и вставляется в новый чат.

```text
╔══════════════════════════════════════════════════════════════╗
║  CLOSED PACKAGES AUDIT — $PERIOD  [$START_ISO..$END_ISO]  [$TARGET_AGENT]            ║
║  Depth: $DEPTH | Scope: $SCOPE                              ║
╚══════════════════════════════════════════════════════════════╝

This is a self-contained audit prompt. Do not re-read the generator.
Run steps A → D in order. Process one package at a time.

── PACKAGE LIST (from registry + index cross-check) ────────────
| # | Package ID | Title | Registry | CI Entries | US Sync | Pre |
|---|------------|-------|----------|------------|---------|-----|
| 1 | <id>       | ...   | OK       | OK/MISS    | OK/MISS | ... |
...
────────────────────────────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP A — INDEX CONSISTENCY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package <id> in the PACKAGE LIST above:

A.1 Registry entry:
  Verify doc/backlog_registry.yaml contains:
    status: closed
    last_review or closed_date falls within [$START_ISO, $END_ISO] (see generator Phase A2)
  → Registry: OK | MISSING

A.2 closed_iterations.md entry:
  Expect a closure heading `### <id> — YYYY-MM-DD` with date in [$START_ISO, $END_ISO]
  (see generator Step A2.2). Supplement: grep -n "<id>" doc/closed_iterations.md
  "Индекс Эпох" rows refer to epoch files (E29…), not package IDs — do not use them as the only CI check.
  → CI Index: OK | MISSING | ORPHAN

A.3 User story consistency:
  python -c "
  import json
  data = json.load(open('doc/user_stories_index.json', encoding='utf-8'))
  stories = data if isinstance(data, list) else (data.get('items') or data.get('stories', []))
  pkg = '<id>'
  relevant = [s for s in stories if s.get('covered_by') == pkg]
  for s in relevant:
      print(s.get('us_id', s.get('id')), s.get('status'), s.get('closed_date', ''))
  "
  For each US with covered_by == <id>:
    status must be 'closed' AND closed_date must fall within [$START_ISO, $END_ISO]
  → US Index: OK | MISMATCH (list affected US IDs)

A.4 CJM consistency:
  If <US-IDs from A.3> is empty, run:
    grep -n "<id>" doc/cjm.md | head -20
  Else run:
    grep -n "<id>\|<US-IDs joined by \\|>" doc/cjm.md | head -20
  Check that corresponding MoT is marked completed (✅).
  → CJM: OK | INCOMPLETE | NOT_FOUND

Record result: A_RESULT[<id>] = {registry, ci_index, us_index, cjm}

If ANY check MISSING/MISMATCH for <id>:
  → Mark INDEX_FAIL[<id>] = true
  → Note specific failure reason
  → Proceed to Step C for this package (skip Step B for it)
Else:
  → INDEX_PASS[<id>] = true
  → Proceed to Step B. Run coverage checks when COVERAGE_FIX is enabled;
    run replay commands only if DEPTH == dod_replay.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP B — DoD COVERAGE + REPLAY  [skip replay if DEPTH == index_only]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package <id> where INDEX_PASS[<id>] == true:

B.0 Build the package test-intent contract:
  Sources (focused reads only):
    - doc/backlog_registry.yaml entry for <id>:
      `cjm_moments`, `user_stories`, `blocks`, `impact`, `exit_artifact`, `dod_commands`
    - doc/user_stories_index.json entries with `covered_by == <id>`
    - affected `doc/user_stories/<US>.md` frontmatter + acceptance notes only
    - doc/cjm.md lines for the package's CJM moments and US IDs

  Derive TEST_INTENT[<id>] as:
    - required unit/integration assertions for service/API/persistence contracts
    - required e2e/smoke assertions for learner-visible CJM behavior
    - required fixtures/golden files for eval/demo/token-safety packages

  Minimum coverage rule:
    - User-visible CJM or UI flow package → at least one e2e/smoke/UI-facing test
      AND focused unit/service coverage for the underlying contract when applicable.
    - Backend/service/infra package → focused unit/integration test(s) proving the
      changed contract, plus CLI/schema checks if the package ships a script/policy.
    - Eval/demo package → scenario/golden/schema validation plus e2e or eval runner.
    - Documentation-only package → lint/schema/link check is acceptable only if
      `allow_verification_only` is explicit or the package has no runtime behavior.

B.1 Audit existing DoD coverage:
  Collect existing commands from:
    - `dod_commands` in doc/backlog_registry.yaml
    - tests/scripts referenced in `exit_artifact`
    - archive/team_artifacts/<id>/3_architect_contract.md DoD section, if present
    - package-specific section in doc/agent_workflow_test_bundles.md, if present

  For every TEST_INTENT item, classify:
    - COVERED_UNIT
    - COVERED_E2E
    - COVERED_SCHEMA_OR_CLI
    - GAP_UNIT
    - GAP_E2E
    - GAP_DOD_COMMAND

  If any GAP_* exists and COVERAGE_FIX == false:
    → DOD_RESULT[<id>] = STALE (coverage gap)
    → record missing tests and proceed to Step C.

  If any GAP_* exists and COVERAGE_FIX == true:
    → write only missing test/fixture files and DoD metadata needed to cover the gap.
    Allowed write-set for coverage fixes:
      - tests/**/*.py
      - tests/e2e/**/*.ts
      - tests/e2e/fixtures/**
      - eval_data/** or tests/eval/** when the package is eval-related
      - doc/backlog_registry.yaml (`dod_commands` only for <id>)
      - doc/agent_workflow_test_bundles.md only when adding a reusable bundle
    Forbidden during coverage fix:
      - product code under app/ or scripts/ except when the test cannot import an
        existing public contract; in that case STOP and report a product-code blocker.
      - changing package status or reopening before Step C.

    After writing tests:
      - Add/complete `dod_commands` for <id> so future audits can replay exactly
        the new coverage.
      - Run the new focused test commands.
      - If new tests fail because product behavior is broken, do NOT fix product code;
        mark DOD_RESULT[<id>] = FAIL and record the failing assertion.

B.2 Read exit_artifact path from registry:
  python -c "
  import yaml
  data = yaml.safe_load(open('doc/backlog_registry.yaml', encoding='utf-8'))
  pkgs = data.get('items', data.get('packages', []))
  pkg = next((p for p in pkgs if p['id']=='<id>'), None)
  print(pkg.get('exit_artifact','') if pkg else 'NOT_FOUND')
  "
  If exit_artifact is empty or file missing → DOD_RESULT[<id>] = STALE; skip B.3–B.5

B.3 Read architect contract (DoD commands only — do NOT full-read):
  head -80 archive/team_artifacts/<id>/3_architect_contract.md
  OR grep -A 5 "DoD\|Definition of Done\|dod_commands" archive/team_artifacts/<id>/3_architect_contract.md
  Extract: DOD_COMMANDS = list of shell commands to run

  TOKEN GUARD: if contract > 300 lines, read only sections matching
  "DoD|Definition of Done|Acceptance|Commands" via grep.

B.4 Run DoD commands:
  For each command in DOD_COMMANDS:
    Execute command.
    Record: exit code, stdout/stderr summary (≤ 10 lines).
  NEVER assume result — execute every command.
  NEVER skip a command because "it probably still passes".

B.5 Run regression bundle:
  python -c "
  import re
  content = open('doc/agent_workflow_test_bundles.md').read()
  # find bundle for this package or closest matching bundle
  pattern = r'(?i)## .*' + re.escape('<id>') + r'\b.*?\n(.*?)(?=^##|\Z)'
  m = re.search(pattern, content, re.M|re.S)
  if m:
      print(m.group(1)[:500])
  else:
      print('NO_BUNDLE_FOUND')
  "
  If bundle found: run bundle commands.
  If NO_BUNDLE_FOUND: run nearest scope bundle from tester.md Промпт 2.

B.6 Determine DoD verdict:
  ALL required TEST_INTENT items covered AND all commands exit 0 AND all assertions pass
    → DOD_RESULT[<id>] = PASS
  Any command non-zero OR assertion failed
    → DOD_RESULT[<id>] = FAIL (record reason)
  exit_artifact missing, commands not found, or unfilled coverage gap
    → DOD_RESULT[<id>] = STALE

  If FAIL or STALE → proceed to Step C for this package.
  If PASS → skip Step C; record in final report.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP C — REVERT PROCEDURE  [only for INDEX_FAIL or DOD FAIL/STALE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ATOMICITY RULE: complete ALL sub-steps for ONE package before moving
to the next. Do not batch. Commit after each package revert.

REASON = concat of failure reasons from Step A and/or Step B.
TODAY = current date in YYYY-MM-DD format.

C.1 backlog_registry.yaml:
  Edit doc/backlog_registry.yaml — for entry with id == <id>:
    status: closed  →  status: ready
    Add field:  re_entry_condition: "audit $TODAY: $REASON"
    Update:     last_review: $TODAY

C.2 closed_iterations.md:
  In "Индекс Эпох" section: find and REMOVE the line containing <id>.
  In "Recent" section: if <id> appears, add inline: ⚠️ REOPENED $TODAY
  DO NOT delete the Goal/Delivered block — preserve history.

C.3 user_stories_index.json:
  For each US where covered_by == <id> AND status == 'closed':
    status: closed  →  status: ready
    Remove closed_date field (set to null or delete key)
  After editing, run sync/lint из [**_common_rules.md** § Sync](_common_rules.md)
  (это регенерирует doc/tasklist.md и другие derived файлы).

C.4 user_stories/<US>.md frontmatter sync:
  For each affected US from C.3:
    head -20 doc/user_stories/<US>.md
    If frontmatter has: status: closed  →  status: ready
    If frontmatter has: closed_date     →  remove or clear it
    Write back the updated frontmatter only (do not touch body).

C.5 cjm.md:
  US_IDS = list of US IDs from C.3
  If US_IDS is empty: grep -n "<id>" doc/cjm.md | head -20
  Else: grep -n "<id>\|<US_IDS joined by \\|>" doc/cjm.md | head -20
  For each matching MoT marked ✅:
    Replace ✅ with 🔁 reopened $TODAY: <id>
  If no match found: add note to audit report (CJM_NOT_MATCHED).

C.6 changelog.md — APPEND ONLY (never rewrite):
  Append to doc/changelog.md:
    ## Reopened: <id> ($TODAY)
    - Reason: $REASON
    - Affected US: <US_IDS>
    - Action: status closed → ready; removed from closed_iterations index
  DO NOT edit existing changelog entries.

C.7 tasklist.md — derived file:
  Already regenerated in C.3 via backlog_registry_lint.py.
  Verify: grep "<id>" doc/tasklist.md confirms entry is present as ready.

C.8 Git commit (one per package):
  git add doc/backlog_registry.yaml doc/closed_iterations.md \
          doc/user_stories_index.json doc/changelog.md \
          doc/tasklist.md doc/cjm.md
  git add doc/user_stories/ -- <affected US files>
  git commit -m "audit($PERIOD_SLUG): reopen <id> — $REASON"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP D — FINAL AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Print structured markdown report:

## Closed Packages Audit — $PERIOD ($START_ISO .. $END_ISO)

| Package | Index Sync | DoD Replay | Verdict | Action |
|---------|:----------:|:----------:|:-------:|--------|
| <id>    | ✅ OK      | ✅ PASS    | PASS    | none   |
| <id>    | ❌ CI MISS | skipped    | FAIL    | reopened |
| <id>    | ✅ OK      | ⚠️ STALE  | STALE   | reopened |

**Summary:** N total | N PASS | N FAIL | N STALE | N REOPENED

### DoD Coverage Gaps / Fixes

| Package | CJM/US intent | Gap | Added tests | DoD commands updated |
|---------|---------------|-----|-------------|----------------------|
| <id>    | ...           | e2e | tests/e2e/... | yes |

### Reopened Packages

| Package | Reason | Affected US | CJM |
|---------|--------|-------------|-----|
| <id>    | ...    | US-123, ... | 🔁  |

### Index Desyncs (not causing revert)
<list packages where only WARN-level issues found, no revert needed>

### Next Actions
- Re-run orchestration for reopened packages via `generate_orchestration_prompt.md`
- Confirm CJM_NOT_MATCHED entries manually if any

Save report to: archive/team_artifacts/audit_${PERIOD_SLUG}/audit_report.md

Update machine-readable raw audit state in:
  archive/team_artifacts/audit_${PERIOD_SLUG}/_audit_raw.json

Required `_audit_raw.json` update:
  - Preserve existing keys such as `results`, `summary`, and `orphan_ci_headings`.
  - Upsert `coverage_groups["group_<NN>"]` after each group coverage report.
  - For every package in the group, record:
      package_id, group_id, coverage_result, added_tests,
      dod_commands_updated, commands_run, blockers, report_path, updated_at.
  - Update `summary.coverage_groups_completed`,
    `summary.coverage_packages_pass`,
    `summary.coverage_packages_fail`,
    `summary.coverage_packages_stale`.
  - Do not treat the group as complete until both the markdown report and
    `_audit_raw.json` are updated.

Refresh coverage analysis after every group coverage update:
  doc/team_workflow/audit_groups_${PERIOD_SLUG}_$TARGET_AGENT/coverage_dod_analysis.md

When to refresh `coverage_dod_analysis.md`:
  - after a group coverage markdown report is saved;
  - after `_audit_raw.json` receives or changes `coverage_groups["group_<NN>"]`;
  - after `doc/backlog_registry.yaml` `dod_commands` changes;
  - after tests/e2e specs/fixtures/eval data are added or changed for coverage.

Refresh requirements:
  - completed packages from `_audit_raw.json` must no longer appear as open gaps;
  - summary counts and wave/group rollups must be recomputed;
  - remaining groups must keep their current gaps visible.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- DO NOT fix product bugs during the audit.
  The audit is read-only except for:
  - coverage fixes in Step B when `COVERAGE_FIX == true` (tests/fixtures/DoD metadata only);
  - revert operations in Step C.
- Coverage fixes may add tests, fixtures, and DoD commands. They must not change product
  behavior. If a new test exposes a product bug, mark FAIL/STALE and use Step C/reopen.
- DO NOT run Step C without confirmed FAIL or STALE from Step A or B.
  INDEX_WARN alone (partial desync with no clear cause) → flag in report only.
- ATOMICITY: one package per transaction. Never batch-revert.
  If the agent crashes mid-Step-C → finish Step C for the in-progress package
  before anything else in the next session.
- Token budget: ≤ 20 000 tokens per package (Steps A+B combined).
  For large contracts: read DoD section only (grep), not full file.
- For DoD replay (Step B): NEVER assume a command passes — run it.
  "Probably still works" is not a PASS verdict.
- For DoD coverage (Step B.0–B.1): NEVER count a package as PASS just because it has
  "tests" in `exit_artifact`. Map each CJM/US acceptance point to an executable test
  or record the exact gap.
- For coverage reports: ALWAYS update
  `archive/team_artifacts/audit_${PERIOD_SLUG}/_audit_raw.json` in the same session.
  A markdown-only group report is incomplete audit state.
- After `_audit_raw.json`, ALWAYS refresh
  `doc/team_workflow/audit_groups_${PERIOD_SLUG}_$TARGET_AGENT/coverage_dod_analysis.md`.
  A raw JSON update with stale coverage analysis is incomplete audit state.
- CJM grep uses US-IDs (from user_stories_index.json) not pkg-IDs directly,
  because CJM references US milestones. pkg-ID grep is supplementary.
- Run python scripts/check_readset.py before each package's Step B
  (см. также token/read-set канон [`_common_rules.md`](_common_rules.md)).
- After all packages processed: run `python scripts/backlog_registry_lint.py`
  with no flags (schema check; exit 0). Если в ходе аудита правились `backlog_registry.yaml` / US index — дополнительно sync из [**§ Sync в _common_rules.md**](_common_rules.md).
```

---

## Token Safety Notes (CLAUDE.md compliance)

| Файл | Как читать |
|------|-----------|
| `doc/closed_iterations.md` | Только секция «Индекс Эпох» + последние 30 строк (`tail -30`). Не full-read. |
| `doc/cjm.md` | `grep -n "<pkg-id>\|<US-id>"` — не full-read. |
| `doc/backlog_registry.yaml` | Python/yq фильтр по `status == closed`, не full-read. |
| `doc/user_stories_index.json` | Python filter по `closed_date` и `covered_by`. |
| `doc/user_stories/<US>.md` | Только frontmatter: `head -20`. |
| `archive/team_artifacts/<id>/3_architect_contract.md` | `head -80` или grep по `DoD\|Commands`. |
| `doc/agent_workflow_test_bundles.md` | grep по package ID — не full-read. |

---

## Сценарии использования

### Сценарий A: Быстрая ежемесячная сверка индексов

```
Прочитай doc/team_workflow/generate_audit_closed_packages_prompt.md
TARGET_AGENT: claude_code
PERIOD: 2026-04
DEPTH: index_only
```

→ Агент выводит таблицу консистентности (registry ↔ closed_iterations ↔ US-index ↔ CJM)
  без запуска тестов. Занимает ~5 минут. Flagged пакеты выносятся в отчёт.

### Сценарий B: Полный DoD replay после серии исправлений

```
Прочитай doc/team_workflow/generate_audit_closed_packages_prompt.md
TARGET_AGENT: claude_code
PERIOD: 2026-04
DEPTH: dod_replay
```

→ Для каждого `closed` пакета апреля запускается полный DoD replay.
  При FAIL — автоматический revert в `ready` со всеми связанными индексами.

### Сценарий C: Глубокий аудит (closed + wip)

```
Прочитай doc/team_workflow/generate_audit_closed_packages_prompt.md
TARGET_AGENT: cursor_ai
PERIOD: 2026-04
SCOPE: closed,wip
DEPTH: index_only
```

→ Включает незакрытые WIP пакеты в сверку индексов.
  Полезно перед ретроспективой или release-freeze.

### Сценарий D: Окно по датам (спринт / хотфиксы)

```
Прочитай doc/team_workflow/generate_audit_closed_packages_prompt.md
TARGET_AGENT: claude_code
PERIOD: 2026-04-10..2026-04-28
DEPTH: index_only
```

→ Только пакеты / US с датами закрытия внутри диапазона (удобно вне календарного месяца).

---

## Связанные файлы

| Файл | Назначение |
|------|-----------|
| `[generate_plan_next_prompt.md](generate_plan_next_prompt.md)` | Планирование следующего пакета |
| `[generate_orchestration_prompt.md](generate_orchestration_prompt.md)` | Запуск оркестрации по контракту |
| `[generate_resume_prompt.md](generate_resume_prompt.md)` | Продолжение прерванной работы |
| `[tester.md](tester.md)` | DoD-чеклист (Промпт 1) и Regression Suite (Промпт 2) |
| `[orchestrator_template.md](orchestrator_template.md)` | Базовый шаблон конвейера |
| `scripts/backlog_registry_lint.py` | Регенерация derived-файлов после revert |
| `scripts/check_readset.py` | Проверка token budget перед каждым Step |
| `scripts/audit_closed_packages_helpers.py` | Единые правила `PERIOD` и фильтрации закрытых пакетов |
| `doc/backlog_registry.yaml` | SSoT статусов пакетов |
| `doc/closed_iterations.md` | SSoT закрытых итераций |
| `doc/user_stories_index.json` | SSoT user story статусов |
