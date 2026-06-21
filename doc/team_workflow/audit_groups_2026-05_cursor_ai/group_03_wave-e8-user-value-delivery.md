# Audit group group_03 — E8 user value / backlog hygiene

Target agent: Cursor AI
Period: 2026-05 (2026-05-01 .. 2026-05-31)
Depth: dod_replay | Scope: closed

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-e8-1-cjm-outcome-discipline` |
| 2 | `epoch-e8-2-active-backlog-cleanup` |

## Coverage Completion Prompt

Execute DoD coverage completion for the packages above per `archive/doc_team_workflow/audit_coverage_prompt_2026-05_cursor_ai.md`.
Allowed writes: tests/fixtures/eval data, `doc/backlog_registry.yaml` dod_commands only, coverage reports, `_audit_raw.json`.
Forbidden: `app/**`, `scripts/**`, product refactors, status/reopen without Step C of the main audit prompt.

## Raw JSON Update

After completing this group's coverage work:

1. Update `archive/team_artifacts/audit_2026-05/_audit_raw.json` — merge `coverage_groups["group_03"]` with per-package `coverage_result`, `commands_run`, `blockers`, `added_tests`, `updated_files`.
2. Sync `summary.coverage_groups_completed`, `coverage_packages_*` counters.
3. Do not mark the group PASS until all package `dod_commands` replay green.

## Coverage Analysis Refresh

1. Edit `doc/team_workflow/audit_groups_2026-05_cursor_ai/coverage_dod_analysis.md`.
2. Set **Verdict** to PASS/PARTIAL/FAIL per package in this group.
3. Remove closed gaps for packages promoted to PASS.
