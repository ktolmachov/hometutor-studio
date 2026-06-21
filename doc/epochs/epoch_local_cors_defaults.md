# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-local-cors-defaults: CORS hardening (2026-04-18)

- **CJM:** Trust / Security — local-first posture; architecture review finding #9.
- **Scope:** только `app/config.py`, `app/api_helpers.py`, `app/api.py`; без изменений роутеров и тестов.
- **Изменения:**
  - `app/config.py` — добавлены `cors_methods: str = "GET,POST,DELETE,OPTIONS"` и `cors_headers: str = "Content-Type,Authorization,X-Request-ID"` в `Settings`.
  - `app/api_helpers.py` — рефакторинг через общий `_cors_list(raw, default)`; добавлены `cors_methods_list()` и `cors_headers_list()`; default берётся из `Settings.model_fields`; `"*"` passthrough сохранён для dev-override.
  - `app/api.py` — `allow_methods` и `allow_headers` переведены с хардкодного `["*"]` на вызовы хелперов.
- **Guardrail:** `cors_origins` логика не изменилась; wildcard env-override (`CORS_METHODS=*`) по-прежнему работает.
- **Проверки:** `pytest tests/test_api.py -q` → 72 passed; assertion `'*' not in settings.cors_methods` and `'*' not in settings.cors_headers` — ok.
