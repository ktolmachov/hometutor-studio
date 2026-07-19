# One Calm Learning Route — план кандидатов (разбор №23 «Не меню режимов, а одна учебная нить»)

> **Источник:** эволюционный разбор №23
> ([`../presentations/evolutionary_analyses/23_one_calm_route.html`](../presentations/evolutionary_analyses/23_one_calm_route.html)),
> hometutor HEAD `9c4913c1d` «330», 2026-07-18 (ревизия 2026-07-19, независимый
> контр-аудит нашёл переоцененную причинность в первом варианте якоря — исправлено
> ниже). Боль-якорь подтверждена read-only прогоном на живом user-state и активном
> бандле: SSR → 97 due-карточек; сохранённый адаптивный план → gap `agent-harness`
> (mastery 0.44); KG day route → 6 новых frontier-концептов; `AGENT_ENABLED=false`.
>
> **Уточнение якоря после контр-аудита.** Изолированный прогон с усечённым входом
> (только `flashcard_due_n=0, sm2_due_n=0` + weak concept) даёт `mastery_stale` →
> «вернуться к `TopicB`» — фикстуре тестов studio из `quiz_mastery` (диагноз №22).
> Но прогон с ПОЛНЫМ контекстом, который реально собирает
> `gather_smart_study_router_session_context()` (`app/ui/resume_cards_smart_study.py:334`),
> показывает другое: живая база сейчас содержит непустой `tutor_learning_resume`
> с настоящей темой (`app/user_state_tutor.py:71`), а каскад ставит `tutor_resume`
> выше `mastery_stale` (`app/smart_study_scoring.py:162-164`) — значит primary
> сегодня «Продолжить чат», не `TopicB`. Это **два независимых дефекта**, не один:
> (A) home SSR не получает сохранённый `plan_primary_block` (`mission_control.py:289`)
> и текущий scorer разрешает plan block только на `surface="adaptive_plan"`
> (`smart_study_scoring.py:90,142-160`);
> (B) `get_weak_concepts()` подаётся в SSR без фильтра по активному графу
> (`mission_control.py:288`, `resume_cards_smart_study.py:344,379`), хотя нужный
> фильтр `weak_concepts_for_kg()` уже существует (`app/learner_state_scope.py:141-152`)
> и просто не подключён на этом пути. Дефект B реален и воспроизводится
> детерминированно в изоляции; он становится видимым primary конкретно тогда,
> когда tutor resume устареет (переиндексация меняет `index_version`,
> `resume_cards_smart_study.py:296-314`) или в новой сессии без resume/reading —
> не «через 97 карточек», как утверждала первая версия.
>
> **Статус:** ✅ A1 shipped 2026-07-19; ✅ A2 shipped 2026-07-19; B1–B4/C1–C2 — кандидаты. НЕ записи `backlog_registry.yaml` — промоут только решением
> владельца.
>
> **North star:** `Calm Start Rate` — доля сессий, где студент за ≤60 секунд начинает
> содержательное действие через primary или одну мягкую альтернативу, не открывая
> полный список режимов и не меняя направление больше одного раза. Сначала 7-дневный
> baseline; критерий эффекта P0 — +20 п.п. при неизменной или лучшей доле завершения
> первого шага.
>
> **Общий kill switch P0:** потребовались новая БД/схема, новый агентный pipeline или
> LLM-арбитр для готовых числовых сигналов — стоп. Появился новый view/режим «Умный
> маршрут» — стоп: оболочка ошибочно стала ещё одной дверью. Разные поверхности после
> P0 всё ещё показывают разные primary — работа не завершена.

---

## Wave `wave-one-route-core` (P0)

### A1. «Одна правда маршрута»: SSR становится канонической Route Policy

- **Problem.** Mission Control, Adaptive Plan и Knowledge Graph имеют собственные
  правдоподобные представления «что делать сегодня». Home SSR не получает primary
  plan block; Adaptive Plan отдельно объявляет следующий шаг и отдельно строит SSR;
  KG independently выбирает шесть day-route stops. Один hero на главной уже сделан,
  но единого арбитра между советчиками нет.
- **Evidence.**
  - `app/ui/mission_control.py:267-297` — `surface="home"`, при этом
    `plan_primary_block=None`;
  - `app/smart_study_scoring.py:90,142-160` — `plan_first` сейчас равен
    `surface == "adaptive_plan" and plan_block is not None`; pure-прогон с
    `surface="home"` и непустым `plan_primary_block` даёт `safe_default`, а не
    `plan_block_tutor`, то есть дефект A состоит из двух частей: missing input +
    surface gate;
  - `app/smart_study_recommendation.py:337-378` — один детерминированный каскад
    `cards_due → sm2_due → quiz_failed → adaptive_plan → ...`;
  - `app/smart_study_scoring.py:70-220` — фактические CTA и педагогические причины;
  - `app/ui/adaptive_plan_hub_layout.py:91-185` — свой «Следующий шаг», затем свой SSR
    с `plan_primary_block`;
  - `app/ui/knowledge_graph_d3_analysis.py:227-293,386-444` — independent worth и
    `select_day_route(k=6)`;
  - `app/ui/mission_control.py:288` и `app/ui/resume_cards_smart_study.py:344,379` —
    первый weak-концепт из `quiz_adaptive.get_weak_concepts()` попадает в SSR без
    фильтра по активному графу (дефект B);
  - `app/ui/resume_cards_smart_study.py:126,139` — live metrics/debug snapshot
    используют тот же raw `get_weak_concepts()`; это не обязательно меняет primary
    route, но может оставить off-graph `TopicB` в observability после фикса SSR;
  - `app/learner_state_scope.py:141-152` — `weak_concepts_for_kg(kg, ...)` уже
    пересекает weak concepts с `active_concept_ids(kg)`; это готовый фильтр для
    дефекта B, используемый рядом (mastery levels, due reviews), но не для weak
    concepts, подаваемых в SSR; честный fallback на пустом активном графе (line 149)
    — не новый баг, но означает, что фильтр не защищает при пустом графе;
  - живой прогон: SSR «Повторить» (97), plan `gap: agent-harness`, KG — 6 новых тем;
  - изолированный прогон weak-concept веткой (fc=0, sm2=0, без tutor/reading resume):
    home → `mastery_stale` «вернуться к TopicB» — воспроизводит дефект B
    детерминированно, но требует отсутствия более приоритетных сигналов, что НЕ
    текущее состояние живой базы (см. уточнение якоря выше);
  - прогон с полным контекстом на том же снимке: `has_tutor_resume=true` (реальная
    тема из БД) → primary `tutor_resume` «Продолжить чат», `TopicB` не появляется —
    подтверждает, что дефект B сегодня замаскирован дефектом-независимым сигналом
    tutor resume, а не отсутствует.
- **Proposed.**
  1. Сохранить публичный `SmartStudyRecommendation` как канонический route-decision
     contract, не вводить параллельный «универсальный режим». Добавить только данные,
     необходимые всем проекциям: `phase` (`understand|practice|check|retain|plan`),
     `topic_hint`, `origin`, `return_view` и stable `decision_id` из локальных сигналов.
  2. Собрать один pure context builder для home/plan/progress/KG. Он получает уже
     существующие сигналы: две due-очереди, quiz feedback, tutor/reading resume,
     first weak concept, сохранённый primary plan block. KG candidate передаётся только
     когда уже вычислен или когда намерение = `new_topic`; P0 не запускает тяжёлую
     перестройку графа ради hero.
  3. Правило приоритета остаётся детерминированным. Минимальная политика:
     retention debt → recovery after failed quiz → explicit intent → saved plan →
     active resume → graph/new-topic candidate → safe tutor. LLM не меняет выбор.
  4. Mission Control, Adaptive Plan, Progress и KG получают одну decision. Plan/KG
     могут показывать подробности своих данных, но primary CTA/тема/reason берутся из
     decision. Если canonical step отсутствует в графе, KG честно показывает
     «текущий шаг вне этой карты», а не строит конкурирующее «сегодня».
  5. Добавить дешёвые session-tape события `route_offered`, `route_selected`,
     `learning_action_started` в существующий JSONL-контракт. Payload — только ids,
     surface, hint/phase и latency; вопрос/текст запрещены как сейчас.
- **Files.**
  - `app/smart_study_router.py`, `app/smart_study_recommendation.py`,
    `app/smart_study_scoring.py`;
  - новый небольшой pure-модуль допустим только если facade разрастается:
    `app/smart_study_route_context.py`;
  - `app/ui/resume_cards.py` / текущие context helpers;
  - `app/ui/resume_cards_smart_study.py` (переключить оба SSR-вызова
    `get_weak_concepts()` на `weak_concepts_for_kg(kg, ...)` и синхронизировать
    live-metrics/debug weak source — дефект B);
  - `app/learner_state_scope.py` (переиспользуется как есть; менять только если
    fallback на пустом графе окажется недостаточным для home — обсудить отдельно,
    не расширять втихую);
  - `app/ui/mission_control.py`, `app/ui/adaptive_plan_hub_layout.py`,
    `app/ui/dashboards_progress.py`, KG view/presentation module, использующий
    `day_route`;
  - `app/session_tape.py`.
- **DoD.** (раздельно по дефектам — не один общий пункт)
  - один snapshot сигналов даёт один `primary_nav`, `topic_hint` и `reason` на home,
    plan, progress и KG;
  - fixture живой боли: 97 due + plan gap + 6 frontier → primary «Повторить», plan/KG
    показывают тот же active route, остальные кандидаты — не competing hero;
  - **Дефект A** (`plan_primary_block=None` + `surface=="adaptive_plan"` gate):
    без due, при сохранённом actionable plan → home и plan выбирают один и тот же
    plan step. Regression test строит ctx с пустыми due-очередями и непустым
    `plan_primary_block`, ожидает `primary_nav="plan_block_tutor"` на
    surface `"home"`. Фикс должен покрыть обе причины: home получает block, а
    scorer/policy явно разрешает plan branch на home в рамках канонического route
    contract, а не молча падает в `safe_default`;
  - **Дефект B** (weak concept без фильтра по графу): weak-концепт, отсутствующий
    в `active_concept_ids(kg)`, никогда не становится `first_weak_concept` для
    SSR — БЕЗУСЛОВНО, не «при наличии более сильного сигнала» (более сильный
    сигнал и сегодня обычно выигрывает в каскаде; условие было бы тавтологией).
    Regression test: fixture concept вне активного графа + пустые due + пустой
    tutor/reading resume → primary НЕ ссылается на этот concept (либо
    `safe_default`, либо следующий валидный weak concept из отфильтрованного
    списка). Реализуется заменой источника на `weak_concepts_for_kg(kg, ...)`,
    не эвристикой внутри Route Policy; live-metrics/debug snapshot не должны
    продолжать показывать off-graph concept как `weak_top`;
  - `new_topic` выбирает KG candidate только при отсутствии более сильного recovery
    debt или после явного override;
  - decision строится без LLM и без новых writes; session-tape не содержит текста;
  - targeted: `tests/test_mission_control_progressive.py`,
    `tests/test_mission_control_navigation.py`, `tests/test_adaptive_plan_ui_contract.py`,
    `tests/test_knowledge_graph_d3_section.py`, новые pure policy tests, тесты
    `session_tape` — зелёные.
- **North star contribution.** Убирает необходимость сравнивать три «сегодня»;
  обеспечивает единый numerator для Calm Start Rate.
- **Kill switch.** Нужна новая persistence-схема или KG payload строится на каждом
  рендере home только ради рекомендации — стоп; KG остаётся проекцией до дешёвого
  кандидата. Переименование всех SSR-модулей/контрактов — стоп: это не цель P0.
- **Effort.** 2–3 дня. **Priority.** P0. **Dependencies.** нет жёстких; параллельный
  трек — изоляция тестов №22 (`progress_mirror_plan.md` P0-2): Route Policy не чинит
  грязные данные, но пока изоляция не отгружена, фильтр по известным cid (см. DoD) —
  единственная защита hero от фикстур.
- **Doc-sync.** `docs/user_guide.md` (единый следующий шаг), `docs/architecture.md`
  или `docs/technical_specification.md` (Route Policy и проекции).

### A2. «Намерение вместо режима»: один shell решения и быстрый выход

- **Problem.** Intent-язык уже существует, но разнесён по Tutor и SSR cards. На
  главной один hero, однако альтернативы/режимы остаются названиями инструментов;
  полностью раскрыть семь намерений сразу означало бы построить новое меню.
- **Evidence.**
  - `app/ui/tutor_chat_header.py:51-79` — «Объясни проще», «Дай пример», «Проверь
    меня», «Следующий шаг» уже обещаны как единый поток;
  - `app/ui/tutor_chat_render.py:354-392` — action panel уже содержит «Дай задачу на
    применение» и «Покажи связь с практикой»;
  - `app/ui/adaptive_plan_card.py:69-114` — рабочие handlers для sources,
    `tutor_simpler`, quiz, progress, flashcard create, topics;
  - `app/ui/smart_study_next_step_card.py:37-218` — primary, reason, secondaries,
    feedback и what-if preview уже реализованы;
  - `app/ui/main.py:302-328` — ручной full command access уже спрятан в «Ещё».
- **Proposed.**
  1. Сделать один `render_learning_route_decision(...)` (эволюция текущей SSR card),
     используемый на всех учебных поверхностях: один primary; всегда видимая одна
     строка «почему»; максимум две контекстные альтернативы; ссылки «Почему именно
     это» и «Сменить направление».
  2. Палитра «Сменить направление» содержит семь пользовательских намерений:
     `не понял`, `объясни проще`, `хочу практику`, `проверь меня`, `помоги запомнить`,
     `составь план`, `что дальше`. Они мапятся на существующие handlers/prompt builders;
     названия режимов показываются только как результат («откроется короткая проверка»),
     не как исходный выбор.
  3. По умолчанию палитра закрыта. Две alternatives выбираются контекстно: после
     ошибки — «проще»/«практика»; при due — «5 минут»/«новая тема»; после ответа —
     «проверь»/«запомнить».
  4. Добавить эпизодические preferences без новой схемы: budget 5/15/25 минут и
     `gentle` через session state и существующую SSR steering preference. Persistence
     — только если уже поддерживается user-state helper; P0 не расширяет DB.
  5. Ручной контроль не удалять: четыре destination и «Ещё · все разделы» остаются
     постоянным escape hatch; в route shell есть «Вручную»/«Закончить».
  6. Agent presence: подпись «Навигатор предлагает» + reason. Tool trace и raw policy
     только в existing details/debug tier. Никакой отдельной новой avatar-панели.
- **Files.** `app/ui/smart_study_next_step_card.py`, `app/ui/mission_control.py`,
  `app/ui/adaptive_plan_card.py`, `app/ui/tutor_chat_render.py`, при необходимости
  маленький UI-only mapping `app/ui/learning_intents.py`, `app/session_tape.py`.
- **DoD.**
  - на каждом route shell ровно один primary и ≤2 видимых alternatives;
  - семь intents доступны за «Сменить направление», но не занимают первый экран;
  - каждый intent сохраняет `topic_hint`, origin/return point и ведёт в существующий
    executor без пустого повторного ввода;
  - «Вручную» и «Закончить» доступны всегда; нет скрытого write-action;
  - screen-reader labels описывают действие, не внутренний mode id;
  - session-tape позволяет вычислить ≤60 sec, mode-list opened и direction changes;
  - targeted: `tests/test_mission_control_progressive.py`,
    `tests/test_mission_control_navigation.py`, `tests/test_tutor_chat_ui_contract.py`,
    `tests/test_global_navigation.py`, `tests/test_navigation_visibility.py`; добавить
    pure mapping tests для 7 intents.
- **North star contribution.** Снижает число обязательных mode-решений до нуля и
  измеряет спокойный старт.
- **Kill switch.** На первом экране одновременно видно >2 alternatives или семь intent
  buttons — стоп. Новый intent требует дублировать prompt text вне `app/prompts/` —
  стоп; использовать builders/semantic action ids.
- **Effort.** 2–3 дня. **Priority.** P0. **Dependencies.** A1 contract.
- **Doc-sync.** `docs/user_guide.md`, `docs/quickstart.md`.

---

## Wave `wave-one-route-continuity` (P1)

### B1. Checkpoint после каждого результата

- **Problem.** Переходы есть, но вызываются разными локальными панелями; завершение
  шага не гарантирует повторный canonical decision.
- **Evidence.** `app/ui/tutor_chat_session.py:439-468` уже имеет «Продолжить 1 шаг» /
  «Готово на сегодня»; `app/ui/continuity_bridge.py:495-498` формирует next-step copy;
  flashcard→tutor handoff уже сохраняет контекст.
- **Proposed.** Единый checkpoint-компонент после tutor micro-step, quiz evaluation и
  review batch: «продолжить предложенное / сменить направление / закончить». Он
  повторно вызывает A1 с обновлёнными сигналами и сохраняет origin/return point.
- **Files.** `app/ui/tutor_chat_session.py`, quiz result UI, flashcards review summary,
  `app/ui/continuity_bridge.py`, route UI component.
- **DoD.** Три golden flows `answer→check`, `quiz fail→explain→retry`,
  `review→plan/finish` проходят без ручного поиска раздела; back/finish не теряют
  контекст. Targeted tutor/quiz/flashcard handoff tests зелёные.
- **North star.** Увеличивает долю завершённых первых шагов и последовательных вторых.
- **Kill switch.** Checkpoint начинает сам запускать следующий LLM/quiz без click —
  стоп.
- **Effort.** 2 дня. **Priority.** P1. **Dependencies.** A1–A2.

### B2. Учебный компас как единая строка состояния

- **Problem.** Студент видит названия разделов, но не всегда понимает фазу учебной
  работы и точку возврата.
- **Proposed.** Над route shell: `цель · фаза · бюджет · возврат`, например
  «Понять agent-harness · объяснение · 9 мин осталось · затем короткая проверка».
  Данные берутся из goal snapshot, route phase, budget session state и return point.
- **Files.** route UI component, `app/ui/global_navigation.py` только если нужен
  компактный slot, tutor/quiz/flashcard shells.
- **DoD.** Одинаковая строка на home, tutor, quiz, flashcards и plan; ни одного raw
  agent/mode id; при отсутствии данных честное сокращение, не synthetic default.
- **North star.** Снижает direction changes и early exits.
- **Kill switch.** Компас превращается во второй dashboard с метриками — стоп; одна
  строка и один progress indicator максимум.
- **Effort.** 1–2 дня. **Priority.** P1. **Dependencies.** A1.

### B3. Безопасный автопилот одной сессии

- **Problem.** Ручной выбор каждого перехода утомляет, но навязанный agent-loop лишает
  контроля.
- **Proposed.** Opt-in budget 5/15/25 минут. Route Policy предлагает цепочку, но
  фактически выполняет только один шаг до checkpoint. Всегда видны «Пауза», «Вручную»,
  «Готово». Write-actions (save cards, record optional plan changes) требуют явного
  подтверждения; quiz attempts/reviews записываются только как прямое действие
  студента по существующим контрактам.
- **Files.** route session-state helper, checkpoint component, existing executor UIs.
- **DoD.** Тайм-бюджет уменьшается по завершённым шагам; refresh/resume не запускает
  действие повторно; stop работает на любой фазе; нет нового background worker.
- **North star.** Guardrail completion первого шага не падает; median direction changes
  снижается.
- **Kill switch.** Нужен scheduler/background agent или новая persistence-схема —
  отложить; P1 остаётся foreground/checkpoint flow.
- **Effort.** 2–3 дня. **Priority.** P1. **Dependencies.** B1.

### B4. Агент из отдельной двери — в нужный момент маршрута

- **Problem.** Backend-агент умеет собирать read-only инструменты, но UI оформляет его
  отдельным view; по умолчанию gate выключен. Это одновременно слишком невидимо для
  доверия и слишком похоже на ещё один режим при включении.
- **Evidence.** `config.env:81-82`; `app/ui/feature_registry.py:96-107`;
  `app/ui/main.py:451-526`; `app/agent/tool_registry.py:1-18,129-144`.
- **Proposed.** Убрать agent tile/view из learner-primary IA (manual/debug access можно
  сохранить). Route Policy вызывает agent loop только для composition cases:
  «собери сессию по теме», «найди gap и дай practice», «свяжи консpekt+graph+quiz».
  Простые intents идут напрямую в existing executors. В UI видны reason и итоговый
  plan; tool trace — раскрытие.
- **Files.** `app/ui/feature_registry.py`, `app/ui/mission_control.py`, `app/ui/main.py`,
  agent entry helper; backend contracts не переписывать.
- **DoD.** При `AGENT_ENABLED=false` route shell остаётся полноценным; при true сложный
  composition case использует agent, простой «объясни проще» — нет; ручной fallback
  доступен; agent не сохраняет cards без approval.
- **North star.** Agent enablement не является условием спокойного старта.
- **Kill switch.** Для P1 требуется менять agent FSM/tool registry — стоп; задача только
  про размещение и dispatch.
- **Effort.** 1–2 дня. **Priority.** P1. **Dependencies.** A1–A2.

---

## Wave `wave-one-route-learning` (P2)

### C1. Калибровка Route Policy по наблюдаемому поведению

- **Problem.** Статический приоритет должен учиться на misroute feedback, но не
  становиться непрозрачным ranking-LLM.
- **Proposed.** Версионировать policy; анализировать `route_offered/selected/start`,
  cancel, direction change и SSR feedback. Изменения весов/порядка — только через
  offline replay fixtures + regression tests. ML hybrid остаётся optional tie-break,
  не новым источником правды.
- **Files.** SSR feedback/policy modules, analysis script под `scripts/`, tests.
- **DoD.** Есть baseline report по North star и разрезам hint/intent; policy change
  имеет before/after replay; rollback = config/policy version, без миграции данных.
- **Kill switch.** Оптимизация кликов снижает completion или объяснимость — rollback.
- **Effort.** волна. **Priority.** P2. **Dependencies.** 2–4 недели событий после P0.

### C2. Адаптивная глубина ручной кабины

- **Problem.** Tier-system существует, но раскрытие инструментов связано в основном с
  настройками, а не с доказанной потребностью студента.
- **Proposed.** Не менять уровни автоматически без согласия. Показывать contextual
  discovery после реального использования: «Вы часто меняете направление — закрепить
  Quiz в ручной кабине?»; любые изменения видимости подтверждаются пользователем и
  используют существующие UI preference helpers.
- **Files.** `app/ui_preferences.py`, control panel, route analytics projection.
- **DoD.** Нет silent UI mutation; можно undo; cold-user experience неизменен; tier и
  requirements invariants сохраняются.
- **Kill switch.** Нужен новый learner-stage store — отложить; использовать current
  preferences и локальные события.
- **Effort.** волна. **Priority.** P2. **Dependencies.** C1 data.

---

## Практический порядок внедрения (5–10 решений)

1. ✅ A1 — единый pure decision contract и общая fixture боли.
2. ✅ A1 — одинаковый primary на home/plan/progress/KG.
3. ✅ A1 — три session-tape события для baseline Calm Start Rate.
4. ✅ A2 — один reusable route shell с ≤2 alternatives.
5. ✅ A2 — закрытая palette семи намерений поверх готовых handlers.
6. B1 — checkpoint после tutor/quiz/review.
7. B2 — компактный учебный компас.
8. B3 — opt-in автопилот 5/15/25 минут.
9. B4 — agent dispatch для composition cases, не отдельная learner-дверь.
10. C1 — калибровка только после накопления baseline и offline replay.

## Явно НЕ делать

- не добавлять девятый mode tile «Умный маршрут»;
- не выводить семь intent-кнопок одновременно на первом экране;
- не заменять детерминированный SSR LLM-арбитром;
- не удалять ручную навигацию и expert/debug inspectability;
- не запускать следующий шаг, write-action или смену цели без checkpoint;
- не создавать новую БД/схему ради route state;
- не пересчитывать тяжёлый KG payload на каждом home render;
- не считать клик успехом без содержательного учебного события.

---

## Протокол верификации HTML-разбора (ревизия 2026-07-19)

Локальный сервер `python -m http.server` в `evolutionary_analyses/`, проверено
Browser-панелью на `9c4913c1d` «330»:

- `<meta charset="utf-8">` первой строкой — заголовок таба читается кириллицей
  (до фикса: `Ð Ð°Ð·Ð±Ð¾Ñ€ â„–23…`);
- `document.documentElement.scrollWidth === clientWidth` (`hasHScroll: false`) —
  горизонтального overflow нет на всю высоту документа (`docH≈10163px`);
- inline SVG-диаграмма (`.figure svg`, 5 `rect` + 14 `text`) растеризована через
  canvas с подстановкой вычисленных `var()`-цветов: 78331 закрашенных пикселей
  из 223600 (35%) — SVG рендерится, не пустой `1×1` (урок KG3D);
- `data-theme="light"` override поверх тёмного `prefers-color-scheme` даёт
  читаемый light-режим (визуально проверено скриншотом; токены `--paper`/`--ink`
  переключились);
- текст страницы (`get_page_text`) не содержит артефактов кодировки/незакрытых
  тегов в проверенной части документа.

Известное ограничение инструмента: `computer{action:"scroll"}` таймаутится на
этой странице (тайловый капчер) — обход через `document.body.style.transform`
для позиционирования нужного участка перед скриншотом. Полный скролл всей
страницы (все 8 секций подряд) в эту ревизию не переснят — проверены заголовок,
секция 1, диаграмма секции 2 и light-тема; секции 3–8 проверены текстовым
дампом (`get_page_text`), не визуально.
