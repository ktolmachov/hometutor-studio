# Scoped Audit Group 02 ? 2026-04

Target agent: Cursor AI  
Period: 2026-04 (2026-04-01 .. 2026-04-30)  
Depth: dod_replay  
Scope: closed  

This file audits only the related wave/dependency packages listed below. It is safe to run independently from other groups unless Step C reopens a package that appears in a CJM cross-link noted here.

## Group Summary

- Packages: 12
- Waves: wave-autonomous-control-plane-v1, wave-autonomous-control-plane-v2
- CJM moments: infra
- User stories in April index: none
- CI miss: 11
- US miss: 12
- CJM cross-links to other groups: infra -> groups [2, 3, 6, 14, 15]

## Packages

| # | Package ID | Date | Wave | CI | US | CJM | Title |
|---:|---|---|---|---|---|---|---|
| 1 | epoch-control-plane-v3-core | 2026-04-28 | wave-autonomous-control-plane-v1 | OK | MISS | infra | pipeline_state.json + result.json в logs/autonomous_runs/<run_id>/; get_or_create_run_id() (ms+to... |
| 2 | epoch-failure-classifier | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | Exit-code classes are loaded from policies/failure_classes.yaml and written into result.json as s... |
| 3 | epoch-quality-gates-matrix | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | quality_gates.run_all() exposes a shared gate matrix with blocker/shadow summaries; run_autonomou... |
| 4 | epoch-prompt-routing-registry | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | Prompt route selection is resolved through policies/prompts_registry.yaml and prompt_routing_regi... |
| 5 | epoch-skills-jit-router | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | skills_router.py recommends JIT skills from policies/skills_router.yaml by path and keyword. |
| 6 | epoch-nonstop-wave-policy | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | nonstop_wave_policy.py enforces safe non-stop wave limits using policies/nonstop_wave_policy.yaml. |
| 7 | epoch-hitl-approval-protocol | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | hitl_approval.py enforces approval-required actions from policies/hitl_approval_policy.yaml and i... |
| 8 | epoch-pipeline-concurrency-locks | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | pipeline_lock.py and current_task locks prevent concurrent package/task mutations in run_autonomous. |
| 9 | epoch-thin-current-task | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | Large GUI tasks spill into doc/context_pack.md while doc/current_task.md remains thin and preserv... |
| 10 | epoch-agent-evals-layer | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | Control-plane evals cover policies, routing, gates, and observability through deterministic pytes... |
| 11 | epoch-adversarial-eval-harness | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | adversarial_eval.py runs deterministic negative/positive cases for command guard, HITL, skills ro... |
| 12 | epoch-autonomous-observability-dashboard | 2026-04-29 | wave-autonomous-control-plane-v2 | MISS | MISS | infra | pipeline_status.py --json aggregates logs/autonomous_runs into runs/stats including closure_succe... |

## Strong Relations Inside This Group

- `epoch-control-plane-v3-core` <-> `epoch-failure-classifier`: depends_on:epoch-control-plane-v3-core
- `epoch-control-plane-v3-core` <-> `epoch-quality-gates-matrix`: depends_on:epoch-control-plane-v3-core
- `epoch-control-plane-v3-core` <-> `epoch-prompt-routing-registry`: depends_on:epoch-control-plane-v3-core
- `epoch-control-plane-v3-core` <-> `epoch-skills-jit-router`: depends_on:epoch-control-plane-v3-core
- `epoch-control-plane-v3-core` <-> `epoch-nonstop-wave-policy`: depends_on:epoch-control-plane-v3-core
- `epoch-control-plane-v3-core` <-> `epoch-hitl-approval-protocol`: depends_on:epoch-control-plane-v3-core
- `epoch-control-plane-v3-core` <-> `epoch-pipeline-concurrency-locks`: depends_on:epoch-control-plane-v3-core
- `epoch-failure-classifier` <-> `epoch-quality-gates-matrix`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-prompt-routing-registry`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-skills-jit-router`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-nonstop-wave-policy`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-hitl-approval-protocol`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-pipeline-concurrency-locks`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-thin-current-task`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-agent-evals-layer`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-failure-classifier` <-> `epoch-autonomous-observability-dashboard`: depends_on:epoch-failure-classifier, wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-prompt-routing-registry`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-skills-jit-router`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-nonstop-wave-policy`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-hitl-approval-protocol`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-pipeline-concurrency-locks`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-thin-current-task`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-agent-evals-layer`: depends_on:epoch-quality-gates-matrix, wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-quality-gates-matrix` <-> `epoch-autonomous-observability-dashboard`: depends_on:epoch-quality-gates-matrix, wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-skills-jit-router`: wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-nonstop-wave-policy`: wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-hitl-approval-protocol`: wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-pipeline-concurrency-locks`: wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-thin-current-task`: depends_on:epoch-prompt-routing-registry, wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-agent-evals-layer`: depends_on:epoch-prompt-routing-registry, wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-prompt-routing-registry` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-nonstop-wave-policy`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-hitl-approval-protocol`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-pipeline-concurrency-locks`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-thin-current-task`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-agent-evals-layer`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-skills-jit-router` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-nonstop-wave-policy` <-> `epoch-hitl-approval-protocol`: wave:wave-autonomous-control-plane-v2
- `epoch-nonstop-wave-policy` <-> `epoch-pipeline-concurrency-locks`: wave:wave-autonomous-control-plane-v2
- `epoch-nonstop-wave-policy` <-> `epoch-thin-current-task`: wave:wave-autonomous-control-plane-v2
- `epoch-nonstop-wave-policy` <-> `epoch-agent-evals-layer`: wave:wave-autonomous-control-plane-v2
- `epoch-nonstop-wave-policy` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-nonstop-wave-policy` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-hitl-approval-protocol` <-> `epoch-pipeline-concurrency-locks`: wave:wave-autonomous-control-plane-v2
- `epoch-hitl-approval-protocol` <-> `epoch-thin-current-task`: wave:wave-autonomous-control-plane-v2
- `epoch-hitl-approval-protocol` <-> `epoch-agent-evals-layer`: wave:wave-autonomous-control-plane-v2
- `epoch-hitl-approval-protocol` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-hitl-approval-protocol` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-pipeline-concurrency-locks` <-> `epoch-thin-current-task`: wave:wave-autonomous-control-plane-v2
- `epoch-pipeline-concurrency-locks` <-> `epoch-agent-evals-layer`: wave:wave-autonomous-control-plane-v2
- `epoch-pipeline-concurrency-locks` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-pipeline-concurrency-locks` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-thin-current-task` <-> `epoch-agent-evals-layer`: wave:wave-autonomous-control-plane-v2
- `epoch-thin-current-task` <-> `epoch-adversarial-eval-harness`: wave:wave-autonomous-control-plane-v2
- `epoch-thin-current-task` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-agent-evals-layer` <-> `epoch-adversarial-eval-harness`: depends_on:epoch-agent-evals-layer, wave:wave-autonomous-control-plane-v2
- `epoch-agent-evals-layer` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2
- `epoch-adversarial-eval-harness` <-> `epoch-autonomous-observability-dashboard`: wave:wave-autonomous-control-plane-v2

## Coverage Completion Prompt

Use this file as a standalone Cursor AI prompt for completing DoD test coverage for `group_02_wave-autonomous-control-plane-v1.md`.
It follows `archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md`, but is scoped to this group only.

## Inputs

- This group file: `doc/team_workflow/audit_groups_2026-04_cursor_ai/group_02_wave-autonomous-control-plane-v1.md`
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

- Packages: 12
- PASS: 12
- PARTIAL: 0
- STALE/no executable evidence: 0
- E2E/UI smoke gaps: 0
- Unit/CLI gaps: 0
- DoD command gaps: 0

| Package | Current evidence | Gap to close | Primary intent |
|---|---|---|---|
| `epoch-control-plane-v3-core` | dod, unit, cli/schema | none | CLI/schema/policy regression for infra behavior |
| `epoch-failure-classifier` | dod, unit, cli/schema | none | CLI/schema/policy regression for infra behavior |
| `epoch-quality-gates-matrix` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-prompt-routing-registry` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-skills-jit-router` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-nonstop-wave-policy` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-hitl-approval-protocol` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-pipeline-concurrency-locks` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-thin-current-task` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-agent-evals-layer` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-adversarial-eval-harness` | dod, unit | none | CLI/schema/policy regression for infra behavior |
| `epoch-autonomous-observability-dashboard` | dod, unit, cli/schema | none | CLI/schema/policy regression for infra behavior |

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

- Group intent focus: infra.
- User-visible CJM/UI flow: at least one UI/e2e/smoke test for the visible learner path, plus unit/service coverage for the contract feeding it.
- Backend/service/API/persistence: focused unit or integration tests proving the changed public contract.
- Eval/demo: scenario/golden/schema validation plus e2e or eval runner where the package promises a demo/user-facing proof.
- Token-safety/control-plane/infra: CLI/schema/policy tests plus at least one regression around the consumed API.
- Documentation-only: lint/schema/link check is enough only when there is no runtime behavior and `allow_verification_only` or equivalent notes justify it.

## Processing Order

Process packages in table order:

1. `epoch-control-plane-v3-core`
2. `epoch-failure-classifier`
3. `epoch-quality-gates-matrix`
4. `epoch-prompt-routing-registry`
5. `epoch-skills-jit-router`
6. `epoch-nonstop-wave-policy`
7. `epoch-hitl-approval-protocol`
8. `epoch-pipeline-concurrency-locks`
9. `epoch-thin-current-task`
10. `epoch-agent-evals-layer`
11. `epoch-adversarial-eval-harness`
12. `epoch-autonomous-observability-dashboard`

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
Select-String -Path doc/closed_iterations.md -Pattern "epoch\-control\-plane\-v3\-core|epoch\-failure\-classifier|epoch\-quality\-gates\-matrix|epoch\-prompt\-routing\-registry|epoch\-skills\-jit\-router|epoch\-nonstop\-wave\-policy|epoch\-hitl\-approval\-protocol|epoch\-pipeline\-concurrency\-locks|epoch\-thin\-current\-task|epoch\-agent\-evals\-layer|epoch\-adversarial\-eval\-harness|epoch\-autonomous\-observability\-dashboard"
Select-String -Path doc/cjm.md -Pattern "infra"
Select-String -Path doc/team_workflow/audit_groups_2026-04_cursor_ai/coverage_dod_analysis.md -Pattern "epoch\-control\-plane\-v3\-core|epoch\-failure\-classifier|epoch\-quality\-gates\-matrix|epoch\-prompt\-routing\-registry|epoch\-skills\-jit\-router|epoch\-nonstop\-wave\-policy|epoch\-hitl\-approval\-protocol|epoch\-pipeline\-concurrency\-locks|epoch\-thin\-current\-task|epoch\-agent\-evals\-layer|epoch\-adversarial\-eval\-harness|epoch\-autonomous\-observability\-dashboard"
```

Before editing tests for a package, run a scoped read-set check:

```powershell
.\.venv\Scripts\python.exe scripts/check_readset.py doc/backlog_registry.yaml doc/user_stories_index.json doc/team_workflow/audit_groups_2026-04_cursor_ai/group_02_wave-autonomous-control-plane-v1.md
```

## Output Report

Save this group coverage report to:

`archive/team_artifacts/audit_2026-04/group_02_dod_coverage_report.md`

Required format:

```markdown
# DoD Coverage Completion ? Group 02

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

