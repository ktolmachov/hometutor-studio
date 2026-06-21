# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-learning-route-continuity: e2e coverage всех 13 MoT CJM (2026-04-17)

- **CJM:** все 13 моментов истины (`doc/cjm.md` §5) получили e2e-покрытие; 9 новых тестов закрыли переходы маршрута обучения, 4 момента покрыты существующими тестами.
- **Scope:** только Playwright e2e-тесты, без изменений runtime-кода и API.
- **@nightly (5 тестов, 7 кейсов):** `learning_route_continuity.spec.ts` (MoT #2–4, §6 North Star: answer→trust→tutor→quiz→progress Δmastery), `tutor_context_preservation.spec.ts` (#3), `quiz_error_recovery.spec.ts` (#4), `resume_next_day.spec.ts` (#5), `concept_graduation.spec.ts` (#9).
- **@smoke (4 теста, 5 кейсов):** `reindex_profile_preservation.spec.ts` (#6), `srs_soft_recovery.spec.ts` (#7), `flashcard_session_summary.spec.ts` (#12), `progress_next_action.spec.ts` (#8).
- **MoT #1, 10, 11, 13** покрыты существующими тестами: onboarding, `guided_start.spec.ts`, `flashcards_review_flow.spec.ts`, `home_mode_selection.spec.ts`.
- **Документация:** `tests/e2e/README.md` — CJM MoT coverage table, epoch summary, OPENAI_API_KEY rules; live-сценарии корректно `skip` без ключа.
- **Коммиты:** b309a9d, 3318b5f.
- **Проверки:** `npm run test:e2e:smoke` (offline), `npm run test:e2e:nightly` (с `OPENAI_API_KEY`).
