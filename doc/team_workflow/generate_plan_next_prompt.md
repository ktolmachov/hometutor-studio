# generate_plan_next_prompt

Актуализировано: **2026-05-02**

Промпт для **генерации нового пакета** в [`doc/backlog_registry.yaml`](../backlog_registry.yaml), когда активный backlog пуст или устарел.
[`doc/tasklist.md`](../tasklist.md) является производным weekly view и обновляется только через sync-скрипт.

> **Быстрый старт:** не знаешь с чего начать? Запусти роутер:
> ```bash
> python scripts/workflow.py
> ```
> Он сам определит состояние и выдаст следующий шаг. Документация: [`workflow_router.md`](./workflow_router.md).

> Активный пакет уже есть в [`doc/backlog_registry.yaml`](../backlog_registry.yaml) со статусом `wip`/`ready`?
> → [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md) — запустит оркестрацию.
>
> Работа по конкретному PACKAGE_ID уже начиналась (есть `archive/team_artifacts/<ID>/`)?
> → [`generate_resume_prompt.md`](./generate_resume_prompt.md) — подхватит точку остановки.
>
> Backlog пустой или устаревший (все пакеты закрыты, нет `ready`/`WIP`)?
> → **этот файл**. Делает планирование, а не запуск.

---

## Правило выбора входа

| Ситуация | Что запускать |
|----------|---------------|
| Есть пакет со статусом `ready` или `WIP` в [`doc/backlog_registry.yaml`](../backlog_registry.yaml) | [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md) |
| Работа по `PACKAGE_ID` уже начиналась | [`generate_resume_prompt.md`](./generate_resume_prompt.md) |
| Backlog пустой / все закрыты / хочу спланировать следующее | [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md) (этот файл) |

---

## Чем отличается от [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md) (§ Case B)

`generate_orchestration_prompt` в Case B предлагает **одного** кандидата и сразу идёт в оркестрацию.

Этот файл — **полноценная фаза планирования**:

| Различие | Orchestration Case B | Plan Next (этот файл) |
|----------|----------------------|----------------------|
| Число кандидатов | 1 | 1–3 с ranking |
| Глубина контракта | минимальный stub | полный контракт (DoD, metrics, write-set, read-set hint) |
| Preflight token-check | нет | обязателен для каждого кандидата |
| Запись в [`backlog_registry.yaml`](../backlog_registry.yaml) | нет | да, после accept; [`tasklist.md`](../tasklist.md) регенерируется |
| Следующий шаг | сразу запускает оркестрацию | **останавливается** — планирование и исполнение разделены |

Разделение снижает риск: человек видит обоснованный контракт **до** того, как начнётся запись кода.

---

## Как использовать

Вставить в любой AI-агент (Claude Code, Codex, Cursor AI):

```
Прочитай doc/team_workflow/generate_plan_next_prompt.md
и выполни инструкции.
```

Опционально (если хочется ограничить):

```
Прочитай doc/team_workflow/generate_plan_next_prompt.md
FOCUS_CJM: 2    # id momenta of truth из doc/cjm.md § 5
MAX_CANDIDATES: 3
TARGET_AGENT: continue
```

---

## Инструкции для AI-агента

```text
Goal: produce 1–3 proposed wave (or single-package) contracts for
      doc/backlog_registry.yaml when the backlog is empty or stale.
      Stop after writing the accepted contract — do NOT run orchestration.

INPUT (optional):
  FOCUS_CJM:      <moment id 1–6 from doc/cjm.md § 5; default: all>
  MAX_CANDIDATES: <1..3; default: 3>
  TARGET_AGENT:   <claude_code | codex | cursor_ai | continue; default: cursor_ai>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 — DRIFT GUARD (MANDATORY, runs before anything else)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run: python scripts/check_backlog_drift.py

Interpret exit codes (see scripts/check_backlog_drift.py docstring):
  0 = OK — proceed to Phase 1.
  1 = WARN-only (reserved; when implemented, print warnings and continue normal
      Phases 1+ unless team policy says otherwise). Do NOT enter the DRIFT fast-path
      unless the tool output includes explicit DRIFT violation lines (today: use exit 2 only).
  2 = DRIFT — enter the DRIFT fast-path below.

  As of 2026-05-02 the script only returns 0 or 2 in practice (warnings list is always empty).

If exit == 1 under a future script version: never invoke the DRIFT fast-path on WARN alone.

If exit == 2 (DRIFT):
  STOP ranking / pool expansion (Phases 2–3) and skip Phase 6 (multi-candidate choice).
  Print: "⚠ Drift detected — remediation path (single candidate)."
  Run: same script with --explain; follow printed quick-fix hints when safe.

  Inspect doc/backlog_registry.yaml for package id `epoch-truth-sync` (grep id + status only):
    - If status is `ready` or `wip`: STOP this prompt. Print: use
      generate_orchestration_prompt.md (or generate_resume_prompt.md) — do not
      add a duplicate contract.
    - If status is `closed` or the id is absent: do NOT resurrect the historical
      id for a new remediation. Draft ONE new remediation package (new PACKAGE_ID,
      e.g. epoch-ssot-drift-<YYYYMMDD>) using the contract template in
      archive/agent_prompts/wave_planning_migration_spec_2026-04-22.md § 3 as
      content baseline (same checks/commands scope), adjusted to current US/CJM refs.
    - If status is `proposed` (only): you may advance that row to `ready` per
      Phase 7 after preflight, instead of inventing a second id.

  Still run Phase 4 for that single candidate and Phase 5 (preflight: check_readset +
  lint_agent_prompts). If Phase 5 is BLOCK for the drafted read-set — STOP and
  escalate to a human (no silent registry write).
  Phase 7: write/update doc/backlog_registry.yaml for that one package. Drift path
  waives Phase 6 interactive pick after preflight SAFE or WARN; document the waiver
  in the printed summary.

Otherwise proceed to Phase 1.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — VERIFY BACKLOG IS ACTUALLY EMPTY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read: doc/backlog_registry.yaml (status/id/title/priority/wave fields only; grep/section read, never full-read)

If doc/backlog_registry.yaml contains any item with status `ready` or `wip`:
  STOP this planning prompt.
  Print:
    "⚠ Backlog не пуст. Найдены активные пакеты:
       - <PACKAGE_ID_1> (<status>)
       - <PACKAGE_ID_2> (<status>)
     Следующий шаг: generate_orchestration_prompt.md (новая оркестрация)
     или generate_resume_prompt.md (продолжение по artifact)."
  Automation / Zero-Click: do not treat this as terminal success. Immediately load
  doc/team_workflow/generate_orchestration_prompt.md (or generate_resume_prompt.md
  if artifacts for that PACKAGE_ID already exist) and continue the pipeline in the
  same session — same as if the operator had chosen the correct entrypoint from the
  table at the top of this file.

Otherwise proceed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — DISCOVER CANDIDATE POOL (strict read-set)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Token budget for this phase: ≤ 8k input tokens total.

Epoch / archive files (token_safety — full-read **forbidden** for most):
  - **doc/epochs/*.md** — do not open whole files or the folder. If a single epoch is
    strictly required: pick **at most one** file via `rg -l "<keyword>" doc/epochs/*.md`,
    then read **only** the header + one target section (or `head -n 40`), never ~700+ lines.
  - Prefer **doc/future_roadmap.md** for “what’s next” instead of deep epoch dives.
  - **doc/changelog.md**, **doc/adr.md** — tail or status table only if needed; never full-read.

Preferred source (if present, read first and prefer over prose):
  0. doc/backlog_registry.yaml (schema v2 when available)
       - Authoritative list of proposed/ready/deferred items and waves.
       - Before using: run `python scripts/backlog_registry_lint.py --strict`;
         if the command exits non-zero, fall back to sources 1–5 below and flag the lint
         errors in the final report.
       - If schema_version >= 2: use waves: block as primary candidate pool
         (Phase 3 wave-ranking formula below).
       - If schema_version == 1 or waves: is empty: use single-package ranking
         (legacy formula in Phase 3 fallback).
       - Registry items with `status: ready` or a met `re_entry_condition`
         become candidate sources (c) and (d) in Phase 3.

Read ONLY (fallback or enrichment when registry is absent/stale):
  1. doc/cjm.md
       - § 5 Критические моменты (all)
       - § 8 Где CJM подсвечивает текущие задачи (all)
       - Skip § 2–4 narrative
  2. doc/user_stories.md
       - "Базовый shortlist из CJM" section
       - § Индекс Stories (for resolving US-* → file paths only)
       - Skip closed shortlists (E10/E11/E13) — historical
  3. doc/closed_iterations.md
       - Last 3 closure blocks only (хвост файла — свежие `### ...`; не Индекс Эпох в начале, не full-read).
         Подсказка: `rg "^### " doc/closed_iterations.md` — взять последние 3 заголовка и прочитать только эти
         блоки; либо `Get-Content doc/closed_iterations.md -Tail 160` (PowerShell).
  4. doc/future_roadmap.md
       - Only epochs whose entry condition is met per registry state
       - Safe read: one section / table at a time; if the file is large, use rg for the
         epoch id or heading, then copy only that block (see doc/token_safety.md).
  5. doc/backlog_registry.yaml deferred/proposed items
       - re-entry conditions — a deferred item may have become ready

Do NOT read in this phase:
  - individual doc/user_stories/us-*.md files (only after shortlist)
  - doc/epochs/*.md except the narrow exception above (max one file, fragment only —
    arch history is usually **not** needed to propose; default = skip entirely)
  - doc/conventions*.md (applies at execution time, not planning)
  - doc/architecture.md, doc/adr.md (too large; planning uses CJM + US)

If any source file is missing: flag "⚠ missing: <path>" and continue with what exists.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — RANK CANDIDATES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

═══ WAVE-RANKING (primary, when schema_version >= 2 and waves pool non-empty) ═══

Candidate = WAVE (not a single package).
Pool = waves with status in {proposed, ready} where all depends_on are closed.

Score each wave 1–5 on:
  - user_visible_impact    35%  (sum of packages' impact;
                                 max 5 if ≥2 pkgs move a P0 MoT)
  - wave_synergy           20%  (n_unique_us * 0.8 + shared_read_files * 0.4,
                                 capped at 5; shared_read_files = files
                                 appearing in read_set_hint of ≥2 packages)
  - mot_recency_gap        20%  (days since entry_mot last touched;
                                 ≥14d → 5, 7d → 3, <3d → 1, null → 3)
  - dependency_ready       15%  (all depends_on waves/packages closed → 5)
  - delivery_cost          10%  (inverse: sum cost_estimate; all-S → 5,
                                 any L → 1, mixed M → 3)

Rank desc by weighted score. Take top MAX_CANDIDATES waves.

Fallback: if waves pool is empty → use single-package ranking below.

═══ SINGLE-PACKAGE RANKING (fallback) ═══

Candidate sources:
  (a) Active pain points from cjm.md § 8 not yet addressed.
  (b) P0 user stories whose acceptance criteria are not yet satisfied.
  (c) Deferred items whose re-entry condition is now met.
  (d) Future-roadmap entries whose entry condition is met.

Score each candidate 1–5 on:
  - user_visible_impact    40%   (moves a CJM moment of truth)
  - cjm_moment_criticality 30%   (higher for P0 moments: #2, #5, #7)
  - dependency_ready       20%   (no blockers, all upstream done)
  - delivery_cost          10%   (lower is better; prefer ≤3 file write-set)

Rank desc by weighted score. Take top MAX_CANDIDATES.

If fewer than MAX_CANDIDATES distinct candidates: proceed with what exists,
note "⚠ pool smaller than requested" and the reason.

If no candidate is eligible under current registry / re-entry rules:
  STOP before drafting contracts.
  Print:
    "blocker: no eligible plan-next candidate under current registry/re-entry rules."

  Planning escape hatch BEFORE manually packaging one epoch (human-driven):
    1) Optionally run doc/team_workflow/generate_breakthrough_ideation_prompt.md
       in MODE=CANDIDATE_TABLE (see § «Как использовать» there): one Markdown table
       of rows (CJM Stage/Moment · US · pain · feature area · source) from cjm /
       user_stories / future_roadmap (+ optional backlog grep).
    2) Pick a TARGET from that table; optionally run full breakthrough ideation
       (TARGET + N_IDEAS) if many hypotheses are needed; artifact only — no registry write.
    3) Then use doc/team_workflow/product_owner_plan_package_prompt.md
       to formulate ONE proposed package after reassessing CJM, deferred items, and roadmap.

  Canonical minimal path (same blocker text): jump straight to
  doc/team_workflow/product_owner_plan_package_prompt.md if ideation/table is skipped.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4 — DRAFT CONTRACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each ranked candidate:
  Read: doc/user_stories/<primary_US>.md  (only ONE US file per candidate)
  Read: one relevant section of cjm.md § 8 for that moment

  Draft the following fields:

    PACKAGE_ID        slug: "epoch-<topic>" or "E<N>-<letter>" aligned
                      with existing naming in closed_iterations.md
    PACKAGE_TITLE     one line, user-visible outcome
    CJM_STAGE         "<moment id> — <moment name>"
    PAIN_POINT        one sentence from cjm.md § 8 for that moment
    USER_STORIES      comma-separated, primary first
    WAVE_ID           wave this package belongs to (if wave-ranking was used)
    OUTCOMES          2–4 bullets, user-visible, testable
    TARGET_ARTIFACTS  3–5 files with expected_result column
    METRICS           numeric thresholds (where applicable)
    DOD               4–5 checkpoints, each with a pytest / script command
    WRITE_SET_MAX     list of globs/paths (≤ 5 entries)
    READ_SET_HINT     list of paths + safe method per doc/token_safety.md
                      (e.g. "app/query_service.py — signatures only")
    DOD_COMMANDS      exact pytest commands for test_bundles
    RATIONALE         2 sentences: why this candidate beats the others

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5 — PREFLIGHT TOKEN CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each candidate:
  Run: python scripts/check_readset.py <READ_SET_HINT paths>

  Interpret result:
    SAFE  → keep as-is
    WARN  → add "compress read-set before orchestration" to RATIONALE
    BLOCK → drop candidate from pool; append a replacement from Phase 3
            runner-up, or note "⚠ pool reduced" if no runner-up exists.

Also run: python scripts/lint_agent_prompts.py
  If it reports issues, add them as known blockers for all candidates
  (they affect every orchestration regardless of package).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6 — PRESENT TO USER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If wave-ranking was used, print a wave comparison table first:

  | # | WAVE_ID | Pkgs | Entry→Exit MoT | North star (short) | Score | Drift | Notes |
  |---|---------|------|----------------|--------------------|-------|-------|-------|
  | 1 | wave-flashcard-polish   | 2 | #12→#12 | Deck UX без инструкций | 4.1 | SAFE | ... |
  | 2 | wave-first-answer-ux    | 1 | #2→#2   | Example questions       | 3.8 | SAFE | ... |
  | 3 | wave-sync-export        | 2 | infra   | Multi-device restore    | 3.2 | SAFE | ... |

Then print individual candidate (first package of each wave) comparison table:

  | # | PACKAGE_ID | CJM | Primary US | Score | Read-set check | Notes |
  |---|------------|-----|------------|-------|----------------|-------|
  | 1 | ...        | ... | ...        |  4.3  | SAFE           |       |
  | 2 | ...        | ... | ...        |  3.8  | WARN           | ...   |
  | 3 | ...        | ... | ...        |  3.5  | SAFE           |       |

Then print each candidate's FULL registry-ready contract block in the
schema used by doc/backlog_registry.yaml.

Finally, ask:

  "Which candidate to accept?
     1 / 2 / 3       — accept as-is, write contract to backlog_registry.yaml
     1m / 2m / 3m    — accept with modifications (then specify)
     refine          — expand pool, re-rank
     abort           — stop without changes
  "

Wait for user input. Do not proceed without explicit accept.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7 — WRITE CONTRACT TO REGISTRY (only after explicit accept)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SSoT, запрет правок tasklist «в обход», команды lint/sync: [`_common_rules.md`](_common_rules.md).

When user answers 1 / 2 / 3 (with or without modifications):

  Edit doc/backlog_registry.yaml:
    - Set package status → "ready"
    - Ensure dod_commands, user_stories, outcomes/blocks, read_set_hint are filled in
    - If package belongs to a wave, ensure wave status is "wip" or "ready"
    - Ensure items[].id for the new row is unique (lint will fail on duplicates)

  Mandatory validation + sync (do not skip; if any step fails, fix YAML and repeat):

    1. Lint + regenerate derived views — из корня, по разделу **Sync** `_common_rules.md`
       (`--strict --sync-from-index --write-sync` при schema_version >= 2; иначе см. канон).

    2. If this command exits **non-zero**: Phase 7 is **not** complete — repair
       syntax/schema/uniqueness until lint passes; do not hand off to orchestration.

  This regenerates doc/tasklist.md automatically (Truth View + Wave queue + contract block).

  Do NOT:
    - edit doc/tasklist.md manually
    - create git commits
    - modify any other file
    - run orchestration

Print:

  "✅ Contract written to doc/backlog_registry.yaml for <PACKAGE_ID>;
   doc/tasklist.md regenerated from the registry.
   Review the diff, commit when happy, then run:

       Прочитай doc/team_workflow/generate_orchestration_prompt.md
       TARGET_AGENT: <claude_code | codex | cursor_ai | continue>

   If TARGET_AGENT is continue, first generate the agent-specific orchestration
   document:

       .\.venv\Scripts\python.exe scripts\generate_orchestration_prompt.py --agent continue

   Then use the manual handoff loop until the DeepSeek TUI executor wrapper is
   implemented:

       .\.venv\Scripts\python.exe scripts\workflow.py --loop --skip-review --watch-contract --agent continue --post-agent-no-dod-cache

   Do not use `scripts/deepseek_agent_trigger.ts` as a production executor:
   it is a DeepSeek Chat API handoff experiment with no local file tools.
   Target implementation plan:
   doc/team_workflow/guides/workflow_deepseek_tui_trigger_implementation_plan.md

   For other TARGET_AGENT values, replace `continue` in the orchestration command
   with the chosen agent and use that agent's documented trigger/manual path."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Do NOT invent user stories. Only reference US-* that exist as files
  in doc/user_stories/. If a story seems missing, flag it and skip.

- Do NOT propose a candidate that substantially duplicates any of
  the last 3 closure blocks in doc/closed_iterations.md (same tail-only rule as Phase 2).

- Do NOT write an OUTCOME or DoD without a numeric metric or a
  concrete testable checkpoint (pytest command, script exit code,
  file existence check).

- Do NOT run generate_orchestration_prompt.md automatically **unless** the session started from `python scripts/workflow.py --skip-review` (или агенту явно передан расширенный `next_hint` с этим флагом): после Phase 7 выполни повторный вызов роутера как указано в hint (`… --skip-review --exec`) — см. [`workflow_router.md`](./workflow_router.md).
  Planning and execution are separate steps by design — otherwise the user must
  review the written contract before orchestration begins.

- Token budget суммарно по фазам: см. [`_common_rules.md`](_common_rules.md). If the
  candidate pool requires reading too many US files, reduce MAX_CANDIDATES and report why.

- If all candidates fail preflight (BLOCK on check_readset):
  stop and report "blocker: no candidate has a token-safe read-set.
  Fix read-set hints in token_safety_registry.json first."

- Never modify doc/cjm.md, doc/user_stories.md, doc/future_roadmap.md
  in this flow. They are read-only sources for planning.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (what the user sees)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Verification line:
     "Backlog empty — proceeding with plan-next."
2. Comparison table (Phase 6).
3. N contract blocks (one per candidate), markdown-ready.
4. Interactive prompt (accept / modify / refine / abort).
5. After accept: backlog_registry.yaml + regenerated tasklist.md diff summary + next-step hint.
```

---

## Сценарии использования

### Сценарий A: предыдущий пакет только что закрыт

Разработчик завершил `epoch-answer-quality-eval`, CI зелёный, в [`backlog_registry.yaml`](../backlog_registry.yaml) нет `ready`/`wip` пакетов.

```
Прочитай doc/team_workflow/generate_plan_next_prompt.md
```

Агент предложит 3 кандидата с учётом того, что только что закрыто. Пользователь выбирает, агент пишет контракт в [`backlog_registry.yaml`](../backlog_registry.yaml) и регенерирует [`tasklist.md`](../tasklist.md). Далее — [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md) как обычно.

### Сценарий B: один focus area

```
Прочитай doc/team_workflow/generate_plan_next_prompt.md
FOCUS_CJM: 7
MAX_CANDIDATES: 2
```

Агент ограничится CJM moment #7 (Day-2 retention). Полезно, когда команда хочет закрыть конкретный gap.

### Сценарий C: нет подходящих кандидатов

Все кандидаты упираются в BLOCK на `check_readset.py`. Агент остановится и укажет причину (обычно — крупные модули без записи в `token_safety_registry.json`). Это blocker не уровня планирования, а уровня инфраструктуры — его чинят отдельно.

---

## Связанные файлы

- [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md) — следующий шаг после accept
- [`generate_resume_prompt.md`](./generate_resume_prompt.md) — когда работа по PACKAGE_ID уже ведётся
- [`generate_breakthrough_ideation_prompt.md`](./generate_breakthrough_ideation_prompt.md) — при блокере Phase 3: опционально `MODE=CANDIDATE_TABLE`, затем ideation по `TARGET`; не пишет реестр до решения человека
- [`product_owner_plan_package_prompt.md`](./product_owner_plan_package_prompt.md) — минимальный ручной путь после блокера Phase 3 (один package proposal)
- [`doc/prompts_usage_guide.md`](../prompts_usage_guide.md) — матрица сценариев PO и анти-тупик
- [`doc/backlog_registry.yaml`](../backlog_registry.yaml) — SSoT и destination для принятого контракта
- [`doc/tasklist.md`](../tasklist.md) — производный weekly view после sync
- [`doc/cjm.md`](../cjm.md) — источник moments of truth
- [`doc/user_stories.md`](../user_stories.md) — shortlist и индекс US-*
- [`doc/future_roadmap.md`](../future_roadmap.md) — долгосрочная стратегия
- [`doc/closed_iterations.md`](../closed_iterations.md) — что уже закрыто (анти-дубликат)
- [`scripts/check_readset.py`](../../scripts/check_readset.py) — preflight token guard
- [`scripts/lint_agent_prompts.py`](../../scripts/lint_agent_prompts.py) — валидация промптов
