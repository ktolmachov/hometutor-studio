# Scoped Audit Group 01 ? 2026-04

Target agent: Cursor AI  
Period: 2026-04 (2026-04-01 .. 2026-04-30)  
Depth: dod_replay  
Scope: closed  

This file audits only the related wave/dependency packages listed below. It is safe to run independently from other groups unless Step C reopens a package that appears in a CJM cross-link noted here.

## Group Summary

- Packages: 15
- Waves: wave-course-learning-v2
- CJM moments: #9 Master, course-workspace
- User stories in April index: US-17.1, US-17.10, US-17.11, US-17.2, US-17.3, US-17.4, US-17.5, US-17.6, US-17.7, US-17.8, US-17.9
- CI miss: 0
- US miss: 4
- CJM cross-links to other groups: #9 Master -> groups [1, 3, 9]

## Packages

| # | Package ID | Date | Wave | CI | US | CJM | Title |
|---:|---|---|---|---|---|---|---|
| 1 | epoch-course-workspace-ab | 2026-04-20 | - | OK | MISS | course-workspace | Course Workspace: activate folder as course, focus queries, course activation in Topics |
| 2 | epoch-course-workspace-d | 2026-04-20 | - | OK | MISS | course-workspace | Course Workspace: generate flashcards from document, get course learning plan |
| 3 | epoch-course-workspace-e | 2026-04-20 | - | OK | MISS | course-workspace | Course Workspace: review due flashcards by SM-2, generate flashcards for course |
| 4 | epoch-course-workspace-f | 2026-04-20 | - | OK | MISS | course-workspace | Course Workspace: transition from hard card to tutor, see course progress in dashboard |
| 5 | epoch-e30-a1-cockpit-scaffold | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase A: `app/ui/course_cockpit.py` — 3-column layout, `RAG_COURSE_COCKPIT_V2`, header, exit; tab... |
| 6 | epoch-e30-a2-cockpit-rotator | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase A: `app/ui/cockpit_rotator.py` — interleaved rotation, transitions, триггеры 3 errors → tut... |
| 7 | epoch-e30-b1-graduation-overlay | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase B: `app/ui/graduation_overlay.py` — concept graduation ceremony, Path Map animation, `conce... |
| 8 | epoch-e30-b2-daily-briefing | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase B: `app/ui/daily_briefing.py` — morning brief + evening debrief, gap parking; `course_metri... |
| 9 | epoch-e30-c1-diagnostic | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase C: `app/diagnostic_service.py` — pre-flight adaptive quiz, `diagnostic.v1` artifact, skip-c... |
| 10 | epoch-e30-c2-pace-engine | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase C: `app/pace_engine.py` — Sprint/Steady/Deep, rolling pace, `plan.v2` с pace_mode, override... |
| 11 | epoch-e30-d1-smart-resume | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase D: `app/warmup_planner.py` — pause tiers, soft-recovery overdue, `warmup.v1`, hooks resume_... |
| 12 | epoch-e30-d2-focus-mode | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Phase D: `app/ui/focus_mode.py` — Pomodoro 25/5, distraction-lock, 4-cycle deep-work + streak shi... |
| 13 | epoch-e30-e1-course-graduation | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace, #9 Master | Phase E: `app/course_graduation.py` — course graduation ceremony, PDF certificate, Knowledge Vaul... |
| 14 | epoch-e30-idea-1-daily-runway | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Ideation stage7: дневная микро-цель (N шагов / M минут) + streak chip в `course` scope; события в... |
| 15 | epoch-e30-idea-2-retrieval-gates | 2026-04-28 | wave-course-learning-v2 | OK | OK | course-workspace | Ideation stage7: 1–3 retrieval-вопроса между K-модулями плана (interleaving с пройденными чанками... |

## Strong Relations Inside This Group

- `epoch-course-workspace-ab` <-> `epoch-course-workspace-d`: depends_on:epoch-course-workspace-ab
- `epoch-course-workspace-d` <-> `epoch-course-workspace-e`: depends_on:epoch-course-workspace-d
- `epoch-course-workspace-e` <-> `epoch-course-workspace-f`: depends_on:epoch-course-workspace-e
- `epoch-course-workspace-f` <-> `epoch-e30-a1-cockpit-scaffold`: depends_on:epoch-course-workspace-f
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-a2-cockpit-rotator`: depends_on:epoch-e30-a1-cockpit-scaffold, wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-b1-graduation-overlay`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-b2-daily-briefing`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-c1-diagnostic`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-c2-pace-engine`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-d1-smart-resume`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-d2-focus-mode`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-e1-course-graduation`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-a1-cockpit-scaffold` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-b1-graduation-overlay`: depends_on:epoch-e30-a2-cockpit-rotator, wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-b2-daily-briefing`: depends_on:epoch-e30-a2-cockpit-rotator, wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-c1-diagnostic`: depends_on:epoch-e30-a2-cockpit-rotator, wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-c2-pace-engine`: depends_on:epoch-e30-a2-cockpit-rotator, wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-d1-smart-resume`: wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-d2-focus-mode`: wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-e1-course-graduation`: wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-a2-cockpit-rotator` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-b2-daily-briefing`: wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-c1-diagnostic`: wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-c2-pace-engine`: wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-d1-smart-resume`: depends_on:epoch-e30-b1-graduation-overlay, wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-d2-focus-mode`: depends_on:epoch-e30-b1-graduation-overlay, wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-e1-course-graduation`: wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-b1-graduation-overlay` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-c1-diagnostic`: wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-c2-pace-engine`: wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-d1-smart-resume`: depends_on:epoch-e30-b2-daily-briefing, wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-d2-focus-mode`: depends_on:epoch-e30-b2-daily-briefing, wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-e1-course-graduation`: wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-idea-1-daily-runway`: depends_on:epoch-e30-b2-daily-briefing, wave:wave-course-learning-v2
- `epoch-e30-b2-daily-briefing` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-c1-diagnostic` <-> `epoch-e30-c2-pace-engine`: wave:wave-course-learning-v2
- `epoch-e30-c1-diagnostic` <-> `epoch-e30-d1-smart-resume`: wave:wave-course-learning-v2
- `epoch-e30-c1-diagnostic` <-> `epoch-e30-d2-focus-mode`: wave:wave-course-learning-v2
- `epoch-e30-c1-diagnostic` <-> `epoch-e30-e1-course-graduation`: depends_on:epoch-e30-c1-diagnostic, wave:wave-course-learning-v2
- `epoch-e30-c1-diagnostic` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-c1-diagnostic` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-c2-pace-engine` <-> `epoch-e30-d1-smart-resume`: wave:wave-course-learning-v2
- `epoch-e30-c2-pace-engine` <-> `epoch-e30-d2-focus-mode`: wave:wave-course-learning-v2
- `epoch-e30-c2-pace-engine` <-> `epoch-e30-e1-course-graduation`: depends_on:epoch-e30-c2-pace-engine, wave:wave-course-learning-v2
- `epoch-e30-c2-pace-engine` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-c2-pace-engine` <-> `epoch-e30-idea-2-retrieval-gates`: depends_on:epoch-e30-c2-pace-engine, wave:wave-course-learning-v2
- `epoch-e30-d1-smart-resume` <-> `epoch-e30-d2-focus-mode`: wave:wave-course-learning-v2
- `epoch-e30-d1-smart-resume` <-> `epoch-e30-e1-course-graduation`: depends_on:epoch-e30-d1-smart-resume, wave:wave-course-learning-v2
- `epoch-e30-d1-smart-resume` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-d1-smart-resume` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-d2-focus-mode` <-> `epoch-e30-e1-course-graduation`: depends_on:epoch-e30-d2-focus-mode, wave:wave-course-learning-v2
- `epoch-e30-d2-focus-mode` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-d2-focus-mode` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-e1-course-graduation` <-> `epoch-e30-idea-1-daily-runway`: wave:wave-course-learning-v2
- `epoch-e30-e1-course-graduation` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2
- `epoch-e30-idea-1-daily-runway` <-> `epoch-e30-idea-2-retrieval-gates`: wave:wave-course-learning-v2

## Coverage Completion Prompt

Use this file as a standalone Cursor AI prompt for completing DoD test coverage for `group_01_wave-course-learning-v2.md`.
It follows `archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md`, but is scoped to this group only.

## Inputs

- This group file: `doc/team_workflow/audit_groups_2026-04_cursor_ai/group_01_wave-course-learning-v2.md`
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

- Packages: 15
- PASS: 0
- PARTIAL: 11
- STALE/no executable evidence: 4
- E2E/UI smoke gaps: 11
- Unit/CLI gaps: 0
- DoD command gaps: 4

| Package | Current evidence | Gap to close | Primary intent |
|---|---|---|---|
| `epoch-course-workspace-ab` | none | GAP_DOD_COMMAND | course workspace/cockpit learner assertion |
| `epoch-course-workspace-d` | none | GAP_DOD_COMMAND | course workspace/cockpit learner assertion |
| `epoch-course-workspace-e` | none | GAP_DOD_COMMAND | course workspace/cockpit learner assertion |
| `epoch-course-workspace-f` | none | GAP_DOD_COMMAND | course workspace/cockpit learner assertion |
| `epoch-e30-a1-cockpit-scaffold` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-a2-cockpit-rotator` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-b1-graduation-overlay` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-b2-daily-briefing` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-c1-diagnostic` | dod, cli/schema | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-c2-pace-engine` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-d1-smart-resume` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-d2-focus-mode` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-e1-course-graduation` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-idea-1-daily-runway` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |
| `epoch-e30-idea-2-retrieval-gates` | dod, unit | GAP_E2E_OR_UI_SMOKE | course workspace/cockpit learner assertion |

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

- Group intent focus: #9 Master, course-workspace.
- User-visible CJM/UI flow: at least one UI/e2e/smoke test for the visible learner path, plus unit/service coverage for the contract feeding it.
- Backend/service/API/persistence: focused unit or integration tests proving the changed public contract.
- Eval/demo: scenario/golden/schema validation plus e2e or eval runner where the package promises a demo/user-facing proof.
- Token-safety/control-plane/infra: CLI/schema/policy tests plus at least one regression around the consumed API.
- Documentation-only: lint/schema/link check is enough only when there is no runtime behavior and `allow_verification_only` or equivalent notes justify it.

## Processing Order

Process packages in table order:

1. `epoch-course-workspace-ab`
2. `epoch-course-workspace-d`
3. `epoch-course-workspace-e`
4. `epoch-course-workspace-f`
5. `epoch-e30-a1-cockpit-scaffold`
6. `epoch-e30-a2-cockpit-rotator`
7. `epoch-e30-b1-graduation-overlay`
8. `epoch-e30-b2-daily-briefing`
9. `epoch-e30-c1-diagnostic`
10. `epoch-e30-c2-pace-engine`
11. `epoch-e30-d1-smart-resume`
12. `epoch-e30-d2-focus-mode`
13. `epoch-e30-e1-course-graduation`
14. `epoch-e30-idea-1-daily-runway`
15. `epoch-e30-idea-2-retrieval-gates`

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
Select-String -Path doc/closed_iterations.md -Pattern "epoch\-course\-workspace\-ab|epoch\-course\-workspace\-d|epoch\-course\-workspace\-e|epoch\-course\-workspace\-f|epoch\-e30\-a1\-cockpit\-scaffold|epoch\-e30\-a2\-cockpit\-rotator|epoch\-e30\-b1\-graduation\-overlay|epoch\-e30\-b2\-daily\-briefing|epoch\-e30\-c1\-diagnostic|epoch\-e30\-c2\-pace\-engine|epoch\-e30\-d1\-smart\-resume|epoch\-e30\-d2\-focus\-mode|epoch\-e30\-e1\-course\-graduation|epoch\-e30\-idea\-1\-daily\-runway|epoch\-e30\-idea\-2\-retrieval\-gates"
Select-String -Path doc/cjm.md -Pattern "US\-17\.1|US\-17\.10|US\-17\.11|US\-17\.2|US\-17\.3|US\-17\.4|US\-17\.5|US\-17\.6|US\-17\.7|US\-17\.8|US\-17\.9|\#9\ Master|course\-workspace"
Select-String -Path doc/team_workflow/audit_groups_2026-04_cursor_ai/coverage_dod_analysis.md -Pattern "epoch\-course\-workspace\-ab|epoch\-course\-workspace\-d|epoch\-course\-workspace\-e|epoch\-course\-workspace\-f|epoch\-e30\-a1\-cockpit\-scaffold|epoch\-e30\-a2\-cockpit\-rotator|epoch\-e30\-b1\-graduation\-overlay|epoch\-e30\-b2\-daily\-briefing|epoch\-e30\-c1\-diagnostic|epoch\-e30\-c2\-pace\-engine|epoch\-e30\-d1\-smart\-resume|epoch\-e30\-d2\-focus\-mode|epoch\-e30\-e1\-course\-graduation|epoch\-e30\-idea\-1\-daily\-runway|epoch\-e30\-idea\-2\-retrieval\-gates"
```

Before editing tests for a package, run a scoped read-set check:

```powershell
.\.venv\Scripts\python.exe scripts/check_readset.py doc/backlog_registry.yaml doc/user_stories_index.json doc/team_workflow/audit_groups_2026-04_cursor_ai/group_01_wave-course-learning-v2.md
```

## Output Report

Save this group coverage report to:

`archive/team_artifacts/audit_2026-04/group_01_dod_coverage_report.md`

Required format:

```markdown
# DoD Coverage Completion ? Group 01

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

