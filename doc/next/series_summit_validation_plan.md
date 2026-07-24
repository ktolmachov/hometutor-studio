# Series Summit Validation Plan — разбор №28 «Строили вглубь — фасад остался прежним»

**Источник:** [`../presentations/evolutionary_analyses/28_summit_retrospective.html`](../presentations/evolutionary_analyses/28_summit_retrospective.html)
**Дата:** 2026-07-24 · hometutor HEAD `05565efe9` «392» → реализация закрыта на `589636dab` «393» + последующие правки того же дня
**Статус:** P0-2 implementation shipped, outcome unvalidated (DoD требует live-подтверждение
на профиле владельца + screenshot до/после — не сделано, см. §P0-2 ниже); P0-1 infra shipped
и replay #26 validated; P0-1 replay №2/№19/№22/№23 остаётся открытым (mechanically-reverified,
не behavioral validated). Артефакты:
[`replay_artifacts_2026-07/replay_2026-07-24.md`](replay_artifacts_2026-07/replay_2026-07-24.md).

North star разбора: **OVR (Outcome Validation Rate)** = разборы со статусом
`validated`/`no-effect`/`regressed` ÷ все разборы.

**Обновлено 2026-07-24 (контр-аудит поймал арифметическую ошибку исходной версии
плана):** original baseline был **1/27 ≈ 3.7%**, target был заявлен «≥6/28 ≈ 21%» — но
волна P0-1 содержит ровно 5 кандидатов (№2, №19, №22, №23, №26), из которых №26 уже
входил в исходный baseline. Даже идеальный исход волны (все 5 → `validated`) даёт
максимум **5/28 ≈ 17.9%**, не 21% — target был недостижим по построению задолго до
реализации. Исправлено: **target = 5/28 ≈ 17.9%** (все пять исходных кандидатов волны
validated); шестой, ранее не заявленный разбор для достижения 21% не добавляется —
это была бы скрытая эскалация объёма P0-1, а не исправление арифметики.

**Текущее фактическое значение (2026-07-24 после первого прогона волны): 1/28 ≈ 3.6%**
(знаменатель вырос на сам №28; числитель не изменился — №26 переподтверждён
`validated`, №2/№19/№22/№23 получили только `mechanically-reverified`, что по
определению не входит в числитель). До target 5/28 остаётся полный поведенческий
replay четырёх пунктов.

Wiring-status: **`wired-existing`** — сама формула OVR полностью посчитываема
(ведомость в README серии + replay-артефакты, готова с P0-1 infra 2026-07-24);
дальнейшего инженерного wiring не требуется. Оставшийся разрыв до target —
**validation gap**, не wiring gap: нужны 4 живых поведенческих прогона, не код.

---

## P0-1 — Волна валидации (погасить 5 векселей)

**Статус 2026-07-24:** infra и первый прогон закрыты; полный поведенческий replay
для 4 из 5 пунктов остаётся открытым (см. итог ниже, детали —
[`replay_artifacts_2026-07/replay_2026-07-24.md`](replay_artifacts_2026-07/replay_2026-07-24.md)).

| Разбор | Что сделано 2026-07-24 | Статус |
|---|---|---|
| №26 | Живой `compute_trusted_route_rate.py`: TLRR 61.1%, бит-в-бит с 2026-07-23; 112 тестов. Тот же тестовый прогон затронул 6 pre-existing файлов зоны №26 (`app/quiz_scoped.py`, `scripts/run_gate_scoped_quiz.py` + тесты), закоммиченных отдельно владельцем как «395»/`ec310c7a0` — не работа этой волны, только протестированы заодно | **`validated`** |
| №2, №19, №22, №23 | Целевые regression-bundles прогнаны (59+54+7+159=279 тестов, все зелёные) | **`mechanically-reverified`**, НЕ `validated` — живого поведенческого прохода не было |
| checkpoint acceptance-rate | Прочитан из уже писавшихся `checkpoint_offered`↔`route_selected(accepted=True)`; `scripts/compute_checkpoint_acceptance_rate.py`. **Контр-аудит нашёл двойной счёт**: первая версия джойнила по `(session_id, decision_id)` set-membership, а `decision_id` не уникален на completion (`app/ui/autopilot.py::step_completed` — «two distinct completions... are still two separate steps»); одно принятие могло ошибочно засчитать несколько checkpoint. Исправлено на FIFO-последовательное сопоставление по порядку событий в append-only tape (1 принятие ⇒ максимум 1 checkpoint); 4 новых теста (повторяющийся decision_id, accept до offer, разные сессии, несвязанная поверхность — последний явно документирует остаточное ограничение, не выдаёт его за решённое) | wired (после fix), live-прогон честно `N/A` (0 `checkpoint_offered` в истории) |
| world time-to-first-action | **Kill switch плана сработал** — план требовал остановиться, если сигнал ещё не пишется; `world_entered`/`world_first_action` не существовали до этой волны. Вместо остановки принято сознательное решение расширить `EVENT_REQUIRED_FIELDS` в `session_tape.py` (новый size-extract модуль `app/ui/dashboards_graph_world_events.py`, вызывается из `dashboards_graph.py`, чтобы не пробить architecture guard №12 peak_file_lines=1958) через уже существующий `session_tape.append_event` pipeline; `scripts/compute_world_time_to_first_action.py` | wired (scope сознательно расширен, зафиксировано здесь явно), live-прогон честно `N/A` (0 `world_entered` в истории) |

**Остаток P0-1 (единственная незакрытая часть):** живой поведенческий replay
№2/№19/№22/№23 — реальный профиль, секундомер/SQL-снимок, не regression-тесты.
OVR не увеличился (1/28 ≈ 3.6%, было 1/27 ≈ 3.7%) именно потому, что mechanical
re-verification намеренно не засчитывается как outcome-валидация.

- **Learning stage:** 10 — прогресс, возврат и достижение цели (метазадача серии).
- **Outcome signal:** OVR серии; для каждого из 5 разборов — явный outcome-статус с артефактом.
- **Cross-cutting pain:** `PAIN-03` (провода без поверхности — сигналы пишутся, статусы не выводятся)
  с элементом `PAIN-02` (правило «shipped ≠ validated» существует в гайде §4.2, но не исполняется циклом).
- **Problem:** 24 структурных ядра отгружены, replay исходной боли после отгрузки выполнен
  только для №26. Все остальные — вечный `shipped-unvalidated`; вопрос «стало ли лучше»
  не имеет ни одного числа в ответ.
- **Evidence:** ведомость §2 разбора №28; `hometutor-studio@5ee934c:doc/presentations/evolutionary_analyses/README.md`
  (таблицы «Wiring-status North star» — `mixed`, «Outcome после реализации» — `mixed`, №1–23 не аудированы);
  №20: observational metrics `time-to-first-action`, `hall_returns` — «не wired» (строка разбора №20).
- **Difference from №N:** №8 делал видимыми фичи, №11 сверял витрину с продуктом; здесь впервые
  проверяются **результаты серии** повторным замером исходных болей.
- **Proposed:**
  1. Replay исходного боль-якоря на живом продукте для пяти разборов с наибольшей ценой векселя:
     - №2 (первые 10 минут: живой прогон нового профиля до первого инсайта, секундомер);
     - №19 (маршрут лекции: пройти отрезок → gate quiz → CTA, зафиксировать факт петли);
     - №22 (зеркало прогресса: сверка mastery-процента с БД на живом профиле);
     - №23 (одна нить: сессия только через интенты, счётчик выходов в старое меню);
     - №26 (контрольный пересчёт TLRR — уже validated, вносится как эталон формата артефакта).
  2. Подключить два уже пишущихся сигнала как метрики:
     - checkpoint-события №23 (`checkpoint_offered` / принятие) → acceptance-rate;
     - session-события мира №20 → `time-to-first-action` (первое действие после входа в 3D/мир).
  3. Каждому из 5 — статус `validated` / `no-effect` / `regressed` + ссылка на артефакт
     (лог прогона, SQL-снимок, скрин) в README серии; OVR-строка в разделе «Здоровье серии».
- **Files (as amended 2026-07-24 — исходный план предполагал «без новых хранилищ»,
  это не подтвердилось для world-сигнала, см. Kill switch ниже):**
  `hometutor: app/ui/checkpoint.py` (нет изменений — сигнал уже писался), `app/ui/
  adaptive_plan_card.py` (нет изменений), `scripts/compute_checkpoint_acceptance_rate.py`
  (новый, читает существующие события; после контр-аудита — FIFO join +
  `(decision_id, surface)` ключ, помечен `metric_kind: "proxy"`); `app/session_tape.py`
  (**новые типы событий** `world_entered`/`world_first_action` в `EVENT_REQUIRED_FIELDS` —
  расширение схемы, не предусмотренное исходным планом); `app/ui/
  dashboards_graph_world_events.py` (новый size-extract модуль, вызывается из
  `dashboards_graph.py`); `scripts/compute_world_time_to_first_action.py` (новый);
  `hometutor-studio/doc/presentations/evolutionary_analyses/README.md` (ведомость + OVR);
  артефакты — `hometutor-studio/doc/next/replay_artifacts_2026-07/`.
- **DoD:** 5 outcome-статусов с артефактами; OVR посчитан и опубликован; два сигнала возвращают
  числа на живом профиле; ни один статус не проставлен без артефакта.
  **Фактический прогресс DoD (2026-07-24):** только №26 получил `validated` с артефактом;
  №2/№19/№22/№23 — `mechanically-reverified` (не входит в «5 outcome-статусов» DoD как задумано —
  это промежуточный статус, не финальный); оба сигнала действительно возвращают числа
  (честный `N/A`), но checkpoint-сигнал — `proxy`, не точный count. DoD **не закрыт полностью**.
- **Metric contract (актуализировано 2026-07-24 после независимого контр-аудита —
  исходные числа ниже были арифметически недостижимы и оставлены здесь как факт истории,
  не как текущий контракт):**
  ~~baseline 3.7%; target ≥21%~~ → **текущий baseline (после первого прогона волны)
  1/28 ≈ 3.6%; target 5/28 ≈ 17.9%** (5 кандидатов волны: №2, №19, №22, №23, №26;
  6-й разбор для достижения исходных «21%» сознательно не добавлен — это была бы
  скрытая эскалация объёма P0-1). Источник: README серии + этот файл.
  Guardrail: `shipped-unvalidated`/`mechanically-reverified` не переименовываются в
  `validated` без артефакта живого поведенческого прогона; `regressed` — валидный итог.
- **Kill switch (сработал 2026-07-24 для world-сигнала — зафиксировано, не скрыто):**
  условие «потребовалась новая схема/хранилище/пайплайн» **выполнилось**:
  `world_entered`/`world_first_action` не существовали до этой волны, план ошибочно
  предполагал обратное. Вместо остановки было принято решение расширить
  `session_tape.EVENT_REQUIRED_FIELDS` двумя типами через уже существующий generic
  append-only pipeline (не новое хранилище/файл-формат — тот же механизм, что и все
  остальные event types в этом файле). **Ratification-статус: implemented pending
  owner ratification** — решение принято агентом в рамках сессии реализации, не
  владельцем явно; требуется подтверждение владельца, что это расширение схемы приемлемо,
  прежде чем считать kill switch полностью закрытым, а не просто зафиксированным.
- **Effort:** дни. **Priority:** P0. **Dependencies:** нет (не зависит от #27).

## P0-2 — Диета поверхности (первое видимое упрощение)

**Статус 2026-07-24: implementation shipped, outcome unvalidated (не «закрыт»).**
Независимый аудит верно указал: DoD ниже требует живое подтверждение на профиле
владельца и screenshot до/после — ни то, ни другое не сделано. `cross_cutting_pains.md`
корректно называет этот инстанс `mitigated`, не `closed`; этот план синхронизирован
с той же формулировкой.

Что сделано (код + тесты, синтетические сценарии — не живой профиль владельца):
`get_ui_level()` (`app/ui_preferences.py`) больше не
автоапгрейдит активный профиль до `diagnostic`; добавлены `is_ui_level_decided()`/
`should_offer_first_choice()`; one-time баннер «Простой/Полный вид» на Mission Control
(`_render_first_level_choice_banner` в `app/ui/mission_control.py`); существующий
3-пресетный переключатель (`control_panel.py`) не тронут — kill switch (0 удалённых/
рефакторенных вью) соблюдён. Тесты: `tests/test_ui_preferences.py`,
`tests/test_mission_control_first_level_choice.py` — синтетические
`AppTest`/monkeypatch-сценарии, не живая БД владельца; плюс полный прогон
`test_mission_control_*`/`test_navigation_visibility.py`/`test_global_navigation.py`/
`test_architecture_guards.py` — все зелёные, регрессий не найдено.

Что НЕ сделано (открытый остаток DoD): живая проверка на реальном `user_state.db`
владельца — `visible_nav_views_for_level(get_ui_level())` фактически ≤10 на его
профиле; screenshot до/после в `replay_artifacts_2026-07/`.

- **Learning stage:** 1 — первый запуск / каждый вход владельца.
- **Outcome signal:** число nav-экранов, которые видит владелец при входе: 18 → ≤10.
- **Cross-cutting pain:** `PAIN-03` — упрощение построено (study-уровень), но невидимо владельцу.
- **Problem:** `get_ui_level()` молча повышает профиль с активностью до `diagnostic` —
  владелец всегда видит все 18 экранов; study-поверхность достаётся только пустому профилю.
- **Evidence:** `hometutor@05565efe9:app/ui_preferences.py::get_ui_level` (строки 140–152,
  ветка `_has_existing_activity() → LEVEL_DIAGNOSTIC`);
  `hometutor@05565efe9:app/ui/feature_registry.py::FEATURES` (26 фич, 18 nav, докстринг
  «аддитивный слой»); git: 0 удалённых файлов `app/ui` за серию при 29 добавленных.
- **Difference from №N:** №8/№23 добавляли слои видимости и нить; здесь **меняется только дефолт** —
  ни одного нового слоя и ни одного удаления.
- **Proposed:**
  1. Убрать молчаливый автоапгрейд в `get_ui_level()`: профиль с активностью при первом входе
     после обновления получает **один** вопрос «Простой вид или полный?» (выбор сохраняется).
  2. Переключатель «Простой вид / Полный вид» на Mission Control (использует существующие
     `set_ui_level()` / study-пресет; никаких новых уровней).
  3. Смок: study-дефолт показывает ≤10 nav-экранов; deeplink-мост и requirement-гейты
     (№8) не ломаются — существующие тесты `navigation_visibility` зелёные.
- **Files:** `hometutor: app/ui_preferences.py`, `app/ui/mission_control*.py` (переключатель),
  `tests/test_ui_preferences.py`, `tests/test_navigation_visibility*.py`.
- **DoD:** владелец при входе видит study-поверхность (или свой явный выбор); переключение
  в 1 клик; 0 удалённых вью; тесты навигации зелёные; скрин до/после в replay-артефакты.
- **Metric contract:** `visible_nav_views_for_level(get_ui_level())` на профиле владельца:
  baseline 18, target ≤10; wiring: `wired-existing` (функция уже есть).
- **Kill switch:** ход потянул удаление/рефакторинг вью или новый уровень видимости — стоп:
  разрешены только смена дефолта и переключатель.
- **Effort:** часы–день. **Priority:** P0. **Dependencies:** нет.

## P1 — #27 Execution Packet (engineering-трек, без изменений)

Параллельная дорожка по плану
[`local_model_execution_packet_plan.md`](local_model_execution_packet_plan.md) v1.7:
P0-1 Authoritative Trigger Hardening → P0-2 Runner v0 → P0-3 finalize-review.
Разбор №28 не меняет ни состав, ни порядок; смешивать волну валидации с #27 запрещено.

## P2 — после P0

| Ход | Условие |
|---|---|
| Разбор «Возвращение после перерыва» (нулевая область карты) | только после P0-1, чтобы родиться с wired-метрикой возврата |
| №25 semantic eval / SGAR baseline | только отдельным решением владельца; без прокси-метрик |
| №11 пересъёмка витрины 06/30 | перед внешним показом; после P0-2 — на упрощённой поверхности |

## НЕ делать (вердикты №28)

- Новый продуктовый разбор до конца волны валидации.
- «Чинить восторг» новой большой фичей (Мнемополис-2 и т.п.).
- Удалять код/вью ради упрощения.
- Подменять semantic eval №25 прокси-метриками.
