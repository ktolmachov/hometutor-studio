# Экземпляр батч-переоткрытия по шаблону reopen_prompt_closed_window_template.md

**Сгенерировано:** экземпляр для окон **последних 3 календарных дней**, конец окна = **2026-04-28**.  
**Шаблон:** [reopen_prompt_closed_window_template.md](reopen_prompt_closed_window_template.md)

Чтобы не было drift с актуальным реестром при повторном использовании через неделю — заново выполни **шаг 0** из шаблона или пересчёт с `date.today()`.

---

## Привязка параметров

| Параметр | Значение |
|----------|-----------|
| `PERIOD` | `2026-04-26..2026-04-28` |
| `SCOPE` | `closed` |
| `PERIOD_SLUG` | `2026-04-26__2026-04-28` |
| `START_ISO` | `2026-04-26` |
| `END_ISO` | `2026-04-28` |
| `TODAY` (выполнение) | `2026-04-28` |
| `COUNT` | 13 |

**`REASON`:** подставь сам одной строкой, например:  
`admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — <кратко зачем>`

---

## Промпт агенту — вставить в новый чат

```text
╔══════════════════════════════════════════════════════════════════╗
║  BATCH REOPEN (closed → ready)
║  Window: [2026-04-26 .. 2026-04-28]   PERIOD_SLUG: 2026-04-26__2026-04-28
║  Template: doc/team_workflow/reopen_prompt_closed_window_template.md
╚══════════════════════════════════════════════════════════════════╝

ROLE: Apply Step C (REVERT PROCEDURE) only, from:
  doc/team_workflow/generate_audit_closed_packages_prompt.md — § STEP C.
  Do NOT change application code except doc/registry files listed in Step C.
  Do NOT skip substeps.

GLOBAL:
  PERIOD_SLUG = 2026-04-26__2026-04-28
  START_ISO   = 2026-04-26
  END_ISO     = 2026-04-28
  REASON      = "admin reopen: batch last-3-days window 2026-04-26..2026-04-28 — <уточни человеком>"
  TODAY       = 2026-04-28

For EACH <id> IN LIST BELOW — sequential order — one complete Step C + one git commit:

  PACKAGE_IDS_ORDERED = (
    epoch-control-plane-v3-core,
    epoch-demo,
    epoch-e30-a1-cockpit-scaffold,
    epoch-e30-a2-cockpit-rotator,
    epoch-e30-b1-graduation-overlay,
    epoch-e30-b2-daily-briefing,
    epoch-e30-c1-diagnostic,
    epoch-e30-c2-pace-engine,
    epoch-e30-d1-smart-resume,
    epoch-e30-d2-focus-mode,
    epoch-e30-e1-course-graduation,
    epoch-e30-idea-1-daily-runway,
    epoch-e30-idea-2-retrieval-gates
  )

STEP C — per `<id>` (полный текст подпунктов C.1 … C.8 см. generate_audit_closed_packages_prompt.md):

  C.1 doc/backlog_registry.yaml
  C.2 doc/closed_iterations.md
  C.3 doc/user_stories_index.json  — US с covered_by == <id> и closed_date в [START_ISO, END_ISO]
  C.4 doc/user_stories/<US>.md      — только frontmatter
  C.5 doc/cjm.md
  C.6 doc/changelog.md             — только append
  C.7 после правок индекса: .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync
  C.8 git commit на один id: audit(2026-04-26__2026-04-28): reopen <id> — <REASON>

After all IDs: .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py  (exit 0)

Report: таблица | Package | reopened | commit |
```
