# Эволюционные разборы («нескучные разборы»)

Готовые HTML-разборы по формату из
[`../evolutionary_analysis_guide.md`](../evolutionary_analysis_guide.md). Каждый —
самодостаточная страница (без внешних зависимостей, светлая/тёмная тема, inline
SVG-диаграммы). Формат подтверждён владельцем как эталонный после разбора
2026-07-10.

**Визуальный стиль зафиксирован (v1.0, 2026-07-12)** —
[`../notebook_deck_guide.md`](../notebook_deck_guide.md) /
[`../notebook_template.html`](../notebook_template.html). Палитра, типографика и
восемь секций там финальны; новый CSS с нуля не изобретать. Разборы №1–8
предшествуют фиксации и палитру не наследуют (исторический снимок, см.
guide §9) — начиная с №9 все разборы используют один и тот же локон.

## Карта покрытия серии

Срез на 2026-07-24 после добавления №28. Теги пересекаются: один разбор может входить в несколько
областей. «0» означает отсутствие **отдельного end-to-end разбора**, а не полное
отсутствие компонента в других работах.

| Область | Число разборов | Разборы / комментарий |
|---|---:|---|
| Граф, визуальная карта и игровой мир знаний | **6** | №3, №6, №15, №17, №18, №20 |
| Материал, контент и качество конспекта/лекции | 5 | №3, №13, №14, №19, №26 |
| Маршрут, навигация и следующий шаг | 5 | №2, №4, №10, №22, №23 |
| Память, план и прогресс | 5 | №1, №7, №10, №22, №23 |
| Надёжность, невидимая инфраструктура и архитектура | 5 | №5, №8, №12, №27, №28 (№27 — инженерный процесс; №28 — метаразбор итогов серии, отличие от №8/№10 указано в паспорте) |
| Курсы, каталог и обучение продукту | 3 | №16, №19, №21 |
| Оформление и внешняя витрина | 3 | №9, №11, №16 |
| Качество объяснения/лекционного обучения | 1 | №19 |
| Качество квизов как самостоятельного учебного инструмента | 2 | №24 (coverage by analysis/contract only: E1 only, E2 не выполнен — не путать с №25, где E2 выполнен и дал 0/15); №26 (E2 выполнен: 9/9 структурно валидных генераций на живом бандле) |
| Качество retrieval, цитат и ответа как учебного доказательства | 2 | №25 (E1, E2 0/15); №26 (groundedness как контракт синтеза курса) |
| **Мотивация, возврат после перерыва и долгосрочное удержание** | **0** | Progress/route затрагивают тему, но не проверяют возврат и retention end-to-end |

Карта — обязательный preflight перед выбором темы. Нулевая область получает
coverage-бонус, но не автоматический P0: всё равно нужна проверяемая боль. Для
области с четырьмя и более разборами новый выпуск допустим только с новой
пользовательской болью и явной строкой «чем отличается от №N». После добавления
разбора автор обновляет этот срез; мокапы №18 в счёт не входят.

**Здоровье серии.** Канонических разборов — 28; ещё 3 HTML-файла являются
мокапами №18. До №24 формулировка North star встречалась в 17 из 23 разборов, но единый
статус подключения метрик до сих пор не вёлся. Поэтому утверждение вроде
«11 метрик объявлены, 0 подключены» нельзя считать фактом без отдельного аудита.
№24 и №25 задают metric contracts, но их VLQR/SGAR baselines честно остаются `not measured`:
для №24 E2 не выполнялся; для №25 E2 дал 0/15 valid, но это gated feasibility result,
а не измеренный SGAR baseline.
№27 — первый инженерный (не продуктовый) разбор с E2-подтверждением после №12.
Для №26 North star имеет измеренный baseline 0%; для №27 baseline VLCR — `N/A`, поскольку
authoritative-прогонов ещё не было. №28 — метаразбор итогов серии («обзор с высоты пройденного пути»): ввёл North star всей серии —
**OVR (Outcome Validation Rate)** = разборы со статусом `validated`/`no-effect`/`regressed` ÷ все;
baseline честный **1/27 ≈ 3.7%** (только №26 с live TLRR 61.1%). Изначальный target
«≥6/28 ≈ 21%» был арифметически недостижим (волна P0-1 — ровно 5 кандидатов, из которых
№26 уже входил в baseline; максимум при идеальном исходе 5/28 ≈ 17.9%) — пойман
независимым аудитом 2026-07-24 и исправлен на **target 5/28 ≈ 17.9%**, статус
`wired-existing` (формула считаема, остаток до target — validation gap, не wiring gap).
**Обновление 2026-07-24 после P0-1/P0-2:** OVR пересчитан — **1/28 ≈ 3.6%**. Replay
№2/№19/№22/№23 дал только `mechanically-reverified` (regression-тесты зелёные, не
поведенческая проверка) и намеренно не увеличил числитель — увеличение OVR только за счёт
переклассификации статуса без живого прогона было бы ровно тем фиктивным прогрессом, который
эта метрика должна ловить. См. [`../../next/replay_artifacts_2026-07/replay_2026-07-24.md`](../../next/replay_artifacts_2026-07/replay_2026-07-24.md).
Для новых разборов статус
метрики обязателен по правилу `North star wired` из гайда.

| Центральный контроль | Текущий статус | Охват |
|---|---|---|
| Wiring-status North star | `mixed` | №1–23 не аудированы; №24 — `wire-in-P0`; №25 SGAR — `not measured` (E2 feasibility: 0/15 valid, но SGAR baseline не измерен); №26 TLRR — `wired / live-validated`, baseline **61.1%** (2026-07-23: live-replay + audit-fixes + grounded-alias refresh + verified_quiz unblock; `grounded_explanation ≡ evidence_span`; 102 теста); №27 VLCR — `wire-in-P0`, baseline `N/A` (0 authoritative-прогонов; знаменатель равен 0); №28 OVR — `wired-existing` (формула считаема, P0-1/P0-2 shipped 2026-07-24), текущее значение **1/28 ≈ 3.6%** (только №26 validated; №2/№19/№22/№23 — mechanically-reverified, не засчитаны) |
| Outcome после реализации | `mixed` | №1–23 не аудированы; №24/№25 — analyses provisional; №26 — implementation verified (2026-07-23: TLRR 61.1%, 11/18 full steps, 11/236 evidence-bound quiz rows; remaining 7 steps are content-side residuals: 4 без `label_mention`, 3 без discriminating selection); №27 — analysis complete (E2 executed, план v1.7), implementation ⬜; №28 — analysis complete (E2: живой пересчёт git/реестров 2026-07-24), **implementation P0-1/P0-2 shipped 2026-07-24, outcome unvalidated** (только №26 replay validated; P0-2 и остальные 4 replay — №2, №19, №22, №23 — ждут live-подтверждения — не «⬜», но и не «✅») |
| Точность причинности | `historical-partial` | детальный аудит ниже охватывает №1–15; №16–23, №27 требуют rolling audit |

№26 закрывает deterministic evidence-gate и contract wiring для связки №24/#25, но не
закрывает полностью VLQR (#24) и SGAR (#25) как самостоятельные quality baselines.

Новые выпуски не добавляются в `not-audited`: metric contract и outcome-status
фиксируются сразу. Исторический ledger обновляется отдельным аудитом, без
догадок по тексту HTML.

Сквозные классы причин ведутся отдельно в
[`cross_cutting_pains.md`](cross_cutting_pains.md). Новый разбор обязан указать
существующий `PAIN-*` либо обосновать новый класс.

## Как сделать новый разбор

1. Заполни промпт скриптом из этой же папки:

   ```bash
   python generate_analysis_prompt.py \
     --area "Качество квизов" \
     --coverage-area "Качество квизов как самостоятельного учебного инструмента" \
     --role "студент" \
     --action "проверяет понимание по своему материалу" \
     --reality-domain "в генерации, показе, оценке и влиянии квиза на mastery" \
     --tension "скорость ↔ педагогическая валидность" \
     --tension "разнообразие ↔ сравнимость" \
     --pain "<факт, проверенный по коду перед запуском>" \
     --learning-stage "6. Практика и квиз" \
     --outcome-signal "доля вопросов, проверяющих перенос, а не узнавание" \
     --cross-pain "PAIN-02: рубрика вне eval-цикла" \
     --pain-evidence "E2: живой прогон фиксированного корпуса" \
     --different-from "№19: здесь оценивается качество квиза end-to-end"
   ```

   Скрипт не вызывает LLM — он только собирает готовый промпт из проверенного
   шаблона. Сама «РЕАЛЬНОСТЬ» и «ВЕРДИКТЫ» требуют агента с доступом к коду.

2. Скопируй вывод в **новую** сессию агента — не смешивай с правкой кода в той
   же сессии (см. гайд, раздел «Когда это работает»).

3. Оформление разбора начинай с копии
   [`../notebook_template.html`](../notebook_template.html), не с CSS с нуля и не
   с копипаста прошлого файла — палитра и компоненты зафиксированы в
   [`../notebook_deck_guide.md`](../notebook_deck_guide.md).

4. Сохрани готовый HTML сюда же как `NN_slug.html`, добавь строку в таблицу
   ниже и обнови карту покрытия выше. Если разбор тянет за собой реализацию —
   actionable-план кладётся отдельно в [`../../next/`](../../next/) (гайд,
   раздел 4), не сюда.

Статусы не склеивать: `готов анализ`, `P0 shipped` и `outcome validated` — три
разных факта. После реализации повторить исходный боль-якорь и обновить outcome
как `shipped-unvalidated`, `validated`, `no-effect` или `regressed`.

## Разборы

| № | Область | Статус анализа | Файл | Detail-plan | Рантайм-прогресс (срез 2026-07-19) |
|---|---|---|---|---|---|
| 1 | Судьба одного знания (петля памяти) | готово (2026-07-11) | [`01_knowledge_fate.html`](01_knowledge_fate.html) | [`../../next/knowledge_fate_memory_loop_plan.md`](../../next/knowledge_fate_memory_loop_plan.md) | ✅ P0: canonical cid, `sessions_completed`/`interactions` разделены, provenance gate (`test_memory_loop_closure.py`, 11 тестов — 8 по петле + 3 LLM-resilience). B1 (P1, 2026-07-13): кнопка «📥 Сохранить как карточку» из ответа тьютора — замыкает петлю памяти в UI (`_render_save_tutor_answer_as_flashcard`, get-or-create колода «Из ответов тьютора», теги `concept:`/`source:`); тесты `test_tutor_save_card.py` |
| 2 | Первые 10 минут (онбординг, time-to-first-insight) | готово (2026-07-11) | [`02_first_ten_minutes.html`](02_first_ten_minutes.html) | [`../../next/first_ten_minutes_onboarding_plan.md`](../../next/first_ten_minutes_onboarding_plan.md) | ✅ P0 (2026-07-13, wave-onboarding-closure): A2 честный статус hero — «готовится/собирается» показывается только при реально идущем реиндексе + `enable_first_session_precompute`, иначе нейтральная подписка без ложного обещания (`mission_control_first_session.py`); A1 единый источник кандидатов — `list_course_candidates_from_index` выводит курсы из индексированных путей (demo/uploads/user), а не из жёсткого `data/docs` (`course_cache.py`, `ingestion_support.py`). `enable_first_session_precompute=true` по умолчанию (ранее opt-in=false; gate документирован, артефакт строится после реиндекса) |
| 3 | Материал как продукт (конспект, граф, таймкоды) | готово (2026-07-11) | [`03_material_as_product.html`](03_material_as_product.html) | [`../../next/material_as_product_quality_plan.md`](../../next/material_as_product_quality_plan.md) | ✅ P0 freshness+audit-tail; ✅ P1 B1/B2 passport+лестница; ✅ P2 C2 learner-language (+MC badge); ✅ P2 C1 «🕰 устарел» по `source_sha256`. Ранее: badges, Mermaid **14** типов |
| 4 | Агент как одна кнопка (Agent Coach → UI) | готово (2026-07-11) | [`04_agent_as_one_button.html`](04_agent_as_one_button.html) | [`../../next/agent_as_one_button_plan.md`](../../next/agent_as_one_button_plan.md) | ✅ FeatureSpec + tile + view + POST `/ask` c `query_mode:"agent"`. Gate `AGENT_ENABLED` проверен в feature_visible и navigation_visibility. Трассировка агента (scenario, tool calls) в ответе |
| 5 | Доверие под нагрузкой (провайдер, скорость, честность fallback) | готово (2026-07-11) | [`05_trust_under_load.html`](05_trust_under_load.html) | [`../../next/trust_under_load_provider_plan.md`](../../next/trust_under_load_provider_plan.md) | ✅ timeout propagation исправлен (llama-index 60s → 30s), soft timeout 15s через ThreadPoolExecutor, тест soft timeout |
| 6 | Инфографика: живая карта материала (спецвыпуск, вне очереди) | готово (2026-07-11) | [`06_infographics.html`](06_infographics.html) | [`../../next/infographics_living_map_plan.md`](../../next/infographics_living_map_plan.md) | ✅ velocity/sessions/interactions в stats-бар графа, единый `_enrich_stats_with_learner_velocity()` для `build_kg_payload` и `compute_kg_counters` |
| 7 | План обучения: стол, который забывает, где вы сидите | готово (2026-07-11) | [`07_learning_plan.html`](07_learning_plan.html) | [`../../next/learning_plan_single_source_plan.md`](../../next/learning_plan_single_source_plan.md) | ✅ C1 bridge: `learning_plan_context` обновляется при загрузке кэшированного плана |
| 8 | Невидимая половина (метаразбор серии: сильный ход к шедевру) | готово (2026-07-12) | [`08_invisible_half.html`](08_invisible_half.html) | [`../../next/invisible_half_closure_plan.md`](../../next/invisible_half_closure_plan.md) | ✅ P0: AGENT_ENABLED gate, tier/requirement split в навигации, stale view не пробивает requirement |
| 9 | Своя комната (цветовые схемы «миры» + фоны мирового уровня) | готово (2026-07-12) | [`09_color_worlds.html`](09_color_worlds.html) | [`../../next/color_worlds_theming_plan.md`](../../next/color_worlds_theming_plan.md) | ✅ A1: `:root` расширен (9→22 токена), литералы `.stApp`/`.hero`/`.chip`/`.home-dash-head-*`/`.flashcard-*` → `var(--)`. A2: `theme_presets.py` (5 миров, полные gradient-строки head). B1: `get_ui_theme()`/`set_ui_theme()`. B2: `inject_theme_overrides()` после auth. B3: вкладка «Оформление». C3: токены темы в flashcard iframe. ✅ `tests/test_theme_presets.py` (5), `test_ui_preferences.py` (+4 теста темы). |
| 10 | Кольцо замкнулось, но беззвучно (финал: синтез разборов №1–№9) | готово (2026-07-12) | [`10_full_circle.html`](10_full_circle.html) | [`../../next/full_circle_visibility_plan.md`](../../next/full_circle_visibility_plan.md) | ✅ A1: learner trace в tutor chat (`ctx.metadata` → `assistant_meta` → `tutor_meta` → visible string). A2: due badge `flashcard_due_n + sm2_due_n` в SSR banner «К повторению: N (сумма двух очередей)». |
| 11 | Витрина обещаний: сценарии против реальности | готово (2026-07-12) | [`11_usage_scenarios.html`](11_usage_scenarios.html) | [`../../next/usage_scenarios_refresh_plan.md`](../../next/usage_scenarios_refresh_plan.md) | ✅ P0 A1/A2: freshness stamp в `generate_demo_doc.py` + quickstart_demo; YAML `scenario_31`–`35` + PNG в studio/runtime `screenshots/final/`. ⬜ P1: пересъёмка 06/30 после Full Circle (кадры 12.07; gap stamp честный) |
| 12 | Архитектура и дизайн (первый инженерный: стены без сигнализации) | готово (2026-07-12) | [`12_architecture_design.html`](12_architecture_design.html) | [`../../next/architecture_guards_plan.md`](../../next/architecture_guards_plan.md) | ✅ P0: бюджет no-growth **33/155/1942/361** + waiver `app/prompts/_impl.py`; `tests/test_architecture_guards.py` + явный CI-шаг «Architecture regression guards»; `arch_regression_guards.py` → exit 0 |
| 13 | Аудио-подкасты: конспекты и части лекций в уши | готово (2026-07-13) | [`13_audio_podcasts.html`](13_audio_podcasts.html) | [`../../next/audio_podcasts_plan.md`](../../next/audio_podcasts_plan.md) | ✅ P0/A2 закрыты после критического аудита: sibling `.m4a` discovery + `st.audio(..., format="audio/mp4")` разделов, слушаемый плейлист, офлайн-извлечение аудио в PS-конвейере, «Выпуск в дорогу» (m4a + TOC). Закреплены фиксы blocker'ов: `extract_audio_to_m4a(str)`, path-safety для absolute path, исключение `end=None` из concat, регрессионные тесты + Windows CI `test-media-pipeline-audio`. |
| 14 | Качество конспектов (включая Живые): паспорт написан, продукт показывает галочку | готово (2026-07-13) | [`14_konspekt_quality.html`](14_konspekt_quality.html) | [`../../next/konspekt_quality_plan.md`](../../next/konspekt_quality_plan.md) | ✅ P0 A1/A2: `quality_rubric` + парсер таблицы + паспорт на topics/reader; `knowledge_status` + `open_question` в корзине/MC. ✅ P1 B1–B3 (тьютор CTA, novelty, noise-filter) + P2 C1–C3 (grades, smart_konspekt fate, факты↔интерпретации) |
| 15 | 3D граф знаний: карта, которая не знает цену своих узлов | готово (2026-07-13) | [`15_knowledge_graph_3d.html`](15_knowledge_graph_3d.html) | [`../../next/knowledge_graph_3d_plan.md`](../../next/knowledge_graph_3d_plan.md) | ✅ P0 A1/A2 worth+маршрут. ✅ P1 B1 offline 3D-зал + audit fixes: script-safe JSON, floors by sorted lesson id + dynamic grid, 2D/3D share server `day_route`, DOM text for stop list |
| 16 | Учебный курс по продукту (первый разбор типа «обучение»: продукт учит всему, кроме себя) | готово (2026-07-14) | [`16_beginner_course.html`](16_beginner_course.html) | учебный комплект: [`../../courses/hometutor_101/`](../../courses/hometutor_101/) | ✅ P0: 6 лекций + 6 конспектов (рубрика OK×6) + 6 видео-сценариев + слайд-дек + dogfood-README. ✅ P1: 5 экранов в витрине (`scenario_36` маршрут дня · `37` паспорт/статусы/счётчики · `38` Оформление) + 6 MP4 в `videos/` (silent Ken Burns). ⬜ P2 (решение владельца): дверь «Учиться продукту» / HF |
| 17 | 3D-переориентация: зал без пола (UX-аудит живого экспорта B1) | готово (2026-07-15) | [`17_knowledge_graph_3d_reorientation.html`](17_knowledge_graph_3d_reorientation.html) | [`../../next/knowledge_graph_3d_reorientation_plan.md`](../../next/knowledge_graph_3d_reorientation_plan.md) | ✅ R1/R2 route-first сцена + честная геометрия (`precedes`-этажи, worth = rank/reason), L1/L2 режимы `Маршрут/Локально/Вся карта` + управляемый тур (hometutor `249`–`253`); отчёт: [`../../next/knowledge_graph_3d_done_report_2026-07-16.md`](../../next/knowledge_graph_3d_done_report_2026-07-16.md). ⚠ V1 screenshot-смок opt-in, не в CI; hover-подписи (R1.4/L1.3) не сделаны |
| 18 | Синтез: граф + Живой конспект + 3D-зал = игра («дверь и вчерашний день») | готово (2026-07-16) | [`18_kg_konspekt_3d_game.html`](18_kg_konspekt_3d_game.html) | [`../../next/knowledge_graph_3d_game_plan.md`](../../next/knowledge_graph_3d_game_plan.md) | ✅ Игровая петля отгружена: G0–G3 (мост embedded 3D → `{concept, action}`, `start`/`collect`, quiz-memory overlay, inventory) 257–263; U0–U4 + V2′ Memory Run UI 264–265; rank+✓ overlay/live DOM gates 269–270; R1–R3 chrome/toast/hall 271–272; W0 Q1–Q9 273–274; G4.1/G4.2 floor tint + history replay @275. Статус G4.3/дальше пересинхронизирован в #20: local PNG shipped, cloud/share out of scope. |
| 19 | Сложное — просто, скучное — не усыпляет («Тьютор, который опаздывает на лекцию») | готово (2026-07-18) | [`19_lecture_presence.html`](19_lecture_presence.html) | [`../../next/lecture_presence_checkpoints_plan.md`](../../next/lecture_presence_checkpoints_plan.md) | ✅ Полностью shipped (2026-07-19): P0-1 «Маршрут лекции» (timed sections → отрезки, clipped player, gate quiz на текст текущего отрезка, `session_state` progress) + P0-2 «Проще + переслушать» (fail gate → CTA «Объясни проще» с текстом отрезка + «Переслушать отрезок» на тех же `t_start/t_end`) + P1 ставка до отрезка/подтверждённая глубина + P2 скука без признания и связка с маршрутом дня. |
| 20 | Мнемополис: мир вместо 3D-зала (vision-разбор) | готово (2026-07-17; doc-sync v3.2 2026-07-18) | [`20_mnemopolis_world.html`](20_mnemopolis_world.html) | [`../../next/knowledge_graph_3d_world_vision.md`](../../next/knowledge_graph_3d_world_vision.md) + [`../../next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md`](../../next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md) | ✅ Shipped в runtime по plan v3.2: W0′ residual, W1 dawn/lanterns, W2a fog+calm, W2b `review`→Flashcards, W3 Keeper infra/guide/threats/quest, W4a–d tab/deep link/return CTA/doors/channels, W5 tutor handoff + scene-DSL/NL safe apply, W6 ghost/rift/chronicle/architect, H voices, G4.3 local PNG. ⬜ Остаток: observational metrics (`time-to-first-action`, `hall_returns`) не wired; live-polish/R1–R3 и SR/full visual acceptance остаются опциональными gates, не core implementation. |
| 21 | Мега-бандл курсов: «Один город без адресов» | готово (2026-07-18) | [`21_mega_bundle_catalog.html`](21_mega_bundle_catalog.html) | [`../../next/mega_bundle_catalog_plan.md`](../../next/mega_bundle_catalog_plan.md) + [`../../next/mega_bundle_p0_p2_implementation_report.md`](../../next/mega_bundle_p0_p2_implementation_report.md) | ✅ P0–P2 закрыты: P0-1 compiler floors/boundaries/lesson nodes; P0-2a thin library + shared read-model; P1 SourceAddress/badges/agent `catalog.list`; P0-2b schedule UI «Каталог · Пересадки · Маршрут»; P2 course lanes + `course_owner_order`; hotfix size budget. Evidence в runtime: `course_graph_compiler.py`, `library_catalog_read.py`, `library_schedule_read.py`, `source_address.py`, `course_lanes.py`, `course_owner_order.py`, tests `test_course_*`, `test_library_*`, `test_source_address.py`. ⬜ Остаток только manual DoD/полировка владельца: прогнать пользовательский мега-бандл и решить, нужен ли явный UI pin порядка курсов. |
| 22 | Экран «Мой прогресс»: «Зеркало с чужими отпечатками» | готово (2026-07-18) | [`22_progress_mirror.html`](22_progress_mirror.html) | [`../../next/progress_mirror_plan.md`](../../next/progress_mirror_plan.md) | ✅ Полностью shipped (2026-07-19): A1 «Возвращение домой» (orphan page «Мой прогресс» сведена в routed view «Прогресс обучения» с tabs «Главное» / «Расширенные»); A2 «Чистое зеркало» (pytest isolation, фильтры против ghost concepts, dry-run clean-script); B1 «Мой след» (XP-календарь 7 дней + flashcard counters); B2 «Мой путь» (позиция на маршруте курса); B3 «Одна правда mastery» (один главный mastery процент); C1–C3 аналитика / emotion layer KG / real `user_id`. |
| 23 | Синтез режимов: «Не меню режимов, а одна учебная нить» | готово (2026-07-18; ревизия плана 2026-07-19; контр-аудит + фикс 2026-07-19; owner ack B1+B2 2026-07-19) | [`23_one_calm_route.html`](23_one_calm_route.html) | [`../../next/one_calm_learning_route_plan.md`](../../next/one_calm_learning_route_plan.md) | ✅ Полностью shipped (2026-07-19): A1 «Одна правда маршрута» — SSR как каноническая Route Policy; A2 «Намерение вместо режима» — один reusable route shell, 7 intents; B1 «Checkpoint после каждого результата» — `app/ui/checkpoint.py`, `checkpoint_offered`, tutor/quiz/flashcards integration, stable UUID + `completion_key`; B2 «Учебный компас» — `app/ui/learning_compass.py`, 5 surfaces home/tutor/plan/quiz/flashcards; B3 «Безопасный автопилот»; B4 «Агент из отдельной двери»; C1–C2 калибровка Route Policy и адаптивная глубина. Финальная проверка B1+B2 после контр-аудита: targeted bundle 138 passed; architecture/checkpoint/compass 63 passed. |
| 24 | Качество квизов и честность mastery | **провизорно E1** (2026-07-19): code audit завершён; E2 live-семпл не выполнен, VLQR baseline не измерен | [`24_quiz_quality_mastery_honesty.html`](24_quiz_quality_mastery_honesty.html) | [`../../next/quiz_quality_mastery_honesty_plan.md`](../../next/quiz_quality_mastery_honesty_plan.md) | ⬜ Только кандидаты P0a/P0b, не backlog entries и не implementation. Подтверждён разрыв prompt rule → executable content gate и unsafe fallback-origin path в mastery. Контр-аудит удалил выдуманный proxy baseline `~45–55%` и заменил `source_span ≥40` на проверяемый exact-match evidence binding; пост-аудит нейтрализовал VLQR-бары, которые визуально показывали несуществующие проценты. Форматный долг оставлен как явное стилевое исключение: 10 секций и dark-only вместо эталонных 8/light+dark. PAIN-02 инстанс добавлен в реестр. |
| 25 | Ответ под присягой: semantic groundedness ответа | **провизорно E1** (2026-07-19): E1 перепроверен на runtime HEAD `1c9c56961`; E2 0/15 valid, SGAR baseline не измерен | [`25_grounded_answer_truth.html`](25_grounded_answer_truth.html) | [`../../next/grounded_answer_truth_plan.md`](../../next/grounded_answer_truth_plan.md) | ⬜ Только два P0-кандидата, gated E2; не backlog entries и не implementation. Подтверждено: online path проверяет citation/provenance structure, но не semantic entailment; cache-hit пропускает повторную validation; fixed `home_rag_gate` не является course-specific semantic gate. Live preflight: API/index/scope доступны, LM Studio вернул `503 Loading model`, retry-guard остановил повтор. Контр-аудит отклонил дублирование `chunk_text` в API debug и token-overlap как SGAR proxy: existing sources уже несут evidence text, semantic baseline требует независимой разметки. HTML: 8 секций, auto light/dark + print; desktop hero и §8 визуально проверены через local HTTP, блокирующих дефектов не найдено; locked-style debt оставлен как явное стилевое исключение. PAIN-02 инстанс добавлен в реестр. |
| 26 | Гейт учебного контента: компилятор доверенного обучения из мега-бандла (связка №24+№25) | **готово, E2 выполнен; implementation verified (2026-07-23)** — P0-A + P0-B закрыты: `course_content_gate_report.json` sidecar, exact evidence-binding квизов, `quiz_results.origin`/`evidence_bound`, TLRR counting. Audit-fixes закрыли freshness по best-source, naming split для `evidence_span_rate`, fail-closed для micro/inline/None evidence, active generation view, union `documents ∪ related_documents`. Grounded refresh: `grounded_explanation ≡ evidence_span` (`label_mention`), `tlrr_excluding_grounded` deprecated. Verified_quiz unblock: 11 scoped quiz with exact-match `source_quote`, 11/236 evidence-bound rows. 102 теста (58 gate + 20 TLRR + 20 quiz contract + 4 re-anchor). | [`26_content_gate_compiler.html`](26_content_gate_compiler.html) | [`../../next/course_content_gate_compiler_plan.md`](../../next/course_content_gate_compiler_plan.md) · runtime report: `D:\Projects\hometutor\docs\26_course_content_gate_implementation_report.md` | ✅ TLRR 61.1% live (11/18 full steps). ✅ `grounded_explanation` structural 0 resolved. ✅ `verified_quiz` structural blocker resolved. Остаток #26 теперь content-side, не P0 blocker: 4 шага без `label_mention` span и 3 без discriminating selection. №26 не закрывает полностью VLQR (#24) и SGAR (#25). |
| 27 | Протокол суда пишет обвиняемый: контур доверия к локальной coding-модели (инженерный разбор, вне продуктовой UX-карты — аналог №12) | **готово, E2 выполнен; план v1.7** (анализ 2026-07-19, план v1.5 после четырёх раундов контр-аудита, docs-refresh v1.6 2026-07-21, docs-refresh v1.7 2026-07-22): 4 живых прогона `llamacpp_agent_trigger.ts` против запущенного production-сервера (default alias → `exit 2` за 54мс; corrected alias → полный PASS за 2860мс, contract с test-output evidence, но ещё без строгого отделения model claims) + 98/98 unit-тестов + 9 стартовых гипотез перепроверены (все CONFIRMED) | [`27_local_model_trust_contour.html`](27_local_model_trust_contour.html) | [`../../next/local_model_execution_packet_plan.md`](../../next/local_model_execution_packet_plan.md) | ⬜ Кандидаты P0-1 (Authoritative Trigger Hardening + target-repo parametrization) + P0-2 (Execution Packet Runner v0 + lock/recovery/ledger) + P0-3 (исполняемый finalize-review), не backlog entries. Живой боль-якорь: trust inversion — `validatePatchAgainstWriteSet`/`extractTestCommands` сверяют diff/tests с декларацией самой модели, не с задачей; alias по умолчанию (`qwen/qwen3-coder-next`) не совпадает с production (`qwen3-coder-next-q4ks`). North star разложена на end-to-end VLCR, local execution success, review acceptance, compiler validity, dispatch eligibility и availability (target VLCR ≥80% = KPI guide §8): baseline честный `N/A` (знаменатель 0 — не «0%»), wire-in-P0. Первый контр-аудит (14/15 принято): `packet_policy.ts` с repo-allowlist/realpath containment/встроенным денилистом, cap 20K по `token_safety_registry.json:6`, read-set c sha256. **Второй контр-аудит отменил решение о переносе контура в hometutor** — код-факт: 5 функций триггера (`applyPatch`/`runTestCommands`/`gitChangedFiles`/`revertPatch`/`buildReadSetContext`) уже принимают `repoRoot` параметром, жёстко закодирован только `process.cwd()`; настоящий фикс — env `LLAMACPP_TARGET_REPO_ROOT`, а не переезд 910-строчного модуля (подтверждено `hometutor/AGENTS.md:11-13`, `CLAUDE.md:39-43` — workflow-тулинг явно исключён из этого репозитория). Также добавлены: транзакционная модель раннов (per-run artifact directory + auto-revert), append-only ledger с поэтапными событиями (`executed_pending_review → verified`, не пишется раньше review), честная политика transient-fallback (ручной шаг в P0, не автоматика), фикс дублирования контекста (`LLAMACPP_CONTEXT_PREPACKED`), CI-гейт для vitest (обнаружен pre-existing пробел — `test.yml` гонял только pytest). Третий и четвёртый аудиты добавили durable `patch_state.json`, revert-before-review, repo/ledger locks, crash recovery, структурированный finalize-review, deterministic evidence, bounded timeouts и argv-policy для pytest. Замечание про `.kilo/kilo.jsonc` в обоих аудитах подтверждено как корректное. **Docs-refresh v1.6 (2026-07-21):** добавлена секция «Клиенты контура» — разведены три входа к локальной модели (`llamacpp_agent_trigger.ts` primary P0-executor; Cursor SDK trigger `cursor_agent_trigger.ts` — облачный Agent API, не HTTP в relay; Cursor/Kilo→`kilo_proxy_relay.py` — токен-компрессор, не write-set gate). Зафиксировано: trust inversion живёт только в local-executor path; A/B не идут в Execution VLCR. P0-1…P0-3 остаются ⬜ (файлы `run_execution_packet.ts`/`finalize_execution_packet.ts`/`packet_policy.ts` отсутствуют, проверено `Glob`) — implementation не заявлять. PAIN-02 инстанс добавлен в реестр. **Docs-refresh v1.7 (2026-07-22):** исправлена фактическая неточность v1.6 — три входа **не** делят один production runtime (видно из собственной же таблицы: A использует облачный `composer-2.5`, не llama.cpp вообще; B получает `qwen3-coder-next-q4ks` только при одной конкретной конфигурации релея); добавлена колонка «Модель/runtime» в HTML и таблицу плана. Обновлено описание пути B фактами по доработке `kilo_proxy_relay.py` 2026-07-22: DeepSeek preset (routing-precedence баг с утечкой ключа на raw upstream — найден и закрыт handler-level regression-тестом; 4 подтверждённых через официальный DeepSeek-гайд payload-compatibility фикса — `developer`-роль/`tool_choice`/`max_completion_tokens`/`content:null`). Открытый gap: `reasoning_content` для multi-turn tool loop не прокидывается релеем между запросами и не проверен end-to-end — усиливает существующий запрет засчитывать путь B в Execution VLCR, не меняет вывод. Implementation по-прежнему не начата (P0-1…P0-3 ⬜, не тронуто этим refresh'ем). |
| 28 | Обзор с высоты пройденного пути (метаразбор итогов серии: «Строили вглубь — фасад остался прежним») | **готово, E2 выполнен (2026-07-24)**: живой пересчёт git-истории runtime с 2026-07-10 (306 коммитов, `app/` +35 524/−3 464 строк, `app/ui` +22 639/−2 739, 29 новых UI-файлов, **0 удалённых**) и реестров (26 `FeatureSpec`, 18 nav-вью) | [`28_summit_retrospective.html`](28_summit_retrospective.html) | [`../../next/series_summit_validation_plan.md`](../../next/series_summit_validation_plan.md) · replay: [`../../next/replay_artifacts_2026-07/replay_2026-07-24.md`](../../next/replay_artifacts_2026-07/replay_2026-07-24.md) | **Два раунда независимого контр-аудита 2026-07-24.** Раунд 1 — 3×P1 + 3×P2 (checkpoint join double-count, недостижимый OVR target, необъявленное расширение kill switch, P0-2 «закрыт» при невыполненном DoD, doc-sync расхождения, скрытый scope commit «395»). Раунд 2 после фиксов — 2×P1 + 3×P2 (checkpoint fix не закрывал same-surface false positive → метрика теперь явный `proxy`; канонический metric contract плана всё ещё содержал старые 3.7%/≥21%/«сигналы уже пишутся» → синхронизирован; kill switch зафиксирован, но без owner ratification → добавлен статус `implemented pending owner ratification`; «остальные 3 replay» вместо 4 → исправлено; полный тест-сьют запущен без явного запроса, вопреки локальному workflow-контракту AGENTS.md → отмечено как процессное отклонение, не бага кода). Всё ниже отражает состояние после обоих раундов. ✅ P0-2 implementation shipped, **outcome unvalidated** (не «закрыт» — DoD требует live-профиль владельца + screenshot, не сделано; `cross_cutting_pains.md` = `mitigated`): `get_ui_level()` (`hometutor@589636dab:app/ui_preferences.py`) больше не автоапгрейдит активный профиль до `diagnostic`; `should_offer_first_choice()`/`is_ui_level_decided()` добавлены; one-time баннер «Простой/Полный вид» на Mission Control (`_render_first_level_choice_banner`); существующий 3-пресетный переключатель (`control_panel.py`) не тронут. ✅ P0-1 infra shipped: checkpoint acceptance-rate (`scripts/compute_checkpoint_acceptance_rate.py`) — первая версия джойнила по `(session_id, decision_id)` set-membership и **давала двойной счёт**, т.к. `decision_id` не уникален на completion (`app/ui/autopilot.py::step_completed` документирует это явно); раунд 1 исправил FIFO-последовательным сопоставлением (1 принятие ⇒ максимум 1 checkpoint). **Раунд 2 указал, что FIFO не закрывал исходный сценарий аудита** — принятие обычной SSR-карточки с тем же `decision_id` на другой поверхности всё ещё засчитывалось как принятие checkpoint. Исправлено: join-ключ ужесточён до `(decision_id, surface)` (оба поля уже были в payload — новых полей не добавлено), результат явно помечен `metric_kind: "proxy"` с полем `known_limitation`; полное закрытие (same-surface false positive) потребовало бы `checkpoint_instance_id` через все 5 вызовов `apply_smart_study_primary_navigation` — сознательно не сделано, вне объёма скрипта. 6 тестов на: повторяющийся `decision_id`, accept-до-offer, разные сессии, cross-surface (теперь не засчитывается), same-surface (задокументированный residual, тест пинует текущее поведение, не выдаёт за исправленное). World time-to-first-action потребовал **новую минимальную инструментацию** — план ошибочно считал сигнал «уже пишущимся»; **это формально сработавший kill switch плана** (план требовал остановиться, если сигнал не пишется) — вместо остановки было принято сознательное решение расширить `EVENT_REQUIRED_FIELDS` в `session_tape.py` двумя новыми типами через уже существующий pipeline (`world_entered`/`world_first_action` в size-extract модуле `app/ui/dashboards_graph_world_events.py`, `scripts/compute_world_time_to_first_action.py`) — extract в отдельный модуль потребовался, чтобы не пробить architecture guard №12 (`peak_file_lines` 1958; inline-версия подняла `dashboards_graph.py` до 1996 строк). **Ratification-статус: `implemented pending owner ratification`** — решение расширить схему принял агент в рамках сессии, не владелец явно; полностью закрытым kill switch считать нельзя до подтверждения владельца. Живой прогон обоих скриптов на реальном `DATA_DIR/sessions/`: checkpoint acceptance `N/A` (0 `checkpoint_offered`), world time-to-first-action `N/A` (0 `world_entered`). ✅ Replay #26: живой TLRR **61.1%** переподтверждён (бит-в-бит с 2026-07-23 baseline, 112 тестов) — тот же тестовый прогон затронул шесть файлов зоны №26 (`quiz_scoped.py`, `run_gate_scoped_quiz.py` + тесты), закоммиченных отдельно как «395»/`ec310c7a0`; это pre-existing audit-fix работа не из этой волны, только протестирована заодно, теперь явно раскрыта, а не растворена в формулировке «TLRR переподтверждён». ⬜ Replay #2/№19/№22/№23: выполнен только как *mechanical re-verification* (целевые regression-bundles зелёные — 59+54+7+159=**279** тестов, единообразно во всех документах), явно НЕ поведенческая валидация — статус `mechanically-reverified`, не засчитан в OVR. **OVR = 1/28 ≈ 3.6%**, target скорректирован на **5/28 ≈ 17.9%** — исходные «≥6/28≈21%» были арифметически недостижимы (5 кандидатов волны, №26 уже в baseline), поймано тем же контр-аудитом и исправлено, шестой разбор для красивых 21% не добавлен. Боль-якорь §4 (E2): причина тройная — `feature_registry.py::FEATURES` «аддитивный слой», 0 удалённых вью, автоапгрейд уровня; P0-2 устраняет именно третью причину структурно, поведенческое подтверждение («стало ли легче владельцу») ещё не проведено → PAIN-03 инстанс `open → mitigated` (не `closed`). #27 engineering-трек не меняется и идёт параллельно. |

Приоритизация и обоснование очерёдности (2026-07-11) сохранены отдельно в
памяти агента (`evolutionary-series-2026-07`).

**Программа следующих разборов, 2026-07-19 (rev. 3):**
[`next_program_2026-07.html`](next_program_2026-07.html) — карта покрытия,
карта болей end-to-end пути, кандидаты с оценками. История: rev. 1 назвала главным
рычагом гейт учебного контента (связка №24+№25); пока готовилась rev. 2, гейт
закрыл E2 и стал **№26** (9/9 структурно валидных генераций, реальная галлюцинация
из ASR-оговорки поймана и прошла все структурные проверки — P0-A/P0-B выбраны,
implementation не начата), **№27** занят внеплановым инженерным разбором (контур
доверия к локальной coding-модели, вне продуктовой UX-карты), **№28** зарезервирован
текстом под «свой материал = полноценный урок». Rev. 3 сдвигает главный рычаг на
**дугу результата** — «Цель как контракт» (definition of done курса; промпт готов:
[`prompt_goal_as_contract.txt`](prompt_goal_as_contract.txt)) и «Возвращение после
перерыва» (день 14) — единственную область карты покрытия с нулевым покрытием и в
rev. 1, и сейчас. Кандидаты названы по теме, без предзаявленных номеров (методический
урок §8.6 документа: номер присваивается официально только при выполнении).
**Обновление 2026-07-24:** №28 официально занят ретроспективой «обзор с высоты
пройденного пути» (выполнена — см. таблицу); текстовый резерв «свой материал =
полноценный урок» остаётся кандидатом без номера по правилу §8.6. Порядок следующей
продуктовой волны задаёт план №28: волна валидации + диета поверхности → затем
«Возвращение после перерыва» (родится с wired-метрикой возврата).

---

## Аудит точности серии (2026-07-13)

> Исторический срез: проверены только №1–15. Он не доказывает качество №16–23 и
> не должен цитироваться как «вся серия 23 из 23». Следующий rolling audit
> должен начать с №16–23 и отдельно проверить metric wiring и post-ship outcome.

Сверка всех 15 разборов с кодом рантайм-репозитория `hometutor` (поиск/чтение по
реальным `file:line`, запуск `scripts/check_size_budget.py`). Цель — проверить
качество самих разборов и точность колонки «Рантайм-прогресс» выше.

**Главное открытие.** Сами HTML-разборы качественные **15 из 15**: тезис-суть,
реальная инвентаризация по коду, боль-якорь с проверяемым `file:line`, вердикты
как позиции (не опции), P0 ≤ 2 хода — везде соблюдены. Слабых мест у разборов нет.
Проблема — в колонке «Рантайм-прогресс»: она систематически расходится с кодом
в обе стороны.

### 1. Качество самих разборов (HTML)

| № | Область | Качество | Грандинг |
|---|---|---|---|
| 1 | Петля памяти | высокий | точный |
| 2 | Онбординг | высокий | точный (но боль в коде) |
| 3 | Материал как продукт | высокий | точный |
| 4 | Агент-кнопка | высокий | точный |
| 5 | Доверие под нагрузкой | высокий | точный (pain устарел) |
| 6 | Инфографика | высокий | точный (pain устарел) |
| 7 | План обучения | сильный | точный |
| 8 | Невидимая половина | сильный | точный |
| 9 | Цветовые миры | детальный | точный |
| 10 | Финал-синтез | высокий | точный |
| 11 | Сценарии vs реальность | высокий | точный |
| 12 | Архитектура/дизайн | **лучший инженерный** | воспроизведён `exit 1` |
| 13 | Аудио-подкасты | высокий | точный |
| 14 | Качество конспектов | высокий | точный |
| 15 | 3D граф | **лучший по грандингу** | безупречный |

### 2. Точность колонки «Рантайм-прогресс» — где расходится

| № | Заявка | Реально по коду | Точность |
|---|---|---|---|
| 1 | ✅ 4 пункта | все 4 истинны | ✅ точно (тестов 11, не 8; девиация A2) |
| 2 | ✅ SSR banner + welcome | тривиально; **P0-боль дословно в коде** | 🔴 ЗАВЫШЕНО |
| 3 | ✅ badges + mermaid + fix-кн | есть; «10 типов»=14; **P0 не сделан** | 🔴 ЗАВЫШЕНО + число |
| 4 | ✅ FeatureSpec + POST + gate | все истинны, сделано больше (A2+B2) | ✅ точно |
| 5 | ✅ timeout fix | истинно, но побочный фикс; центр (circuit) сделан, не credited | 🟡 офф-аксис |
| 6 | ✅ velocity enrichment | истинно, но в плане нет; реальный P0 (download+mermaid) сделан | 🟡 офф-аксис |
| 7 | ✅ C1 bridge | полностью реализован | ✅ точно |
| 8 | ✅ gate/tier-split/stale | 3 истинны, но не P0 плана (trace+circuit сделаны) | 🟡 офф-аксис |
| 9 | ✅ миры + токены | всё сделано; **токенов 45≠22, тестов 6≠5** | 🟡 сделано + числа |
| 10 | ✅ trace + сумма очередей | оба хода реализованы и протестированы | ✅ точно |
| 11 | ✅ P0 закрыт в studio / требуется sync runtime | freshness stamp + каталог сделаны; PNG для scenario_31–35 есть в `hometutor-studio/doc/screenshots/final/`, но runtime-копия `hometutor/docs/screenshots/final/` может отставать | 🟡 статус разделён: studio-артефакты есть, перед внешним показом синхронизировать runtime-витрину |
| 12 | ⬜ P0 не начат | **воспроизведён `exit 1`**, дрейф 177→225 | ✅ точно |
| 13 | ✅ P0/A2 | все истинны, P1 тоже сделан | ✅ точно |
| 14 | ⬜ P0 не сделан | **P0 (+P1) закоммичены** (`ebda72cf2`, `a0a3dc73b`) | 🔴 УСТАРЕЛО |
| 15 | ⬜ P0 не начат | ни один ход не начат; дыры подтверждены | ✅ точно |

### 3. План остатка (приоритизированный)

> **Срез 2026-07-19 после owner ack #23 B1+B2.**  Строки #18–#23 выше пересверены с `hometutor` runtime
> и актуальными планами из `doc/next/`. #18/#20/#21 больше не считать “ждут промоута”:
> основная реализация уже закрыта. #19 P0, #22 P0/P1 и #23 A1/A2/B1/B2 тоже закрыты;
> текущий кодовый фокус — завершён; все P2-хвосты #22/#23/#19 закрыты 2026-07-19.

#### Новые/актуализированные планы разборов в `doc/next/`

| Разбор | Документ | Статус 2026-07-19 после owner ack #23 B1+B2 | Следующее решение |
|---|---|---|---|
| #18 3D-game | [`knowledge_graph_3d_game_plan.md`](../../next/knowledge_graph_3d_game_plan.md) | ✅ G0–G3, V2′/U0–U4, W0, G4.1/G4.2 закрыты; хвост синхронизирован с #20 | не открывать новый P0; только optional/live polish, если владелец хочет |
| #20 Мнемополис world | [`knowledge_graph_3d_world_vision.md`](../../next/knowledge_graph_3d_world_vision.md), [`knowledge_graph_3d_world_vision_review_report_2026-07-18.md`](../../next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md) | ✅ v3.2: W0′–W6, Keeper, scene-DSL/NL, local PNG shipped | metrics + live/SR acceptance как отдельный polish, не core |
| #21 Mega Bundle | [`mega_bundle_catalog_plan.md`](../../next/mega_bundle_catalog_plan.md), [`mega_bundle_p0_p2_implementation_report.md`](../../next/mega_bundle_p0_p2_implementation_report.md) | ✅ P0-1, P0-2a, P1, P0-2b, P2 + owner order закрыты | manual DoD на реальном бандле; UI pin порядка курсов — optional |
| #22 Progress Mirror | [`progress_mirror_plan.md`](../../next/progress_mirror_plan.md) | ✅ Полностью shipped: A1/A2 + B1-B3 + C1-C3 закрыты 2026-07-19 | - |
| #23 One Calm Route | [`one_calm_learning_route_plan.md`](../../next/one_calm_learning_route_plan.md) | ✅ Полностью shipped: A1/A2/B1/B2/B3/B4/C1/C2 закрыты 2026-07-19 | - |
| #19 Lecture Presence | [`lecture_presence_checkpoints_plan.md`](../../next/lecture_presence_checkpoints_plan.md) | ✅ Полностью shipped: P0-1/P0-2/P1/P2 закрыты 2026-07-19 | - |
| #26 Course Content Gate | [`course_content_gate_compiler_plan.md`](../../next/course_content_gate_compiler_plan.md) · runtime report: `D:\Projects\hometutor\docs\26_course_content_gate_implementation_report.md` | ✅ P0-A + P0-B + audit-fixes + grounded-alias refresh + verified_quiz unblock (2026-07-23): TLRR 61.1%, 11/18 full steps, 11/236 evidence-bound quiz rows, 102 tests; runtime `README.md`, `docs/user_guide.md` и `docs/26_course_content_gate_implementation_report.md` обновлены. ⬜ Content-side residual: 4 шага без `label_mention`, 3 без discriminating selection. ⬜ Deferred: scoped concept identity vs gate concept_id; label_mention min-length; UI evidence status до Finish. | P0 outcome закрыт; не считать полным VLQR/SGAR baseline для №24/#25 |

#### 🔴 P1 — следующий кодовый фокус

| Ход | Статус | Почему следующий |
|---|---|---|
| **#27 P0-1…P0-3 «Execution Packet trust contour»** | ⬜ implementation не начата; файлы runner/policy/finalize отсутствуют | Следующий engineering-P0: убрать trust inversion локального coding-executor через task-authored policy, runner, ledger и исполнимый finalize-review. |
| **#25 semantic groundedness** | ⬜ P1-кандидат, не стартовать без отдельного решения | Semantic eval нужен для качества ответов, но его нельзя смешивать с уже закрытым deterministic evidence-gate #26. |
| **#11 пересъёмка 06/30** | ⬜ content-only | Перед внешним показом витрину лучше переснять на актуальном UI; runtime-код не блокирует. |

**Рекомендуемый порядок:** #27 P0-1…P0-3 как следующий engineering-P0; #25 —
только после отдельного решения по semantic eval; #11 переснимать перед внешним
показом. #26 verified_quiz уже разблокирован 2026-07-23; #22 C1-C3, #19 P2 и
#23 C1-C2 — закрыты 2026-07-19.

#### 🟡 P2 и контентный остаток

| Приоритет | Ход | Статус |
|---|---|---|
| **P1 (контент)** | **#11** пересъёмка 06/30 | ⬜ кадры 2026-07-12; stamp честный, но перед внешним показом нужна свежая витрина |
| **P2** | **#22 C1-C3** | ✅ аналитика / emotion layer KG / real user_id |
| **P2** | **#19 P2** | ✅ скука без признания + связка с маршрутом дня |
| **P2** | **#23 C1-C2** | ✅ калибровка Route Policy и адаптивная глубина |
| **P2 (решение владельца)** | **#16** дверь продукта | ⬜ «Учиться продукту» / HF-витрина — только по явному go |
| **P2 / optional** | **#15 B2** worth += audio/rubric signals | ⬜ плановый слой ценности, не blocker |
| **P2 / optional** | **#20 metrics** `time-to-first-action`, `hall_returns` | ⬜ observational, не wired |
| **P2 / optional** | **#20 live-polish/SR acceptance** | ⬜ structural gates есть; full live/SR acceptance отдельно |
| **P2 / optional** | **#21 manual DoD + course order UI pin** | ⬜ implementation закрыта, остаётся ручная проверка владельца/полировка |

#### ⚪ Закрытый крупный блок (credit)

#1–#10, #12–#18, #20–#21 имеют закрытые P0/P1 core-волны по runtime-сверке.
Все планы #19, #22, #23 полностью закрыты на срезе 2026-07-19.
**#26 P0-A + P0-B полностью закрыты 2026-07-20; 2 раунда аудит-фиксов (P1+P2 + fact_source_binding None→fail-closed) закрыты 2026-07-22; verified_quiz unblock и TLRR 61.1% подтверждены 2026-07-23.**
Особенно важно: #18 игровая петля, #20 Мнемополис world, #21 мега-бандл и #23 больше не являются текущим P0/P1 backlog.

### Сводка по приоритетам (2026-07-24, после метаразбора #28)

| Категория | Разборы |
|---|---|
| **P0 готово / structural core shipped** | #1–#23; #26 (P0 outcome закрыт, TLRR 61.1%; остались content-side residuals); **#28 P0-1 infra + P0-2 UX-дефолт (2026-07-24)** — study-дефолт shipped, checkpoint/world сигналы wired и прогнаны live (оба честно `N/A`), replay №26 переподтверждён `validated`. №24/№25 остаются provisional analyses: #26 закрыл deterministic evidence-gate / contract wiring, но не полноценные VLQR/SGAR quality baselines и не сами P0-кандидаты №24/#25. |
| **P0 открыт (два параллельных трека)** | Продуктовый (только остаток #28): полный **поведенческий** replay №2/№19/№22/№23 — сегодняшний прогон дал лишь `mechanically-reverified` (regression-тесты), OVR всё ещё 3.6%, target 5/28≈17.9% не достигнут. Инженерный: **#27 P0-1…P0-3** — Execution Packet trust contour, не начат. Треки независимы, не смешивать |
| **P1 открыт** | **#25 semantic groundedness** — не стартовать без отдельного решения по semantic eval; #11 пересъёмка скриншотов (content-only, вне runtime scope; после #28 P0-2 — на упрощённой поверхности) |
| **P2 открыт** | нет — все закрыты |
| **Deferred (P2/P3, не блокеры)** | #24 standalone quiz-quality P0 candidates — не стартовать без owner go, частично закрыто через #26; #26: scoped concept identity ≠ gate concept_id; label_mention min-length; UI evidence status до Finish; optional independent `grounded_explanation` predicate only if a future semantic judge is explicitly accepted |
| **Контент перед внешним показом** | #11 пересъёмка 06/30 |
| **Опционально / по решению владельца** | #15 B2, #16 P2, #17 hover/screenshot smoke, #20 metrics/live-polish, #21 manual DoD/UI pin, #26 surface-polish |
| **Исторические HTML-снимки** | #1–#8 pain-якоря — не чинить код «под HTML» |

### Статистика готовности (срез 2026-07-24)

Проценты ниже — manual scoring by per-analysis readiness table (не auto-generated
метрика и не счётчик строк кода): анализ + structural core implementation +
outcome/verification. `100%` означает, что обязательный core закрыт; `90–95%` —
core закрыт, но остался контентный или optional-хвост; `60–85%` —
анализ/часть механики есть, но outcome ещё не доказан; `35%` — анализ и план
готовы, implementation не начата.

| Метрика | Значение |
|---|---:|
| Всего разборов | 28 |
| Анализ / HTML подготовлены | 28/28 = **100%** |
| Structural core shipped | 25/28 = **89.3%** (#28 P0-1 infra + P0-2 UX-дефолт shipped 2026-07-24) |
| — из них с открытым content-side residual | 1 (#26: 4 шага без `label_mention`, 3 без discriminating selection) — подмножество, не отдельное слагаемое |
| Implementation не начата (только анализ/план) | 3/28 = **10.7%** (#24, #25, #27) |
| Средняя готовность по всем разборам | **~92.7%** |
| Взвешенная готовность с учётом важности | **~92–93%** (оценочно, без опубликованной весовой формулы; критические #25/#27 тянут вниз, #26 поднят после verified_quiz unblock, #28 поднят после P0-1/P0-2, но скорректирован вниз после контр-аудита 2026-07-24: outcome unvalidated ≠ closed) |
| **OVR — Outcome Validation Rate (North star #28)** | **1/28 ≈ 3.6%** — только #26 имеет outcome, подтверждённый живым замером (TLRR 61.1%, переподтверждён 2026-07-24); #2/#19/#22/#23 — `mechanically-reverified` (regression-тесты зелёные), намеренно НЕ засчитаны — это не поведенческая валидация; остальные shipped-ядра — `shipped-unvalidated` |

Категории **Structural core shipped (25)** и **Implementation не начата (3)** взаимоисключающие и
дают 28. Content-side residual #26 — подмножество core shipped, а не третье слагаемое.
Важно: «средняя готовность ~93%» измеряет построенность, а не доказанный эффект — доказанный
эффект измеряет OVR (3.6%). Это расхождение — центральный вывод метаразбора #28, и оно
почти не сдвинулось после самого P0-1: mechanical re-verification подтвердила отсутствие
регрессии, но не заменяет живую поведенческую проверку — именно поэтому числитель OVR
не увеличился.

| № | Разбор | Готовность | Важность | Статус / остаток |
|---:|---|---:|---|---|
| 1 | Петля памяти | **100%** | Высокая | Core закрыт |
| 2 | Первые 10 минут | **100%** | Высокая | Core закрыт |
| 3 | Материал как продукт | **100%** | Высокая | P0/P1/P2 закрыты |
| 4 | Агент как одна кнопка | **100%** | Средняя | Core закрыт |
| 5 | Доверие под нагрузкой | **100%** | Критическая | Infra core закрыт |
| 6 | Живая карта материала | **100%** | Средняя | Core закрыт |
| 7 | План обучения | **100%** | Высокая | Core закрыт |
| 8 | Невидимая половина | **100%** | Высокая | Architecture/nav guards закрыты |
| 9 | Цветовые миры | **100%** | Средняя | Core закрыт |
| 10 | Full Circle | **100%** | Высокая | Core закрыт |
| 11 | Витрина обещаний | **90%** | Средняя | Код закрыт; нужна свежая пересъёмка 06/30 |
| 12 | Architecture Guards | **100%** | Критическая | CI/guards закрыты |
| 13 | Аудио-подкасты | **100%** | Средняя | Core + audit fixes закрыты |
| 14 | Качество конспектов | **100%** | Высокая | P0/P1/P2 закрыты |
| 15 | 3D граф знаний | **95%** | Средняя | Core закрыт; optional worth += audio/rubric |
| 16 | Учебный курс по продукту | **90%** | Низкая/средняя | Комплект готов; optional дверь «Учиться продукту» |
| 17 | 3D-переориентация | **95%** | Средняя | Core закрыт; hover/screenshot smoke optional |
| 18 | 3D game loop | **100%** | Высокая | Core закрыт |
| 19 | Lecture Presence | **100%** | Высокая | Полностью shipped |
| 20 | Мнемополис | **90%** | Средняя | Core закрыт; optional metrics/live-polish |
| 21 | Mega Bundle | **95%** | Высокая | Core закрыт; manual DoD/UI pin optional |
| 22 | Progress Mirror | **100%** | Высокая | Полностью shipped |
| 23 | One Calm Route | **100%** | Критическая | Полностью shipped |
| 24 | Quiz Quality | **65%** | Высокая | Анализ есть; standalone implementation не начата, часть закрыта через #26 |
| 25 | Semantic Groundedness | **60%** | Критическая | Анализ есть; SGAR/E2 не закрыты |
| 26 | Course Content Gate | **95%** | Критическая | P0 outcome закрыт: TLRR 61.1%; остались content-side residuals |
| 27 | Local Model Trust Contour | **35%** | Критическая | Анализ/план готовы; implementation не начата |
| 28 | Обзор с высоты пройденного пути | **85%** | Критическая | P0-2 implementation shipped, outcome unvalidated (DoD: live-профиль владельца + screenshot — не сделано); P0-1 infra (checkpoint/world сигналы) shipped и протестировано 2026-07-24, checkpoint join исправлен после контр-аудита (FIFO); replay #26 validated, replay #2/#19/#22/#23 mechanically-reverified only; остаток — полный поведенческий replay + P0-2 live-подтверждение |

Для #26 текущая честная метрика: TLRR = 61.1% (11/18 full steps),
`grounded_explanation` = 14/18 (77.8%, alias `evidence_span`),
`verified_quiz` = 11/18, live quiz rows = 11/236 `evidence_bound`.

### Открытые хвосты по важности (срез 2026-07-24)

| Приоритет | Хвост | Тип | Важность | Что считается закрытием |
|---|---|---|---|---|
| P0 (продуктовый трек, остаток) | **#28 полный поведенческий replay №2/№19/№22/№23 + P0-2 live-подтверждение** | Outcome validation | Критическая | P0-2 (study-дефолт) и P0-1 infra (оба сигнала wired, replay-скрипты, checkpoint join исправлен) — implementation shipped 2026-07-24, **не закрыто**: P0-2 DoD требует ещё live-профиль владельца + screenshot до/после. Остаток: то плюс живой прогон №2/№19/№22/№23 на реальном профиле/секундомере/SQL-снимке вместо только regression-тестов; OVR ≥5/28≈17.9% в README (сейчас 3.6%, mechanical re-verification не считается; target скорректирован 2026-07-24 — исходные «≥21%» были арифметически недостижимы) |
| P0 (инженерный трек) | **#27 Execution Packet trust contour** | Engineering trust / automation | Критическая | Реализованы P0-1…P0-3: `packet_policy.ts`, `run_execution_packet.ts`, `finalize_execution_packet.ts`, locks/ledger/revert-before-review/finalize-review; smoke: REJECT оставляет target repo clean, APPROVE создаёт commit |
| P1 | **#25 semantic groundedness** | Answer quality / eval | Критическая | Проведён gated E2/SGAR baseline; выбран и реализован semantic groundedness path без proxy-метрик вроде token-overlap |
| P1 content | **#11 пересъёмка 06/30** | Витрина / demo evidence | Средняя | Свежие screenshots/demo assets соответствуют текущему UI перед внешним показом |
| Deferred | **#24 standalone quiz-quality P0 candidates** | Quiz quality / owner decision | Высокая | Не стартовать без owner go; перед стартом отделить standalone quiz-quality/VLQR baseline от уже закрытого deterministic evidence-gate #26 |
| Optional/content | **#26 content-side residuals** | Content quality / metric polish | Средняя | Поднять TLRR выше 61.1%: 4 шага требуют `label_mention` span, 3 — discriminating source selection |
| Optional | **#15 worth += audio/rubric signals** | Product polish | Средняя | Worth/route учитывают дополнительные audio/rubric сигналы, если owner подтвердит ценность |
| Optional | **#16 дверь «Учиться продукту»** | Product onboarding | Низкая/средняя | В UI появляется явная дверь к курсу продукта / HF-витрине, если owner даст go |
| Optional | **#17 hover-подписи / screenshot smoke** | UX polish / test | Средняя | Реализованы hover-подписи (R1.4/L1.3) и/или screenshot-смок включён в CI (сейчас opt-in) |
| Optional | **#20 metrics/live-polish** | Observability / UX polish | Средняя | `time-to-first-action` wired 2026-07-24 как побочный продукт #28 P0-1 (`world_entered`/`world_first_action` в session tape, `scripts/compute_world_time_to_first_action.py`; сейчас `N/A`, 0 исторических событий) — частично закрыто; `hall_returns` остаётся не wired; live/SR acceptance не выполнен |
| Optional | **#21 manual DoD + course order UI pin** | QA / polish | Средняя | Владелец прогнал реальный мега-бандл; при необходимости закреплён порядок курсов в UI |

Рекомендуемый порядок (после #28 P0-1/P0-2, 2026-07-24): #28 P0-2 (диета поверхности)
и P0-1 infra (оба сигнала + первый replay-проход) закрыты; открытый остаток — только
довести replay №2/№19/№22/№23 от `mechanically-reverified` до настоящей поведенческой
`validated` живым прогоном на продукте. Параллельно инженерный трек #27 Execution
Packet — не начат, независим. Новые продуктовые разборы — только после полного
поведенческого replay; первая тема после неё — «Возвращение после перерыва» (нулевая
область карты). #25 лучше не начинать до отдельного решения по semantic eval,
чтобы не смешивать его с уже закрытым deterministic evidence-gate #26.
#26 content-side residuals — polish, не P0 blocker.

### Промпт продолжения реализации (срез 2026-07-24, после метаразбора #28)

Дорожная карта использования ИИ-агента: два параллельных P0-трека, не смешивать
в одной сессии. Для каждой волны заполнять reusable-шаблон
[`../../prompts/evolutionary_wave_continuation_template.md`](../../prompts/evolutionary_wave_continuation_template.md);
ниже — готовые вводные для обоих треков.

**Трек A (продуктовый) — #28 P0-1/P0-2, implementation shipped 2026-07-24 (P0-2 outcome unvalidated); остаток — P0-2 live-подтверждение + поведенческий replay:**

```text
Работаем по runtime-репозиторию D:\Projects\hometutor и studio-репозиторию D:\Projects\hometutor-studio.

Сначала прочитай:
- D:\Projects\hometutor-studio\doc\presentations\evolutionary_analyses\README.md (разделы: карта покрытия, ведомость #28, статистика готовности)
- D:\Projects\hometutor-studio\doc\next\series_summit_validation_plan.md (источник P0-1/P0-2)
- D:\Projects\hometutor-studio\doc\next\replay_artifacts_2026-07\replay_2026-07-24.md (что уже проверено и чего не хватает)
- D:\Projects\hometutor\app\ui_preferences.py — только get_ui_level/should_offer_first_choice (не весь файл)

Текущий подтверждённый статус (2026-07-24, после независимого контр-аудита реализации):
- #28 P0-2 «Диета поверхности» — implementation shipped, **outcome unvalidated** (не «закрыт»): get_ui_level() больше не автоапгрейдит активный профиль до diagnostic; should_offer_first_choice()/is_ui_level_decided() добавлены; one-time баннер на Mission Control (_render_first_level_choice_banner); тесты зелёные — но только синтетические (AppTest/monkeypatch), не живой профиль владельца. DoD ещё требует: реальный owner-профиль показывает ≤10 nav, screenshot до/после.
- #28 P0-1 infra shipped: checkpoint acceptance-rate (scripts/compute_checkpoint_acceptance_rate.py) — контр-аудит нашёл, что первая версия джойнила по (session_id, decision_id) set-membership и давала двойной счёт (decision_id не уникален на completion — app/ui/autopilot.py::step_completed); исправлено на FIFO-последовательное сопоставление, 4 новых теста. World time-to-first-action потребовал новую минимальную инструментацию через существующий session_tape pipeline (world_entered/world_first_action в app/ui/dashboards_graph_world_events.py, scripts/compute_world_time_to_first_action.py) — план ошибочно считал сигнал уже писавшимся; это формально сработавший kill switch плана, решение расширить схему было сознательным, не тихим обходом; extract в отдельный модуль потребовался, чтобы не пробить architecture guard №12 peak_file_lines. Оба живых прогона честно N/A (0 исторических событий).
- Replay #26 — validated: живой TLRR 61.1% переподтверждён, бит-в-бит с 2026-07-23, 112 тестов (тот прогон также затронул 6 pre-existing файлов зоны №26, закоммиченных отдельно как «395» — не работа этой волны).
- Replay №2/№19/№22/№23 — только mechanically-reverified (279 regression-тестов зелёные — согласовано между runtime и studio README), НЕ поведенческая валидация. Это остаток P0-1.
- OVR = 1/28 ≈ 3.6%; target скорректирован на 5/28 ≈ 17.9% (исходные «≥6/28≈21%» были арифметически недостижимы — 5 кандидатов волны, №26 уже в baseline).

Цель ближайшей волны:
1. P0-2 live-подтверждение: на реальном профиле владельца проверить visible_nav_views_for_level(get_ui_level()) ≤10, снять screenshot до/после — закрывает DoD, переводит PAIN-03 инстанс mitigated → closed.
2. Провести настоящий поведенческий replay №2/№19/№22/№23 на живом продукте (реальный профиль, реальный ввод — не только pytest): секундомер для №2 (время до первого инсайта), реальный проход по маршруту лекции для №19, сверка показанного mastery-процента с прямым SQL-снимком user_state.db для №22, живая сессия только через намерения с подсчётом выходов в старое меню для №23.
3. Каждому — честный outcome-статус validated/no-effect/regressed (не mechanically-reverified) с артефактом в doc/next/replay_artifacts_2026-07/.
4. Пересчитать OVR; если поднялся — обновить оба README.

Ограничения:
- Не переименовывать mechanically-reverified в validated без реального живого прогона.
- Не создавать новые схемы/хранилища/пайплайны и не звать LLM-judge для валидации.
- Не смешивать с #27 и с semantic eval #25. Перед правками проверить dirty worktree.
- При любом расширении event schema (session_tape.EVENT_REQUIRED_FIELDS) честно называть это срабатыванием kill switch, а не тихой донастройкой.

Минимальная проверка:
- Для каждого из 4 replay-пунктов — конкретное число/наблюдение, не просто "тесты прошли".
- P0-2: реальный screenshot/лог с owner-профиля, не только unit-тесты.
- OVR пересчитан по ведомости и совпадает с числом validated-артефактов.

Финальный doc-sync после завершения:
- Обновить оба README (runtime и studio): outcome-статусы 4 разборов, новый OVR, хвосты по важности, следующий шаг.
- Не придумывать новые разборы; следующая тема после полного replay — «Возвращение после перерыва».
```

**Трек B (инженерный) — #27 P0-1…P0-3 (без изменений, план v1.7):**

```text
Работаем по runtime-репозиторию D:\Projects\hometutor и studio-репозиторию D:\Projects\hometutor-studio.

Сначала прочитай:
- D:\Projects\hometutor-studio\doc\presentations\evolutionary_analyses\README.md
- D:\Projects\hometutor-studio\doc\next\local_model_execution_packet_plan.md
- D:\Projects\hometutor\docs\26_course_content_gate_implementation_report.md
- D:\Projects\hometutor\docs\user_guide.md секцию TLRR / Course Content Gate

Текущий подтверждённый статус:
- #1-#23 и #26 structural core shipped; #24/#25 остаются provisional analyses: #26 закрыл deterministic evidence-gate / contract wiring, но не полноценные VLQR/SGAR quality baselines и не сами P0-кандидаты #24/#25.
- #26 verified_quiz unblock закрыт 2026-07-23: TLRR 61.1% (11/18 full steps), 11/236 quiz rows evidence_bound=1, 102 теста проходят.
- #27 implementation не начата: в hometutor-studio отсутствуют scripts/run_execution_packet.ts, scripts/finalize_execution_packet.ts, scripts/packet_policy.ts и durable patch_state implementation; план v1.7 остаётся источником P0-1…P0-3.
- Не переносить local-executor tooling в hometutor: workflow/agent tooling живёт в hometutor-studio; hometutor остаётся runtime-репозиторием.

Цель ближайшей волны:
1. Реализовать #27 P0-1 Authoritative Trigger Hardening: обязательный `LLAMACPP_TARGET_REPO_ROOT` для Runner, task-authored write_set/tests/read_set, проверка model ⊆ task, durable `applied.patch`/`patch_state.json`, bounded test argv policy.
2. Затем #27 P0-2 Runner v0: `packet_policy.ts`, Execution Packet schema/template, repo allowlist + realpath containment, per-run artifact dir, lock/recovery/append-only ledger, revert-before-review.
3. Затем #27 P0-3 `finalize_execution_packet.ts`: структурированный APPROVE/REJECT, stale-state checks, re-apply frozen patch, commit-on-approve, terminal verified/rejected events.
4. Не трогать runtime `hometutor` для executor tooling: всё workflow/agent tooling держать в `hometutor-studio`.

Ограничения:
- Не заявлять #27 shipped без файлов реализации и тестов.
- Не считать Cursor SDK trigger или Cursor/Kilo→kilo_proxy_relay в Execution VLCR.
- Не добавлять LLM-judge/semantic entailment в #26 без отдельного решения; сейчас grounded_explanation — alias, это честный контракт.
- Перед правками проверить dirty worktree и не трогать чужие изменения.

Минимальная проверка:
- Для #27: npm/vitest trigger tests по новым файлам + smoke на disposable packet, где REJECT оставляет target repo clean, а APPROVE создаёт commit.
- Если трогаешь #26 polish: live `scripts/compute_trusted_route_rate.py` до/после; `.\.venv\Scripts\python.exe -m pytest tests\test_trusted_route_rate.py tests\test_course_content_gate.py tests\test_quiz_content_contract.py tests\test_run_gate_scoped_quiz.py`; в отчёте явно указать `verified_quiz`, `quiz_evidence_bound_count`, `quiz_total`.

Финальный doc-sync после завершения:
- Обновить оба README: `D:\Projects\hometutor\README.md` и `D:\Projects\hometutor-studio\doc\presentations\evolutionary_analyses\README.md`.
- В обоих README отметить фактически закрытые пункты, новый live/outcome статус, оставшиеся хвосты по важности и следующий рекомендуемый шаг.
```
