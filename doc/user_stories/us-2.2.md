---
us_id: "US-2.2"
epic: 2
epic_name: "Epic 2: Ingest"
priority: "P1"
cjm_stage: "2"
cjm_moment_name: "First answer / course activation"
status: "closed"
covered_by: "epoch-demo-scenario-08-trust"
closed_date: "2026-04-26"
---

# US-2.2 — Инкрементальная переиндексация по умолчанию (P1)

## Epic 2: Ingest

[← Back to user stories index](../user_stories.md)

---

### US-2.2 — Инкрементальная переиндексация по умолчанию (P1)
**As a** Learner, который добавил один новый PDF,
**I want** чтобы reindex обработал только дельту,
**so that** я не жду полного пересчёта.

**Acceptance:**
- Given существующий индекс и один новый файл в `data/`,
- When я запускаю reindex,
- Then обрабатывается только новый файл, lineage записывается, активация атомарна.

---

## Epic 3: First Answer

## Status History

- 2026-04-26 | status: `closed` | covered_by: `epoch-demo-scenario-08-trust` | closed_date: `2026-04-26`
