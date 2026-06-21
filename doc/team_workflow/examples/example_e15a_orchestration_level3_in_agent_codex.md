# E15-A: Оркестрация в OpenAI Codex CLI

Актуализировано: **2026-04-12**
Шаблон: [orchestrator_template.md](orchestrator_template.md)

## Специфика Codex CLI

| Возможность | Реализация |
|-------------|-----------|
| Параллельные агенты | ✗ Нет нативного параллелизма — **sequential по умолчанию** |
| Изоляция ролей | Смена контекста через `/agent` thread или явное `/role` в промпте |
| Вложенность | Глубина 1 через Agents SDK; в CLI — один активный thread |
| Файлы | Shell MCP: `cat`, `echo`, стандартный bash |
| Shell | Shell Tool MCP (sandboxed bash) |
| Передача артефактов | Через файловую систему: записать → прочитать |
| Ссылки на файлы | Явные `cat path/to/file` в промпте |
| Конфигурация | `AGENTS.md` в корне проекта |

**Ключевое ограничение:** Codex CLI не поддерживает параллельный запуск агентов
в одном вызове. Step 3 (Architect + Designer) выполняется **последовательно**.
Это trade-off: Designer может использовать Architect contract до начала своей работы.

---

## AGENTS.md (настройки агента)

Создать/обновить `AGENTS.md` в корне проекта перед запуском:

```markdown
# home-rag_v2 Agent Instructions

## Project context
- Python FastAPI + Streamlit learning assistant
- Conventions: doc/conventions.md (ALWAYS read before editing any code)
- Active backlog: doc/backlog_registry.yaml (SSoT); doc/tasklist.md is generated view
- Role prompts: doc/team_workflow/<role>.md
- WIP = 1: one package at a time

## Rules
- Never edit files outside the stated write-set
- Always run pytest after code changes, report exact output
- No bare except blocks (see doc/conventions.md)
- Config only via get_settings() / get_retrieval_settings()
- LLM access only via app/provider.py
- Prompts only in app/prompts.py
- Save artifacts via: cat > path/file.md (preserves multiline)

## Standard test commands
- Flashcard tests: python -m pytest tests/test_flashcard_service.py -v
- API tests:       python -m pytest tests/test_api.py -v
- Full suite:      python -m pytest tests/ --tb=short
```

---

## Как запустить

```bash
# В терминале, из корня проекта:
codex

# Затем вставить промпт оркестратора (блок ниже)
```

---

## Промпт оркестратора для Codex CLI

```text
╔══════════════════════════════════════════════════════════════════╗
║  TEAM PIPELINE ORCHESTRATOR — E15-A  [Codex CLI]               ║
╚══════════════════════════════════════════════════════════════════╝

You are a team pipeline orchestrator for home-rag_v2.
Execute the 6-role team pipeline for E15-A sequentially.
You have Shell Tool MCP (bash) available.

ENVIRONMENT:
  Shell: bash
  Artifacts: archive/team_artifacts/E15-A/
  Execution model: SEQUENTIAL (Codex CLI — no native parallel agents)

PACKAGE CONTEXT:
  ID:      E15-A
  Feature: Flashcards deck progress bar + tag filter in review session
  CJM:     Retain
  US:      US-15.3, US-15.4
  Outcomes:
    1. Deck detail view: progress bar shows % mastered cards
    2. Review session: tag filter to focus on weak areas

─────────────────────────────────────────────────────────────────
SETUP
─────────────────────────────────────────────────────────────────

mkdir -p archive/team_artifacts/E15-A
echo "[E15-A] Pipeline started: $(date)"

─────────────────────────────────────────────────────────────────
STEP 1/8 — Product Owner
─────────────────────────────────────────────────────────────────

Read your role instructions:
  cat doc/team_workflow/product_owner.md

Read context files:
  Select-String -Path doc\backlog_registry.yaml -Pattern "E15-A|status:|dod_commands|user_stories" -Context 0,8
  cat doc/cjm.md
  cat doc/user_stories/US-15.3.md
  cat doc/user_stories/US-15.4.md
  cat doc/closed_iterations.md | tail -80
  cat doc/vision.md

Act as Product Owner. Execute Prompt 1 from product_owner.md.
Package ID: E15-A. Max 2 outcomes (pre-scoped: progress bar + tag filter).
Output ONLY the structured artifact.

Save:
  cat > archive/team_artifacts/E15-A/1_po_package.md

Checkpoint (verify before continuing):
  ✓ CJM stage = Retain
  ✓ Both US-15.3 and US-15.4 referenced
  ✗ "ESCALATION" keyword → STOP, report to user

echo "[E15-A] Step 1/8 — PO: COMPLETE"

─────────────────────────────────────────────────────────────────
STEP 2/8 — Analyst
─────────────────────────────────────────────────────────────────

Read your role instructions:
  cat doc/team_workflow/analyst.md

Read context files:
  cat archive/team_artifacts/E15-A/1_po_package.md
  cat doc/user_stories/US-15.3.md
  cat doc/user_stories/US-15.4.md
  cat doc/cjm.md
  cat app/routers/flashcards.py
  cat app/flashcard_service.py
  grep -n "flashcard\|ease_factor\|next_review\|tags" app/user_state.py | head -80
  cat app/ui/flashcards_ui.py

Act as Analyst. Execute Prompt 1 from analyst.md.
For Outcome 2 (tag filter): check exactly how tags are stored in DB
  (grep output above shows field type and format).
Flag "Open Questions → Architect" for Step 3.
Output ONLY the structured specification.

Save:
  cat > archive/team_artifacts/E15-A/2_analyst_spec.md

Checkpoint:
  ✓ Given/When/Then for all 6 scenarios (3 per outcome)
  ✗ "Open Questions → PO" → STOP, report to user
  ✓ "Open Questions → Architect" → note it, pass to Step 3

echo "[E15-A] Step 2/8 — Analyst: COMPLETE"

─────────────────────────────────────────────────────────────────
STEP 3a/8 — Architect  [runs BEFORE Designer — sequential trade-off]
─────────────────────────────────────────────────────────────────

Read your role instructions:
  cat doc/team_workflow/architect.md

Read context files:
  cat archive/team_artifacts/E15-A/2_analyst_spec.md
  cat doc/conventions.md
  cat doc/conventions_architecture.md
  cat doc/conventions_reference.md
  cat doc/adr.md
  cat app/user_state.py
  cat app/flashcard_service.py
  cat app/routers/flashcards.py
  cat app/api_models.py
  cat app/api_helpers.py
  grep -n "ease_factor\|DEFAULT_MASTERY" app/spaced_repetition.py
  cat tests/test_flashcard_service.py | head -100

Act as Architect. Execute Prompt 1 from architect.md.

Address the Open Question from Analyst re: tags storage:
  Recommendation: SQL LIKE query on comma-separated string is sufficient.
  Justification: deck size < 1000 cards; separate tags table adds migration
  complexity without measurable query performance benefit at this scale.
  No new ADR needed — document inline in contract.

Split into two sub-packages:
  E15-A-1: backend only (user_state, flashcard_service, routers, api_models, tests)
  E15-A-2: UI + tag filter endpoint param (flashcards_ui, user_state tag param,
            flashcard_service tag param, routers tag param, tests)

Include copy-paste developer prompts for BOTH sub-packages.
Output ONLY the structured contract.

Save:
  cat > archive/team_artifacts/E15-A/3_architect_contract.md

Checkpoint:
  ✓ Write-set E15-A-1 ∩ write-set E15-A-2 = ∅ (no file appears in both)
  ✗ Overlap detected → STOP, report to user

echo "[E15-A] Step 3a/8 — Architect: COMPLETE"

─────────────────────────────────────────────────────────────────
STEP 3b/8 — Designer  [runs AFTER Architect — can reference write-set]
─────────────────────────────────────────────────────────────────

Read your role instructions:
  cat doc/team_workflow/designer.md

Read context files:
  cat archive/team_artifacts/E15-A/2_analyst_spec.md
  cat archive/team_artifacts/E15-A/3_architect_contract.md
  cat doc/cjm.md
  cat app/ui/flashcards_ui.py
  cat app/ui/home_hub.py
  grep -n "st.progress\|percent" app/ui/dashboards.py
  grep -n "^.*fc_.*=\|session_state\[.fc_" app/ui/main.py
  grep -n "session_state\[.fc_" app/ui/flashcards_ui.py
  cat app/ui_theme.css | grep -A3 "progress\|card\|badge"

Act as Designer. Execute Prompt 1 from designer.md.
Cover ONLY deck detail view modifications (not home screen — badge unchanged).
For each new component: define all 4 states (loading/empty/error/populated).
Check grep output for existing fc_* session_state keys — no new collisions.
Output ONLY the structured UI spec.

Save:
  cat > archive/team_artifacts/E15-A/4_designer_ui_spec.md

echo "[E15-A] Step 3b/8 — Designer: COMPLETE"

─────────────────────────────────────────────────────────────────
STEP 4/8 — Developer: E15-A-1 (backend)
─────────────────────────────────────────────────────────────────

Read your role instructions:
  cat doc/team_workflow/developer.md

Read context files:
  cat archive/team_artifacts/E15-A/3_architect_contract.md
  cat archive/team_artifacts/E15-A/4_designer_ui_spec.md

Act as Developer. Use the copy-paste prompt for E15-A-1 from the contract.

Additional constraint from Designer:
  Response "percent" field must be 0.0–100.0 float (NOT 0.0–1.0).
  UI will use: st.progress(response["percent"] / 100)

Write-set (ONLY these 5 files):
  app/user_state.py
  app/flashcard_service.py
  app/routers/flashcards.py
  app/api_models.py
  tests/test_flashcard_service.py

Implementation cycle (follow this order):
  1. Read current state of each write-set file
  2. Plan changes (list them before editing)
  3. Edit files
  4. Run tests — report exact output:
       python -m pytest tests/test_flashcard_service.py -v 2>&1
       python -m pytest tests/test_api.py -k flashcard -v 2>&1

Save output summary:
  cat > archive/team_artifacts/E15-A/5a_developer_e15a1.md

echo "[E15-A] Step 4/8 — Developer E15-A-1: COMPLETE"

─────────────────────────────────────────────────────────────────
STEP 5/8 — Tester: E15-A-1
─────────────────────────────────────────────────────────────────

Read your role instructions:
  cat doc/team_workflow/tester.md

Read context files:
  cat archive/team_artifacts/E15-A/3_architect_contract.md
  cat archive/team_artifacts/E15-A/5a_developer_e15a1.md

Act as Tester. Execute Prompt 1 from tester.md.
PACKAGE_ID=E15-A-1, PACKAGE_TYPE=code.

Run ALL of these commands — MANDATORY, do not skip:
  git diff --name-only HEAD~5..HEAD
  python -m pytest tests/test_flashcard_service.py -v 2>&1
  python -m pytest tests/test_api.py -k flashcard -v 2>&1
  grep -n "except Exception" app/flashcard_service.py app/user_state.py
  grep -n "get_settings\|from app.config" app/flashcard_service.py
  grep -n "def get_deck_progress" app/flashcard_service.py

Execute Steps 1–5 from Tester Prompt 1.
End output with exactly one of:
  ### VERDICT: PASS
  ### VERDICT: CONDITIONAL PASS
  ### VERDICT: FAIL

Save:
  cat > archive/team_artifacts/E15-A/6a_tester_e15a1.md

Verdict routing:
  PASS             → continue to Step 6
  CONDITIONAL PASS → print conditions to user, ask: "Proceed to E15-A-2? (y/n)"
                     if y: add conditions to deferred.md, continue
  FAIL             → print the ONE blocker line, ask: "Re-run Developer? (y/n)"
                     if y: re-run Step 4 with blocker appended to dev prompt
                     if n: STOP pipeline

echo "[E15-A] Step 5/8 — Tester E15-A-1: $(grep 'VERDICT:' 6a_tester_e15a1.md)"

─────────────────────────────────────────────────────────────────
STEP 6/8 — Developer: E15-A-2 (UI + tag filter)
─────────────────────────────────────────────────────────────────

Same structure as Step 4. Use E15-A-2 section from contract.
Include full 4_designer_ui_spec.md as UI contract.

Write-set (ONLY these 5 files):
  app/ui/flashcards_ui.py
  app/user_state.py             (get_due_flashcards tag param only)
  app/flashcard_service.py      (get_due_flashcards tag param only)
  app/routers/flashcards.py     (/due/list tag query param only)
  tests/test_flashcard_service.py

Critical constraint: do NOT change /flashcards/due/count endpoint.
  The home badge (app/ui/home_hub.py) depends on it — must not regress.

Save:
  cat > archive/team_artifacts/E15-A/5b_developer_e15a2.md

echo "[E15-A] Step 6/8 — Developer E15-A-2: COMPLETE"

─────────────────────────────────────────────────────────────────
STEP 7/8 — Tester: E15-A-2
─────────────────────────────────────────────────────────────────

Same structure as Step 5.
Additional regression commands:
  python -m pytest tests/test_flashcard_service.py -v 2>&1
  grep -n "due/count" app/ui/home_hub.py
  grep -rn "due/list" app/ui/home_hub.py app/ui/resume_cards.py

Save:
  cat > archive/team_artifacts/E15-A/6b_tester_e15a2.md

echo "[E15-A] Step 7/8 — Tester E15-A-2: $(grep 'VERDICT:' 6b_tester_e15a2.md)"

─────────────────────────────────────────────────────────────────
STEP 8/8 — Closure  [only after both PASS]
─────────────────────────────────────────────────────────────────

Update doc/backlog_registry.yaml — set E15-A status/closure fields, then regenerate doc/tasklist.md:
  .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync

Update doc/changelog.md — add entry at top of file.
Update doc/closed_iterations.md — add E15-A closure block.

List artifacts:
  echo "=== E15-A Artifacts ===" && ls -lh archive/team_artifacts/E15-A/
  echo "=== Changed files ===" && git diff --name-only HEAD~10..HEAD | sort -u

echo "[E15-A] Step 8/8 — Closure: DONE ✓"
echo "Pipeline complete: $(date)"

─────────────────────────────────────────────────────────────────
ORCHESTRATOR RULES
─────────────────────────────────────────────────────────────────

ALWAYS:
  • cat role prompt file at the start of each step.
  • cat artifact file when passing to next step.
  • Save artifacts with: cat > file.md  (not echo, not tee)
  • Run ALL mandatory commands — never assume results.

NEVER:
  • Edit files outside stated write-set.
  • Skip a checkpoint.
  • Proceed past FAIL without user decision.
  • Edit doc/backlog_registry.yaml/generated tasklist.md before Step 7 PASS.

─────────────────────────────────────────────────────────────────
BEGIN — echo "[E15-A] Step 1/8 — PO: STARTED" then execute Step 1.
```

---

## Диаграмма выполнения Codex CLI

```
codex (single sequential thread)
│
├─ Step 1  PO          read registry entry, cjm.md, US-15.3/15.4
│          └──────────> 1_po_package.md
│
├─ Step 2  Analyst     cat 1_po_package.md + app/routers/flashcards.py + ...
│          └──────────> 2_analyst_spec.md
│
├─ Step 3a Architect   cat 2_analyst_spec.md + conventions + adr
│          └──────────> 3_architect_contract.md
│          [SEQUENTIAL — no parallel]
├─ Step 3b Designer    cat 2_analyst_spec.md + 3_contract + app/ui/*.py
│          └──────────> 4_designer_ui_spec.md
│
├─ Step 4  Developer   edits app/user_state.py, flashcard_service.py ...
│          pytest      python -m pytest tests/test_flashcard_service.py
│          └──────────> 5a_developer_e15a1.md
│
├─ Step 5  Tester      git diff, pytest -v, grep checks
│          └──────────> 6a_tester_e15a1.md  [VERDICT: PASS/FAIL]
│
├─ Step 6  Developer   edits app/ui/flashcards_ui.py + tag filter
│          └──────────> 5b_developer_e15a2.md
│
├─ Step 7  Tester      regression: pytest + grep due/count in home_hub
│          └──────────> 6b_tester_e15a2.md  [VERDICT: PASS/FAIL]
│
└─ Step 8  Closure     edit backlog_registry.yaml, sync tasklist.md, changelog.md, closed_iterations.md
           DONE ✓
```

## Ключевые отличия от Claude Code

| Аспект | Claude Code | Codex CLI |
|--------|:-----------:|:---------:|
| Step 3 | Architect ∥ Designer | Architect → Designer |
| Агент | Agent tool (подагент) | тот же поток (`/role`) |
| Файлы | Read/Write tools | cat / bash redirect |
| Изоляция | отдельный контекст | общий thread |
| Преимущество | параллелизм | Designer видит контракт Architect |

---

## Приложение: параллельный Step 3 через Agents SDK

Если параллелизм критичен, обернуть через Python:

```python
# scripts/e15a_parallel_step3.py
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def run_architect(spec: str) -> str:
    instructions = open("doc/team_workflow/architect.md").read()
    r = await client.responses.create(
        model="codex-mini-latest",
        instructions=instructions,
        input=f"Execute Prompt 1. Package E15-A.\n\nANALYST SPEC:\n{spec}"
    )
    return r.output_text

async def run_designer(spec: str) -> str:
    instructions = open("doc/team_workflow/designer.md").read()
    ui = open("app/ui/flashcards_ui.py").read()
    r = await client.responses.create(
        model="codex-mini-latest",
        instructions=instructions,
        input=f"Execute Prompt 1.\n\nANALYST SPEC:\n{spec}\n\nCURRENT UI:\n{ui}"
    )
    return r.output_text

async def main():
    spec = open("archive/team_artifacts/E15-A/2_analyst_spec.md").read()
    contract, ui_spec = await asyncio.gather(
        run_architect(spec),
        run_designer(spec)
    )
    open("archive/team_artifacts/E15-A/3_architect_contract.md", "w").write(contract)
    open("archive/team_artifacts/E15-A/4_designer_ui_spec.md", "w").write(ui_spec)
    print("Step 3 parallel: COMPLETE")

asyncio.run(main())
```
