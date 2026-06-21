# Журнал Архитектурных Решений

Статус: `ADR`
Роль: журнал принятых и предлагаемых архитектурных решений.
Важно: каждая запись имеет собственный статус (`Accepted`, `Proposed` и т.д.), поэтому не все ADR описывают уже реализованное состояние кода.

> Бортовой журнал архитектурных решений проекта hometutor.
> Код отвечает на вопрос «как». Этот документ отвечает на вопрос «почему».

## Реестр решений

| ADR | Название | Статус | Дата |
|-----|---------|--------|------|
| [001](#adr-001) | RAG-фреймворк: llama-index | Accepted | 2025-12 |
| [002](#adr-002) | Векторная БД: Chroma PersistentClient | Accepted | 2025-12 |
| [003](#adr-003) | LLM-провайдер: OpenRouter через OpenAI-совместимый клиент | Accepted | 2025-12 |
| [004](#adr-004) | Единая pipeline factory вместо разрозненной сборки | Accepted | 2026-02 |
| [005](#adr-005) | Конфигурация: pydantic-settings с обратной совместимостью | Accepted | 2026-02 |
| [006](#adr-006) | Переход от Q&A RAG к Knowledge Management RAG | Accepted | 2026-03 |
| [007](#adr-007) | Hybrid Retrieval: BM25 + Vector Search | Accepted | 2026-03 |
| [008](#adr-008) | Хранение document-level summaries | Accepted | 2026-03 |
| [009](#adr-009) | Подход к topic clustering | Accepted | 2026-03 |
| [010](#adr-010) | Local state persistence and optional entrypoints | Accepted | 2026-04 |
| [011](#adr-011) | Async/Sync Layering Policy | Accepted | 2026-04-19 |
| [012](#adr-012) | Caching Strategy | Accepted | 2026-04-19 |
| [013](#adr-013) | Knowledge Graph Storage Format | Accepted | 2026-04-19 |
| [014](#adr-014) | LLM Resilience Wrapper Contract | Accepted | 2026-04-24 |
| [015](#adr-015) | Tutor Orchestration Pattern | Accepted | 2026-04-24 |
| [016](#adr-016) | Metrics/Observability Decomposition Contract | Accepted | 2026-04-25 |
| [017](#adr-017) | Course Progression and Pace Subsystem | Accepted | 2026-04-29 |
| [018](#adr-018) | Autonomous Agent Control Plane Runner | Accepted | 2026-04-29 |
| [019](#adr-019) | Query/Graph god-module split boundary (Wave B3) | Accepted | 2026-05 |
| [020](#adr-020) | Smart Study Router and SSR ML Hybrid Contract | Accepted | 2026-05-11 |
| [021](adr_021_smart_router_rag_modes.md) | Smart Router RAG modes and bounded GraphRAG analytics | Accepted | 2026-05-14 |
| [021a](adr_021a_smart_router_architecture_lifts.md) | ADR-021a: Audit architecture lifts (dispositions before implementation) | Accepted | 2026-05-17 |
| [022](adr_022_ssr_ai_eval_harness.md) | SSR-AI eval harness and local artifact contract | Accepted | 2026-05-18 |
| [021b](#adr-021-latency-budgets) | Surface latency budgets (Move 2 MVP — mission_load) | Proposed | 2026-05-24 |
| [022b](#adr-022-session-tape) | Session tape (append-only learning arc trace) | Accepted | 2026-05-24 |
| [023](adr_023_ssr_graph_routing.md) | SSR graph routing: prerequisite-aware weak-concept ordering | Accepted | 2026-05-29 |
| [024](#adr-024) | Local balanced model for hometutor learning-plane | Accepted | 2026-06-04 |
| [025](adr_025_course_graph_compiler.md) | Course Graph Compiler and local artifact cache | Accepted | 2026-06-11 |

---

<a id="adr-001"></a>
## ADR-001: RAG-фреймворк: llama-index

**Статус:** Accepted
**Дата:** 2025-12
**Автор:** Владелец проекта

### Контекст

Проекту нужен фреймворк для построения RAG-пайплайна: загрузка документов → разбиение на чанки → создание эмбеддингов → хранение в векторной БД → retrieval → формирование промпта → вызов LLM → ответ с источниками.

Ключевые ограничения:
- Проект — персональный инструмент, не enterprise-система. Приоритет — скорость прототипирования.
- Нужна поддержка нескольких стратегий чанкинга (sentence window, sentence splitter) из коробки.
- Нужна интеграция с Chroma и OpenAI-совместимыми провайдерами.
- Один разработчик. Не должно требовать глубокой экспертизы в ML-инфраструктуре.

### Альтернативы

**A. LangChain**
- Плюсы: самый популярный фреймворк, огромное сообщество, множество интеграций, LangGraph для агентов.
- Минусы: избыточная абстракция для простого RAG, частые breaking changes между версиями, сложная отладка цепочек (chain-of-chains), документация местами противоречива.
- Почему отклонён: для персонального проекта overhead абстракций LangChain превышает пользу. «Слишком много магии» для задачи, которая решается 5 модулями.

**B. llama-index**
- Плюсы: фокус именно на RAG (а не на generic agent chains), встроенные стратегии чанкинга (SentenceWindowNodeParser, SentenceSplitter), нативная интеграция с Chroma, OpenAI-совместимые клиенты для LLM и embeddings, встроенные evaluation-метрики (Faithfulness, AnswerRelevancy, ContextRelevancy).
- Минусы: меньше сообщество чем у LangChain, менее гибок для сложных агентных сценариев, API иногда меняется между minor-версиями.

**C. Собственная реализация (requests + chromadb + OpenAI SDK)**
- Плюсы: полный контроль, минимум зависимостей, нет overhead фреймворка.
- Минусы: придётся реализовать chunking, node parsing, retrieval, prompt templating, evaluation — всё с нуля. Время разработки ×3–5 при минимальном выигрыше для MVP.
- Почему отклонён: нарушает принцип «минимум кода, только необходимый функционал».

### Решение

Используем llama-index как основной RAG-фреймворк.

### Последствия

**Положительные:**
- Из коробки получили SentenceWindowNodeParser, SentenceSplitter, ChromaVectorStore, OpenAI LLM/Embedding клиенты, встроенный reranker, evaluation framework.
- Первый рабочий прототип (итерация 1) собран за 2 дня.
- Pipeline factory (итерация 7) естественно ложится на абстракции llama-index (QueryEngine, Retriever, NodePostprocessor).

**Отрицательные:**
- Привязка к экосистеме llama-index. Замена на другой фреймворк потребует переписывания `ingestion.py`, `retrieval.py`, `pipeline_factory.py`, `pipeline_profiler.py` — примерно 60% кодовой базы.
- Обновления llama-index иногда ломают API. Нужно фиксировать версии в requirements.txt.
- Для будущих агентных сценариев (итерация 17: learning plan generator) llama-index менее гибок, чем LangGraph. Возможно, потребуется добавить LangGraph как дополнительную зависимость для агентных pipeline.

### Compliance & Ethics

Llama-index — open-source (MIT license). Не передаёт данные на свои серверы. Все LLM-вызовы идут напрямую к провайдеру, указанному в конфигурации.

---

<a id="adr-002"></a>
## ADR-002: Векторная БД: Chroma PersistentClient

**Статус:** Accepted
**Дата:** 2025-12
**Автор:** Владелец проекта

### Контекст

Нужно хранилище для эмбеддингов с поддержкой: similarity search, metadata filtering, персистентность между перезапусками, локальная работа без сервера.

Ограничения:
- Локальный проект, запускается на одной машине. Нет Kubernetes, нет облака.
- Размер данных — десятки-сотни документов (не миллионы).
- Не нужна горизонтальная масштабируемость.

### Альтернативы

**A. FAISS (Facebook AI Similarity Search)**
- Плюсы: быстрейший vector search, battle-tested, zero dependencies для in-memory.
- Минусы: нет встроенного metadata filtering (нужно реализовывать отдельно), нет персистентности из коробки (нужно сериализовать/десериализовать вручную), нет collection management.
- Почему отклонён: отсутствие metadata filtering критично — проект использует фильтры по folder_name, file_name, relative_path для scoped retrieval.

**B. Chroma (PersistentClient)**
- Плюсы: встроенный metadata filtering, персистентность на диск, нативная интеграция с llama-index (ChromaVectorStore), collection management, zero-config для локального использования.
- Минусы: медленнее FAISS на больших объёмах (>100K документов), не production-grade для high-load, ограниченные возможности backup/replication.

**C. PGVector (PostgreSQL + vector extension)**
- Плюсы: production-grade, полноценный SQL для metadata queries, транзакционность, backup/replication.
- Минусы: требует установки и настройки PostgreSQL, избыточен для локального персонального проекта, дополнительная зависимость в стеке.
- Почему отклонён: нарушает принцип KISS. Для десятков документов PostgreSQL — оверкилл.

**D. Qdrant**
- Плюсы: мощный metadata filtering, хорошая производительность, gRPC API.
- Минусы: нужно запускать как отдельный сервис (Docker), усложняет локальный запуск.
- Почему отклонён: дополнительный процесс при запуске противоречит цели «python main.py и всё работает».

### Решение

Используем Chroma с PersistentClient, хранение на локальном диске в `chroma_db/`.

### Последствия

**Положительные:**
- Zero-config: `chromadb.PersistentClient(path=str(CHROMA_DIR))` — одна строка для подключения.
- Metadata filtering работает из коробки: `MetadataFilter(key="folder_name", value=...)`.
- Данные переживают перезапуск сервиса без дополнительного кода.

**Отрицательные:**
- При переходе на multi-user или high-load потребуется миграция на Chroma Server или PGVector. Это затронет `ingestion.py`, `retrieval_cache.py` и потребует изменения connection logic.
- Chroma не поддерживает BM25/keyword search из коробки. Hybrid-путь (ADR-007) строит BM25 in-memory поверх нод из Chroma — два параллельных механизма поиска, но один источник нод.
- Нет встроенного blue-green switching коллекций. Для атомарного reindex (итерация 16) потребуется реализовать это вручную через именование коллекций (частично — staging-коллекции в `ingestion.py`).

---

<a id="adr-003"></a>
## ADR-003: LLM-провайдер: OpenRouter через OpenAI-совместимый клиент

**Статус:** Accepted
**Дата:** 2025-12
**Автор:** Владелец проекта

### Контекст

Проекту нужен LLM-провайдер для: генерации ответов, explain-файлов, eval-judge, а в будущем — query rewriting, classification, metadata extraction.

Ограничения:
- Нет собственных GPU. Модель должна быть облачной.
- Нужна возможность переключаться между моделями (GPT-4, Claude, Mixtral, Qwen) без изменения кода.
- Бюджет ограничен — нужна возможность использовать дешёвые модели для вспомогательных задач.

### Альтернативы

**A. OpenAI API напрямую**
- Плюсы: лучшее качество моделей, стабильный API, отличная документация.
- Минусы: привязка к одному провайдеру, нет доступа к open-source моделям (Mixtral, Qwen, LLaMA), ценообразование выше для некоторых задач.
- Почему отклонён: для eval-judge, query rewriting и metadata extraction хочется использовать дешёвые модели, которых нет в OpenAI.

**B. OpenRouter**
- Плюсы: единый API, совместимый с OpenAI SDK, доступ к 100+ моделям от разных провайдеров, переключение модели через одну строку конфига (`LLM_MODEL=...`), прозрачное ценообразование.
- Минусы: дополнительный прокси-слой (latency +50–100ms), зависимость от стороннего сервиса, при падении OpenRouter — не работает ничего.

**C. Локальная модель (Ollama / vLLM)**
- Плюсы: полная автономность, нет переменных расходов, данные не покидают машину.
- Минусы: требует GPU, качество open-source моделей ниже для complex reasoning, сложная настройка.
- Почему отклонён: нет GPU, нарушает принцип быстрого прототипирования.

### Решение

Используем OpenRouter как единый LLM-провайдер через OpenAI-совместимый клиент llama-index (`OpenAI(api_base="https://openrouter.ai/api/v1")`). Модель переключается через `.env` без изменения кода.

### Последствия

**Положительные:**
- Один `provider.py` обслуживает все сценарии. Переключение модели — одна переменная.
- Можно использовать разные модели для разных задач: дорогую для generation, дешёвую для classification.
- Архитектура провайдера не привязана к OpenRouter: замена `api_base` на `https://api.openai.com/v1` переключит на прямой OpenAI.

**Отрицательные:**
- Зависимость от внешнего сервиса. При падении OpenRouter или проблемах с интернетом — система неработоспособна. Нет offline-режима.
- Дополнительный latency прокси-слоя.
- Стоимость масштабируется линейно с количеством LLM-вызовов. При расширении pipeline (rewrite + generate + judge = 3 вызова) стоимость утраивается.

### Compliance & Ethics

- Данные из `data/` (лекции, заметки) отправляются в облачный LLM в составе промптов. Если в документах есть конфиденциальная информация, она может быть передана провайдеру.
- Митигация: для чувствительных данных — переключиться на локальную модель (Ollama), заменив `api_base` в `.env`. Архитектура это позволяет без изменения кода.

---

<a id="adr-004"></a>
## ADR-004: Единая pipeline factory вместо разрозненной сборки

**Статус:** Accepted
**Дата:** 2026-02 (итерация 7)
**Автор:** Владелец проекта

### Контекст

До итерации 7 параметры пайплайна (prompt, filters, postprocessors, reranker, profile resolution) собирались в трёх разных местах:
- `retrieval.py` — для production запросов
- `pipeline_profiler.py` — для профилирования
- `compare_eval.py` — для eval-сравнений

Это приводило к расхождениям: production использовал один prompt, profiler — другой. Profile `fast` работал в API, но не в CLI. Reranker включался в одном месте и не включался в другом.

Проблема: **три источника правды для одного пайплайна**. Любое изменение нужно вносить в трёх местах; при забытом месте — скрытый баг.

### Альтернативы

**A. Конфигурационный файл (YAML/JSON) pipeline**
- Плюсы: декларативное описание, легко сравнить конфигурации.
- Минусы: нужен парсер, сложнее для динамических overrides (profile → params), дополнительная абстракция.
- Почему отклонён: overkill для текущего масштаба. Добавляет слой парсинга без выигрыша.

**B. Pipeline Factory — единый модуль сборки**
- Плюсы: один источник правды, все потребители вызывают одни и те же функции (`resolve_pipeline_params`, `build_filters`, `build_postprocessors`), изменение в одном месте автоматически распространяется.
- Минусы: все потребители зависят от одного модуля; если factory сломается, ломается всё.

**C. Оставить как есть, покрыть тестами на консистентность**
- Почему отклонён: тесты ловят расхождения постфактум, а не предотвращают их. С ростом числа конфигураций (hybrid search, query rewriting) количество мест для синхронизации будет только расти.

### Решение

Создан `app/pipeline_factory.py` с функциями `resolve_pipeline_params()`, `build_filters()`, `build_postprocessors()` и единым `QA_PROMPT`. Все потребители (`retrieval.py`, `pipeline_profiler.py`, `compare_eval.py`) импортируют и используют эти функции.

### Последствия

**Положительные:**
- Расхождение между production и profiler устранено. Один prompt, один profile resolution, одни postprocessors.
- Добавление нового параметра (например, `retrieval_mode: hybrid`) потребует изменения только в factory.
- Тесты на консистентность стали тривиальными: достаточно тестировать factory, а не каждого потребителя.

**Отрицательные:**
- `pipeline_factory.py` стал критическим модулем. Баг в нём ломает production, profiler и eval одновременно.
- Factory расширена несколькими промпт-ключами по типам запросов (qa, overview, synthesis, learning_plan, keyword и др.); единая точка сборки сохранена, но модуль остаётся чувствительным к изменениям.

---

<a id="adr-005"></a>
## ADR-005: Конфигурация: pydantic-settings с обратной совместимостью

**Статус:** Accepted
**Дата:** 2026-02 (итерация 8)
**Автор:** Владелец проекта

### Контекст

До итерации 8 конфигурация читалась через `os.getenv()` с ручным приведением типов (`int()`, `.lower() == "true"`). Не было валидации диапазонов, не было нормализации неизвестных значений профиля, опечатка в имени переменной давала молчаливый fallback на дефолт.

Одновременно 10+ модулей импортируют настройки через `from app.config import CHUNK_SIZE, ...`. Переход на getter-функцию `get_settings()` сломал бы все импорты разом.

### Альтернативы

**A. Полный переход на get_settings() во всех модулях**
- Плюсы: один источник правды, нет глобалов, легко мокать в тестах.
- Минусы: сломает все существующие импорты, большой единовременный рефакторинг, высокий риск регрессий.
- Почему отложён: слишком рискованно делать в той же итерации, что и переход на pydantic. Запланирован на итерацию 15.

**B. pydantic-settings + `_export()` для обратной совместимости**
- Плюсы: новый код может использовать `get_settings()`, старый продолжает работать через глобалы, валидация и нормализация работают для обоих путей (потому что `_export()` берёт значения из уже валидированного `Settings`).
- Минусы: два источника правды (getter и глобалы), тесты не могут подменить конфиг без переимпорта модулей.

**C. Dynaconf или python-decouple**
- Почему отклонён: pydantic-settings уже в стеке (pydantic используется FastAPI), добавление другой config-библиотеки — лишняя зависимость.

### Решение

Введён класс `Settings(BaseSettings)` с pydantic-settings. Валидация через `field_validator`. Доступ через `get_settings()`. Обратная совместимость через `_export()`, заполняющую глобальные переменные модуля. Миграция с глобалов на getter запланирована на итерацию 15.

### Последствия

**Положительные:**
- Валидация работает: `chunk_size < 1` → ошибка при старте, а не молчаливый баг в рантайме.
- Неизвестный `RAG_PROFILE` → warning + fallback на `quality`, а не непредсказуемое поведение.
- Новые модули (`provider.py`, `guardrails.py`) используют `get_settings()` — чистая архитектура.

**Отрицательные:**
- **Техдолг: два пути конфигурации.** Старые модули (`ingestion.py`, `retrieval_cache.py`, `pipeline_factory.py`) читают глобалы. Новые — getter. При рассогласовании (теоретически невозможно через `_export()`, но снижает ясность кода) — скрытый баг.
- Тесты не могут атомарно подменить настройки без `importlib.reload()`.
- При введении multi-workspace (итерация 16) понадобятся настройки per-collection — глобальная `Settings` не поддерживает это.

---

<a id="adr-006"></a>
## ADR-006: Переход от Q&A RAG к Knowledge Management RAG

**Статус:** Accepted
**Дата:** 2026-03
**Автор:** Владелец проекта

### Контекст

Проект начинался как Q&A RAG: задай вопрос → получи ответ с источниками. Но основной сценарий использования оказался шире:
- Изучение новых технологий через конспекты лекций.
- Добавление лекций в RAG, группировка по темам.
- Составление планов обучения по изученному материалу.
- Навигация между связанными темами и концепциями.

Q&A RAG работает на chunk-level: находит 3–5 релевантных фрагментов и генерирует ответ. Но для сценария «составь план обучения по всем лекциям на тему безопасности» нужен document-level retrieval, cross-document synthesis и понимание связей между темами. Текущая архитектура этого не поддерживает.

### Альтернативы

**A. Остаться на Q&A RAG, улучшая качество retrieval**
- Плюсы: минимум изменений, фокус на одном сценарии.
- Минусы: не решает основную пользовательскую задачу — навигацию по знаниям и синтез конспектов.
- Почему отклонён: проект перестаёт решать задачу, для которой создан.

**B. Поэтапный переход: расширение pipeline новыми режимами**
- Плюсы: обратная совместимость, Q&A продолжает работать, новые режимы (synthesis, learning plan) добавляются инкрементально. Risk-free: если новый режим не работает — fallback на Q&A.
- Минусы: архитектурная сложность растёт (router, множественные промпты, document-level index + chunk-level index).

**C. Переписать на агентный фреймворк (LangGraph + RAG)**
- Плюсы: агентный подход нативно поддерживает multi-step workflows (plan → retrieve → synthesize → refine).
- Минусы: переписывание 80% кода, потеря наработок 9 итераций, высокий риск.
- Почему отклонён: эволюция, а не революция. 9 итераций инвестиций не должны быть потеряны.

### Решение

Поэтапный переход (вариант B). Roadmap:
1. Итерация 10: hybrid retrieval (BM25 + vector) — улучшение качества Q&A.
2. Итерация 11: smart ingestion (metadata enrichment, semantic chunking, document summaries) — создание базы для knowledge management.
3. Итерация 12: query understanding (rewriting, classification) — определение типа запроса.
4. Итерация 13: knowledge organization (topic clustering, synthesis, router) — реализация KM-сценариев.
5. Итерация 17: advanced workflows (knowledge graph, learning plan generator).

### Последствия

**Положительные:**
- Q&A остаётся базовым режимом. Все текущие пользовательские сценарии продолжают работать.
- Каждая итерация самодостаточна: можно остановиться на любой и иметь рабочий продукт.
- Knowledge Management сценарии (каталог тем, конспекты, планы обучения) появляются поэтапно.

**Отрицательные:**
- Растёт архитектурная сложность: router, множественные промпты, двухуровневый retrieval, topic clustering.
- Стоимость LLM-вызовов растёт: metadata extraction при ingestion, query rewriting, synthesis — каждый этап добавляет вызовы.
- `pipeline_factory.py` потребует существенного расширения: от одного `QA_PROMPT` к набору промптов, от одного query engine к RouterQueryEngine.
- UI (Streamlit) потребует новых экранов: каталог тем, форма синтеза, план обучения. Текущий Q&A-интерфейс недостаточен.

---

<a id="adr-007"></a>
## ADR-007: Hybrid Retrieval: BM25 + Vector Search

**Статус:** Accepted
**Дата:** 2026-03
**Итерация:** 10

### Контекст

Vector-only retrieval (cosine similarity по embeddings) плохо работает на:
- Точных совпадениях: имена, аббревиатуры, ID документов («RFC-2024-003», «HDBSCAN»).
- Датах и числах: «лекция от 28 февраля».
- Keyword-запросах: «найди все упоминания OWASP».

Лекция по RAG прямо указывает: «Семантический поиск хорошо понимает смысл, синонимы, но плохо работает с конкретными идентификаторами. Решение: гибридный поиск».

### Альтернативы

**A. rank_bm25 (Python-библиотека, in-memory)**
- Плюсы: лёгкая (~50 строк интеграции), нет дополнительных зависимостей-сервисов, работает in-memory, легко интегрировать с llama-index через кастомный retriever.
- Минусы: BM25-индекс пересоздаётся при каждом запуске (нет персистентности), при >100K нод in-memory может стать проблемой, нет fuzzy matching.

**B. llama-index BM25Retriever**
- Плюсы: нативная интеграция, уже совместим с QueryFusionRetriever.
- Минусы: зависит от дополнительного пакета `llama-index-retrievers-bm25`, может не поддерживать все версии llama-index.

**C. Tantivy (через tantivy-py)**
- Плюсы: полноценный поисковый движок уровня Lucene, персистентность на диске, fuzzy search, phrase search.
- Минусы: тяжёлая зависимость (Rust-библиотека), сложнее интеграция, overkill для десятков документов.
- Почему склоняемся против: нарушает KISS, может потребоваться в будущем при >1000 документов.

**D. SPLADE (sparse neural retrieval)**
- Плюсы: семантически обогащённый sparse retrieval, лучше чем BM25 на modern benchmarks.
- Минусы: требует модели SPLADE (дополнительная зависимость), сложнее настроить, меньше документации.
- Почему отложён: исследовать после стабилизации базового hybrid.

### Решение (фактическая реализация)

Реализовано в `app/hybrid_retrieval.py`:

- **BM25:** `llama_index.retrievers.bm25.BM25Retriever` поверх нод из Chroma; кэш индекса в памяти процесса с инвалидацией при смене индекса.
- **Fusion:** параллельный запуск BM25 и vector в `parallel` executor, затем **Reciprocal Rank Fusion (RRF)** с параметром `k=60` (`_RRF_K = 60`).
- **Конфигурация:** `RetrievalSettings.retrieval_mode` — `vector_only` | `hybrid` | `doc_then_chunk` (в `app/config.py` — `KNOWN_RETRIEVAL_MODES`). Дефолт в `.env.example` для `RETRIEVAL_MODE` — `vector_only`; hybrid включается явно.

### Последствия (по факту)

**Положительные:**
- Keyword-heavy запросы и точные совпадения обрабатываются лучше, чем при vector-only.
- Один кодовый путь для hybrid без отдельного `QueryFusionRetriever` в проде — явный RRF.

**Отрицательные:**
- При `hybrid` два поиска + fusion вместо одного — выше latency.
- BM25 in-memory пересобирается при необходимости; при больших объёмах нод — нагрузка на память.

### Критерий принятия (выполнен)

Режим стабилен в прод-коде и покрыт тестами retrieval; eval сравнение vector vs hybrid остаётся рекомендуемой проверкой качества на своём датасете.

---

<a id="adr-008"></a>
## ADR-008: Хранение document-level summaries

**Статус:** Accepted
**Дата:** 2026-03
**Итерация:** 11

### Контекст

Для knowledge management сценариев (каталог тем, выбор документов, cross-document synthesis) нужен двухуровневый retrieval: сначала определить релевантные документы, затем искать чанки внутри. Для первого уровня нужны document-level summaries.

### Альтернативы

**A. Отдельная Chroma-коллекция `document_summaries`**
- Плюсы: чистое разделение, vector search по summaries, можно использовать другую embedding-модель, не загрязняет основной индекс.
- Минусы: два запроса к Chroma при двухуровневом retrieval, дополнительная логика синхронизации при reindex.

**B. Ноды в основной коллекции с metadata `node_type=summary`**
- Плюсы: один индекс, один Chroma-клиент, фильтрация через metadata.
- Минусы: summary-ноды смешиваются с chunk-нодами при обычном retrieval (нужен обязательный фильтр `node_type != summary`), при росте числа summary нод может влиять на качество vector search.

**C. JSON-файл с summaries (аналог index_meta.json)**
- Плюсы: самый простой вариант, нет зависимости от Chroma, легко инспектировать.
- Минусы: нет vector search по summaries — только exact match или regex.

### Решение (фактическая реализация)

Реализовано в `app/ingestion.py`:

- Отдельная Chroma-коллекция для summary: имя `settings.summary_collection_name` (по умолчанию `home_rag_summaries`), ноды с `node_type=document_summary`.
- При включённом `enable_document_summaries` summary строится LLM-вызовом (`build_document_summary_with_cost`); при blue-green/staging-переиндексации summary-коллекция пересоздаётся вместе с основной.
- Двухуровневый режим `doc_then_chunk` в `app/retrieval.py` использует summary-индекс для выбора документов перед chunk-ретривалом.

### Последствия (по факту)

**Положительные:**
- Разделение chunk-level и document-level поиска без смешивания нод в одной коллекции без фильтров.
- Управляется флагами `enable_document_summaries` и `summary_collection_name`.

**Отрицательные:**
- Дополнительные LLM-вызовы при ingestion при включённых summaries.
- Две коллекции — сложнее lifecycle и инвалидация кэша retrieval.

---

<a id="adr-009"></a>
## ADR-009: Подход к topic clustering

**Статус:** Accepted
**Дата:** 2026-03 (принято 2026-04-18)
**Итерация:** 13

### Контекст

Для каталога тем нужно автоматически группировать документы по тематической близости и давать кластерам человекочитаемые названия.

### Альтернативы

**A. Статическая кластеризация при reindex**
- Плюсы: результат вычисляется один раз, endpoint `/topics` отдаёт мгновенно, нет overhead при каждом запросе.
- Минусы: при добавлении одного документа без reindex — каталог устаревает.

**B. Динамическая кластеризация по запросу**
- Плюсы: всегда актуальна, не нужен reindex для обновления тем.
- Минусы: latency 2–5 секунд на `/topics` (кластеризация + LLM naming), нагрузка при каждом запросе.

**C. Гибрид: статическая при reindex + инкрементальное обновление при добавлении документа**
- Плюсы: быстрый ответ + актуальность.
- Минусы: сложность реализации инкрементальной кластеризации (HDBSCAN поддерживает approximate prediction для новых точек, но не гарантирует стабильность кластеров).

### Решение

Принят фактический runtime-подход из `app/knowledge_service.py`: каталог тем строится при запросе из metadata (`topic_name`) с lightweight embedding-кластеризацией для неразмеченных документов (косинусная схожесть, порог по умолчанию 0.88). Полный reindex+HDBSCAN-пайплайн из раннего черновика в текущем контуре не внедряется.

Алгоритм:
1. При reindex извлечь embeddings всех document summaries из коллекции.
2. HDBSCAN кластеризация (не требует заранее задавать число кластеров).
3. Для каждого кластера — LLM-вызов: «Назови тему, объединяющую эти документы: [titles + first sentences]».
4. Сохранить `topic_id` и `topic_name` в metadata каждого документа.

### Статус реализации (факт на 2026-04-18)

Решение реализовано и используется в прод-коде: `get_topics_catalog` и `_cluster_records` обеспечивают стабильный topic-каталог без отдельного тяжёлого шага при reindex. Это снимает неопределённость статуса и фиксирует текущий архитектурный выбор как целевой.

### Ожидаемые последствия (если когда-либо реализовать вариант A из черновика)

**Положительные:**
- `GET /topics` отвечает мгновенно (чтение metadata).
- Кластеры стабильны между запросами (нет рандомизации при каждом вызове).
- LLM naming делает темы человекочитаемыми.

**Отрицательные:**
- При добавлении документа без reindex — он не попадает ни в один кластер.
- HDBSCAN может создавать «шумовой» кластер для документов, не вписывающихся ни в одну тему. Нужно решить, как отображать unclustered документы.
- Стоимость reindex увеличивается: N LLM-вызовов для naming кластеров (обычно 3–10 кластеров).

---

<a id="adr-010"></a>
## ADR-010: Local state persistence and optional entrypoints

**Статус:** Accepted
**Дата:** 2026-04-12
**Принято:** 2026-04-16
**Итерация:** Architecture review follow-up / `epoch-adr-010-acceptance`

### Контекст

Код уже использует несколько устойчивых архитектурных решений, которые раньше не имели отдельной ADR-записи: SQLite для `user_state.db` и учебного состояния, отдельный `SessionStore` для истории chat/tutor сессий, файловые и SQLite-артефакты для graph/index generations, а также optional Telegram entrypoint на `aiogram`.

После `epoch-local-store-contracts` правило persistence уточнено: `_with_db()` является обязательной границей для user-state таблиц, а отдельные локальные SQLite-хранилища допустимы только как документированные store wrappers или generation artifacts со своей ответственностью.

### Предлагаемое решение

Принять текущую стратегию как локальную single-user persistence model:

- FastAPI, Streamlit, CLI и Telegram работают поверх одного локального инстанса и одного пользователя по умолчанию; Telegram — дополнительный клиент/entrypoint на той же машине, а не отдельный backend или облачная синхронизация.
- Таблицы пользовательского и учебного состояния (`reading_status`, `quiz_results`, `spaced_repetition`, `quiz_mastery`, `tutor_learning_resume`, `learner_goal_snapshot`, `flashcard_decks`, `flashcards`, `app_kv`, sync bundle и связанные archive/log tables) принадлежат `app/user_state.py` / доменным `app/user_state_*` модулям и проходят через `_with_db()` или публичные CRUD-хелперы.
- История chat/tutor сессий живёт в `app/session_store.py` (`SessionStore`, `sessions.db`) как отдельный session wrapper; внешние модули используют wrapper, а не ad hoc SQL к session DB.
- Backend-safe события живут в `app/event_tracking.py` (`ui_events.db`) как независимый analytics-style store без зависимости от Streamlit UI.
- Observability хранит JSONL `metrics_store_path` и SQLite dashboard cache `metrics_dashboard_db_path` в `app/metrics.py`; это cache/reporting artifact, а не user-state DB.
- Knowledge graph generation bundle хранит `kg.sqlite` рядом с `property_graph_store.json` через `app/knowledge_graph_bundle.py` / `SqliteBundleKnowledgeGraph`; это versioned artifact index lifecycle, а не часть backup/sync user-state tables.
- Большие или производные артефакты индекса остаются файловыми/versioned через registry/generation pointers; перенос пользовательского прогресса идёт через sync bundle, а перенос индекса/graph artifacts — через lifecycle/backup контур индекса.

### Последствия

- Это не новая миграция и не поручение на переписывание: ADR фиксирует уже реализованную модель.
- Новые user-state таблицы должны добавляться в `app/user_state_core._ensure_schema()` и обслуживаться через `_with_db()` / доменные `user_state_*` helper'ы.
- Новый SQLite store вне `user_state.py` допустим только после явной записи в `doc/conventions_architecture.md`: владелец, путь, wrapper/API, участие или неучастие в backup/sync, focused tests.
- Роутеры, UI и сервисы не должны открывать прямые SQLite-соединения к user-state tables; они вызывают владельца домена.
- Telegram-функции должны оставаться совместимыми с local-first моделью: настройки читаются через `get_settings()`, запросы проходят guardrails/input validation, session id имеет префикс `tg-*`, а состояние не отделяется от локального Streamlit/API состояния.
- Эта ADR не закрывает соседние remediation-срезы: `epoch-query-service-decomposition`, `epoch-local-cors-defaults` и разрыв циклических импортов остаются отдельными решениями.

---

<a id="adr-011"></a>
## ADR-011: Async/Sync Layering Policy

**Статус:** Accepted
**Дата:** 2026-04-19
**Принято:** 2026-04-19
**Итерация:** Architecture review / `arch-cleanup-e30`

### Контекст

В кодовой базе 15 async def (FastAPI handlers, Telegram handlers, middleware) и 854 sync def (domain logic, сервисы, retrieval). Паттерн существует и соблюдается, но нигде явно не задокументирован. Без ADR будущие агенты могут начать async-ификацию сервисного слоя, нарушая целостность архитектуры.

### Предлагаемое решение

**Async boundary находится строго на HTTP/IO слое:**

- `app/routers/*.py` — async handlers (FastAPI требует async для ожидания I/O)
- `app/telegram_handlers.py` — async handlers (aiogram требует async)
- `app/api.py` — async lifespan, middleware
- Всё остальное (`app/*_service.py`, `app/query_service.py`, `app/retrieval.py`, ...) — синхронное

**Правила:**

- Domain logic, сервисы, retrieval, prompts, knowledge graph — **всегда sync**
- CPU-bound или blocking операции в async context — через `asyncio.to_thread()` (пример: api.py:62)
- Никаких `async def` в сервисном слое без явного согласования в новом ADR
- llama-index, LangChain, Anthropic SDK в этом проекте используются синхронно

### Обоснование

llama-index ecosystem — синхронный. Async-ификация потребует полного переписывания без ощутимого выигрыша на single-user local deployment. Текущий sync-first подход упрощает отладку, трейсинг и тестирование.

### Последствия

- Новые сервисные функции — sync по умолчанию; если нужен async — требуется обоснование и новый ADR
- `asyncio.to_thread()` — стандартный паттерн для вызова sync кода из async handlers при необходимости
- Тесты сервисного слоя не требуют `pytest-asyncio`

---

<a id="adr-012"></a>
## ADR-012: Caching Strategy

**Статус:** Accepted
**Дата:** 2026-04-19
**Принято:** 2026-04-19
**Итерация:** Architecture review / `arch-cleanup-e30`

### Контекст

В проекте существует минимум три уровня кеширования: `lru_cache` на провайдерах, `retrieval_cache` для query engines, `request_cache` для HTTP-вызовов. Стратегия работает, но не задокументирована — нет единого понимания кто владеет кешем, как происходит инвалидация и когда допустимо добавлять новый уровень.

### Предлагаемое решение

**Трёхуровневая кеш-иерархия:**

1. **Provider level** (`app/provider.py`) — `lru_cache` на фабриках LLM/embedding клиентов. Инвалидация: перезапуск процесса. Цель: избежать повторной инициализации тяжёлых клиентов.

2. **Retrieval level** (`app/retrieval_cache.py`) — кеш query engines, привязанных к index. Инвалидация: явный вызов при reindex (`cache.clear()`). Цель: не пересоздавать BM25/vector engine на каждый запрос.

3. **Request level** (`app/request_cache.py`) — кеш HTTP-вызовов к внешним сервисам. Инвалидация: TTL или явный сброс. Цель: снизить latency на повторяющихся API-запросах.

**Правила:**

- **Владелец кеша — retrieval слой**, не query слой. `query_service.py` не кеширует сам — он получает готовый engine из retrieval_cache.
- TTL не нужен для provider/retrieval кешей — инвалидация строго через reindex
- Новый уровень кеша допустим только с явным указанием владельца, инвалидационного события и размера кеша
- `lru_cache` без ограничения размера запрещён вне provider.py (риск memory leak при долгой работе)

### Обоснование

Local deployment, single-process, нет Redis. `lru_cache` достаточен. Разделение по уровням предотвращает stale data: retrieval cache сбрасывается при reindex, что автоматически «освежает» все зависимые query engines.

### Последствия

- При добавлении нового кешируемого ресурса — определить его уровень (provider/retrieval/request) и зарегистрировать инвалидационное событие
- Retrieval cache должен сбрасываться синхронно с завершением reindex в `admin` router
- Размер `lru_cache` в retrieval_cache.py ограничен настройкой `retrieval_cache_size` из config

---

<a id="adr-013"></a>
## ADR-013: Knowledge Graph Storage Format

**Статус:** Accepted
**Дата:** 2026-04-19
**Принято:** 2026-04-19
**Итерация:** Architecture review / `arch-cleanup-e30`

### Контекст

Knowledge graph хранится в двух форматах одновременно: JSON-файл (`concept_graph.json`, `property_graph_store.json`) и SQLite (`kg.sqlite` через `SqliteBundleKnowledgeGraph`). Гибридный подход сложился исторически и нигде не задокументирован. Будущие агенты могут добавить третий формат или нарушить согласованность.

### Предлагаемое решение

**Гибрид JSON (source of truth) + SQLite (indexed read layer):**

- **JSON** — canonical source of truth. Читаем руками, легко version-control, используется при debug и ручном инспекте графа. Путь: `DATA_DIR/concept_graph.json`.
- **SQLite** (`kg.sqlite`) — production read layer. Даёт O(log n) lookup по topic/concept ID, поддерживает SQL joins для `GET /kb/graph/*` endpoints. Строится **из JSON** при startup или reindex.
- **Write path** — всегда через JSON. SQLite является производным артефактом и не является primary storage.
- `JsonKnowledgeGraph` — дефолтный reader (для dev/debug). `SqliteBundleKnowledgeGraph` — production reader.

**Правила:**

- Нельзя писать напрямую в kg.sqlite в обход JSON update
- При reindex: JSON обновляется → SQLite перестраивается из JSON
- Новые поля графа добавляются в JSON schema первыми, SQLite schema — следует
- `app/knowledge_graph_bundle.py` является единственным владельцем SQLite-слоя

### Обоснование

JSON даёт человекочитаемость и простоту отладки. SQLite даёт производительность для API. Разделение write/read paths предотвращает рассинхронизацию: единственный источник правды — JSON.

### Последствия

- `GET /kb/graph/*` endpoints читают из SQLite — гарантированная производительность
- Backup и sync графа работают с JSON-файлом (не с SQLite)
- Если SQLite повреждён — восстанавливается из JSON через reindex
- Добавление новых graph storage форматов требует нового ADR

---

<a id="adr-014"></a>
## ADR-014: LLM Resilience Wrapper Contract

**Статус:** Accepted
**Дата:** 2026-04-24
**Принято:** 2026-04-24
**Итерация:** Architecture review / 2026-04-24

### Контекст

Слой `app/llm_resilience.py` стал обязательной точкой отказоустойчивости для вызовов `llm.complete` и `llm.chat`, но контракт не был явно зафиксирован в ADR. Из-за этого новые модули могли обходить wrapper и терять единые метрики ошибок и fallback-поведение.

### Решение

Фиксируем обязательный контракт для resilience-wrapper:

- Все LLM-вызовы в orchestration- и service-слоях идут через `complete_with_resilience` / `chat_with_resilience`.
- Wrapper обязан:
  - писать structured logs (`llm_*_failed`, `llm_fallback_invoked`);
  - отправлять ошибку в `record_error(endpoint="llm:<stage>")`;
  - выполнять максимум один fallback на `llm_fallback_model`, если включён `enable_llm_fallback`.
- Вызов wrapper всегда передаёт `stage`, чтобы метрики были сопоставимы между модулями.

### Последствия

- Архитектурный drift контролируется простым guard-правилом по наличию ADR и проверками на прямые `.chat(` без wrapper в критичных модулях.
- Новые LLM-интеграции обязаны сначала определить `stage` и только после этого вызывать wrapper.

---

<a id="adr-015"></a>
## ADR-015: Tutor Orchestration Pattern

**Статус:** Accepted
**Дата:** 2026-04-24
**Принято:** 2026-04-24
**Итерация:** Architecture review / 2026-04-24

### Контекст

Tutor subsystem вырос до набора модулей (`tutor_orchestrator`, `tutor_pipeline_contract`, `tutor_learner_contract`, `tutor_personalization_policy`, router/surfaces), но rationale и стабильный контракт межшагового обмена не были собраны в одном месте.

### Решение

Фиксируем паттерн orchestration для `query_mode=tutor`:

- Оркестрация выполняется как контрактный pipeline до генерации ответа.
- Источник состояния шага — `QueryContext.metadata["tutor_orchestration_pipeline"]`.
- Итоги шагов и диагностика — `QueryContext.trace["tutor_pipeline"]`.
- При сбое LLM/JSON оркестратор обязан перейти в rule-based fallback, не прерывая `ask`-запрос.

### Последствия

- UI/API получают стабильные поля для debug и аналитики tutor-цикла.
- Добавление новых шагов оркестрации требует совместимости с `tutor_pipeline_contract` и обновления ADR при изменении базового контракта.

---

<a id="adr-016"></a>
## ADR-016: Metrics/Observability Decomposition Contract

**Статус:** Accepted
**Дата:** 2026-04-25
**Принято:** 2026-04-25
**Итерация:** Architecture review / 2026-04-25

### Контекст

Observability-контур был декомпозирован на набор модулей (`metrics.py`, `metrics_core.py`, `metrics_storage.py`, `metrics_db.py`, `metrics_aggregator.py`, `metrics_summarizer.py`, `metrics_graph_expansion.py`), но без явной ADR-фиксации границ ответственности. Это затрудняет безопасные изменения и провоцирует drift (перенос SQL/агрегаций/сериализации между слоями).

### Решение

Фиксируем слой observability как **семимодульный контракт** с жёсткими границами:

- `metrics.py` — публичный фасад runtime-метрик и API-ориентированные точки входа.
- `metrics_core.py` — базовые типы/примитивы и нормализация событий.
- `metrics_storage.py` — запись/чтение JSONL и low-level storage IO.
- `metrics_db.py` — SQLite-кэш для dashboard/аналитических чтений.
- `metrics_aggregator.py` — вычисление агрегатов из сырых событий.
- `metrics_summarizer.py` — сборка summary payload/срезов для UI/API.
- `metrics_graph_expansion.py` — graph-specific counters и метрики расширения графа.

Правила взаимодействия:

- Router/API-слой работает через публичные функции `metrics.py` (не импортирует внутренние модули напрямую).
- `metrics.py` remains an explicit compatibility facade. It may re-export the public
  observability API and proxy mutable test constants to `metrics_core.py`, but it
  must not grow new storage, SQL, aggregation, summarization, or graph-specific
  business logic. New implementation logic belongs in the decomposed modules
  listed above, with `metrics.py` updated only as a thin public surface when a
  stable compatibility import is required.
- The facade may use the current `MetricsModule(types.ModuleType)` proxy pattern
  to keep test patching of path constants compatible across submodules. This is
  accepted technical debt for compatibility, not a precedent for adding dynamic
  module-class patterns elsewhere.
- `metrics_aggregator.py` и `metrics_summarizer.py` не выполняют низкоуровневый IO напрямую, а используют storage/db слои.
- Graph-специфика изолируется в `metrics_graph_expansion.py`; общий observability-flow не зависит от graph-модуля циклически.

### Последствия

- Появляется явный архитектурный контракт для текущей декомпозиции и критерии, по которым проверяется drift.
- Рефакторинги observability обязаны сохранять границы модулей или сопровождаться новым ADR (supersede/replace).
- Проще выполнять review: изменения классифицируются по слоям (facade/core/storage/db/aggregate/summary/graph), а не «по файлам как придётся».

---

<a id="adr-017"></a>
## ADR-017: Course Progression and Pace Subsystem

**Статус:** Accepted
**Дата:** 2026-04-29
**Принято:** 2026-04-29
**Итерация:** Architecture review / 2026-04-29

### Контекст

Course Workspace grew into a dedicated learning progression subsystem with
`course_cache.py`, `course_metrics.py`, `course_graduation.py`, and
`pace_engine.py`. The modules touch cached course views, progress/graduation
state, workflow metrics, and learner pacing, so the boundary must be explicit
instead of inferred from UI code.

### Решение

- `course_cache.py` owns derived course-level projections and cache invalidation
  for Course Workspace views.
- `course_metrics.py` owns Course Workspace telemetry and exposes the single
  product-event path for course workflow events.
- `course_graduation.py` owns graduation/readiness decisions and returns
  deterministic status payloads for UI and future orchestration.
- `pace_engine.py` owns pace mode defaults and recommendations. It is a local,
  deterministic strategy module, not a plugin system.
- Persistent learner/course state stays under ADR-010 ownership: user-state
  tables and writes go through `app/user_state.py`, `_with_db()`, or domain
  user-state helpers. Course modules must not open SQLite connections directly.
- Course progression complements SRS. Concept/card review remains owned by
  `spaced_repetition.py` and `flashcard_service.py`; course graduation may read
  their derived signals through public service/user-state helpers but does not
  replace the SRS lifecycle.

### Последствия

- New Course Workspace modules must be documented in `doc/architecture.md`.
- Changes to graduation criteria, pace strategy, or persistence ownership require
  an ADR update when they alter the subsystem contract.
- Telemetry stays compatible with ADR-016: course workflow events use the
  metrics storage/public observability path and do not create a separate metrics
  store.

---

<a id="adr-018"></a>
## ADR-018: Autonomous Agent Control Plane Runner

**Статус:** Accepted
**Дата:** 2026-04-29
**Принято:** 2026-04-29
**Итерация:** Architecture review / 2026-04-29

### Контекст

The autonomous runner moved beyond a helper script and now acts as a local
control plane for team workflow execution: it prepares task context, runs agent
chains, records proof bundles, classifies failures, and gates closure with HITL
approval.

### Решение

- `scripts/run_autonomous.py` is the primary local control-plane entrypoint.
  Shell launchers are thin Windows convenience wrappers only.
- The runner must keep policy and gate logic in reusable modules under
  `scripts/` / `policies/` rather than embedding workflow rules in prompts.
- Proof artifacts, run status, and pipeline metrics are written under
  `archive/team_artifacts/` and `archive/pipeline_metrics.md`.
- Human approval remains mandatory for closure paths that skip or override DoD,
  quality gates, or package lifecycle checks.
- The control plane must preserve the project invariants from this ADR log and
  `doc/conventions*.md`: local-first operation, bounded write-set, token-safety
  checks, and explicit evidence for automated decisions.

### Update 2026-05-19: trigger executor classification

The DeepSeek trigger experiments clarified that `--trigger-cmd` is not one
kind of integration. A trigger can either execute locally, create a handoff for
another local agent, or act as a planning/review sidecar. ADR-018 therefore
classifies trigger commands by capability, not by model vendor.

Accepted extension:

- A production `--trigger-cmd` executor must have local file/tool access and
  must be able to create or update the package `execution_contract.md` as
  verifiable proof.
- Chat-only REST API triggers are handoff-only. They may create a `BLOCKED:`
  contract or metrics evidence, but they must not be documented or treated as
  package executors.
- `scripts/deepseek_agent_trigger.ts` is retained as an experimental DeepSeek
  Chat API handoff/gate experiment. It is useful for validating prompts and
  failure classification, but not for closing code/orchestration packages.
- The target DeepSeek executor is a separate DeepSeek TUI wrapper
  (`scripts/deepseek_tui_agent_trigger.ts`, planned) because `deepseek exec
  --auto --output-format stream-json` has demonstrated local `read_file` and
  `write_file` tool access.
- Every local executor trigger must record model, session id, status, token
  counts, contract path, and budget verdict in metrics. Budget enforcement is a
  post-run gate when the underlying CLI does not expose pre-run token limits.

Evidence from the 2026-05-18/19 smoke tests:

- DeepSeek Chat API completed an API call but could only return text; it was
  correctly rejected when the response was a command plan instead of proof.
- DeepSeek TUI read `doc/current_task.md` successfully through `read_file`
  (`status=completed`, `input_tokens=61547`).
- DeepSeek TUI wrote and read back a scratch file successfully
  (`status=completed`, `input_tokens=92272`).
- DeepSeek TUI created a scratch `execution_contract.md` successfully when run
  from the repository root (`model=deepseek-v4-pro`, `input_tokens=92797`).
- A minimal isolated cwd with only `DEEPSEEK.md` still used about 49k input
  tokens on `deepseek-v4-flash`, so a 20k hard budget is not realistic for this
  CLI without additional upstream context controls.

DeepSeek -> IDE/local-agent alternatives:

| Option | Role | Pros | Cons | Decision |
|---|---|---|---|---|
| DeepSeek Chat API -> IDE handoff | Generates/validates handoff text, then a human or IDE agent executes `doc/current_task.md`. | Simple, cheap to wire, exercises validators and failure gates. | No local file/shell tools; cannot execute package work; can only stop with `BLOCKED` for code tasks. | Keep as experimental handoff-only path. |
| DeepSeek TUI direct executor | `workflow.py` launches a wrapper around `deepseek exec --auto --output-format stream-json`. | Real local file reads/writes; non-interactive stream events; model can be selected through env; can create proof contract. | High baseline context cost; no documented `--max-input-tokens`/`--no-context` flags; `--auto` requires strict write-set and contract gates. | Recommended target DeepSeek path. |
| DeepSeek TUI planner + Cursor/Codex executor | DeepSeek produces critique/plan; existing local IDE agent performs edits and tests. | Lower risk for write operations; good second-opinion loop; easy fallback when TUI budget is too high. | Not zero-click; handoff drift is possible; requires two-agent coordination. | Supported fallback for high-risk packages. |
| Cursor SDK executor + DeepSeek sidecar | Cursor remains the local executor; DeepSeek is optional planner/reviewer. | Uses the existing production-capable local agent path; clearer file/tool semantics. | Not DeepSeek-native execution; depends on Cursor SDK credentials and behavior. | Production option when Cursor SDK is available. |
| Manual Continue/IDE execution | `workflow.py` prepares `doc/current_task.md`; user opens it in the IDE agent. | Lowest implementation risk; strong human control; works today. | Manual, slower, weaker metrics, not a full autonomous loop. | Recovery/manual mode. |
| Future MCP/ACP/local-agent adapter | Standardize trigger events and tool permissions behind a protocol adapter. | Best long-term isolation and observability; can support multiple agents. | More infrastructure; current DeepSeek CLI exposes only minimal documented flags. | Revisit after TUI wrapper proves stable. |
| DeepSeek TUI → `_trigger_shared.ts` child adapter | Extend `_trigger_shared.ts` with `spawnChildProcess()` helper; TUI wrapper feeds `runTrigger()` loop through a `ChildProcessAdapter` interface. | Keeps shared contract surface; metrics and gates remain unified; TS tests can mock child process spawn; composable with orchestrator. | Requires extending `_trigger_shared.ts` with spawn lifecycle and stream parser; increases shared module size. | Recommended implementation pattern for TUI wrapper. |
| Smart Trigger Orchestrator | A meta-trigger (`trigger_orchestrator.ts`) that selects strategy based on package risk, available credentials, and historical metrics; chains triggers (plan → execute → verify); falls back automatically. | Eliminates manual trigger selection; risk-aware multi-model execution; automatic fallback chain; unified metrics with strategy rationale. | Higher implementation complexity; requires all individual triggers to stabilize first; strategy heuristics need tuning. | Next-level target after TUI wrapper stabilizes. Design: `doc/team_workflow/guides/workflow_trigger_orchestrator_design.md`. |

### Последствия

- New runner capabilities require tests or smoke checks near the control-plane
  scripts, plus documentation in architecture/runbook files when behavior
  changes.
- Agent orchestration remains a local automation layer. It does not create new
  application runtime endpoints and must not bypass API, persistence, provider,
  prompt, or guardrail contracts.

---

<a id="adr-019"></a>
## ADR-019: Query/Graph god-module split boundary (Wave B3)

**Статус:** Accepted
**Дата:** 2026-05
**Итерация:** Architecture review remediation / AR-2026-04-21-005 (P5b Wave B3)

### Контекст

`app/query_service.py` и `app/knowledge_graph.py` превышали локальные пороги размера (>600 строк) и накапливали смешанную ответственность (FAQ cache path, ingestion graph payload assembly, чтение графа).

### Решение

- **Ingestion graph payload:** сборка словаря `concepts/documents/edges` из метаданных документов вынесена в `app/knowledge_graph_payload.py`. Публичный импорт `build_graph_payload_from_documents` и совместимость с потребителями (`app.knowledge_graph`, bundle writer, тесты) сохраняются через реэкспорт из фасада `knowledge_graph.py`.
- **FAQ cache path ответа:** поиск похожих вопросов и сборка полного результата при cache hit вынесены в `app/query_faq_cache.py` (`try_faq_cache`). `query_service.answer_question` остаётся оркестратором; HTTP/UI контракты полей ответа не меняются.
- Алгоритмические блоки (`_tarjan_sccs`, `JsonKnowledgeGraph`, proxy `knowledge_graph`) остаются в `knowledge_graph.py`; циклических импортов с payload-модулем нет.

### Последствия

- Последующие сплиты B3/B4 должны сохранять тонкий фасад и избегать дублирования публичных entrypoints.
- Регрессии контролируются целевым pytest bundle `tests/test_query_service.py` + `tests/test_api.py` и при необходимости `tests/test_knowledge_graph.py`.

---

<a id="adr-020"></a>
## ADR-020: Smart Study Router and SSR ML Hybrid Contract

**??????:** Accepted
**????:** 2026-05-11
**????????:** Architecture review remediation / AR-2026-05-11-005

### ????????

Smart Study Router (SSR) ???????? ????????? ??????? ??? ?? ????? home hub,
adaptive plan, tutor chat ? flashcards. ????????? ?????? ?????????? explainable,
local-first ? ?????????? ??? ??????: ???????????? ????? primary action,
????????????, ????????? evidence-??????? ? ???????????? LLM-????? ??????? ???????.

### ???????

- `app/smart_study_router.py` ???????? public facade ? compatibility import surface ??? UI/tests.
- Rule engine ????? ? `app/smart_study_recommendation.py`; ???????? ???????????? ? `hint_kind`, `primary_nav`, labels, secondaries, route pedagogy ? optional ML audit.
- Evidence ledger ????? ? `app/smart_study_evidence.py` ? ???????? ?????? ?? ?????????? ????????? ??????????, ?? ?? ????????? ???????.
- Optional ML hybrid ????? ? `app/smart_study_ssr_ml.py`: ?? ????? rerank ?????? ?????? rule-allowed tier, ?????? ????????? confidence/latency budgets ?? `Settings` ? fallback ?? rule recommendation ??? ????? ?????? ?????/??????/latency.
- Weight artifacts ??????????? ????? `app/ssr_ml_reranking.py`; ?????? `numpy` dependency ????????? ? `requirements.txt`.
- LLM personalization ??? ?????? ?????????? ????? ? `app/ui/adaptive_plan_llm_enrichment.py`. ??? ????? ???????? ?????? paragraph text, ?? ?? `hint_kind`, `primary_nav` ??? ????????????? ?????????.
- JSONL profiles SSR LLM ???????? append-only observability artifacts, ? ?? user-state persistence.

### ???????????

- SSR decisions ???????? deterministic ? ???????????? ??? Streamlit/LLM.
- ML ? LLM ? adapters behind explicit fallbacks, ?? sources of truth.
- ????? SSR surfaces ?????? ???????????? facade ??? ????????????? focused modules; ????? router/evidence store/LLM contract ??????? ?????????? ADR.

---

<a id="adr-021-latency-budgets"></a>
## ADR-021: Surface latency budgets (Move 2 MVP — mission_load)

**Статус:** Accepted
**Дата:** 2026-05-24
**Итерация:** strong-move-latency-budget-contracts-v1 (balance plan §11.2, Phase 7)

### Контекст

Move 2 generalizes Phase 2 timeout policy per UX surface. Phase 2 `home_rag_llm_local_*_timeout_sec` (seconds) remains primary-chat-only SSoT. MVP wraps only `mission_load` — the disk/session-cache path for first-session artifact (`load_first_session_artifact_cached_for_scope`).

### Решение

- **Registry:** `app/latency_budget.py` — `SURFACE_BUDGETS` with ms thresholds per surface and variant (`cold` / `warm`).
- **mission_load cold/warm:** cold 800/1500/3000 ms; warm 200/600/1500 ms. Warm = session cache hit before disk read.
- **Ladder (steps 1–4):** under target → full path; approaching soft → `degrade_reason=approaching_soft`; soft breach → emit `surface_breached_soft`, continue load; hard breach → emit `surface_breached_hard`, map to existing Empty/Error UI (disk-only — **no** `get_llm()`, **no** Phase 2 provider fallback).
- **Trace:** dedicated JSONL `logs/latency_budget.jsonl` (canonical for `scripts/local_status.py`); optional debug duplicate via `log_event()`.
- **Vocabulary:** `surface`, `variant`, `target_ms`, `soft_ms`, `hard_ms`, `actual_ms`, `degraded`, `degrade_reason`, events `budget_completed`, `surface_breached_soft`, `surface_breached_hard`.
- **Banner transport:** sp1 writes session_state keys; sp2 renders banner (out of scope for this ADR half).
- **Non-goals:** in-flight HTTP/provider cancel on hard breach; wrapping quiz/SSR/ingestion; env-configurable ms thresholds in MVP.

**Rollout v1 extension (epoch-latency-budget-surface-rollout-v1):**

- **Surfaces added:** `query` (2500/4000/8000 ms), `tutor_turn` (1500/3000/6000 ms). Flat surfaces use registry variant key `cold` via `_thresholds_for` fallback.
- **Wrap boundary:** `answer_question` in `query_service.py` — after `_prepare_query_context`, around main answer flow + exception/fallback handlers. Surface = `tutor_turn` iff `query_mode=tutor`, else `query`.
- **Hard breach LLM surfaces:** emit `surface_breached_hard` in JSONL/session tape only — **no** tuple mutation (unlike `mission_load` disk empty/error mapping). Phase 2 UX delegated to existing `answer_question` / provider fallback paths.
- **Ladder steps 1–2:** observability only (trace-only); no retrieval-k / rerank / timeout mutation on `approaching_soft`.
- **Aliases (plan §11.2, comment-only):** `scoped_answer` → `query`, `tutor_next_step` → `tutor_turn`.
- **Debug bridge:** `debug.latency_budget` on every `answer_question` response (`budget_meta_to_session_event`); sp2 syncs to session_state for banner.

**Quiz surface extension (epoch-latency-budget-quiz-surface-v1):**

- **Surfaces added:** `quiz_gen` (2000/3000/6000 ms), `quiz_submit` (2000/3000/6000 ms). Flat surfaces use registry variant key `cold`.
- **Scope:** `quiz_gen` = scoped/micro quiz LLM generation (`generate_scoped_quiz` post-validation body; `generate_micro_quiz` LLM+parse only). `quiz_submit` = full `process_micro_quiz_outcome` service path (diagnose + SR + save + recommended_next + gamification).
- **Wrap boundaries:** pre-validation fast-fail and `InvalidMicroQuizQuestionError` **before** `with_budget` — no budget SLO attribution. Scoped local self-check submit (UI index compare) — out of MVP scope for `quiz_submit`.
- **Hard breach quiz surfaces:** emit `surface_breached_hard` in JSONL/session tape only — **no** tuple mutation (unlike `mission_load` disk empty/error mapping); **no** BALANCED chat profile switch. Degradation UX = existing quiz template/resilience/offline paths.
- **API/service bridge:** optional top-level `latency_budget` on quiz service returns and `POST /quiz/generate`, `/quiz/generate/scoped`, `POST /quiz/evaluate` (`budget_meta_to_session_event` shape); sp2 syncs via `sync_latency_budget_from_payload`.
- **US-5.1:** service-level budget clock; learner-visible &lt; 2s validated by regression tests, not UI-render-included clock.

### Последствия

- Future surfaces wrap via `with_budget()`; lint for untagged call sites deferred.
- Hard breach on slow disk is **non-preemptive** — I/O may complete past hard wall; user sees terminal Empty/Error, not infinite spinner.
- Owner must accept (Proposed → Accepted) before merge per backlog `re_entry_condition`.

---

<a id="adr-022-session-tape"></a>
## ADR-022: Session tape (append-only learning arc trace)

**Статус:** Proposed
**Дата:** 2026-05-24
**Итерация:** strong-move-session-tape-v1 (balance plan §11.3, Move 3)

### Контекст

Move 3 — learning arc теряется между четырьмя aggregate stores (SRS, course_cache, session_store, Chroma). Нужен append-only per-session trace для восстановления CJM #2 First Answer, #4 First Micro-Quiz, #7 Spaced Rep Due и cross-loop observability (US-3.1, US-7.3, US-16.0).

### Решение

- **Store:** `data/sessions/<session_id>.jsonl` — одна строка JSON на событие; atomic append (open `a`, write line, flush).
- **Schema v1 envelope:** `ts` (ISO8601 UTC), `event`, `session_id`, `schema_version: 1`, optional `course_id`, optional `surface`, `payload` (object).
- **Event types (MVP emit):** `session_started`, `session_ended`, `mission_loaded`, `question_asked`, `retrieval_completed`, `answer_surfaced`, `quiz_attempt`, `surface_breached_soft`, `surface_breached_hard`, `budget_completed`.
- **Reserved (not emitted MVP):** `card_created`, `dwell_ms` — bump `schema_version` + amend ADR before emit.
- **Privacy:** writer strips forbidden keys (`answer`, `raw_text`, `chunk`, `front`, `back`, `api_key`, …) at write time; no raw question/answer/card text in tape.
- **Reader:** `app/session_replay.py::iter_events` — lenient skip malformed/partial lines; never raises to caller.
- **Ownership:** session lifecycle module (`session_tape.py`); hooks in sp2 call writer only — production UX reads existing aggregates, not tape.
- **Store relationships:** mastery→SRS, readiness→course_cache, chat history→session_store, **session arc→tape**.
- **Debug API:** `GET /debug/session-tape/{session_id}` behind `session_tape_debug_replay_enabled=False` (default); no learner nav link.
- **Offline/E2E:** when `session_id` present, always write; payload tagged `offline: true` when `home_rag_e2e_offline` or `home_rag_micro_quiz_offline`.
- **Filename sanitization:** reject `/`, `\`, `..` in `session_id`; fallback SHA256 hex.

### Последствия

- Phase 2 readers (promise card, adaptive_plan) gated ≥2 weeks observation after write-only MVP.
- Non-blocking I/O: tape failure never blocks `/ask` or UI render.
- `session_started` idempotent per process (in-memory dedup).
- Owner must accept (Proposed → Accepted) before merge per backlog `re_entry_condition`.

---

<a id="adr-024"></a>
## ADR-024: Local balanced model for hometutor learning-plane

**Статус:** Accepted
**Дата:** 2026-06-04

### Контекст

После перехода localhost balanced-mode на LM Studio нужно было выбрать локальную модель
по умолчанию для learning-plane и подтвердить, что она не требует тихого cloud fallback,
не уходит в reasoning leakage и выдерживает реальные RAG/tutor/quiz smoke cases.

### Решение

Используем `qwen/qwen3.6-27b` как balanced local default model для learning-plane:

- `LLM_MODEL=qwen/qwen3.6-27b`
- `QUIZ_LLM_MODEL=qwen/qwen3.6-27b`
- `GRAPH_MODEL=qwen/qwen3.6-27b`
- `SSR_LLM_MODEL=qwen/qwen3.6-27b`

### Evidence

- Smoke Gate v7: 18/18 PASS (`logs/smoke_qwen3_6_27b_v7.json`)
- `cases_error: 0`
- `failures: []`
- `require_model: true`
- `require_no_fallback: true`
- `max_reasoning_tokens: true`
- `reasoning_tokens: 0`
- Latency: avg 13.204s, p50 8.716s, p95 25.831s

### Последствия

`qwen/qwen3.6-27b` принята как balanced local model для hometutor. В текущей локальной
LM Studio конфигурации она даёт достаточное качество для grounded RAG answers,
tutor/quiz generation и anti-hallucination behavior.

Остаточный quality follow-up: `prompt-role-unification-v1` должен добить оставшиеся
tutor/quiz/minicheck user-only prompt paths до `system + user` или explicit allowlist,
с машинной проверкой `require_model`, `require_no_fallback` и `max_reasoning_tokens=0`.

---

## Как работать с этим документом

1. **Новое решение:** создать секцию с номером ADR-0XX, статус `Proposed`, описать контекст, альтернативы, предлагаемое решение, последствия. Отправить на ревью.
2. **Принятие:** изменить статус на `Accepted`, зафиксировать дату.
3. **Отклонение:** изменить статус на `Rejected`, записать причину. Не удалять — отклонённые решения так же ценны, как принятые.
4. **Устаревание:** создать новый ADR, который ссылается на старый (`Supersedes ADR-00X`). Старый ADR получает статус `Superseded by ADR-0YY`.
5. **Поиск:** искать по контексту проблемы, а не по номеру. Если через год кто-то спросит «почему Chroma, а не PGVector» — ответ в ADR-002.
