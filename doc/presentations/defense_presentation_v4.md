# home-rag_v2 — персональный AI-тьютор на ваших материалах

## От поиска по документам к полному учебному циклу (local-first)

> **Проект:** home-rag_v2 · Персональный учебный ассистент на основе ваших материалов
> **Дата:** июнь 2026
> **Формат:** 16 слайдов · Markdown-презентация
> **Версия:** 4.1 — компиляция v1–v3 + актуальные достижения + local dev trigger

![От разрозненных документов к структурированным знаниям](../screenshots/mastery_engine/from_documents_to_deep_knowledge.png)

---

## Главный тезис

> **home-rag_v2 — это не только Q&A по документам.**
> Это инструмент, который ведёт пользователя по всему учебному циклу:
> вопрос → объяснение → проверка → запоминание → план — с опорой на ваши
> собственные материалы и возможностью работать полностью локально.

Ключевые свойства:

- **Local-first** — может работать без облака; данные остаются на машине пользователя
- **Полный цикл** — от ответа до интервального повторения в одном инструменте
- **Управляемость** — система предлагает следующий шаг, а не оставляет пользователя перед пустым чатом

---

## Слайд 1 — Достижения последнего спринта (июнь 2026)

![Overlay завершения темы после достижения mastery](../screenshots/2026-06-20/scenario_29/02_celebration_overlay.png)

### Что сделано

| Достижение | Результат | Дата |
|---|---|---|
| Новая локальная модель | `qwopus3.6-35B-A3B-MTP` на llama.cpp: rank 99.55, ~185 ток/с, quality 11.5/11.5, RAG-smoke PASS | 2026-06-20 |
| Golden E2E graduation | Сквозной путь папка → курс → graduation; в тесте `fallback_used=false` (6/6 course loop, 18/18 smoke) | 2026-06-10 |
| Course Graph Evidence | Граф концептов с типизированными связями и provenance до chunk'ов; включение graph-aware retrieval только при измеримом uplift | 2026-06-11 |
| Flashcard → Tutor fast-path | Маршрут «Не знаю / Объясни» по быстрому RAG-пути с честным разделением latency | 2026-06-20 |
| Grounding / Abstain Contract | Каждый факт привязан к источнику; при слабом контексте — отказ от ответа вместо догадки | 2026-06 |

### Состояние проекта (снимок 2026-06-20)

**92 волны · 249 пакетов (241 закрыт) · 87/87 User Stories · 13/13 моментов истины CJM · 2 995 тест-функций.** Активных открытых пакетов нет; очередь — кандидаты в статусе `proposed`.

---

## Слайд 2 — Проблема и решение

### Проблема: куча документов → ценность?

| Что хочется | Что происходит сейчас |
|---|---|
| Быстро найти ответ по своим материалам | ChatGPT не знает ваших документов |
| Разобраться в сложной теме | Поиск по файлам даёт фрагменты без контекста |
| Запомнить надолго | Ручные Anki-карточки — долго и рутинно |
| Видеть прогресс | Непонятно, что освоено, а что нет |

**Следствие:** переключение между несколькими инструментами и потеря контекста.

### Решение: один инструмент, полный цикл, local-first

```
Документы → Q&A → Тьютор → Квиз → Карточки → Mastery → Graduation
                                                  ↑
                                       Smart Study Router
                                    (подсказка следующего шага)
```

![Быстрый ответ с оценкой confidence и источниками](../screenshots/2026-06-20/scenario_01/03_quick_answer_with_sources.png)

---

## Слайд 3 — Полный учебный цикл

> В типичной RAG-системе сценарий заканчивается на ответе. Здесь ответ — это первый шаг цикла.

| Шаг | Что делает система | Скриншот-доказательство |
|---|---|---|
| 1. Ответ | RAG-ответ + оценка confidence + источники | confidence-чип, 3 источника |
| 2. Тьютор | Объяснение и наводящие вопросы вместо лекции | план разбора темы из 3 шагов |
| 3. Квиз | Проверка понимания, а не только прочтения | feedback + подсказка |
| 4. Карточка | Перенос важного в SM-2 карточку без копипасты | preview карточек |
| 5. Повторение | Интервальное повторение, мягкое восстановление после пропуска | очередь «осталось ~4 мин» |
| 6. Mastery | recognition → recall → transfer → graduation | mastery timeline за 7 дней |

![Tutor: переход из Q&A с сохранением контекста темы](../screenshots/2026-06-20/scenario_03/02_tutor_context_handoff.png)

**Идея:** не отдельный «RAG-чат» и не отдельная «SRS-система», а связка источник → объяснение → проверка → запоминание → план.

---

## Слайд 4 — Архитектура и стек

### Четыре слоя системы

```
┌─────────────────────────────────────────────────────────┐
│  UI         Streamlit · 5 экранов · Mission Control      │
├─────────────────────────────────────────────────────────┤
│  API        FastAPI · 93 endpoint · типизированные модели│
├─────────────────────────────────────────────────────────┤
│  Services   RAG · Tutor · SSR · Flashcards · Graph       │
├─────────────────────────────────────────────────────────┤
│  Storage    SQLite (10+ таблиц) · ChromaDB · BM25        │
└─────────────────────────────────────────────────────────┘
        LLM-слой: llama.cpp / LM Studio (local) ↔ Cloud
```

**Tech stack:** FastAPI · Streamlit · SQLite · ChromaDB · LangChain · llama.cpp / OpenAI-совместимый API.

### Ключевые архитектурные решения

- **Modular service layer** — бизнес-логика отделена от API/UI; крупные модули разбиты на сервисы
- **Типизированные контракты** (`QueryContext`, `QueryResponse`) — снижают риск рассинхрона payload'ов
- **Config через env** — переключение Local ↔ Cloud без изменения кода
- **23 ADR** — значимые решения задокументированы

---

## Слайд 5 — RAG: ядро системы

### 5-ступенчатый pipeline

```
Запрос → Classify → Rewrite → Retrieve → Rerank → Generate → Ответ
                                  │                    │
                          hybrid (BM25 + vector)  grounded + citations
                                  │
                          Self-Correction Loop (retry при слабом контексте)
```

### Что заложено в RAG

- **Гибридный поиск** — BM25 + векторный
- **Двухуровневая индексация** — Document-level + Chunk-level под разные типы запросов
- **Профили** (ADR-021) — `fast` / `quality` / `graph_aware`, выбор под задачу
- **Заземление** — каждый тезис с inline-цитатой `[N]`; при слабом контексте — отказ от ответа

**Измерено** (retrieval-only eval, demo-набор из 15 вопросов): recall@3 ≈ **86–87 %** (hybrid) против 80 % (vector-only), средняя retrieve-латентность ≈ **0.57 с**.

![Источники с именами файлов и match-score](../screenshots/2026-06-20/scenario_08/02_three_sources_listed.png)

---

## Слайд 6 — Smart Study Router и AI Vision L1–L5

### Проблема: «много режимов — что делать дальше?»

Система предлагает следующий шаг с объяснением «почему сейчас» и безопасными альтернативами, вместо того чтобы оставлять выбор полностью на пользователе.

### Пять уровней (инженерно доставлены; часть serving — за gate'ами по данным)

| Уровень | Что добавляет | Статус |
|---|---|---|
| L1 — локальная память | ML forgetting curve, reranking (целевой AUC-ROC ≥ 0.75) | доставлен; serving после ≥1000 real samples |
| L2 — объяснения | LLM-объяснения с semantic caching (целевой p95 < 2 с) | доставлен |
| L3 — недельный план | Rule-based weekly planner + telemetry | доставлен |
| L4 — граф prerequisites | Prerequisite-aware routing | доставлен (за feature-flag) |
| L5 — обучение на отказах | Misroute policy learning (offline, с decay) | доставлен |

![AI Vision: уровни 3–4 — недельный план и граф prerequisites](../screenshots/2026-06-20/scenario_22/03_levels_3_4_planner_graph.png)

---

## Слайд 7 — Course Graph Evidence

> Раньше «Graph DNA» строился как filename-fallback (узлы без семантических связей). Эта волна сделала граф evidence-backed.

### Что доставлено (волна закрыта 2026-06-11)

- **Course Graph Compiler** — нормализованный граф концептов с типизированными связями и provenance до конкретных chunk'ов
- **Relation UX** — типы связей, confidence и source-evidence в UI; `precedes` отличается от prerequisite; pending-граф не выдаётся за готовый
- **Uplift Gate** — graph-aware retrieval включается только при измеримом uplift против hybrid-baseline; при отсутствии uplift профиль демотируется

### Защитные правила (kill-switches)

filename-fallback, выдаваемый за semantic-ready · связь без evidence · curriculum-order, выдаваемый за prerequisite · graph-aware без uplift-gate · скрытый cloud-вызов в extraction — каждое блокирует поставку.

![Персональный подграф знаний с mastery](../screenshots/2026-06-20/scenario_26/03_subgraph_mastery.png)

---

## Слайд 8 — Локальная модель: qwopus3.6-35B на llama.cpp

### Benchmark 2026-06-20 (pack v1.8): 3 кандидата, 8 задач + real RAG-smoke

| Модель | rank | ток/с | quality | RAG smoke |
|---|---|---|---|---|
| qwopus3.6-35B-A3B-MTP | 99.55 | ~185 | 11.5/11.5 | PASS |
| qwopus3.6-27B-v2-MTP | 93.55 | ~46 | 11.5/11.5 | — |
| qwen3.6-27B | 93.21 | ~43 | 11.5/11.5 | — |

Принятая модель примерно **в 4 раза быстрее** предыдущих кандидатов при сопоставимом качестве (≈185 против ≈43–46 ток/с).

### Local vs Cloud — выбор за пользователем, без изменения кода

| Критерий | Local (llama.cpp) | Cloud |
|---|---|---|
| Приватность | данные на машине пользователя | данные уходят провайдеру |
| Стоимость API | 0 ₽ | зависит от провайдера |
| Переключение | `switch_local_llm.ps1` / `.env` | то же |

> Эволюция: `qwen/qwen3.6-27b` (LM Studio, ADR-024) → `qwopus3.6-35B` (llama.cpp) — смена модели и backend без переписывания кода.

---

## Слайд 9 — Доверие и заземление (Grounding Contract)

> Цель — чтобы каждый тезис ответа опирался на конкретный фрагмент источника.

### Механизмы

- **Inline-цитаты `[N]`** — факт ссылается на фрагмент контекста
- **Provenance ledger** — машинно-проверяемая связь факт → источник → chunk
- **Honest abstain** — при слабом контексте система отказывается от ответа, а не достраивает его
- **Over-/under-citation tolerance** — лишние или недостающие ссылки локальной модели не ломают валидный ответ и не маскируют пробелы
- **Confidence-оценка** — пользователю видно, насколько ответ обоснован

### Трёхслойная оценка качества

```
Deterministic checks  →  LLM-as-Judge  →  Human Feedback
   (быстро, дёшево)      (faithfulness)    (реальная польза)
```

Дополнительно — RAGAS-метрики (context_precision@k, answer_correctness) поверх существующего eval-harness. Faithfulness-прогон с LLM выполняется отдельно (методика готова).

![Раскрытые источники: тезисы подкреплены фрагментами](../screenshots/2026-06-20/scenario_01/04_sources_expanded.png)

---

## Слайд 10 — AI-assisted разработка

### Было → стало

| | Было | Стало |
|---|---|---|
| Конвейер | ручные переключения между шагами | router + SDK-trigger автоматизируют рутину |
| Запуск | копировать промпты вручную | принят контракт → дальнейшие шаги по скрипту |
| Контроль | ручная проверка | DoD проверяется автоматически |
| Следующий шаг | искать самому | стартует по очереди из реестра |

```powershell
python scripts/workflow.py --loop --skip-review --watch-contract \
    --trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts" --agent cursor_ai
```

### Принцип: «документ — закон, скрипт — движок, агент — руль»

- **Token-safety registry** — предсказуемый бюджет контекста для каждого LLM-вызова
- **Autonomous control plane** — durable run_id, policy-driven решения, observability
- **Командный конвейер** — PO → Analyst → Architect → Dev → Tester как воспроизводимый процесс

> Результат: меньше ручной координации, разработчик сосредоточен на решениях, а не на оркестрации.

---

## Слайд 11 — Локальная разработка: qwen3-coder-next как patch executor

> Прорыв 2026-06-21: локальная модель перестала быть «чатом рядом с IDE» и
> стала controlled executor в реальном trigger path.

### Железо и сервер

| Слой | Значение |
|---|---|
| Модель | `qwen/qwen3-coder-next` |
| Сервер | llama.cpp OpenAI-compatible API `http://127.0.0.1:8080/v1` |
| Профиль | AutoFit, `ctx=32768`, `parallel=1`, KV `q8_0/q8_0`, reasoning off |
| Железо | 2× RTX 5070 Ti 16GB; fixed GPU split отключён |

### Trigger как компилятор патчей

```
current_task.md
  → read-set context injection
  → fenced diff from model
  → WRITE_SET gate
  → hunk normalization
  → git apply --check/apply
  → targeted tests
  → execution_contract.md from evidence
```

### Live smoke evidence

| Gate | Result |
|---|---|
| `/v1/models` alias | PASS: `qwen/qwen3-coder-next`, `n_ctx=32768` |
| Disposable repo patch | PASS: `app/math_utils.py`, `WRITE_SET=["app/math_utils.py"]` |
| Tests | PASS: `2 passed` |
| Metrics | `hunk_count_normalized=true`, `recount_used=false`, `adapter_fallback_used=false`, `context_chars=918` |

> Следующий шаг: первая реальная low-risk задача в репозитории, например
> метрики `context_files_count` / `context_truncated` для самого trigger.

---

## Слайд 12 — Метрики (воспроизводимые числа)

| Метрика | Значение | Источник |
|---|---|---|
| User Stories закрыто | 87 / 87 | `user_stories_index.json` |
| CJM моменты истины | 13 / 13 | `cjm.md` |
| Волн завершено | 92 | `backlog_registry.yaml` |
| Пакетов (закрыто / всего) | 241 / 249 | `backlog_registry.yaml` |
| Тест-функций pytest | 2 995 (323 файла) | `grep "def test_"` |
| FastAPI endpoints | 93 | `app/routers/` |
| Architecture Decision Records | 23 | `adr.md` |
| Retrieval recall@3 (hybrid, demo-набор) | ≈ 86–87 % · latency ≈ 0.57 с | `eval/` |
| Local LLM throughput | ≈ 185 ток/с (qwopus35B) | benchmark 2026-06-20 |
| Local coding trigger | live smoke PASS (`qwen3-coder-next`, n_ctx=32768) | `llamacpp_agent_trigger.ts`, 2026-06-21 |
| Golden E2E graduation | 6/6 loop · 18/18 smoke · fallback_used=false | session tape |

> Числа воспроизводимы из репозитория и логов. Часть eval-метрик получена на demo-наборе и помечена соответственно.

---

## Слайд 13 — Конкурентный анализ

*Анализ выполнен AI-assisted (Claude): матрица по критериям → gap-анализ → позиционирование.*

| Критерий | home-rag | NotebookLM | Anki | ChatGPT+Files | Obsidian |
|---|---|---|---|---|---|
| Q&A по документам | RAG + источники | ✅ | ❌ | ✅ | частично |
| Автоквизы из ответов | ✅ | ❌ | ручные | ❌ | ❌ |
| SM-2 карточки | авто | ❌ | сильнейший | ❌ | частично |
| Mastery tracking | 3 уровня | ❌ | базово | ❌ | ❌ |
| AI-тьютор | ✅ | ❌ | ❌ | ручной | ❌ |
| Подсказка следующего шага | ✅ | ❌ | ❌ | ❌ | ❌ |
| Evidence-backed граф | ✅ | частично | ❌ | ❌ | ручной |
| Local-first | ✅ | cloud | ✅ | cloud | ✅ |
| Стоимость | 0 ₽ (local) | бесплатно | бесплатно | $20/мес | бесплатно |

> Сильная сторона home-rag — закрытие полного учебного цикла локально в одном инструменте. Перечисленные продукты сильны в отдельных частях цикла.

---

## Слайд 14 — Дорожная карта

### Закрыто (фундамент)

Localhost Delight loop · SSR AI Vision L1–L5 · Course Graph Evidence · Grounding Contract · Flashcard fast-path · Golden E2E graduation · Local llama.cpp coding trigger smoke.

### Очередь кандидатов (`proposed`)

| Направление | Пакет | Ценность |
|---|---|---|
| Measurement loop | `ragas-langfuse-dataset-v1` | Метрики качества + трассировка прогонов |
| Smart Notes | `smart-notes-native-generation-v1` | Авто-конспект из материалов |
| PII masking | `redaction-sink-coverage-v1` | Маскирование чувствительных данных |
| Advanced RAG | `multi-query-expansion-v1` | Multi-query expansion + rerank |
| Skills Platform | `workflow-skills-thin-adapter-v1` | Тонкие skill-адаптеры workflow |
| Local Code Executor | first real low-risk trigger task | Метрики context packaging и безопасный rollout llama.cpp trigger |

### Дальний горизонт

Desktop installer (снижение порога входа) · SSR serving promotion (после накопления real samples) · Learning Outcomes research · collaborative learning.

---

## Слайд 15 — Демо: «от вопроса до mastery за ~3 минуты»

| Время | Действие | Реплика |
|---:|---|---|
| 0:00 | Папка с обычными материалами + готовый индекс | «Это локальные конспекты, не размеченная база.» |
| 0:30 | Сложный вопрос (синтез из нескольких фрагментов) | «Нужен синтез, а не одно определение.» |
| 0:55 | Ответ + citations + confidence | «Видно, на чём стоит ответ, и можно проверить.» |
| 1:20 | «Учить эту тему» | «У многих RAG здесь конец, тут — переход в обучение.» |
| 1:45 | 1–2 шага tutor + quiz | «Проверяется понимание, а не формулировка.» |
| 2:25 | Создать flashcard | «Важное → карточка без копипасты.» |
| 2:45 | Mastery dashboard + adaptive plan | «Система обновляет модель знания и предлагает шаг.» |

**Демо-вопрос:**
> «Почему RAG-ответ сам по себе недостаточен для обучения, и как связка tutor → quiz → flashcards → mastery plan закрывает этот разрыв? Укажи, какие части ответа подтверждаются источниками.»

Полный сценарий: [`defense_killer_demo.md`](defense_killer_demo.md) · демо-гифы: `../screenshots/2026-06-20/`

---

## Слайд 16 — Итоги

![Progress rail учебного цикла на главном экране](../screenshots/2026-06-20/scenario_29/01_delight_progress_rail.png)

> **home-rag_v2 — персональная система обучения**, которая знает ваши материалы,
> отслеживает прогресс и предлагает следующий шаг — от первого вопроса до graduation,
> с возможностью работать полностью локально.

### Три довода

1. **Полный цикл** — источник → объяснение → проверка → запоминание → план → graduation в одном инструменте
2. **Подкреплено числами** — 87/87 US, 13/13 MoT, 2 995 тест-функций, 92 закрытых волны, Golden E2E с `fallback_used=false`
3. **Local-first** — ≈185 ток/с на qwopus35B, 0 ₽ за API, данные на машине пользователя

**Local-first. Open-source. Полный цикл. AI-assisted.**

---

<sub>Подготовлено для защиты проектной работы · июнь 2026 · Версия 4.1 · компиляция v1–v3 + актуальные достижения + local dev trigger</sub>
