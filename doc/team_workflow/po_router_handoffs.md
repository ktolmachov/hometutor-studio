# PO Router — Role Handoffs

Модуль роутера продуктового планирования.  
Основной файл: [`product_owner_router.md`](product_owner_router.md).

Актуализировано: **2026-05-08**

---

## Product Owner → Analyst

**Триггер:** Ideation вернул идеи, но нет user story

**Handoff prompt:**
```text
Прочитай doc/team_workflow/analyst.md

Контекст:
- Ideation artifact: <path to artifact>
- Accepted idea: <title>
- CJM moment: <moment>
- Method source: <source>

Задача:
1. Создать user story US-<epic>.<number> для этой идеи
2. Определить acceptance criteria (measurable, ≤5 criteria)
3. Связать с CJM moment
4. Проверить дубли с existing US (user_stories_index.json)
5. Вернуть к Product Owner для package planning

Deliverable:
- doc/user_stories/us-<id>.md
- Обновлённый doc/user_stories_index.json
```

**Expected turnaround:** 2-4 часа

---

## Analyst → Product Owner

**Триггер:** User story создана и validated

**Handoff message:**
```text
✅ US-<id> готова: doc/user_stories/us-<id>.md

Summary:
- Title: "<title>"
- Value: <value statement>
- CJM: <moment>
- Priority: <P0/P1/P2>

Следующий шаг для PO:
- Запустить product_owner_plan_package_prompt.md с US-<id>
- Или добавить US-<id> в existing wave (если cohesive)
```

---

## Product Owner → Architect

**Триггер:** Package planning показал technical risks или dependencies

**Handoff prompt:**
```text
Прочитай doc/team_workflow/architect.md

Контекст:
- Package: <package-id>
- Goal: <goal>
- User stories: <US list>
- Risk: "<risk description>"
- Dependency: "<dependency>"

Задача:
1. Оценить technical feasibility
2. Предложить architecture approach
3. Определить write_set и read_set
4. Оценить cost (S/M/L) и risks
5. Проверить conflicts с existing packages
6. Вернуть к Product Owner с recommendation

Deliverable:
- archive/team_artifacts/<package-id>/architecture.md
- Updated cost_estimate в package contract
```

**Expected turnaround:** 4-8 часов

---

## Architect → Product Owner

**Триггер:** Technical design готов

**Handoff message:**
```text
✅ Architecture design готов: archive/team_artifacts/<package-id>/architecture.md

Findings:
- Feasible: ✅/❌
- Approach: <summary>
- Write-set: <N> файлов
- Cost estimate: <S/M/L>
- Risks: <summary>

Recommendation: ✅ Approve / ⚠️ Условно / ❌ Block

Следующий шаг для PO:
1. Принять package contract
2. Записать в backlog_registry.yaml (status: ready)
3. Sync registry
4. Запустить workflow.py
```

---

## Handoff to Execution (после registry)

### Связь с workflow_router.md

| Роутер | Зона ответственности | Граница |
|--------|---------------------|---------| 
| **product_owner_router** | Planning (до `ready`) | Запись в `backlog_registry.yaml` + sync |
| **workflow_router** ([`workflow_router.md`](workflow_router.md)) | Execution (после `ready`) | orchestration/execution_auto → DoD → close |

### ⚠️ Первый шаг execution может быть ручным

После `status: ready` workflow.py может вернуть:
1. **`ready_fresh`** → автокоманда orchestration
2. **`ready_orch`** → **РУЧНОЙ ШАГ**
3. **`ready_executing`** → **РУЧНОЙ ШАГ**
4. **`execution_auto`** → автокоманда для low-complexity

Детали: [`workflow_router.md`](workflow_router.md).

### Checkpoint перед handoff

- ✅ Package в `backlog_registry.yaml` имеет `status: ready`
- ✅ `wave_id` указан и wave существует
- ✅ `user_stories` ссылаются на существующие US файлы
- ✅ `dod_commands` заполнены и executable
- ✅ `backlog_registry_lint.py --strict` зелёный
- ✅ `tasklist.md` обновлён через `--sync-from-index --write-sync`
