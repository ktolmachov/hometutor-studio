# Requirements Document

## Introduction

Фича создаёт два документа для академической защиты проектной работы по проекту **hometutor**:

1. **Скрипт выступления** (`doc/defense_presenter_script.md`) — структурированный текст на 3 минуты для академической защиты, отличный от конкурсного `doc/presenter_script.md`. Акцент на учебном процессе разработки, архитектурных решениях и результатах.

2. **Презентация проекта** (`doc/defense_presentation.md`) — Markdown-документ со структурой слайдов, охватывающий обзор продукта, архитектуру, скриншоты режимов, схему RAG/ingest, сравнение LLM-режимов, процесс разработки, идеи развития роутера и ссылки на связанные документы.

Оба документа должны быть самодостаточными: понятными без предварительного знакомства с кодовой базой, опираться на реальные артефакты проекта (скриншоты, сценарии, архитектурные решения).

## Glossary

- **Defense_Script**: Markdown-документ `doc/defense_presenter_script.md` — скрипт выступления на академической защите.
- **Defense_Presentation**: Markdown-документ `doc/defense_presentation.md` — структура слайдов для академической защиты.
- **Slide**: Логический раздел презентации, оформленный как секция второго уровня (`## Слайд N`).
- **RAG_Pipeline**: Цепочка обработки запроса: ingest → Chroma-индекс → retrieval → LLM-генерация ответа.
- **Ingest**: Процесс загрузки и индексирования документов из папки `data/` в векторный индекс Chroma.
- **Learning_Cycle**: Учебный цикл продукта: ответ → тьютор → квиз → SRS → план.
- **Smart_Router**: Скрипт `scripts/workflow.py` — умный роутер командного конвейера разработки.
- **Local_LLM**: Режим работы с локальной языковой моделью через Ollama (без интернета).
- **Cloud_LLM**: Режим работы с облачными OpenAI-совместимыми провайдерами.
- **Concept_Graduation**: Механика перевода концепта в статус `graduated` после 7+ дней на transfer-уровне.
- **Course_Workspace**: Режим активации папки как отдельного курса с изолированным прогрессом.
- **SRS**: Spaced Repetition System — алгоритм интервального повторения (SM-2).

---

## Requirements

### Requirement 1: Скрипт выступления на академической защите

**User Story:** Как студент, защищающий проектную работу, я хочу иметь структурированный скрипт выступления на 3 минуты, чтобы уверенно провести защиту перед академической комиссией.

#### Acceptance Criteria

1. THE Defense_Script SHALL быть создан по пути `doc/defense_presenter_script.md`.
2. THE Defense_Script SHALL содержать таймкоды для каждого раздела, суммарно покрывающие ровно 3 минуты (0:00–3:00).
3. THE Defense_Script SHALL включать раздел «Постановка задачи» (0:00–0:30), описывающий учебную проблему, которую решает проект.
4. THE Defense_Script SHALL включать раздел «Архитектурное решение» (0:30–1:15), описывающий стек и ключевые технические решения.
5. THE Defense_Script SHALL включать раздел «Демонстрация ключевых функций» (1:15–2:15), охватывающий Learning_Cycle, Concept_Graduation и Course_Workspace.
6. THE Defense_Script SHALL включать раздел «Процесс разработки» (2:15–2:45), описывающий командный конвейер и Smart_Router.
7. THE Defense_Script SHALL включать раздел «Итоги и дальнейшее развитие» (2:45–3:00).
8. WHEN Defense_Script создаётся, THE Defense_Script SHALL содержать ключевые фразы для каждого раздела, выделенные как 🎯 **Ключевая фраза**.
9. THE Defense_Script SHALL содержать таблицу страховочных ответов на типичные вопросы академической комиссии (минимум 5 вопросов).
10. IF Defense_Script содержит ссылки на артефакты проекта, THEN THE Defense_Script SHALL ссылаться только на реально существующие файлы в репозитории.
11. THE Defense_Script SHALL быть написан на русском языке.
12. THE Defense_Script SHALL отличаться от `doc/presenter_script.md` по структуре и акцентам: фокус на академических критериях (постановка задачи, обоснование решений, результаты), а не на конкурсном питче.

---

### Requirement 2: Слайд — Обзор продукта

**User Story:** Как член академической комиссии, я хочу видеть краткий обзор продукта на первом слайде, чтобы сразу понять что это, для кого и какую проблему решает.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать слайд «Обзор продукта» как первый содержательный слайд.
2. THE Defense_Presentation SHALL включать в слайд обзора: название продукта, целевую аудиторию, формулировку решаемой проблемы и ключевые отличия от аналогов.
3. WHEN слайд обзора создаётся, THE Defense_Presentation SHALL указывать конкретные инструменты, которые заменяет hometutor (ChatGPT для вопросов, Anki для карточек, Obsidian для заметок).

---

### Requirement 3: Слайд — Архитектура и стек технологий

**User Story:** Как технический рецензент, я хочу видеть архитектурный слайд, чтобы оценить обоснованность технических решений.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать слайд «Архитектура и стек технологий».
2. THE Defense_Presentation SHALL перечислять компоненты стека: FastAPI (порт 8000), Streamlit UI (порт 8501), CLI, Telegram-бот, Chroma, llama-index, SQLite.
3. THE Defense_Presentation SHALL описывать слои архитектуры: интерфейсный (UI/CLI/Telegram), API (FastAPI), сервисный (query_service, tutor_orchestrator), persistence (SQLite + Chroma).
4. THE Defense_Presentation SHALL указывать принцип local-first как архитектурный инвариант.
5. WHEN слайд архитектуры создаётся, THE Defense_Presentation SHALL содержать текстовую ASCII-схему или Mermaid-диаграмму компонентов.

---

### Requirement 4: Слайды — Скриншоты основных режимов

**User Story:** Как член комиссии, я хочу видеть реальные скриншоты продукта, чтобы убедиться что функциональность реализована, а не задекларирована.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать от 2 до 3 слайдов со скриншотами основных режимов.
2. WHEN слайды со скриншотами создаются, THE Defense_Presentation SHALL ссылаться на реальные файлы из `doc/screenshots/final/`.
3. THE Defense_Presentation SHALL включать скриншот режима «Быстрый ответ с источниками» (scenario_01).
4. THE Defense_Presentation SHALL включать скриншот режима «Tutor + Quiz» (scenario_03 или scenario_04).
5. THE Defense_Presentation SHALL включать скриншот режима «Прогресс и слабые места» (scenario_07) или «Персональный план» (scenario_09).
6. WHEN скриншот включается в слайд, THE Defense_Presentation SHALL содержать подпись, объясняющую что именно показано на кадре.

---

### Requirement 5: Слайд — Схема RAG и Ingest

**User Story:** Как технический рецензент, я хочу видеть понятную схему того, как работает RAG и ingest в проекте, чтобы оценить глубину понимания технологии.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать слайд «Как работает RAG и Ingest».
2. THE Defense_Presentation SHALL включать в слайд пошаговую схему RAG_Pipeline: загрузка документов → чанкинг → эмбеддинги → Chroma-индекс → retrieval → LLM-генерация → ответ с источниками.
3. THE Defense_Presentation SHALL включать в слайд описание Ingest-процесса: сканирование `data/`, парсинг форматов (PDF, MD, TXT), создание/обновление индекса.
4. WHEN слайд RAG создаётся, THE Defense_Presentation SHALL содержать текстовую схему (ASCII или Mermaid) потока данных.
5. THE Defense_Presentation SHALL указывать роль `app/provider.py` как единой точки подключения LLM и embeddings.

---

### Requirement 6: Слайд — Сравнение режимов Local LLM vs Cloud LLM

**User Story:** Как пользователь, рассматривающий продукт, я хочу видеть сравнение режимов работы с локальной и облачной LLM, чтобы выбрать подходящий вариант.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать слайд «Local LLM vs Cloud LLM».
2. THE Defense_Presentation SHALL включать таблицу сравнения с колонками: критерий, Local_LLM (Ollama), Cloud_LLM (OpenAI-совместимые).
3. THE Defense_Presentation SHALL охватывать в таблице минимум 5 критериев: приватность данных, стоимость, качество ответов, скорость, требования к железу.
4. THE Defense_Presentation SHALL указывать конкретные значения: стоимость Cloud_LLM ~$1–5/мес при ежедневном использовании, стоимость Local_LLM — 0 ₽.
5. THE Defense_Presentation SHALL указывать что переключение между режимами осуществляется через `.env` без изменения кода.

---

### Requirement 7: Слайд — Процесс разработки

**User Story:** Как академический рецензент, я хочу видеть информацию о процессе разработки продукта, чтобы оценить зрелость инженерной культуры команды.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать слайд «Процесс разработки».
2. THE Defense_Presentation SHALL описывать командный конвейер: PO → Analyst → Architect → Designer → Developer → Tester.
3. THE Defense_Presentation SHALL упоминать Smart_Router (`scripts/workflow.py`) как инструмент автоматизации конвейера.
4. THE Defense_Presentation SHALL указывать количество закрытых итераций (14+) как показатель зрелости процесса.
5. THE Defense_Presentation SHALL описывать режим авто-цикла `--loop` Smart_Router'а, который ведёт пакет от `proposed` до `closed`.
6. THE Defense_Presentation SHALL упоминать использование AI-агентов (Cursor AI, Claude Code) в конвейере разработки.

---

### Requirement 8: Слайд — Идеи развития Smart Router

**User Story:** Как член комиссии, оценивающий перспективы проекта, я хочу видеть конкретные идеи дальнейшего развития, чтобы оценить понимание команды направлений улучшения.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать слайд «Идеи развития: Smart Router».
2. THE Defense_Presentation SHALL описывать идею SDK trigger: автозапуск агента из терминала через Cursor SDK.
3. THE Defense_Presentation SHALL описывать идею замены polling на event-driven watching (inotify/watchdog вместо `time.sleep`).
4. THE Defense_Presentation SHALL для каждой идеи указывать: текущее состояние, предлагаемое улучшение и ожидаемый эффект.
5. THE Defense_Presentation SHALL содержать минимум 2 идеи развития роутера из `doc/team_workflow/workflow_router.md`.

---

### Requirement 9: Слайд — Ссылки на связанные документы

**User Story:** Как рецензент, я хочу видеть ссылки на связанные документы проекта, чтобы при необходимости углубиться в детали.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL содержать финальный слайд «Связанные документы».
2. THE Defense_Presentation SHALL включать ссылки на: `doc/user_guide.md`, `doc/quickstart_demo.md`, `doc/personalized_learner_model.md`, `doc/scenarios/README.md`, `doc/screenshots/README.md`, `doc/team_workflow/process.md`, `doc/team_workflow/workflow_router.md`.
3. THE Defense_Presentation SHALL для каждой ссылки содержать краткое описание (1 строка) что находится в документе.

---

### Requirement 10: Структура и оформление Defense_Presentation

**User Story:** Как автор документа, я хочу чтобы презентация имела единообразную структуру, чтобы её можно было легко конвертировать в слайды или использовать как standalone-документ.

#### Acceptance Criteria

1. THE Defense_Presentation SHALL быть создан по пути `doc/defense_presentation.md`.
2. THE Defense_Presentation SHALL использовать заголовки второго уровня (`## Слайд N — Название`) для каждого слайда.
3. THE Defense_Presentation SHALL содержать в начале оглавление со ссылками на все слайды.
4. THE Defense_Presentation SHALL содержать в начале метаданные: название проекта, дата, тип мероприятия («Академическая защита проектной работы»).
5. THE Defense_Presentation SHALL быть написан на русском языке.
6. THE Defense_Presentation SHALL содержать минимум 8 слайдов: обзор, архитектура, 2–3 скриншота, RAG/ingest, сравнение LLM, процесс разработки, идеи развития, ссылки.
7. IF слайд содержит схему или диаграмму, THEN THE Defense_Presentation SHALL оформлять её в блоке кода с указанием типа (`mermaid` или `text`).
