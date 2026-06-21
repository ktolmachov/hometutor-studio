# Autonomous Delivery Control Plane v2 — Implementation Plan

## Context

The current `run_autonomous` pipeline is already a self-propagating loop with hard gates, DoD cache, closure modes, two-state Cursor hook (`pipeline_guard.py`), and budget profiles. But critical decisions still flow through **markdown semantics + exit-code interpretation**: the agent reads stdout strings like "§Now empty — promoting X" or "DoD drift" and decides what to do. This is fragile and silently drifts when wording changes.

The breakthrough is to convert the pipeline from "prompt tells the agent what to do" to **"deterministic control plane decides; agent only executes the current task"**. Concretely:

- State lives in `pipeline_state.json`, not in scattered markdown.
- Every `--post-agent` exit emits `result.json` with `event`, `severity`, `next_action`, `requires_human`.
- Closure requires a `proof_bundle/` manifest, not self-attestation.
- Stop hook gates on freshness of proof + write-set conformance, not just existence of `execution_contract.md`.
- Agent reads only `current_task.md` + `current_task.meta.json`; everything else is for scripts.

This plan reflects what already exists (exit codes 0–7, hard gates, two-state hook, dod_cache.json, execution_contract.md) and only fills genuine gaps.

---

## Inventory snapshot (verified 2026-04-27)

| Component | Status | Notes |
|---|---|---|
| `scripts/run_autonomous.py` | exists, 2355 lines | exit codes 0–7 used; `post_agent` at line ~1170 |
| `scripts/close_package.py` | exists, 1186 lines | `ClosePackageArgs` dataclass; closes 6 docs |
| `scripts/pipeline_status.py` | exists, 214 lines | reports active package + DoD; no `--json` mode |
| `.cursor/hooks/pipeline_guard.py` | exists, 105 lines | STATE A/B reactive hook; no proof-freshness check |
| `doc/team_workflow/run_autonomous.md` | 61 lines | **already slim** — keep as architectural doc |
| `doc/team_workflow/run_autonomous_prompt.md` | 49 lines | **already slim** — extract exit-code table to runbook |
| `archive/team_artifacts/<id>/execution_contract.md` | exists per package | proto-proof; markdown only |
| `archive/team_artifacts/<id>/dod_cache.json` | exists per package | `cache_key`, `result`, `commands` |
| `pipeline_state.json` | **missing** | core gap |
| `logs/autonomous_runs/<run_id>/result.json` | **missing** | core gap |
| `schemas/*.schema.json` | **missing** | core gap |
| `proof_bundle/manifest.json` | **missing** | extends existing dod_cache.json |
| `doc/current_task.meta.json` | **missing** | machine twin of current_task.md |
| `doc/team_workflow/prompts_registry.yaml` | **missing** | catalog drift unguarded |

---

## Sequenced backlog (10 packages)

Critical path is P0 (1→2→3). Everything else can parallelize after P0 lands. Pacing: one P0 per wave, max 5 packages per non-stop wave (per existing `process.md` arch-review-every-3 rule).

### P0-1. `epoch-control-plane-v2-core` — JSON event protocol [START HERE]

**Goal:** every `--post-agent` exit produces `logs/autonomous_runs/<run_id>/result.json` with structured `event`, `severity`, `next_action`, `requires_human`. Stop relying on stdout string parsing.

**Write-set:**
- `scripts/run_autonomous.py` — wrap `post_agent()` return path so all 8 exit branches (codes 0–7) emit result.json before exit.
- `scripts/pipeline_events.py` *(new)* — `Event` dataclass, `emit(run_id, event, severity, next_action, ...)`, `latest_result_path()`.
- `scripts/pipeline_state.py` *(new)* — read/write `pipeline_state.json`, atomic via tmp+rename.
- `schemas/pipeline_result.schema.json` *(new)* — JSON Schema draft 2020-12.
- `schemas/pipeline_state.schema.json` *(new)*.
- `tests/test_pipeline_events.py` *(new)* — schema validation, atomic write, latest symlink.
- `tests/test_run_autonomous_result_json.py` *(new)* — every exit code 0–7 emits valid result.json.
- `doc/team_workflow/run_autonomous_runbook.md` *(new)* — extracted exit-code table from `run_autonomous_prompt.md`.
- `doc/team_workflow/run_autonomous_prompt.md` — replace exit-code semantics block with a one-line pointer to runbook + result.json.

**DoD:**
```
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_events.py tests/test_run_autonomous_result_json.py -v
.\.venv\Scripts\python.exe scripts/run_autonomous.py --smoke --budget-profile strict
.\.venv\Scripts\python.exe scripts/pipeline_status.py --json
test -f logs/autonomous_runs/latest/result.json
```

**Acceptance:**
- Every exit branch (0,1,2,3,4,5,6,7) writes result.json before returning.
- `result.json` validates against schema.
- `requires_human=true` ⇒ non-stop loop exits cleanly.
- `run_autonomous_prompt.md` contains no exit-code table (moved to runbook).

**Reuse:** existing exit codes; existing `post_agent()` at `scripts/run_autonomous.py:1170`; existing `dod_cache.json` format for `dod_result` field.

---

### P0-2. `epoch-proof-bundle-closure-gate`

**Goal:** `close_package.run_close_package_impl()` refuses closure unless `proof_bundle/manifest.json` is valid. Existing `execution_contract.md` and `dod_cache.json` get folded into the bundle.

**Write-set:**
- `scripts/close_package.py` — add `_validate_proof_bundle(package_id) -> tuple[bool, list[str]]`, gate `run_close_package_impl` on it (skippable via existing `force=True`).
- `scripts/proof_bundle.py` *(new)* — `build_manifest(package_id)`: collects test_output.txt, changed_files.txt, git_diff_stat.txt, dod_result.json (from dod_cache), budget_report.json.
- `schemas/proof_manifest.schema.json` *(new)*.
- `scripts/run_autonomous.py::post_agent` — call `proof_bundle.build_manifest(package_id)` before `close_package`.
- `tests/test_proof_bundle.py` *(new)*.
- `tests/test_close_package.py` — extend with proof-gate cases.

**DoD:**
```
.\.venv\Scripts\python.exe -m pytest tests/test_proof_bundle.py tests/test_close_package.py -v
.\.venv\Scripts\python.exe scripts/run_autonomous.py --smoke --budget-profile strict
test -f archive/team_artifacts/<smoke_pkg>/proof_bundle/manifest.json
```

**Acceptance:** closure without bundle fails with `event=PROOF_MISSING`. `--force` still works for human override.

**Reuse:** `archive/team_artifacts/<id>/execution_contract.md` becomes `proof_bundle/execution_contract.md`; `dod_cache.json` becomes `proof_bundle/dod_result.json`.

---

### P0-3. `epoch-hook-final-step-gate` — proof-freshness stop hook

**Goal:** `pipeline_guard.py` blocks Cursor stop not just when `execution_contract.md` is missing, but also when (a) `pipeline_state.state == EXECUTING` and there's no `result.json` newer than the latest `git diff` mtime, (b) write-set diverges from `current_task.meta.json::allowed_write_set`, (c) retry budget exceeded.

**Write-set:**
- `.cursor/hooks/pipeline_guard.py` — extend STATE detection with proof-freshness + write-set conformance + retry-budget checks.
- `scripts/write_set_check.py` *(new)* — `check_write_set(allowed: list[str], actual: list[str]) -> Verdict`.
- `doc/current_task.meta.json` — generated alongside `current_task.md` by `run_autonomous.py`.
- `scripts/run_autonomous.py` — emit `current_task.meta.json` next to `current_task.md`.
- `tests/test_pipeline_guard.py` *(new — currently no tests for the hook)*.

**DoD:**
```
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_guard.py tests/test_write_set_check.py -v
.\.venv\Scripts\python.exe .cursor/hooks/pipeline_guard.py < tests/fixtures/cursor_stop_event.json
```

**Acceptance:** hook returns `followup_message` for each scenario: missing proof, stale proof, write-set drift, retry exceeded.

**Reuse:** existing `pipeline_guard.py:105` STATE A/B logic — extend, don't rewrite.

---

### P1-4. `epoch-failure-classifier`

**Goal:** every exit code maps to a named failure class with declarative `next_action`. Built on P0-1 result.json.

**Write-set:**
- `scripts/failure_classifier.py` *(new)* — class table (`RETRYABLE_SYNC_LAG`, `CONTRACT_MISSING`, `DOD_DRIFT`, `DOD_FAIL`, `HARD_GATE`, `WRITE_SET_VIOLATION`, `BUDGET_BLOCK`, `ENV_ERROR`).
- `doc/team_workflow/run_autonomous_policy.yaml` *(new)* — class → policy mapping (`max_retries`, `requires_human`, `next_command`).
- `scripts/run_autonomous.py` — non-stop loop reads `result.next_action` instead of inferring from exit code.

**DoD:** `pytest tests/test_failure_classifier.py -v`

---

### P1-5. `epoch-prompt-routing-registry`

**Goal:** `prompts_registry.yaml` is single source of truth for prompt routing; validator catches drift.

**Write-set:**
- `doc/team_workflow/prompts_registry.yaml` *(new)* — every prompt with `input_state`, `output_artifacts`, `forbidden_when`.
- `scripts/validate_prompt_routes.py` *(new)*.
- `doc/team_workflow/prompts_catalog.md` — add machine-readable section pointer.

**DoD:** `python scripts/validate_prompt_routes.py` exits 0; broken-link test fails as expected on synthetic drift.

---

### P1-6. `epoch-quality-gates-matrix`

**Goal:** unify pre-closure gates into one `quality_gates.run_all(package_id) -> GateReport`. Replaces ad-hoc checks scattered across `close_package.py`.

**Write-set:**
- `scripts/quality_gates.py` *(new)* — write-set, read-set, DoD, docs-sync, security, budget regression.
- `scripts/close_package.py` — call `quality_gates.run_all()` before doc updates.

---

### P1-7. `epoch-thin-current-task`

**Goal:** `current_task.md` ≤ 250 lines; rich context moved to `archive/team_artifacts/<id>/context_pack.md`.

**Write-set:**
- `scripts/generate_next_prompt.py` (or wherever `current_task.md` is generated) — split output into thin handoff + context pack.
- `scripts/run_autonomous.py` — emit both files.

---

### P1-8. `epoch-skills-jit-router`

**Goal:** `skills_router.yaml` triggers JIT skill loading per task; main prompt stays small.

**Write-set:**
- `doc/team_workflow/skills_router.yaml` *(new)* — first 5 triggers (FastAPI, llama-index RAG, eval/judge, SQLite, ingestion).
- `scripts/skills_router.py` *(new)*.

---

### P2-9. `epoch-nonstop-wave-policy`

**Goal:** safer non-stop. Replace `--non-stop-max-next-tasks 50` default with wave policy: `max_tasks_per_wave: 5`, `max_minutes: 90`, `require_arch_review_after_closed: 3`, auto-stop on `budget_margin_below_chars: 7000`.

**Write-set:**
- `doc/team_workflow/run_autonomous_policy.yaml` — wave section.
- `scripts/run_autonomous.py` — enforce in non-stop loop.

---

### P2-10. `epoch-autonomous-observability-dashboard`

**Goal:** `pipeline_status.py --json` returns last run, state, package, next_action, p95 cycle time. Builds run timeline from `logs/autonomous_runs/`.

**Write-set:**
- `scripts/pipeline_status.py` — add `--json` flag.
- `scripts/pipeline_timeline.py` *(new)* — aggregates `logs/autonomous_runs/*/result.json`.

---

## Critical files to modify

| File | Why |
|---|---|
| `scripts/run_autonomous.py:1170` (`post_agent`) | emit result.json on every exit branch (P0-1) |
| `scripts/close_package.py` | proof-bundle gate (P0-2), quality gates (P1-6) |
| `.cursor/hooks/pipeline_guard.py` | freshness + write-set checks (P0-3) |
| `doc/team_workflow/run_autonomous_prompt.md` | move exit-code table out (P0-1) |
| `doc/team_workflow/run_autonomous.md` | already slim — only adds pointers to new schema/runbook docs |

## Files to create

```
schemas/pipeline_result.schema.json
schemas/pipeline_state.schema.json
schemas/proof_manifest.schema.json
scripts/pipeline_events.py
scripts/pipeline_state.py
scripts/proof_bundle.py
scripts/failure_classifier.py
scripts/quality_gates.py
scripts/write_set_check.py
scripts/validate_prompt_routes.py
scripts/skills_router.py
scripts/pipeline_timeline.py
doc/team_workflow/run_autonomous_runbook.md
doc/team_workflow/run_autonomous_policy.yaml
doc/team_workflow/prompts_registry.yaml
doc/team_workflow/skills_router.yaml
doc/current_task.meta.json  (generated, not committed)
logs/autonomous_runs/<run_id>/result.json  (generated, not committed)
```

## Reuse (don't reinvent)

- Exit codes 0–7 — already structured; classify rather than renumber.
- `dod_cache.json` schema — fold into proof_bundle as `dod_result.json`.
- `execution_contract.md` — keep, move under `proof_bundle/`.
- `pipeline_guard.py` STATE A/B — extend, don't rewrite.
- `ClosePackageArgs` dataclass — add `skip_proof_gate` flag, mirror existing `force`/`skip_dod` patterns.
- `closure_mode_src_from_git_paths` in `prompt_utils.py` — reuse for proof bundle build.

---

## Verification (end-to-end after P0-1+P0-2+P0-3)

```bash
# 1. Smoke run produces result.json
.\.venv\Scripts\python.exe scripts/run_autonomous.py --smoke --budget-profile strict
test -f logs/autonomous_runs/latest/result.json
python -c "import json,jsonschema; jsonschema.validate(json.load(open('logs/autonomous_runs/latest/result.json')), json.load(open('schemas/pipeline_result.schema.json')))"

# 2. Smoke closure produces proof bundle
test -f archive/team_artifacts/epoch-demo/proof_bundle/manifest.json

# 3. Hook blocks stop when proof stale
echo '{"event":"stop"}' | .\.venv\Scripts\python.exe .cursor/hooks/pipeline_guard.py | grep -q "followup_message"

# 4. JSON status
.\.venv\Scripts\python.exe scripts/pipeline_status.py --json | python -c "import sys,json; r=json.load(sys.stdin); assert 'state' in r and 'next_action' in r"

# 5. Test suite
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_events.py tests/test_run_autonomous_result_json.py tests/test_proof_bundle.py tests/test_pipeline_guard.py -v
```

## Risks & guardrails

1. **Backward compat of `--post-agent`** — existing automation calls it. Keep stdout/exit code behavior identical; result.json is additive.
2. **Schema churn** — version schemas (`$id` with `/v1/`) so future changes don't break in-flight runs.
3. **Hook regressions** — extending `pipeline_guard.py` risks breaking Cursor flow. Add `tests/test_pipeline_guard.py` BEFORE extending (test-first for the hook is non-negotiable since there are zero tests today).
4. **Proof bundle on legacy packages** — `--force` escape hatch in `close_package.py`; document in runbook.
5. **Token budget** — `run_autonomous.md` and `run_autonomous_prompt.md` are already slim (61/49 lines). Don't rewrite them; just trim the exit-code table out of the prompt.
6. **Single-package scope** — P0-1 alone is ~6 files + 2 tests + 2 docs. Each P0 ships independently; do not bundle.

## Outcome

After P0-1..P0-3, the pipeline shifts from text-driven to event-driven:
- Agent reads only `current_task.md` + meta.json.
- Scripts decide via `pipeline_state.json` + `result.json`.
- Closure requires durable proof.
- Stop hook gates on freshness, not just file existence.

The remaining P1/P2 packages are quality multipliers; they don't unlock new behavior, they reduce drift and operator load.
