# Продуктовая Идея

Статус: `Roadmap`
Роль: продуктовая идея и направления развития.
Не считать этот файл источником правды о том, что уже реализовано; текущие возможности описаны в `vision.md`, `user_guide.md` / `user_guide_details.md` и коде.

**Сводная ось эпох / волн / пакетов:** [`doc/roadmap.md`](roadmap.md). **Факт исполнения и закрытий:** только `doc/backlog_registry.yaml` + `doc/closed_iterations.md`.

## Идея

Проект `home-rag_v2` — локальный RAG-сервис для работы с личной базой знаний, заметками и проектной документацией. Он индексирует документы из папки `data/`, находит релевантные фрагменты и формирует ответ с привязкой к источникам.

Основной сценарий использования:
- задать вопрос по своим файлам;
- быстро получить краткий ответ;
- увидеть, на какие документы и фрагменты опирается система;
- при необходимости посмотреть источник или объяснение выбранного файла;
- перейти от ответа к теме, связанным документам и synthesis по выбранной выборке.

## Что уже умеет проект

Сервис поддерживает несколько способов работы:
- FastAPI API для запросов, переиндексации, профилирования и служебных операций;
- CLI-клиент для локальных запросов;
- Streamlit UI для интерактивной работы с ответами и источниками.

Поддерживаемые возможности:
- индексация файлов `.pdf`, `.txt`, `.md`, `.docx`, `.html`;
- RAG-ответы с источниками, confidence и debug-данными;
- hybrid retrieval: vector search + BM25 для keyword-heavy запросов;
- metadata enrichment и document summaries при индексации;
- двухуровневый retrieval `doc -> chunk` для обзорных и synthesis-сценариев;
- query rewriting и classify/router для типов `qa`, `keyword`, `overview`, `synthesis`;
- профили `fast` и `quality`;
- типизированная конфигурация через pydantic-settings с валидацией;
- централизованный провайдер LLM/embeddings (`app/provider.py`);
- input guardrails: валидация длины запроса, детекция prompt injection (EN/RU);
- output guardrails: проверка на пустой ответ, утечку системных инструкций, наличие источников, фильтрация PII/секретов;
- FAQ-память для похожих вопросов;
- diff по изменениям в индексируемых файлах;
- pipeline profiling и compare/eval сценарии;
- observability-контур: runtime metrics, cost/quality dashboard, история запросов и feedback;
- каталог тем, synthesis по теме или набору документов, unified knowledge search и proactive suggestions;
- knowledge workspace в Streamlit UI: тема -> документы -> synthesis;
- learning plan endpoint и UI-сценарий для темы или выбранных документов;
- follow-up режим `Study mode` для учебных вопросов без полноценного session-based multi-turn;
- session-based multi-turn: `session_id`, persisted session history, bounded history, condense в pipeline и отдельный chat mode;
- tutor mode поверх multi-turn: structured tutor response, CTA `Объясни проще` / `Дай пример` / `Проверь меня` / `Следующий шаг`, Socratic follow-up, micro-quiz, immediate feedback и adaptive quiz difficulty;
- return-to-learn UX: карточки `Продолжить обучение` и `Пора повторить`, resume actions, mastery dashboard;
- Smart Study Router (product direction): объяснимая подсказка следующего учебного шага по learning state, чтобы пользователь не выбирал режим вручную после ответа, tutor, quiz, flashcards или dashboard; → **[детальное описание killer feature](smart_study_router.md)**;
- trust UX для tutor и Q&A: confidence, число источников, coverage warning;
- guided tutor entry points: `Понять тему`, `Подготовиться к экзамену`, `Разобрать задание`, плюс глубина ответа `Коротко / С примерами / Глубоко`;
- Streamlit (ит. 19.2c): навигация по разделам списком с группами, onboarding → чат тьютора, список источников в trust-панели из сессии, раздельные карточки «Продолжить чат с тьютором» / тема-план, мост из быстрого ответа в тьютора, опционально `SHOW_TUTOR_DEV_TOOLS` для отладки шаблона квиза;
- explain/content для `.txt`, `.md`, `.html`, `.pdf`.

## Текущее архитектурное состояние

Проект прошёл серию закрытых итераций (см. `doc/backlog_registry.yaml` и `doc/closed_iterations.md`: в т.ч. 1–16 и линейка 19.x частично) и имеет стабильную модульную структуру:

- `app/config.py` — типизированные настройки (`Settings`, `RetrievalSettings`) через pydantic-settings;
- `app/provider.py` — централизованное создание LLM и embedding-клиентов;
- `app/ingestion.py` / `app/ingestion_metadata.py` — загрузка, metadata enrichment и индексация документов в Chroma;
- `app/pipeline_factory.py` — единая сборка pipeline: prompt, фильтры, профили, postprocessors;
- `app/hybrid_retrieval.py` — hybrid retrieval и BM25-ветка;
- `app/pipeline_runner.py` / `app/pipeline_steps.py` — composable pipeline steps, `QueryContext`, rewrite/classify/fallback;
- `app/retrieval.py` — сборка query engine поверх pipeline factory;
- `app/query_service.py` — high-level сервис формирования ответа, tutor payload и trust signals;
- `app/knowledge_service.py` — темы, synthesis, KB overview, suggestions и unified knowledge search;
- `app/quiz_service.py` / `app/quiz_adaptive.py` — tutor quiz flow, micro-quiz feedback и adaptive difficulty;
- `app/user_state.py` / `app/spaced_repetition.py` — пользовательский прогресс, `quiz_results`, resume state и due review logic;
- `app/session_store.py` — persisted session history для multi-turn и tutor flow;
- `app/metrics.py` / `app/routers/metrics.py` — runtime-метрики, quality/cost dashboard, feedback и история;
- `app/guardrails.py` — input/output guardrails (prompt injection, PII, пустой ответ);
- `app/input_validation.py` — валидация входящих запросов для API;
- `app/utils.py` — общие утилиты (safe_preview и т.п.);
- `app/pipeline_profiler.py` — профилирование через тот же контур, что и production;
- `app/explain_service.py` — безопасный просмотр и объяснение файлов;
- `app/ui/main.py` — UI не только для Q&A, но и для knowledge workflows.

Единая pipeline factory и pipeline runner устранили расхождения между production, CLI, profiler и eval-сценариями, а knowledge layer перевёл продукт из pure Q&A RAG в knowledge workspace.

## Куда проект развивается дальше

> **2026-05:** нумерация итераций 14–19.x в этом разделе — **исторический нарратив**. Фактическая ось поставки: [`doc/roadmap.md`](roadmap.md) и машинный [`doc/backlog_registry.yaml`](backlog_registry.yaml).

Roadmap (подробности в `backlog_registry.yaml`; `tasklist.md` — производный weekly view):

**Что уже закрыто (Блок 0 + итерации 10–14):**
- поддержка `.html` в индексации;
- endpoint инспекции индекса (`GET /index/stats`);
- eval dataset и baseline/eval артефакты;
- hybrid retrieval (BM25 + vector search);
- smart ingestion: metadata enrichment, document summaries, metadata filtering;
- query understanding: rewriting, classify/router, `QueryContext`, pipeline runner;
- knowledge organization: каталог тем, synthesis, global KB search, knowledge workspace;
- observability: runtime-метрики, cost/quality dashboard, история, feedback, confidence/debug signals.

**Следующий этап: стабилизация (итерации 14–16):**
- internal cleanup: декомпозиция API и доступ к конфигурации через `get_settings()` / `get_retrieval_settings()` (итерация 15 — закрыто в коде);
- data lifecycle: blue-green reindex, versioning индекса (`index_registry.json`), метки в UI/history; partial reindex, `What Changed` и расширенный lifecycle — частично в backlog (см. `backlog_registry.yaml`, ит. 16);
- production hardening observability: error tracking, richer alerts, более строгие operational policy.

**Следующий этап: зрелость продукта (итерации 17 Core – 19.2):**
- 17 Core: knowledge graph platform, provenance, graph-augmented retrieval, self-correction, production-grade learning-plan foundation;
- 17.1 UX tail: home next-best-action surface поглощён E13; оставшиеся кандидаты только по новому owner decision (research sessions UX, graph visualization, compare mode);
- 18 Core: production hardening — retry/backoff, auth hooks, rate limiting, stronger runtime policies;
- 18.1 Performance tail: caches, response reuse, semantic/perf cost optimizations;
- 19: multi-turn context — `session_id`, persisted session history, bounded history, condense в pipeline и chat mode; `query_mode` здесь только transport/extension field;
- 19.1: Tutor MVP поверх session-based multi-turn — pedagogical behavior-layer уже частично реализован: structured tutor response, CTA, Socratic follow-up, micro-quiz, immediate feedback, trust signals и guided tutor entry points; открыты auto-loop по умолчанию и typed tutor contract;
- 19.2: Tutor Core Integration — tutor должен работать как единый learning loop `ответ -> 1 micro-quiz -> diagnostic feedback -> следующий шаг`, а не как набор несвязанных tutor-фич;
- 19.3: Retention Loop — spaced repetition, quiz feedback loop, dynamic learning plan, concept mastery, `Продолжить обучение` и `Пора повторить` уже частично реализованы; дальше остаются personalization и polishing;
- 19.4: Pedagogical Orchestration — learner-state, server-side orchestration next step, typed Socratic, session-aware homework behavior;
- 19.5: Personalized Tutor & Pedagogical Eval — адаптация по `learning_goal`, `quiz_mastery`, `due review` и отдельный набор pedagogical quality gates.
- 20.x: Smart Study Router — перенос паттерна workflow-роутера в учебный UX: `learning state -> next_action + reason + primary button`, с ideation TARGET `US-20.1`. **Полностью доставлен** (US-20.1–20.12). Детали: [`smart_study_router.md`](smart_study_router.md).

## Критерий пользы

Проект решает задачу, если пользователь может:
- быстро переиндексировать свою локальную базу знаний;
- получить осмысленный ответ по документам с понятными источниками;
- понять, как собран ответ и откуда взялись фрагменты;
- безопасно открыть и посмотреть текстовый источник;
- увидеть, какие темы уже есть в базе знаний;
- собрать конспект по теме или вручную выбранной подборке документов;
- построить базовый план обучения по теме или выбранным документам;
- продолжить tutor-сессию с последнего шага и быстро перейти к повторению просроченных тем;
- получить не только ответ, но и следующий учебный шаг с проверкой понимания;
- понимать, почему система предлагает именно этот следующий шаг, и выбирать безопасную альтернативу без потери learning loop;
- перейти от ответа к связанным темам и непросмотренным документам;
- сравнить качество и скорость разных конфигураций пайплайна;
- быть уверенным, что система защищена от prompt injection и утечек PII.

Целевые сценарии Knowledge Management (итерации 13, 17):
- увидеть, какие темы покрыты в базе знаний (каталог тем) — уже реализовано;
- получить структурированный конспект по теме из нескольких документов — уже реализовано;
- получить план обучения с порядком изучения и зависимостями — реализовано в базовом виде, углублённая версия остаётся в итерации 17;
- навигировать между связанными документами и концепциями.
