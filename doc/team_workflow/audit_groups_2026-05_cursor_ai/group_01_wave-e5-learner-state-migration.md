# Audit group group_01 — E5 learner state migration

Target agent: Cursor AI
Period: 2026-05 (2026-05-01 .. 2026-05-31)
Depth: dod_replay | Scope: closed

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-e5-0-versioned-learner-profile-history` |
| 2 | `epoch-e5-1-migration-safe-mastery-rehydrate` |
| 3 | `epoch-e5-2-learner-profile-history-api` |
| 4 | `epoch-e5-3-learner-migration-metrics` |
| 5 | `epoch-e5-4-learner-migration-slo-alert` |
| 6 | `epoch-e5-5-learner-migration-gate-command` |
| 7 | `epoch-e5-6-learner-migration-smoke-command` |
| 8 | `epoch-e5-7-learner-migration-ci-gate` |
| 9 | `epoch-e5-8-learner-lineage-sync-on-activation` |

## Coverage Completion Prompt

Execute DoD coverage completion for the packages above per `archive/doc_team_workflow/audit_coverage_prompt_2026-05_cursor_ai.md`.
Allowed writes: tests/fixtures/eval data, `doc/backlog_registry.yaml` dod_commands only, coverage reports, `_audit_raw.json`.
Forbidden: `app/**`, `scripts/**`, product refactors, status/reopen without Step C of the main audit prompt.

## Raw JSON Update

After completing this group's coverage work:

1. Update `archive/team_artifacts/audit_2026-05/_audit_raw.json` — merge `coverage_groups["group_01"]` with per-package `coverage_result`, `commands_run`, `blockers`, `added_tests`, `updated_files`.
2. Sync `summary.coverage_groups_completed`, `coverage_packages_*` counters.
3. Do not mark the group PASS until all package `dod_commands` replay green.

## Coverage Analysis Refresh

1. Edit `doc/team_workflow/audit_groups_2026-05_cursor_ai/coverage_dod_analysis.md`.
2. Set **Verdict** to PASS/PARTIAL/FAIL per package in this group.
3. Remove closed gaps for packages promoted to PASS.
