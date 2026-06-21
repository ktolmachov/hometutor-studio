# DoD Test Coverage Analysis ? 2026-04 / Cursor AI

Scope: all closed packages selected by `generate_audit_closed_packages_prompt.md` for `2026-04`.

This is a static completeness audit. It maps package CJM/US intent to explicit test evidence in `dod_commands`, `exit_artifact`, referenced test files, and completed group results from `_audit_raw.json`.

Update rule: refresh this file after every group coverage completion, after updating `_audit_raw.json`, and after any edit to `dod_commands`, tests, e2e specs, fixtures, eval data, or package coverage status.

## Summary

- Packages analyzed: 88
- PASS: 88
- PARTIAL: 0
- STALE/no executable evidence: 0
- Completed coverage packages from `_audit_raw.json`: 88
- Packages with explicit `dod_commands`: 85
- Packages with unit/pytest or CLI/schema evidence: 84
- Packages with e2e/smoke evidence: 73
- GAP_UNIT_OR_CLI: 0
- GAP_E2E_OR_UI_SMOKE: 0
- GAP_DOD_COMMAND: 0

## Wave / Group Rollup

| Wave | Packages | PASS | PARTIAL | STALE | E2E gaps | DoD command gaps | Completed packages |
|---|---:|---:|---:|---:|---:|---:|---:|
| wave-agentic-tutor-depth | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-answer-quality-eval | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-autonomous-control-plane-v1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| wave-autonomous-control-plane-v2 | 11 | 11 | 0 | 0 | 0 | 0 | 11 |
| wave-course-learning-v2 | 11 | 11 | 0 | 0 | 0 | 0 | 11 |
| wave-first-answer-ux | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| wave-flashcard-polish | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-interactive-tour | 4 | 4 | 0 | 0 | 0 | 0 | 4 |
| wave-learning-loop-demo | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-orchestration-demo | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| wave-plan-visibility | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| wave-production-health | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-retention-demo | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-sync-export | 2 | 2 | 0 | 0 | 0 | 0 | 2 |
| wave-token-safety-ingestion | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| wave-trust-demo | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| none | 42 | 42 | 0 | 0 | 0 | 0 | 42 |

## Package Findings

| Package | Wave | CJM | US | Evidence | Gaps | Verdict | Completed group |
|---|---|---|---|---|---|---|---|
| `epoch-5min-loop-polish` | none | #4 First micro-quiz | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-context-cart-mvp` | none | #2 First Answer, #10 Retrieval trust | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-unified-context-layer` | none | #3 Continuity, #7 Progress, #11 Retain | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-qa-tutor-handoff` | none | #3 Transition to tutor | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-answer-quality-eval` | none | #2 First Answer, #10 Retrieval trust | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-micro-quiz-feedback-tail` | none | #4 First micro-quiz | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-17-1-ux-tail` | none | #1 Discover, #2 First Answer | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-cjm-us-frontmatter` | none | #2 First Answer, #3 Transition to tutor, #10 Guided start | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-us7-3-resume-card` | none | #5 Return next day | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-adaptive-plan-today` | none | Adaptive plan | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-quiz-hint-on-fail` | none | #4 First micro-quiz | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-tutor-transparency` | none | #3 Switch to Tutor | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-mastery-after-reindex` | none | #6 After reindex | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-env-required-vars` | none | #1 First launch | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-inline-citations-first-answer` | none | #3 First answer | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-course-workspace-ab` | none | course-workspace | - | dod, e2e | - | PASS | yes |
| `epoch-course-workspace-d` | none | course-workspace | - | dod, e2e | - | PASS | yes |
| `epoch-course-workspace-e` | none | course-workspace | - | dod, e2e | - | PASS | yes |
| `epoch-course-workspace-f` | none | course-workspace | - | dod, e2e | - | PASS | yes |
| `epoch-srs-priority-queue` | none | #7 Spaced repetition due | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-reindex-mastery-guard` | none | #6 After reindex | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-ingest-first-index-progress` | none | - | US-2.1 | dod, unit, e2e | — | PASS | group_15 |
| `epoch-truth-sync` | none | - | US-12.2 | dod, unit, e2e | — | PASS | group_15 |
| `epoch-citations-trust-close` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-srs-priority-reason` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-srs-plan-close` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-reindex-quiz-close` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-backup-benchmark-close` | none | - | US-12.1, US-12.3 | dod, unit, e2e | — | PASS | group_15 |
| `epoch-flashcard-deck-mgmt` | wave-flashcard-polish | #11 Flashcard creation, #12 Flashcard review | - | dod, unit, e2e | — | PASS | group_05 |
| `epoch-flashcard-export-upload` | wave-flashcard-polish | #12 Flashcard review | - | dod, unit, e2e | — | PASS | group_05 |
| `epoch-first-answer-examples` | wave-first-answer-ux | #2 First Answer | US-3.3 | dod, unit, e2e | — | PASS | group_11 |
| `epoch-plan-diff-ux` | wave-plan-visibility | #6 Adaptive plan | - | dod, unit, e2e | — | PASS | group_12 |
| `epoch-sync-restore-wizard` | wave-sync-export | infra | - | dod, unit | — | PASS | group_06 |
| `epoch-sync-multidevice` | wave-sync-export | infra | - | dod, unit | — | PASS | group_06 |
| `epoch-wave-contract` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-router-accuracy-baseline` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-query-service-assembly` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-architecture-review-baseline` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-query-service-assembly-v2` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-flashcard-export-upload-r2` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-plan-next-candidate-seed` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-ui-main-split` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-demo-pipeline-hardening` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-demo-scenario-03-tutor` | wave-learning-loop-demo | #3 Transition to tutor | - | dod, e2e, unit | — | PASS | group_07 |
| `epoch-demo-scenario-04-quiz` | wave-learning-loop-demo | #4 First micro-quiz | - | dod, e2e, unit | — | PASS | group_07 |
| `epoch-demo-scenario-06-srs` | wave-retention-demo | #11 Retain | US-11.1 | e2e, unit | — | PASS | group_04 |
| `epoch-demo-scenario-07-progress` | wave-retention-demo | #7 Progress | - | e2e, unit | — | PASS | group_04 |
| `epoch-demo-scenario-09-learning-plan` | wave-orchestration-demo | #8 Learning plan | - | e2e, unit | — | PASS | group_04 |
| `epoch-demo-scenario-08-trust` | wave-trust-demo | #10 Retrieval trust | US-2.2 | dod, e2e, unit | — | PASS | group_13 |
| `epoch-tour-skeleton-ch1` | wave-interactive-tour | #1 Discover, #2 First Answer | US-1.1, US-1.3 | dod, unit, e2e | - | PASS | yes |
| `epoch-tour-persistence-ch2-5` | wave-interactive-tour | #3 Transition to tutor, #4 First micro-quiz, #5 Return next day, #6 After reindex, #7 Progress, #8 Learning plan, #9 Master | US-13.1, US-14.3, US-15.1, US-15.2, US-15.3, US-15.5, US-5.1, US-5.2, US-6.1, US-6.2, US-6.3, US-7.1, US-7.3, US-7.4, US-9.1 | dod, unit, e2e | - | PASS | yes |
| `epoch-tour-scenarios-10-14` | wave-interactive-tour | #5 Return next day, #6 After reindex, #11 Retain, #9 Master, infra | US-10.1, US-10.2, US-10.3, US-15.4, US-15.6, US-16.0, US-16.1, US-16.2, US-16.3, US-16.4, US-16.5, US-16.6, US-7.2 | dod, e2e, cli/schema | - | PASS | yes |
| `epoch-tour-demo-doc-refresh` | wave-interactive-tour | #1 Discover | US-14.1 | dod, e2e, cli/schema | - | PASS | yes |
| `epoch-aqe-corpus-choice` | wave-answer-quality-eval | #2 First Answer, #10 Retrieval trust | US-3.1, US-3.2 | dod, cli/schema, e2e | — | PASS | group_08 |
| `epoch-answer-quality-baseline` | wave-answer-quality-eval | #2 First Answer | US-3.1, US-3.2, US-12.4 | dod, cli/schema, e2e | — | PASS | group_08 |
| `epoch-mastery-gap-routing` | wave-agentic-tutor-depth | #3 Transition to tutor, #8 Learning plan | US-4.1, US-8.1, US-8.2 | dod, unit, e2e | — | PASS | group_09 |
| `epoch-concept-remediation-step` | wave-agentic-tutor-depth | #3 Transition to tutor, #9 Master | US-14.4, US-4.2, US-9.2 | dod, unit, e2e | — | PASS | group_09 |
| `epoch-latency-slo-gate` | wave-production-health | #2 First Answer | - | dod, cli/schema, e2e | — | PASS | group_10 |
| `epoch-llm-regression-baseline` | wave-production-health | #2 First Answer, #10 Retrieval trust | US-12.4 | dod, cli/schema, e2e | — | PASS | group_10 |
| `epoch-control-plane-v3-core` | wave-autonomous-control-plane-v1 | infra | - | dod, unit, cli/schema | - | PASS | yes |
| `epoch-failure-classifier` | wave-autonomous-control-plane-v2 | infra | - | dod, unit, cli/schema | - | PASS | yes |
| `epoch-quality-gates-matrix` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-prompt-routing-registry` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-thin-current-task` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-skills-jit-router` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-nonstop-wave-policy` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-agent-evals-layer` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-adversarial-eval-harness` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-hitl-approval-protocol` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-pipeline-concurrency-locks` | wave-autonomous-control-plane-v2 | infra | - | dod, unit | - | PASS | yes |
| `epoch-autonomous-observability-dashboard` | wave-autonomous-control-plane-v2 | infra | - | dod, unit, cli/schema | - | PASS | yes |
| `epoch-e30-a1-cockpit-scaffold` | wave-course-learning-v2 | course-workspace | US-17.2 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-a2-cockpit-rotator` | wave-course-learning-v2 | course-workspace | US-17.4 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-b1-graduation-overlay` | wave-course-learning-v2 | course-workspace | US-17.5 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-b2-daily-briefing` | wave-course-learning-v2 | course-workspace | US-17.6 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-c1-diagnostic` | wave-course-learning-v2 | course-workspace | US-17.1 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-c2-pace-engine` | wave-course-learning-v2 | course-workspace | US-17.3 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-d1-smart-resume` | wave-course-learning-v2 | course-workspace | US-17.8 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-d2-focus-mode` | wave-course-learning-v2 | course-workspace | US-17.7 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-e1-course-graduation` | wave-course-learning-v2 | course-workspace, #9 Master | US-17.9 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-idea-1-daily-runway` | wave-course-learning-v2 | course-workspace | US-17.10 | dod, unit, e2e | - | PASS | yes |
| `epoch-e30-idea-2-retrieval-gates` | wave-course-learning-v2 | course-workspace | US-17.11 | dod, unit, e2e | - | PASS | yes |
| `epoch-ingestion-loader-extraction` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-doc-ingestion-split-arch-sync` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-demo` | none | - | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-ingestion-loader-token-registry` | wave-token-safety-ingestion | infra | - | dod, unit, cli/schema | — | PASS | group_14 |
| `epoch-token-registry-measure-reconcile` | none | infra | - | dod, unit, e2e | — | PASS | group_15 |
| `epoch-context-cart-token-metrics` | none | infra | - | dod, unit, e2e | — | PASS | group_15 |

## Required Test Additions

### `epoch-flashcard-deck-mgmt`

- Wave: `wave-flashcard-polish`
- CJM: #11 Flashcard creation, #12 Flashcard review
- US: —
- Completed: `group_05` (`coverage_result` PASS)
- Evidence: `tests/test_flashcard_deck_mgmt.py`; `tests/e2e/flashcard_wave_polish_smoke.spec.ts`; `tests/e2e/flashcards_review_flow.spec.ts`; `dod_commands` в реестре

### `epoch-flashcard-export-upload`

- Wave: `wave-flashcard-polish`
- CJM: #12 Flashcard review
- US: —
- Completed: `group_05` (`coverage_result` PASS)
- Evidence: `tests/test_flashcard_export_upload.py`; `tests/e2e/flashcard_wave_polish_smoke.spec.ts`; `tests/e2e/flashcards_review_flow.spec.ts`; `dod_commands` в реестре

### `epoch-first-answer-examples`

- Wave: `wave-first-answer-ux`
- CJM: #2 First Answer
- US: US-3.3
- Completed: `group_11` (`coverage_result` PASS)
- Evidence: `tests/test_first_answer_examples.py`; `tests/e2e/first_answer_examples_wave_smoke.spec.ts`; `dod_commands` в реестре

### `epoch-plan-diff-ux`

- Wave: `wave-plan-visibility`
- CJM: #6 Adaptive plan
- US: -
- Completed: `group_12` (`coverage_result` PASS)
- Evidence: `tests/test_plan_diff_ux.py`; `tests/test_adaptive_plan_hub.py::test_changed_delta_normalization_keeps_only_current_concepts`; `tests/e2e/plan_diff_ux_wave_smoke.spec.ts`; `dod_commands` в реестре

### `epoch-sync-restore-wizard`

- Wave: `wave-sync-export`
- CJM: infra
- US: —
- Completed: `group_06` (`coverage_result` PASS)
- Evidence: `tests/test_sync_restore_wizard.py`; `dod_commands` в реестре

### `epoch-sync-multidevice`

- Wave: `wave-sync-export`
- CJM: infra
- US: —
- Completed: `group_06` (`coverage_result` PASS)
- Evidence: `tests/test_sync_multidevice.py`; `dod_commands` в реестре

### `epoch-demo-scenario-03-tutor`

- Wave: `wave-learning-loop-demo`
- CJM: #3 Transition to tutor
- US: US-3.1 (registry); покрытие сценария в индексе см. пакет
- Completed: `group_07` (`coverage_result` PASS)
- Covered: YAML storyboard contract `tests/test_demo_scenarios_learning_loop_yaml.py::test_scenario_03_answer_to_tutor_yaml_contract`, demo e2e `tests/e2e/demos/scenario_03_answer_to_tutor.spec.ts`; DoD см. `dod_commands` в `doc/backlog_registry.yaml` и `coverage_groups.group_07` в `_audit_raw.json`.

### `epoch-demo-scenario-04-quiz`

- Wave: `wave-learning-loop-demo`
- CJM: #4 First micro-quiz
- US: -
- Completed: `group_07` (`coverage_result` PASS)
- Covered: YAML storyboard contract `tests/test_demo_scenarios_learning_loop_yaml.py::test_scenario_04_mini_quiz_yaml_contract`, demo e2e `tests/e2e/demos/scenario_04_mini_quiz.spec.ts`; DoD см. `dod_commands` в `doc/backlog_registry.yaml` и `coverage_groups.group_07` в `_audit_raw.json`.

### `epoch-demo-scenario-06-srs`

- Wave: `wave-retention-demo`
- CJM: #11 Retain
- US: US-11.1
- Covered: YAML storyboard contract `tests/test_demo_scenarios_retention_orchestration_yaml.py`, offline JSON `tests/test_offline_payloads_contract.py`, demo e2e `tests/e2e/demos/scenario_06_spaced_repetition.spec.ts`; DoD см. `dod_commands` в `doc/backlog_registry.yaml` и `coverage_groups.group_04` в `_audit_raw.json`.

### `epoch-demo-scenario-07-progress`

- Wave: `wave-retention-demo`
- CJM: #7 Progress
- US: -
- Covered: YAML contract + offline payload scenario_07 + e2e `scenario_07_progress_gaps.spec.ts`; DoD см. реестр / group_04.

### `epoch-demo-scenario-09-learning-plan`

- Wave: `wave-orchestration-demo`
- CJM: #8 Learning plan
- US: -
- Covered: YAML contract + offline payload scenario_09 + e2e `scenario_09_personalized_plan.spec.ts`; DoD см. реестр / group_04.

### `epoch-demo-scenario-08-trust`

- Wave: `wave-trust-demo`
- CJM: #10 Retrieval trust
- US: US-2.2
- Completed: `group_13` (`coverage_result` PASS)
- Covered: YAML contract `tests/test_demo_scenarios_retention_orchestration_yaml.py::test_scenario_08_source_trust_yaml_contract`, offline JSON `tests/test_offline_payloads_contract.py` (`scenario_08.json`), demo e2e `tests/e2e/demos/scenario_08_source_trust.spec.ts`; DoD см. `dod_commands` в `doc/backlog_registry.yaml` и `coverage_groups.group_13` в `_audit_raw.json`.

### `epoch-aqe-corpus-choice`

- Wave: `wave-answer-quality-eval`
- CJM: #2 First Answer, #10 Retrieval trust
- US: US-3.1, US-3.2
- Completed: `group_08` (`coverage_result` PASS)
- Covered: smoke e2e `tests/e2e/aqe_wave_coverage_smoke.spec.ts` (offline Quick Answer → sources/stub); JSON/CLI checks в `dod_commands` реестра; `coverage_groups.group_08` в `_audit_raw.json`.

### `epoch-answer-quality-baseline`

- Wave: `wave-answer-quality-eval`
- CJM: #2 First Answer
- US: US-3.1, US-3.2, US-12.4
- Completed: `group_08` (`coverage_result` PASS)
- Covered: smoke e2e `tests/e2e/aqe_wave_coverage_smoke.spec.ts` (first-answer block + stub); eval/CLI checks в `dod_commands` реестра; `coverage_groups.group_08` в `_audit_raw.json`.

### `epoch-mastery-gap-routing`

- Wave: `wave-agentic-tutor-depth`
- CJM: #3 Transition to tutor, #8 Learning plan
- US: US-4.1, US-8.1, US-8.2
- Completed: `group_09` (`coverage_result` PASS)
- Covered: smoke e2e `tests/e2e/agentic_tutor_depth_smoke.spec.ts` (adaptive plan expander + «Пересчитать план»); pytest в `dod_commands`; `coverage_groups.group_09` в `_audit_raw.json`.

### `epoch-concept-remediation-step`

- Wave: `wave-agentic-tutor-depth`
- CJM: #3 Transition to tutor, #9 Master
- US: US-14.4, US-4.2, US-9.2
- Completed: `group_09` (`coverage_result` PASS)
- Covered: smoke e2e `tests/e2e/agentic_tutor_depth_smoke.spec.ts` (intro remediation verbs); pytest в `dod_commands`; `coverage_groups.group_09` в `_audit_raw.json`.

### `epoch-latency-slo-gate`

- Wave: `wave-production-health`
- CJM: #2 First Answer
- US: -
- Completed: `group_10` (`coverage_result` PASS)
- Covered: smoke e2e `tests/e2e/production_health_wave_smoke.spec.ts` (Quick Answer → первый ответ/stub под оффлайн-стеком); CLI/checks в `dod_commands`; `coverage_groups.group_10` в `_audit_raw.json`.

### `epoch-llm-regression-baseline`

- Wave: `wave-production-health`
- CJM: #2 First Answer, #10 Retrieval trust
- US: US-12.4
- Completed: `group_10` (`coverage_result` PASS)
- Covered: smoke e2e `tests/e2e/production_health_wave_smoke.spec.ts` (блок источников / trust-сигналы под оффлайн-стубом); eval/CLI checks в `dod_commands`; `coverage_groups.group_10` в `_audit_raw.json`.
