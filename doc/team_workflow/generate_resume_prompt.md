# generate_resume_prompt

Актуализировано: **2026-04-12**

Промпт для генерации **промпта продолжения** — когда другой агент
уже частично выполнил конвейер и нужно передать эстафету с точки остановки.

Связанный файл: `[generate_orchestration_prompt.md](generate_orchestration_prompt.md)`
(полный запуск с нуля — используйте его если работа ещё не начиналась).

---

## Как использовать

Вставить в любой AI-агент:

```
Прочитай doc/team_workflow/generate_resume_prompt.md
и выполни инструкции.
TARGET_AGENT: <claude_code | codex | cursor_ai>
```

Можно указать пакет явно (если знаете ID):

```
Прочитай doc/team_workflow/generate_resume_prompt.md
TARGET_AGENT: cursor_ai
PACKAGE_ID: E15-A
```

---

## Чем отличается от generate_orchestration_prompt.md


|                        | generate_orchestration_prompt | generate_resume_prompt                     |
| ---------------------- | ----------------------------- | ------------------------------------------ |
| Точка старта           | Всегда Step 1 (PO)            | С первого незавершённого шага              |
| Артефакты              | Не нужны — создаются с нуля   | Читает существующие, инжектит как контекст |
| Обнаружение прогресса  | —                             | Сканирует `archive/team_artifacts/`    |
| Вердикты Tester        | —                             | Обрабатывает FAIL → Resume к Developer     |
| Контекст нового агента | Только пакет                  | Пакет + все предыдущие артефакты           |


---

## Инструкции для AI-агента

```text
Goal: generate a ready-to-paste RESUME prompt that continues
      an in-progress team pipeline from the last completed step.

INPUTS:
  TARGET_AGENT: <specified by user — claude_code | codex | cursor_ai>
  PACKAGE_ID:   <optional — if not given, discover из doc/backlog_registry.yaml; см. [`_common_rules.md`](_common_rules.md)>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASES 1–3 — SHARED WITH generate_orchestration_prompt.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Execute Phases 1, 2, 3 exactly as written in:
  doc/team_workflow/generate_orchestration_prompt.md

They produce:
  PACKAGE_ID, PACKAGE_TITLE, CJM_STAGE, USER_STORIES,
  OUTCOMES, DOD_COMMANDS, ARTIFACTS_DIR,
  PACKAGE_CONTEXT block,
  orchestrator_template.md content,
  agent adapter values for TARGET_AGENT.

If PACKAGE_ID was given by user — skip Phase 1 discovery,
use the provided value directly and proceed to Phase 2.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE R1 — SCAN ARTIFACTS (новая фаза, только для resume)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

List files in ARTIFACTS_DIR:
  (check if directory exists — if not, this is a fresh start,
   redirect user to generate_orchestration_prompt.md)

Apply the COMPLETION MAP to determine what is done:

  FILE PRESENT + non-empty?          STEP STATUS
  ─────────────────────────────────────────────────────────────
  1_po_package.md                  → Step 1 (PO)        ✓ DONE
  2_analyst_spec.md                → Step 2 (Analyst)   ✓ DONE
  3_architect_contract.md          → Step 3a (Architect)✓ DONE
  4_designer_ui_spec.md            → Step 3  (full)     ✓ DONE
  5a_developer_sp1.md              → Step 4 (Dev sp1)   ✓ DONE
  6a_tester_sp1.md
    + contains "VERDICT: PASS"
      or "VERDICT: CONDITIONAL PASS" → Step 5 (Test sp1) ✓ DONE
    + contains "VERDICT: FAIL"      → Step 4 REDO NEEDED ↩
  checkpoint_sp1.md                → CHECKPOINT commit sp1 ✓ DONE
    (if missing after Step 5 PASS → RESUME_STEP = "CHECKPOINT — commit sp1")
  5b_developer_sp2.md              → Step 6 (Dev sp2)   ✓ DONE
  6b_tester_sp2.md
    + contains "VERDICT: PASS"
      or "VERDICT: CONDITIONAL PASS" → Step 7 (Test sp2) ✓ DONE
    + contains "VERDICT: FAIL"      → Step 6 REDO NEEDED ↩
  ─────────────────────────────────────────────────────────────

Determine RESUME_STEP = first step whose condition is NOT met.

Special cases:
  A) 3_architect_contract.md present BUT 4_designer_ui_spec.md missing
     → RESUME_STEP = "Step 3b — Designer only"
     → Architect contract is available as context

  B) 6a_tester_sp1.md present with "VERDICT: FAIL"
     → RESUME_STEP = "Step 4 — Developer sp1 (redo)"
     → Extract blocker: first line after "VERDICT: FAIL"
     → BLOCKER = <that line>

  C) 6b_tester_sp2.md present with "VERDICT: FAIL"
     → RESUME_STEP = "Step 6 — Developer sp2 (redo)"
     → Extract blocker: first line after "VERDICT: FAIL"
     → BLOCKER = <that line>

  D) All 8 steps complete (6b has PASS)
     → Print: "✓ Pipeline for PACKAGE_ID is already complete."
     → Suggest: run generate_orchestration_prompt.md for next package
     → STOP

Print to user (before generating the prompt):
  "━━━━ Pipeline State: PACKAGE_ID ━━━━
   ✓ DONE  | Step 1  | PO          | 1_po_package.md
   ✓ DONE  | Step 2  | Analyst     | 2_analyst_spec.md
   ✓ DONE  | Step 3a | Architect   | 3_architect_contract.md
   ✗ TODO  | Step 3b | Designer    | (missing)
   ✗ TODO  | Step 4  | Developer   | —
   ...
   ─────────────────────────────────
   ▶ RESUME FROM: Step 3b — Designer"
  Wait 2 seconds (let user read), then continue.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE R2 — BUILD CONTEXT PACKAGE (что знает новый агент)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The new agent has NO memory of the previous agent's work.
It must receive the necessary completed artifacts as embedded context.

Use the CONTEXT DEPENDENCY MAP to decide what to inject:

  RESUME_STEP                INJECT THESE ARTIFACTS
  ─────────────────────────────────────────────────────────────
  Step 3b (Designer)         2_analyst_spec.md
                             3_architect_contract.md (write-set reference)
  Step 4 (Dev sp1)           3_architect_contract.md
                             4_designer_ui_spec.md
  Step 4 REDO (FAIL)         3_architect_contract.md (sp1 section)
                             4_designer_ui_spec.md
                             6a_tester_sp1.md (blocker section only)
  Step 5 (Tester sp1)        3_architect_contract.md (sp1 section)
                             5a_developer_sp1.md
  Step 6 (Dev sp2)           3_architect_contract.md (sp2 section)
                             4_designer_ui_spec.md
                             checkpoint_sp1.md (sp1 commit SHA)
                             [note: sp1 was verified PASS and committed]
  Step 6 REDO (FAIL)         3_architect_contract.md (sp2 section)
                             4_designer_ui_spec.md
                             6b_tester_sp2.md (blocker section only)
                             checkpoint_sp1.md (sp1 commit SHA)
  Step 7 (Tester sp2)        3_architect_contract.md (sp2 section)
                             5b_developer_sp2.md
                             checkpoint_sp1.md (sp1 commit SHA — use as COMMIT_RANGE base)
                             [note: sp1 verified PASS — regression expected]
  Step 8 (Closure)           6a_tester_sp1.md (verdict line)
                             6b_tester_sp2.md (verdict line)
  ─────────────────────────────────────────────────────────────

For Tester REDO cases:
  Extract ONLY the blocker block from the tester artifact (not full file).
  Format as:
    === BLOCKER FROM PREVIOUS TESTER RUN ===
    <extracted blocker text>
    === END BLOCKER ===
  This goes at the TOP of the Developer's prompt.

Read each artifact in the INJECT list.
Build CONTEXT_BLOCK:
  TOKEN BUDGET GUARD:
  Before building CONTEXT_BLOCK, estimate artifact sizes.
  If total injected content > ~15 000 words:
    Summarize each artifact to: section headers + key decisions/findings only.
    Add note at top: "⚠ Context summarized — full files at: ARTIFACTS_DIR"
  Otherwise inject full content.

For each artifact:
    === COMPLETED ARTIFACT: N_role_name.md ===
    <full content or summary if budget exceeded>
    === END ===

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE R3 — BUILD RESUME PROMPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Assemble the resume prompt in this structure:

┌─────────────────────────────────────────────────────────────┐
│ HEADER BLOCK                                                │
├─────────────────────────────────────────────────────────────┤
│ PIPELINE STATE BLOCK (completed steps summary)              │
├─────────────────────────────────────────────────────────────┤
│ CONTEXT BLOCK (injected artifacts)                          │
├─────────────────────────────────────────────────────────────┤
│ RESUME EXECUTION (steps from RESUME_STEP to Step 8)         │
│   — uses same step structure as orchestrator_template.md    │
│   — uses agent syntax from the adapter file                 │
└─────────────────────────────────────────────────────────────┘

HEADER BLOCK format:
  ╔══════════════════════════════════════════════════════════╗
  ║  TEAM PIPELINE RESUME — PACKAGE_ID  [TARGET_AGENT]      ║
  ╚══════════════════════════════════════════════════════════╝
  Resuming from: RESUME_STEP
  Artifacts dir: ARTIFACTS_DIR
  Agent: TARGET_AGENT

PIPELINE STATE BLOCK format:
  ── PIPELINE STATE ──────────────────────────────────────────
  [✓ DONE]  Step 1  — Product Owner    → 1_po_package.md
  [✓ DONE]  Step 2  — Analyst          → 2_analyst_spec.md
  [✓ DONE]  Step 3a — Architect        → 3_architect_contract.md
  [▶ START] Step 3b — Designer         ← RESUME HERE
  [ TODO ]  Step 4  — Developer sp1
  [ TODO ]  Step 5  — Tester sp1
  ...
  ────────────────────────────────────────────────────────────
  ⚠ Previous agent stopped at: Step 3b (artifact missing)
    OR
  ⚠ Previous agent stopped at: Step 4 REDO — FAIL blocker:
    "<blocker text>"

CONTEXT BLOCK format:
  ── CONTEXT FROM COMPLETED STEPS ───────────────────────────
  (Read by new agent before executing — do not skip)
  === COMPLETED ARTIFACT: 3_architect_contract.md ===
  <content>
  === END ===
  ...
  ────────────────────────────────────────────────────────────

RESUME EXECUTION:
  Copy steps RESUME_STEP through Step 8 from the filled
  orchestrator template (as generated in Phase 4 of
  generate_orchestration_prompt.md).

  For the FIRST active step (RESUME_STEP):
    Add at top of step instructions:
      "Context from previous agent is embedded above in CONTEXT BLOCK.
       Read it before acting — do not re-read files that are already
       provided there."

  For REDO steps (Tester FAIL → Developer):
    Replace the step title with:
      "STEP N — Developer sp1 (REDO — fix blocker from Tester)"
    Add at top:
      "⚠ Redo required. Previous Tester run returned FAIL.
       Blocker is at the top of this prompt.
       Fix ONLY the blocker. Do not re-implement from scratch."

  For all steps from RESUME_STEP+1 onward:
    Keep identical to the original orchestrator template steps
    (same syntax, same checkpoints, same verdict routing).

  ORCHESTRATOR RULES section:
    Keep unchanged from orchestrator_template.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE R4 — OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Print to user:
  "Resume prompt ready for PACKAGE_ID on TARGET_AGENT.
   Resuming from: RESUME_STEP
   Context injected: N artifacts
   Saving to: ARTIFACTS_DIR/resume_TARGET_AGENT_stepN.md"

Save:
  ARTIFACTS_DIR/resume_TARGET_AGENT_step<RESUME_STEP_NUMBER>.md

Then print the full prompt to the user for copy-paste.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NEVER assume an artifact is complete without reading its content.
  An empty file or a file ending mid-sentence is NOT complete.
- NEVER inject the full content of ALL artifacts — only what
  CONTEXT DEPENDENCY MAP says is needed for RESUME_STEP.
  Injecting everything wastes context window and confuses the agent.
- NEVER omit the PIPELINE STATE BLOCK — the new agent needs to know
  what it is continuing, not starting.
- For REDO steps: inject the blocker at the very TOP of the prompt,
  before the context block. The Developer must see it first.
- If a "CONDITIONAL PASS" step has deferred items, include them in
  the PIPELINE STATE BLOCK as:
    [✓ COND] Step 5 — Tester sp1 → deferred: <item>
- Do NOT regenerate artifacts for completed steps.
  Even if an artifact looks suboptimal — it was accepted, keep it.
- The output must be immediately pasteable. No "[fill in here]" gaps.
```

---

## Сценарии использования

### Сценарий A: Агент завис на середине

Другой агент начал E15-A, сделал Steps 1–3, упал на Step 4 (закончился контекст).

```
Прочитай doc/team_workflow/generate_resume_prompt.md
TARGET_AGENT: claude_code
PACKAGE_ID: E15-A
```

→ Получаете промпт который стартует с Step 4, с контрактом Архитектора
  и UI-спецификацией Дизайнера вшитыми как контекст.

### Сценарий B: Тестировщик сказал FAIL

Step 5 (Tester sp1) вернул `VERDICT: FAIL`. Вы хотите передать фикс
новому агенту, не объясняя всю историю вручную.

```
Прочитай doc/team_workflow/generate_resume_prompt.md
TARGET_AGENT: cursor_ai
PACKAGE_ID: E15-A
```

→ Система находит `VERDICT: FAIL` в `6a_tester_sp1.md`, извлекает blocker,
  генерирует Resume промпт с пометкой "REDO — fix blocker" в Step 4.
  Blocker — первое что видит Developer.

### Сценарий C: Смена агента

Начали в Cursor AI, хотите продолжить в Claude Code (например, параллелизм нужен).

```
Прочитай doc/team_workflow/generate_resume_prompt.md
TARGET_AGENT: claude_code
PACKAGE_ID: E15-A
```

→ Генерирует Resume промпт с синтаксисом Claude Code (Agent tool),
  с инжектированным контекстом — новый агент не знает что был предыдущий.

### Сценарий D: Смена члена команды

Коллега сделал роль Архитектора в своём агенте, передаёт вам.
У вас нет истории его сессии.

→ Просто запустите generate_resume_prompt — он найдёт артефакты
  в `archive/team_artifacts/PACKAGE_ID/` и сгенерирует
  промпт с нужным контекстом.

---

## Связанные файлы


| Файл                                                                   | Назначение            |
| ---------------------------------------------------------------------- | --------------------- |
| `[generate_orchestration_prompt.md](generate_orchestration_prompt.md)` | Старт с нуля          |
| `[orchestrator_template.md](orchestrator_template.md)`                 | Базовый шаблон        |
| `[agent_adapter_claude_code.md](guides/agent_adapter_claude_code.md)`         | Синтаксис Claude Code |
| `[agent_adapter_codex.md](guides/agent_adapter_codex.md)`                     | Синтаксис Codex CLI   |
| `[agent_adapter_cursor_ai.md](guides/agent_adapter_cursor_ai.md)`             | Синтаксис Cursor AI   |


