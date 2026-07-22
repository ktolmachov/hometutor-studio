# hometutor Project Rules for Claude

**Last updated:** 2026-06-21  
**Status:** Active — apply to all Claude Code sessions in this project

---

## 📋 Project Brief

**hometutor** is a Python RAG (Retrieval-Augmented Generation) application for adaptive tutoring with graph-based knowledge retrieval, learner state persistence, and LLM-based answer generation.

**Tech stack:** FastAPI, Streamlit, SQLite, Chroma, LangChain, Anthropic API.

**Key source-of-truth docs:**
- **🧭 [`doc/index.md`](doc/index.md) — START HERE** — unified navigation hub by role and scenario (new, 2026-04-25)
- `doc/backlog_registry.yaml` — current backlog, package status, ownership (SSoT)
- `doc/tasklist.md` — generated weekly view; do not edit manually for status/scope
- `doc/agent_workflow.md` — how to safely use agents/Claude on this project
- `doc/conventions.md` — engineering rules (error handling, config access, imports, etc.)
- `doc/token_safety.md` — **critical reference for file inclusion rules** (new, 2026-04-19)

---

## 🏗️ Two-Root Repository Layout

This project is physically split across **two independent git working trees**.
Every path in this document and in prompts must be resolved against the correct root.

| Root | What lives here | How to derive |
|---|---|---|
| **CODE_ROOT** | `app/`, `app/routers/`, `app/ui/`, `requirements.txt` — all Python source | `pip show hometutor` → "Editable project location" (currently `D:\Projects\hometutor`) |
| **DOCS_ROOT** (this repo) | `doc/`, `tests/`, `scripts/`, baseline yaml, `CLAUDE.md` | current working directory (`D:\Projects\hometutor-studio`) |

**Key rules:**
- `app/` **does not exist** in this working directory. It is importable only via the editable install.
- File operations (`rg`, `Read`, `Get-Content`) on `app/**` must target `CODE_ROOT`, not cwd.
- Git operations per root: `git -C $CODE_ROOT diff ...` for code, `git diff ...` (cwd) for docs/tests.
- The two repos have **independent histories**. Baseline yaml stores `code_sha` + `docs_sha` (not a single sha).
- Derive CODE_ROOT at runtime, do not hardcode:
  ```powershell
  $CODE_ROOT = (pip show hometutor | Select-String 'Editable project location:').ToString().Split(':',2)[1].Trim()
  ```

---

## 🎯 Context Policy for Claude Code

**Keep every LLM call under 12k estimated input tokens when possible.**

### 1. Read-Set Rules (Mandatory)

- **Max 3–5 files per LLM call.** For routine tasks, prefer 2–3.
- **Never read extra files beyond explicit read-set.** No fishing or "context exploration."
- **Only include relevant sections or samples**, not entire files, unless explicitly safe per token_safety.md.
- **Fresh context always:** Ignore prior responses/tools in each new Claude Code call.
- **Long session:** if estimated input **>20k tokens** or **msgs≫15** in a tool-heavy chat, stop and start a **new chat** (relay does not trim history).

### 2. Large-File Rules (Non-Negotiable)

#### Python Modules (>600 lines)

Never include full contents. Instead:

- **Signatures only:** `grep "^class\|^def " <file>`
- **Imports + exports only:** first 50 lines + public methods/constants
- **1–2 selected methods/classes** relevant to the task

#### Test Files (>800 lines)

Never include full file. Instead:

- **Single test case** (copy-paste the entire `def test_<name>(...):` block)
- **Test patterns:** `grep "def test_"` to list + read 1–2 examples
- **Fixtures only:** copy just the `@pytest.fixture` blocks you need

#### Documentation (>400 lines)

Never include full file. Instead:

- **Relevant section only** (e.g., `## Module: QueryService`)
- **Status table or header** (first 30 lines)
- **Last N entries** (for changelog, only append-target + last 2–3 rows)
- **Summary:** short hand-written outline instead of full text

### 3. Forbidden Full-Read Files

**These files MUST NEVER be read in full without explicit justification.** Use safe methods from token_safety.md instead.
Verify current size before reading: `(Get-Content <file>).Count` (PowerShell) or `wc -l` (Bash).
app/* files are under **CODE_ROOT** (see § Two-Root Repository Layout), not in this cwd.

```
❌ AGENTS.md                   → use: rg "^## " section only; never Read-tool (in <rules>)
❌ CLAUDE.md                   → use: rg "^## " section only; never Read-tool (duplicate policy)
❌ doc/backlog_registry.yaml   → use: rg one PACKAGE_ID block only
❌ doc/closed_iterations.md    → use: one closed-package section via rg
❌ doc/conventions_architecture.md → use: one ## section via rg
❌ doc/conventions_reference.md    → use: one ## section via rg
❌ app/query_service.py        → use: grep signatures           (CODE_ROOT)
❌ app/knowledge_graph.py      → use: grep signatures           (CODE_ROOT)
❌ app/prompts/_impl.py        → use: grep signatures           (CODE_ROOT, SSoT промптов)
✅ app/tutor_prompts.py        → safe to read fully (bridge)    (CODE_ROOT)
❌ tests/test_api.py           → use: 1 test case               (DOCS_ROOT)
❌ tests/test_query_service.py → use: 1 test case               (DOCS_ROOT)
❌ doc/changelog.md            → use: last 2–3 rows             (DOCS_ROOT)
❌ doc/adr.md                  → use: status table only          (DOCS_ROOT)
❌ doc/architecture.md         → use: module list only           (DOCS_ROOT)
❌ doc/cjm.md                  → use: specific pain point        (DOCS_ROOT)
❌ doc/epochs/*                → use: grep headers or 1 file max (DOCS_ROOT)
```

For any other file >600 lines, check token_safety.md before reading.

### 4. Epoch Files — How to Choose

`doc/epochs/` содержит 25+ файлов (e4–e29 + тематические). Никогда не читайте папку целиком.

**Как выбрать нужный epoch-файл:**

```bash
# Список epoch-файлов с их первой строкой (title/статус)
grep -l "^# " doc/epochs/*.md | sort

# Для arch review — последние 2–3 эпохи по номеру:
ls doc/epochs/e*.md | sort -V | tail -3

# Заголовки и статус последних эпох (не тело):
for f in $(ls doc/epochs/e*.md | sort -V | tail -3); do
  echo "=== $f ==="; head -10 "$f"; echo
done
```

**Правила:**

| Задача | Что читать |
|---|---|
| Arch review (последние решения) | max 1–2 epoch файла; только header + tables |
| Planning следующего пакета | только **один** целевой epoch-файл (e.g., `e29.md`) |
| Поиск паттерна из прошлых эпох | `grep -l "keyword" doc/epochs/*.md` → читать только найденный |
| Понять текущий статус | `doc/backlog_registry.yaml` — не epoch-файлы |

**Никогда:** не добавлять несколько epoch-файлов в один read-set.

### 5. Compression Rule

- **If estimated input exceeds 12k tokens:** compress history/read-set before sending
- **If estimated input exceeds 20k tokens:** **stop**, report blocker, don't send
- **Compression techniques** (see doc/token_safety.md § Правила Сжатия):
  - trim old history (keep last 2–3 steps)
  - replace full-file with summary (1–2 sentences)
  - use grep instead of full-read
  - drop lowest-signal files

### 5. Retry Policy

- **Forbidden:** re-send same payload after error
- **Required:** compress context first (remove files, trim history, use summaries)
- **Max 1 safe retry** after compression; beyond that, stop and report

---

## 📐 Safe Read-Set Examples

### Planning a Package (~8–10k tokens)

```
# app/* under CODE_ROOT, doc/* and tests/* under DOCS_ROOT (cwd)
Read ONLY:
1. app/target_module.py — grep "^class\|^def " (signatures)
2. tests/test_target.py — grep "def test_" (list) + read 1 example
3. doc/backlog_registry.yaml — ONLY entry for target package (not entire file)

SKIP:
- Full file bodies
- doc/epochs/, doc/cjm.md, doc/changelog.md
- Any file >400 lines not listed above
```

### Architecture Review Phase (~6–8k tokens per phase)

```
Read ONLY (Phase 1 — Conventions Audit):
- doc/conventions.md (full, 710 tokens)
- doc/conventions_architecture.md (full, 3k tokens)
- doc/conventions_reference.md (full, 1.9k tokens)

DO NOT yet read:
- Code modules (use grep instead)
- doc/adr.md, doc/architecture.md (for Phase 3)
- Test files (for Phase 2)
```

### Verify a Package (~10k tokens)

```
# git diff per-root: git -C $CODE_ROOT for app/, git diff (cwd) for doc/tests/
Read ONLY:
- CONTRACT_FILE (execution contract, ~1.5k)
- git diff HEAD~N..HEAD (scope check, ~2k)
- tests/test_target.py — grep "def test_" + read 1–2 relevant cases (~1k)

SKIP:
- Full changelog, full tasklist, full test files
- Full code review (only spot-check diffs)
```

---

## 🚨 Critical Checkpoints

**Before submitting any LLM call in Claude Code:**

- [ ] All files >600 lines use safe method (signatures/grep/section)
- [ ] No full read of files in Forbidden list above
- [ ] No entire directory read (doc/epochs/, doc/user_stories/, etc.)
- [ ] Estimated input ≤ 12k tokens (or ≤ 20k with compression)
- [ ] Not retrying same payload without compression
- [ ] Fresh context statement if continuing from prior call

If any checkbox fails, compress or skip the call.

**Quick token budget check:**

```bash
python scripts/check_readset.py <file1> <file2> ...
# SAFE  = within 12k, all files OK
# WARN  = over 12k, compress before sending
# BLOCK = forbidden file or over 20k, must fix before sending

python scripts/check_readset.py --signatures app/query_service.py
# Shows grep command to use instead of full-read
```

---

## 🔧 Working Conventions

### Code Changes

1. **Write-set first:** Always ask/confirm which files can be changed
2. **Scope tight:** No unrelated refactors or cleanups in the same call
3. **Test mandatory:** Run DoD tests before claiming done
4. **Doc sync required:** If contract/UI/roadmap changes, update docs

See `doc/agent_workflow_templates.md` § Verify Prompt for full DoD checklist.

### Document Sync

When code changes, update these **if** affected:

- `doc/backlog_registry.yaml` — update package status (SSoT); `doc/tasklist.md` is
  **DERIVED** — generated by lint, never edit manually for status changes.
  Run `python scripts/backlog_registry_lint.py --sync-from-index --write-sync` to regenerate.
- `doc/changelog.md` — append new entry (don't rewrite full file)
- `doc/api_reference.md` — if HTTP contract changed
- `doc/conventions.md` — if engineering rules changed
- `doc/user_guide.md` / `user_guide_details.md` — if UI behavior changed

### SSoT Status

Источник Truth View и контрактов активных пакетов — **`doc/backlog_registry.yaml`**
(через `prompt_utils.parse_truth_view_from_registry` / загрузку контракта из реестра).
Скрипты оркестрации и next-task **не** подгружают `doc/tasklist.md`, если в YAML нет данных —
нужно поправить реестр и при необходимости пересобрать weekly view через
`python scripts/backlog_registry_lint.py --sync-from-index --write-sync`.

`doc/tasklist.md` остаётся **производным** файлом (строка «Now», очередь волн, синхронизированные
блоки контрактов). Парсер `prompt_utils.parse_truth_view(text)` — для тестов и фикстур по строке
markdown, не операционный fallback для маршрутизации.

### Test Selection

Use test bundles from `doc/agent_workflow_test_bundles.md` § Стандартные Test Bundles.

**Never** run tests without a clear reason. Prefer targeted test files:

```bash
# Tutor core changes
pytest tests/test_tutor_orchestrator.py tests/test_pipeline_steps.py

# Query service / API changes
pytest tests/test_query_service.py tests/test_api.py

# Learner state changes
pytest tests/test_user_state.py tests/test_learner_model_service.py
```

---

## ✅ Positive Patterns to Preserve

These patterns are working well; replicate them in future work:

1. **Modular service layer** (`app/*_service.py`) — keeps business logic separate from API/UI
2. **Typed contracts** (QueryContext, QueryResponse, etc. in `app/models.py`) — prevents payload mismatches
3. **Guardrails pattern** (app/guardrails.py) — centralized input validation
4. **Fixtures in conftest.py** — DRY test setup, easy to extend
5. **Config through env** (app/config.py with pydantic Settings) — no hardcoding, flexible deployment

---

## 🚫 Prohibited Actions

These actions require **explicit user confirmation in chat** before proceeding:

- Permanent deletes (files, database records, git branches)
- Force-push to main/master
- Modifying CI/CD pipelines
- Changing security permissions (file access, API keys, environment variables)
- Creating new accounts or external API integrations
- Large refactors without owner sign-off

See `doc/agent_workflow_cycle.md` § Правила Для A/B/C Split for multi-agent coordination rules.

---

## 📚 How to Use This Document

**For Claude in Claude Code (you):**

- Check this document at the start of each session
- Before any large LLM call, validate against § Critical Checkpoints
- Refer to `doc/token_safety.md` for file-by-file safe methods
- Refer to `doc/agent_workflow_templates.md` for templates and DoD checklists

**For human users:**

- If Claude violates a rule above, link this doc and the specific rule
- If a rule needs updating, edit this file and commit (it's project policy)
- For token issues, first check `doc/token_safety.md` before asking Claude

---

## 📞 When to Stop and Ask for Clarification

Stop work and ask the user if:

- Scope is ambiguous (change vs. refactor vs. feature?)
- Write-set conflicts with another active branch/agent
- Required test bundle is unclear
- Token budget would exceed 20k even after compression
- Discovered a blocker file not listed in backlog_registry/current task (new service, new test, new doc needed)
- Multiple contradictory rules in conventions (should not happen, but report if it does)

**Default:** narrow scope beats broad scope. If unsure, ask.

---

## 🤝 Командный конвейер (Team Workflow)

Четыре входа в процесс — выбирать по ситуации:

| Ситуация | Что запускать |
|---|---|
| Backlog пустой / все пакеты закрыты / нужен новый контракт | `doc/team_workflow/generate_plan_next_prompt.md` |
| В `backlog_registry.yaml` есть `ready`/`wip` пакет | `doc/team_workflow/generate_orchestration_prompt.md` |
| Работа по `PACKAGE_ID` уже начиналась (`archive/team_artifacts/<ID>/`) | `doc/team_workflow/generate_resume_prompt.md` |
| Периодический аудит закрытых пакетов / проверка SSoT консистентности | `doc/team_workflow/generate_audit_closed_packages_prompt.md` |

Planning и orchestration — раздельно. `plan_next` предлагает 1–3 кандидата с ranking, запускает preflight `check_readset.py`, пишет контракт в `backlog_registry.yaml`, регенерирует `tasklist.md` и останавливается. Orchestration запускается только после review принятого контракта.

Умный роутер следующего шага: `python scripts/workflow.py` — см. [`doc/team_workflow/workflow_router.md`](doc/team_workflow/workflow_router.md). Тексты промпта для агента в консоли (блок «Промпт для агента») — единый источник в [`scripts/workflow_strings.py`](scripts/workflow_strings.py).

Промпты ролей и пример использования: [`doc/team_workflow/README.md`](doc/team_workflow/README.md).

---

## 🔗 Related Documents

- [`doc/token_safety.md`](doc/token_safety.md) — complete reference for file inclusion safety
- [`doc/agent_workflow.md`](doc/agent_workflow.md) — slim index (navigation hub для split-карты)
- [`doc/agent_workflow_rules.md`](doc/agent_workflow_rules.md) — Token Budget & Retry Safety v1
- [`doc/team_workflow/README.md`](doc/team_workflow/README.md) — team AI pipeline (PO → Analyst → Architect → Dev → Tester)
- [`doc/team_workflow/workflow_router.md`](doc/team_workflow/workflow_router.md) — умный роутер (`workflow.py`), `--loop`, якоря документации
- [`scripts/workflow_strings.py`](scripts/workflow_strings.py) — SSoT строк промпта агента для вывода роутера
- [`doc/conventions.md`](doc/conventions.md) — engineering rules and patterns
- [`doc/backlog_registry.yaml`](doc/backlog_registry.yaml) — current backlog and ownership
- [`doc/tasklist.md`](doc/tasklist.md) — generated weekly view

---

**Version:** 1.1 (2026-06-21) — added two-root layout, dynamic line-counts, app/tutor_prompts.py  
**Next Review:** after E15 completion or upon significant project changes
