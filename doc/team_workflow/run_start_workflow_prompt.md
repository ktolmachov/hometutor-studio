# run_start_workflow_prompt

Updated: **2026-04-22**

Prompt for an AI agent that must execute the workflow router end-to-end through the E2E PowerShell launcher.

---

## How to use

Paste into the target AI agent:

```text
Read doc/team_workflow/run_start_workflow_prompt.md
and execute the instructions.

START_MODE: <dry-run | execute>
TARGET_AGENT: <codex | claude_code | cursor_ai>
PACKAGE_ID: <optional package id or empty; default = auto-detect from backlog_registry.yaml>
FORCE: <true | false>
```

---

## Instructions For The AI Agent

```text
Goal: execute the unified workflow for hometutor end-to-end.

For START_MODE: execute, it is incorrect to stop after the router prints a planning prompt.
The workflow is complete only when:
  1. planning has been executed in this same session,
  2. the final copy-paste execution prompt has been produced,
  3. archive/team_artifacts/<PACKAGE_ID>/execution_contract.md exists.

You must first read:
  - doc/team_workflow/start_workflow.md
  - doc/team_workflow/generate_execution_prompt_auto.md

Execution policy:
  - Use the E2E wrapper:
      scripts/run_start_workflow_e2e.ps1
  - If the agent is weak at constructing PowerShell commands on Windows,
    use the shim:
      scripts\run_start_workflow_e2e.bat
  - Do not assemble the Python command manually unless the launcher itself fails.
  - The launcher is responsible for using the project `.venv`.

PACKAGE_ID is optional.
If PACKAGE_ID is empty or omitted, do not ask for it.
Let the launcher and router auto-detect the active package from doc/backlog_registry.yaml.

Pre-check:
  - Verify that scripts/run_start_workflow_e2e.ps1 exists.
  - Verify that scripts\run_start_workflow_e2e.bat exists.
  - Verify that scripts/run_start_workflow.ps1 exists.
  - Verify that .venv\Scripts\python.exe exists.
  - If any of these are missing, report a blocker and stop.

Case A - START_MODE: dry-run
  Run:
    powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow_e2e.ps1 -Mode dry-run -TargetAgent <TARGET_AGENT>

  Simpler Windows fallback:
    scripts\run_start_workflow_e2e.bat dry-run <TARGET_AGENT>

  If PACKAGE_ID is non-empty, append:
    -PackageId <PACKAGE_ID>

  If FORCE == true, append:
    -Force

  Stop after reporting the real output.

Case B - START_MODE: execute
  Run:
    powershell -ExecutionPolicy Bypass -File scripts/run_start_workflow_e2e.ps1 -Mode execute -TargetAgent <TARGET_AGENT>

  Simpler Windows fallback:
    scripts\run_start_workflow_e2e.bat execute <TARGET_AGENT>

  If PACKAGE_ID is non-empty, append:
    -PackageId <PACKAGE_ID>

  For the `.bat` fallback, append PACKAGE_ID as the third positional argument.

  If FORCE == true, append:
    -Force

  For the `.bat` fallback, append `force` as the fourth positional argument.

  Interpret result:

  1. If the launcher exits 0 and confirms execution_contract.md exists:
     workflow planning is complete. Stop there.

  2. If the launcher exits non-zero specifically because execution_contract.md
     is still missing:
     this is not a final blocker. It means you must continue in this same session:
       - execute the generated planning prompt,
       - continue until the final copy-paste execution prompt is produced,
       - save it to archive/team_artifacts/<PACKAGE_ID>/execution_contract.md,
       - verify that the file now exists.

  3. After creating execution_contract.md, report success and stop.
     Do NOT execute the final implementation prompt in this session.
     That final implementation prompt is the only handoff for a separate session.

Rules:
  1. Do not ask the user which branch to choose after reading start_workflow.md.
     The router script is the decision-maker.
  2. Do not read prompt files from archive/agent_prompts/.
     That archive is write-only for this workflow.
  3. You must actually run the launcher command in the terminal.
     Do not stop at analysis.
  4. In execute mode, "the next human/operator action is to run the planning prompt"
     is always the wrong conclusion.
  5. The first valid human handoff point is after execution_contract.md has been created.
  6. If the launcher fails for another reason, report the exact blocker and stop.

Output format:

  EXECUTED COMMAND:
  <the exact launcher command you ran>

  ROUTER RESULT:
  <short summary of what the launcher/router selected>

  PLANNING RESULT:
  <short summary of what happened after the launcher if planning had to be continued>

  EXECUTION CONTRACT:
  <path to archive/team_artifacts/<PACKAGE_ID>/execution_contract.md and whether it now exists>

  NEXT STEP:
  <only the final separate-session handoff after execution_contract.md exists>

  BLOCKERS:
  <only if something failed and could not be continued>
```

---

## Why this file exists

This file closes the false handoff gap:

1. run the E2E launcher,
2. detect whether execution_contract.md exists,
3. if not, continue the planning flow in the same session,
4. only then hand off the final implementation prompt.
