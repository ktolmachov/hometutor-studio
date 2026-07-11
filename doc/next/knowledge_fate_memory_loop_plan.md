# Knowledge Fate — Memory Loop Closure Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения — `backlog_registry.yaml`
этим документом не меняется, промоушен волн/пакетов решает владелец.
Owner: product / learning experience
Source: эволюционный разбор hometutor «Судьба одного знания» (2026-07-11), формат —
[`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md).
Полный читаемый разбор:
[`../presentations/evolutionary_analyses/01_knowledge_fate.html`](../presentations/evolutionary_analyses/01_knowledge_fate.html)
(тот же контент опубликован как HTML-артефакт сессии).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- [`learning_loop_simplicity_plan.md`](learning_loop_simplicity_plan.md) — соседний план из предыдущего
  разбора той же серии («Судьба одного знания» — разбор №1, «Петля обучения» — разбор из 2026-07-10;
  оба про одну петлю, но с разных сторон: тот про UI/фокус экрана, этот — про сохранность памяти)
- hometutor: `docs/user_guide.md`, `docs/conventions_architecture.md`, `docs/api_reference.md`, `CLAUDE.md`

## Как использовать этот документ

Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог
промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной.
Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted
tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне
согласованного write-set. Все evidence-ссылки проверены на `hometutor@bde34e4` (`147`).

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`.

## Суть разбора

Суть петли памяти: **понимание → след → возврат**. Знание, не оставившее следа, для
системы не существует. Аудит показал: «что я знаю» записано в пяти независимых
хранилищах (`quiz_mastery`, `spaced_repetition`, `profile.mastery_vector`, карточный
SM-2, `tutor_sessions.mastery_level`), но только квиз-события доходят до концептной
памяти через honest provenance-gate. Диалог с тьютором и чтение конспекта — полностью
бесследны; повтор карточки следит только за самой карточкой, не за концептом.

---

## Волна-кандидат A: `wave-memory-loop-closure` (P0)

**North star (кандидат):** каждое учебное событие — квиз, повтор карточки, диалог с
тьютором — оставляет проверяемый след в памяти системы; студент никогда не видит
«чистый лист» после часа реальной работы.

**Kill switch (кандидат):** если exposure-слой (A2) начинает засорять граф/SSR ложными
сигналами «освоено» (mastery меняется от exposure-события хотя бы один раз в проде),
немедленно откатить запись exposure и вернуться к чисто quiz-driven mastery — provenance-
gate не подлежит компромиссу.

### Кандидат A1 — Замкнуть ревью карточки в концептную память

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое (инфраструктура уже существует)

**Проблема.** `review_flashcard()` обновляет расписание самой карточки, лог ревью и
недельный счётчик, но никогда не трогает концептную память. Студент три раза подряд
проваливает карточку по теме X — граф знаний остаётся зелёным, Smart Study Router не
узнаёт о проблеме.

**Evidence:**
- `app/flashcard_service.py:798-870` (`review_flashcard`) — вызывает
  `update_flashcard_sr`, `record_flashcard_review_log`, `increment_weekly_progress`,
  `append_flashcard_rating_history`; ни одного вызова `spaced_repetition.*` или
  `quiz_adaptive.*`.
- `app/fact_source_binding.py:110-136` (`apply_quiz_outcome_to_learner_state`) — уже
  существующая единая точка записи в концептную память: provenance-gate +
  `record_quiz_score_for_spaced_repetition` + `update_mastery_after_score`. Принимает
  `concept`, `score`, `level`, `quiz_result_id` — рассчитан на квиз-провенанс, нужен
  новый тип события.
- `app/flashcards_tag_display.py:59-80` (`source_path_from_card`) и
  `app/flashcard_service.py:288-304` (`_course_card_tags`) — карточка уже несёт
  `source:`-тег документа, но не `concept:`-тег; концепт для проброса в единую точку
  сейчас негде взять напрямую.

**Proposed change:**
1. Добавить новый provenance-тип `flashcard_review` в `app/fact_source_binding.py`
   (рядом с `build_quiz_event_provenance`), не ослабляя сам gate.
2. `review_flashcard()` после успешного апдейта SR карточки пробрасывает `quality` →
   `score_01 = quality / 5` в `record_quiz_score_for_spaced_repetition(concept, score,
   provenance=...)`, где `concept` резолвится из тегов карточки.
3. Если у карточки нет резолвящегося концепта (старые карточки без `concept:`-тега) —
   пропустить запись в концептную память, не изобретать эвристику молча (честное
   отсутствие следа лучше ложного).

**Files:** `app/flashcard_service.py`, `app/fact_source_binding.py`,
`app/spaced_repetition.py` (если нужен explicit entry без quiz-specific полей),
targeted tests (`tests/test_flashcards_scheduling.py`,
`tests/test_flashcards_memory_signals.py`, guardrails/pipeline invariants при
необходимости).

**DoD:**
- Провал карточки с резолвящимся концептом обновляет `spaced_repetition` и
  `quiz_mastery` тем же путём, что и квиз.
- Карточка без `concept:`-тега не создаёт ложную запись — фиксируется тестом.
- Провенанс `flashcard_review` виден в трассировке (`get_last_mastery_provenance`).

**Doc-sync:** `docs/architecture.md` (если меняется диаграмма источников mastery),
`docs/conventions_architecture.md` (единая точка записи расширена).

**Dependencies:** нет — использует существующую инфраструктуру provenance-gate.

---

### Кандидат A2 — Exposure-след тьюторского ответа

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое–среднее (новый слой ниже gate, но узкий scope)

**Проблема.** После каждого tutor-ответа вызывается
`update_learner_model_after_interaction("local", "tutor", {}, ...)` с пустым outcome.
Единственный эффект ветки `"tutor"` — `cognitive_load -= 0.05`. Час диалога с тьютором
не оставляет для системы никакого следа о том, какие концепты обсуждались.

**Evidence:**
- `app/query_response_postprocessing.py:404-417` — вызов с `outcome={}`.
- `app/learner_model_service.py:504-536` (`update_learner_model_after_interaction`) —
  ветка `elif it == "tutor":` (строка 528-529) не делает ничего, кроме `cognitive_load`.
- Ветка `"quiz"` (строки 516-526) в той же функции — рабочий образец merge в
  `mastery_vector`, но она принадлежит выше provenance-gate (см. A1 про её отдельность
  от `quiz_mastery`/`spaced_repetition` — П5 разбора «пять зеркал»).

**Proposed change:**
1. Ввести отдельный, явно более слабый слой памяти — *exposure* (не mastery): «эти
   концепты встречались в ответе тьютора» без изменения `quiz_mastery` /
   `spaced_repetition` / provenance-gated mastery.
2. Источник концептов для exposure — уже resolved `ctx.metadata` /
   `tutor_decision.focus_topic` в `query_response_postprocessing.py` (тот же контекст,
   где сейчас формируется `outcome={}`).
3. Хранить exposure минимально — например compact per-concept "last_seen_at" в
   `app_kv`/новой узкой таблице, БЕЗ scoring/весов. Никакого влияния на SM-2 расписание.
4. В чате — одна честная строка: «Запомнил за тебя: N концептов» (первый видимый эффект
   для студента, без обещания «выучено»).

**Files:** `app/query_response_postprocessing.py`, `app/learner_model_service.py`
(новая функция exposure, отдельная от mastery-веток), возможно новый модуль
`app/learner_exposure.py` вместо разрастания `learner_model_service.py`,
`app/ui/tutor_chat_response_render.py` (строка в чате), targeted tests.

**DoD:**
- Tutor-ответ с известными концептами создаёт exposure-запись; provenance-gated mastery
  не меняется ни на йоту (regression test: exposure-путь не может писать в
  `quiz_mastery`/`spaced_repetition`).
- Студент видит подтверждение в чате после ответа.
- Kill switch волны проверяем: тест на «exposure никогда не апдейтит mastery».

**Doc-sync:** `docs/architecture.md` (новый слой памяти документируется рядом с
provenance-gate), `docs/user_guide.md` (что значит «запомнил» в чате).

**Dependencies:** независим от A1, можно вести параллельно.

---

## Волна-кандидат B: `wave-memory-loop-trust` (P1)

**North star (кандидат):** студент сохраняет любой момент понимания одним жестом и
видит одну честную очередь «что повторить», а не две конкурирующие цифры.

### Кандидат B1 — Кнопка «→ в карточку» из ответа тьютора

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** среднее

**Проблема.** `add_flashcard()` вызывается только из API-роутера
(`app/routers/flashcards.py:484`) — в UI нет ни одной кнопки, которая создаёт карточку
из ответа тьютора. Единственный текущий путь «карточка → тьютор» (flashcard handoff)
не работает в обратную сторону.

**Evidence:**
- `app/flashcard_handoff.py:76-175` (`build_flashcard_handoff_seed`) — образцовый,
  уже работающий путь «карточка → мгновенное объяснение тьютора»; использовать как
  зеркальный образец структуры данных (front/back/topic/source_path).
- `app/user_state_flashcards.py:475-496` (`add_flashcard`) — существующий backend-путь,
  никогда не вызываемый из `app/ui/*`.
- `app/flashcards_tag_display.py:59-80` (`source_path_from_card`) — уже умеет резолвить
  путь источника; для новой карточки из ответа тьютора нужен симметричный резолвер
  «источник ответа → `source:`-тег».

**Proposed change:**
1. Кнопка в рендере tutor-ответа (рядом с существующими CTA типа «Объясни проще»):
   «Сохранить как карточку».
2. `front` = вопрос студента (или сжатая формулировка), `back` = `teaching_summary` из
   ответа; `tags` включают `source:<путь источника ответа>` и новый `concept:<topic>`.
3. Использует существующий `add_flashcard()` — не создавать параллельный insert-путь.

**Files:** `app/ui/tutor_chat_response_render.py` или `app/ui/tutor_chat_actions.py`
(кнопка), `app/flashcard_service.py` (генератор тегов из ответа, если нужен helper),
targeted tests (`tests/test_navigation_visibility.py` если кнопка меняет feature
registry).

**DoD:** карточка, созданная из ответа тьютора, содержит `source:` и `concept:` теги;
видна в обычной колоде ревью; не ломает существующий flashcard_handoff в обратную
сторону.

**Doc-sync:** `docs/user_guide.md` (новый жест сохранения).

**Dependencies:** выигрывает от `concept:`-тега, вводимого этим же пакетом (B1), и от
A1 (общий провенанс-тип для ревью карточек с `concept:`-тегом).

---

### Кандидат B2 — Единая очередь «Повторить сегодня»

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое–среднее

**Проблема.** UI показывает два независимых числа «к повторению»: карточное
(`count_due_flashcards`) в Mission Control/чате и концептное (`count_due_reviews`) в
tutor chat/Telegram — под похожими подписями, без объяснения разницы.

**Evidence:**
- `app/ui/mission_control.py:132-138` (`_flashcards_due_count`) →
  `user_state.count_due_flashcards()`.
- `app/ui/tutor_chat_render.py:336` и `app/ui/tutor_chat_quiz.py:137` →
  `count_due_reviews()` из `app/spaced_repetition.py:216-237`.
- `app/spaced_repetition.py:358-377` (`due_reviews_summary_for_tutor`) — уже возвращает
  агрегат с preview list для концептов; аналогичного агрегата, объединяющего оба
  источника, нет.

**Proposed change:**
1. Один helper `get_unified_due_summary()`, который возвращает
   `{flashcards_due, concepts_due, total_due}` с явными подписями («карточек» /
   «тем без карточки»), а не одно слитное число, которое скрывает разницу источников.
2. Заменить прямые вызовы `count_due_flashcards()` / `count_due_reviews()` в UI-виджетах
   на этот helper.

**Files:** новый или существующий shared helper (кандидат: `app/spaced_repetition.py`
рядом с `due_reviews_summary_for_tutor`), `app/ui/mission_control.py`,
`app/ui/tutor_chat_render.py`, `app/ui/tutor_chat_quiz.py`, `app/due_queue_display.py`,
targeted tests.

**DoD:** все поверхности UI показывают одну и ту же пару чисел с одинаковыми подписями;
regression test фиксирует единый источник.

**Doc-sync:** `docs/user_guide.md`, раздел про повторение.

**Dependencies:** независим от A1/A2/B1, можно вести параллельно.

---

## Волна-кандидат C: `wave-memory-loop-mirror` (P2)

**North star (кандидат):** одна точка истины «что я знаю» с производными
представлениями; возврат из карточки ведёт в точное место лекции, а не просто в файл.

### Кандидат C1 — `mastery_vector` как derived view

**Статус:** `proposed`, требует discovery по миграции существующих снапшотов

**Приоритет:** P2 · **Усилие:** среднее

**Проблема.** `profile.mastery_vector` — третья независимая копия «что я знаю» рядом с
`quiz_mastery` и `spaced_repetition`; расхождения между копиями — то же семейство
багов, что и «76 vs 89 концептов» из прошлого разбора (`learning_loop_simplicity_plan.md`,
кандидат B1).

**Evidence:**
- `app/knowledge_graph.py:862-891` (`get_mastery_vector`) — уже derived от
  `quiz_adaptive.get_all_mastery_levels()`, независимый расчёт.
- `app/learner_model_service.py:171-201` (`_filter_mastery_vector_for_active_index`) —
  отдельная фильтрация той же информации в профиле.

**Discovery перед реализацией:**
1. Сверить, какие UI-поверхности (радар, adaptive plan) читают `profile.mastery_vector`
   напрямую и не переживут ли замену derived view без визуальной регрессии.
2. Решить миграцию существующих сохранённых профилей (`profile.model_dump`) — held data
   vs recompute on read.

**Files:** `app/learner_model_service.py`, `app/knowledge_graph.py`,
`app/visualization_service.py`, targeted tests.

**DoD:** один источник правды для mastery; `mastery_vector` в профиле либо удалён, либо
явно помечен как cached derived snapshot с TTL.

**Doc-sync:** `docs/architecture.md`.

---

### Кандидат C2 — Section-anchor у карточек + коэффициент следа на дашборде

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** среднее

**Проблема/возможность.** Карточка знает `source_path`, но не конкретное место в
материале (раздел·строку·таймкод) — возврат из проваленной карточки в лекцию менее
точен, чем возврат из провала квиза. Отдельно: «коэффициент следа» (доля учебных
событий, оставляющих след — метрика из самого разбора) нигде не визуализирован.

**Evidence:**
- `app/flashcards_tag_display.py:59-80` (`source_path_from_card`) — резолвит только
  путь файла, не anchor внутри него.
- Section Anchor Index уже существует для другого сценария —
  `app/section_index.py` (используется квиз/тьютор-путём для точного возврата;
  сверить точный контракт перед реализацией, не дублировать).

**Proposed change:**
1. При генерации карточки из документа/квиза сохранять section-anchor (если источник
   генерации уже его знает) в отдельном поле, не перегружая `tags`.
2. Добавить на дашборд метрик (`app/routers/metrics.py`,
   `app/educational_metrics_service.py`) панель «коэффициент следа» по типам событий
   (квиз/ревью/диалог/чтение) — источник данных: `agent_runs`/`chat_sessions` против
   `spaced_repetition`/review-лога за период, без новой телеметрии.

**Files:** `app/flashcard_service.py`, `app/section_index.py` (сверка контракта),
`app/educational_metrics_service.py`, `app/routers/metrics.py`, targeted tests.

**DoD:** карточка из документа с известным anchor возвращает точнее файла; дашборд
показывает коэффициент следа по 4 типам событий за выбранный период.

**Doc-sync:** `docs/api_reference.md` (если появляется endpoint), `docs/user_guide.md`.

**Dependencies:** выигрывает от A1/A2 (иначе «диалог»/«ревью» коэффициент останется
на нуле не из-за отсутствия метрики, а из-за реального разрыва).

---

## Рекомендованный порядок реализации

1. **A1** — замкнуть ревью карточки; малый и самодостаточный, использует готовую
   инфраструктуру provenance-gate.
2. **A2** — exposure-след тьютора; независим от A1, но вместе они закрывают оба
   бесследных события из боли-якоря.
3. **B2** — единая очередь; независим, можно вести параллельно с A1/A2.
4. **B1** — кнопка «→ в карточку»; логически проще после A1 (общий провенанс-тип для
   ревью карточек с `concept:`-тегом), но не блокируется технически.
5. **C1** — derived `mastery_vector`; требует discovery по миграции, не блокирует A/B.
6. **C2** — section-anchor + коэффициент следа на дашборде; ставить последним, чтобы
   метрика измеряла эффект уже выполненных A1/A2, а не пустоту.

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../presentations/evolutionary_analyses/README.md`](../presentations/evolutionary_analyses/README.md) — индекс серии разборов
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`learning_loop_simplicity_plan.md`](learning_loop_simplicity_plan.md) — соседний план из разбора №0 (UI/фокус)
- hometutor: `docs/user_guide.md`, `docs/conventions_architecture.md`, `docs/api_reference.md`, `CLAUDE.md`
