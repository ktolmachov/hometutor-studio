# Generate Audit Packages Coverage Prompt

Use this generator after `generate_audit_closed_packages_prompt.md` has produced
the period audit prompt and the corresponding audit group files.

It creates a reusable coverage-completion prompt that checks whether each closed
package has enough unit/e2e/fixture/eval coverage for its linked CJM moments and
user stories, adds missing tests when allowed, updates DoD commands, writes the
coverage report, updates `_audit_raw.json`, and refreshes `coverage_dod_analysis.md`.

## Parameters

```text
TARGET_AGENT: <cursor_ai | codex | claude_code | ...>
PERIOD: <YYYY-MM | YYYY-MM-DD..YYYY-MM-DD>
SCOPE: <closed | closed,wip, default closed>
```

Derived bindings:

```text
PERIOD_SLUG = filesystem-safe PERIOD
AUDIT_DIR = archive/team_artifacts/audit_${PERIOD_SLUG}
GROUP_DIR = doc/team_workflow/audit_groups_${PERIOD_SLUG}_${TARGET_AGENT}
SOURCE_AUDIT_PROMPT = doc/team_workflow/audit_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md
OUTPUT_PROMPT = doc/team_workflow/audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md
RAW_JSON = archive/team_artifacts/audit_${PERIOD_SLUG}/_audit_raw.json
```

## Preconditions

Before generating the prompt, verify that these files exist:

- `SOURCE_AUDIT_PROMPT`
- `GROUP_DIR/run_next_group_coverage_audit.md`
- at least one `GROUP_DIR/group_*.md`
- `GROUP_DIR/coverage_dod_analysis.md`
- `doc/backlog_registry.yaml`
- `doc/user_stories_index.json`
- `doc/cjm.md`

If any required file is missing, stop and report which upstream step must run
first.

## Generation Rules

Read `GROUP_DIR/run_next_group_coverage_audit.md` and extract group files in numeric order. Do not
guess group names from memory.

The generated prompt must include:

1. Inputs and goal.
2. Processing order with every generated group file.
3. Allowed write-set:
   - `tests/**/*.py`
   - `tests/e2e/**/*.ts`
   - `tests/e2e/fixtures/**`
   - `eval_data/**`
   - `tests/eval/**`
   - `doc/backlog_registry.yaml` (`dod_commands` only for the package being processed)
   - `doc/agent_workflow_test_bundles.md` only when adding a reusable bundle
   - `${AUDIT_DIR}/*coverage*.md` reports
   - `${RAW_JSON}`
   - `${GROUP_DIR}/coverage_dod_analysis.md`
4. Forbidden write-set:
   - `app/**`
   - `scripts/**`
   - package status changes
   - reopening packages
   - broad refactors
5. Coverage rules by package type:
   - User-visible CJM/UI flow: e2e/smoke/UI-facing test plus focused unit/service coverage when applicable.
   - Backend/service/API/persistence: focused unit or integration tests proving the public contract.
   - Eval/demo: scenario/golden/schema validation plus e2e or eval runner where promised.
   - Token-safety/control-plane/infra: CLI/schema/policy tests plus regression around the consumed API.
   - Documentation-only: lint/schema/link check only when there is no runtime behavior and the package explicitly allows verification-only closure.
6. Per-package procedure:
   - read focused group/registry/US/CJM lines;
   - map each CJM/US acceptance point to an executable assertion;
   - record already-covered assertions;
   - add the smallest missing tests/fixtures only when needed;
   - add exact replay command(s) to `dod_commands`;
   - run only new/affected tests;
   - record PASS/FAIL/STALE.
7. Output report format.
8. Mandatory `_audit_raw.json` update.
9. Mandatory `coverage_dod_analysis.md` refresh.

The generated prompt must say that a markdown-only coverage report is incomplete
audit state. A raw JSON update with stale `coverage_dod_analysis.md` is also
incomplete audit state.

## Output

Save the generated prompt to:

```text
doc/team_workflow/audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md
```

Then print:

```text
Audit coverage prompt ready.
Period: ${PERIOD} | Scope: ${SCOPE} | Agent: ${TARGET_AGENT}
Groups found: <N>
Saved to: doc/team_workflow/audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md
```

Then print the full generated prompt for copy-paste.

---

## Generated Prompt Template

````markdown
# AUDIT COVERAGE PROMPT — ${PERIOD} / ${TARGET_AGENT_LABEL}

Target agent: ${TARGET_AGENT_LABEL}  
Period: ${PERIOD} (${START_ISO} .. ${END_ISO})  
Scope: ${SCOPE}  
Mode: DoD test coverage completion

This prompt complements `${SOURCE_AUDIT_PROMPT}`.
Use it to verify and complete test coverage for each selected package by its
linked CJM moments and user stories.

## Inputs

- Group runbook/index: `${GROUP_DIR}/run_next_group_coverage_audit.md`
- Group files: `${GROUP_DIR}/group_*.md`
- Static coverage analysis: `${GROUP_DIR}/coverage_dod_analysis.md`
- Raw audit JSON: `${RAW_JSON}`
- SSoT registry: `doc/backlog_registry.yaml`
- US index: `doc/user_stories_index.json`
- CJM: `doc/cjm.md`

## Goal

For every package in the selected group:

1. Derive expected test coverage from `cjm_moments`, `user_stories`, `blocks`,
   `impact`, `exit_artifact`, and linked US acceptance notes.
2. Check current evidence in `dod_commands`, referenced tests/e2e specs,
   fixtures/eval data, and package contracts.
3. If coverage is incomplete, add focused missing tests and update package
   `dod_commands`.

Do not change product code. If a newly added test exposes a product bug, stop
for that package, mark it `FAIL`, and record the failing assertion.

## Processing Order

${GROUP_ORDER_LIST}

## Allowed Write-Set

- `tests/**/*.py`
- `tests/e2e/**/*.ts`
- `tests/e2e/fixtures/**`
- `eval_data/**`
- `tests/eval/**`
- `doc/backlog_registry.yaml` (`dod_commands` only for the package being processed)
- `doc/agent_workflow_test_bundles.md` only when adding a reusable bundle
- `${AUDIT_DIR}/*coverage*.md` reports
- `${RAW_JSON}`
- `${GROUP_DIR}/coverage_dod_analysis.md`

Forbidden:

- `app/**`
- `scripts/**`
- package status changes
- reopening packages
- broad refactors

## Coverage Rules

Use these minimums:

- User-visible CJM/UI flow: at least one UI/e2e/smoke test for the visible learner path, plus unit/service coverage for the contract feeding it.
- Backend/service/API/persistence: focused unit or integration tests proving the changed public contract.
- Eval/demo: scenario/golden/schema validation plus e2e or eval runner where the package promises a demo/user-facing proof.
- Token-safety/control-plane/infra: CLI/schema/policy tests plus at least one regression around the consumed API.
- Documentation-only: lint/schema/link check is enough only when there is no runtime behavior and `allow_verification_only` or equivalent notes justify it.

## Per-Package Procedure

For each package:

1. Read only focused lines from the group file, registry entry, linked US, and CJM.
2. Map each CJM/US acceptance point to an executable assertion.
3. If an assertion is already covered, record the file/command.
4. If an assertion is missing, add the smallest test that proves it.
5. Add exact replay command(s) to `dod_commands`.
6. Run only the new/affected tests.
7. Record the result.

Use `.\.venv\Scripts\python.exe` for Python commands.

## Output Report

Save a report to:

`${AUDIT_DIR}/dod_coverage_completion_report.md`

For a single group, prefer:

`${AUDIT_DIR}/group_<NN>_dod_coverage_report.md`

Required format:

| Package | CJM/US Intent | Added Tests | DoD Commands | Result |
|---------|---------------|-------------|--------------|--------|
| `<id>` | ... | `tests/...` | `pytest ...` | PASS |

## Product-Code Blockers

| Package | Test | Failing Assertion | Next Action |
|---------|------|-------------------|-------------|

## Raw JSON Update

After saving the markdown report, update `${RAW_JSON}`.

Required behavior:

1. Preserve existing `results`, `summary`, `orphan_ci_headings`, and unrelated keys.
2. Upsert a `coverage_groups` object if it does not exist.
3. For each completed group, write `coverage_groups["group_<NN>"]` with `group_id`,
   `report_path`, `updated_at`, `packages`, `commands_run`, and `blockers`.
4. For each package in `packages`, record `package_id`, `coverage_result`,
   `cjm_us_intent`, `added_tests`, `dod_commands`, `dod_commands_updated`, and `blockers`.
5. Update `summary.coverage_groups_completed`, `summary.coverage_packages_pass`,
   `summary.coverage_packages_fail`, `summary.coverage_packages_stale`, and
   `summary.coverage_packages_total`.

A group is not complete if only the markdown report exists.

## Coverage Analysis Refresh

After `_audit_raw.json` is updated, refresh:

`${GROUP_DIR}/coverage_dod_analysis.md`

Refresh this file whenever any of these change:

- a group coverage report is completed;
- `_audit_raw.json` receives a new or updated `coverage_groups["group_<NN>"]`;
- `doc/backlog_registry.yaml` `dod_commands` changes;
- tests, e2e specs, fixtures, eval data, or package coverage status changes.

The refreshed analysis must:

- reflect completed group packages as `PASS` when `_audit_raw.json` records them as `PASS`;
- recompute summary counts and wave/group rollups;
- remove closed gaps from `Required Test Additions`;
- keep remaining gaps visible for groups not yet completed.

After completing a group, run:

```powershell
.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py
```

Do not run the full suite unless explicitly requested.
````
