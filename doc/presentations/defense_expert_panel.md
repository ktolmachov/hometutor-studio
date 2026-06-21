# hometutor — Экспертная RAG/AI-защита

> Вторая виртуальная защита по [`doc/defense_presentation.md`](defense_presentation.md).  
> Формат: панель сильных экспертов по RAG, retrieval, evaluation, AI safety, MLOps, privacy и educational AI.  
> Цель: найти неочевидные слабые места, подготовить ответы студента и зафиксировать улучшения в презентации.

---

## Состав экспертной панели

| Роль | Фокус атаки |
|---|---|
| RAG Architect | Архитектура retrieval, chunking, Chroma, two-stage retrieval |
| Retrieval Scientist | Метрики retrieval, BM25/vector fusion, reranking, recall@k |
| LLM Evaluation Lead | Faithfulness, Answer Relevancy, baseline, regression gates |
| AI Safety Engineer | Prompt injection, data exfiltration, output guardrails |
| MLOps / Infra Lead | Latency, cost, observability, model migration, failure modes |
| Privacy Engineer | Local-first claims, cloud trade-offs, data sovereignty |
| Educational AI Researcher | Mastery model, SRS, tutor quality, learning transfer |
| Product Reviewer | Differentiation from NotebookLM, Anki, Obsidian, ChatGPT |

---

## Вердикт панели

**Сильная сторона проекта:** это не “ещё один RAG-чат”, а локальный учебный контур: `answer → tutor → quiz → SRS → mastery → plan`. Архитектурные границы (`provider.py`, `config.py`, guardrails, routers, persistence) выглядят осознанно и защищаемо.

**Главная претензия экспертов:** защита должна избегать маркетинговых абсолютов. Сильная защита RAG-проекта строится не на словах “production-ready” и “высокое качество”, а на eval-run, threat model, failure modes, cost/latency breakdown и честном описании ограничений.

**Что исправлено в презентации после этой панели:**
- Добавлен экспертный eval-контур: retrieval metrics, grounding, answer quality, cost/latency, regression baseline.
- Формулировка “production-ready” заменена на “production-oriented” для локального one-user сценария.
- Явно добавлена граница: без опубликованного eval-run нельзя численно утверждать “высокое качество”.
- Добавлены ограничения: BM25 in-memory, OCR/PDF parsing, слабость локальных моделей, confidence не равен вероятности истинности.
- В список связанных документов добавлена ссылка на этот экспертный разбор.

---

## Бреши, найденные экспертами, и как их закрывать на защите

| Брешь | Почему опасно | Как отвечать |
|---|---|---|
| “Production-ready” звучит слишком широко | Эксперт спросит про SLO, multi-user, monitoring, disaster recovery | “Production-oriented для локального one-user deployment; internet-scale требует отдельной infra” |
| “Высокие метрики” без run-id | Нельзя проверить воспроизводимость | “Показываю методику и eval-инфраструктуру; числа только из конкретного eval-run” |
| Local-first vs cloud LLM | Можно обвинить в противоречии | “State/index local-first; inference может быть local или cloud, fully offline только local-local” |
| Confidence score | Могут спутать с вероятностью истинности | “Это retrieval confidence/explainability signal, не truth probability” |
| Hybrid retrieval | Нужны доказательства выигрыша | “Сравнение режимов через recall@k/MRR/hit rate на одном dataset — следующий обязательный артефакт” |
| BM25 in-memory | Риск RAM/warm-up на больших корпусах | “При больших корпусах нужен persistent sparse index или внешний search backend” |
| Prompt injection | RAG-системы уязвимы через документы | “Есть input/output guardrails; следующая зрелость — document-level policy и adversarial eval corpus” |
| OCR / плохие PDF | Retrieval не спасает плохой parsing | “Source-readiness diagnostics есть; OCR-ingest — отдельный scope” |
| Tutor quality | Хороший ответ не равен обучению | “Нужны educational metrics: retention, transfer, quiz outcomes, SRS stability” |

---

## Сложные вопросы экспертов и ответы студента

### 1. RAG Architect

**Вопрос:** Вы называете pipeline “production-oriented”. Что именно делает его production-oriented, если это локальный проект, а не сервис с SLO?  
**Ответ:** Я не утверждаю internet-scale production. Production-oriented здесь означает инженерные практики для надёжного локального RAG: централизованный provider, конфигурационные профили, typed pipeline, retrieval trace, self-correction, reranker, guardrails, eval-сервис, cost logs, partial reindex и документация архитектурных инвариантов. Для multi-user production потребуются отдельные SLO, auth, tenancy, persistent sparse search и ops-инфраструктура.

**Вопрос:** Почему chunk size около 700 и overlap 50 — это не магическое число?  
**Ответ:** Это текущая рабочая настройка, а не универсальная истина. Для защиты корректно сказать: chunking должен оцениваться на корпусе через retrieval metrics. В проекте параметры вынесены в `RetrievalSettings`, значит их можно сравнивать экспериментально без переписывания pipeline.

**Вопрос:** Как вы предотвращаете “lost in the middle”, если synthesis получает много контекста?  
**Ответ:** Через document-level narrowing, rerank/top-n, specialized prompts и ограничение контекста. Но это зона риска: для длинных synthesis-запросов нужен отдельный eval на multi-document QA и проверка source coverage, а не только faithfulness.

**Вопрос:** Почему Chroma остаётся приемлемым выбором, если есть Qdrant, Weaviate и PGVector?  
**Ответ:** Потому что задача local-first/one-user. Chroma PersistentClient минимизирует operational burden и хорошо встраивается в llama-index. Если появятся требования multi-user, concurrent writes, ACL и managed ops, выбор надо пересмотреть.

### 2. Retrieval Scientist

**Вопрос:** Как доказать, что hybrid retrieval лучше vector-only, а не просто звучит солиднее?  
**Ответ:** Нужен одинаковый eval dataset и сравнение `vector_only`, `hybrid`, `bm25_only`, `doc_then_chunk` по recall@k, MRR, hit rate, route match и latency. В презентацию добавлен eval-контур именно для такого доказательства.

**Вопрос:** RRF объединяет ранги, но не нормализует смысл scores. Почему это нормально?  
**Ответ:** RRF хорош тем, что устойчив к несовместимым score-шкалам dense и sparse retrievers. Это простая и объяснимая baseline-стратегия. Дальше можно сравнивать weighted fusion, learned reranking или cross-encoder reranking по eval-набору.

**Вопрос:** Что случится с точными терминами на русском и английском вперемешку?  
**Ответ:** Vector retrieval может сгладить термин, BM25 ловит точные строки, но морфология и транслитерации остаются риском. Для смешанных корпусов стоит добавить нормализацию, synonyms dictionary или language-aware sparse retrieval и проверить на bilingual eval cases.

**Вопрос:** Вы измеряете Answer Relevancy, но где retrieval precision?  
**Ответ:** Это справедливый укол. Answer Relevancy не заменяет retrieval metrics. В `eval_service` есть retrieval recall/MRR/hit rate, но для экспертной защиты надо явно показывать retrieval table отдельно от LLM-answer metrics.

### 3. LLM Evaluation Lead

**Вопрос:** LLM-as-Judge сам может ошибаться. Почему комитет должен доверять Faithfulness?  
**Ответ:** Не должен слепо. LLM-as-Judge — один слой, а не истина. Его надо сочетать с deterministic checks, source coverage, human review и baseline/regression. Поэтому презентация теперь говорит о трёхслойной оценке, а не о магической метрике качества.

**Вопрос:** Где golden dataset? Без него regression gate не имеет смысла.  
**Ответ:** Минимальный golden dataset должен включать qa, keyword, overview, synthesis, negative/no-answer, prompt-injection и плохие источники. Если на защите спросят статус, честный ответ: инфраструктура есть; сильный следующий артефакт — зафиксированный dataset и baseline JSON.

**Вопрос:** Как вы отделяете retrieval failure от generation failure?  
**Ответ:** Через retrieval trace, source scores, route, rerank settings и answer quality metrics. Если context recall низкий — проблема retrieval. Если контекст хороший, но ответ неверный — проблема prompt/generation/postprocessing.

**Вопрос:** Почему human feedback в UI не является научной оценкой?  
**Ответ:** Потому что это noisy product signal: пользователи оценивают полезность, а не обязательно factuality. Его надо использовать как сигнал triage, но не как единственную метрику качества.

### 4. AI Safety Engineer

**Вопрос:** RAG prompt injection часто приходит не от пользователя, а из документа. Ваш input guardrail это не поймает. Что делать?  
**Ответ:** Да, input guardrail недостаточен для document-borne prompt injection. Нужны document-level sanitization, policy in system prompt, source trust metadata, adversarial corpus, output guardrails и запрет выполнять инструкции из retrieved content. В текущей защите это надо признать как важный security follow-up.

**Вопрос:** Может ли модель раскрыть личные заметки из другого курса?  
**Ответ:** Риск связан с scope filtering. Course workspace должен ограничивать retrieval соответствующей папкой/курсом. На защите важно подчеркнуть: изоляция курса — продуктовая и retrieval-функция, но для multi-user privacy понадобятся ACL и tenant isolation.

**Вопрос:** Что будет, если пользователь спросит: “игнорируй источники и ответь из общих знаний”?  
**Ответ:** Guardrails и prompt должны удерживать answer grounded. Если источников нет или они слабы, корректное поведение — отказаться или дать дисклеймер. Это проверяется negative/no-answer eval cases.

**Вопрос:** Как вы защищаете output от PII leakage?  
**Ответ:** В guardrails есть output checks/redaction path, но зрелый ответ: PII leakage требует отдельной policy, тестового набора и audit logs. Для академического проекта важно показать boundary и направление усиления.

### 5. MLOps / Infra Lead

**Вопрос:** Где latency budget по стадиям? Общая latency ничего не объясняет.  
**Ответ:** Правильно. Нужен breakdown: classify, rewrite, embedding query, retrieval, rerank, generation, judge. В презентации теперь указано, что latency доказывается profiler/cost logs, а не одним средним числом.

**Вопрос:** Что произойдёт при смене embedding-модели? Старый индекс станет несовместимым?  
**Ответ:** Да, поэтому проект хранит metadata индекса и проверяет embedding model mismatch. При смене embedding-модели нужен reindex. Это сильная часть защиты: model migration учтена как operational concern.

**Вопрос:** Как вы предотвращаете runaway cost при synthesis и eval judge?  
**Ответ:** Через настройки моделей, token budgets, cost logs, sample rate для async judge и ограничение retry. Для защиты надо говорить не “дёшево”, а “стоимость наблюдаема и управляется”.

**Вопрос:** Что будет при пустом индексе или corrupted Chroma?  
**Ответ:** Должен быть явный fallback: пользователь видит, что индекс пуст/неактуален, получает next action для reindex, а не hallucinated answer. Это стоит демонстрировать как failure-mode behavior.

### 6. Privacy Engineer

**Вопрос:** “Local-first” звучит как privacy guarantee. Это юридически опасно. Как переформулировать?  
**Ответ:** “Local-first storage and state; inference privacy depends on selected provider.” Это честнее. В презентации уже поправлено: полностью offline только при локальных LLM и embeddings.

**Вопрос:** Если используется OpenRouter/OpenAI-совместимый endpoint, какие данные уходят наружу?  
**Ответ:** Уходит пользовательский вопрос и retrieved context, достаточный для ответа. Индекс и SQLite остаются локально, но содержимое фрагментов всё равно передаётся провайдеру. Поэтому cloud mode не подходит для чувствительных материалов без отдельного согласия.

**Вопрос:** Можно ли удалить данные полностью?  
**Ответ:** Для зрелого продукта нужен documented data deletion flow: Chroma index, SQLite state, logs, feedback, history, cost logs. Если такой flow не показан, лучше не заявлять compliance, а говорить о локальном контроле файлов.

### 7. Educational AI Researcher

**Вопрос:** Почему mastery score действительно отражает обучение, а не просто активность?  
**Ответ:** Это модельный proxy. Он становится сильнее, если учитывает quiz correctness, SRS outcomes, time decay, difficulty и transfer-level задания. На защите нужно говорить “mastery signal”, а не “доказанное знание”.

**Вопрос:** Сократический tutor может раздражать или вести не туда. Как оценивать педагогическое качество?  
**Ответ:** Через tutor regression dataset, human review, outcome metrics после quiz и retention over time. Хороший критерий — улучшение ответов ученика и стабильность recall/transfer, а не красота объяснения.

**Вопрос:** Concept Graduation через 7+ дней transfer — это педагогически обосновано?  
**Ответ:** Это практическое правило для MVP. Его надо калибровать на пользовательских данных. Корректный ответ: graduation rule configurable/evaluable, а не универсальная педагогическая константа.

### 8. Product Reviewer

**Вопрос:** NotebookLM тоже отвечает по документам. Почему пользователь выберет ваш проект?  
**Ответ:** Потому что здесь фокус не только на Q&A, а на обучении: quiz, flashcards, SRS, mastery, adaptive plan, локальный state и course workspace. NotebookLM силён в document Q&A, но не закрывает весь цикл повторения.

**Вопрос:** Anki уже лучше в SRS. Зачем свой SRS?  
**Ответ:** Anki силён как карточная система, но он не знает retrieval context и не строит tutor/quiz от ответа. Собственный SRS нужен для бесшовного перехода из RAG-ответа в проверку и повторение. Экспорт в Anki может быть интеграцией, а не заменой ядра.

**Вопрос:** Что является killer demo для комиссии?  
**Ответ:** Один сценарий: загрузить материал → спросить сложный вопрос → показать источники и confidence → нажать “Учить эту тему” → получить tutor/quiz → создать flashcard → увидеть mastery/progress. Это демонстрирует отличие от обычного RAG-чата.

---

## Финальный ответ студента экспертной панели

“Я согласен с главным замечанием: защищать RAG-проект нельзя только красивой диаграммой. Поэтому я уточняю позиционирование: это production-oriented local-first учебный ассистент для one-user сценария, а не заявка на internet-scale SaaS. Сильная часть работы — полный учебный цикл и архитектурные границы. Слабая часть, которую я честно фиксирую как следующий инженерный шаг, — публичный eval baseline с retrieval metrics, adversarial document-injection cases и latency/cost breakdown. После замечаний панели я уже усилил презентацию: добавил eval-контур, ограничения, и убрал необоснованные абсолютные claims.”

---

## Рекомендации экспертов на следующий спринт

1. Зафиксировать `eval_data/defense_eval_questions.json` с категориями: qa, keyword, overview, synthesis, negative, injection.
2. Прогнать `vector_only` / `hybrid` / `doc_then_chunk` и сравнить recall@k, MRR, hit rate, latency.
3. Добавить adversarial RAG-набор: prompt injection внутри документа, конфликтующие источники, no-answer.
4. Сделать один слайд/таблицу “cost and latency by stage” из profiler/cost logs.
5. Документировать data deletion flow для Chroma, SQLite, logs/history/feedback.
6. Явно назвать confidence `retrieval confidence`, чтобы не обещать probability of truth.
7. Для course workspace описать boundary: folder/course scope сейчас, ACL/tenant isolation — будущий multi-user слой.
8. Для педагогики добавить eval не только answer quality, но и learning outcome: quiz correctness, retention, transfer tasks.
