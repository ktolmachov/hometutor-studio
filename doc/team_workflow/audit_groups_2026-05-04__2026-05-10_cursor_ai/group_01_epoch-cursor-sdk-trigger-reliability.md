# Audit group group_01 — epoch-cursor-sdk-trigger-reliability

Target agent: Cursor AI  
Period: 2026-05-04..2026-05-10 (2026-05-04 .. 2026-05-10)  
Depth: dod_replay | Scope: closed

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-cursor-sdk-trigger-reliability` |

## Coverage Completion Prompt

Execute DoD coverage completion for the package above per `archive/doc_team_workflow/audit_coverage_prompt_2026-05-04__2026-05-10_cursor_ai.md`.

Allowed writes: `tests/**/*.py`, `tests/e2e/**/*.ts`, fixtures/eval paths per generator; `doc/backlog_registry.yaml` (`dod_commands` only for this package); `${AUDIT_DIR}/*coverage*.md`; `archive/team_artifacts/audit_2026-05-04__2026-05-10/_audit_raw.json`; `doc/team_workflow/audit_groups_2026-05-04__2026-05-10_cursor_ai/coverage_dod_analysis.md`.

Forbidden: `app/**`, `scripts/**`, статус пакетов / reopen без Step C основного аудита.

## Raw JSON Update

After completing this group's coverage work:

1. Update `archive/team_artifacts/audit_2026-05-04__2026-05-10/_audit_raw.json` — merge `coverage_groups["group_01"]` with `coverage_result`, `commands_run`, `blockers`, `added_tests`, `updated_files`.
2. Sync `summary.coverage_groups_completed`, счётчики пакетов.
3. Не помечать группу PASS, пока все целевые команды DoD не зелёные.

## Coverage Analysis Refresh

1. Правка `doc/team_workflow/audit_groups_2026-05-04__2026-05-10_cursor_ai/coverage_dod_analysis.md`.
2. Verdict PASS/PARTIAL/FAIL для пакетов группы.
3. Убрать закрытые gaps для пакетов со статусом PASS.
