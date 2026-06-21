# Закрытые Итерации

Актуализировано по roadmap на **2026-04-19** (в т. ч. **ingest-acceleration**, **epoch-local-cors-defaults**, **epoch-ui-refactoring**, **epoch-metrics-decomposition**, **epoch-learning-route-continuity**; ранее **epoch-query-service-decomposition**, **epoch-adr-010-acceptance**, **epoch-user-state-decomposition**, **epoch-local-store-contracts**, **E29** quiz service boundary, **E28-A** US-8.2, **E16**, **E24-B-2**, **E11-R**, **E13**, **E12**, архив **T1–T25** и т. д.).

Этот файл хранит **исторические** детали закрытых итераций, чтобы не перегружать `tasklist.md`.
Источник правды по активному backlog и owner'ам — `doc/backlog_registry.yaml`; `doc/tasklist.md` — производный weekly view (регенерация: `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).



## epoch-query-service-decomposition: answer_question cohesive subflows (2026-04-16)

- **Источник:** `archive/architecture_review.md` finding #7 / remediation #6 — `query_service.answer_question()` был отмечен как god function; recommended action: extract cohesive subflows, especially session persistence, tutor post-processing, and fallback assembly.
- **Scope:** safe decomposition only; no `/ask` response-shape changes, no retrieval behavior changes, no router/API migrations, no SQLite schema changes, no CORS work.
- **Package A — session persistence:** `app/query_session_persistence.py` owns compact source metadata and chat-session persistence; `query_service` keeps compatibility wrappers for existing tests/callers.
- **Package B — RAG execution:** `app/query_rag_execution.py` owns QueryEngine execution, tracing, generation token accounting, graph-expansion trace propagation, and retrieval self-correction; `query_service._execute_rag_query()` delegates while preserving monkeypatch compatibility for `query_service.build_query_engine`.
- **Package C — Tutor post-processing:** `app/query_response_postprocessing.py` owns answer text post-processing, source parsing, Tutor v2 parse/format bridge, inline quiz generation hook, tutor decision/profile update, and auto-quiz attachment; `query_service._process_rag_response()` delegates.
- **Package D — fallback assembly:** `app/query_fallbacks.py` owns safe fallback response assembly after output guardrail failures; `query_service._build_safe_fallback_result()` delegates while keeping local trace/quality helper compatibility.
- **Closure decision:** final response assembly remains in `query_service.py` for now because it is tightly coupled to debug schema, token usage/costs, tutor payload, orchestration persistence, and session persistence; extracting it is deferred until a concrete follow-up risk appears.
- **Проверки:** `.\.venv\Scripts\python.exe -m pytest tests/test_query_service.py tests/test_multi_turn.py tests/test_api.py -v` → `107 passed`; `git diff --check` → no whitespace errors (CRLF warnings only).
