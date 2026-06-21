# Roadmap Governance

Актуализировано: **2026-05-04**

Этот файл хранит правила управления roadmap, чтобы `backlog_registry.yaml` оставался единственным SSoT, а `tasklist.md` — коротким производным execution view.

## Роли документов

- `backlog_registry.yaml` — что делать сейчас, приоритет, статусы, owner'ы и package scope.
- `tasklist.md` — производный Truth View / weekly view; без длинных повторов закрытых пакетов (они в `closed_iterations.md`).
- `closed_iterations.md` — закрытые итерации и исторические детали.
- `future_roadmap.md` — стратегический горизонт после foundation.
- `changelog.md` — журнал документированных изменений.

## Словарь нумерации

- **Итерации поставки `16-19`, затем `24-26`** — исполняемые delivery slices.
- **Эпохи E4-E13** — крупные продуктовые волны; E13 сейчас закрыт как home UX-tail, а не новый open horizon.
- **Срезы `20.0-23.x`** — внутренний roadmap эпох, а не delivery iteration.

Главное правило: если в конфликте daily execution и horizon, приоритет всегда у delivery iteration из `backlog_registry.yaml`.

## E8 epoch discipline (User Value Delivery)

- Один **epoch** (например E8.1) — не более **5** итоговых outcomes; каждый привязан к стадии **CJM** и user story из `doc/user_stories.md`.
- Приоритет верификации: **pytest** (e2e API-flow, latency SLO для «первого ответа»), а не очередной standalone benchmark/gate-скрипт.
- Детальные parallel-agent playbooks для **закрытых** горизонтов не дублировать в daily backlog — хранить в `doc/closed_iterations.md` / истории PR.

## Active Backlog Rule

Пункт считается активным только если у него есть:

- owner
- текущий статус
- блокируемый следующий шаг или явная зависимость
- exit artifact или критерий закрытия
- `last_review`

Если этих атрибутов нет, пункт не должен получать статус `ready`/`wip` в `backlog_registry.yaml`.

## Merge-Gate Discipline

### 17 Core MVP

Нельзя расширять за счёт:

- UX-полировки
- performance cache work
- self-correction
- дальних E4-like обещаний

### 17 Core Extension

Идёт отдельным merge-gate и не должен задерживать MVP.

### 18 Core

Стартует только после честного закрытия `17 Core MVP`, а не после декларации “архитектура уже почти готова”.

## Tail Sunset Policy

Каждый tail старше **90 дней** с `last_review` должен получить одно из решений:

- `absorbed by <owner>`
- `parking lot` с датой следующего review
- `won't do`
- `archive`

## Tail Enforcement

Policy недостаточно. Нужен операционный механизм:

- короткий sweep-review каждые 2 недели
- полный sweep не реже 90 дней
- табличный отчёт по tails: `item | owner | age | proposed decision | next review`

Без такого механизма tail-policy остаётся декларацией.

## Doc-Sync Gate

Doc-sync больше не считается `nice to have`.

Минимальный gate:

1. `backlog_registry.yaml`, generated `tasklist.md` и `changelog.md` не расходятся по статусам `closed/open/deferred`.
2. Документация не обещает runtime, которого нет в коде или конфиге.
3. Миграционные оговорки по `index_version` / `generation_id` не устарели.

Checklist при смене статуса пакета:

1. Обновить статус/сводку пакета в `doc/backlog_registry.yaml` и синхронизировать `doc/tasklist.md` (скрипт `scripts/backlog_registry_lint.py --sync-from-index --write-sync`).
2. Если пакет закрыт, перенести краткую historical summary в `doc/closed_iterations.md` и не держать полный контракт в `tasklist.md`.
3. Добавить запись в `doc/changelog.md`.
5. Для затронутых US обновить `doc/user_stories/*.md`: `status`, `covered_by`, `closed_date`.
6. После правок US пересобрать `doc/user_stories_index.json`.

Реализация: pre-commit и/или CI с owner review поверх автоматической проверки.

## Truth View Contract

Для каждого активного пункта в weekly backlog должна существовать краткая строка вида:

`Item | Owner | Status | Blocks | Exit artifact | Last review`

> **Внимание (SSoT):** Таблица Truth View теперь генерируется автоматически. Источником правды является файл `doc/backlog_registry.yaml`. Запрещено править markdown-таблицу напрямую. Любые изменения статуса пакета должны вноситься в yaml-реестр, после чего `tasklist.md` обновляется линтером: `python scripts/backlog_registry_lint.py --sync-from-index --write-sync`.

**Инвариант активного пакета (не смешивать с шириной таблицы):** среди всех записей `items` в `doc/backlog_registry.yaml` одновременно допускается **не более одной** строки со статусом **`ready` или `wip`**. Остальная очередь держится в **`proposed`** (или **`deferred`** с условием возврата). Поле **`active_package_id`** рядом с `active_wave_id` дублирует id этого единственного пакета для быстрых чтений (`resolve_active_package_id` в `scripts/prompt_utils.py`); при валидном реестре его поддерживает **`python scripts/backlog_registry_lint.py --sync-from-index --write-sync`**. Проверка после закрытия пакетов и в контуре doc-sync: `scripts/roadmap_sync_check.py` (сообщение вида `expected at most one active ready/wip package`). Формулировка продублирована в шапке `doc/backlog_registry.yaml`.

Это основной антидот против когнитивной перегрузки roadmap.

## Architecture review remediation (волна закрыта, 2026-05-03)

- **SSoT findings:** `doc/archive/arch_review_baseline.yaml` — поддерживать в актуальном виде при новых finding’ах.
- **Исполнение:** волна `wave-arch-review-remediation-2026-05` в `doc/backlog_registry.yaml` — **completed**; двенадцать пакетов P1–P4 и P5 (E/D/A/C, B1–B4) доставлены и зафиксированы в `doc/closed_iterations.md` (см. также сводку в [`doc/roadmap.md`](roadmap.md)).
- **Инвариант оркестрации:** по-прежнему не более одного активного `ready`/`wip` пакета (Truth View Contract выше); любая следующая arch-remediation — **новая** волна/пакеты в реестре после решения owner.
- **При закрытии связанных пакетов:** обновлять baseline, `changelog.md`, не держать устаревшие `active_wave_id` в YAML без нужды.

## E11 Quality Guardrails

- E10.3 router baseline (`overall_accuracy=0.6538`, 17/26, dataset v1.3) is a **regression guard**, not a quality target.
- `scripts/run_router_eval.py` exits `2` only when overall accuracy drops by more than 5 p.p.; per-category drops can still hide.
- E11-D, E11-Q, and E11-R are closed; if a later full eval shows router intent failures again, open a new owner-scoped package using **E11-Q/E11-R** diagnostics as evidence.
- Use **E11-P Playwright E2E Metrics** as the closed browser-level gate for E11-A/E11-D: PR smoke on offline/fixture state, nightly live flow only when credentials are available, HTML report/trace/video as CI artifacts.
- MCP servers are local agent visibility tools, not CI gates: Playwright MCP for local browser control; Chrome DevTools MCP only for console/network/performance debugging and not on production/private browser sessions.
- **E11-R** is closed. Re-entry condition for router intent repair: a fresh full eval falls below the E11-R gate (`python scripts/run_router_eval.py` < **22/26** or per-category guardrail regression).
- Do not relabel gold to match current LLM output; relabel only after explicit orchestrator contract decision.
- Decision 2026-04-12: router intent repair tail is closed by full E11-R eval. Future router/prompt regressions reopen as a new owner-scoped quality package, not by reopening E11-D.

## E13 UX Tail Decision

- Decision 2026-04-12: deferred `17.1 UX tail` for the home surface is absorbed by **E13-A Home Mode Selector / UX Tail** and marked `closed` in `doc/backlog_registry.yaml`.
- Re-entry for `17.1 UX tail` requires fresh user feedback or a CJM gap; do not reopen it just to add another home widget.
- Guardrail: home UX work must route to existing full surfaces instead of duplicating Quiz, Adaptive Daily Plan, Progress, gamification, or Knowledge Graph on the first screen.

## Interactive Tour Wave Discipline

- Тур не должен дублировать функциональность существующих panels/views — только переключать `current_view` и рендерить overlay.
- Контент глав живёт в `app/ui/tutorial_chapters.py` как структуры данных; никакого LLM в guide-runtime.
- Если `tutorial_chapters.py` приближается к 600 строк — раздробить по уровням (`_ch1.py`..`_ch5.py`) до коммита (CLAUDE.md token-safety).

## Основные управленческие риски

- `17 Core` как single point of failure для всего roadmap
- нелинейная нумерация как источник путаницы
- drift между roadmap и runtime
- постепенное расползание tails
- преждевременная конкуренция horizon-секций с текущим execution path
