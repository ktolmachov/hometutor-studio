# Audit group group_02 — wave-smart-study-router-surface-parity

Target agent: Codex CLI  
Period label: `epic20-smart-study-router`  
Depth: dod_replay | Scope: closed (Epic 20 only)

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-smart-study-router-surface-parity` |

## Coverage Completion Prompt

Execute DoD coverage completion per `doc/team_workflow/archive/audit_coverage_prompt_epic20-smart-study-router_codex.md`.

Linked user story: US-20.1 (primary `covered_by`).

Allowed writes: `tests/**/*.py`, `tests/e2e/**/*.ts`, `tests/e2e/fixtures/**`, `eval_data/**`, `tests/eval/**`; `doc/backlog_registry.yaml` (`dod_commands` only for `epoch-smart-study-router-surface-parity`); `archive/team_artifacts/audit_epic20-smart-study-router/*coverage*.md`; `archive/team_artifacts/audit_epic20-smart-study-router/_audit_raw.json`; `doc/team_workflow/audit_groups_epic20-smart-study-router_codex/coverage_dod_analysis.md`.

Forbidden: `app/**`, `scripts/**`, package status changes / reopen without Step C.

## Raw JSON Update

1. Merge `coverage_groups["group_02"]` into `_audit_raw.json` with per-package results.
2. Update summary counters.

## Coverage Analysis Refresh

Refresh `coverage_dod_analysis.md`; mark US-20.1 / surface-parity package row when e2e + unit evidence is complete.
