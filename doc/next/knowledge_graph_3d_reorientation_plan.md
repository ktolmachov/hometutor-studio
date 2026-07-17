# Knowledge graph 3D reorientation: candidate plan («Зал без пола»)

**Источник:** эволюционный разбор №17
(`doc/presentations/evolutionary_analyses/17_knowledge_graph_3d_reorientation.html`),
2026-07-15, аудит живого экспорта `knowledge_graph_3d (2).html` и runtime-кода
hometutor.

**Связь с планом №15.** Это не замена `knowledge_graph_3d_plan.md`, а материализация
его поправки после B1 polish. План №15 довёл провод данных до маршрута дня и
самодостаточного 3D HTML. Этот план фиксирует продуктовый провал B1: offline-контракт
закрыт, но пользовательский контракт ориентации не закрыт.

**Статус:** кандидаты, НЕ записи `backlog_registry.yaml` — владелец промоутит вручную.
Перед промоутом сверять Evidence с актуальным HEAD и актуальным экспортом.

**Update 2026-07-16/17:** P0 route-scene implementation completed in runtime.
R1/R2 are `done`; L1/L2 are `MVP done` (route/local/all, controlled tour,
hover reasons, click-to-local context); V1 is `partial done` (HTML/JS contracts +
opt-in Playwright smoke for 1366x768 and 1920x1080; mandatory browser screenshot CI
remains pending). Full report:
`doc/next/knowledge_graph_3d_done_report_2026-07-16.md`.

**Рамка:** P0 = «человек за 5 секунд понимает: я здесь, дальше сюда, потому что...».
Kill switch для P0: если нужен LLM, новое хранилище, новая схема payload или
длинная легенда «как ориентироваться» — стоп. Данные уже есть; задача P0 — не добыть
новый смысл, а дать ему правильную сцену.

**Поправка к статусу B1 из №15.** `B1 done` → `technical DoD done · product DoD failed`.
Технический DoD «offline HTML / этажи / остановки / полёт / тот же payload» остаётся
доказанным; продуктовый DoD добавляет «ориентиры / семантический порядок / читаемый
первый кадр / управляемый маршрут».

**Границы с другими планами.**
- `knowledge_graph_3d_plan.md` владеет A1/A2: `due`, `novel`, `worth`, `day_route`.
  Здесь эти поля только переосмысляются как маршрутный ранг и причина, не как география.
- `infographics_living_map_plan.md` владеет паттерном самодостаточного экспорта.
  Здесь он сохраняется: один HTML, без CDN, тот же payload.
- `knowledge_fate_memory_loop_plan.md` владеет записью следа. Здесь нет записи прогресса
  из offline HTML; экспорт отвечает за ориентацию, продукт — за действие.
- `audio_podcasts_plan.md` и `konspekt_quality_plan.md` остаются источниками метаданных.
  Audio/rubric не входят в P0 worth и не должны двигать геометрию зала.

---

## Волна `wave-kg-route-scene` (P0)

### R1 «Маршрутная сцена» — первый кадр не весь граф, а путь дня

**Статус:** `done` (2026-07-17) — default route mode, `1 → N` route scene,
quiet lesson anchors, no full-graph edges in first frame, right-panel reason/next stop,
reason callout near the active stop.

- **Problem.** Экспорт технически показывает граф, но не отвечает на главный вопрос
  пользователя: где я и куда дальше. В живом файле было 164 узла, 367 связей и
  башня перекрывающихся узлов; подписи lesson-узлов и high-worth концептов создавали
  визуальный шум, хотя подписей было меньше 164. Большая часть кадра пустая, низ
  сцены обрезан, а направление курса не считывается.
- **Evidence.** Приложенный экспорт: 164 nodes, 26 lesson nodes, 138 concepts,
  367 edges; `DAY_ROUTE` = `study-session-agent`, `rag`, `hometutor`, `ai-agent`,
  `memory-loop`, `tutor`. Исторические line evidence относились к pre-redesign
  шаблону; актуальное доказательство — `kg_3d_template.html` с default `route`,
  `edgeVisibleInMode()` без рёбер в route, `drawActiveReasonCallout()`, `hoverAt()`,
  `focus()` click-to-local и targeted-тесты `Test3DCoverageAndContracts`.
- **Proposed.**
  1. Начальный режим `kg_3d_template.html` = `route` mode, не `all graph`: рендерить
     `DAY_ROUTE`, связанные lesson-узлы и только immediate prerequisites/unlocks
     активной остановки.
  2. Добавить явную трассу `1 → N`, активную остановку, кнопки предыдущая/следующая/пауза,
     строку `Стоп N/M · reason` рядом с активной точкой и тот же список справа.
  3. Worth перестаёт быть высотой/масштабом сцены: в P0 он даёт ранг, причину и бейдж
     остановки. Геометрию курса он не двигает.
  4. Подписи первого кадра ограничить: route stops + active/next labels + active reason.
     Lesson anchors в route остаются тихими; остальные подписи — hover/selection.
- **Files.** `app/ui/assets/kg_3d_template.html`,
  `app/ui/knowledge_graph_d3.py` (`build_kg_3d_html`, `_day_route_ids` при необходимости);
  тесты: `tests/test_knowledge_graph_counters.py` + визуальная проверка экспортного HTML.
- **DoD.** В первом кадре 6/6 route stops видны без зума; не более 10 текстовых подписей;
  активная остановка и следующая остановка называются без вращения; каждая остановка
  имеет одну видимую причину; полный граф доступен отдельным режимом «Вся карта».
- **Doc-sync.** `docs/user_guide.md` (раздел 3D-экспорта).
- **Effort.** День.
- **Dependencies.** A2 из `knowledge_graph_3d_plan.md`.

### R2 «Честная геометрия» — оси, порядок и bounds имеют один смысл

**Статус:** `done` (2026-07-17) — worth removed from geometry; route scene has its own
layout; lesson order/floor helpers use `precedes`; Home/tour completion/resize return
to route fit.

- **Problem.** Сейчас «этаж урока» и «ценность концепта» используют одну вертикальную
  координату. Концепты при worth около 6.3 оказываются на 148-166 единиц выше связанного
  урока при шаге этажа 55, то есть почти на три этажа выше. Пользователь теряет
  принадлежность концепта уроку. Дополнительно `cz` объявлен как глубина камеры, но не
  участвует в `project()`, поэтому это не настоящая камера.
- **Evidence.** Исторический экспорт смешивал worth-height и этаж урока; актуальный
  шаблон фиксирует оси в `nodePos()` и `routeStopPos()`, а `computeLessonOrder()`
  строит этажи из `precedes` с collapse `.md/.txt` вариантов. Runtime test проверяет
  и Python helper, и наличие shipped JS-алгоритма в HTML.
- **Proposed.**
  1. Определить координаты через один устойчивый смысл на ось:
     `X = progression/order`, `Y = floor/layer`, `Z = local lane/depth`.
     Worth не участвует в координатах.
  2. Порядок уроков брать из `precedes` / lesson sort compiler logic, а не из
     лексической сортировки id в шаблоне.
  3. Группировать файловые варианты одного урока или отображать их как материалы одного
     floor-anchor, а не как самостоятельные этажи.
  4. Добавить auto-fit по фактическим bounds route-scene и кнопки Home / вид сверху.
  5. Либо реализовать настоящую world-camera, либо честно оставить 2.5D fixed-isometric
     без заявленного «полёта в глубину».
- **Files.** `app/ui/assets/kg_3d_template.html`,
  `app/ui/knowledge_graph_d3.py`; возможно тонкий helper в
  `app/ui/knowledge_graph_d3_analysis.py`, если порядок route/floors удобнее тестировать
  в Python; тесты: targeted unit на floor order + экспортный smoke.
- **DoD.** После открытия, resize и навигации сохраняются верх/низ/вперёд; активная
  остановка остаётся в кадре; route-scene не обрезается на 1366x768 и 1920x1080 в
  opt-in smoke; lesson anchors в route тихие и не спорят с остановками; в local/all
  подписи ограничены collision-aware лимитом; zoom/home возвращают один и тот же
  читаемый вид.
- **Doc-sync.** `docs/user_guide.md`.
- **Effort.** День-два.
- **Dependencies.** R1.

---

## Волна `wave-kg-local-context` (P1)

### L1 «Локальное исследование» — раскрывать сложность после выбора

**Статус:** `MVP done` (2026-07-17) — route/local/all modes exist; route stays clean,
click on a route stop switches to local context, hover shows reason, all mode exposes
the full graph.

- **Problem.** Полный граф конкурирует с маршрутом: 367 связей и все подписи появляются
  раньше, чем пользователь выбрал контекст. Это делает 3D-зал шумнее 2D-карты, хотя
  его роль должна быть обратной — быстрее дать ориентиры.
- **Evidence.** Historical: рёбра и подписи рисовались глобально. Current: `visibleIdSet()`,
  `addImmediateContext()`, `edgeVisibleInMode()` and `focus()` implement route/local/all
  density changes; test locks click-to-local and hover existence.
- **Proposed.**
  1. Режимы: `route` → `local` → `all`.
  2. Клик по остановке раскрывает её immediate prerequisites, unlocks и lesson-anchor;
     дальние связи скрыты до режима `all`.
  3. Hover показывает подпись и reasons; click закрепляет локальный контекст.
  4. Боковая панель синхронизируется с активной остановкой и локальным окружением.
- **Files.** `app/ui/assets/kg_3d_template.html`; тесты: HTML contract на наличие
  режимов и сохранение offline/no external script.
- **DoD.** Первый кадр остаётся маршрутным; выбор узла добавляет контекст без возврата
  к полной сетке; пользователь может вернуться к маршруту одной кнопкой.
- **Effort.** День.
- **Dependencies.** R1/R2.

### L2 «Управляемый тур» — заменить скачки на понятный просмотр

**Статус:** `MVP done` (2026-07-16) — tour state machine, pause/resume/prev/next,
reduced-motion fallback, no `setInterval`, completion returns to route overview.

- **Problem.** Текущий «полёт» не помогает ориентации: `setInterval` каждые 620 мс
  переключает stop, а не строит непрерывное движение с сохранением направления.
- **Evidence.** Historical: прежний полёт перескакивал по timer. Current: `tourState`,
  `goToStop()`, `scheduleNextTour()` and `toggleTour()`; contract test asserts no
  `setInterval` and route-fit on completion.
- **Proposed.**
  1. Тур = deterministic state machine: `idle`, `playing`, `paused`, `step`.
  2. Переход между остановками 1.2-1.8 секунды, easing без потери forward-axis.
  3. Manual controls всегда доступны; reduced-motion отключает автодвижение.
- **Files.** `app/ui/assets/kg_3d_template.html`.
- **DoD.** Пользователь может остановить тур, вернуться на предыдущую остановку и
  продолжить; active stop и reason не исчезают во время перехода.
- **Effort.** Полдня-день.
- **Dependencies.** R1.

---

## Волна `wave-kg-product-proof` (P1/P2)

### V1 «Визуальный контракт экспорта» — тестировать не только HTML-строки

**Статус:** `partial done` (2026-07-17) — contract tests cover route-first HTML,
offline/no external script, `DAY_ROUTE`, no worth-height, no topbar, smart labels,
hover/click-to-local, no dead audio/rubric badges, Home/tour/resize route-fit. Opt-in
Playwright smoke exists behind `HT_RUN_KG_3D_VISUAL=1` and checks 1366x768 + 1920x1080;
mandatory screenshot/canvas CI is still pending because browser binaries are not a
standard dependency.

- **Problem.** Текущие тесты доказывают сериализацию, offline-безопасность и наличие
  canvas, но не ловят главный провал: непонятный первый кадр, обрезку, пустоту, коллизии
  текста и потерю ориентации.
- **Evidence.** `tests/test_knowledge_graph_counters.py` covers `build_kg_3d_html`,
  edges/nodes, `DAY_ROUTE`, escaping, отсутствие внешних script src, route-first
  contract and opt-in browser smoke. В обычном CI visual smoke пропущен, поэтому V1
  остаётся partial, а не full.
- **Proposed.**
  1. Добавить lightweight browser/canvas smoke для generated HTML: canvas не пустой,
     route labels present, route stops count visible in DOM/sidebar.
  2. Для ручного QA сохранить чеклист: 1366x768, 1920x1080, first frame, Home,
     next/prev, all graph.
  3. Если Playwright недоступен в targeted-test окружении, оставить Python/DOM contract
     + screenshot script как dev check.
- **Files.** `tests/test_knowledge_graph_counters.py`; возможно `scripts/` для ручного
  screenshot-check, если это не раздувает runtime.
- **DoD.** Тесты ловят отсутствие route-scene, external script, пустой canvas contract
  и потерю embedded `DAY_ROUTE`; ручной чеклист приложен к docs/user guide или plan note.
- **Effort.** Полдня.
- **Dependencies.** R1/R2.

### V2 «Режим всей карты и дополнительные бейджи»

- **Problem.** Audio/rubric и полный граф полезны, но если они попадут в первый кадр,
  они снова утопят маршрут. B2 из №15 не должен становиться новой причиной шумного
  интерфейса.
- **Proposed.**
  1. Audio/rubric показывать как бейджи/действия выбранного узла, не как слагаемые
     геометрии и не как обязательный P0.
  2. Full graph mode включается вручную и сохраняет фильтры подписи/рёбер.
  3. C1 iframe рассматривать только после прохождения теста ориентации экспортной версии.
- **Files.** `app/ui/assets/kg_3d_template.html`, `docs/user_guide.md`.
- **DoD.** P0 route mode не меняется; дополнительные сигналы не увеличивают число
  подписей первого кадра; full graph не является default.
- **Effort.** Дни.
- **Dependencies.** R1/R2/L1.

---

## Рекомендованный порядок

R1 → R2 → V1 → L1 → L2 → V2.

**North star:** человек открывает 3D-карту и без вращения отвечает тремя фразами:
«я здесь», «дальше сюда», «потому что...».

**Метрики.** Визуальный шум первого кадра: 164 узла + 367 связей + глобальные
lesson/high-worth labels → route-only scene с ≤10 route labels/callouts. Видимых
остановок маршрута: не гарантировано → 6/6 для стандартного A2 route. Worth в
геометрии: да → нет, только rank/reason. Route action: скачки таймера → управляемый
тур. Порядок уроков: id-sort → `precedes`/course order. Статус B1:
`technical done · product failed` → `technical + product route-scene done`.

**Не делать в P0.**
- Не добавлять новую схему payload.
- Не начинать с Three.js/WebGL ради «настоящего 3D»; сначала доказать ориентацию.
- Не показывать полный граф первым экраном.
- Не использовать worth как высоту.
- Не продвигать 3D iframe в продукт до прохождения ориентационного теста.
