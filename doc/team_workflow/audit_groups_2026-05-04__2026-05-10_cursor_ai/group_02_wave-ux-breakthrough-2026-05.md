# Audit group group_02 — wave-ux-breakthrough-2026-05

Target agent: Cursor AI  
Period: 2026-05-04..2026-05-10 (2026-05-04 .. 2026-05-10)  
Depth: dod_replay | Scope: closed

## Packages

| # | Package ID |
|---:|---|
| 1 | `ux-foundation-parsers-contracts` |
| 2 | `ux-first-answer-wait-flow` |
| 3 | `epoch-us19-2-tutor-handoff-ux` |
| 4 | `ux-mastery-celebration-analytics` |
| 5 | `ux-home-hub-navigation-polish` |

## Coverage Completion Prompt

Execute DoD coverage completion for the packages above per `archive/doc_team_workflow/audit_coverage_prompt_2026-05-04__2026-05-10_cursor_ai.md`.

Allowed writes: как в `generate_audit_packages_coverage_prompt.md` § Generation Rules (tests/e2e/fixtures/eval; `dod_commands` в registry для затронутых пакетов; отчёты; `_audit_raw.json`; `coverage_dod_analysis.md`).

Forbidden: `app/**`, `scripts/**`, смена статуса пакетов без Step C.

## Raw JSON Update

1. Обновить `archive/team_artifacts/audit_2026-05-04__2026-05-10/_audit_raw.json` — `coverage_groups["group_02"]` и сводные счётчики.
2. После группы — проверить согласованность с `group_01`.

## Coverage Analysis Refresh

Обновить `coverage_dod_analysis.md`: вердикты по пяти пакетам; gaps только если coverage prompt нашёл дыры поверх зелёного DoD replay.
