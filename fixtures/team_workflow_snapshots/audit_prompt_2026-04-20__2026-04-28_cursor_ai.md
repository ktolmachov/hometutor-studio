╔══════════════════════════════════════════════════════════════╗
║ CLOSED PACKAGES AUDIT — 2026-04-20..2026-04-28  [2026-04-20 .. 2026-04-28]  [cursor_ai]
║ Depth: index_only | Scope: closed,wip
╚══════════════════════════════════════════════════════════════╝

> **Генератор:** `doc/team_workflow/generate_audit_closed_packages_prompt.md` Phase A3.
> В запросе указаны оба режима dod_replay и index_only; для исполнения Step B принят **index_only** (перезапуск с `DEPTH=dod_replay` включает DoD replay).

This is a self-contained audit prompt. Do not re-read the generator.
Run steps A → D in order. Process one package at a time.

**Tooling (Cursor AI):**
- Читать файлы: `@путь` (напр. `@doc/backlog_registry.yaml`, `@app/foo.py:10-90`)
- Команды: встроенный терминал (pytest, grep, git, python)
- Записывать: правки через агент/IDE («Save to: …»)

────────────────────────────────────────────────────────────────

Pre-Audit Index Sync: `2026-04-20..2026-04-28` (**2026-04-20 .. 2026-04-28**)

| Метрика | Значение |
|---------|----------|
| Пакеты в backlog_registry (SCOPE `closed,wip`) | **72** |
| Уникальных `###` заголовков в closed_iterations за период | **72** |
| Совпадение Registry ↔ CI (по спискам) | **0 orphan CI**, **0 без CI-heading** |
| Пакеты с хотя бы одним US в `user_stories_index` за окно дат | **20** |

Табличный pre-sync по каждому пакету — ниже (колонка **Pre-check**: PASS если CI и US есть; WARN если только US пропускается там, где историй нет для пакета в окне дат).

── PACKAGE LIST (from generator Phase A2) ────────────────────────

| # | Package ID | Title | Registry | CI Entries | US Index | Pre-check |
|---|---|---|:---:|:---:|:---:|:---:|
| 1 | `epoch-17-1-ux-tail` | UX-tail polish: deterministic primary CTA on entry surf... | OK | OK | MISS | WARN |
| 2 | `epoch-5min-loop-polish` | Stabilize the 5-minute learner flow answer -> micro-qui... | OK | OK | MISS | WARN |
| 3 | `epoch-adaptive-plan-today` | Plan for today after the first session, connecting firs... | OK | OK | MISS | WARN |
| 4 | `epoch-answer-quality-baseline` | Eval pipeline + baseline score + CI gate; scripts/run_a... | OK | OK | OK | PASS |
| 5 | `epoch-answer-quality-eval` | CI-visible answer-quality gate for First Answer trust m... | OK | OK | MISS | WARN |
| 6 | `epoch-aqe-corpus-choice` | Выбор и формирование golden set для AQE: synthetic corp... | OK | OK | MISS | WARN |
| 7 | `epoch-architecture-review-baseline` | Query service boundary остается разделенной на knowledg... | OK | OK | MISS | WARN |
| 8 | `epoch-backup-benchmark-close` | tests/test_backup_benchmark_acceptance.py` — US-10.1: `... | OK | OK | OK | PASS |
| 9 | `epoch-citations-trust-close` | tests/test_citations_trust.py` — acceptance-level тесты... | OK | OK | MISS | WARN |
| 10 | `epoch-cjm-us-frontmatter` | Structured pain→moment→status map + US frontmatter inde... | OK | OK | MISS | WARN |
| 11 | `epoch-concept-remediation-step` | Tutor предлагает конкретные шаги исправления по каждому... | OK | OK | OK | PASS |
| 12 | `epoch-context-cart-mvp` | Token-safe context assembly for plan/orchestration/veri... | OK | OK | MISS | WARN |
| 13 | `epoch-control-plane-v3-core` | pipeline_state.json + result.json в logs/autonomous_run... | OK | OK | MISS | WARN |
| 14 | `epoch-course-workspace-ab` | Course Workspace: activate folder as course, focus quer... | OK | OK | MISS | WARN |
| 15 | `epoch-course-workspace-d` | Course Workspace: generate flashcards from document, ge... | OK | OK | MISS | WARN |
| 16 | `epoch-course-workspace-e` | Course Workspace: review due flashcards by SM-2, genera... | OK | OK | MISS | WARN |
| 17 | `epoch-course-workspace-f` | Course Workspace: transition from hard card to tutor, s... | OK | OK | MISS | WARN |
| 18 | `epoch-demo` | smoke package scaffolding for post-agent CLI verification | OK | OK | MISS | WARN |
| 19 | `epoch-demo-pipeline-hardening` | Demo pipeline hardening: narrative ordering, strict val... | OK | OK | MISS | WARN |
| 20 | `epoch-demo-scenario-03-tutor` | Demo показывает переход Answer → Tutor за один клик с с... | OK | OK | MISS | WARN |
| 21 | `epoch-demo-scenario-04-quiz` | Demo показывает formative assessment с немедленной обра... | OK | OK | MISS | WARN |
| 22 | `epoch-demo-scenario-06-srs` | Demo показывает: система знает что студент забывает и н... | OK | OK | OK | PASS |
| 23 | `epoch-demo-scenario-07-progress` | Demo показывает: dashboard не декоративный — каждая циф... | OK | OK | MISS | WARN |
| 24 | `epoch-demo-scenario-08-trust` | Demo доказывает anti-hallucination: каждый тезис → фраг... | OK | OK | OK | PASS |
| 25 | `epoch-demo-scenario-09-learning-plan` | Demo показывает: AI не отвечает — AI ведёт по учебному ... | OK | OK | MISS | WARN |
| 26 | `epoch-e30-a1-cockpit-scaffold` | Phase A: `app/ui/course_cockpit.py` — 3-column layout, ... | OK | OK | MISS | WARN |
| 27 | `epoch-e30-a2-cockpit-rotator` | Phase A: `app/ui/cockpit_rotator.py` — interleaved rota... | OK | OK | MISS | WARN |
| 28 | `epoch-e30-b1-graduation-overlay` | Phase B: `app/ui/graduation_overlay.py` — concept gradu... | OK | OK | MISS | WARN |
| 29 | `epoch-e30-b2-daily-briefing` | Phase B: `app/ui/daily_briefing.py` — morning brief + e... | OK | OK | MISS | WARN |
| 30 | `epoch-e30-c1-diagnostic` | Phase C: `app/diagnostic_service.py` — pre-flight adapt... | OK | OK | MISS | WARN |
| 31 | `epoch-e30-c2-pace-engine` | Phase C: `app/pace_engine.py` — Sprint/Steady/Deep, rol... | OK | OK | OK | PASS |
| 32 | `epoch-e30-d1-smart-resume` | Phase D: `app/warmup_planner.py` — pause tiers, soft-re... | OK | OK | OK | PASS |
| 33 | `epoch-e30-d2-focus-mode` | Phase D: `app/ui/focus_mode.py` — Pomodoro 25/5, distra... | OK | OK | OK | PASS |
| 34 | `epoch-e30-e1-course-graduation` | Phase E: `app/course_graduation.py` — course graduation... | OK | OK | OK | PASS |
| 35 | `epoch-e30-idea-1-daily-runway` | Ideation stage7: дневная микро-цель (N шагов / M минут)... | OK | OK | OK | PASS |
| 36 | `epoch-e30-idea-2-retrieval-gates` | Ideation stage7: 1–3 retrieval-вопроса между K-модулями... | OK | OK | OK | PASS |
| 37 | `epoch-env-required-vars` | UI shows missing-env warning | OK | OK | MISS | WARN |
| 38 | `epoch-first-answer-examples` | Hero-экран показывает 3 кликабельных example questions,... | OK | OK | OK | PASS |
| 39 | `epoch-flashcard-deck-mgmt` | Learner может редактировать/удалять карточки и колоды и... | OK | OK | MISS | WARN |
| 40 | `epoch-flashcard-export-upload` | Экспорт колоды в Anki .apkg; загрузка PDF/text файла из... | OK | OK | MISS | WARN |
| 41 | `epoch-flashcard-export-upload-r2` | Экспорт выбранной колоды в `.apkg` доступен из UI; загр... | OK | OK | MISS | WARN |
| 42 | `epoch-ingest-first-index-progress` | CLI первой индексации выводит стабильный прогресс: proc... | OK | OK | OK | PASS |
| 43 | `epoch-inline-citations-first-answer` | Inline citations in first answer | OK | OK | MISS | WARN |
| 44 | `epoch-latency-slo-gate` | p95 latency CI gate интегрирован в pre-merge workflow; ... | OK | OK | MISS | WARN |
| 45 | `epoch-llm-regression-baseline` | Full LLM regression suite с golden baselines; nightly C... | OK | OK | OK | PASS |
| 46 | `epoch-mastery-after-reindex` | Preserve mastery and show an explicit profile-updated b... | OK | OK | MISS | WARN |
| 47 | `epoch-mastery-gap-routing` | Orchestrator маршрутизирует следующую тему исходя из ре... | OK | OK | OK | PASS |
| 48 | `epoch-micro-quiz-feedback-tail` | Submit feedback tail ships status/explanation/one CTA c... | OK | OK | MISS | WARN |
| 49 | `epoch-plan-diff-ux` | Expander «Что изменилось» в Adaptive Plan card показыва... | OK | OK | MISS | WARN |
| 50 | `epoch-plan-next-candidate-seed` | Планировочный цикл не блокируется drift-ошибками на ста... | OK | OK | MISS | WARN |
| 51 | `epoch-qa-tutor-handoff` | One-click handoff from Quick Answer to Tutor with prese... | OK | OK | MISS | WARN |
| 52 | `epoch-query-service-assembly` | Query flow разбит на knowledge lookup, rag assembly и f... | OK | OK | MISS | WARN |
| 53 | `epoch-query-service-assembly-v2` | Query service assembly path remains stable for knowledg... | OK | OK | MISS | WARN |
| 54 | `epoch-quiz-hint-on-fail` | Hint instead of strict fail in micro-quiz, reducing dro... | OK | OK | MISS | WARN |
| 55 | `epoch-reindex-mastery-guard` | Reindex mastery guard: mastery and profile preserved af... | OK | OK | MISS | WARN |
| 56 | `epoch-reindex-quiz-close` | tests/test_reindex_quiz_acceptance.py` — US-2.2: `plan_... | OK | OK | MISS | WARN |
| 57 | `epoch-router-accuracy-baseline` | Router accuracy baseline воспроизводимо считается на `e... | OK | OK | MISS | WARN |
| 58 | `epoch-srs-plan-close` | tests/test_srs_recovery_plan.py` — US-7.2: `defer_due_f... | OK | OK | MISS | WARN |
| 59 | `epoch-srs-priority-queue` | SRS priority queue: learner sees due reviews with prior... | OK | OK | MISS | WARN |
| 60 | `epoch-srs-priority-reason` | В top-priority due блоке показывается краткая причина п... | OK | OK | MISS | WARN |
| 61 | `epoch-sync-multidevice` | Multi-device parity: экспорт/импорт bundle + merge-конф... | OK | OK | MISS | WARN |
| 62 | `epoch-sync-restore-wizard` | Restore wizard в Settings: загрузка файла, валидация sy... | OK | OK | MISS | WARN |
| 63 | `epoch-tour-demo-doc-refresh` | Quickstart demo обновлён: добавлен вводный раздел про i... | OK | OK | OK | PASS |
| 64 | `epoch-tour-persistence-ch2-5` | Guide-runtime сохраняет/восстанавливает прогресс и пров... | OK | OK | OK | PASS |
| 65 | `epoch-tour-scenarios-10-14` | Добавлены и зелёные в demo pipeline сценарии 10–14: day... | OK | OK | OK | PASS |
| 66 | `epoch-tour-skeleton-ch1` | Skeleton интерактивного тура: state, overlay (CSS-only)... | OK | OK | OK | PASS |
| 67 | `epoch-truth-sync` | scripts/rebuild_user_stories_index.py` пересоздаёт `doc... | OK | OK | OK | PASS |
| 68 | `epoch-tutor-transparency` | Learner-facing explanation of tutor orchestration decis... | OK | OK | MISS | WARN |
| 69 | `epoch-ui-main-split` | app/ui/main.py` becomes a lightweight router entrypoint... | OK | OK | MISS | WARN |
| 70 | `epoch-unified-context-layer` | Persistent topic / mastery% / due / streak strip across... | OK | OK | MISS | WARN |
| 71 | `epoch-us7-3-resume-card` | Day-2 resume card: learner returns to the last useful l... | OK | OK | MISS | WARN |
| 72 | `epoch-wave-contract` | doc/backlog_registry.yaml` schema bumped to v2 с блоком... | OK | OK | MISS | WARN |

────────────────────────────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP A — INDEX CONSISTENCY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package `<id>` in the PACKAGE LIST above:

**A.1 Registry entry:**

Verify `doc/backlog_registry.yaml` contains:

- `status`: `closed` (или `wip` если в scope включён wip и строка есть в этом списке)
- `last_review` или `closed_date` попадают в интервал **[2026-04-20, 2026-04-28]** (см. `scripts/audit_closed_packages_helpers.py`)

→ Registry: OK | MISSING

**A.2 closed_iterations.md entry:**

Expect a closure heading ``### `<id>` — YYYY-MM-DD``` with date within **[2026-04-20, 2026-04-28]**.

Дополнительно:

```powershell
grep -n "<id>" doc/closed_iterations.md
```

→ CI Index: OK | MISSING | ORPHAN

**A.3 User story consistency:**

```powershell
.\.venv\Scripts\python.exe -c "
import json
from pathlib import Path
data = json.load(open('doc/user_stories_index.json', encoding='utf-8'))
stories = data if isinstance(data, list) else (data.get('items') or data.get('stories', []))
pkg = '<id>'
for s in stories:
    if s.get('covered_by') == pkg:
        print(s.get('us_id', s.get('id')), s.get('status'), s.get('closed_date', ''))
"
```

For each US with `covered_by == <id>`: `status` must be `closed` AND `closed_date` (если указана) должна входить в **[2026-04-20, 2026-04-28]**.

→ US Index: OK | MISMATCH

**A.4 CJM consistency:**

```powershell
grep -n "<id>" doc/cjm.md | Select-Object -First 20
```

(Pри необходимости добавить US-id из A.3 в паттерн.)

→ CJM: OK | INCOMPLETE | NOT_FOUND

Record: `A_RESULT[<id>] = {registry, ci_index, us_index, cjm}`

Если MISSING/MISMATCH — `INDEX_FAIL[<id>] = true` → переход к Step C (**без Step B**, т.к. индекс неверен).

Если только US «нет связанных строк в окне» для пакетов без связанных US — зафиксировать как WARN в отчёте, без revert по умолчанию.

Если всё ок → `INDEX_PASS` → для **DEPTH=index_only** **пропуск Step B**, сразу **Step D** по этому пакету.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP B — DoD REPLAY  [skipped — DEPTH = index_only]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Текущий режим генератора: `index_only`** — команды pytest/DoD **не выполняются** в этом прогоне.

Чтобы включить описанную ниже проверку, скопируйте этот промпт в новый чат с **`DEPTH=dod_replay`** (без index_only):

For each `<id>` with `INDEX_PASS[<id>] == true`:

**B.1–B.5:** как в § Generated Prompt аудита в `generate_audit_closed_packages_prompt.md`:
- читать `exit_artifact`, `archive/team_artifacts/<id>/3_architect_contract.md` (DoD через `head`/grep),
- выполнять все команды из DoD, regression bundle из `doc/agent_workflow_test_bundles.md` или `doc/team_workflow/tester.md`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP C — REVERT PROCEDURE  [only for INDEX_FAIL или FAIL/STALE при dod_replay]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Только если подтверждён сбой Step A или (после `dod_replay`) Step B. Атомарно по одному `<id>`.

См. шаблон C.1–C.8 в `doc/team_workflow/generate_audit_closed_packages_prompt.md` (переменные `$PERIOD_SLUG` = `2026-04-20__2026-04-28`, даты начала/конца = выше).

Commit message: `audit(2026-04-20__2026-04-28): reopen <id> — <reason>`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP D — FINAL AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Структурированный отчёт Markdown; сохранить в:

`archive/team_artifacts/audit_2026-04-20__2026-04-28/audit_report.md`

**Summary:** после **index_only** ожидается отчёт по сверке индексов; DoD столбцы — «skipped».

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Не править код и не исправлять баги в этом прогоне (кроме Step C при явном FAIL по правилам).
- Не переоткрывать пакеты при одном только WARN без подтверждённой рассинхронизации регистра/registry.
- Токены: использовать `grep`/`head` для больших файлов; см. `doc/token_safety.md`.

Report save path slug: **`audit_2026-04-20__2026-04-28`** = `audit_2026-04-20__2026-04-28`

Literal bindings for this audit:

| Key | Value |
|-----|-------|
| PERIOD | `2026-04-20..2026-04-28` |
| START_ISO | `2026-04-20` |
| END_ISO | `2026-04-28` |
| DEPTH | `index_only` |
| SCOPE | `closed,wip` |
| TARGET_AGENT | `cursor_ai` |
