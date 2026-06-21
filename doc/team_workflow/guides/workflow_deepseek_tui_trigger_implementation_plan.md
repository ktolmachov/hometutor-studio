# DeepSeek TUI Trigger Implementation Plan

> Status: implementation plan (revised 2026-05-19)
> Date: 2026-05-19
> Scope: add a local DeepSeek TUI executor trigger for `workflow.py --loop --watch-contract`.
> Revision notes: critical errors fixed per 2026-05-19 review (C1–C5, D1–D3).

## Goal

Build a real local executor trigger:

```powershell
.\.venv\Scripts\python.exe scripts\workflow.py `
  --loop --skip-review --watch-contract `
  --trigger-cmd "npx tsx scripts/deepseek_tui_agent_trigger.ts" `
  --agent continue --post-agent-no-dod-cache
```

The new trigger must run `deepseek exec --auto --output-format stream-json`, execute `doc/current_task.md` through local DeepSeek TUI tools, require a substantive `execution_contract.md`, enforce token budget from stream metadata, and return clear process exit codes.

## Baseline Evidence

Manual smoke tests already confirmed:

1. `deepseek exec --auto --output-format stream-json` runs non-interactively.
2. Authentication works after key refresh.
3. `read_file` works: the agent read `doc/current_task.md`.
4. `write_file` works: the agent created `archive/team_artifacts/_scratch/deepseek_tui_write_smoke.txt`.
5. Contract smoke works from repo cwd:
   `archive/team_artifacts/_scratch/deepseek_tui_contract_smoke/execution_contract.md`.
6. `DEEPSEEK_MODEL=deepseek-v4-flash` is honored:
   `metadata.model = deepseek-v4-flash`.
7. Budget risk is real:
   - Project cwd smoke used about `61k-92k` input tokens.
   - Minimal cwd smoke still used `49838` input tokens.
   - A `20k` input-token hard limit is currently too low for this CLI.
8. `deepseek exec` has no documented `--cwd` flag. The cwd of the spawning process determines where file tools operate.

## Architecture

Keep the trigger paths separate:

- `scripts/deepseek_agent_trigger.ts` remains a DeepSeek Chat API handoff trigger. It has no local file-system executor.
- `scripts/deepseek_tui_agent_trigger.ts` becomes the local coding-agent trigger. It can use DeepSeek TUI file and shell tools.
- `scripts/trigger_orchestrator.ts` (future Phase 0) will provide automatic trigger selection and fallback.

The TUI wrapper reuses some conventions from `scripts/_trigger_shared.ts` (task path resolution, metrics writing, logging, done banner) but **must extend** the shared runtime with a new `spawnExecutor()` helper for child process lifecycle:

- `_trigger_shared.ts` currently assumes a single async `execute()` callback returning `TriggerResult`. The TUI wrapper needs to spawn `deepseek exec`, read its stdout line-by-line, and accumulate state over time.
- New exports needed in `_trigger_shared.ts`: `spawnChildProcess()`, `StreamJsonParser` class, and `ChildProcessAdapter` interface.
- TUI-specific logic (stream event parsing, budget gate, TUI-specific contract validation) stays inside the new wrapper.

## Runtime Defaults

Recommended defaults:

```text
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TUI_WARN_INPUT_TOKENS=80000
DEEPSEEK_TUI_MAX_INPUT_TOKENS=120000
DEEPSEEK_TUI_TIMEOUT_MS=900000
```

Rationale: current empty/minimal context baseline is already about `50k` input tokens, so `20k` would fail every run. The wrapper should still hard-fail above `DEEPSEEK_TUI_MAX_INPUT_TOKENS`.

## Task 1 — Trigger Wrapper with CWD Guard

Create:

```text
scripts/deepseek_tui_agent_trigger.ts
```

Responsibilities:

1. Resolve task path from `WORKFLOW_CURRENT_TASK_PATH`, argv, or `doc/current_task.md`.
2. **Detect repository root** by walking up from `process.cwd()` to find `.git` directory. If repo root differs from `process.cwd()`, call `process.chdir(repoRoot)` before spawning. This is critical: `deepseek exec` has no `--cwd` flag, so cwd of the spawning process determines where all file tools operate.
3. **Verify cwd** post-chdir: assert that `doc/current_task.md` exists relative to `process.cwd()`. If not, fail with `EXIT_CONFIG` and a clear error message.
4. Read the task file.
5. Extract `archive/team_artifacts/<package_id>/execution_contract.md` path from task text.
6. Launch:

```powershell
deepseek exec --auto --output-format stream-json "<compact prompt>"
```

7. Pass `DEEPSEEK_MODEL` through env, defaulting to `deepseek-v4-flash`.
8. Use a compact prompt that tells the agent to read the task file, execute it fully, and write final proof to the exact contract path.

Prompt shape:

```text
Read <task_path>. Execute it completely from repository cwd.
Use only the task's read-set/write-set/DoD rules.
Do not leave <contract_path> as STARTED.
Write the final proof to <contract_path>.
```

## Task 2 — Pre-Run Context Estimation

Before spawning `deepseek exec`, perform a lightweight context cost estimation:

1. Count tracked files in `process.cwd()` (excluding `.git`, `node_modules`, `.venv`, `__pycache__`, `chroma_db`).
2. Estimate rough token impact as `fileCount * AVG_TOKENS_PER_FILE` (use conservative 200 tokens/file).
3. If estimated context > `DEEPSEEK_TUI_MAX_INPUT_TOKENS`: **abort before spawning** with `budget_pre_estimate_exceeded`.
4. If estimated context > `DEEPSEEK_TUI_WARN_INPUT_TOKENS`: log a warning but proceed.
5. Record estimation in metrics: `pre_run_file_count`, `pre_run_token_estimate`.

This prevents obvious cost blowouts where the repo has grown beyond the budget threshold. It is not exact (DeepSeek TUI may load fewer or more files), but catches the 95% case.

Check for `.deepseekignore` or `.deepseek/config.json` and warn if absent:
```text
WARN: no .deepseekignore found — DeepSeek TUI may scan all repo files. Consider creating one to reduce input token cost.
```

## Task 3 — Parse Stream JSON

Parse one JSON event per stdout line. Track:

```text
type:error          — session-level errors (hard fail)
type:tool_use       — agent invoking a tool
type:tool_result    — tool response (may contain errors)
type:content        — agent text output
type:session_capture
type:metadata
type:done
```

Persist summary fields:

```text
metadata.status
metadata.model
metadata.input_tokens
metadata.output_tokens
metadata.session_id
last_session_error        (from type:error events only)
content_preview
tool_use_count
tool_error_count          (from type:tool_result with error flag)
tool_success_count
```

**Error classification** (critical fix — C4):

- **Session-level errors** (`type:error` at top level): **hard-fail**. These indicate the DeepSeek TUI process itself failed.
- **Tool-level errors** (`type:tool_result` with error/failure): **increment `tool_error_count`**, log warning, but **do not hard-fail**. The agent may recover from transient tool failures (file not found during exploration, lint warnings, etc.).

Hard-fail if:

- any `type:error` session-level event appears;
- no `metadata` event appears;
- `metadata.status != completed`;
- process exit code is non-zero;
- no `done` event appears.

Do **not** hard-fail on `tool_error_count > 0` — record it in metrics for observability.

## Task 4 — Enforce Budget

Rules:

- If `metadata.input_tokens` is missing: fail, because budget cannot be proven.
- If `input_tokens > DEEPSEEK_TUI_MAX_INPUT_TOKENS`: fail with `budget_exceeded`.
- If `input_tokens > DEEPSEEK_TUI_WARN_INPUT_TOKENS`: succeed only if all other gates pass, but record a warning in metrics.

The wrapper must not print success after a budget failure.

## Task 5 — Validate Execution Contract (TUI-specific)

After DeepSeek TUI exits, validate the contract path.

**Outcome-based validation** (critical fix — C5):

The TUI executor is a local agent with file/shell tools. Unlike the Chat API trigger, it **actually reads files, starts work, and creates artifacts**. Contract validation must focus on the **final outcome**, not on intermediate process signals.

Fail if:

- the file does not exist;
- the file is empty;
- the file is exactly `STARTED` (agent started but never wrote proof);
- the file does not contain `EXECUTION_PROOF:` marker;
- the file lacks both `Changed files:` and `Verification:` sections after the marker.

Do **not** reject based on plan-only signals (`I'll start`, `cat archive/...`, `Get-Content`, `echo "STARTED"`). These were designed for the Chat API trigger where plans are the **only** output. A TUI executor legitimately reads files and starts work as part of its execution. The contract is judged by its final shape, not by phrases in the body.

For this TUI executor, `BLOCKED: no local tool access` must be a failure. DeepSeek TUI already proved local file tools in smoke tests, so that line means execution did not happen.

Required success shape:

```text
EXECUTION_PROOF:

Summary: ...

Changed files:
- ...

Verification:
- ...
```

## Task 6 — Metrics

Write JSONL metrics to a **unified** trigger metrics path:

```text
archive/team_artifacts/_metrics/trigger_metrics.jsonl
```

All triggers (Cursor, DeepSeek API, DeepSeek TUI, future orchestrator) should write to this single file. The `event` field distinguishes them. This replaces the per-trigger JSONL files (critical fix — D1).

Suggested event for TUI:

```json
{
  "event": "deepseek_tui_agent_prompt",
  "status": "finished",
  "exit_code": 0,
  "task_path": "doc/current_task.md",
  "contract_path": "archive/team_artifacts/<package>/execution_contract.md",
  "model": "deepseek-v4-flash",
  "input_tokens": 92797,
  "output_tokens": 275,
  "session_id": "...",
  "duration_ms": 12345,
  "budget_warning": true,
  "pre_run_file_count": 450,
  "pre_run_token_estimate": 90000,
  "tool_use_count": 12,
  "tool_error_count": 1,
  "tool_success_count": 11,
  "cwd_verified": true,
  "repo_root": "D:\\Projects\\hometutor-studio"
}
```

Failure statuses:

```text
agent_error           — session-level error event
agent_failed          — metadata.status != completed
budget_exceeded       — post-run input_tokens over hard limit
budget_pre_estimate_exceeded — pre-run estimation over hard limit
missing_metadata      — no metadata event in stream
missing_contract      — contract file not created
invalid_contract      — contract lacks EXECUTION_PROOF shape
timeout               — process exceeded DEEPSEEK_TUI_TIMEOUT_MS
config_error          — cwd mismatch, missing task file, etc.
```

## Task 7 — Tests (TypeScript + Python integration)

**Primary tests: TypeScript** (critical fix — C1):

Create:

```text
tests/trigger/deepseek_tui_stream_parser.test.ts
tests/trigger/deepseek_tui_contract_validator.test.ts
tests/trigger/deepseek_tui_budget_gate.test.ts
```

Use `vitest` (or `jest` if already configured). Export the stream parser, contract validator, and budget gate as testable modules from the wrapper. Test cases:

1. **Stream parser — happy path:**
   - Feed valid stream-json lines → parser accumulates metadata, tool counts, content.
   - Verify `metadata.status`, `input_tokens`, `tool_use_count`.

2. **Stream parser — session error:**
   - Feed `type:error` event → parser marks session error.
   - Verify hard-fail classification.

3. **Stream parser — tool error (no hard-fail):**
   - Feed `type:tool_result` with error flag → parser increments `tool_error_count`.
   - Verify session is NOT marked as failed.

4. **Contract validator — valid proof:**
   - Input with `EXECUTION_PROOF:` + `Changed files:` + `Verification:` → ok.

5. **Contract validator — STARTED only:**
   - Input `STARTED` → reject.

6. **Contract validator — missing proof marker:**
   - Input with detailed text but no `EXECUTION_PROOF:` → reject.

7. **Contract validator — BLOCKED (TUI-specific):**
   - Input `BLOCKED: no local tool access` → reject (TUI has tools).

8. **Contract validator — plan-only is NOT rejected for TUI:**
   - Input with `I'll start by reading...` + `EXECUTION_PROOF:` + sections → ok.
   - Input with `cat archive/team_artifacts/...` in body + `EXECUTION_PROOF:` → ok.

9. **Budget gate — exceeded:**
   - `input_tokens=999999` with `MAX=120000` → fail.

10. **Budget gate — warning zone:**
    - `input_tokens=95000` with `WARN=80000, MAX=120000` → pass with warning.

11. **Budget gate — missing tokens:**
    - `input_tokens=undefined` → fail.

12. **Pre-run estimation — over budget:**
    - Mock file count producing estimate over MAX → fail before spawn.

**Integration tests: Python** (workflow.py ↔ trigger interop):

```text
tests/test_deepseek_tui_trigger_integration.py
```

Use a fake `deepseek` shell script on PATH. Test only the end-to-end contract:

1. Happy path: fake emits valid stream-json + creates contract → wrapper exits 0 → metrics written.
2. Wrapper exits non-zero → workflow.py detects and stops loop.

## Task 8 — Documentation

Add or update:

```text
doc/team_workflow/guides/workflow_deepseek_tui_trigger_guide.md     (new)
doc/team_workflow/guides/workflow_deepseek_api_trigger_guide.md     (update links)
doc/team_workflow/workflow_router.md                                 (update trigger section)
doc/changelog.md
```

Documentation must clearly distinguish:

- DeepSeek Chat API trigger: handoff only, no local repo tools.
- DeepSeek TUI trigger: local executor, can read/write files and run tools.
- Smart Trigger Orchestrator (future): automatic trigger selection and fallback.

Document the recommended command:

```powershell
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"
$env:DEEPSEEK_TUI_MAX_INPUT_TOKENS = "120000"
$env:DEEPSEEK_TUI_WARN_INPUT_TOKENS = "80000"

.\.venv\Scripts\python.exe scripts\workflow.py `
  --loop --skip-review --watch-contract `
  --trigger-cmd "npx tsx scripts/deepseek_tui_agent_trigger.ts" `
  --agent continue --post-agent-no-dod-cache
```

## Task 9 — First Real Smoke

Do not start with a production package. First use a scratch/demo package.

Verify:

1. `workflow.py` writes `doc/current_task.md`.
2. `deepseek_tui_agent_trigger.ts` detects repo root and verifies cwd.
3. Pre-run context estimation runs without error.
4. `deepseek_tui_agent_trigger.ts` launches DeepSeek TUI from repo cwd.
5. DeepSeek TUI writes the expected `execution_contract.md`.
6. Stream metadata says `status=completed`.
7. `input_tokens <= DEEPSEEK_TUI_MAX_INPUT_TOKENS`.
8. Tool errors (if any) are recorded but do not abort the run.
9. Wrapper exits `0`.
10. `workflow.py --watch-contract` continues to `--post-agent`.

## Definition of Done

Done when:

- TypeScript unit tests pass for stream parser, contract validator, and budget gate.
- Python integration test passes for workflow.py ↔ trigger interop.
- Existing trigger tests still pass.
- Docs explain API trigger vs TUI trigger vs future orchestrator without ambiguity.
- Manual scratch smoke creates a valid contract in the repository, not in user home.
- Wrapper never succeeds without a substantive `execution_contract.md`.
- Wrapper blocks over-budget runs before post-agent closure.
- Pre-run estimation prevents obvious cost blowouts.
- Tool-level errors are recorded in metrics but do not abort runs.
- Metrics include model, token usage, status, session id, contract path, tool counts, and cwd verification.
- Unified metrics path used: `archive/team_artifacts/_metrics/trigger_metrics.jsonl`.

## Known Risks

1. DeepSeek TUI currently has a high baseline input context. Budget gate is mandatory.
2. `deepseek exec --help` exposes no `--max-input-tokens`, `--no-context`, `--config`, `--model`, or `--cwd` flags. Model and budget must be controlled via env and post-run metadata. CWD must be set before spawning.
3. `--auto` can write files. The wrapper must rely on `doc/current_task.md`, write-set rules, post-agent gates, and contract validation.
4. Windows cwd matters. The wrapper must explicitly detect repo root and chdir before spawn. If launched outside the repo, files may be written under `C:\Users\<user>\archive\...`.
5. Pre-run estimation is approximate (counts files × heuristic). It may underestimate if some files are very large or if DeepSeek TUI loads additional context. The post-run budget gate remains the authoritative check.

## Future: Smart Trigger Orchestrator (Phase 0)

After this plan stabilizes, the next step is `scripts/trigger_orchestrator.ts` — a meta-trigger that:

- Detects available credentials (CURSOR_API_KEY, DEEPSEEK_API_KEY).
- Reads package complexity from the task or contract metadata.
- Selects strategy: direct execute (low risk) → plan-then-execute (medium) → review-execute-verify (high).
- Falls back automatically (Cursor → DeepSeek TUI → manual handoff).
- Writes unified metrics with strategy rationale.

See `doc/team_workflow/guides/workflow_trigger_orchestrator_design.md` for the full design.
