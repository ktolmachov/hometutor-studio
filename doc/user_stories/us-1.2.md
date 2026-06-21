---
us_id: "US-1.2"
epic: 1
epic_name: "Epic 1: Discover & Install"
priority: "P0"
cjm_stage: "1"
cjm_moment_name: "Discover / first launch"
status: "closed"
covered_by: "strong-move-first-session-cold-open-v1"
closed_date: "2026-05-24"
---

# US-1.2 — Поднять локально без чтения 5 документов (P0)

## Epic 1: Discover & Install

[← Back to user stories index](../user_stories.md)

---

### US-1.2 — Поднять локально без чтения 5 документов (P0)
**As a** разработчик с Python 3.11,
**I want** один скрипт / одну команду, которая поднимает рабочее окружение,
**so that** я не должен вручную подбирать версии `pandas`, `plotly`, `llama_index.retrievers.bm25`.

**Acceptance:**
- Given чистый clone репозитория,
- When я выполняю установку по инструкции из README,
- Then все зависимости из тестов (`pytest tests/test_user_state.py`) проходят без `ModuleNotFoundError`.
- And `.env.example` содержит все обязательные переменные с пояснениями.

## Status History

- 2026-04-25 | status: `closed` | covered_by: `unknown-closed` | closed_date: `2026-04-25`
