# 📦 Архив Документации

> Замороженные материалы, исторические решения и старые планы.
> Используйте для понимания, как и почему были приняты те или иные решения, но **не как источник текущего состояния системы**.

**Дата архивирования:** 2026-04-25

---

## 📋 Содержимое Архива

### 🏛️ Архитектурные Решения (историческое)

| Файл | Почему заархивирован | Когда полезен |
|---|---|---|
| **adr_rag_architecture.md** | Старая редакция ADR (April 2026); актуальное в `doc/adr.md` | Если нужна историческая перспектива ранних решений по RAG |
| **architectural_refactoring.md** | План рефакторинга выполнен; реальная архитектура в `doc/architecture.md` | Понимание миграции между версиями архитектуры |
| **blue_green_reindex_design.md** | Дизайн реализован и закрыт в E6–E8 | История как был реализован safe reindex |
| **blue_green_reindex_implementation_plan.md** | План выполнен; текущий процесс в `doc/index_lifecycle.md` | Контекст для анализа старых ошибок в reindex |

### ⚙️ Технические Отчёты (статические снимки)

| Файл | Почему заархивирован | Когда полезен |
|---|---|---|
| **architecture_review_2026-04-24.md** | Снимок архревью на дату; следующий review будет свежее | Если нужно сравнить состояние архитектуры между датами |
| **arch_review_baseline.yaml** | Baseline для incremental reviews; используется в `doc/agent_workflow_arch_review.md` | Непрямое использование через workflow агентов |
| **workflow_hardening_plan_2026-04-24.md** | Одноразовый точечный план; применён и закрыт | История того, какие hardening'и были сделаны в апреле |
| **kilo_budget_remediation_plan.md** | План коррекции бюджета выполнен; актуальное в `doc/kilo_budget_system.md` | Контекст как проблема была обнаружена и решена |

### 📊 Планы и Чеклисты (исполненные)

| Файл | Почему заархивирован | Когда полезен |
|---|---|---|
| **token_optimization_plan.md** | Исходный план оптимизации; реализованная версия в коде и `doc/token_safety.md` | История эволюции token-бюджетной системы |
| **token_optimization_checklist.md** | Детальный чеклист оптимизации; закрыт | Если нужны исторические метрики и пороги до текущего состояния |
| **IMPLEMENTATION_COMPLETE.md** | Отчёт о внедрении token-safety (готово); финал в `doc/token_safety.md` | Обзор всех этапов внедрения token-guardrails |
| **IMPLEMENTATION_P0_P1.md** | Отчёт о P0/P1-фазах внедрения (готово) | История фазированного развёртывания |
| **tasklist_historical.md** | Старый weekly backlog; текущий в `doc/tasklist.md` | Контекст закрытых спринтов и exit criteria |

### 📝 Исторические Записки

| Файл | Почему заархивирован | Когда полезен |
|---|---|---|
| **handoff_next_level.md** | Историческая хэндовер-записка между сессиями | Контекст переходов между phase-ами проекта |

---

## 🎯 Как Пользоваться Архивом

### ✅ Когда Читать Архив:
- **Archaeology** — понимаете баг и хотите узнать, как он появился
- **Historical Context** — нужна история решения или план, который был выполнен
- **Версионирование** — сравниваете текущее состояние с прошлым

### ❌ Когда НЕ Читать Архив:
- Ищете **текущее состояние системы** → читайте `doc/architecture.md`, `doc/adr.md`
- Ищете **актуальный процесс** → читайте `doc/agent_workflow*.md`, `doc/team_workflow/`
- Ищете **roadmap** → читайте `doc/tasklist.md`, `doc/future_roadmap.md`
- Хотите **запустить приложение** → `doc/user_guide.md`, `doc/quickstart.md`

---

## 🗺️ Справочник По Замене

Если вы нашли ссылку на архивный файл в документации, вот куда перейти вместо:

| Архивный файл | Замена |
|---|---|
| `adr_rag_architecture.md` | → `doc/adr.md` (обновлённые ADR) |
| `architectural_refactoring.md` | → `doc/architecture.md` (текущая архитектура) |
| `blue_green_reindex_*.md` | → `doc/index_lifecycle.md` (current reindex process) |
| `tasklist_historical.md` | → `doc/tasklist.md` (active backlog) |
| `token_optimization_checklist.md` | → `doc/token_safety.md` (current standards) |
| `IMPLEMENTATION_COMPLETE.md` | → `doc/token_safety.md` или `doc/kilo_budget_system.md` |
| `handoff_next_level.md` | → `doc/current_task.md` (текущая работа) |
| `workflow_hardening_plan_*.md` | → `doc/conventions.md` (окончательные правила) |
| `architecture_review_*.md` | → `doc/adr.md` (latest decisions) |
| `kilo_budget_remediation_plan.md` | → `doc/kilo_budget_system.md` (active system) |

---

## 📅 История Архивирования

**2026-04-25**: Большой рефакторинг документации
- Переработан `doc/index.md` в полноценный навигатор с таблицами и быстрым старт по ролям
- 14 старых документов переместили в `archive/` для чистоты основной папки `doc/`
- Обновлены 56 ссылок в 11 документах
- Создан этот гид

---

> 💡 **Дальше архив не читайте** — закоммитьте эту папку и забудьте про неё. Если историческая информация нужна — она здесь, но это редко случается.
