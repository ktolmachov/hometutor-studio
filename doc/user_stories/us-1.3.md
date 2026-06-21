---
us_id: "US-1.3"
epic: 1
epic_name: "Epic 1: Discover & Install"
priority: "P1"
cjm_stage: "1"
cjm_moment_name: "Discover / first launch"
status: "closed"
covered_by: "epoch-tour-skeleton-ch1"
closed_date: "2026-04-26"
---

# US-1.3 — Понять, какие env-переменные обязательны (P1)

## Epic 1: Discover & Install

[← Back to user stories index](../user_stories.md)

---

### US-1.3 — Понять, какие env-переменные обязательны (P1)
**As a** новый пользователь,
**I want** при первом старте получить читаемое сообщение о недостающих env,
**so that** я не диагностирую stack trace.

**Acceptance:**
- Given в окружении нет ключевой переменной,
- When я запускаю `streamlit run app/ui/main.py`,
- Then UI открывается с offline-баннером и списком недостающих переменных, а не падает.

---

## Epic 2: Ingest

## Status History

- 2026-04-26 | status: `closed` | covered_by: `epoch-tour-skeleton-ch1` | closed_date: `2026-04-26`
