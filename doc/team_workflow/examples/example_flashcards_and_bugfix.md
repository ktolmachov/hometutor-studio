# Пример автоматизации: Flashcards + Bug Fix

Актуализировано: **2026-04-12**

Два сквозных примера работы командного конвейера из [`process.md`](process.md)
на реальном материале проекта.

---

## Пример 1: Развитие фичи Flashcards

### Контекст

E12 закрыт: базовые flashcards реализованы (генерация, SM-2 review, Anki export,
колоды, home badge). Следующий шаг — улучшение качества учёбы: пользователь
хочет видеть **статистику прогресса по колоде** и иметь возможность
**отфильтровать карточки по тегу** во время сессии повторения.

Это реальный gap из `doc/cjm.md` (стадия **Retain**) — пользователь не видит,
насколько он продвинулся внутри конкретной колоды.

---

### Фаза 1: Product Owner — Промпт 1 (Planning)

**Что вставить в агент:**

```text
Role: Product Owner for hometutor learning assistant.
Goal: define the next delivery package.

Read these files (do not edit yet):
1. doc/backlog_registry.yaml — current active backlog, open/deferred/proposed items
2. doc/cjm.md — customer journey map, pain points by stage
3. doc/future_roadmap.md — strategic horizon (E15+)
4. doc/closed_iterations.md — last 2-3 closed epochs (patterns, size)
5. doc/user_stories.md — index of user stories
6. doc/vision.md — product boundaries and value proposition

Analysis steps:
1. Identify the top CJM pain point that is NOT yet addressed by closed epochs.
2. Find user stories (US-*) that map to this pain point.
3. Check if any deferred items in backlog_registry.yaml should be absorbed.
4. Verify that the proposed work fits within WIP=1 and max 5 outcomes.

Output format:
## Proposed Package: E15-A

...
```

**Ожидаемый артефакт от агента:**

```markdown
## Proposed Package: E15-A

### CJM Stage
Retain — пользователь повторяет карточки, но не знает, насколько
хорошо он знает колоду в целом и где слабые места.

### Goal
Пользователь видит прогресс внутри колоды и может сфокусировать
повторение на слабых тегах.

### Outcomes (2)
- Outcome 1: Deck Progress Bar
  - User Story: US-15.3 (track mastery per deck)
  - AC: пользователь видит % освоенных карточек (easy/good/hard)
    на странице колоды
  - CJM Stage: Retain

- Outcome 2: Tag filter in review session
  - User Story: US-15.4 (filter cards by tag)
  - AC: при старте сессии пользователь может выбрать тег;
    только карточки этого тега попадают в очередь
  - CJM Stage: Retain

### Dependencies
E12 closed (base flashcard stack) ✓

### Risks
- US-15.3 acceptance criteria неполны — нужна детализация Аналитика
- Tag filter меняет /flashcards/due/list endpoint — риск регрессии badge
```

---

### Фаза 2: Analyst — Промпт 1 (Детализация)

**Что вставить в агент:**

```text
Role: Analyst for hometutor learning assistant.
Goal: produce a detailed specification for package E15-A.

Input from Product Owner:
[вставить артефакт от PO]

Read these files (do not edit):
1. doc/user_stories/US-15.3.md
2. doc/user_stories/US-15.4.md
3. doc/cjm.md
4. app/routers/flashcards.py — существующие endpoints
5. app/flashcard_service.py — бизнес-логика
6. app/user_state.py — схема БД (flashcard_decks, flashcards)
7. app/ui/flashcards_ui.py — текущий UI

[полный промпт из analyst.md → Промпт 1]
```

**Ожидаемый артефакт (фрагмент):**

```markdown
## Specification: E15-A

### Outcome 1: Deck Progress Bar

#### Scenarios
| # | Given | When | Then |
|---|-------|------|------|
| 1 | Колода существует, 10 карточек, 6 с ease_factor > 2.5 | Пользователь открывает страницу колоды | Прогресс-бар показывает 60%, label "6 из 10 освоено" |
| 2 | Колода пустая | Пользователь открывает страницу | Прогресс-бар = 0%, label "Нет карточек" |
| 3 | Все карточки новые (ни разу не повторялись) | Открывает страницу | 0%, label "0 из N освоено" |

#### Data Flow
GET /flashcards/{deck_id}/progress
  → flashcard_service.get_deck_progress(deck_id)
  → user_state: SELECT count(*) WHERE ease_factor > 2.5
  → {"mastered": N, "total": M, "percent": P}
  → flashcards_ui.py: st.progress(P/100)

#### Affected Components
- API: новый GET /flashcards/{deck_id}/progress
- Models: новый FlashcardDeckProgress response model
- Services: новый get_deck_progress() в flashcard_service.py
- UI: прогресс-бар в deck detail view

### Outcome 2: Tag Filter in Review Session

#### Scenarios
| # | Given | When | Then |
|---|-------|------|------|
| 1 | Колода с тегами "python", "math" | Пользователь выбирает тег "python" | В сессию попадают только карточки с тегом "python" |
| 2 | Тег выбран, нет due-карточек с этим тегом | Старт сессии | Сообщение "Нет карточек к повторению по тегу 'python'" |
| 3 | Тег не выбран (All) | Старт сессии | Все due-карточки (текущее поведение) |

#### Open Questions
- Теги хранятся как строка (comma-separated) в поле tags в БД.
  Нужно ли добавить отдельную таблицу тегов? → Архитектору
```

---

### Фаза 3: Architect — Промпт 1 (Execution Contract)

**Что вставить в агент:**

```text
Role: Architect for hometutor learning assistant.
Goal: produce an execution contract for package E15-A.

Input:
[вставить спецификацию от Аналитика]

Read these files (do not edit):
1. doc/conventions.md
2. doc/conventions_architecture.md
3. doc/adr.md
4. app/flashcard_service.py
5. app/routers/flashcards.py
6. app/user_state.py
7. app/api_models.py
8. tests/test_flashcard_service.py

[полный промпт из architect.md → Промпт 1]
```

**Ожидаемый артефакт:**

```markdown
## Execution Contract: E15-A

### Package E15-A-1: Deck Progress
**Responsibility:** backend progress calculation + API endpoint

Write-set:
- app/user_state.py — add get_deck_progress_stats(deck_id) SQL query
- app/flashcard_service.py — add get_deck_progress(deck_id) function
- app/routers/flashcards.py — add GET /flashcards/{deck_id}/progress
- app/api_models.py — add FlashcardDeckProgress model
- tests/test_flashcard_service.py — add progress tests

Read-set:
- app/spaced_repetition.py — SM-2 thresholds
- app/api_helpers.py — error handling patterns

Do-not-touch:
- app/ui/flashcards_ui.py (до E15-A-2)
- app/prompts.py
- app/config.py

DoD:
- pytest tests/test_flashcard_service.py green
- GET /flashcards/{deck_id}/progress returns {"mastered": N, "total": M, "percent": P}
- ease_factor > 2.5 threshold matches SM-2 convention in app/spaced_repetition.py

### Package E15-A-2: Tag Filter UI (depends on E15-A-1)
**Responsibility:** UI tag selector + filtered due endpoint

Write-set:
- app/user_state.py — add tag filter to get_due_flashcards()
- app/flashcard_service.py — pass tag param to get_due_flashcards()
- app/routers/flashcards.py — add ?tag= query param to /due/list
- app/ui/flashcards_ui.py — tag selector multiselect before session start

Do-not-touch:
- app/ui/home_hub.py (badge uses /due/count, not /due/list — no regression)
- app/ui/resume_cards.py

DoD:
- pytest tests/test_flashcard_service.py green (tag filter cases)
- /flashcards/due/list?tag=python returns only cards with "python" in tags
- /flashcards/due/count unchanged (no regression on home badge)

### New ADR Needed?
No. Tags as comma-separated string is acceptable given SQLite LIKE query
(< 1000 cards). Not worth a separate tags table at current scale.

### Copy-Paste Developer Prompt (E15-A-1):
Goal: close E15-A-1 only.
Context: Add deck progress endpoint to flashcards feature (Retain CJM).
Scope: new get_deck_progress_stats in user_state, get_deck_progress in
flashcard_service, GET /flashcards/{deck_id}/progress endpoint.
Files to inspect first:
- app/user_state.py (existing flashcard schema)
- app/flashcard_service.py
- app/spaced_repetition.py (ease_factor threshold)
- tests/test_flashcard_service.py
DoD: pytest tests/test_flashcard_service.py green;
endpoint returns {"mastered":N, "total":M, "percent":P}.
Do not touch: app/ui/, app/prompts.py, app/config.py.
Output: changed files + tests + unresolved risk.
```

---

### Фаза 4: Designer — Промпт 1 (UI Spec) — параллельно с Architect

**Что вставить в агент:**

```text
Role: UX/UI Designer for hometutor Streamlit learning assistant.
Goal: produce a UI specification for package E15-A.

Input:
[вставить спецификацию от Аналитика]

Read these files (do not edit):
1. doc/cjm.md
2. app/ui/flashcards_ui.py — current flashcard UI
3. app/ui/home_hub.py — home badge reference
4. app/ui/main.py — navigation

[полный промпт из designer.md → Промпт 1]
```

**Ожидаемый артефакт (фрагмент):**

```markdown
## UI Specification: E15-A

### Screen: Deck Detail View (модификация)

#### Layout (добавляется после заголовка колоды)
┌──────────────────────────────────────┐
│  📚 Название колоды                  │
│  ─────────────────────────────────── │
│  Прогресс освоения                   │
│  [████████░░░░░░░░░░] 40%            │
│  6 из 15 карточек освоено            │
│  ─────────────────────────────────── │
│  Фильтр по тегу: [All ▾]             │
│                                      │
│  [Начать повторение →]               │
└──────────────────────────────────────┘

#### Components
| Component | Type | Data Source | Interaction |
|-----------|------|-------------|-------------|
| Progress bar | st.progress(val) | GET /flashcards/{id}/progress | read-only |
| Progress label | st.caption | same response | read-only |
| Tag selector | st.selectbox | GET /flashcards/{id}/tags | фильтрует сессию |
| Start button | st.button | — | запускает сессию с tag param |

#### States
| State | Condition | What User Sees |
|-------|-----------|---------------|
| Loading | API call | st.spinner("Загружаю статистику...") |
| Empty deck | total=0 | st.info("Нет карточек. Создайте карточки из документа.") |
| All new | mastered=0 | Прогресс 0%, "Начните повторение — карточки пока не освоены" |
| Populated | mastered>0 | Полный layout с прогресс-баром |

#### Session State Keys
- st.session_state["fc_tag_filter"] — выбранный тег, default None
- st.session_state["fc_session_active"] — bool (уже используется)
```

---

### Фаза 5: Developer — Промпт 1 (Реализация E15-A-1)

**Что вставить в агент (copy-paste из контракта Архитектора):**

```text
Goal: close E15-A-1 only.

Context:
Add deck progress statistics to flashcards feature.
Closes CJM Retain gap: user sees how well they know a deck.

Scope:
1. Add get_deck_progress_stats(deck_id) to app/user_state.py
2. Add get_deck_progress(deck_id) to app/flashcard_service.py
3. Add GET /flashcards/{deck_id}/progress endpoint
4. Add FlashcardDeckProgress Pydantic model to app/api_models.py

Files to inspect first:
- app/user_state.py (flashcard schema, existing _with_db pattern)
- app/flashcard_service.py (existing service functions)
- app/spaced_repetition.py (SM-2 thresholds, ease_factor)
- app/routers/flashcards.py (existing endpoint patterns)
- tests/test_flashcard_service.py (test patterns)

Write-set:
- app/user_state.py
- app/flashcard_service.py
- app/routers/flashcards.py
- app/api_models.py
- tests/test_flashcard_service.py

Do not touch:
- app/ui/ (E15-A-2)
- app/prompts.py
- app/config.py
- app/ui/home_hub.py (badge uses /due/count — no touch)

DoD:
- pytest tests/test_flashcard_service.py green
- GET /flashcards/{deck_id}/progress returns {"mastered":N,"total":M,"percent":P}
- ease_factor > 2.5 threshold aligns with app/spaced_repetition.py convention

Working rules:
- Follow conventions from doc/conventions.md
- Use _with_db() pattern from user_state.py for all DB access
- Use existing error handling patterns from app/api_helpers.py
- Do not refactor unrelated functions

Output:
- Changed files
- Tests run + result
- What was completed
- Unresolved risk / follow-up, if any
```

---

### Фаза 6: Tester — Промпт 1 (Верификация)

**Что вставить в агент:**

```text
Role: Tester for hometutor learning assistant.
Goal: verify package E15-A-1.

CONTRACT_FILE: archive/agent_prompts/e15_a1_flashcard_progress_2026-04-13.md
PACKAGE_ID: E15-A-1
COMMIT_RANGE: HEAD~3..HEAD
PACKAGE_TYPE: code

[полный промпт из tester.md → Промпт 1]
```

**Ожидаемый артефакт:**

```markdown
## Step 1: Scope Check

Changed files vs write-set:
| File | In Write-Set? | Expected? |
|------|:------------:|:---------:|
| app/user_state.py | yes | yes |
| app/flashcard_service.py | yes | yes |
| app/routers/flashcards.py | yes | yes |
| app/api_models.py | yes | yes |
| tests/test_flashcard_service.py | yes | yes |

→ OK. No extra files changed.

## Step 2: DoD Checklist

| # | DoD Criterion | Command | Result | Pass? |
|---|--------------|---------|--------|:-----:|
| 1 | pytest green | pytest tests/test_flashcard_service.py | 23 passed | ✓ |
| 2 | endpoint returns correct shape | curl /flashcards/1/progress | {"mastered":6,"total":10,"percent":60.0} | ✓ |
| 3 | ease_factor threshold = 2.5 | grep ease_factor user_state.py | line 312: > 2.5 | ✓ |

## Step 5: Verdict

### PASS
All DoD criteria met. No scope violations. No regressions.
Regression bundle: pytest tests/test_flashcard_service.py — 23 passed, 0 failed.
```

---

## Пример 2: Поиск и исправление бага

### Контекст

Пользователь сообщает: **"badge с количеством карточек к повторению на главном
экране показывает 0, хотя в разделе Flashcards есть 5 карточек due".**

---

### Шаг 1: Tester — Regression Suite (диагностика)

**Что вставить в агент:**

```text
Role: Tester for hometutor.
Goal: run regression suite to locate failing area.

Run these test bundles:
1. python -m pytest tests/test_flashcard_service.py -v
2. python -m pytest tests/test_api.py -k "flashcard" -v
3. python -m pytest tests/test_user_state.py -k "due" -v

Also check manually:
- curl http://localhost:8000/flashcards/due/count
- curl http://localhost:8000/flashcards/due/list

Report: which tests fail, what errors appear.
[полный промпт из tester.md → Промпт 2]
```

**Ожидаемый артефакт:**

```markdown
## Regression Report — 2026-04-13

| # | Suite | Tests | Passed | Failed |
|---|-------|-------|--------|--------|
| 1 | test_flashcard_service.py | 20 | 19 | 1 |
| 2 | test_api.py (flashcard) | 5 | 5 | 0 |
| 3 | test_user_state.py (due) | 3 | 2 | 1 |

### Failures
| Test | Error |
|------|-------|
| test_count_due_flashcards | AssertionError: expected 3, got 0 |
| test_user_state_due_returns_correct_count | AssertionError: expected 2, got 0 |

Manual API check:
- GET /flashcards/due/count → {"count": 0}  ← WRONG (5 cards are overdue)
- GET /flashcards/due/list → []             ← WRONG

### Likely Cause
count_due_flashcards() in user_state.py queries next_review <= NOW.
Possible timezone mismatch: cards stored as UTC ISO string,
query uses datetime.now() without UTC → comparison fails.

### Overall: FAIL (2 failures)
```

---

### Шаг 2: Analyst — Impact Analysis (опционально при сложном баге)

Для простого бага этот шаг пропускается — Tester уже указал likely cause.
Analyst нужен, если баг затрагивает несколько компонентов.

---

### Шаг 3: Architect — Диагностика и write-set

**Что вставить в агент:**

```text
Role: Architect for hometutor.
Goal: confirm root cause and define write-set for bugfix.

Bug report:
- /flashcards/due/count returns 0 when cards are overdue
- Likely cause from Tester: timezone mismatch in count_due_flashcards()

Read these files (do not edit):
1. app/user_state.py — count_due_flashcards(), get_due_flashcards()
2. app/flashcard_service.py — _utc_now_iso()
3. tests/test_user_state.py — failing test

Confirm:
1. Is _utc_now_iso() used consistently for both storage and comparison?
2. Is the SQL query using UTC-aware comparison?
3. Are there other places in the codebase with the same issue?

Output:
- Root cause (exact file:line)
- Write-set for fix
- Do-not-touch list
- DoD
- Regression test bundle
```

**Ожидаемый артефакт:**

```markdown
## Bug Root Cause: E15-BUG-001

### Root Cause
app/user_state.py:287
  `WHERE next_review <= datetime('now')`

Cards are stored with next_review as UTC ISO string
(e.g. "2026-04-10T08:00:00+00:00") via _utc_now_iso().
SQLite's datetime('now') returns UTC without timezone offset.
The comparison fails because ISO offset string "+00:00" sorts AFTER
naive UTC string "2026-04-13T...", causing all overdue cards to be missed.

### Fix
Replace: `datetime('now')`
With:    `strftime('%Y-%m-%dT%H:%M:%S', 'now')`
And strip timezone from stored value before comparison,
OR store next_review as naive UTC ISO without offset.

Consistent approach: use datetime.utcnow().isoformat() (no tz suffix)
for storage AND query. Update _utc_now_iso() in flashcard_service.py.

### Write-set
- app/user_state.py — fix SQL WHERE clause (lines ~287, ~310)
- app/flashcard_service.py — fix _utc_now_iso() to return naive UTC

### Do-not-touch
- app/spaced_repetition.py
- app/ui/
- app/prompts.py

### DoD
- pytest tests/test_flashcard_service.py green
- pytest tests/test_user_state.py -k "due" green
- curl /flashcards/due/count returns correct count
- No regression: pytest tests/test_api.py -k "flashcard" green

### Regression Bundle
pytest tests/test_flashcard_service.py tests/test_user_state.py tests/test_api.py
```

---

### Шаг 4: Developer — Промпт Bugfix

**Что вставить в агент:**

```text
Role: Developer for hometutor.
Goal: fix bug E15-BUG-001 (due count always returns 0).

Symptoms:
GET /flashcards/due/count returns {"count": 0} even when cards are overdue.
Tests test_count_due_flashcards and test_user_state_due_returns_correct_count fail.

Root cause (from Architect):
app/user_state.py ~line 287: datetime('now') comparison fails against
UTC ISO strings with "+00:00" offset stored by _utc_now_iso().

Expected behavior:
/flashcards/due/count returns correct count of cards where next_review <= now.

Files to inspect first:
- app/user_state.py (count_due_flashcards, get_due_flashcards, ~lines 280-320)
- app/flashcard_service.py (_utc_now_iso function)
- tests/test_user_state.py (failing tests — understand expected data format)

Write-set:
- app/user_state.py — fix datetime comparison in SQL queries
- app/flashcard_service.py — fix _utc_now_iso() to use naive UTC

Do not touch:
- app/spaced_repetition.py
- app/routers/flashcards.py (unless SQL fix requires API change)
- app/ui/

DoD:
- pytest tests/test_flashcard_service.py green (all passing)
- pytest tests/test_user_state.py -k "due" green
- Regression test added for timezone handling

Working rules:
- Write regression test FIRST, then fix
- Keep fix minimal — do not refactor _utc_now_iso callers beyond this bug
- If stored data in SQLite already has "+00:00" suffix, strip it in SQL:
  replace(next_review, '+00:00', '') — document this decision

Output:
- Root cause (file:line, what was wrong)
- Fix applied (file:line, what changed)
- Regression test added
- Test results
```

---

### Шаг 5: Tester — Верификация фикса

**Что вставить в агент:**

```text
Role: Tester for hometutor.
Goal: verify bugfix E15-BUG-001.

CONTRACT_FILE: (bug report from Architect above)
PACKAGE_ID: E15-BUG-001
COMMIT_RANGE: HEAD~1..HEAD
PACKAGE_TYPE: code

Expected after fix:
- pytest tests/test_flashcard_service.py: all green
- pytest tests/test_user_state.py -k "due": all green
- GET /flashcards/due/count: returns correct count

[полный промпт из tester.md → Промпт 1]
```

**Ожидаемый вердикт:**

```markdown
## Verdict: PASS

Scope check: only app/user_state.py and app/flashcard_service.py changed.
DoD: pytest tests/test_flashcard_service.py — 21 passed (incl. new regression test).
Regression: pytest tests/test_api.py -k "flashcard" — 5 passed, 0 failed.
Manual: GET /flashcards/due/count → {"count": 5} ✓

Badge on home screen now shows correct count.
```

---

## Сводная схема двух примеров

```
FEATURE (E15-A):                  BUG (E15-BUG-001):
PO → Analyst → Architect          Tester (диагностика)
             ↘ Designer           ↓
               Developer    Architect (root cause + write-set)
               Tester            ↓
               PO (closure)  Developer (bugfix)
                                  ↓
                              Tester (verify)
                                  ↓
                              PO (closure)
```

**Ключевая разница:**
- Фича проходит полный конвейер (6 ролей, артефакт на каждом шаге).
- Баг стартует с Tester (диагностика), Analyst пропускается при ясном root cause,
  Developer получает готовый write-set от Архитектора.

## Где хранить артефакты

```
archive/team_artifacts/
  E15-A/
    1_po_package.md
    2_analyst_spec.md
    3_architect_contract.md
    4_designer_ui_spec.md
    5a_developer_e15a1.md
    5b_developer_e15a2.md
    6a_tester_e15a1.md
    6b_tester_e15a2.md
  E15-BUG-001/
    1_tester_regression_report.md
    2_architect_root_cause.md
    3_developer_fix.md
    4_tester_verify.md
```
