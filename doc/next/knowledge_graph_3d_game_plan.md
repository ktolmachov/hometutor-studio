# Knowledge graph 3D game: candidate plan («Дверь и вчерашний день»)

**Источник:** эволюционный разбор №18
(`doc/presentations/evolutionary_analyses/18_kg_konspekt_3d_game.html`), 2026-07-16,
синтез Граф Знаний + Живой конспект + 3D-зал (триада по слову владельца) на базе
разборов №1 (петля памяти), №14 (качество конспектов), №15/№17 (3D-зал).

**Evidence-база и её свежесть.** Проверено на hometutor @ `ec9a3c250` «275»
(2026-07-17…18). Сводка исполнения:

| Слой | Commits | Статус |
|---|---|---|
| G0–G3 (мост, actions, память, инвентарь) | 257–263 | ✅ |
| U0–U4 + V2′ (Memory Run UI) | 264–265 | ✅ |
| Overlay rank+✓ + live DOM gates | 269–270 | ✅ |
| R1 chrome · R2 toast · R3 hall | 271–272 | ✅ |
| W0 quality Q1–Q9 (vision audit) | 273–274 | ✅ bulk |
| W0′ residual + W1 dawn/lanterns | WT 2026-07-18 | ✅ uncommitted (verify-pass) |
| W2a fog + calm world | WT 2026-07-18 | ✅ uncommitted |
| W2b action review → Flashcards | WT 2026-07-18 | ✅ uncommitted |
| W3a Keeper infra | @279 | ✅ |
| W3b Keeper guide (A) | @280 | ✅ |
| W3c Keeper threats (B) | @281 | ✅ |
| W4a sidebar «В Мнемополис» | WT 2026-07-18 | ✅ uncommitted |
| W4b return CTA after quiz | WT 2026-07-18 | ✅ uncommitted |
| W4c district doors MVP | @286? / prior | ✅ |
| W4d return after FC/collect | WT 2026-07-18 | ✅ uncommitted |
| G4.1 floor tint · G4.2 history replay | 275 | ✅ |
| G4.3 «фото дня» | WT / runtime | ✅ local PNG only (no cloud/share) |
| Мнемополис (разбор №20) | vision v1 | 🟡 W0′+W1 done in WT; next W2a / catalog |

**Line-refs в исторических разделах G0–G3 — ориентиры на момент реализации, не
контракт**; сверять по имени функции. Актуальный порядок и статусы — в разделе
«Ревизия v2» ниже.

**Связь с планами №15/№17.** Это продолжение линии, не замена:
- `knowledge_graph_3d_plan.md` владеет A1/A2 (worth, day_route) и объявил C1 (iframe)
  и C2 (route trace) отложенными;
- `knowledge_graph_3d_reorientation_plan.md` закрыл ориентацию (route-first сцена,
  R1/R2/L1/L2) — отчёт `knowledge_graph_3d_done_report_2026-07-16.md`. C1 (iframe в
  продукт) + V2′ gate: **закрыты** (embedded-зал + always-on structural/visual smoke);
- этот план материализует C1 + C2 как **игровую петлю**: дверь из остановки в действие
  (изучить / собрать в конспект) и след прогресса по квизам в сцене. UI-скин Memory Run
  (U0–U4) закрыт в v2.

---

## Ревизия v2 — 2026-07-17…18 (hometutor @ `ec9a3c250` «275»)

**Статус волн v1 по факту:** G0 ✅, G1 ✅, G2 ✅, G3 ✅ — коммиты 257–263
(компонент `app/ui/assets/kg_3d_component/index.html`, action-мост `_kg3d` с nonce и
dedup, `start`→Quiz + `collect`→workbench в `app/ui/dashboards_graph.py`, память
`__MASTERY_HISTORY__`/`__SNAPSHOT_DATE__`, ◆ и счётчик корзины в шаблоне).
**G2 overlay-контракт (ранг + ✓):** regression fix **@269**, live DOM gate **@270**.

### Статус волн v2 (UI Memory Run) — **DONE** (+ polish / W0 / G4 partial)

| Волна | Статус | Evidence (hometutor) |
|---|---|---|
| **U0** Memory Run parity | ✅ | skin + **R1** topbar≤72 / ←▶→⋯; **R2** toast; **R3** hall lanes; **W0** axis/nav/fitCamera; rank+✓ (@269) |
| **V2′** Gate | ✅ | design contract + viewport matrix always-on; live rank/✓ (@270); chrome/toast/hall asserts (@271–274) |
| **U1** Карточка ценности | ✅ | eyebrow/роль, W, mastery-ring, chips due/novel/✓/◆, дата квиза из `MASTERY_HISTORY` |
| **U2** Дверь Obsidian | ✅ | `_concept_sections_view_model` → `__CONCEPT_SECTIONS__`; «Открыть раздел» embedded-only; export без URI |
| **U3** Внутрь узла | ✅ | `openInterior` / «Внутрь» / 2-й клик; sticky opaque head (W0 Q6); Esc/✕ |
| **U4** Правила + экскурсия | ✅ | `#onboard` + «?»; Тур → «Экскурсия дня» |
| **G4** прогрессия/реплей | ✅ | **G4.1+G4.2 @275** · **G4.3 photo** ✅ local PNG only |

**Write-set (накопительно):** `app/ui/assets/kg_3d_template.html`,
`app/ui/knowledge_graph_d3.py`, `app/ui/dashboards_graph.py`,
`app/ui/assets/kg_3d_component/index.html`, `tests/test_knowledge_graph_counters.py`,
`docs/user_guide.md` (+ polish/W0/G4 primarily in `kg_3d_template.html` + counters tests).

**Живой прогон (агент, 2026-07-17 @265):** Streamlit embedded 3D-зал — topbar/compass/routeOn,
CTA, inventory, interior. **Пост-v2 / polish (269–275):** Playwright production HTML +
pytest `test_knowledge_graph_counters.py` + `test_knowledge_graph_d3_section.py` —
**78 passed**. Literal pixel-perfect vs golden mockup — ⚠️ (mockups в studio; gates structural/DOM).

**Ops (2026-07-17):** `ingest.py --reset` → `EMBED_MODEL=text-embedding-qwen3-embedding-0.6b`
stored=config (15 files / 414 nodes); mismatch pplx↔qwen3 снят.

**Исторический прогон владельца (@263, до v2 UI):** G0–G3 работали, UI аскетичен —
закрыто U0–U4 + polish.

### Диагноз: почему реализация ≠ макет

1. **Визуальный контракт не был волной.** Раздел «UI reference v2 — Memory Run» ниже
   прямо помечен «не отдельная backlog-задача», а волны G0–G3 описывали только
   трубопровод (мост, действия, память, инвентарь). В итоге все функции макета
   реализованы — но внутри старого аскетичного шаблона №17: панель = пульт из ~10 мелких
   кнопок со шрифтами 10–12px (`kg_3d_template.html:12-44`), один фиолетовый акцент
   `#8b5cf6` на `#0a0a0f`, ни топбара, ни карточки остановки, ни большого CTA, ни
   компаса. Функциональный паритет достигнут; визуальный даже не планировался.
2. **Kill switch перечитан шире, чем написан.** Запреты («ни одной новой
   подписи/сущности в первом кадре», «без Three.js/частиц») — про шум и домен. Палитра,
   типографика и композиция панели под них не попадают, но план не выделил разрешённый
   фронт работ по арт-дирекции — и её никто не тронул.
3. **V2-gate меряет живучесть, не дизайн** («canvas не пуст, ≤8 подписей») — он зелёный
   на любом некрасивом зале; к тому же всё ещё opt-in. Дизайн-паритет с reference не
   требует ни один тест. (Тот же урок, что с пустым canvas №17: статические проверки
   проходят — живой прогон разочаровывает.)
4. **Токены reference живут в другом репо** (`--kgx-*`,
   `18_kg_3d_hall_route_mockup.html:195-209` в studio), production-шаблон — в hometutor;
   общего файла токенов нет, дрейф был механически неизбежен.
5. **Reference — постановочная сцена, production — генерическая проекция реальных
   данных:** в макете дуга маршрута и портальные рамы скомпонованы вручную; в production
   фоновые точки и тусклые рёбра конкурируют с маршрутом за внимание.

### Решение по UI (зафиксировано): Memory Run — production-скин, а не «референс для вдохновения»

Третий дизайн не изобретать. Reference уже (а) одобрен владельцем («в разборе зал
выглядит круче»), (б) фиксирует state-machine, семантику цвета и responsive-контракт,
(в) offline и написан на том же canvas 2D — переносится без Three.js.

Рассмотренные альтернативы — отклонены:
- **светлая тема** — «мрачно» лечится контрастом и иерархией, а не белым фоном: reference
  такой же ночной, но читается; светлая тема ломает образ ночного зала памяти;
- **Three.js/WebGL** — запрещён kill switch и не нужен: reference достигает вида на
  canvas 2D;
- **новый редизайн с нуля** — дороже, без валидации владельцем, и снова разойдётся с
  разбором №18.

### Волна `wave-kg-memory-run-parity` (P0) — ✅ DONE 2026-07-17 (@264–265)

#### U0 ✅ «Memory Run parity» — порт арт-дирекции reference в production-шаблон

- **Status.** ✅ Реализовано: Memory Run = production-скин `kg_3d_template.html`.
  Post-audit @269: список done-остановок — номер + `.stop-check` ✓ (не замена номера).
- **Problem.** См. диагноз: весь UI-слой шаблона — пульт №17.
- **Proposed.**
  1. Скопировать kgx-токены палитры (§«Арт-дирекция» ниже; источник —
     `18_kg_3d_hall_route_mockup.html:195-209`) в `kg_3d_template.html`; палитра
     scoped внутри компонента, как и было решено.
  2. Топбар 64px: бренд, segmented-переключатель «Маршрут / Созвездие / След памяти»
     (маппинг уже решён ниже: Созвездие = `local`, След памяти = `route` + overlay),
     прогресс «N из M» + кольцо.
  3. Правая панель 314px как в reference: eyebrow «ОСТАНОВКА N · <роль>», заголовок
     ~1.5rem, причина, строка памяти + mastery-кольцо, пара CTA — «▶ Начать» (градиент
     cyan→lime, тёмный текст, высота ≥40px) и «В конспект»; список остановок со
     статус-подстрочником; футер-инвентарь «Живой конспект · N разделов».
  4. Сцена: акцент зависит от режима; пройденный участок тропы — сплошной зелёный,
     будущий — пунктир; компас; подписи ≥12px с halo; фоновые узлы приглушить сильнее.
  5. Пульт расформировать: Home/Сверху/Сброс → иконки-кнопки на сцене; «Тур» → U4;
     «След памяти» → сегмент топбара; ◀/▶ → стрелки на сцене (как в reference).
  6. Kill switch не задет: состав первого кадра (≤8 подписей, никаких новых сущностей)
     не меняется — меняется скин.
- **Files.** `app/ui/assets/kg_3d_template.html` (CSS/markup/draw);
  `tests/test_knowledge_graph_counters.py` (обновить контракты панели + структурные
  проверки скина: топбар присутствует, CTA ≥40px, шрифт подписей канвы ≥12px).
- **DoD.** Скрин production embedded-зала рядом со скрином reference на сопоставимых
  данных различается данными, а не дизайном; **обязателен живой прогон** (запущенный
  Streamlit, не статический diff — урок №17); route-кадр не потерял контракт ориентации.
- **Effort.** 1–2 дня.
- **Dependencies.** Нет. Блокирует U1–U4 (они рендерятся уже в новой панели).

#### V2′ ✅ «Gate по-настоящему» — уточнение V2

- **Status.** ✅ Реализовано (2026-07-17).
- Структурный design-contract always-on:
  `tests/test_knowledge_graph_counters.py::test_3d_memory_run_design_contract_static`
  (topbar, CTA ≥40px, `--kgx-*`, export без дверей).
- Viewport matrix always-on (Playwright+Chromium):
  `test_3d_visual_smoke_viewport_matrix` — 1366×768, 1920×1080, 1024×768, 390×844;
  opt-out только `HT_SKIP_KG_3D_VISUAL=1` (не opt-in).
- Живой прогон Streamlit embedded-зала подтверждён при закрытии U0–U4.

### Волна `wave-kg-doors` (P1) — ✅ DONE 2026-07-17

#### U1 ✅ «Карточка ценности узла» — показать всё, что payload уже знает

- **Status.** ✅ Реализовано в карточке остановки (скин U0).
- **Problem.** `updateStopInfo` (ранее) выводил 3–4 строки 11px:
  label, причину, mastery %, «дальше». Владелец: «информации по ценности узла мало».
- **Proposed.** В карточке остановки (в скине U0): роль-eyebrow из `worth_reason`,
  W-ранг, mastery-кольцо, чипы `due`/`novel`, дата последнего quiz-события по концепту
  (из `MASTERY_HISTORY` — уже в шаблоне). Всё — существующие render-данные; домен не
  трогаем. Минуты («Начать · 12 мин» из reference) — только при честной render-side
  оценке (например, по числу разделов конспекта); выдумывать длительность запрещено.
- **Effort.** Полдня. **Dependencies.** U0.

#### U2 ✅ «Дверь в Obsidian» — открыть раздел конспекта из зала (embedded-only)

- **Status.** ✅ Реализовано: `_concept_sections_view_model` + `__CONCEPT_SECTIONS__`
  (export = `{}`, без URI).
- **Problem.** Из зала можно собрать разделы в корзину, но нельзя открыть сам раздел:
  двери в Живой конспект/Obsidian нет. Механика в продукте уже есть: `obsidian_uri`
  (`app/obsidian_export.py:168`) и per-section ссылки во flashcards
  (`app/flashcard_handoff.py:246`).
- **Proposed.** Python при rerun считает view-model «разделы концепта»
  `[{heading, in_basket, obsidian_uri}]` тем же поиском, что `collect`
  (`_collect_concept_sections_to_workbench`, `app/ui/dashboards_graph.py:487`:
  `build_section_index` + `best_section_for`), и передаёт **component args**
  (view-model, embedded-only — тот же канал, что G3). Кэш в `st.session_state`; если
  индекс дорогой — считать только для активной остановки. Карточка рендерит
  «Открыть раздел» ссылками `obsidian://`; в export дверей нет (vault/корзина не
  запекаются).
- **Kill switch.** Не задет: view-model input, домен и хранилища не меняются.
- **Files.** `app/ui/knowledge_graph_d3.py` (args), `app/ui/dashboards_graph.py`
  (view-model), `kg_3d_template.html` (рендер ссылок); тесты: args-контракт, export без
  ссылок.
- **Effort.** День. **Dependencies.** U0; механика args G3 (есть).

#### U3 ✅ «Внутрь узла» — drill-down интерьер

- **Status.** ✅ Реализовано: `openInterior` / close, panel-state, не новая 3D-сцена.
- **Problem.** «Провалиться внутрь узла нельзя»: клик = фокус камеры, второго уровня нет.
- **Proposed.** Второй клик по активной остановке (или кнопка «Внутрь» в карточке) →
  короткий подлёт камеры в узел (~200мс; при `prefers-reduced-motion` — мгновенно) →
  поверх сцены открывается **интерьер узла** (panel-state, не новая 3D-сцена; сцена
  приглушается): разделы конспекта концепта (view-model U2) со статусами ◆ и дверями
  Obsidian; связи precede/follows из `EDGES`; последние quiz-события. Действия — те же
  `start`/`collect` (concept-level; per-section collect — отдельный кандидат: потребует
  поля `section_id` в action-envelope). Esc/крестик — назад в зал.
- **Kill switch.** Не задет (render-слой); первый кадр не меняется.
- **Effort.** 1–2 дня. **Dependencies.** U0, U2.

### Волна `wave-kg-clarity` (P2) — ✅ DONE 2026-07-17

#### U4 ✅ «Правила зала + экскурсия»

- **Status.** ✅ Реализовано: onboarding `#onboard` + «?»; легенда-петит снята;
  кнопка тура → «Экскурсия дня».
- **Problem.** Правила зала — легенда 10px (старый шаблон); смысл тура
  (автопролёт камеры) владельцу не ясен.
- **Proposed.**
  1. **Onboarding-оверлей** при первом открытии embedded-зала за сессию (component arg,
     UI-state): полупрозрачный слой с 3 указателями — «ты здесь», «дальше сюда, потому
     что …», «✓ был в квизе · ◆ в конспекте» — и кнопкой «Понятно»; повторный вызов —
     кнопка «?» в топбаре. Легенду-петит убрать.
  2. **Тур → «экскурсия дня»:** на каждой остановке — причина и статус крупно в карточке,
     финал — CTA «Начать <первый непройденный>» (финал уже реализован в G1). Если после
     U0 и onboarding экскурсия не даёт ценности поверх ◀/▶ — кандидат на удаление кнопки
     (меньше пульт, меньше правил).
- **Effort.** День. **Dependencies.** U0.

### Актуальный порядок и метрики (v2) — прогресс @275

**Исполнено:**
- P0 U0+V2′ · P1 U1+U2 · P2 U3+U4 — **@264–265** ✅  
- Post-audit rank+✓ overlay — **@269–270** ✅  
- R1 chrome · R2 toast · R3 hall — **@271–272** ✅  
- W0 Q1–Q9 bulk (axis/nav, compass, fitRouteCamera margin, status, links,
  smooth path, ring track) — **@273–274** ✅; residual W0′ остаётся отдельно
- G4.1 floor tint · G4.2 history replay — **@275** ✅  

**Осталось в этом плане:** — (G4.3 local PNG ✅; cloud/share = privacy out of scope).  
**Мнемополис (№20):** `knowledge_graph_3d_world_vision.md` — каталог §11 shipped @305; residual = optional live polish / metrics.

| Что | Было (@263) | Стало (@275) |
|---|---|---|
| Панель | пульт: ~10 кнопок, 10–12px | ✅ топбар + карточка + 2 CTA; R1 topbar≤72, `?` в progress |
| Читаемость | серые 10–12px | ✅ ≥12px + halo, `--kgx-*`; W0 axis выше nav |
| Ценность узла | 3 строки 11px | ✅ роль + W + mastery + due/novel + дата квиза |
| Дверь в конспект | только collect | ✅ + Obsidian `kgx-link-btn` (Q5) embedded |
| Внутрь узла | нельзя | ✅ interior + sticky opaque head |
| Правила / тур | легенда 10px / автопролёт | ✅ onboard + «Экскурсия дня» |
| Визуальный gate | opt-in, 1 viewport | ✅ structural + viewport matrix + live overlay DOM |
| Список done | ✓ заменял номер | ✅ rank + `.stop-check` overlay |
| Toast ack | нет | ✅ R2 `#toast` / `showToast` |
| Сцена «зал» | пустой космос | ✅ R3 lanes/grid/underglow; Q8 smooth path |
| Camera / mobile | crop на 390 | ✅ W0 `fitRouteCamera` margin clamp; residual vertical fill/mobile overlap → W0′ |
| G4 этажи / реплей | — | ✅ G4.1 tint local/all · G4.2 `#replaybar` |
| G4 фото дня | — | ✅ local PNG (`downloadHallPhotoLocal`); no cloud |

**Не делать (дополнение к списку v1).**
- Не изобретать третий дизайн — только паритет с reference №18.
- Не заменять контраст светлой темой.
- Не выдумывать минуты/длительности без render-side основания.
- Не считать UI-волну «сделанной» без живого прогона running-артефакта.

---

## Терминология и границы схемы

**Триада синтеза.** Граф Знаний (мир/экономика), **Живой конспект** (инвентарь/крафт:
корзина `workbench_service`, паспорт качества №14, scoped quiz), 3D-зал (сцена).

**Два разных «контракта» — не путать (устраняет ложный конфликт kill switch ↔ G1/G2/G3):**
- **Payload domain schema** — поля узлов/рёбер/статов, которые считает `build_kg_payload`
  (`worth`, `due`, `novel`, `mastery`, `mastery_history`, `decay_vector`, …).
  **Заморожена.** Новых доменных полей и источников данных не вводим.
- **3D render contract** — то, что `build_kg_3d_html` подставляет в шаблон и как шаблон
  это рисует (плейсхолдеры, режим export/embedded, view-model). **Расширяемо.**
  Передать в 3D уже посчитанные ключи payload (`mastery_history`/`decay_vector`) или
  добавить флаг режима — это расширение render-контракта, а НЕ смена доменной схемы.

**Два режима честности (матрица) — не смешивать (устраняет противоречие offline/live):**

| Режим | Как рендерится | Данные | Действия наружу |
|---|---|---|---|
| `export` | скачанный самодостаточный HTML | **baked snapshot** в момент экспорта | нет: read-only, кнопки деградируют в подсказку |
| `embedded` | iframe/компонент внутри продукта | live payload + мост к Streamlit | есть: `start`/`collect` через мост |

Export **не может** читать живую корзину/память продукта — только запечённый снимок.
Только embedded имеет мост и живое состояние. Любое «прочитать корзину» / «записать в
workbench» — исключительно embedded.

**Два направления обмена — не путать (термины):**
- **Action bridge (child → Python):** зал шлёт намерение `{concept_id, action}` наружу —
  это и есть «мост» (G0). Только embedded.
- **Component args / view-model (Python → зал):** продукт передаёт в шаблон входные
  данные — это **не** мост, а вход компонента. Здесь важно **не путать два подмножества
  args**:
  - **общие для обоих режимов** (payload узлов/маршрута, флаг режима, `snapshot_date`) —
    в `export` запечены в момент сборки, в `embedded` живые;
  - **только embedded** (live view-model корзины — множество «в конспекте», счётчик,
    случайный `session_nonce` текущей Streamlit-сессии для action-envelope) —
    в `export` **отсутствует/пустой**: скачанный файл живую корзину продукта не знает
    (см. G3). «Оба режима получают args» относится только к первому подмножеству.

**Про «мост в export».** Контракт export — «действия не срабатывают» (inert/read-only),
а не «строк моста нет в файле». Надёжный inert (не полагаться на «нет родителя»: в
standalone-HTML `window.parent === window`, и `postMessage` уйдёт самому себе — если
страница слушает свой тип, возможно ложное самосрабатывание):
- в `export` кнопки действий **не рендерятся** либо `disabled`/подсказка-only;
- обработчик `hometutor:kg-action` **gated `host_mode === 'embedded'`** — в export не навешан;
- тест проверяет **отсутствие side-effect** (состояние не меняется), а не поведение
  `postMessage`.
Offline-контракт №17 (нет внешних `<script src>`) при этом сохраняется.

**Kill switch.** Стоп, если: меняется **доменная** схема payload; появляется новое
хранилище; нужен LLM-вызов; вводится вторая валюта прогресса (XP/монеты/стрики/
лидерборды); игровой слой добавил хоть одну подпись или новую сущность в первый кадр
route-режима (ориентация №17 неприкосновенна). Расширение 3D render-контракта
(флаг режима, плейсхолдеры истории/decay, дата снимка, view-model корзины) под kill
switch **не попадает** — это слой рендера, не домен.

**Статус:** кандидаты, НЕ записи `backlog_registry.yaml` — владелец промоутит вручную.

---

## UI reference v2 — «Memory Run» (контракт; реализован как production-скин U0 ✅)

Интерактивный reference-макет встроен в разбор №18 и зафиксирован отдельно в трёх
автономных offline-файлах. В них одна сцена и одна state-machine, различается только
начальная конфигурация `scene_mode + memory_overlay`:

- `doc/presentations/evolutionary_analyses/18_kg_3d_hall_route_mockup.html` —
  `route`, золотой путь и первый кадр;
- `doc/presentations/evolutionary_analyses/18_kg_3d_hall_constellation_mockup.html` —
  `local`, контекст курса без возврата к шуму полного графа;
- `doc/presentations/evolutionary_analyses/18_kg_3d_hall_memory_mockup.html` —
  `route + memory_overlay=on`, текущая дорожка + след предыдущего снимка.

Это **визуальный и интеракционный контракт**, а не новый источник бизнес-логики:
данные в макетах синтетические и нужны только для проверки композиции. Production
берёт узлы/маршрут/worth/mastery из существующего render-контракта.

### Арт-дирекция и семантика цвета

Сильный образ — не «граф в чёрном космосе», а **ночной зал памяти с цветными
маршрутами-сигналами**. Декор архитектурный: перспективный пол, портальные рамы,
цветовые полосы глубины и компас. Частицы, случайные звёзды, bokeh и декоративные
сущности запрещены: они не несут состояния и возвращают визуальный шум №17.

Цвет — не украшение, а второй канал после формы/текста:

| Состояние | Цвет reference | Дополнительный канал |
|---|---|---|
| пройдено по quiz | lime/green | `✓`, сплошной участок тропы |
| активная остановка | electric violet | увеличенный узел + шестиугольный фокус |
| следующие остановки | cyan/blue/coral | номер ранга остаётся видимым |
| собрано в конспект | coral | ромб `◆` на существующем узле |
| след прошлого снимка | gold → coral | отдельная тонкая пунктирная траектория |
| текущий режим | accent режима | заливка выбранного сегмента + статус сцены |

Палитра scoped внутри 3D-компонента; notebook-палитра разбора №18 и продуктовая тема
Streamlit не меняются. Никаких сетевых шрифтов/CDN: системный sans, offline-контракт
сохраняется.

### Композиция и responsive-контракт

- **Desktop ≥861 px:** верхняя полоса 64 px; сцена доминирует; справа фиксированная
  колонка 314 px с одной активной остановкой, действиями и линейным списком маршрута.
- **Tablet ≤860 px:** панель уходит под сцену; список остановок — две колонки; canvas
  остаётся не ниже 480 px.
- **Mobile ≤560 px:** одна колонка остановок, действия вертикально, canvas не ниже
  420 px; нет горизонтального overflow и внутренних полос прокрутки.
- Заголовок активной остановки, причина, mastery и две команды всегда помещаются без
  обрезки. На canvas одновременно подписаны только active + next; полный список имён
  живёт справа/снизу.

### Режимы сцены

**⚠️ Миграция имён (reference → production, решено).** Runtime `kg_3d_template.html`
уже везёт `viewMode: route|local|all` (shipped #17, покрыт тестами). Reference-ярлыки
**не вводят новый nav-режим** и не переименовывают shipped enum:
- reference **`route`** = production `route` (тот же);
- reference **«Созвездие»** = **презентационный ярлык ровно одного режима —
  `local`** (ближайший контекст). Одна кнопка не может выбирать два режима сразу:
  `all` (полный граф) «Созвездием» НЕ является — это отдельное углублённое действие
  внутри «Созвездия» (существующая кнопка «Вся карта»), не третий ярлык. Production
  `scene_mode` остаётся `route|local|all`;
- reference **«След памяти» / `memory`** = **overlay `memory_overlay`** (G2), ортогональный
  `scene_mode` — может быть включён поверх `route`, а не отдельная навигация.

Ниже режимы описаны в reference-терминах для дизайна; production-контракт — три строки
выше.

1. **`route` — первый кадр и основной продуктовый путь.** Видны `route.length`
   остановок, вход/сегодня/дальше, active + next и минимум фонового контекста. Этот
   режим открывается всегда; последний выбранный режим не персистим, чтобы не потерять
   ориентацию.
2. **«Созвездие» (= `local`) — контекст.** Добавляет ближайший контекст и рёбра к нему;
   route остаётся поверх и не теряет ранги. Фоновые узлы кодируются цветом/размером, но
   не получают постоянных подписей. Полный граф (`all`) — отдельное углублённое действие
   внутри «Созвездия» (кнопка «Вся карта»), в переключатель режимов не выносится.
3. **«След памяти» (= `memory_overlay`) — снимок.** Поверх текущего `scene_mode` рисует
   смещённую траекторию предыдущего snapshot. В export рядом виден `snapshot_date`; слова
   «сегодня/вчера» запрещены. В embedded допустимы live-метки при наличии реальной даты.

### UI state-machine и взаимодействия

Минимальное состояние компонента:

```text
host_mode:    export | embedded          # канал/gating, НЕ навигация (см. G0)
scene_mode:   route | local | all        # канонический enum рантайма (shipped #17)
memory_overlay: on | off                 # G2-след снимка, поверх любого scene_mode
selected_concept_id: string
done_concept_ids: Set<string>       # только quiz-сигнал G2
collected_concept_ids: Set<string>  # embedded view-model G3 (только host_mode=embedded)
pending_action: null | {event_id, action, concept_id, phase}  # один in-flight action
```

`host_mode` и `scene_mode` — **независимые оси**: первое определяет доставку/gating
действий (export inert, embedded с мостом), второе — навигацию по сцене. Смешивать
(как было `mode==='embedded'` ↔ навигационный режим) нельзя.

- Клик по узлу или строке маршрута меняет только `selected_concept_id` и камеру.
- `←/→` и клавиши стрелок проходят по `day_route`; границы не зацикливаются.
- `Начать`/`В конспект` создают action-event. Одновременно разрешено **ровно одно**
  действие: единый `pending_action` блокирует обе команды до ack/error/rerun, но не
  мешает осматривать другие остановки; статус всегда называет исходную остановку.
- После успешного `collect` Python возвращает обновлённые component args, и только они
  являются источником истины для `◆` и счётчика. Макет может показывать optimistic
  pending, но не имеет права окончательно «нарисовать успех» без ack. `collect` —
  **add-only**: для уже собранного концепта кнопка disabled; удаление потребует отдельного
  действия/подтверждения и в эту волну не входит.
- После quiz-события новый payload меняет `done_concept_ids`, mastery и следующий
  маршрут; UI не начисляет локальные XP и не симулирует доменный прогресс.
- Motion: только движение тропы, фокус-рамка и мягкая параллакс-реакция; при
  `prefers-reduced-motion` сцена статична, все состояния остаются читаемыми.

### Компонентные зоны (production mapping)

| Зона reference | Источник production | Действие |
|---|---|---|
| верхний progress `N/M` | `day_route` + quiz progress G2 | read-only |
| canvas route | `nodes`, `edges`, `day_route`, worth/rank | select/focus |
| карточка остановки | selected node + `worth_reason`, mastery/decay | `start` / `collect` |
| список маршрута | тот же `day_route` | select/focus |
| `◆` и счётчик конспекта | embedded component args G3 | обновляются после ack |
| memory trace | `mastery_history` + `snapshot_date` G2 | read-only |

### UI DoD

- Три standalone-макета открываются напрямую, не имеют внешних `<script src>`,
  показывают соответствующую начальную конфигурацию и остаются интерактивными.
- В route-кадре путь считывается за 5 секунд: вход → active → next; active/next не
  зависят только от цвета и называются без вращения.
- `Начать` показывает **pending → демо-ack** и НЕ трогает mastery/`done` (это только
  намерение навигации; в production `done`/mastery приходят из реального quiz-события,
  не из клика). `В конспект` показывает pending, а маркер и счётчик меняет только после
  ack; повторный collect disabled. Пока одно действие pending, обе CTA заблокированы,
  статус не теряет исходную остановку при смене фокуса. Timeout/error снимает блокировку
  и предлагает повторить, не меняя доменное состояние; в reference этот путь
  воспроизводится fixture-атрибутом `data-demo-ack="timeout"`.
- 1366×768, 1920×1080, 1024×768 и 390×844: нет overlap, горизонтального overflow,
  обрезанных кнопок/заголовков; canvas не пустой.
- Contrast текста/команд ≥ WCAG AA; native focus-ring не отключается; canvas имеет
  `aria-label`, все действия доступны через semantic buttons.

---

## Волна `wave-kg-game-bridge` (P0) — не больше двух ходов

Риск игровой петли — в мосте: если embedded-компонент не умеет вернуть действие в
Python, «дверь» не открывается. Поэтому P0 = **сначала доказать мост (read-only), потом
повесить на него действия**. Навигация и запись разделены: у них разные риски и границы.

### G0 ✅ (реализовано, 257–263) «Мост действия» — embedded 3D возвращает `{concept_id, action}` (только UI-state, без доменной записи)

- **Problem.** 3D-шаблон не имеет ни одного канала наружу: в `kg_3d_template.html` нет
  `postMessage`, нет `setComponentValue`, нет ссылок. Простой `components.html(...)`
  (обычный sandbox-iframe) **архитектурно не может** вызвать Python — вернуть значение
  умеет только custom-компонент. Значит «клик в зале → действие в продукте» сперва надо
  **доказать как факт**, а не предположить.
- **Evidence.** 2D-карта уже решает это проверенным мостом: `declare_component("kg_d3")`
  (`app/ui/knowledge_graph_d3.py:741`, путь `assets/kg_d3_component`) → обёртка
  `kg_d3_component/index.html` хостит произвольный HTML через `srcdoc` и возвращает
  значение двумя каналами: `setComponentValue` (`:24-28`) и форс-rerun через `_kgc`
  query-param (`syncConceptSelection`, `:32-43`); слушает `postMessage`
  `hometutor:kg-select` от внутреннего фрейма (`:57-59`). 3D-шаблон в этот мост пока
  ничего не шлёт (grep `postMessage` по `kg_3d_template.html` — пусто).
- **Формат возврата — не ломать 2D (решено).** Текущий `kg_d3_component` возвращает
  **строку** (concept id): `setComponentValue(String(value))`, Python читает
  `selected_concept: str`. Нельзя молча заменить на `{concept_id, action}` — 2D-контракт
  сломается. **Зафиксировано: отдельный компонент `kg_3d_component`** со своим контрактом;
  строковый 2D-компонент не трогается вовсе (изоляция рисков). Вариант «общий компонент
  с envelope и обратной совместимостью» отклонён — экономия одного файла не стоит
  связывания контрактов.
- **Событийная модель — selection ≠ action.** В сцене клик по узлу/остановке уже значит
  **навигацию/фокус внутри сцены** (`focus`, локальный контекст). Действие наружу
  посылают **только кнопки** «▶ Начать» / «➕ В конспект» в карточке остановки — не сам
  клик по остановке. Смешивать нельзя (ложные срабатывания).
- **Проблема канала (решить ДО реализации, один выбор — не «на выбор»).** Component
  value (`setComponentValue`) под `@st.fragment` partial-rerun **может проглатываться** —
  именно поэтому 2D держит query-param `_kgc` как форс-rerun. Но `_kgc` несёт только
  `concept` (`syncConceptSelection`), для действия этого мало. Значит «полагаться только
  на component value» и «тест текущего поведения» — **не механизм доставки**, а
  `sessionStorage` сам по себе Python ничего не отдаёт. **Решение зафиксировано:
  единственный канал доставки action — query-param `_kg3d`**, по образцу проверенного
  `_kgc`, но action-safe. Action-envelope через `setComponentValue` **не отправляется
  вовсе**: это тоже канал доставки в Python, а не «UI-подсказка», и второй канал дал бы
  двойную доставку одного события. За `setComponentValue` остаётся только
  selection-синхронизация (строка concept id, как в 2D). Optimistic pending — внутреннее
  состояние child-сцены, выставляется до `postMessage` и живёт до ack.
- **Proposed.**
  1. При создании embedded-компонента Python генерирует 128-битный случайный
     `session_nonce`, хранит его в `st.session_state` и передаёт сцене только как
     component arg. Envelope:
     `{version:1, source:'kg3d', event_id, session_nonce, concept_id, action}`,
     `action ∈ {'start','collect'}`. `event_id` — уникальный на нажатие UUID/ULID;
     nonce привязывает старый URL к конкретной Streamlit-сессии. Клиентский timestamp
     **не является** защитой от replay: он подделывается и потому в security-контракт
     не входит.
  2. В 3D-шаблоне (только `host_mode==='embedded'`) **кнопки** карточки остановки шлют
     обёртке `postMessage({type:'hometutor:kg-action', version:1, source:'kg3d',
     event_id, session_nonce, concept_id, action})`. Событие без обязательного поля
     отклоняется. Обёртка кодирует envelope в **`_kg3d`** query-param и форсит
     full-rerun (переживает fragment-rerun, читается через `st.query_params`). Клик по
     узлу/остановке действие НЕ шлёт, только меняет `selected_concept_id`.
  3. Python-контракт `_kg3d` (валидация + защита от случайного replay):
     - **сериализация:** `base64url(minified JSON envelope)` — один параметр, без
       вложенных разделителей; предел длины **≤ 600 символов**;
     - **валидация:** `version===1`, `source==='kg3d'`, `action ∈ {'start','collect'}`,
       `concept_id ∈ node_ids`, `event_id` имеет допустимый UUID/ULID-формат,
       `session_nonce` в constant-time сравнении равен nonce текущей сессии;
     - **дедуп:** bounded map последних **64** `event_id → processing|succeeded|failed`
       (FIFO в `st.session_state`), а не безымянный set;
     - **порядок:** `validate → remove query param → reserve event_id → execute → ack`.
       Удаление `_kg3d` выполняется и для отклонённого/ошибочного значения, чтобы URL
       не зацикливал rerun. `event_id` резервируется до side effect: это доставка
       **at-most-once в пределах bounded dedup-window (последние 64 события)**, а не
       exactly-once и не гарантия на всю сессию. Ошибка получает состояние `failed`,
       error-toast и ручной retry с новым `event_id`;
     - `collect` дополнительно проверяет актуальное состояние workbench перед записью:
       повтор с другим `event_id` не дублирует уже собранные разделы. Это доменная
       идемпотентность операции, отдельная от транспортного дедупа;
     - успешный результат попадает в `st.session_state["kg_3d_action"]` (UI-state, не
       per-user persistence), после чего host-rerun возвращает сцене обновлённые args.
- **Files.** новый `app/ui/assets/kg_3d_component/index.html` (решено — отдельный
  компонент, см. «Формат возврата»), `app/ui/assets/kg_3d_template.html`
  (кнопки + `postMessage` подключены только при `host_mode==='embedded'`),
  `app/ui/knowledge_graph_d3.py` (`build_kg_3d_html` — embedded-флаг + чтение возврата),
  `app/ui/dashboards_graph.py` (встроить зал рядом с 2D);
  тесты: клик по **кнопке** в embedded-зале меняет `kg_3d_action`; malformed/длинный
  envelope, неизвестный concept, неверный nonce и повторный `event_id` отклоняются и
  очищаются из URL; повторный collect с новым `event_id` не дублирует разделы;
  в `export`-режиме кнопки inert (действие не срабатывает).
- **DoD.** В продукте: клик по кнопке действия в карточке остановки embedded-зала
  выставляет `st.session_state["kg_3d_action"]` и показывает toast. **Никакой доменной/
  per-user записи** (только UI-state). Повторная доставка `event_id`, пока он находится
  в окне последних 64 событий, не создаёт второе действие; URL из другой сессии не
  проходит nonce-проверку. В `export`-режиме кнопки inert; offline-контракт (нет внешних
  `<script src>`) сохранён.
- **Doc-sync.** —
- **Effort.** День.
- **Dependencies.** V2 (визуальный gate) для промоута iframe в продукт; сам мост можно
  доказывать за флагом раньше.

### G1 ✅ (реализовано, 257–263) «Действия продукта» — `start` (навигация) и `collect` (запись) поверх моста

- **Problem.** Мост доставляет намерение, но действий ещё нет: тур завершается «Маршрут
  дня завершён» без хода. Контраст: у карточки того же концепта в 2D дверь в конспект
  уже есть.
- **Evidence.** `kg_3d_template.html:855` (`scheduleNextTour` — терминальный финал),
  `updateStopInfo` (`:902` — причина без хода); `app/ui/dashboards_graph.py:892`
  («➕ Собрать всё по концепту» → `_collect_concept_sections_to_workbench`, `:183`);
  `app/workbench_service.py:310` (`add_section`); `living_konspekt_state.py:120`
  (UI-зеркало + событие `living_konspekt_section_added`, комментарий-фуннель уже
  упоминает «из графа»); `dashboards_graph.py:1113` (пока только `st.download_button`).
- **Proposed.** Два действия с **разными** границами — не смешивать:
  - **`start` (навигация, без записи):** `kg_3d_action == 'start'` → переключить режим
    через `st.session_state[PENDING_CURRENT_VIEW_KEY] = "Интерактивный Quiz"` / `"Flashcards"`
    (`app/ui/session_state.py`, паттерн `adaptive_plan_card.py:99-104`) — **не** писать
    `current_view` напрямую (StreamlitAPIException в callback). Преселект конкретного
    концепта: needs discovery — единого session-ключа «quiz по концепту» может не быть;
    если нет, `start` ведёт в режим по теме концепта, преселект — отдельным ходом. Риск —
    только UX.
  - **`collect` (запись в workbench):** `kg_3d_action == 'collect'` → вызвать
    существующую `_collect_concept_sections_to_workbench` (ту же, что 2D — ноль новой
    доменной логики) **только если** актуальный workbench ещё не содержит целевые
    разделы; toast как у 2D. Пока Streamlit не вернул обновлённые component args,
    единый `pending_action` блокирует обе CTA. Для уже собранного концепта `collect`
    disabled; обратного toggle/remove здесь нет. Пишущее действие покрыть отдельно.
  - **Финал тура:** вместо «Маршрут дня завершён» — «Дальше: <первый непройденный стоп>»
    с теми же действиями (в `export`-режиме — текущий текст, кнопки деградируют в
    подсказку «откройте в hometutor → Knowledge Graph → 3D-зал»).
- **Files.** `app/ui/assets/kg_3d_template.html`, `app/ui/dashboards_graph.py`;
  тесты: `start` меняет режим и не пишет в workbench; `collect` вызывает
  `_collect_concept_sections_to_workbench` ровно один раз и не создаёт дубль при новом
  `event_id`; export-кнопки не активны.
- **DoD.** Из embedded-зала: остановка → «Начать» открывает выбранный режим
  (quiz/flashcards) с best-available контекстом концепта, без записи (преселект
  конкретного концепта закрывается отдельным discovery/тестом, не гарантируется здесь);
  остановка → «➕ В конспект» пополняет корзину за 1 клик (toast как у 2D);
  export-HTML остаётся read-only; первый кадр route-режима не изменился (лимит подписей).
- **Doc-sync.** `docs/user_guide.md` (раздел Knowledge Graph / 3D-зал).
- **Effort.** День.
- **Dependencies.** G0; **iframe в продукт — только после V2**.

---

## Волна `wave-kg-game-proof` (P1) — gate раньше содержания

### V2 ✅ / V2′ ✅ (закрыто 2026-07-17 @264–265) «Обязательный визуальный gate»

- **Status.** ✅ Закрыто вместе с U0 (см. «Ревизия v2» / V2′). Iframe C1 (embedded-зал)
  в продукте уже работает; gate не блокирует.
- **Problem (исторический).** C1 нельзя было грузить, пока устойчивость сцены не
  доказана машинно; смок был opt-in (`HT_RUN_KG_3D_VISUAL=1`).
- **Сделано.**
  1. Opt-in снят: visual smoke always-on при наличии Playwright; opt-out
     `HT_SKIP_KG_3D_VISUAL=1`.
  2. Матрица viewport'ов: 1366×768, 1920×1080, 1024×768, 390×844.
  3. Объект gate — production `build_kg_3d_html` (+ structural design-contract скина U0).
  4. Контракт: canvas не пустой, `route.length` остановок, topbar/CTA≥40px, export inert.
  5. **@270:** live DOM — rank text на каждой остановке, `.stop-check` absolute только
     у done, topbar≥64 / side~314 (desktop), no `<script src>`; static contract +
     `test_route_stop_done_check_overlays_index` (anti-pattern ternary запрещён).
- **Tests.** `test_3d_memory_run_design_contract_static`,
  `test_3d_visual_smoke_viewport_matrix`, `test_route_stop_done_check_overlays_index`
  в `tests/test_knowledge_graph_counters.py`.

### G2 ✅ (реализовано, 257–263) «Вчера в зале» — снимок прогресса по квизам (честно суженный)

- **Problem.** `build_kg_3d_html` встраивает только NODES/EDGES/STATS/HEALTH/DAY_ROUTE;
  `mastery_history`/`decay_vector` в 3D не передаются. Сцена не отличает продвинутую
  остановку от непродвинутой.
- **⚠️ Честная граница охвата.** `build_mastery_history`
  (`knowledge_graph_d3_analysis.py:147`) строится **только** из `quiz_rows`
  (таблица `quiz_results`). Это значит: ✓ в зале = **«есть quiz-событие по концепту»**,
  а НЕ «любое действие сегодня». Сбор в конспект (`collect`), открытие quiz (`start`),
  flashcard-review (он идёт в SR/`decay_vector`, не в mastery_history) — этим сигналом
  **не отражаются**. Более широкая «память сессии» потребовала бы нового источника
  событий → конфликт с kill switch → **вне этого плана** (кандидат в отдельную волну
  петли памяти №1, не здесь). Поэтому North star сужен: «зал помнит твой прогресс по
  квизам», не «всё, что ты сделал».
- **Семантика времени (не wall-clock, не «сегодня»).** Export — это **снимок**. Помечать
  остановки не «сегодня/вчера», а «изменилось в последнем снимке / раньше», и показывать
  **дату снимка явно** («снимок от YYYY-MM-DD»). Иначе месячной давности экспорт вечно
  показывает «сегодня». В `embedded`-режиме (live) настоящие сегодня/вчера допустимы.
- **⚠️ Источник даты снимка — render-time, не из истории.** `mastery_history` даёт даты
  **quiz-событий**, а не дату экспорта. «Дата последнего квиза» ≠ «дата снимка» (снимок
  можно сделать через неделю без квизов). Значит `build_kg_3d_html` подставляет
  **отдельное render-time поле** (`__EXPORTED_AT__` / `snapshot_date`, = момент сборки
  HTML) — это добавка в **render-контракт**, не в доменную схему payload.
- **Evidence.** `app/ui/knowledge_graph_d3.py:719-733` (3D-embed без памяти) против
  `:712-713` (2D-embed с `__MASTERY_HISTORY__`/`__DECAY_VECTOR__`); payload уже несёт
  оба ключа (render-контракт, не домен).
- **Proposed.**
  1. Передать `__MASTERY_HISTORY__`/`__DECAY_VECTOR__` в `build_kg_3d_html` (уже
     посчитанные ключи — расширение render-контракта, домен не трогаем).
  2. Остановка с quiz-событием в последнем снимке — ✓ **оверлеем поверх рангового
     бейджа** (номер/worth-rank сохраняется — не заменять цифру, иначе теряется порядок
     маршрута); в export — подпись даты снимка (`snapshot_date`); в embedded — живой
     «сегодня». Никаких новых сущностей — только состояние существующего бейджа.
     **Status @270:** контракт enforced — side list `.stop-index` + `.stop-check`
     (@269), canvas `fillText(rank)` + adjacent ✓; regression test
     `test_route_stop_done_check_overlays_index` + live asserts in visual smoke.
  3. Плотнее пунктир между продвинутыми остановками. Никаких новых подписей.
- **Files.** `app/ui/assets/kg_3d_template.html`, `app/ui/knowledge_graph_d3.py`
  (`build_kg_3d_html` — `__MASTERY_HISTORY__`/`__DECAY_VECTOR__` + `__EXPORTED_AT__`);
  тесты: embed-контракт (`__MASTERY_HISTORY__` заменён, JSON script-safe), `snapshot_date`
  присутствует в export и рендерится, ранг остаётся видимым под ✓, лимит подписей не вырос.
- **DoD.** Остановка с quiz-прогрессом визуально отличается без вращения и без легенды;
  export честно подписан датой снимка; первый кадр — тот же route-контракт.
- **Doc-sync.** `docs/user_guide.md`.
- **Effort.** День.
- **Dependencies.** Лучше после G0/G1 (иначе память декоративна и неполна).

### G3 ✅ (реализовано, 257–263) «Инвентарь на сцене» — маркер «в конспекте» (embedded-only)

- **Уже закрыто в 254/256 — из плана убрано (иначе развернём разработку чинить
  исправленное):** hover-подписи (`hoverAt`, `kg_3d_template.html:986` + mousemove
  `:1073`), refit при resize (`:111` → `fitRouteCamera` в route-режиме), on-canvas
  причина активной точки (`drawActiveReasonCallout`, `:717`), приоритет подписей
  active > next > ранг (`labelQueue.sort` по `priority`, `:707-712`), убран hardcoded
  `/6` (`:1174` теперь `route.length/route.length`), убраны мёртвые бейджи
  `n.audio`/`n.rubric`. Контрактные тесты на `drawActiveReasonCallout`/`hoverAt` —
  в `test_knowledge_graph_counters.py` (254/256).
- **Problem (остаётся).** Сцена не показывает, что добыча уже собрана: нет маркера
  «в конспекте» и счётчика корзины.
- **⚠️ Только embedded, через component args (Python → зал), не через action-мост.**
  «В корзине ли раздел» — это **live product state**, его нет в
  `NODES/EDGES/STATS/HEALTH/DAY_ROUTE` и он не должен туда попадать (заморозка домена).
  Маркер приходит **входными аргументами компонента** (Python → сцена, view-model input) —
  это **другое направление**, чем action-мост G0 (сцена → Python). Термин «мост» здесь не
  использовать. В export маркера нет (корзина туда не запекается).
- **Proposed.**
  1. Embedded: Python передаёт в зал **component args'ами** множество «концепты, чьи
     разделы в корзине» (view-model input, не payload-домен, не action-мост); остановка
     получает маркер «в конспекте» (состояние существующего объекта, не новая сущность).
  2. Счётчик корзины в боковой панели зала — тот же счётчик, что у 2D
     (`dashboards_graph.py:906-912`).
- **DoD.** В embedded-зале остановка со собранными разделами помечена; счётчик совпадает
  с 2D; в export маркера/счётчика нет (честно — корзины там нет).
- **Effort.** День.
- **Dependencies.** G0 (embedded-компонент существует), G1 (`collect` наполняет корзину).

---

## Волна `wave-kg-game-progression` (P2)

### G4 «Прогрессия и реплей» — partial @275 (G4.1+G4.2 ✅ · G4.3 ⬜)

- **Status.** G4.1+G4.2 реализованы в `kg_3d_template.html` (hometutor @275):
  1. ✅ **Этажи:** `floorProgressScore` + fill/tint pad в `drawFloorPlane` **только**
     local/all; route-кадр не трогается. Mastery из текущего/replay snapshot,
     decay из `DECAY_VECTOR` (render-only).
  2. ✅ **Реплей:** `#replaybar` (◀ date ▶ ▷ Live); `historyReplayIndex` +
     `refreshMemorySetsFromHistory`; auto-play с reduced-motion → jump-to-live.
     Виден в local/all или при memory overlay / active scrub.
  3. ⬜ **Фото дня** — **не начат** (privacy DoD ниже).
- **⚠️ Privacy DoD (обязателен до реализации G4.3).** «Фото дня» содержит названия
  концептов/уроков и прогресс — потенциально чувствительное. До реализации явно
  зафиксировать: что именно попадает в shareable-экспорт; опция обезличивания (скрыть
  названия / только структуру и ранги); дефолт — приватный (локальный) экспорт, share —
  осознанное действие. Local-first: без загрузки на внешние сервисы.
- **Effort.** Волна.
- **Dependencies.** G2; G4.2 переиспользует снимки mastery_history (не tour L2).

---

## Рекомендованный порядок (v1 — история; актуальный статус см. «Ревизия v2»)

**P0:** G0 → G1. **P1:** V2 (gate) ‖ G2 → G3. **P2:** G4.  
*(Исполнено: G0–G3 @257–263 ✅; V2′+U0–U4 @264–265 ✅; overlay @269–270 ✅;
R1–R3 @271–272 ✅; W0 @273–274 ✅; **G4.1+G4.2 @275 ✅**; **G4.3 ⬜**.)*

**North star (честный):** человек открывает зал, за 5 секунд понимает «я здесь, дальше
сюда, потому что…», за 2 клика начинает реальное действие (изучить / собрать) — и зал
показывает его прогресс **по квизам** снимком с честной датой.  
**@275:** + этажи окрашены mastery (local/all) и scrubber реплея `mastery_history`.

**Метрики (снимок «до» → «после @275»).**

| Что | Было (до волн) | После @275 |
|---|---|---|
| Действие из зала | невозможно | ✅ `start`/`collect` (G0/G1) |
| Добыча со сцены | нет у зала | ✅ «В конспект» + Obsidian (G1/U2) |
| Финал тура | тупик | ✅ следующий + «Экскурсия дня» (U4) |
| 3D в продукте | download-only | ✅ embedded C1 + Memory Run; export |
| Память в зале | нет | ✅ ✓ quiz + rank overlay; G4.2 replay |
| Визуальный смок | opt-in | ✅ structural + viewport matrix + DOM |
| UI / ценность / внутри | пульт №17 | ✅ U0–U4 + R1–R3 + W0 |
| Подписей в 1-м кадре | ≤8 | ✅ ≤8 |
| G4 | — | ✅ G4.1+G4.2 · ⬜ G4.3 |
| Embed index | pplx≠qwen3 | ✅ reindex qwen3 match |

**Не делать.**
- Не грузить iframe C1 в продукт до зелёного V2.
- Не писать в домен из `export`-HTML; не читать корзину из export.
- Не выдавать mastery_history за «всё, что сделал пользователь» (это только квизы).
- Не считать «сегодня/вчера» от wall-clock в скачанном снимке; дата снимка — render-time
  (`__EXPORTED_AT__`), не дата последнего квиза.
- Не смешивать клик-по-остановке (навигация/фокус) с действием (только кнопки).
- Не заменять номер рангового бейджа галочкой — ✓ оверлеем, ранг остаётся.
- Не ломать строковый контракт 2D-компонента при вводе `{concept_id, action}`.
- Не вводить вторую валюту (XP/монеты/стрики/лидерборды).
- Не менять **доменную** схему payload, не создавать новых хранилищ, не звать LLM.
- Не добавлять Three.js/WebGL, аватары, частицы, сущности/подписи в первый кадр route.

---

## Продолжение линии → Мнемополис (кандидат к разбору №20)

Следующий этап линии — расширение зала до **мира** (ceremonial hub, не замена
Mission Control; двери в разделы; Хранитель; антагонисты из данных; рассвет):
см. `knowledge_graph_3d_world_vision.md` (**v1, 2026-07-18**, re-baseline @275).

**Качество скина (Q1–Q9 @270):** bulk закрыт runtime **W0 @273–274**.
**Residual W0′ + W1** (vision §1.2 / §8): реализованы в hometutor **working tree**
2026-07-18 (verify-pass: 78 tests, 4 viewports, night≠dawn sky). Next: **W2a**
Туман (opt.) и каталог Мнемополис; G4.3 photo ⬜.

Kill switch vision **v3.1**: LLM только с числовым budget (§6.2 vision), cache,
degrade, non-blocking first paint, no domain write; scene-DSL = design spike;
домен и first route-кадр неприкосновенны; G0 `+review` — отдельная волна W2b.

### Что осталось (чеклист владельца)

| # | Тема | Статус |
|---|---|---|
| 1 | G4.3 export «фото дня» + privacy DoD | ⬜ |
| 2 | Push hometutor `main` (ahead origin; @275) | ops |
| 3 | Мнемополис W0′+W1 → commit runtime WT | 🟡 verify-pass, uncommitted |
| 4 | Live Streamlit smoke (опционально) | ops |
