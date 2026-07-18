# Мнемополис: от «3D-зала» к живому миру памяти (vision + аудит качества)

**Статус:** north-star + **runtime implementation status** (разбор №20).  
Материал `hometutor-studio` (`doc/next/`), не runtime-docs `hometutor/docs/`.  
**НЕ backlog-registry** — владелец промоутит вручную; при конфликте с кодом
приоритет у `hometutor` runtime.

**Источники и evidence-база (re-baseline 2026-07-18, doc-sync v3):**
- hometutor HEAD @ `fe63bb3e2` «302» (Мнемополис-каталог + W5b.2 NL + H/G LLM
  controls; локальный G4.3 PNG; tab split graph/Мнемополис);
- исторический baseline G0–G4.2: commits **@257–275** (мост, Memory Run skin,
  rank+✓, R1–R3, W0 Q1–Q9, G4.1/G4.2);
- план-предшественник `knowledge_graph_3d_game_plan.md` (исторический; может
  отставать от runtime — сверять §0 / §11 этого файла);
- structural + viewport gates: `tests/test_knowledge_graph_counters.py`,
  `tests/test_mnemo_keeper.py`, `tests/test_mnemo_scene_dsl.py`,
  `tests/test_sidebar_mnemo_polis.py`.

**Связь с эволюционной разработкой** (`hometutor/docs/evolutionary_development.md`):
каждая реализация — **одна волна = один разрыв**, рабочее состояние после волны.
Толстые пакеты «весь город сразу» запрещены.

**Состояние каталога (doc-sync v3):** product-механики v1 из §11 **реализованы
в runtime**. Открыто: (1) optional live UX residual R1–R3 после U5 HUD;
(2) kill-switch polish антагонистов (§7: ≤1 сцена / TTL / ghost→quiz);
(3) measurable metrics §11.4; (4) cloud/share G4.3 — out of scope без privacy
review. **Не** re-open closed waves «с нуля».

---

## 0. Что уже сделано (не чинить повторно)

| Слой | Статус | Evidence |
|---|---|---|
| G0–G3 мост / start·collect / память / ◆ | ✅ | @257–263 |
| U0–U4 Memory Run skin + V2′ gates | ✅ | @264–265 |
| Overlay rank+✓ live DOM | ✅ | @269–270 |
| Legacy polish R1 chrome · R2 toast · R3 hall lanes | ✅ | @271–272 |
| W0: axis/nav underlay, compass labels, fitRouteCamera margin, link styles, interior head, smooth path, progress track | ✅ bulk | @273–274 |
| W0′ residual R1–R7 (code + structural tests) | ✅ code | WT 2026-07-18; live visual re-check optional after U5 |
| W1 dawn / lanterns | ✅ | `quizRouteProgress` / `drawRouteLantern` |
| W2a fog + calm · W2b `review` | ✅ | template + action whitelist |
| G4.1 floor tint · G4.2 `#replaybar` | ✅ | @275 |
| G4.3 «фото дня» | ✅ **local PNG only** | browser download; **no** server/cloud/share |
| Keeper A–D, H; C1/C2; W4a–d; W5b/W5b.1/W5b.2; W6a–d | ✅ | §11.1–11.3 |
| Tab split «Граф» / «Мнемополис» + deep link | ✅ | `mnemo_nav` + `dashboards_graph` |
| Мнемополис (разбор №20) | vision **synced to runtime** | этот документ + `hometutor/app/ui/*` |

### 0.1 Implementation snapshot — 2026-07-18 (runtime @302)

- Раздел `Knowledge Graph` — два stateful-таба: **«🕸 Граф знаний»** (default) и
  **«🌆 Мнемополис»**; lazy render 2D vs 3D.
- Сайдбар **«🌆 В Мнемополис»** + return CTA → таб Мнемополиса (revisioned key).
- Hall: fog / ghost / rift (conceptual `prereqs`) / quest / voices / chronicle /
  architect banner / local photo / scene presets + host NL panel.
- Runtime evidence (ядро):
  `app/ui/assets/kg_3d_template.html`,
  `app/ui/knowledge_graph_d3.py`,
  `app/ui/dashboards_graph.py`,
  `app/ui/dashboards_graph_keeper.py`,
  `app/ui/dashboards_graph_scene.py`,
  `app/ui/mnemo_nav.py`,
  `app/mnemo_keeper.py`, `app/mnemo_keeper_views.py`,
  `app/mnemo_scene_dsl.py`,
  `docs/user_guide.md`.
- Verification (типичный targeted bundle): counters + mnemo_keeper + scene_dsl +
  sidebar_mnemo + architecture guards; size-budget
  (`long_functions=155`, `peak_file_lines=1942`).

---

## 1. Аудит качества скина

### 1.1 Исторический аудит @270 (закрыт волной W0 @273–274)

На @270 живой прогон фиксировал P0/P1 дефекты **Q1–Q9**. Они были backlog-ом
полировки Memory Run и **в основном закрыты** в `kg_3d_template.html` @273–274:

| ID | Было (@270) | Статус (doc-sync v3 / runtime) |
|---|---|---|
| Q1 | nav перекрывал «СЕГОДНЯ» | ✅ underlay + axisY выше nav |
| Q2 | компас vs floor-ось | ✅ code W0′-R2 (стрелка «КУРС» + floor-легенда); live re-check optional |
| Q3 | mobile crop / fitCamera | ✅ code W0′-R3 + U5 HUD stack; live 390 re-check optional |
| Q4 | desktop маршрут сверху | ✅ code W0′-R1 fitRouteCamera + HUD insets; live polish optional |
| Q5 | «Внутрь» vs «Открыть раздел» | ✅ оба `kgx-link-btn` |
| Q6 | interior head/фон | ✅ sticky opaque head |
| Q7 | dev-footer hint | ✅ W0′-R4: `#hint` clipped / diagnostics, не learner surface |
| Q8 | зигзаг хвоста 4→5→6 | ✅ presentation-only smooth path |
| Q9 | ring 0/6 / chip copy | ✅ W0′-R5/R6 learner chips + track contrast (code) |

**Не переоткрывать** закрытые пункты как «с нуля».

### 1.2 Residual after U5 HUD — **optional live quality**, not v1 blockers

W0′ + W1 **closed in code** (§11.1). После U5 (floating docks / full-bleed stage)
имеет смысл **живой** visual smoke (1366 / 860 / 390), не re-implement R1–R7:

| ID | Тема | Статус |
|---|---|---|
| R1 | desktop vertical fill / «чернота» | code ✅; optional live tweak post-U5 |
| R2 | dual nav legends | code ✅ (arrow compass + floor labels) |
| R3 | mobile callout ∩ chrome | code ✅ + U5 stack; optional live gate |
| R4 | `#hint` learner noise | ✅ clipped diagnostics |
| R5 | chip copy | ✅ learner RU chips |
| R6 | ring @0% | ✅ track contrast |
| R7 | export CTA hierarchy | ✅ product-only copy |

#### Owner decisions (зафиксировано)

- **Onboarding:** first embedded open / localStorage-seen; host may force; см.
  `docs/user_guide.md` (кнопка «Правила»).
- **Тихие рёбра** (`type` vs `relation_type`): optional P2 diagnostics warn —
  **не** v1 blocker.

**Механики v1 (каталог §11) закрыты в runtime.** «Мировой класс» = optional live
polish + metrics §11.4, не re-open waves.

---

## 2. Название: «3D-зал» мир перерос

Кандидаты:

| Название | За | Против |
|---|---|---|
| **Мнемополис** (рекомендую) | город памяти; вмещает районы, линии курсов, этажи, туман, рассвет; уникальное слово — presence в UI и разборах; рус./лат. написание живут оба | нужно один раз объяснить (одной строкой в onboarding) |
| Атлас памяти | понятен сразу | «атлас» — плоская карта, теряется объём и жизнь |
| Город знаний | понятен сразу | генерик, не присвоить |

Иерархия имён: **Мнемополис** — весь мир (ceremonial / deep surface); **Memory Run** —
ежедневный забег (маршрут дня, уже прижилось); районы — двери в разделы (§4).
«3D-зал» — историческое имя вкладки до rename.

**Onboarding one-liner (обязателен при rename):**  
«Мнемополис — город твоей памяти: всё, что ты видишь, отражает реальные quiz, повторения и конспект.»

---

## 3. Принцип мирового класса: «мир — честная проекция твоей памяти»

Уникальность hometutor — сочетание, которого нет ни у кого из «геймификаторов»:
граф знаний + spaced repetition + quiz-история + RAG + **локальный** LLM.
Отсюда один закон мира:

> **Каждый объект, свет, угроза и «живой» эффект мира — проекция реального сигнала
> данных обучения. В Мнемополисе нет декорации, которая врёт о прогрессе.**

### 3.1 Data-bound атмосфера (обязана кодировать сигнал)

| Образ | Сигнал | Пусто / нет данных |
|---|---|---|
| Туман | `1 - retention` из `decay_vector` | нет тумана |
| Рассвет / небо | `doneConceptIds.length / route.length` (quiz-route coverage; пустой route = 0/N) | ночь (0/N) |
| Фонарь | quiz-событие в `mastery_history` | фонарь погашен |
| ◆ | workbench collected (embedded args) | нет маркера |
| Стройплощадка | **только** при честном freshness-сигнале (отдельный audit; иначе cut) | обычный узел |
| Высота обсерватории | level из `gamification_service` | не рисовать башню-цифру без данных |

### 3.2 Structural depth-cues (разрешены явно)

Архитектурные depth-cues Memory Run / R3 — **не** «выдуманный прогресс»:
перспективный пол, portal arches, lane grid, underglow тропы. Они отвечают за
читаемость зала, **не** за mastery/XP. Kill switch v3 запрещает *бессмысленный
шум* (частицы, bokeh, случайные звёзды), а не structural hall language.

Правило ревью волны:  
**data-bound** элемент без сигнала → cut;  
**structural** элемент без data claim → ok, если не обещает прогресс.

### 3.3 Offline / local-first

- Мир как render/view работает **полностью офлайн** (export snapshot).
- Хранитель — local-first через provider layer (`LOCAL_STRICT` / `BALANCED`),
  OpenAI-compatible endpoint; **полная деградация без LLM обязательна** (§6).
- UI не ждёт LLM на first paint (§6 budget).

Duolingo рисует сову поверх прогресс-бара; Мнемополис рисует **сам прогресс** как
город. Это и есть решение мирового класса — **если** §3 не нарушен.

---

## 4. Карта районов: двери в разделы (не open-world)

### 4.1 Product framing

Район = **дверь** (1 клик → существующий `view` через `PENDING_CURRENT_VIEW_KEY`)
+ **состояние** (свет/износ по данным) — не новая доменная логика и не brawler-map.

G1 уже доказывает частный переход `start` → «Интерактивный Quiz». Универсальный
district routing = таблица маппинга + preselect keys, не новый роутер.

### 4.2 Полный каталог (long-term map)

| Район (образ) | View продукта | 3D-образ v1 (дверь, не prop-city) | Сигнал данных |
|---|---|---|---|
| **Врата / Вокзал** | Mission Control | portal glyph на входе тропы | day_route, streak |
| **Магистраль дня** | Адаптивный план | неоновая тропа Memory Run (есть) | worth, day_route |
| **Арена испытаний** | Интерактивный Quiz | door + light = recent quiz score | quiz_results |
| **Оранжерея памяти** | Flashcards / SR | door + wilt tint = low retention | SR due, decay |
| **Кузница конспекта** | Живой конспект | door + ◆ count | workbench |
| **Архив-башня** | Темы / Поиск / Объяснить файл | door group (3 view) | lessons / floors |
| **Обсерватория** | Прогресс / Метрики | door + level tint | gamification_service |
| **Маяк Тьютора** | Чат с тьютором / Быстрый ответ | door + beam | tutor / ask |
| **Линии курсов** | Курс / Course Cockpit | edge highlight active course | active_course |
| **Летопись** | История + G4.2 replay | door; scrubber уже в зале | mastery_history |

### 4.3 MVP районов (первая реализация — не весь каталог)

**Только 4 двери** в `local` / `all` (не в first route-кадре):

1. Арена → Quiz  
2. Оранжерея → Flashcards  
3. Магистраль → Адаптивный план  
4. Кузница → Живой конспект  

Остальные — каталог после MVP. Районы = **door chips / portal glyphs**, не
отдельные 3D-кварталы с props.

### 4.4 Правила

- районы **не** в первом route-кадре (ориентация №17 неприкосновенна);
- нет данных — нет «фейкового» состояния двери (dim + честный empty);
- у каждой MVP-двери — строка в action→view→preselect table (§5);
- обратный портал — §5.

---

## 5. Навигация: Mission Control остаётся home; мир — ceremonial hub

### 5.1 Owner decision (зафиксировано vision-рекомендацией)

| Роль | Поверхность |
|---|---|
| **Home / daily cockpit** | Mission Control (без изменений статуса) |
| **Ceremonial hub / memory surface** | Мнемополис (Knowledge Graph → таб «🌆 Мнемополис») |
| **Deep link** | сайдбар «🌆 В Мнемополис» + CTA «Вернуться в мир» после учебных действий |

**Не делать в v1:** подмена Mission Control миром, авто-redirect на 3D при старте
сессии, второй «главный» hub с дублирующими daily widgets.

**Реализованный UI-контракт:** обычный вход в `Knowledge Graph` открывает таб
«🕸 Граф знаний»; ceremonial deep link открывает «🌆 Мнемополис». Оба режима
остаются внутри одного раздела и переключаются явными табами.

### 5.2 Петля «выйти → сделать → вернуться»

1. **Глобальная кнопка «🌆 В Мнемополис»** в сайдбаре →
   `PENDING_CURRENT_VIEW_KEY` → Knowledge Graph (3D-вкладка). Одна строка
   паттерна, уже проверенного в `adaptive_plan_card.py` / `dashboards_graph.py`.
2. **Возврат с трофеем (честные каналы, без unified fake-event):**
   - quiz → ✓ / фонарь / рассвет через `mastery_history`;
   - SR/flashcards → туман через `decay_vector`;
   - collect → ◆ через workbench view-model.  
   UI recipe: один toast-шаблон «Мир обновился: {каналы}» (например «✓ и небо»
   / «туман редел» / «◆ в кузнице») — **без** обещания единого event bus.
3. **Контекст остановки:** реальные keys
   `kg_selected_concept` / `kg_action_concept` /
   `interactive_quiz_focus_concept`. Общего `selected_concept_id` нет —
   тонкий session focus helper (UI-state only) допустим как отдельная микроволна,
   не как «новая доменная схема».

### 5.3 Таблица district / action routing (обязательна до кода дверей)

| Источник | action / door | View | Preselect keys (best-available) |
|---|---|---|---|
| CTA «Начать» | `start` (G0/G1) | Интерактивный Quiz | `interactive_quiz_focus_concept`, `kg_action_concept` |
| «Развеять туман» / review | **`review`** (новый whitelist) | Flashcards | preselect contract W2b: `flashcards_focus_concept`, `flashcards_queue=due`, `kg_return=mnemo` |
| collect | `collect` | (остаёмся / toast) workbench | collected args refresh |
| Дверь Арена | nav only | Quiz | concept focus if any |
| Дверь Оранжерея | nav only | Flashcards | due/concept if any |
| Дверь Магистраль | nav only | Адаптивный план | — |
| Дверь Кузница | nav only | Живой конспект | — |
| Сайдбар | nav only | Knowledge Graph | restore last concept if any |

Расширение G0 whitelist `start|collect` → `+ review` — **отдельная contract-волна
W2b**, не «мелочь внутри тумана».

---

## 6. ИИ-агент «Хранитель Мнемо»

### 6.1 Жёсткий технический контракт (все сценарии)

- только provider layer (`app/provider.py`), профили `LOCAL_STRICT` / `BALANCED`;
- LLM пишет **только текст / scene-commands**, никогда — в домен (mastery, SR,
  workbench, gamification);
- промпты — только `app/prompts/` (не роутеры/UI);
- кэш обязателен; ключ минимум
  `(provider_id, model_id, prompt_version, scenario, snapshot_date|day, locale,
  route_fingerprint|concept_set_hash)`;
  для multi-concept (B) — hash набора угроз, не один `concept_id`;
- **first paint никогда не ждёт LLM** (skeleton / static degrade → async fill);
- circuit-breaker провайдера + session budget (ниже);
- обязательная деградация: мир полностью функционален при LLM down.

### 6.2 LLM budget appendix (kill switch v3.1 — числовой)

| Параметр | Значение v1 | Примечание |
|---|---|---|
| Max LLM calls / UI-session | **≤ 4** | сверх → только static degrade |
| Max input tokens / call | **≤ 1 600** | только выбранные node labels / короткие snippets, не raw corpus |
| Max output tokens / call | **≤ 400** | A: ≤6×2 предл.; B: короткий список |
| Max total tokens / UI-session | **≤ 8 000 input + 1 600 output** | counters обязательны; сверх → static degrade |
| Wall timeout / call | **≤ 8 s** (local) / **≤ 5 s** (cloud path) | timeout = degrade, не spinner-forever |
| Cache TTL | до смены `snapshot_date` или day_route fingerprint | повторный open зала = 0 calls |
| Parallelism | 1 in-flight | без очереди «догоняющих» narrations |
| Domain write | **hard fail** | contract-test: mock LLM cannot mutate user-state |
| Cloud path privacy | explicit provider consent/settings | BALANCED/cloud path off by default for private notes |
| Fail-closed copy | «Хранитель молчит — данные на месте» | без пустых «магических» карточек |

Ослабление «LLM = стоп» (v1/v2) → «LLM = opt-in narrative layer» (v3.1) **только**
при соблюдении этой таблицы. Нарушение budget = stop-сигнал волны.

### 6.3 Сценарии

#### A. Экскурсовод (нарративный Memory Run) — first LLM product slice
Вход: day_route + worth_reason + mastery + названия.  
Выход: до 6 связок по 1–2 предложения. Кэш на день/route fingerprint.  
Деградация: текущие `worth_reason` в карточке (уже есть).

#### B. Хранитель памяти (сводка угроз)
Угрозы **считаются детерминированно** (`decay_vector`, SR due); LLM — только
формулировка.  
«Развеять» → action `review` (W2b), не старый `start`→Quiz.  
Деградация: список угроз без прозы.

#### C. Собеседник в интерьере — **phased · done v1**
- **C1 ✅:** «💬 Спросить» → handoff в «Чат с тьютором»
  (`build_tutor_prompt_for_concept` + `tutor_pending_prompt`).
- **C2 ✅:** «📜 Кратко» — inline read-only graph brief; stay in hall; no LLM.

#### D. Квестмейстер — **done**
Одна строка цели утра. Degrade «N из M»; optional LLM (host buttons). Без валюты.

#### E. Архитектор достройки — **done v1 (banner only)**
Стройка (`#architectbox`) только при honest publish status (tone ≠ success).  
LLM-советы достройки — **не** shipped (high cost of being wrong); cut v1.

#### F. NL-управление миром (scene-DSL) — **done spike + apply**
Read-only schema (`filter/focus/scene_mode/overlay/route_override`), **не** G0.  
Runtime: `app/mnemo_scene_dsl.py` (validate + presentation + deterministic NL);
hall presets; host panel «🎛 Сцена».  
`route_override` = highlight only; **domain `day_route` не меняется**.  
LLM free-form → DSL: **не** shipped (security). Cloud/share photo: out of scope.

#### G. Летописец — **done**
Короткий текст над G4.2 (`mastery_history` quiz-only) + optional LLM.  
G4.3: **локальный PNG** (browser download); cloud/share = privacy out of scope.

#### H. Голоса антагонистов — **done**
Static bank + optional LLM (host buttons). Тон: уважительный, не стыдящий.

### 6.4 Порядок LLM / narrative волн (эволюционно) — status

| Волна | Содержание | Status |
|---|---|---|
| W3a | infra budget/cache/degrade | ✅ @279 |
| W3b | guide surface | ✅ @280 |
| W3c | threats panel | ✅ WT |
| W3d / D | quest «N из M» | ✅ |
| C1 / C2 | ask handoff / brief | ✅ |
| H voices | static + optional LLM | ✅ |
| W6c G chronicle | летопись | ✅ |
| W6a ghost | ✓-double | ✅ |
| W5b / W5b.1 / W5b.2 | DSL validate + presets + NL | ✅ |
| W6b / W6d | rift prereqs / architect banner | ✅ |
| G4.3 | local PNG only | ✅ (no cloud) |

---

## 7. Антагонисты: честные опасности мира

Закон §3: **антагонист = визуализация реального врага обучения**, не random mob.
Ровно три (больше — шум).

### Туман Забвения (враг №1 — кривая забывания)
- **Данные:** `decay_vector` retention 0..1; сила = `1 - retention`.
- **Образ:** дымка + *опционально* partial glyphs на canvas
  («Guardrails» → «Gu…rd…s»). **Полное имя всегда** в side card / interior
  (a11y; anti-shame).
- **Опасность:** «окутан» = invitation, не hide content forever.
- **Развеять:** 2–3 SR-карточки → action **`review`** (W2b). Педагогически =
  retrieval practice.
- **Не блокирует:** CTA «войти сквозь туман» / «Начать» всегда доступны.
  Contract-test: fog never disables primary actions.

### Призрак Уверенности (враг №2 — иллюзия знания) — **visual done**
- **Данные:** quiz-seen / high mastery + низкий retention (fog signal).
- **Образ:** полупрозрачный ✓-двойник; `prefers-reduced-motion` → static.
- **Развеять (product path):** ▶ Quiz / 💬 Спросить / 🔁 (как общие CTA).  
  Dedicated «1 контрольный вопрос только из Призрака» — **optional polish**,
  не v1 blocker (общий quiz pipeline уже доступен).

### Разлом (враг №3 — незакрытые пререквизиты) — **done via conceptual prereqs**
- **Не** lesson-floor `precedes` edges (они = этажи/порядок уроков, не audit-ok
  как conceptual prerequisites).
- **Данные v1:** `node.prereqs` из graph payload (conceptual). Weak =
  missing node или not learned / mastery < 80%.
- **Образ:** трещина под stop (local/all only); chip «разлом · N опоры».
- **Non-block:** CTA всегда доступны; calm hides.
- **Не re-open** «Разлом на precedes» без отдельного data-audit go.

### Правила дозировки (kill switch ориентации)

| Правило | v1 status |
|---|---|
| first **route**-кадр: без полных антагонистов | ✅ fog/ghost/rift gated |
| полные образы — local/all + interior | ✅ |
| `prefers-reduced-motion` → static | ✅ partial |
| **«Спокойный мир»** выключает антагонистов | ✅ |
| copy: no shame («ты забыл / слабый / провал») | ✅ review |
| одновременно ≤1 «сценка» угрозы | ⬜ optional polish |
| угроза без действия ≤2 мин → hide | ⬜ optional polish |

### Нарезка волн антагонистов
- **W2a ✅** Туман + calm; **W2b ✅** `review`; **W6a ✅** Призрак visual;
  **W6b ✅** Разлом via conceptual prereqs.

---

## 8. Игровые элементы (витрина первой валюты, не вторая)

XP, уровни, daily/quiz-стрики и бейджи **уже есть**
(`app/gamification_service.py`). Мир не дублирует и не вводит вторую валюту —
он **материализует** первую:

- **Рассвет (hero):** небо = `doneConceptIds.length/route.length`
  (quiz-route coverage). 0/N ночь → N/N золото.
  Ноль новых данных, максимум эмоции. Экран «N из N» = награда сам по себе.
- **Фонари:** stop с quiz-событием → фонарь в рамках снимка; след труда на тропе.
- **Отстроенный квартал (после MVP дверей):** lesson concepts ≥80% mastery →
  portal glyph door «загорается». Без таймеров и монет.
- **Стрик = непрерывность света:** `daily_streak` подсвечивает магистраль.
  Пропуск → свет **остывает** (dim), **не** «теряется прогресс».
  ✓ / ◆ / mastery / XP **не откатываются**. Copy: «свет затих», не «ты потерял».
- **Обсерватория:** level title + badge vitrines из gamification_service.
- **Реплей:** G4.2 уже; G4.3 photo — отдельно + privacy DoD.

**Запрещено:** монеты, магазин, лидерборды, «жизни», потеря прогресса,
punish-mechanics, второй XP-счётчик в 3D payload.

---

## 9. 3D-образы режимов

| Режим / оверлей | Образ | Реализация (canvas 2D) |
|---|---|---|
| Маршрут | **Тропа рассвета** — чистая тропа, небо по quiz-прогрессу | gradient от `doneConceptIds.length/route.length` |
| Созвездие (`local`) | **Квартал под фонарём** — конус света + door chips MVP | radial light + dim outside |
| Вся карта (`all`) | **Обзор** — floors + course edges | G4.1 tint + course highlight |
| След памяти | **Аврора** — лента previous snapshot | `memoryOverlay` raised/blurred |
| Дозор (overlay) | **Туман** — forgetting layer | overlay on local/all; quiet markers on route |
| Стройка (node state) | **Леса** | only if freshness signal audited |
| Хроника | **G4.2 scrubber** + optional dawn replay | уже есть bar; text/photo later |

Без WebGL. Новых nav-режимов сверх `route|local|all` + overlays — нет.

---

## 10. Ревизия kill switch (v3.1)

| Правило | v1/v2 | v3.1 (этот документ) |
|---|---|---|
| Доменная схема payload | заморожена | **заморожена** |
| Новые хранилища | стоп | **стоп** |
| Вторая валюта | стоп | **стоп** (витрина первой) |
| Первый route-кадр | ≤8 подписей, без лишних сущностей | **неприкосновенен**; антагонисты/районы не в нём; contract-test на UI-волнах |
| LLM | стоп | **разрешены** только по §6.1–6.2 (budget table, cache, degrade, no domain write, non-blocking first paint) |
| Декор | запрет шума | запрет **бессмысленного** шума; **structural** hall cues разрешены (§3.2); data-bound атмосфера обязана кодировать сигнал (§3.1) |
| Three.js/WebGL | стоп | стоп, пока canvas 2D достаточен |
| G0 action whitelist | `start\|collect` | расширение только отдельной волной + tests (`review` = W2b) |
| scene-DSL | — | **shipped** validate + presets + deterministic NL (§6F); no LLM-NL |
| Home surface | — | Mission Control = home; Мнемополис = ceremonial hub (§5.1) |

---

## 11. Волны (эволюционная нарезка)

Каждая волна: один разрыв, минимальный write-set, targeted tests, V2′ gate на
UI-волнах, живой прогон running-артефакта. Если следующая не случится — продукт
остаётся лучше, чем до волны.

Исключение W0′: это не новая продуктовая механика, а один визуальный residual-bundle
из одного live-аудита Memory Run; он допустим только пока остаётся в пределах
одного шаблона, doc-sync и viewport-gate без схем, stores и новых действий.

### 11.1 Near-term — **shipped**

| Волна | Разрыв | Содержание | P | Effort | Write-set (ориентир) | Tests / DoD |
|---|---|---|---|---|---|---|
| **W0′** Residual polish | W0′-R1…R7 §1.2 | `fitRouteCamera` vertical fill; одна легенда compass/axis; mobile overlap; hide `#hint`; learner chips; ring contrast; export CTA copy | P0 | ✅ WT 2026-07-18 | `kg_3d_template.html`, `docs/user_guide.md`, counters tests | 78 tests; live 4 viewports; R1–R7 verify-pass |
| **W1** Рассвет и фонари | нет «живого» quiz-неба | sky gradient + lanterns from quiz-route coverage (§8) | P0 | ✅ WT 2026-07-18 | `kg_3d_template.html` (+ tests) | night mean_sky≪dawn; reduced-motion solid lantern; route clean |
| **W2a** Туман visual | forgetting invisible | fog from `1-retention` + «Спокойный мир» toggle; non-block CTAs; full name in panel | P1 | ✅ WT 2026-07-18 | `kg_3d_template.html`, counters, user_guide | quiet markers on route; full mist local/all; calm sessionStorage; chip «туман · можно войти» |

### 11.2 Core narrative / actions — **shipped**

| Волна | Разрыв | Содержание | P | Effort | Notes |
|---|---|---|---|---|---|
| **W2b** action `review` | нет двери в Flashcards из зала | whitelist + Python handler + preselect; CTA «Развеять»/«Повторить» | P1 | ✅ WT 2026-07-18 | `start|collect|review`; nav → Flashcards; export inert; 80 tests |
| **W3a** Keeper infra | нет безопасного LLM-слоя | cache, budget counters, degrade smoke, `app/prompts/` stubs | P1 | ✅ @279 | `app/mnemo_keeper.py` + prompts; unit tests; no domain writers |
| **W3b** Keeper A | тур без нарратива | экскурсовод в карточке + host buttons offline/LLM | P1 | ✅ @280 | `build_guide_view_model` → hall; first paint offline |
| **W3c** Keeper B | угрозы без сводки | deterministic list + optional prose + panel | P1 | ✅ WT 2026-07-18 | `build_threats_view_model`; 🔁=review |

### 11.3 Catalog W4–W6 / Keeper / G4.3 — **shipped in runtime**

| Волна | Содержание | P | Preconditions |
|---|---|---|---|
| **W4a** Сайдбар + явный таб «Мнемополис» | deep link + stateful/lazy tab split | P2 | ✅ runtime 2026-07-18 | `mnemo_nav.open_mnemo_polis`; revisioned tab key; 2D default / 3D deep link |
| **W4b** Return CTA after quiz | trophy toast recipe quiz-channel | P2 | ✅ WT 2026-07-18 | after interactive/scoped quiz; honest quiz channel copy |
| **W4c** District doors MVP (4) | local/all door chips + routing table | P2 | ✅ WT 2026-07-18 | `door_*` actions; not in route frame |
| **W4d** Return after flashcards / collect | SR/◆ channels | P2 | ✅ WT 2026-07-18 | FC review CTA; collect ◆ toast in-hall |
| **W5a** Keeper C1 tutor handoff | interior «Спросить» → tutor chat | P2 | ✅ WT 2026-07-18 | action `ask` + build_tutor_prompt_for_concept |
| **W5b** design spike scene-DSL | schema/validator | P2 | ✅ WT 2026-07-18 | `app/mnemo_scene_dsl.py` |
| **W5b.1** presentation apply | presets + filter dim | P2 | ✅ WT 2026-07-18 | hall presets; day_route unchanged |
| **W5b.2** NL scene commands | safe parse → validate → apply | P2 | ✅ WT 2026-07-18 / @302 | host panel; no LLM; no eval |
| **W5c** Keeper C2 inline ask | brief in-hall from graph data | P3 | ✅ WT 2026-07-18 | action `brief`; no LLM; stay in hall |
| **W3d** Keeper D quest | one morning-goal line | P2 | ✅ WT 2026-07-18 | degrade «N из M»; optional LLM |
| **W6a** Призрак | antagonist #2 visual | P3 | ✅ WT 2026-07-18 | ghost ✓ when quiz-seen + fog; calm hides |
| **W6b** Разлом | antagonist #3 | P3 | ✅ WT 2026-07-18 | conceptual `node.prereqs` only; non-block |
| **W6c** Летописец text on G4.2 | Keeper G prose | P3 | ✅ WT 2026-07-18 | chronicle + optional LLM |
| **W6d** Стройка / Architect | publish banner | P3 | ✅ WT 2026-07-18 | banner when tone≠success; no LLM write |
| **G4.3** фото дня | local PNG only | P3 | ✅ WT 2026-07-18 | browser download; no server/cloud |
| **H** voices | antagonist lines | P3 | ✅ WT 2026-07-18 / @302 | static bank + host LLM buttons |

### 11.4 Метрики (измеримые) — **observational backlog, not v1 ship blockers**

| Метрика | Как узнать | Цель | Status |
|---|---|---|---|
| Time-to-first-action | client timestamp open → first action | ≤10 s median warm | ⬜ not instrumented |
| Route completion visual contract | 0/N vs N/N screenshots | dawn only at N/N | partial structural tests |
| Return-to-hall | UI counter `hall_returns` | baseline then threshold | ⬜ not wired |
| LLM budget integrity | counters + tests | 0 domain writes; ≤4 calls | ✅ unit tests |
| §3 invariant | review checklist | no data-less progress art | ✅ process |
| Orientation | contract-test route first frame | ≤8 labels; no full antagonists | ✅ partial tests |

Неизмеримое («возврат стал нормой») — qualitative owner observation.

### 11.5 Не делать

- аватар игрока, open-world бродилка, экономика/магазин, punish-механики;
- антагонисты, блокирующие контент или стыдящие;
- LLM-запись в домен; LLM без cache/budget/degrade; LLM на first paint;
- LLM free-form → arbitrary scene-DSL / JS;
- новые nav-режимы сверх `route|local|all` + overlays;
- второй источник правды прогресса; `mastery_history` ≠ «все действия»;
- Мнемополис как замена Mission Control;
- Разлом на lesson `precedes` без data-audit go;
- G4.3 cloud/share без privacy review;
- толстые «волны-пакеты» monoblock — только нарезка §11.1–11.3.

---

## 12. Чеклист промоута волны (из evolutionary_development.md)

Перед стартом реализации:
1. Сверить якоря (файл:строка, «кнопки нет», payload fields) с текущим HEAD.
2. Один разрыв; минимальный write-set; targeted tests названы заранее.
3. UI-формулировки честные (провод vs поверхность названы).
4. Нет LLM/feature-flag/new store, если хватает deterministic state.
5. Stop-сигнал: если всплыл новый пайплайн/схема вне замысла — пересобрать волну.

После:
1. Targeted tests green; `ruff` на изменённых py.
2. UI-волна: V2′ structural + viewport + живой прогон.
3. Явно: что закрыто, что осталось следующей волне.

---

## 13. История ревизий vision

| Rev | Дата | Суть |
|---|---|---|
| v0 | 2026-07-17 | Первый draft; evidence @270; волны W0–W6 monoblock |
| **v1** | **2026-07-18** | Deep review: re-baseline @275; W0′ residual; G4.1/G4.2; MC = home; districts; LLM budget; scene-DSL spike; evolutionary waves |
| **v2** | **2026-07-18** | Tab split «Граф» / «Мнемополис»; deep link; lazy render |
| **v3** | **2026-07-18** | **Doc-sync to runtime @302:** catalog §11 closed; G4.3 local PNG; Разлом = conceptual prereqs; W5b.1–2 NL; H/G LLM buttons; residual R1–R3 → optional live; metrics §11.4 marked observational; kill-switch polish listed open |

---

## 14. Открыто после doc-sync v3 (не re-open closed waves)

| # | Тема | Критичность | Примечание |
|---|---|---|---|
| 1 | Live visual smoke post-U5 (R1–R3) | UX quality | 1366 / 860 / 390; не code re-do |
| 2 | Ghost → dedicated quiz handoff | optional polish | CTA ▶/💬 уже есть |
| 3 | Threat TTL ≤2 min / ≤1 сцена | optional kill-switch | |
| 4 | Metrics §11.4 instrumentation | observational | |
| 5 | G4.3 cloud/share | privacy go | local PNG already shipped |
| 6 | `game_plan.md` sync | doc-only | may lag this file |
| 7 | Push `hometutor` origin | ops | ahead local commits |

---

**Итог для владельца (v3):** north star (§3) + Memory Run + **каталог механик v1
в runtime** (через ~@302). Vision приведён к коду. Backlog **не** «W0′→W1→W2a» —
это закрыто. Дальше только optional live polish, kill-switch polish, metrics,
privacy-cloud photo, ops push.
