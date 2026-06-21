# PO Router — Conflict Resolution Rules

Модуль роутера продуктового планирования.  
Основной файл: [`product_owner_router.md`](product_owner_router.md).

Актуализировано: **2026-05-08**

---

## Правила разрешения конфликтов

| Ситуация | Приоритет | Действие |
|----------|-----------|----------|
| `proposed` в registry + plan-next blocker | **Registry wins** | 1. Review proposed packages<br>2. Если не подходят → ideation |
| `deferred` + `re_entry_condition` met + новая ideation | **Re-entry wins** | 1. Проверить `re_entry_condition`<br>2. Если met → activate deferred<br>3. Иначе → ideation |
| Несколько `proposed` волн | **Wave ranking formula** | Применить `wave_synergy_score` + `mot_recency_gap` из `backlog_registry.yaml` |
| Ideation artifact + existing US | **Merge strategy** | 1. Проверить дубли в `user_stories_index.json`<br>2. Если дубль → update existing US<br>3. Иначе → create new US |
| Parallel ideation runs для одного TARGET | **Latest wins** | Использовать artifact с newest timestamp |
| Owner decision conflict (2 PO) | **Escalate** | Sync meeting для alignment |

---

## Алгоритм проверки конфликтов

> ⚠️ **Скрипт `check_backlog_conflicts.py` не реализован.** Используйте manual check:

```powershell
# Проверить conflicts вручную:
Select-String -Path doc/backlog_registry.yaml -Pattern "status: proposed|status: deferred|status: wip|status: ready"

# Или использовать существующий скрипт drift:
.\.venv\Scripts\python.exe scripts\check_backlog_drift.py
```

---

## Примеры разрешения

### Пример 1: Proposed packages существуют

```text
Ситуация: plan-next blocker, но в registry есть 2 proposed packages

Действие:
1. Прочитать doc/backlog_registry.yaml (grep "status: proposed")
2. Review каждый proposed package:
   - Есть ли owner approval?
   - Актуален ли scope?
   - Блокирует ли что-то?
3. Если подходит → promote к ready
4. Если нет → ideation для нового направления
```

### Пример 2: Deferred re-entry

```text
Ситуация: deferred item 'ocr-docling' имеет re_entry_condition: "US-2.3 accepted"

Действие:
1. Проверить doc/user_stories/us-2.3.md (status: closed)
2. Condition met → activate deferred
3. Обновить status: deferred → ready
4. Sync registry
5. Запустить workflow.py
```
