# ADR По RAG-Архитектуре

Статус: `ADR`
Роль: расширение ADR по RAG-пайплайну и смежным архитектурным решениям.
Значительная часть записей в этом документе имеет статус `Proposed`; не воспринимать их как описание уже реализованного runtime.

> Этот документ дополняет `adr.md` (ADR-001–009) решениями уровня RAG pipeline: 
> как именно устроены retrieval, synthesis, ingestion, evaluation, и почему именно так.

---

## Реестр

| ADR | Название | Статус | Дата | Зависит от |
|-----|---------|--------|------|------------|
| [010](#adr-010) | Query Processing Pipeline: 5-ступенчатый контур | Proposed | 2026-03 | 004, 006, 007 |
| [011](#adr-011) | Двухуровневая индексация: Document + Chunk | Proposed | 2026-03 | 002, 008 |
| [012](#adr-012) | Multi-Prompt Architecture: промпт как функция типа запроса | Proposed | 2026-03 | 004, 006, 010 |
| [013](#adr-013) | Evaluation Strategy: трёхслойная модель оценки | Proposed | 2026-03 | 003, 005 |
| [014](#adr-014) | Self-Correction Loop: Corrective RAG | Proposed | 2026-03 | 007, 010, 013 |
| [015](#adr-015) | Knowledge Graph: облегчённый граф концепций | Proposed | 2026-03 | 008, 009, 011 |

---

<a id="adr-010"></a>
## ADR-010: Query Processing Pipeline — 5-ступенчатый контур

**Статус:** Proposed  
**Дата:** 2026-03  
**Итерации:** 10–13  
**Зависит от:** ADR-004 (pipeline factory), ADR-006 (переход к KM RAG), ADR-007 (hybrid retrieval)

### Контекст

Текущий pipeline — двухступенчатый:

```
Вопрос → [Retrieve (vector)] → [Synthesize (LLM)] → Ответ
```

Это работает для простых точечных вопросов, но даёт плохие результаты на:
- Нечётких запросах («а что там про безопасность?») — embedding запроса неинформативен.
- Keyword-запросах («HDBSCAN», «RFC-2024-003») — vector search пропускает точные совпадения.
- Обзорных запросах («Составь конспект по теме RAG») — chunk-level retrieval не видит документы целиком.
- Follow-up вопросах («А что ещё?») — нет контекста предыдущего диалога.

Лекция по RAG описывает Production RAG Pipeline: Router → Query Rewriter → Hybrid Retriever → Reranker → LLM + Critic → Cache. Нужно спроектировать целевую архитектуру и путь к ней.

### Целевая архитектура: 5 ступеней

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUERY PROCESSING PIPELINE                   │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ 1.CLASSIFY│──▶│2.REWRITE │──▶│3.RETRIEVE│──▶│4.RERANK  │    │
│  │  Router   │   │ Enricher │   │  Hybrid  │   │ + Filter │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       │                              │              │           │
│       │ тип запроса            BM25 + Vector    Cross-encoder   │
│       │ → промпт               + Doc-level      + Metadata     │
│       │ → стратегия                              replacement    │
│       │                                               │         │
│       │              ┌──────────┐                     │         │
│       └─────────────▶│5.GENERATE│◀────────────────────┘         │
│                      │ Synthesize│                               │
│                      └──────────┘                               │
│                           │                                     │
│                    prompt(type) + context → LLM → ответ         │
└─────────────────────────────────────────────────────────────────┘
```

**Ступень 1: Classify (Router).** Определяет тип запроса и выбирает стратегию для всех последующих ступеней. Типы: `qa` (точечный вопрос), `overview` (обзор темы), `synthesis` (конспект), `learning_plan` (план обучения), `keyword` (точный поиск).

**Ступень 2: Rewrite (Enricher).** Преобразует запрос пользователя в оптимальный search query. Для `qa` — переформулировка в самодостаточный вопрос. Для `overview`/`synthesis` — генерация подвопросов (SubQuestionQueryEngine). Для `keyword` — пропуск (pass-through). Для follow-up — condensing с учётом истории.

**Ступень 3: Retrieve (Hybrid).** BM25 + Vector Search + Reciprocal Rank Fusion. Для `overview`/`synthesis` — двухуровневый: сначала документы (по summaries), затем чанки внутри выбранных документов. Для `qa`/`keyword` — одноуровневый chunk-level.

**Ступень 4: Rerank + Filter.** Cross-encoder reranker (FlagEmbeddingReranker) + MetadataReplacementPostProcessor (sentence window) + metadata-фильтры (folder, file). Для `synthesis` — сортировка по документам, а не по скору.

**Ступень 5: Generate (Synthesize).** LLM-вызов с промптом, выбранным ступенью 1. Для `qa` — краткий ответ. Для `synthesis` — структурированный конспект. Для `learning_plan` — план с порядком изучения.

### Альтернативы

**A. Монолитный pipeline с if-else по типу запроса**
- Плюсы: простота, всё в одном модуле.
- Минусы: pipeline_factory превращается в God Module. Каждый новый тип запроса — это ещё один if/else во всех 5 ступенях. Невозможно тестировать ступени независимо.
- Почему отклонён: нарушает Single Responsibility и не масштабируется.

**B. Композируемый pipeline: каждая ступень — отдельный модуль с единым интерфейсом**
- Плюсы: ступени независимы, тестируемы, заменяемы. Router выбирает конфигурацию ступеней, а не код внутри каждой ступени.
- Минусы: больше модулей, сложнее trace/debug.

**C. Agentic pipeline (ReAct loop)**
- Плюсы: максимальная гибкость — агент сам решает, какую ступень вызвать следующей.
- Минусы: недетерминированность (один и тот же запрос может обрабатываться по-разному), сложная отладка, высокая стоимость (каждое «размышление» агента — LLM-вызов).
- Почему отклонён на текущем этапе: для learning_plan (итерация 17) может потребоваться, но для основных сценариев детерминированный pipeline надёжнее.

### Предлагаемое решение

**Вариант B — композируемый pipeline.** Каждая ступень реализуется как модуль с функцией `process(query_context) → query_context`. Router собирает конфигурацию ступеней на основе типа запроса.

Реализация через расширение `pipeline_factory.py`:

```python
# Концептуальная схема (не финальный код)
PIPELINE_CONFIGS = {
    "qa":            [classify, rewrite_qa, retrieve_hybrid_chunks, rerank, generate_qa],
    "overview":      [classify, rewrite_overview, retrieve_doc_level, rerank, generate_overview],
    "synthesis":     [classify, rewrite_sub_questions, retrieve_two_level, rerank_by_doc, generate_synthesis],
    "learning_plan": [classify, rewrite_plan, retrieve_two_level, rerank_by_doc, generate_plan],
    "keyword":       [classify, passthrough, retrieve_bm25_only, no_rerank, generate_qa],
}
```

### Latency Budget

| Ступень | Целевой latency | Источник latency |
|---------|----------------|-----------------|
| 1. Classify | ≤500 ms | 1 LLM-вызов (cheap model) |
| 2. Rewrite | ≤800 ms | 1 LLM-вызов (cheap model) |
| 3. Retrieve | ≤300 ms | BM25 (in-memory) + Chroma (disk) + fusion |
| 4. Rerank | ≤400 ms | Cross-encoder inference (CPU) |
| 5. Generate | ≤3000 ms | 1 LLM-вызов (main model) |
| **Total (qa)** | **≤5000 ms** | |
| **Total (synthesis)** | **≤8000 ms** | Больше чанков → длиннее generate |

Текущий pipeline (retrieve + generate): ~3000–5000 ms. Целевой добавляет ~1300 ms на classify + rewrite. Допустимо для interactive use case.

### Cost Budget (per query, OpenRouter pricing)

| Ступень | Модель | ~Tokens | ~Стоимость |
|---------|--------|---------|-----------|
| Classify | gpt-4o-mini / cheap | ~200 in + 50 out | $0.0001 |
| Rewrite | gpt-4o-mini / cheap | ~300 in + 100 out | $0.0002 |
| Generate (qa) | gpt-4o / main | ~2000 in + 500 out | $0.01 |
| Generate (synthesis) | gpt-4o / main | ~8000 in + 2000 out | $0.04 |
| **Total (qa)** | | | **~$0.01** |
| **Total (synthesis)** | | | **~$0.04** |

Текущий pipeline: ~$0.008 per query. Целевой добавляет ~$0.0003 на cheap ступени. Рост менее 5% для qa, основной overhead — в synthesis (больше контекста в generate).

### Стратегия поэтапного внедрения

```
Сейчас:     Retrieve(vector) → Generate(qa_prompt)

Итерация 10: Retrieve(hybrid) → Rerank → Generate(qa_prompt)

Итерация 12: Rewrite → Retrieve(hybrid) → Rerank → Generate(qa_prompt)
             + Classify(prepare router signals)

Итерация 13: Classify → Rewrite → Retrieve(hybrid|two_level) → Rerank → Generate(prompt_by_type)

Итерация 17: Classify → [if learning_plan: Agentic sub-pipeline]
             → Rewrite → Retrieve → Rerank → Generate
```

На каждом шаге pipeline обратно-совместим: `qa` тип обрабатывается тем же путём, что и раньше, только с дополнительными ступенями.

### Критерии принятия

1. qa latency ≤ 5 секунд (p95) после добавления classify + rewrite.
2. synthesis latency ≤ 10 секунд (p95).
3. Eval: keyword-вопросы — улучшение ≥15% (context recall) после hybrid retrieval.
4. Eval: обзорные вопросы — faithfulness ≥ 0.8 после двухуровневого retrieval.
5. Каждая ступень может быть отключена через конфиг (`ENABLE_REWRITE=false`).

### Риски

| Риск | Вероятность | Импакт | Митигация |
|------|------------|--------|-----------|
| Classify ошибается в типе → неправильный промпт → плохой ответ | Средняя | Высокий | Fallback: при неуверенной классификации → qa (самый безопасный тип) |
| Rewrite искажает intent → retrieval по неправильному запросу | Средняя | Высокий | Debug: отображать rewritten query в ответе. Конфиг: отключаемый rewrite |
| 5 ступеней → сложный debug | Высокая | Средний | Structured logging каждой ступени. Debug endpoint `/pipeline/trace` |
| Стоимость synthesis запросов ×4 от qa | Низкая | Средний | Дешёвые модели для classify/rewrite. Rate limit на synthesis |

### Последствия

**Положительные:**
- Каждый тип запроса обрабатывается оптимальной стратегией. «Составь конспект» больше не обрабатывается как точечный Q&A.
- Поэтапное внедрение: на каждом этапе pipeline рабочий и измеримо лучше предыдущего.
- Ступени независимы: можно заменить BM25 на SPLADE, или FlagEmbeddingReranker на Cohere, изменив один модуль.

**Отрицательные:**
- Архитектурная сложность: от 2 модулей (retrieval + query_service) до 7+ (classifier, rewriter, hybrid_retriever, doc_retriever, reranker, synthesizer, router).
- Debugging требует трассировки всего pipeline. Без structured logging — невозможно понять, на какой ступени ошибка.
- pipeline_factory.py в текущем виде не поддерживает эту архитектуру — потребуется рефакторинг или замена на pipeline runner.

---

<a id="adr-011"></a>
## ADR-011: Двухуровневая индексация — Document + Chunk

**Статус:** Proposed  
**Дата:** 2026-03  
**Итерация:** 11  
**Зависит от:** ADR-002 (Chroma), ADR-008 (document summaries)

### Контекст

Текущая индексация создаёт один уровень: документ → чанки (ноды) → embeddings в Chroma. Retrieval ищет по чанкам.

Это создаёт две проблемы:

**Проблема 1: «Какие лекции покрывают тему X?»** — вопрос уровня документов, а не чанков. Chunk-level retrieval возвращает 5 фрагментов из, возможно, 5 разных документов — но не может сказать, какие документы целиком релевантны.

**Проблема 2: Topic clustering по чанкам — шумный.** 700-символьный чанк может содержать часть одной темы и часть другой. Кластеризация на уровне документов (по summaries) семантически чище.

### Целевая схема индексации

```
┌────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                   │
│                                                        │
│  data/*.html,pdf,md,txt,docx                           │
│       │                                                │
│       ▼                                                │
│  ┌──────────┐                                          │
│  │  Parse    │  SimpleDirectoryReader + HTML extractor  │
│  │  + Meta   │  → файловые metadata (name, path, ext)  │
│  └──────────┘                                          │
│       │                                                │
│       ├──────────────────────┐                          │
│       ▼                      ▼                          │
│  ┌──────────┐          ┌──────────┐                    │
│  │ Chunk     │          │ Summarize│                    │
│  │ (semantic │          │ (LLM)    │                    │
│  │  or fixed)│          │          │                    │
│  └──────────┘          └──────────┘                    │
│       │                      │                          │
│       ▼                      ▼                          │
│  ┌──────────┐          ┌──────────┐                    │
│  │ Enrich   │          │ Enrich   │                    │
│  │ metadata │          │ metadata │                    │
│  │ (LLM)    │          │ (LLM)    │                    │
│  │ topics,  │          │ topic,   │                    │
│  │ concepts │          │ concepts,│                    │
│  └──────────┘          │ level,   │                    │
│       │                │ type     │                    │
│       ▼                └──────────┘                    │
│  ┌──────────┐               │                          │
│  │ Chroma   │               ▼                          │
│  │ chunks   │          ┌──────────┐                    │
│  │ collection│         │ Chroma   │                    │
│  └──────────┘          │ docs     │                    │
│                        │ collection│                   │
│                        └──────────┘                    │
│                              │                          │
│                              ▼                          │
│                        ┌──────────┐                    │
│                        │ Topic    │                    │
│                        │ Cluster  │                    │
│                        │ (HDBSCAN)│                    │
│                        └──────────┘                    │
└────────────────────────────────────────────────────────┘
```

Два Chroma-хранилища:

| Коллекция | Содержимое | Кол-во записей | Используется для |
|-----------|-----------|----------------|-----------------|
| `home_rag` (chunks) | Чанки документов с embeddings | ~100–5000 | chunk-level retrieval (qa, keyword) |
| `home_rag_docs` (documents) | Summary + metadata каждого документа | ~10–100 | document-level retrieval (overview, synthesis, topics) |

### Metadata-схема

**Chunk node:**
```json
{
  "file_name": "Security_by_Design.html",
  "relative_path": "lectures/Security_by_Design.html",
  "folder_rel": "lectures",
  "ext": ".html",
  "doc_id": "lectures/Security_by_Design.html",
  "concepts": ["prompt injection", "guardrails", "OWASP"],
  "node_type": "chunk"
}
```

**Document node:**
```json
{
  "file_name": "Security_by_Design.html",
  "relative_path": "lectures/Security_by_Design.html",
  "doc_id": "lectures/Security_by_Design.html",
  "summary": "Лекция о многоуровневой защите AI-систем: API Gateway, Input/Output Guardrails, изоляция тенантов в векторной БД, OWASP для LLM...",
  "topic": "AI Security",
  "topic_id": "cluster_03",
  "concepts": ["prompt injection", "guardrails", "OWASP", "adversarial attacks", "PII filtering"],
  "doc_type": "lecture",
  "complexity": "intermediate",
  "node_type": "document_summary"
}
```

### Стоимость обогащённой индексации

| Операция | LLM-вызовы | ~Tokens per doc | ~Стоимость per doc (cheap model) |
|----------|-----------|----------------|--------------------------------|
| Summary generation | 1 | ~3000 in + 300 out | $0.001 |
| Metadata extraction | 1 | ~3000 in + 200 out | $0.001 |
| Topic naming (per cluster) | 1 | ~500 in + 50 out | $0.0003 |
| **Total per document** | **2** | | **~$0.002** |
| **50 документов** | **100** | | **~$0.10** |

При текущих ценах: обогащённая индексация 50 документов стоит ~10 центов. Приемлемо.

### Latency индексации

| Текущая (50 docs) | С enrichment (50 docs) | Разница |
|-------------------|----------------------|---------|
| ~30–60 sec (embedding only) | ~90–180 sec (+LLM calls) | +60–120 sec |

Индексация запускается редко (при добавлении документов). Рост latency ×2–3 допустим.

### Критерии принятия

1. `GET /index/stats` возвращает количество документов в обеих коллекциях и список metadata-полей.
2. Двухуровневый retrieval: запрос «какие лекции про безопасность?» возвращает документы (по summaries), а не чанки.
3. Metadata filtering: `topic=AI Security` фильтрует документы корректно.
4. Eval: обзорные вопросы — context recall ≥ 0.7 (сейчас не измеряется, т.к. нет doc-level retrieval).

---

<a id="adr-012"></a>
## ADR-012: Multi-Prompt Architecture — промпт как функция типа запроса

**Статус:** Proposed  
**Дата:** 2026-03  
**Итерации:** 12–13  
**Зависит от:** ADR-004 (pipeline factory), ADR-006 (KM RAG), ADR-010 (5-ступенчатый pipeline)

### Контекст

Текущий `QA_PROMPT` — один на все случаи:

```
Ты помощник по личной базе знаний.
Используй только найденный контекст.
...
Ответь: 1. Простыми словами 2. По делу 3. Кратко
```

Инструкция «Кратко» — правильная для `qa` типа, но вредная для `synthesis` (конспект должен быть подробным) и `learning_plan` (план должен быть структурированным и длинным).

### Предлагаемая архитектура

```python
# app/prompts.py

PROMPTS = {
    "qa": PromptTemplate("""
Ты помощник по личной базе знаний.
Используй ТОЛЬКО найденный контекст. Если данных не хватает, скажи об этом.

Контекст:
{context_str}

Вопрос: {query_str}

Ответь кратко, по существу, с опорой на источники.
"""),

    "overview": PromptTemplate("""
Ты помощник-аналитик по личной базе знаний.
На основе найденного контекста дай обзор темы.

Контекст из нескольких документов:
{context_str}

Тема: {query_str}

Перечисли ключевые идеи, подходы и концепции. Укажи, из каких документов взята каждая идея.
Если контекста недостаточно для полного обзора, отметь это.
"""),

    "synthesis": PromptTemplate("""
Ты составитель конспектов по личной базе знаний.
На основе фрагментов из нескольких документов составь структурированный конспект.

Фрагменты:
{context_str}

Тема конспекта: {query_str}

Требования:
1. Структура: введение, основные разделы, итог.
2. Каждый раздел — 3–5 предложений.
3. В конце каждого раздела — ссылка на источник(и).
4. Если фрагменты противоречат друг другу — отметь расхождение.
"""),

    "learning_plan": PromptTemplate("""
Ты составитель планов обучения по личной базе знаний.
На основе доступных документов и их тем, составь план обучения.

Доступные документы и темы:
{context_str}

Цель обучения: {query_str}

Требования:
1. Расположи темы от простого к сложному.
2. Для каждого шага укажи: тема, документ(ы), ключевые концепции.
3. Укажи зависимости: «перед изучением X нужно знать Y».
4. Оцени время на каждый шаг (в часах).
"""),
}
```

### Альтернативы

**A. Один универсальный промпт с динамическими инструкциями**
```
Ты помощник. {instructions_by_type}. Контекст: {context_str}. Вопрос: {query_str}.
```
- Плюсы: один шаблон, меньше кода.
- Минусы: промпт становится длинным и размытым. LLM хуже следует сложным мульти-модальным инструкциям. Сложно тестировать каждый режим изолированно.
- Почему отклонён: промпт-инженерия показывает, что специализированные промпты стабильно выигрывают у универсальных.

**B. Отдельные промпты на каждый тип (предложенный вариант)**
- Плюсы: каждый промпт заточен под свою задачу, легко итерировать и тестировать независимо.
- Минусы: больше файлов/кода, при добавлении нового типа — ещё один промпт.

**C. Промпты в конфиг-файле (YAML/JSON)**
- Плюсы: можно менять промпты без изменения кода.
- Минусы: теряется типизация, сложнее тестировать, risk of injection через конфиг.
- Почему отклонён: для персонального проекта — overkill. Python-файл с PromptTemplate даёт те же возможности с type safety.

### Решение

Отдельные промпты в `app/prompts.py` (вариант B). Router (ступень 1 из ADR-010) выбирает промпт по типу запроса. `pipeline_factory.py` принимает `prompt_key` вместо жёстко зашитого `QA_PROMPT`.

### Связь с pipeline_factory

Текущий код:
```python
engine = index.as_query_engine(text_qa_template=QA_PROMPT, ...)
```

Целевой:
```python
prompt = PROMPTS[query_context.query_type]
engine = index.as_query_engine(text_qa_template=prompt, ...)
```

### Критерии принятия

1. Eval: для synthesis-вопросов — ответ содержит структуру (заголовки/разделы), не менее 3 абзацев. С QA_PROMPT — содержит 1–2 предложения.
2. Eval: для learning_plan — ответ содержит упорядоченные шаги, ссылки на документы, оценку времени.
3. Промпт qa даёт те же результаты, что и текущий QA_PROMPT (regression test).
4. Переключение промпта через конфиг: `DEFAULT_QUERY_TYPE=qa` для обратной совместимости.

---

<a id="adr-013"></a>
## ADR-013: Evaluation Strategy — трёхслойная модель оценки

**Статус:** Proposed  
**Дата:** 2026-03  
**Итерации:** 0.3 (dataset), 10–14  
**Зависит от:** ADR-003 (OpenRouter), ADR-005 (Settings)

### Контекст

Текущий eval (`compare_eval.py`) измеряет Faithfulness, Answer Relevancy, Context Relevancy по одному вопросу за раз, offline, вручную. Нет baseline, нет regression detection, нет continuous monitoring.

Лекция по тестированию LLM описывает три уровня: простые тесты (формат, длина), LLM-as-Judge, Human Feedback. Нужна стратегия, покрывающая все три.

### Трёхслойная модель

```
┌──────────────────────────────────────────────────┐
│          Слой 3: Human Feedback                  │
│  Когда: ad-hoc, после крупных изменений          │
│  Что: ручная оценка 10–20 ответов               │
│  Стоимость: ~30 минут человеческого времени      │
├──────────────────────────────────────────────────┤
│          Слой 2: LLM-as-Judge (Async)            │
│  Когда: sampling 10% runtime запросов            │
│  Что: Faithfulness, Answer Relevancy             │
│  Стоимость: ~$0.005 per judged query             │
│  Модель: отдельный judge (EVAL_JUDGE_LLM)        │
├──────────────────────────────────────────────────┤
│          Слой 1: Deterministic Checks            │
│  Когда: каждый запрос, синхронно                 │
│  Что: ответ не пустой, есть источники,           │
│       длина в допустимом диапазоне,              │
│       нет "I don't know" при наличии контекста,  │
│       устойчивость к Unicode-обфускации          │
│       (Unicode NFKC + частичная гомоглиф-норм.)  │
│  Стоимость: 0 (regex/code checks)               │
└──────────────────────────────────────────────────┘
```

### Слой 1: Deterministic Checks (каждый запрос)

| Проверка | Как | Порог | Действие при нарушении |
|----------|-----|-------|----------------------|
| Ответ не пустой | `len(answer.strip()) > 0` | — | Fallback message |
| Есть source nodes | `len(sources) > 0` | — | Warning в ответе |
| Длина ответа | `50 < len(answer) < 10000` | — | Log warning |
| Нет отказа при наличии контекста | Regex: «не могу ответить» + sources > 0 | — | Log warning, track metric |
| Score source nodes | `min(scores) > 0.3` | 0.3 | Low confidence warning |

Стоимость: 0. Latency: < 1 ms.

### Слой 2: LLM-as-Judge (10% запросов, async)

| Метрика | Что оценивает | Судья |
|---------|-------------|-------|
| Faithfulness | Ответ основан на контексте, нет галлюцинаций | Judge LLM |
| Answer Relevancy | Ответ релевантен вопросу | Judge LLM |
| Context Recall | Контекст содержит информацию для ответа | Judge LLM |

Стоимость: ~$0.005 per judged query (1 judge вызов ≈ 3000 tokens). При 100 запросов/день × 10% = 10 judge calls = $0.05/день.

Реализация: после ответа пользователю — async task запускает judge и сохраняет score в `metrics_store` (JSON или SQLite).

### Слой 3: Human Feedback

Streamlit UI: кнопки 👍/👎 после каждого ответа. Сохранение feedback в JSONL. Анализ после каждой итерации.

### Eval Dataset (baseline)

| Категория | Кол-во вопросов | Пример |
|-----------|----------------|--------|
| Точечный Q&A | 8 | «Что такое RLHF?» |
| Keyword search | 5 | «Найди все про OWASP» |
| Обзорный | 5 | «Какие подходы к защите RAG описаны?» |
| Cross-document | 5 | «Сравни подходы к безопасности в двух лекциях» |
| Synthesis | 4 | «Составь конспект по теме RAG» |
| Негативный | 3 | «Какой рецепт борща?» (нет в базе) |
| **Итого** | **30** | |

### Критерии принятия

1. Слой 1 работает на каждом запросе. Метрики доступны через `/metrics`.
2. Слой 2: sampling 10% запросов, scores сохраняются, доступны через `/metrics/quality`.
3. Baseline: eval dataset из 30 вопросов прогнан на текущем pipeline, scores зафиксированы.
4. Regression: после каждой итерации 10–13 — прогон eval dataset, сравнение с baseline. Деградация > 5% по любой метрике — блокер для merge.

---

<a id="adr-014"></a>
## ADR-014: Self-Correction Loop — Corrective RAG

**Статус:** Proposed  
**Дата:** 2026-03  
**Итерация:** 17  
**Зависит от:** ADR-007 (hybrid retrieval), ADR-010 (pipeline), ADR-013 (evaluation)

### Контекст

Даже с hybrid retrieval и reranking, retrieval может вернуть нерелевантный контекст. LLM сгенерирует ответ на основе этого контекста — красивый, уверенный и неправильный.

Лекция по RAG описывает Self-Correction RAG: «LLM оценивает релевантность возвращённых документов. Если нерелевантны — Query Rewriting или Web-поиск для дополнительного контекста».

### Предлагаемая схема

```
retrieve(query) → nodes
         │
         ▼
relevance_check(query, nodes) → score
         │
    ┌────┴────┐
    │ ≥ 0.6   │ < 0.6
    │         │
    ▼         ▼
 generate  rewrite(query) → query_v2
              │
              ▼
         retrieve(query_v2) → nodes_v2
              │
              ▼
         relevance_check(query_v2, nodes_v2)
              │
         ┌────┴────┐
         │ ≥ 0.6   │ < 0.6
         ▼         ▼
      generate   generate with disclaimer:
                 "Недостаточно данных для уверенного ответа"
```

Максимум 1 retry. Бесконечный loop не допускается.

### Cost Impact

| Сценарий | LLM-вызовы | ~Стоимость |
|----------|-----------|-----------|
| Контекст релевантен (80% запросов) | +1 cheap (relevance check) | +$0.0002 |
| Контекст нерелевантен, retry помог (15%) | +1 cheap (check) + 1 cheap (rewrite) + 1 cheap (check) | +$0.0006 |
| Контекст нерелевантен, retry не помог (5%) | +2 cheap (checks) + 1 cheap (rewrite) | +$0.0006 |

Средний overhead: ~$0.0003 per query. Пренебрежимо мало.

### Критерии принятия

1. Faithfulness на eval dataset: улучшение ≥ 5% (за счёт отсечения нерелевантного контекста).
2. Доля ответов с disclaimer «недостаточно данных» на негативных вопросах (нет в базе): ≥ 80%.
3. Latency: retry path ≤ +2 секунды к обычному pipeline.
4. Отключается через конфиг: `ENABLE_SELF_CORRECTION=false`.

---

<a id="adr-015"></a>
## ADR-015: Knowledge Graph — облегчённый граф концепций

**Статус:** Proposed  
**Дата:** 2026-03  
**Итерация:** 17  
**Зависит от:** ADR-008 (document summaries), ADR-009 (topic clustering), ADR-011 (двухуровневая индексация)

### Контекст

Для learning plan generator нужно знать:
- Какие концепции содержит каждый документ.
- Какие документы связаны через общие концепции.
- Какие концепции являются prerequisite для других.

Vector search и topic clustering дают тематическую близость, но не видят направленные связи: «для понимания Self-Correction RAG нужно сначала знать Query Rewriting и Faithfulness».

### Альтернативы

**A. Full GraphRAG (llama-index PropertyGraphIndex + Neo4j)**
- Плюсы: полноценный граф с триплетами, traversal, graph-based retrieval.
- Минусы: Neo4j — дополнительный сервис, сложная настройка, overkill для десятков документов, долгая индексация (LLM извлекает каждый триплет).
- Почему отклонён: нарушает KISS. При 20–50 документах граф будет маленьким, и overhead setup не оправдан.

**B. Облегчённый граф концепций (JSON + Chroma)**

Структура:
```json
{
  "concepts": {
    "prompt_injection": {
      "name": "Prompt Injection",
      "documents": ["Security_by_Design.html", "Интеграции_AI.html"],
      "related_concepts": ["guardrails", "input_validation", "OWASP"],
      "prerequisite_for": ["output_guardrails", "adversarial_attacks"]
    },
    "hybrid_search": {
      "name": "Hybrid Search (BM25 + Vector)",
      "documents": ["RAG_Уменьшение_галлюцинаций.html"],
      "related_concepts": ["BM25", "vector_search", "reranking"],
      "prerequisite_for": ["agentic_rag"]
    }
  },
  "documents": {
    "Security_by_Design.html": {
      "concepts": ["prompt_injection", "guardrails", "OWASP", ...],
      "complexity": "intermediate",
      "prerequisites": ["RAG_basics"]
    }
  }
}
```

- Плюсы: нет дополнительных зависимостей, JSON инспектируется человеком, связи `prerequisite_for` дают направленный граф для learning plan.
- Минусы: нет graph-based retrieval (traversal), масштабируется хуже чем Neo4j, связи извлекаются LLM — могут быть неточными.

**C. SQLite с таблицами concepts, documents, relations**
- Плюсы: SQL-запросы, нормализация, индексы.
- Минусы: ещё одна зависимость (хотя SQLite встроен в Python), schema migration при изменении структуры.
- Почему отложен: может стать следующим шагом, если JSON перестанет масштабироваться.

### Предлагаемое решение

**Вариант B — JSON граф концепций.** Генерируется при индексации, хранится в `concept_graph.json`.

Процесс:
1. При индексации каждого документа LLM извлекает список концепций и prerequisites.
2. Concept graph строится как merge всех документов.
3. `related_concepts` — автоматически по co-occurrence (два концепта в одном документе → связаны).
4. `prerequisite_for` — LLM-extracted (при enrichment: «какие знания нужны для понимания этого документа?»).

### Использование в Learning Plan

```
Вход: goal = "Научиться проектировать production RAG"

1. Classify → learning_plan type
2. Retrieve documents relevant to "production RAG" (doc-level)
3. Load concept_graph.json
4. Topological sort по prerequisite_for:
   RAG_basics → hybrid_search → reranking → query_rewriting → ...
5. Map concepts → documents
6. Generate plan с ordering и временными оценками
```

### Критерии принятия

1. `GET /knowledge/concepts` — возвращает граф концепций.
2. `GET /knowledge/concepts/{concept}/documents` — документы, содержащие концепцию.
3. `GET /knowledge/documents/{doc}/prerequisites` — prerequisite документы.
4. Learning plan для «изучить RAG» — содержит упорядоченные шаги от простого к сложному.
5. Граф пересоздаётся при reindex автоматически.

### Риски

| Риск | Вероятность | Импакт | Митигация |
|------|------------|--------|-----------|
| LLM извлекает неточные prerequisites | Высокая | Средний | Ручная коррекция через API: `PUT /knowledge/concepts/{id}` |
| Граф слишком большой для JSON | Низкая (при <100 docs) | Низкий | Миграция на SQLite |
| Topological sort невозможен (циклы) | Средняя | Высокий | Cycle detection + break weakest edge |

---

## Кросс-ссылки между ADR

```
ADR-001 (llama-index) ←── ADR-004 (pipeline factory) ←── ADR-010 (5-step pipeline)
                                                              │
ADR-002 (Chroma) ←──── ADR-008 (doc summaries) ←── ADR-011 (2-level index)
                                                              │
ADR-003 (OpenRouter) ←── ADR-013 (eval strategy)    ADR-012 (multi-prompt)
                              │                            │
ADR-006 (Q&A→KM) ───────────┼── ADR-010 ←────────── ADR-012
                              │        │
                              │   ADR-014 (self-correction)
                              │
ADR-009 (topic clustering) ←── ADR-015 (knowledge graph)
```

---

# ADR: Дополнения к архитектуре home-rag_v2 (ADR-016–020)

> Этот документ дополняет существующие `adr.md` (ADR-001–009) и `adr_rag_architecture.md` (ADR-010–015). Новые записи основаны на анализе архитектуры от 2026-03-16, фокусируясь на устранении выявленных ошибок (race conditions, dual config, incomplete pipeline) и улучшениях (knowledge graph, streaming, caching). Они совместимы с принятыми решениями и roadmap в `tasklist.md`.

## Реестр новых решений

| ADR | Название | Статус | Дата | Зависит от |
|-----|---------|--------|------|------------|
| [016](#adr-016) | Blue-Green Reindex для атомарной переиндексации | Proposed | 2026-03-16 | 002, 008 |
| [017](#adr-017) | Полный 5-ступенчатый Query Pipeline с RouterQueryEngine | Proposed | 2026-03-16 | 004, 010, 012 |
| [018](#adr-018) | Унификация конфигурации: удаление глобальных переменных | Accepted | 2026-03-16 | 005 |
| [019](#adr-019) | Универсальный Explain для всех форматов документов | Proposed | 2026-03-16 | 006, 011 |
| [020](#adr-020) | Внедрение PropertyGraphIndex для Knowledge Graph | Proposed | 2026-03-16 | 009, 015 |

---

### ADR-016: Blue-Green Reindex для атомарной переиндексации

**Статус**: Proposed  
**Контекст**: Текущая переиндексация (`retrieval_cache.py`) удаляет коллекцию в background, что приводит к race condition: запросы могут попадать на частично удалённый индекс. Это нарушает consistency (ADR-002) и приводит к ошибкам в production.  

**Рассмотренные альтернативы**:  
- Lock на весь индекс (замедляет все запросы).  
- Отключение API на время reindex (downtime).  
- Blue-green: две коллекции (active/staging), атомарный swap.  

**Решение**: Внедрить blue-green подход. Создавать staging-коллекцию, индексировать в неё, затем атомарно переименовать в active через `client.rename_collection`. Инвалидировать кэш одним вызовом. Добавить `wait_if_reindexing()` для всех путей и `X-Reindex-Version` header.  

**Последствия**:  
- Положительные: Устраняет race, zero-downtime reindex.  
- Отрицательные: Удваивает дисковое пространство временно.  
- Effort: 2–3 дня (итерация 16).  

---

### ADR-017: Полный 5-ступенчатый Query Pipeline с RouterQueryEngine

**Статус**: Proposed  
**Контекст**: Текущий pipeline (`pipeline_runner.py`, `retrieval.py`) реализует только classify+rewrite, но retrieve/rerank/generate слиты. Это нарушает ADR-010 (5-step loop) и снижает качество для overview/synthesis (ADR-012).  

**Рассмотренные альтернативы**:  
- Кастомный loop в `PipelineRunner`.  
- LlamaIndex `RouterQueryEngine` + `SubQuestionQueryEngine`.  
- Полный graph-based pipeline (слишком рано).  

**Решение**: Расширить `PipelineRunner` на полный 5-step (classify → rewrite → retrieve → rerank → generate) с использованием `RouterQueryEngine` для маршрутизации по типу запроса. Добавить `subquestions` в `QueryContext` для synthesis.  

**Последствия**:  
- Положительные: Улучшает качество, упрощает multi-prompt (ADR-012).  
- Отрицательные: Увеличивает latency на 200–500 мс (оптимизировать cheap models).  
- Effort: 4–5 дней (итерация 12).  

---

### ADR-018: Унификация конфигурации: удаление глобальных переменных

**Статус**: Accepted  
**Контекст**: Двойная конфигурация (`get_settings()` + `_export()` глобалы) приводит к расхождениям при hot-reload и тестах, нарушая ADR-005.  

**Рассмотренные альтернативы**:  
- Сохранить глобалы для legacy.  
- Полный переход на getters.  

**Решение**: Удалить `_export()` полностью. Все модули (provider, guardrails, etc.) перевести на `get_settings()` / `get_retrieval_settings()`. Добавить кэш в pydantic-settings для тестов.  

**Последствия**:  
- Положительные: Один источник правды, проще тесты.  
- Отрицательные: Миграция кода (поиск/замена).  
- Effort: 1 день (итерация 15).  

---

### ADR-019: Универсальный Explain для всех форматов документов

**Статус**: Proposed  
**Контекст**: `explain_service.py` ограничивает explain/content .txt/.md, сломанный UX для PDF/DOCX (70% документов). Нарушает принцип KM в `product_idea.md`.  

**Рассмотренные альтернативы**:  
- Только text-files (текущий).  
- LLM-extraction для non-text.  
- Интеграция PyMuPDF/unstructured.  

**Решение**: Сделать универсальный: сначала текст, fallback на LLM-саммари по первым 8k токенов + PyMuPDF для PDF.  

**Последствия**:  
- Положительные: Полный coverage форматов.  
- Отрицательные: +1 LLM-вызов для non-text (budget в `budget_llm.md`).  
- Effort: 1 день (итерация 11).  

---

### ADR-020: Внедрение PropertyGraphIndex для Knowledge Graph

**Статус**: Accepted (MVP итерация 16 tail, 2026-04-05)  
**Контекст**: Нет графа концепций (только clustering), что блокирует learning plans и связи (ADR-009, ADR-015). JSON-граф не масштабируется.  

**Рассмотренные альтернативы**:  
- JSON-graph (текущий план).  
- SQLite/Neo4j-lite.  
- LlamaIndex `PropertyGraphIndex`.  

**Решение**: Внедрить `PropertyGraphIndex` с SQLite-backend. При enrichment добавлять `prerequisite_for` / `related_concepts`. Использовать для graph-augmented retrieval.  

**Реализация MVP**: `SimplePropertyGraphStore` (LlamaIndex) сериализуется в `property_graph_store.json`; полный JSON-снимок графа для API/UI — в `kg.sqlite` (`data/graph_generations/`). Graph-augmented retrieval — итерация 17 Core.  

**Последствия**:  
- Положительные: Топологическая сортировка O(1), масштабируемость.  
- Отрицательные: Миграция от JSON (итерация 17).  
- Effort: 3 дня.  

---
