---
us_id: "US-7.1"
epic: 7
epic_name: "Epic 7: Spaced Repetition & Retain"
priority: "P0"
cjm_stage: "7"
cjm_moment_name: "Spaced repetition due"
status: "closed"
covered_by: "epoch-tour-persistence-ch2-5"
closed_date: "2026-04-26"
---

# US-7.1 — Видеть очередь повторений с приоритетами (P0)

## Epic 7: Spaced Repetition & Retain

[← Back to user stories index](../user_stories.md)

---

### US-7.1 — Видеть очередь повторений с приоритетами (P0)
**As a** Learner следующего дня,
**I want** видеть due reviews отсортированными по приоритету,
**so that** я не утопаю в overdue.

**Acceptance:**
- Given в `spaced_repetition` есть >5 due концептов,
- When я открываю tutor / resume,
- Then список ограничен top-N (≤7) с явным "ещё X отложено", приоритет = days_overdue × mastery gap.

## Status History

- 2026-04-22 | status: `closed` | covered_by: `epoch-srs-priority-queue` | closed_date: `2026-04-22`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
