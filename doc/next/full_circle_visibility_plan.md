# Full Circle — Visibility Plan

**Дата:** 2026-07-12 · **База проверки:** hometutor HEAD `c374892` «194» + рабочее дерево
**Источник:** финальный эволюционный разбор №10 «Кольцо замкнулось, но беззвучно»
(`../presentations/evolutionary_analyses/10_full_circle.html`,
артефакт https://claude.ai/code/artifact/b8630747-b686-4d69-85ae-18df8c9e65f6)

Этот план — runtime-handoff для `D:\Projects\hometutor`. Он не требует внешних команд и не блокирует реализацию ожиданием статусов из других репозиториев.
Перед кодом всё равно сверить фактический runtime-код: detail-планы серии могут
отставать от HEAD.

## Контекст: что уже сделано и не входит в этот план

Коммиты 186–191 (2026-07-12) закрыли оба хода метаразбора №8:

- **След:** tutor outcome непустой (`query_response_postprocessing.py:415-430`),
  flashcard review пишет learner-state, канонический резолвер концептов
  (`fact_source_binding.py`), `tests/test_memory_loop_closure.py`.
- **Честность:** circuit breaker подключён к живому трафику
  (`llm_resilience.py:168-171, :191, :209`), быстрый честный отказ,
  preflight-подсказки cloud/local (`app/ui/preflight.py:26-52`), provider errors
  в `query_service.py`.
- Вне серии: витрина HF Spaces (`deploy/hf-spaces/`).

Главный факт синтеза: среди открытых дыр теперь преобладают **видимость и двери**.
Появление нового пайплайна, нового хранилища или LLM-вызова в P0 = kill switch.

---

## wave-full-circle-pulse (P0 — два хода)

### A1. «Пульс петли» в tutor chat

- **Problem:** самый важный эффект серии не виден студенту. Tutor уже пишет
  learner outcome, но экран не отвечает на вопрос «что изменилось после этой
  сессии?» без debug-панели.
- **Evidence:** `update_outcome` собирается в `query_response_postprocessing.py:415-424`
  и передаётся в learner model. Но UI tutor history берёт metadata из
  `assistant_meta["tutor"]`: `query_rag_assembly.build_tutor_payloads()` собирает
  `assistant_meta`, а `app/ui/tutor_chat_session.py` передаёт `msg.metadata["tutor"]`
  как `tutor_meta` в `render_tutor_structured_response()`. Простая запись в
  `ctx.metadata` сама по себе до renderer не дойдёт.
- **Proposed:** добавить маленький learner trace summary и провести его полным
  путём:
  `update_outcome` → `ctx.metadata["learner_trace"]` →
  `assistant_meta["tutor"]["learner_trace"]` → `tutor_meta` в history message →
  видимая строка в tutor chat.
- **UI copy:** короткая строка рядом с tutor visibility area, например
  `След записан: <concept> · источников: N`. LLM source добавлять в эту строку
  только если source summary уже доступен в `tutor_meta`; не строить новый
  provider pipeline ради бейджа.
- **Files:** `app/query_response_postprocessing.py`, `app/query_rag_assembly.py`,
  `app/ui/tutor_chat_response_render.py`; опционально `app/ui/tutor_chat_render.py`
  или `app/ui/helpers.py` для маленького formatter/renderer.
- **Tests:** `tests/test_memory_loop_closure.py` должен проверить metadata trace;
  добавить/расширить targeted UI/assembly test, который доказывает, что
  `assistant_meta["tutor"]["learner_trace"]` появляется и renderer может его
  прочитать.
- **DoD:** после ответа тьютора trace visible без debug; запись только
  best-effort и не ломает ответ при ошибке learner model; Quick Answer не
  регрессирует.
- **Закрывает:** зеркальную часть №1 и visibility-бейдж №5 одним runtime-ходом.

### A2. Одно surface-число «Повторить сегодня»

- **Problem:** студент видит несколько разных «повторить»: flashcards due и
  KG/SM-2 due могут выглядеть как конкурирующие двери возврата в петлю.
- **Evidence:** home/tutor smart-study уже принимает оба значения через
  `build_smart_study_recommendation(flashcard_due_n=…, sm2_due_n=…)`; данные
  расписания не надо менять.
- **Proposed:** унифицировать surface-представление: одно число и одна подпись
  «Повторить сегодня» на ключевых поверхностях. На первом шаге это может быть
  честная сумма двух очередей: `flashcard_due_n + sm2_due_n`, с подписью, что это
  две очереди повторения. Union допустим только если явно определён ключ
  дедупликации.
- **Navigation boundary:** не обещать «единую очередь», если реализация не вводит
  отдельный review-router. Кнопка может вести в приоритетную существующую очередь
  по текущей логике smart-study; это должно быть честно отражено в copy/test.
- **Files:** `app/ui/mission_control.py`, `app/ui/tutor_chat_response_render.py`,
  `app/ui/resume_cards_due.py` / `app/ui/resume_cards_smart_study.py`, только если
  там реально живёт surface-число.
- **DoD:** surface-число одинаково считается на home/tutor; copy не врёт про
  объединённую очередь; scheduling SM-2 и flashcards не меняется; targeted
  scheduling/UI tests зелёные.

## wave-full-circle-honesty-doors (P1)

- **B1. Честный hero (№2 A2):** `mission_control_first_session.py:217` — заменить
  безусловное «Первый обзор курса готовится…» на честный статус или CTA
  «Собрать обзор».
- **B2. Свежесть карты на Mission Control (№3 A1):** показать «карта отстаёт на
  N лекций» из уже вычисляемых величин; учесть, что `_compact_report` может
  отбрасывать `source_paths`.
- **B3. Дверь агента (№4 A1+A2):** `FeatureSpec` с
  `requires=("agent_enabled",)` и read-only router поверх agent runs. Делать
  строго после P0: автопилот бессмыслен, пока петля не видна.

## wave-full-circle-home (P2)

- **C1. «Своя комната»** — цветовые миры и фоны как слой присвоения после зеркала.
- **C2. One-pager лекции (№6 B1)** — единая страница лекции.
- **C3. Section-anchor карточек (№1 C2)** — усиливает возврат из карточки.
- **C4. Витрина:** закрепить демо-опыт HF Spaces (persistent volume или
  замороженный демо-аккаунт), если это всё ещё нужно владельцу.

---

## Метрики финала

1. **Видимый коэффициент следа** (quiz/review/tutor): 0/3 → 3/3; в данных уже 3/3.
2. Чисел «повторить» на ключевых поверхностях: несколько → 1 честное surface-число.
3. Вопрос-метрика: «что изменилось после этой сессии?» — ответ с экрана, без debug.
4. Цена сбоя LM Studio ~3 с уже достигнута кодом; P0 не должен ухудшать это.

## Рекомендованный runtime-порядок

A1 → A2 → B1 → B2 → B3 → C1 → C2 → C3 → C4.

P0 маленький по объёму, но не должен быть фальшиво упрощён: для A1 обязательна
проверка полного пути metadata до tutor UI, а для A2 — честная семантика числа и
навигации.

