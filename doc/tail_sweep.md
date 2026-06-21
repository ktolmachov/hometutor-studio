# Tail sweep (исполнение)

Актуализировано: **2026-04-06**

Политика: [doc/roadmap_governance.md](roadmap_governance.md) (Tail Sunset Policy: 90 дней с `last_review`).

**SSoT:** статусы пакетов и поля вроде `last_review` живут в [doc/backlog_registry.yaml](backlog_registry.yaml). Таблица § **Truth View** в [doc/tasklist.md](tasklist.md) **генерируется** из реестра — после правок YAML пересобрать производный файл:

`python scripts/backlog_registry_lint.py --sync-from-index --write-sync`

Для обзора «как сейчас в weekly view» можно открыть `tasklist.md` **после** синка; не править markdown-таблицу статусов вручную.

## Чеклист (ежеквартально или при backlog review)

1. Убедиться, что `doc/tasklist.md` актуален относительно реестра (команда выше). Для чтения — § **Truth View** в [doc/tasklist.md](tasklist.md) или соответствующие `items` в `backlog_registry.yaml`.
2. Для каждой строки со статусом `partial`, `next` или tail без явной даты: проверить `last_review` (в YAML у пакета / в зеркальной таблице после синка).
3. Если с последнего review прошло **≥ 90 дней** — зафиксировать одно решение:
   - **absorbed** (указать owner-итерацию в тексте) — логика перенесена;
   - **parking lot** — оставить в backlog с новой датой следующего review;
   - **won't do** — явно снять с execution path;
   - **archive** — только исторический интерес, перенести детали в `doc/closed_iterations.md` при необходимости.
4. Внести изменения в **`doc/backlog_registry.yaml`** (статус, `last_review`, заметки). Снова запустить `backlog_registry_lint.py --sync-from-index --write-sync`. При необходимости обновить § **Immediate Backlog** / **Deferred** в реестре или сопутствующих doc-доках по политике roadmap.

## Обход репозитория (поиск устаревших review)

Из корня репозитория (нужен [ripgrep](https://github.com/BurntSushi/ripgrep)):

```bash
rg "last_review" doc/backlog_registry.yaml
rg "Last review" doc/tasklist.md doc/future_roadmap.md
```

Даты в формате `YYYY-MM-DD` сравнивать с текущей датой вручную или скриптом — автоматизация не обязательна (KISS). Для новых проходов приоритетнее смотреть **`last_review` в YAML**; строка в `tasklist.md` — отражение после синка.

## Журнал проходов

| Дата | Источник правды | Итог |
|------|-----------------|------|
| 2026-04-06 | § Truth View в [`tasklist.md`](tasklist.md) (запись до уточнения SSoT в этом чеклисте) | Порог **90 дней** ни для одной строки не превышен; sunset не применялся. Строки с `partial` / хвостами: зафиксированы решения (см. ниже). Обновлён `Last review` у строк таблицы на дату sweep. |

### Проход 2026-04-06 (детализация)

Опорная дата sweep: **2026-04-06**. Порог «старше 90 дней с `Last review`» — не сработал (все review не старше 2026-04-05).

| Item | Было (Last review) | Решение |
|------|-------------------|---------|
| 16 foundation | 2026-04-05 | Без изменений статуса; **review обновлён** на 2026-04-06. |
| 16 tail (partial) | 2026-04-05 | **Parking lot** для «What Changed» / synthesis archive — подтверждено; следующий owner-review **2026-07-05** (без сдвига). Truth View: обновлён только маркер последнего sweep. |
| 17 Core MVP | 2026-04-05 | closed; review → 2026-04-06. |
| 17 Core Extension | 2026-04-05 | closed; review → 2026-04-06. |
| 18 Core | 2026-04-06 | closed; без доп. действий. |
| 19 platform tail | 2026-04-06 | closed; без доп. действий. |

## Связь с `16 tail`

Расширение Freshness (**«What Changed»**, **synthesis archive**) — **parking lot** (не в текущем execution path); детали и даты — § **Parking lot (16 tail)** в [`tasklist.md`](tasklist.md) после синка с реестром (правки — в `doc/backlog_registry.yaml`). Следующий owner-review **2026-07-05**.
