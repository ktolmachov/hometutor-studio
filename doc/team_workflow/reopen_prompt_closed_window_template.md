# Reopen prompt — шаблон: батч переоткрытия `closed → ready` за окно PERIOD

Шаблон принимает **период и scope как входные параметры** (как аудит в [generate_audit_closed_packages_prompt.md](generate_audit_closed_packages_prompt.md)): список пакетов **не захардкожен** — его нужно один раз получить из реестра командами ниже.

**Процедура:** только **Step C** того же документа (`REVERT PROCEDURE`) — без изменений `scripts/audit_closed_packages_helpers.py`.

---

## Входные параметры (подставь перед использованием)

| Параметр | Обязательно | По умолчанию | Значение |
|----------|:-------------:|--------------|-----------|
| `PERIOD` | да | — | Окно дат включительно, форматы см. ниже (**тот же контракт**, что у аудита). |
| `SCOPE` | нет | `closed` | Статусы в `doc/backlog_registry.yaml`: например `closed` или `closed,wip`. |
| `REASON` | да | — | Человекочитаемая причина переоткрытия (changelog / `re_entry_condition`). Без этого не запускать. |
| `TODAY` | нет | дата запуска | `YYYY-MM-DD` для `last_review` и пометок; по умолчанию — календарный день выполнения. |

Связанные литералы (вычислить один раз перед копированием промпта в чат):

- `$PERIOD_SLUG` = `PERIOD` с заменой `..` → `__`.
- `$START_ISO`, `$END_ISO` = из `parse_period(PERIOD)` (см. скрипт ниже).

### Форматы `PERIOD` (как в аудите)

| Формат | Пример |
|--------|--------|
| Месяц | `2026-04` |
| Несколько месяцев | `2026-03..2026-05` |
| Точные даты | `2026-04-26..2026-04-28` |

«Последние **N** календарных дней» включительно до сегодня: задай конец `END = date.today()`, начало `START = END - timedelta(days=N-1)`, затем `PERIOD = f"{START.isoformat()}..{END.isoformat()}"`.

---

## Шаг 0 — собрать список `<id>` (обязательно)

В корне репозитория задай `AUDIT_PERIOD` и при необходимости `AUDIT_SCOPE`, затем:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:AUDIT_PERIOD = '2026-04-26..2026-04-28'   # <-- замени
$env:AUDIT_SCOPE = 'closed'                     # <-- при нужде closed,wip
.\.venv\Scripts\python.exe -c "
from pathlib import Path
import os, sys, yaml
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))
from scripts import audit_closed_packages_helpers as ach
PERIOD = os.environ['AUDIT_PERIOD'].strip()
SCOPE = os.environ['AUDIT_SCOPE'].strip()
scopes = ach.parse_scope_csv(SCOPE)
data = yaml.safe_load((ROOT / 'doc/backlog_registry.yaml').read_text(encoding='utf-8'))
start, end = ach.parse_period(PERIOD)
print('START_ISO', start.isoformat())
print('END_ISO', end.isoformat())
print('PERIOD_SLUG', PERIOD.replace('..', '__'))
rows = sorted(ach.iter_closed_packages_for_period(data, start, end, scopes), key=lambda r: r['id'])
print('COUNT', len(rows))
for row in rows:
    print(row['id'])
"
```

Скопируй вывод: `COUNT`, список id, значения `START_ISO`, `END_ISO`, `PERIOD_SLUG`. Вставь их в промпт ниже без правки реестра вручную.

---

## Предупреждение

Стандартный аудит допускает Step C чаще всего после **FAIL/STALE**. Батчевое переоткрытие — **административное решение**: зафиксируй `REASON`.

**Один пакет = один полный Step C.1–C.8 + один коммит.** Не объединять пакеты в один коммит.

---

## Промпт агенту — вставить в новый чат (шаблон)

Подставь плейсхолдеры вручную или скриптом:

- `<PERIOD_SLUG>`
- `<START_ISO>`
- `<END_ISO>`
- `<REASON>` (кавычки по необходимости)
- `<TODAY>`
- Списки `{ id1, id2, ... }` из шага 0

````text
╔══════════════════════════════════════════════════════════════════╗
║  BATCH REOPEN (closed → ready)
║  Window: [<START_ISO> .. <END_ISO>]   PERIOD_SLUG: <PERIOD_SLUG>
║  Template: doc/team_workflow/reopen_prompt_closed_window_template.md
╚══════════════════════════════════════════════════════════════════╝

ROLE: Apply Step C (REVERT PROCEDURE) only, from:
  doc/team_workflow/generate_audit_closed_packages_prompt.md — § STEP C.
  Do NOT change application code except doc/registry files listed in Step C.
  Do NOT skip substeps.

GLOBAL:
  PERIOD_SLUG = <PERIOD_SLUG>
  START_ISO   = <START_ISO>
  END_ISO     = <END_ISO>
  REASON      = <REASON>
  TODAY       = <TODAY>

For EACH <id> IN LIST BELOW — sequential order — one complete Step C + one git commit:

  PACKAGE_IDS_ORDERED = (
    [вставь сюда id из вывода шага 0, по строке или через запятую]
  )

STEP C — per `<id>` (полный текст подпунктов C.1 … C.8 см. generate_audit_closed_packages_prompt.md):

  C.1 doc/backlog_registry.yaml
  C.2 doc/closed_iterations.md
  C.3 doc/user_stories_index.json  — US с covered_by == <id> и closed_date в [START_ISO, END_ISO]
  C.4 doc/user_stories/<US>.md      — только frontmatter
  C.5 doc/cjm.md
  C.6 doc/changelog.md             — только append
  C.7 после правок индекса: .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync
  C.8 git commit на один id: audit(<PERIOD_SLUG>): reopen <id> — <REASON>

After all IDs: .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py  (exit 0)

Report: таблица | Package | reopened | commit |
````

---

## Пример параметров (экземпляр, не часть контракта)

- `PERIOD=2026-04-26..2026-04-28`, `SCOPE=closed`, `TODAY=2026-04-28` приводит к тем же числам списков, что и в старом снимке «последние 3 дня» конца апреля 2026; список id всегда брать только из шага 0 на актуальный `backlog_registry.yaml`.

---

## Связанные документы

- [generate_audit_closed_packages_prompt.md](generate_audit_closed_packages_prompt.md) — Step C и индексы
- [generate_orchestration_prompt.md](generate_orchestration_prompt.md) — после переоткрытия
