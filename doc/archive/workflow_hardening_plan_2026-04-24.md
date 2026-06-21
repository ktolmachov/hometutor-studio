# Workflow Hardening Plan — 2026-04-24

Цель: зафиксировать план исправлений для workflow-документации и prompt-контрактов так,
чтобы следующая fresh-context сессия могла реализовать изменения без повторного расследования.

Этот план основан на критической проверке:

- `doc/agent_workflow.md`
- `doc/agent_workflow_arch_review.md`
- `doc/agent_workflow_rules.md`
- `doc/agent_workflow_templates.md`
- `doc/team_workflow/orchestrator_template.md`
- связанных prompt/guard артефактов

## Executive Summary

Главная проблема не в одном документе, а в рассинхронизации контрактов для агентов.
Каноническое правило проекта уже требует target `<=12k`, soft `12k-20k`, hard `>20k`
для входного контекста, но часть orchestration/fix prompt шаблонов все еще разрешает
старый режим `20k-30k` или пишет только `<=20k` без обязательного target `<=12k`.

Это критично: следующий агент может получить copy-paste prompt, который формально
нарушает `AGENTS.md` и `doc/agent_workflow_rules.md`, а затем сорваться в context overflow,
дорогой LLM-вызов или некорректный retry.

Нужный прорыв качества: превратить workflow-доки из набора советов в проверяемый контракт.
Для этого надо синхронизировать budget language, исправить Windows-unsafe evidence commands,
закрепить `.venv`-first Python policy, убрать битые/устаревшие ссылки и добавить автоматический
lint, который не даст этим ошибкам вернуться.

## Current Evidence

Проверки, выполненные 2026-04-24:

```powershell
.\.venv\Scripts\python.exe scripts/check_readset.py `
  doc/agent_workflow.md `
  doc/agent_workflow_arch_review.md `
  doc/agent_workflow_rules.md `
  doc/agent_workflow_templates.md `
  doc/team_workflow/orchestrator_template.md
```

Результат: `BLOCK`, estimated total около `20.7k` токенов. Вывод: эти документы нельзя
вставлять в одну LLM-сессию целиком; следующая реализация должна читать их точечно.

```powershell
.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py
```

Результат: `OK`. Важно: текущий lint не ловит смысловой drift вроде `Hard-limit > 30k`.

```powershell
.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py
```

Результат: `PASS`, context_length ошибок в недавних логах нет.

## Critical Findings To Fix

### WF-HARDEN-001 — Старый token budget в team orchestrator

Severity: critical.

Файл:

- `doc/team_workflow/orchestrator_template.md`

Проблемные строки:

- `Token budget per LLM call: target <= 20k input tokens.`
- `Soft-limit 20k-30k`
- `Hard-limit > 30k`

Почему критично:

- Канон проекта: target `<=12k`, soft `12k-20k`, hard `>20k`.
- Orchestrator template генерирует реальные copy-paste prompts.
- Агент может считать контекст до 30k допустимым, хотя `AGENTS.md` и `agent_workflow_rules.md`
  уже запрещают такой вызов.

Исправление:

- Заменить budget block на единый canonical wording:

```text
Token budget per LLM call:
- Target: <=12k input tokens.
- Soft-limit: 12k-20k. Compress history/read-set before sending.
- Hard-limit: >20k. STOP before the call and report blocker.
- Read-set max 3-5 files; owner/write-set is not read-set.
- After ERR: max 1 retry, only with reduced context.
```

### WF-HARDEN-002 — Arch-review fix prompts не наследуют target `<=12k`

Severity: critical.

Файл:

- `doc/agent_workflow_arch_review.md`

Проблемные места:

- Fix prompt requirements используют `Token budget: <=20k input tokens`.
- Template в конце также пишет только `<=20k`.

Почему критично:

- Сам arch-review документ уже знает про `12k target / 20k hard-limit`, но copy-paste fix prompt
  передает исполнителю более слабое правило.
- Fix prompt обычно запускается в fresh-context сессии; если там нет `AGENTS.md` в полном виде,
  weak wording становится фактическим контрактом.

Исправление:

- Везде заменить `Token budget: <=20k input tokens` на:

```text
Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
```

### WF-HARDEN-003 — Битая ссылка на Kilo budget в slim index

Severity: warning, но быстро исправляется.

Файл:

- `doc/agent_workflow.md`

Проблема:

- Ссылка `../kilo_budget_system.md` ведет в корень репозитория.
- Реальный файл существует как `doc/kilo_budget_system.md`.

Исправление:

- Заменить ссылку на `kilo_budget_system.md`.

### WF-HARDEN-004 — Unix-only команды в copy-paste evidence/runbook

Severity: critical для Windows-first проекта.

Файлы:

- `doc/agent_workflow_arch_review.md`
- возможно `doc/agent_workflow_templates.md`
- возможно `doc/team_workflow/*.md`

Проблемные паттерны:

- `head -30`
- `grep -v`
- `wc -l`
- pipe chains без Windows/Powershell варианта
- голый `python -c`
- голый `python scripts/...`

Почему критично:

- Проект явно требует Windows/Powershell совместимость и `.venv`-first Python.
- Evidence commands должны быть воспроизводимыми.
- Сейчас copy-paste команды могут падать на машине пользователя или использовать не тот Python.

Исправление:

- Для каждой команды дать Powershell-first вариант.
- Если сохраняется bash-вариант, явно помечать его как Git Bash only.
- Для Python-команд в проекте использовать:

```powershell
.\.venv\Scripts\python.exe <script>
.\.venv\Scripts\python.exe -c "<code>"
.\.venv\Scripts\python.exe -m pytest <tests>
```

Примеры замен:

```text
head -30 doc/epochs/e4.md
```

заменить на:

```powershell
Get-Content -Path doc/epochs/e4.md -TotalCount 30
```

```text
wc -l <file>
```

заменить на:

```powershell
(Get-Content -Path <file>).Count
```

```text
rg "prompt = |PROMPT = |prompt\s*=" app/ --type py | grep -v prompts.py
```

заменить на:

```powershell
rg "prompt = |PROMPT = |prompt\s*=" app/ --type py | Select-String -NotMatch "prompts.py"
```

или еще лучше сделать отдельный Python checker, чтобы не зависеть от shell semantics.

### WF-HARDEN-005 — `scripts/arch_regression_guards.sh` нарушает `.venv`-first policy

Severity: critical, если этот guard предлагается как regression protection.

Файл:

- `scripts/arch_regression_guards.sh`

Проблема:

- Script выбирает `python` раньше `.venv/Scripts/python.exe`.
- AGENTS требует сначала `.\.venv\Scripts\python.exe`, fallback на `python` / `py` только если
  `.venv` недоступен.

Исправление:

- Переставить detection order:

```bash
if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON_CMD=(".venv/Scripts/python.exe")
elif [ -x ".venv/bin/python" ]; then
  PYTHON_CMD=(".venv/bin/python")
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=(python)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
else
  PYTHON_CMD=()
fi
```

Дополнительно:

- Рассмотреть перенос guard в `scripts/arch_regression_guards.py`, чтобы он был Windows-native.
- Если оставить `.sh`, не ссылаться на него как единственный pre-merge guard для Windows.

### WF-HARDEN-006 — Baseline/report lifecycle не до конца согласован

Severity: warning.

Файлы:

- `doc/agent_workflow_arch_review.md`
- `doc/arch_review_baseline.yaml`
- `doc/architecture_review_2026-04-21.md`
- `archive/architecture_review.md`

Текущее состояние:

- `doc/arch_review_baseline.yaml` существует.
- `last_review.report_file` указывает на `doc/architecture_review_2026-04-21.md`.
- В `doc/` также есть актуальный report.
- В `archive/` есть legacy `architecture_review.md`.
- Arch-review prompt все еще говорит сверяться с `archive/architecture_review.md` для resolved findings.

Почему риск:

- Следующая review-сессия может смешать baseline YAML и legacy markdown.
- Есть риск повторно репортить resolved findings из legacy report.

Исправление:

- В `doc/agent_workflow_arch_review.md` явно установить precedence:
  1. `doc/arch_review_baseline.yaml` — source of truth для findings history.
  2. `last_review.report_file` — reference report.
  3. `archive/architecture_review*.md` — historical only, не источник статуса.
- Уточнить, что legacy `archive/architecture_review.md` нельзя использовать для reclassification,
  только для background context при необходимости.

### WF-HARDEN-007 — `app/tutor_prompts.py` описан как источник prompt definitions

Severity: warning.

Файл:

- `doc/agent_workflow_arch_review.md`

Проблема:

- В таблице read-set `app/tutor_prompts.py` описан как `Tutor prompt definitions`.
- Фактически файл является bridge/re-export из `app/prompts.py`; source of truth остается
  `app/prompts.py`.

Исправление:

- Заменить описание на:

```text
`app/tutor_prompts.py` — compatibility bridge/re-export from `app/prompts.py`;
verify it does not become a second prompt source.
```

### WF-HARDEN-008 — Current lint не ловит drift в workflow prompts

Severity: critical как regression prevention gap.

Файлы:

- `scripts/lint_agent_prompts.py` или новый `scripts/check_workflow_docs.py`
- тесты для нового checker, если в проекте есть pattern для scripts tests

Проблема:

- `scripts/lint_agent_prompts.py` проходит, хотя в docs есть `Hard-limit > 30k`.
- Значит текущий lint проверяет форму, но не ключевые invariants.

Исправление:

- Добавить checker, который падает на:
  - `Hard-limit > 30k`
  - `Soft-limit 20k-30k`
  - `target <= 20k` в workflow prompt context
  - `Token budget: <= 20k` без `Target <=12k`
  - `python scripts/` в workflow docs
  - `python -m pytest` без `.venv` в workflow docs, если это не example/fallback
  - markdown-ссылки на несуществующие локальные файлы в `doc/agent_workflow*.md`
- Подключить checker к `scripts/lint_agent_prompts.py` или документировать как обязательную
  post-agent проверку рядом с ним.

## Recommended Write-set

Минимальный write-set для реализации:

- `doc/agent_workflow.md`
- `doc/agent_workflow_arch_review.md`
- `doc/agent_workflow_templates.md`
- `doc/team_workflow/orchestrator_template.md`
- `scripts/arch_regression_guards.sh`
- `scripts/lint_agent_prompts.py` или новый `scripts/check_workflow_docs.py`
- `tests/test_workflow_docs.py` или ближайший существующий tests target для scripts/doc checks

Если нужно жестко держать write-set `<=5` файлов, split:

### Slice A — Docs Contract Sync

Write-set:

- `doc/agent_workflow.md`
- `doc/agent_workflow_arch_review.md`
- `doc/agent_workflow_templates.md`
- `doc/team_workflow/orchestrator_template.md`

DoD:

- no `Hard-limit > 30k`
- no `Soft-limit 20k-30k`
- no prompt budget block that says only `<=20k` without target `<=12k`
- fixed `kilo_budget_system.md` link
- Windows/Powershell command alternatives added for arch-review evidence commands

### Slice B — Regression Guards

Write-set:

- `scripts/arch_regression_guards.sh`
- `scripts/lint_agent_prompts.py` or new `scripts/check_workflow_docs.py`
- `tests/test_workflow_docs.py` or existing suitable test file

DoD:

- `.venv/Scripts/python.exe` checked before `python`
- lint catches old budget strings
- lint catches broken local markdown links in workflow docs
- lint passes after docs are fixed

## Suggested Read-set For Next Session

Keep the read-set small. Do not read all workflow files fully in one call.

Start with:

- `doc/agent_workflow_rules.md` — lines 18-30 only
- `doc/team_workflow/orchestrator_template.md` — lines 314-323 only
- `doc/agent_workflow_arch_review.md` — lines 119-214 and 383-445 only
- `doc/agent_workflow.md` — lines 34-42 only
- `scripts/arch_regression_guards.sh` — lines 1-80 only

Useful commands:

```powershell
rg -n "20k|30k|12k|Hard-limit|Soft-limit|Token budget|python scripts/|python -m pytest|grep -v|wc -l|head -30" doc/agent_workflow*.md doc/team_workflow/orchestrator_template.md
```

```powershell
rg -n "kilo_budget_system|architecture_review|arch_review_baseline|tutor_prompts.py|scripts/arch_regression_guards.sh" doc/agent_workflow*.md
```

## Execution Prompt For Next Session

```text
Goal: implement workflow hardening from doc/workflow_hardening_plan_2026-04-24.md.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- Owner/write-set files are not automatically read-set.

Read ONLY:
- doc/workflow_hardening_plan_2026-04-24.md
- doc/agent_workflow_rules.md lines 18-30
- doc/team_workflow/orchestrator_template.md lines 314-323
- doc/agent_workflow_arch_review.md lines 119-214 and 383-445
- doc/agent_workflow.md lines 34-42
- scripts/arch_regression_guards.sh lines 1-80

Write-set:
- doc/agent_workflow.md
- doc/agent_workflow_arch_review.md
- doc/agent_workflow_templates.md
- doc/team_workflow/orchestrator_template.md
- scripts/arch_regression_guards.sh
- scripts/lint_agent_prompts.py OR scripts/check_workflow_docs.py
- tests/test_workflow_docs.py OR closest existing test file for scripts/doc lint

Tasks:
1. Sync all workflow/team prompt budget language to target <=12k, soft 12k-20k, hard >20k.
2. Fix the broken `kilo_budget_system.md` link in doc/agent_workflow.md.
3. Replace or annotate Unix-only evidence commands in arch-review docs with Powershell-first equivalents.
4. Clarify arch-review baseline/report precedence:
   doc/arch_review_baseline.yaml is source of truth; legacy archive reports are historical only.
5. Update `app/tutor_prompts.py` description: compatibility bridge/re-export, not second prompt source.
6. Fix `.venv`-first Python detection in scripts/arch_regression_guards.sh.
7. Add or extend a lint/check script so old budget strings and broken workflow doc links fail automatically.

DoD:
- `rg -n "Hard-limit > 30k|Soft-limit 20k|20k-30k|target <= 20k|target ≤ 20k" doc/agent_workflow*.md doc/team_workflow/orchestrator_template.md` returns no stale budget matches.
- `rg -n "Token budget: <= 20k|Token budget: ≤ 20k" doc/agent_workflow*.md doc/team_workflow/orchestrator_template.md` returns no weak budget header without target <=12k.
- `rg -n "../kilo_budget_system.md" doc/agent_workflow.md` returns no matches.
- `.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py` passes.
- New/extended workflow-doc lint passes.
- Targeted tests for the new lint/check pass.
- No unrelated docs or code changed.

Output:
- changed files
- exact checks run
- any remaining risk
```

## Verification Commands

Use `.venv` first:

```powershell
.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py
```

```powershell
.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py
```

```powershell
rg -n "Hard-limit > 30k|Soft-limit 20k|20k-30k|target <= 20k|target ≤ 20k" doc/agent_workflow*.md doc/team_workflow/orchestrator_template.md
```

```powershell
rg -n "../kilo_budget_system.md" doc/agent_workflow.md
```

If a new checker is added:

```powershell
.\.venv\Scripts\python.exe scripts/check_workflow_docs.py
.\.venv\Scripts\python.exe -m pytest tests/test_workflow_docs.py -v
```

## Non-goals

- Do not rewrite the whole workflow system.
- Do not change backlog process semantics unless needed to remove a contradiction.
- Do not run full test suite.
- Do not read `doc/adr.md`, `doc/changelog.md`, `tests/test_api.py`, `app/query_service.py`,
  `app/prompts.py`, or `app/knowledge_graph.py` fully.
- Do not treat `app/tutor_prompts.py` as a second prompt source.

## Residual Risks

- Some workflow docs outside the inspected set may also contain old budget language.
  Use `rg` across `doc/team_workflow/*.md` and `archive/agent_prompts/*.md`, but update only active
  prompts unless the user explicitly asks to clean archives.
- `scripts/arch_regression_guards.sh` is bash-oriented. For Windows-first reliability,
  a Python checker is stronger than trying to make shell pipelines portable.
- Existing `lint_agent_prompts.py` may have a different responsibility boundary. If extending it
  makes it too broad, create a dedicated `scripts/check_workflow_docs.py` and call it from the
  documented post-agent checks.

