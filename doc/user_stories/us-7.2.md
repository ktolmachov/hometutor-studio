---
us_id: "US-7.2"
epic: 7
epic_name: "Epic 7: Spaced Repetition & Retain"
priority: "P1"
cjm_stage: "5"
cjm_moment_name: "Return next day"
status: "closed"
covered_by: "epoch-tour-scenarios-10-14"
closed_date: "2026-04-27"
---

# US-7.2 — Soft-recovery после пропуска нескольких дней (P1)

## Epic 7: Spaced Repetition & Retain

[← Back to user stories index](../user_stories.md)

---

### US-7.2 — Soft-recovery после пропуска нескольких дней (P1)
**As a** Learner, пропустивший 5 дней,
**I want** не получить 50 overdue одним списком,
**so that** я не сдаюсь сразу.

**Acceptance:**
- Given последний login был >3 дня назад и >20 due,
- When я открываю SRS,
- Then система предлагает «recovery plan»: разнести overdue на 3–5 дней, mark остальные как deferred.

## Status History

- 2026-04-22 | status: `closed` | covered_by: `epoch-srs-plan-close` | closed_date: `2026-04-22`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-scenarios-10-14` | closed_date: `2026-04-26`
