# E15-A: Оркестрация в Cursor AI

Актуализировано: **2026-04-12**
Шаблон: [orchestrator_template.md](orchestrator_template.md)

## Специфика Cursor AI

| Возможность | Реализация |
|-------------|-----------|
| Параллельные агенты | ✓ До **8** агентов (Cursor 3, Agents Window) |
| Изоляция | Каждый агент — отдельный **git worktree** |
| Модель взаимодействия | Flat peers — нет родителя/потомка, только общая FS |
| Файлы | IDE-native редактирование; `@filename` для контекста |
| Shell | Terminal в IDE; `Ctrl+`` ` |
| Передача артефактов | Через FS (worktrees видят общие файлы через merge) |
| Контекст | Семантический поиск по codebase — `@codebase`; явный `@file` |
| Composer mode | Агент, который пишет код с несколькими файлами |
| Контекстное окно | 200K токенов (фиксировано) — осторожно с большими файлами |

**Ключевая особенность:** в Cursor агенты — **независимые peers** в отдельных
worktrees. Нет явного оркестратора, который ими управляет. Роль оркестратора
выполняет **человек** через Agents Window, или один агент-координатор
в основном Composer window.

**Рекомендуемый подход для этого проекта:** один Composer window как оркестратор
(роль человека-координатора), параллельные агенты через Agents Window для Step 3.

---

## Структура Cursor workspace

```
`PROJECT_ROOT_PATH`/   ← main worktree (оркестратор работает здесь)
hometutor-studio-e15a-arch/ ← worktree для Architect (Step 3, parallel)
hometutor-studio-e15a-des/  ← worktree для Designer (Step 3, parallel)
```

Worktrees создаются автоматически командой `/worktree` в Cursor.

---

## Как запустить

1. Открыть проект в Cursor AI
2. Открыть Composer (Ctrl+I или Cmd+I)
3. Убедиться что включён **Agent mode** (не Chat mode)
4. Вставить промпт оркестратора ниже

---

## Промпт оркестратора для Cursor AI

```text
╔══════════════════════════════════════════════════════════════════╗
║  TEAM PIPELINE ORCHESTRATOR — E15-A  [Cursor AI]               ║
╚══════════════════════════════════════════════════════════════════╝

You are a team pipeline orchestrator for hometutor.
Execute the 6-role team pipeline for E15-A in Cursor AI Agent mode.

ENVIRONMENT:
  IDE: Cursor AI (Agent mode / Composer)
  Artifacts: archive/team_artifacts/E15-A/
  Parallel: Steps 3 uses Cursor Agents Window (2 parallel agents)
  Context: use @filename for file references; @codebase for semantic search

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

Run in terminal:
  mkdir -p archive/team_artifacts/E15-A

─────────────────────────────────────────────────────────────────
STEP 1/8 — Product Owner
─────────────────────────────────────────────────────────────────

Context needed (add to this Composer window):
  @doc/team_workflow/product_owner.md
  @doc/backlog_registry.yaml
  @doc/tasklist.md  # generated view only
  @doc/cjm.md
  @doc/user_stories/US-15.3.md
  @doc/user_stories/US-15.4.md
  @doc/vision.md

Act as Product Owner. Follow Prompt 1 from @doc/team_workflow/product_owner.md.
Package ID: E15-A. Max 2 outcomes (pre-scoped).
Output ONLY the structured package definition artifact.

Save output to file:
  archive/team_artifacts/E15-A/1_po_package.md

Checkpoint (YOU verify before next step):
  ✓ CJM stage = Retain?
  ✓ Both US-15.3 and US-15.4 referenced?
  ✗ "ESCALATION" → STOP, ask user

Print: [E15-A] Step 1/8 — PO: COMPLETE

─────────────────────────────────────────────────────────────────
STEP 2/8 — Analyst
─────────────────────────────────────────────────────────────────

Context needed:
  @doc/team_workflow/analyst.md
  @archive/team_artifacts/E15-A/1_po_package.md
  @doc/user_stories/US-15.3.md
  @doc/user_stories/US-15.4.md
  @app/routers/flashcards.py
  @app/flashcard_service.py
  @app/user_state.py
  @app/ui/flashcards_ui.py

Act as Analyst. Follow Prompt 1 from @doc/team_workflow/analyst.md.
For Outcome 2 (tag filter): check how tags field is stored in app/user_state.py.
Use @codebase to find any other tag-related code if needed.
Flag "Open Questions → Architect" for Step 3.
Output ONLY the structured specification.

Save: archive/team_artifacts/E15-A/2_analyst_spec.md

Checkpoint:
  ✓ Given/When/Then for all scenarios?
  ✗ "Open Questions → PO" → STOP, ask user

Print: [E15-A] Step 2/8 — Analyst: COMPLETE

─────────────────────────────────────────────────────────────────
STEP 3/8 — Architect + Designer  [PARALLEL via Agents Window]
─────────────────────────────────────────────────────────────────

## How to run parallel in Cursor:

Open Agents Window (View → Agents, or Ctrl+Shift+A).
Launch two agents simultaneously:

═══ AGENT A: Architect ═══════════════════════════════════════

Open new agent in Agents Window → name it "E15-A Architect"

Paste this prompt:
---
Role: Architect for hometutor.
Goal: execution contract for E15-A.

@doc/team_workflow/architect.md
@archive/team_artifacts/E15-A/2_analyst_spec.md
@doc/conventions.md
@doc/conventions_architecture.md
@doc/conventions_reference.md
@doc/adr.md
@app/user_state.py
@app/flashcard_service.py
@app/routers/flashcards.py
@app/api_models.py
@app/api_helpers.py
@app/spaced_repetition.py
@tests/test_flashcard_service.py

Follow Architect Prompt 1 from @doc/team_workflow/architect.md.
Address Open Question: tags as comma-separated string → use SQL LIKE query.
Justify: < 1000 cards, no separate tags table needed. No new ADR required.
Split into E15-A-1 (backend) and E15-A-2 (UI + tag filter).
Include copy-paste developer prompts for BOTH sub-packages.
Output ONLY structured contract.
Save to: archive/team_artifacts/E15-A/3_architect_contract.md
---

═══ AGENT B: Designer ════════════════════════════════════════

Open second agent in Agents Window → name it "E15-A Designer"

Paste this prompt:
---
Role: UX/UI Designer for hometutor.
Goal: UI specification for E15-A.

@doc/team_workflow/designer.md
@archive/team_artifacts/E15-A/2_analyst_spec.md
@doc/cjm.md
@app/ui/flashcards_ui.py
@app/ui/home_hub.py
@app/ui/dashboards.py
@app/ui/main.py
@app/ui_theme.css

Follow Designer Prompt 1 from @doc/team_workflow/designer.md.
Cover ONLY deck detail view modifications.
All 4 states per new component (loading/empty/error/populated).
Check @app/ui/main.py for existing fc_* session_state keys — no collisions.
Output ONLY structured UI spec.
Save to: archive/team_artifacts/E15-A/4_designer_ui_spec.md
---

Wait for BOTH agents to complete in Agents Window.

═══ Return to main Composer window ════════════════════════════

Checkpoint (YOU verify):
  @archive/team_artifacts/E15-A/3_architect_contract.md
  @archive/team_artifacts/E15-A/4_designer_ui_spec.md
  ✓ Write-set sp1 ∩ write-set sp2 = ∅?
  ✗ Overlap → STOP, resolve with user

Print: [E15-A] Step 3/8 — Architect+Designer: PARALLEL COMPLETE

─────────────────────────────────────────────────────────────────
STEP 4/8 — Developer: E15-A-1 (backend)
─────────────────────────────────────────────────────────────────

Context needed:
  @doc/team_workflow/developer.md
  @archive/team_artifacts/E15-A/3_architect_contract.md
  @archive/team_artifacts/E15-A/4_designer_ui_spec.md

Act as Developer. Use the copy-paste developer prompt for E15-A-1
extracted from @archive/team_artifacts/E15-A/3_architect_contract.md.

Additional constraint from Designer:
  Response "percent" field must be 0.0–100.0 float.
  UI will consume: st.progress(response["percent"] / 100)

Write-set (ONLY these files):
  @app/user_state.py
  @app/flashcard_service.py
  @app/routers/flashcards.py
  @app/api_models.py
  @tests/test_flashcard_service.py

Apply changes via Cursor's multi-file edit capability.
After editing, run in terminal:
  python -m pytest tests/test_flashcard_service.py -v
  python -m pytest tests/test_api.py -k flashcard -v

Save output summary: archive/team_artifacts/E15-A/5a_developer_e15a1.md

Print: [E15-A] Step 4/8 — Developer E15-A-1: COMPLETE

─────────────────────────────────────────────────────────────────
STEP 5/8 — Tester: E15-A-1
─────────────────────────────────────────────────────────────────

Context needed:
  @doc/team_workflow/tester.md
  @archive/team_artifacts/E15-A/3_architect_contract.md
  @archive/team_artifacts/E15-A/5a_developer_e15a1.md

Act as Tester. Follow Prompt 1 from @doc/team_workflow/tester.md.
PACKAGE_ID=E15-A-1, PACKAGE_TYPE=code.

Run in terminal (MANDATORY — all of these):
  git diff --name-only HEAD~5..HEAD
  python -m pytest tests/test_flashcard_service.py -v 2>&1 | tee /tmp/test_sp1.txt
  python -m pytest tests/test_api.py -k flashcard -v 2>&1
  grep -n "except Exception" app/flashcard_service.py app/user_state.py
  grep -n "def get_deck_progress" app/flashcard_service.py

Execute Tester Steps 1–5. End with:
  ### VERDICT: PASS  |  ### VERDICT: CONDITIONAL PASS  |  ### VERDICT: FAIL

Save: archive/team_artifacts/E15-A/6a_tester_e15a1.md

Verdict routing:
  PASS             → continue Step 6
  CONDITIONAL PASS → show conditions to user, wait confirmation
  FAIL             → show ONE blocker, ask user to re-run Developer

Print: [E15-A] Step 5/8 — Tester E15-A-1: <VERDICT>

─────────────────────────────────────────────────────────────────
STEP 6/8 — Developer: E15-A-2 (UI + tag filter)
─────────────────────────────────────────────────────────────────

Same structure as Step 4.
Use E15-A-2 section from @archive/team_artifacts/E15-A/3_architect_contract.md.
Include full @archive/team_artifacts/E15-A/4_designer_ui_spec.md.

Write-set:
  @app/ui/flashcards_ui.py
  @app/user_state.py              (get_due_flashcards tag param only)
  @app/flashcard_service.py       (get_due_flashcards tag param only)
  @app/routers/flashcards.py      (/due/list tag query param only)
  @tests/test_flashcard_service.py

Critical: do NOT touch app/ui/home_hub.py — badge uses /due/count, not /due/list.

Save: archive/team_artifacts/E15-A/5b_developer_e15a2.md

─────────────────────────────────────────────────────────────────
STEP 7/8 — Tester: E15-A-2
─────────────────────────────────────────────────────────────────

Same structure as Step 5.
Additional regression:
  python -m pytest tests/test_flashcard_service.py -v 2>&1
  grep -n "due/count" app/ui/home_hub.py
  grep -rn "due/list" app/ui/home_hub.py app/ui/resume_cards.py

Save: archive/team_artifacts/E15-A/6b_tester_e15a2.md

─────────────────────────────────────────────────────────────────
STEP 8/8 — Closure  [only after both PASS]
─────────────────────────────────────────────────────────────────

Edit these files directly in Cursor:
  @doc/backlog_registry.yaml ← set E15-A status/closure fields
  @doc/tasklist.md          ← regenerated by backlog_registry_lint.py
  @doc/changelog.md         ← add E15-A entry
  @doc/closed_iterations.md ← add E15-A closure block

Use multi-file edit: select all three in Composer, apply changes at once.

List results in terminal:
  ls -lh archive/team_artifacts/E15-A/
  git diff --stat HEAD~10..HEAD | head -20

Print: ✓ E15-A complete. Pipeline done.

─────────────────────────────────────────────────────────────────
ORCHESTRATOR RULES
─────────────────────────────────────────────────────────────────

ALWAYS:
  • @-reference the role prompt file at start of each step.
  • @-reference artifact files when passing to next step.
  • Run actual terminal commands — never assume test results.
  • Wait for Agents Window to show "Complete" before Step 4.
  • Keep context lean: add only files listed per step (200K limit).

NEVER:
  • Edit files outside stated write-set.
  • Skip checkpoint.
  • Run Step N+1 without Step N checkpoint passing.
  • Edit backlog_registry.yaml/generated tasklist.md before Step 7 PASS.

CURSOR-SPECIFIC:
  • Each @file reference uses semantic context — be specific.
  • If context window fills up: use /compact or start new Composer.
  • Agents Window agents don't see main Composer history.
  • For large files (user_state.py): use @file:line-range to limit tokens.

─────────────────────────────────────────────────────────────────
BEGIN — print "[E15-A] Step 1/8 — PO: STARTED" then execute Step 1.
```

---

## Диаграмма выполнения Cursor AI

```
Main Composer window (оркестратор)
│
├─ Step 1  @product_owner.md + @backlog_registry.yaml + @US-15.3 + @US-15.4
│          └─ saves → 1_po_package.md
│
├─ Step 2  @analyst.md + @1_po_package.md + @flashcard_service.py + ...
│          └─ saves → 2_analyst_spec.md
│
├─ Step 3  Agents Window [PARALLEL]
│          │
│          ├─ Agent "E15-A Architect" (own worktree)
│          │   @architect.md + @2_analyst_spec.md + @conventions.md + ...
│          │   └─ saves → 3_architect_contract.md
│          │
│          └─ Agent "E15-A Designer" (own worktree)
│              @designer.md + @2_analyst_spec.md + @flashcards_ui.py + ...
│              └─ saves → 4_designer_ui_spec.md
│          [wait for both in Agents Window]
│
├─ Step 4  @developer.md + @3_contract + @4_ui_spec
│          Cursor multi-file edit: user_state.py, flashcard_service.py, ...
│          terminal: pytest tests/test_flashcard_service.py -v
│          └─ saves → 5a_developer_e15a1.md
│
├─ Step 5  @tester.md + @3_contract + @5a_developer
│          terminal: git diff, pytest -v, grep checks
│          └─ saves → 6a_tester_e15a1.md  [VERDICT]
│
├─ Step 6  @3_contract (sp2) + @4_ui_spec
│          Cursor multi-file edit: flashcards_ui.py, tag filter files
│          └─ saves → 5b_developer_e15a2.md
│
├─ Step 7  terminal: pytest + regression grep
│          └─ saves → 6b_tester_e15a2.md  [VERDICT]
│
└─ Step 8  Multi-file edit: @backlog_registry.yaml @tasklist.md @changelog.md @closed_iterations.md
           DONE ✓
```

## Cursor-специфичные советы

**Контекст 200K:** Cursor жёстко ограничен 200K на окно. При большом проекте:
- Не добавляйте `@codebase` без нужды — это дорого по токенам
- Для больших файлов используйте `@user_state.py:280-350` (только нужные строки)
- Если контекст заполняется: `/compact` или новый Composer window

**Agents Window (Step 3):** агенты в Agents Window работают изолированно.
Они НЕ видят историю главного Composer окна. Промпт должен быть
самодостаточным — все нужные `@files` прямо в промпте агента.

**Multi-file edit (Steps 4, 6, 8):** Cursor умеет редактировать несколько файлов
в одном ответе — укажите все файлы из write-set явно, и Cursor предложит
`Apply All` для атомарного применения изменений.

**Merge worktrees:** после завершения параллельных агентов в Step 3,
их изменения (артефакты) автоматически видны в основном worktree
(они пишут в общую FS). Конфликтов нет — агенты пишут в разные файлы.

## Ключевые отличия от Claude Code

| Аспект | Claude Code | Cursor AI |
|--------|:-----------:|:---------:|
| Step 3 | Agent tool (1 message, 2 calls) | Agents Window (2 отдельных агента) |
| Изоляция агентов | separate context window | separate git worktree |
| Контекст | вставка содержимого inline | `@filename` семантик |
| Модель | opus/sonnet выбирается явно | Composer 1.5 (фиксировано) |
| Лимит контекста | 1M tokens | 200K tokens — жёстко |
| Запись файлов | Write tool | IDE native + terminal |
| Вложенность | глубина 1 (подагент → нельзя агент) | flat peers (Agents Window) |
