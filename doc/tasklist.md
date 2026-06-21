# План работ

Актуализировано: **2026-05-01**.

Краткий weekly backlog. История закрытых пакетов: `doc/closed_iterations.md`. Правила: `doc/roadmap_governance.md`. Стратегический горизонт: `doc/future_roadmap.md`.

## Now

> Deprecated display: this section is a generated weekly view. Use `doc/backlog_registry.yaml`
> as the source of truth for current packages, Truth View, and Wave queue.

### Truth View

<!-- GENERATED: tasklist.truth_view (do not edit manually) -->

| Package | Status | CJM | Primary US | Owner | Notes |
|---|---|---|---|---|---|

### Wave queue

<!-- GENERATED: tasklist.wave_queue (do not edit manually) -->

<!-- ACTIVE_WAVE: wave-advanced-rag-rewrite-rerank -->
- **Active wave:** `wave-advanced-rag-rewrite-rerank`
- **Queued (same wave):**
  - `multi-query-expansion-v1`
  - `lost-in-middle-reorder-v1`
- **Queued (other waves):**
- `wave-smart-notes-killer-feature`: `smart-notes-konspekt-surfacing-v1`, `smart-notes-native-generation-v1`
  - Kill switch: UI badge показывает конспект несуществующего файла; native generation пишет truncated Markdown (finish_reason=length принят); фича делает тихий cloud-вызов без явного режима или ломает текущий txt map/reduce/compose export.
- `wave-workflow-skills-platform`: `workflow-skills-thin-adapter-v1`, `workflow-role-subagents-v1`
  - Kill switch: Тело skill'а копирует логику генератора (4-е представление SSoT); skill проскакивает стоп-точку процесса (review контракта, WIP=1, RED Ops gate); путь md+скрипты для cursor_ai/codex ломается или становится второсортным.
- **North star:** Поверх уже работающих single-query rewrite (enable_rewrite), hybrid RRF (ParallelHybridRetriever) и cross-encoder rerank (bge-reranker, enable_reranker on by default) основной answer-путь получает multi-query expansion и явный lost-in-the-middle reorder контекста; source-coverage растёт без регрессии latency_budget.
- **Kill switch:** Expansion/reorder добавляют >hard_ms к query-budget >2 дней, снижают grounded-citation rate, или ломают retrieval_router / существующий reranker fallback.

### Recent closed references

<!-- GENERATED: tasklist.recent_closed (do not edit manually) -->

- `epoch-answer-quality-eval` закрыт 2026-04-20; см. `doc/closed_iterations.md`.
- `epoch-inline-citations-first-answer` закрыт 2026-04-22; см. `doc/closed_iterations.md`.
- `epoch-5min-loop-polish` закрыт 2026-04-21; см. `doc/closed_iterations.md`.
- `epoch-us7-3-resume-card` закрыт 2026-04-21; см. `doc/closed_iterations.md`.
- `epoch-qa-tutor-handoff` закрыт 2026-04-20; см. `doc/closed_iterations.md`.
- `epoch-unified-context-layer` закрыт 2026-04-20; см. `doc/closed_iterations.md`.
- `epoch-17-1-ux-tail` закрыт 2026-04-20; см. `doc/closed_iterations.md`.
- `epoch-micro-quiz-feedback-tail` закрыт 2026-04-20; см. `doc/closed_iterations.md`.
- `epoch-cjm-us-frontmatter` закрыт 2026-04-21; см. `doc/closed_iterations.md`.
- `epoch-adaptive-plan-today` закрыт 2026-04-22; см. `doc/closed_iterations.md`.
- Более ранние закрытия, audit-corrections и архивные детали: `doc/closed_iterations.md` и `archive/team_artifacts/*`.

## Maintenance (compact)

- 2026-04-29: Architecture Review Phase 2 guard для `app/ingestion.py` (2100L max), вынесен `ingestion_env_diag.py`; оркестрация index build вынесена в `app/ingestion_loader.py` (см. `doc/architecture.md`). Док-синхронизация: `epoch-doc-ingestion-split-arch-sync`.

- 2026-04-26: выполнен corrective doc/code sync по architecture review (fan-out `app/ui/tutor_chat.py`, production-safe FAQ exception logging в `app/knowledge_service.py`, явный блок tutorial subsystem в `doc/architecture.md`).
- `epoch-cjm-us-frontmatter`, `epoch-us7-3-resume-card`, `epoch-5min-loop-polish` остаются в архивах и `doc/closed_iterations.md` (без дублей в `tasklist.md`).
- `epoch-context-cart-mvp` закрыт; история и артефакты — в `doc/closed_iterations.md` и `doc/backlog_registry.yaml`.
- Источник исторических деталей: `doc/closed_iterations.md`; не дублировать большие execution-сводки в `tasklist.md`.

## Правила выполнения

- WIP = 1; не больше **5** user-visible outcomes на эпоху.
- Пакет: стадия CJM + user story (`doc/cjm.md`, `doc/user_stories/*.md`); старт — контрактный prompt из `doc/agent_workflow_templates.md` (раздел `Шаблон planning prompt`).
- Без CJM/DoD — не берем. Infra/eval — только если защищает текущий user-visible loop.

## Deferred

<!-- GENERATED: tasklist.deferred (do not edit manually) -->

| Item | Re-entry condition | Last review |
|-----|--------------------|-------------|
| `performance-tail-18-1` | latency SLO breach: eval gate p95 trips; reopen only if threshold crossed | 2026-04-20 |
| `ocr-docling` | user request for PDF/image ingest | 2026-05-01 |

## Архив Roadmap

История и длинные чеклисты: [closed_iterations.md](closed_iterations.md), [tasklist_historical.md](archive/tasklist_historical.md).
