# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-local-store-contracts: SQLite/local-store ownership contract (2026-04-13)

- **Источник:** `archive/architecture_review.md` finding/remediation #4 — ambiguity around direct SQLite stores outside `app/user_state._with_db()`.
- **Scope:** documentation-only architecture contract: clarify `_with_db()` as mandatory for user-state tables, while independent local stores are allowed only behind documented wrappers/artifact writers.
- **Контракт:** documented current non-user-state stores: `app/session_store.py` (`sessions.db`), `app/event_tracking.py` (`ui_events.db`), `app/metrics.py` (metrics JSONL + dashboard SQLite cache), and `app/knowledge_graph_bundle.py` (per-generation/staging `kg.sqlite` artifact).
- **Проверки:** doc grep for the new persistence contract; no pytest required because runtime code was not changed.
