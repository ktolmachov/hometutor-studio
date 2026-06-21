# generate_orchestration_prompt

Актуализировано: **2026-04-29**

Генерирует готовый промпт оркестратора для следующего активного пакета
из `doc/backlog_registry.yaml` под конкретного агента.
Общие правила **SSoT / tasklist / PowerShell / токены / sync**: [`_common_rules.md`](_common_rules.md).
`doc/tasklist.md` — только derived display; источник истины — YAML (см. канон выше).

> **Предпочтительный путь** — Python-скрипт ниже (Phases 1–5 выполняются автоматически).
> Мануальный процесс (Phases 1–5 через AI-агент) сохранён ниже как запасной вариант.

---

## ⚡ Автоматический способ (рекомендуется)

```bash
# Основной вызов — автовыбор пакета:
python scripts/generate_orchestration_prompt.py --agent cursor_ai
python scripts/generate_orchestration_prompt.py --agent claude_code
python scripts/generate_orchestration_prompt.py --agent codex

# Явное указание пакета:
python scripts/generate_orchestration_prompt.py --agent cursor_ai --package epoch-foo

# Просмотр активных пакетов:
python scripts/generate_orchestration_prompt.py --list

# Dry-run (не сохранять на диск):
python scripts/generate_orchestration_prompt.py --agent cursor_ai --dry-run

# Принудительная генерация (пакет уже в работе):
python scripts/generate_orchestration_prompt.py --agent cursor_ai --force
```

**Что делает скрипт** (заменяет Phases 1–5):
- Phase 1: находит активный пакет в `doc/backlog_registry.yaml` (приоритет: `wip > ready > open > proposed`)
- Phase 1: work-state detection — если `execution_contract.md` уже есть → STOP с инструкцией
- Phase 2: pre-extracts context (US acceptance criteria, CJM moment, recent closed iterations)
- **Phase 2.5: Ops Impact detection** — сопоставляет анонсированный write-set / scope hints из реестра со списком триггеров из [`rag_llm_ops_project_document.md` §35](rag_llm_ops_project_document.md#35-hook-в-team-workflow-процесс). Выставляет `{{OPS_GATE_NEEDED}}` и `{{OPS_ROLES_TRIGGERED}}` (см. ниже)
- Phase 3: загружает `orchestrator_template.md` + адаптер агента
- Phase 4: программно заполняет все `{{PLACEHOLDER}}` (Codex MAX_PARALLEL=1 → Step 3 sequential; STEP 3.5 при `{{OPS_GATE_NEEDED}}=true` тоже sequential для Codex)
- Phase 5: сохраняет в `archive/team_artifacts/<ID>/orchestration_<agent>.md`, добавляет строку в `archive/pipeline_metrics.md` (включая колонку ops_gate)

---

---

## Мануальный путь (только если скрипт недоступен)

> ⛔ **Используй этот раздел только если `scripts/generate_orchestration_prompt.py` недоступен.**
> Мануальный путь дороже по токенам, медленнее и допускает больше ошибок.
> Если скрипт работает — используй автоматический способ выше.

Вставить в любой AI-агент (Claude Code, Codex, Cursor AI):

```
Прочитай doc/team_workflow/generate_orchestration_prompt.md
и выполни инструкции (мануальный раздел).
TARGET_AGENT: <claude_code | codex | cursor_ai | continue>
```

### Инструкции для AI-агента (мануальный путь)

```text
Goal: generate a ready-to-paste orchestration prompt for the next active
      delivery package in hometutor.

INPUT:
  TARGET_AGENT: <specified by user — claude_code | codex | cursor_ai | continue>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — DISCOVER NEXT ACTIVE PACKAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read: doc/backlog_registry.yaml  (primary source; см. также [`_common_rules.md`](_common_rules.md))
Optional cross-check: doc/tasklist.md  (generated display only; do not use it to override registry)

Search for the first package with status `wip`, `ready`, `open`, or `proposed` in registry items
(priority: wip > ready > open > proposed).

WORK-STATE CHECK (mandatory before Phase 2):

  Step A — Check if orchestration for THIS agent already exists:
    If archive/team_artifacts/<PACKAGE_ID>/orchestration_<TARGET_AGENT>.md exists:
      STOP (file already generated for this agent).
      Print: "⛔ orchestration_<TARGET_AGENT>.md already exists. Use --force to regenerate."
      Exit unless user explicitly requests --force.

  Step B — Check for execution artefacts + multi-agent scenario:
    If execution_contract.md exists:
      Check if orchestration_<OTHER_AGENT>.md files exist in team_artifacts/:
        YES (other agents already have orchestration):
          → PROCEED without --force (multi-agent scenario is valid).
          Print: "ℹ Generating orchestration for <TARGET_AGENT>
                    (orchestration for <OTHER_AGENTS> already exists)"
        NO (no orchestration at all):
          → STOP. Print:
              "⛔ Execution artefacts exist but no orchestration yet.
               Options:
                 Resume:  python scripts/generate_next_prompt.py --resume
                 Close:   python scripts/close_package.py
                 Force:   python scripts/generate_orchestration_prompt.py --agent TARGET_AGENT --force"
          Exit unless user explicitly requests --force.

CASE A — Active package found:
  Extract:
    PACKAGE_ID    ← package identifier (e.g. "E15-A")
    PACKAGE_TITLE ← one-line description
    CJM_STAGE     ← CJM stage from the entry
    USER_STORIES  ← comma-separated US-* references
    OUTCOMES      ← bullet list of user-visible outcomes
    DOD_COMMANDS  ← DoD pytest commands from the entry

CASE B — No active package (section "Now" has no open/WIP):
  DO NOT STOP. Auto-pivot to planning workflow immediately:

  Preferred path (script):
    Run: python scripts/generate_orchestration_prompt.py --agent TARGET_AGENT
    The script detects no active registry package and automatically outputs the full
    generate_plan_next_prompt.md instructions. Execute them in this session.

  Manual path (no script available):
    Read and execute doc/team_workflow/generate_plan_next_prompt.md
    immediately — do not pause for user confirmation.
    After planning adds a package to backlog_registry.yaml and regenerates tasklist.md, continue with orchestration.

  Legacy note (old behaviour — do NOT follow):
    Print:
      [This message is now obsolete — see CASE B above]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — ENRICH PACKAGE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each US-* in USER_STORIES:
  Read: doc/user_stories/<US-N.M>.md   (if file exists)
  Extract: acceptance criteria summary (≤ 3 bullet points per story)
  If file missing: flag "⚠ user story file missing: <US-N.M>.md"

Read: doc/cjm.md
  Find the entry for CJM_STAGE
  Extract: pain point description (1 sentence)

Read: doc/closed_iterations.md (last 2-3 closure blocks at file tail — not the header/index)
  Note: what was delivered recently (avoid duplicating)

Read: doc/conventions.md (TL;DR section only — do not load full file)

Build:
  PACKAGE_CONTEXT block:
    ID:            PACKAGE_ID
    Feature:       PACKAGE_TITLE
    CJM Stage:     CJM_STAGE — <pain point description>
    User Stories:  USER_STORIES
    Outcomes:
      1. <outcome 1>
      2. <outcome 2>
      ...
    Key AC:
      US-N.M: <1-3 bullet acceptance criteria>
      ...
    DoD commands: DOD_COMMANDS

  ARTIFACTS_DIR:  archive/team_artifacts/PACKAGE_ID/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2.5 — OPS IMPACT DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Goal: decide whether STEP 3.5 (Ops Impact Gate) fires for this package, and which Ops
roles to invoke. Output: two placeholders consumed by Phase 4.

INPUT (from registry entry only — DO NOT speculate):
  - any `write_set:` hints
  - any `affected_files:` hints
  - `outcomes` text (string-search for module names)
  - `cjm_moments`, `user_stories` text (string-search for known module names)

TRIGGER TABLE (canonical — keep in sync with rag_llm_ops_project_document.md §35
              and performance_devops.md):
  llmops  ← app/provider.py
  llmops  ← app/config.py (new LLM/embeddings/profile keys per balance plan §Phase 1)
  llmops  ← app/prompts/ OR app/tutor_prompts.py
  llmops + performance  ← scripts/local_readiness.py OR app/ui/llm_local_banner.py
  ragops  ← app/query_service.py OR app/pipeline_steps.py
  ragops  ← app/course_cache.py OR app/ui/study_scope.py
  ragops  ← data/docs/ (course corpus writes)
  ragops  ← app/routers/course_upload.py OR app/services/course_upload_service.py
  mlops + ragops  ← app/knowledge_graph.py
  mlops + ragops  ← embeddings model / chunking strategy / index version
  performance  ← scripts/local_*.{py,ps1} OR .env.example
  performance  ← any new timeout / budget / runtime dependency
  performance + ragops  ← new ingestion-pipeline step / ingest throughput change
  performance (sole)  ← Dockerfile / CI workflow / GitHub Actions

ALGORITHM:
  triggered_roles = set()
  for each module path or balance-plan §-reference in registry hints:
    if matches a row above → add the role(s) to triggered_roles
  {{OPS_ROLES_TRIGGERED}} = comma-joined sorted list (e.g. "llmops,ragops")
  {{OPS_GATE_NEEDED}}     = "true" if triggered_roles non-empty else "false"

FALLBACK (ambiguous registry):
  If registry entry has no write_set hints AND no module names appear in any text field:
    Set {{OPS_GATE_NEEDED}}="false" and {{OPS_ROLES_TRIGGERED}}=""
    BUT print a one-line warning:
      "⚠ No Ops triggers detected from registry text. If Architect contract in STEP 3
       reveals affected Ops surfaces, manually re-run STEP 3.5."

NEVER infer Ops triggers from CJM-stage names alone (CJM is too broad).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — LOAD TEMPLATE + AGENT ADAPTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read: doc/team_workflow/orchestrator_template.md
  This is the base template with {{PLACEHOLDERS}}.

Read agent adapter based on TARGET_AGENT:
  claude_code → doc/team_workflow/guides/agent_adapter_claude_code.md
  codex       → doc/team_workflow/guides/agent_adapter_codex.md
  cursor_ai   → doc/team_workflow/guides/agent_adapter_cursor_ai.md
  continue    → doc/team_workflow/guides/agent_adapter_continue.md
  kilo        → doc/team_workflow/guides/agent_adapter_kilo.md

The adapter file defines how to substitute each {{PLACEHOLDER}}
for the target agent's syntax and capabilities.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4 — FILL TEMPLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replace every {{PLACEHOLDER}} in orchestrator_template.md:

Package placeholders (from Phase 2):
  {{PACKAGE_ID}}      → PACKAGE_ID
  {{PACKAGE_TITLE}}   → PACKAGE_TITLE
  {{CJM_STAGE}}       → CJM_STAGE — <pain point>
  {{USER_STORIES}}    → USER_STORIES
  {{OUTCOMES}}        → formatted outcome list
  {{ARTIFACTS_DIR}}   → archive/team_artifacts/PACKAGE_ID/
  {{DOD_COMMANDS}}    → DOD_COMMANDS from Phase 1 (exact pytest commands)

Agent placeholders (from adapter file):
  {{PARALLEL_SYNTAX}} → value from adapter
  {{READ_FILE}}       → value from adapter
  {{WRITE_FILE}}      → value from adapter
  {{RUN_CMD}}         → value from adapter
  {{AGENT_SPAWN}}     → value from adapter
  {{MAX_PARALLEL}}    → value from adapter

Ops gate placeholders (from Phase 2.5):
  {{OPS_GATE_NEEDED}}      → "true" | "false"
  {{OPS_ROLES_TRIGGERED}}  → comma-joined list (e.g. "ragops,llmops") or ""

DoD placeholder:
  In each STEP N — Developer section:
    Replace generic DoD with DOD_COMMANDS from the package entry.
    If backlog_registry.yaml has no DoD commands: use "pytest tests/ -k <package_id_lower> -v"

Step 3 parallelism:
  If MAX_PARALLEL == 1 (Codex):
    Split Step 3 into "STEP 3a — Architect" and "STEP 3b — Designer"
    Add note: "[SEQUENTIAL — no native parallel agents]"
  If MAX_PARALLEL > 1 (Claude Code, Cursor AI):
    Keep Step 3 as single parallel step
    Fill {{PARALLEL_SYNTAX}} with adapter value

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5 — OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Print to user:
  "Generated orchestration prompt for PACKAGE_ID on TARGET_AGENT."
  "CJM: CJM_STAGE | Outcomes: N | Sub-packages: M"
  "Saving to: archive/team_artifacts/PACKAGE_ID/orchestration_TARGET_AGENT.md"

Save the filled prompt:
  archive/team_artifacts/PACKAGE_ID/orchestration_TARGET_AGENT.md

Then print the full filled prompt to the user so they can copy-paste it
into the target agent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Do NOT invent package scope. Use only what is in `doc/backlog_registry.yaml`
  or confirmed by the user in Phase 1 Case B.
- Do NOT skip Phase 2 enrichment — AC and pain point context are
  required for the Developer and Tester steps to be usable.
- Do NOT output a partial prompt. The result must be complete
  and immediately pasteable into the target agent without editing.
- If any required file is missing (US story, cjm entry), flag it
  and use a placeholder: "[MISSING: doc/user_stories/US-N.M.md]"
- The output prompt must reference doc/team_workflow/<role>.md files
  exactly as written in orchestrator_template.md — do not paraphrase.
```
