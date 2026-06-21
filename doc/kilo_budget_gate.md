# Kilo Budget Gate — predict-and-prevent regression guard

Fast, local gate that catches workflow-launcher budget regressions **before
the commit lands**. No Kilo GUI, no relay, no network. Runs in ~100–300ms.

## What it does

For each of the four governed launchers:

- `doc/team_workflow/generate_orchestration_prompt.md`
- `doc/team_workflow/generate_plan_next_prompt.md`
- `doc/team_workflow/generate_resume_prompt.md`
- `doc/team_workflow/generate_execution_prompt_auto.md`

the gate:

1. Reads the HEAD version of the launcher (via `git show HEAD:<path>`).
2. Reads the staged index snapshot of the launcher for real commit-time checks.
3. Uses the worktree only in `--dry-run` mode.
4. Builds a synthetic payload in both cases using the same committed or staged fixture snapshot that the pending commit would contain.
5. Calls the same `evaluate_guard()` that `scripts/kilo_proxy_relay.py` uses at runtime (single source of truth — see [`scripts/_kilo_guard.py`](../scripts/_kilo_guard.py)).
6. Fails the commit if:
   - any launcher transitioned to a worse level (`ok → warn`, `warn → soft_block`, etc.), **or**
   - any launcher is already at `soft_block` or `hard_block` in the staged candidate.

## Running it

```bash
# Gate the pending commit (fails if regression found)
python scripts/kilo_budget_gate.py

# Report current levels only, never fail
python scripts/kilo_budget_gate.py --dry-run

# Machine-readable output
python scripts/kilo_budget_gate.py --json

# Use env-driven thresholds instead of built-in defaults
python scripts/kilo_budget_gate.py --thresholds-from-env
```

## Installing as a pre-commit hook

Recommended: install the `pre-commit` framework and activate the hook from [`.pre-commit-config.yaml`](../.pre-commit-config.yaml):

```bash
pip install pre-commit
pre-commit install
```

After that, `git commit` automatically runs the gate when workflow docs, the injection fixture, core guard files, or the gate stack itself change.

## Overriding a single commit

When you know the regression is intentional (e.g. adding a genuinely needed section that pushes the launcher into `warn`):

```bash
KILO_BUDGET_GATE=skip git commit -m "..."
# or
git commit --no-verify -m "..."
```

Both are logged; neither is silent.

## When gate fails — how to investigate

The gate tells you exactly which launcher regressed and by how many chars. To see which **message-level contributor** is the driver:

```bash
python scripts/kilo_budget_simulate.py simulate \
    --launcher doc/team_workflow/generate_plan_next_prompt.md \
    --injection fixtures/kilo_injection_baseline.json \
    --user-turn "plan next" \
    --attribute --section-attribute
```

`--attribute` показывает вклад на уровне messages, а `--section-attribute` — внутри самого launcher по `##`/`###` секциям.

## Refreshing the injection fixture

Committed fixture (`fixtures/kilo_injection_baseline.json`) is the version-controlled source used by the gate by default.
If `fixtures/kilo_injection_captured.json` exists, gate automatically prefers it as authoritative source.
A calibrated fixture is an approximation and should stay separate.

```bash
# After running the v1 probe harness and getting real logs/kilo_relay.jsonl:
python scripts/kilo_budget_simulate.py capture \
    --from-jsonl logs/kilo_relay.jsonl \
    --probe ORCH-LAUNCHER \
    -o fixtures/kilo_injection_captured.json
```

Commit the updated fixture separately from any launcher changes so the diff stays easy to review.
Подробный пошаговый процесс: [`doc/kilo_budget_capture_runbook.md`](kilo_budget_capture_runbook.md).

## Relationship to the v1 probe harness

- **v1 probe** (`scripts/kilo_budget_probe.py`) — authoritative runtime capture via real Kilo sessions. Slow, manual, occasionally needed to refresh the injection fixture.
- **This gate** — fast, static, deterministic. Catches regressions on every commit before they reach runtime.

The two share the exact same guard logic (`scripts/_kilo_guard.py`), so by construction the gate and the probe cannot disagree on verdicts for an identical payload.

## Thresholds

Defaults (from `GuardThresholds`):

| Threshold | Value | Triggers |
|---|---|---|
| warn_body_chars | 70,000 | `warn` |
| max_body_chars | 90,000 | `soft_block` |
| hard_block_body_chars | 110,000 | `hard_block` |
| max_messages | 15 | `soft_block` |
| max_largest_message_chars | 24,000 | `warn` |
| max_tools | 13 | `warn` |

These can be overridden via the same env vars the relay uses (`KILO_RELAY_WARN_BODY_CHARS`, etc.) by passing `--thresholds-from-env`.

## Verification

```bash
pytest tests/test_kilo_guard.py tests/test_kilo_budget_simulate.py tests/test_kilo_budget_gate.py -q
```

The gate itself now has focused tests for staged-vs-worktree behavior and staged fixture loading.
