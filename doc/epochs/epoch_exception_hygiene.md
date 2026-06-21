# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-exception-hygiene: broad exception boundary hygiene (2026-04-13)

- **Источник:** `archive/architecture_review.md` remediation #5 — broad `except Exception` without required `# noqa: BLE001` justification.
- **Scope:** first boundary slice only: `/ask` router (`app/routers/query.py`) and pipeline fallback (`app/pipeline_steps.py`); service/router/UI/Telegram sweeps deferred in artifacts.
- **Код:** `/ask` best-effort history/FAQ persistence and final unknown-error boundary catches now carry explicit BLE001 justifications; pipeline fallback catches in `run_step_safe`, subquestion generation, optional KG lookup, and tutor orchestrator fallback now document graceful degradation.
- **Проверки:** `.venv\Scripts\python.exe -m pytest tests/test_api.py -q` → 68 passed; `.venv\Scripts\python.exe -m pytest tests/test_pipeline_steps.py -q` → 30 passed.
- **Артефакты:** `archive/team_artifacts/epoch-exception-hygiene/`.
