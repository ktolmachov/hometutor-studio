# Audit group group_03 — Smart Study Router next-level trust

Target agent: Codex CLI  
Period label: `epic20-smart-study-router`  
Depth: dod_replay | Scope: closed (Epic 20 only)

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-ssr-next-contrastive-explanations` |
| 2 | `epoch-ssr-next-confidence-ledger` |

## Coverage Completion Prompt

Execute per `doc/team_workflow/archive/audit_coverage_prompt_epic20-smart-study-router_codex.md`.

Linked user stories: US-20.7, US-20.8.

Allowed writes: same allowlist as group_01 (narrow `dod_commands` edits to these two package ids).

Forbidden: `app/**`, `scripts/**`, status / reopen without Step C.

## Raw JSON Update

Merge `coverage_groups["group_03"]` into `_audit_raw.json`.

## Coverage Analysis Refresh

Update rollup table for US-20.7 / US-20.8 and package rows; record Playwright evidence when replayed.
