# First Ten Minutes — Onboarding Closure Plan

Updated: 2026-07-11

Status: all candidates `proposed`. Это не SSoT исполнения — `backlog_registry.yaml`
этим документом не меняется, промоушен волн/пакетов решает владелец.
Owner: product / learning experience
Source: эволюционный разбор hometutor «Первые 10 минут» (2026-07-11), формат —
[`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md).
Полный читаемый разбор:
[`../presentations/evolutionary_analyses/02_first_ten_minutes.html`](../presentations/evolutionary_analyses/02_first_ten_minutes.html)
(тот же контент опубликован как HTML-артефакт сессии).

Related docs:
- `doc/backlog_registry.yaml` — SSoT исполнения; кандидаты попадают туда только решением владельца
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1
  той же серии («Судьба одного знания», петля памяти)
- [`learning_loop_simplicity_plan.md`](learning_loop_simplicity_plan.md) — detail-plan разбора №0
  (UI/фокус Mission Control)
- hometutor: `docs/quickstart.md`, `docs/user_guide.md`, `docs/architecture.md`, `CLAUDE.md`

## Как использовать этот документ

Каждый пункт ниже — candidate-package с достаточной детализацией, чтобы владелец мог
промоутить его в wave/package `backlog_registry.yaml` или отклонить/отложить с причиной.
Реализация кода происходит в `hometutor` и подчиняется его runtime-правилам: targeted
tests, doc-sync при изменении поведения, никаких попутных рефакторингов вне
согласованного write-set. Все evidence-ссылки проверены на `hometutor@60b55f3` (`149`) —
плюс незакоммиченный дифф кандидата A2 из `learning_loop_simplicity_plan.md` в
`app/ui/mission_control.py`, который не меняет ни один из фактов ниже (он переставляет
порядок блоков внутри уже существующей функции, не трогает `first_run.py` /
`ingestion_support.py` / `course_cache.py`).

Статусы: `proposed` → `accepted` → `in_progress` → `done` / `declined` / `superseded`.

## Суть разбора

Новый студент в первые 10 минут хочет одного доказательства: *мои материалы оживают*.
Всё до первого заземлённого ответа с источником — долг, всё после — доверие. Аудит
показал: онбординг построен дважды — слой «обещаний» (три двери первого запуска,
first-session hero, тур) и слой «исполнения» (пути на диске, билдер артефакта, LLM-стек)
— и эти слои физически смотрят в разные папки одного диска.

---

## Волна-кандидат A: `wave-onboarding-closure` (P0)

**North star (кандидат):** через любую из трёх дверей первого запуска новичок за один
цикл индексации получает работающий first-session hero (миссия курса + seed-вопросы с
черновиками ответов) — без единого невыполненного обещания на экране.

**Kill switch (кандидат):** если унификация резолвера кандидатов (A1) начинает включать
в «курсы» служебные/тестовые папки, которые раньше корректно отфильтровывались только
явным `data/docs`-скоупом, откатить на allowlist явных top-level директорий
(`demo`, `uploads`, определённые пользователем) вместо общего вывода из путей индекса.

### Кандидат A1 — Единый источник кандидатов для первого обзора

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое–среднее

**Проблема.** Билдер first-session артефакта и резолвер scope для hero вычисляют «что
такое курс» двумя независимыми путями, которые расходятся для всех трёх дверей первого
запуска, кроме гипотетической `data/docs/<курс>`.

**Evidence:**
- `app/demo_sandbox.py:22-23` (`demo_target_dir`) — демо-дверь кладёт материалы в
  `DATA_DIR / "demo"`.
- `app/demo_sandbox.py:96-107` (`save_uploaded_files`) — загрузка кладёт в
  `DATA_DIR / "uploads"`.
- `docs/quickstart.md:66` — третья дверь и документация советуют «Положите материалы в
  `data/`» (корень), без указания `data/docs`.
- `app/ingestion_index_full.py:356-357` и `app/ingestion_index_partial.py:272-273` —
  единственные вызовы `run_first_session_precompute_tail(docs_root=DATA_DIR / "docs", …)`.
- `app/ingestion_support.py:279-304` (`run_first_session_precompute_tail`) →
  `list_course_candidates(docs_root=...)` (`app/course_cache.py:523-549`) —
  файловый скан только внутри переданного `docs_root`.
- `app/course_cache.py:861-873` (`_course_options_from_index_stats`) — hero-резолвер,
  напротив, выводит список курсов из `index_stats["folder_rel_options"]` / `files`
  (то есть из уже проиндексированных путей, а не файлового скана заданной директории).
- `app/course_folder_filter.py:5-16` (`_TECHNICAL_COURSE_FOLDER_NAMES/PREFIXES`) — общий
  фильтр служебных папок, которым уже пользуется резолвер hero; билдер его не вызывает
  вовсе (у него нет списка «служебных», у него просто узкий `docs_root`).

**Proposed change:**
1. Источником кандидатов для `run_first_session_precompute_tail` сделать те же
   top-level папки, что видит резолвер hero — то есть вычислять их из уже
   проиндексированных путей (доступны сразу после ingest, precompute tail и так
   запускается post-ingest), а не файловым сканом жёстко заданного `docs_root`.
   Технически: заменить `list_course_candidates(docs_root=DATA_DIR/"docs")` на
   вариант, читающий те же индексированные relative-пути, что использует
   `_course_options_from_index_stats`, пропущенные через тот же
   `is_user_course_folder_rel` фильтр (`app/course_folder_filter.py`).
2. `demo`, `uploads` и любая пользовательская top-level папка автоматически становятся
   валидными кандидатами first-session артефакта — без явного allowlist на каждую дверь.
3. Не менять контракт `build_first_session_artifact` (`app/services/first_session_builder.py:141`)
   и `retrieve_fn` — меняется только источник списка `course_id`/`source_paths`, который
   передаётся в него.

**Files:** `app/ingestion_support.py` (`run_first_session_precompute_tail`,
`_build_and_save_first_session_candidate`), `app/course_cache.py` (возможно общий helper
рядом с `list_course_candidates`/`_course_options_from_index_stats`, чтобы не дублировать
логику вывода кандидатов из индекса), targeted tests (ingestion tail precompute,
`tests/test_ingestion_support.py` если существует, иначе ближайший relevant test file).

**DoD:**
- После полного/частичного реиндекса через дверь «Демо» или «Загрузить файлы»
  first-session артефакт существует для соответствующей папки.
- Regression test фиксирует: `demo` и `uploads` — валидные course-кандидаты для
  precompute tail (не только `data/docs/*`).
- Kill switch волны проверяем: тест на то, что служебные папки
  (`.cache`, `chroma_db`, …) не проходят в кандидаты.

**Doc-sync:** `docs/architecture.md` (если меняется диаграмма ingest tail),
`docs/quickstart.md` (уточнить, что все три двери first-run ведут к first-session hero).

**Dependencies:** нет — независимый фикс источника данных.

---

### Кандидат A2 — Честный статус вместо «готовится»

**Статус:** `proposed`

**Приоритет:** P0 · **Усилие:** малое

**Проблема.** Когда first-session артефакт отсутствует, hero безусловно показывает
«Первый обзор курса готовится — ниже есть подсказка, с чего начать» — независимо от
того, запланирована ли вообще его сборка для текущего scope. До A1 это было гарантированно
ложное обещание для demo/uploads; после A1 разрыв станет реже, но не нулевым (например,
пока идёт первый реиндекс).

**Evidence:**
- `app/ui/mission_control_first_session.py:216-217` (`render_first_session_hero`) —
  `st.info("Первый обзор курса готовится — ниже есть подсказка, с чего начать")`
  для `load_status == "empty"`, без проверки, идёт ли вообще сборка.
- `app/ui/first_run.py:41-43` (`_start_reindex`) — уже существующий, работающий триггер
  реиндекса (используется всеми тремя дверями first-run); переиспользуется здесь, а не
  изобретается новый UI-time retrieval path.
- `app/services/first_session_builder.py:141-148` (`build_first_session_artifact`) —
  чистый builder, требует `retrieve_fn` над **тёплым** post-ingest индексом
  (`app/ingestion_support.py:201-230`, `build_ingest_tail_retrieve_fn`); UI-time
  (Streamlit request) не имеет такого тёплого доступа к retrieval-сервисам ingest-процесса
  — поэтому «собрать сейчас» технически должно означать «запустить реиндекс», не прямой
  вызов билдера из UI-потока.

**Proposed change:**
1. `load_status == "empty"` различает два случая: «сборка идёт/запланирована» (после A1 —
   реиндекс для этого scope уже стартовал, `poll_reindex_status` в сессии) vs «сборки нет
   и не запущена».
2. Для первого случая — текущий текст «готовится» уместен (это правда).
3. Для второго — CTA «Собрать обзор курса» кнопкой, вызывающей тот же `_start_reindex()`,
   что и двери first-run; либо, если это избыточно для конкретного экрана, эта ветка
   вообще не показывает фразу про «готовится» (seed-чипы и так дают следующий шаг).

**Files:** `app/ui/mission_control_first_session.py`, возможно `app/ui/first_run.py`
(переиспользование `_start_reindex`), targeted tests (`tests/test_mission_control_progressive.py`
или соседний first-session test file).

**DoD:** hero никогда не утверждает «готовится», если сборка не запущена и не запланирована;
пользователь либо видит правдивый статус ожидания, либо получает CTA, которая реально
что-то запускает.

**Doc-sync:** `docs/user_guide.md` (если появляется новая CTA-кнопка на главном экране).

**Dependencies:** логически усиливается A1 (после A1 случаев «сборки нет и не запланирована»
станет меньше), но не блокируется им — можно реализовать в любом порядке.

---

## Волна-кандидат B: `wave-onboarding-trust` (P1)

**North star (кандидат):** ни одно сообщение первого экрана не создаёт ложных ожиданий
о том, что сейчас сработает, а что нет; тур предлагается в момент, когда он усиливает
уже случившийся успех, а не отвлекает от спасения пустого индекса.

### Кандидат B1 — Тур предлагается после первого ответа, не до материалов

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое

**Проблема.** Чекбокс «Запустить интерактивный тур» стоит в onboarding-диалоге, который
показывается при первом же запуске — то есть до того, как в индексе вообще есть материалы.
Если включён, первый шаг тура (`welcome` → `try_examples`) уводит пользователя со сцены,
где он мог бы решить проблему пустого индекса.

**Evidence:**
- `app/ui/home_hub.py:86` (`launch_tour = st.checkbox(...)`) и `home_hub.py:99-100`
  (`if launch_tour: _start_tutorial(0)`) — тур стартует сразу после клика «Начать» в
  onboarding-диалоге, независимо от состояния индекса.
- `app/ui/tutorial_guide.py:109-113` (`_jump_to_target_view`) — каждый шаг тура
  устанавливает `st.session_state["current_view"] = step.target_view`.
- `app/ui/tutorial_chapters.py:34-49` (`ch1_first_answer`, шаг `welcome`) —
  `target_view="Быстрый ответ"`, то есть первый шаг уводит именно туда.
- Название главы 1 — «Первый ответ» (`title_ru="Глава 1. Первый ответ"`,
  `tutorial_chapters.py:35`) — тур уже концептуально рассчитан на момент *после* того,
  как первый ответ возможен, просто предлагается не в тот момент.

**Proposed change:**
1. Убрать чекбокс тура из `_render_onboarding()` (`home_hub.py`) — onboarding-диалог
   остаётся только про выбор уровня интерфейса.
2. Показать предложение тура одноразовым баннером/CTA после первого успешного ответа
   с непустыми источниками (естественная точка — рядом с существующим
   `render_post_first_answer_goal_prompt`, `home_hub.py:110-153`, тот же жизненный
   момент «есть с чем сравнивать цель»).
3. `app_kv`-флаг «предложение тура показано», чтобы не повторять на каждый ответ.

**Files:** `app/ui/home_hub.py`, `app/ui/main.py` (если вызов онбординга завязан на
текущее место), targeted tests (`tests/test_navigation_visibility.py` если меняется
видимость элементов).

**DoD:** onboarding-диалог первого запуска не предлагает тур; предложение тура появляется
не раньше первого ответа с источником; повторный показ подавлен флагом.

**Doc-sync:** `docs/user_guide.md`, раздел про онбординг/тур.

**Dependencies:** независим от A1/A2.

---

### Кандидат B2 — Честный преполётный светофор вместо «SSR в template-режиме»

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое

**Проблема.** Когда локальный LLM-endpoint недоступен, баннер сообщает только про SSR
(«Локальная LLM недоступна — SSR работает в template-режиме»). Реальный масштаб шире:
основной чат/тьютор-ответ тоже пойдёт на тот же endpoint и с высокой вероятностью упадёт
по таймауту, потому что оба уровня LLM-fallback выключены по умолчанию — баннер об этом
не предупреждает.

**Evidence:**
- `app/ui/llm_local_banner.py:33-46` (`_build_status`, `reachable is False`) — текст
  сообщения ограничен формулировкой про SSR/template-режим.
- `app/config.py:230-231` (`enable_llm_fallback: bool = False`, `llm_fallback_model: str | None = None`)
  — fallback-путь 1 выключен по умолчанию.
- `config.env:70` (`HOME_RAG_LLM_FALLBACK_ENABLED=false`) — fallback-путь 2 (cross-base)
  тоже выключен по умолчанию.
- `app/llm_resilience.py:38-118` (`complete_with_resilience`) — оба уровня подстраховки
  реализованы корректно, но при обоих `False` primary-путь просто `raise`s дальше при
  connection error.
- `app/llm_local_health.py:49-56` (`probe_local_llm`) — проба уже возвращает достаточно
  данных (`reachable`, `model_loaded`), чтобы построить более полную картину; используется
  только для SSR-специфичного сообщения.

**Proposed change:**
1. Не менять дефолты fallback (см. Вердикты разбора: local-first и приватность важнее) —
   менять только текст/охват баннера.
2. Когда `reachable=False` **и** оба fallback выключены, баннер явно называет более широкий
   эффект: «Ответы тьютора и Быстрого ответа тоже не будут работать, пока не запущен
   локальный LLM-сервер» — не только SSR.
3. Формулировка остаётся одной строкой + деталями в существующем `st.expander`
   (`llm_local_banner.py:74-81`), без нового UI-паттерна.

**Files:** `app/ui/llm_local_banner.py`, targeted tests (баннер, если покрыт тестами —
искать по ключевым словам «llm_local» в `tests/`).

**DoD:** при недоступном local LLM и обоих fallback выключенных баннер называет
основной чат/тьютор в списке того, что не будет работать, а не только SSR.

**Doc-sync:** нет (текст сообщения, не поведение).

**Dependencies:** независим от остальных кандидатов волны.

---

### Кандидат B3 — Телеметрия time-to-first-insight (TTFI)

**Статус:** `proposed`

**Приоритет:** P1 · **Усилие:** малое

**Проблема.** Воронка первого запуска телеметрически видна почти полностью (выбор двери,
завершение онбординга, латентность по поверхностям), кроме самого важного события —
первого ответа с непустыми источниками. Без него нельзя измерить north star разбора
(медиана TTFI).

**Evidence:**
- `app/ui/first_run.py:32-38` (`_track_door`) — событие `first_run_door_selected`.
- `app/ui/home_hub.py:101-106` — событие `onboarding_completed` с `ui_level`.
- `app/latency_budget.py:21-38` — `latency_budget.jsonl`, бюджеты по 5 поверхностям
  (`mission_load`, `query`, `tutor_turn`, `quiz_gen`, `quiz_submit`), пригодны как источник
  таймстампов для расчёта TTFI, но не отмечают «это был первый ответ пользователя».
- Ни в `app/ui_events.py`, ни в существующих вызовах `track_event` нет события вида
  `first_grounded_answer`.

**Proposed change:**
1. Одно новое событие `first_grounded_answer` — эмитится один раз за учётный период
   (первый ответ с непустым `sources`), с полями: `door` (из первой двери, если есть),
   `elapsed_ms_since_install` или `elapsed_ms_since_onboarding_completed`.
2. TTFI = разница между таймстампом `onboarding_completed` (или `first_run_door_selected`,
   если онбординг пропущен) и `first_grounded_answer` — вычисляется в
   `educational_metrics_service.py` или соседнем aggregator, без новой БД-таблицы поверх
   существующего event-лога.
3. Дашборд/метрика — минимально панель на существующей метрик-поверхности
   (`app/routers/metrics.py`), не новый endpoint, если можно обойтись расширением
   существующего.

**Files:** `app/ui_events.py` (или где формируются события ответа с источниками —
`app/ui/query_tab_answer_section.py` / аналог в tutor chat), `app/educational_metrics_service.py`,
`app/routers/metrics.py`, targeted tests.

**DoD:** событие `first_grounded_answer` эмитится ровно один раз на пользователя/сессию;
TTFI вычислим из существующего event-лога без ручного разбора логов.

**Doc-sync:** `docs/api_reference.md` только если добавляется публичный metrics endpoint.

**Dependencies:** независим, но осмысленнее после A1 (иначе TTFI будет измерять в основном
провалы, а не реальный путь до первого инсайта).

---

## Волна-кандидат C: `wave-onboarding-durability` (P2)

**North star (кандидат):** первый запуск на чистой машине (новый клон, без файла `.env`,
без предустановленного LLM) проходит без ручных правок конфигурации и без ожидания LLM
для демо-двери.

### Кандидат C1 — Убрать машино-специфичный `HOME_RAG_HOME` из скриптов запуска

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** малое

**Проблема.** `scripts/local_start.ps1` и `docker-compose.yml` по умолчанию используют
`HOME_RAG_HOME=D:\AI\app` — путь конкретной машины автора. На чистом клоне этого каталога
нет; поведение — либо падение, либо тихая работа с пустым `data/`, что похоже на «двери
первого запуска сломаны», хотя причина — конфигурация окружения.

**Evidence:**
- `docs/quickstart.md:68` — уже задокументированная растяжка: «Важно: `scripts\local_start.ps1`
  и `docker-compose.yml` по умолчанию используют `HOME_RAG_HOME=D:\AI\app` — путь конкретной
  машины автора. На чистом клоне этого каталога нет, и запуск упадёт или будет работать с
  пустым `data/`».
- `app/config.py:46` — `DATA_DIR = Path(os.getenv("HOME_RAG_DATA_DIR", str(HOME_RAG_HOME / "data")))`.

**Proposed change:** дефолт `HOME_RAG_HOME` в скриптах запуска — путь относительно
репозитория (например, `$PSScriptRoot/..`), не абсолютный путь конкретной машины;
существующее предупреждение в quickstart остаётся как fallback-документация для случаев
явного переопределения.

**Files:** `scripts/local_start.ps1`, `docker-compose.yml`, `docs/quickstart.md` (снять
предупреждение после фикса или сузить его до «как переопределить путь», если это всё ещё
нужно для многодисковых установок).

**DoD:** `git clone` + `local_start.ps1` без ручной установки `HOME_RAG_HOME` поднимает
приложение с `data/` внутри репозитория.

**Doc-sync:** `docs/quickstart.md`.

**Dependencies:** независим от остальных волн.

---

### Кандидат C2 — Замороженный demo first-session артефакт в репозитории

**Статус:** `proposed`

**Приоритет:** P2 · **Усилие:** малое–среднее

**Проблема/возможность.** После A1/A2 демо-дверь корректно запускает сборку first-session
артефакта, но сборка всё ещё требует реиндекса и (опционально) вызова LLM для
черновиков ответов (`app/services/first_session_builder.py`, `_generate_draft_answer`,
строки 130-138) — на медленной/офлайн машине это не мгновенно. Демо-набор маленький и
стабильный (`demo_data/`, 7 файлов, 20 КБ) — его first-session артефакт можно посчитать
один раз и закоммитить.

**Evidence:**
- `app/demo_sandbox.py:18-19` (`demo_source_dir`) — фиксированный источник `BASE_DIR / "demo_data"`,
  не меняется пользователем.
- `app/services/first_session_builder.py:130-138` — генерация черновика ответа опциональна
  и best-effort (`except Exception: return None`), но при доступном LLM добавляет задержку
  и вариативность вывода для одного и того же демо-контента.
- `app/course_cache.py:936-963` (`first_session_artifact_path`, `save_first_session_artifact`)
  — артефакт уже сериализуется в JSON на диск; тот же формат можно поставить заранее
  собранным файлом.

**Proposed change:**
1. Собрать first-session артефакт для `demo_data/` один раз офлайн-скриптом, закоммитить
   JSON рядом с demo-данными (или в `app/services/`/фикстурах, где удобнее для загрузчика).
2. При установке демо-материалов (`install_demo_materials`, `app/demo_sandbox.py:46-57`)
   копировать также заранее собранный артефакт в путь, который вернёт
   `first_session_artifact_path("demo")`, вместо (или в дополнение к) ожидания
   `run_first_session_precompute_tail` после реиндекса.
3. Обычный precompute tail остаётся источником истины и может перезаписать артефакт при
   следующем реиндексе — замороженная версия только устраняет ожидание для самого первого
   демо-открытия.

**Files:** `app/demo_sandbox.py`, `app/course_cache.py`, новый офлайн-скрипт сборки
(в `hometutor/scripts/` или аналоге), сам JSON-артефакт, targeted tests.

**DoD:** сразу после установки демо-материалов (`install_demo_materials`) first-session
hero показывает миссию и seed-вопросы без ожидания реиндекса/LLM.

**Doc-sync:** `docs/quickstart_demo.md` (если процесс обновления demo-материалов меняется).

**Dependencies:** выигрывает от A1 (тот же формат артефакта, тот же путь резолвинга),
но может быть сделан независимо, так как демо — частный, наперёд известный случай.

---

## Рекомендованный порядок реализации

1. **A1** — единый источник кандидатов; без него A2/B3 измеряют в основном разрыв,
   который A1 и устраняет.
2. **A2** — честный статус; логически проще после A1 (меньше случаев «сборки нет»),
   но не блокируется технически.
3. **B2** — преполальный светофор; независим, малый текстовый фикс, можно вести
   параллельно с A1/A2.
4. **B1** — тур после первого ответа; независим, малый UI-фикс.
5. **B3** — TTFI-телеметрия; ставить после A1, иначе метрика отражает воронку с
   заведомым разрывом, а не эффект остальных фиксов.
6. **C1** — machine-specific `HOME_RAG_HOME`; независим, можно в любой момент.
7. **C2** — замороженный demo-артефакт; последним, использует тот же формат, что и A1.

## Связанные документы

- [`../presentations/evolutionary_analysis_guide.md`](../presentations/evolutionary_analysis_guide.md) — формат исходного анализа
- [`../presentations/evolutionary_analyses/README.md`](../presentations/evolutionary_analyses/README.md) — индекс серии разборов
- [`../backlog_registry.yaml`](../backlog_registry.yaml) — SSoT исполнения
- [`knowledge_fate_memory_loop_plan.md`](knowledge_fate_memory_loop_plan.md) — detail-plan разбора №1 (петля памяти)
- [`learning_loop_simplicity_plan.md`](learning_loop_simplicity_plan.md) — detail-plan разбора №0 (UI/фокус)
- hometutor: `docs/quickstart.md`, `docs/user_guide.md`, `docs/architecture.md`, `CLAUDE.md`
