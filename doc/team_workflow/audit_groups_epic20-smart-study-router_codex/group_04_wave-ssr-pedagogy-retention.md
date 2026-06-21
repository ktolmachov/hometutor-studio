# Audit group group_04 — SSR pedagogy + retention / quiet access

Target agent: Codex CLI  
Period label: `epic20-smart-study-router`  
Depth: dod_replay | Scope: closed (Epic 20 only)

## Packages

| # | Package ID |
|---:|---|
| 1 | `epoch-ssr-next-learning-debt-queue` |
| 2 | `epoch-ssr-next-steering-toggles` |
| 3 | `epoch-ssr-next-outcome-receipts` |
| 4 | `epoch-ssr-next-quiet-mode` |

## Coverage Completion Prompt

Execute per `doc/team_workflow/archive/audit_coverage_prompt_epic20-smart-study-router_codex.md`.

Linked user stories: US-20.9, US-20.10, US-20.11, US-20.12.

Allowed writes: same allowlist as group_01 (`dod_commands` only for ids in this table).

Forbidden: `app/**`, `scripts/**`, status / reopen without Step C.

## Raw JSON Update

Merge `coverage_groups["group_04"]` into `_audit_raw.json`; this is the final numeric group — after PASS, `run_next_group_coverage_audit.md` should advance to “all groups completed” + chain check only.

## Coverage Analysis Refresh

Mark remaining Epic 20 stories PASS/FAIL; ensure `coverage_dod_analysis.md` has no orphan PARTIAL rows without explanation.
