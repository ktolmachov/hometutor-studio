# AUDIT COVERAGE PROMPT — Epic 20 Smart Study Router / Codex

Target agent: **Codex CLI**  
Period label: `epic20-smart-study-router` (Epic 20 SSR only; not a calendar window)  
Scope: `closed`  
Mode: DoD test coverage completion (`COVERAGE_FIX=true`)

This prompt complements `doc/team_workflow/archive/audit_prompt_epic20-smart-study-router_codex.md`. Use it to verify and complete test coverage for Smart Study Router packages by linked CJM moments and user stories (`US-20.1` … `US-20.12`).

**Product / architecture index:** `doc/smart_study_router.md`.

## Inputs

- Group runbook: `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/run_next_group_coverage_audit.md`
- Group files: `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/group_*.md`
- Static coverage analysis: `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`
- Raw audit JSON: `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json`
- SSoT registry: `doc/backlog_registry.yaml`
- US index: `doc/user_stories_index.json`
- CJM: `doc/cjm.md` (grep only for SSR / US-20 / package ids)

## Goal

For every package in the active group:

1. Derive expected test coverage from registry `cjm_moments`, `user_stories`, `blocks`, `impact`, `exit_artifact`, and linked US acceptance notes (`doc/user_stories/us-20.*.md`).
2. Check current evidence in `dod_commands`, `tests/test_smart_study_router.py`, `tests/e2e/smart_study_router.spec.ts`, and paths listed in `exit_artifact` / `doc/smart_study_router.md`.
3. If coverage is incomplete, add the smallest missing tests or fixtures and update **only** those packages’ `dod_commands` with exact replay commands.

**Do not change product code** (`app/**`). If a new test exposes a product bug, stop for that package, mark `FAIL`, and record the assertion in the group report and `_audit_raw.json`.

A **markdown-only** coverage report is incomplete audit state. A raw JSON update with a **stale** `coverage_dod_analysis.md` is also incomplete audit state — both must be updated together.

## Processing Order

1. `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/group_01_wave-smart-study-router-foundation.md`
2. `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/group_02_wave-smart-study-router-surface-parity.md`
3. `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/group_03_wave-ssr-next-level-trust.md`
4. `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/group_04_wave-ssr-pedagogy-retention.md`

Follow the numeric order from `run_next_group_coverage_audit.md` when executing manually (`execute_one`).

## Allowed Write-Set

- `tests/**/*.py`
- `tests/e2e/**/*.ts`
- `tests/e2e/fixtures/**`
- `eval_data/**`
- `tests/eval/**`
- `doc/backlog_registry.yaml` (`dod_commands` only for the package being processed)
- `doc/agent_workflow_test_bundles.md` only when adding a reusable bundle
- `archive/team_artifacts/audit_epic20-smart-study-router/*coverage*.md` reports
- `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json`
- `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`

## Forbidden Write-Set

- `app/**`
- `scripts/**`
- package `status` changes or reopen workflows
- broad refactors

## Coverage Rules (SSR-specific minimum)

- Deterministic routing / card builders: exercised in `tests/test_smart_study_router.py` (+ `tests/test_ui_helpers.py` where UI contracts are touched).
- Learner-visible SSR surfaces (home / progress / flashcards / tutor surfaces per US): `npm run test:e2e:smoke -- tests/e2e/smart_study_router.spec.ts` or narrower spec path **as recorded per package** in `dod_commands` after edits.
- Steering / receipts / quiet-mode: combine unit asserts on pure helpers **and** at least one e2e/smoke assertion when behaviour is visibly learner-facing.

## Per-Package Procedure

1. Read focused lines from the group file, registry entry, linked US frontmatter + acceptance bullets, and `doc/smart_study_router.md` module list.
2. Map each acceptance bullet to an executable assertion or Playwright expectation.
3. Record existing coverage (file:test name or spec case).
4. Add missing tests/fixtures **only when needed**.
5. Add exact replay command(s) to `dod_commands` for that package id.
6. Run **only** new/affected commands (never full-repo `pytest`).
7. Append `archive/team_artifacts/audit_epic20-smart-study-router/group_<NN>_dod_coverage_report.md` documenting PASS/FAIL/STALE.

## `_audit_raw.json` mandate

After each group:

- Populate `coverage_groups["group_<NN>"]` with `packages[]`, `coverage_result`, `commands_run`, `packages_pass`, `packages_fail`, timestamps.
- Update `summary.coverage_packages_total` to reflect completed packages.
- Preserve `story_results` for US-20.1..US-20.12 — refresh per-story verdicts when evidence completes.

## Output report format

Per group markdown report sections:

- Group id + package list  
- Commands run (exact strings)  
- Added tests / files  
- Blockers  
- Verdict for each package: PASS | FAIL | STALE  

Use `.\.venv\Scripts\python.exe` for all Python invocations.

After all groups: run

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period epic20-smart-study-router --target-agent codex --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_epic20-smart-study-router/audit_chain_state.json
```
