# generate_breakthrough_ideation_prompt

Актуализировано: **2026-05-02** (CANDIDATE_TABLE: критерии выбора)

Общие для агентов правила (**SSoT / sync после YAML, Windows/PowerShell, token budget**): [`_common_rules.md`](_common_rules.md).

Промпт для **генерации прорывных идей** по конкретному CJM-этапу, User Story, pain point или области фичей.

> Нужно спланировать следующий пакет из backlog?
> → [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md) — выберет и напишет контракт (если есть eligible-кандидаты по правилам реестра).
>
> Plan-next вернул `blocker: no eligible plan-next candidate…` или нужно **один** согласованный package proposal без генерации десятка идей?
> → [`product_owner_plan_package_prompt.md`](./product_owner_plan_package_prompt.md) — ручная упаковка пакета под PO.
>
> Нужен **табличный обзор** возможных направлений из CJM / user stories / roadmap перед выбором TARGET?
> → **этот файл**, режим **`MODE=CANDIDATE_TABLE`** (§ «Как использовать»): одна таблица **с критериями выбора** (критичность P0–P2, рычаг влияния, актуальность H/M/L, сила сигнала, пороги), без ≥N идей и без диффов.
>
> Нужен поиск **новых сценариев** по конкретному направлению (Stage / US / pain / feature area)?
> → **этот файл**, основной режим с `TARGET` + `N_IDEAS`: ≥N идей + черновики диффов в артефакте (`archive/ideation/…`).
>
> Нужно спроектировать дизайн UI/UX для уже известного пакета?
> → [`designer.md`](./designer.md) — макеты и контракты UI.

---

## Правило выбора входа

| Ситуация | Что запускать |
|----------|---------------|
| Автоматический следующий пакет из SSoT, есть кандидаты по [`backlog_registry.yaml`](../backlog_registry.yaml) / CJM / re-entry | [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md) |
| `blocker: no eligible plan-next candidate…` — нужно **одно** решение PO: цель, ≤5 outcomes, US, риски (без «шторма идей») | [`product_owner_plan_package_prompt.md`](./product_owner_plan_package_prompt.md); после согласования — ручное/редакторское попадание в реестр и sync |
| Уже есть `ready` / `wip` у пакета и пора исполнять | `python scripts/workflow.py` (роутер; или вручную: [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md)) |
| Работа по `PACKAGE_ID` уже ведётся (`archive/team_artifacts/<ID>/`) | [`generate_resume_prompt.md`](./generate_resume_prompt.md) |
| Нужна **матрица направлений** (CJM moment / US / pain / feature / источник **+ критерии приоритизации**) для выбора будущего TARGET | **Этот файл** — **`MODE=CANDIDATE_TABLE`** (инвентаризация, см. § «Как использовать») |
| Выбран TARGET; нужны **≥N прорывных идей** и внешние практики (линзы), артефакт с предложенными диффами | **Этот файл** — основной режим: `TARGET` + `N_IDEAS` (+ опц. `ANGLES`, `CONSTRAINTS`) |
| Need AI Vision ideas with ML/data/eval/cost constraints | **This file** - `MODE=AI_VISION_IDEATION` with `TARGET`, `N_IDEAS`, `ANGLES`, and AI-specific `CONSTRAINTS` |
| Идеи уже отфильтрованы; нужно **зашить одну** победившую концепцию в формальный package | Сначала [`product_owner_plan_package_prompt.md`](./product_owner_plan_package_prompt.md); затем правка [`backlog_registry.yaml`](../backlog_registry.yaml) и sync по канону [**_common_rules.md** § Sync](_common_rules.md) при готовности контракта |
| UI/UX дизайн известного объёма работ | [`designer.md`](./designer.md) |

**Типичная цепочка при пустом машинном пуле:** [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md) → (blocker) **CANDIDATE_TABLE** → основной breakthrough по строке → [`product_owner_plan_package_prompt.md`](./product_owner_plan_package_prompt.md) → реестр/sync.

## Чем отличается от [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md)

| Различие | Plan Next | Breakthrough Ideation (этот файл) |
|----------|-----------|-----------------------------------|
| Задача | Выбрать следующий пакет, написать контракт | Сгенерировать ≥N новых идей для целевой области |
| Входы | Empty backlog → список кандидатов | CJM Stage / US / pain point / feature area |
| Выходы | Контракт в backlog_registry.yaml + regenerated tasklist.md | Артефакт с готовыми диффами (cjm/us/backlog_registry/epochs) |
| Применение | Запись в backlog_registry.yaml через plan-next/sync | Артефакт → review → ручное или через orchestration |
| Источник идей | CJM, user stories, roadmap | Best practices (Duolingo/Anki/Khan/Notion/etc), методики (SM-2, Hook Model, JTBD) |
| Линзы | N/A | UX / Pedagogy / Engagement / Accessibility / Monetization / Retention |

Plan Next выбирает из существующего backlog. Breakthrough Ideation **генерирует новые кандидаты** для конкретной цели.

---

## Чем отличается от [`product_owner_plan_package_prompt.md`](./product_owner_plan_package_prompt.md)

| | [Product Owner — Планирование пакета](./product_owner_plan_package_prompt.md) | Breakthrough Ideation (этот файл) |
|--|------|------|
| **Задача** | Сформулировать **один** следующий delivery-пакет (`epoch-*`): цель, до 5 outcomes, риски, зависимости, поглощение deferred | Сгенерировать **много** прорывных сценариев/идей (≥N) по заданному направлению с опорой на внешние практики и линзы |
| **Выход** | Текстовый пакет для review: CJM stage, US, AC на уровне буллетов; явный запрет лезть в техническую реализацию | Артефакт в `archive/ideation/…` с идеями, источниками методик и **предложенными** диффами для CJM/US/registry/epochs (агент **не** коммитит и не правит SSoT напрямую, пока владелец не примет) |
| **Вход** | Широкое чтение: `backlog_registry`, CJM, roadmap, closed iterations, индекс stories, `vision` | Узкий **`TARGET`** (Stage / US / pain / feature area) + `N_IDEAS`, опционально `ANGLES`/`CONSTRAINTS` |
| **Связь с беклогом** | Напрямую проверяет registry (active/deferred/proposed) и вплетает deferred | Может использовать registry как справочник, но фокус на **новизне** и brainstorming, а не на строгой записи контракта |
| **Типичная цепочка** | Plan-next blocker → **этот** PO-промпт → ручное внесение в `backlog_registry.yaml` / оркестрация | Ideation / таблица кандидатов (см. ниже) → фильтр человеком → затем **PO plan package** или сразу упаковка в registry |

**Кратко:** `product_owner_plan_package_prompt` — «упаковать **один** пакет». Breakthrough ideation — «**насыпать** идеи и черновики изменений, потом выбрать». Часто порядок такой: таблица пробелов → breakthrough по выбранной строке → PO plan package для финального package proposal.

---

## Как использовать

Вставить в любой AI-агент (Claude Code, Codex, Cursor AI):

```
Прочитай doc/team_workflow/generate_breakthrough_ideation_prompt.md
и выполни инструкции ниже.

Параметры (обязательные):
  TARGET: Stage #7: Course Learning Mode
          (или: US 14.3 / pain point: high churn in retention / feature: quiz retry flow)
  N_IDEAS: 10      (минимум новых идей)
  
Параметры (опционально):
  ANGLES: Engagement, Pedagogy   (какие линзы фокусировать; default: все)
  CONSTRAINTS: cannot break: existing quiz format, token budget <1M per query
```

**Таблица кандидатов перед ideation (ещё без генерации N идей).** Режим **`MODE=CANDIDATE_TABLE`**: собрать **обзорный список направлений** из CJM, user stories и roadmap (плюс при необходимости deferred/proposed из реестра), выписать **одну** Markdown-таблицу и **отсортировать строки** так, чтобы проще выбрать наиболее актуальное и сильное по влиянию направление для будущего `TARGET`. В таблице обязательны колонки **`Критичность`**, **`Влияние`**, **`Актуальность`**, **`Сила сигнала`**, **`Порог / блокеры`** (шкалы и порядок сортировки — в блоке ниже; идеи и диффы не генерировать).

```
Прочитай doc/team_workflow/generate_breakthrough_ideation_prompt.md
и выполни ТОЛЬКО режим CANDIDATE_TABLE (инвентаризация, без PHASE 2 генерации идей).

Источники (read-only; read-set/token budget см. также [`_common_rules.md`](_common_rules.md); большие файлы — только §/grep):
  - doc/cjm.md — §5 «Критические моменты», §6 «Метрики переходов learning route» (если строки про переходы), §8 «CJM pain table»
  - doc/user_stories.md — shortlist, индекс stories, **Priority (P0/P1/P2)**, статусы/coverage
  - doc/future_roadmap.md — Current Horizon Decision, Re-entry Rules
  - при необходимости doc/backlog_registry.yaml — только записи со status deferred/proposed
    (grep/slice, не загружать файл целиком)

Вывод: одна Markdown-таблица (10–25 строк, можно меньше если мало сигнала); **перед выдачей отсортируй строки** по правилу из блока ниже (Актуальность → Критичность → Сила сигнала).
  Заголовок (все колонки обязательны):

  | # | CJM Stage / Moment | US (id или «—») | Pain point (кратко) | Feature area | Источник | Критичность | Влияние | Актуальность | Сила сигнала | Порог / блокеры |

  Расшифровка критериев выбора (заполняй по фактам из источников; не выдумывай метрики и числовые SLO):
  - Критичность — `P0` | `P1` | `P2` | `—`:
    `P0` если направление напрямую закрывает moment of truth из cjm §5 или помечено `P0` в `doc/user_stories.md`;
    `P1` — известный pain / доверие / удержание в цикле, типично `P1` в индексе US;
    `P2` — улучшение, nice-to-have, типично `P2` в индексе US;
    `—` для строк без пользовательской US (мета: roadmap/registry workflow, чистая инфра без MoT в строке).
  - Влияние — ровно один первичный рычаг (для сортировки): `activation` | `trust` | `retention` | `loop` | `completion` | `infra` | `meta`.
    Пояснение: `loop` — глубина учебного цикла (tutor/quiz/plan/SRS), `completion` — ощущение прогресса/graduation,
    `infra` — качество/латентность/ingest/eval без прямого UX-момента в строке, `meta` — планирование пакета/горизонт.
  - Актуальность — `H` | `M` | `L`:
    `H` — есть явный триггер сейчас: `deferred`/`proposed` в registry, открытая US (`open` / `open_candidates`), правило re-entry в roadmap, упоминание регрессии/gate;
    `M` — закрытая US/pain, но в источнике есть follow-up (deferred id, `re_entry_condition`, residual scope, связанный tail в notes);
    `L` — базовая строка по §5/§6 без свежего сигнала сверх «всегда важный MoT».
  - Сила сигнала — `S` | `M` | `W`:
    `S` — прямой якорь в `backlog_registry.yaml` (id пакета, re-entry, blocks) или открытый planning-артефакт;
    `M` — согласованные `doc/cjm.md` §8 + US status/coverage;
    `W` — только §5/§6 или общий narrative без жёсткой привязки к closed/open статусу.
  - Порог / блокеры — до ~12 слов: что нужно, чтобы честно стартовать (например: «eval gate breach», «story gate OCR», «owner + DoD», «нет open US», «—»).

  Сортировка по умолчанию для человека: сначала `Актуальность` (H→M→L), внутри — `Критичность` (P0→P1→P2→—), затем `Сила сигнала` (S→M→W). При равенстве — по субъективному `Влиянию` (activation/trust выше meta), только если так удобнее PO.

Правила:
  - Одна строка = одно возможное направление для последующего TARGET.
  - Если pain в §8 уже `closed:*`, всё равно включай строку, если roadmap или deferred/registry намекают на follow-up — отрази это в `Актуальности`/`Силе сигнала`/`Пороге` и в колонке `Источник`.
  - Не генерируй прорывные идеи и не предлагай диффы — только таблица.
После того как человек выбрал строку, запускай основной промпт сверху с TARGET, взятым из этой строки (Stage / US / pain / feature), опционально скопируй критерии выбора в комментарий к TARGET для контекста линз.
```

Опционально (для ограничения):

```
Прочитай doc/team_workflow/generate_breakthrough_ideation_prompt.md
FOCUS_CJM: Stage #7
N_IDEAS: 7
ANGLES: UX, Pedagogy, Engagement
```

---

## Инструкции для AI-агента

```text
Goal: generate ≥N breakthrough scenarios for <TARGET> (CJM stage / US / pain point / feature area).
      Produce ≥N_IDEAS candidates with method sources.
      Stop after creating diffs in read-only artifact.
      Do NOT apply edits directly to cjm.md / user_stories / backlog_registry / tasklist / epochs.
      Output = archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md with proposed changes.

INPUT (required):
  <TARGET>      — CJM stage ID ("Stage #7: Course Learning Mode"),
                  US ID ("US 14.3"),
                  pain point ("high churn in retention"),
                  or feature area ("quiz retry flow")
  <N_IDEAS>     — minimum viable ideas to generate (default: 10)
  
INPUT (optional):
  <ANGLES>      — comma-separated lenses to prioritize
                  (default: all of [UX, Pedagogy, Engagement, Accessibility,
                   Monetization, Retention])
  <CONSTRAINTS> — semicolon-separated rules
                  (e.g. "cannot break: existing contract; token budget <1M per call;
                   must work offline")
  MODE=CANDIDATE_TABLE — см. § «Как использовать», подзаголовок «Таблица кандидатов перед ideation»: таблица с колонками приоритизации и сортировкой строк (без ≥N идей и без PHASE 2–N идеационных фаз ниже).
  MODE=AI_VISION_IDEATION — AI-specific ideation mode. Each accepted idea
                  must include ml_approach, data_requirements, and
                  evaluation_contract. Apply AI-specific constraints in
                  Phase 2 before ranking.

Token budget for entire flow: не выходить за лимиты [`_common_rules.md`](_common_rules.md); для суммарного прогона этой инструкции целиться в ≤12k входных токенов, когда возможно.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRANCH — MODE=CANDIDATE_TABLE (если активирован пользователем)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Цель: дать человеку **обзорную таблицу** возможных TARGET'ов перед основным breakthrough-прогоном.

Шаги (read-only):
  1. doc/cjm.md — §5 (moments), §8 (pain table): выписать связки moment ↔ pain ↔ US из таблицы.
  2. doc/user_stories.md — индекс/shortlist: уточнить id US, **Priority (P0/P1/P2)** и статусы/Coverage для колонки «Критичность» и «Сила сигнала».
  3. doc/future_roadmap.md — Current Horizon, Re-entry — добавить строки и отметить **Актуальность** (H/M/L), если стратегия намекает на gap/follow-up или мета-планирование.
  4. Опционально: doc/backlog_registry.yaml — только deferred/proposed (grep), не читать весь файл; для таких строк — **Сила сигнала S**, **Актуальность** по `re_entry_condition`/`notes`.

Вывести **ровно одну** Markdown-таблицу со столбцами (см. § «Как использовать», блок MODE=CANDIDATE_TABLE):
  # | CJM Stage / Moment | US (id или —) | Pain point (кратко) | Feature area | Источник | Критичность | Влияние | Актуальность | Сила сигнала | Порог / блокеры

  Значения и шкалы колонок «Критичность» … «Порог / блокеры» — **строго** по расшифровке в § «Как использовать» (тот же режим); не придумывать числовые SLO.
  После заполнения таблицы **отсортируй строки** для человека: Актуальность H→M→L, затем Критичность P0→P1→P2→—, затем Сила сигнала S→M→W (как в § «Как использовать»).

  10–25 строк; если сигнал слабый — меньше. Не генерировать новые продуктовые идеи и не писать диффы.
  STOP (не переходить к PHASE 2 и далее в этом тексте).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 — INPUTS & VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Если MODE=CANDIDATE_TABLE уже выполнен — этот PHASE и всё ниже до конца блока инструкций **пропускаются**.

1. Parse <TARGET>:
   - If matches "Stage #\d+.*": extract stage number, read doc/cjm.md § Stage
   - If matches "US \d+\.\d+": locate doc/user_stories/us-<ID>.md
   - If prose (e.g., "high churn"): grep doc/cjm.md for keyword
   - If feature area (e.g., "quiz retry"): grep app/<module>.py for context
   
   If <TARGET> not found: STOP with "⚠ <TARGET> not found. Check doc/cjm.md, user_stories/, or app modules."

2. Normalize <ANGLES>:
   - If empty: use all = [UX, Pedagogy, Engagement, Accessibility, Monetization, Retention]
   - Else: split by comma, lowercase, validate against known set
   
3. Parse <CONSTRAINTS>:
   - Split by semicolon
   - Store for PHASE 2 validation (each idea must respect constraints)

4. Token budget estimate:
   - doc/cjm.md relevant section: ~500–800 tokens
   - 1–2 user_stories: ~800–1200 tokens
   - backlog_registry relevant entries: ~300–500 tokens
   - Total Phase 1 estimate: ~2000 tokens
   
   If estimated Phase 1 выше допустимого порога для одного вызова (см. [`_common_rules.md`](_common_rules.md)): STOP with "Token budget exceeded. Narrow scope (fewer files or less detail)."
   Otherwise: proceed.

DoD: <TARGET> validated, <ANGLES> normalized, <CONSTRAINTS> parsed, token check passed.

### AI-Specific Constraints

When `MODE=AI_VISION_IDEATION` is active, parse these constraint types in
addition to the base constraints:

Latency constraints:

- `inference_latency_p95: < 50ms | < 200ms | < 1s`
- `llm_call_timeout: < 2s | < 5s | < 10s`

Cost constraints:

- `token_budget_per_call: < 500 | < 2000 | < 10000`
- `llm_calls_per_session: < 1 | < 5 | < 20`

Data constraints:

- `training_data_volume: < 1k rows | < 10k | < 100k`
- `labeling_effort: none | low (< 1 hour) | medium (< 1 day) | high (> 1 day)`

Model constraints:

- `model_size: < 1MB | < 10MB | < 100MB`
- `model_type: sklearn_only | pytorch_allowed | llm_allowed`

Privacy constraints:

- `data_location: local_only | cloud_allowed_anonymized | cloud_allowed_full`
- `model_training: on_device | cloud_federated | cloud_centralized`

Explainability constraints:

- `decision_traceability: full | partial | none`
- `user_override: always | sometimes | never`

For `MODE=AI_VISION_IDEATION`, the default lenses become:
`UX`, `Pedagogy`, `Retention`, `ML_Feasibility`, `Data_Requirements`,
`Inference_Cost`, and `Explainability`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — CONTEXT LOAD (read-set, ≤ 2k tokens)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read (priority order, stop when hit token limit):

  1. doc/cjm.md
     - If <TARGET> is stage-based: read ONLY § Stage #N (30–50 lines)
       Include: Action/Touchpoint/Pain/Opportunity rows for that stage
     - If <TARGET> is pain-based: grep for keyword, read ≤ 100 lines context
     - Skip § narrative text and other stages

  2. doc/user_stories/ (if <TARGET> is US-based or relevant US exist)
     - Locate 1–2 US files mapped to <TARGET>
     - Read: title, value statement, acceptance criteria only
     - Skip: implementation details, technical notes

  3. doc/backlog_registry.yaml
     - Read ONLY entries tagged with <TARGET>'s CJM stage or US epic (grep/section read, ≤ 80 lines)
     - Look for: closed/deferred patterns, what's already been tried
     - Skip: full file or unrelated epochs

  4. app/<relevant_module>.py (if <TARGET> is feature-based)
     - Run: rg "^class\|^def " <file> — signatures only
     - Do NOT read full function bodies
     - Extract: method names, class structure, public API

Stop-condition: if read-set нарушает token budget канона [`_common_rules.md`](_common_rules.md), compress Phase 1 (drop lowest-signal file) or STOP.

Summary: Context loaded. Known pain points, user stories, and architecture context captured.
Proceed to Phase 2.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — BREAKTHROUGH IDEATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH lens in <ANGLES>:

  A. Identify world-class analogs:
     - Duolingo (learning, engagement, retention)
     - Anki (spaced repetition, card UX)
     - Khan Academy (pedagogy, scaffolding, assessment)
     - Quizlet (collaboration, gamification)
     - Notion AI (multi-modal, contextual help)
     - Others relevant to <TARGET>
     
     For each analog: name 1–2 specific UX/feature patterns

  B. Apply proven methods:
     - SM-2 (spaced repetition algorithm)
     - Retrieval practice (testing effect)
     - Interleaving (mixed practice order)
     - Gamification loops (progress, badges, leaderboards)
     - Hook Model (trigger → action → reward → investment)
     - Jobs-to-be-Done (user's functional + emotional job)
     - Kano model (basic/performance/delighter features)
     - North Star metric framing
     
     For each method: brainstorm 2–3 concrete scenarios for <TARGET>

  C. Generate ≥ (N_IDEAS / |<ANGLES>|) candidates per lens
     Each candidate = structured record:
     
       {
         title:          "1-line catchy name",
         user_value:     "Why does the user care? 1 line.",
         method_source:  "Duolingo (swipe-to-delete) / SM-2 algorithm / Hook Model",
                         (REQUIRED: must name real source, not invented)
         lens:           "UX | Pedagogy | Engagement | Accessibility | Monetization | Retention",
         effort:         "S | M | L",  (Small/Medium/Large)
         impact:         "Low | Med | High",  (user-visible improvement)
         risk:           "1-line risk (what could go wrong)",
         dependencies:   "list of <TARGET>-relative dependencies or 'none'",
         constraint_check: "✅ passes all <CONSTRAINTS> or 🚫 violates <CONSTRAINT_NAME>"
       }

     If MODE=AI_VISION_IDEATION, each candidate MUST also include:

       {
         ml_approach: {
           type: "lightweight_local | llm_enhanced | hybrid_rule_ml",
           model_size: "< 1MB | < 10MB | < 100MB | > 100MB",
           training_data: "user_local | synthetic | none (zero-shot)",
           inference_latency: "< 50ms | 50-200ms | > 200ms"
         },
         data_requirements: {
           min_samples: "<number or explicit none>",
           features: ["<feature list>"],
           labeling_effort: "none | low | medium | high"
         },
         evaluation_contract: {
           primary_metric: "<metric_name>",
           baseline: "<current_value or unknown>",
           target: "<target_value>",
           test_set: "<source>"
         }
       }

  Validation per candidate:
    - method_source MUST be attributable (not "creative idea")
    - If constraint_check = 🚫, mark idea but continue generating (rank lower later)
    - Impact + effort: not all high-impact low-effort (realistic tradeoffs)
    - If MODE=AI_VISION_IDEATION, reject or park ideas that violate local-first,
      latency, cost, privacy, model-size, or explainability constraints.

DoD: Generated ≥ N_IDEAS candidates total across all lenses.
     Each has method_source. Proceed to Phase 3.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — RANKING & TRIAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rank all candidates by score:

  score = (impact × cjm_criticality) / effort

  Where:
    impact ∈ {Low:1, Med:2, High:3}
    effort ∈ {S:1, M:2, L:3}
    cjm_criticality = 1.0 if <TARGET> is P0 moment (MoT #2, #5, #7, etc.)
                    = 0.7 if <TARGET> is P1 moment
                    = 0.4 if <TARGET> is P2 / feature area

  > ⚠️ **Единая формула.** Не использовать альтернативные множители (×3, ×5). Scores между артефактами должны быть сравнимы.
  > Каноническая ссылка: `doc/team_workflow/product_owner_router.md` § Scoring Formula.

Output ranking table:

  | Rank | ID | Title | Lens | Effort | Impact | Score | Constraint | Status |
  |------|----|----|------|--------|--------|-------|-------------|--------|
  | 1 | 01 | Swipe-to-skip | UX | S | High | 3.0 | ✅ | ✅ accept |
  | 2 | 02 | Peer huddles | Engagement | M | High | 1.5 | ✅ | ✅ accept |
  | 3 | 03 | AI hint on 3x fail | Pedagogy | M | Med | 1.0 | ✅ | ✅ accept |
  | 4 | 04 | Streak badges | Gamification | S | Med | 2.0 | ✅ | ✅ accept |
  | 5 | 05 | Dark mode | Accessibility | S | Low | 1.0 | ✅ | ✅ accept |
  | 6 | 06 | Premium hints | Monetization | M | Med | 0.7 | ✅ | 🅿️ parked |
  | ... | ... | ... | ... | ... | ... | ... | ... | ... |

Decision rule:
  - Top 5 (or default 50%-ile by score): ✅ accept → proceed to Phase 4 blocks
  - Remainder: 🅿️ parked → note reason (lower score, constraint violation, etc.)
  - If viable ideas < 3: STOP and report:
    "⚠ Insufficient viable ideas for <TARGET> (only N found). 
     Recommendation: broaden <ANGLES> or <CONSTRAINTS>, or refocus <TARGET>."

DoD: Ranking complete. ≥ 3 viable ideas identified. Proceed to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4 — DRAFT DIFFS (read-only artifact, DO NOT APPLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create ONE artifact file in archive/:

  PATH: archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md
  
  Example paths:
    - archive/ideation/stage7_course_learning_2026-04-26.md
    - archive/ideation/us14_3_retry_questions_2026-04-26.md
    - archive/ideation/pain_high_churn_retention_2026-04-26.md

File content structure (markdown):

━━ BLOCK 0: HEADER ━━
# Breakthrough Ideation: <TARGET>
**Date:** <YYYY-MM-DD>
**Focus:** <TARGET> (CJM / US / Pain / Feature)
**Lenses:** <ANGLES used>
**Ideas Generated:** <N>
**Viable (✅):** <count>
**Parked (🅿️):** <count>

━━ BLOCK 1: CONTEXT SUMMARY ━━
## Context

### Target
<Copy from Phase 1: what is <TARGET>, why it matters>

### Current State
<From CJM/US/backlog_registry: existing pain points, closed work, deferred items>

### Constraints Respected
<list of <CONSTRAINTS> or "none">

━━ BLOCK 2: RANKING TABLE ━━
## Ideas (Ranked)

Copy the ranking table from Phase 3, full detail.

━━ BLOCK 3: DIFFS FOR CJM.MD ━━
## Block 1: Suggested Additions to doc/cjm.md

Stage: <TARGET stage>

Copy-paste these into Stage § Action/Touchpoint/Pain/Opportunity section:

```markdown
| Type | Entry | Notes |
|------|-------|-------|
| Opportunity | <accepted idea #1 title as opportunity> | <user_value> |
| Opportunity | <accepted idea #2 title> | <user_value> |
| ...
```

(Format: copy existing rows from cjm.md for this stage, follow same structure)
(Review before pasting — this is a suggested edit, not auto-apply)

━━ BLOCK 4: DIFFS FOR USER_STORIES ━━
## Block 2: Suggested New User Stories for doc/user_stories/

For each accepted idea #1–#5, generate:

```yaml
---
us_id: <next-free-id-in-epic>    # e.g., if epic has us-14.1, us-14.2 → us-14.3
epic: <inferred-from-target>     # e.g., if Stage #7 → epic "Learning"
cjm_stage: <TARGET stage>
cjm_moment_name: "<name from cjm.md>"
status: proposed
priority: TBD
---

## <Idea Title>

**User Value:**
<user_value from idea>

**Acceptance Criteria:**
- [ ] <1st measurable criterion (e.g., "swipe gesture recognized 95% of time")>
- [ ] <2nd criterion>
- [ ] <3rd criterion or outcome>

**Related Idea:** <method_source> from <analog source>

**Notes:** <1-2 line explanation, if needed>
```

(Save each as doc/user_stories/us-<epic>.<number>.md)
(Example: doc/user_stories/us-learning.3.md)
(Review before creating — these are suggestions, not auto-apply)

━━ BLOCK 5: DIFFS FOR BACKLOG_REGISTRY.YAML ━━
## Block 3: Suggested New Packages for doc/backlog_registry.yaml

For each accepted idea, generate one row per table format:

```
Package | Status | CJM | Primary US | Owner | Notes
<pkg-id> | ready | <stage> | <us-id> | TBD | <title>: <user_value>
```

Examples:
```
E15-A | ready | #7 | us-learning.3 | TBD | Swipe-to-skip: faster interaction flow in course review
E15-B | ready | #7 | us-learning.4 | TBD | Peer huddles: social learning + motivation
E15-C | ready | #7 | us-learning.5 | TBD | AI hint escalation: guided practice without spoilers
```

(Apply these package entries to backlog_registry.yaml after review; sync — см. [**_common_rules.md** § Sync](_common_rules.md))

━━ BLOCK 6: EPOCH PROPOSAL (optional) ━━
## Block 4: Suggested New Epoch or Phase (if applicable)

If ≥ 3 accepted ideas AND cohesive theme:

```markdown
# e<N>_<slug>

**Title:** <Thematic title of breakthrough wave>

**Goal:** <1-2 sentences: what's the user journey transformation?>

**Entry Condition:** <From <TARGET>: when should this epoch start?>

**Phases:**

1. **Phase 1 — UX Foundations**
   Deliverables: <packages that set up base layer>
   
2. **Phase 2 — Engagement Layer**
   Deliverables: <packages that add motivation/social>
   
3. **Phase 3 — Pedagogy Integration**
   Deliverables: <packages that bind to learning outcomes>
   
4. **Phase 4 — Retention Mechanics**
   Deliverables: <packages that ensure habit formation>
   
5. **Phase 5 — Measurement & Iteration**
   Deliverables: <metrics + analysis packages>

**North Star Metric:** <1 metric that measures success of entire epoch>

**Exit Condition:** <when is this epoch "done"?>
```

(This is a proposal. File as new `doc/epochs/e<N>_<slug>.md` after review, or add as phase to existing epoch if relevant)

━━ END OF ARTIFACT ━━

IMPORTANT:
  - Do NOT edit cjm.md, user_stories/, backlog_registry.yaml, tasklist.md, or epochs/ directly
  - Save ONLY to archive/ideation/ artifact file
  - All blocks are formatted for copy-paste review + manual apply
  - Blocks 1–4 are always included; Block 5 (epoch) only if ≥3 ideas

DoD: Artifact file created at expected path.
     All blocks (1–4 or 1–5) present and formatted.
     Ready for user review.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5 — REVIEW HANDOFF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output to user (print to terminal):

**✅ Breakthrough Ideation Complete**

Artifact path: `archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md`

**Ideas Generated:** <N_total> total
  - ✅ Accepted (top 5 or 50%-ile): <N_accepted>
  - 🅿️  Parked (lower score / blocked): <N_parked>

**Top-N Table** (accepted ideas):

| Rank | Title | Effort | Impact | Score | Method Source |
|------|-------|--------|--------|-------|---|
| 1 | ... | S | High | 9.0 | Duolingo |
| 2 | ... | M | High | 6.0 | Hook Model |
| ... | ... | ... | ... | ... | ... |

**Open Questions:**
  - <1-2 risks or assumptions for review>
  - <Constraint violations, if any>

**Next Steps:**

1. **Review artifact:** Read blocks 1–4 in `archive/ideation/...`
   - Do the ideas match your vision?
   - Are method_sources credible?
   - Are constraints respected?

2. **Apply to docs (one of two paths):**
   
   **Path A — Manual:**
   Copy blocks 1–4 from artifact → paste into cjm.md / user_stories/ / backlog_registry.yaml manually, then run sync.
   Edit as needed. Commit when happy.
   
   **Path B — Automated (if N ≥ 3):**
   Run: `Прочитай doc/team_workflow/generate_orchestration_prompt.md`
   with TARGET_PACKAGE=<first-accepted-idea-id> to generate full orchestration.
   Orchestration will integrate artifact blocks into existing files.

3. **If changes needed:** Return to this prompt with refined <TARGET>, <N_IDEAS>, or <CONSTRAINTS>.

---

Artifact ready for review at: `archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md`
```

---

## RULES

- Read-set/token budget канона — [`_common_rules.md`](_common_rules.md). Дополнительно: **≤5 файлов** суммарно и укладываться по токенам по фазам ниже без нарушения канона.
- Write-set: **ONLY** `archive/ideation/<TARGET_SLUG>_<YYYY-MM-DD>.md`
  - Do NOT edit cjm.md, user_stories/, backlog_registry.yaml, tasklist.md, epochs/ directly
  - All proposed changes go into artifact blocks only
  
- Forbidden:
  - Creating files outside archive/ideation/
  - Directly applying diffs to product docs
  - Inventing method_sources (every idea must reference real analogs or proven methods)
  - Exceeding token budget (сверяйся с [`_common_rules.md`](_common_rules.md); при перегрузке Phase 1 — compress or STOP)
  
- If viable ideas < 3:
  - STOP immediately
  - Report: "⚠ Insufficient ideas. Reason: <constraint violations | scope too narrow | all ideas high-effort>."
  - Suggest: broaden <ANGLES> or relax <CONSTRAINTS>
  
- Every accepted idea must have:
  - explicit user_value (not "nice to have", but real pain/job addressed)
  - method_source (source must be attributable: product name, algorithm, framework)
  - effort estimate (must be realistic given team capacity)
  
- Respect <CONSTRAINTS>:
  - Each constraint checks during Phase 2 generation
  - Any idea violating constraint → marked 🚫 in ranking, sorted lower
  
- Token budget enforcement (совместимо с каноном [`_common_rules.md`](_common_rules.md)):
  - Phase 0–1: estimate ≤ 2k tokens
  - Phase 2–5: estimate ≤ 10k tokens
  - If total после Phase 1 угрожает превысить суммарный лимит (канон): abort and report blocker

---

## OUTPUT FORMAT (what the user sees)

After Phase 5, user receives:

1. **Artifact path** — clickable or copy-paste
2. **Ranking table** — top-N ideas with scores
3. **Open questions** — risks / assumptions for review
4. **Next steps** — Path A or B for applying changes
5. **Optional:** sample of Block 1 (cjm diffs) or Block 5 (epoch proposal) as preview

Example output:

```
✅ Breakthrough Ideation Complete

Artifact: archive/ideation/stage7_course_learning_2026-04-26.md

Ideas: 12 total (7 ✅, 5 🅿️ parked)

Top-5 Accepted:

| Rank | Title | Effort | Impact | Score | Source |
|------|-------|--------|--------|-------|--------|
| 1 | Swipe-to-skip | S | High | 9.0 | Duolingo |
| 2 | Peer huddles | M | High | 6.0 | Hook Model + Khan |
| 3 | AI hint on fail | M | Med | 4.0 | Retrieval Practice |
| 4 | Streak badges | S | Med | 3.0 | Gamification |
| 5 | Spaced review | M | Med | 2.8 | SM-2 |

Open: Will peer huddles work without instructor? (dependency check needed)

Next: Review artifact, then apply via Path A (manual) or Path B (orchestration).
```

---

## USAGE SCENARIOS

### Сценарий 1: Stage #7 — Course Learning Mode (Engagement Focus)

**Inputs:**
```
TARGET: Stage #7: Course Learning Mode
N_IDEAS: 10
ANGLES: Engagement, Pedagogy, UX
```

**Expected Output:**
- 10+ ideas focused on keeping learners in course without skipping
- Sources: Duolingo (streaks), Anki (review scheduling), Khan (scaffolding)
- Artifact: archive/ideation/stage7_course_learning_2026-04-26.md
- Top ideas: swipe interactions, spaced review, peer feedback loops

**Next:** Apply to backlog_registry.yaml as wave (E15-A/B/C), sync tasklist.md, or fold into existing epoch

---

### Сценарий 2: US 14.3 — Retry Failed Questions (UX + Pedagogy)

**Inputs:**
```
TARGET: US 14.3
N_IDEAS: 7
ANGLES: UX, Pedagogy, Accessibility
CONSTRAINTS: cannot break existing quiz format
```

**Expected Output:**
- 7 ideas for better retry UX (hints, scaffolding, alternative questions)
- Sources: Khan Academy (hint escalation), SM-2 (spacing), retrieval practice
- Artifact: archive/ideation/us14_3_retry_2026-04-26.md
- Top ideas: AI hints on 3rd attempt, variant questions, learning summary before retry

**Next:** Map to new US in learning epic, create packages

---

### Сценарий 3: Pain Point — High Churn in Retention Stage (All Lenses)

**Inputs:**
```
TARGET: pain point: learners drop out after first week in Retain stage
N_IDEAS: 10
ANGLES: (all)
```

**Expected Output:**
- 10 ideas across engagement, pedagogy, monetization, retention
- Sources: Duolingo (notifications + challenges), Notion (community), Quizlet (social)
- Artifact: archive/ideation/pain_high_churn_retention_2026-04-26.md
- Top ideas: streak mechanics, cohort challenges, instructor nudges, retention alerts

**Next:** Large multi-wave initiative → propose new epoch (e.g., e16_retention_turnaround)

---

### Сценарий 4: US 20.1 — [Smart Study Router](../smart_study_router.md) (Next-Best Study Action)

**Inputs:**
```
TARGET: US-20.1: Smart Study Router / умная подсказка следующего учебного шага
N_IDEAS: 10
ANGLES: UX, Pedagogy, Retention, Accessibility
CONSTRAINTS: must preserve local-first; must explain why action was chosen; cannot hide existing tutor/quiz/flashcard/dashboard entry points
```

**Expected Output:**
- 10+ ideas for `learning state -> next_action + reason + primary button`
- Sources: Duolingo (next lesson / streak recovery), Khan Academy (mastery practice), Anki (due review), JTBD / Hook Model / Retrieval Practice
- Artifact: `archive/ideation/us20_1_smart_study_router_<YYYY-MM-DD>.md`
- Top ideas: explainable next step card, weak-concept recovery router, due-review priority, post-answer "learn this" runway, dashboard next-action diff

**Next:** Review artifact, select 1–3 ideas, then package via `product_owner_plan_package_prompt.md`.

---

## RELATED FILES

- [`doc/cjm.md`](../cjm.md) — customer journey map with pain points
- [`doc/user_stories.md`](../user_stories.md) — index of user stories
- [`doc/user_stories/README.md`](../user_stories/README.md) — каталог историй (`us-*.md`)
- [`doc/backlog_registry.yaml`](../backlog_registry.yaml) — active backlog and wave queue SSoT
- [`doc/tasklist.md`](../tasklist.md) — generated weekly view
- [`doc/epochs/e29.md`](../epochs/e29.md) — пример файла эпохи (`doc/epochs/*.md`)
- [`archive/ideation/`](../../archive/ideation/) — каталог артефактов ideation
- [`generate_plan_next_prompt.md`](./generate_plan_next_prompt.md) — for planning next package when backlog is empty
- [`workflow_router.md`](./workflow_router.md) — единая точка входа: `python scripts/workflow.py` определяет следующий шаг автоматически
- [`generate_orchestration_prompt.md`](./generate_orchestration_prompt.md) — for full team workflow after artifact review
- [`designer.md`](./designer.md) — for designing UI/UX contract for known package
