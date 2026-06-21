# Audit group group_01 — wave-smart-study-router foundation

Target agent: Codex CLI  
Period label: `epic20-smart-study-router`  
Depth: dod_replay | Scope: closed (Epic 20 only)

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-smart-study-router-card` |
| 2 | `epoch-smart-study-router-core-policies` |
| 3 | `epoch-smart-study-router-accessibility-harness` |

## Coverage Completion Prompt

Execute DoD coverage completion for the packages above per `doc/team_workflow/archive/audit_coverage_prompt_epic20-smart-study-router_codex.md`.

Linked user stories: US-20.2, US-20.3–US-20.6 (US-20.1 обрабатывается отдельно в `group_02` → `epoch-smart-study-router-surface-parity`). Пакет `epoch-smart-study-router-trust-control` не входит в US-20.1…US-20.12 и исключён из Epic-20 групп.

Allowed writes: `tests/**/*.py`, `tests/e2e/**/*.ts`, `tests/e2e/fixtures/**`, `eval_data/**`, `tests/eval/**`; `doc/backlog_registry.yaml` (`dod_commands` only for listed packages); `archive/team_artifacts/audit_epic20-smart-study-router/*coverage*.md`; `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json`; `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`; `doc/agent_workflow_test_bundles.md` only when adding a reusable bundle.

Forbidden: `app/**`, `scripts/**`, package status changes / reopen without Step C of the main audit prompt.

## Raw JSON Update

After completing this group's coverage work:

1. Update `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json` — merge `coverage_groups["group_01"]` with `coverage_result`, `commands_run`, `blockers`, `added_tests`, `updated_files`.
2. Sync `summary.coverage_groups_completed` and package counters.
3. Do not mark the group PASS until all recorded DoD commands for these packages are green.

## Coverage Analysis Refresh

1. Edit `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`.
2. Set PASS / PARTIAL / FAIL per package for this group.
3. Remove resolved gaps for packages that reach PASS with evidence.
