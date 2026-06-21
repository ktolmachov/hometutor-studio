---
us_id: "US-9.1"
epic: 9
epic_name: "Epic 9: Progress & Motivation"
priority: "P1"
cjm_stage: "8"
cjm_moment_name: "Progress check"
status: "closed"
covered_by: "epoch-cjm-progress-next-action"
closed_date: "2026-05-01"
---

# US-9.1 — Один экран прогресса (P1)

## Epic 9: Progress & Motivation

[← Back to user stories index](../user_stories.md)

---

### US-9.1 — Один экран прогресса (P1)
**As a** Learner,
**I want** один tab "Progress" с mastery, weekly goals, streak и графом,
**so that** я не собираю метрики из 4 мест.

**Acceptance:**
- Given у меня есть данные за ≥1 неделю,
- When я открываю Progress tab,
- Then я вижу в одном месте: mastery vector, `weekly_goals` state, `daily_streak` и KG snapshot.
- And данные берутся из существующих источников (`user_state`, `gamification_service`, KG / progress visuals), без нового тяжёлого dashboard.
- And если часть данных отсутствует, UI показывает компактный fallback вместо пустого блока.

## Status History

- 2026-04-25 | status: `closed` | covered_by: `epoch-demo-scenario-07-progress` | closed_date: `2026-04-25`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
