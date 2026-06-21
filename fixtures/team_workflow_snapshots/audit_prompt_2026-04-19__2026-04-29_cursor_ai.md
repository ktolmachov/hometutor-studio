# Closed Packages Audit Prompt — generated for Cursor AI

**Period:** `2026-04-19..2026-04-29` (`2026-04-19` .. `2026-04-29`)  
**Depth:** `dod_replay` | **Scope:** `closed` | **Agent:** `cursor_ai`

**Counts:** Registry packages: **85** | CI headings (unique): **74** | Pre-check rows with CI/US gap: **60**  
**ORPHAN_IN_CI:** none

---

## TOOL_SYNTAX (from `agent_adapter_cursor_ai.md`)

**READ_FILE:** `@path` or `@path:start-end` in Composer; semantic `@codebase` только при необходимости.

**RUN_CMD:** встроенный терминал Cursor (`Ctrl+` \`): команды как в примерах ниже; интерпретатор `.\.venv\Scripts\python.exe`.

---

```text
╔══════════════════════════════════════════════════════════════╗
║  CLOSED PACKAGES AUDIT — 2026-04-19..2026-04-29  [2026-04-19..2026-04-29]  [cursor_ai]            ║
║  Depth: dod_replay | Scope: closed                              ║
╚══════════════════════════════════════════════════════════════╝

This is a self-contained audit prompt. Do not re-read the generator.
Run steps A → D in order. Process one package at a time.

── PACKAGE LIST (from registry + index cross-check) ────────────
| # | Package ID | Title (truncated) | Registry | CI Entries | US Sync | Pre |
|---|------------|-------------------|----------|------------|---------|-----|

| 1 | `epoch-17-1-ux-tail` | UX-tail polish: deterministic primary CTA on entry surfaces and explicit QA→Tuto | OK | OK | MISS | WARN |
| 2 | `epoch-5min-loop-polish` | Stabilize the 5-minute learner flow answer -> micro-quiz -> feedback/explanation | OK | OK | MISS | WARN |
| 3 | `epoch-adaptive-plan-today` | Plan for today after the first session, connecting first value to a durable lear | OK | OK | MISS | WARN |
| 4 | `epoch-adversarial-eval-harness` | adversarial_eval.py runs deterministic negative/positive cases for command guard | OK | MISSING | MISS | WARN |
| 5 | `epoch-agent-evals-layer` | Control-plane evals cover policies, routing, gates, and observability through de | OK | MISSING | MISS | WARN |
| 6 | `epoch-answer-quality-baseline` | Eval pipeline + baseline score + CI gate; scripts/run_aqe.py; результат ≥ 80% gr | OK | OK | OK | PASS |
| 7 | `epoch-answer-quality-eval` | CI-visible answer-quality gate for First Answer trust moment (golden dataset + t | OK | OK | MISS | WARN |
| 8 | `epoch-aqe-corpus-choice` | Выбор и формирование golden set для AQE: synthetic corpus или real-data; AQE-R r | OK | OK | MISS | WARN |
| 9 | `epoch-architecture-review-baseline` | Query service boundary остается разделенной на knowledge, RAG assembly и fallbac | OK | OK | MISS | WARN |
| 10 | `epoch-autonomous-observability-dashboard` | pipeline_status.py --json aggregates logs/autonomous_runs into runs/stats includ | OK | MISSING | MISS | WARN |
| 11 | `epoch-backup-benchmark-close` | tests/test_backup_benchmark_acceptance.py` — US-10.1: `import_full_sync_bundle() | OK | OK | OK | PASS |
| 12 | `epoch-citations-trust-close` | tests/test_citations_trust.py` — acceptance-level тесты: anchor IDs от `linkify_ | OK | OK | MISS | WARN |
| 13 | `epoch-cjm-us-frontmatter` | Structured pain→moment→status map + US frontmatter index for plan_next candidate | OK | OK | MISS | WARN |
| 14 | `epoch-concept-remediation-step` | Tutor предлагает конкретные шаги исправления по каждому concept gap в плане. | OK | OK | OK | PASS |
| 15 | `epoch-context-cart-mvp` | Token-safe context assembly for plan/orchestration/verify flows; bridge between  | OK | OK | MISS | WARN |
| 16 | `epoch-control-plane-v3-core` | pipeline_state.json + result.json в logs/autonomous_runs/<run_id>/; get_or_creat | OK | OK | MISS | WARN |
| 17 | `epoch-course-workspace-ab` | Course Workspace: activate folder as course, focus queries, course activation in | OK | OK | MISS | WARN |
| 18 | `epoch-course-workspace-d` | Course Workspace: generate flashcards from document, get course learning plan | OK | OK | MISS | WARN |
| 19 | `epoch-course-workspace-e` | Course Workspace: review due flashcards by SM-2, generate flashcards for course | OK | OK | MISS | WARN |
| 20 | `epoch-course-workspace-f` | Course Workspace: transition from hard card to tutor, see course progress in das | OK | OK | MISS | WARN |
| 21 | `epoch-demo` | smoke package scaffolding for post-agent CLI verification | OK | OK | MISS | WARN |
| 22 | `epoch-demo-pipeline-hardening` | Demo pipeline hardening: narrative ordering, strict validation commands, auto-ch | OK | OK | MISS | WARN |
| 23 | `epoch-demo-scenario-03-tutor` | Demo показывает переход Answer → Tutor за один клик с сохранением контекста темы | OK | OK | MISS | WARN |
| 24 | `epoch-demo-scenario-04-quiz` | Demo показывает formative assessment с немедленной обратной связью — не AI-чат,  | OK | OK | MISS | WARN |
| 25 | `epoch-demo-scenario-06-srs` | Demo показывает: система знает что студент забывает и напоминает в нужный момент | OK | OK | OK | PASS |
| 26 | `epoch-demo-scenario-07-progress` | Demo показывает: dashboard не декоративный — каждая цифра превращается в actiona | OK | OK | MISS | WARN |
| 27 | `epoch-demo-scenario-08-trust` | Demo доказывает anti-hallucination: каждый тезис → фрагмент → строка в файле. Lo | OK | OK | OK | PASS |
| 28 | `epoch-demo-scenario-09-learning-plan` | Demo показывает: AI не отвечает — AI ведёт по учебному пути с персональным плано | OK | OK | MISS | WARN |
| 29 | `epoch-doc-ingestion-split-arch-sync` | Синхронизировать описание модуля ingestion: doc/architecture.md (разделы с app/i | OK | OK | MISS | WARN |
| 30 | `epoch-e30-a1-cockpit-scaffold` | Phase A: `app/ui/course_cockpit.py` — 3-column layout, `RAG_COURSE_COCKPIT_V2`,  | OK | OK | OK | PASS |
| 31 | `epoch-e30-a2-cockpit-rotator` | Phase A: `app/ui/cockpit_rotator.py` — interleaved rotation, transitions, тригге | OK | OK | OK | PASS |
| 32 | `epoch-e30-b1-graduation-overlay` | Phase B: `app/ui/graduation_overlay.py` — concept graduation ceremony, Path Map  | OK | OK | OK | PASS |
| 33 | `epoch-e30-b2-daily-briefing` | Phase B: `app/ui/daily_briefing.py` — morning brief + evening debrief, gap parki | OK | OK | OK | PASS |
| 34 | `epoch-e30-c1-diagnostic` | Phase C: `app/diagnostic_service.py` — pre-flight adaptive quiz, `diagnostic.v1` | OK | OK | OK | PASS |
| 35 | `epoch-e30-c2-pace-engine` | Phase C: `app/pace_engine.py` — Sprint/Steady/Deep, rolling pace, `plan.v2` с pa | OK | OK | OK | PASS |
| 36 | `epoch-e30-d1-smart-resume` | Phase D: `app/warmup_planner.py` — pause tiers, soft-recovery overdue, `warmup.v | OK | OK | OK | PASS |
| 37 | `epoch-e30-d2-focus-mode` | Phase D: `app/ui/focus_mode.py` — Pomodoro 25/5, distraction-lock, 4-cycle deep- | OK | OK | OK | PASS |
| 38 | `epoch-e30-e1-course-graduation` | Phase E: `app/course_graduation.py` — course graduation ceremony, PDF certificat | OK | OK | OK | PASS |
| 39 | `epoch-e30-idea-1-daily-runway` | Ideation stage7: дневная микро-цель (N шагов / M минут) + streak chip в `course` | OK | OK | OK | PASS |
| 40 | `epoch-e30-idea-2-retrieval-gates` | Ideation stage7: 1–3 retrieval-вопроса между K-модулями плана (interleaving с пр | OK | OK | OK | PASS |
| 41 | `epoch-env-required-vars` | UI shows missing-env warning | OK | OK | MISS | WARN |
| 42 | `epoch-failure-classifier` | Exit-code classes are loaded from policies/failure_classes.yaml and written into | OK | MISSING | MISS | WARN |
| 43 | `epoch-first-answer-examples` | Hero-экран показывает 3 кликабельных example questions, сгенерированных по содер | OK | OK | OK | PASS |
| 44 | `epoch-flashcard-deck-mgmt` | Learner может редактировать/удалять карточки и колоды из UI; CTA «Создать карточ | OK | OK | MISS | WARN |
| 45 | `epoch-flashcard-export-upload` | Экспорт колоды в Anki .apkg; загрузка PDF/text файла из UI для генерации карточе | OK | OK | MISS | WARN |
| 46 | `epoch-flashcard-export-upload-r2` | Экспорт выбранной колоды в `.apkg` доступен из UI; загрузка файла из UI создаёт  | OK | OK | MISS | WARN |
| 47 | `epoch-hitl-approval-protocol` | hitl_approval.py enforces approval-required actions from policies/hitl_approval_ | OK | MISSING | MISS | WARN |
| 48 | `epoch-ingest-first-index-progress` | CLI первой индексации выводит стабильный прогресс: processed/total и текущий фай | OK | OK | OK | PASS |
| 49 | `epoch-ingestion-loader-extraction` | Выделить orchestration загрузчика из app/ingestion.py в app/ingestion_loader.py; | OK | OK | MISS | WARN |
| 50 | `epoch-inline-citations-first-answer` | Inline citations in first answer | OK | OK | MISS | WARN |
| 51 | `epoch-latency-slo-gate` | p95 latency CI gate интегрирован в pre-merge workflow; порог из tests/eval/thres | OK | OK | MISS | WARN |
| 52 | `epoch-llm-regression-baseline` | Full LLM regression suite с golden baselines; nightly CI job; нет silent regress | OK | OK | OK | PASS |
| 53 | `epoch-mastery-after-reindex` | Preserve mastery and show an explicit profile-updated badge after reindex. | OK | OK | MISS | WARN |
| 54 | `epoch-mastery-gap-routing` | Orchestrator маршрутизирует следующую тему исходя из реального mastery/gap, не r | OK | OK | OK | PASS |
| 55 | `epoch-micro-quiz-feedback-tail` | Submit feedback tail ships status/explanation/one CTA contract for micro-quiz an | OK | OK | MISS | WARN |
| 56 | `epoch-nonstop-wave-policy` | nonstop_wave_policy.py enforces safe non-stop wave limits using policies/nonstop | OK | MISSING | MISS | WARN |
| 57 | `epoch-pipeline-concurrency-locks` | pipeline_lock.py and current_task locks prevent concurrent package/task mutation | OK | MISSING | MISS | WARN |
| 58 | `epoch-plan-diff-ux` | Expander «Что изменилось» в Adaptive Plan card показывает diff added/removed con | OK | OK | MISS | WARN |
| 59 | `epoch-plan-next-candidate-seed` | Планировочный цикл не блокируется drift-ошибками на старте (`check_backlog_drift | OK | OK | MISS | WARN |
| 60 | `epoch-prompt-routing-registry` | Prompt route selection is resolved through policies/prompts_registry.yaml and pr | OK | MISSING | MISS | WARN |
| 61 | `epoch-qa-tutor-handoff` | One-click handoff from Quick Answer to Tutor with preserved continuity context. | OK | OK | MISS | WARN |
| 62 | `epoch-quality-gates-matrix` | quality_gates.run_all() exposes a shared gate matrix with blocker/shadow summari | OK | MISSING | MISS | WARN |
| 63 | `epoch-query-service-assembly` | Query flow разбит на knowledge lookup, rag assembly и fallback assembly без изме | OK | OK | MISS | WARN |
| 64 | `epoch-query-service-assembly-v2` | Query service assembly path remains stable for knowledge and fallback branches. | OK | OK | MISS | WARN |
| 65 | `epoch-quiz-hint-on-fail` | Hint instead of strict fail in micro-quiz, reducing drop-off after incorrect ans | OK | OK | MISS | WARN |
| 66 | `epoch-reindex-mastery-guard` | Reindex mastery guard: mastery and profile preserved after reindex | OK | OK | MISS | WARN |
| 67 | `epoch-reindex-quiz-close` | tests/test_reindex_quiz_acceptance.py` — US-2.2: `plan_partial_reindex` возвраща | OK | OK | MISS | WARN |
| 68 | `epoch-router-accuracy-baseline` | Router accuracy baseline воспроизводимо считается на `eval_data/tutor_regression | OK | OK | MISS | WARN |
| 69 | `epoch-skills-jit-router` | skills_router.py recommends JIT skills from policies/skills_router.yaml by path  | OK | MISSING | MISS | WARN |
| 70 | `epoch-srs-plan-close` | tests/test_srs_recovery_plan.py` — US-7.2: `defer_due_flashcards_for_recovery` п | OK | OK | MISS | WARN |
| 71 | `epoch-srs-priority-queue` | SRS priority queue: learner sees due reviews with priorities, not flat 50+ list | OK | OK | MISS | WARN |
| 72 | `epoch-srs-priority-reason` | В top-priority due блоке показывается краткая причина приоритета (`давно не повт | OK | OK | MISS | WARN |
| 73 | `epoch-sync-multidevice` | Multi-device parity: экспорт/импорт bundle + merge-конфликт policy | OK | OK | MISS | WARN |
| 74 | `epoch-sync-restore-wizard` | Restore wizard в Settings: загрузка файла, валидация sync_version, preview row c | OK | OK | MISS | WARN |
| 75 | `epoch-thin-current-task` | Large GUI tasks spill into doc/context_pack.md while doc/current_task.md remains | OK | MISSING | MISS | WARN |
| 76 | `epoch-tour-demo-doc-refresh` | Quickstart demo обновлён: добавлен вводный раздел про in-app interactive tour, п | OK | OK | OK | PASS |
| 77 | `epoch-tour-persistence-ch2-5` | Guide-runtime сохраняет/восстанавливает прогресс и проводит пользователя через г | OK | OK | OK | PASS |
| 78 | `epoch-tour-scenarios-10-14` | Добавлены и зелёные в demo pipeline сценарии 10–14: day-2 resume, Anki export, q | OK | OK | OK | PASS |
| 79 | `epoch-tour-skeleton-ch1` | Skeleton интерактивного тура: state, overlay (CSS-only), глава 1 «Первый ответ»  | OK | OK | OK | PASS |
| 80 | `epoch-truth-sync` | scripts/rebuild_user_stories_index.py` пересоздаёт `doc/user_stories_index.json` | OK | OK | OK | PASS |
| 81 | `epoch-tutor-transparency` | Learner-facing explanation of tutor orchestration decisions without exposing raw | OK | OK | MISS | WARN |
| 82 | `epoch-ui-main-split` | app/ui/main.py` becomes a lightweight router entrypoint under 300 lines. | OK | OK | MISS | WARN |
| 83 | `epoch-unified-context-layer` | Persistent topic / mastery% / due / streak strip across all modes. | OK | OK | MISS | WARN |
| 84 | `epoch-us7-3-resume-card` | Day-2 resume card: learner returns to the last useful learning point without hun | OK | OK | MISS | WARN |
| 85 | `epoch-wave-contract` | doc/backlog_registry.yaml` schema bumped to v2 с блоком `waves:` (4 волны) и опц | OK | OK | MISS | WARN |

────────────────────────────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP A — INDEX CONSISTENCY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package `<id>` in the PACKAGE LIST above:

A.1 Registry entry:
  Verify `doc/backlog_registry.yaml` contains:
    status: closed
    last_review or closed_date falls within [2026-04-19, 2026-04-29] (see generator Phase A2)
  → Registry: OK | MISSING

A.2 closed_iterations.md entry:
  Expect a closure heading `### <id> — YYYY-MM-DD` with date in [2026-04-19, 2026-04-29]
  (see generator Step A2.2). Supplement: `grep -n "<id>" doc/closed_iterations.md`
  "Индекс Эпох" rows refer to epoch files (E29…), not package IDs — do not use them as the only CI check.
  → CI Index: OK | MISSING | ORPHAN

A.3 User story consistency:
  ```powershell
  .\.venv\Scripts\python.exe -c "import json; data=json.load(open('doc/user_stories_index.json',encoding='utf-8')); stories=data if isinstance(data,list) else (data.get('items') or data.get('stories',[])); pkg='<id>'; relevant=[s for s in stories if s.get('covered_by')==pkg]; print('\n'.join('%s %s %s'%((s.get('us_id',s.get('id')),s.get('status'),s.get('closed_date',''))) for s in relevant))"
  ```
  For each US with covered_by == `<id>`:
    status must be 'closed' AND closed_date must fall within [2026-04-19, 2026-04-29]
  → US Index: OK | MISMATCH (list affected US IDs)

A.4 CJM consistency:
  `grep -n "<id>\|<US-IDs from A.3>" doc/cjm.md | Select-Object -First 20`
  Check that corresponding MoT is marked completed (✅).
  → CJM: OK | INCOMPLETE | NOT_FOUND

Record result: A_RESULT[<id>] = {registry, ci_index, us_index, cjm}

If ANY check MISSING/MISMATCH for `<id>`:
  → Mark INDEX_FAIL[<id>] = true
  → Note specific failure reason
  → Proceed to Step C for this package (skip Step B for it)
Else:
  → INDEX_PASS[<id>] = true
  → Proceed to Step B (if DEPTH == dod_replay) or skip to Step D

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP B — DoD REPLAY  [skip entirely if DEPTH == index_only]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package `<id>` where INDEX_PASS[<id>] == true:

B.1 Read exit_artifact path from registry:
  ```powershell
  .\.venv\Scripts\python.exe -c "import yaml; data=yaml.safe_load(open('doc/backlog_registry.yaml',encoding='utf-8')); pkgs=data.get('items',data.get('packages',[])); pkg=next((p for p in pkgs if p['id']=='<id>'), None); print(pkg.get('exit_artifact','') if pkg else 'NOT_FOUND')"
  ```
  If exit_artifact is empty or file missing → DOD_RESULT[<id>] = STALE; skip B.2–B.4

B.2 Read architect contract (DoD commands only — do NOT full-read):
  `Get-Content archive/team_artifacts/<id>/3_architect_contract.md -TotalCount 80`
  OR `Select-String -Path archive/team_artifacts/<id>/3_architect_contract.md -Pattern 'DoD|Definition of Done|dod_commands' -Context 0,5`
  Extract: DOD_COMMANDS = list of shell commands to run

  TOKEN GUARD: if contract > 300 lines, read only sections matching
  "DoD|Definition of Done|Acceptance|Commands" via Select-String/grep.

B.3 Run DoD commands:
  For each command in DOD_COMMANDS:
    Execute command (adapt paths for Windows if needed).
    Record: exit code, stdout/stderr summary (≤ 10 lines).
  NEVER assume result — execute every command.
  NEVER skip a command because "it probably still passes".

B.4 Run regression bundle:
  ```powershell
  .\.venv\Scripts\python.exe -c "import re; content=open('doc/agent_workflow_test_bundles.md',encoding='utf-8').read(); pattern=r'(?i)## .*'+re.escape('<id>')+r'.*?\n(.*?)\n(?=^##|\Z)'; import re as R; m=R.search(pattern, content, R.M|R.S); print((m.group(1)[:500]) if m else 'NO_BUNDLE_FOUND')"
  ```
  If bundle found: run bundle commands.
  If NO_BUNDLE_FOUND: run nearest scope bundle from `doc/team_workflow/tester.md` Промпт 2.

B.5 Determine DoD verdict:
  ALL commands exit 0 AND all assertions pass → DOD_RESULT[<id>] = PASS
  Any command non-zero OR assertion failed    → DOD_RESULT[<id>] = FAIL (record reason)
  exit_artifact missing or commands not found → DOD_RESULT[<id>] = STALE

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
  Edit `doc/backlog_registry.yaml` — for entry with id == `<id>`:
    status: closed  →  status: ready
    Add field:  re_entry_condition: "audit $TODAY: $REASON"
    Update:     last_review: $TODAY

C.2 closed_iterations.md:
  In "Индекс Эпох" section: find and REMOVE the line containing `<id>`.
  In "Recent" section: if `<id>` appears, add inline: ⚠️ REOPENED $TODAY
  DO NOT delete the Goal/Delivered block — preserve history.

C.3 user_stories_index.json:
  For each US where covered_by == `<id>` AND closed_date ∈ [2026-04-19, 2026-04-29]:
    status: closed  →  status: ready
    Remove closed_date field (set to null or delete key)
  After editing, run:
    `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync`
  This regenerates `doc/tasklist.md` and other derived files.

C.4 user_stories/<US>.md frontmatter sync:
  For each affected US from C.3:
    `Get-Content doc/user_stories/<US>.md -TotalCount 20`
    If frontmatter has: status: closed  →  status: ready
    If frontmatter has: closed_date     →  remove or clear it
    Write back the updated frontmatter only (do not touch body).

C.5 cjm.md:
  US_IDS = list of US IDs from C.3
  `grep -n "<id>\|<US_IDS joined by \|>" doc/cjm.md | Select-Object -First 20`
  For each matching MoT marked ✅:
    Replace ✅ with 🔁 reopened $TODAY: `<id>`
  If no match found: add note to audit report (CJM_NOT_MATCHED).

C.6 changelog.md — APPEND ONLY (never rewrite):
  Append to `doc/changelog.md`:
    ## Reopened: `<id>` ($TODAY)
    - Reason: $REASON
    - Affected US: <US_IDS>
    - Action: status closed → ready; removed from closed_iterations index
  DO NOT edit existing changelog entries.

C.7 tasklist.md — derived file:
  Already regenerated in C.3 via backlog_registry_lint.py.
  Verify: `Select-String -Path doc/tasklist.md -Pattern "<id>"` confirms entry is present as ready.

C.8 Git commit (one per package):
  git add doc/backlog_registry.yaml doc/closed_iterations.md \
          doc/user_stories_index.json doc/changelog.md \
          doc/tasklist.md doc/cjm.md
  git add doc/user_stories/ -- <affected US files>
  git commit -m "audit(2026-04-19__2026-04-29): reopen <id> — $REASON"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP D — FINAL AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Print structured markdown report:

## Closed Packages Audit — 2026-04-19..2026-04-29 (2026-04-19 .. 2026-04-29)

| Package | Index Sync | DoD Replay | Verdict | Action |
|---------|:----------:|:----------:|:-------:|--------|
| `<id>`    | ✅ OK      | ✅ PASS    | PASS    | none   |
| `<id>`    | ❌ CI MISS | skipped    | FAIL    | reopened |
| `<id>`    | ✅ OK      | ⚠️ STALE  | STALE   | reopened |

**Summary:** N total | N PASS | N FAIL | N STALE | N REOPENED

### Reopened Packages

| Package | Reason | Affected US | CJM |
|---------|--------|-------------|-----|
| `<id>`    | ...    | US-123, ... | 🔁  |

### Index Desyncs (not causing revert)
<list packages where only WARN-level issues found, no revert needed>

### Next Actions
- Re-run orchestration for reopened packages via `generate_orchestration_prompt.md`
- Confirm CJM_NOT_MATCHED entries manually if any

Save report to: `archive/team_artifacts/audit_2026-04-19__2026-04-29/audit_report.md`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- DO NOT write any code or fix any bugs during the audit.
  The audit is read-only except for revert operations in Step C.
- DO NOT run Step C without confirmed FAIL or STALE from Step A or B.
  INDEX_WARN alone (partial desync with no clear cause) → flag in report only.
- ATOMICITY: one package per transaction. Never batch-revert.
  If the agent crashes mid-Step-C → finish Step C for the in-progress package
  before anything else in the next session.
- Token budget: ≤ 20 000 tokens per package (Steps A+B combined).
  For large contracts: read DoD section only (grep), not full file.
- For DoD replay (Step B): NEVER assume a command passes — run it.
  "Probably still works" is not a PASS verdict.
- CJM grep uses US-IDs (from user_stories_index.json) not pkg-IDs directly,
  because CJM references US milestones. pkg-ID grep is supplementary.
- Run `python scripts/check_readset.py` before each package's Step B
  to confirm read-set is within token budget.
- After all packages processed: run `python scripts/backlog_registry_lint.py`
  with no flags (schema check). Must exit 0.
```
