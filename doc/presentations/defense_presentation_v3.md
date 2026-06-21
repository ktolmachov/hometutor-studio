# ИИ-тьютор с RAG: персонализированное обучение на собственных документах

> **Проект:** home-rag_v2  
> **Дата защиты:** май 2026  
> **Формат:** 12 слайдов  
> **Версия:** 3.0 — Издание для проектной защиты

---

## Слайд 1 — Проблема и решение

### Проблема

У вас есть **папка с материалами**: лекции, статьи, заметки.

| Что хочется | Что происходит сейчас |
|---|---|
| Быстро найти ответ по материалам | ChatGPT не знает ваших документов |
| Разобраться в теме | Поиск по файлам даёт фрагменты без контекста |
| Запомнить надолго | Ручные Anki-карточки — долго и скучно |
| Видеть прогресс | Непонятно, что уже освоено, а что нет |

**Результат:** переключение между 4–5 инструментами, потеря контекста и мотивации.

---

### Решение: ИИ-тьютор с RAG

**Один инструмент. Полный учебный цикл. Local-first.**

```
📁 Загрузили документы (PDF, MD, DOCX, TXT)
        ↓
🔍 RAG-поиск → ответ с кликабельными источниками
        ↓
👨‍🏫 Тьютор → разбор темы через диалог
        ↓
📝 Квиз → автоматическая проверка понимания
        ↓
🗂️ Карточки → интервальное повторение (SM-2)
        ↓
📊 Mastery tracking → прогресс по концептам
        ↓
🧠 Умный маршрутизатор → «следующий лучший шаг»
        ↓
📅 Недельный план → адаптивное расписание
```

**Принцип:** индекс, прогресс и учебное состояние — на вашей машине. Полный offline при локальных LLM.

---

## Слайд 2 — Соответствие требованиям к проекту

### ✅ Чеклист

| Требование | Статус | Реализация |
|---|---|---|
| **Frontend: 3+ экрана** | ✅ 5 экранов | Q&A, Тьютор, Карточки, Дашборд, Администрирование |
| **Адаптивный дизайн** | ✅ | Streamlit responsive layout + sidebar |
| **Интерактивные элементы** | ✅ | Формы, кнопки, прогресс-бары, табы |
| **Обработка загрузки/ошибок** | ✅ | Spinner, guardrails, error messages |
| **БД: 3+ связанные таблицы** | ✅ 10+ таблиц | flashcard_decks, flashcards, spaced_repetition, quiz_mastery, quiz_results, sessions, app_kv, graph_snapshot и др. |
| **API с CRUD** | ✅ | FastAPI, 90+ endpoints |
| **Аутентификация** | ✅ | Персистентный session_id для UI; `X-API-Key` (`HOME_RAG_API_KEY`) для защищённых REST endpoints |
| **Валидация данных** | ✅ | Pydantic + guardrails.py |
| **Интеграция внешних API** | ✅ | OpenAI-compatible API (Ollama / облако) |
| **Файловое хранилище** | ✅ | Загрузка и индексация документов |
| **Поиск и фильтрация** | ✅ | Гибридный поиск: векторный + ключевые слова |
| **AI-агенты на всех этапах** | ✅ | Планирование → разработка → тесты → деплой |
| **Git с историей коммитов** | ✅ | 14+ итераций с DoD-чеклистом |
| **Документация** | ✅ | README, API reference, user guide, quickstart |

### Дополнительные функции (выбраны 3 из 7)

- ✅ **Интеграция с внешними API** — LLM-провайдеры (Ollama, OpenRouter, OpenAI)
- ✅ **Файловое хранилище** — загрузка документов через UI и API
- ✅ **Поиск и фильтрация** — гибридный RAG-поиск с фильтрацией по курсу/источнику

---

## Слайд 3 — Архитектура и стек технологий

### Четыре слоя системы

```
┌─────────────────────────────────────────────────────┐
│  🖥️ ИНТЕРФЕЙСНЫЙ СЛОЙ                              │
│  Streamlit :8501 · CLI · Telegram-бот               │
├─────────────────────────────────────────────────────┤
│  🚀 API-СЛОЙ — FastAPI :8000                        │
│  /ask · /flashcards · /quiz · /dashboard · /admin   │
├─────────────────────────────────────────────────────┤
│  ⚙️ СЕРВИСНЫЙ СЛОЙ                                 │
│  QueryService · TutorOrchestrator · KnowledgeGraph  │
│  FlashcardService · SmartStudyRouter · LearnerModel │
├─────────────────────────────────────────────────────┤
│  💾 СЛОЙ ДАННЫХ                                     │
│  SQLite (user_state.db) · ChromaDB (векторы)        │
│  provider.py (LLM/Embeddings) · ML-модели           │
└─────────────────────────────────────────────────────┘
```

### Стек технологий

| Уровень | Технология | Роль |
|---|---|---|
| **Frontend** | Streamlit (Python) | Веб-интерфейс, 5 страниц, responsive |
| **Backend** | FastAPI | REST API, 20+ endpoints, async |
| **БД (реляционная)** | SQLite | Прогресс, карточки, сессии |
| **БД (векторная)** | ChromaDB | Эмбеддинги документов |
| **LLM / Embeddings** | Ollama · OpenAI-compatible | Ответы, туториал, квизы |
| **ML** | scikit-learn · XGBoost | Кривая забывания, персонализация |
| **Индексация** | LlamaIndex · LangChain | Парсинг, чанкинг, граф концептов |
| **Валидация** | Pydantic v2 | Схемы запросов/ответов |
| **Тесты** | pytest · playwright | Unit, integration, e2e |

### Архитектурные принципы

1. **Local-first** — все данные на машине пользователя; облако опционально
2. **provider.py** — единая точка LLM/Embeddings; смена провайдера через `.env`
3. **QueryContext** — типизированный pipeline: каждый шаг принимает и возвращает контекст
4. **guardrails.py** — централизованная валидация на всех точках входа
5. **Опциональные переключатели** — ML/LLM-уровни включаются независимо

---

## Слайд 4 — Frontend: 5 экранов, UX

### Экраны приложения

#### Экран 1: Q&A — вопрос-ответ с источниками

```
┌─────────────────────────────────────────────────────┐
│  💬 Задайте вопрос по вашим материалам              │
│  [________________________________________________] │
│  [Спросить]                                         │
│                                                     │
│  📚 Ответ (уверенность поиска: 87%)                │
│  «Retrieval pipeline состоит из 5 шагов...»         │
│                                                     │
│  📎 Источники:                                      │
│  · lecture_03.pdf · chapter_2.md · notes.txt        │
│                                                     │
│  [👨‍🏫 Учить тему 5 минут] [📝 Создать квиз]        │
└─────────────────────────────────────────────────────┘
```

**Что реализовано:** RAG-ответ → кликабельные источники → призыв к учебному действию  
**Состояния:** loading spinner, no-results, low-confidence warning, error fallback

#### Экран 2: Тьютор — сократический диалог

- Поэтапный разбор темы через серию вопросов
- Контекст передаётся из Q&A — нет разрыва
- История сессии сохраняется; можно продолжить

#### Экран 3: Карточки — интервальное повторение

- Автоматически созданные из квизов и ответов тьютора
- Алгоритм SM-2: расчёт следующего повторения
- Кнопки оценки: Легко / Хорошо / Трудно / Снова
- Фильтр по курсу / теме

#### Экран 4: Дашборд — прогресс и mastery

- Mastery по концептам: узнавание → воспроизведение → применение → graduation
- Динамика за 30 дней
- Слабые места: какие темы требуют повторения
- Серия дней (streak)

#### Экран 5: Администрирование

- Загрузка документов (UI upload + drag-and-drop)
- Запуск переиндексации
- Управление курсами (активация папки как курса)
- Статистика индекса

### UI/UX решения

| Паттерн | Реализация |
|---|---|
| **Состояния загрузки** | `st.spinner` на все LLM-вызовы |
| **Обработка ошибок** | Try/except + friendly error messages |
| **Адаптивность** | Sidebar collapse на узких экранах |
| **Онбординг** | Quickstart подсказки при пустом индексе |
| **Навигация** | Sidebar с иконками + хлебные крошки |

---

## Слайд 5 — Backend: API, БД, валидация

### База данных: 10+ реальных таблиц (SQLite)

Ниже — ключевые таблицы из `app/user_state_db.py` и `app/session_store.py`.

```sql
-- Колоды карточек (группировка)
CREATE TABLE flashcard_decks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    source_type TEXT    NOT NULL DEFAULT 'document',
    source_id   TEXT,
    card_count  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

-- Карточки (SM-2 state встроен)
CREATE TABLE flashcards (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id       INTEGER NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    front         TEXT    NOT NULL,
    back          TEXT    NOT NULL,
    tags          TEXT,
    easiness      REAL    NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    next_review   TEXT,
    last_review   TEXT,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

-- SM-2 состояние на концепт (для quiz/SRS flow)
CREATE TABLE spaced_repetition (
    concept       TEXT PRIMARY KEY,
    easiness      REAL    NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 1,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    next_review   TEXT,
    last_review   TEXT
);

-- Уровень освоения концепта (mastery tracking)
CREATE TABLE quiz_mastery (
    concept        TEXT PRIMARY KEY,
    current_level  TEXT NOT NULL DEFAULT 'recognition',  -- recognition/recall/transfer
    success_streak INTEGER NOT NULL DEFAULT 0,
    last_updated   TEXT NOT NULL
);

-- Результаты квизов (история)
CREATE TABLE quiz_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    concept    TEXT,
    level      TEXT,
    score      REAL NOT NULL,
    timestamp  TEXT NOT NULL,
    attempt_number INTEGER DEFAULT 1
);

-- История диалоговых сессий (session_store.py)
CREATE TABLE sessions (
    session_id       TEXT PRIMARY KEY,
    messages         TEXT NOT NULL,  -- JSON-массив сообщений
    last_updated     TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    session_metadata TEXT NOT NULL DEFAULT '{}'
);

-- Key-value хранилище (адаптивные планы, конфиг)
CREATE TABLE app_kv (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Граф концептов:** `graph_snapshot` (1 строка, JSON-blob) + вся логика в `app/knowledge_graph.py`.
**Связь карточки ↔ концепт:** через текстовый ключ `concept`, а не нумерованный FK — осознанное упрощение для local-first MVP.
**Аутентификация:** нет отдельной таблицы `users`; изоляция пользователя через `session_id` (one person — one machine).

### REST API: ключевые endpoints (итого 90+)

| Method | Endpoint | Операция |
|---|---|---|
| POST | `/ask` | Q&A запрос (RAG) |
| GET | `/flashcards/cards` | Список карточек к повторению |
| POST | `/flashcards/cards/{card_id}/review` | Оценить карточку (CRUD: Update) |
| DELETE | `/flashcards/cards/{card_id}` | Удалить карточку (CRUD: Delete) |
| DELETE | `/flashcards/decks/{deck_id}` | Удалить колоду (CRUD: Delete) |
| POST | `/quiz/generate` | Сгенерировать квиз по теме |
| POST | `/quiz/submit` | Отправить ответы квиза |
| GET | `/dashboard/mastery` | Статистика прогресса |
| GET | `/dashboard/weak-spots` | Слабые места |
| POST | `/admin/reindex` | Переиндексация документов |
| POST | `/admin/upload` | Загрузка файлов |
| GET | `/router/next-step` | Умный маршрутизатор |
| GET | `/plan/weekly` | Недельный план |

### Валидация и безопасность

```python
# Pydantic-модели для всех запросов
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    mode: Literal["qa", "overview", "synthesis"] = "qa"
    scope: Optional[str] = None  # фильтр по курсу

# guardrails.py — централизованная защита
def validate_input(text: str) -> ValidationResult:
    # Проверка длины, спецсимволов, prompt injection
    # На всех точках входа: API, UI, Telegram
```

**Аутентификация:** персистентный `session_id` в SQLite для UI (Streamlit st.session_state + store); API-key header (`X-API-Key`) для REST-клиентов; Telegram — `chat_id` используется как `session_id` (single-user; ALLOWED_CHAT_IDS — в roadmap).

---

## Слайд 6 — Ключевая функция: RAG-pipeline

> **RAG (Retrieval-Augmented Generation)** — языковая модель отвечает строго по вашим документам, а не из общих знаний.

### 5-ступенчатый pipeline

```
❓ Вопрос пользователя
    ↓
1️⃣ КЛАССИФИКАЦИЯ
   Тип запроса: qa / overview / synthesis / study-plan
    ↓
2️⃣ ПЕРЕФОРМУЛИРОВКА
   Улучшение запроса для поиска; подвопросы для сложных тем
    ↓
3️⃣ ПОИСК (гибридный)
   Векторный поиск (семантика) + ключевые слова (точность)
   Двухуровневый: документы → фрагменты
    ↓
4️⃣ ПЕРЕРАНЖИРОВАНИЕ
   Cross-encoder: точная оценка релевантности
   Self-check: если контекст слабый — retry с новым запросом
    ↓
5️⃣ ГЕНЕРАЦИЯ
   LLM строго по найденным фрагментам
   Ответ + кликабельные источники + confidence
    ↓
💬 Ответ с источниками
```

### Уникальные решения

| Фича | Ценность |
|---|---|
| **Двухуровневая индексация** | Документы + фрагменты → отвечает и на «дай обзор», и на точечные вопросы |
| **Граф концептов** | Связи между темами → правильный порядок изучения |
| **Self-Correction Loop** | Низкая уверенность поиска → автоматический retry с переформулировкой |
| **Частичная переиндексация** | Только изменённые файлы → быстро при больших корпусах |
| **Переключение Local ↔ Cloud** | `.env` — код не меняется |

### Eval-run: сравнение режимов поиска (demo_data, N=15 вопросов)

Прогон: `scripts/run_defense_eval.py` → `eval/eval_results_2026-05-20.json` (retrieval-only, run_id=`eval-2026-05-20`).

| Режим | Источник в top-3 | Avg latency (retrieve) |
|---|---|---|
| vector_only | 12/15 (80%) | 0.75 с |
| **hybrid** | **13/15 (87%)** | **0.57 с** |
| bm25_only (keyword) | 13/15 (87%) | < 0.1 с* |

\* bm25_only — после прогрева BM25-кэша.  
⏳ **Faithfulness (LLM-as-judge):** методика есть (`eval/` директория), числа — следующий запланированный run.

Вывод: гибрид даёт +7 п.п. к hit-rate vs только векторный при сопоставимой латентности на demo-корпусе.

---

## Слайд 7 — Учебный AI-цикл

### Полный цикл: от вопроса до закрепления

#### Шаг 1: Q&A → Тьютор (5 минут на тему)

```
Студент: «Как работает self-attention?»
          ↓
RAG-ответ с источниками (уверенность поиска: 91%)
          ↓
[Кнопка: Учить тему 5 минут]
          ↓
Тьютор: «Хорошо! Начнём с базы. Что такое attention в NLP — можете объяснить своими словами?»
Студент: «Это когда модель смотрит на все слова сразу...»
Тьютор: «Точно! Теперь объясните, почему это называется self...»
```

#### Шаг 2: Квиз — немедленная проверка

```
❓ Что из перечисленного НЕ является компонентом self-attention?
   ○ Query matrix  ○ Key matrix  ○ Value matrix  ● Dropout layer

✅ Верно! Dropout — регуляризация, не часть механизма attention.
   → Создана карточка: «Компоненты self-attention»
   → Mastery score для концепта: +0.15
```

#### Шаг 3: Карточки — интервальное повторение

```
📅 Завтра: 3 карточки по self-attention
📅 Через 4 дня: повторение при оценке «Хорошо»
📅 Через 9 дней: при стабильном «Легко»

После 3 успешных повторений: концепт переходит в «применение»
После 7 дней стабильного «применения»: graduation — тема освоена
```

#### Шаг 4: Умный маршрутизатор

```
💡 Следующий лучший шаг: повторить 4 карточки по «Multi-head attention»
   Почему: 2 дня до просрочки по прогнозу кривой забывания
   После: рекомендую тему «Positional Encoding» — логичный следующий шаг

[Повторить сейчас] [Показать план] [Отложить]
```

### Алгоритм SM-2 (Spaced Repetition)

Реализация: [`app/spaced_repetition.py`](app/spaced_repetition.py) — стандартный SM-2 с quality-шкалой 0..5.

```python
def apply_sm2(
    easiness: float,      # текущий ease factor (≥ 1.3)
    interval_days: int,   # текущий интервал
    repetitions: int,     # сколько раз карточка пройдена подряд
    quality: int,         # 0..5 (< 3 = ошибка, сброс)
) -> tuple[float, int, int]:
    """Возвращает (new_easiness, new_interval_days, new_repetitions)."""
    q = max(0, min(5, int(quality)))
    if q < 3:                         # Hard / Again — сброс
        new_r, new_i = 0, 1
    else:                             # Good / Easy — наращиваем
        new_r = repetitions + 1
        new_i = 1 if new_r == 1 else (6 if new_r == 2
                                       else max(1, round(interval_days * easiness)))
    # Стандартная формула корректировки ease factor
    new_e = max(1.3, easiness + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    return new_e, new_i, new_r
```

**Шкала quality:** 5 = без затруднений, 4 = Easy, 3 = Good, 2 = Hard, 1/0 = Again (сброс).  
**UI:** кнопки «Легко / Хорошо / Трудно / Снова» переводятся в 5/4/2/1 перед вызовом.

---

## Слайд 8 — Использование AI-агентов в разработке

### Этап 1: Планирование и дизайн

| Задача | AI-инструмент | Результат |
|---|---|---|
| Генерация идеи и анализ конкурентов | ChatGPT / Claude | Матрица конкурентов, gap-анализ |
| User Stories и ТЗ | Claude в Cursor | 14 user stories с acceptance criteria |
| UI-концепции | Text-to-UI + Cursor | Wireframes всех 5 экранов |
| Архитектурные решения | Claude (ADR) | 12 Architecture Decision Records |

**Пример промпта для User Stories:**
```
Goal: Создать User Story для функции Q&A по документам
Context: Студент хочет быстро находить ответы в своих лекциях
Format: As a [role], I want [feature], so that [value]
DoD: Acceptance criteria с тест-кейсами
```

### Этап 2: Разработка кода

| Задача | AI-агент | Конкретный пример |
|---|---|---|
| Инициализация проекта | Cursor Agent | Структура FastAPI + Streamlit + pytest |
| RAG-pipeline | Claude Code | `query_service.py` — 5-шаговый pipeline |
| SM-2 алгоритм | GitHub Copilot | `flashcard_service.py` — расчёт интервалов |
| Pydantic-схемы | Cursor | `api_models.py` — все request/response модели |
| Граф концептов | Claude | `knowledge_graph.py` — построение и обход |

### Этап 3: Backend и инфраструктура

| Задача | AI-агент | Артефакт |
|---|---|---|
| Проектирование БД | Claude | ERD + SQL-схема 6 таблиц |
| API endpoints | Cursor Agent | 20+ FastAPI routers |
| Docker | Claude | `docker-compose.yml` (1 сервис, ChromaDB in-process) |
| pytest-тесты | Cursor | 1800+ тест-функций, 276 тест-файлов |

**Пример: генерация тестов**
```python
# Промпт → Cursor Agent → готовый тест
"""
Напиши pytest-тест для endpoint POST /ask:
- Мокируй RAG pipeline
- Проверь: status 200, наличие sources, confidence/search confidence в [0,1]
- Edge case: пустой вопрос → 422
"""
```

### Этап 4: Отладка и оптимизация

| Задача | AI-инструмент | Результат |
|---|---|---|
| Анализ ошибок | Claude в Cursor | Диагностика по traceback за 30 сек |
| Оптимизация RAG | Claude | Self-Correction Loop — retry + «источников недостаточно» при низком confidence |
| Профилирование | Cursor Agent | Bottleneck в embedding — кеш запросов |
| Аудит безопасности | Claude | Найден prompt injection риск → guardrails |

### Автоматизированный workflow (ноу-хау проекта)

```powershell
# Одна команда запускает весь конвейер разработки
python scripts/workflow.py --loop --skip-review --watch-contract \
    --trigger-cmd "npx tsx scripts/cursor_agent_trigger.ts"
```

**Что происходит автоматически:**

```
📋 Plan-next → контракт в backlog_registry.yaml
        ↓
🎯 Complexity check → оркестрация или прямое выполнение
        ↓
🤖 Cursor SDK → Agent.prompt(task)
        ↓
✅ DoD check → pytest + lint → закрытие итерации
        ↓
🔄 Re-route → следующий пакет
```

**Результат:** 14+ итераций с полным DoD, автоматизация 95% шагов разработки.

---

## Слайд 9 — Дополнительные функции

### 1. Интеграция с внешними API (LLM-провайдеры)

```bash
# Переключение Local ↔ Cloud — только .env, без изменения кода

# Local (Ollama, полный offline)
OPENAI_API_BASE=http://127.0.0.1:11434/v1
LLM_MODEL=qwen2.5:7b-instruct
EMBED_MODEL=nomic-embed-text

# Cloud (OpenRouter, максимальное качество)  
OPENAI_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-3.5-sonnet
```

**Поддерживаемые провайдеры:** Ollama, OpenAI, Anthropic (через OpenRouter), любой OpenAI-совместимый API.

### 2. Файловое хранилище — загрузка документов

**Через UI:**
- Drag-and-drop загрузка (PDF, MD, DOCX, TXT)
- Прогресс-бар индексации
- Превью извлечённых концептов

**Через API:**
```http
POST /admin/upload
Content-Type: multipart/form-data

file: [binary]
course_scope: "ml_course"
```

**Через CLI:**
```bash
python -m app.cli index data/ml_course/
```

### 3. Поиск и фильтрация данных

**Гибридный поиск:**
```python
# Векторный поиск (семантика) + BM25 (ключевые слова)
# Результаты объединяются через Reciprocal Rank Fusion
results = hybrid_search(
    query="что такое attention",
    mode="hybrid",          # vector / keyword / hybrid
    scope="ml_course",      # фильтр по курсу
    top_k=5,
    rerank=True
)
```

**Фильтрация в UI:**
- По курсу / папке
- По дате добавления
- По типу документа
- По уровню mastery концепта

### 4. Telegram-бот

```
/ask Как работает backpropagation?
→ RAG-ответ с источниками

/quiz retrieval pipeline
→ Квиз из 3 вопросов

/review
→ Карточки на сегодня (5 штук)

/progress
→ Mastery сводка за неделю
```

---

## Слайд 10 — Деплой, CI/CD и история разработки

### Git-история: 14+ итераций с полным DoD

```
git log --oneline

e29-close: Smart Study Router AI Vision — L1+L2 ready
e28-close: Knowledge Graph — prerequisite chains
e27-close: Adaptive Plan — weekly planner baseline
e26-close: Course Workspace — isolated progress
e25-close: Mastery Graduation — concept lifecycle
e24-close: Concept Graph — indexing + traversal
e23-close: Self-Correction Loop — retry on low confidence
e22-close: Hybrid Search — BM25 + vector RRF fusion
...
```

**Каждая итерация:** контракт → реализация → `pytest` → DoD-чеклист → закрытие  
**Автоматизация:** `python scripts/workflow.py` — 95% шагов без ручного вмешательства

---

### Docker: контейнеризация

```yaml
# docker-compose.yml (реальный файл)
services:
  home-rag:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:8000:8000"   # FastAPI  → http://127.0.0.1:8000/docs
      - "127.0.0.1:8501:8501"   # Streamlit → http://127.0.0.1:8501
    volumes:
      - ./data:/app/data          # PDF/MD/DOCX + user_state.db
      - ./chroma_db:/app/chroma_db  # векторный индекс (persistent)
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"  # доступ к Ollama на хосте
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

> **Архитектурная заметка:** ChromaDB работает как in-process `PersistentClient` внутри контейнера `home-rag` — отдельного сервиса chroma нет. Данные персистентны через volume `./chroma_db`. Порты привязаны к `127.0.0.1` для безопасности локального деплоя.

---

### Варианты деплоя

| Вариант | Streamlit | FastAPI | Ollama | Цена | Статус |
|---|---|---|---|---|---|
| **Local (localhost)** | ✅ | ✅ | ✅ full offline | 0 ₽ | ✅ Рабочий |
| **Docker Compose (любая машина)** | ✅ | ✅ | ✅ | 0 ₽ | ✅ Рабочий |
| **Hugging Face Spaces** | ✅ нативно | ⚠️ demo/Docker Space | ❌ → cloud LLM | Бесплатно | 🟡 Demo target |
| **RUVDS VPS** (Россия) | ✅ через Nginx | ✅ | ⚠️ CPU медленно / GPU тариф | ~600 ₽/мес | 🟡 Primary deploy target |
| **Hetzner CX11** (EU) | ✅ через Nginx | ✅ | ⚠️ CPU-only медленно | €4/мес | 🟡 Alternative VPS |
| **Vercel** | ❌ serverless не держит Streamlit | ⚠️ Stateless API only | ❌ | Бесплатно | ⚠️ Не full stack |

> **Vercel — почему не подходит для полного стека:** текущий Streamlit + локальный индекс + фоновые операции требуют долгоживущего процесса и persistent state. Vercel можно рассматривать только после выделения отдельного stateless REST API.

#### Архитектура онлайн-деплоя (RUVDS / Hetzner)

```
Браузер пользователя
        ↓ HTTPS
   Nginx (SSL termination)
   ├── / → Streamlit :8501  (WebSocket proxy)
   └── /api/ → FastAPI :8000
        ↓
   Docker Compose
   ├── home-rag (FastAPI + Streamlit)
   ├── chroma_db volume (векторный индекс)
   └── .env (LLM_MODEL, HOME_RAG_API_KEY, ...)
```

---

### CI/CD: GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python -m pip install -r requirements.txt
      - run: python -m pip install ruff pytest
      - run: python -m ruff check app tests
      - run: python -m pytest tests/test_api.py tests/test_provider.py -q

  docker-build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v6
        with:
          push: false
          tags: home-rag:ci
```

**Проверяемый результат каждого push в `main`:**

```
GitHub Actions → CI
├── Tests and lint
└── Docker build

SSH deploy на VPS — следующий шаг после настройки VPS_HOST / VPS_SSH_KEY.
```

---

### Итоговая карта деплоя

```
Разработчик → git push main
                    ↓
             GitHub Actions CI
             ├── pytest (unit tests)
             ├── ruff lint
             └── docker build
                    ↓
             VPS deploy target (RUVDS/Hetzner)
             Nginx + Docker Compose + demo data
                    ↓
        публичный URL после настройки домена и секретов
```

---

## Слайд 11 — Конкурентный анализ

### Анализ конкурентов (AI-assisted)

*Анализ выполнен с помощью Claude: запрос → матрица по 10 критериям → gap-анализ → позиционирование*

### Сравнительная таблица

| Критерий | **home-rag** | NotebookLM | Anki | ChatGPT+Files | Obsidian |
|---|---|---|---|---|---|
| Q&A по документам | ✅ RAG + источники | ✅ | ❌ | ✅ | ⚠️ |
| Автоквизы из ответов | ✅ | ❌ | ⚠️ ручные | ❌ | ❌ |
| SM-2 карточки | ✅ авто | ❌ | ✅ лучший | ❌ | ⚠️ |
| Mastery tracking | ✅ 3 уровня | ❌ | ⚠️ базово | ❌ | ❌ |
| AI-тьютор | ✅ | ❌ | ❌ | ⚠️ ручной | ❌ |
| Умный маршрутизатор | ✅ | ❌ | ❌ | ❌ | ❌ |
| Local-first | ✅ полный | ❌ cloud | ✅ | ❌ cloud | ✅ |
| Открытый код | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Стоимость** | **0 ₽ (local)** | Бесплатно | Бесплатно | $20/мес | Бесплатно |

### Уникальное позиционирование

**Только home-rag закрывает полный учебный цикл:**

```
Документы → Q&A → Тьютор → Квиз → Карточки → Mastery → Graduation
                                                    ↑
                                          AI-маршрутизатор
                                          (следующий шаг)
```

**Конкуренты:** сильны в отдельных частях, но требуют 3–5 инструментов для полного цикла.

---

## Слайд 12 — Итоги и дорожная карта

### Что реализовано

| Компонент | Статус | Ключевые метрики |
|---|---|---|
| **RAG-pipeline** | ✅ Production-ready | 5 ступеней, self-correction, hybrid search |
| **Учебный цикл** | ✅ Полный | Q&A → Тьютор → Квиз → SM-2 → Mastery |
| **Умный маршрутизатор** | ✅ Rule-based v2.0 | 7 состояний, объяснимые рекомендации |
| **Smart Study Router (AI Vision L1-L2)** | ✅ | ML forgetting curve + LLM explanations + route simulator |
| **Graф концептов** | ✅ | Prerequisite-цепочки, graduation |
| **5 функциональных экранов UI** | ✅ | Q&A (табы), Тьютор, Карточки, Прогресс (multipage), Админ |
| **Mission Control home** | ✅ | SSR-guided 7 tile hub + breadcrumbs |
| **FastAPI + 90+ endpoints** | ✅ | CRUD, валидация, аутентификация |
| **10+ таблиц SQLite** | ✅ | flashcard_decks, flashcards, spaced_repetition, quiz_mastery, sessions, app_kv и др. |
| **ADR-021 Smart RAG** | ✅ | 6-phase routing contract, profile-aware retrieval |
| **Docker** | ✅ | docker-compose, 1 сервис (ChromaDB — in-process PersistentClient) |
| **AI-assisted разработка** | ✅ | 14+ итераций, 1800+ тестов, автопилот workflow |
| **Документация** | ✅ | README, API ref, user guide, quickstart |

### Измерено сегодня (воспроизводимые числа)

| Метрика | Значение | Источник |
|---|---|---|
| Retrieval recall@3 — hybrid | **87 %** (13/15) | `eval/eval_results_2026-05-20.json` |
| Retrieval recall@3 — vector_only | 80 % (12/15) | то же |
| Avg latency retrieve (hybrid) | **0.57 с** | то же |
| User Stories закрыто | **87 / 87** (100%) | `user_stories_index.json` |
| CJM моменты истины покрыты | **13 / 13** (100%) | `cjm.md` |
| Волн завершено | **67** | `backlog_registry.yaml` |
| Пакетов закрыто | **205+** | `backlog_registry.yaml` |
| Тест-функций pytest | **1 824** | `grep -c "^def test_"` |
| FastAPI endpoints | **90+** | `app/routers/` |
| Итераций с DoD | **14+** | git log |
| SSR AI Vision L1 (ML forgetting curve) | ✅ AUC-ROC ≥ 0.75 | `ssr-ai-vision-wave-1-foundation` |
| SSR AI Vision L2 (LLM explanations) | ✅ p95 latency < 2s | `ssr-ai-vision-wave-2-explainability` |
| ⏳ Faithfulness (LLM-as-judge) | методика готова, run после защиты | `eval/` |
| ⏳ Longitudinal retention rate | данные накапливаются | dashboard |

---

### Следующий уровень: Localhost Balance + Course Delight Loop (Phase 1)

```
🚀 PHASE 1: Balanced LLM Fallback + Папка→Курс под ключ + Golden E2E

Волна 1: Balanced LLM Fallback
  ⚖️ Graceful degradation: local Ollama → cloud OpenRouter → cached responses
  🔄 Automatic retry с fallback при timeout/error
  📊 Transparent cost/latency tradeoff в UI

Волна 2: Папка→Курс под ключ
  📁 Drag-and-drop папку → система автоматически создаёт курс
  🎓 Структура курса из иерархии файлов + граф концептов
  ✅ One-click activation без конфига

Волна 3: Golden E2E (10 минут до graduation)
  🎬 Новый пользователь: загрузил папку → прошёл 5-минутный learning loop → 
     получил карточки → повторил → видит прогресс → graduation
  📈 Метрика: ≥60% новых пользователей доходят до first graduation за сессию

Волна 4: AI Vision L3-L5 (при наличии данных)
  🧠 Graph-aware routing (prerequisite chains)
  🎯 Outcome-based feedback loop (learner steering)
  📚 Longitudinal retention analysis
```

### Главный тезис защиты

> **ИИ-тьютор с RAG — это не ещё один чат-бот.**
>
> Это **персональная система обучения**, которая знает ваши материалы,
> следит за вашим прогрессом и ведёт вас по оптимальному учебному пути —
> от первого вопроса до освоения темы.
>
> **Local-first. Open-source. Полный цикл. AI-powered.**

---

### Использование AI-агентов: сводка по этапам

| Этап | AI-инструмент | Артефакт |
|---|---|---|
| Идея и анализ конкурентов | Claude | Матрица, gap-анализ, позиционирование |
| User Stories | Claude в Cursor | 87 US с acceptance criteria (100% покрытие) |
| Архитектура и ADR | Claude Code | 12 Architecture Decision Records + ADR-021 Smart RAG |
| Проектирование БД | Claude | ERD + SQL-схема (10+ таблиц) |
| Код компонентов | Cursor Agent | RAG pipeline, SM-2, граф, API, SSR AI Vision |
| Smart Study Router | Claude + Cursor | 5-уровневый маршрутизатор с ML + LLM |
| Рефакторинг | Cursor | Guardrails, provider abstraction, god-module splits |
| Тесты | Cursor Agent | 1824 pytest tests, 100% CJM coverage |
| Docker / CI | Claude | docker-compose, GitHub Actions, autonomous control plane |
| Отладка | Claude в Cursor | Prompt injection fix, latency optimization, eval gates |
| Документация | Claude | README, API reference, user guide, roadmap |
| Презентация | Claude | Эта презентация (v3.0) |

---

<sub>📅 Подготовлено для защиты проектной работы · май 2026 · Версия 3.0</sub>
