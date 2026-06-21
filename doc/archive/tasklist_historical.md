# Tasklist: исторические exit criteria и журнал This Week

Роль: архив формальных критериев закрытых срезов и завершённого weekly-чеклиста. **Активный backlog** — в [tasklist.md](tasklist.md); закрытые эпохи и таблицы — в [closed_iterations.md](closed_iterations.md).

Актуализировано: **2026-04-19**

## Exit Criteria

### E4 (closed by sprint exit criteria — 2026-04-07)

Минимум инкрементов после foundation (см. [`future_roadmap.md`](future_roadmap.md) § E4 Summary):

- **E4.0 — multi-hop graph expand:** параметр `max_hops` в `expand_doc_ids_via_graph`, конфиг `graph_expand_max_hops`, проводка в graph postprocessor; trace `max_hops` / `hops_applied`.
- **E4.1 — observability / provenance в trace:** `concept_ids_sample` (до 32 id концептов) в выходе `expand_doc_ids_via_graph`; `graph_expansion_ms` во всех ветках trace graph postprocessor (`pipeline_trace` / `ctx.trace`).
- **E4.2 — metrics:** компактный снимок `graph_expansion` в JSONL request-событиях; агрегаты latency (p50/p95/p99 `graph_expansion_ms`) и quality (applied/skipped/error, `avg_extra_chunks_when_applied`) в `get_metrics()` и `summarize_metrics_store`.
- **E4.3 — provenance UI (минимум):** expander «Расширение графа (retrieval)» в `debug_panel` при наличии `pipeline_trace.graph_expansion` (вкладка «Быстрый ответ»).
- **E4.4 — latency/quality benchmark (CLI):** `scripts/graph_expansion_benchmark.py` — агрегаты из JSONL (`aggregate_graph_expansion_from_request_events` в `app/metrics.py`) или снимок `graph_expansion` с `GET /metrics` (`--metrics-url`).
- **E4.5 — benchmark quality gate:** `scripts/graph_expansion_benchmark.py` поддерживает пороги (`--min-events`, `--max-p95-ms`, `--min-applied-rate`, `--max-error-rate`, `--min-avg-extra-chunks`) и завершает процесс с non-zero exit code при провале gate; `app/metrics.py` публикует derived rates (`applied/skipped/error/unknown_outcome`).
- **E4.6 — ready command + smoke gate:** `scripts/check_graph_expansion_gate.py` даёт готовый gate с профилями `local` / `strict`; `scripts/smoke_graph_expansion_gate.py` генерирует graph-expansion request-события через `/ask` в изолированный JSONL и сразу прогоняет gate.
- **E4.7 — CI merge-gate:** GitHub Actions workflow `.github/workflows/graph-expansion-smoke-gate.yml` запускает целевые тесты и `scripts/smoke_graph_expansion_gate.py --profile strict` на `pull_request` и `push` в `main/master`.
- **E4.8 — compare report + provenance UX:** `scripts/graph_expansion_compare.py` сравнивает baseline/candidate по `p95_total_answer_ms`, `p95_graph_expansion_ms`, `applied_rate`, `error_rate`, `avg_extra_chunks_when_applied`; trace `graph_expansion` расширен route/doc-reason sample, а `debug_panel` показывает не только факт expansion, но и почему были добавлены чанки.
- **E4.9 — graph off/on smoke compare runner:** `scripts/smoke_graph_expansion_gate.py` поддерживает режимы `--graph-mode off|on`, а `scripts/smoke_graph_expansion_compare.py` сам генерирует обе стороны и печатает delta между `graph_off` и `graph_on`.
- **E4.10 — delta compare gate:** `scripts/graph_expansion_compare.py` умеет валидировать delta между baseline/candidate по правилу «regression budget vs applied-rate lift» (`--profile`, `--enforce-gate`, `--max-p95-total-answer-regression-pct`, `--min-applied-rate-lift`, `--max-error-rate-increase`); `scripts/smoke_graph_expansion_compare.py` использует ту же логику для off/on smoke gate.
- **E4.11 — segmented diagnostics:** `app/metrics.py` публикует breakdown `graph_expansion.by_query_type`, `skip_reasons`, `error_types`; `scripts/graph_expansion_benchmark.py` нормализует те же разрезы из JSONL и `GET /metrics`, а `scripts/graph_expansion_compare.py` показывает также delta по `skipped_rate`, чтобы отделять реальную деградацию graph retrieval от сдвига query mix.
- **E4.12 — query-type-aware compare diagnostics:** `scripts/graph_expansion_compare.py` строит отдельный `query_type_compare` и `graph_expansion_counter_compare`, чтобы baseline/candidate и off/on smoke можно было разбирать по каждому `query_type`, а не только по общему среднему.
- **E4.13 — query-type-aware compare gate:** `scripts/graph_expansion_compare.py` и `scripts/smoke_graph_expansion_compare.py` поддерживают `--gate-query-type`, а `compare_gate` публикует `query_type_checks`, чтобы regression budget можно было валидировать для целевого retrieval-type, не смешивая его с общим query mix.
- **E4.14 — query-type-specific compare gate profiles:** `scripts/graph_expansion_compare.py` и `scripts/smoke_graph_expansion_compare.py` поддерживают `--gate-query-type-profile query_type=local|strict`; targeted `query_type_checks` могут жить на более строгом или мягком профиле, чем общий compare-gate.
- **E4.15 — presets + multi-query smoke runbook:** `scripts/graph_expansion_compare.py` и `scripts/smoke_graph_expansion_compare.py` поддерживают готовые `--preset` (`overall-local`, `overall-strict`, `synthesis-strict`, `learning-plan-local`, `dual-local`, `dual-strict` и др.); `scripts/smoke_graph_expansion_gate.py` генерирует multi-query-type traffic через `--query-types`; [`doc/observability_slo.md`](observability_slo.md) содержит ready-to-run recipes; CI workflow запускает не только общий smoke gate, но и targeted compare merge-gate для `synthesis-strict`.
- **регрессия:** `tests/fixtures/graph_eval_baseline.json` schema ≥ 3; `tests/test_graph_retrieval.py`.

**Решение owner 2026-04-07:** этого набора достаточно, чтобы считать sprint exit criteria по E4 выполненными и перевести active horizon на E5.

**Не входит:** полноценный внешний SaaS-дашборд; **E4.2–E4.15** закрывают метрики API, debug UI, CLI-отчёт, quality gate, smoke-команду, CI merge-gate, compare-report, off/on smoke compare runner, delta compare gate, segmented diagnostics, query-type-aware compare, query-type-aware gate, query-type-specific profiles и ready presets / multi-query smoke runbook.

### 17 Core MVP

Минимум, без которого нельзя честно переходить к `18 Core`:

- structure-aware metadata: `course/module/lecture/section_path/page_range/doc_kind`
- provenance minimum для graph entities/relations
- graph-backed retrieval в ограниченном production path
- `KnowledgeGraphReader` как runtime abstraction
- graph-candidate eval dataset и baseline

**Не входит в MVP:**

- full graph-details UX
- compare/export
- self-correction loop
- advanced planning/generator flows
- perf/cache polishing

### 17 Core Extension

- self-correction не ломает MVP path
- graph API и learning-plan flows имеют отдельный baseline
- cycle detection и ручная коррекция покрыты tests/eval

### 18 Core

- retry/backoff и timeout budget в production path
- fallback policy по provider/model
- structured logging и error tracking
- reliability/chaos checks и graceful shutdown
- **tail:** отдельные таймауты embedding (`embed_request_timeout`, `embed_connect_timeout_sec` → `get_embed_model`)

### 19 Platform Tail

- CLI `ask.py --session-id` / `--new-session` / `--query-mode` согласован с `QueryOptions` (как POST `/ask`)
- bounded history: `session_history_max_messages` в `Settings` + обрезка в `SessionStore.save`; stats в `debug.session_history`
- Session Store v2: колонка `session_metadata`, `GET /sessions/{id}` (404 если нет строки), `PATCH /sessions/{id}/metadata`
- FAQ: запись в Chroma из `/ask` не выполняется при непустом `session_id` (кэш по чтению уже отключался в retrieval)
- multi-turn регрессия: `tests/test_multi_turn.py::test_multi_turn_two_turns_persist_same_session`

## This Week (архив)

1. [x] Owner decision по `16 tail`: parking «What Changed» / synthesis archive; следующий review **2026-07-05** (см. Truth View).
2. [x] `17 Core MVP` закрыт по merge-gate; Extension — cycle detection срез.
3. [x] Doc-sync gate: `tests/test_doc_sync_gate.py` (pytest в CI/локально).
4. [x] Диаграмма зависимостей `16 → 17 → 18 → 19 → E4 → E5` в [`doc/architecture.md`](architecture.md).
5. [x] Механизм tail sweep: [`doc/tail_sweep.md`](tail_sweep.md) (чеклист + команда обхода).
6. [x] Операционный tail sweep **2026-04-06**: журнал в `tail_sweep.md`; parking «What Changed» / synthesis archive зафиксирован в § Parking lot (16 tail).
7. [x] Post-foundation: `changelog.md` **2026-04-06**, Truth View + § Now/Next — вход в горизонт **E4**; `vision.md` / `architecture.md` — дата актуализации.
8. [x] **E4.0:** multi-hop graph expand + `GRAPH_EXPAND_MAX_HOPS` / `graph_expand_max_hops`; baseline v2.
9. [x] **E4.1:** `concept_ids_sample`, `graph_expansion_ms`; `graph_eval_baseline` v3.
10. [x] **E4.2:** отдельные graph expansion метрики в `get_metrics` / JSONL (`graph_expansion`).
11. [x] **E4.3:** provenance graph expansion в debug UI (`debug_panel`).
12. [x] **E4.4:** CLI benchmark graph expansion (`graph_expansion_benchmark.py`).
13. [x] **E4.5:** quality gate для benchmark CLI (`--min-events`, `--max-p95-ms`, `--min-applied-rate`, `--max-error-rate`, `--min-avg-extra-chunks`) + derived rates в `/metrics`.
14. [x] **E4.6:** ready-to-run gate command (`check_graph_expansion_gate.py`) + smoke script, который сам генерирует `graph_expansion` request-события и валидирует gate.
15. [x] **E4.7:** merge-gate для E4 в CI: workflow `graph-expansion-smoke-gate.yml` запускает smoke path и строгий профиль порогов на PR/push.
16. [x] **E4.8:** compare report `graph_expansion_compare.py` и richer provenance UX в debug panel (`concept_route_sample`, `added_doc_reason_sample`).
17. [x] **E4.9:** smoke runner, который сам генерирует `graph_off` и `graph_on` JSONL и сразу строит compare-report (`smoke_graph_expansion_compare.py`).
18. [x] **E4.10:** delta compare gate с профилями `local/strict` и `exit code 2` при неоправданной latency-регрессии (`graph_expansion_compare.py`, `smoke_graph_expansion_compare.py`).
19. [x] **E4.11:** сегментированные diagnostics для graph expansion: `by_query_type`, `skip_reasons`, `error_types` в `/metrics` и benchmark CLI; compare-report дополняет delta по `skipped_rate`.
20. [x] **E4.12:** query-type-aware compare diagnostics: `graph_expansion_compare.py` теперь показывает отдельный baseline/candidate delta по каждому `query_type` и диагностическим counters, smoke compare использует тот же формат.
21. [x] **E4.13:** query-type-aware compare gate: `--gate-query-type` валидирует compare-gate отдельно для целевого `query_type`, а smoke compare использует тот же contract.
22. [x] **E4.14:** query-type-specific compare gate profiles: `--gate-query-type-profile synthesis=strict` даёт отдельный regression budget для targeted gate без ручного дублирования threshold-флагов.
23. [x] **E4.15:** ready presets, multi-query smoke и CI targeted compare: `--preset synthesis-strict` / `learning-plan-local`, `--query-types synthesis,learning_plan` и workflow merge-gate превращают compare/gate контур в готовый operational runbook.
24. [x] Owner decision: считать **E4 sprint exit criteria fulfilled** и перевести active horizon на **E5**.
25. [x] **E5.0:** versioned learner profile history (`personalized_learner_model_history_json`) и тест `test_save_learner_profile_appends_versioned_history`.
26. [x] **E5.1:** migration-safe fallback `mastery_vector` из history при смене `generation_id`; тест `test_profile_rehydrates_mastery_from_history_when_current_is_orphaned`.
27. [x] **E5.2:** endpoint `/kb/learner/profile-history` (history + current `state_migration`) и API-тест `test_learner_profile_history_endpoint`.
28. [x] **E5.3:** endpoint `/metrics/learner` + rollup `get_learner_profile_migration_metrics` (rehydrated/index_changed rates); тесты `test_get_learner_profile_migration_metrics_rollup`, `test_metrics_learner_endpoint`.
29. [x] **E5.4:** learner migration SLO alert (`slo_max_learner_rehydrated_rate`) в `evaluate_slo_alerts` / `/metrics/alerts`; тест `test_evaluate_slo_alerts_includes_learner_rehydrated_rate_alert`.
30. [x] **E5.5:** ready quality-gate CLI `scripts/check_learner_migration_gate.py` (local/strict, exit code 2 on fail); тесты `tests/test_check_learner_migration_gate.py`.
31. [x] **E5.6:** smoke gate command `scripts/smoke_learner_migration_gate.py` (генерация history + запуск gate); тесты `tests/test_smoke_learner_migration_gate.py`.
32. [x] **E5.7:** CI merge-gate `.github/workflows/learner-migration-smoke-gate.yml` (strict smoke gate on PR/push) + runbook recipes в `doc/observability_slo.md`.
33. [x] **E5.8:** eager learner DB lineage sync при активации индекса (`apply_index_activation_hooks` → `run_learner_state_lineage_sync`); `doc/index_lifecycle.md`; тест `test_apply_index_activation_hooks_syncs_learner_lineage`.
34. [x] **E6.0:** tutor orchestration contract (`tutor_pipeline_contract`, rule fallback, trace `tutor_pipeline`, init в `query_service`); тесты pipeline + orchestrator.
35. [x] **E6.1:** Agent A — `tutor_personalization_policy` clamp + attach в пайплайне и `PedagogicalRouter`; `tests/test_tutor_personalization_policy.py`.
36. [x] **E6.2:** Agent B — tutor payload + KV snapshot + Streamlit surfaces для E6 pipeline.
37. [x] AQE-R remediation (2026-04-19): unblocking epoch-answer-quality-eval start.
38. [x] agent-workflow-token-p3 (2026-04-19): context compression and planning template consolidation.
39. [x] [ingest-acceleration](epochs/ingest_acceleration.md) (2026-04-19): no-op fast path and extraction cache.
