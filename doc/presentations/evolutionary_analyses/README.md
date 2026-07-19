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

Срез на 2026-07-19 после добавления №24. Теги пересекаются: один разбор может входить в несколько
областей. «0» означает отсутствие **отдельного end-to-end разбора**, а не полное
отсутствие компонента в других работах.

| Область | Число разборов | Разборы / комментарий |
|---|---:|---|
| Граф, визуальная карта и игровой мир знаний | **6** | №3, №6, №15, №17, №18, №20 |
| Материал, контент и качество конспекта/лекции | 4 | №3, №13, №14, №19 |
| Маршрут, навигация и следующий шаг | 5 | №2, №4, №10, №22, №23 |
| Память, план и прогресс | 5 | №1, №7, №10, №22, №23 |
| Надёжность, невидимая инфраструктура и архитектура | 3 | №5, №8, №12 |
| Курсы, каталог и обучение продукту | 3 | №16, №19, №21 |
| Оформление и внешняя витрина | 3 | №9, №11, №16 |
| Качество объяснения/лекционного обучения | 1 | №19 |
| **Качество квизов как самостоятельного учебного инструмента** | **1** | №24: E1 code audit завершён; обязательный E2 live-семпл 0/15, VLQR baseline не измерен |
| **Качество retrieval, цитат и ответа как учебного доказательства** | **1** | №25: E1 verified на runtime HEAD `1c9c56961`; E2 0/15 valid, SGAR baseline не измерен |
| **Мотивация, возврат после перерыва и долгосрочное удержание** | **0** | Progress/route затрагивают тему, но не проверяют возврат и retention end-to-end |

Карта — обязательный preflight перед выбором темы. Нулевая область получает
coverage-бонус, но не автоматический P0: всё равно нужна проверяемая боль. Для
области с четырьмя и более разборами новый выпуск допустим только с новой
пользовательской болью и явной строкой «чем отличается от №N». После добавления
разбора автор обновляет этот срез; мокапы №18 в счёт не входят.

**Здоровье серии.** Канонических разборов — 25; ещё 3 HTML-файла являются
мокапами №18. До №24 формулировка North star встречалась в 17 из 23 разборов, но единый
статус подключения метрик до сих пор не вёлся. Поэтому утверждение вроде
«11 метрик объявлены, 0 подключены» нельзя считать фактом без отдельного аудита.
№24 и №25 задают metric contracts, но их VLQR/SGAR baselines честно остаются `not measured`.
Для новых разборов статус метрики обязателен по правилу `North star wired` из гайда.

| Центральный контроль | Текущий статус | Охват |
|---|---|---|
| Wiring-status North star | `mixed` | №1–23 не аудированы; №24 — `wire-in-P0`; №25 SGAR — `not measurable` до E2 |
| Outcome после реализации | `mixed` | №1–23 не аудированы; №24/№25 — analyses provisional, implementation отсутствует |
| Точность причинности | `historical-partial` | детальный аудит ниже охватывает №1–15; №16–23 требуют rolling audit |

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
| 19 | Сложное — просто, скучное — не усыпляет («Тьютор, который опаздывает на лекцию») | готово (2026-07-18) | [`19_lecture_presence.html`](19_lecture_presence.html) | [`../../next/lecture_presence_checkpoints_plan.md`](../../next/lecture_presence_checkpoints_plan.md) | ⬜ Кандидаты остаются открытыми: P0-1 «Маршрут лекции» (8–12 мин clipped-отрезки из `t_start/t_end`, gate quiz через `generate_scoped_quiz_from_content`, честный progress) и P0-2 «Проще + переслушать» с адресом отрезка. Runtime уже умеет media boundaries/listened receipts и scoped quiz helper, но единого lecture-route/quiz-checkpoint потока по timed-разделу ещё нет. |
| 20 | Мнемополис: мир вместо 3D-зала (vision-разбор) | готово (2026-07-17; doc-sync v3.2 2026-07-18) | [`20_mnemopolis_world.html`](20_mnemopolis_world.html) | [`../../next/knowledge_graph_3d_world_vision.md`](../../next/knowledge_graph_3d_world_vision.md) + [`../../next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md`](../../next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md) | ✅ Shipped в runtime по plan v3.2: W0′ residual, W1 dawn/lanterns, W2a fog+calm, W2b `review`→Flashcards, W3 Keeper infra/guide/threats/quest, W4a–d tab/deep link/return CTA/doors/channels, W5 tutor handoff + scene-DSL/NL safe apply, W6 ghost/rift/chronicle/architect, H voices, G4.3 local PNG. ⬜ Остаток: observational metrics (`time-to-first-action`, `hall_returns`) не wired; live-polish/R1–R3 и SR/full visual acceptance остаются опциональными gates, не core implementation. |
| 21 | Мега-бандл курсов: «Один город без адресов» | готово (2026-07-18) | [`21_mega_bundle_catalog.html`](21_mega_bundle_catalog.html) | [`../../next/mega_bundle_catalog_plan.md`](../../next/mega_bundle_catalog_plan.md) + [`../../next/mega_bundle_p0_p2_implementation_report.md`](../../next/mega_bundle_p0_p2_implementation_report.md) | ✅ P0–P2 закрыты: P0-1 compiler floors/boundaries/lesson nodes; P0-2a thin library + shared read-model; P1 SourceAddress/badges/agent `catalog.list`; P0-2b schedule UI «Каталог · Пересадки · Маршрут»; P2 course lanes + `course_owner_order`; hotfix size budget. Evidence в runtime: `course_graph_compiler.py`, `library_catalog_read.py`, `library_schedule_read.py`, `source_address.py`, `course_lanes.py`, `course_owner_order.py`, tests `test_course_*`, `test_library_*`, `test_source_address.py`. ⬜ Остаток только manual DoD/полировка владельца: прогнать пользовательский мега-бандл и решить, нужен ли явный UI pin порядка курсов. |
| 22 | Экран «Мой прогресс»: «Зеркало с чужими отпечатками» | готово (2026-07-18) | [`22_progress_mirror.html`](22_progress_mirror.html) | [`../../next/progress_mirror_plan.md`](../../next/progress_mirror_plan.md) | ✅ P0-2 A2 «Чистое зеркало» shipped 2026-07-19: кран (conftest `pytest_configure` + guard в `_resolve_state_db_path`), джойн (heatmap/narrative фильтр по активному графу, «общий фон»), чистка (`scripts/clean_progress_ghosts.py` dry-run+backup), тесты (`test_user_state_isolation.py`, 9 тестов + регрессия). ⬜ P0-1 A1 «Возвращение домой» (router view + табы «Главное/Расширенные»), B1–B3, C1–C3 — кандидаты. |
| 23 | Синтез режимов: «Не меню режимов, а одна учебная нить» | готово (2026-07-18; ревизия плана 2026-07-19; контр-аудит + фикс 2026-07-19) | [`23_one_calm_route.html`](23_one_calm_route.html) | [`../../next/one_calm_learning_route_plan.md`](../../next/one_calm_learning_route_plan.md) | ⬜ Кандидаты, не backlog entries. План актуализирован 2026-07-19: P0 `wave-one-route-core` требует каноническую Route Policy для home/plan/progress/KG и один shell решения с закрытой палитрой намерений. Runtime уже имеет SSR/Mission Control/план/Мнемополис как отдельные сильные поверхности, но единый primary route contract ещё не введён. Независимый контр-аудит снял переоцененную причинность («97 карточек → TopicB» не доказано при полном контексте) и развёл два дефекта: A — home не получает `plan_primary_block`, а scorer сейчас разрешает plan branch только на `surface="adaptive_plan"`; B — `get_weak_concepts()` без фильтра `weak_concepts_for_kg()` по активному графу в SSR и live-metrics путях, сейчас замаскировано живым `tutor_learning_resume`. |
| 24 | Качество квизов и честность mastery | **провизорно E1** (2026-07-19): code audit завершён; E2 live-семпл не выполнен, VLQR baseline не измерен | [`24_quiz_quality_mastery_honesty.html`](24_quiz_quality_mastery_honesty.html) | [`../../next/quiz_quality_mastery_honesty_plan.md`](../../next/quiz_quality_mastery_honesty_plan.md) | ⬜ Только кандидаты P0a/P0b, не backlog entries и не implementation. Подтверждён разрыв prompt rule → executable content gate и unsafe fallback-origin path в mastery. Контр-аудит удалил выдуманный proxy baseline `~45–55%` и заменил `source_span ≥40` на проверяемый exact-match evidence binding. Форматный долг: 10 секций и dark-only вместо эталонных 8/light+dark; реальный render не подтверждён из-за блокировки локального `file://`. |
| 25 | Ответ под присягой: semantic groundedness ответа | **провизорно E1** (2026-07-19): E1 перепроверен на runtime HEAD `1c9c56961`; E2 0/15 valid, SGAR baseline не измерен | [`25_grounded_answer_truth.html`](25_grounded_answer_truth.html) | [`../../next/grounded_answer_truth_plan.md`](../../next/grounded_answer_truth_plan.md) | ⬜ Только два P0-кандидата, gated E2; не backlog entries и не implementation. Подтверждено: online path проверяет citation/provenance structure, но не semantic entailment; cache-hit пропускает повторную validation; fixed `home_rag_gate` не является course-specific semantic gate. Live preflight: API/index/scope доступны, LM Studio вернул `503 Loading model`, retry-guard остановил повтор. Контр-аудит отклонил дублирование `chunk_text` в API debug и token-overlap как SGAR proxy: existing sources уже несут evidence text, semantic baseline требует независимой разметки. HTML: 8 секций, auto light/dark + print; desktop hero и §8 визуально проверены через local HTTP, блокирующих дефектов не найдено. |

Приоритизация и обоснование очерёдности (2026-07-11) сохранены отдельно в
памяти агента (`evolutionary-series-2026-07`).

**Программа следующих разборов (№26+), 2026-07-19:**
[`next_program_2026-07.html`](next_program_2026-07.html) — карта покрытия №1–23,
карта болей end-to-end пути, шесть кандидатов с оценками. №24 и №25 выполнены провизорно
(E1 complete, E2 missing); следующий пользовательский P0 — №27
«свой материал = полноценный урок». Главный прорывной
ход — «гейт учебного контента» (связка №24+№25). Это слой программы, не разбор —
номера присваиваются окончательно при выполнении.

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

> **Срез 2026-07-19.**  Строки #18–#23 выше пересверены с `hometutor` runtime и
> актуальными планами из `doc/next/`. #18/#20/#21 больше не считать “ждут промоута”:
> основная реализация уже закрыта. Реальный кодовый P0 теперь сосредоточен в #19,
> #22 и #23.

#### Новые/актуализированные планы разборов в `doc/next/`

| Разбор | Документ | Статус 2026-07-19 | Следующее решение |
|---|---|---|---|
| #18 3D-game | [`knowledge_graph_3d_game_plan.md`](../../next/knowledge_graph_3d_game_plan.md) | ✅ G0–G3, V2′/U0–U4, W0, G4.1/G4.2 закрыты; хвост синхронизирован с #20 | не открывать новый P0; только optional/live polish, если владелец хочет |
| #20 Мнемополис world | [`knowledge_graph_3d_world_vision.md`](../../next/knowledge_graph_3d_world_vision.md), [`knowledge_graph_3d_world_vision_review_report_2026-07-18.md`](../../next/knowledge_graph_3d_world_vision_review_report_2026-07-18.md) | ✅ v3.2: W0′–W6, Keeper, scene-DSL/NL, local PNG shipped | metrics + live/SR acceptance как отдельный polish, не core |
| #21 Mega Bundle | [`mega_bundle_catalog_plan.md`](../../next/mega_bundle_catalog_plan.md), [`mega_bundle_p0_p2_implementation_report.md`](../../next/mega_bundle_p0_p2_implementation_report.md) | ✅ P0-1, P0-2a, P1, P0-2b, P2 + owner order закрыты | manual DoD на реальном бандле; UI pin порядка курсов — optional |
| #22 Progress Mirror | [`progress_mirror_plan.md`](../../next/progress_mirror_plan.md) | ⬜ P0 открыт: orphan page + грязная память | промоутить `wave-progress-home` и `wave-progress-clean-room` |
| #23 One Calm Route | [`one_calm_learning_route_plan.md`](../../next/one_calm_learning_route_plan.md) | ⬜ P0 открыт: нет единой Route Policy между home/plan/progress/KG | промоутить после/вместе с #22 P0-2 |
| #19 Lecture Presence | [`lecture_presence_checkpoints_plan.md`](../../next/lecture_presence_checkpoints_plan.md) | ⬜ P0 открыт: lecture route и timed quiz gates не собраны | промоутить `P0-1 → P0-2`, не ждать #22/#23 |

#### 🔴 P0 — оставшиеся кодовые доработки

| Ход | Статус | Почему следующий |
|---|---|---|
| **#22 P0-2 «Чистое зеркало»** | ⬜ | Без изоляции/джойна/чистки Progress и Route Policy продолжают видеть тестовые следы (`TopicB`, 3650d intervals, fixture mastery). |
| **#22 P0-1 «Возвращение домой»** | ⬜ | `Мой прогресс` остаётся orphan page через `st.switch_page`, а `Прогресс обучения` — отдельный routed view; CTA и sidebar живут в разных навигационных мирах. |
| **#23 P0-1 Route Policy** | ⬜ | Home/Plan/Progress/KG выбирают primary next step разными правилами; нужен один read-only contract поверх SSR, без нового pipeline/DB. |
| **#23 P0-2 One Route Shell** | ⬜ | После policy нужна одна поверхность решения: один primary, reason, максимум две альтернативы, закрытая палитра намерений. |
| **#19 P0-1 Lecture Route** | ⬜ | Таймкоды уже есть, но нет маршрута 8–12 мин с clipped audio, progress и scoped quiz gate по timed-разделу. |
| **#19 P0-2 Simpler + Relisten** | ⬜ | Нужна короткая “проще” версия + переслушивание ровно проблемного отрезка, иначе 123-мин лекция остаётся одним битом listened. |

**Рекомендуемый порядок:** #22 P0-2 → #22 P0-1 → #23 P0-1 → #23 P0-2.
#19 можно вести параллельно: он опирается на media/scoped-quiz слой, а не на Progress/Route cleanup.

#### 🟡 P1/P2 и контентный остаток

| Приоритет | Ход | Статус |
|---|---|---|
| **P1 (контент)** | **#11** пересъёмка 06/30 | ⬜ кадры 2026-07-12; stamp честный, но перед внешним показом нужна свежая витрина |
| **P2 (решение владельца)** | **#16** дверь продукта | ⬜ «Учиться продукту» / HF-витрина — только по явному go |
| **P2 / optional** | **#15 B2** worth += audio/rubric signals | ⬜ плановый слой ценности, не blocker |
| **P2 / optional** | **#20 metrics** `time-to-first-action`, `hall_returns` | ⬜ observational, не wired |
| **P2 / optional** | **#20 live-polish/SR acceptance** | ⬜ structural gates есть; full live/SR acceptance отдельно |
| **P2 / optional** | **#21 manual DoD + course order UI pin** | ⬜ implementation закрыта, остаётся ручная проверка владельца/полировка |

#### ⚪ Закрытый крупный блок (credit)

#1–#10, #12–#18, #20–#21 имеют закрытые P0/P1 core-волны по runtime-сверке.
Особенно важно: #18 игровая петля, #20 Мнемополис world и #21 мега-бандл больше не являются текущим P0 backlog.

### Сводка по приоритетам (2026-07-19)

| Категория | Разборы |
|---|---|
| **P0 готово / core shipped** | #1–#10, #12–#18, #20–#21 |
| **P0 открыт** | #19 lecture route, #22 progress mirror, #23 one calm route |
| **Контент перед внешним показом** | #11 пересъёмка 06/30 |
| **Опционально / по решению владельца** | #15 B2, #16 P2, #20 metrics/live-polish, #21 manual DoD/UI pin |
| **Исторические HTML-снимки** | #1–#8 pain-якоря — не чинить код «под HTML» |
