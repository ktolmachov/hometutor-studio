# ADR-025: Course Graph Compiler and local artifact cache

**Статус:** Accepted  
**Дата:** 2026-06-11

## Контекст

Course-level navigation needs a deterministic concept graph derived from local source
files. Re-running extraction on every UI request is slow, provider-dependent, and
breaks the project's local-first behavior.

## Решение

- `app/course_graph_compiler.py` owns compilation and validation of the course graph.
- `app/prompts/course_graph_extraction.py` owns the extraction prompt contract.
- `app/course_cache.py` owns persisted local artifacts and cache lookup; UI and routers
  consume those service outputs rather than invoking graph extraction directly.
- LLM access remains behind `app/provider.py`, settings behind `app/config.py`, and
  generated artifacts are rebuildable from local sources.

## Последствия

Compilation can be triggered explicitly or at an ingestion boundary without coupling
rendering to provider latency. Schema changes require cache invalidation or migration,
and compiler output must remain deterministic after normalization.
