# Инженерные дисциплины MLOps + LLMOps + RAGOps для RAG / LLM-проекта

## Версия документа

**Статус:** Draft / Recommended (rev. 2026-05-23 — critical review + balance-plan alignment)
**Проект:** `hometutor` / локальная RAG-платформа
**Целевая архитектура:** Smart Router RAG: `fast + hybrid + graph` → GraphRAG Global Analytics
**Назначение:** описать инженерную, архитектурную и организационную модель развития RAG / LLM-системы, включая новые роли MLOps, LLMOps, RAGOps и их включение в проектную оркестрацию.

> **Совместимость с активным планом:** этот документ обязан читаться вместе с [`doc/next/localhost_balance_course_delight_plan.md`](../next/localhost_balance_course_delight_plan.md). Балансовый план задаёт приоритетные тесты и приёмочные критерии, к которым Ops-дисциплины должны привязываться **первыми**. Конфликты решаются в пользу балансового плана и существующих ADR ([`doc/adr.md`](../adr.md)).

---

## 0. Critical Review Log (что было исправлено в rev. 2026-05-23)

| # | Где | Что было не так | Что исправлено |
|---|---|---|---|
| E1 | §14 RACI | В строках `Vector index`, `BM25/RRF`, `Reranker`, `Prompt registry`, `Token budget`, `Retrieval trace`, `Golden dataset`, `Eval reports` стояло несколько `A/R` в одной строке — нарушение базового инварианта RACI (один Accountable). | Один `A` на строку, остальные → `R`/`C`. См. §14. |
| E2 | §5.6 Router metrics | В списке метрик ошибочно отсутствовала `false hybrid rate` (4 режима маршрутизации, метрик ошибок только 3). | Метрика добавлена. |
| E3 | §17 Структура команды | Designer как роль не упоминалась ни в minimal/optimal/mature team, хотя в `process.md` это полноценный шаг 3b. | Designer добавлен. Architect в §17.3 разведён с AI Platform Lead. |
| E4 | §23 Project structure | Структура аспирационная (`app/rag/`, `app/llm/`, `app/ops/`, `app/graph/`), не отражает реальные пути проекта (`app/provider.py`, `app/config.py`, `app/routers/`, `app/ui/`). | Раздел помечен как reference layout, добавлен §34 «Mapping на реальный hometutor». |
| E5 | §19 vs §30 | §19 содержит фазы 0–8 (9 фаз), §30 — 8 шагов summary; нумерация плыла. | Summary §30 пронумерован 0–8, а итоговые 8 «steps» в §28 отделены как практические шаги внедрения, не фазы. |
| E6 | §5.3 example JSON | Поля `vector_index` / `bm25_index` в JSON не совпадали по форме с описанными выше (`embedding_dimension`, `chunking_strategy`). | Пример нормализован. |
| E7 | §6.6 Fallback Strategy | Не различался primary chat LLM и secondary LLM channels — конфликт с фундаментом балансового плана (см. §0 балансового плана). | Введён §31 «Primary chat LLM vs secondary LLM channels», fallback политика расщеплена. |
| E8 | Отсутствовала привязка к LOCAL_STRICT / BALANCED / CLOUD_FAST | Балансовый план — единственный активный roadmap, ops-документ его не упоминал. | Введён §32 «Profile-aware Ops policy». |
| E9 | Course-aware retrieval не было в RAGOps | RAGOps описана корпус-широко, но Course Workspace требует scoped retrieval и persistent upload в `data/docs/<course>/`. | Введён §33 «Course Delight Loop ownership matrix». |
| E10 | Phase 0 §19 | Фраза «не пересоздавать Chroma client на каждый запрос» относится к старому состоянию и могла быть выполнена; нет проверки. | Phase 0 переформулирована как «verify and seal» с пометкой о привязке к balance plan Phase 1. |

Если что-то из перечисленного снова разъедется с реальностью кода — обновить эту таблицу одной строкой и проставить дату в шапке.

---

# 1. Executive Summary

Проект `hometutor` развивается из локальной RAG-системы в инженерную платформу для работы с документами, знаниями, LLM, retrieval, graph analysis и учебно-аналитическими сценариями.

Главный переход:

```text
От:   простого vector RAG
К:    Smart Router RAG + Hybrid Retrieval + Graph Mode + Global GraphRAG Analytics
```

Для такого уровня системы недостаточно просто «подключить LLM» или «добавить Chroma». Необходимы три эксплуатационные дисциплины:

```text
MLOps  — управляет ML-моделями, embeddings, reranker, router, eval.
LLMOps — управляет LLM, промптами, токенами, latency, safety, генерацией.
RAGOps — управляет документами, chunking, индексами, retrieval, citations, качеством RAG.
```

Вместе они превращают RAG-проект из экспериментальной демки в управляемую инженерную систему.

Ключевая целевая формула:

```text
Smart Router RAG
+ Hybrid Retrieval
+ Graph Mode
+ Prompt Registry
+ Retrieval Trace
+ Golden Dataset
+ Metrics Dashboard
+ MLOps / LLMOps / RAGOps roles
= инженерная RAG-платформа
```

---

# 2. Контекст проекта

## 2.1. Исходная точка

`hometutor` — локальный RAG-проект, ориентированный на работу с:

- PDF;
- DOCX;
- Markdown;
- HTML;
- технической документацией;
- учебными материалами;
- архитектурными документами;
- транскриптами лекций;
- локальными LLM;
- embeddings;
- reranker;
- Chroma / FAISS;
- FastAPI endpoint `/ask`.

Базовый pipeline:

```text
Документы
  ↓
Извлечение текста
  ↓
Очистка / нормализация
  ↓
Chunking
  ↓
Embeddings
  ↓
Vector Store
  ↓
Retriever
  ↓
Reranker
  ↓
Context Builder
  ↓
LLM
  ↓
Ответ + источники
```

## 2.2. Основная проблема

Обычный vector RAG хорошо работает для простых вопросов, но плохо справляется со сценариями:

- «сравни подходы»;
- «найди противоречия»;
- «построй карту знаний»;
- «объясни причинно-следственные связи»;
- «какие архитектурные риски есть в проекте»;
- «какие темы повторяются во всех документах»;
- «почему компонент A влияет на компонент B».

Для таких задач нужна не одна retrieval-стратегия, а адаптивная архитектура.

## 2.3. Целевая стратегия

Целевая стратегия — не заменить все на GraphRAG, а построить маршрутизируемую RAG-платформу:

```text
Simple question        → Fast RAG
Detailed question      → Hybrid RAG
Relationship question  → Graph RAG
Whole corpus analysis  → Global GraphRAG Analytics
```

---

# 3. RAG-пайплайн: от текущего состояния к целевой архитектуре

## 3.1. Naive Vector RAG

Классический стартовый pipeline:

```text
User Query
  ↓
Embedding
  ↓
Vector Search
  ↓
Top-K Chunks
  ↓
LLM Answer
```

Преимущества:

- простой;
- быстрый;
- понятный;
- хорошо подходит для MVP;
- легко отлаживать на старте.

Ограничения:

- плохо находит точные термины, если embedding не сработал;
- не объединяет лексический и семантический поиск;
- не понимает связи между сущностями;
- плохо работает с вопросами по всему корпусу;
- может возвращать похожие, но не самые полезные chunks;
- плохо объясняет причинные связи.

## 3.2. Hybrid RAG

Следующий уровень:

```text
User Query
  ↓
BM25 Search + Vector Search
  ↓
RRF Merge
  ↓
Reranker
  ↓
Context Builder
  ↓
LLM Answer
```

Hybrid RAG объединяет:

- BM25 / lexical search;
- semantic vector search;
- Reciprocal Rank Fusion;
- reranking;
- metadata filtering;
- context compression.

Это должен быть основной production backbone проекта.

## 3.3. Graph RAG mode

Graph RAG mode используется для вопросов о связях:

```text
User Query
  ↓
Query Entity Extraction
  ↓
Entity Matching
  ↓
Graph Neighborhood Retrieval
  ↓
Linked Chunks Retrieval
  ↓
Hybrid Retrieval Optional
  ↓
Context Builder
  ↓
LLM Answer
```

Этот режим нужен для вопросов:

- «как связаны X и Y»;
- «почему A влияет на B»;
- «какие компоненты участвуют в цепочке»;
- «какие зависимости есть между темами»;
- «какой root cause у проблемы».

## 3.4. GraphRAG Global Analytics

Отдельный тяжелый режим:

```text
Documents
  ↓
Chunks
  ↓
Entity / Relation Extraction
  ↓
Knowledge Graph
  ↓
Community Detection
  ↓
Community Summaries
  ↓
Global Map-Reduce Answer
```

Используется для:

- карты знаний;
- анализа всего корпуса;
- поиска противоречий;
- архитектурного risk review;
- global summary;
- topic dependency map;
- learning path generation.

Главный принцип:

```text
GraphRAG не является default pipeline.
GraphRAG — это отдельный аналитический режим.
```

---

# 4. Целевая архитектура Smart Router RAG

## 4.1. Архитектурная схема

```text
                          ┌────────────────────┐
                          │     User Query     │
                          └─────────┬──────────┘
                                    ↓
                          ┌────────────────────┐
                          │ Query Normalizer   │
                          └─────────┬──────────┘
                                    ↓
                          ┌────────────────────┐
                          │ Smart RAG Router   │
                          └─────────┬──────────┘
                                    ↓
        ┌───────────────────────────┼───────────────────────────┐
        ↓                           ↓                           ↓
┌────────────────┐          ┌────────────────┐          ┌────────────────┐
│ Fast RAG       │          │ Hybrid RAG     │          │ Graph RAG      │
│ Vector only    │          │ BM25+Vector    │          │ Graph-aware    │
│ Low latency    │          │ RRF+Reranker   │          │ Relations      │
└───────┬────────┘          └───────┬────────┘          └───────┬────────┘
        ↓                           ↓                           ↓
        └───────────────────────────┼───────────────────────────┘
                                    ↓
                          ┌────────────────────┐
                          │ Context Builder    │
                          └─────────┬──────────┘
                                    ↓
                          ┌────────────────────┐
                          │ Answer Generator   │
                          └─────────┬──────────┘
                                    ↓
                          ┌────────────────────┐
                          │ Answer + Evidence  │
                          └────────────────────┘
```

## 4.2. Режимы

| Режим | Назначение | Главный trade-off |
|---|---|---|
| `fast` | быстрые фактологические вопросы | быстро, но не глубоко |
| `hybrid` | основной качественный режим | лучше качество, выше latency |
| `graph` | связи, зависимости, причины | глубже, но сложнее |
| `global_graph` | анализ всего корпуса | мощно, но дорого и медленно |

## 4.3. Query Router

Router выбирает режим:

```text
fast | hybrid | graph | global_graph
```

На старте он может быть rule-based:

- короткие терминологические вопросы → `fast`;
- сравнения и подробные инструкции → `hybrid`;
- связи, причины, зависимости → `graph`;
- весь корпус, карта знаний, противоречия → `global_graph`.

Затем Router можно усилить LLM-классификатором и eval dataset.

---

# 5. MLOps в RAG / LLM-проекте

## 5.1. Определение

MLOps в проекте `hometutor` — это дисциплина управления ML-компонентами RAG-системы:

- embedding models;
- reranker models;
- router classifier;
- entity extractor;
- relation extractor;
- evaluation models;
- indexing experiments;
- quality metrics;
- model and index versions.

Главный вопрос MLOps:

```text
Можем ли мы воспроизводимо понять, почему качество модели или retrieval изменилось?
```

## 5.2. Зоны ответственности MLOps

MLOps отвечает за:

1. Версионирование моделей.
2. Версионирование embeddings.
3. Версионирование reranker.
4. Эксперименты с chunking и retrieval.
5. Offline evaluation.
6. Regression testing качества.
7. Model registry.
8. Dataset registry.
9. Index registry.
10. Rollback моделей и индексов.
11. Метрики качества.
12. Сравнение fast/hybrid/graph режимов.

## 5.3. Что версионирует MLOps

```text
embedding_model
embedding_dimension
reranker_model
router_version
entity_extractor_version
relation_extractor_version
chunking_strategy
index_version
eval_dataset_version
retrieval_config_version
```

Пример:

```json
{
  "run_id": "eval_2026_05_23_001",
  "embedding_model": "bge-m3",
  "embedding_dimension": 1024,
  "reranker_model": "bge-reranker-base",
  "chunking_strategy": "sentence_window_v2",
  "vector_index_version": "chroma_v12",
  "bm25_index_version": "bm25_v5",
  "eval_dataset_version": "golden_rag_v3"
}
```

> Поля в JSON должны точно совпадать со списком `index registry` (см. §24.3) — если они расходятся, реестр — источник истины.

## 5.4. MLOps для embeddings

Embeddings определяют качество semantic retrieval.

MLOps должен контролировать:

- модель embeddings;
- размерность;
- нормализацию;
- совместимость индекса;
- скорость batch indexing;
- качество retrieval;
- языковую поддержку;
- domain performance.

Критическое правило:

```text
Новая embedding model = новый vector index.
```

## 5.5. MLOps для reranker

Reranker должен использоваться осознанно.

Метрики:

- reranker latency;
- reranker uplift;
- top-N quality;
- cost per query;
- failure rate;
- memory usage.

Решение по reranker должно быть режимным:

```text
fast   → reranker обычно off
hybrid → reranker on
graph  → reranker optional
global → reranker зависит от сценария
```

## 5.6. MLOps для Smart Router

Router — это отдельный ML/AI-компонент.

Нужно измерять:

- router accuracy (overall);
- false fast rate (выбран `fast`, нужен был `hybrid`/`graph`/`global_graph`);
- false hybrid rate (выбран `hybrid`, нужен был другой режим);
- false graph rate;
- false global_graph rate;
- manual override rate;
- confidence distribution.

Инвариант: количество error-rate метрик должно совпадать с количеством маршрутов (сейчас 4 → 4 false-rate метрики). Если добавится новый маршрут, добавить соответствующую метрику.

Пример eval-записи:

```json
{
  "question": "Как связаны ChromaDB, VectorStoreIndex и /ask?",
  "expected_mode": "graph",
  "actual_mode": "hybrid",
  "is_correct": false,
  "error_type": "graph_false_negative"
}
```

---

# 6. LLMOps в RAG / LLM-проекте

## 6.1. Определение

LLMOps — это дисциплина управления LLM-вызовами, промптами, токенами, latency, safety, structured output и качеством генерации.

Главный вопрос LLMOps:

```text
Можем ли мы стабильно получать качественные ответы от LLM, контролируя контекст, стоимость, промпты и галлюцинации?
```

## 6.2. Зоны ответственности LLMOps

LLMOps отвечает за:

1. Prompt registry.
2. Prompt versioning.
3. LLM model selection.
4. Token budget.
5. Context compression.
6. Fallback strategy.
7. Structured output.
8. JSON validation.
9. Hallucination control.
10. Safety rules.
11. Latency and token monitoring.
12. LLM call tracing.
13. Prompt regression tests.
14. Model routing.

## 6.3. Prompt Registry

Промпты должны быть отдельными артефактами:

```text
prompts/
  answer/
    rag_answer_v1.md
    rag_answer_v2.md
  router/
    router_v1.md
  graph/
    entity_extraction_v1.md
    relation_extraction_v1.md
  eval/
    faithfulness_judge_v1.md
```

Каждый ответ должен знать:

```json
{
  "prompt_name": "rag_answer",
  "prompt_version": "v2",
  "llm_model": "qwen2.5-coder-32b",
  "temperature": 0.1,
  "max_tokens": 2048
}
```

## 6.4. Token Budget Manager

LLMOps должен управлять бюджетом контекста:

```text
system_prompt_tokens
conversation_history_tokens
retrieved_context_tokens
graph_context_tokens
answer_budget_tokens
safety_margin_tokens
```

Пример:

```json
{
  "model_context_window": 32768,
  "system_prompt_budget": 1200,
  "history_budget": 3000,
  "retrieved_context_budget": 18000,
  "graph_context_budget": 4000,
  "answer_budget": 4000,
  "safety_margin": 2500
}
```

## 6.5. Context Compression

Контекст перед LLM должен проходить compression:

- deduplication;
- reranking;
- MMR;
- chunk trimming;
- metadata-aware pruning;
- graph neighborhood pruning;
- summary replacement;
- citation preserving.

Правильная цель:

```text
Не максимум контекста, а максимум полезного evidence на токен.
```

## 6.6. Fallback Strategy

Для разных задач нужны разные модели:

| Задача | Channel kind | Рекомендуемый уровень модели |
|---|---|---|
| Router | secondary | small / fast |
| Query rewrite | secondary | small / medium |
| Entity extraction | secondary | medium |
| Relation extraction | secondary | medium / strong |
| Fast answer | **primary chat** | local fast |
| Hybrid answer | **primary chat** | medium / strong |
| Global synthesis | **primary chat** | strong |
| Eval judge | secondary | strong offline |

**Channel kind** напрямую определяет fallback политику в `hometutor`:

- **primary chat** — обслуживает `/ask`, tutor, course mission. Идёт через `app/provider.py` и подчиняется балансовому профилю (`LOCAL_STRICT` / `BALANCED` / `CLOUD_FAST`) + soft/hard timeout (см. §31 и Phase 2 балансового плана).
- **secondary** — отдельные клиенты (`QUIZ_LLM_*`, `SSR_LLM_*`, `INGESTION_MODEL`, `CLASSIFIER_MODEL`, `REWRITE_MODEL`, `EVALUATE_MODEL`, `EVAL_JUDGE_LLM`, `LLAMAINDEX_METADATA_FALLBACK_MODEL`). Работают по существующему circuit breaker (`LLM_LOCAL_CB_*`) и **не** включаются в profile-fallback в рамках текущего пакета.

Эту классификацию нельзя терять при последующих рефакторах — это контракт ops с балансовым планом.

## 6.7. LLM Call Trace

Каждый LLM-вызов логируется:

```json
{
  "operation": "answer_generation",
  "model": "qwen2.5-coder-32b",
  "prompt_version": "rag_answer_v3",
  "input_tokens": 8900,
  "output_tokens": 1300,
  "latency_ms": 5200,
  "temperature": 0.1,
  "status": "success"
}
```

---

# 7. RAGOps в RAG / LLM-проекте

## 7.1. Определение

RAGOps — это дисциплина эксплуатации retrieval-augmented generation системы.

Она управляет всем путем:

```text
documents → chunks → indexes → retrieval → context → answer → citations → evaluation
```

Главный вопрос RAGOps:

```text
Достаем ли мы правильный контекст, и можно ли доказать ответ источниками?
```

## 7.2. Зоны ответственности RAGOps

RAGOps отвечает за:

1. Document registry.
2. Chunk registry.
3. Index registry.
4. Document parsing quality.
5. Chunking strategy.
6. Metadata quality.
7. Retrieval trace.
8. Citation correctness.
9. Context precision.
10. Context recall.
11. Empty retrieval rate.
12. Duplicate context rate.
13. Reindex pipeline.
14. Incremental indexing.
15. Source provenance.
16. RAG evaluation.

## 7.3. DocumentOps

Для каждого документа нужно хранить:

```json
{
  "document_id": "doc_001",
  "file_name": "lesson_01_rag.pdf",
  "relative_path": "data/lectures/rag/lesson_01_rag.pdf",
  "content_hash": "sha256:...",
  "file_type": "pdf",
  "pages": 42,
  "language": "ru",
  "status": "indexed",
  "indexed_at": "2026-05-23T10:30:00"
}
```

## 7.4. ChunkOps

Для каждого chunk:

```json
{
  "chunk_id": "doc_001_chunk_023",
  "document_id": "doc_001",
  "chunk_index": 23,
  "text_hash": "sha256:...",
  "page": 12,
  "section": "Hybrid Retrieval",
  "chunking_strategy": "sentence_window",
  "chunk_size": 1200,
  "chunk_overlap": 150
}
```

## 7.5. IndexOps

Индексы должны быть совместимы друг с другом:

```text
Vector index
BM25 index
Graph index
Summary index
Community index
```

Критическое правило:

```text
Все индексы должны ссылаться на одинаковые chunk_id.
```

## 7.6. RetrievalOps

Retrieval trace должен показывать:

- какие chunks нашел vector search;
- какие chunks нашел BM25;
- как RRF объединил результаты;
- что выбрал reranker;
- какие entities нашел graph retriever;
- какие chunks попали в final context.

## 7.7. CitationOps

Ответ должен быть проверяемым.

Каждый факт должен иметь связь с:

- document_id;
- file name;
- page;
- section;
- chunk_id;
- text span.

---

# 8. Связь MLOps + LLMOps + RAGOps по слоям архитектуры

## 8.1. Слой Ingestion

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| загрузка документов |  |  | ✅ |
| парсинг PDF/DOCX |  |  | ✅ |
| очистка текста |  |  | ✅ |
| language detection | ✅ |  | ✅ |
| document registry |  |  | ✅ |
| content hash |  |  | ✅ |

## 8.2. Слой Chunking

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| выбор chunk_size | ✅ |  | ✅ |
| chunk overlap | ✅ |  | ✅ |
| semantic chunking | ✅ | ✅ | ✅ |
| chunk metadata |  |  | ✅ |
| chunk quality eval | ✅ |  | ✅ |

## 8.3. Слой Embeddings / Indexing

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| embedding model | ✅ |  | ✅ |
| vector index | ✅ |  | ✅ |
| BM25 index |  |  | ✅ |
| index versioning | ✅ |  | ✅ |
| reindex pipeline | ✅ |  | ✅ |

## 8.4. Слой Retrieval

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| vector search | ✅ |  | ✅ |
| BM25 search |  |  | ✅ |
| RRF | ✅ |  | ✅ |
| reranker | ✅ |  | ✅ |
| retrieval trace |  |  | ✅ |
| retrieval eval | ✅ |  | ✅ |

## 8.5. Слой Graph

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| entity extraction | ✅ | ✅ | ✅ |
| relation extraction | ✅ | ✅ | ✅ |
| graph normalization | ✅ |  | ✅ |
| graph retrieval | ✅ |  | ✅ |
| graph answer prompt |  | ✅ | ✅ |
| relation evidence |  |  | ✅ |

## 8.6. Слой LLM Answer

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| model selection | ✅ | ✅ |  |
| prompt version |  | ✅ |  |
| token budget |  | ✅ | ✅ |
| context builder |  | ✅ | ✅ |
| hallucination control | ✅ | ✅ | ✅ |
| citations |  |  | ✅ |

## 8.7. Слой Evaluation

| Задача | MLOps | LLMOps | RAGOps |
|---|---:|---:|---:|
| golden dataset | ✅ | ✅ | ✅ |
| answer relevance | ✅ | ✅ | ✅ |
| faithfulness | ✅ | ✅ | ✅ |
| context precision | ✅ |  | ✅ |
| citation accuracy |  |  | ✅ |
| regression testing | ✅ | ✅ | ✅ |

---

# 9. Роли в проекте

## 9.1. Почему нужны новые роли

В классическом backend-проекте достаточно ролей:

- Backend Developer;
- DevOps Engineer;
- QA Engineer;
- System Analyst;
- Architect;
- Product Owner.

В RAG / LLM-проекте появляются новые зоны неопределенности:

- качество retrieval;
- качество embeddings;
- версионирование индексов;
- управление prompt templates;
- контроль hallucinations;
- оценка faithfulness;
- graph extraction;
- LLM cost/latency;
- evaluation datasets;
- model routing.

Эти зоны не закрываются полностью ни классическим Backend, ни DevOps, ни QA. Поэтому нужны роли или хотя бы responsibility areas:

```text
MLOps Engineer
LLMOps Engineer
RAGOps Engineer
```

В маленьком проекте это могут быть не отдельные люди, а «шляпы» одного-двух инженеров. В зрелом проекте — отдельные роли.

---

# 10. Роль MLOps Engineer

## 10.1. Миссия роли

MLOps Engineer отвечает за воспроизводимость, измеримость и управляемость ML-компонентов системы.

Главный вопрос роли:

```text
Почему эта версия retrieval/model лучше или хуже предыдущей?
```

## 10.2. Зона ответственности

- embedding models;
- reranker models;
- router classifier;
- entity/relation extraction models;
- eval datasets;
- experiment tracking;
- model registry;
- index registry;
- quality regression tests;
- model rollout/rollback.

## 10.3. Типовые задачи

- сравнить embeddings `model_a` vs `model_b`;
- измерить uplift от reranker;
- построить eval report;
- настроить MLflow / experiment logs;
- добавить regression suite для retrieval;
- зафиксировать модельные версии;
- подготовить rollback индекса;
- оценить degradation после изменения chunking.

## 10.4. Артефакты MLOps

- model registry;
- index registry;
- eval reports;
- experiment reports;
- model comparison matrix;
- regression dashboard;
- router confusion matrix;
- reranker uplift report.

## 10.5. KPI / метрики

- retrieval quality uplift;
- router accuracy;
- reranker uplift;
- eval pass rate;
- model rollback time;
- reproducibility rate;
- experiment trace completeness.

---

# 11. Роль LLMOps Engineer

## 11.1. Миссия роли

LLMOps Engineer отвечает за стабильную, контролируемую и безопасную работу LLM-слоя.

Главный вопрос роли:

```text
Почему LLM дала именно такой ответ, каким prompt/model/context это было вызвано, и можно ли это повторить?
```

## 11.2. Зона ответственности

- prompt registry;
- prompt versioning;
- prompt tests;
- LLM routing;
- token budget;
- context compression;
- fallback strategy;
- structured outputs;
- JSON validation;
- latency/cost monitoring;
- hallucination mitigation;
- safety rules.

## 11.3. Типовые задачи

- создать prompt contract для answer generation;
- настроить prompt versioning;
- добавить token budget manager;
- оптимизировать long context;
- сделать fallback с local model на stronger model;
- добавить JSON schema validation для extractor;
- снизить hallucinations;
- измерить token usage по режимам.

## 11.4. Артефакты LLMOps

- prompt registry;
- prompt changelog;
- token budget policy;
- LLM usage report;
- model routing policy;
- fallback matrix;
- structured output schemas;
- prompt regression report.

## 11.5. KPI / метрики

- hallucination rate;
- faithfulness score;
- prompt regression pass rate;
- average input tokens;
- average output tokens;
- LLM latency p50/p95;
- fallback success rate;
- structured output validity rate.

---

# 12. Роль RAGOps Engineer

## 12.1. Миссия роли

RAGOps Engineer отвечает за качество retrieval, надежность индексов, корректность источников и проверяемость ответов.

Главный вопрос роли:

```text
Достала ли система правильные документы, правильные chunks и корректно ли сослалась на источники?
```

## 12.2. Зона ответственности

- document registry;
- chunk registry;
- chunking strategy;
- metadata quality;
- vector index;
- BM25 index;
- graph index;
- retrieval trace;
- context builder;
- citation engine;
- reindex pipeline;
- incremental indexing;
- retrieval eval.

## 12.3. Типовые задачи

- добавить `document_id`, `chunk_id`, `content_hash`;
- улучшить chunking для PDF;
- настроить BM25 + vector + RRF;
- добавить retrieval trace;
- сделать citation engine;
- измерить context precision;
- найти причины плохого retrieval;
- настроить reindex only changed documents;
- отладить graph retrieval.

## 12.4. Артефакты RAGOps

- document registry;
- chunk registry;
- index registry;
- retrieval traces;
- citation reports;
- context quality reports;
- reindex logs;
- failed parsing reports;
- source provenance map.

## 12.5. KPI / метрики

- context precision;
- context recall;
- citation accuracy;
- empty retrieval rate;
- duplicate context rate;
- average chunks per answer;
- indexing failure rate;
- reindex duration;
- stale index rate.

---

# 13. Связка новых ролей с классическими ролями

## 13.1. Backend Developer

Backend Developer реализует API, сервисы, интеграции, storage, business logic.

Связка:

- с RAGOps — endpoints `/ask`, `/index`, `/trace`, `/graph`;
- с LLMOps — LLM client, prompt loading, fallback;
- с MLOps — eval runner, model registry API.

## 13.2. DevOps Engineer

DevOps отвечает за инфраструктуру, деплой, observability, CI/CD.

Связка:

- с MLOps — model/index artifacts deployment;
- с LLMOps — LLM serving, GPU, latency monitoring;
- с RAGOps — storage, indexes, reindex jobs.

## 13.3. Data Engineer

Data Engineer отвечает за pipeline данных.

Связка:

- с RAGOps — ingestion, parsing, document registry;
- с MLOps — dataset versioning;
- с LLMOps — data preparation для prompts/eval.

## 13.4. ML Engineer

ML Engineer отвечает за модели, embeddings, reranker, extractors.

Связка:

- с MLOps — training/evaluation;
- с RAGOps — retrieval quality;
- с LLMOps — model behavior and inference constraints.

## 13.5. AI / LLM Engineer

AI / LLM Engineer проектирует LLM workflows.

Связка:

- с LLMOps — prompts, chains, agents;
- с RAGOps — context builder;
- с MLOps — eval and model comparison.

## 13.6. QA Engineer

QA должен расшириться до AI QA.

Новые обязанности:

- проверка faithfulness;
- проверка citations;
- golden dataset;
- regression prompts;
- adversarial questions;
- no-answer tests;
- mode routing tests.

## 13.7. Architect

Architect отвечает за общую целостность:

- Smart Router RAG architecture;
- mode boundaries;
- graph strategy;
- ops boundaries;
- ADR;
- NFR;
- risks;
- evolutionary roadmap.

## 13.8. Product Owner / Domain Expert

PO / domain expert определяет:

- какие ответы полезны;
- какие документы важны;
- какие сценарии приоритетны;
- какие ошибки критичны;
- какие eval-вопросы отражают реальность.

---

# 14. RACI-матрица ответственности

**Инвариант RACI:** ровно один `A` (Accountable) на строку. Если найдена строка с двумя `A` — это баг матрицы, не «разделение ответственности».

| Активность | Architect | Backend | DevOps | MLOps | LLMOps | RAGOps | QA | PO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Smart Router architecture | **A** | C | C | C | C | C | C | I |
| `/ask` API | C | **A** | C | I | C | R | C | I |
| Vector index | C | R | C | C | I | **A** | C | I |
| BM25 / RRF | C | R | I | C | I | **A** | C | I |
| Reranker | C | R | C | **A** | I | R | C | I |
| Prompt registry | C | R | I | I | **A** | C | C | I |
| Token budget | C | R | I | I | **A** | R | C | I |
| Retrieval trace | C | R | I | C | C | **A** | C | I |
| Golden dataset | C | I | I | R | C | R | **A** | C |
| Eval reports | C | I | I | **A** | R | R | R | C |
| Graph extraction | C | R | I | **A** | R | R | C | I |
| Global GraphRAG | **A** | R | C | R | R | R | C | C |
| Deployment | C | C | **A** | C | C | C | I | I |
| Monitoring dashboards | C | R | **A** | R | R | R | C | I |
| Profile-aware fallback (`LOCAL_STRICT`/`BALANCED`/`CLOUD_FAST`) | C | R | I | I | **A** | C | C | I |
| Course activation contract | C | R | I | I | C | **A** | C | C |
| Course document upload | C | R | I | I | I | **A** | C | C |
| Adaptive next step (deterministic baseline) | C | **A** | I | I | C | R | C | C |
| Localhost readiness banner | C | R | C | I | R | R | C | C |

Новые строки внизу таблицы (`Profile-aware fallback` … `Localhost readiness banner`) добавлены для покрытия областей балансового плана. Их Accountable ставится осознанно: profile-fallback — LLMOps, потому что это политика LLM-уровня; course activation/upload — RAGOps, потому что это персистентный рост корпуса.

Обозначения:

```text
A — Accountable, финально отвечает
R — Responsible, выполняет
C — Consulted, консультируется
I — Informed, информируется
```

---

# 15. Включение ролей в проектную оркестрацию

## 15.1. Почему роли должны быть частью orchestration

MLOps, LLMOps и RAGOps не должны работать «после разработки». Они должны быть встроены в жизненный цикл задачи.

Плохая модель:

```text
Сначала разработали фичу → потом кто-то проверил качество RAG.
```

Правильная модель:

```text
Feature idea
  ↓
RAG impact analysis
  ↓
Prompt/model/index impact analysis
  ↓
Implementation
  ↓
Eval
  ↓
Release gate
  ↓
Monitoring
```

## 15.2. Definition of Ready

Перед началом задачи должно быть понятно:

- какой режим RAG затрагивается;
- какие документы используются;
- какой expected behavior;
- нужны ли изменения prompt;
- нужны ли изменения индекса;
- нужны ли eval-вопросы;
- какие метрики должны не ухудшиться.

Пример DoR:

```text
Задача готова к разработке, если:
- определен режим: fast/hybrid/graph/global;
- есть expected behavior;
- есть минимум 3 eval-вопроса;
- понятны затронутые индексы;
- понятны prompt/model changes;
- определены acceptance criteria.
```

## 15.3. Definition of Done

Задача считается завершенной, если:

- код реализован;
- trace добавлен;
- eval пройден;
- prompt version обновлена;
- index compatibility проверена;
- latency не вышла за threshold;
- citations корректны;
- changelog заполнен;
- rollback path понятен.

## 15.4. Release Gates

Перед релизом проверять:

```text
1. Router accuracy не ухудшилась.
2. Context precision не ухудшился.
3. Faithfulness не ухудшился.
4. Citation accuracy не ухудшилась.
5. Latency p95 в пределах нормы.
6. Token usage в пределах бюджета.
7. Index versions совместимы.
8. Prompt versions зафиксированы.
9. Есть rollback.
```

## 15.5. Ритуалы проекта

### Weekly RAG Quality Review

Участники:

- RAGOps;
- MLOps;
- LLMOps;
- QA;
- Architect;
- PO.

Обсуждается:

- top failed questions;
- bad retrieval cases;
- hallucinations;
- broken citations;
- eval trend;
- latency trend;
- next improvement experiments.

### Prompt Review

Участники:

- LLMOps;
- RAGOps;
- QA;
- Domain Expert.

Обсуждается:

- prompt changes;
- regression cases;
- structured output failures;
- hallucination patterns.

### Retrieval Review

Участники:

- RAGOps;
- MLOps;
- Backend;
- Architect.

Обсуждается:

- BM25/vector/RRF performance;
- reranker uplift;
- empty retrieval;
- duplicate chunks;
- chunking issues;
- index freshness.

### Graph Quality Review

Участники:

- RAGOps;
- MLOps;
- LLMOps;
- Architect.

Обсуждается:

- noisy entities;
- duplicated entities;
- weak relations;
- unsupported graph edges;
- graph retrieval quality;
- community summaries.

---

# 16. Рекомендации по созданию новых ролей и внедрению

## 16.1. Не создавать роли сразу как full-time позиции

Для маленького проекта лучше начать с responsibility areas:

```text
Один инженер может временно носить несколько шляп:
- Backend + RAGOps
- ML Engineer + MLOps
- AI Engineer + LLMOps
```

Когда объем растет, выделять роли отдельно.

## 16.2. Этап 1: Назначить ответственных за зоны

Минимально:

| Зона | Ответственный |
|---|---|
| RAGOps Foundation | Backend / RAG Engineer |
| LLMOps Foundation | AI / LLM Engineer |
| MLOps Foundation | ML Engineer / Architect |
| Eval | QA + RAGOps + PO |
| Architecture | Architect |

## 16.3. Этап 2: Ввести артефакты

Создать обязательные артефакты:

```text
1. Document registry
2. Chunk registry
3. Index registry
4. Prompt registry
5. Model registry
6. Retrieval trace
7. Golden dataset
8. Eval reports
9. Release checklist
10. Ops dashboard
```

## 16.4. Этап 3: Встроить роли в workflow задач

Каждая задача должна иметь секции:

```text
RAG impact:
LLM impact:
Model/index impact:
Prompt impact:
Eval impact:
Observability impact:
Rollback plan:
```

## 16.5. Этап 4: Ввести quality gates

Нельзя релизить изменения retrieval/prompt/model без:

- eval run;
- trace verification;
- prompt version update;
- index compatibility check;
- latency check;
- rollback plan.

## 16.6. Этап 5: Разделить роли при росте проекта

Когда проект становится больше, роли разделяются:

| Уровень зрелости | Организация ролей |
|---|---|
| MVP | один инженер закрывает RAGOps/LLMOps/MLOps частично |
| Early product | RAGOps выделен, LLMOps/MLOps частично |
| Production | отдельные owner'ы MLOps, LLMOps, RAGOps |
| Platform | полноценная AI Platform Team |

---

# 17. Рекомендуемая структура команды

## 17.1. Минимальная команда

```text
1 Architect / Tech Lead
1 Backend / RAG Engineer
1 AI / LLM Engineer
1 Designer (part-time)
1 QA / Evaluator
```

Распределение:

- Architect — архитектура и ADR;
- Backend/RAG Engineer — API, retrieval, indexes, course corpus operations;
- AI/LLM Engineer — prompts, LLM, graph extraction;
- Designer — UI-контракты для readiness, course cockpit, status banner (часто part-time, см. [`doc/team_workflow/designer.md`](designer.md));
- QA/Evaluator — golden dataset, regression, quality checks.

## 17.2. Оптимальная команда

```text
1 Architect
1 Backend Engineer
1 RAGOps Engineer
1 LLMOps Engineer
1 MLOps Engineer
1 Designer
1 QA / AI Evaluator
1 Domain Expert / Product Owner
```

## 17.3. Зрелая AI Platform Team

```text
AI Platform Lead             (роль; может выполняться Architect)
Architect
Backend / Platform Engineers
MLOps Engineer
LLMOps Engineer
RAGOps Engineer
Data Engineer
ML Engineer
Designer
AI QA Engineer
Domain Expert / Product Owner
DevOps / SRE
```

**Замечание о Designer:** даже в зрелой AI Platform Team Designer остаётся отдельной ролью — UX-контракт для readiness/course cockpit/AI status banner критичен для North Star балансового плана (см. §3.2 и §3.4 балансового плана).

---

# 18. Интеграция ролей в Smart Router RAG

## 18.1. Fast RAG

| Роль | Ответственность |
|---|---|
| RAGOps | vector retrieval, metadata, citations |
| MLOps | embedding version, retrieval eval |
| LLMOps | fast prompt, token budget |
| Backend | endpoint and performance |
| QA | simple factual tests |

## 18.2. Hybrid RAG

| Роль | Ответственность |
|---|---|
| RAGOps | BM25, vector, RRF, trace |
| MLOps | reranker, experiments, uplift |
| LLMOps | context compression, answer prompt |
| Backend | integration and config |
| QA | quality regression |

## 18.3. Graph RAG

| Роль | Ответственность |
|---|---|
| RAGOps | graph retrieval, evidence chunks |
| MLOps | entity/relation extractor quality |
| LLMOps | extraction prompts, graph answer prompt |
| Architect | graph model and boundaries |
| QA | relationship test cases |

## 18.4. Global GraphRAG

| Роль | Ответственность |
|---|---|
| Architect | global analytics architecture |
| RAGOps | source provenance, community evidence |
| MLOps | community detection, summary quality eval |
| LLMOps | map-reduce prompts, synthesis prompts |
| PO/Domain Expert | validates usefulness |
| QA | contradiction and global summary tests |

---

# 19. Roadmap внедрения

## Phase 0. Stabilize current RAG  (verify-and-seal)

Цель: подтвердить, что фундамент уже стабилен и зафиксировать инварианты.

Tasks:

- verify: Chroma client и `VectorStoreIndex` не пересоздаются на каждый запрос (если регрессия — починить; если уже стабильно — добавить smoke-тест-инвариант);
- verify: config полностью идёт через `get_settings()` (см. [`doc/conventions.md`](../conventions.md));
- verify/add: `document_id`, `chunk_id`, `content_hash` присутствуют в индексе;
- verify/add: retrieval trace включён в `/ask` ответ;
- verify/add: source metadata доступна на UI level.

Owner:

- RAGOps;
- Backend.

> Phase 0 пересекается с balance plan Phase 1 («Balance Profile»): readiness и config должны быть согласованы. Не запускать Phase 1 этого документа, пока balance plan Phase 1 не закрыт.

## Phase 1. RAGOps Foundation

Tasks:

- document registry;
- chunk registry;
- index registry;
- citation engine;
- trace logs;
- failed parsing logs.

Owner:

- RAGOps.

## Phase 2. Hybrid RAG

Tasks:

- BM25;
- vector search;
- RRF;
- reranker;
- comparison `fast` vs `hybrid`.

Owner:

- RAGOps;
- MLOps;
- Backend.

## Phase 3. LLMOps Foundation

Tasks:

- prompt registry;
- prompt versioning;
- token budget manager;
- LLM call logging;
- fallback policy;
- structured output validation.

Owner:

- LLMOps.

## Phase 4. Golden Dataset + Eval

Tasks:

- 50+ questions;
- fast/hybrid/graph/global categories;
- expected documents;
- expected entities;
- expected mode;
- eval runner;
- report generation.

Owner:

- QA;
- MLOps;
- RAGOps;
- PO.

## Phase 5. Smart Router v1

Tasks:

- `mode=auto`;
- rule-based routing;
- router trace;
- manual override;
- router eval.

Owner:

- Architect;
- LLMOps;
- MLOps;
- Backend.

## Phase 6. Graph RAG MVP

Tasks:

- entity extraction;
- relation extraction;
- graph store;
- entity normalization;
- relation evidence links;
- `/ask/graph`.

Owner:

- RAGOps;
- MLOps;
- LLMOps;
- Architect.

## Phase 7. Smart Router v2

Tasks:

- graph route;
- graph signals;
- router confusion matrix;
- route quality dashboard.

Owner:

- MLOps;
- LLMOps.

## Phase 8. Global GraphRAG Analytics

Tasks:

- community detection;
- community summaries;
- global map-reduce analysis;
- knowledge map;
- contradiction detection;
- architecture risk analysis.

Owner:

- Architect;
- RAGOps;
- MLOps;
- LLMOps.

---

# 20. Golden Dataset

## 20.1. Назначение

Golden Dataset нужен, чтобы улучшения были измеримыми.

Без него изменения выглядят так:

```text
«Кажется, стало лучше».
```

С ним:

```text
Hybrid RAG улучшил context precision на 18%, но latency выросла на 900 мс.
```

## 20.2. Структура

```text
eval/datasets/
  fast_questions.jsonl
  hybrid_questions.jsonl
  graph_questions.jsonl
  global_questions.jsonl
```

## 20.3. Пример

```json
{
  "id": "graph_001",
  "question": "Как связаны ChromaDB, VectorStoreIndex и /ask endpoint?",
  "expected_mode": "graph",
  "expected_entities": ["ChromaDB", "VectorStoreIndex", "/ask"],
  "expected_relation_types": ["uses", "calls", "retrieves_from"],
  "expected_documents": ["api.py", "pipeline_profiler.py"]
}
```

---

# 21. Метрики качества

## 21.1. MLOps Metrics

- embedding retrieval quality;
- reranker uplift;
- router accuracy;
- model version stability;
- eval pass rate;
- regression failures;
- experiment reproducibility.

## 21.2. LLMOps Metrics

- input tokens;
- output tokens;
- LLM latency;
- prompt version usage;
- structured output validity;
- hallucination rate;
- faithfulness;
- fallback success rate.

## 21.3. RAGOps Metrics

- context precision;
- context recall;
- citation accuracy;
- empty retrieval rate;
- duplicate context rate;
- stale index rate;
- indexing failure rate;
- chunk quality.

## 21.4. Product Metrics

- user satisfaction;
- useful answer rate;
- correction rate;
- repeated question rate;
- successful task completion;
- time-to-answer.

---

# 22. Observability и dashboards

## 22.1. RAG Quality Dashboard

Показывает:

- context precision;
- context recall;
- citation accuracy;
- faithfulness;
- top failed questions;
- mode quality comparison.

## 22.2. Retrieval Dashboard

Показывает:

- vector latency;
- BM25 latency;
- reranker latency;
- RRF candidates;
- empty retrieval rate;
- duplicate chunks;
- average final context size.

## 22.3. LLM Dashboard

Показывает:

- input/output tokens;
- latency p50/p95;
- prompt versions;
- model usage;
- failures;
- timeouts;
- fallback activations.

## 22.4. Router Dashboard

Показывает:

- distribution по режимам;
- router confidence;
- manual overrides;
- misroutes;
- graph false negatives;
- global false positives.

## 22.5. Indexing Dashboard

Показывает:

- documents indexed;
- chunks generated;
- failed files;
- indexing duration;
- embedding duration;
- skipped unchanged documents;
- active index versions.

---

# 23. Рекомендуемая структура проекта (REFERENCE LAYOUT, не текущая реальность)

> ⚠️ Эта структура — **аспирационный reference**, а не текущее состояние `hometutor`. Реальные пути проекта (`app/provider.py`, `app/config.py`, `app/routers/`, `app/ui/`, `app/services/`, `data/docs/`) описаны в §34. Не использовать этот блок как карту существующего кода.

```text
  app/
    api.py

    config/
      settings.py

    ingestion/
      loaders.py
      cleaners.py
      chunkers.py
      metadata.py
      pipeline.py

    indexes/
      vector_index.py
      bm25_index.py
      graph_index.py
      registry.py

    retrieval/
      vector_retriever.py
      bm25_retriever.py
      hybrid_retriever.py
      rrf.py
      reranker.py

    rag/
      router.py
      context_builder.py
      answer_generator.py
      citations.py

    graph/
      entity_extractor.py
      relation_extractor.py
      normalizer.py
      graph_store.py
      graph_retriever.py
      global_analyzer.py

    llm/
      client.py
      prompts.py
      token_budget.py
      fallback.py

    ops/
      tracing.py
      metrics.py
      eval_logger.py
      run_registry.py

    eval/
      datasets/
        fast_questions.jsonl
        hybrid_questions.jsonl
        graph_questions.jsonl
        global_questions.jsonl
      metrics.py
      run_eval.py
      reports.py

  prompts/
    answer/
    router/
    graph/
    eval/

  data/
    raw/
    processed/
    indexes/
    registry/

  logs/
    requests.jsonl
    retrieval_traces.jsonl
    eval_runs.jsonl
```

---

# 24. Минимальная база данных Ops

## 24.1. documents

```sql
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    file_type TEXT,
    content_hash TEXT NOT NULL,
    language TEXT,
    status TEXT,
    created_at TEXT,
    indexed_at TEXT
);
```

## 24.2. chunks

```sql
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER,
    text_hash TEXT,
    page INTEGER,
    section TEXT,
    chunking_strategy TEXT,
    chunk_size INTEGER,
    chunk_overlap INTEGER,
    FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
```

## 24.3. index_versions

```sql
CREATE TABLE index_versions (
    index_version TEXT PRIMARY KEY,
    vector_index_name TEXT,
    bm25_index_name TEXT,
    graph_index_name TEXT,
    embedding_model TEXT,
    reranker_model TEXT,
    chunking_strategy TEXT,
    created_at TEXT,
    is_active INTEGER
);
```

## 24.4. request_traces

```sql
CREATE TABLE request_traces (
    request_id TEXT PRIMARY KEY,
    question TEXT,
    mode_requested TEXT,
    mode_used TEXT,
    router_reason TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_latency_ms INTEGER,
    created_at TEXT
);
```

## 24.5. entities

```sql
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    display_name TEXT,
    entity_type TEXT,
    description TEXT,
    confidence REAL,
    created_at TEXT,
    updated_at TEXT
);
```

## 24.6. relations

```sql
CREATE TABLE relations (
    relation_id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    description TEXT,
    evidence_chunk_id TEXT,
    confidence REAL,
    created_at TEXT
);
```

---

# 25. Orchestration: как включить Ops-роли в процесс разработки

## 25.1. Задача в backlog

Каждая задача должна иметь поля:

```text
Business goal:
Affected RAG mode:
Affected documents:
Affected prompts:
Affected indexes:
Affected models:
Evaluation cases:
Metrics to protect:
Rollback plan:
Owners:
```

## 25.2. Пример задачи

```text
Title: Добавить Hybrid RAG mode

Business goal:
Улучшить качество ответов на сложные вопросы.

Affected RAG mode:
hybrid

Affected indexes:
BM25 index, vector index

Affected models:
reranker model

Affected prompts:
rag_answer_v2

Evaluation cases:
15 hybrid questions

Metrics to protect:
latency p95 < 15 sec
context precision не ниже baseline
citation accuracy не ниже baseline

Owners:
RAGOps, MLOps, Backend, QA
```

## 25.3. Pull Request Template

```text
## What changed?

## RAG impact
- [ ] fast
- [ ] hybrid
- [ ] graph
- [ ] global_graph

## LLM impact
- [ ] prompt changed
- [ ] token budget changed
- [ ] model changed

## MLOps impact
- [ ] embedding changed
- [ ] reranker changed
- [ ] eval changed
- [ ] index version changed

## RAGOps impact
- [ ] chunking changed
- [ ] retrieval changed
- [ ] citations changed
- [ ] trace changed

## Evaluation
- eval run id:
- metrics before:
- metrics after:

## Rollback plan
```

---

# 26. Release Checklist

Перед релизом проверить:

```text
[ ] Все prompts имеют версии.
[ ] Все модели имеют версии.
[ ] Все индексы имеют версии.
[ ] document/chunk metadata заполнены.
[ ] Retrieval trace работает.
[ ] Golden dataset прогнан.
[ ] Router accuracy не ухудшилась.
[ ] Context precision не ухудшился.
[ ] Citation accuracy не ухудшилась.
[ ] Faithfulness не ухудшился.
[ ] Latency p95 в пределах нормы.
[ ] Token usage в пределах бюджета.
[ ] Rollback plan готов.
```

---

# 27. Риски и mitigation

| Риск | Влияние | Mitigation |
|---|---|---|
| Ошибочный Router | сложные вопросы идут в fast | eval, manual override, trace |
| Шумный graph | ложные связи | evidence required, confidence threshold |
| Галлюцинации LLM | недостоверные ответы | citations, faithfulness eval, prompt rules |
| Раздувание контекста | latency/cost/overflow | token budget, compression |
| Несовместимые индексы | неправильный context | index registry, chunk_id consistency |
| Prompt regression | качество внезапно падает | prompt tests, versioning |
| Reranker тормозит | высокая latency | mode-specific reranker, caching |
| Global GraphRAG дорогой | долгие операции | explicit mode, scope limit |
| Нет eval | невозможно улучшать | golden dataset mandatory |

---

# 28. Практические рекомендации по первому внедрению

## 28.1. Самый первый шаг

Внедрить RAGOps Foundation:

```text
document_id
chunk_id
content_hash
index_version
retrieval_trace
citations
```

Это фундамент. Без него дальнейшие улучшения будут плохо управляемыми.

## 28.2. Второй шаг

Добавить Hybrid RAG:

```text
BM25 + Vector + RRF + Reranker
```

Это даст самый быстрый прирост качества.

## 28.3. Третий шаг

Добавить LLMOps Foundation:

```text
prompt registry
prompt versioning
token budget
LLM call trace
fallback policy
```

## 28.4. Четвертый шаг

Сделать Golden Dataset:

```text
15 fast
15 hybrid
10 graph
10 global
```

## 28.5. Пятый шаг

Добавить Smart Router:

```text
mode=auto
fast/hybrid routing
trace
manual override
```

## 28.6. Шестой шаг

Добавить Graph MVP:

```text
entities
relations
evidence links
graph retrieval
/ask/graph
```

## 28.7. Седьмой шаг

GraphRAG Global Analytics:

```text
community summaries
knowledge map
contradiction detection
architecture risk analysis
```

---

# 29. Финальная целевая модель

Итоговая модель проекта:

```text
User Query
  ↓
Smart Router
  ↓
Fast / Hybrid / Graph / Global Graph
  ↓
Context Builder
  ↓
LLM Answer
  ↓
Citations + Trace + Metrics
  ↓
Evaluation + Continuous Improvement
```

Ops-дисциплины:

```text
MLOps  → модели, embeddings, reranker, router, eval
LLMOps → prompts, tokens, LLM calls, hallucination control
RAGOps → documents, chunks, indexes, retrieval, citations
```

Командная модель:

```text
Architect задает систему.
Backend реализует API и integration.
RAGOps отвечает за retrieval truth.
LLMOps отвечает за generation control.
MLOps отвечает за model quality and reproducibility.
QA проверяет regression and faithfulness.
PO/domain expert определяет полезность ответа.
DevOps/SRE обеспечивает стабильность и deployment.
```

---

# 30. Краткое резюме

Для `hometutor` оптимальный путь — не просто «добавить GraphRAG» и не просто «поставить reranker».

Оптимальный путь (нумерация выровнена с §19 фазами 0–8):

```text
0. Stabilize current RAG (verify-and-seal)
1. RAGOps Foundation
2. Hybrid RAG
3. LLMOps Foundation
4. Golden Dataset + Evaluation
5. Smart Router v1
6. Graph RAG MVP
7. Smart Router v2 (с graph signals)
8. Global GraphRAG Analytics
```

AI Platform Team practices — это не отдельная фаза, а способ запускать каждую из 0–8 (см. §17 и §31–§34).

Главный организационный вывод:

```text
MLOps, LLMOps и RAGOps должны быть не вспомогательными активностями,
а полноценными зонами ответственности внутри проектной оркестрации.
```

Главный технический вывод:

```text
Качество RAG определяется не одной LLM,
а всей цепочкой:

documents → chunks → embeddings → retrieval → reranker → context → prompt → LLM → citations → eval
```

Главный архитектурный вывод:

```text
Smart Router RAG + Ops-дисциплины = путь от локального эксперимента к надежной AI/RAG-платформе.
```

---

# 31. Primary chat LLM vs Secondary LLM channels (контракт с balance plan)

Балансовый план ([`doc/next/localhost_balance_course_delight_plan.md`](../next/localhost_balance_course_delight_plan.md) §0) расщепляет LLM-каналы на два класса. Этот раздел — обязательный мост между ним и Ops-дисциплинами.

| Канал | Что обслуживает | Кто owner | Fallback политика |
|---|---|---|---|
| **Primary chat LLM** | `/ask`, tutor, course mission, scoped course answer | LLMOps | Profile-aware (`LOCAL_STRICT` / `BALANCED` / `CLOUD_FAST`) + soft/hard timeout в `app/provider.py` |
| **Secondary LLM channels** | quiz (`QUIZ_LLM_*`), SSR (`SSR_LLM_*`), ingestion (`INGESTION_MODEL`, `LLAMAINDEX_METADATA_FALLBACK_MODEL`), classifier (`CLASSIFIER_MODEL`), rewrite (`REWRITE_MODEL`), evaluator (`EVALUATE_MODEL`, `EVAL_JUDGE_LLM`) | LLMOps + соответствующий feature owner | Существующий circuit breaker (`LLM_LOCAL_CB_*`); **не** включается в profile-fallback |

## 31.1. Что это значит для пакетов

- Любой пакет, который **меняет LLM поведение primary chat канала**, обязан пройти LLMOps gate с проверкой соответствия профилю.
- Любой пакет, расширяющий fallback за пределы primary chat (например, на quiz-канал), — это **отдельный пакет** и требует новой RACI-строки и нового ADR.
- Smoke по quiz/SSR обязателен в DoD пакетов, трогающих `app/provider.py`, чтобы поймать регресс secondary channels.

## 31.2. Anti-pattern, который ловит LLMOps на review

```text
✗ Новый пакет переносит ВСЕ LLM-вызовы в profile-fallback одним рефакторингом
✗ Soft/hard timeout начинает дублировать CB-политику (см. balance plan §Phase 1)
✗ Секрет fallback'а (OpenRouter ключ) утекает в LOCAL_STRICT при ошибке профиля
```

---

# 32. Profile-aware Ops policy (LOCAL_STRICT / BALANCED / CLOUD_FAST)

`HOME_RAG_LOCAL_PROFILE` (см. balance plan §Phase 1) — это **ось runtime**, которая меняет поведение Ops:

| Профиль | MLOps | LLMOps | RAGOps |
|---|---|---|---|
| `LOCAL_STRICT` | Eval только на локальных моделях; eval judge offline. Cloud-only embeddings → блокирует ingest. | Primary chat LLM **только** локально; cloud fallback запрещён. При CB-open → friendly strict error. | Retrieval trace показывает «local only»; CitationOps не должна намекать на cloud-источники в banner. |
| `BALANCED` | Эксперимент может смешивать local+cloud, но run_id фиксирует обе версии. | Primary chat: local → cloud fallback по soft/hard timeout. Banner: «fast fallback active». | Retrieval trace честно показывает каждый шаг; embeddings provider может быть локальным или cloud, отдельный banner. |
| `CLOUD_FAST` | Eval reproducibility ниже (cloud-side не версионирован пользователем); MLOps фиксирует это в run_id. | Primary chat сразу в cloud; latency budget жёстче. | Файлы и индекс локально; контекст уходит в cloud. RAGOps обязан показать privacy_note. |

## 32.1. Обязательные проверки на release

```text
[ ] BALANCED не пересылает данные в cloud для secondary channels (если это не было целью пакета).
[ ] LOCAL_STRICT не утечёт ни одного байта в cloud (ни LLM, ни embeddings, ни telemetry).
[ ] CLOUD_FAST не блокирует UI, если ключ fallback не задан — показывает понятную ошибку.
[ ] Embeddings provider banner и LLM banner показываются как ДВЕ независимые оси.
```

## 32.2. Какие KPI MLOps/LLMOps/RAGOps меняются при смене профиля

| KPI | LOCAL_STRICT | BALANCED | CLOUD_FAST |
|---|---|---|---|
| `llm_latency_p95` (primary chat) | выше (локалка) | смешанный | низкий |
| `fallback_success_rate` | n/a | основная метрика | n/a |
| `cloud_request_count` | строго 0 | > 0 при fallback | основной поток |
| `eval_reproducibility_rate` | высокий | средний | низкий (зависит от cloud) |

При выходе профиля за норму — алёрт в Local Control Center (см. balance plan §Phase 7).

---

# 33. Course Delight Loop ownership matrix

Балансовый план §4 определяет Course Activation Contract (4.1–4.10). Это критическая user-visible цепочка. Распределение ответственности:

| Шаг | Owner (RACI A) | Поддерживают (R) | Артефакт балансового плана |
|---|---|---|---|
| 4.1 Course discovery | RAGOps | Backend, Designer | `list_course_candidates()` в `app/course_cache.py` |
| 4.2 One-click activation | RAGOps | Backend, LLMOps (deterministic baseline) | `app/ui/study_scope.py`, `app/ui/topics_tab_right_column.py` |
| 4.3 First mission | LLMOps (LLM enrichment) + RAGOps (deterministic baseline) | Backend, Designer | `app/ui/course_cockpit.py`, `app/adaptive_plan.py` |
| 4.4 Add documents from UI | RAGOps | Backend (router/service), DevOps (filesystem safety) | `app/routers/course_upload.py`, `app/services/course_upload_service.py` |
| 4.5 Scoped answer with sources | RAGOps | LLMOps (prompt), Backend | `app/quiz_scoped.py` + retrieval trace |
| 4.6 Tutor inside course | LLMOps | Backend, RAGOps | `app/tutor_orchestrator.py`, `app/prompts/` |
| 4.7 Course quiz | LLMOps (quiz prompts) + RAGOps (scoped retrieval) | Backend, QA | `app/quiz_scoped.py`, `app/ui/scoped_quiz.py` |
| 4.8 Flashcards / SRS | RAGOps (course tagging) | Backend | `app/flashcard_service.py` |
| 4.9 Adaptive next step | Backend (deterministic SSR) | RAGOps, LLMOps (enrichment) | `app/smart_study_router.py`, `app/ui/graduation_overlay.py` |
| 4.10 Promise for next session | RAGOps (persistence) + Designer (single renderer) | Backend | `app/ui/resume_cards_tutor.py`, `app/course_cache.py` |

## 33.1. Инварианты, которые Ops проверяют на каждом релизе

- **Deterministic baseline:** course mission / route / next step должны работать при LLM enrichment failure (см. balance plan §3.3).
- **Course scope leak:** scoped answer не должен возвращать источники вне активного курса (RAGOps owns this test).
- **Upload safety:** запись только в `data/docs/<active-course-folder>/`, sanitization, dedupe suffix, API-key guard (RAGOps + DevOps).
- **Promise renderer uniqueness:** единственный визуальный компонент promise — `app/ui/resume_cards_tutor.py`; `mission_control.py` его только подключает (Designer owns this contract).

---

# 34. Mapping ролей на реальные модули `hometutor`

Reference layout §23 — желаемое, **не реальное**. Эта таблица — фактическое соответствие:

| Тема | Реальные модули `hometutor` | Owner |
|---|---|---|
| Primary chat LLM client + fallback | `app/provider.py`, `app/llm_local_health.py` | LLMOps |
| Config | `app/config.py` (через `get_settings()`) | LLMOps + RAGOps по контракту |
| Retrieval / pipeline | `app/query_service.py`, `app/pipeline_steps.py` | RAGOps |
| Routers / API | `app/routers/` | Backend |
| UI surface | `app/ui/` | Designer + Backend |
| Course scope / cache | `app/course_cache.py`, `app/course_metrics.py`, `app/ui/study_scope.py` | RAGOps |
| Tutor pipeline | `app/tutor_orchestrator.py`, `app/tutor_cycle.py`, `app/tutor_pipeline_contract.py`, `app/tutor_prompts.py` | LLMOps |
| Knowledge graph | `app/knowledge_graph.py` | MLOps + RAGOps |
| Flashcards / SRS | `app/flashcard_service.py`, `app/learner_state_scope.py` | RAGOps + Backend |
| Adaptive routing | `app/smart_study_router.py`, `app/adaptive_plan.py`, `app/warmup_planner.py` | Backend (deterministic) + LLMOps (enrichment) |
| Graduation | `app/ui/graduation_overlay.py` (AR-2026-04-29-004 — НЕ воссоздавать `app/course_graduation.py`) | RAGOps + Designer |
| Promise / resume | `app/ui/resume_cards_tutor.py` (single renderer), `app/ui/mission_control.py` (observer) | Designer + RAGOps |
| Document corpus | `data/docs/<course>/` | RAGOps |
| Readiness / banner | `scripts/local_readiness.py`, `app/ui/llm_local_banner.py` | LLMOps + Designer |

**Что НЕ создавать (anti-pattern список):**

- `app/course_graduation.py` (AR-2026-04-29-004)
- параллельный prompt-стор за пределами `app/prompts/` / `app/tutor_prompts.py`
- отдельный SQLite-сторадж вне documented user-state/cache wrappers
- запись upload-файлов за пределы `data/docs/<active-course>/`

---

# 35. Hook в team-workflow процесс

Ops-роли подключаются к пайплайну через **STEP 3.5 — Ops Impact Gate** в [`orchestrator_template.md`](orchestrator_template.md). Gate срабатывает, если контракт пакета затрагивает:

```text
- app/provider.py                                     → LLMOps owner
- app/config.py (новые LLM/embeddings/profile ключи)  → LLMOps
- app/query_service.py / app/pipeline_steps.py        → RAGOps
- app/knowledge_graph.py                              → MLOps + RAGOps
- app/prompts/ или app/tutor_prompts.py               → LLMOps
- индексы / chunks / embeddings (`data/indexes/` etc.)→ MLOps + RAGOps
- app/course_cache.py / app/ui/study_scope.py         → RAGOps
- scripts/local_readiness.py / app/ui/llm_local_banner.py → LLMOps + Performance (+ Designer note)
- scripts/local_*.{py,ps1} / .env.example             → Performance
- новые таймауты / budgets / runtime-зависимости      → Performance
- ingest throughput / новые ingestion-pipeline шаги   → Performance + RAGOps
- Dockerfile / CI workflows / GitHub Actions          → Performance (sole)
```

Полный текст gate-промпта — в [`doc/team_workflow/orchestrator_template.md`](orchestrator_template.md) § STEP 3.5.

Промпты ролей:

- [`doc/team_workflow/mlops_engineer.md`](mlops_engineer.md)
- [`doc/team_workflow/llmops_engineer.md`](llmops_engineer.md)
- [`doc/team_workflow/ragops_engineer.md`](ragops_engineer.md)
- [`doc/team_workflow/performance_devops.md`](performance_devops.md)


