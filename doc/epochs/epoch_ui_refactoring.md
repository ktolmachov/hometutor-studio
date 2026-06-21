# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-ui-refactoring: tutor_chat decomposition (2026-04-17)

- **CJM:** Tutor session — снижение риска регрессий в критическом tutor path (MoT #3, #4) через изоляцию UI-компонентов.
- **Scope:** структурный рефакторинг без изменений публичных контрактов или API.
- **Декомпозиция:** `app/ui/tutor_chat.py` → 7 модулей: `tutor_chat_header` (заголовки/стили), `tutor_chat_controls` (сессии/глубина), `tutor_chat_footer` (экспорт/статистика), `tutor_chat_actions`, `tutor_chat_session`, `tutor_chat_quiz`, `tutor_chat_render`.
- **Guardrail:** фасад `tutor_chat.py` сохранён; внешние вызовы из UI не изменились.
- **Проверки:** `python -c "import app.ui.tutor_chat; print('ok')"` + smoke по tutor_chat test contour.
- **Примечание:** реализовано 2026-04-17 (changelog), формально закрыто 2026-04-18 (planning doc-sync).
