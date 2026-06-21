> **ORCHESTRATION CLOSURE — write execution proof only.**
> Replace `archive/team_artifacts/multi-query-expansion-v1/execution_contract.md` with substantive delivery proof (not `STARTED`).
> Do **not** run `close_package.py` or `run_autonomous.py --post-agent` — workflow does that.

# Orchestration Step 8 — Closure (proof file only)

Package: `multi-query-expansion-v1`
Target agent: `cursor_ai`
Orchestration reference: `archive/team_artifacts/multi-query-expansion-v1/orchestration_cursor_ai.md`

Your **only** deliverable in this session is **`archive/team_artifacts/multi-query-expansion-v1/execution_contract.md`** with substantive execution proof:

- summary of product behavior delivered
- exact product and test file paths changed (sp1 write-set only if applicable)
- DoD commands and results (paste pytest output or reference artifact paths)
- blockers or follow-up risks, if any

Read for context (do not execute shell from STEP 8 closure block):

- `archive/team_artifacts/multi-query-expansion-v1/5a_developer_sp1.md`
- `archive/team_artifacts/multi-query-expansion-v1/6a_tester_sp1.md`
- Developer / tester sections in `archive/team_artifacts/multi-query-expansion-v1/orchestration_cursor_ai.md`

**Forbidden in this session:** `close_package.py`, registry edits, `backlog_registry_lint`, post-agent, git commit.
Stop immediately after saving `archive/team_artifacts/multi-query-expansion-v1/execution_contract.md`.
---

## Mandatory Final Step

Replace `archive/team_artifacts/multi-query-expansion-v1/execution_contract.md` with the proof sections above. Do not run package closure scripts.

If blocked, write a `BLOCKED` proof with last completed step and exact blocker.

If delivery was already committed before this closure step (no new working-tree changes), add a machine-parseable evidence block **exactly** as shown (no backticks around SHA or paths, no parenthetical comments on the commit line):

```text
allow_verification_only

## Pre-existing delivery evidence

- commit: <plain 7-40 char SHA, no backticks>
- files: app/your_module.py, tests/test_your_module.py
```

Do not close the package manually. `scripts/workflow.py --loop --watch-contract` is watching progress and will run `run_autonomous.py --post-agent` when proof is substantive.
