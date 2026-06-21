# run_autonomous — v3 control-plane runbook

Актуализировано: **2026-05-02** (exit-code cross-ref; concurrency → 9)

## Purpose

`scripts/run_autonomous.py` is no longer only a prompt/exit-code loop. It is the
entrypoint into the autonomous delivery control plane:

- durable run identity through `HOME_RAG_RUN_ID`;
- per-run state and result artifacts;
- proof bundle validation before closure;
- shared quality gates for runners and hooks;
- deterministic policy/eval checks;
- observability through `pipeline_status.py`.

## Run Correlation

- Run id source: `pipeline_events.get_or_create_run_id()`.
- Existing `HOME_RAG_RUN_ID` is reused for child processes.
- New top-level ids use `{ms_since_epoch}-{6_hex}` to avoid subsecond collisions.
- Run directory: `logs/autonomous_runs/<run_id>/`.
- Active process registry: `logs/autonomous_runs/current/<pid>.json`.
- Orphan events without run id go to `logs/autonomous_runs/_orphan/<YYYY-MM-DD>.jsonl`.

## Run Artifacts

| File | Purpose |
|------|---------|
| `logs/autonomous_runs/<run_id>/result.json` | Final process result: `run_id`, `exit_code`, `finished_at`, optional `package_id`, `argv`, and structured `failure_class`. |
| `logs/autonomous_runs/<run_id>/pipeline_state.json` | Current/final phase: `planning`, `execution`, `post_agent`, `closed`, or `failed`. |
| `logs/autonomous_runs/<run_id>/event_log.jsonl` | Durable event trail: gates, sandbox blocks, proof failures, phase changes. |
| `logs/autonomous_runs/<run_id>/proof_bundle/manifest.json` | Closure proof manifest with artifact paths and sha256 hashes. |
| `logs/autonomous_runs/<run_id>/state_snapshots/*.json` | Time-travel snapshots captured by recorder/replay tooling. |
| `logs/autonomous_runs/current/<pid>.json` | PID-scoped active-run marker; stale entries are cleaned at startup. |

## Schemas And Policies

| Path | Purpose |
|------|---------|
| `schemas/pipeline_result.schema.json` | `result.json` contract. |
| `schemas/pipeline_state.schema.json` | `pipeline_state.json` contract. |
| `schemas/pipeline_status_observability.schema.json` | `pipeline_status.py --json` `runs`/`stats` subset. |
| `policies/failure_classes.yaml` | Exit-code to named class + `next_action` mapping. |
| `policies/pipeline_gate_policy.yaml` | Shadow/enforcing gate mode, retry budget, result freshness. |
| `policies/agent_sandbox_policy.yaml` | Command guard allow/block policy. |
| `policies/prompts_registry.yaml` | Prompt route registry. |
| `policies/skills_router.yaml` | JIT skill recommendation policy. |
| `policies/hitl_approval_policy.yaml` | Actions that require explicit human approval. |
| `policies/nonstop_wave_policy.yaml` | Non-stop wave safety limits. |

Policy files are YAML-compatible JSON unless the loader explicitly uses YAML.

## Gates

All runner-facing final checks should go through `quality_gates.run_all()`:

- `pipeline_guard` checks write-set drift, retry budget, and stale `result.json`;
- `proof_bundle` validates proof manifest hashes when a run id is available.

Current call-sites:

- `scripts/run_autonomous.py --post-agent`;
- `scripts/close_package.py`;
- `.cursor/hooks/pipeline_guard.py` through the shared `quality_gates` facade.

Hook behavior is advisory. Runner behavior is enforcing when the policy mode and
gate result mark a blocker.

## Concurrency And HITL

Concurrency controls:

- `scripts/run_autonomous.py` rejects a new run when
  `pipeline_lock.package_run_conflict(package_id)` finds another live PID entry
  for the same package in `logs/autonomous_runs/current/<pid>.json`;
- `scripts/run_autonomous.py` wraps `doc/current_task.md` writes with
  `pipeline_lock.file_lock(doc/current_task.md.lock)`;
- `pipeline_lock.file_lock()` releases by removing the lock file in `finally`
  and removes stale lock files after the TTL.

**Exit codes (operational):** parallel run for the same `--package` (`package_run_conflict`) and failure to acquire `doc/current_task.md` during GUI task write terminate with **`9`** (`pipeline_lock_conflict` in `policies/failure_classes.yaml`). Post-agent success is **`0`** (stop) or **`10`** (continue `--non-stop` chain in the same session). Registry/roadmap quality gates blocking closure use **`2`**; malformed CLI / non-stop policy / post-agent context gate use **`8`**. Canonical matrix: [run_autonomous_prompt.md](run_autonomous_prompt.md), [zero_click_delivery_analysis.md](../../archive/doc_team_workflow/archive/zero_click_delivery_analysis.md).

HITL policy:

- `enable_gate_enforcing` requires approval before switching gates from shadow
  to enforcing;
- `git_push` requires approval before changing remote repository state;
- `close_without_dod` requires approval before package closure can skip DoD.

`scripts/close_package.py --skip-dod` and contracts with no `DOD_COMMANDS`
are blocked unless the caller passes `--approve-close-without-dod` after
explicit human approval.

## Evals

Deterministic adversarial evals live in `scripts/adversarial_eval.py` with
cases in `policies/adversarial_eval_cases.yaml`.

The default suite covers:

- command guard blocks for destructive git and shell chaining;
- HITL approval enforcement for dangerous gate changes;
- skill routing and prompt routing, including default fallback route;
- pipeline guard negatives for write-set drift, retry budget, and stale result;
- proof bundle tampering via checksum mismatch.

## Thin Task And Context Pack

GUI task generation uses:

- `doc/current_task.md` for short execution instructions and `## Write-Set`;
- `doc/context_pack.md` for large spilled prompt/context payloads.

The `## Write-Set` section must remain in `doc/current_task.md`; the write-set
drift gate reads that file directly.

## Observability

Use:

```powershell
.\.venv\Scripts\python.exe scripts\pipeline_status.py
.\.venv\Scripts\python.exe scripts\pipeline_status.py --json
```

The JSON output includes:

- `runs[]`: recent autonomous run timeline;
- `stats.closure_success_rate`;
- `stats.false_closure_rate`;
- `stats.prompt_injection_block_rate`;
- `stats.median_duration_s`;
- `stats.failure_class_counts`.

The pretty output surfaces the same SLO names so operators can compare CLI and
JSON output directly.

## Replay And Proof

- Build proof: `scripts/proof_bundle.py`.
- Validate proof: `proof_bundle.validate(package_id, run_id=...)`.
- Replay dry-run: `scripts/replay_run.py --dry-run <manifest>`.

Missing legacy `execution_contract.md` in `--post-agent` remains exit `3`.
Missing/tampered proof manifest after legacy proof is a gate failure with exit
`2` and `PROOF_MISSING`/`PROOF_TAMPERED` event names.

## Regression Command

Default control-plane regression:

```powershell
.\scripts\run_control_plane_regression.ps1
```

Optional modes:

```powershell
.\scripts\run_control_plane_regression.ps1 -FullPytest
.\scripts\run_control_plane_regression.ps1 -AppSmokeE2E
.\scripts\run_control_plane_regression.ps1 -NightlyE2E
.\scripts\run_control_plane_regression.ps1 -ReportPath archive\team_artifacts\_regression\manual.json
```

Default mode intentionally skips full app browser smoke because the control
plane is covered by script/API tests. Use `-AppSmokeE2E` when investigating the
broader app-level smoke suite.

Reports are written to:

```text
archive/team_artifacts/_regression/control_plane_<timestamp>.json
```

Regression reports are generated artifacts and are ignored by git.

## Targeted Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_failure_classifier.py tests/test_pipeline_events.py tests/test_run_autonomous_result_json.py tests/test_pipeline_status.py tests/test_quality_gates.py tests/test_pipeline_guard_hook.py tests/test_pipeline_guard_logic.py tests/test_pipeline_lock.py tests/test_hitl_approval.py tests/test_proof_bundle.py tests/test_close_package_guards.py tests/test_run_autonomous_agent_chain.py tests/test_adversarial_eval.py tests/test_prompt_routing_registry.py tests/test_skills_router.py tests/test_prompt_utils.py tests/test_write_set_check.py -q
.\.venv\Scripts\python.exe scripts\check_backlog_drift.py
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --strict
.\.venv\Scripts\python.exe scripts\roadmap_sync_check.py
```

Optional — line coverage for `run_autonomous.py` (requires `pytest-cov`; listed in `requirements.txt`):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_run_autonomous_agent_chain.py tests/test_run_autonomous_cost_summary.py tests/test_failure_classifier.py --cov=run_autonomous --cov-report=term-missing -q
```
