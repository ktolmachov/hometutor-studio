# Adapter: Continue / DeepSeek-oriented workflow

This file is read by `generate_orchestration_prompt.md` in Phase 3.
It defines placeholder values for sequential Continue/DeepSeek-oriented
orchestration.

Current status:

- `scripts/deepseek_tui_agent_trigger.ts` is the active executor wrapper for DeepSeek via the local TUI CLI (`deepseek exec`). It has full local shell/file tool access.
- `scripts/deepseek_agent_trigger.ts` remains an experimental Chat API handoff-only path (no tools).
- The Smart Trigger Orchestrator (`trigger_orchestrator.ts`) will automatically select the TUI trigger if `DEEPSEEK_API_KEY` is present and the `deepseek` binary is on PATH.

---

## Placeholder values

```yaml
MAX_PARALLEL: 1

AGENT_SPAWN: |
  Continue/DeepSeek trigger runs one autonomous agent call from doc/current_task.md.
  It cannot spawn native parallel sub-agents inside the trigger call.
  Execute all roles sequentially in the same run:
    "Act as <Role>. Read doc/team_workflow/<role>.md and follow Prompt N."
  Persist every role artifact to archive/team_artifacts/{{PACKAGE_ID}}/ before moving on.
  The final proof must be a substantive execution_contract.md, not only STARTED.

PARALLEL_SYNTAX: |
  [SEQUENTIAL - Continue/DeepSeek trigger has no native parallel sub-agents]
  Step 3 is split into:
    STEP 3a - Architect  (runs first)
    STEP 3b - Designer   (runs after Architect)
  Designer can reference the Architect artifact from the filesystem.

READ_FILE: |
  Use filesystem reads through the available shell/tooling:
    Get-Content path/to/file.md -TotalCount 120
    Select-String -Path path/to/file.md -Pattern "pattern" -Context 2,4
    rg -n "pattern" path/to/file-or-dir
  Read only the required sections; avoid full reads of large files.

WRITE_FILE: |
  Write artifacts with the available file editing tool or shell-safe file writer.
  Preserve UTF-8 and multiline content exactly.
  Required artifact directory:
    archive/team_artifacts/{{PACKAGE_ID}}/
  Final proof:
    archive/team_artifacts/{{PACKAGE_ID}}/execution_contract.md

RUN_CMD: |
  Use project-local commands from the repository root.
  Python commands must prefer:
    .\.venv\Scripts\python.exe
  Examples:
    .\.venv\Scripts\python.exe -m pytest tests/test_relevant.py -v --tb=short
    .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync
    rg -n "pattern" app tests doc
```

---

## Trigger contract

`workflow.py --agent continue` prepares `doc/current_task.md` and Continue-specific
orchestration artifacts. The historical command
`workflow.py --trigger-cmd "npx tsx scripts/deepseek_agent_trigger.ts" --agent continue`
is retained only as a Chat API handoff experiment: for code/orchestration
packages it should report `BLOCKED: no local tool access`, not claim execution.

Keep the orchestration sequential and artifact-driven: each role reads the prior
role artifacts from disk, writes its own artifact, and only then advances.
