# Мнемополис: от «3D-зала» к живому миру памяти (vision + аудит качества)

**Статус:** кандидат-материал к эволюционному разбору №20 (номер сдвинут 2026-07-18: №19 занят темой обучения) («расширение границ игрового
3D-мира и интеграция разделов приложения»). **НЕ backlog** — владелец промоутит
вручную. Материал `hometutor-studio` (`doc/next/`), не runtime-docs `hometutor/docs/`.

**Источники и evidence-база (re-baseline 2026-07-18):**
- hometutor HEAD @ `ec9a3c250` «275»;
- план-предшественник `knowledge_graph_3d_game_plan.md` (G0–G3 + U0–U4 + V2′ —
  DONE @257–265; rank+✓ @269–270; R1–R3 @271–272; **W0 Q1–Q9 @273–274**;
  **G4.1 floor tint + G4.2 history replay @275**; G4.3 «фото дня» ⬜ privacy DoD);
- исторический audit-snapshot vision v0: @ `3d6fe0a94` «270» (до W0/G4 polish);
- живой прогон production export (Playwright, viewports 1366×768 / 860×768 /
  390×844, фикстура 12 узлов / маршрут 6) + `tests/test_knowledge_graph_counters.py`
  (structural + viewport gates always-on).

**Связь с эволюционной разработкой** (`hometutor/docs/evolutionary_development.md`):
каждая реализация — **одна волна = один разрыв**, рабочее состояние после волны,
без LLM/новой схемы без нужды. Толстые пакеты «весь город сразу» запрещены; ниже
волны нарезаны так, чтобы продукт не ломался, если следующая волна не случится.

**Промоут-политика (после ревью 2026-07-18):** first slice **W0′ + W1**
реализован в hometutor **working tree** (2026-07-18, uncommitted на момент verify;
маркеры `quizRouteProgress` / `drawRouteLantern` / W0′-R1…R7). Далее: **W2a** (opt.)
и каталог (§5 home, §6 LLM, §6F spike, §7 Разлом audit).

---

## 0. Что уже сделано (не чинить повторно)

| Слой | Статус | Evidence |
|---|---|---|
| G0–G3 мост / start·collect / память / ◆ | ✅ | @257–263 |
| U0–U4 Memory Run skin + V2′ gates | ✅ | @264–265 |
| Overlay rank+✓ live DOM | ✅ | @269–270 |
| Legacy polish R1 chrome · R2 toast · R3 hall lanes | ✅ | @271–272 |
| W0: axis/nav underlay, compass labels, fitRouteCamera margin, link styles, interior head, smooth path, progress track | ✅ bulk | @273–274 |
| G4.1 floor tint (local/all) · G4.2 `#replaybar` scrubber | ✅ | @275 |
| G4.3 «фото дня» | ⬜ | privacy DoD из game plan |
| Мнемополис (разбор №20) | vision + runtime implementation | этот документ + `hometutor/app/ui/dashboards_graph.py` |

### 0.1 Implementation snapshot — 2026-07-18

- Раздел `Knowledge Graph` разделён на два явных stateful-таба:
  **«🕸 Граф знаний»** (default) и **«🌆 Мнемополис»**.
- Сайдбарная кнопка **«🌆 В Мнемополис»** и return CTA открывают сразу таб
  Мнемополиса через revisioned widget key; выбор не сбрасывается на следующем
  Streamlit rerun.
- Тяжёлые поверхности рендерятся лениво: D3-компонент создаётся только в табе
  графа, embedded 3D hall — только в табе Мнемополиса. 2D-граф больше не стоит
  над 3D-залом и не требует прокрутки для обнаружения мира.
- Статус карты, действия с концептом, HTML-export и classic agraph находятся в
  табе графа; arrival banner, Keeper controls и Memory Run — в табе Мнемополиса.
- Runtime evidence: `app/ui/mnemo_nav.py`, `app/ui/dashboards_graph.py`,
  `app/ui/dashboards_graph_publish_status.py`,
  `tests/test_sidebar_mnemo_polis.py`.
- Verification: targeted UI/architecture bundle — **108 passed**; Ruff — green;
  size-budget guard — green (`long_functions=155`, `peak_file_lines=1942`).

---

## 1. Аудит качества скина

### 1.1 Исторический аудит @270 (закрыт волной W0 @273–274)

На @270 живой прогон фиксировал P0/P1 дефекты **Q1–Q9**. Они были backlog-ом
полировки Memory Run и **в основном закрыты** в `kg_3d_template.html` @273–274:

| ID | Было (@270) | Статус @275 |
|---|---|---|
| Q1 | nav перекрывал «СЕГОДНЯ» | ✅ underlay + axisY выше nav |
| Q2 | компас vs floor-ось — две системы | ⚠️ partial: оси переименованы (КУРС/ДАЛ/ВХОД/СЕГ), но **двойная легенда остаётся** |
| Q3 | mobile crop / fitCamera | ⚠️ partial: margin clamp есть; 390×844 всё ещё плотный chrome (callout∩compass∩nav) |
| Q4 | desktop маршрут в верхней половине | ⚠️ residual: нижняя «чернота» всё ещё выражена |
| Q5 | «Внутрь» vs «Открыть раздел» | ✅ оба `kgx-link-btn` |
| Q6 | interior head/фон | ✅ sticky opaque head |
| Q7 | dev-footer hint | ⚠️ residual: `#hint` «N узлов · режим · export» всё ещё в DOM |
| Q8 | зигзаг хвоста 4→5→6 | ✅ presentation-only smooth path |
| Q9 | ring 0/6 / stale status | ⚠️ track есть; contrast ring@0% и learner-copy чипов — residual |

**Не переоткрывать** закрытые пункты как «с нуля». Дальше — только residual (§1.2).

### 1.2 Residual @275 (живой прогон re-baseline) — scope волны **W0′**

Memory Run узнаваем: topbar 64px, side 314px desktop, CTA ≥40px, route-first,
export inert, G4.2 replay bar. Ниже — что **ещё** отделяет «хорошо» от «шедевра».

#### P0 — residual композиции

- **W0′-R1 (ex-Q4 residual). Desktop: маршрут всё ещё прижат к верхней половине**;
  нижняя треть сцены — пустая чернота. `fitRouteCamera` улучшен, но vertical
  fill reference-уровня не достигнут. Fix: донастроить pitch/centerY/targetH
  + проверка 1366 и 1920 в visual smoke.
- **W0′-R2 (ex-Q2 residual). Две легенды навигации:** floor «ВХОД / СЕГОДНЯ / ДАЛЬШЕ»
  + компас «КУРС / ДАЛ / ВХОД / СЕГ» (ещё и обрезки «ДАЛ/СЕГ»). Fix: **одна**
  семантика. Вариант A — компас без текстовых осей (только стрелка «курс»);
  вариант B — floor-ось alone, компас = N-E-S-W без дублей смысла.
- **W0′-R3 (ex-Q3 residual). Mobile 390×844:** маршрут в кадре в целом держится, но
  callout активной остановки пересекается с компасом; «СЕГОДНЯ» почти не
  читается между chrome. Fix: callout offset / hide floor-labels on narrow /
  scale compass; gate «нет overlap critical labels» в viewport matrix.

#### P1 — residual polish

- **W0′-R4 (ex-Q7). Dev-hint footer** (`12 узлов · маршрут 6/6 · режим route · export`)
  — убрать из learner surface; перенести в `?`-диалог / `title` / diagnostics.
- **W0′-R5. Chip copy bug:** `due ${n.due}` при boolean даёт «due true»; `novel` —
  developer English. Fix: learner chips (`пора повторить` / `новое`), без raw
  boolean/english keys.
- **W0′-R6. Progress ring @0%** — трек есть, но визуально почти «пустой круг»;
  усилить track contrast (WCAG-ish на тёмном фоне).
- **W0′-R7. Export CTA hierarchy** — disabled primary/secondary выглядят одинаково
  «мёртвыми»; усилить copy «доступно в продукте» без шума.

#### Примечания (owner decisions, не дефекты W0′)

- **Onboarding:** `(SHOW_ONBOARDING || isEmbedded) && !sessionStorage.seen` —
  embedded всегда предлагает onboarding на первом tab-open, даже если host
  передал `show_onboarding=false`. **Решение (зафиксировать):** оставить
  «раз на browser-tab для embedded» как product default; host-flag только
  *форсирует* повтор. Документировать в `docs/user_guide.md` при промоуте W0′.
- **Тихие рёбра:** payload с `{type:…}` вместо `{relation_type:…}` даёт пустое
  «Созвездие» без warn. Предложение (P2): `console.warn` + счётчик «рёбер
  отброшено» в `?`-диагностике — не блокирует W0′.

**Прорыв уровня качества = W0′ (W0′-R1…R7) + W1 «Рассвет» (§8).**
Не называть «мировым классом» до live-gate после W0′+W1. Полировка без новой
механики + небо/фонари из quiz-данных — первый наблюдаемый скачок.

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

#### C. Собеседник в интерьере — **phased**
- **C1 (сначала):** кнопка «Спросить об этом» = handoff в «Чат с тьютором»
  через существующие `build_tutor_prompt_for_concept` + `tutor_pending_prompt`
  (деградация = основной путь v1).
- **C2 (позже):** inline read-only concept retrieval — **отдельная** волна,
  только если C1 доказал спрос. Не совмещать с scene-DSL.

#### D. Квестмейстер
Одна строка цели утра + существующие бейджи. Без новой валюты.  
Деградация: «N из M».

#### E. Архитектор достройки — **P3 / high-trust**
Стройплощадка только при честном freshness-сигнале (иначе cut).  
Предложения LLM — текст; человек подтверждает в существующих инструментах.  
Высокий cost of being wrong → не near-term.

#### F. NL-управление миром (scene-DSL) — **design spike, не implementation wave**
Командная строка («покажи слабое», «фильтр агенты») потребует **новой read-only
schema** (`filter/focus/scene_mode/overlay/route_override`), **не** G0 envelope
(`start|collect`).  

**До кода обязательно:**
- JSON schema + version;
- allowlist команд и node ids;
- reject unknown keys;
- `route_override` = presentation only (доменный `day_route` не менять; UI
  copy не говорит «маршрут дня перестроен»);
- security/tests: prompt injection → no write, no arbitrary JS;
- отдельный owner go/no-go.

Деградация v1: **нет строки**, только кнопки. Spike может завершиться «не делаем».

#### G. Летописец — поверх **уже существующего G4.2**
G4.1+G4.2 @275 уже дают floor tint + history scrubber.  
G = короткий текст Хранителя над quiz-only `mastery_history` (честное сужение) +
опционально будущий G4.3 photo (privacy DoD game plan).  
Деградация: replay bar без прозы. **Не** описывать G4 как «ещё не реализован».

#### H. Голоса антагонистов
1 строка / угроза, пачка на день, кэш. Тон: уважительный юмор, **никогда не
стыдящий**. Деградация: static bank в шаблоне / `app/prompts/`.

### 6.4 Порядок LLM-волн (эволюционно)

| Волна | Содержание |
|---|---|
| W3a | ✅ @279 infra |
| W3b | ✅ @280 guide surface |
| W3c | ✅ WT threats panel + host buttons |
| W3d / D | ✅ WT 2026-07-18 quest line «N из M» + optional LLM |
| H voices | ✅ WT 2026-07-18 static bank + optional path |
| W6c G chronicle | ✅ WT 2026-07-18 летопись over mastery_history |
| W6a ghost | ✅ WT 2026-07-18 ✓-double when learned+fog |
| W5b scene-DSL | ✅ spike schema/validator only (no UI) |
| W6b/W6d/G4.3 | ✅ WT 2026-07-18 (W6b conceptual prereqs; W6d publish banner; G4.3 privacy stub) |

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

### Призрак Уверенности (враг №2 — иллюзия знания)
- **Данные:** давний ✓ + низкий retention.
- **Образ:** полупрозрачный ✓-двойник; при `prefers-reduced-motion` — статичный.
- **Развеять:** 1 контрольный вопрос через quiz pipeline (домен пишет quiz-event
  как обычно; LLM не участвует в записи).

### Разлом (враг №3 — незакрытые пререквизиты) — **blocked on data audit**
- **Кандидат данных:** `precedes` edges. Сейчас edges в первую очередь задают
  lesson-floor order; **не доказано**, что это conceptual prerequisites.
- **До UI Разлома:** data audit — какие edges = учебный prereq; иначе **cut**.
- **Если audit ok:** трещина перед stop; «перепрыгнуть» всегда можно; мост =
  prereq practice. Non-block обязателен.

### Правила дозировки (kill switch ориентации)
- first **route**-кадр: антагонистов нет (макс. тихие markers на stops);
  полные образы — local/all + interior;
- одновременно ≤1 «сценка» угрозы;
- `prefers-reduced-motion` → static;
- тумблер **«Спокойный мир»** выключает антагонистов целиком;
- угроза без действия ≤2 минут → не показывать;
- copy review: запрещены формулировки «ты забыл / ты слабый / провал».

### Нарезка волн антагонистов
- **W2a:** только Туман visual + calm-world toggle (read-only, без нового action);
- **W2b:** action `review` + preselect Flashcards (провод двери «развеять»);
- **W6a:** Призрак (после W2a proven);
- **W6b:** Разлом — только после data audit go.

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
| scene-DSL | — | **не в implementation backlog** без design spike go (§6F) |
| Home surface | — | Mission Control = home; Мнемополис = ceremonial hub (§5.1) |

---

## 11. Волны (эволюционная нарезка)

Каждая волна: один разрыв, минимальный write-set, targeted tests, V2′ gate на
UI-волнах, живой прогон running-артефакта. Если следующая не случится — продукт
остаётся лучше, чем до волны.

Исключение W0′: это не новая продуктовая механика, а один визуальный residual-bundle
из одного live-аудита Memory Run; он допустим только пока остаётся в пределах
одного шаблона, doc-sync и viewport-gate без схем, stores и новых действий.

### 11.1 Near-term (готовы к промоуту после doc-sync / owner ack)

| Волна | Разрыв | Содержание | P | Effort | Write-set (ориентир) | Tests / DoD |
|---|---|---|---|---|---|---|
| **W0′** Residual polish | W0′-R1…R7 §1.2 | `fitRouteCamera` vertical fill; одна легенда compass/axis; mobile overlap; hide `#hint`; learner chips; ring contrast; export CTA copy | P0 | ✅ WT 2026-07-18 | `kg_3d_template.html`, `docs/user_guide.md`, counters tests | 78 tests; live 4 viewports; R1–R7 verify-pass |
| **W1** Рассвет и фонари | нет «живого» quiz-неба | sky gradient + lanterns from quiz-route coverage (§8) | P0 | ✅ WT 2026-07-18 | `kg_3d_template.html` (+ tests) | night mean_sky≪dawn; reduced-motion solid lantern; route clean |
| **W2a** Туман visual | forgetting invisible | fog from `1-retention` + «Спокойный мир» toggle; non-block CTAs; full name in panel | P1 | ✅ WT 2026-07-18 | `kg_3d_template.html`, counters, user_guide | quiet markers on route; full mist local/all; calm sessionStorage; chip «туман · можно войти» |

### 11.2 Next (после W0′+W1 live)

| Волна | Разрыв | Содержание | P | Effort | Notes |
|---|---|---|---|---|---|
| **W2b** action `review` | нет двери в Flashcards из зала | whitelist + Python handler + preselect; CTA «Развеять»/«Повторить» | P1 | ✅ WT 2026-07-18 | `start|collect|review`; nav → Flashcards; export inert; 80 tests |
| **W3a** Keeper infra | нет безопасного LLM-слоя | cache, budget counters, degrade smoke, `app/prompts/` stubs | P1 | ✅ @279 | `app/mnemo_keeper.py` + prompts; unit tests; no domain writers |
| **W3b** Keeper A | тур без нарратива | экскурсовод в карточке + host buttons offline/LLM | P1 | ✅ @280 | `build_guide_view_model` → hall; first paint offline |
| **W3c** Keeper B | угрозы без сводки | deterministic list + optional prose + panel | P1 | ✅ WT 2026-07-18 | `build_threats_view_model`; 🔁=review |

### 11.3 Later catalog (не один «W4/W5/W6 bag»)

| Волна | Содержание | P | Preconditions |
|---|---|---|---|
| **W4a** Сайдбар + явный таб «Мнемополис» | deep link + stateful/lazy tab split | P2 | ✅ runtime 2026-07-18 | `mnemo_nav.open_mnemo_polis`; revisioned tab key; 2D default / 3D deep link |
| **W4b** Return CTA after quiz | trophy toast recipe quiz-channel | P2 | ✅ WT 2026-07-18 | after interactive/scoped quiz; honest quiz channel copy |
| **W4c** District doors MVP (4) | local/all door chips + routing table | P2 | ✅ WT 2026-07-18 | `door_*` actions; not in route frame |
| **W4d** Return after flashcards / collect | SR/◆ channels | P2 | ✅ WT 2026-07-18 | FC review CTA; collect ◆ toast in-hall |
| **W4d** Return after flashcards / collect | SR/◆ channels | P2 | W2a/W2b as needed |
| **W5a** Keeper C1 tutor handoff | interior «Спросить» → tutor chat | P2 | ✅ WT 2026-07-18 | action `ask` + build_tutor_prompt_for_concept |
| **W5b** design spike scene-DSL | schema/validator only | P2 | ✅ WT 2026-07-18 | `app/mnemo_scene_dsl.py`; no UI wire |
| **W5c** Keeper C2 inline ask | brief in-hall from graph data | P3 | ✅ WT 2026-07-18 | action `brief`; no LLM; stay in hall |
| **W3d** Keeper D quest | one morning-goal line | P2 | ✅ WT 2026-07-18 | degrade «N из M»; optional LLM; no currency |
| **W6a** Призрак | antagonist #2 | P3 | ✅ WT 2026-07-18 | ghost ✓ when quiz-seen + fog; calm hides |
| **W6b** Разлом | antagonist #3 | P3 | ✅ WT 2026-07-18 | conceptual `node.prereqs` only (not lesson edges); non-block |
| **W6c** Летописец text on G4.2 | Keeper G prose | P3 | ✅ WT 2026-07-18 | chronicle over mastery_history |
| **W6d** Стройка / Architect E | freshness + optional LLM advice | P3 | ✅ WT 2026-07-18 | banner only when publish tone≠success; no LLM write |
| **G4.3** фото дня | privacy DoD game plan | P3 | ✅ stub WT 2026-07-18 | disabled 📷; no capture/upload until privacy review |
| **H** voices | antagonist lines | P3 | ✅ WT 2026-07-18 | static bank; optional LLM path unused on first paint |

### 11.4 Метрики (измеримые)

| Метрика | Как узнать | Цель |
|---|---|---|
| Time-to-first-action | client timestamp open → first `start`/`collect`/`review` | ≤10 s median на warm load |
| Route completion visual contract | fixture 0/N vs N/N screenshots after W1 | binary diff: dawn visible only at N/N; no text/CTA overlap |
| Return-to-hall | local counter `hall_returns` (UI-only) after W4b | baseline first; success threshold set only after ≥50 sessions |
| LLM budget integrity | counters + tests | 0 domain writes; ≤4 calls/session; token caps §6.2 |
| §3 invariant | review checklist per wave | no data-less «progress claim» art |
| Orientation | contract-test route first frame | ≤8 labels; no antagonist entities |

Неизмеримое («возврат стал нормой») — не KPI, а qualitative owner observation.

### 11.5 Не делать

- аватар игрока, open-world бродилка, экономика/магазин, punish-механики;
- антагонисты, блокирующие контент или стыдящие;
- LLM-запись в домен; LLM без cache/budget/degrade; LLM на first paint;
- новые nav-режимы сверх `route|local|all` + overlays;
- второй источник правды прогресса; `mastery_history` ≠ «все действия»;
- Мнемополис как замена Mission Control;
- scene-DSL / Разлом / Architect без audit·spike go;
- толстые «волны-пакеты» (старые W4–W6 monoblocks) — только нарезка §11.1–11.3.

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
| **v1** | **2026-07-18** | Deep review applied: re-baseline @275; W0 closed + W0′ residual; G4.1/G4.2 fact; Mission Control = home; districts MVP 4 doors; LLM budget table; scene-DSL → spike; waves evolutionary split; §3 structural vs data-bound; Разлом blocked on audit; streak «остывает» |
| **v2** | **2026-07-18** | Runtime progress sync: явные табы «Граф знаний» / «Мнемополис»; 2D default; sidebar/return deep link в 3D; revisioned state; lazy render; architecture guard green |

---

**Итог для владельца:** north star (§3) и Memory Run-база — сильные.  
В backlog **сейчас** — только **W0′ → W1 → (W2a)**. Остальное остаётся каталогом
кандидатов до отдельных go-решений.
