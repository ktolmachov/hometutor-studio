# #26 Course Content Gate + Verified Step: Implementation Report

**Волна: #26 P0-A + P0-B · fix-wave после контр-аудита · hometutor runtime · 2026-07-20**

---

## Статус (честный)

| Параметр | Значение |
|---|---|
| Plan | `hometutor-studio/doc/next/course_content_gate_compiler_plan.md` |
| E2 (живой семпл) | ✅ выполнен **до** implementation (2026-07-19) |
| **P0-A Gate Packet** | ✅ shipped (labels + best/rejected + **evidence spans** + UI expander) |
| **P0-B Verified Step** | ✅ partial→fixed: mastery gate + origins; TLRR **plan formula**; answer honesty UI |
| **Full step 6/6 on live bundle** | ⬜ residual: `grounded_explanation` component still unwired → TLRR full-contract often 0 |
| Tests | **82/82 PASS** (`test_course_content_gate` + `test_quiz_content_contract` + `test_trusted_route_rate`) |
| Live reindex on reference bundle | ⬜ not re-run in this session (unit/integration fixtures only) |

---

## Write-set (включая fix-wave)

### Новые

| Файл | Назначение |
|---|---|
| `app/course_content_gate.py` | Gate packet: role/freshness/noise/practice, best-source, **evidence_spans**, lookup API |
| `scripts/run_course_content_gate.py` | Manual runner |
| `scripts/compute_trusted_route_rate.py` | TLRR = **full_contract_steps / competing_topics** (plan formula) |
| `tests/test_course_content_gate.py` | Gate unit/integration |
| `tests/test_quiz_content_contract.py` | Evidence binding + mastery isolation + micro fallback E2E |
| `tests/test_trusted_route_rate.py` | Formula + per-concept verified quiz |

### Изменённые

| Файл | Назначение |
|---|---|
| `app/user_state_db.py` | `quiz_results.origin`, `evidence_bound` (CREATE + migration) |
| `app/user_state_quiz.py` | `save_quiz_result(origin=, evidence_bound=)` |
| `app/prompts/_impl.py` | `QUIZ_SCOPED_PROMPT` + `source_quote` |
| `app/quiz_scoped.py` | normalize `source_quote`; `evidence_bound_for_questions()` exact-match |
| `app/quiz_micro.py` | fallback + micro_llm `evidence_bound=False`; safe handling when SR=None; skip PLM when blocked |
| `app/quiz_service.py` | inline quiz → `origin=inline_quiz`, `evidence_bound=False` |
| `app/fact_source_binding.py` | mastery/SR blocked when `evidence_bound is False` |
| `app/knowledge_graph_bundle.py` | non-fatal content-gate sidecar after quality report |
| `app/ui/living_konspekt_reader.py` | expander «Почему этот фрагмент…» |
| `app/ui/scoped_quiz.py` | all-or-nothing evidence; **warning «не подтверждено»** when mastery blocked |
| `docs/user_guide.md` | honesty of mastery + content gate |

---

## Fix-wave (после контр-аудита) — что исправлено

| Дефект аудита | Исправление |
|---|---|
| TLRR = component share / 6 | **Plan formula:** `full_contract_steps / competing_topics` |
| verified_quiz = global COUNT | Per-concept: `DISTINCT concept WHERE evidence_bound=1` matched to topic |
| evidence_span = «есть path» | Real `evidence_spans[].excerpt` from best-source file; missing → component fail |
| grounded_explanation silent 5/6 | Explicit residual: always false; script notes TLRR may stay 0 |
| Micro LLM / inline write mastery | `evidence_bound=False` + origin; process path no longer crashes on `sr=None` |
| process_micro still updated PLM | PLM mastery_gain skipped when evidence_blocked |
| Scoped UI silent block | `st.warning` «не подтверждено» + journal-only message |
| Mastery tests hit prod DB | Mocked SR/mastery writers in unit tests |
| No E2E fallback | `test_process_micro_quiz_fallback_blocks_mastery` |
| Report overclaim «closed 6/6» | This report: honest residual table |

---

## DoD re-score

| Gate | Статус |
|---|---|
| Packet JSON, no new DB/LLM | ✅ |
| Reindex sidecar hook | ✅ |
| Labels + best/rejected reason | ✅ |
| Evidence spans (excerpt) | ✅ when source file resolvable under data_dir |
| UI «почему фрагмент» | ✅ code path; live smoke depends on active gate report |
| Quiz without evidence → no mastery | ✅ scoped all-or-nothing + micro/inline False |
| Fallback → no mastery | ✅ + E2E process path |
| origin/evidence_bound persistent | ✅ |
| TLRR plan formula + rates | ✅ (full-contract often 0 until grounded_explanation) |
| Answer label «не подтверждено» | ✅ scoped warning + micro retention_line |
| ≥1 live step 6/6 on reference bundle | ⬜ residual (component 4 unwired) |
| Live 3–5 topics on real bundle | ⬜ run `scripts/run_course_content_gate.py` after reindex |

---

## Fix-wave 2 (контр-аудит fix-wave, 2026-07-21)

| Замечание аудита | Исправление |
|---|---|
| concept_id matching slug vs UI identifier | `concept_aliases` / `expand_concept_keyset`: slugify + hyphen/underscore + alphanumeric compact; tests `test_verified_quiz_matches_via_slug_alias` |
| E2E test not proving PLM/XP skip | spies on `update_learner_model_after_interaction` + `award_xp_for_block`; assert 0 calls + AssertionError if invoked |
| selection_reason tautology (always «Роль:») | `best_source.discriminating` + `_is_discriminating_selection`; TLRR uses flag (role-only identical sources → false) |
| evidence_span weak + unlimited read | read cap 64KB; `match_kind=label_mention\|prose_fallback`; TLRR accepts only `label_mention` |
| silent zeros on missing columns | PRAGMA check + **stderr WARNING** + `metrics_error` in result JSON |

Tests after fix-wave 2: **82/82 PASS**.

---

## Fix-wave 3 (аудит residual defects, 2026-07-21)

| Замечание | Исправление |
|---|---|
| Legacy discriminating text heuristic | Удалён `reason.split(";")`; только recompute via sources или fail-closed |
| Legacy span без match_kind = pass | **Не** pass; `legacy_evidence_span_steps` + flag на step |
| Full TLRR структурно 0 | Явно: `tlrr_status=grounded_explanation_not_implemented`; KPI = `tlrr_excluding_grounded` |
| Single-source selection fail | Vacuous pass при `<2` sources / document_count |
| Нет теста missing columns | `test_count_quiz_metrics_missing_columns_sets_metrics_error` |
| Cyrillic needles vs translit | `_concept_match_needles` + slugify в evidence spans |
| User-facing TLRR | `docs/user_guide.md` — таблица full vs excluding_grounded |

---

## Residual / next (not blockers for partial ship)

1. **grounded_explanation** — wire в маршрут; до этого full TLRR = 0 by design.
2. Live dry-run: reindex → content gate on 3–5 topics of reference bundle.
3. Passport/Library surface beyond living-konspekt reader.
4. Per-question persistence of evidence_bound.
5. Semantic entailment (#25) offline/P2.
6. Evidence span = head-of-file heuristic (64KB); long files may FN — `scan_limit_bytes` marked.

---

## Команды проверки

```text
.\.venv\Scripts\python.exe -m pytest tests/test_course_content_gate.py tests/test_quiz_content_contract.py tests/test_trusted_route_rate.py -q
.\.venv\Scripts\python.exe scripts/compute_trusted_route_rate.py --json
.\.venv\Scripts\python.exe scripts/run_course_content_gate.py
```

---

*Создано: 2026-07-20 · fix-wave после контр-аудита · status: P0-A shipped, P0-B shipped with honest TLRR residual.*
