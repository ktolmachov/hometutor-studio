# Mega bundle: candidate plan («Один город без адресов» — границы курсов, адреса, каталог)

**Источник:** эволюционный разбор №21
(`doc/presentations/evolutionary_analyses/21_mega_bundle_catalog.html`), 2026-07-18,
тема владельца «мега-бандл нескольких курсов: общий план, маршрут в Мнемополисе по всем
конспектам, простой каталог с ИИ-навигацией».

**Статус плана:** v1.2 (2026-07-18) — visual QA макета №21 после фиксов
плиточного интерактива и консистентности.
v1.1 (2026-07-18) — правка после critical review vs runtime.
Первичный draft v1.0 опирался на hometutor @ `8623c3476` «291»; ниже — re-baseline
на **≥ @305** (`2f9f36dcb` и новее). При реализации сверять по **имени функции**,
не по номеру строки.

**Evidence-база.**

| Слой | Что | Как принимать |
|---|---|---|
| **CI / unit** | synthetic fixture: 2 top-папки курса × 2 «урока» (md+txt) + `living-konspekt/` | обязательно, без `D:\AI\…` |
| **Manual / owner** | `D:\AI\app\data` — «ИИ Агенты» (5 уроков) + «ИИ Агенты Deep» (1 модуль) + `living-konspekt/рабочий-конспект.md`; gen `reset_home_rag_v2_2026_07_17T21_01` | опциональный live DoD; числа 13/6/8/82 — **snapshot-specific**, не unit-assert |
| **Runtime note** | После 291: Mnemonopolis W2–W6, Keeper budget/cache, W2b flashcards handoff, size-budget splits | write-set зала/маршрута сверять с HEAD, не с 291 |

**Тезис разбора.** Мега-бандл в слое данных уже существует: единый индекс (сквозной
Q&A при **пустом** `folder` / `folder_rel` в `QueryOptions` — single-folder filter
или «вся область», не multi-scope OR), единый граф-бандл обоих курсов (на эталоне
владельца: ~13 документов, ~82 концепта, gate ✓), **~8 общих тем уже слиты
компилятором** (на эталоне: Agentic Loop, Tools, Guardrails, Evals, AI Agent, LLM,
Pipeline, RAG — документы обоих курсов у одного концепта), память сквозная по
каноническому `cid`.

Слой опыта — одно-курсовый: scope = одна папка; отдельного экрана
«курсы → конспекты → разделы» по **всей** области без смены scope нет
(есть «Темы» / Mission Control / Course Cockpit — см. продуктовую границу ниже);
у агента нет инструмента библиотеки; там, где бандл прорывается наружу
(этажи/маршрут), lesson-лестница **не знает границ курсов** и врёт.

**Уже в runtime (не изобретать заново).**

- Render-payload узлов: поле **`courses: list[str]`** — top-папки из
  `documents` / `related_documents` (`build_kg_payload` в
  `app/ui/knowledge_graph_d3.py`). Это **не** scalar `course` и **не** урок.
- North star «курс · **урок**» для concept-stop day_route = `courses` **+**
  резолв урока (lesson via `part_of` / primary document → lesson-anchor), не
  «добавить `course` с нуля».
- `is_user_course_folder_rel` / `is_user_source_path`
  (`app/course_folder_filter.py`) **не** отсекают `living-konspekt/`
  (возвращают `True`). Exclude для лестницы — **явный** список, не «существующий
  course resolver».

**Боль-якорь (живой прогон на эталоне, не grep).** Прямой вызов
`lesson_floor_order(...)` (`app/ui/knowledge_graph_d3_analysis.py`) на снимке
активного бандла → **13 этажей на 6 реальных уроков**: этаж 1 — «Модуль 1»
Deep **перед** «урок_1 Введение» базового (в `typed_relations`:
`lesson:…deep-modul-1…-txt → precedes → lesson:…urok-1-vvedenie…-md`); каждый
урок раздвоен (`.md` и `.txt` — отдельные lesson-узлы); последний этаж —
`living-konspekt` («урок №9999» по sort-key без цифр).

**North star (одна на весь план):** «у каждого шага есть адрес» — доля остановок
`select_day_route` / Memory Run, подписанных **«курс · урок»**: 0% → 100%.

**Прокси (manual на эталоне, не CI-числа):** этажей 13 → 6; `precedes` через
границы top-папок → 0; общих тем **видно в UI** 0 → 8. В unit — только
инварианты fixture.

**Продуктовая граница каталога.** Не плодить третий «вход в материалы» без
решения владельца:

| Вариант | Когда |
|---|---|
| **A (рекомендуется v1.1)** | Новый thin view «Библиотека области» (sibling) + явная ссылка из «Темы» / MC; «Темы» остаётся prep/активный курс |
| B | Расширить «Темы» до multi-course browse (больше churn в topics_tab) |
| C | Только Mission Control tiles (мало глубины «разделы») |

Пока не выбрано иначе — **вариант A**, write-set не раздувает `topics_tab`.

---

## P0-1 «Курс — гражданин графа»: границы и честные этажи

- **Problem.** Компилятор не знает «курс»: документы бандла — плоская куча,
  отсортированная по первой цифре имени. Отсюда ложный межкурсовой `precedes`,
  dual lesson-узлы md/txt и личный конспект в лестнице.
- **Evidence (имена; строки — ориентир HEAD ≥305).**
  - `course_graph_compiler._lesson_sort_key` — первое `\d+` стема
    («Модуль 1» = «урок_1» = 1), tie-break `path.casefold()` →
    `ИИ Агенты Deep/…` раньше `ИИ Агенты/…`;
  - `_append_lesson_anchor_nodes`: `sorted(documents_grouped, key=_lesson_sort_key)`
    без группировки по top-папке; `zip(lesson_meta, lesson_meta[1:])` → `precedes`
    сквозь границы папок;
  - docstring/логика: **один lesson-узел на документ** → md и txt = два id
    (`lesson:…-md` / `lesson:…-txt` через `slugify` + `_lesson_anchor_id`);
  - `living-konspekt/…` тоже получает lesson-узел;
  - `lesson_anchor_key` срезает суффиксы **`.md`/`.txt` с конца строки**, но id
    уже `…-md` / `…-txt` (slug) — коллапс **не** срабатывает
    (подтверждено: разные anchor keys → 13 этажей).
- **Proposed.** Одна правда в **компиляторе**; floors наследуют через
  `precedes` (`lesson_floor_order` / JS `computeLessonOrder`).
  1) **Группировать** документы одного урока: stem до расширения внутри top-папки
     (md+txt → **один** lesson-узел; в `documents` / related — оба пути);
  2) **`precedes` только внутри** каждой top-папки курса (zip по сгруппированным
     meta per folder);
  3) **Exclude из lesson-лестницы** (явный rule, не `is_user_course_folder_rel`):
     как минимум `living-konspekt/`; при необходимости — другие non-curriculum
     корни (зафиксировать список в compiler + test);
  4) **Canonical lesson id:** стабильный slug **без** хвоста `-md`/`-txt`
     (или явная политика «prefer .md»); document оба path;
  5) **Defense-in-depth (рекомендуется):** в `lesson_anchor_key` (+ JS twin)
     нормализовать slug-суффикс `-(md|txt|markdown)$` — страховка для legacy
     снимков, если merge в compiler неполный;
  6) **Поля адреса (render, аддитивно):**
     - **не** дублировать `courses[]` новым параллельным API без нужды;
     - на **lesson**-узлах: scalar/display `course` = top-папка (или первый
       element path) + label урока;
     - на **concept**-узлах: уже есть `courses[]`; урок — отдельный резолв в P1
       (или thin helper в P0-1 tests-only).
- **Миграция / совместимость.** После rebuild id lesson-узлов могут смениться
  (`…-md` → канон). Kill: не писать ad-hoc migrator user_state; mastery/due на
  lesson-id редки — зафиксировать в DoD «полный recompile gen». Не трогать
  concept `cid`.
- **Files.**
  - must: `app/course_graph_compiler.py`;
  - tests: compiler grouping / per-folder precedes / exclude living-konspekt;
  - optional safety: `app/ui/knowledge_graph_d3_analysis.py`,
    `app/ui/assets/kg_3d_template.html` (`lesson_anchor_key` / `lessonAnchorKey`);
  - payload labels: `app/ui/knowledge_graph_d3.py` (`build_kg_payload`) — только
    если lesson-node display нужен в P0-1; domain dump — compiler bucket.
- **DoD.**
  - **Unit (fixture):** 2 курса × (md+txt на урок) + `living-konspekt/foo.md` →
    0 `precedes` cross top-folder; lesson-узлов = число уроков (не 2×); living
    **не** в lesson ladder; floor order = per-course chains, не interleaved.
  - **Manual (эталон):** rebuild (`scripts/rebuild_knowledge_graph.py`) →
    ~6 lesson floors; этаж 1 = базовый «урок_1…»; 0 cross-folder `precedes`.
- **Kill switch.** Не-аддитивная ломка домен-схемы бандла; новое хранилище;
  LLM для порядка уроков; «починить только UI floors» без compiler (симптом
  вернётся на recompile).
- **Effort.** ~день. **Priority.** P0. **Dependencies.** нет.

---

## P0-2a «Библиотека области (thin)»: каталог из готовых резолверов

- **Problem.** Без смены active scope нельзя обойти все курсы/конспекты/разделы
  с одного экрана. «Темы» / cockpit завязаны на активный курс.
- **Evidence.**
  - scope one-folder: `activate_scope` / `ACTIVE_SCOPE_KEY` (`app/ui/study_scope.py`);
  - опции курсов: `build_mission_control_course_options` (`app/course_cache.py`);
  - UI label «Все курсы» отсутствует; empty folder в Q&A ≠ отдельный scope-mode;
  - `scan_konspekts(course_dir)` (`app/konspekt_discovery.py`) — для активного
    курса в topics flow; паспорт/staleness (разбор №14) переиспользовать;
  - разделы: `section_index`;
  - Q&A с фильтром курса: `QueryOptions.folder` / `folder_rel` (пусто = область
    индекса целиком). **Не** cite telemetry-строк `query_service` как контракт.
- **Proposed (thin, 0 LLM, 0 storage).**
  1) View «Библиотека» (FeatureSpec, variant A) — **только сегмент Каталог**;
  2) список курсов из `build_mission_control_course_options`;
  3) курс → `scan_konspekts` + passport/staleness **без** `activate_scope`;
  4) конспект → `section_index` + «открыть»;
  5) действия: открыть / «Сделать активным» (`activate_scope`) / «Спросить»
     (префилл Q&A с `folder_rel` курса **или** empty = вся область).
- **Shared projection (обязательно).** Вынести read-model
  `list_library_courses / list_konspekts / list_sections` в узкий pure-модуль
  (напр. `app/library_catalog_read.py` или рядом с discovery) — **один** API для
  UI и будущего `catalog.list` (P1). Streamlit view только рисует.
- **Files.** read-model + `app/ui/library_catalog.py` (или согласованное имя) +
  `feature_registry` / nav visibility; read-only reuse: `course_cache`,
  `konspekt_discovery`, `section_index`.
- **DoD (thin).**
  - видны оба курса и конспекты эталона **без** смены scope;
  - ≤2 клика до конспекта любого курса;
  - «Спросить по Deep» → источники с path prefix Deep (integration/UI test
    с mock API ok);
  - тест: browse **не** мутирует scope; `activate` — только явная кнопка;
  - visual: readable mobile single-column; без требования 3-col schedule grid.
- **Kill switch.** Свой кэш/БД каталога; третий резолвер «что такое курс»;
  LLM-навигация в P0.
- **Effort.** ~день. **Priority.** P0. **Dependencies.** нет (P0-1 не нужен).

---

## P0-2b «Расписание области» (visual + сегменты) — отдельная волна

- **Problem.** Thin catalog закрывает «найти файл»; не закрывает ощущение
  «одна поверхность: каталог · пересадки · маршрут» из макетов №21.
- **Proposed.** UI direction из разбора №21 (сетка плиток, status, pin, a11y):
  1) сегменты **`Каталог` | `Пересадки` | `Маршрут`** (tablist/tabpanel);
  2) плитка: quant + status → адрес `курс · урок` → имя → course chip → CTA;
  3) «Вся область» — summary-плитка (counts из графа/индекса, не хардкод 82/8
     в коде; на эталоне manual check);
  4) responsive 3→2→1; focus-visible; status не только цветом.
- **Dependencies (жёстко).**
  - Каталог-сегмент: P0-2a;
  - **Пересадки:** P1 badge / shared-theme list (данные после честного бандла);
  - **Маршрут + тот же адрес, что в каталоге:** P0-1 + P1 address resolver.
- **DoD.** Keyboard по сегментам; нет overlap/h-scroll на 390 и 1366; адрес
  concept-stop совпадает с форматом в каталоге (north star helper).
- **Design QA макета №21 (2026-07-18).** После review-fix pass: поиск реально
  скрывает неподходящие плитки; empty state есть во всех сегментах; звёзды
  читаемы в light/dark и active/inactive состояниях; адрес не пересекается с
  правым маркером; вердикты получили rail-акцент по типу решения; проверены
  desktop/mobile breakpoints 1440/900/760/600/560/390 без horizontal overflow.
- **Effort.** отдельная волна (не «~день» вместе с 2a). **Priority.** P0/P1
  borderline — **после** P0-1 и thin 2a. **Не** блокирует P0-1.

---

## P1 Пересадки + адреса + агент-навигатор

- **Problem.** Shared themes невидимы в UI; остановки day_route без «курс · урок»;
  агент не отвечает «где X в курсе Y» адресом раздела.
- **Evidence.**
  - multi-course concepts: `courses[]` length ≥ 2 или documents из ≥2 top-folder
    (эталон ~8) — **уже в payload**, UI badge нет;
  - `select_day_route` — worth/due/frontier, **без** address labels;
  - агент: 9 tools (`rag.*`, `quiz.generate`, `learner.*`, `graph.inspect`,
    `konspekt.inspect`, `cards.*`); library tool нет; `konspekt.inspect` =
    workbench, не FS-каталог;
  - golden: `eval_data/agent_scenarios_golden_v1.json`.
- **Proposed.**
  1) **Badge** «в N курсах» / list первоисточников из `courses[]` + related paths
     (2D card + hall chip) — арифметика, 0 LLM;
  2) **Address helper** (pure): concept_id → `"{course} · {lesson_label}"`
     используя `courses[]`, `part_of`→lesson node, fallback primary doc path;
     встроить в day_route UI, Memory Run stop card, adaptive plan step labels;
  3) **`catalog.list`** agent tool → **тот же read-model, что P0-2a** (не
     импорт Streamlit); golden «найди раздел про … в Deep».
- **DoD.**
  - shared theme → оба курса кликабельны;
  - north star: 100% stops day_route с non-empty address **на fixture + эталоне**;
  - agent golden green без hallucinated paths.
- **Files (ориентир).** `knowledge_graph_d3` / dashboards card; thin
  `app/library_catalog_read.py` + `app/agent/tools_*.py`; tests + golden json;
  hall template — copy only.
- **Effort.** дни. **Priority.** P1.
- **Dependencies.** P0-1 (честные lesson nodes / part_of); P0-2a read-model
  (для tool). **Не** ждать P0-2b visual schedule.

---

## P2 Линии курсов в зале + порядок области (post-addresses)

- **Problem.** Визуально курсы слабо различимы как «линии»; порядок
  «Deep после base» только в голове владельца.
- **Не путать с vision W4.** Shipped W4a–d = tab Мнемополис, return CTA,
  **district doors** (4), FC return — **не** metro map. «Линии курсов» в vision
  §4 — метафора / future district, MVP doors уже закрыты. P2 = **новая**
  presentation-волна поверх P0-1/P1 данных.
- **Proposed.**
  1) Presentation-only: course = color lane / edge tint в local|all; transfer =
     multi-`courses` nodes (данные после P0-1/P1);
  2) optional owner order: `course.yaml` **или** pin order в UI-state
     (default: курсы независимы; **не** писать cross-folder `precedes`);
  3) adaptive/weekly plan: course tags + «пересадка в Deep» как **recommend**,
     не curriculum edge.
- **DoD.** Export hall: ≥2 course tints + ≥1 transfer highlight на эталоне;
  owner order меняет только recommendations, typed `precedes` не трогает.
- **Kill switch.** Рисовать межкурсовой `precedes` «для красоты»; второй XP;
  cloud photo scope-creep.
- **Effort.** волна. **Priority.** P2. **Dependencies.** P0-1, P1
  (addresses + transfers visible).

---

## НЕ делать (вердикты разбора, зафиксированы)

1. **Второй «мега-граф» или хранилище каталога** — бандл один; каталог = проекция
   FS + index (+ graph read для badge).
2. **LLM для порядка курсов и границ** — FS + lesson numbers; межкурсовой
   order — явное решение владельца (P2 optional).
3. **Мульти-scope retrieval (OR по нескольким folder сразу)** — не нужен: пустой
   folder = вся область; один `folder_rel` = один курс. «Спросить по Deep» =
   single-folder filter, **не** multi-scope.
4. **Автослияние текстов конспектов разных курсов** — concept merge уже есть;
   перегенерация ломает line anchors / sidecars (№14).
5. **Параллельное поле `course` в обход `courses[]`** без таблицы «lesson scalar
   vs concept list» — только согласованный address helper.
6. **Полагаться на `is_user_course_folder_rel` для исключения living-konspekt** —
   predicate пропускает эту папку.
7. **Re-open vision W4** под видом metro — W4 shipped; P2 отдельно.

**Правило границы:** `hometutor-studio/doc/backlog_registry.yaml` этим планом
не редактируется — только кандидаты; промоут — решением владельца. Runtime
source of truth — код hometutor + `docs/`, не studio backlog.

**Рекомендованный порядок:**

```text
P0-1 (compiler floors/boundaries)
  → P0-2a (thin library + shared read-model)
  → P1 (badge + address helper + catalog.list)
  → P0-2b (schedule UI / 3 segments)   # optional polish surface
  → P2 (course lanes + owner order)
```

**Минимальный valuable slice:** только **P0-1** на synthetic fixture + manual
rebuild эталона — уже чинит ложь этажей/precedes; каталог и metro не блокируют.
