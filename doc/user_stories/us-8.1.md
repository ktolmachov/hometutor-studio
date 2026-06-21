---
us_id: "US-8.1"
epic: 8
epic_name: "Epic 8: Reindex Resilience"
priority: "P0"
cjm_stage: "6"
cjm_moment_name: "Adaptive plan / reindex resilience"
status: "closed"
covered_by: "epoch-mastery-gap-routing"
closed_date: "2026-04-27"
---

# US-8.1 — Сохранить mastery после reindex (P0)

## Epic 8: Reindex Resilience

[← Back to user stories index](../user_stories.md)

---

### US-8.1 — Сохранить mastery после reindex (P0)
**As a** Learner после reindex,
**I want** чтобы мой mastery vector и история не обнулились,
**so that** я не терял прогресс.

**Acceptance:**
- Given у меня есть mastery в `quiz_mastery` и `personalized_learner_model_history_json`,
- When активируется новый `index_version` / `generation_id`,
- Then `mastery_vector` rehydrate из versioned history (E5.1), lineage синхронизируется (E5.8),
  никаких orphaned current state.

## Status History

- 2026-04-25 | status: `closed` | covered_by: `epoch-demo-scenario-09-learning-plan` | closed_date: `2026-04-25`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-scenarios-10-14` | closed_date: `2026-04-26`
