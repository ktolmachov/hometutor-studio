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

## Как сделать новый разбор

1. Заполни промпт скриптом из этой же папки:

   ```bash
   python generate_analysis_prompt.py \
     --area "Первые 10 минут" \
     --role "новый студент" \
     --action "впервые открывает приложение" \
     --reality-domain "в онбординге (app/ui/mission_control.py, ...)" \
     --tension "простота ↔ глубина" \
     --tension "мощь ↔ фокус" \
     --pain "<факт, проверенный по коду перед запуском>"
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
   ниже. Если разбор тянет за собой реализацию — actionable-план кладётся
   отдельно в [`../../next/`](../../next/) (гайд, раздел 4), не сюда.

## Разборы

| № | Область | Статус анализа | Файл | Detail-plan | Рантайм-прогресс (2026-07-12) |
|---|---|---|---|---|---|---|
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

Приоритизация и обоснование очерёдности (2026-07-11) сохранены отдельно в
памяти агента (`evolutionary-series-2026-07`).

---

## Аудит точности серии (2026-07-13)

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

> **Срез 2026-07-15 (после wave-material-passport + audit-хвост #3/#9/#12).**  
> Все 🔴 P0 из аудита 2026-07-13 **закрыты в коде**. Ниже — только реальный остаток
> и честный backlog P1/P2. Исторические «Resolve»-заметки свёрнуты: трекер-таблица
> выше — SSoT статуса.

#### 🔴 P0 — кодовый долг аудита

| Ход | Статус | Примечание |
|---|---|---|
| #2 A1/A2 онбординг | ✅ | единые кандидаты + честный hero-статус |
| #3 A1/A2 freshness + audit-tail | ✅ | set-based gap; audit после activation; heuristic paths/hashes |
| #11 A1 freshness stamp + A2 YAML 31–35 | ✅ | stamp в `generate_demo_doc` / quickstart_demo; PNG в studio+runtime |
| #12 A1/A2 guards + budget | ✅ | **33/155/1942/361**; pytest + CI step |
| #14 A1/A2 паспорт рубрики + статус знания | ✅ | парсер, surfaces, `knowledge_status`/`open_question` |
| #15 A1/A2 + B1 3D-зал | ✅ | due/novel/worth + offline 3D export (floors, day_route flight) |

#### 🟡 Док-гигиена (колонка трекера + conventions)

| Что | Статус |
|---|---|
| #3 / #11 / #12 / #14 строки трекера | ✅ обновлены 2026-07-15 |
| size budget в `conventions_architecture.md` → 1942 | ✅ |
| «Темы и шрифты»: system-ui / ui-monospace, без Manrope/Plex | ✅ |
| flashcard iframe: mono без IBM Plex (N1) | ✅ |
| compiler/heuristic sidecar paths нормализованы (N4/N5) | ✅ |
| HTML pain-якоря #5/#6/#8 как исторический снимок | ⚪ допустимо; при rev. — «диагноз устарел» |

#### 🟢 P1/P2 — backlog

| Приоритет | Ход | Статус |
|---|---|---|
| **P1 (сделано)** | **#3 B1/B2** | ✅ passport + лестница `min_documents` (M1–M3 closed) |
| **P1 (сделано 2026-07-15)** | **#15 B1** | ✅ offline 3D-зал + audit P1–P3: script-safe export, sorted floors, dynamic grid, shared day_route 2D/3D |
| **P2 (сделано)** | **#3 C1/C2** | ✅ stale badge + learner-language status (+MC) |
| **P1 (сделано)** | **#16** beginner course | ✅ 5 экранов (36–38) + 6 MP4; dogfood README |
| **P1 (контент)** | **#11** пересъёмка 06/30 | ⬜ кадры 2026-07-12; stamp честный — переснять перед внешним показом |
| **P2 (контент)** | **#11** video / daily-use | ⬜ нарезка из YAML narration (жанр daily-use уже есть) |
| **P2 (решение владельца)** | **#16** дверь продукта | ⬜ «Учиться продукту» / HF-витрина — только по явному go |
| **P1 (код, опц.)** | **#15 B2** | ⬜ worth += audio/rubric signals (план) |

#### ⚪ Закрытый P1/P2 (краткий credit)

#1 B1/B2/C1 · #5 A2 · #6 B1 one-pager · #7 A3 coach→`get_today_primary` · #8 transient→circuit · #9 C2 local-first fonts · #13 C1–C3 telegram/segment · #14 B1–B3 + C1–C3 · #3 A–C · #15 A1/A2/B1.

### Сводка по приоритетам (2026-07-15, после #15 B1)

| Категория | Разборы |
|---|---|
| **P0+кодовый P1 готово** | #1–#10, #12–#16 (вкл. 3D-зал + курс 101 P1) |
| **Код закрыт в волне material+3D** | #3 full; #15 B1 3D |
| **Контент #16 P1 закрыт** | 5 экранов + 6 silent MP4; dogfood в README курса |
| **Остался контент** | #11 пересъёмка 06/30 (перед внешним показом) |
| **Опционально** | #15 B2 worth×audio/rubric; #16 P2 дверь «Учиться продукту» |
| **Исторические HTML-снимки** | #1–#8 pain-якоря — не чинить код «под HTML» |

**Рекомендуемый порядок дальше:** (1) #11 пересъёмка 06/30 перед внешним показом;
(2) #16 P2 — только по решению владельца (кнопка/HF); (3) #15 B2 — если нужны
сигналы audio/rubric в цене узла; (4) озвучка silent-видео курса — отдельный
продакшн, не блокер P1.
