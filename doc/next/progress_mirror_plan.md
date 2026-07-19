# Progress Mirror — план кандидатов (разбор №22 «Зеркало с чужими отпечатками»)

> **Источник:** эволюционный разбор №22
> ([`../presentations/evolutionary_analyses/22_progress_mirror.html`](../presentations/evolutionary_analyses/22_progress_mirror.html)),
> hometutor HEAD `a5b8c1d` «#22 P0-2 clean-room», 2026-07-19. Боль-якорь подтверждена живым прогоном
> UI (клик по CTA, DOM-проверка `hasSidebar:false`, пиксельный замер canvas) и прямыми
> запросами к живой `D:\AI\app\data\user_state.db`.
>
> **Статус:** A2 shipped 2026-07-19; A1/B1–B3/C1–C3 — кандидаты. НЕ записи `backlog_registry.yaml` — промоут решением владельца.
>
> **North star разбора:** «зеркальная точность» — доля строк главного таба «Прогресса»,
> подтверждённых реальным действием студента, = 100% (на 2026-07-18 в Emotional Heatmap
> реальна 1 строка из 8; после A2 clean-room — тестовые фикстуры изолированы, join
> по активному графу отфильтровывает призраков). Прокси-метрики: призрачные концепты
> на экране 7→0 (A2); мёртвые навигационные кнопки ≥5→0 (A1); поверхности прогресса
> 3→1 видимая (A1); ответ «курс · урок · шаг» — на первом экране без скролла (B2).
>
> **Kill switch (общий для P0):** потребовалось новое хранилище/схема/пайплайн или LLM
> там, где хватает арифметики готовых данных, — стоп. Чистка живой БД раньше изоляции
> тестов — стоп (призраки возвращаются ежедневным прогоном). Слияние view потребовало
> переписать `dashboards_progress.py` с нуля — стоп, скоуп режется до переноса контента.

---

## Wave `wave-progress-home` (P0)

### A1. «Возвращение домой»: страница-сирота становится view роутера с табами

- **Problem.** «Мой прогресс» — нативная multipage-страница вне роутера: без сайдбара
  (штатная навигация выключена глобально), без пути назад, с мёртвой навигацией.
  Одновременно в роутере живёт почти дословный двойник «Прогресс обучения» —
  две сводки-копии. На странице ≥5 кнопок, которые пишут
  `current_view`/`PENDING_CURRENT_VIEW_KEY` и делают `st.rerun()`, хотя потребитель
  этих ключей живёт только в `app/ui/main.py`.
- **Evidence.**
  - `app/ui/pages/3_Мой_прогресс.py:64-73` — primary-CTA пишет `current_view` +
    `st.rerun()`; живой клик 2026-07-18: остались на той же странице;
  - `app/ui/pages/3_Мой_прогресс.py:317` — код признаётся: «Откройте главный экран
    Home RAG…»;
  - `.streamlit/config.toml:8` — `showSidebarNavigation = false`; DOM живой страницы:
    `hasSidebar: false`;
  - `app/ui/sidebar.py:294-295` — кнопка сайдбара уводит `st.switch_page(...)` в тупик;
  - дубль сводки: `app/ui/dashboards_progress.py:251-348` ↔ `pages/3:93-167`;
  - роутер-двойник: `app/ui/main.py:422-437` (view «Прогресс обучения», tier 2 в
    `feature_registry.py:30`);
  - страница — наследие извлечения: существует с `fffeecb9a` «Extract product…»,
    4 правки за всю историю.
- **Proposed.**
  1. Контент «Моего прогресса» переносится в view «Прогресс обучения» роутера
     (одна сводка вместо двух копий; имя view на поверхности — «Прогресс»).
  2. Внутри view — `st.tabs("Главное", "Расширенные")`:
     «Главное» = карточка «Следующий шаг» (CTA теперь работает штатной
     PENDING-навигацией) + heatmap + radar + геймификация-кратко;
     «Расширенные» = остальная телеметрия после чистки дублей (см. вердикты разбора:
     полный «План на сегодня» → строка-тизер; pie уровней — удалить; agraph-рендеры —
     удалить, подграф эмоций уходит в P2 слоем на KG).
  3. `sidebar.py:294` ведёт на view (`PENDING_CURRENT_VIEW_KEY = "Прогресс обучения"`),
     `st.switch_page` для прогресса убирается; `pages/3_Мой_прогресс.py` — тонкий
     алиас (switch на главную с pending view) или удаляется по решению владельца.
  4. Отладка (полный JSON, `user_id="local"` `pages/3:79`, сырая таблица
     reading_status) — за debug-тиром.
- **Files.** `app/ui/dashboards_progress.py`, `app/ui/pages/3_Мой_прогресс.py`
  (перенос/алиас), `app/ui/sidebar.py`, `app/ui/main.py` (если меняется label view),
  `app/ui/feature_registry.py` (если добавляется debug-подсекция).
- **DoD.** На странице прогресса есть сайдбар и путь на главную; клик по primary-CTA
  реально открывает чат тьютора/Flashcards; ни одна кнопка не «переживает» rerun без
  эффекта; двух одинаковых сводок больше нет (grep дублей метрик); табы рендерятся;
  `pytest tests/test_navigation_visibility.py tests/test_feature_registry.py` зелёные.
- **Doc-sync.** `docs/user_guide.md` (раздел «Мой прогресс»), `docs/architecture.md`
  (если структура app/ui/pages меняется).
- **Effort.** ~день. **Priority.** P0. **Dependencies.** нет.

### A2. «Чистое зеркало»: кран, джойн, чистка — строго в этом порядке

- **Problem.** Живая память студента заросла тестовыми фикстурами и показывается
  без сверки с графом: экран советует «подтянуть TopicB», которой не существует.
- **Evidence** (живая БД, снимок 2026-07-18):
  - `app_kv.emotional_heatmap_json`: 216 строк, 214 призрачных (topic_x 52, global 31,
    общая 27, TopicA/TopicB/e2e_topic/t по 26), реальных 2 (ai-agent);
  - `quiz_mastery`: 7/7 фикстуры (записаны 2026-07-18 11:42, привязаны к активной
    генерации); `spaced_repetition`: 6/6 фикстуры (topic_x: 26 повторений, интервал
    3650 дней, next_review 2036-07-15); `quiz_results`: 182/182 фикстуры;
  - писатель — тесты hometutor-studio: `tests/test_quiz_service.py:434,456` (topic_x,
    два проходящих вызова за прогон → ровно ×2 строк),
    `tests/test_fact_source_binding.py:62,77` (BindA, LegacyTopic),
    `tests/test_e2e_user_flow.py:118` (e2e_topic); прогоны ~ежедневные с 2026-06-21;
  - канал — editable-install hometutor в venv студии +
    `app/config.py:17-18` (`load_dotenv(BASE_DIR/...)` по абсолютному пути) →
    `.env` → `HOME_RAG_HOME=D:\AI\app`; изоляции нет: в hometutor
    `tests/conftest.py` отсутствует, conftest студии DATA_DIR не трогает;
  - рендер без джойна: `app/ui/progress_visuals.py:58-68` (pivot KV-блоба как есть);
    свой вклад продукта: `app/query_tutor_context.py:357` (тема по умолчанию «общая»);
  - экранные следствия (живой прогон): «Слабые места: TopicB» в «Неделе в обучении»,
    «Мини-квизы: 78 / 3» при 0 UI-квизах за неделю (78 = ежедневные прогоны тестов,
    инкрементирующие `increment_weekly_progress`).
- **Proposed.**
  1. **Кран (обязателен первым).** В hometutor — корневой `tests/conftest.py`,
     заворачивающий user-state/DATA_DIR в tmp-путь; плюс дешёвый guard в
     `app/user_state.py` (или общем резолвере пути БД): при активном
     `PYTEST_CURRENT_TEST` запись в прод-путь (`HOME_RAG_HOME`-производный) — отказ с
     внятной ошибкой. В студии — аналогичная изоляция conftest (отдельный PR в studio).
  2. **Джойн представления.** Heatmap, weekly narrative и «слабые места» показывают
     только концепты, известные графам курсов, — тот же принцип, что уже защищает
     счётчики (`get_quiz_mastery_rows_for_kg`); «общая»/«global» агрегируются в одну
     строку «общий фон», а не маскируются под темы.
  3. **Чистка по правилу (после 1).** Разовый скрипт с бэкапом: удалить из
     `quiz_mastery`/`spaced_repetition`/`quiz_results`/`emotional_heatmap_json` строки,
     чей концепт не встречается ни в одной генерации графов и совпадает со списком
     известных фикстур; сухой прогон + явное подтверждение владельца.
- **Files.** `tests/conftest.py` (новый), `app/user_state.py` (guard),
  `app/ui/progress_visuals.py`, `app/ui/weekly_study_narrative_ui.py` (джойн),
  `scripts/` (скрипт чистки); в studio — `tests/conftest.py`.
- **DoD.** Прогон полного pytest обоих репо не меняет ни байта в
  `D:\AI\app\data\user_state.db` (сравнение mtime/хэша до/после); на живой странице
  heatmap не содержит ни одной фикстуры; «Мини-квизы: N/3» растёт только от действий
  в UI; тест на guard (запись в прод-путь под pytest → исключение).
- **Doc-sync.** `docs/conventions_reference.md` (правило изоляции тестов от живой БД).
- **Effort.** ~день. **Priority.** P0. **Dependencies.** нет (независим от A1).

- **Runtime progress (2026-07-19).** ✅ A2 shipped — `wave-progress-clean-room`:
  - **Кран:** `tests/conftest.py` `pytest_configure` + `app/user_state_db.py` guard (`PYTEST_CURRENT_TEST` → RuntimeError если путь в production `data/`).
  - **Джойн:** `app/learner_model_service.py` `get_emotional_heatmap_pivot()` фильтрует по `active_concept_ids` активного графа; внеграфовые → «общий фон». `app/ssr_weekly_narrative.py` `_collect_production_signals()` использует `weak_concepts_for_kg()`.
  - **Чистка:** `scripts/clean_progress_ghosts.py` — dry-run по умолчанию, backup, `--confirm --confirm-token CLEAN-PROGRESS-GHOSTS`.
  - **Тесты:** `tests/test_user_state_isolation.py` (9 тестов: изоляция, guard, heatmap filter, narrative). Регрессия: guardrails/pipeline/navigation/flashcards/mnemo/mission_control — зелёные. Architecture guards + size budget pass.
  - **Write-set:** `tests/conftest.py`, `app/user_state_db.py`, `app/learner_model_service.py`, `app/ssr_weekly_narrative.py`, `scripts/clean_progress_ghosts.py`, `tests/test_user_state_isolation.py`, `scripts/check_config_access.py`.
  - А2 закрывает DoD: тесты не меняют production `user_state.db`; heatmap не показывает TopicB/fixture ids; guard-test падает на production-путь под pytest.

---

## Wave `wave-progress-my-path` (P1)

### B1. «Мой след»: карточки, дни, прослушано — из готовых данных

- **Problem.** Реальный след студента (100 flashcards + 44 повторения, XP-история по
  дням, биты «прослушано») на экране прогресса отсутствует; вместо него — призрачная
  телеметрия.
- **Evidence.** Живая БД: `flashcards` 100, `flashcard_review_log` 44 (теги
  `source:ии агенты/урок_N…`); `gamification_state_v1.xp_daily_history` — готовая
  лента дней с 2026-06-21; «прослушано» — `living_konspekt_media.py:356-366`
  (B1 разбора №19). На странице (`pages/3`) поиск «flashcard» даёт только чтение
  `flashcards_due_count` из session_state.
- **Proposed.** Карточка «Мой след» на табе «Главное»: 7 последних дней из
  `xp_daily_history` (был/не был + XP), счётчики карточек (всего/повторено/к повтору —
  хелпер `get_flashcard_progress_stats` уже есть, используется двойником
  `dashboards_progress.py:229-232`), прослушанные разделы. 0 новых вычислений.
- **Files.** `app/ui/dashboards_progress.py` (или новый узкий модуль карточки).
- **DoD.** «Мой след» виден без скролла; каждое число кликом ведёт к источнику
  (Flashcards / Живой конспект). **Effort.** дни. **Dependencies.** A1.

### B2. «Мой путь»: позиция на маршруте курса

- **Problem.** Вопрос владельца «где я сейчас на маршруте и на пути изучения по плану
  курса» не имеет ответа ни на одном экране прогресса.
- **Evidence.** Данные уже есть: `reading_status` — «План по теме „Курс: ИИ Агенты“,
  шаг 1/7 „Фундамент: Агент vs LLM и концепция Harness“, progress 0.14»;
  порядок уроков — `lesson_floor_order` (№17/№21); адрес «курс · урок» — P0-1 разбора
  №21 (`mega_bundle_catalog_plan.md`). Сейчас reading_status рендерится сырым
  dataframe в подвале (`pages/3:430-432`).
- **Proposed.** Карточка «Я на маршруте»: «Курс · урок X/N · шаг M/K „…“» +
  прогресс-бар; источник — `reading_status` + резолвер курса; после промоута №21 P0-1
  подключить канонический адрес узла. Сырой dataframe уходит в debug.
- **Files.** `app/ui/dashboards_progress.py`. **DoD.** ответ «где я» — первый экран
  таба «Главное». **Effort.** дни. **Dependencies.** A1; выигрывает от №21 P0-1,
  но не блокируется им.

### B3. Одна правда mastery

- **Problem.** Три соперничающих процента на одном экране: 0.0% (quiz-вектор),
  44% (блок плана), 80% (PLM-radar) — все «честные» в своих силосах.
- **Evidence.** `pages/3:88` (`mastery_vector.avg`), скриншот/живой прогон блока
  «МИНИ-ПРАКТИКА Mastery 44%» (`adaptive_daily_plan_layout.py`), radar
  `vis_service.create_mastery_vector_radar(profile.mastery_vector)` (`pages/3:214-218`).
- **Proposed.** На «Главном» — одно число (PLM-вектор, как самый живой канал) с
  подписью источника; quiz-вектор и покрытие графа — в «Расширенных» с явными
  подписями «что это и чем отличается» (тексты уже написаны в help'ах — свести).
- **Files.** `app/ui/dashboards_progress.py`. **DoD.** на первом экране один процент
  mastery. **Effort.** дни. **Dependencies.** A1.

---

## Wave `wave-progress-analytics-fate` (P2)

### C1. Судьба «Аналитики»

- **Problem.** `pages/4_Аналитика.py` строит heatmap/кривую удержания поверх
  `quiz_results`, которые на живой БД — 182/182 тестовые фикстуры; экран показывает
  аналитику несуществующей учёбы.
- **Evidence.** `app/ui/pages/4_Аналитика.py:25,40-55`; снимок quiz_results
  (topic_x 52, TopicA/TopicB/e2e_topic/BindA/t по 26).
- **Proposed.** Либо пересадить на реальные источники (`flashcard_review_log`,
  `xp_daily_history`, quiz_ui_stats), либо спрятать за debug/feature-тиром до
  пересадки. После A2 (чистки) таблица quiz_results станет честно пустой — экран
  должен уметь это говорить.
- **Effort.** волна. **Dependencies.** A2.

### C2. Подграф эмоций — слоем на карту KG

- **Problem.** Третий рендер графа на странице прогресса пуст (canvas 1200×560 без
  единого пикселя) и дублирует карту, у которой уже есть mastery/worth-слои.
- **Evidence.** `pages/3:230-257`; живой замер canvas: sampledNonWhite=0.
- **Proposed.** Убрать agraph-рендеры со страницы (A1 уже убирает); эмодзи-слой
  эмоций добавить в payload/легенду карты KG отдельным кандидатом (render-contract,
  домен не меняется — по образцу слоёв №15/№17).
- **Effort.** волна. **Dependencies.** A1, A2.

### C3. Реальный user_id вместо "local"

- **Problem.** `pages/3:79` жёстко передаёт `user_id="local"` в PLM при живом
  auth-контуре (`auth_gate.current_user_id`); при включённом AUTH_ENABLED профиль
  на странице не привязан к вошедшему пользователю.
- **Proposed.** Брать `current_user_id()` (fallback "local" при выключенном auth) —
  тот же паттерн, что в contextvar-гейте `require_ui_auth_or_stop`.
- **Effort.** часы (но P2: single-user сегодня). **Dependencies.** A1.

---

## Рекомендованный порядок

A1 → A2 (можно параллельно) → B1 → B2 → B3 → C1 → C2 → C3.

## Явно НЕ входит в план (вердикты разбора)

- Четвёртая поверхность «правильного прогресса» — только слияние существующих.
- Новый прогресс-сервис/хранилище/схема — всё представление готовых данных.
- LLM для чистки или классификации призраков — достаточно джойна с графами.
- Ручная чистка живой БД до изоляции тестов — призраки вернутся следующим прогоном.
- Телеметрия времени просмотра видео (кастомный плеер) — отвергнута ещё в №19;
  след «прослушано» строится на существующем `mark_listened`.
