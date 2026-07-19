# Course Content Gate — компилятор доверенного обучения из мега-бандла: Plan

**Разбор №26 (связка №24+№25) · hometutor @ `84b7b5668ac2589b9ca2fb325c8279437ae961b` «343» · 2026-07-19**

---

## Статус

| Параметр | Значение |
|---|---|
| E1 (код/конфиг) | ✅ верифицировано на HEAD 343 |
| E2 (живой семпл) | ✅ **выполнен**: 9/9 структурно валидных quiz-генераций (3 темы × 3 повтора, 54 вопроса) + 3 синтеза урока на живом бандле; модель `qwopus3.6-35b-a3b-v1-mtp` @ `127.0.0.1:8080/v1` (llama.cpp), T=0.25, prompt @343, cache persist off, один процесс на повтор. «Структурно валидные» ≠ «качественные»: 0/54 несут evidence-поле, ≥1 семантическое искажение подтверждено (см. ниже) |
| E2 (данные) | ✅ живые снимки: `kg.sqlite` (8 конкурирующих тем), `user_state.db` (схема quiz_results без origin/evidence; 0 реальных концептов в mastery), `llm_request_cache.db` (нет ревизии контракта), `get_topics_catalog()` → 0 тем |
| Семпл-артефакты | `hometutor-studio/eval_data/content_gate_e2_2026-07-19/` — raw outputs целиком, рубрика v1.0 зафиксирована до генерации, cherry-picking запрещён |
| Семантическая аджюдикация | ✅ выполнена и заархивирована: [`semantic_adjudication_2026-07-19.md`](../../eval_data/content_gate_e2_2026-07-19/semantic_adjudication_2026-07-19.md) — Claude (эта сессия), не self-grade; 13/13 D2-флагов адъюдицированы построчно (12 GROUNDED, 1 BORDERLINE), 2 confirmed findings с цитатами; D3-only флаги (22 доп.) — scope cut, не адъюдицированы |
| P0 выбран | да: P0-A Gate Packet + P0-B Verified Step Contract |
| **Implementation** | ⬜ **не начата.** Разбор доказывает и упаковывает боль в исполнимый P0 — он не закрывает её сам по себе. `PAIN-02` instance в реестре остаётся `Status: open` до P0-A/P0-B + post-ship replay. |

**Ограничение честности семпла:** 9 генераций = минимум гайда §4.1 для
исследовательского вердикта (3×3). Проценты качества (VLQR/SGAR) по нему не
заявляются; семпл доказывает **механизм** и даёт нижнюю границу
«≥1 `DISTORTED` искажение + 1 `BORDERLINE` semantic issue, прошедшие все структурные
проверки» (Finding 1 `DISTORTED` + Finding 2 `BORDERLINE`, см. адъюдикацию).
Расширение до 15 (5×3) — P1.

**Методическая находка из аджюдикации (важна для P0-B):** лексическая
диагностика D2 (доля слов правильного ответа, найденных в контексте) не поймала
самое опасное искажение (`r1/guardrails#3` — D2=1.0, потому что фабрикация
использует дословные слова источника в неверном смысле). Это подтверждает
(не только теоретически, но эмпирически на этом семпле) выбор P0-B: gate должен
требовать **exact-match конкретной цитаты** (`source_quote`), не overlap-порог —
overlap можно обмануть дословными словами не в том смысле.

---

## Паспорт

| Поле | Значение |
|---|---|
| Learning stage | 2 (импорт/индексация) · 4 (ответ/доверие) · 6 (практика/квиз) · 9 (план/следующий шаг) |
| Outcome signal | студент получает короткий проверяемый source-grounded маршрут из лучших фрагментов разных курсов |
| Cross-cutting pain | `PAIN-02` — закон вне ежедневного цикла: качество контента измеряется (async judge, рубрики, паспорта, отчёты гейтов), но не управляет маршрутом/ответом/квизом/mastery |
| Difference from №21 | №21 дал адреса и каталог; здесь решается, какие фрагменты стоит учить |
| Difference from №24 | №24 — качество квизов изолированно; здесь квиз-гейт — звено маршрута |
| Difference from №25 | №25 — groundedness одного ответа; здесь groundedness — контракт синтеза курса |

---

## North Star

**`trusted_learning_route_rate` (TLRR)** — доля шагов учебного маршрута
(day route / SSR primary), где выполнены все 6 компонент контракта шага:

```
1. source address        («курс · урок» — есть, №21 P1: concept_address.py)
2. evidence span         (фрагмент-основание шага)
3. quality/freshness label (роль + свежесть источника)
4. grounded explanation  (объяснение с привязкой; simple version — к тому же span)
5. verified quiz/task    (вопрос с evidence binding, подтверждён источником)
6. selection reason      (почему выбран этот источник/фрагмент)
```

| Параметр | Значение |
|---|---|
| Формула | `TLRR = |шаги с 6/6 компонентами| / |шаги маршрута|` — детерминированный подсчёт, без LLM |
| Источник данных | content gate packet (P0-A) + route payload (`select_day_route` / SSR) + quiz evidence status (P0-B) |
| Baseline | **0%** — live: компонента 1 отгружена, компоненты 2–6 не существуют ни у одного шага |
| Target | P0-сценарий: ≥1 полный шаг на эталонном бандле; %-target назначается после первого замера (правило №24/№25: не выдумывать проценты) |
| Wiring-status | **`wire-in-P0`** — подсчёт входит в DoD P0-B |

Дополнительные метрики:

| Метрика | Формула / источник | Baseline | Wiring |
|---|---|---|---|
| `verified_quiz_question_rate` | вопросы с exact-match evidence binding / все вопросы, влияющие на mastery (детерминированная часть VLQR №24) | 0/54 в E2 (схема не просит evidence) | `wire-in-P0` |
| `freshness_labeled_step_rate` | шаги с ярлыком роли/свежести / все шаги gated-тем | 0% | `wire-in-P0` |
| `source_grounded_answer_rate` (SGAR №25) | semantic entailment claim→source, независимая разметка | не измерен | `not-measurable` до offline-разметки (P1/P2 линии №25) |
| `practice_backed_topic_rate` | темы маршрута с привязанной практикой | не считается | `wire-in-P1` |
| `student_time_saved_estimate` | — | — | `not-measurable`: честной методики нет — не заявляем |

---

## Ключевые evidence-якоря (E1 + E2)

Формат: `repo@commit:path::symbol`; строки — подсказка на 343.

1. **Эталон гейта существует:**
   `hometutor@84b7b5668:app/course_graph_compiler.py::evaluate_graph_quality_gate`
   (L854–902) — 10 проверок, честный отказ. Live: `graph_quality_report.json`
   активной генерации: `gate_passed=true`, 82 концепта, 100% evidence, 0 сирот.

2. **Квиз-путь без контентного гейта:**
   `hometutor@84b7b5668:app/quiz_scoped.py::parse_scoped_quiz_json` — структура only;
   `hometutor@84b7b5668:app/fact_source_binding.py::apply_quiz_outcome_to_learner_state`
   — немедленная запись mastery+SR. E2: **0/54** сгенерированных вопросов несут
   какое-либо evidence/origin-поле (схема не просит).

3. **Живое искажение (боль-якорь):** семпл `r1/guardrails#3` — вопрос
   «…за который „присядут"?» с верным ответом «Уголовное наказание для системы»,
   рождён из оговорки в ASR-транскрипте `ИИ Агенты/Урок 4….txt`
   («…не присядешь… Ну, не мне, а системе»). Структурно валиден; дошёл бы до
   mastery. Рядом валидные вопросы (числовой факт «50 тыс. токенов MCP»
   подтверждён дословно) — семпл честный, не cherry-pick.

4. **Mastery-запись неопровержима постфактум:**
   `D:\AI\app\data\user_state.db::quiz_results` — колонок origin/evidence/question
   нет (189 строк; в `quiz_mastery` 0 реальных концептов курса — только тестовые
   призраки №22).

5. **Петля «слабый концепт → квиз» мертва на живом бандле:**
   `hometutor@84b7b5668:app/knowledge_catalog.py::get_topics_catalog` → live 0 тем
   (summary-коллекция пуста) ⇒
   `hometutor@84b7b5668:app/quiz_scoped.py::weak_spot_scoped_quiz_params`
   (topic без source_paths) ⇒ `synthesize_topic_summary` = "" ⇒ отказ
   «Слишком мало текста». Рабочий production-путь — только с явными
   `documents` (`app/routers/quiz.py` L115–128).

6. **Маршрут слеп к качеству:**
   `hometutor@84b7b5668:app/ui/knowledge_graph_d3_analysis.py::node_worth`
   (L234–268) — due/novel/decay/frontier/reach; ни качества, ни свежести.
   Входы SSR (`smart_study_recommendation.py`) — очереди/weak/topic; то же.

7. **Приборы есть, проводки нет (PAIN-02):**
   `hometutor@84b7b5668:app/async_quality_judge.py::schedule_async_quality_judge_if_sampled`
   — judge выключен по умолчанию (`config.py` L116–117), оценки только в metrics;
   `hometutor@84b7b5668:app/query_metrics.py::_compute_deterministic_quality_checks`
   (L115–141) → debug; `hometutor@84b7b5668:app/konspekt_learning_passport.py`
   (rubric/grades/staleness) → 2 UI-вью.

8. **№25-факты re-verified на 343:**
   `hometutor@84b7b5668:app/grounded_answer.py::apply_grounded_validation`
   (L461) — cache_hit → `skipped=True`; live `llm_request_cache.db`:
   `request_hash → response_json`, ревизии контракта нет.
   `.github/workflows/ci.yml` — ruff/pytest/arch guards; контентных гейтов нет.

9. **Синтез-инфраструктура для кандидат-урока работает:** E2 3/3 синтеза
   (обе стороны курса в секциях), но `compute_source_coverage` на живом бандле
   отдаёт `covered=2 / total=0 / ratio=0.0` (каталог пуст) — coverage сломан;
   кандидат-урок повторяет ASR-артефакт («EVO» как имя сервиса).

---

## P0-A: Course Content Gate Packet

- **Problem.** После реиндекса гейт проверяет только карту. По темам с
  конкурирующими источниками (live: 8) никто не решает, какой фрагмент учить,
  не помечает роли/свежесть/шумность и не оставляет проверяемого следа решения.
  Сырой ASR-транскрипт входит в экзаменационный контекст наравне с вычитанным
  конспектом.
- **Evidence.** Якоря 1, 3, 6, 7, 9 выше.
- **Proposed.** Хвост реиндекса (или ручной запуск по теме) собирает
  `course_content_gate_report.json` **рядом с** `graph_quality_report.json`
  в бандле генерации (существующий паттерн хранения, не новая схема):
  - темы (концепты с ≥2 документами; приоритет — с ≥2 course folders);
  - конкурирующие источники по теме (из `documents`/`related_documents`);
  - детерминированные ярлыки: роль (`конспект .md` / `транскрипт .txt` /
    `living-konspekt` — по типу и папке), freshness (source hash/mtime,
    паттерн №3), шумность транскрипта (плотность междометий/обрывов),
    practice-сигналы (наличие заданий/код-блоков);
  - best-source choice **with reason** + rejected/secondary **with reason**
    (никто не удаляется);
  - evidence spans (chunk-выдержки по теме — то, что уже возвращает
    `fetch_document_chunks_text`).
  - Поверхность: минимум одна — блок «почему этот фрагмент» в паспорте темы /
    Library (read-model уже есть: `library_catalog_read.py`).
- **Files.** NEW `app/course_content_gate.py` (pure, read-only по индексу/графу) +
  вызов из реиндекс-хвоста рядом с publish гейта графа; NEW
  `scripts/run_course_content_gate.py` (ручной запуск по теме);
  UI: точечная вставка в существующий паспорт (без нового вью);
  tests NEW `tests/test_course_content_gate.py` (fixture 2 курса × md+txt).
- **DoD.**
  - работает на 3–5 темах эталонного бандла (те же guardrails/agentic-loop/rag);
  - audit packet сохраняется в бандл генерации и воспроизводим;
  - никакой новой БД/схемы; LLM не вызывается;
  - студент видит хотя бы один «почему этот фрагмент лучше» с причиной;
  - `freshness_labeled_step_rate` считается для gated-тем.
- **Metric contract.** `freshness_labeled_step_rate` 0% → 100% на gated-темах
  (wire-in-P0); вклад в TLRR-компоненты 2, 3, 6.
- **Kill switch.** Потребовалась новая большая БД/схема/пайплайн → стоп,
  packet остаётся read-only файлом; захотелось LLM-скоринга источников →
  заменить на детерминированные ярлыки, LLM — только offline P1/P2.
- **Effort.** ~день. **Priority.** P0. **Dependencies.** нет (граф и адреса №21
  уже отгружены).

---

## P0-B: Verified Learning Step Contract

- **Problem.** Шаг маршрута не имеет контракта доверия: quiz без evidence
  обновляет mastery (якоря 2–4), ответ без groundedness не маркируется,
  North star не считается.
- **Evidence.** Якоря 2, 3, 4, 6, 8 выше; №24 план P0a (evidence binding,
  fallback origin); №25 candidate P0-A (packet), P0-B (cache parity — остаётся
  gated отдельным аудитом кэша).
- **Proposed.** Минимальный исполняемый контракт:
  1. **Quiz evidence binding** (линия №24 P0a, поглощается сюда):
     `QUIZ_SCOPED_PROMPT` + `source_quote`/`origin`; `_normalize_scoped_questions`
     ставит `evidence_bound=True` только при нормализованном **exact-match**
     цитаты в фактическом generation context (не overlap-порог — семантическая
     аджюдикация этого семпла эмпирически показала, почему: Finding 1 в
     `semantic_adjudication_2026-07-19.md` имел лексический overlap 100% при
     фабрикации смысла — overlap обманывается дословными словами не в том
     смысле, exact-match конкретной цитаты устойчивее); `_fallback_micro_quiz`
     получает `origin="fallback"`; `process_micro_quiz_outcome` не пишет mastery
     для fallback.
  2. **Mastery только от validated + evidence-статус персистентен, не только
     runtime-параметр.** `apply_quiz_outcome_to_learner_state` принимает и
     **сохраняет** evidence-статус, чтобы TLRR/post-ship replay могли читать
     его из БД, а не только из живого вызова:
     - `quiz_results`: **аддитивные** nullable-колонки `origin TEXT`,
       `evidence_bound INTEGER` (0/1) через `ALTER TABLE ... ADD COLUMN`
       (SQLite, backward-compatible, старые строки → NULL = «не оценено»,
       не «fallback»/«не evidence-bound» — различать явно в чтении);
     - не-validated исход **не пишет** в `quiz_mastery`/`spaced_repetition`
       (как раньше), но **пишет** в `quiz_results` с `evidence_bound=0` —
       иначе аудит-след пропадает и TLRR/replay нечем считать постфактум;
     - это **не** «новая схема» в смысле kill switch ниже (новая таблица/
       хранилище/пайплайн) — это аддитивная колонка существующей таблицы,
       тот же паттерн, что миграции `generation_id`/`index_version` в этой же
       таблице.
  3. **Ярлык ответа:** не-grounded/skipped ответ несёт видимый статус
     «не подтверждено» (данные уже в debug/quality_checks — вывести ярлыком,
     не новым вычислением).
  4. **North star wiring:** детерминированный скрипт
     `scripts/compute_trusted_route_rate.py` считает TLRR по gate packet +
     route payload + **`quiz_results.evidence_bound`** (не только по
     live-вызову — так возможен post-ship replay без повторной генерации)
     для P0-сценария.
- **Files.** `app/prompts/_impl.py` (QUIZ_SCOPED_PROMPT), `app/quiz_scoped.py`,
  `app/quiz_micro.py`, `app/fact_source_binding.py` (+ tier/статус в сигнатуре),
  `app/user_state_quiz.py` (или соседний owner схемы `quiz_results` —
  аддитивная миграция origin/evidence_bound), UI scoped/micro quiz completion
  (`app/ui/scoped_quiz.py` и соседи), NEW
  `scripts/compute_trusted_route_rate.py`, tests NEW
  `tests/test_quiz_content_contract.py`, `tests/test_trusted_route_rate.py`.
- **DoD.**
  - один route step проходит контракт целиком на эталонном бандле (6/6);
  - quiz без evidence не обновляет mastery (тест);
  - fallback-вопрос не обновляет mastery (тест);
  - `quiz_results.origin`/`evidence_bound` персистентны для **каждого**
    исхода (не только validated) — тест на аддитивную миграцию (старые строки
    читаются, новые пишут статус);
  - ответ без groundedness маркируется «не подтверждено»/abstain;
  - TLRR считается для P0-сценария **из БД** (не только из live-прогона) и
    попадает в отчёт;
  - `verified_quiz_question_rate` и `fallback_rate` считаются (wire-in-P0).
- **Metric contract.** TLRR baseline 0% зафиксирован; после P0 — первый замер;
  `critical_unsupported_rate` (№24) считается на новых генерациях.
- **Kill switch.** Модель игнорирует evidence-поле → вопрос остаётся
  display-only «LIMITED», порог не ослаблять до «есть строка»; понадобилась
  **новая таблица/хранилище/пайплайн** для mastery/evidence-аудита → стоп
  (аддитивные nullable-колонки к `quiz_results` — разрешены, это не то же
  самое, что «новая схема»; см. Proposed п.2); runtime LLM-judge → нет.
- **Effort.** 1–2 дня. **Priority.** P0. **Dependencies.** P0-A для
  reason/label компонент TLRR; quiz-часть независима.

---

## P1

1. **Семпл 15 (5 тем × 3 повтора)** по рубрике №26 v1.0 с независимой
   аджюдикацией — первые честные VLQR-числа; replay боль-якоря
   («уголовное наказание» класс обязан не пройти в mastery без evidence-статуса и ярлыка; semantic entailment остаётся отдельным offline/P2 слоем);
   outcome-status по правилам серии.
2. **UI-паспорт «почему выбран источник»** — полноценная поверхность выбора
   (сегодня — минимальный блок из P0-A).
3. **Сравнение курсов по ролям**: база / практика / свежий опыт / альтернативная
   позиция — на данных packet, presentation-only.
4. **Починить топливо синтеза**: пустая summary-коллекция (`get_topics_catalog`
   → 0) и сломанный `compute_source_coverage` (`covered=2/total=0`) — без этого
   weak-spot петля остаётся мёртвой. (Отдельный маленький ход, вероятно
   ingestion-конфиг; расследовать перед фиксом.)

## P2

- Персонализация под цель: «быстро войти» / «стать практиком» / «экспертная
  насмотренность» (лестница L1–L6);
- автоматический gap-analysis «этого нет ни в одном курсе → нужен свой опыт»;
- экспорт личной программы обучения;
- offline semantic SGAR baseline (линия №25 P2) на packet-данных.

---

## НЕ делать (вердикты)

1. ❌ Runtime LLM-judge перед публикацией каждого ответа — латентность + вторая
   самооценка (№14); online остаётся детерминированным.
2. ❌ Ещё один summary/паспорт без исполняемых проверок.
3. ❌ Считать цитату или token overlap доказательством semantic groundedness
   (контр-аудит №25).
4. ❌ Обновлять mastery от неподтверждённого квиза, включая fallback.
5. ❌ Строить план по частоте терминов.
6. ❌ Прятать слабые/устаревшие источники без объяснения — только
   rejected-with-reason.
7. ❌ Новая БД/схема ради гейта — packet = файл в бандле генерации.
8. ❌ Заявлять VLQR/SGAR-проценты без живого измерения нужного размера.
9. ❌ Менять `node_worth`/SSR-формулы до измеренного эффекта — сначала ярлыки и
   reason, потом веса.
10. ❌ Трогать `backlog_registry.yaml` — только кандидаты, промоут решением
    владельца.

---

## Kill Switch (весь план)

- Новая большая БД/схема/пайплайн в P0 → стоп, только read-only audit packet.
- LLM там, где хватает детерминированного evidence matching → заменить.
- Метрику нельзя посчитать → не заявлять доказанный эффект.
- Живой E2 недоступен → provisional E1 (здесь выполнен; для replay обязателен
  тот же бандл/темы/рубрика).

## Post-ship replay

Повторить прогон E2 (те же 3 темы, тот же бандл, та же рубрика v1.0) после P0:
- Finding 1 (`r1/guardrails#3`, «уголовное наказание для системы») не должен
  пройти в mastery без evidence-статуса и ярлыка: P0-B закрывает отсутствие
  цитаты/evidence, но не доказывает semantic entailment сам по себе;
- Finding 2 (`r2/guardrails#4`, subject substitution при дословно верной фразе)
  честно **может повториться** — P0-B детерминированный, semantic entailment
  слой для этого класса не входит в P0 (offline/P2); замер `TLRR` не должен
  молчаливо считать Finding-2-класс закрытым;
- TLRR P0-сценария > 0. Статусы: `shipped-unvalidated` → `validated` /
  `no-effect` / `regressed`.

---

## Связи

| Разбор | Что берём | Что меняем |
|---|---|---|
| №21 | адреса «курс · урок», каталог, courses[] | добавляем «что учить и почему», не «где лежит» |
| №22 | чистое зеркало данных | продолжение: чистый контент поверх чистых данных |
| №23 | Route Policy / один primary шаг | контракт доверия шага, который Policy сможет требовать |
| №24 | рубрика квиза, P0a evidence binding | поглощается в P0-B как часть контракта шага |
| №25 | рубрика R1–R8, packet-методология, cache parity | packet становится общекурсовым; parity — отдельный gated ход |

---

*Создано: 2026-07-19 · runtime HEAD `84b7b5668` «343» · E1 verified · E2 executed
(9/9 + 3 синтеза, артефакты в `eval_data/content_gate_e2_2026-07-19/`) ·
P0 = Gate Packet + Verified Step Contract.*

