# Универсальный верификационный шаблон для execution contracts

**Роль:** шаблон для проверки результатов работы агента-исполнителя по любому
контракту из `archive/agent_prompts/`.

**Как использовать:**
1. Скопировать раздел `## Промпт для агента` ниже в новый чат.
2. Заполнить параметрическую секцию `[ЗАПОЛНИТЬ ПЕРЕД ЗАПУСКОМ]`.
3. Запустить в отдельном потоке — не в том же чате, где работал исполнитель.

**Когда запускать:** после того как агент-исполнитель сообщил о завершении
пакета и предоставил Output (changed files, tests run, etc.).

**Ограничение:** верифицировать только один пакет за раз.
Не запускать C до закрытия B; не запускать D до закрытия C.

---

## Промпт для агента

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
Goal: verify <PACKAGE_ID> — confirm DoD met, scope clean, no regressions.
Do NOT write code. Do NOT edit any files. Output = structured verdict only.

════════════════════════════════════════════════════════
[ЗАПОЛНИТЬ ПЕРЕД ЗАПУСКОМ]

CONTRACT_FILE  = archive/agent_prompts/<имя_файла>.md
PACKAGE_ID     = <например, E14-B или E11-R>
PACKAGE_SECTION = <заголовок секции внутри CONTRACT_FILE, если файл содержит
                  несколько пакетов; оставить пустым если файл — один пакет>
COMMIT_RANGE   = HEAD~1..HEAD
                 (или: <sha_before>..<sha_after> если закрытие было несколько
                 коммитов назад; или: имя ветки если работа велась в ветке)
PACKAGE_TYPE   = code | doc | mixed
                 code  → агент менял app/, tests/, scripts/
                 doc   → агент менял только doc/
                 mixed → и то, и другое
════════════════════════════════════════════════════════

## Step 0 — Read and parse the contract

Read CONTRACT_FILE fully (and PACKAGE_SECTION если указана).

Из контракта извлечь и зафиксировать явно:

  WRITE_SET      : список файлов, которые агенту разрешено создавать/менять.
  DO_NOT_TOUCH   : список файлов/зон, которые явно запрещены.
  DOD_ITEMS      : каждый пункт Definition of Done (нумеровать 1, 2, 3...).
  VERIFY_CMDS    : команды, указанные в контракте в секции DoD / Verification.
  REGRESSION_TESTS: тесты/команды из секции Regression или смежные, упомянутые
                   в контракте.
  OUTPUT_REQUIRED: что контракт требует от исполнителя в Output.

Если контракт не содержит явного Write-set или DoD — зафиксировать это как
INFO-gap перед переходом к следующим шагам.

## Step 1 — Scope check

Run: git diff --name-only COMMIT_RANGE
Run: git log --oneline COMMIT_RANGE   (для понимания количества коммитов)

Для каждого изменённого файла определить статус:

  ✅ IN_WRITE_SET      : файл входит в WRITE_SET контракта.
  ⚠️  OUT_OF_WRITE_SET  : файл изменён, но в WRITE_SET не указан.
                         Severity: warning — если файл смежный (тест, doc);
                                   critical — если это незапланированный модуль.
  🚫 DO_NOT_TOUCH_VIOLATED: файл из DO_NOT_TOUCH списка был изменён.
                         Severity: critical — независимо от содержания изменения.

Особые правила по PACKAGE_TYPE:

  PACKAGE_TYPE = doc:
    Любой файл из app/, tests/, scripts/ → critical scope violation.
    При обнаружении: FAIL немедленно, не продолжать Step 2.

  PACKAGE_TYPE = code:
    Проверить дополнительно:
    - Нет ли импортов из app/ui/ в app/*.py (backend→UI direction violation).
    - Нет ли изменений в файлах, помеченных как "reference, not target"
      в контракте (например, pipeline_steps.py как эталон паттерна).

  PACKAGE_TYPE = mixed:
    Применить правила обоих типов.

Итог Step 1:
  - Полный список изменённых файлов с их статусом.
  - Есть ли critical violations → если да, перейти к Step 5 (Verdict: FAIL).
  - Есть ли warning violations → зафиксировать, продолжить верификацию.

## Step 2 — DoD verification

Для каждого пункта из DOD_ITEMS:

  2а. Определить тип проверки:
      - pytest     : запустить команду, ожидать PASSED
      - grep       : поиск паттерна в файле, ожидать наличие/отсутствие
      - import     : python -c "import <module>; print('OK')"
      - file_exists: проверить что файл создан / удалён
      - content    : прочитать фрагмент файла и оценить соответствие
      - git_log    : убедиться что артефакт создан (eval_results/, etc.)
      - cross_doc  : два doc-файла согласованы между собой

  2б. Если контракт даёт точную команду → запустить её verbatim.
      Если контракт описывает критерий без команды → вывести минимальную
      проверяемую команду самостоятельно.

  2в. Записать результат каждого DoD-пункта:
      PASS  : проверка выполнена, результат соответствует ожидаемому.
      FAIL  : проверка провалена (указать точный output или diff).
      SKIP  : проверка неприменима (указать причину: зависимость не закрыта,
              OPENAI_API_KEY отсутствует, и т.п.). SKIP не блокирует PASS.

  2г. Spot check качества (только для PACKAGE_TYPE = code или mixed):
      Выбрать 2-3 изменённых блока/функции из git diff.
      Для каждого оценить:
      - Технически проходит ли DoD-grep/import? (формальный критерий)
      - Соответствует ли намерению контракта? (качественный критерий)
      Примеры частых расхождений:
      - except заменён на более узкий тип, но logging и fallback не добавлены.
      - Поле добавлено в Settings, но default некорректен (None вместо значения).
      - Функция вынесена в новый модуль, но старая версия не удалена.
      - Импорт заменён, но в __init__.py или tests остался старый путь.
      Если обнаружено — severity: warning (не блокирует, если тест зелёный).

## Step 3 — Regression check

Определить смежные тест-бандлы:

  а. Взять Write-set из контракта.
  б. Для каждого изменённого app/-модуля найти тест: tests/test_<module>.py.
  в. Дополнительно проверить test bundle из `doc/agent_workflow_test_bundles.md`
     — выбрать подходящий по типу изменения.

  Если смежные тесты не очевидны — запустить минимальный baseline:
    python -m pytest tests/test_api.py tests/test_config.py -v

  Записать:
  - Какие тесты запущены (список).
  - Результат каждого (PASSED / FAILED / ERROR).
  - Если FAILED: имя теста, строка, сообщение об ошибке.

## Step 4 — Output completeness check

Контракт требовал от исполнителя определённый Output (из OUTPUT_REQUIRED).
Проверить, что исполнитель предоставил все запрошенные артефакты:

  - Список изменённых файлов: есть / отсутствует.
  - Результаты тестов: есть / отсутствует.
  - Специфические артефакты (eval JSON, disposition-отчёт, etc.): есть / отсутствует.
  - Unresolved risk: упомянуто / не упомянуто.

Если обязательные Output-артефакты отсутствуют:
  - Критические (тесты, изменённые файлы) → CONDITIONAL PASS minimum.
  - Вспомогательные (disposition-отчёт, risk) → info-gap, не блокирует.

## Step 5 — Verdict

На основании Step 1–4 вынести один из трёх вердиктов:

────────────────────────────────────────────
PASS
Условие: все DoD-пункты PASS или SKIP (с обоснованием), scope чист
  или только warning-уровня, регрессий нет.

Действия при PASS:
  1. Закрыть пакет в doc/tasklist.md:
     - Изменить статус `open` → `closed` с датой.
     - Добавить exit artifact (что именно проверено).
  2. Добавить запись в doc/closed_iterations.md (2-6 строк):
     - Что было сделано.
     - Какие файлы изменены.
     - DoD выполнен: ссылка на тесты / артефакты.
     - Unresolved risk (если есть SKIP).
  3. Добавить строку в doc/changelog.md.
  4. Если это последний пакет эпохи → добавить строку в Truth View таблицу
     doc/tasklist.md и обновить Активный Горизонт.
────────────────────────────────────────────
CONDITIONAL PASS
Условие: ≥1 DoD-пункт FAIL, но severity = warning/info (тест зелёный,
  проблема — качество или документация). Или SKIP без критической зависимости.

Действия при CONDITIONAL PASS:
  1. Зафиксировать конкретно: какой DoD-пункт не выполнен и почему это warning.
  2. Варианты:
     а. Исправить в рамках текущего пакета (если исправление ≤30 минут).
     б. Принять и добавить follow-up в Deferred таблицу doc/tasklist.md
        с re-entry condition.
  3. Остальные closure-действия как при PASS.
  4. Если долг блокирует доверие к поставке (как у FAIL по смыслу) — одна строка
     HANDOFF_SIGNAL в отчёте (формат: doc/team_workflow/tester.md).
────────────────────────────────────────────
FAIL
Условие: critical scope violation (DO_NOT_TOUCH нарушен или doc-only пакет
  изменил код), ≥1 DoD-пункт FAIL critical (тест упал, импорт сломан,
  артефакт не создан), или регрессия в смежных тестах.

Действия при FAIL:
  1. НЕ закрывать пакет в tasklist.md.
  2. Сформулировать blocker для возврата исполнителю:
     - Какой именно DoD-пункт не выполнен.
     - Файл и строка (если применимо).
     - Точная команда, которая должна вернуть PASS.
  3. Не перечислять всё подряд — только первый критический blocker.
  4. Добавить строку HANDOFF_SIGNAL в отчёт (обязательно при FAIL; см. tester.md).
────────────────────────────────────────────

## Output (обязательный формат)

### Параметры верификации
- Пакет: PACKAGE_ID
- Контракт: CONTRACT_FILE
- Commit range: COMMIT_RANGE

### Scope Report
| Файл | Статус | Severity |
|------|--------|---------|
| ... | IN_WRITE_SET / OUT_OF_WRITE_SET / DO_NOT_TOUCH_VIOLATED | — / warning / critical |

### DoD Checklist
| # | Критерий (из контракта) | Проверка | Результат | Severity |
|---|------------------------|---------|----------|---------|
| 1 | ... | grep -n "..." file.py → 0 | PASS | — |
| 2 | ... | pytest tests/test_x.py | FAIL: 2 failed | critical |
| 3 | ... | — | SKIP: E14-B not closed yet | — |

### Spot Check (только code/mixed)
| Блок | Формально | Качественно | Вывод |
|------|-----------|-------------|-------|
| app/foo.py:45 except clause | PASS (тип специфичен) | Нет logging | warning |

### Regression Check
| Тест | Результат |
|------|----------|
| tests/test_config.py | PASSED (12/12) |
| tests/test_api.py | PASSED (34/34) |

### Output Completeness
- Changed files list: ✅ / ❌
- Test results: ✅ / ❌
- Special artifacts: ✅ / ❌ / N/A
- Unresolved risk: ✅ / ❌

### Verdict
**[PASS | CONDITIONAL PASS | FAIL]**

Обоснование: (1-3 предложения)

При **FAIL** или **CONDITIONAL PASS**, если остаётся блокирующий риск для доверия к поставке — добавьте **ровно одну** строку после обоснования:
HANDOFF_SIGNAL: <что видит пользователь / что упало> → layer (contract | ui_spec | impl | tests | flaky_env)
(каноничный формат: doc/team_workflow/tester.md). При **PASS** строку не добавлять.

Если PASS → текст для doc/closed_iterations.md:
"""
### PACKAGE_ID — <название пакета> (дата)
Что сделано: ...
Файлы изменены: ...
DoD: pytest <команда> — зелёный; <другой критерий> — выполнен.
Risk / follow-up: ... (или "нет").
"""

Если FAIL → blocker для исполнителя:
"""
Blocker: <DoD-пункт N> не выполнен.
Файл: <path>:<line>
Что проверить: <exact command>
Ожидаемый результат: <что должно быть>
Фактический результат: <что есть сейчас>
"""
```

---

## Справка: типовые severity-правила

| Ситуация | Severity | Verdict impact |
|---------|----------|---------------|
| DO_NOT_TOUCH файл изменён | critical | FAIL немедленно |
| doc-only пакет изменил app/ файл | critical | FAIL немедленно |
| pytest упал (target тесты) | critical | FAIL |
| pytest упал (regression тесты) | critical | FAIL |
| Circular import | critical | FAIL |
| grep показывает нарушение конвенции | critical | FAIL |
| Файл вне write-set, но смежный (тест, doc) | warning | CONDITIONAL PASS |
| DoD-пункт выполнен формально, но не качественно | warning | CONDITIONAL PASS |
| Output исполнителя неполный (нет risk-секции) | info | не влияет на verdict |
| SKIP по объективной причине (нет API key, зависимость не закрыта) | — | не влияет |

## Справка: как найти COMMIT_RANGE

```bash
# Последний коммит
git log --oneline -5

# Что изменилось в последнем коммите
git diff --name-only HEAD~1..HEAD

# Что изменилось в последних N коммитах
git diff --name-only HEAD~N..HEAD

# Что изменилось в ветке относительно main
git diff --name-only main..HEAD

# Полный diff для чтения содержимого
git diff HEAD~1..HEAD -- app/metrics.py
```

## Справка: test bundles по типу изменений

Из `doc/agent_workflow_test_bundles.md`:

| Тип изменения | Bundle |
|---|---|
| Config / Settings | `tests/test_config.py` |
| Tutor core / orchestration | `test_tutor_orchestrator.py test_pipeline_steps.py` |
| Tutor API / typed contracts | `test_query_service.py test_tutor_learner_contract.py test_api.py` |
| Persistence / learner state | `test_user_state.py test_learner_model_service.py` |
| Graph metrics / gate | `test_metrics.py test_graph_expansion_benchmark.py test_check_graph_expansion_gate.py` |
| Flashcards / SRS | `test_flashcard_service.py test_spaced_repetition.py` |
| Quiz / adaptive | `test_quiz_service.py test_quiz_adaptive.py` |
| Baseline (неизвестный тип) | `test_api.py test_config.py` |
