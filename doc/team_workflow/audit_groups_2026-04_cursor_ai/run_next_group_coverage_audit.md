# Audit Group Analysis ? 2026-04 / Cursor AI

Source prompt: `archive/doc_team_workflow/audit_prompt_2026-04_cursor_ai.md`

Coverage completion prompt: `archive/doc_team_workflow/audit_coverage_prompt_2026-04_cursor_ai.md`  
Static DoD coverage analysis: `coverage_dod_analysis.md`

## Next Action

Completed coverage groups: `group_01`, `group_02`, `group_03`, `group_04`, `group_05`, `group_06`, `group_07`, `group_08`, `group_09`, `group_10`, `group_11`, `group_12`, `group_13`, `group_14`, `group_15`.

All groups completed.

Recommended final run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-04 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-04/audit_chain_state.json
```

After each group, run:

```powershell
.\.venv\Scripts\python.exe scripts/check_audit_chain_state.py --period 2026-04 --target-agent cursor_ai --write-next-action --write-summary --write-raw-check --json-out archive/team_artifacts/audit_2026-04/audit_chain_state.json
```

The next group is safe to start only after the check is PASS or any reported
FAIL is intentionally resolved.

## Coverage Analysis Refresh

Refresh `coverage_dod_analysis.md` after:

- any group coverage report is completed;
- `archive/team_artifacts/audit_2026-04/_audit_raw.json` receives or changes `coverage_groups["group_<NN>"]`;
- `doc/backlog_registry.yaml` `dod_commands` changes;
- tests, e2e specs, fixtures, eval data, or package coverage status changes.

A completed group with PASS packages in `_audit_raw.json` must no longer appear as open gaps in `coverage_dod_analysis.md`.

## Grouping Rule

Primary safe groups use wave/dependency relations, with one deliberate exception: all standalone packages that have no `wave_id` are merged into a single `no-wave` audit group. Packages without a wave that are already connected to a wave by `depends_on` stay inside that wave group. CJM and US are analyzed and embedded into group files as cross-check metadata, but CJM is not used as a hard merge edge because broad moments such as `#2 First Answer` and `#10 Retrieval trust` would merge most of the audit into one oversized group.

## Statistics

- Packages in source audit: 88
- Audit groups generated: 15
- Wave/dependency groups: 14
- Merged no-wave group: 1 group / 38 packages
- Original standalone no-wave components merged: 37
- Largest group size: 38
- Packages with `wave_id`: 46
- Packages without `wave_id`: 42
- Distinct waves in audit: 16
- Packages with April US coverage: 25
- Packages missing April US coverage: 63
- Packages with CJM moments: 69
- Distinct CJM moments: 23
- CJM moments spanning multiple groups: 12
- US IDs spanning multiple groups: 0
- CI heading misses: 11
- US index misses: 63
- CI and US both missing: 11

Group size distribution:

| Size | Count |
|---:|---:|
| 1 | 4 |
| 2 | 6 |
| 3 | 1 |
| 4 | 1 |
| 12 | 1 |
| 15 | 1 |
| 38 | 1 |

## Generated Group Files

| Group | File | Packages | Waves | CI Miss | US Miss | First Package |
|---:|---|---:|---|---:|---:|---|
| 01 | [group_01_wave-course-learning-v2.md](group_01_wave-course-learning-v2.md) | 15 | wave-course-learning-v2 | 0 | 4 | `epoch-course-workspace-ab` |
| 02 | [group_02_wave-autonomous-control-plane-v1.md](group_02_wave-autonomous-control-plane-v1.md) | 12 | wave-autonomous-control-plane-v1, wave-autonomous-control-plane-v2 | 11 | 12 | `epoch-control-plane-v3-core` |
| 03 | [group_03_wave-interactive-tour.md](group_03_wave-interactive-tour.md) | 4 | wave-interactive-tour | 0 | 0 | `epoch-tour-skeleton-ch1` |
| 04 | [group_04_wave-orchestration-demo.md](group_04_wave-orchestration-demo.md) | 3 | wave-orchestration-demo, wave-retention-demo | 0 | 2 | `epoch-demo-scenario-06-srs` |
| 05 | [group_05_wave-flashcard-polish.md](group_05_wave-flashcard-polish.md) | 2 | wave-flashcard-polish | 0 | 2 | `epoch-flashcard-deck-mgmt` |
| 06 | [group_06_wave-sync-export.md](group_06_wave-sync-export.md) | 2 | wave-sync-export | 0 | 2 | `epoch-sync-restore-wizard` |
| 07 | [group_07_wave-learning-loop-demo.md](group_07_wave-learning-loop-demo.md) | 2 | wave-learning-loop-demo | 0 | 2 | `epoch-demo-scenario-03-tutor` |
| 08 | [group_08_wave-answer-quality-eval.md](group_08_wave-answer-quality-eval.md) | 2 | wave-answer-quality-eval | 0 | 1 | `epoch-aqe-corpus-choice` |
| 09 | [group_09_wave-agentic-tutor-depth.md](group_09_wave-agentic-tutor-depth.md) | 2 | wave-agentic-tutor-depth | 0 | 0 | `epoch-mastery-gap-routing` |
| 10 | [group_10_wave-production-health.md](group_10_wave-production-health.md) | 2 | wave-production-health | 0 | 1 | `epoch-latency-slo-gate` |
| 11 | [group_11_wave-first-answer-ux.md](group_11_wave-first-answer-ux.md) | 1 | wave-first-answer-ux | 0 | 0 | `epoch-first-answer-examples` |
| 12 | [group_12_wave-plan-visibility.md](group_12_wave-plan-visibility.md) | 1 | wave-plan-visibility | 0 | 1 | `epoch-plan-diff-ux` |
| 13 | [group_13_wave-trust-demo.md](group_13_wave-trust-demo.md) | 1 | wave-trust-demo | 0 | 0 | `epoch-demo-scenario-08-trust` |
| 14 | [group_14_wave-token-safety-ingestion.md](group_14_wave-token-safety-ingestion.md) | 1 | wave-token-safety-ingestion | 0 | 1 | `epoch-ingestion-loader-token-registry` |
| 15 | [group_15_no-wave.md](group_15_no-wave.md) | 38 | none | 0 | 35 | `epoch-micro-quiz-feedback-tail` |

## CJM Cross-Group Links

| CJM Moment | Groups | Packages |
|---|---|---|
| #1 Discover | 03, 15 | `epoch-17-1-ux-tail`, `epoch-tour-skeleton-ch1`, `epoch-tour-demo-doc-refresh` |
| #10 Retrieval trust | 08, 10, 13, 15 | `epoch-context-cart-mvp`, `epoch-answer-quality-eval`, `epoch-demo-scenario-08-trust`, `epoch-aqe-corpus-choice`, `epoch-llm-regression-baseline` |
| #11 Retain | 03, 04, 15 | `epoch-unified-context-layer`, `epoch-demo-scenario-06-srs`, `epoch-tour-scenarios-10-14` |
| #2 First Answer | 03, 08, 10, 11, 15 | `epoch-context-cart-mvp`, `epoch-answer-quality-eval`, `epoch-17-1-ux-tail`, `epoch-cjm-us-frontmatter`, `epoch-first-answer-examples`, `epoch-tour-skeleton-ch1`, `epoch-aqe-corpus-choice`, `epoch-answer-quality-baseline`, `epoch-latency-slo-gate`, `epoch-llm-regression-baseline` |
| #3 Transition to tutor | 03, 07, 09, 15 | `epoch-qa-tutor-handoff`, `epoch-cjm-us-frontmatter`, `epoch-demo-scenario-03-tutor`, `epoch-tour-persistence-ch2-5`, `epoch-mastery-gap-routing`, `epoch-concept-remediation-step` |
| #4 First micro-quiz | 03, 07, 15 | `epoch-5min-loop-polish`, `epoch-micro-quiz-feedback-tail`, `epoch-quiz-hint-on-fail`, `epoch-demo-scenario-04-quiz`, `epoch-tour-persistence-ch2-5` |
| #5 Return next day | 03, 15 | `epoch-us7-3-resume-card`, `epoch-tour-persistence-ch2-5`, `epoch-tour-scenarios-10-14` |
| #6 After reindex | 03, 15 | `epoch-mastery-after-reindex`, `epoch-reindex-mastery-guard`, `epoch-tour-persistence-ch2-5`, `epoch-tour-scenarios-10-14` |
| #7 Progress | 03, 04, 15 | `epoch-unified-context-layer`, `epoch-demo-scenario-07-progress`, `epoch-tour-persistence-ch2-5` |
| #8 Learning plan | 03, 04, 09 | `epoch-demo-scenario-09-learning-plan`, `epoch-tour-persistence-ch2-5`, `epoch-mastery-gap-routing` |
| #9 Master | 01, 03, 09 | `epoch-tour-persistence-ch2-5`, `epoch-tour-scenarios-10-14`, `epoch-concept-remediation-step`, `epoch-e30-e1-course-graduation` |
| infra | 02, 03, 06, 14, 15 | `epoch-sync-restore-wizard`, `epoch-sync-multidevice`, `epoch-tour-scenarios-10-14`, `epoch-control-plane-v3-core`, `epoch-failure-classifier`, `epoch-quality-gates-matrix`, `epoch-prompt-routing-registry`, `epoch-thin-current-task`, `epoch-skills-jit-router`, `epoch-nonstop-wave-policy`, `epoch-agent-evals-layer`, `epoch-adversarial-eval-harness`, `epoch-hitl-approval-protocol`, `epoch-pipeline-concurrency-locks`, `epoch-autonomous-observability-dashboard`, `epoch-ingestion-loader-token-registry`, `epoch-token-registry-measure-reconcile`, `epoch-context-cart-token-metrics` |

## US Cross-Group Links

None. Every April US ID maps to at most one generated group.
