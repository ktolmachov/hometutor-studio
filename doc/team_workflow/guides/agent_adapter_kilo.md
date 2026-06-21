# Adapter: Kilo

Short operational adapter for Kilo GUI sessions.
Keep this file minimal to avoid inflating injected context.

```yaml
MAX_PARALLEL: 1

AGENT_SPAWN: |
  Kilo should use fresh GUI sessions for planning, execution, and commit work.
  Do not continue multi-phase workflow in one long session.

PARALLEL_SYNTAX: |
  Prefer sequential execution.
  If parallel work is truly needed, use separate fresh Kilo sessions with disjoint ownership.

READ_FILE: |
  Read only the handoff file first.
  Max 3 files in one Kilo GUI session.
  Never open together:
    - doc/backlog_registry.yaml
    - doc/team_workflow/generate_plan_next_prompt.md
    - doc/backlog_registry.yaml
    - doc/tasklist.md  # generated view only
    - doc/closed_iterations.md
    - doc/cjm.md
  Use rg/file:line instead of full-read for heavy files.
  If backlog/history docs are needed, stop and request a slimmer handoff.

WRITE_FILE: |
  Write only the declared write-set.
  Do not widen write-set during the same Kilo session.

RUN_CMD: |
  Use the built-in terminal and prefer:
    .\.venv\Scripts\python.exe -m pytest <targeted tests> -v
    rg -n "pattern" <path>
```
