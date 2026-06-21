# Token Optimization Checklist (2026-04-20)

## Резюме Оптимизаций

Потребление входных токенов снижено на **40–60%** в типовом агент-вызове благодаря пяти критическим изменениям в шаблонах и промтах.

**Актуализация 2026-04-20:** добавлены критический разбор самого чеклиста, синхронизация лимитов с `doc/agent_workflow.md` (12k / 20k), пересчёт оценок размеров файлов по рабочему дереву, пометка что блок **Token Firewall (P0–P6 + P1A)** — дорожная карта (скрипты в репозитории на момент правки могут отсутствовать), полный консолидированный список рекомендаций и отдельный пакет **Context Cart / task-aware context routing** для средних doc-файлов из шаблонов.

**Ключевые метрики:**
- Baseline: ~18–24k входных токенов на планирование/verify-вызов
- После оптимизации: ~10k (планирование), ~6k (verify)
- Доля экономии: -40% для типовых, -50–60% для больших read-sets

---

## ✅ Реализованные Рекомендации (Приоритет по ROI)

### 1. Ограничение Read-set до 3–5 Файлов (Эффект: -40–50%)

**Что изменилось:**
- `doc/agent_workflow.md`, раздел "Какие файлы читать" → явное ограничение max 5 файлов
- Все шаблоны (Micro-Plan, Planning Prompt, Micro-Execute) теперь содержат **"Read ONLY (max N файлов)"**
- Исключены избыточные файлы: полный `closed_iterations.md`, `doc/cjm.md` целиком, `doc/epochs/*` целиком, `doc/api_reference.md` полный

**Как использовать:**
Перед каждым LLM-вызовом явно выписать read-set:
```text
Read ONLY (max 5 файлов):
1. app/query_service.py — signatures only (не full body при >600 строках)
2. tests/test_query_service.py — grep "def test_" + один релевантный тест, не весь файл
3. doc/tasklist.md — строка <target-package> ONLY
```

**Проверка:** Если контекст растёт выше 20k → перезапустить с меньшим read-set, не добавлять файлы.

---

### 2. Запрет glm-5.1, Fallback на grok-4.1 (Эффект: -25% Стоимости)

**Что изменилось:**
- `doc/agent_workflow.md`, раздел "Model routing" → явный запрет glm-5.1
- Базовая модель: `grok-4.1-fast-thinking` для всех вызовов по умолчанию
- Дорогая reasoning-модель: только для критических архитектурных анализов с явным одобрением

**Почему:**
Анализ call #14 показал, что glm-5.1 стоит ~4–5× дороже grok-4.1 при аналогичном качестве результата.

**Как использовать:**
- Используй grok-4.1 для planning, execution, verify по умолчанию
- Запросить одобрение перед использованием дорогой модели в промте контракта

---

### 3. Явное Ограничение History (Эффект: -15–20%)

**Что изменилось:**
- `doc/agent_workflow.md`, раздел "Ограничение history" → добавлено **"Scope: Ignore prior responses/tools. Fresh context only."**
- Все шаблоны (Micro-Plan, Micro-Execute, Micro-Verify) содержат эту строку

**Как использовать:**
Каждый новый LLM-вызов начинайте с явного statement:
```text
Ignore prior responses/tools. Fresh context only.
```

**Проверка:** Если контекст содержит history из предыдущих вызовов → удалить, оставить только последние 2–3 шага.

---

### 4. Fallback для Больших Контекстов (Эффект: Предотвращение 3+ Ретраев, -10% Риска)

**Что изменилось:**
- `doc/agent_workflow.md`, раздел **Retry policy** и **Token Budget**: целевой вход **≤12k**, soft **12k–20k** (обязательное сжатие), **>20k — вызов запрещён** (hard-limit). Ретрай с тем же payload после ERR **запрещён**; допускается **не более одного** ретрая после сжатия history/read-set.

**Как использовать:**
- Перед **каждым** облачным вызовом оценить вход: при **>20k** — **не отправлять**, сжать read-set/history или разбить задачу на фазы.
- В soft-зоне **12k–20k** — убрать старые tool-логи, сократить вставки файлов до snippets, заменить полные тесты на `rg` + один кейс.
- Ранее в этом чеклисте фигурировал порог **>40k** — это **устаревшая** формулировка относительно текущего контракта проекта; ориентир для stop/retry — **20k** (как в `doc/agent_workflow.md` и `doc/token_safety.md`).
- Максимум **1** безопасный ретрай после сжатия; далее — остановка и отчёт о блокере.

---

### 5. Исключение Избыточных Файлов (Эффект: -20–30% для Big Calls)

**Что изменилось:**
- `doc/agent_workflow.md` → явный список файлов и паттернов, которые нельзя тащить в контекст «по умолчанию» целиком или пачкой без режима чтения.

**Как использовать (уточнение по размерам на 2026-04-20):**
- ❌ **`doc/tasklist.md` целиком** — по-прежнему плохо по смыслу (шум) и может разрастись; читать **только строку целевого пакета**.
- ❌ **`doc/cjm.md` целиком** — файл **плотный по байтам** (~6.3k est даже при ~240 строках); брать **только** journey/pain-секцию.
- ❌ **`doc/epochs/` как каталог или много файлов подряд** — суммарно легко уйти в десятки тысяч токенов; читать **один** epoch-файл и **не** `doc/epochs/e4.md` целиком (самый тяжёлый).
- ❌ **`doc/api_reference.md` целиком** — умеренный размер, но в связке с кодом/тестами быстро съедает бюджет; только нужные endpoint-группы.
- ⚠️ **`doc/closed_iterations.md`:** в **текущем** дереве файл **короткий** (оценка порядка **<1k** est); цифра «15–20k» в старых примерах относилась к **длинным** сессиям/историческим версиям. Практическое правило не меняется: не включать «на всякий случай» — только абзац/slice по пакету.
- ❌ **`doc/changelog.md` целиком** — крупный и растущий; только хвост или заготовка под append.

**Как использовать:**
Вместо полных файлов:
- Используй **`doc/epochs/<target-epoch>.md`** (фрагмент/header), а не скан всей папки; **`e4.md`** не открывать целиком без предобработки.
- Читай только целевую секцию из `doc/cjm.md`.
- Читай одну строку из `doc/tasklist.md`.

---

## 🎯 Чек-Лист Перед Каждым LLM-Вызовом

Используй этот чек-лист, чтобы убедиться, что контекст оптимизирован:

- [ ] **Read-set:** ≤ 5 файлов (рутина — 2–3), явно перечисленных в промте
- [ ] **Запрещённые файлы:** проверил каждый файл через `python scripts/check_readset.py` или таблицу в `doc/token_safety.md`
- [ ] **Крупные файлы (>600 строк):** использую signatures/grep/секцию — не full-read
- [ ] **History:** добавлена фраза "Ignore prior responses/tools. Fresh context only."
- [ ] **Model:** базовая (не reasoning-модель) для типовых вызовов
- [ ] **Контекст:** ≤ 12k токенов (hard stop при >20k)
- [ ] **Ретрай:** только после сжатия history/read-set, максимум 1 безопасный ретрай
- [ ] **Мета:** не прикреплять целиком длинные архивные контракты без необходимости (doc/agent_workflow.md теперь slim index, full_read allowed)
- [ ] **Owner vs Read:** в контракте есть явная строка, что owner/write-set ≠ read-set

**Быстрая проверка:**
```bash
python scripts/check_readset.py <file1> <file2> ...
# SAFE=0 / WARN=1 / BLOCK=2
```

---

## 📊 Примеры Экономии

### Пример 1: Planning Call (было 83k, стало ~10k, -88%)

**Было (Call #5):**
```
doc/tasklist.md (целиком): 8k
doc/epochs/ (3 файла): 6k
doc/cjm.md (целиком): 2k
doc/closed_iterations.md (целиком): до **~20k** только в «тяжёлых» исторических сценариях; в актуальном дереве см. таблицу размеров
doc/conventions*.md (3 файла): 12k
Target files (5 файлов): 15k
Tests: 3k
History from prior calls: 17k
---
Total: 83k токенов, 19% сессии
```

**Стало (оптимизировано):**
```
Target file (app/query_service.py): 5k
Target test (tests/test_query_service.py): 2k
doc/tasklist.md (одна строка): 0.5k
Model: grok-4.1 вместо glm-5.1
History: свежий, без накопления
---
Total: ~10k токенов (-88%), -2% сессии
```

### Пример 2: Verify Call (было 15k, стало ~6k, -60%)

**Было:**
```
Contract file: 3k
Commit diff: 2k
Full project scan: 8k
Task history: 2k
---
Total: 15k
```

**Стало:**
```
Contract file: 3k
Commit diff: 2k
No project scan
Fresh context, no history
---
Total: ~6k (-60%)
```

---

## ⚙️ Обновлённые Шаблоны

Все шаблоны в `doc/agent_workflow.md` обновлены. Вот ключевые:

### ✅ Micro-Plan (~1,500 токенов, strict read-set)
```text
Read ONLY (max 3 files):
1. <target-file.py> — signatures only (если >600 строк — не full body)
2. <target-test.py> — grep "def test_" + один релевантный тест, не весь файл
3. [OPTIONAL] doc/tasklist.md — ONLY row <target-package>

Ignore prior responses/tools. Fresh context only.
```

### ✅ Micro-Execute (~1,200 токенов)
```text
Read ONLY (max 2 files):
- <target-file.py>
- <target-test.py>

Ignore prior responses/tools. Fresh context only.
```

### ✅ Micro-Verify (~800 токенов)
```text
Ignore prior responses/tools. Fresh context only.

Steps:
1. Run: <command>
2. Check diff...
```

### ✅ Planning Prompt (вместо 35k → ~10k)
Читает только 3 файла вместо 9.

---

## 🔄 Переход На Новые Шаблоны

### Для Новых Agent Запросов (с 2026-04-19)
Используй обновлённые шаблоны из `doc/agent_workflow.md` — они автоматически лимитируют read-set и history.

### Для Существующих Потоков
Если у тебя уже идёт диалог с агентом:
1. Перезапусти с новым шаблоном, если контекст превышает 20k
2. Явно добавь "Ignore prior responses/tools" в начало нового промта
3. Перечисли read-set (max 5 файлов) перед задачей

---

## 📈 Ожидаемые Результаты

После внедрения:
- **Медиана стоимости на вызов:** 1.26 руб → ~0.8 руб (-36%)
- **Базовые входные токены:** 18.8k → ~11k (-41%)
- **Максимальная стоимость вызова:** 7.12 руб (glm-5.1) → 1.5–2 руб (grok-4.1)
- **Ретраи из-за контекста:** 3–5 за сессию → 0–1 (fallback вместо ретрая)

---

## Критический разбор документа (самоаудит)

| Проблема | Почему это важно | Что сделано в этой версии |
|---|---|---|
| **Порог 40k vs 20k** | Расхождение с `doc/agent_workflow.md` и `doc/token_safety.md` создаёт ложное чувство безопасности | П.4 приведён к **12k / 20k**; 40k помечен как устаревшая отсылка |
| **Устаревшие оценки по файлам** | Таблицы «строк / токенов» устаревают после каждого крупного merge | Таблицы ниже **пересчитаны** по рабочему дереву на **2026-04-20**; добавлена рекомендация периодически прогонять измерение |
| **`doc/closed_iterations.md` «15–20k»** | Вводило в заблуждение: в текущем дереве файл короткий, риск — в привычке читать «целиком без цели» | П.5 уточнён: отдельно **текущий размер** и **практическое правило** |
| **Дублирование с `doc/token_safety.md`** | Два источника с разными цифрами → агент выбирает «удобную» оценку | Явно: **канонические safe-methods** — в `doc/token_safety.md`; этот чеклист — **операционный** чек + ROI + Cursor-специфика |
| **Блок P0–P6 описывает артефакты** | В репозитории может не быть `token_safety.yml`, `build_context_pack.py` — риск принять план за факт | Заголовок блока помечен как **roadmap**; DoD остаётся целевым контрактом на будущие пакеты |
| **Примеры read-set без режима** | Строка «`tests/test_query_service.py`» без «patterns only» провоцирует full-read | Обновлены пример в §1 и блок Micro-Plan; добавлен **полный** список рекомендаций с режимами |
| **`doc/agent_workflow.md` как @-вложение** | Сам файл **>1200 строк / ~66 KiB** — один attach почти съедает soft-limit | Добавлен в таблицу рисков и в рекомендации: не прикреплять целиком в каждый вызов |

---

## 🚨 Red Flags (Признаки Того, Что Оптимизация Не Работает)

Если видишь одно из ниже — перезапусти с меньшим read-set:
- ❌ Оценка входа **>20k** перед отправкой (hard-limit проекта) или стабильно **>12k** без причины (нарушение целевого режима)
- ❌ Промт содержит 8+ файлов в read-set
- ❌ Есть строки вроде "doc/closed_iterations.md", "doc/epochs/ (all)", "doc/cjm.md (full)"
- ❌ History содержит более 3 прошлых шагов целиком
- ❌ Вызов использует glm-5.1 для рутинной задачи
- ❌ Третий+ ретрай подряд (значит, need fallback truncation)

---

## 🔎 Cursor AI Audit: Почему Растут Входные Токены

Анализ `doc/agent_workflow.md` показывает, что основной риск для Cursor AI возникает не в low-budget шаблонах `Micro-Plan` / `Micro-Execute`, а в широких контрактных промтах для planning, verify и особенно Architecture Review. Cursor склонен трактовать формулировки вроде `app/*`, `tests/*`, `scripts/*`, "scan the codebase", "Read doc/adr.md and doc/architecture.md", "Owner files" и "Read these files as authoritative baseline" как разрешение включить полные файлы или большие tool-output блоки в следующий LLM-вызов.

Технические причины высокого входного контекста:
- **Широкий baseline вместо bounded read-set.** Блок Architecture Review перечисляет документацию, core-модули, UI, тесты и `doc/epochs/`; если читать всё целиком, один вызов легко уходит за 80k.
- **Owner files смешиваются с read-set.** В execution-контрактах список владения может быть воспринят как список файлов для полного чтения, хотя owner/write-set не равен read-set.
- **Полные тесты дороже кода.** `tests/test_api.py` и `tests/test_query_service.py` большие; для контракта обычно нужны 1-2 test cases, fixtures или `rg "def test_<pattern>"`.
- **Документы с историей и решениями накапливаются.** `doc/changelog.md`, `doc/adr.md`, `doc/cjm.md`, `doc/epochs/*` часто добавляют контекст "на всякий случай", но для текущей задачи нужна строка, таблица статусов, конкретный pain point или header.
- **История tool calls добавляется повторно.** Cursor может переносить предыдущие grep/read/test outputs в новый запрос; это особенно дорого после architecture/codebase scans.
- **Грубые оценки в шаблонах устаревают.** Фактические размеры файлов меняются; перед вызовом нужно проверять текущий размер, а не полагаться только на старую пометку в промте.

### Файлы Из Шаблонов, Которые Нельзя Читать Целиком

Оценка: `EstTokens ≈ UTF-8 bytes / 4` (грубо; tokenizer модели может отличаться). **Измерено в рабочем дереве: 2026-04-20.**

| Файл | Строк | Est tokens | Риск | Безопасный метод |
|---|---:|---:|---|---|
| `doc/epochs/e4.md` | 742 | ~23,000 | BLOCK | Только header / целевой фрагмент; не весь файл |
| `app/prompts.py` | 1194 | ~18,400 | BLOCK | `rg -n "^def|^[A-Z_].*=" app/prompts.py` + одна секция |
| `doc/changelog.md` | 551 | ~15,700 | BLOCK | Только последние 2–3 записи или append-target |
| `tests/test_api.py` | 1614 | ~14,200 | BLOCK | `rg "def test_<pattern>" tests/test_api.py` + один test case |
| `doc/adr.md` | 666 | ~13,800 | BLOCK | Только Status-таблица / конкретный ADR |
| `app/knowledge_graph.py` | 1258 | ~13,700 | BLOCK | `rg -n "^class|^def " app/knowledge_graph.py` + при необходимости один класс |
| `doc/agent_workflow.md` | 64 | ~1.1k | OK (slim index) | Навигационный hub; детали в topic-файлах (split 2026-04-20) |
| `tests/test_query_service.py` | 1012 | ~10,200 | BLOCK | 1–2 теста/fixture, не весь файл |
| `app/query_service.py` | 916 | ~8,450 | BLOCK | Signatures + одна функция/участок |
| `app/tutor_orchestrator.py` | 641 | ~7,100 | BLOCK | Signatures + конкретный flow |
| `app/learner_model_service.py` | 662 | ~6,750 | BLOCK | Signatures + конкретный метод |
| `doc/cjm.md` | 241 | ~6,300 | BLOCK | Только pain/journey-секция (мало строк, много текста) |
| `app/learning_plan_service.py` | 592 | ~6,100 | BLOCK | Signatures, если файл не в write-set |
| `doc/architecture.md` | 383 | ~5,100 | BLOCK | Только module list / одна секция |

### Файлы, Которые Можно Читать Только При Явной Нужде

Эти файлы не всегда нарушают hard-limit по одиночке, но быстро раздувают пакет, если идут вместе с core/test файлами:

| Файл | Строк | Est tokens | Рекомендация |
|---|---:|---:|---|
| `doc/user_guide_details.md` | 419 | ~4,000 | Одна feature-секция; не весь справочник в каждом вызове |
| `app/pipeline_steps.py` | 450 | ~4,600 | Только signatures или один шаг pipeline |
| `app/config.py` | 340 | ~4,100 | Только `Settings` / `RetrievalSettings` и затронутые поля |
| `doc/conventions_architecture.md` | 113 | ~3,900 | Baseline для arch audit; иначе одна секция |
| `app/graph_retrieval.py` | 419 | ~3,700 | Только execution path под задачу |
| `app/retrieval.py` | 380 | ~3,500 | Только strategy/entrypoint section |
| `doc/api_reference.md` | 256 | ~3,300 | 5–10 endpoint samples или одна группа маршрутов |
| `doc/observability_slo.md` | 253 | ~3,100 | Только проверяемые SLO/метрики |
| `doc/conventions_reference.md` | 75 | ~2,900 | Узкая секция вместо полного файла при не-arch задаче |
| `doc/technical_specification.md` | 270 | ~1,900 | Секция entry points / форматы, не весь документ без нужды |

### Что Исправить В Контрактных Промтах Для Cursor

- Заменять `Read doc/adr.md and doc/architecture.md` на `Read ONLY ADR status table and architecture module list`.
- Заменять `doc/epochs/ (последние 2-3 эпохи)` на `one target epoch header only`; `doc/epochs/e4.md` нельзя читать целиком.
- В каждом execution prompt явно писать: `Owner files are write-scope, not read-scope. Do not read owner files fully unless listed in Read ONLY`.
- Для тестов писать не `tests/test_*.py`, а `rg "def test_<feature>" tests/<file>.py`, затем открыть один test case.
- Для Architecture Review запускать только одну phase за вызов; полный Phase 1-5 review не должен быть одним Cursor call.
- Перед отправкой промта делать dry-run read-set: если сумма EstTokens >12k, заменить самые крупные файлы на grep/signatures/section summaries.

### Полный набор рекомендаций (консолидировано)

**Перед вызовом (обязательно):**

1. Выписать **Read ONLY (≤5)**: путь + **режим** (`signatures` / `section:…` / `one test` / `rg …` / `tail changelog`).
2. Вставить в начало промпта: `Ignore prior responses/tools. Fresh context only.`
3. Явно развести: **`Owner files` = write-scope**, не read-set; full-read только если файл перечислен в Read ONLY с режимом `full` и файл не в BLOCK-списке `doc/token_safety.md`.
4. Оценить суммарный вход (**system + rules + @files + история + вставки**). **>20k — не вызывать**; **>12k** — сжать до целевого коридора.
5. Прогнать `python scripts/check_readset.py …` (или `--signatures`) для спорных путей; при `BLOCK` — пересобрать read-set.

**Формулировки в контракте (заменить опасные шаблоны):**

- Вместо «изучи `app/*` / `tests/*`» → перечислить **конкретные файлы** и режимы; напомнить: glob в workflow — **source map**, не read-set.
- Вместо «тесты вокруг фичи» → `rg "def test_<feature>" tests/<file>.py` + **один** кейс.
- Вместо «прочитай ADR / architecture» → «**только** status table / module list / одна секция».
- Вместо «Doc sync: changelog» без уточнения → «**одна** новая запись / diff хвоста», не весь `doc/changelog.md`.
- Architecture review: **одна фаза = один LLM-вызов**; не Phase 1–5 одним сообщением.

**Cursor-специфика:**

- `doc/agent_workflow.md` — slim index (64 стр, full_read allowed). Детали по темам — в `agent_workflow_rules.md`, `agent_workflow_templates.md`, `agent_workflow_cycle.md`, `agent_workflow_arch_review.md`, `agent_workflow_test_bundles.md`.
- После тяжёлого шага (**codebase_search**, крупный `read_file`, длинный вывод терминала) — новый узкий чат или ручное удаление артефактов из контекста перед следующим облачным вызовом.
- Следить за **дублированием**: один и тот же большой файл не должен попадать и как owner-инструкция, и как полный attach.

**Синхронизация документации:**

- При изменении «тяжёлых» файлов обновлять **`doc/token_safety.md`** (канон) и пересчитывать строки/оценки в этом чеклисте **или** добавить скрипт измерения в CI (см. P2/P0 roadmap ниже).

**Verify (отдельный поток):**

- Вход: **контракт** + **diff** (`COMMIT_RANGE`) + **вывод целевой команды** + при необходимости **один** snippet; без «project scan», без полных `tests/test_*.py`, без полного `doc/changelog.md`.
- См. шаблон в `doc/agent_workflow_templates.md` (Verify Prompt) и `archive/agent_prompts/agent_prompts_verify.md`.

**Модели и стоимость:**

- Соблюдать **model routing** из `doc/agent_workflow_rules.md`: для рутины не использовать запрещённые модели; дорогую reasoning — только с явным одобрением owner.

---

## 🛒 Context Cart: Task-aware Context Routing

**Идея:** агент не выбирает doc-файлы вручную по принципу "этот файл небольшой, значит можно целиком". Перед чтением он собирает **context cart**: минимальную корзину фрагментов под конкретную задачу, с причинами включения, режимом чтения и оценкой токенов.

Это закрывает риск для файлов из шаблонов, которые по одиночке обычно безопасны, но пачкой быстро раздувают вызов: `doc/conventions.md`, `doc/tasklist.md`, `doc/closed_iterations.md`, `doc/technical_specification.md`, `doc/observability_slo.md`, `doc/api_reference.md`, `doc/conventions_reference.md`, `doc/conventions_architecture.md`, типовые `doc/epochs/*.md` кроме `e4.md`.

### Правила Для Средних Doc-файлов

| Сценарий | Решение |
|---|---|
| Файл является главным источником решения и идёт один | full-read разрешён, если `check_readset.py` не даёт `BLOCK` |
| В read-set уже есть 2–3 code/test файла | doc-файлы читать только секцией, строкой, tail/head или grep |
| Нужны 3+ средних документа | сначала собрать context cart; full-read заменить на секции |
| Задача не архитектурная | `conventions_architecture.md`, `conventions_reference.md`, `technical_specification.md` только через релевантную секцию |
| Нужен backlog/status | `backlog_registry.yaml`: одна запись пакета или узкий grep; опционально производный `tasklist.md` (§ Now / Truth View) для снимка, не весь файл |
| Нужен API-контракт | `api_reference.md`: одна группа endpoints / 5–10 samples, не весь справочник |
| Нужен changelog/doc-sync | `changelog.md`: только новая запись или tail последних 2–3 записей |
| Нужен epoch context | максимум один `doc/epochs/<target>.md`; `e4.md` только фрагмент |

### Routing Profile Для Реестра

Расширить `doc/token_safety_registry.json` или будущий `doc/token_safety.yml` не только размерами, но и маршрутизацией:

```json
{
  "doc/api_reference.md": {
    "default_read_mode": "section_by_heading",
    "full_read_policy": "allowed_if_primary_only",
    "routes": ["api", "contracts", "routers"],
    "preferred_sections": ["Ask", "Flashcards", "Quiz"],
    "grep_hints": ["^## ", "POST /ask", "flashcards"]
  },
  "doc/tasklist.md": {
    "default_read_mode": "sections:Now,Planned",
    "full_read_policy": "allowed_if_primary_only",
    "routes": ["planning", "backlog", "roadmap"],
    "grep_hints": ["^## Now", "epoch-", "Truth View"]
  },
  "doc/conventions_architecture.md": {
    "default_read_mode": "grep_then_section",
    "full_read_policy": "discouraged",
    "routes": ["architecture", "provider", "pipeline", "persistence"],
    "grep_hints": ["provider", "pipeline", "router", "persistence"]
  }
}
```

### CLI-Контракт `context_cart.py`

Целевой CLI:

```bash
python scripts/context_cart.py --task "изменить API контракты flashcards"
python scripts/context_cart.py --task "verify AQE package" --emit-agent-prompt
python scripts/context_cart.py --task "обновить архитектурные правила" --budget 12000
```

Формат выхода:

```text
Context Cart
Task: изменить API контракты flashcards
Budget: SAFE, estimated_input_tokens=5200

Primary:
- doc/api_reference.md
  read: section "Flashcards"
  reason: public API contract may change

- app/routers/flashcards.py
  read: full
  reason: target implementation file

Support:
- doc/tasklist.md
  read: section "Now"
  reason: current backlog/source of truth

Skip:
- doc/conventions_architecture.md
  reason: no architecture change detected
```

`--emit-agent-prompt` должен выдавать готовый planning-prompt на базе `doc/agent_workflow.md`:

```text
Read ONLY:
1. doc/tasklist.md:section:Now
2. doc/api_reference.md:section:Flashcards
3. app/routers/flashcards.py:full

Do not read:
- doc/agent_workflow.md full
- tests/test_api.py full
- doc/epochs/ directory
```

### DoD Для Context Cart

- Context cart выбирает **фрагменты**, а не просто файлы.
- Каждый inclusion имеет `reason`, `read mode`, `estimated_tokens`.
- `SAFE/WARN/BLOCK` совпадает с лимитами 12k / 20k.
- Если средний doc-файл не primary, default mode не `full`, а `section` / `grep` / `tail`.
- Для 3+ doc-файлов full-read запрещён без явного override и причины.
- Выход содержит `Skip` для похожих, но лишних источников, чтобы агент не тащил "на всякий случай".
- `context_cart.py` может передать cart в `build_context_pack.py` или заменить ручной read-set в planning prompt.
- Тесты покрывают: task routing, суммарный бюджет, запрет batch full-read для средних docs, `--emit-agent-prompt`.

### Практический MVP Без Большого Builder

Чтобы получить ценность быстро, не ждать полного `build_context_pack.py`:

1. Завести отдельный backlog-пакет `epoch-context-cart-mvp`.
2. Расширить существующий `doc/token_safety_registry.json`, а не вводить YAML первым шагом.
3. Научить `scripts/check_readset.py` понимать `path:mode[:selector]`.
4. Добавить golden tests для типовых задач и ожидаемых carts.
5. Добавить в doc-sync ритм короткую строку `Context impact`.

**Почему так:** текущий JSON-реестр и `check_readset.py` уже работают. Самая дешёвая победа — сделать их mode-aware и task-aware, а не начинать с нового формата или крупного builder.

### `epoch-context-cart-mvp`

**Статус:** отдельный infra/eval-пакет, можно брать после `epoch-answer-quality-eval` или раньше, если снова появляются planning/verify вызовы в зоне `>12k`.

**User story:** «Как агент/разработчик, я получаю безопасный read-set под задачу до чтения файлов, а не вспоминаю вручную, какие средние документы можно открывать целиком.»

**Exit artifacts:**
- `doc/token_safety_registry.json` расширен routing metadata для средних doc-файлов.
- `scripts/check_readset.py` принимает `path:mode[:selector]`.
- `scripts/context_cart.py` строит минимальный cart из routing profiles.
- `tests/test_token_registry.py` покрывает новые поля registry.
- `tests/test_check_readset_modes.py` или расширение текущих тестов покрывает mode parsing.
- `tests/fixtures/context_cart/*.json` и `tests/test_context_cart.py` фиксируют golden carts.
- `doc/agent_workflow.md` указывает на `context_cart.py` / mode-aware `check_readset.py`.

**DoD:**
- `doc/changelog.md` без mode даёт `BLOCK`; `doc/changelog.md:tail:3` проходит как safe snippet.
- `doc/api_reference.md` без mode в пачке 3+ docs даёт `WARN/BLOCK`; `doc/api_reference.md:section:Flashcards` проходит.
- `doc/tasklist.md:section:Now` проходит и оценивается как фрагмент, не полный файл.
- Golden cart для API task не включает architecture docs full-read.
- Golden cart для roadmap task не включает full changelog.
- `--emit-agent-prompt` генерирует `Read ONLY` и `Do not read`.

### Mode-aware `check_readset.py`

Целевой синтаксис:

```bash
python scripts/check_readset.py doc/api_reference.md:section:Flashcards
python scripts/check_readset.py doc/tasklist.md:section:Now
python scripts/check_readset.py doc/changelog.md:tail:3
python scripts/check_readset.py tests/test_api.py:test_case:test_flashcards
python scripts/check_readset.py app/query_service.py:signatures
```

**Правила:**
- `path` без mode трактуется как `full`.
- `full` для `full_read: forbidden` даёт `BLOCK`.
- `section`, `tail`, `head`, `grep`, `signatures`, `test_case`, `diff_only` оцениваются как snippets.
- неизвестный mode даёт `BLOCK`, а не fallback на full-read.
- отсутствующий selector для `section` / `test_case` даёт `BLOCK`.
- для 3+ medium docs без mode включается batch guard: `WARN` или `BLOCK` по суммарному бюджету.

### JSON Registry First

Не блокировать MVP ожиданием YAML. Расширять текущий `doc/token_safety_registry.json`:

```json
{
  "doc/api_reference.md": {
    "lines": 256,
    "est_tokens": 3300,
    "full_read": "allowed_if_primary_only",
    "default_mode": "section",
    "safe_modes": ["section", "grep", "samples"],
    "routes": ["api", "contracts", "routers"],
    "grep_hints": ["^## ", "POST /ask", "flashcards"],
    "batch_full_read": "warn"
  }
}
```

YAML остаётся возможным P0+ улучшением, если понадобится ручная поддерживаемость. До этого источник истины — JSON + генератор `measure_token_registry.py`.

### Golden Carts

Golden fixtures должны фиксировать не алгоритмическую красоту, а ожидаемое поведение на реальных задачах:

```json
{
  "task": "изменить API контракт flashcards",
  "expected_include": [
    "doc/api_reference.md:section:Flashcards",
    "app/routers/flashcards.py:full",
    "tests/test_api.py:test_case:flashcards"
  ],
  "expected_exclude": [
    "doc/conventions_architecture.md:full",
    "doc/changelog.md:full",
    "doc/epochs/:full"
  ]
}
```

Минимальный набор:
- API contract task.
- Roadmap/tasklist update task.
- Architecture/provider task.
- Observability/SLO task.
- Epoch context task.
- Verify-only task.

### Context Impact В Doc-sync

После крупных doc-sync или изменения тяжёлых документов добавлять короткую строку в changelog/tasklist:

```text
Context impact: no registry route changes needed.
```

или:

```text
Context impact: update routes for doc/api_reference.md and doc/observability_slo.md.
```

Это превращает token safety в обычный maintenance rhythm: каждый doc-sync явно отвечает, нужно ли менять routing profiles.

---

## 🚀 План Реализации Token Firewall (roadmap)

> **Статус:** ниже — **целевая архитектура** и контракт DoD для будущих пакетов. Отдельные артефакты (`doc/token_safety.yml`, `scripts/build_context_pack.py`, `scripts/context_cart.py`, linters) **могут ещё не существовать** в репозитории; до их появления использовать `doc/token_safety.md` + `scripts/check_readset.py` + ручной dry-run.

Цель: перевести контроль входных токенов из "агент должен помнить правила" в исполняемый контур: task → context cart → manifest → token estimate → safe snippets → hard fail до отправки LLM-вызова.

### P0 — Машиночитаемый Источник Истин

**Outcome:** один machine-readable реестр для правил full-read / safe-read. MVP расширяет существующий JSON; YAML остаётся возможным follow-up.

**Write-set:**
- `doc/token_safety_registry.json`
- `doc/token_safety.yml`
- `doc/token_safety.md`
- `scripts/check_readset.py`
- `tests/test_token_safety_registry.py`

**Контракт `doc/token_safety.yml`:**
```yaml
budgets:
  target_input_tokens: 12000
  hard_input_tokens: 20000
defaults:
  missing_mode: block
  large_file_lines: 600
files:
  app/prompts.py:
    full_read: block
    estimate_tokens: 18356
    safe_modes: [symbols, section]
    commands:
      symbols: 'rg -n "^def|^[A-Z_].*=" app/prompts.py'
  tests/test_api.py:
    full_read: block
    estimate_tokens: 14230
    safe_modes: [test_case, grep]
  doc/api_reference.md:
    full_read: allowed_if_primary_only
    estimate_tokens: 3300
    safe_modes: [section, grep, samples]
    routes: [api, contracts, routers]
    default_mode: section
    commands:
      headings: 'rg -n "^## " doc/api_reference.md'
```

**DoD:**
- `check_readset.py` читает registry, а не держит forbidden list в коде.
- Любой read-set без mode для unsafe-файла возвращает `BLOCK`.
- Для средних doc-файлов есть `routes`, `default_mode`, `full_read_policy`, `grep_hints`.
- Markdown-таблица в `doc/token_safety.md` синхронизирована с YAML или явно помечена как generated/reference.
- MVP не требует миграции на YAML: если YAML отсутствует, JSON registry остаётся источником истины.

**Проверки:**
```bash
python -m pytest tests/test_token_registry.py -v
python scripts/check_readset.py app/prompts.py
python scripts/check_readset.py app/prompts.py:symbols
python scripts/check_readset.py doc/changelog.md:tail:3
```

### P1 — Context Pack Builder

**Outcome:** агент строит безопасный context pack вместо передачи сырых файлов.

**Write-set:**
- `scripts/build_context_pack.py`
- `scripts/context_cart.py` или импортируемый модуль routing внутри builder
- `tests/test_build_context_pack.py`
- `tests/test_context_cart.py`
- `doc/context_pack_format.md`
- `doc/agent_workflow.md`

**CLI-контракт:**
```bash
python scripts/build_context_pack.py \
  --goal "plan epoch-answer-quality-eval" \
  --read app/query_service.py:signatures \
  --read tests/test_query_service.py:test_case:test_ask_sources \
  --read doc/tasklist.md:section:epoch-answer-quality-eval \
  --budget 12000 \
  --hard-limit 20000
```

**Формат выхода:**
```text
Context Pack
Goal: ...
Budget: SAFE, estimated_input_tokens=7420
Included snippets:
- app/query_service.py: signatures, 840 est tokens
- tests/test_query_service.py:test_ask_sources, 1100 est tokens
Omitted:
- app/query_service.py full body, unsafe, ~8449 est tokens
```

**DoD:**
- `SAFE` при ≤12k, `WARN` при 12k-20k, `BLOCK` при >20k.
- Full-read unsafe-файла невозможен без явного override; override по умолчанию отсутствует.
- Builder поддерживает modes: `full`, `signatures`, `section`, `test_case`, `tail`, `head`, `grep`, `diff_only`.
- Для `section` и `test_case` отсутствующий pattern даёт `BLOCK`, а не silently full-read.
- Builder принимает результат `context_cart.py` как вход и сохраняет reasons/omitted sources.
- Batch из 3+ средних doc-файлов переводится в section/grep modes или даёт `WARN/BLOCK`.

**Проверки:**
```bash
python -m pytest tests/test_build_context_pack.py -v
python -m pytest tests/test_context_cart.py -v
python scripts/build_context_pack.py --goal smoke --read app/prompts.py:symbols
python scripts/build_context_pack.py --goal smoke --read app/prompts.py
```

### P1A — Context Cart Routing Profiles

**Outcome:** план чтения строится от задачи, а не от привычного списка шаблонных документов.

**Write-set:**
- `scripts/context_cart.py`
- `tests/test_context_cart.py`
- `doc/token_safety_registry.json` или `doc/token_safety.yml`
- `doc/context_pack_format.md`
- `doc/agent_workflow.md`

**Routing rules:**
- `api`, `contracts`, `routers` → `doc/api_reference.md:section`, router file, one contract test.
- `planning`, `backlog`, `roadmap` → `doc/backlog_registry.yaml` (целевой пакет / узкий фрагмент), опционально `doc/tasklist.md:section:Now`, optional `doc/closed_iterations.md:grep:<package>`.
- `architecture`, `provider`, `pipeline`, `persistence` → one architecture/conventions section, not all conventions docs.
- `observability`, `slo`, `metrics` → `doc/observability_slo.md:section:<metric>` + changed metric code.
- `epoch` → one target `doc/epochs/<id>.md:head/section`; never directory read.

**DoD:**
- CLI prints `Primary`, `Support`, `Optional`, `Skip`.
- Each entry has mode, reason and estimated tokens.
- `--emit-agent-prompt` produces `Read ONLY` and `Do not read` blocks.
- Medium docs full-read is allowed only when `primary_only` and cart has no competing medium-doc batch.
- Tests cover representative tasks for API, planning, architecture, observability and epoch routing.
- Golden fixtures live in `tests/fixtures/context_cart/*.json` and assert both expected includes and expected excludes.
- `Context impact` guidance is added to doc-sync/changelog workflow.

**Проверки:**
```bash
python -m pytest tests/test_context_cart.py -v
python scripts/context_cart.py --task "изменить API контракты flashcards"
python scripts/context_cart.py --task "обновить roadmap после token firewall" --emit-agent-prompt
```

### P1B — Mode-aware Read-set Validator

**Outcome:** `check_readset.py` becomes useful before full Context Cart exists.

**Write-set:**
- `scripts/check_readset.py`
- `tests/test_token_registry.py`
- `tests/test_check_readset_modes.py` или существующий тестовый файл registry
- `doc/token_safety.md`
- `doc/token_optimization_checklist.md`

**DoD:**
- CLI accepts `path:mode[:selector]`.
- Unsafe path without mode is treated as full-read and blocked.
- Safe modes estimate snippet-sized context and print the command/hint used.
- Unknown modes and missing selectors fail closed.
- Batch guard catches 3+ medium docs without modes.

**Проверки:**
```bash
python -m pytest tests/test_token_registry.py tests/test_check_readset_modes.py -v
python scripts/check_readset.py doc/changelog.md
python scripts/check_readset.py doc/changelog.md:tail:3
python scripts/check_readset.py doc/api_reference.md:section:Flashcards doc/tasklist.md:section:Now
```

### P2 — Prompt Linter Для Контрактов

**Outcome:** опасные формулировки в `doc/agent_workflow.md` и `archive/agent_prompts/` ловятся до merge.

**Write-set:**
- `scripts/lint_agent_prompts.py`
- `tests/test_lint_agent_prompts.py`
- `doc/agent_workflow.md`
- `.github/workflows/` или существующий docs/test gate

**Danger patterns:**
- `app/*`, `tests/*`, `scripts/*` без пояснения `source map, not read-set`
- `scan the codebase` без grep/phase/read-set limit
- `Read doc/adr.md`, `Read doc/architecture.md` без `ONLY`
- `Owner files:` без соседнего `Read ONLY:`
- `doc/epochs/` без `one header / one target epoch`
- `tests/test_*.py` без `test_case` / `grep`
- `Full architecture review` без "forbidden as one call"
- любой бюджет выше `20k`

**DoD:**
- Linter падает на новых unsafe prompt patterns.
- Для намеренных historical examples доступен allowlist с причиной.
- `doc/agent_workflow.md` проходит linter без allowlist.

**Проверки:**
```bash
python -m pytest tests/test_lint_agent_prompts.py -v
python scripts/lint_agent_prompts.py doc/agent_workflow.md archive/agent_prompts
```

### P3 — Diff-only Verify Mode

**Outcome:** verify-вызовы получают только contract, diff, test output и точечный snippet.

**Write-set:**
- `scripts/build_context_pack.py`
- `doc/agent_workflow.md`
- `tests/test_build_context_pack.py`

**Правило verify context:**
```text
Verify input may include only:
- contract summary
- git diff / changed files
- exact test output
- one relevant snippet if the diff is ambiguous
No project scan. No full tests. No full docs.
```

**DoD:**
- `--mode verify` запрещает `full`, `app/*`, `tests/*`, `doc/*` без `diff_only` / `section`.
- Builder умеет включать `git diff -- <paths>` как snippet.
- Verify prompt в `agent_workflow.md` ссылается на `build_context_pack.py --mode verify`.

**Проверки:**
```bash
python -m pytest tests/test_build_context_pack.py -v
python scripts/build_context_pack.py --mode verify --goal "verify package" --read diff:staged
```

### P4 — Signature / Snippet Cache

**Outcome:** большие стабильные файлы читаются через дешёвые generated summaries.

**Write-set:**
- `scripts/update_context_signatures.py`
- `var/context_signatures/.gitkeep` или `.cache/context_signatures/.gitkeep`
- `tests/test_update_context_signatures.py`
- `doc/context_pack_format.md`

**Generated artifacts:**
```text
var/context_signatures/app_prompts.symbols.md
var/context_signatures/app_query_service.signatures.md
var/context_signatures/tests_test_api.tests.md
```

**DoD:**
- Cache содержит только signatures/test names/symbols, не полные тела функций.
- Cache invalidates by file mtime/hash.
- `build_context_pack.py` предпочитает cache для `signatures` / `symbols`, если hash актуален.
- Generated cache либо gitignored, либо committed как lightweight index; решение фиксируется в doc.

**Проверки:**
```bash
python -m pytest tests/test_update_context_signatures.py tests/test_build_context_pack.py -v
python scripts/update_context_signatures.py --check
```

### P5 — Token Ledger И Cost Feedback Loop

**Outcome:** каждый context-pack и blocked attempt оставляет измеримый след.

**Write-set:**
- `scripts/build_context_pack.py`
- `scripts/token_ledger.py` или `app/llm_guards.py`
- `tests/test_token_ledger.py`
- `doc/cost_tracking.md`

**Ledger record:**
```json
{
  "ts": "2026-04-20T12:00:00Z",
  "task": "cursor-token-guard",
  "phase": "planning",
  "estimated_input_tokens": 7420,
  "budget_status": "SAFE",
  "read_set": ["app/query_service.py:signatures"],
  "blocked_files": ["app/prompts.py:full"]
}
```

**DoD:**
- `SAFE/WARN/BLOCK` записываются в JSONL.
- `BLOCK` включает список файлов и safe alternatives.
- Есть weekly summary command: top unsafe files, top phases, median/95p estimated tokens.

**Проверки:**
```bash
python -m pytest tests/test_token_ledger.py -v
python scripts/build_context_pack.py --goal smoke --read app/prompts.py:symbols --ledger logs/token_budget_ledger.jsonl
```

### P6 — Интеграция В AGENTS / Cursor / CI

**Outcome:** human-facing и agent-facing правила используют один исполняемый workflow.

**Write-set:**
- `AGENTS.md`
- `.cursor/rules/workflow.mdc`
- `doc/agent_workflow.md`
- `doc/token_optimization_checklist.md`
- `.github/workflows/` или существующий CI gate

**Изменения:**
- В первые 30-50 строк `AGENTS.md` добавить короткий `TOKEN FIREWALL`.
- В Cursor rule добавить обязательное использование context pack для любых задач с large/unsafe files.
- CI запускает prompt linter и registry tests.
- `doc/agent_workflow.md` заменяет ручной dry-run на команду `build_context_pack.py`.

**DoD:**
- Новый агент видит короткий fail-closed блок до длинных соглашений.
- Cursor получает одинаковую инструкцию: owner/write-set is not read-set.
- CI падает при возврате unsafe prompt patterns.

**Проверки:**
```bash
python -m pytest tests/test_token_safety_registry.py tests/test_lint_agent_prompts.py tests/test_build_context_pack.py -v
python scripts/lint_agent_prompts.py AGENTS.md .cursor/rules/workflow.mdc doc/agent_workflow.md archive/agent_prompts
```

### Рекомендуемый Порядок Внедрения

| Пакет | Почему первым | Риск | Можно отдавать агенту? |
|---|---|---|---|
| P0 YAML registry | создаёт единый источник истины | низкий | да |
| P2 prompt linter | быстро ловит регрессии в промтах | низкий | да |
| P1B mode-aware check_readset | даёт пользу до большого builder | низкий | да, первым после JSON registry |
| P1A context cart routing | убирает ручной выбор средних doc-файлов | средний | да, отдельным пакетом после P0 |
| P1 context pack builder | главный функциональный прорыв | средний | да, отдельным пакетом |
| P3 diff-only verify | резко режет verify-вызовы | низкий | да |
| P4 signature cache | оптимизация поверх builder | средний | после P1 |
| P5 token ledger | наблюдаемость и cost feedback | средний | после P1 |
| P6 integration | закрепляет workflow в правилах и CI | средний | последним |

### Definition Of Done Для Всего Token Firewall

- Ни один unsafe full-read не проходит без `BLOCK`.
- Любой read-set без mode для большого файла блокируется.
- `check_readset.py` понимает `path:mode[:selector]` и fail-closed для неизвестных режимов.
- Planning и verify имеют разные default modes; verify не может запускать project scan.
- Контрактные промты проходят linter.
- Context cart выбирает task-aware read modes для средних doc-файлов и объясняет skipped sources.
- Golden carts защищают routing logic от регрессий.
- Changelog/doc-sync фиксирует `Context impact` для крупных doc-изменений.
- Context pack показывает included/omitted/token estimate до LLM-вызова.
- Ledger позволяет увидеть median / p95 estimated input tokens по фазам.
- Документация (`AGENTS.md`, `.cursor/rules/workflow.mdc`, `doc/agent_workflow.md`) указывает на один и тот же исполняемый путь.

---

### 6. Token Safety Reference + Validator (Эффект: предотвращение случайных 20k+ вызовов)

**Что добавлено (2026-04-19, обновлено 2026-04-20):**

| Артефакт | Файл | Что делает |
|---|---|---|
| Справочник | `doc/token_safety.md` | Таблица: ❌/⚠️/✅ для каждого файла + safe method |
| Реестр размеров | `doc/token_safety_registry.json` | `lines` / `bytes` / `est_tokens`, `full_read: forbidden`, `safe_hint`; генерация: `python scripts/measure_token_registry.py --write` |
| Скрипт | `scripts/check_readset.py` | CLI-валидатор: SAFE/WARN/BLOCK; подмешивает подсказки из реестра |
| Gate | `scripts/lint_agent_prompts.py` | JSON-валидность реестра + smoke BLOCK на токсичном read-set |
| Тесты | `tests/test_token_registry.py` | pytest: схема реестра + интеграция `check_readset` |
| Project rule | `CLAUDE.md` | Правила для Claude Code, загружаются автоматически |
| Permissions | `.claude/settings.json` | Auto-allow для read-only/check команд без prompt |
| Cursor rule | `.cursor/rules/workflow.mdc` | Token budget + запрет @ `agent_workflow` целиком + режимы Read ONLY |
| Agent rule | `AGENTS.md` | Forbidden list + лимиты 12k/20k + ссылки на реестр/lint |

**Как использовать скрипт:**
```bash
# Проверить read-set до отправки
python scripts/check_readset.py app/query_service.py tests/test_api.py doc/tasklist.md
# → BLOCK: 2 forbidden + 32k tokens

# Посмотреть safe команды для больших файлов
python scripts/check_readset.py --signatures app/query_service.py app/tutor_orchestrator.py
# → 💡 grep "^class\|^def " app/query_service.py

# С кастомным бюджетом
python scripts/check_readset.py --budget 8000 app/api.py app/models.py

# Реестр размеров + gate (для CI / перед merge doc-изменений)
python scripts/measure_token_registry.py --write
python scripts/lint_agent_prompts.py
```

**Проверка:** запустить скрипт с forbidden file → exit code 2 (BLOCK).

---

## 📚 Дополнительные Ресурсы

**После крупных изменений в «тяжёлых» файлах** (см. список в `doc/token_safety.md` и ключи в `doc/token_safety_registry.json`):

1. `python scripts/measure_token_registry.py --write`
2. при необходимости подправить **числа в текстовых таблицах** в `doc/token_safety.md` (и при расхождении — отражения в этом чеклисте / `doc/agent_workflow.md`);
3. `python scripts/lint_agent_prompts.py` и `python -m pytest tests/test_token_registry.py`.

**Разовый пересчёт одного пути вручную:**

```bash
python -c "import os; p=r'app/prompts.py'; b=os.path.getsize(p); print(p, 'bytes', b, 'est~', b//4)"
```

Повторить для путей из read-set или прогнать свой список в цикле — и сверить сумму `est` с лимитом **12k / 20k**.

- **Основной документ:** `doc/agent_workflow.md` (разделы 2.2–2.5, шаблоны)
- **Таблица безопасных методов:** `doc/token_safety.md` (при расхождении цифр с этим чеклистом — **сначала** обновить канон в `token_safety.md`, затем здесь)
- **Подробный анализ:** `archive/agent_prompts/token_analysis_cursor_ai_2026-04-19.md`
- **Контрактные промты:** `archive/agent_prompts/` (примеры для разных типов задач)
- **Скрипт-валидатор:** `scripts/check_readset.py --help`

---

## 📝 История Оптимизаций

| Дата | Версия | Изменение | Эффект |
|---|---|---|---|
| 2026-04-19 | v1.0 | Read-set ≤ 5 файлов, forbid glm-5.1, no history accumulation, fallback >40k, exclude excess files | -40–60% входные токены |
| 2026-04-19 | v1.1 | token_safety.md, check_readset.py, CLAUDE.md, .claude/settings.json, обновлены workflow.mdc и AGENTS.md | Запрет forbidden files, автовалидация, CI-friendly exit codes |
| 2026-04-20 | v1.2 | Самоаудит чеклиста; лимиты 12k/20k вместо 40k; пересчёт таблиц размеров; уточнение по `closed_iterations` и `doc/epochs`; `doc/agent_workflow.md` в BLOCK-мета; полный список рекомендаций; roadmap disclaimer для P0–P6 | Меньше ложных оценок и расхождений с `agent_workflow` |
| 2026-04-20 | v1.3 | `doc/token_safety_registry.json`, `measure_token_registry.py`, `lint_agent_prompts.py`, `tests/test_token_registry.py`; `check_readset` читает реестр; синхронизация `doc/token_safety.md`, `AGENTS.md`, `doc/agent_workflow.md`, `archive/agent_prompts/README.md`, `.cursor/rules/workflow.mdc` | Исполняемый контур P0-lite без PyYAML |
| 2026-04-20 | v1.4 | Зафиксирован процесс обслуживания: `measure_token_registry.py --write` + ручная сверка таблиц в `doc/token_safety.md` после крупных правок в тяжёлых файлах | Единый owner-процесс для цифр в доках |
| 2026-04-20 | v1.5 | Добавлен план `Context Cart / task-aware context routing`: routing profiles для средних doc-файлов, `context_cart.py`, `--emit-agent-prompt`, DoD и место P1A в Token Firewall roadmap | Снижение риска batch full-read для "умеренных" docs из шаблонов |
