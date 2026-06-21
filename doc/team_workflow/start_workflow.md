# start_workflow

> ⚠ **Устарело.** Основной entry point теперь — `scripts/workflow.py`.
> Подробности: [`workflow_router.md`](workflow_router.md)

```bash
python scripts/workflow.py --agent cursor_ai
# Непрерывный plan-next → оркестрация без паузы на ревью контракта:
python scripts/workflow.py --agent cursor_ai --skip-review
```

---

Ниже сохранена историческая документация PowerShell-лаунчеров для справки.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow_e2e.ps1 -Mode dry-run -TargetAgent codex
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow_e2e.ps1 -Mode execute -TargetAgent codex
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow.ps1 -Mode dry-run -TargetAgent codex
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow.ps1 -Mode execute -TargetAgent codex
powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow.ps1 -Mode execute -TargetAgent codex -PackageId <PACKAGE_ID>
```

For AI-agent execution, prefer `run_start_workflow_e2e.ps1`.
It adds a hard guardrail: execute mode is not considered complete unless
`archive/team_artifacts/<PACKAGE_ID>/execution_contract.md` exists.

For weaker Windows agents that struggle with PowerShell command assembly, use:

```bat
scripts\run_start_workflow_e2e.bat dry-run codex
scripts\run_start_workflow_e2e.bat execute codex
scripts\run_start_workflow_e2e.bat execute codex <PACKAGE_ID>
scripts\run_start_workflow_e2e.bat execute codex <PACKAGE_ID> force
```

Direct router calls still exist, but the launcher is the safer default because it:
- uses the project-local `.venv\Scripts\python.exe`
- builds the command consistently
- reduces shell-specific errors in AI-agent sessions

Important boundary:
- The launcher/router chooses and starts the workflow branch.
- In agent-driven `execute` mode, this is not the final stopping point.
- The agent must continue through planning execution in the same session until
  `archive/team_artifacts/<PACKAGE_ID>/execution_contract.md` has been created.

## What it automates

Instead of manually deciding between:
- `generate_plan_next_prompt.md`
- `generate_execution_prompt_auto.md`
- `generate_orchestration_prompt.md`
- resume flow

the router evaluates project state and chooses the next step automatically.

## Decision policy

1. If `doc/backlog_registry.yaml` has no active package with status `wip`, `ready`, `open`, or `proposed`:
   it routes to the plan-next path via `scripts/generate_orchestration_prompt.py --agent <agent>`.

2. If the active package already has execution artefacts:
   it routes to `python scripts/generate_next_prompt.py --resume`.

3. If the active package contract is high-complexity:
   it routes to `python scripts/generate_orchestration_prompt.py --agent <agent>`.

4. If the active package contract is low/medium complexity:
   it routes to `python scripts/generate_next_prompt.py`.

## Complexity heuristic

Implemented in `scripts/prompt_utils.py :: classify_package_complexity`.
The heuristic is a **continuous composite score** (no step-function cliffs) with
per-signal auditable drivers, calibrated thresholds, and a margin-based
confidence estimate.

### Signals evaluated

| Signal            | Source                         | Transform                          | Weight |
|-------------------|--------------------------------|------------------------------------|-------:|
| write_set_size    | `WRITE_SET_MAX` / `WRITE_SET`  | `max(0, log₂(1+n) − log₂(1+2))`    | 1.5    |
| dod_ops           | `DOD_COMMANDS` (split on `;`, `&&`, `\|\|`) | `max(0, log₂(1+n) − log₂(2))` | 1.0    |
| outcomes          | `OUTCOMES`                     | `max(0, log₂(1+n) − log₂(3))`      | 0.5    |
| read_set          | `READ_SET_HINT`                | `max(0, log₂(1+n) − log₂(3))`      | 0.5    |
| user_stories      | `USER_STORIES` (deduped, case-insensitive) | `max(0, log₂(1+n) − log₂(2))` | 1.0    |
| dir_breadth       | Shannon entropy of top-level dirs of `WRITE_SET_MAX` | `max(0, H − 0.5)` | 1.5    |
| hot_paths         | regex over WRITE_SET for `schema/migration/auth/config/pipeline/core/tasklist/docker/.github/` | `min(3, hits)` | 1.5    |
| risk_keywords     | regex over OUTCOMES/RATIONALE/DOD/PAIN_POINT/EXEC_CONSTRAINTS for `breaking/deprecat/migrat/rollback/destructive/concurrent/async/security/authn?/schema change/…` | `min(4, distinct)` | 0.8 |
| exec_constraints  | non-empty lines of `EXEC_CONSTRAINTS` | `min(2.0, 0.5·lines)`       | 1.0    |

### Thresholds

- `score ≥ 4.0` → **high**      → orchestration
- `score ≥ 2.0` → **medium**    → execution-auto
- `score <  2.0` → **low**      → execution-auto

### Why this design (vs. the legacy step-function)

1. **Log-scaled size**: 5 files vs 20 files now produce different scores, not
   the same `+2` bucket.
2. **Excess-over-baseline**: the median contract (2 writes, 1 cmd, 2 outcomes,
   1 story) contributes zero to size signals — only deviation raises the score.
3. **Directory entropy (Shannon)**: 5 files in one dir ≠ 5 files in five
   subsystems; breadth is captured as `bits of entropy`.
4. **Hot-path detection**: a 2-file package touching `app/schema.py` +
   `migrations/…` is flagged high-risk regardless of size.
5. **Risk keywords**: "breaking", "rollback", "migrate", "security", etc. in
   contract prose compound the score.
6. **DoD atomization**: `pytest X && mypy Y && ruff check` is counted as 3
   operations, not 1.
7. **Confidence**: `high | medium | low` reflects the margin to the nearest
   threshold — packages near a boundary are flagged for calibration.
8. **Auditable drivers**: each contributing signal is returned with
   `{signal, value, weight, contrib, note}`. This enables future
   calibration against historical outcomes.

### Override

Optional explicit override in the contract:

```md
- `COMPLEXITY`: `low`
```

Allowed values: `low`, `medium`, `high`.

Override policy:
- `high`         → orchestration
- `low|medium`   → execution-auto

**The override never erases the audit trail.** The return value keeps
`computed_label` and `score` so the router can log the disagreement and the
heuristic can be recalibrated against operator judgement over time.

### Calibration anchors (unit-tested)

- Compact package (2 writes, 1 cmd, 2 outcomes, 1 story): score ≈ 0.75 → **low**
- Broad package (5 writes, 3 cmds, 4 outcomes, 2 stories, 5 read-hints): score ≈ 4.6 → **high**
- Small package touching `app/schema.py` + `migrations/0003.py`: **medium/high**
  despite only 2 files, driven by `hot_paths`.

See `tests/test_prompt_utils.py :: TestClassifyPackageComplexity` for the full
set of invariants enforced in CI.

## Why this exists

This removes the manual triage step from the workflow and gives the operator one stable command.
The human no longer has to inspect package complexity first and decide which prompt-generation path to trigger.
