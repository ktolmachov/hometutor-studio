# Smart Trigger Orchestrator Design

> Status: implemented (Phase 0 + Phase 1 complete; Phase 2 partial)
> Date: 2026-06-21
> Scope: `scripts/trigger_orchestrator.ts` — a meta-trigger for automatic trigger selection, multi-model chaining, and fallback.
> ADR reference: ADR-018 trigger executor classification, Option 8.

---

## 1. Problem Statement

Today, `workflow.py --trigger-cmd` accepts a single, manually chosen trigger command. The user must:

1. Know which triggers exist and what they can do.
2. Check which API keys are available in the environment.
3. Match the package risk/complexity to the right trigger.
4. Manually switch `--trigger-cmd` when credentials change or a trigger fails.

This is error-prone and does not scale. A low-risk infra package and a high-risk schema migration use the same trigger with the same settings.

## 2. Solution: Smart Trigger Orchestrator

A single `--trigger-cmd` entry point that replaces all individual trigger commands:

```powershell
.\.venv\Scripts\python.exe scripts\workflow.py `
  --loop --skip-review --watch-contract `
  --trigger-cmd "npx tsx scripts/trigger_orchestrator.ts" `
  --agent auto --post-agent-no-dod-cache
```

The orchestrator reads the task + package metadata, checks available credentials, and selects the optimal execution strategy.

## 3. Strategy Matrix + Adaptive Demotion

| Risk Level | Credentials Available | Strategy | Steps |
|---|---|---|---|
| Low | Cursor | `direct_cursor` | Cursor executor |
| Low | DeepSeek only | `direct_deepseek_tui` | DeepSeek TUI executor |
| Low | None | `manual_handoff` | Print instructions, exit 0 |
| Medium | Cursor + DeepSeek | `plan_then_execute` | DeepSeek API plan → Cursor execute |
| Medium | Cursor only | `direct_cursor` | Cursor executor (warn: no review) |
| Medium | DeepSeek only | `direct_deepseek_tui` | DeepSeek TUI executor (warn: no review) |
| High | Cursor + DeepSeek | `review_execute_verify` | DeepSeek plan → review gate → Cursor → DeepSeek verify |
| High | Cursor only | `plan_then_execute` | Cursor with human review gate |
| High | None | `manual_handoff` | Print instructions, exit 0 |

### Adaptive Demotion

Before strategy selection, the orchestrator computes a **cursor success rate** from recent `trigger_metrics.jsonl` rows (only rows with `event === "trigger_orchestrator"`). If the rate drops below 40%, `creds.cursor` is demoted to `false` for this run — cursor will not be selected as primary or fallback, even if the raw credential is present in env.

This prevents futile retries on a trigger that has been systematically failing.

### Risk Classification

Risk is derived from the task/contract, not guessed:

```typescript
function classifyRisk(taskContent: string): "low" | "medium" | "high" {
  // Check for explicit COMPLEXITY marker in contract
  const complexityMatch = taskContent.match(/COMPLEXITY:\s*(low|medium|high)/i);
  if (complexityMatch) return complexityMatch[1].toLowerCase() as any;

  // Heuristic signals
  const signals = {
    writeSetSize: (taskContent.match(/write.?set/i) ? 
      taskContent.split('\n').filter(l => l.match(/^\s*-\s+\S/)).length : 0),
    hasSchemaChange: /schema|migration|database|sqlite/i.test(taskContent),
    hasSecurityPath: /auth|security|guardrail|validation/i.test(taskContent),
    hasConfigChange: /config\.py|\.env|settings/i.test(taskContent),
    dodCommandCount: (taskContent.match(/pytest|lint|check_/g) || []).length,
  };

  const score = 
    (signals.writeSetSize > 8 ? 2 : signals.writeSetSize > 4 ? 1 : 0) +
    (signals.hasSchemaChange ? 2 : 0) +
    (signals.hasSecurityPath ? 1 : 0) +
    (signals.hasConfigChange ? 1 : 0) +
    (signals.dodCommandCount > 3 ? 1 : 0);

  if (score >= 4) return "high";
  if (score >= 2) return "medium";
  return "low";
}
```

### Credential Detection

```typescript
interface AvailableCredentials {
  cursor: boolean;    // CURSOR_API_KEY present and non-empty
  deepseekApi: boolean;  // DEEPSEEK_API_KEY present
  deepseekTui: boolean;  // `deepseek` binary on PATH
}

function detectCredentials(): AvailableCredentials {
  return {
    cursor: Boolean(process.env.CURSOR_API_KEY?.trim()),
    deepseekApi: Boolean(process.env.DEEPSEEK_API_KEY?.trim()),
    deepseekTui: existsSync(which("deepseek")), // or check PATH
  };
}
```

## 4. Strategy Execution

### 4.1 Direct Execute

The simplest strategy. Delegates to a single trigger:

```
orchestrator → cursor_agent_trigger.ts (or deepseek_tui_agent_trigger.ts)
             → writes execution_contract.md
             → returns exit code
```

### 4.2 Plan-Then-Execute

Uses DeepSeek Chat API as a planner, then a local executor:

```
orchestrator → deepseek_agent_trigger.ts (role: planner)
             → saves plan to archive/team_artifacts/<id>/execution_plan.md
             → cursor_agent_trigger.ts (with plan appended to prompt)
             → writes execution_contract.md
             → returns exit code
```

The plan step enriches the task with:
- Implementation approach
- Risk areas to watch
- Expected test commands
- File change predictions

This is **not** the same as orchestration (which happens earlier in the pipeline). This is **within-execution** planning: the planner sees the same task the executor sees, and provides tactical guidance.

### 4.3 Review-Execute-Verify

The most thorough strategy for high-risk packages:

```
orchestrator → deepseek_api plan
             → review_gate (human or automated)
             → cursor execute (with plan)
             → deepseek_api verify (review contract quality)
             → returns exit code
```

The review gate can be:
- **Automated:** check that the plan doesn't violate write-set boundaries or touch forbidden paths.
- **Human:** pause and wait for human approval (only if `--require-human-review` flag is set).

### 4.4 Fallback Chain

When a trigger fails, the orchestrator tries the next available option:

```
try cursor (if creds.cursor — effective, after adaptive demotion)
  → failure?
    → try deepseek_tui (if creds.deepseekTui)
      → spawn error?
        → manual_handoff (print instructions, exit 0)
```

Fallback is **not automatic for all failures**. It triggers only on non-deterministic errors. Errors in `NON_SELF_HEALABLE_ERROR_PREFIXES` (e.g., `"timeout:"`, `"started_stall:"`, `"execution_contract_not_substantive"`, `"execution_contract_path_not_found"`) are **deterministic** and skip self-heal retry.

Self-heal retry: up to `ORCHESTRATOR_SELF_HEAL_RETRIES` (default: 1) retries before fallback.

**Adaptive demotion** → fallback interaction: if cursor success rate drops below 40% in recent history, `creds.cursor` is set to `false`. Fallback selection uses `creds.cursor` (effective), **not** `rawCreds.cursor` (raw env). This prevents wasting time on a demoted trigger.

Fallback does **not** trigger on:
- Contract validation failure (the agent ran but produced bad output)
- Budget exceeded (the run completed but cost too much)
- Task execution error with deterministic error prefix

### 4.5 Local llama.cpp Trigger (Phase 1 adjacent)

`scripts/llamacpp_agent_trigger.ts` exists as a **direct controlled executor** for
low-risk local patch tasks, but it is not yet part of automatic orchestrator
strategy selection.

Direct debug/live command:

```powershell
npx tsx scripts/llamacpp_agent_trigger.ts doc/current_task.md
```

Current proven contract (hardened live smoke 2026-06-21):

```text
model: qwen/qwen3-coder-next
endpoint: http://127.0.0.1:8080/v1
server: AutoFit, ctx=32768, parallel=1, KV=q8_0/q8_0, reasoning=off
trigger path: task -> read-set context injection -> fenced diff -> write-set gate
            -> hunk normalization -> git apply --check/apply -> targeted tests
            -> execution_contract.md from evidence
metrics: hunk_count_normalized=true, recount_used=false,
         repair_used=false, adapter_fallback_used=false,
         tests_status=passed, context_chars=725, context_files_count=2,
         context_truncated=false, duration_ms=9839, n_ctx=32768
```

Important distinction: Cursor/DeepSeek TUI agents can inspect local files through
their tools. The llama.cpp OpenAI-compatible API model cannot. Therefore the
trigger itself injects bounded `CONTEXT EXCERPTS FROM READ_SET` into the prompt.
The system prompt explicitly treats those excerpts as the only available file
context and rejects claims about unseen file contents.

Phase 1 hardening now also includes:

- targeted test allowlist for project pytest and
  `npm.cmd run test:trigger -- tests/trigger/<name>.test.ts`;
- rejection of shell chaining in model-proposed test commands;
- trigger-side retry/backoff for `HTTP 503 Loading model`
  (`3s -> 8s -> 15s`, then `server_loading_timeout`).

Before adding `llamacpp` to `trigger_registry.ts` and strategy selection:

- collect several successful low-risk real tasks;
- implement or explicitly defer model repair attempt and guarded one-line fallback;
- keep high-risk/schema/security/provider/config tasks out of llama.cpp auto-selection.

## 5. Metrics Schema

All orchestrator runs write to `archive/team_artifacts/_metrics/trigger_metrics.jsonl`:

```json
{
  "event": "trigger_orchestrator",
  "strategy": "plan_then_execute",
  "risk_level": "medium",
  "risk_score": 3,
  "risk_signals": { "has_schema_change": false, "has_security_change": false, "file_count": 4 },
  "credentials_detected": { "cursor": true, "deepseek_api": true, "deepseek_tui": false },
  "credentials_effective": { "cursor": true, "deepseek_api": true, "deepseek_tui": false },
  "adaptive_adjustments": { "cursor_rate": 0.85, "cursor_demoted": false },
  "steps": [
    {
      "trigger": "deepseek_api",
      "role": "planner",
      "status": "finished",
      "duration_ms": 15000,
      "model": "deepseek-v4-flash",
      "input_tokens": 8500
    },
    {
      "trigger": "cursor",
      "role": "executor",
      "status": "finished",
      "duration_ms": 180000,
      "model": "composer-2"
    }
  ],
  "fallback_chain": [],
  "overall_status": "finished",
  "overall_duration_ms": 195000,
  "task_path": "doc/current_task.md",
  "contract_path": "archive/team_artifacts/<id>/execution_contract.md"
}
```

## 6. Configuration

Environment variables:

```text
# Strategy override (optional — normally auto-detected)
TRIGGER_STRATEGY=direct_cursor|direct_deepseek_tui|plan_then_execute|review_execute_verify|manual_handoff

# Risk override (optional — normally auto-classified from task)
TRIGGER_RISK_OVERRIDE=low|medium|high

# Human review gate (default: false — automated review only)
TRIGGER_REQUIRE_HUMAN_REVIEW=false

# Fallback behavior (default: true)
TRIGGER_ENABLE_FALLBACK=true

# Circuit breaker: trip after N consecutive orchestrator-level errors (default: 5)
ORCHESTRATOR_CIRCUIT_BREAKER_THRESHOLD=5

# Cooldown after circuit breaker trip, seconds (default: 300)
ORCHESTRATOR_COOLDOWN_SECS=300

# Self-heal retries before falling back (default: 1)
ORCHESTRATOR_SELF_HEAL_RETRIES=1

# DeepSeek TUI model to use for low-risk direct execution (default: deepseek-v4-flash)
# Set DEEPSEEK_MODEL=deepseek-reasoner in env and this to a lighter model for low-risk runs.
ORCHESTRATOR_DEEPSEEK_TUI_LOW_MODEL=deepseek-v4-flash

# Keep original DEEPSEEK_MODEL for all risk levels, skip model override (default: false)
ORCHESTRATOR_KEEP_DEEPSEEK_MODEL=false

# Existing per-trigger variables remain valid:
CURSOR_API_KEY=...
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_TUI_MAX_INPUT_TOKENS=120000

# Local llama.cpp direct trigger (not yet auto-selected by orchestrator):
LLAMACPP_BASE_URL=http://127.0.0.1:8080/v1
LLAMACPP_MODEL=qwen/qwen3-coder-next
LLAMACPP_MAX_INPUT_TOKENS=24000
LLAMACPP_MAX_OUTPUT_TOKENS=6000
LLAMACPP_CONTEXT_MAX_CHARS=60000
LLAMACPP_CONTEXT_FILE_MAX_CHARS=20000
```

## 7. Implementation Phases

### Phase 0: Registry + Selection ✅ done

- `scripts/trigger_registry.ts` with configs for all known triggers.
- `classifyRiskWithScore()`, `detectCredentials()`, `selectStrategy()`.
- Tests for selection logic (pure functions, no API calls).

### Phase 1: Automatic Fallback ✅ done

- Fallback chain logic: primary → alternate on non-deterministic failure.
- Self-heal retry (ORCHESTRATOR_SELF_HEAL_RETRIES).
- Circuit breaker (ORCHESTRATOR_CIRCUIT_BREAKER_THRESHOLD / ORCHESTRATOR_COOLDOWN_SECS).
- Adaptive demotion: success-rate gating, `creds` (effective) vs `rawCreds` separation.
- NON_SELF_HEALABLE_ERROR_PREFIXES for deterministic errors.
- Low-risk TUI model override (ORCHESTRATOR_DEEPSEEK_TUI_LOW_MODEL).
- All transitions recorded in metrics with risk_score, risk_signals, adaptive_adjustments, credentials_effective.

### Phase 2: Plan-Then-Execute 🔶 partial

- `plan_then_execute` strategy: DeepSeek API planner → cursor executor.
- Plan saved to `archive/team_artifacts/<id>/execution_plan.md`.
- Post-execution contract verification: not yet implemented (future).
- Tests with mock plan + mock execution: pending.

### Phase 2b: Local llama.cpp Executor 🔶 direct trigger hardened

- `llamacpp_agent_trigger.ts`: live smoke PASS against local
  `qwen/qwen3-coder-next` on 2026-06-21; hardened live smoke PASS after
  no-tools prompt hardening, npm trigger-test allowlist, and 503 loading retry.
- Proven: `/v1/models` alias gate, read-set context injection, write-set
  validation, hunk normalization, `git apply --check/apply`, targeted tests,
  context metrics, evidence-only contract.
- Not yet in orchestrator auto-selection; next step is a first real low-risk
  task plus an explicit decision on model repair attempt and guarded fallback.

### Phase 3: Learning Loop (future)

- Analyze past trigger metrics: success rate, token cost, duration per strategy.
- Auto-adjust risk thresholds based on historical data.
- Surface strategy recommendations in `collect_workflow_metrics.py`.

## 8. Relationship to Existing Triggers

The orchestrator does **not replace** individual triggers. It spawns them as separate child processes via `spawnSync`:

```
trigger_orchestrator.ts
  ├── spawnSync("npx tsx scripts/cursor_agent_trigger.ts", ...)
  ├── spawnSync("npx tsx scripts/deepseek_agent_trigger.ts", ...)
  ├── spawnSync("npx tsx scripts/deepseek_tui_agent_trigger.ts", ...)
  ├── (future) spawnSync("npx tsx scripts/llamacpp_agent_trigger.ts", ...)
  └── imports _trigger_shared.ts (metrics, logging, contract gates, heartbeat)
```

Each trigger is an independent process. The orchestrator reads exit codes and metrics JSON to determine success/failure and routing decisions.

Individual triggers remain usable via `--trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts"` for cases where the user wants direct control. However, the recommended entry point is the orchestrator:

```powershell
--trigger-cmd "npx tsx scripts/trigger_orchestrator.ts"
```

## 9. Prerequisites

1. DeepSeek TUI trigger (`deepseek_tui_agent_trigger.ts`) must be implemented and smoke-tested.
2. All triggers must export their `execute()` functions for programmatic use.
3. `_trigger_shared.ts` must support child process spawning (for TUI).
4. Unified metrics path (`trigger_metrics.jsonl`) adopted by all triggers.
5. Before `llamacpp` auto-selection: require successful Phase 1 real tasks and
   a registry entry that restricts it to low-risk local patch execution.

## 10. Definition of Done

Phase 0 is done when:

- `trigger_registry.ts` defines all known triggers with their capabilities.
- `selectStrategy()` passes tests for all risk × credentials combinations.
- `trigger_orchestrator.ts` runs as a valid `--trigger-cmd` and delegates to a single trigger.
- Existing trigger tests still pass.
- ADR-018 references this design document.
- `workflow_router.md` documents the orchestrator as the recommended future `--trigger-cmd`.
