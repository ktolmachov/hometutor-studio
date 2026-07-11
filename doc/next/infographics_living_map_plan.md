# Инфографика: живая карта материала — Implementation Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения — `backlog_registry.yaml`
этим документом не меняется, промоушен волн/пакетов решает владелец.
Owner: product / learning experience
Source: эволюционный разбор hometutor «Инфографика: живая карта материала» (спецвыпуск,
2026-07-11), формат —
[`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md).
Полный читаемый разбор:
[`../presentations/evolutionary_analyses/06_infographics.html`](../presentations/evolutionary_analyses/06_infographics.html)
(тот же контент опубликован как HTML-артефакт сессии:
https://claude.ai/code/artifact/302099ee-f1d6-41f9-b80a-a5d9f165aac7).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- [`material_as_product_quality_plan.md`](material_as_product_quality_plan.md) — detail-plan разбора №3
  (конспект/граф/таймкоды); этот план опирается на ту же граф-payload и media-sidecar инфраструктуру
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- hometutor: `docs/multimodal_konspekt_plan.md` (US-M2.2 «Обогатить раздел» — исходный контракт для P0-2),
  `docs/architecture.md`, `docs/conventions_architecture.md`, `docs/conventions_reference.md`, `CLAUDE.md`

## Как использовать этот документ

Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог
промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной.
Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted
tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне
согласованного write-set. Все evidence-ссылки проверены на `hometutor@fc0f696` (`159`).

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`.

## Суть разбора

Инфографика в hometutor — не жанр иллюстрации, а сжатие материала до формы, которую мозг
схватывает за секунды и с которой можно вернуться в материал (раздел·строка·минута видео).
Визуальный конвейер построен наполовину: рендереры (mermaid-парсер, инлайнер картинок,
d3-карта курса, plotly-слой прогресса) готовы и ждут; данные (граф-payload, section_index,
media-таймкоды, гейт качества графа) посчитаны и провалидированы; но между ними — три
разрыва. Ни один промпт не производит mermaid-схемы. Единственный самодостаточный
интерактивный HTML-артефакт (`build_kg_html`) собирается на каждый рендер и тут же
выбрасывается — наружу отдаётся только мёртвый SVG-снимок. Mermaid грузится с CDN, пока d3
уже вендорен — local-first продукт непоследователен сам с собой. План ниже — не про новую
визуализацию, а про то, чтобы соединить уже существующие половины конвейера.

---

## Волна-кандидат A: `wave-infographics-closure` (P0)

**North star (кандидат):** каждый готовый визуальный артефакт продукта (карта курса,
схема раздела) можно унести из приложения одним файлом — без похода в NotebookLM или
внешний редактор.

**Kill switch (кандидат):** если экспорт HTML-карты создаёт нагрузку поддержки (жалобы на
размер файла, битые ссылки на источники после переноса), сначала ограничить экспорт по
размеру графа/дать предупреждение, а не убирать кнопку — сама возможность выгрузки не
вызывает регресса существующего UI.

### Кандидат A1 — Кнопка «Скачать живую карту (HTML)»

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое (данные уже посчитаны, `build_kg_html` уже строит
готовую строку HTML — не хватает `st.download_button` поверх неё)

**Проблема.** `build_kg_html(payload)` собирает полностью самодостаточный интерактивный
HTML — вшитый d3, узлы, рёбра, уровни, кластеры, decay-vector, недельный план, диагностика
качества. Он вызывается на каждый рендер вкладки графа и используется единственно как
буфер для Streamlit-компонента. Наружу этот файл никогда не предлагается — притом что
паттерн «скачать markdown/файл кнопкой» уже используется в 13 других местах UI
(`print_view.py`, `topics_tab_*`, `flashcards_*`, `tutor_chat_footer.py` и др.).

**Evidence:**
- `app/ui/knowledge_graph_d3.py:590-606` (`build_kg_html`) — строит готовую строку HTML из
  `payload` (шаблон + JSON-плейсхолдеры + вшитый `d3.v7.min.js`, CDN только fallback
  на строке 592).
- `app/ui/knowledge_graph_d3.py:609-680` (`_kg_d3_component`, `render_d3_knowledge_graph`)
  — единственный сегодняшний потребитель: `components.declare_component(...)` рендерит HTML
  внутрь iframe компонента (строка ~670-680), сам HTML пользователю недоступен.
- `app/ui/dashboards_graph.py:1070-1078` — точка вызова `render_d3_knowledge_graph(...)`,
  куда возвращается `payload`; естественное соседство для кнопки — сразу после этого блока,
  рядом с уже существующей строкой статистики (`st.caption(...)`, строка 1084-1088).
- `app/ui/print_view.py:46-53` — образцовый паттерн `st.download_button(label=..., data=...,
  file_name=..., mime="text/markdown", ...)`, который можно скопировать с `mime="text/html"`.
- `app/ui/assets/knowledge_graph_d3_template.html:697-706` (KG-04) — существующий
  SVG-экспорт внутри самого компонента остаётся как есть, это отдельная (более лёгкая,
  статичная) возможность — не заменяется этим кандидатом.

**Proposed change:**
1. В `app/ui/dashboards_graph.py`, сразу после блока `st.caption(...)` со статистикой
   (после строки 1088), добавить `st.download_button("⬇ Скачать живую карту (HTML)",
   data=build_kg_html(payload), file_name="knowledge_graph.html", mime="text/html", ...)`.
2. `build_kg_payload`/`build_kg_html` уже импортированы транзитивно через
   `render_d3_knowledge_graph`; при необходимости — прямой импорт `build_kg_html` из
   `app.ui.knowledge_graph_d3`, вызов на уже возвращённом `payload` (пересчёт не нужен).
3. Никакой новой логики генерации — единственное новое действие: показать существующую
   строку пользователю через уже стандартный компонент Streamlit.

**Files:** `app/ui/dashboards_graph.py`, targeted test (smoke: кнопка присутствует и не
падает при пустом/непустом графе — ближайший relevant UI-test рядом с
`tests/test_navigation_visibility.py` или `tests/test_feature_registry.py`).

**DoD:**
- На вкладке графа доступна кнопка скачивания `knowledge_graph.html`; открытый локально
  файл воспроизводит интерактивную карту (узлы, зум, клики) без сети — d3 уже вендорен.
- Кнопка не появляется/не падает при пустом графе (тот же guard, что уже есть для
  остального контента вкладки, строки 1040-1046).
- Regression test фиксирует, что `build_kg_html(payload)` возвращает непустую строку с
  `<svg` и не содержит незамещённых `__PLACEHOLDER__`-токенов.

**Doc-sync:** `docs/user_guide.md` (новая возможность «скачать карту курса»),
`docs/architecture.md` (если там описан граф-рендеринг — добавить строку про экспорт).

**Dependencies:** нет — расширяет существующий, уже вызываемый путь. Независим от A2.

---

### Кандидат A2 — Схема раздела: передатчик к готовому mermaid-приёмнику

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** среднее (промпт-роль + preview UI + вендоринг зависимости)

**Проблема.** `living_konspekt_reader.py` уже парсит и рендерит блоки ```mermaid``` из
текста раздела в интерактивную SVG-диаграмму — но ни один промпт продукта такие блоки не
производит (grep `mermaid|диаграм` по `app/prompts/_impl.py` — 0 совпадений). Схема
появляется только если студент сам впишет её в markdown вручную. При этом контракт на эту
фичу («Обогатить раздел», US-M2.2) уже спроектирован 2026-07-05 в
`docs/multimodal_konspekt_plan.md` — код не начат. Отдельно: сам приёмник грузит
mermaid@11 с CDN, тогда как d3 в том же приложении вендорен — local-first продукт
непоследователен, и offline-схемы молча не рендерятся без предупреждения.

**Evidence:**
- `app/ui/living_konspekt_reader.py:140` (`_MERMAID_RE`) и `:196-276`
  (`render_markdown_with_mermaid`, `_render_mermaid_diagram`) — готовый приёмник; парсит
  ```mermaid```/```flowchart``` блоки из текста раздела, рендерит через
  `streamlit.components.v1.html`.
- `app/ui/living_konspekt_reader.py:253` — `import mermaid from
  'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs'` — единственная
  внешняя CDN-зависимость в этом рендере; сравнить с
  `app/ui/knowledge_graph_d3.py:591-592` (`_load_d3_source()`, локальный
  `assets/d3.v7.min.js`, CDN только как fallback) — образец, как это должно быть сделано.
- `docs/multimodal_konspekt_plan.md` US-M2.2 (раздел 6, Epic M2) и backlog-пункт
  «M2.2 Section enrichment preview» (раздел 9) — готовый контракт: промпт в
  `app/prompts/`, preview принять/отклонить, результат содержит
  схему/пример/аналогию/термины, декоративный контент запрещён prompt rule, запись только
  по явному подтверждению.
- `app/prompts/_impl.py:1137-1148` (`PROMPT_ROLE_CONTRACT`) — реестр ролей промптов с
  форматом (`system_user`/`user_only`) и обоснованием; новая роль (например
  `section_diagram`) регистрируется здесь по тому же паттерну.
- `app/provider.py` — существующие ролевые фабрики (`get_graph_llm()` строка 654,
  `get_obsidian_export_llm()` строка 621, `get_evaluate_llm()` строка 645) — образец, через
  какую фабрику должна идти LLM-роль для генерации схемы; новую отдельную роль заводить
  только если существующая (`get_graph_llm()`, ближе всего по домену — концепты/связи)
  не подходит по параметрам вызова.
- `app/ui/living_konspekt_workbench_panel.py:357-373`
  (`st.session_state["fc_preview_cards"]`, `_clear_flashcards_preview_widget_state`) —
  существующий паттерн preview-состояния в этом же модуле (карточки-кандидаты перед
  подтверждением) — модель для preview-состояния схемы раздела, тот же файл уже содержит
  вызов `render_markdown_with_mermaid` (строка 222-224).

**Proposed change:**
1. Вендорить `mermaid@11` (или актуальную зафиксированную версию) в
   `app/ui/assets/` по образцу `_load_d3_source()` в `knowledge_graph_d3.py`; в
   `_render_mermaid_diagram` заменить прямой `import from 'https://cdn.jsdelivr.net/...'`
   на инлайн `<script>` с вендоренным содержимым, CDN оставить только как fallback (тот же
   паттерн, что и `__D3_TAG__`).
2. Новая промпт-роль `section_diagram` в `app/prompts/_impl.py`: вход — текст раздела
   (`own_text` из `IndexedSection`), выход — строго один блок ```mermaid``` (flowchart/mind
   map, без произвольного текста вне диаграммы), coherence-правило запрещает декоративную
   схему без структурной сути раздела. Роль регистрируется в `PROMPT_ROLE_CONTRACT`.
3. Вызов идёт через существующую provider-фабрику (кандидат — `get_graph_llm()`, финальное
   решение — на этапе реализации, с обоснованием в PR).
4. Кнопка «Схема раздела» в `living_konspekt_workbench_panel.py` (рядом с существующим
   вызовом `render_markdown_with_mermaid`, строка 222-224): генерирует mermaid-код →
   кладёт в `st.session_state` как preview → рендерит через уже существующий
   `_render_mermaid_diagram` для предпросмотра → кнопки «Принять» (дописывает блок в текст
   раздела через существующий write-path конспекта) / «Отклонить» (очищает preview state).
5. Ничего не пишется в markdown без явного подтверждения — тот же принцип, что и
   flashcards preview в этом же файле.

**Files:** `app/ui/assets/` (новый вендоренный mermaid asset), `app/ui/living_konspekt_reader.py`
(`_render_mermaid_diagram` — переключить источник скрипта), `app/prompts/_impl.py` (новая
роль + `PROMPT_ROLE_CONTRACT` запись), `app/provider.py` (только если существующая фабрика
не подходит — иначе без изменений), `app/ui/living_konspekt_workbench_panel.py` (кнопка +
preview state), targeted tests (prompt registry test рядом с существующими для
`PROMPT_ROLE_CONTRACT`, UI smoke test для preview/accept/reject).

**DoD:**
- `render_markdown_with_mermaid` рендерит диаграммы offline (без сети) — вендоринг
  подтверждён тестом или ручной проверкой с отключённым интернетом.
- Кнопка «Схема раздела» генерирует ровно один mermaid-блок; результат показывается как
  preview до подтверждения; отказ не меняет текст раздела.
- Декоративная генерация (схема без структурной связи с текстом) исключается
  prompt-правилом — задокументировано в тексте промпта.
- Промпт-роль зарегистрирована в `PROMPT_ROLE_CONTRACT`, вызов LLM проходит только через
  `app/provider.py`.

**Doc-sync:** `docs/multimodal_konspekt_plan.md` (обновить статус US-M2.2 с «ТЗ» на
реализовано/частично), `docs/conventions_reference.md` (если добавляется новая
prompt-роль — свериться с правилами реестра), `.env.example`/`config.env` (только если
вводится runtime-флаг для этой фичи — по умолчанию решение НЕ вводить лишний флаг, см. п.
«анти-цели» в `docs/multimodal_konspekt_plan.md` §8).

**Dependencies:** независим от A1. Вендоринг mermaid — самостоятельная под-задача, может
быть сделана первой и отдельно, даже до генерации.

---

## Волна-кандидат B: `wave-infographics-onepager` (P1)

**North star (кандидат):** любая лекция имеет одну страницу-карту — детерминированную,
без LLM, доступную в первый день изучения курса.

### Кандидат B1 — «Одна страница лекции» (детерминированный one-pager)

**Статус:** `proposed`, требует discovery по месту размещения UI

**Приоритет:** P1 · **Усилие:** среднее-крупное (новый агрегатор + рендер-шаблон по
образцу существующего, но без новых вычислений верхнего уровня)

**Проблема/возможность.** Три источника данных уже посчитаны независимо и никогда не
сведены в один визуальный артефакт: структура лекции (`section_index.py`), концепты и связи
конкретной лекции (уже присутствуют в `build_kg_payload`), таймкоды разделов (media
sidecar). Студент, открывающий лекцию в первый раз, не получает ориентацию за 30 секунд —
именно то, чего просит страх «утонуть в материале» (разбор №2, время до первого инсайта).
Ни граф целиком (tier 3, слишком широк — весь курс, не одна лекция), ни голый markdown
конспекта (нет визуальной формы) не закрывают эту потребность напрямую.

**Evidence:**
- `app/section_index.py:196-239` (`build_section_index`) — уже возвращает
  `list[IndexedSection]` со slug, `line_start/end`, `own_text` для одного документа —
  готовый скелет one-pager.
- `app/ui/knowledge_graph_d3.py:481-587` (`build_kg_payload`) — уже строит `nodes`, `edges`,
  `levels`, `cluster_labels`, `decay_vector`, `mastery_history` для всего курса; для
  one-pager лекции нужна фильтрация по `source_paths`/`doc_index` конкретного документа
  (уже есть паттерн — `dashboards_graph.py:1056-1068` строит `source_paths` из
  `get_active_scope()`).
- `app/media_sidecar.py:313-340` (`load_media_sidecar_for_konspekt`,
  `load_media_sidecar`) — уже читает таймкоды разделов (`MediaSection`, включая `t_start`,
  `confidence`) при наличии sidecar; при его отсутствии/устаревании — деградация без
  таймкодов (см. существующий паттерн stale-состояний в
  `docs/multimodal_konspekt_plan.md` §10, таблица UI-состояний).
- `app/ui/knowledge_graph_d3.py:590-606` (`build_kg_html`) — образец паттерна рендера
  «шаблон + JSON-плейсхолдеры»: новый one-pager рендерится тем же способом (свой HTML
  шаблон в `app/ui/assets/`, свой `build_lecture_onepager_html(payload)`), не переиспользуя
  граф-шаблон напрямую (разное содержимое — секции лекции, не весь курс).
- `app/ui/print_view.py:11-28,46-53` (`open_print_view`, download button) — готовая точка
  выдачи: one-pager можно предложить как альтернативный download рядом с уже существующим
  «Скачать Markdown» — не новый экран, тот же паттерн, что A1.

**Discovery перед реализацией:**
1. Где именно в UI размещается вход в one-pager — шапка Живого конспекта (новая кнопка
   рядом с текущими действиями раздела) или «Чистый вид» (второй download рядом с .md) —
   решить на этапе реализации по существующей навигации, не вводя новый top-level view
   (правило из плана №3, кандидат B1 — «не новый экран»).
2. Нужен ли отдельный лёгкий JSON-контракт `LectureOnepagerPayload` (id секции, заголовок,
   диапазон строк, топ-концепты секции, таймкод, mastery/decay overlay опционально) или
   достаточно фильтрованного среза `build_kg_payload` — решить после первого прототипа.
3. LLM не требуется на этом шаге — если на этапе реализации захочется подписи/аннотации,
   это отдельный follow-up с prompt-ролью, не блокирует базовый one-pager.

**Files после discovery:** новый модуль-билдер (например `app/lecture_onepager.py`), новый
HTML-шаблон в `app/ui/assets/`, точка вызова в `app/ui/living_konspekt_reader.py` или
`app/ui/print_view.py`, targeted tests.

**DoD (после discovery):**
- One-pager собирается детерминированно (без LLM-вызова) из уже существующих данных.
- Отсутствие media sidecar/таймкодов не блокирует one-pager — секции без таймкода
  показываются без соответствующей кнопки (тот же degraded-state принцип, что в
  `docs/multimodal_konspekt_plan.md` §10).
- Клик по элементу one-pager ведёт в точное место лекции (раздел или, при наличии
  валидного таймкода, минуту видео) — центральная метрика ценности (см. North star волны C).

**Doc-sync:** `docs/user_guide.md` (новая возможность), `docs/architecture.md` (новый
модуль, если появляется).

**Dependencies:** выигрывает от готовности A1 (тот же паттерн рендера/download), но
технически независим — может стартовать параллельно.

---

## Волна-кандидат C: `wave-infographics-mirror` (P2)

**North star (кандидат):** инфографика знает, что студент уже знает — то, чего не может
дать ни один внешний генератор картинок.

### Кандидат C1 — Mastery/decay overlay («Моя карта»)

**Статус:** `proposed`, зависит от B1

**Приоритет:** P2 · **Усилие:** малое поверх B1 (данные уже посчитаны)

**Проблема/возможность.** `build_kg_payload` уже вычисляет `decay_vector` (retention
0..1 на концепт) и `mastery_history` — но эти данные используются только внутри
интерактивного графа курса (tier 3), не проецируются на one-pager конкретной лекции.

**Evidence:**
- `app/ui/knowledge_graph_d3.py:583-585` — `decay_vector` (KG-06) и `mastery_history` (KG-07)
  уже присутствуют в возвращаемом payload `build_kg_payload`.

**Proposed change:** после реализации B1 — добавить опциональный overlay-слой на one-pager:
цвет/интенсивность блока секции по mastery концептов этой секции, тлеющий индикатор по
`decay_vector`. Никаких новых вычислений — проекция уже существующих чисел на уже
существующий one-pager.

**Files:** тот же билдер/шаблон, что в B1.

**DoD:** one-pager с overlay визуально отличает «знаю» / «забываю» / «не проходил» без
дополнительного запроса к БД сверх уже используемого в B1.

**Doc-sync:** `docs/user_guide.md`.

**Dependencies:** строго после B1 — overlay накладывается на уже существующий one-pager,
самостоятельной ценности без него не несёт.

---

### Кандидат C2 — Телеметрия «CTR возврата»

**Статус:** `proposed`, требует discovery по месту хранения метрики

**Приоритет:** P2 · **Усилие:** малое

**Проблема/возможность.** North star всего разбора — доля кликов из инфографики,
приводящих в раздел/минуту видео — сейчас нечем измерить: ни A1 (скачанный файл), ни B1
(one-pager) не производят событие клика обратно в систему.

**Discovery перед реализацией:**
1. Скачанный HTML-файл (A1) открывается вне Streamlit-сессии — трекать клики внутри него
   можно только через deep-link обратно в приложение (аналогично `obsidian_uri`/`vscode_uri`
   в `app/obsidian_export.py`), что требует отдельного протокола; для one-pager (B1),
   встроенного в саму сессию, трекинг проще — событие можно писать через существующий
   телеметрический путь (см. образец «телеметрия дверей» в разборе №2).
2. Нужно решить: единая метрика для A1+B1 или раздельные — после того, как оба кандидата
   реализованы.

**Files после discovery:** телеметрический модуль (существующий, если есть, иначе — по
образцу телеметрии из разбора №2), дашборд метрик (`app/ui/pages/4_Аналитика.py` или
`app/ui/data_views.py`).

**Doc-sync после реализации:** `docs/architecture.md` (если добавляется новое событие).

**Dependencies:** имеет смысл только после A1 и B1 — измерять нечего, пока нет самих
артефактов.

---

## Рекомендованный порядок реализации

1. **A1** — кнопка скачивания живой карты курса; самый дешёвый ход, данные уже посчитаны,
   демонстрирует ценность жанра «живой HTML» немедленно.
2. **A2** — передатчик схем раздела + вендоринг mermaid; можно вести параллельно с A1
   (разные файлы), вендоринг mermaid — независимая под-задача, можно сделать первой.
3. **B1** — «Одна страница лекции»; крупнейший кандидат, стартует после A1 (переиспользует
   его паттерн рендера) и не зависит от A2, но выигрывает от готового mermaid-приёмника,
   если решится включать схемы в one-pager.
4. **C1** — mastery/decay overlay; строго после B1, дешёвая надстройка.
5. **C2** — телеметрия CTR возврата; последней, измеряет эффект уже сделанных A1/B1, не
   пустоту.

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../presentations/evolutionary_analyses/README.md`](../presentations/evolutionary_analyses/README.md) — индекс серии разборов
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`material_as_product_quality_plan.md`](material_as_product_quality_plan.md) — detail-plan разбора №3 (материал/граф/таймкоды)
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan разбора №2 (онбординг)
- hometutor: `docs/multimodal_konspekt_plan.md` (US-M2.2), `docs/architecture.md`,
  `docs/conventions_architecture.md`, `docs/conventions_reference.md`, `CLAUDE.md`
