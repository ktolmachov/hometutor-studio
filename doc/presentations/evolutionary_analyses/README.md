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
| 3 | Материал как продукт (конспект, граф, таймкоды) | готово (2026-07-11) | [`03_material_as_product.html`](03_material_as_product.html) | [`../../next/material_as_product_quality_plan.md`](../../next/material_as_product_quality_plan.md) | ✅ P0 (2026-07-13, wave-material-freshness): A1 видимый индекс свежести карты — `graph_freshness_gap()` + сегмент «🗺 Карта отстаёт: N материалов не на карте» в context row Mission Control (`_compact_report` хранит `source_paths_count`); A2 аудит дубликатов концептов в штатный реиндекс-хвост (`write_graph_audit_report` после `published` в full/partial). Ранее: inline badges, Mermaid-валидатор (**14** типов, не 10), 🔎 fix-кнопка no_sections в audit графа |
| 4 | Агент как одна кнопка (Agent Coach → UI) | готово (2026-07-11) | [`04_agent_as_one_button.html`](04_agent_as_one_button.html) | [`../../next/agent_as_one_button_plan.md`](../../next/agent_as_one_button_plan.md) | ✅ FeatureSpec + tile + view + POST `/ask` c `query_mode:"agent"`. Gate `AGENT_ENABLED` проверен в feature_visible и navigation_visibility. Трассировка агента (scenario, tool calls) в ответе |
| 5 | Доверие под нагрузкой (провайдер, скорость, честность fallback) | готово (2026-07-11) | [`05_trust_under_load.html`](05_trust_under_load.html) | [`../../next/trust_under_load_provider_plan.md`](../../next/trust_under_load_provider_plan.md) | ✅ timeout propagation исправлен (llama-index 60s → 30s), soft timeout 15s через ThreadPoolExecutor, тест soft timeout |
| 6 | Инфографика: живая карта материала (спецвыпуск, вне очереди) | готово (2026-07-11) | [`06_infographics.html`](06_infographics.html) | [`../../next/infographics_living_map_plan.md`](../../next/infographics_living_map_plan.md) | ✅ velocity/sessions/interactions в stats-бар графа, единый `_enrich_stats_with_learner_velocity()` для `build_kg_payload` и `compute_kg_counters` |
| 7 | План обучения: стол, который забывает, где вы сидите | готово (2026-07-11) | [`07_learning_plan.html`](07_learning_plan.html) | [`../../next/learning_plan_single_source_plan.md`](../../next/learning_plan_single_source_plan.md) | ✅ C1 bridge: `learning_plan_context` обновляется при загрузке кэшированного плана |
| 8 | Невидимая половина (метаразбор серии: сильный ход к шедевру) | готово (2026-07-12) | [`08_invisible_half.html`](08_invisible_half.html) | [`../../next/invisible_half_closure_plan.md`](../../next/invisible_half_closure_plan.md) | ✅ P0: AGENT_ENABLED gate, tier/requirement split в навигации, stale view не пробивает requirement |
| 9 | Своя комната (цветовые схемы «миры» + фоны мирового уровня) | готово (2026-07-12) | [`09_color_worlds.html`](09_color_worlds.html) | [`../../next/color_worlds_theming_plan.md`](../../next/color_worlds_theming_plan.md) | ✅ A1: `:root` расширен (9→22 токена), литералы `.stApp`/`.hero`/`.chip`/`.home-dash-head-*`/`.flashcard-*` → `var(--)`. A2: `theme_presets.py` (5 миров, полные gradient-строки head). B1: `get_ui_theme()`/`set_ui_theme()`. B2: `inject_theme_overrides()` после auth. B3: вкладка «Оформление». C3: токены темы в flashcard iframe. ✅ `tests/test_theme_presets.py` (5), `test_ui_preferences.py` (+4 теста темы). |
| 10 | Кольцо замкнулось, но беззвучно (финал: синтез разборов №1–№9) | готово (2026-07-12) | [`10_full_circle.html`](10_full_circle.html) | [`../../next/full_circle_visibility_plan.md`](../../next/full_circle_visibility_plan.md) | ✅ A1: learner trace в tutor chat (`ctx.metadata` → `assistant_meta` → `tutor_meta` → visible string). A2: due badge `flashcard_due_n + sm2_due_n` в SSR banner «К повторению: N (сумма двух очередей)». |
| 11 | Витрина обещаний: сценарии против реальности | готово (2026-07-12) | [`11_usage_scenarios.html`](11_usage_scenarios.html) | [`../../next/usage_scenarios_refresh_plan.md`](../../next/usage_scenarios_refresh_plan.md) | ⬜ P0: freshness stamp + 5 YAML-манифестов слепых зон; пересъёмка 06/30 после Full Circle P0 |
| 12 | Архитектура и дизайн (первый инженерный: стены без сигнализации) | готово (2026-07-12) | [`12_architecture_design.html`](12_architecture_design.html) | [`../../next/architecture_guards_plan.md`](../../next/architecture_guards_plan.md) | ✅ P0 (2026-07-13): константы `check_size_budget` сверены с HEAD (33/155/1929/361) + waiver `app/prompts/_impl.py`; новый `tests/test_architecture_guards.py` — провод 4 стражей в pytest/CI (`arch_regression_guards.py` → exit 0) |
| 13 | Аудио-подкасты: конспекты и части лекций в уши | готово (2026-07-13) | [`13_audio_podcasts.html`](13_audio_podcasts.html) | [`../../next/audio_podcasts_plan.md`](../../next/audio_podcasts_plan.md) | ✅ P0/A2 закрыты после критического аудита: sibling `.m4a` discovery + `st.audio(..., format="audio/mp4")` разделов, слушаемый плейлист, офлайн-извлечение аудио в PS-конвейере, «Выпуск в дорогу» (m4a + TOC). Закреплены фиксы blocker'ов: `extract_audio_to_m4a(str)`, path-safety для absolute path, исключение `end=None` из concat, регрессионные тесты + Windows CI `test-media-pipeline-audio`. |
| 14 | Качество конспектов (включая Живые): паспорт написан, продукт показывает галочку | готово (2026-07-13) | [`14_konspekt_quality.html`](14_konspekt_quality.html) | [`../../next/konspekt_quality_plan.md`](../../next/konspekt_quality_plan.md) | ⬜ P0: прочитать готовую рубрику качества (роль + парсер + паспорт вместо «✅ готовы»); статус знания (3 состояния) + «мой открытый вопрос» в строке корзины |
| 15 | 3D граф знаний: карта, которая не знает цену своих узлов | готово (2026-07-13) | [`15_knowledge_graph_3d.html`](15_knowledge_graph_3d.html) | [`../../next/knowledge_graph_3d_plan.md`](../../next/knowledge_graph_3d_plan.md) | ✅ P0 (HEAD 216, wave-kg-node-worth): поле `due` (due_reviews→{cid:n_due}) + `novel` + честная шапка `total_concepts`/`total_lessons` (89→76); `worth(node)` в `knowledge_graph_d3_analysis.py` (веса due/novel/decay/frontier/reach) + кнопка «Авто: маршрут дня» по ценности; B1 `build_kg_3d_html` (3D-зал) начат. Тесты `test_knowledge_graph_counters.py::TestNodeWorth` + A1-wiring |
| 16 | Учебный курс по продукту (первый разбор типа «обучение»: продукт учит всему, кроме себя) | готово (2026-07-14) | [`16_beginner_course.html`](16_beginner_course.html) | учебный комплект вместо detail-плана: [`../../courses/hometutor_101/`](../../courses/hometutor_101/) | ✅ P0 выпущен вместе с разбором: курс «hometutor 101» — 6 лекций + 6 конспектов с рубрикой (валидатор `validate_smart_konspekt.py --profile local`: OK ×6) + 6 видео-сценариев на кадрах витрины + слайд-дек (16 слайдов) + dogfood-README. Шаблон серии расширен вариантом «разбор-обучение» (`evolutionary_analysis_guide.md` §2.1, v1.2). ⬜ P1: снять 5 экранных состояний — маршрут дня, паспорт конспекта, статусы раздела, счётчики, «Оформление» — и собрать видео |

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

**🔴 P0 — несделанная работа в коде (главное)**

> Обновлено по результатам работы: многие пункты закрыты (см. Resolve ниже и пометки).

| Ход | Где | Что сделать |
|---|---|---|
| #2A1 единый кандидат первого обзора | `app/ingestion_index_full.py:357`, `ingestion_index_partial.py:273` | demo/uploads → first-session артефакт ✅ (закрыто ранее) |
| #2A2 честный статус | `app/ui/mission_control_first_session.py:217` | убрать безусловный `st.info("…готовится…")` — это боль-якорь №2 ✅ (закрыто ранее) |
| #3A1 индекс свежести карты | `app/ui/mission_control.py:928` | сегмент «Карта отстаёт»/freshness-gap ✅ (set-based + source_paths + source_content_hashes в heuristic, нормализация) |
| #3A2 аудит дубликатов в реиндекс | `app/knowledge_graph_audit.py:202` | подключить `write_graph_audit_report` к штатному реиндексу ✅ (уже было подключено, улучшено покрытие тестов + proof в orchestrator) |
| #12A2 сверить константы бюджета | `scripts/check_size_budget.py:15-18` | `34/155/1928/361` + waiver (иначе вечный красный CI) ✅ |
| #12A1 стражи в pytest | `tests/test_architecture_guards.py` (создать) | параметризованная обёртка над 4 стражами ✅ + явный шаг в .github/workflows/ci.yml |
| #15A1 цена на узле графа | `app/ui/knowledge_graph_d3.py:569-583`, `template:305` | `due` (сейчас due_reviews собираются и выбрасываются `:649→:525-604`); `novel`; шапка 89→76 ✅ (закрыто ранее) |
| #15A2 «Маршрут дня» по ценности | `template:679` `_bfsPath` | чистая `worth(node)` вместо невзвешенного BFS ✅ (закрыто ранее) |
| #11 синхронизация scenario_31–35 | `hometutor-studio/doc/screenshots/final/` → `hometutor/docs/screenshots/final/` | PNG-артефакты 31–35 есть в studio; проверить/синхронизировать runtime-копию перед внешним показом ✅ (скриншоты присутствуют в runtime; очищены «Capture pending» и описания в user_scenarios.md) |

**🟡 Док-гигиена колонки (дёшево, устраняет ложь)**

- #2 `✅` → частично/⬜ (P0 не сделан)
- #3 «10 типов» → **14**; отметить, что P0 не сделан
- #1 тестов **11** не 8; описать девиацию A2 (`mastery_vector` обновляется, хотя план требовал exposure-only)
- #5/#6/#8 дополнить ячейки: credit реальных P0 (circuit feeding / download+mermaid / memory trace); боль-якоря устарели
- #9 токенов **45** не 22; тестов **6** не 5
- #11 синхронизировать scenario_31–35 из studio в runtime-витрину, если внешний показ читает `hometutor/docs/screenshots/final/` ✅ (скриншоты есть + очищены pending в user_scenarios.md)
- #14 ⬜ → ✅ (P0 закоммичен)
- Дополнительно: обновлены user_guide.md (убраны внутренние #2A/#3A), conventions_architecture.md (убрано «ежедневно», добавлен явный CI шаг, добавлен раздел про шрифты), explicit guards step в ci.yml.

**🟢 P1/P2 — вторичные пробелы**

- #1 B1 карточка из ответа тьютора; B2 единая очередь; C1 derived `mastery_vector`
- #5 A2 короткий timeout для known-unhealthy ветки ✅ (в llm_resilience при _circuit_open используем min(soft, 1.5s) для complete/chat); B1 бейдж источника LLM в tutor chat
- #6 B1 one-pager лекции
- #7 A3 unify coach/weekly к `get_today_primary_learning_item()` (`dashboard.py:43`, `pages/3_Мой_прогресс.py:171`)
- #8 circuit срабатывает только на `_is_connection_error`, не на таймауты/5xx (`llm_resilience.py:208-209`) ✅ (расширено _is_connection_error на timeouts + 5xx, обновлён docstring)
- #9 C2 шрифты с Google CDN (`ui_theme.css:1-2`) — разрыв local-first ✅ (убраны импорты Manrope/IBM Plex, только Material Symbols для иконок + системные стеки + переменные)
- #13 C1–C3 telegram-доставка / диалоговый подкаст / сегмент дня
- #14 C2 мёртвая фабрика B (`smart_konspekt`, `FileNotFoundError` в чистом чекауте) ✅ (fallback default prompt в get_smart_lecture_konspekt_universal_prompt); C3 факты ↔ интерпретации

**⚪ Устаревшие HTML-pain-якори (#5, #6, частично #8).** Разборы №1–8 — исторические
снимки (см. выше §9). Их боль-якорья («grep circuit → пусто», «mermaid с CDN»,
«download не предлагается») уже разрешены кодом, но в HTML читаются как текущие.
Допустимо как снимок; при следующей ревизии — пометить «диагноз устарел — см. коммит».

### Сводка по приоритетам

- **Готово и точно**: #4, #7, #10, #13
- **Готово, README неточен (числа/credit)**: #1, #5, #6, #8, #9
- **Завышено ✅, P0 не сделан**: (обновлено)
- **Занижено ⬜, на самом деле сделано**: #14 (+ частично #11)
- **Точно ⬜, работа впереди**: #11 runtime-sync (частично закрыт)
- Дополнительно закрыто в этой сессии: #3A1/#3A2 полностью (set-based freshness + heuristic source_paths/hashes), #12A1 (CI visibility), #9 C2 (fonts), #8 (transient errors), #5 A2 (short timeout unhealthy), #14 C2 (prompt fallback), док-гигиена.

> **Resolve (2026-07-13, позднее).** Два рекомендованных хода закрыты — аудит выше
> был снимком ≤HEAD 208; рантайм к моменту исполнения ушёл на HEAD 216:
> - **#12A сделан**: константы `check_size_budget` сверены с HEAD
>   (33/155/1929/361) + waiver `app/prompts/_impl.py`; новый
>   `tests/test_architecture_guards.py` проводит 4 стража в pytest/CI;
>   `arch_regression_guards.py` → exit 0. (Строка трекера #12 обновлена ⬜→✅.)
> - **#15A уже в HEAD 216**: поля `due`/`novel` на узле (`due_reviews`→{cid:n_due}),
>   `worth(node)` в `knowledge_graph_d3_analysis.py` (веса due/novel/decay/frontier/reach),
>   кнопка «Авто: маршрут дня» по ценности вместо BFS, честная шапка
>   `total_concepts`/`total_lessons` (89→76), B1 3D-зал `build_kg_3d_html` начат;
>   тесты `test_knowledge_graph_counters.py::TestNodeWorth`. (Строка #15 ⬜→✅.)
>
> Реальным пробелом серии остаётся только #11 runtime-sync (частично закрыт: скриншоты присутствуют в hometutor/docs, очищены pending-статусы в user_scenarios.md).
> **#2 P0 закрыт**, **#3 P0 закрыт** (включая heuristic-путь source_paths + source_content_hashes в
> knowledge_graph_bundle, set-based freshness gap, нормализация). 
> **#12A1** улучшен (явный шаг в ci.yml + обновлена документация).
> **#9 C2** (шрифты) почищен (local-first для текста).
> **#8**, **#5 A2**, **#14 C2** тоже закрыты в этой сессии.
> Строки трекера и гигиена обновлены. Дополнительно закрыт **#1 B1**. Флаг
> `enable_first_session_precompute` задокументирован. user_guide и conventions очищены от внутренних меток.
