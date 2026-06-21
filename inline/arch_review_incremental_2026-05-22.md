# Architecture Review — Incremental, 2026-05-22

## Pre-scan Summary

- **Baseline:** [`doc/archive/arch_review_baseline.yaml`](../doc/archive/arch_review_baseline.yaml), last_review.sha = `3795ed10`, date = 2026-05-17.
- **Incremental scope:** 59 changed `.py` files in `app/` since baseline (`git diff --name-only 3795ed10..HEAD -- 'app/*.py' 'app/**/*.py'`).
- **Regression guards:** `.venv\Scripts\python.exe scripts/arch_regression_guards.py` → **all 27 guards pass** (os.environ, sqlite delegation, llm.chat wrapper, knowledge_graph imports, prompt boundary, inline `import logging`, ADR registry, SSR module entries, line/function sizes for tracked files, etc.).
- **Baseline replay (active findings only):**
  - `AR-2026-05-11-004` (`app/ui/home_hub.py` >600L) — **persists**, file now 670L (was ~602L at first_seen).
  - `AR-2026-04-21-005` (positive-pattern note that `app/ui/resume_cards_tutor.py` is "pending a later UI split wave") — **persists** as latent debt; file remains 657L.
  - `AR-2026-04-24-009` (tutor_chat.py fan-out positive pattern, `status=new`) — **resolved**: regression guard pins fan-out at 1 import; original concern no longer applicable.
  - All other baseline findings remain `resolved` / `accepted-tech-debt` (status unchanged).

## Executive Summary

Health is good: every automated guard passes, no convention violations re-appeared, and the prompt/SQLite/LLM resilience boundaries hold. Three classes of incremental decay are worth attention before the next epoch: (1) `app/api.py` ships 8 unannotated `except Exception` blocks introduced with the new SSR/local-LLM warm-up threads (BLE001 convention drift); (2) UI split waves left ~10 new modules absent from `doc/architecture.md` Module Reference; (3) two previously-clean modules crossed the 600-line split threshold — `app/eval_service.py` (916L) and `app/ui/dashboards.py` (645L) — with `eval_service` showing four functions over the 80-line ceiling.

## Findings Table

| # | ID | Phase | Severity | Status | Finding | File(s) | Evidence (cmd → expected) | Suggested Action |
|---|----|-------|----------|--------|---------|---------|---------------------------|------------------|
| 1 | AR-2026-05-22-001 | 4 | warning | new | `app/api.py` adds 8 `except Exception` blocks (warm-up threads + lifespan) without `# noqa: BLE001 - rationale`, violating `doc/conventions_reference.md` § Обработка ошибок. | app/api.py:59, 70, 81, 92, 106, 165, 208, 225 | `(Get-ChildItem app/api.py \| Select-String 'except Exception' \| Where-Object { $_.Line -notmatch 'noqa.*BLE001' }).Count` → `8` (expected `0`) | Annotate each with `# noqa: BLE001` + short rationale; promote any silent-degrade ones to metric/log_event. |
| 2 | AR-2026-05-22-002 | 4 | warning | new | 38 unannotated `except Exception` blocks across changed-scope UI/service modules (sidebar, topics_tab_right_column, flashcards_ui, tutor_chat_*, dashboards, query_tab_answer_section, scoped_quiz, …). | app/ui/sidebar.py:119/171/178/210/247, app/ui/topics_tab_right_column.py:106/165/202/241, app/ui/flashcards_ui.py:365/437, app/ui/tutor_chat_response_render.py:132/180, app/ui/tutor_mastery_forecast_panel.py:390/471, app/ui/dashboards.py:357/585, app/ui/query_tab_answer_section.py:299/307, app/ui/resume_cards_due.py:172, app/ui/scoped_quiz.py:31, app/ui/tutor_chat_controls.py:53, app/ui/main.py:86, app/ui/offline_banner.py:13/28, app/query_service.py:712, app/quiz_service.py:293, app/index_diff.py:120/263, app/ingestion_content_state.py:121 | Repo-wide unannotated `except Exception` count = **86**; incremental-scope subset = **38**. Expected: 0 unannotated in changed-scope files. | Add `# noqa: BLE001 - <reason>` per block; extend `scripts/arch_regression_guards.py::_check_broad_exceptions_annotated` to cover these files. |
| 3 | AR-2026-05-22-003 | 2 | warning | new | `app/eval_service.py` grew to **916L** (was below 600L threshold at baseline); now hosts 4 functions >80L (max 109L). Largest non-test module change in this window. | app/eval_service.py | `(Get-Content app/eval_service.py).Count` → `916`; AST count of functions >80L → `4` | Split eval setup vs. scoring vs. compare assembly into focused modules; add line-count guard at 1000L until the split lands. |
| 4 | AR-2026-05-22-004 | 2 | warning | new | `app/ui/dashboards.py` reached **645L** with `_render_learning_progress_tab` (285L) and `_render_knowledge_graph_tab` (208L). | app/ui/dashboards.py:151, app/ui/dashboards.py:438 | `(Get-Content app/ui/dashboards.py).Count` → `645`; AST scan returns those two functions over 200L. | Extract per-tab renderers into `app/ui/dashboards_*.py` (mirror `tutor_chat_*` pattern); add line-count guard. |
| 5 | AR-2026-05-22-005 | 2 | info | persists (since 2026-05-11) | `app/ui/home_hub.py` continues to exceed 600L (now **670L**, baseline AR-2026-05-11-004). | app/ui/home_hub.py | `(Get-Content app/ui/home_hub.py).Count` → `670` | Schedule UI split similar to resume_cards/tutor_chat waves; bump `last_seen` and add guard. |
| 6 | AR-2026-05-22-006 | 2 | info | persists (since 2026-04-21) | `app/ui/resume_cards_tutor.py` still **657L** — known pending split per AR-2026-04-21-005 expected_evidence; `render_home_continue_unified` is 223L. | app/ui/resume_cards_tutor.py:132 | `(Get-Content app/ui/resume_cards_tutor.py).Count` → `657` | Continue the resume-cards UI split wave that already produced `_due` / `_smart_study` slices. |
| 7 | AR-2026-05-22-007 | 3 | warning | new | 10 new (split-wave) modules absent from `doc/architecture.md` Module Reference: smart_study_scoring, resume_cards_due/_smart_study/_tutor, query_tab_answer_section, query_tab_poll, tutor_chat_controls, topics_tab_right_column, tutor_mastery_forecast_panel, kb_fetch. | doc/architecture.md | `foreach ($m in 'smart_study_scoring','resume_cards_due','resume_cards_smart_study','resume_cards_tutor','query_tab_answer_section','query_tab_poll','tutor_chat_controls','topics_tab_right_column','tutor_mastery_forecast_panel','kb_fetch') { if ((Get-Content doc/architecture.md -Raw) -notmatch $m) { $m } }` → all 10 listed | Add one-line entries to the Module Reference; extend `_check_ssr_modules_documented` (or sibling check) with this list. |
| 8 | AR-2026-05-22-008 | 4 | info | new | `_generate_llm_explanation` in `app/ui/adaptive_plan_llm_explanation.py` is **212L** — UI module performing LLM orchestration in a single function. | app/ui/adaptive_plan_llm_explanation.py:28 | `.\.venv\Scripts\python.exe -c "import ast;t=ast.parse(open('app/ui/adaptive_plan_llm_explanation.py','rb').read());[print(n.end_lineno-n.lineno+1,n.name) for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='_generate_llm_explanation']"` → `212 _generate_llm_explanation` | Move LLM-call assembly out of the UI module (service helper); keep UI thin. |
| 9 | AR-2026-05-22-009 | 2 | info | new | `render_query_answer_section` in `app/ui/query_tab_answer_section.py` is **263L** (just-introduced module). | app/ui/query_tab_answer_section.py:48 | AST scan as above → `263 render_query_answer_section` | Decompose into per-section helpers (answer body / sources / actions). |
| 10 | AR-2026-04-24-009 | 5 | — | resolved | tutor_chat.py fan-out positive pattern; baseline noted `status=new`. Guard pins fan-out at 1; no further monitoring needed. | app/ui/tutor_chat.py | `.\.venv\Scripts\python.exe -c "import ast;f='app/ui/tutor_chat.py';t=ast.parse(open(f,'rb').read());print(len({n.module for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('app.')}))"` → `1` | Close baseline entry. |
| 11 | AR-2026-05-11-004 | 2 | — | persists | Tracked under #5 above (home_hub.py). | app/ui/home_hub.py | see #5 | bump `last_seen=2026-05-22`. |

(Findings without an "AR-2026-05-22-…" id are baseline carry-overs.)

## Baseline Update (patch for `doc/archive/arch_review_baseline.yaml`)

```yaml
last_review:
  sha: <HEAD-sha-of-current-commit>   # author: confirm via `git rev-parse HEAD`
  date: "2026-05-22"
  backlog_wave_id: wave-arch-review-incremental-2026-05-22
  report_files:
    - inline/arch_review_incremental_2026-05-22.md
  phases_completed: [1, 2, 3, 4, 5]
  phases_pending: []
  previous_sha: 3795ed10391bd20f5172890f349d1c84c905bf8d
  previous_report: D:/Downloads/plans/bright-forging-bubble.md

# Status changes for existing entries:
# - AR-2026-04-24-009: status=resolved, resolved_date="2026-05-22"
# - AR-2026-05-11-004: last_seen="2026-05-22" (still status=new/persists)

# New findings to append:
- id: AR-2026-05-22-001
  phase: 4
  severity: warning
  title: "app/api.py: 8 broad except Exception blocks without BLE001 annotation (warm-up threads + lifespan)"
  files:
    - "app/api.py:59"
    - "app/api.py:70"
    - "app/api.py:81"
    - "app/api.py:92"
    - "app/api.py:106"
    - "app/api.py:165"
    - "app/api.py:208"
    - "app/api.py:225"
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  owner: null
  target_epoch: null
  evidence_cmd: |
    (Select-String -Path app/api.py -Pattern "except Exception" | Where-Object { $_.Line -notmatch "noqa.*BLE001" }).Count
  expected_evidence: |
    8
  regression_guard: |
    Extend scripts/arch_regression_guards.py::_check_broad_exceptions_annotated to include app/api.py.

- id: AR-2026-05-22-002
  phase: 4
  severity: warning
  title: "38 broad except Exception blocks without BLE001 annotation across changed-scope UI/service modules"
  files:
    - "app/ui/sidebar.py"
    - "app/ui/topics_tab_right_column.py"
    - "app/ui/flashcards_ui.py"
    - "app/ui/tutor_chat_response_render.py"
    - "app/ui/tutor_mastery_forecast_panel.py"
    - "app/ui/dashboards.py"
    - "app/ui/query_tab_answer_section.py"
    - "app/ui/resume_cards_due.py"
    - "app/ui/scoped_quiz.py"
    - "app/ui/tutor_chat_controls.py"
    - "app/ui/main.py"
    - "app/ui/offline_banner.py"
    - "app/query_service.py:712"
    - "app/quiz_service.py:293"
    - "app/index_diff.py:120"
    - "app/index_diff.py:263"
    - "app/ingestion_content_state.py:121"
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  owner: null
  target_epoch: null
  evidence_cmd: |
    $changed = @(git diff --name-only 3795ed10391bd20f5172890f349d1c84c905bf8d..HEAD) | Where-Object { $_ -like "app/*.py" -or $_ -like "app/ui/*.py" }
    $violations = Get-ChildItem -Recurse -Path app -Filter "*.py" | Select-String -Pattern "except Exception" | Where-Object { $_.Line -notmatch "noqa.*BLE001" -and $_.Line -notmatch "^\s*#" }
    ($violations | Where-Object { $changed -contains (($_.Path -replace [regex]::Escape("$pwd\"),"") -replace "\\","/") }).Count
  expected_evidence: |
    >=38 unannotated except Exception blocks in incremental scope
  regression_guard: |
    Extend scripts/arch_regression_guards.py::_check_broad_exceptions_annotated allow-list to cover changed-scope UI/service files.

- id: AR-2026-05-22-003
  phase: 2
  severity: warning
  title: "app/eval_service.py grew to 916L and has 4 functions >80L (max 109L)"
  files: ["app/eval_service.py"]
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  owner: null
  target_epoch: null
  evidence_cmd: |
    (Get-Content app/eval_service.py).Count
  expected_evidence: |
    916
  regression_guard: |
    Add scripts/arch_regression_guards.py::_check_file_line_count("app/eval_service.py", 1000) until eval split lands.

- id: AR-2026-05-22-004
  phase: 2
  severity: warning
  title: "app/ui/dashboards.py reached 645L; _render_learning_progress_tab (285L) and _render_knowledge_graph_tab (208L) over 200L"
  files:
    - "app/ui/dashboards.py:151"
    - "app/ui/dashboards.py:438"
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  owner: null
  target_epoch: null
  evidence_cmd: |
    (Get-Content app/ui/dashboards.py).Count
  expected_evidence: |
    645
  regression_guard: |
    Add scripts/arch_regression_guards.py::_check_file_line_count("app/ui/dashboards.py", 700) + max-function check.

- id: AR-2026-05-22-005
  phase: 2
  severity: info
  title: "app/ui/home_hub.py still >600L (670L) — persists since 2026-05-11 (baseline AR-2026-05-11-004)"
  files: ["app/ui/home_hub.py"]
  first_seen: "2026-05-11"
  last_seen: "2026-05-22"
  status: persists
  regression_guard: null

- id: AR-2026-05-22-006
  phase: 2
  severity: info
  title: "app/ui/resume_cards_tutor.py still 657L (pending UI split wave)"
  files: ["app/ui/resume_cards_tutor.py:132"]
  first_seen: "2026-04-21"
  last_seen: "2026-05-22"
  status: persists
  regression_guard: null

- id: AR-2026-05-22-007
  phase: 3
  severity: warning
  title: "10 new split-wave modules absent from doc/architecture.md Module Reference"
  files:
    - "doc/architecture.md"
    - "app/smart_study_scoring.py"
    - "app/ui/resume_cards_due.py"
    - "app/ui/resume_cards_smart_study.py"
    - "app/ui/resume_cards_tutor.py"
    - "app/ui/query_tab_answer_section.py"
    - "app/ui/query_tab_poll.py"
    - "app/ui/tutor_chat_controls.py"
    - "app/ui/topics_tab_right_column.py"
    - "app/ui/tutor_mastery_forecast_panel.py"
    - "app/ui/kb_fetch.py"
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  owner: null
  target_epoch: null
  evidence_cmd: |
    $arch = Get-Content doc/architecture.md -Raw; foreach ($m in 'smart_study_scoring','resume_cards_due','resume_cards_smart_study','resume_cards_tutor','query_tab_answer_section','query_tab_poll','tutor_chat_controls','topics_tab_right_column','tutor_mastery_forecast_panel','kb_fetch') { if ($arch -notmatch $m) { $m } }
  expected_evidence: |
    All 10 names listed (i.e., none present in architecture.md).
  regression_guard: |
    Extend scripts/arch_regression_guards.py::_check_ssr_modules_documented to include the 10 new modules above.

- id: AR-2026-05-22-008
  phase: 4
  severity: info
  title: "_generate_llm_explanation in app/ui/adaptive_plan_llm_explanation.py is 212L; UI module orchestrating LLM call"
  files: ["app/ui/adaptive_plan_llm_explanation.py:28"]
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  regression_guard: null

- id: AR-2026-05-22-009
  phase: 2
  severity: info
  title: "render_query_answer_section is 263L in newly-introduced app/ui/query_tab_answer_section.py"
  files: ["app/ui/query_tab_answer_section.py:48"]
  first_seen: "2026-05-22"
  last_seen: "2026-05-22"
  status: new
  regression_guard: null
```

## Metrics Snapshot

- Changed `.py` modules in incremental scope: **59** (52 in `app/`, including `app/ui/`).
- Modules **>600L** in `app/`: 11 — eval_service.py (916), knowledge_graph.py (1063 — forbidden read), query_service.py (752), tutor_orchestrator.py (696), quiz_parse.py (662), flashcard_service.py (646), graph_retrieval.py (623), ui/home_hub.py (670), ui/resume_cards_tutor.py (657), ui/dashboards.py (645), ui/interactive_quiz.py (644).
- Functions **>80L**: 25 sampled, top 5 outside UI helpers: `render_review` (323), `render_topics_plan_subtab` (301), `_render_learning_progress_tab` (285), `_ensure_schema` (268), `_render_interactive_quiz_tab` (268).
- Convention violations (Phase 1): **0 new** (os.environ, sqlite delegation, llm.chat resilience, UI/router knowledge_graph imports all clean).
- BLE001-annotation drift (Phase 4): **86 total** unannotated `except Exception` in `app/`, of which **38** in changed-scope files.
- ADR drift: 0 ADR-table vs ADR-body mismatches (registry passes regression guard).
- Doc-code drift: 10 new split-wave modules absent from `doc/architecture.md`; 0 mismatches in sampled API endpoints.
- Dead code candidates (changed scope): none surfaced (regression guards keep `course_graduation`, `diagnostic_service` allowlisted).
- Duplication clusters: none new flagged in this window.

## Recommended Actions (prioritized)

1. **Annotate broad-excepts in `app/api.py` (warning).** Add `# noqa: BLE001 - <reason>` + (optional) `log_event` to the 8 lifespan/warm-up handlers, and extend the regression guard. Scope **S**, "epoch-arch-review-p4a-api-ble001".
2. **Annotate broad-excepts across changed UI/service files (warning).** ~38 sites; mechanical fix following the established repo pattern. Scope **M**, "epoch-arch-review-p4b-ui-ble001".
3. **Split `app/eval_service.py` (916L, warning).** Pull scoring vs compare assembly into focused modules; add 1000L guard. Scope **M**, "epoch-arch-review-p2-eval-split".
4. **Decompose `app/ui/dashboards.py` (645L, warning).** Extract per-tab renderers; add guard. Scope **M**, "epoch-arch-review-p2-dashboards-split".
5. **Backfill `doc/architecture.md` Module Reference for 10 new split-wave modules (warning).** One-line entries; extend `_check_ssr_modules_documented`. Scope **S**, "epoch-arch-review-p3-arch-doc-sync".
6. **Continue `resume_cards_tutor.py` / `home_hub.py` UI split (info / persists).** Both still >600L; pin guard thresholds and schedule a UI wave. Scope **M**, "epoch-ui-split-resume-homehub".
7. **Move `_generate_llm_explanation` out of UI (info).** Thin the 212L UI function by relocating LLM orchestration to a service helper. Scope **S**.

## Fix Prompts

### Phase 1 — Conventions Compliance Audit

*No critical/warning findings; nothing to fix. Regression guard set remains authoritative.*

### Phase 2 — Structural Health

```text
Goal: fix Phase 2 findings from inline/arch_review_incremental_2026-05-22.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-22.md

Findings to fix (critical + warning from Phase 2, by baseline ID):
- AR-2026-05-22-003: app/eval_service.py grew to 916L with 4 functions >80L
- AR-2026-05-22-004: app/ui/dashboards.py 645L; _render_learning_progress_tab 285L + _render_knowledge_graph_tab 208L

Write-set (<=5 files):
- app/eval_service.py  (split into eval_service.py + new helper modules)
- app/ui/dashboards.py (split into dashboards.py + dashboards_*.py per tab)
- scripts/arch_regression_guards.py (add line-count guards)
- doc/architecture.md (add new helper modules to Module Reference)

Read ONLY:
- app/eval_service.py — rg "^def |^class " app/eval_service.py
- app/ui/dashboards.py — rg "^def |^class " app/ui/dashboards.py
- doc/conventions_architecture.md — § Структура проекта (anchor only)
- one existing tab render module under app/ui/ (signatures) as template

Do not touch:
- Phase 1/3/4/5 files (api.py, BLE001 annotations, architecture-doc unrelated entries)
- knowledge_graph.py, query_service.py, tutor_orchestrator.py (forbidden full-read)

DoD (one per finding):
- AR-2026-05-22-003: `(Get-Content app/eval_service.py).Count` -> <=700; AST scan returns 0 functions >100L
- AR-2026-05-22-004: `(Get-Content app/ui/dashboards.py).Count` -> <=500; AST scan returns 0 functions >150L
- `pytest tests/test_eval_service*.py tests/test_dashboards*.py -q` -> pass

Regression Guard (one per finding):
- AR-2026-05-22-003: add scripts/arch_regression_guards.py::_check_file_line_count("app/eval_service.py", 1000) + max-function 120 check
- AR-2026-05-22-004: add scripts/arch_regression_guards.py::_check_file_line_count("app/ui/dashboards.py", 700) + max-function 200 check

Post-fix baseline update:
- Mark AR-2026-05-22-003 and AR-2026-05-22-004 as status=resolved in doc/archive/arch_review_baseline.yaml with resolved_date=2026-05-22.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) added + unresolved risk.

Optional follow-up (info-level, not in DoD):
- AR-2026-05-22-005: ui/home_hub.py still 670L — schedule UI split.
- AR-2026-05-22-006: ui/resume_cards_tutor.py still 657L — finish resume-cards split wave.
- AR-2026-05-22-009: render_query_answer_section 263L — decompose later.
```

### Phase 3 — Architecture Decision Audit

```text
Goal: fix Phase 3 findings from inline/arch_review_incremental_2026-05-22.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-22.md

Findings to fix (critical + warning from Phase 3, by baseline ID):
- AR-2026-05-22-007: 10 new split-wave modules absent from doc/architecture.md Module Reference
    smart_study_scoring, resume_cards_due, resume_cards_smart_study, resume_cards_tutor,
    query_tab_answer_section, query_tab_poll, tutor_chat_controls, topics_tab_right_column,
    tutor_mastery_forecast_panel, kb_fetch

Write-set (<=5 files):
- doc/architecture.md
- scripts/arch_regression_guards.py

Read ONLY:
- doc/architecture.md — only the Module Reference section/anchor (skip detail blocks)
- scripts/arch_regression_guards.py::_check_ssr_modules_documented (function only)
- each new module — one-line module docstring via rg '"""' app/<module>.py (no full read)

Do not touch:
- Phase 1/2/4/5 files
- Other ADRs

DoD (one per finding):
- AR-2026-05-22-007: `foreach ($m in 'smart_study_scoring','resume_cards_due','resume_cards_smart_study','resume_cards_tutor','query_tab_answer_section','query_tab_poll','tutor_chat_controls','topics_tab_right_column','tutor_mastery_forecast_panel','kb_fetch') { if ((Get-Content doc/architecture.md -Raw) -notmatch $m) { $m } }` -> empty
- `.\.venv\Scripts\python.exe scripts/arch_regression_guards.py` -> all OK including expanded _check_ssr_modules_documented

Regression Guard:
- AR-2026-05-22-007: extend scripts/arch_regression_guards.py::_check_ssr_modules_documented `modules` tuple with the 10 new names.

Post-fix baseline update:
- Mark AR-2026-05-22-007 as status=resolved in doc/archive/arch_review_baseline.yaml with resolved_date=2026-05-22.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + guard expansion + unresolved risk.
```

### Phase 4 — Implementation Quality

```text
Goal: fix Phase 4 findings from inline/arch_review_incremental_2026-05-22.md.
Ignore prior responses/tools. Fresh context only.

Baseline: doc/archive/arch_review_baseline.yaml
Report:   inline/arch_review_incremental_2026-05-22.md

Findings to fix (critical + warning from Phase 4, by baseline ID):
- AR-2026-05-22-001: 8 broad except Exception in app/api.py without `# noqa: BLE001`
- AR-2026-05-22-002: 38 broad except Exception in changed-scope UI/service modules without `# noqa: BLE001`

Write-set (<=5 files for first slice — SPLIT into 4A, 4B, 4C and ship in that order):
4A (api + core services):
- app/api.py
- app/query_service.py
- app/quiz_service.py
- app/index_diff.py
- app/ingestion_content_state.py
4B (UI surfaces, ship after 4A):
- app/ui/sidebar.py
- app/ui/topics_tab_right_column.py
- app/ui/flashcards_ui.py
- app/ui/tutor_chat_response_render.py
- app/ui/tutor_mastery_forecast_panel.py
4C (UI surfaces tail):
- app/ui/dashboards.py
- app/ui/query_tab_answer_section.py
- app/ui/resume_cards_due.py
- app/ui/scoped_quiz.py
- app/ui/tutor_chat_controls.py
- app/ui/main.py
- app/ui/offline_banner.py
(Run 4A → 4B → 4C; do not merge in one PR.)

Read ONLY:
- doc/conventions_reference.md § Обработка ошибок (anchor only)
- scripts/arch_regression_guards.py::_check_broad_exceptions_annotated (function only)
- Each target file: only the lines around the except blocks (`Select-String -Path <file> -Pattern 'except Exception' -Context 1,3`)

Do not touch:
- Phase 1/2/3/5 modules; do not introduce structural splits in this slice.

DoD (one per finding):
- AR-2026-05-22-001: `(Select-String -Path app/api.py -Pattern 'except Exception' | Where-Object { $_.Line -notmatch 'noqa.*BLE001' }).Count` -> 0
- AR-2026-05-22-002: same command for each Write-set file -> 0
- `.\.venv\Scripts\python.exe scripts/arch_regression_guards.py` -> all OK (including expanded BLE001 allow-list)
- `pytest -q -k "api or query_service or quiz_service or index_diff or ingestion or sidebar or topics or flashcards or tutor or dashboards or scoped_quiz or resume_cards or offline_banner"` -> pass

Regression Guard:
- AR-2026-05-22-001 + AR-2026-05-22-002: extend scripts/arch_regression_guards.py::_check_broad_exceptions_annotated `targets` list to include every Write-set file.

Post-fix baseline update:
- Mark AR-2026-05-22-001 and AR-2026-05-22-002 as status=resolved (per slice, when its allow-list entries pass) in doc/archive/arch_review_baseline.yaml with resolved_date=2026-05-22.

Token budget:
- Target <=12k input tokens.
- Hard stop >20k input tokens.
- If estimated input is 12k-20k, compress before sending.
- No retry with unchanged payload.
Output: changed files + tests run + guard(s) extended + unresolved risk.

Optional follow-up (info-level, not in DoD):
- AR-2026-05-22-008: relocate LLM orchestration from app/ui/adaptive_plan_llm_explanation.py:_generate_llm_explanation (212L) into a service helper.
```

### Phase 5 — Dependency and Ecosystem Health

*No critical/warning findings; `requirements.txt` clean against incremental scope (FlagEmbedding transitive through llama-index reranker; uvicorn/watchdog already accepted-tech-debt or annotated). Nothing to fix.*
