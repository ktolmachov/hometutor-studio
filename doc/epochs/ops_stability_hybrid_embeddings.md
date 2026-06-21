# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## ops-stability-hybrid-embeddings: fail-fast integration + local runbook (2026-04-16)

- **Scope:** operational stability/documentation slice без изменения публичных API контрактов.
- **Стабильность:** устранен `UnboundLocalError` из-за shadowing `logging` (локальные `import logging` внутри функций) в `app/query_response_postprocessing.py`, `app/query_service.py`, `app/pipeline_steps.py`.
- **Integration policy:** `tests/test_integration_retrieval.py` переключен на явный fail-fast при недоступных chat/embeddings зависимостях; ошибка конфигурации больше не маскируется глубоким stacktrace `VectorStoreIndex`.
- **Локальный hybrid runbook:** документирован сценарий cloud LLM + local embeddings (Ollama) в `.env.example` и `README.md`, включая troubleshooting (`No embedding data received`, `OpenAIEmbeddingModelType` mismatch).
- **Automation:** добавлен helper `scripts/run_integration_local.ps1` для локального запуска integration retrieval одной командой.
- **Проверки (актуально):** `python -m pytest tests/ -q` (по умолчанию без integration); `python -m pytest -m integration tests/test_integration_retrieval.py -q` для retrieval integration.
