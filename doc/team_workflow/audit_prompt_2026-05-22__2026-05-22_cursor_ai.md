# CLOSED PACKAGES AUDIT — 2026-05-22..2026-05-22 [cursor_ai]

╔══════════════════════════════════════════════════════════════╗
║  CLOSED PACKAGES AUDIT — 2026-05-22..2026-05-22 [cursor_ai] ║
║  Depth: index_only | Scope: closed                           ║
╚══════════════════════════════════════════════════════════════╝

This is a self-contained audit prompt. Do not re-read the generator.
Run steps A → D in order. Process one package at a time.

── PACKAGE LIST (from registry + index cross-check) ────────────
| # | Package ID | Title | Registry | CI Entries | US Sync | Pre |
|---|------------|-------|----------|------------|---------|-----|
| 1 | epoch-ssr-source-coverage-route-guard-v1 | Source-Coverage Route Guard: при низком retrieval_confidence или недостаточном source coverage SSR не предлагает quiz/tutor как primary... | OK | OK | OK | PASS |
────────────────────────────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP A — INDEX CONSISTENCY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each package <id> in the PACKAGE LIST above:

A.1 Registry entry:
  Verify doc/backlog_registry.yaml contains:
    status: closed
  → Registry: OK

A.2 closed_iterations.md entry:
  Expect a closure heading `### <id> — YYYY-MM-DD` with date in [2026-05-22, 2026-05-22] or nearby.
  → CI Index: OK

A.3 User story consistency:
  Check that US-20.1 and US-11.2 are closed in doc/user_stories_index.json.
  → US Index: OK

A.4 CJM consistency:
  Check that the corresponding moments are marked completed in doc/cjm.md.
  → CJM: OK

Record result: A_RESULT[epoch-ssr-source-coverage-route-guard-v1] = {registry: OK, ci_index: OK, us_index: OK, cjm: OK}

INDEX_PASS[epoch-ssr-source-coverage-route-guard-v1] = true
Proceed to Step B.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP B — DoD COVERAGE + REPLAY  [skipped because DEPTH == index_only]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DoD Replay is skipped for DEPTH == index_only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP C — REVERT PROCEDURE  [skipped because INDEX_PASS == true]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Skipped.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP D — FINAL AUDIT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Print structured markdown report:

## Closed Packages Audit — 2026-05-22..2026-05-22

| Package | Index Sync | DoD Replay | Verdict | Action |
|---------|:----------:|:----------:|:-------:|--------|
| epoch-ssr-source-coverage-route-guard-v1 | ✅ OK | ⏭️ skipped | PASS | none |

**Summary:** 1 total | 1 PASS | 0 FAIL | 0 STALE | 0 REOPENED

Save report to: archive/team_artifacts/audit_2026-05-22__2026-05-22/audit_report.md
Update raw audit state in: archive/team_artifacts/audit_2026-05-22__2026-05-22/_audit_raw.json
