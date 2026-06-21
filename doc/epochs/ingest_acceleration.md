# Epoch: Ingest Acceleration

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## ingest-acceleration: no-op fast path and extraction cache (2026-04-19)

- **CJM:** Ingest / Onboard — сокращает стоимость повторного `build_index(reset=False)` и делает no-op переиндексацию предсказуемой.
- **Scope:** ingest pipeline and docs/config notes; без изменения публичного `/ask` контракта.
- **Изменения:**
  - `build_index(reset=False)` строит дешёвый file manifest до embedding preflight и тяжёлого парсинга, затем выходит с `INGEST_SUMMARY run_kind=noop`, если файлы, embedding model, chunking fingerprint и активная Chroma collection уже актуальны.
  - Parsed/expanded/metadata-normalized `Document` fragments кэшируются в `chroma_db/ingestion_extracted_documents.json`; неизменённые PDF/HTML/DOCX больше не парсятся повторно при частичном reindex.
  - `ingestion_content_hashes.json` хранит file manifest и предыдущие source-fragment/node counts для корректных no-op summaries.
  - Ingest logs показывают `documents_extraction_cache` progress с reused/dirty file counts; README и `.env.example` описывают быстрый обычный путь и `DOC_LOAD_NUM_WORKERS`.
- **Проверки:** affected ingest subset → 16 passed.
