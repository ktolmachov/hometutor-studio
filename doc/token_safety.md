# Token Safety Справочник

Актуализировано: 2026-04-20.

Этот документ — **практический справочник для agentов и Cursor AI**: какие файлы можно включать в контекст целиком, а какие требуют предварительной обработки. Цель: **предотвратить "взрывы" входных токенов** при работе с облачными LLM.

Planning template по умолчанию находится в `doc/agent_workflow_templates.md`
(раздел **Шаблон planning prompt**). Этот документ описывает только safe methods
для включения файлов в контекст.

**Машиночитаемый реестр:** `doc/token_safety_registry.json` — актуальные строки, байты и грубая оценка `est_tokens` (байты / 4), плюс `full_read: forbidden` и `safe_hint`. Обновление: `python scripts/measure_token_registry.py --write`. Валидатор read-set: `python scripts/check_readset.py …` (подмешивает подсказки из реестра).

### Поддержка документации после крупных правок

Когда существенно выросли или переписаны **тяжёлые** файлы из реестра (крупные `app/*.py`, `tests/test_*.py`, `doc/changelog.md`, `doc/adr.md`, `doc/epochs/*.md`, монолитные контракт-доки и т.п.):

1. **`python scripts/measure_token_registry.py --write`** — пересобрать `doc/token_safety_registry.json` (цифры для `check_readset` и агентов).
2. **При необходимости** вручную подправить **числа в текстовых таблицах** ниже в этом файле (`doc/token_safety.md`), чтобы они не расходились с реестром и с копиями в `doc/agent_workflow.md` / `doc/archive/token_optimization_checklist.md` (хотя бы порядок величин и пороги риска).
3. Проверка: **`python scripts/lint_agent_prompts.py`** и **`python -m pytest tests/test_token_registry.py`**.

---

## Быстрый Чек Перед Prompt'ом

| Вопрос | Ответ | Действие |
|---|---|---|
| Вы читаете файл >600 строк целиком? | ДА | Остановитесь. Используйте signatures/head/grep (см. таблицу ниже) |
| Вы читаете 3+ больших файла одновременно? | ДА | Перезапустите с меньшим read-set |
| Ваш входной контекст > 20k токенов? | ДА | **Не отправлять** вызов; сжать history и read-set (целевой коридор ≤12k, см. `doc/agent_workflow_rules.md`) |
| Вы читаете целый каталог (doc/epochs/, doc/user_stories/)? | ДА | Ошибка. Читайте только перечисленные файлы |
| Вы retry'ете с тем же payload? | ДА | Ошибка. Сначала сжмите контекст, потом retry |

---

## Таблица Безопасного Включения: Критические Файлы

### ❌ Однозначно ЗАПРЕЩЕНО читать целиком

Эти файлы **никогда не должны включаться в контекст полностью**, потому что одного файла может быть достаточно, чтобы превысить soft-limit входных токенов.

| Файл | Строк | Est токенов* | ❌ Почему не целиком | ✅ Что вместо этого |
|---|---:|---:|---|---|
| `doc/epochs/e4.md` | 742 | ~23k | Самый тяжёлый epoch-файл | Только header / целевой фрагмент |
| `app/tutor_prompts.py` | small | safe | Designated prompt module; prompts distributed across services | read in full |
| `doc/agent_workflow.md` | 64 | ~1.1k | slim index после split 2026-04-20; full_read allowed | Навигационная ссылка; детали — в topic-файлах |
| `doc/agent_workflow_rules.md` | 111 | ~2.3k | full_read allowed | Читать целиком (~2.3k) |
| `doc/agent_workflow_cycle.md` | 159 | ~1.9k | full_read allowed | Читать целиком (~1.9k) |
| `doc/agent_workflow_templates.md` | 349 | ~5.0k | full_read allowed | Читать целиком (~5k) |
| `doc/agent_workflow_arch_review.md` | 329 | ~5.1k | full_read allowed | Читать целиком (~5.1k) |
| `doc/agent_workflow_test_bundles.md` | 302 | ~2.9k | full_read allowed | Читать целиком (~2.9k) |
| `doc/changelog.md` | 1790 | ~40.0k | История растёт | Только последние 2–3 записи или stub под append |
| `tests/test_api.py` | 1614 | ~14.2k | Интеграционные тесты | `rg "def test_<pattern>"` + 1–2 кейса |
| `doc/adr.md` | 666 | ~13.8k | Длинная история решений | Только `## Status` или один ADR |
| `app/knowledge_graph.py` | 1258 | ~13.7k | Большой граф-модуль | `rg -n "^class|^def "` + при необходимости один класс |
| `tests/test_query_service.py` | 1012 | ~10.2k | Большой юнит-тест | 1 fixture или 1 test case |
| `app/query_service.py` | 916 | ~8.4k | Оркестрация ответа | `rg -n "^class|^def "` или один метод |
| `doc/cjm.md` | 241 | ~6.3k | Мало строк, плотный текст | Только нужный journey / pain |
| `doc/architecture.md` | 728 | ~8.8k | Много связей | Список модулей или один `## Module: …` |
| `doc/epochs/` (папка целиком) | — | **сумма растёт быстро** | Только один целевой epoch-файл + фрагмент |

\*Грубая оценка: размер файла в UTF-8 байтах / 4 (см. `doc/token_safety_registry.json`).

**Правило:** если файл в этой таблице, читайте **только** из колонки "Что вместо этого".

---

## Таблица Безопасного Включения: Средние Файлы

### ⚠️ Читать ТОЛЬКО секциями

Эти файлы безопасны **только если** используется одна конкретная секция, а не весь файл.

| Файл | Строк | Est токенов* | ✅ Читать только | Типичный размер секции |
|---|---:|---:|---|---:|
| `app/tutor_orchestrator.py` | 641 | ~7.1k | 1–2 класса/метода | 200–400 токенов |
| `app/learner_model_service.py` | 662 | ~6.7k | Конкретный метод | 150–300 токенов |
| `app/learning_plan_service.py` | 592 | ~6.1k | Конкретный метод | 150–250 токенов |
| `app/pipeline_steps.py` | 450 | ~4.6k | Конкретный шаг pipeline | 100–200 токенов |
| `app/config.py` | 340 | ~4.1k | Класс `Settings` / затронутые поля | 100–150 токенов |
| `app/graph_retrieval.py` | 419 | ~3.7k | Один execution path | 100–200 токенов |
| `doc/conventions_architecture.md` | 113 | ~3.9k | Конкретная секция | 100–150 токенов |
| `app/retrieval.py` | 380 | ~3.5k | 1 стратегия или 1 функция | 100–200 токенов |
| `doc/api_reference.md` | 256 | ~3.3k | 1–2 группы endpoint | 100–150 токенов |
| `doc/observability_slo.md` | 253 | ~3.1k | Конкретный SLO | 100–150 токенов |
| `doc/user_guide_details.md` | 419 | ~4.0k | 1 feature guide | 100–150 токенов |
| `app/retrieval_strategies.py` | 286 | ~2.3k | 1 strategy class | 100–150 токенов |
| `doc/conventions_reference.md` | 75 | ~2.9k | Конкретный rule по area | 50–100 токенов |
| `doc/tasklist.md` | 83 | ~1.5k | **ТОЛЬКО 1 row целевого пакета** | 50–100 токенов |

**Правило:** для каждого файла из этой таблицы явно выписать, **какую конкретно секцию** вы читаете, перед тем как добавлять в prompt.

---

## Таблица Безопасного Включения: Обычно OK Файлы

### ✅ Как правило, можно целиком (если нужна полнота)

Эти файлы обычно безопасны целиком, но всё равно лучше включать их по необходимости, а не "по привычке".

| Файл | Строк | Est токенов* | Комментарий |
|---|---:|---:|---|
| `doc/conventions.md` | 50 | ~1.0k | Часто достаточно одной секции |
| `app/api.py` | 128 | ~1.1k | OK целиком для обзора маршрутов |
| `app/models.py` | 201 | ~1.8k | OK целиком для контрактов типов |
| `app/ui/main.py` | 199 | ~1.9k | OK целиком при UI-задаче |
| `app/tutor_prompts.py` | 87 | ~1.0k | Обычно OK целиком |
| `tests/conftest.py` | 85 | ~0.8k | OK целиком для fixtures |
| `requirements.txt` | 37 | ~0.2k | Безопасен целиком |
| `doc/closed_iterations.md` | 62 | ~0.9k | Можно целиком по размеру, но лучше абзац по пакету |
| `doc/user_stories/us-*.md` | перем. | перем. | Одна US, не вся папка |

**Правило:** "можно целиком" **не означает** "нужно читать целиком в каждом вызове". Всё равно читайте **только то, что нужно для задачи**.

---

## Практические Примеры: Безопасные Комбинации

Вот примеры read-set'ов, которые **безопасны** (под 20k soft-limit):

### Пример 1: Planning для простого пакета (~8k токенов)

```
Goal: plan E15.3-A (add new quiz type)

Read ONLY:
1. app/quiz_service.py — grep "^class\|^def " (signatures only, ~600 токенов)
2. tests/test_quiz_service.py — grep "def test_" (test patterns, ~400 токенов)
3. doc/tasklist.md — ONLY row "E15.3-A", not entire file (~50 токенов)
4. doc/conventions.md — ONLY section "Quiz & Personalization" (~100 токенов)

Total estimate: ~1.2k, safe margin to 5k+ system prompt + history
```

### Пример 2: Architecture review Phase 1 (~8k токенов)

```
Goal: Phase 1 — Conventions Compliance Audit

Read ONLY:
1. doc/conventions.md (~1k токенов целиком; лучше одна секция)
2. doc/conventions_architecture.md (~3.9k токенов целиком; лучше одна секция)
3. doc/conventions_reference.md (~2.9k токенов целиком; лучше одна секция)
4. grep output for convention violations (manual, ~200 токенов)

Total: ~5.8k, safe for single phase

Don't read yet: code files, doc/adr.md, doc/architecture.md, test files
```

### Пример 3: Verify для code пакета (~10k токенов)

```
Goal: verify E14.2-C (exception handler audit)

Read ONLY:
1. archive/agent_prompts/e14_c_exception_handler_audit_2026-04-12.md (contract, ~1.5k)
2. git diff HEAD~5..HEAD (scope check, manual, ~2k)
3. tests/test_exception_handlers.py — grep "def test_" (patterns, ~300)
4. 1–2 specific exception handlers touched by commit (manual, ~1k)

Total: ~5k, safe margin

Don't read: full test files, full contract review, full changelog
```

---

## Запрещённые Комбинации: Гарантированно Перейду Hard-Limit

### ❌ Плохой read-set #1 (Наивный Architecture Review)

```
Read ALL of:
- app/query_service.py целиком (~8.4k est)
- app/knowledge_graph.py целиком (~13.7k)
- app/prompts.py целиком (удалён; промпты теперь в app/tutor_prompts.py + inline в services)
- tests/test_api.py целиком (~14.2k)
- doc/adr.md целиком (~13.8k)
- doc/architecture.md целиком (~8.8k)

Total: ~73k+ только файлы (оценка est)

PLUS: system prompt, history, contract file — HARD LIMIT (20k) давно превышен
```

### ❌ Плохой read-set #2 (Полная папка epochs)

```
Read ALL of:
- doc/epochs/e1.md (~5k)
- doc/epochs/e2.md (~7k)
- doc/epochs/e3.md (~12k)
- doc/epochs/e4.md (~23k est)
- doc/epochs/e5.md (~14k)

Total: ~55k токенов для истории эпох

PLUS: system prompt, history = 65k+, HARD LIMIT EXCEEDED
```

### ❌ Плохой read-set #3 (Полный doc/ перечень)

```
Read ALL files from doc/ that агент считает "документацией":
- doc/conventions.md (~1k)
- doc/conventions_architecture.md (~3.9k)
- doc/conventions_reference.md (~2.9k)
- doc/api_reference.md (~3.3k)
- doc/user_guide.md (~2.1k)
- doc/user_guide_details.md (~4.0k)
- doc/technical_specification.md (~1.9k)
- doc/observability_slo.md (~3.1k)
- doc/tasklist.md целиком (~1.5k)
- doc/architecture.md (~8.8k)
- doc/adr.md (~13.8k)

Total: ~42k+ токенов только docs (оценка est)

PLUS: code + system prompt — превышает hard-limit 20k
```

---

## Правила Сжатия Контекста (Если Уже Близко к Лимиту)

Если оценка входа приблизилась к **soft-limit 12k–20k**, прежде чем отправить prompt — сжать read-set и history. При **>20k** вызов не отправлять.

### 1. Сжмите History (можно сэкономить 15–20%)

**Было:**
```
User: read app/query_service.py
Claude: [full file + 5k tokens of analysis]
User: now read tests/test_query_service.py
Claude: [full file + 3k tokens of analysis]
User: plan the package
Claude: [1k tokens of plan]
```

**Стало:**
```
User: based on prior context (ignore full files):
- app/query_service.py: orchestration service (~916 lines)
- tests/test_query_service.py: unit tests for orchestration (~1012 lines)
- plan the package for E15.3-A

[только сама постановка, без истории файлов]
```

### 2. Замените Full-File на Summary (можно сэкономить 30–50%)

**Было:**
```
[insert full app/query_service.py here, ~8.4k est tokens]
```

**Стало:**
```
app/query_service.py — summary:
- QueryService.process(query: QueryContext) -> QueryResponse
- Handles: preprocessing, retrieval routing, tutor orchestration, response gen
- Key methods: _preprocess, _route_to_retrieval, _route_to_tutor, _generate
- Depends: app/retrieval.py, app/tutor_orchestrator.py, app/tutor_prompts.py

For full method bodies, use: grep "^class\|^def " app/query_service.py
```

### 3. Читайте Только Нужное (Сэкономить 40–60%)

**Было:**
```
Read doc/conventions.md (full, ~1k est tokens)
Read doc/conventions_architecture.md (full, ~3.9k est tokens)
Read doc/conventions_reference.md (full, ~2.9k est tokens)
Total: ~7.8k est tokens
```

**Стало:**
```
Read ONLY section "Error Handling" from doc/conventions_architecture.md (200 tokens)
Read ONLY section "Import Hygiene" from doc/conventions_reference.md (100 tokens)
Total: 0.3k tokens
```

### 4. Используйте Grep вместо Full-Read (Сэкономить 60–80%)

**Было (до миграции промптов):**
```
Read app/prompts.py целиком (~18.4k est tokens)
```

**Стало (app/prompts.py удалён; промпты в app/tutor_prompts.py + inline):**
```
Read app/tutor_prompts.py целиком (small, safe)
```

---

## Инструкция для Cursor AI / Agents

### Перед каждым Prompt'ом Выполнить Чек

```
1. List all files you plan to read: [ file1, file2, ...]
2. For each file:
   - Check if it's in the ❌ "FORBIDDEN TO READ FULLY" list
   - If YES: use safe method from ✅ column instead
   - If NO: proceed, but check section next
3. Sum estimated tokens:
   - System prompt: ~2k
   - Contract + history: estimate
   - Read-set: sum from table
   - Целевой total ≤ **12k**; максимум после сжатия ≤ **20k** (hard)
4. If total > 20k:
   - Remove lowest-signal files
   - Replace full-reads with summaries/grep
   - Retry estimation
5. Only after estimation ≤ 20k: send prompt
```

### Если Всё Же Перешли Лимит

1. **Остановиться, не отправлять.**
2. **Перезапустить с меньшим read-set** (не retry с тем же payload).
3. **Явно указать:** "Ignored prior responses/tools. Fresh context only."
4. **Логировать:** какие файлы исключены и почему.

---

## FAQ: Частые Ошибки

### Q: "Но агент says читать весь файл для лучшего understanding?"
**A:** Агент ошибается. Для облачных LLM фиксированный бюджет токенов — это физический лимит, не пожелание. Лучшее "understanding" = 0 результат при hard-limit. Используйте методы из таблицы выше.

### Q: "Что если я прочитаю 2 средних файла целиком вместо 1?"
**A:** Проверьте сумму по таблице. Например:
- `app/api.py` целиком ≈ 1.1k
- `app/models.py` целиком ≈ 1.8k
- Сумма ≈ 2.9k, это OK

Но если добавить 3-й:
- `app/ui/main.py` целиком ≈ 1.9k
- Сумма ≈ 4.8k, ещё OK

Четвёртый:
- `doc/conventions.md` целиком ≈ 1.0k
- Сумма ≈ 5.8k, ещё OK, но уже подходит к краю

Пятый:
- `doc/adr.md` целиком ≈ 13.8k
- Сумма ≈ 19.6k — у края hard-limit 20k **до** system/history

Шестой:
- `app/query_service.py` целиком ≈ 8.4k
- Сумма ≈ 28k+ — HARD LIMIT EXCEEDED

Вывод: следите за кумулятивным эффектом.

### Q: "Я read-set маленький, но history большая?"
**A:** Очистите историю. При retry'е новый вызов должен содержать только:
- Новый prompt
- Последние 2–3 шага из истории (если нужны)
- Compact summary вместо полных файлов из прошлых шагов

### Q: "Grep вывод тоже считается в токены?"
**A:** Да. `grep "^class\|^def " app/query_service.py` выдаст порядка сотен–тысячи токенов (зависит от вывода). Это **намного дешевле**, чем полный файл (~8.4k est), но всё равно считается.

---

## Контрольный Список Перед Submit'ом

- [ ] Все файлы в my read-set находятся либо в ✅ SAFE, либо обработаны методом из таблицы ❌
- [ ] Ни один файл > 600 строк не читается целиком (кроме явного разрешения в ✅ SAFE list)
- [ ] Каталоги (doc/epochs/, doc/user_stories/) не читаются целиком
- [ ] Estimated input tokens ≤ **20k** (целевой режим ≤ **12k**)
- [ ] Не retry'ю с неизменённым payload
- [ ] History очищена от лишних старых tool-результатов

Если все пункты ✅ — готово к отправке.

---

## История Изменений

- **2026-04-19:** Инициальная версия. Анализ на основе token consumption audit по `hometutor`.
- **2026-04-20:** Таблицы синхронизированы с `doc/token_safety_registry.json` / `scripts/measure_token_registry.py`; добавлены `doc/agent_workflow.md`, `doc/epochs/e4.md` в критический список; уточнены лимиты 12k/20k и примеры накопления; добавлен раздел «Поддержка документации после крупных правок» (реестр + таблицы).
