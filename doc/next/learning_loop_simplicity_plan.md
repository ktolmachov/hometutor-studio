# Learning Loop Simplicity Plan

Updated: 2026-07-11 (audit reconciliation; см. «История ревизий»)

Status: mixed: A1 done; A2/B1/B2/B3/C2/C3 proposed; C1 needs discovery. Это по-прежнему кандидаты; `backlog_registry.yaml` этим документом не меняется.
Owner: product / learning experience
Source: эволюционный UX/продуктовый разбор hometutor 2026-07-10 (формат — [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md)).
Полный читаемый разбор: HTML-артефакт той сессии — https://claude.ai/code/artifact/c715212c-86fa-477d-96d0-76f749b7a4a8 (приватная session-ссылка; исходный scratchpad-файл не гарантированно переживает сессию).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- `doc/roadmap.md`, `doc/future_roadmap.md`
- `doc/next/roadmap_recommendations_2026-06-11.md` — соседний recommendations-регистр
- hometutor: `docs/user_guide.md`, `docs/conventions_architecture.md`, `docs/api_reference.md`

## История ревизий

- **2026-07-10** — первая версия: все кандидаты были `proposed`.
- **2026-07-11** — сверено с актуальным `hometutor` commit `680345d` (`148`). Основные исправления:
  - **A1 закрыт (`done`)**: `app/ui/study_scope.py`, `app/ui/main.py`, `docs/user_guide.md`, `tests/test_study_scope.py` уже сохраняют и гидратируют course scope через `app_kv`.
  - **A2 evidence сужен**: cold-user уже видит только 3 плитки, а tiles фильтруются по tier. Оставшаяся проблема — конкуренция блоков у non-cold / tier 2+ пользователя вокруг SSR hero.
  - **B1 evidence уточнён**: `dashboards_graph.py` только рендерит caption; D3 stats считаются в `app/ui/knowledge_graph_d3.py`. Несостыковка счётчиков остаётся реальной, но root cause переписан точнее.
  - **B2 сужен**: Mission Control SSR details уже свёрнуты по умолчанию через `<details>` без `open`; оставшаяся проблема — сырой диагностический язык внутри раскрытого блока.
  - **B3 дополнен осторожностью про deep-link**: текст баннера не должен обещать доступность скрытых views, пока не проверены переходы через `PENDING_CURRENT_VIEW_KEY`.
  - **C1 понижен до `needs discovery`**: `source:` tags у карточек обозначают документ-источник, а не стабильный `concept_id`; нужен контракт card→concept до реализации.
  - **C2 переименован** из «уровни 0–4» в **ступени петли обучения** (`learner_stage`), чтобы не конфликтовать с существующими XP-уровнями в `app/gamification_service.py`.
  - **C3 Files расширен**: добавлен `app/ui/pages/3_Мой_прогресс.py` и pre-flight inventory для e2e/deep-link ссылок.

## Как использовать этот документ

Это **не** SSoT исполнения. Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной. Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне согласованного write-set.

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`. В этой ревизии добавлен `needs discovery` — идея ценна, но контракт данных ещё не готов к реализации.

## Суть разбора

Ядро продукта — не набор режимов, а одна петля: **вопрос → понимание → проверка → память (SM-2) → возврат в точное место лекции** (раздел · строка · таймкод видео). Всё, что не крутит эту петлю и не обслуживает её, — кандидат на «спрятать глубже», а не обязательно удалить.

---

## Волна-кандидат A: `wave-learning-loop-hero` (P0)

**North star (кандидат):** пользователь возвращается и продолжает обучение одним действием — без переактивации курса и без выбора из множества равнозначных плиток.

**Kill switch (кандидат):** если скрытие плиток с первого экрана снижает discovery основных режимов у новых пользователей (доля новых пользователей, ни разу не открывших Tutor/Quiz/Flashcards за первую неделю, растёт >10пп), вернуть плитки на первый экран вторым рядом.

### Кандидат A1 — Персистентный активный курс (scope)

**Статус: `done`** — реализован в `hometutor` commit `680345d` (`148`, 2026-07-11). Раздел оставлен как исторический контракт, а не pending-задача.

**Приоритет:** P0 · **Усилие:** малое, подтвердилось

**Изначальная проблема.** Активный курс жил только в `st.session_state` и терялся после перезапуска Streamlit.

**Что реализовано (evidence, hometutor@680345d):**
- `app/ui/study_scope.py:26-28` задаёт ключи `study_scope.active`, `study_scope.last_deactivated`, `_study_scope_hydrated`.
- `app/ui/study_scope.py:78-92` пишет active/last-deactivated scope payload через `app.user_state_core.set_kv`.
- `app/ui/study_scope.py:146-172` сохраняет active scope из `activate_scope()` при `state is None`.
- `app/ui/study_scope.py:184-195` сохраняет last deactivated scope и очищает active scope в `app_kv` из `deactivate_scope()`.
- `app/ui/study_scope.py:227-264` добавляет `restore_scope_from_app_kv()`: гидратация один раз за сессию, проверка существования папки курса, однострочное уведомление при деградации.
- `app/ui/main.py:103-109` вызывает `restore_scope_from_app_kv()` на старте UI и показывает notice через `st.info()`.
- `docs/user_guide.md:300-303` документирует, что активный курс и последний деактивированный курс переживают рестарт.
- `tests/test_study_scope.py:64-205` покрывает persist, hydration, missing-folder degradation, idempotence и no-DB поведение при injected state.

**DoD:** выполнено.
- Рестарт после активного курса → курс восстановлен.
- Удалённая/переименованная папка → no-scope + notice, без краша.
- Последний деактивированный курс переживает рестарт для restore-кнопок.

---

### Кандидат A2 — Один hero-CTA на Mission Control

**Статус: `proposed`; требует owner sign-off перед стартом** — меняет главный экран и широкий UI write-set.

**Приоритет:** P0 · **Усилие:** среднее

**Проблема (уточнена).** V1 завышал масштаб: текущий `Mission Control` уже сфокусирован для cold-user:
- `_COLD_USER_TILE_IDS` содержит только `quick_question`, `tutor`, `quiz` (`app/ui/mission_control.py:142-146`).
- `_render_tile_grid(..., cold_user=True)` фильтрует до этих 3 плиток (`app/ui/mission_control.py:464-466`).
- Non-cold users видят SSR banner + tier-filtered tiles + KG card + Living Konspekt resume-card (`app/ui/mission_control.py:827-886`).

Оставшаяся проблема — warm/non-cold первый экран: SSR уже похож на hero, но конкурирует с сеткой и дополнительными карточками. Tier 2 обычно видит 5 плиток, tier 3+ — до 7.

**Evidence:**
- `app/ui/mission_control.py:294-368` рендерит SSR banner с видимой причиной и primary button.
- `app/ui/mission_control.py:432-489` связывает tiles с `TILE_FEATURE_IDS` и `feature_visible()`.
- `app/ui/feature_registry.py:27-41` задаёт tier-видимость: `quick_answer` tier 1; `tutor`, `quiz`, `flashcards`, `topics`, `progress` tier 2; `course`, `adaptive_plan`, `knowledge_graph`, `living_konspekt` tier 3.
- `app/ui/mission_control.py:878-885` для non-cold рендерит SSR, tiles, configure button, KG mini-card и Living Konspekt card.

**Proposed change:**
1. Оставить SSR единственным hero CTA; не создавать второй decision engine.
2. Добавить компактную строку контекста: активный курс, learner_stage/XP level при наличии, streak.
3. Под hero показывать не больше двух resume-карточек по priority/recency.
4. Полную сетку tiles перенести в свёрнутый блок «Ещё режимы»; entry points не теряются.
5. Course activation после A1 не должна быть постоянной peer-плиткой; первая активация относится к onboarding/course setup.

**Files:** прежде всего `app/ui/mission_control.py`; возможно `app/ui/home_hub.py`, `app/ui/cockpit_rotator.py`, `app/ui/smart_study_next_step_card.py`, `app/ui/resume_cards*.py`, `app/ui/sidebar.py`.

**DoD:**
- Above the fold для warm users: 1 context row, 1 SSR hero CTA, ≤2 resume cards.
- Полная сетка режимов доступна за один клик.
- SSR остаётся единственным источником текста/action hero.
- Cold-user 3-tile focus не регрессирует.

**Doc-sync:** `docs/user_guide.md`, раздел Mission Control.

---

## Волна-кандидат B: `wave-trust-signals` (P1)

**North star (кандидат):** каждое число и каждая рекомендация заслуживают доверия с первого взгляда — без противоречивых счётчиков и developer-language диагностики на learner surface.

### Кандидат B1 — Единый источник счётчиков Knowledge Graph

**Статус: `proposed`**

**Приоритет:** P1 · **Усилие:** малое–среднее

**Проблема.** Mission Control и Knowledge Graph могут показывать разные значения под похожими подписями: «концептов», «готово учить». V1 верно нашёл дублирующуюся логику, но неточно назвал место вычисления D3 stats.

**Уточнённый evidence:**
- `app/ui/mission_control.py:715-721`: Mission Control читает raw `knowledge_graph.get_concepts()`, считает `total`, вычитает `lesson` nodes в `concept_nodes`, а `frontier` берёт из raw `data.get("frontier")`.
- `app/ui/dashboards_graph.py:1089-1093`: graph tab только рендерит `payload["stats"]` в caption.
- `app/ui/knowledge_graph_d3.py:323-381`: D3 payload пересчитывает `frontier` из `mastery`, `learned` и prerequisite readiness, затем задаёт `stats["total"] = len(nodes)` вместе с lesson nodes.
- `app/ui/dashboards_graph.py:1064-1084` передаёт active `source_paths`, но `app/ui/knowledge_graph_d3.py:463-469` использует их только для `compiler_health`, а не для фильтрации nodes. Значит mismatch не объясняется scope filtering.

**Proposed change.** Вынести shared helper (после выбора ownership: `app/knowledge_service.py`, `app/visualization_service.py` или рядом с D3 payload), который возвращает:
- `total_concepts` без lesson nodes;
- `total_lessons`;
- одно определение `frontier_count`;
- `avg_mastery` с явным denominator;
- `clusters`;
- optional `bundle_state` / source label, если published/staging/legacy differs.

Mission Control и Knowledge Graph используют один helper. Если экраны намеренно показывают разные graph versions, UI явно показывает это.

**Files:** shared helper + `app/ui/mission_control.py`, `app/ui/dashboards_graph.py`, targeted tests.

**DoD:**
- Одна версия графа даёт одинаковые counters на Mission Control и Knowledge Graph.
- Разные версии графа явно промаркированы.
- Regression test не даёт вернуть независимый `total - lessons` расчёт.

**Doc-sync:** только если добавляется пользовательский bundle/source label.

---

### Кандидат B2 — SSR explanation без сырой диагностики

**Статус: `proposed`, сужен после аудита**

**Приоритет:** P1 · **Усилие:** малое

**Проблема (уточнена).** V1 утверждал, что «Как выбрана подсказка» раскрыта по умолчанию. Сейчас Mission Control рендерит native `<details class="ssr-details">` без `open`, то есть блок уже свёрнут (`app/ui/mission_control.py:356-357`).

Оставшаяся проблема — содержимое после раскрытия: «Локальные сигналы» всё ещё могут показывать implementation-language вроде `source-trust` и SSR policy internals.

**Evidence:**
- `app/ui/mission_control.py:303-319` собирает `ledger_lines` и рендерит их в секции «Локальные сигналы».
- `app/ui/mission_control.py:356-357` показывает, что details свёрнуты по умолчанию.
- `app/ui/smart_study_next_step_card.py:112-145` содержит отдельный confidence-ledger expander, тоже collapsed.

**Proposed change.** Оставить человекочитаемые секции («Другие варианты», «Если выбрать иначе», «Маршрут») в обычном details, но сырые evidence ledger lines перенести в tier 5 debug surfaces (`panel:debug_summary`) или переписать на learner-language.

**Files:** `app/ui/mission_control.py`, `app/ui/smart_study_next_step_card.py`, `app/smart_study_evidence.py` если текст меняется на источнике.

**DoD:** non-expert users не видят raw `source-trust` / SSR policy flags даже после раскрытия обычных SSR details; expert/debug tier сохраняет inspectability.

**Doc-sync:** `docs/user_guide.md`, раздел Smart Study Router.

---

### Кандидат B3 — Предложить существующим пользователям пресет «Основной»

**Статус: `proposed`**

**Приоритет:** P1 · **Усилие:** малое

**Проблема.** Existing users default to «Всё включено», поэтому progressive disclosure не помогает пользователям, у которых уже накоплена перегрузка UI.

**Evidence:**
- `docs/user_guide.md:70-76` документирует пресеты «Основной» и «Всё включено» и default для existing users.
- `app/ui_preferences.py:109-115` возвращает `LEVEL_ALL` и сохраняет его, если `_has_existing_activity()` true и явного уровня нет.
- `tests/test_ui_preferences.py:24-29` фиксирует это поведение.

**Proposed change.** Одноразовый dismissible banner для existing users без explicit saved choice: предложить «Основной». Accept ставит UI level `2`; dismiss пишет app_kv-флаг «не показывать снова».

**Осторожность.** Не обещать в тексте «всё останется доступным через deep-link», пока это не проверено. Hidden-view navigation идёт через `PENDING_CURRENT_VIEW_KEY` и visible/hidden nav handling; перед такой формулировкой вручную проверить хотя бы один hidden tier-3 view под level 2.

**Files:** `app/ui_preferences.py`, `app/ui/control_panel.py`, возможно `app/ui/navigation_visibility.py`, tests.

**DoD:** banner показан один раз eligible existing users; accept/dismiss persisted; explicit user choice never overwritten; hidden-view/deep-link claim verified before shipping copy.

**Doc-sync:** `docs/user_guide.md`, раздел UI levels.

---

## Волна-кандидат C: `wave-difficulty-and-mastery-mirror` (P2)

**North star (кандидат):** студент видит, где он застревает и куда расти дальше, в одном месте, а не на трёх поверхностях.

### Кандидат C1 — Индекс трудности концепта («Сложные темы»)

**Статус: `needs discovery`**

**Приоритет:** P2 · **Усилие:** пока не оценивать надёжно

**Проблема/возможность.** Сигналы сложности существуют по отдельности: reach в графе, quiz diagnostic status, SM-2/flashcard outcomes, weak concept lists. Они не агрегированы в стабильную поверхность «сложные темы».

**Важное исправление.** V1 предполагал, что Again-rate карточек можно агрегировать по концепту через `source:` tags. Текущий код этого напрямую не поддерживает:
- `app/flashcard_service.py:300` пишет `source:{source_path}`.
- `tests/test_term_cards.py:102-132` документирует `source:` как corpus-relative path convention.
- `tests/test_living_konspekt_view_smoke.py:311-346` использует `source:` для фильтрации document/konspekt memory, а не `concept_id`.

Итого: `source:` даёт card → document, не card → concept. Индексу трудности нужен explicit mapping или аккуратно описанный lossy resolver.

**Discovery перед реализацией:**
1. Выбрать card → concept mapping:
   - добавить explicit `concept:` tag/field при генерации карточек из concept-aware flows; или
   - выводить через document → related concepts из KG с известной неоднозначностью.
2. Найти точное хранилище diagnostic statuses (`recognized`, `recalled`, `misconception`, `cannot_apply`) и решить, агрегировать ли из `quiz_results`, `micro_quiz_events`, tutor snapshots или нового normalized helper.
3. Определить веса скоринга на реальных данных, а не произвольными constants.
4. До нового `hint_kind` составить SSR blast radius: `SmartStudyRouterHintKind`, scoring, evidence/explanation, feedback, `HINT_TO_TILE`, `assert_hint_mapping_complete()`.

**Evidence для SSR blast radius:**
- `app/smart_study_recommendation.py:12` задаёт `SmartStudyRouterHintKind`.
- `app/ui/mission_control.py:48` мапит hints в tiles.
- `app/ui/mission_control.py:889-893` проверяет, что каждый hint имеет tile mapping.

**Files после discovery:** вероятно `app/concept_difficulty_service.py` или `app/learner_model_service.py`, `app/ui/dashboards_progress.py`, SSR routing/explanation files, tests.

**Doc-sync после реализации:** `docs/user_guide.md`; `docs/api_reference.md` только если появится endpoint.

---

### Кандидат C2 — Видимая ступень петли обучения (ранее «уровни 0–4»)

**Статус: `proposed`, переименован после аудита**

**Приоритет:** P2 · **Усилие:** среднее

**Исправление.** Не называть это «level 0–4» в коде или UI. В `app/gamification_service.py` уже есть XP-level система:
- `level_from_total_xp()` — `app/gamification_service.py:113`;
- `level_title()` — `app/gamification_service.py:119`;
- XP progress и level-up logic дальше в том же модуле.

Использовать отдельный термин: **ступень петли обучения** (`learner_stage`). Это прогресс по learning loop, а не XP.

**Предложение ступеней:**
- 0 Старт: первый grounded answer с источником;
- 1 Понимание: первый завершённый quiz;
- 2 Память: карточка вспомнена после интервала хотя бы в неделю;
- 3 Карта: закрыт graph gap;
- 4 Мастерство: course/concept graduation.

**Proposed change.** Добавить небольшой сервис или аккуратно изолированный блок в `app/gamification_service.py`, который считает/хранит `learner_stage`. Показывать компактной строкой на Mission Control. Transition state хранить в `app_kv`, чтобы unlock/toast messages были идемпотентны.

**Открытые вопросы перед реализацией:**
- Какое событие доказывает «remembered after a week» из `spaced_repetition`?
- Какое существующее событие доказывает «graph gap closed»?
- Stage 4 — course graduation, concept graduation или оба?

**Files:** сервис/модуль TBD, `app/ui/mission_control.py`, docs, tests.

**DoD:** stage виден и не конфликтует с XP-level; transition notification показывается один раз; restart/rerender не повторяет старые transition messages.

**Doc-sync:** `docs/user_guide.md`, новый раздел «Ступени петли обучения».

---

### Кандидат C3 — Слияние «зеркала» прогресса

**Статус: `proposed`; требует owner sign-off**

**Приоритет:** P2 · **Усилие:** среднее–большое

**Проблема.** Progress размазан по «Прогресс обучения», «Адаптивный план», weekly narrative и отдельной Streamlit page `app/ui/pages/3_Мой_прогресс.py`.

**Proposed change.** Один nav item «Прогресс» с фиксированным порядком секций: daily ritual → loop stage/streak → mastery/weak spots → сложные темы (после C1 discovery) → graph gaps → weekly narrative. Deep-links на adaptive plan должны работать как redirects/anchors, а не становиться мёртвыми views.

**Files:** `app/ui/dashboards.py`, `app/ui/dashboards_progress.py`, `app/ui/adaptive_plan_hub_layout.py`, `app/ui/adaptive_daily_plan_layout.py`, `app/ui/weekly_study_narrative_ui.py`, `app/ui/constants.py`, `app/ui/feature_registry.py`, `app/ui/pages/3_Мой_прогресс.py`.

**Pre-flight inventory:** e2e view-map, screenshot fixtures, resume-card links, Course Cockpit links, все hard-coded `Адаптивный план` view names.

**DoD:** один Progress surface содержит ordered sections; все existing adaptive-plan links попадают в полезное место; отдельная progress page либо merged, либо явно оставлена с документированной причиной.

**Doc-sync:** `docs/user_guide.md`; `docs/architecture.md`, если меняется navigation structure.

---

## Рекомендованный порядок реализации

1. ~~A1~~ — done in `680345d`.
2. A2 — следующий кандидат, но только после owner sign-off на Mission Control write-set.
3. B1 — независимый trust fix, можно до или после A2.
4. B2 и B3 — малые независимые cleanup packages.
5. C1 — сначала discovery; implementation только после settled data contracts.
6. C2 — после уточнения semantics/events; не блокируется C1 scoring.
7. C3 — последним, с owner sign-off и deep-link/e2e inventory.

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`../next/roadmap_recommendations_2026-06-11.md`](roadmap_recommendations_2026-06-11.md) — соседний recommendations-регистр
- hometutor: `docs/user_guide.md`, `docs/conventions_architecture.md`, `docs/api_reference.md`, `CLAUDE.md`
