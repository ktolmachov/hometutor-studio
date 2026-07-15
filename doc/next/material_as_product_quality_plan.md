# Material as Product — Quality Surfacing Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения — `backlog_registry.yaml`
этим документом не меняется, промоушен волн/пакетов решает владелец.
Owner: product / learning experience
Source: эволюционный разбор hometutor «Материал как продукт» (2026-07-11), формат —
[`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md).
Полный читаемый разбор:
[`../presentations/evolutionary_analyses/03_material_as_product.html`](../presentations/evolutionary_analyses/03_material_as_product.html)
(тот же контент опубликован как HTML-артефакт сессии).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan разбора №2 (онбординг);
  делит один корень с P0-1 этого плана — недоступность локального LLM молча ломает и первый ответ, и promote графа
- [`learning_loop_simplicity_plan.md`](learning_loop_simplicity_plan.md) — detail-plan разбора №0 (UI/фокус)
- hometutor: `docs/architecture.md`, `docs/conventions_architecture.md`, `docs/api_reference.md`, `CLAUDE.md`

## Как использовать этот документ

Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог
промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной.
Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted
tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне
согласованного write-set. Все evidence-ссылки проверены на `hometutor@60b55f3` (`149`).

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`.

## Суть разбора

Материал становится продуктом, когда сырая лекция превращается в живой учебник: индекс,
семантическая карта, конспект и честные таймкоды. Три независимые производственные линии
(in-app reindex, offline ASR/конспект/media-alignment, student-facing Живой конспект)
делают свою работу хорошо и честно — у каждой есть встроенный инструмент качества
(gate графа, media confidence, konspekt provenance). Проблема не в качестве, а в том, что
доказательства качества не доходят до студента: карта может молча отстать от индекса,
аудит дубликатов концептов запускается только вручную, а порог «граф начинается с 3
документов» никак не объясняется.

---

## Волна-кандидат A: `wave-material-freshness` (P0)

**North star (кандидат):** после каждого успешного реиндекса индекс свежести карты равен
нулю; если гейт не пройден или LLM недоступна, студент видит человекочитаемый статус на
главном экране — не только в логе и не только во вкладке графа.

**Kill switch (кандидат):** если показ индекса свежести приводит к тому, что пользователи
массово запускают лишние реиндексы при разнице, объяснимой нормальной задержкой
(секунды между завершением индексации и записью графа), добавить debounce-порог перед
показом бейджа, а не убирать сам сигнал.

### Кандидат A1 — Видимый индекс свежести карты

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое (обе величины уже существуют, не хватает одного поля в существующем ответе)

**Проблема.** Когда promote графа пропускается (гейт не пройден или LLM недоступна),
единственный след — строка в логе `knowledge_graph_promote_skip`. Активным продолжает
служить граф предыдущего поколения. Студент видит новую лекцию в Быстром ответе, но не
на карте/в плане/в SSR — без единого объяснения на изучаемых им экранах.

**Evidence:**
- `app/graph_generation_paths.py:40-73` (`promote_staging_bundle`) — при
  `not staging_bundle_gate_allows_promote(...)` только `logger.info(...)`, возврат `False`.
- `app/knowledge_graph.py:947` (`use_compiler = graph_llm_probe_ok()`) — при недоступной
  LLM компилятор не используется, эвристический путь честно ставит `gate_passed=False`
  (`knowledge_graph_bundle.py:300-310`).
- `app/graph_publish_status.py:76-113` (`get_graph_publish_status`) — уже вычисляет
  `reader_source` (active/previous/legacy) и `latest_failed_staging`, но
  `_compact_report()` (`graph_publish_status.py:9-28`) **отбрасывает поле `source_paths`**
  из report при компактизации для UI — оно есть в сыром report
  (`knowledge_graph_bundle.py:216`, `report_dict["source_paths"] = list(source_paths or [])`),
  но не доходит до потребителей `get_graph_publish_status()`.
- `app/ui/dashboards_graph.py:693-726` (`_render_graph_publish_status`) — единственный
  сегодняшний потребитель статуса, живёт только во вкладке графа, языком разработчика
  («Published graph bundle не найден»).
- `app/ui/mission_control.py:889-912` (`build_context_row_segments`) — уже используемый,
  протестированный паттерн: pure builder списка коротких сегментов для контекстной строки
  Mission Control (сейчас — курс + XP/стрик); `_render_context_row()` (строка 915) рендерит
  их. Естественное место для нового сегмента, без нового UI-компонента.

**Proposed change:**
1. `_compact_report()` в `graph_publish_status.py` сохраняет `source_paths` (или сразу
   `len(source_paths)`) активного бандла — минимальное расширение существующей функции.
2. Новый pure helper (например `graph_freshness_gap(index_stats, publish_status)` рядом
   с `get_graph_publish_status`) считает `len(индексированные пути) − len(source_paths
   активного графа)` по уже нормализованным путям (`normalize_source_paths`,
   `app/course_cache.py`).
3. Если `gap > 0`, `build_context_row_segments` получает новый опциональный сегмент:
   `"🗺 Карта отстаёт: N материалов не на карте"` — человеческим языком, без слов
   «staging»/«bundle»/«promote».
4. При клике/раскрытии сегмента — короткая причина из уже существующих
   `latest_failed_staging.report.fail_reasons` (уже на русском, ничего не переводить).

**Files:** `app/graph_publish_status.py`, `app/ui/mission_control.py`
(`build_context_row_segments`, `_render_context_row`), targeted tests
(`tests/test_navigation_visibility.py` или ближайший relevant UI-test, plus unit test для
нового helper'а вычисления gap).

**DoD:**
- После неудачного promote студент видит на главном экране (не только во вкладке графа)
  разницу «в индексе N, на карте M» человеческим языком.
- Regression test фиксирует: `_compact_report` не теряет `source_paths`.
- Сегмент отсутствует, когда gap == 0 (штатный случай не зашумляется).

**Doc-sync:** `docs/architecture.md` (диаграмма graph publish flow, если есть),
`docs/user_guide.md` (новый статус на главном экране).

**Dependencies:** нет — расширяет существующий, уже вызываемый путь.

---

### Кандидат A2 — Аудит дубликатов концептов в штатный reindex-хвост

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое

**Проблема.** `write_graph_audit_report` (поиск дубликатов концептов вроде «LLM» ≈
«языковая модель») вызывается только из ручного `scripts/rebuild_knowledge_graph.py` —
при штатном реиндексе через приложение дубликаты никем не ловятся. Дубликат концепта
делит mastery студента между двумя узлами графа (см. [[knowledge_fate_memory_loop_plan]],
разбор №1, кандидат C1 про card→concept mapping — то же семейство проблем: mastery
привязан к нестабильной/размноженной идентичности концепта).

**Evidence:**
- `app/knowledge_graph_audit.py:85-202` (`build_graph_audit_report`,
  `write_graph_audit_report`) — не вызывает LLM, работает по уже собранному графу
  (`_duplicate_candidates`, строковое сходство), значит дешёвый и безопасный для
  штатного пути.
- `scripts/rebuild_knowledge_graph.py:40,107` — единственный сегодняшний caller:
  `audit = write_graph_audit_report(generation_bundle_dir(generation_id))`.
- `app/ingestion_index_full.py:220-291` (`_build_index_activation_phase`) — место, где
  уже вызываются `write_staging_knowledge_graph_bundle` / `write_generation_knowledge_graph_bundle`
  и логируется `graph_refresh` — естественное соседство для audit-вызова после успешного
  promote.

**Proposed change:**
1. После успешного `graph_refresh["ok"] and graph_refresh.get("published")` в
   `_build_index_activation_phase` (оба ветвления: staging-activate и reset-generation)
   вызывать `write_graph_audit_report(generation_bundle_dir(generation_id))` — best-effort,
   не блокирует активацию индекса (по аналогии с уже существующим `except Exception` вокруг
   `graph_refresh`).
2. Отчёт кладётся рядом с `graph_quality_report.json` (уже существующий путь
   `generation_bundle_dir`), не создаёт новых директорий.
3. Не менять поведение ручного скрипта — он остаётся рабочим инструментом для
   исторических/staging бандлов.

**Files:** `app/ingestion_index_full.py`, `app/ingestion_index_partial.py` (если там тоже
активируется generation с published graph), targeted tests
(`tests/test_ingestion_support.py` или ближайший ingestion-tail test).

**DoD:** после штатного реиндекса с успешно опубликованным графом
`graph_audit_report.json/.md` существует и актуален без ручного запуска скрипта.

**Doc-sync:** `docs/architecture.md` (если меняется описание ingest tail steps).

**Dependencies:** независим от A1.

---

## Волна-кандидат B: `wave-material-passport` (P1)

**North star (кандидат):** студент открывает одно место и видит, готов ли материал к
обучению — без похода по пяти разным вкладкам и логам.

### Кандидат B1 — «Паспорт материала» из уже существующих сайдкаров

**Статус:** `done` (2026-07-15) — `app/course_quality_passport.py` + карточка в
`course_prepare_view`; тесты `tests/test_course_quality_passport.py`.

**Приоритет:** P1 · **Усилие:** среднее (агрегация, не новые вычисления)

**Проблема.** Пять инструментов качества (`graph_quality_report`, `.media.json` coverage,
konspekt coverage, `source_readiness`, audit дубликатов после A2) существуют независимо
и показываются в разных местах разными путями — либо не показываются вовсе
(`source_readiness` отдаётся только через API, без UI-поверхности).

**Evidence:**
- `app/graph_publish_status.py:76-113` — статус графа.
- `app/konspekt_discovery.py:24-32,95-114` (`CoverageSummary`, `coverage_summary`) —
  уже используется в `app/ui/topics_tab.py:43-44`.
- `app/source_readiness.py:132` (`build_source_readiness_summary`) — используется только
  бэкендом (`app/api_services.py:138`, `app/routers/knowledge.py:258`), нет UI-рендера.
- Media coverage — сайдкар `.media.json`, читается через `app/media_sidecar.py`
  (используется в `app/ui/living_konspekt_next_steps.py` для `video_semantic_moments`,
  но не как единая цифра покрытия на верхнем уровне материала).

**Proposed change:**
1. Один pure aggregator (например `app/course_quality_passport.py` или соседний с
   `course_cache.py`), который собирает уже вычисленные сводки: graph publish status
   (+ freshness gap из A1), konspekt coverage, media coverage (агрегат по курсу, не по
   отдельному файлу), source readiness, audit дубликатов (после A2) — без пересчёта
   retrieval/LLM.
2. Одна секция UI (кандидат места: вкладка Course Cockpit или Knowledge Graph tab, не
   новый top-level view) — короткая карточка с 4–5 строками статуса, каждая кликабельна
   в соответствующий детальный экран (уже существующий).
3. Никаких новых чисел — только сведение уже посчитанного.

**Files:** новый агрегатор-модуль, `app/ui/course_cockpit.py` или `app/ui/dashboards_graph.py`
(куда встраивать карточку — решить на этапе реализации по существующей навигации),
targeted tests.

**DoD:** одна карточка показывает: карта опубликована/отстаёт (из A1), конспекты N/M,
видео-покрытие честное %, source readiness проблемных файлов, дубликаты концептов
(из A2) — с переходом в детальный экран по клику.

**Doc-sync:** `docs/user_guide.md` (новая секция), `docs/architecture.md` (если появляется
новый модуль-агрегатор).

**Dependencies:** выигрывает от A1 (freshness gap) и A2 (audit), логичнее делать после них.

---

### Кандидат B2 — Лестница вместо порога `min_documents < 3`

**Статус:** `done` (2026-07-15) — `format_min_documents_ladder` /
`rewrite_fail_reasons_for_learners` в `course_quality_passport.py`; подключено в
`course_prepare_view` и `dashboards_graph`.

**Приоритет:** P1 · **Усилие:** малое

**Проблема.** Курс из 1–2 документов никогда не получает семантическую карту
(`evaluate_graph_quality_gate` жёстко возвращает `False` до цикла остальных проверок),
и это не объясняется студенту как достижимая цель, а выглядит как отсутствие функции.

**Evidence:**
- `app/course_graph_compiler.py:699-720` (`evaluate_graph_quality_gate`) —
  `if doc_count < 3: _gate("min_documents", ">= 3", doc_count, False, "Недостаточно
  документов для семантического графа"); return False, gates, fail_reasons`. Сообщение
  уже на русском и уже структурировано как `fail_reasons`.
- Тот же report (`fail_reasons`) уже долетает до `graph_publish_status.py` через
  `latest_failed_staging` — инфраструктура доставки текста есть, не хватает того, чтобы
  её показывали как **прогресс**, а не только как ошибку.

**Proposed change:**
1. Специальный случай в UI-рендере (после B1 — в карточке паспорта, до B1 — там же, где
   сегодня рендерится `_render_graph_publish_status`): если единственный проваленный gate
   — `min_documents`, текст меняется с «Недостаточно документов» на позитивную рамку:
   «Добавьте ещё N документ(ов) курса — появится семантическая карта» (N вычисляется из
   `required` и `actual`, оба уже в `GraphQualityGateResult`).
2. Остальные gate-провалы (evidence, orphan rate и т.п.) не переформулируются этим
   пакетом — это отдельная работа над языком (см. кандидат C2).

**Files:** `app/ui/dashboards_graph.py` (или новое место карточки паспорта из B1),
targeted tests.

**DoD:** курс с 1–2 документами показывает конкретное «добавьте N документов», а не общее
«граф не опубликован».

**Doc-sync:** `docs/user_guide.md`.

**Dependencies:** логически проще после/вместе с B1 (общее место рендера), но может быть
сделан отдельно как точечный текстовый фикс.

---

## Волна-кандидат C: `wave-material-durability` (P2)

**North star (кандидат):** ни один сайдкар не может незаметно устареть относительно
своего источника; весь язык статусов материала — учебный, не инженерный.

### Кандидат C1 — Бейдж устаревшего конспекта

**Статус:** `proposed`, требует discovery по стоимости пересчёта

**Приоритет:** P2 · **Усилие:** среднее

**Проблема/возможность.** Smart-конспект несёт sha256 своих входов во frontmatter
(`_sha256_inputs`), но ничто не сравнивает его с текущим состоянием исходников лекции
после правки — конспект может незаметно разойтись с материалом.

**Evidence:**
- `app/smart_konspekt.py:193-203` (`_sha256_inputs`, `_target_path`) — хэш уже
  вычисляется и пишется в frontmatter (`_frontmatter`, строка 255).
- `app/konspekt_discovery.py:33-40` (`_parse_frontmatter`) — уже умеет читать frontmatter
  конспектов; естественное место добавить чтение сохранённого hash.

**Discovery перед реализацией:**
1. Где дёшево пересчитать текущий hash источника для сравнения (на каждый рендер topics
   tab — вероятно нет; на реиндекс — вероятно да, но нужно решить, где именно).
2. Нужен ли явный UI-триггер «проверить актуальность» вместо фонового пересчёта.

**Files после discovery:** `app/konspekt_discovery.py`, возможно
`app/ingestion_index_full.py` (если пересчёт на реиндексе), `app/ui/topics_tab.py`.

**Doc-sync после реализации:** `docs/user_guide.md`.

---

### Кандидат C2 — Learner-language pass по вкладке графа

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** малое–среднее

**Проблема.** Формулировки вкладки графа рассчитаны на разработчика: «Published graph:
active generation `{id}`», «Показан previous published graph», «Последний staging graph
не опубликован» — тот же класс проблемы, что SSR-диагностика в разборе №0
([[learning_loop_simplicity_plan]], кандидат B2).

**Evidence:**
- `app/ui/dashboards_graph.py:705-726` (`_render_graph_publish_status`) — точные строки
  выше.

**Proposed change:** заменить на учебный язык («Карта актуальна» / «Показана предыдущая
версия карты — новая ещё не готова» / «Последняя попытка обновить карту не прошла
проверку качества: <fail_reasons>»), сохранить механизм (source остаётся тем же), не
трогать логику `reader_source`.

**Files:** `app/ui/dashboards_graph.py`.

**DoD:** ни одно сообщение статуса графа не содержит слов «bundle»/«staging»/«promote»/
«generation» на пользовательской поверхности (техническое значение остаётся в debug-tier,
если он есть).

**Doc-sync:** `docs/user_guide.md`.

**Dependencies:** независим, но логично делать вместе с A1/B1 (один заход в один и тот же файл).

---

## Рекомендованный порядок реализации

1. **A1** — видимый индекс свежести карты; малый, самодостаточный, чинит главную боль-якорь.
2. **A2** — аудит дубликатов в штатный хвост; независим от A1, тоже малый.
3. **B2** — лестница вместо порога; можно вести параллельно с A1/A2, чистый текстовый фикс.
4. **B1** — паспорт материала; ставить после A1/A2, чтобы агрегировать уже готовые данные,
   а не пустые заглушки.
5. **C2** — learner-language pass; логично совместить с A1 (один и тот же файл
   `dashboards_graph.py`), но можно и отдельно.
6. **C1** — konspekt staleness; последним, требует discovery по месту пересчёта hash.

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../presentations/evolutionary_analyses/README.md`](../presentations/evolutionary_analyses/README.md) — индекс серии разборов
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- [`first_ten_minutes_onboarding_plan.md`](first_ten_minutes_onboarding_plan.md) — detail-plan разбора №2 (онбординг)
- [`learning_loop_simplicity_plan.md`](learning_loop_simplicity_plan.md) — detail-plan разбора №0 (UI/фокус)
- hometutor: `docs/architecture.md`, `docs/conventions_architecture.md`, `docs/api_reference.md`, `CLAUDE.md`
