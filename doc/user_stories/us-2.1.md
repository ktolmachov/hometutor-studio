---
us_id: "US-2.1"
epic: 2
epic_name: "Epic 2: Ingest"
priority: "P0"
cjm_stage: "1"
cjm_moment_name: "Discover / first launch"
status: "closed"
covered_by: "epoch-ingest-first-index-progress"
closed_date: "2026-04-22"
---

# US-2.1 — Видеть прогресс первой индексации (P0)

## Epic 2: Ingest

[← Back to user stories index](../user_stories.md)

---

### US-2.1 — Видеть прогресс первой индексации (P0)
**As a** Learner,
**I want** видеть прогресс и ETA при первом `build_index`,
**so that** я не думаю, что процесс завис.

**Acceptance:**
- Given в `data/` лежит ≥1 документ,
- When я запускаю build_index CLI,
- Then в stdout я вижу: количество обработанных документов / total, текущий файл,
  средний throughput и оценку оставшегося времени.

## Status History

- 2026-04-22 | status: `closed` | covered_by: `epoch-ingest-first-index-progress` | closed_date: `2026-04-22`
