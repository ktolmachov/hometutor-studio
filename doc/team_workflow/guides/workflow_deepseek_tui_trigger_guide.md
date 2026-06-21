# DeepSeek TUI Trigger Operational Guide

This guide explains how to use the DeepSeek TUI (`deepseek_tui_agent_trigger.ts`) trigger, which allows the autonomous workflow router to execute tasks directly using the DeepSeek CLI (TUI) instead of the local Cursor IDE.

## When to use

- **Zero-click local execution**: When you want the agent to execute file modifications completely in the background without needing a visible IDE window.
- **Continuous execution**: When running `run_autonomous.py`, the TUI trigger provides a robust way to chain commands as long as you have the `deepseek` CLI available on your path.

## Prerequisites

1. **DeepSeek CLI**: The `deepseek` binary must be installed and available on your system `PATH`.
2. **Environment variables**: Ensure your `.env` contains:
   ```env
   DEEPSEEK_API_KEY=your_key_here
   ```

## Configuration

Configure the TUI trigger in your `.env` file (these are optional and have defaults):

```env
# Optional: Set the DeepSeek model (default: deepseek-v4-flash)
DEEPSEEK_MODEL=deepseek-v4-flash

# Token budgets
DEEPSEEK_TUI_MAX_INPUT_TOKENS=120000
DEEPSEEK_TUI_WARN_INPUT_TOKENS=80000

# Execution timeout
DEEPSEEK_TUI_TIMEOUT_MS=900000

# Grace period after SIGTERM before SIGKILL on timeout (default: 5000ms)
DEEPSEEK_TUI_TIMEOUT_KILL_GRACE_MS=5000

# Override the DeepSeek CLI command (default: "deepseek")
DEEPSEEK_CLI_CMD=deepseek

# Exit when EXECUTION_PROOF is found in output, don't wait for EOF (default: true)
DEEPSEEK_TUI_EXIT_ON_SUBSTANTIVE_CONTRACT=true

# How often to poll for proof contract during execution (default: 3000ms)
DEEPSEEK_TUI_PROOF_POLL_MS=3000
```

> [!TIP]
> The TUI trigger estimates token usage from `git ls-files` output before execution (advisory only — not blocking after Phase 1). Each file is capped at 8000 bytes in the estimate.
> Create a `.deepseekignore` file at the root of the repository to omit large/unnecessary directories from the context to save tokens.

### .deepseekignore Best Practices

Add these to `.deepseekignore` to reduce context noise:

```
node_modules/
.venv/
archive/
dist/
*.jsonl
*.log
```

DeepSeek CLI respects `.deepseekignore` and `.gitignore` patterns automatically.

## Running the Trigger

The Smart Trigger Orchestrator automatically selects this trigger if `DEEPSEEK_API_KEY` is set and the `deepseek` binary is on your `PATH`.

```powershell
.\.venv\Scripts\python.exe scripts\workflow.py --loop --trigger-cmd "npx tsx scripts/trigger_orchestrator.ts"
```

If you want to force the DeepSeek TUI trigger, ignoring risk classification:
```powershell
$env:TRIGGER_STRATEGY="direct_deepseek_tui"
.\.venv\Scripts\python.exe scripts\workflow.py --loop --trigger-cmd "npx tsx scripts/trigger_orchestrator.ts"
```

## Proof Monitoring

The trigger watches stdout for an `EXECUTION_PROOF` block in real time. When `DEEPSEEK_TUI_EXIT_ON_SUBSTANTIVE_CONTRACT=true` (default), the process exits as soon as a substantive proof is detected — without waiting for EOF. This avoids unnecessary token consumption from post-answer commentary.

Poll frequency is controlled by `DEEPSEEK_TUI_PROOF_POLL_MS` (default: 3000ms).

## Troubleshooting

### "budget_pre_estimate_exceeded" Error
The trigger estimates context from `git ls-files` (advisory). If the estimate exceeds `DEEPSEEK_TUI_MAX_INPUT_TOKENS * 2`, the run is blocked as a hard advisory cap. **Fix:** Add directories to `.deepseekignore`, or increase `DEEPSEEK_TUI_MAX_INPUT_TOKENS`.

### "missing EXECUTION_PROOF marker" Error
The task instructions require the LLM to output an `EXECUTION_PROOF` block. If the model fails to follow this instruction, validation fails. Check `archive/team_artifacts/_metrics/trigger_metrics.jsonl`. The orchestrator will retry (self-heal) once before falling back.

### "timeout exceeded" Error
The task took longer than `DEEPSEEK_TUI_TIMEOUT_MS`. Increase this value in `.env` if you have complex tasks, or split the task into smaller packages. Note: timeout is a **non-self-healable** error prefix — the orchestrator will NOT retry and will fall back to the next trigger immediately.

### Stall Detection
The trigger monitors for "started stall" — when the CLI process starts but produces no output. A heartbeat checks for activity every 30s (progressive: 30s → 60s → 120s → 300s). If a started stall is detected, the child process is killed and the run exits with `EXIT_TRANSIENT`.

### Windows Process Tree Kill
On Windows, the TUI trigger uses `taskkill /F /T /PID` to kill the full process tree (deepseek CLI + child shells) on timeout or stall. If cleanup fails, check for orphaned `deepseek.exe` processes in Task Manager.
