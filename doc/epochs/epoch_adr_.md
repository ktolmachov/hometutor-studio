# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-adr-010-acceptance: ADR-010 local persistence decision (2026-04-16)

- **Источник:** `archive/architecture_review.md` finding #8 / remediation #7 — `ADR-010` оставался `Proposed`, хотя SQLite/session/Telegram/KG-bundle решения уже реализованы.
- **Scope:** documentation-only ADR acceptance: без runtime-кода, миграций, новых endpoints или functional persistence refactor.
- **Контракт:** `doc/adr.md` — ADR-010 переведён в `Accepted` и описывает local-first single-user persistence model: user-state таблицы принадлежат `app/user_state.py` / доменным `app/user_state_*` модулям и проходят через `_with_db()`, а независимые local stores/artifacts остаются за документированными владельцами (`SessionStore`, `event_tracking`, metrics dashboard cache, KG bundle).
- **Telegram:** зафиксирован как optional entrypoint на той же локальной машине и том же состоянии, а не отдельный backend или облачная синхронизация.
- **Проверки:** `rg -n "ADR-010|Accepted|Superseded|_with_db|SessionStore|ui_events.db|metrics_dashboard_db_path|kg.sqlite|Telegram" doc/adr.md doc/conventions_architecture.md doc/conventions_reference.md`; `git diff --check`. Pytest не требовался, потому что runtime code не менялся.
