# Архитектурный рефакторинг hometutor: от Q&A RAG к модульной системе с графом знаний и диалогами

Статус: `Historical`
Роль: аналитический документ по переходной архитектуре и паттернам рефакторинга.
Может содержать смесь актуального контекста и исторических планов; проверяйте выводы по `architecture.md`, `technical_specification.md` и коду.

> Этот документ дополняет существующие [ADR](adr.md) (001–009) и [ADR RAG Architecture](adr_rag_architecture.md) (010–015), фокусируясь на архитектурных паттернах расширения системы. Он не пересматривает принятые решения, а раскрывает, как именно реализовать переход от текущей архитектуры к целевой.
>
> **Связанные документы:** [tasklist.md](tasklist.md) (roadmap), [vision.md](vision.md) (архитектура), [adr.md](adr.md) + [adr_rag_architecture.md](adr_rag_architecture.md) (обоснования решений), [technical_specification.md](technical_specification.md) (ТЗ).

---

## 1. Текущее состояние архитектуры

### 1.1. Что уже реализовано

После 14 итераций и выполнения Блока 0 проект обладает модульной структурой с разделением ответственности:

- **Pipeline Factory** (`pipeline_factory.py`) — единый источник правды для сборки RAG-пайплайна: промпт, фильтры, профили, postprocessors. Все потребители (retrieval, profiler, eval) используют одни и те же функции ([ADR-004](adr.md#adr-004)).
- **Provider** (`provider.py`) — централизованное создание LLM и embedding-клиентов через OpenRouter ([ADR-003](adr.md#adr-003)).
- **Typed Settings** (`config.py`) — pydantic-settings с валидацией, нормализацией профилей и property-based доступом ([ADR-005](adr.md#adr-005)). Включает feature flags для будущих ступеней pipeline (`ENABLE_REWRITE`, `ENABLE_CLASSIFIER`, `ENABLE_SELF_CORRECTION`) и поля для моделей по ступеням (`rewrite_model`, `classifier_model`, `eval_judge_llm`) — Блок 0.5.
- **Guardrails** (`guardrails.py`, `input_validation.py`) — input (prompt injection EN/RU, длина) и output (PII, утечка инструкций, пустой ответ, наличие источников).
- **Retrieval Cache** (`retrieval_cache.py`) — LRU + TTL кэширование query engine, Chroma-клиента, embed-модели и индекса.
- **Evaluation** — offline batch eval с RAG Triad метриками, отдельный judge LLM (`EVAL_JUDGE_LLM`), compare-eval для сравнения конфигураций.
- **Hybrid Search** (`hybrid_retrieval.py`, итерация 10) — BM25 + vector search через `QueryFusionRetriever` с reciprocal rank fusion ([ADR-007](adr.md#adr-007)). Реализованы `vector_only` / `hybrid`, retrieval regression suite, retrieval-level метрики, keyword-ветка `BM25-only`, параллельный BM25 + vector retrieval и eval-сравнение `vector_only` vs `hybrid` как артефакт roadmap.
- **Smart Ingestion** (`ingestion.py`, `ingestion_metadata.py`, итерация 11) — metadata enrichment, document-level summaries, двухуровневый retrieval `doc -> chunk`, metadata filtering по `topic` / `folder` / `file`.
- **Query Understanding** (`query_routing.py`, `pipeline_runner.py`, `pipeline_steps.py`, итерация 12) — query rewrite, classify/router, `QueryContext`, composable pipeline steps, stage-safe fallback и приоритет конфигурации `QueryContext > overrides > env`.
- **Knowledge Organization** (`knowledge_service.py`, `app/ui/main.py`, `api.py`, итерация 13) — topic clustering, `GET /topics`, `POST /synthesize`, knowledge workspace, global knowledge search, working set, explainability и trust signals для synthesis/overview.
- **Observability** (`metrics.py`, `routers/metrics.py`, итерация 14) — runtime metrics, cost/quality dashboard, feedback loop, history persistence и knowledge-workflow analytics.
- **Промпты** (`prompts.py`) — промпты `qa`, `overview`, `synthesis`, `learning_plan`, `keyword` уже используются в runtime pipeline для реализованных типов запросов; `learning_plan` остаётся за итерацией 17.

Это не монолит. Система уже прошла путь от первого прототипа до модульной архитектуры с единой pipeline factory, типизированной конфигурацией, двумя слоями guardrails, multi-step query pipeline и knowledge workflows поверх hybrid retrieval.

### 1.2. Границы текущей архитектуры

При этом существуют конкретные архитектурные ограничения, которые блокируют следующий уровень функциональности:

**Ограничение 1: Не все целевые типы запросов ещё реализованы в единой схеме.**
Базовый multi-step pipeline уже поддерживает `qa`, `keyword`, `overview` и `synthesis`. Learning plan и study-oriented follow-up уже есть в MVP-виде, но knowledge-graph workflows, self-correction и session-based multi-turn ещё не встроены в тот же production-контур.

**Решение:** 5-ступенчатый pipeline (Classify → Rewrite → Retrieve → Rerank → Generate) с композируемыми ступенями ([ADR-010](adr_rag_architecture.md#adr-010)). Каждая ступень — отдельный модуль с единым интерфейсом.

**Ограничение 2: Smart ingestion закрыт не полностью.**
Document summaries и двухуровневый retrieval уже реализованы, но semantic chunking, quality gates ingestion и полный quality report по reindex ещё остаются в backlog.

**Решение:** Двухуровневая индексация с отдельной коллекцией document summaries ([ADR-011](adr_rag_architecture.md#adr-011)).

**Ограничение 3: Нет контекста между запросами.**
Каждый запрос обрабатывается изолированно. Follow-up вопрос «а что ещё?» не имеет контекста предыдущего ответа.

**Решение:** Multi-turn context через session_id, conversation history и query condensing (итерация 19 в [tasklist.md](tasklist.md)).

**Ограничение 4: Нет production-ready модели связей между документами и концепциями.**
Черновой knowledge graph уже появился в кодовой базе, но полноценные provenance, ручная коррекция, графовые workflow и миграционные правила ещё запланированы на итерацию 17.

**Решение:** Облегчённый JSON-граф концепций ([ADR-015](adr_rag_architecture.md#adr-015)).

---

## 2. Паттерн расширения: композируемый pipeline

### 2.1. От монолитного pipeline к конфигурируемому

Текущий pipeline (после итерации 13):
```
question → retrieve(vector_only | hybrid) → rerank → generate(QA_PROMPT) → answer
```

Целевой pipeline ([ADR-010](adr_rag_architecture.md#adr-010)):
```
question → classify → rewrite → retrieve(strategy) → rerank(strategy) → generate(prompt) → answer
```

Ключевой архитектурный принцип: **тип запроса определяет конфигурацию всех ступеней, а не код внутри каждой ступени.** Router выбирает набор модулей, а не if-else внутри модуля.

### 2.2. Контракт ступени pipeline

Каждая ступень принимает и возвращает `QueryContext` — единый объект, содержащий всё состояние обработки запроса:

```python
@dataclass
class QueryContext:
    # Входные данные
    original_question: str
    session_id: str | None = None
    
    # Заполняется ступенью Classify
    query_type: str = "qa"  # qa | keyword | overview | synthesis | learning_plan
    prompt_key: str = "qa"
    retrieval_strategy: str = "hybrid_chunks"  # hybrid_chunks | two_level | bm25_only
    rerank_strategy: str = "cross_encoder"     # cross_encoder | by_document | none
    
    # Заполняется ступенью Rewrite
    rewritten_query: str | None = None
    sub_queries: list[str] | None = None
    
    # Заполняется ступенью Retrieve
    retrieved_nodes: list = field(default_factory=list)
    retrieved_documents: list = field(default_factory=list)
    
    # Заполняется ступенью Rerank
    reranked_nodes: list = field(default_factory=list)
    
    # Заполняется ступенью Generate
    answer: str = ""
    sources: list = field(default_factory=list)
    
    # Debug / tracing
    trace: dict = field(default_factory=dict)
```

Каждая ступень — функция `process(ctx: QueryContext) → QueryContext`. Pipeline runner вызывает их последовательно:

```python
# Концептуальная схема pipeline runner
PIPELINES = {
    "qa":            [classify, rewrite_qa, retrieve_hybrid, rerank_cross_encoder, generate],
    "keyword":       [classify, passthrough, retrieve_bm25, passthrough, generate],
    "overview":      [classify, rewrite_overview, retrieve_two_level, rerank_by_doc, generate],
    "synthesis":     [classify, rewrite_sub_questions, retrieve_two_level, rerank_by_doc, generate],
    "learning_plan": [classify, rewrite_plan, retrieve_two_level, rerank_by_doc, generate_plan],
}

def run_pipeline(question: str, session_id: str | None = None) -> QueryContext:
    ctx = QueryContext(original_question=question, session_id=session_id)
    
    # Classify определяет тип → выбирается pipeline
    ctx = classify(ctx)
    pipeline = PIPELINES[ctx.query_type]
    
    for step in pipeline[1:]:  # skip classify, уже выполнен
        ctx = step(ctx)
    
    return ctx
```

### 2.3. Связь с pipeline_factory

Текущий `pipeline_factory.py` не заменяется, а оборачивается. `resolve_pipeline_params()` и `build_postprocessors()` продолжают работать для `qa` и `keyword` типов. Новые типы (`synthesis`, `learning_plan`) добавляют свои конфигурации поверх.

```python
# Концептуальный код ступени retrieval для synthesis (после итерации 11).
# Зависит от двухуровневой индексации: get_base_services() должен будет
# возвращать "doc_index" (коллекция document summaries, ADR-011).
# Сейчас get_base_services() возвращает: client, collection, vector_store,
# storage_context, embed_model, llm, index.
def retrieve_two_level(ctx: QueryContext) -> QueryContext:
    services = get_base_services()
    
    # Level 1: document retrieval по summaries (требует итерацию 11)
    doc_retriever = services["doc_index"].as_retriever(similarity_top_k=5)
    ctx.retrieved_documents = doc_retriever.retrieve(ctx.rewritten_query)
    
    # Level 2: chunk retrieval внутри найденных документов
    doc_ids = [d.metadata["doc_id"] for d in ctx.retrieved_documents]
    chunk_retriever = services["index"].as_retriever(
        similarity_top_k=ctx.params["similarity_top_k"],
        filters=MetadataFilters(filters=[MetadataFilter(key="doc_id", value=doc_ids)])
    )
    ctx.retrieved_nodes = chunk_retriever.retrieve(ctx.rewritten_query)
    
    return ctx
```

### 2.4. Graceful degradation по ступеням

Каждая ступень pipeline может упасть или превысить latency budget. Без формализованного fallback-поведения одна ошибка ломает весь pipeline. Принцип: **сбой вспомогательной ступени не должен блокировать ответ пользователю.**

| Ступень | Ошибка / timeout | Fallback-поведение | Логирование |
|---------|------------------|--------------------|-------------|
| Classify | LLM недоступен, timeout > 500 ms | Тип = `qa` (самый безопасный), продолжить pipeline | Warning + metric `classify_fallback_count` |
| Rewrite | LLM недоступен, timeout > 800 ms | Passthrough: `rewritten_query = original_question` | Warning + metric `rewrite_fallback_count` |
| Retrieve | Chroma недоступна, BM25 index пуст | Если hybrid — fallback на vector_only (или наоборот). Если оба — ошибка с сообщением пользователю | Error + metric |
| Rerank | Cross-encoder timeout, OOM | Пропустить rerank: вернуть `retrieved_nodes` без reranking | Warning + metric `rerank_skip_count` |
| Generate | LLM недоступен | Ошибка с сообщением: «Сервис временно недоступен. Повторите запрос позже.» | Error + alert |

Реализация через try/except в pipeline runner:

```python
def run_step_safe(step_fn, ctx: QueryContext, fallback_fn=None) -> QueryContext:
    try:
        return step_fn(ctx)
    except Exception as e:
        logger.warning("Step %s failed: %s, using fallback", step_fn.__name__, e)
        ctx.trace[f"{step_fn.__name__}_error"] = str(e)
        if fallback_fn:
            return fallback_fn(ctx)
        return ctx  # passthrough
```

Generate — единственная ступень без fallback: если LLM недоступен, ответить нечем. Все остальные ступени опциональны и деградируют gracefully.

### 2.5. Приоритет конфигурации и миграция settings

Текущие config settings (`RETRIEVAL_MODE`, `ENABLE_RERANKER`, `RAG_PROFILE`) продолжают работать как defaults. После реализации Classify ступени в итерации 12 критично сохранить прозрачный приоритет: кто определяет стратегию retrieval — config или router.

**Приоритет (от высшего к низшему):**

```
1. QueryContext (заполняется Classify)    ← тип запроса определяет стратегию
2. Pipeline overrides (API params)         ← пользователь явно передал параметры
3. Config defaults (env / Settings)        ← значения по умолчанию
```

Пример: если `RETRIEVAL_MODE=vector_only` в `.env`, но Classify определил тип `overview` → `retrieval_strategy=two_level` из QueryContext перезаписывает config default. Если пользователь явно передал `retrieval_mode=hybrid` в API → API override приоритетнее Classify.

```python
# Концептуальный код (итерация 12+).
# Текущий PipelineOverrides (models.py) содержит: similarity_top_k,
# enable_reranker, rerank_top_n, rerank_model, split_strategy, window_size.
# Поле retrieval_mode пока отсутствует — его потребуется добавить при
# реализации Classify, чтобы API-потребители могли явно переопределять
# стратегию retrieval.
def resolve_retrieval_strategy(ctx: QueryContext, overrides: PipelineOverrides, settings: RetrievalSettings) -> str:
    if overrides and getattr(overrides, "retrieval_mode", None):
        return overrides.retrieval_mode           # приоритет 2: явный override
    if ctx.retrieval_strategy != "default":
        return ctx.retrieval_strategy              # приоритет 1: router decision
    return settings.retrieval_mode                 # приоритет 3: config default
```

Это сохраняет полную обратную совместимость: без Classify и без overrides система работает по config defaults, как сейчас.

### 2.6. Async/sync стратегия pipeline runner

Текущий pipeline (`pipeline_factory` → `retrieval` → `query_service`) полностью синхронный. FastAPI поддерживает async, но переход всего pipeline на async — масштабный рефакторинг.

**Решение: pipeline runner — sync. Параллелизация — локально внутри ступеней.**

- Pipeline runner вызывает ступени последовательно: `for step in pipeline: ctx = step(ctx)`.
- Внутри ступени Retrieve: `ThreadPoolExecutor` для параллельного BM25 + vector search (итерация 10).
- Внутри ступени Generate: sync вызов LLM (для SSE streaming в итерации 18 — отдельный async path в FastAPI endpoint).

Это минимизирует изменения: `answer_question()` остаётся sync, существующие тесты не ломаются. Async endpoint для streaming добавляется параллельно, не заменяя sync path.

### 2.7. Стратегия поэтапного внедрения

Каждая итерация расширяет pipeline, не ломая предыдущие типы:

| Итерация | Что добавляется | Типы запросов |
|----------|----------------|---------------|
| 10 (реализована) | Hybrid retrieval (BM25 + vector), keyword-ветка, параллельный retrieval | qa, keyword |
| 11 (реализована) | Document summaries, двухуровневый retrieval, metadata enrichment | + overview foundation |
| 12 (реализована) | Classify, Rewrite, QueryContext, pipeline runner, feature flags | qa, keyword, overview |
| 13 (реализована) | Synthesis prompt, topic clustering, SubQuestionQueryEngine, knowledge workflows | + synthesis |
| 14 (реализована) | Runtime observability, cost/quality metrics, history/feedback | без изменения типов, но с полной трассировкой |
| 17 | Knowledge graph, production-grade learning plan, self-correction loop (ADR-014) | + graph workflows поверх learning_plan |
| 19 | Session history, query condensing | all types + полноценный multi-turn |

На каждом шаге `qa` тип обрабатывается ровно так же, как раньше — регрессий нет.

---

## 3. Паттерн расширения: граф знаний

### 3.1. Почему облегчённый граф, а не Neo4j

[ADR-015](adr_rag_architecture.md#adr-015) обосновал выбор JSON-графа вместо полноценного Neo4j. Ключевые аргументы:

- При 20–50 документах overhead Neo4j (установка, администрирование, Cypher-запросы) не оправдан.
- Проект — локальный, single-user. `python main.py` должно запускать всё. Дополнительный процесс Neo4j нарушает этот принцип ([ADR-002](adr.md#adr-002), то же обоснование, что и для Chroma vs PGVector).
- JSON-граф инспектируется человеком, версионируется в git, не требует backup-стратегии.

Однако архитектура должна позволять миграцию на Neo4j **без переписывания потребителей графа**. Вот как это обеспечить.

### 3.2. Абстракция доступа к графу

Вместо прямого чтения `concept_graph.json` в коде pipeline — выделить интерфейс:

```python
# app/knowledge_graph.py

class KnowledgeGraphReader:
    """Абстракция чтения графа знаний. Текущая реализация: JSON-файл."""
    
    def get_concepts(self) -> dict:
        """Все концепции с их связями."""
        ...
    
    def get_document_concepts(self, doc_id: str) -> list[str]:
        """Концепции, содержащиеся в документе."""
        ...
    
    def get_prerequisites(self, concept_id: str) -> list[str]:
        """Prerequisite-концепции для данной."""
        ...
    
    def get_related_documents(self, concept_id: str) -> list[str]:
        """Документы, содержащие данную концепцию."""
        ...
    
    def topological_sort(self, concept_ids: list[str]) -> list[str]:
        """Топологическая сортировка по prerequisites."""
        ...


class JsonKnowledgeGraph(KnowledgeGraphReader):
    """Реализация на JSON-файле (concept_graph.json)."""
    
    def __init__(self, path: Path):
        self._path = path
        self._data = self._load()
    ...


# Будущая реализация (итерация 18+ или если масштаб потребует):
# class Neo4jKnowledgeGraph(KnowledgeGraphReader):
#     def __init__(self, uri: str, auth: tuple): ...
```

Все потребители (learning plan generator, `/knowledge/*` endpoints, topic-based retrieval) работают через `KnowledgeGraphReader`, а не через прямое чтение JSON. Замена на Neo4j потребует только новой реализации интерфейса, без изменения pipeline.

### 3.3. Построение графа при индексации

Граф строится как побочный продукт metadata enrichment (итерация 11):

```
Индексация документа
  → LLM извлекает concepts[] и prerequisites[]          ← metadata enrichment
  → concepts сохраняются в metadata чанков и summaries   ← Chroma
  → связи concepts → documents → prerequisites           ← concept_graph.json
  → topic clustering по embeddings summaries              ← итерация 13
```

Важный принцип: **граф не является отдельной системой, а производная от metadata enrichment.** Одно изменение (enrichment) создаёт два артефакта (семантические metadata в Chroma + связи в concept_graph.json).

### 3.4. Использование графа в pipeline

Граф используется на трёх ступенях:

**Ступень Retrieve (для learning_plan и synthesis):**
```python
def retrieve_with_graph(ctx: QueryContext) -> QueryContext:
    graph = get_knowledge_graph()
    
    # Шаг 1: извлечь концепции из запроса (LLM extraction или embedding match по графу)
    relevant_concepts = extract_concepts_from_query(ctx.rewritten_query, graph)
    
    # Шаг 2: расширить retrieval — добавить документы, связанные через граф
    graph_doc_ids = set()
    for concept in relevant_concepts:
        graph_doc_ids.update(graph.get_related_documents(concept))
    
    # Шаг 3: объединить с vector retrieval
    ctx.retrieved_documents = merge(
        vector_retrieved=ctx.retrieved_documents,
        graph_retrieved=graph_doc_ids
    )
    return ctx
```

**Ступень Generate (для learning_plan):**
```python
def generate_plan(ctx: QueryContext) -> QueryContext:
    graph = get_knowledge_graph()
    
    # Топологическая сортировка концепций по prerequisites
    relevant_concepts = extract_concepts(ctx.retrieved_documents)
    ordered = graph.topological_sort(relevant_concepts)
    
    # Mapping concepts → documents
    plan_context = []
    for concept in ordered:
        docs = graph.get_related_documents(concept)
        plan_context.append({"concept": concept, "documents": docs})
    
    # Генерация с LEARNING_PLAN_PROMPT
    ctx.answer = generate(ctx.original_question, plan_context, prompt=LEARNING_PLAN_PROMPT)
    return ctx
```

### 3.5. Когда мигрировать на графовую БД

Конкретные триггеры для пересмотра [ADR-015](adr_rag_architecture.md#adr-015):

| Триггер | Порог | Действие |
|---------|-------|----------|
| Количество концепций | > 500 | JSON → SQLite (таблицы concepts, relations) |
| Количество документов | > 200 | JSON → SQLite |
| Нужен graph traversal > 3 hops | Любой | SQLite → Neo4j / llama-index PropertyGraphIndex |
| Нужен real-time обход графа в retrieval | Любой | SQLite → Neo4j с Cypher queries |
| Multi-user с разными графами | Любой | Neo4j с tenant isolation |

До достижения этих порогов — JSON-граф оптимален по соотношению простота/функциональность.

---

## 4. Паттерн расширения: multi-turn диалоги

### 4.1. Архитектурный подход

Multi-turn запланирован на итерацию 19 ([tasklist.md](tasklist.md)). Ключевое архитектурное решение: **session management встроен в QueryContext, а не в отдельный процесс.**

Проект — локальный, single-user. Redis, отдельный SessionManager-сервис и persistence session store — overkill. Вместо этого:

```python
# Хранение в памяти процесса (для локального single-user сервиса)
_sessions: dict[str, list[Message]] = {}

@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    timestamp: float

def get_session_history(session_id: str, max_messages: int = 20) -> list[Message]:
    return _sessions.get(session_id, [])[-max_messages:]

def add_to_session(session_id: str, message: Message):
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append(message)
    # TTL: удалить сессии старше 1 часа
    _cleanup_expired_sessions()
```

Это согласуется с принципами проекта: «Минимум кода, только необходимый функционал», «Простой и понятный код, без лишних абстракций» ([vision.md](vision.md)). Также в tasklist.md (итерация 19) явно указано: «начать с локального backend (`in-memory`/SQLite) и только затем при реальной необходимости выносить историю в Redis».

### 4.2. Query condensing как ступень pipeline

Multi-turn не требует нового pipeline — он встраивается в ступень Rewrite:

```python
def rewrite_with_history(ctx: QueryContext) -> QueryContext:
    if not ctx.session_id:
        return rewrite_qa(ctx)  # обычный rewrite без истории
    
    history = get_session_history(ctx.session_id)
    if not history:
        return rewrite_qa(ctx)
    
    # Query condensing: переформулировка с учётом истории
    condensed = llm_condense(
        current_question=ctx.original_question,
        history=history[-5:],  # последние 5 сообщений
    )
    ctx.rewritten_query = condensed
    ctx.trace["condensed_from"] = [m.content for m in history[-5:]]
    return ctx
```

Цепочка: condensing → rewriting → retrieval. Если condensing включён и есть история — он заменяет обычный rewrite. Если нет — fallback на обычный rewrite. Конфигурируется через feature flag `ENABLE_MULTI_TURN=true/false` (потребуется добавить в Settings при реализации итерации 19; аналогично уже реализованным `ENABLE_REWRITE`, `ENABLE_CLASSIFIER`, `ENABLE_SELF_CORRECTION`).

### 4.3. Управление длиной контекста

Проблема: при длинном диалоге вся история не помещается в контекстное окно LLM. Подходы, ранжированные по сложности:

**Уровень 1 (итерация 19, MVP):** Sliding window — последние N сообщений (N=5–10). Просто, предсказуемо, достаточно для 90% use cases.

**Уровень 2 (future):** Суммаризация истории — LLM сжимает длинную историю в 2–3 предложения. Дороже (дополнительный LLM-вызов), но сохраняет контекст длинных диалогов.

**Уровень 3 (future):** Semantic selection — embedding каждого сообщения, retrieval наиболее релевантных к текущему вопросу. Самый точный, но самый сложный.

Рекомендация: начать с уровня 1, измерить качество через eval follow-up вопросов, переходить к уровню 2 только при недостаточности.

### 4.4. Взаимодействие multi-turn и self-correction

При одновременной активации multi-turn (итерация 19) и self-correction (итерация 17 Core) важно определить порядок обработки. Принцип: **condense — отдельная ступень между Classify и Rewrite, self-correction — часть Retrieve. Они работают на разных ступенях и не конфликтуют.**

Полная цепочка при обоих включённых:

```
1. Classify                               → определяет тип запроса
2. Rewrite (condensing → rewriting)        → переформулировка с учётом истории
3. Retrieve (hybrid/two_level)             → поиск по переформулированному запросу
4. Relevance check (self-correction)       → оценка качества контекста
   4a. Если score < 0.6 → rewrite(query) → retrieve повторно → check снова
   4b. Если score ≥ 0.6 или retry уже был → продолжить
5. Rerank                                  → ранжирование
6. Generate                                → генерация ответа
```

Self-correction retry использует `rewritten_query` (уже condensed), а не `original_question`. Это важно: retry с raw follow-up вопросом «а что ещё?» бессмысленен без контекста.

В `QueryContext` трассируется полная цепочка:
```python
ctx.trace = {
    "condensed_from": ["Q1: Что такое RAG?", "A1: RAG это..."],
    "rewritten_query": "Какие ограничения у RAG-систем?",
    "self_correction_triggered": True,
    "retry_query": "Ограничения и проблемы RAG: контекстное окно, галлюцинации",
    "relevance_score_before": 0.42,
    "relevance_score_after": 0.78,
}
```

---

## 5. Производительность: бюджеты и оптимизации

### 5.1. Latency budget (на основе [ADR-010](adr_rag_architecture.md#adr-010))

| Ступень | Q&A | Synthesis | Learning Plan |
|---------|-----|-----------|---------------|
| Classify | 500 ms | 500 ms | 500 ms |
| Rewrite | 800 ms | 800 ms | 800 ms |
| Retrieve | 300 ms | 500 ms (two-level) | 500 ms + graph lookup |
| Rerank | 400 ms | 400 ms | 400 ms |
| Generate | 3 000 ms | 5 000 ms | 5 000 ms |
| **Сумма ступеней** | **5 000 ms** | **7 200 ms** | **7 200 ms** |

**Целевые p95 из ADR-010:** qa ≤ 5 000 ms, synthesis ≤ 8 000 ms. **Целевые p95 из tasklist (§2.5a):** qa ≤ 5 с, synthesis ≤ 10 с. Разница между суммой бюджетов (7 200 ms) и p95-целью (8 000–10 000 ms) — запас на сетевые задержки и вариативность LLM-провайдера.

### 5.2. Оптимизации в рамках текущего стека

Проект использует облачный LLM через OpenRouter ([ADR-003](adr.md#adr-003)). vLLM, TensorRT и другие инструменты локального инференса неприменимы — нет GPU, нет локальных моделей. Оптимизации сосредоточены на другом:

**Оптимизация 1: Дешёвые модели для вспомогательных ступеней.**
Classify и Rewrite не требуют мощной модели. Использование дешёвой модели для этих ступеней экономит ~90% стоимости и ~50% latency. В Settings уже добавлены поля `rewrite_model` и `classifier_model` (Блок 0.5, реализован). По умолчанию модель основного LLM (`llm_model`, default `gpt-5-mini`). При подключении Classify/Rewrite (итерация 12) рекомендуется указать дешёвую модель через `.env`.

**Оптимизация 2: Keyword detection без LLM.**
Для ступени Classify: если запрос содержит паттерн аббревиатуры/ID (регулярное выражение: `r'[A-Z]{2,}[-_]?\d+'` или всё в верхнем регистре), тип `keyword` определяется без LLM-вызова. Экономит 500 ms и ~$0.0001 на таких запросах.

**Оптимизация 3: Кэширование retrieval cache.**
Уже реализовано: `retrieval_cache.py` с LRU + TTL для query engine и базовых сервисов (Chroma client, embed model, LLM, index). Планируемое расширение (итерация 18): кэширование результатов retrieval по нормализованному query (хэш rewritten_query → cached nodes). Инвалидация при reindex. Потребуется добавить в Settings: `ENABLE_RETRIEVAL_RESULT_CACHE=true/false` (сейчас отсутствует).

**Оптимизация 4: Параллельный retrieval.**
При hybrid search BM25 и vector search уже выполняются параллельно через `ThreadPoolExecutor`, что сокращает latency retrieval-ступени и соответствует плану итерации 10.

**Оптимизация 5: Streaming ответа.**
Для длинных ответов (synthesis, learning plan) — streaming через SSE (Server-Sent Events) в FastAPI. Пользователь видит ответ посимвольно, а не ждёт полной генерации. Не сокращает total latency, но кардинально улучшает perceived latency. Реализуется в итерации 18 (Production Hardening).

### 5.3. Cost budget (на основе [ADR-010](adr_rag_architecture.md#adr-010))

Стоимости ориентировочные, зависят от конкретных моделей через OpenRouter. «cheap» = `classifier_model` / `rewrite_model` из Settings (fallback на `llm_model`), «main» = `llm_model` (default: `gpt-5-mini`).

| Тип запроса | LLM-вызовы | Примерная стоимость |
|-------------|-----------|-------------------|
| Q&A | classify (cheap) + rewrite (cheap) + generate (main) | ~$0.01 |
| Keyword | classify (regex, $0) + generate (main) | ~$0.008 |
| Synthesis | classify + rewrite + generate (main, longer context) | ~$0.04 |
| Learning Plan | classify + rewrite + graph lookup ($0) + generate (main) | ~$0.04 |
| Self-correction retry | +1 cheap (relevance check) + 1 cheap (rewrite) | +$0.0006 |

При 20 запросах/день: ~$0.20–0.50/день, ~$6–15/месяц. Приемлемо для персонального использования.

---

## 6. Стратегия тестирования расширений

### 6.1. Regression при расширении pipeline

При добавлении каждой новой ступени — regression test:

| Что добавляется | Regression check |
|----------------|-----------------|
| Hybrid retrieval (ит. 10, реализовано) | Eval dataset: `qa` тип даёт не хуже baseline по всем метрикам. Сравнение `vector_only` vs `hybrid` зафиксировано и описано в `doc/eval_hybrid_vs_vector.md` |
| Classify + Rewrite (ит. 12) | `qa` промпт даёт те же результаты, что текущий `QA_PROMPT` из `pipeline_factory.py` |
| Synthesis (ит. 13) | `qa` тип не затронут; synthesis eval ≥ 3 абзацев, со ссылками |
| Self-correction (ит. 17) | Faithfulness ≥ baseline + 5%; запросы с `ENABLE_SELF_CORRECTION=false` обрабатываются как раньше |
| Multi-turn (ит. 19) | Запросы без `session_id` обрабатываются как раньше |

Принцип: **новый тип запроса не должен деградировать существующие типы.** [ADR-013](adr_rag_architecture.md#adr-013) устанавливает порог: деградация > 5% — блокер.

### 6.2. Тестирование графа знаний

| Тест | Что проверяет |
|------|-------------|
| `get_prerequisites("prompt_injection")` возвращает `["guardrails", "input_validation"]` | Корректность направленных связей |
| `topological_sort(["advanced_rag", "basic_rag", "embeddings"])` → `["embeddings", "basic_rag", "advanced_rag"]` | Правильность сортировки |
| Циклическая зависимость → graceful fallback без crash | Устойчивость к ошибкам в данных |
| Добавление нового документа → граф обновляется при reindex | Consistency с индексом |

### 6.3. Тестирование multi-turn

| Тест | Что проверяет |
|------|-------------|
| Q1: «Что такое RAG?» → Q2: «А какие у него ограничения?» | «него» → «RAG» (разрешение анафоры) |
| Q1: «Расскажи про безопасность» → Q2: «А что ещё?» | «ещё» → расширение предыдущего ответа |
| Q1 без session_id → обработка как обычный qa | Обратная совместимость |
| 50 сообщений в сессии → sliding window, нет OOM | Устойчивость к длинным диалогам |

---

## 7. Сводка: что этот документ добавляет к ADR

| Тема | ADR покрывает | Этот документ добавляет |
|------|-------------|------------------------|
| Pipeline | ADR-010: 5 ступеней, latency budget | Контракт `QueryContext`, код pipeline runner, стратегия поэтапного внедрения, связь с pipeline_factory |
| Graceful degradation | — | Fallback-поведение каждой ступени при ошибке/timeout, `run_step_safe` паттерн |
| Config migration | ADR-005: pydantic-settings | Приоритет конфигурации: QueryContext > overrides > config defaults. Потребуется расширение `PipelineOverrides` (`retrieval_mode`) |
| Async/sync | — | Pipeline runner sync, параллелизация внутри ступеней через ThreadPoolExecutor |
| Knowledge Graph | ADR-015: JSON-граф, альтернативы | Абстракция `KnowledgeGraphReader`, код интеграции в pipeline (с корректным extract_concepts_from_query), триггеры миграции на Neo4j |
| Multi-turn | Итерация 19 в tasklist | Архитектура persisted session store, bounded history, condense как отдельная ступень pipeline между classify и rewrite, уровни управления контекстом |
| Self-correction + Multi-turn | ADR-014: corrective RAG | Порядок взаимодействия: condensing → rewrite → retrieve → relevance check → retry → generate |
| Производительность | ADR-010: latency/cost budgets | Конкретные оптимизации (cheap models, regex classify, parallel retrieval, streaming), cost per query type |
| Тестирование | ADR-013: трёхслойная eval strategy | Regression policy для каждой итерации, тест-кейсы для графа, self-correction и multi-turn |
| Альтернативы стека | ADR-001, 002, 003: обоснования | Триггеры для пересмотра решений (когда JSON → SQLite → Neo4j) |

Все предложения в этом документе **совместимы** с принятыми ADR и roadmap в tasklist.md. Существенная часть foundation уже реализована: feature flags, модели по ступеням, hybrid retrieval, smart ingestion, query understanding и knowledge workflows. Оставшиеся предложения не требуют пересмотра существующих решений — только их детализацию и реализацию в итерациях 14–19.
