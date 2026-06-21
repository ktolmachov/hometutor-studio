# DoD test coverage analysis — 2026-05 / Cursor AI

Scope: closed packages with `last_review` / `closed_date` intersecting 2026-05 per `doc/backlog_registry.yaml`.

Refresh after each coverage group, `_audit_raw.json` update, or `dod_commands`/test change.

## Summary

- Packages in period: 34
- DoD replay (registry `dod_commands`): 33 PASS, 1 FAIL (`epoch-home-mode-preview-drawer`)
- Coverage groups completed in raw JSON: 3 (`group_01`–`group_03`) — 15 packages
- Next unresolved group: `group_04` (home mode; preview-drawer FAIL blocks PASS)
- Groups not started: `group_05`–`group_08`

## Package findings

| Package | Wave / group | DoD replay | Group coverage |
|---|---|---|---|
| `epoch-e5-0-versioned-learner-profile-history` | E5 / group_01 | PASS | PASS |
| `epoch-e5-1-migration-safe-mastery-rehydrate` | E5 / group_01 | PASS | PASS |
| `epoch-e5-2-learner-profile-history-api` | E5 / group_01 | PASS | PASS |
| `epoch-e5-3-learner-migration-metrics` | E5 / group_01 | PASS | PASS |
| `epoch-e5-4-learner-migration-slo-alert` | E5 / group_01 | PASS | PASS |
| `epoch-e5-5-learner-migration-gate-command` | E5 / group_01 | PASS | PASS |
| `epoch-e5-6-learner-migration-smoke-command` | E5 / group_01 | PASS | PASS |
| `epoch-e5-7-learner-migration-ci-gate` | E5 / group_01 | PASS | PASS |
| `epoch-e5-8-learner-lineage-sync-on-activation` | E5 / group_01 | PASS | PASS |
| `epoch-e7-0-production-health-bootstrap` | E7 / group_02 | PASS | PASS |
| `epoch-e7-1-tutor-gate-reliability` | E7 / group_02 | PASS | PASS |
| `epoch-e7-2-eval-artifact-retention` | E7 / group_02 | PASS | PASS |
| `epoch-e7-3-gate-triage-automation` | E7 / group_02 | PASS | PASS |
| `epoch-e8-1-cjm-outcome-discipline` | E8 / group_03 | PASS | PASS |
| `epoch-e8-2-active-backlog-cleanup` | E8 / group_03 | PASS | PASS |
| `epoch-home-mode-card-labels` | home / group_04 | PASS | OPEN |
| `epoch-home-mode-flashcard-time-badge` | home / group_04 | PASS | OPEN |
| `epoch-home-mode-preview-drawer` | home / group_04 | FAIL | OPEN |
| `epoch-home-mode-intent-ordering` | home / group_04 | PASS | OPEN |
| `epoch-course-recovery-budget-slider` | course / group_05 | PASS | OPEN |
| `epoch-course-next-session-promise` | course / group_05 | PASS | OPEN |
| `epoch-course-confidence-dip-detector` | course / group_05 | PASS | OPEN |
| `epoch-cjm-progress-next-action` | CJM / group_05 | PASS | OPEN |
| `epoch-run-autonomous-token-registry` | token / group_06 | PASS | OPEN |
| `epoch-check-llm-context-gate-token-registry` | token / group_06 | PASS | OPEN |
| `epoch-generate-orchestration-prompt-token-registry` | token / group_06 | PASS | OPEN |
| `epoch-check-backlog-drift-token-registry` | token / group_06 | PASS | OPEN |
| `epoch-ocr-docling-ingest-phase1` | ingest / group_07 | PASS | OPEN |
| `epoch-ocr-docling-story-gate` | ingest / group_07 | PASS | OPEN |
| `epoch-us-2.3-non-text-corpus-contract` | ingest / group_07 | PASS | OPEN |
| `epoch-answer-trust-to-learning-path` | misc / group_08 | PASS | OPEN |
| `epoch-course-retention-polish` | misc / group_08 | PASS | OPEN |
| `epoch-backlog-active-wave-determinism` | misc / group_08 | PASS | OPEN |
| `epoch-source-readiness-diagnostic-story` | misc / group_08 | PASS | OPEN |

### FAIL detail

- `epoch-home-mode-preview-drawer`: Playwright smoke `tests/e2e/home_mode_selection.spec.ts` — `@smoke secondary tools expander works` — `getByText(/История вопросов/i)` not visible within 30s.
