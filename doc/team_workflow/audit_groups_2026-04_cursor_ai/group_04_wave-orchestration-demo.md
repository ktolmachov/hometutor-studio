# Scoped Audit Group 04 ? 2026-04

Target agent: Cursor AI  
Period: 2026-04 (2026-04-01 .. 2026-04-30)  
Depth: dod_replay  
Scope: closed  

This file audits only the related wave/dependency packages listed below. It is safe to run independently from other groups unless Step C reopens a package that appears in a CJM cross-link noted here.

## Group Summary

- Packages: 3
- Waves: wave-orchestration-demo, wave-retention-demo
- CJM moments: #11 Retain, #7 Progress, #8 Learning plan
- User stories in April index: US-11.1
- CI miss: 0
- US miss: 2
- CJM cross-links to other groups: #11 Retain -> groups [3, 4, 15]; #7 Progress -> groups [3, 4, 15]; #8 Learning plan -> groups [3, 4, 9]

## Packages

| # | Package ID | Date | Wave | CI | US | CJM | Title |
|---:|---|---|---|---|---|---|---|
| 1 | epoch-demo-scenario-06-srs | 2026-04-25 | wave-retention-demo | OK | OK | #11 Retain | Demo показывает: система знает что студент забывает и напоминает в нужный момент (SRS review queue). |
| 2 | epoch-demo-scenario-07-progress | 2026-04-25 | wave-retention-demo | OK | MISS | #7 Progress | Demo показывает: dashboard не декоративный — каждая цифра превращается в actionable next-step. |
| 3 | epoch-demo-scenario-09-learning-plan | 2026-04-25 | wave-orchestration-demo | OK | MISS | #8 Learning plan | Demo показывает: AI не отвечает — AI ведёт по учебному пути с персональным планом. |

## Strong Relations Inside This Group

- `epoch-demo-scenario-06-srs` <-> `epoch-demo-scenario-07-progress`: depends_on:epoch-demo-scenario-06-srs, wave:wave-retention-demo
- `epoch-demo-scenario-07-progress` <-> `epoch-demo-scenario-09-learning-plan`: depends_on:epoch-demo-scenario-07-progress

## Coverage Completion Prompt

Use this file as a standalone Cursor AI prompt for completing DoD test coverage for `group_04_wave-orchestration-demo.md`.
It follows `archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md`, but is scoped to this group only.

## Inputs

- This group file: `doc/team_workflow/audit_groups_2026-04_cursor_ai/group_04_wave-orchestration-demo.md`
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

- Packages: 3
- PASS: 0
- PARTIAL: 3
- STALE/no executable evidence: 0
- E2E/UI smoke gaps: 0
- Unit/CLI gaps: 3
- DoD command gaps: 3

| Package | Current evidence | Gap to close | Primary intent |
|---|---|---|---|
| `epoch-demo-scenario-06-srs` | e2e | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | package-specific CJM/US assertion |
| `epoch-demo-scenario-07-progress` | e2e | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | progress/plan learner assertion |
| `epoch-demo-scenario-09-learning-plan` | e2e | GAP_UNIT_OR_CLI, GAP_DOD_COMMAND | progress/plan learner assertion |

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

- Group intent focus: #11 Retain, #7 Progress, #8 Learning plan.
- User-visible CJM/UI flow: at least one UI/e2e/smoke test for the visible learner path, plus unit/service coverage for the contract feeding it.
- Backend/service/API/persistence: focused unit or integration tests proving the changed public contract.
- Eval/demo: scenario/golden/schema validation plus e2e or eval runner where the package promises a demo/user-facing proof.
- Token-safety/control-plane/infra: CLI/schema/policy tests plus at least one regression around the consumed API.
- Documentation-only: lint/schema/link check is enough only when there is no runtime behavior and `allow_verification_only` or equivalent notes justify it.

## Processing Order

Process packages in table order:

1. `epoch-demo-scenario-06-srs`
2. `epoch-demo-scenario-07-progress`
3. `epoch-demo-scenario-09-learning-plan`

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
Select-String -Path doc/closed_iterations.md -Pattern "epoch\-demo\-scenario\-06\-srs|epoch\-demo\-scenario\-07\-progress|epoch\-demo\-scenario\-09\-learning\-plan"
Select-String -Path doc/cjm.md -Pattern "US\-11\.1|\#11\ Retain|\#7\ Progress|\#8\ Learning\ plan"
Select-String -Path doc/team_workflow/audit_groups_2026-04_cursor_ai/coverage_dod_analysis.md -Pattern "epoch\-demo\-scenario\-06\-srs|epoch\-demo\-scenario\-07\-progress|epoch\-demo\-scenario\-09\-learning\-plan"
```

Before editing tests for a package, run a scoped read-set check:

```powershell
.\.venv\Scripts\python.exe scripts/check_readset.py doc/backlog_registry.yaml doc/user_stories_index.json doc/team_workflow/audit_groups_2026-04_cursor_ai/group_04_wave-orchestration-demo.md
```

## Output Report

Save this group coverage report to:

`archive/team_artifacts/audit_2026-04/group_04_dod_coverage_report.md`

Required format:

```markdown
# DoD Coverage Completion ? Group 04

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

