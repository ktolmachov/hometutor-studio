# Scoped Audit Group 15 ? 2026-04

Target agent: Cursor AI  
Period: 2026-04 (2026-04-01 .. 2026-04-30)  
Depth: dod_replay  
Scope: closed  

This file audits all standalone packages without `wave_id`. They are bundled together so no-wave packages can be checked in one deliberate pass instead of dozens of tiny files.

## Group Summary

- Packages: 38
- Waves: none
- CJM moments: #1 Discover, #1 First launch, #10 Guided start, #10 Retrieval trust, #11 Retain, #2 First Answer, #3 Continuity, #3 First answer, #3 Switch to Tutor, #3 Transition to tutor, #4 First micro-quiz, #5 Return next day, #6 After reindex, #7 Progress, #7 Spaced repetition due, Adaptive plan, infra
- User stories in April index: US-12.1, US-12.2, US-12.3, US-2.1
- CI miss: 0
- US miss: 35
- Original standalone no-wave components merged: 37
- CJM cross-links to other groups: #1 Discover -> groups [3, 15]; #10 Retrieval trust -> groups [8, 10, 13, 15]; #11 Retain -> groups [3, 4, 15]; #2 First Answer -> groups [3, 8, 10, 11, 15]; #3 Transition to tutor -> groups [3, 7, 9, 15]; #4 First micro-quiz -> groups [3, 7, 15]; #5 Return next day -> groups [3, 15]; #6 After reindex -> groups [3, 15]; #7 Progress -> groups [3, 4, 15]; infra -> groups [2, 3, 6, 14, 15]

## Packages

| # | Package ID | Date | Wave | CI | US | CJM | Title |
|---:|---|---|---|---|---|---|---|
| 1 | epoch-micro-quiz-feedback-tail | 2026-04-20 | - | OK | MISS | #4 First micro-quiz | Submit feedback tail ships status/explanation/one CTA contract for micro-quiz answers. |
| 2 | epoch-quiz-hint-on-fail | 2026-04-20 | - | OK | MISS | #4 First micro-quiz | Hint instead of strict fail in micro-quiz, reducing drop-off after incorrect answers. |
| 3 | epoch-5min-loop-polish | 2026-04-21 | - | OK | MISS | #4 First micro-quiz | Stabilize the 5-minute learner flow answer -> micro-quiz -> feedback/explanation -> explicit next... |
| 4 | epoch-context-cart-mvp | 2026-04-20 | - | OK | MISS | #2 First Answer, #10 Retrieval trust | Token-safe context assembly for plan/orchestration/verify flows; bridge between token_safety_regi... |
| 5 | epoch-unified-context-layer | 2026-04-20 | - | OK | MISS | #3 Continuity, #7 Progress, #11 Retain | Persistent topic / mastery% / due / streak strip across all modes. |
| 6 | epoch-qa-tutor-handoff | 2026-04-20 | - | OK | MISS | #3 Transition to tutor | One-click handoff from Quick Answer to Tutor with preserved continuity context. |
| 7 | epoch-answer-quality-eval | 2026-04-20 | - | OK | MISS | #2 First Answer, #10 Retrieval trust | CI-visible answer-quality gate for First Answer trust moment (golden dataset + thresholds + struc... |
| 8 | epoch-17-1-ux-tail | 2026-04-20 | - | OK | MISS | #1 Discover, #2 First Answer | UX-tail polish: deterministic primary CTA on entry surfaces and explicit QA→Tutor loop closure path. |
| 9 | epoch-cjm-us-frontmatter | 2026-04-22 | - | OK | MISS | #2 First Answer, #3 Transition to tutor, #10 Guided start | Structured pain→moment→status map + US frontmatter index for plan_next candidate discovery. |
| 10 | epoch-us7-3-resume-card | 2026-04-21 | - | OK | MISS | #5 Return next day | Day-2 resume card: learner returns to the last useful learning point without hunting across tabs. |
| 11 | epoch-adaptive-plan-today | 2026-04-20 | - | OK | MISS | Adaptive plan | Plan for today after the first session, connecting first value to a durable learning loop. |
| 12 | epoch-tutor-transparency | 2026-04-20 | - | OK | MISS | #3 Switch to Tutor | Learner-facing explanation of tutor orchestration decisions without exposing raw debug noise. |
| 13 | epoch-mastery-after-reindex | 2026-04-20 | - | OK | MISS | #6 After reindex | Preserve mastery and show an explicit profile-updated badge after reindex. |
| 14 | epoch-env-required-vars | 2026-04-22 | - | OK | MISS | #1 First launch | UI shows missing-env warning |
| 15 | epoch-inline-citations-first-answer | 2026-04-22 | - | OK | MISS | #3 First answer | Inline citations in first answer |
| 16 | epoch-srs-priority-queue | 2026-04-22 | - | OK | MISS | #7 Spaced repetition due | SRS priority queue: learner sees due reviews with priorities, not flat 50+ list |
| 17 | epoch-reindex-mastery-guard | 2026-04-22 | - | OK | MISS | #6 After reindex | Reindex mastery guard: mastery and profile preserved after reindex |
| 18 | epoch-ingest-first-index-progress | 2026-04-22 | - | OK | OK | - | CLI первой индексации выводит стабильный прогресс: processed/total и текущий файл. |
| 19 | epoch-truth-sync | 2026-04-22 | - | OK | OK | - | scripts/rebuild_user_stories_index.py` пересоздаёт `doc/user_stories_index.json` из `doc/backlog_... |
| 20 | epoch-citations-trust-close | 2026-04-22 | - | OK | MISS | - | tests/test_citations_trust.py` — acceptance-level тесты: anchor IDs от `linkify_qa_inline_citatio... |
| 21 | epoch-srs-priority-reason | 2026-04-22 | - | OK | MISS | - | В top-priority due блоке показывается краткая причина приоритета (`давно не повторял` / `низкий m... |
| 22 | epoch-srs-plan-close | 2026-04-22 | - | OK | MISS | - | tests/test_srs_recovery_plan.py` — US-7.2: `defer_due_flashcards_for_recovery` при >20 due оставл... |
| 23 | epoch-reindex-quiz-close | 2026-04-22 | - | OK | MISS | - | tests/test_reindex_quiz_acceptance.py` — US-2.2: `plan_partial_reindex` возвращает `use_partial=T... |
| 24 | epoch-backup-benchmark-close | 2026-04-22 | - | OK | OK | - | tests/test_backup_benchmark_acceptance.py` — US-10.1: `import_full_sync_bundle()` возвращает `row... |
| 25 | epoch-wave-contract | 2026-04-22 | - | OK | MISS | - | doc/backlog_registry.yaml` schema bumped to v2 с блоком `waves:` (4 волны) и опциональными полями... |
| 26 | epoch-router-accuracy-baseline | 2026-04-23 | - | OK | MISS | - | Router accuracy baseline воспроизводимо считается на `eval_data/tutor_regression.json`. |
| 27 | epoch-query-service-assembly | 2026-04-24 | - | OK | MISS | - | Query flow разбит на knowledge lookup, rag assembly и fallback assembly без изменения публичного ... |
| 28 | epoch-architecture-review-baseline | 2026-04-24 | - | OK | MISS | - | Query service boundary остается разделенной на knowledge, RAG assembly и fallback assembly без из... |
| 29 | epoch-query-service-assembly-v2 | 2026-04-24 | - | OK | MISS | - | Query service assembly path remains stable for knowledge and fallback branches. |
| 30 | epoch-flashcard-export-upload-r2 | 2026-04-24 | - | OK | MISS | - | Экспорт выбранной колоды в `.apkg` доступен из UI; загрузка файла из UI создаёт карточки в целево... |
| 31 | epoch-plan-next-candidate-seed | 2026-04-24 | - | OK | MISS | - | Планировочный цикл не блокируется drift-ошибками на старте (`check_backlog_drift.py` exit code 0). |
| 32 | epoch-ui-main-split | 2026-04-24 | - | OK | MISS | - | app/ui/main.py` becomes a lightweight router entrypoint under 300 lines. |
| 33 | epoch-demo-pipeline-hardening | 2026-04-25 | - | OK | MISS | - | Demo pipeline hardening: narrative ordering, strict validation commands, auto-chain DoD without f... |
| 34 | epoch-ingestion-loader-extraction | 2026-04-29 | - | OK | MISS | - | Выделить orchestration загрузчика из app/ingestion.py в app/ingestion_loader.py; публичные entryp... |
| 35 | epoch-doc-ingestion-split-arch-sync | 2026-04-29 | - | OK | MISS | - | Синхронизировать описание модуля ingestion: doc/architecture.md (разделы с app/ingestion.py) — ра... |
| 36 | epoch-demo | 2026-04-28 | - | OK | MISS | - | smoke package scaffolding for post-agent CLI verification |
| 37 | epoch-token-registry-measure-reconcile | 2026-04-30 | - | OK | MISS | infra | Пересчитать est_tokens/lines в doc/token_safety_registry.json через scripts/measure_token_registr... |
| 38 | epoch-context-cart-token-metrics | 2026-04-30 | - | OK | MISS | infra | Добавить scripts/context_cart.py в MEASURE_PATHS scripts/measure_token_registry.py (агентский rea... |

## Strong Relations Inside This Group

- `epoch-micro-quiz-feedback-tail` <-> `epoch-quiz-hint-on-fail`: depends_on:epoch-micro-quiz-feedback-tail

## Coverage Completion Prompt

Use this file as a standalone Cursor AI prompt for completing DoD test coverage for `group_15_no-wave.md`.
It follows `archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md`, but is scoped to this group only.

## Inputs

- This group file: `doc/team_workflow/audit_groups_2026-04_cursor_ai/group_15_no-wave.md`
- Static coverage analysis: `doc/team_workflow/audit_groups_2026-04_cursor_ai/coverage_dod_analysis.md`
- SSoT registry: `doc/backlog_registry.yaml`
- US index: `doc/user_stories_index.json`
- CJM: `doc/cjm.md`
- Main coverage prompt: `archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md`

## Goal

For every package in this group:

1. Derive expected test coverage from:
   - `cjm_moments`
   - `user_stories`
   - `blocks`
   - `impact`
   - `exit_artifact`
   - linked US acceptance notes

2. Check current evidence:
   - `dod_commands`
   - referenced `tests/**/*.py`
   - referenced `tests/e2e/**/*.ts`
   - package contract in `archive/team_artifacts/<id>/3_architect_contract.md`, if present

3. If coverage is incomplete:
   - add focused unit/integration tests for backend/service/API/persistence behavior;
   - add e2e/smoke/UI assertions for learner-visible CJM/US behavior;
   - add CLI/schema/golden checks for infra/eval/demo/token-safety packages;
   - update `dod_commands` for the package in `doc/backlog_registry.yaml`.

Do not change product code. If a newly added test exposes a product bug, stop for that package, mark it `FAIL`, and record the failing assertion.

## Current Coverage Gaps

- Packages: 38
- PASS: 5
- PARTIAL: 16
- STALE/no executable evidence: 17
- E2E/UI smoke gaps: 14
- Unit/CLI gaps: 13
- DoD command gaps: 33

| Package | Current evidence | Gap to close | Primary intent |
|---|---|---|---|
| `epoch-micro-quiz-feedback-tail` | none | GAP_UNIT_OR_CLI, GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | micro-quiz learner assertion |
| `epoch-quiz-hint-on-fail` | unit | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | micro-quiz learner assertion |
| `epoch-5min-loop-polish` | unit | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | micro-quiz learner assertion |
| `epoch-context-cart-mvp` | cli/schema | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | source-trust/citation assertion |
| `epoch-unified-context-layer` | none | GAP_UNIT_OR_CLI, GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | progress/plan learner assertion |
| `epoch-qa-tutor-handoff` | none | GAP_UNIT_OR_CLI, GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | Tutor transition/learning-loop assertion |
| `epoch-answer-quality-eval` | cli/schema | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | source-trust/citation assertion |
| `epoch-17-1-ux-tail` | unit | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | first-answer learner assertion |
| `epoch-cjm-us-frontmatter` | cli/schema | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | Tutor transition/learning-loop assertion |
| `epoch-us7-3-resume-card` | unit | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-adaptive-plan-today` | none | GAP_UNIT_OR_CLI, GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | progress/plan learner assertion |
| `epoch-tutor-transparency` | unit | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | Tutor transition/learning-loop assertion |
| `epoch-mastery-after-reindex` | unit | GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-env-required-vars` | none | GAP_UNIT_OR_CLI, GAP_E2E_OR_UI_SMOKE, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-inline-citations-first-answer` | none | GAP_DOD_COMMAND | source-trust/citation assertion |
| `epoch-srs-priority-queue` | none | GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-reindex-mastery-guard` | none | GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-ingest-first-index-progress` | none | GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-truth-sync` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-citations-trust-close` | unit | GAP_DOD_COMMAND | source-trust/citation assertion |
| `epoch-srs-priority-reason` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-srs-plan-close` | unit | GAP_DOD_COMMAND | progress/plan learner assertion |
| `epoch-reindex-quiz-close` | unit | GAP_DOD_COMMAND | micro-quiz learner assertion |
| `epoch-backup-benchmark-close` | unit | GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-wave-contract` | cli/schema | GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-router-accuracy-baseline` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-query-service-assembly` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-architecture-review-baseline` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-query-service-assembly-v2` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-flashcard-export-upload-r2` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | flashcard learner path assertion |
| `epoch-plan-next-candidate-seed` | cli/schema | GAP_DOD_COMMAND | progress/plan learner assertion |
| `epoch-ui-main-split` | none | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-demo-pipeline-hardening` | unit, cli/schema | GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-ingestion-loader-extraction` | dod, unit | none | package-specific CJM/US assertion |
| `epoch-doc-ingestion-split-arch-sync` | dod, unit, cli/schema | none | package-specific CJM/US assertion |
| `epoch-demo` | dod, cli/schema | none | package-specific CJM/US assertion |
| `epoch-token-registry-measure-reconcile` | dod, unit, cli/schema | none | CLI/schema/policy regression for infra behavior |
| `epoch-context-cart-token-metrics` | dod, unit, cli/schema | none | CLI/schema/policy regression for infra behavior |

## Allowed Write-Set

- `tests/**/*.py`
- `tests/e2e/**/*.ts`
- `tests/e2e/fixtures/**`
- `eval_data/**` and `tests/eval/**` only for eval-related packages
- `doc/backlog_registry.yaml` (`dod_commands` only for the package being processed)
- `doc/agent_workflow_test_bundles.md` only when adding a reusable bundle
- `archive/team_artifacts/audit_2026-04/*coverage*.md` reports

Forbidden:

- `app/**`
- `scripts/**`
- package status changes
- reopening packages
- broad refactors

## Coverage Rules For This Group

Use these minimums:

- Group intent focus: #1 Discover, #1 First launch, #10 Guided start, #10 Retrieval trust, #11 Retain, #2 First Answer....
- User-visible CJM/UI flow: at least one UI/e2e/smoke test for the visible learner path, plus unit/service coverage for the contract feeding it.
- Backend/service/API/persistence: focused unit or integration tests proving the changed public contract.
- Eval/demo: scenario/golden/schema validation plus e2e or eval runner where the package promises a demo/user-facing proof.
- Token-safety/control-plane/infra: CLI/schema/policy tests plus at least one regression around the consumed API.
- Documentation-only: lint/schema/link check is enough only when there is no runtime behavior and `allow_verification_only` or equivalent notes justify it.

## Processing Order

Process packages in table order:

1. `epoch-micro-quiz-feedback-tail`
2. `epoch-quiz-hint-on-fail`
3. `epoch-5min-loop-polish`
4. `epoch-context-cart-mvp`
5. `epoch-unified-context-layer`
6. `epoch-qa-tutor-handoff`
7. `epoch-answer-quality-eval`
8. `epoch-17-1-ux-tail`
9. `epoch-cjm-us-frontmatter`
10. `epoch-us7-3-resume-card`
11. `epoch-adaptive-plan-today`
12. `epoch-tutor-transparency`
13. `epoch-mastery-after-reindex`
14. `epoch-env-required-vars`
15. `epoch-inline-citations-first-answer`
16. `epoch-srs-priority-queue`
17. `epoch-reindex-mastery-guard`
18. `epoch-ingest-first-index-progress`
19. `epoch-truth-sync`
20. `epoch-citations-trust-close`
21. `epoch-srs-priority-reason`
22. `epoch-srs-plan-close`
23. `epoch-reindex-quiz-close`
24. `epoch-backup-benchmark-close`
25. `epoch-wave-contract`
26. `epoch-router-accuracy-baseline`
27. `epoch-query-service-assembly`
28. `epoch-architecture-review-baseline`
29. `epoch-query-service-assembly-v2`
30. `epoch-flashcard-export-upload-r2`
31. `epoch-plan-next-candidate-seed`
32. `epoch-ui-main-split`
33. `epoch-demo-pipeline-hardening`
34. `epoch-ingestion-loader-extraction`
35. `epoch-doc-ingestion-split-arch-sync`
36. `epoch-demo`
37. `epoch-token-registry-measure-reconcile`
38. `epoch-context-cart-token-metrics`

## Per-Package Procedure

For each package:

1. Read only focused lines from this group file and the package registry entry.
2. Map each CJM/US acceptance point to an executable assertion.
3. If an assertion is already covered, record the file/command.
4. If an assertion is missing, add the smallest test that proves it.
5. Add exact replay command(s) to `dod_commands` for the package in `doc/backlog_registry.yaml`.
6. Run only the new/affected tests.
7. Record the result.

Use `.\.venv\Scripts\python.exe` for Python commands. For e2e commands, use the existing repo scripts and fixture patterns from `tests/e2e/README.md` and nearby `tests/e2e/**/*.spec.ts`.

## Helpful Focused Reads

Use focused reads only. Do not read large files fully. Use `@file:line-line` in Composer or terminal grep commands.

```powershell
Select-String -Path doc/closed_iterations.md -Pattern "epoch\-micro\-quiz\-feedback\-tail|epoch\-quiz\-hint\-on\-fail|epoch\-5min\-loop\-polish|epoch\-context\-cart\-mvp|epoch\-unified\-context\-layer|epoch\-qa\-tutor\-handoff|epoch\-answer\-quality\-eval|epoch\-17\-1\-ux\-tail|epoch\-cjm\-us\-frontmatter|epoch\-us7\-3\-resume\-card|epoch\-adaptive\-plan\-today|epoch\-tutor\-transparency|epoch\-mastery\-after\-reindex|epoch\-env\-required\-vars|epoch\-inline\-citations\-first\-answer|epoch\-srs\-priority\-queue|epoch\-reindex\-mastery\-guard|epoch\-ingest\-first\-index\-progress|epoch\-truth\-sync|epoch\-citations\-trust\-close|epoch\-srs\-priority\-reason|epoch\-srs\-plan\-close|epoch\-reindex\-quiz\-close|epoch\-backup\-benchmark\-close|epoch\-wave\-contract|epoch\-router\-accuracy\-baseline|epoch\-query\-service\-assembly|epoch\-architecture\-review\-baseline|epoch\-query\-service\-assembly\-v2|epoch\-flashcard\-export\-upload\-r2|epoch\-plan\-next\-candidate\-seed|epoch\-ui\-main\-split|epoch\-demo\-pipeline\-hardening|epoch\-ingestion\-loader\-extraction|epoch\-doc\-ingestion\-split\-arch\-sync|epoch\-demo|epoch\-token\-registry\-measure\-reconcile|epoch\-context\-cart\-token\-metrics"
Select-String -Path doc/cjm.md -Pattern "Adaptive\ plan|US\-12\.1|US\-12\.2|US\-12\.3|US\-2\.1|\#10\ Guided\ start|\#10\ Retrieval\ trust|\#11\ Retain|\#1\ Discover|\#1\ First\ launch|\#2\ First\ Answer|\#3\ Continuity|\#3\ First\ answer|\#3\ Switch\ to\ Tutor|\#3\ Transition\ to\ tutor|\#4\ First\ micro\-quiz|\#5\ Return\ next\ day|\#6\ After\ reindex|\#7\ Progress|\#7\ Spaced\ repetition\ due|infra"
Select-String -Path doc/team_workflow/audit_groups_2026-04_cursor_ai/coverage_dod_analysis.md -Pattern "epoch\-micro\-quiz\-feedback\-tail|epoch\-quiz\-hint\-on\-fail|epoch\-5min\-loop\-polish|epoch\-context\-cart\-mvp|epoch\-unified\-context\-layer|epoch\-qa\-tutor\-handoff|epoch\-answer\-quality\-eval|epoch\-17\-1\-ux\-tail|epoch\-cjm\-us\-frontmatter|epoch\-us7\-3\-resume\-card|epoch\-adaptive\-plan\-today|epoch\-tutor\-transparency|epoch\-mastery\-after\-reindex|epoch\-env\-required\-vars|epoch\-inline\-citations\-first\-answer|epoch\-srs\-priority\-queue|epoch\-reindex\-mastery\-guard|epoch\-ingest\-first\-index\-progress|epoch\-truth\-sync|epoch\-citations\-trust\-close|epoch\-srs\-priority\-reason|epoch\-srs\-plan\-close|epoch\-reindex\-quiz\-close|epoch\-backup\-benchmark\-close|epoch\-wave\-contract|epoch\-router\-accuracy\-baseline|epoch\-query\-service\-assembly|epoch\-architecture\-review\-baseline|epoch\-query\-service\-assembly\-v2|epoch\-flashcard\-export\-upload\-r2|epoch\-plan\-next\-candidate\-seed|epoch\-ui\-main\-split|epoch\-demo\-pipeline\-hardening|epoch\-ingestion\-loader\-extraction|epoch\-doc\-ingestion\-split\-arch\-sync|epoch\-demo|epoch\-token\-registry\-measure\-reconcile|epoch\-context\-cart\-token\-metrics"
```

Before editing tests for a package, run a scoped read-set check:

```powershell
.\.venv\Scripts\python.exe scripts/check_readset.py doc/backlog_registry.yaml doc/user_stories_index.json doc/team_workflow/audit_groups_2026-04_cursor_ai/group_15_no-wave.md
```

## Output Report

Save this group coverage report to:

`archive/team_artifacts/audit_2026-04/group_15_dod_coverage_report.md`

Required format:

```markdown
# DoD Coverage Completion ? Group 15

| Package | CJM/US Intent | Added Tests | DoD Commands | Result |
|---------|---------------|-------------|--------------|--------|
| <id> | ... | tests/... | pytest ... | PASS |

## Product-Code Blockers

| Package | Test | Failing Assertion | Next Action |
|---------|------|-------------------|-------------|
```

## Raw JSON Update

After saving the markdown report, update:

`archive/team_artifacts/audit_2026-04/_audit_raw.json`

Required behavior:

1. Preserve existing `results`, `summary`, `orphan_ci_headings`, and unrelated keys.
2. Upsert `coverage_groups["group_<NN>"]` for this group.
3. Record this group's `report_path`, `updated_at`, `commands_run`, `blockers`, and per-package coverage results.
4. For each package, record `package_id`, `coverage_result`, `cjm_us_intent`, `added_tests`, `dod_commands`, `dod_commands_updated`, and `blockers`.
5. Update summary counters: `coverage_groups_completed`, `coverage_packages_pass`, `coverage_packages_fail`, `coverage_packages_stale`, and `coverage_packages_total`.

A group is not complete if only the markdown report exists.
## Coverage Analysis Refresh

After `_audit_raw.json` is updated, refresh:
`doc/team_workflow/audit_groups_2026-04_cursor_ai/coverage_dod_analysis.md`

Refresh this file whenever:

- this group report is completed;
- `_audit_raw.json` gets or changes `coverage_groups["group_<NN>"]`;
- `doc/backlog_registry.yaml` `dod_commands` changes;
- tests, e2e specs, fixtures, or eval data are added or changed for packages in this group.

The refreshed analysis must:

- mark packages completed in `_audit_raw.json` as PASS when their `coverage_result` is PASS;
- recompute summary and wave/group rollup;
- remove closed gaps from `Required Test Additions`;
- keep unresolved groups visible.
After completing this group, run:

```powershell
.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-04 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-04/audit_chain_state.json
```

Do not run the full suite unless explicitly requested.

