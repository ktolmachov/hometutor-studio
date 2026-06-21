---
us_id: "US-7.3"
epic: 7
epic_name: "Epic 7: Spaced Repetition & Retain"
priority: "P0"
cjm_stage: "5"
cjm_moment_name: "Return next day"
status: "closed"
covered_by: "localhost-balance-course-delight-v1"
closed_date: "2026-05-23"
---

# US-7.3 — Видеть «где остановился» сразу при входе (P0)

## Epic 7: Spaced Repetition & Retain

[← Back to user stories index](../user_stories.md)

---

### US-7.3 — Видеть «где остановился» сразу при входе (P0)
**As a** Learner следующего дня,
**I want** на главном экране видеть resume card,
**so that** я не ищу прошлую сессию вручную.

**Acceptance:**
- Given существует `tutor_learning_resume` с session_id и topic,
- When я открываю UI,
- Then в hero виден resume card с topic, last_action, due_count и кнопкой "Продолжить".

## Status History

- 2026-04-21 | status: `closed` | covered_by: `epoch-us7-3-resume-card` | closed_date: `2026-04-21`
- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-persistence-ch2-5` | closed_date: `2026-04-26`
