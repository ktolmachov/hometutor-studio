# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-metrics-decomposition: metrics module decomposition (2026-04-17)

- **CJM:** Quality Infrastructure — observability/SLO; prerequisite для eval loop и health dashboard.
- **Scope:** архитектурный slice без изменений публичных API metrics endpoints.
- **Декомпозиция:** `app/metrics.py` (~1900 строк) → 6 подмодулей: `metrics_core` (схемы/пути), `metrics_storage` (JSONL), `metrics_aggregator` (in-memory), `metrics_graph_expansion` (графы), `metrics_summarizer` (аналитика/SLO), `metrics_db` (SQLite). Внедрён `MetricsModule` (Class Injection Facade) для динамического патчинга констант в тестах и надёжной изоляции состояния между прогонами.
- **Проверки:** `pytest tests/test_metrics.py tests/test_quality_benchmark_metrics.py -q` → 20 passed.
- **Примечание:** реализовано 2026-04-17 (changelog), формально закрыто 2026-04-18 (planning doc-sync).
