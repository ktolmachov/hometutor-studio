# Детальный справочник: все возможности

> **Это reference-документ. Если ты здесь впервые — начни с [quickstart.md](quickstart.md) (пошаговый онбординг учебного цикла) и [user_scenarios.md](user_scenarios.md) (сценарии от простого к сложному). Сюда заходи, когда нужна точная деталь.**

Актуализировано по коду на **2026-05-20**.

## Где что искать

| Нужно | Раздел |
|---|---|
| Как индексировать файлы, поддерживаемые форматы, ускорение | [Индексация](#индексация) |
| Публичный demo (HF Spaces), VPS, demo_chroma_db | [Публичный demo и деплой](#публичный-demo-и-деплой) |
| Все способы работы: API / CLI / UI / Telegram | [Основные способы работы](#основные-способы-работы) |
| Объяснение и просмотр конкретного файла | [Explain / Content](#explain--content) |
| Tutor-сессии, квизы, оркестрация, policy clamp | [Sessions, Tutor и Quiz](#sessions-tutor-и-quiz) |
| Темы, synthesis, learning plan, Course Workspace | [Темы, Synthesis и Learning Plan](#темы-synthesis-и-learning-plan) |
| Mastery, adaptive plan, analytics, course progress | [Прогресс и аналитика](#прогресс-и-аналитика) |
| Backup, перенос прогресса, offline sync | [Экспорт и импорт состояния](#экспорт-и-импорт-состояния) |
| Все env-переменные по категориям | [Важные переменные `.env`](#важные-переменные-env) |
| Smoke, regression gates, eval loop | [Тесты и smoke-check](#тесты-и-smoke-check) |
| API не стартует, индекс пустой, Telegram не отвечает и т.п. | [Частые проблемы](#частые-проблемы) |
| SSR «Почему сейчас», LM Studio, JSONL-профили | [SSR / LM Studio и профили](#ssr-lm-studio-profiles) |

## Индексация

Проект читает документы из `data/` и сохраняет индекс в `chroma_db/`.

Поддерживаемые форматы для ingest:

- `.txt`
- `.md`
- `.html`
- `.docx`
- `.pdf`

<a id="us-2-3-non-text-corpus"></a>

### Non-text корпус (US-2.3) и отличие от загрузки в Flashcards

**Что считается «non-text» для постоянной базы знаний:** материалы в `data/`, где рабочий текст для retrieval **нельзя** получить обычным извлечением из файла (типично — скан PDF без текстового слоя, фото или растровые изображения страниц). Обычные `.pdf`/`.docx` с копируемым текстом относятся к обычному ingest выше.

**Пайплайн (phase1, US-2.3):** включите `INGEST_DOCLING_ENABLED=true` и установите зависимость `docling` (см. `requirements.txt`). Тогда растровые форматы (`.png`, `.jpg`, …) из `data/` участвуют в общем reindex; PDF со «слабым» нативным текстом дополнительно обрабатываются через Docling. В метаданных чанков для атрибуции выставляется `source_extraction` (`native_text` | `docling_ocr`).

**Контракт продукта:** цель US-2.3 — те же поискоспособные чанки в **общем** индексе и те же трассируемые источники в ответах, что и для текстовых файлов; разовый side-channel без индекса не используется.

**Граница с US-15.5:** разовая **загрузка файла** в UI Flashcards для генерации карточек (в т.ч. `scope=upload`) **не** добавляет материал в постоянную knowledge base для Q&A и тьютора. US-2.3 — про **постоянный** корпус в `data/` и общий retrieval, а не только про подготовку карточек из временного файла.

Повторная индексация:

```bash
python ingest.py
```

**Ускорение индексации (2026-04-19):** при повторном запуске без `reset=True` система сначала строит манифест и выходит с `run_kind=noop`, если ничего не изменилось. Если изменения есть, извлечённые фрагменты документов (`Document`) кэшируются в `chroma_db/ingestion_extracted_documents.json`, что избавляет от повторного тяжёлого парсинга PDF/DOCX для неизменных файлов.

### Полный сброс и загрузка с нуля

Используй, когда нужно полностью заменить корпус документов или устранить повреждённый индекс.

**Перед запуском:** останови API-сервер и Telegram-бот.

**Один шаг — сброс + переиндексация:**

```bash
python scripts/fresh_start.py --confirm-token DELETE-ALL-LOCAL-HOME-RAG-DATA
```

**Только сброс** (без автоматической переиндексации — положи новые файлы в `data/` и запусти вручную):

```bash
python scripts/fresh_start.py --confirm-token DELETE-ALL-LOCAL-HOME-RAG-DATA --skip-ingest
# ... скопируй новые документы в data/ ...
python ingest.py --reset -y
```

**Проверить, что всё чисто** (без удаления):

```bash
python scripts/delete_all_data.py --verify-only
```

Что удаляется:

| Хранилище | Путь |
|---|---|
| Векторный индекс | `chroma_db/` |
| Метаданные индекса | `index_meta.json`, `index_registry.json` |
| Состояние обучения | `data/user_state.db`, `data/cache/` |
| Граф концептов | `data/concept_graph.json`, `data/graph_generations/` |
| Метрики и история | `logs/metrics_store.jsonl`, `logs/metrics_dashboard.db`, `logs/history.jsonl`, `logs/feedback.jsonl` |
| Логи стоимости и SSR | `logs/cost_logs/`, `logs/ssr_llm_profiles/`, `logs/ssr_feedback/` |
| FAQ-память | `faq_memory.jsonl` |

Исходные документы в `data/` (PDF, DOCX и др.) **не удаляются**.

Через API:

- `POST /reindex`
- `GET /reindex/status`
- `GET /index/stats`
- `GET /index/version`
- `GET /index/diff`

<a id="публичный-demo-и-деплой"></a>

## Публичный demo и деплой

**Local-first остаётся основным сценарием:** ваши файлы в `data/`, индекс в `chroma_db/`, прогресс в `data/user_state.db`. Публичный контур — для демо жюри и проверки «приложение онлайн».

### Demo-корпус и прединдекс

| Путь | Назначение |
|---|---|
| `demo_data/` | Фиксированные учебные markdown (6 файлов), см. [demo_data/README.md](../demo_data/README.md) |
| `demo_chroma_db/` | Предсобранный Chroma (~1 MB), чтобы Space/VPS не индексировали при каждом cold start |
| `scripts/build_demo_chroma.py` | Пересборка индекса из `demo_data/` (нужен `OPENAI_API_KEY` для эмбеддингов) |
| `deploy/hf-spaces/bootstrap_demo_paths.sh` | Копирование `demo_*` → `data/` / `chroma_db/` при первом старте |

### Hugging Face Spaces

- Манифест и секреты: [deploy/hf-spaces/README.md](../deploy/hf-spaces/README.md), шаблон env — [deploy/hf-spaces/.env.spaces.example](../deploy/hf-spaces/.env.spaces.example).
- Режим: **Streamlit demo** + cloud LLM (OpenRouter); Ollama на free tier недоступен.
- `app_file`: `app/ui/main.py` (как в локальном UI).
- Ограничение: это не полный private VPS; REST API в SDK Space не поднимается — для `/ask` нужен Docker Space или VPS.

### VPS (RUVDS / Hetzner)

### Docker Compose на машине разработчика (аналог `run_local_stack.ps1 -SkipPip`)

Корневые файлы: [`docker-compose.yml`](../docker-compose.yml), опционально [`docker-compose.lmstudio.yml`](../docker-compose.lmstudio.yml).

**Тома:**

| Хост | Контейнер | Содержимое |
|------|-----------|------------|
| `./data` | `/app/data` | Исходники, SQLite learner state |
| `./chroma_db` | `/app/chroma_db` | Chroma, BM25 cache, `active_index.json` |
| `./logs` | `/app/logs` | `ssr_llm_profiles`, cost logs |
| `./.env` | `/app/.env` | Конфиг (ro) |

**Порты (привязка к loopback хоста):** `127.0.0.1:8000`, `127.0.0.1:8501`.

**LM Studio / Ollama на хосте:** в контейнере добавлен `extra_hosts: host.docker.internal`. В `.env` укажите `http://host.docker.internal:1234/v1` (см. [deploy/docker/env.docker.example](../deploy/docker/env.docker.example)) **или** подключите overlay с socat-мостом `127.0.0.1:1234` → хост:

```powershell
docker compose -f docker-compose.yml -f docker-compose.lmstudio.yml up --build
```

Перед первым запуском на хосте: `python scripts/bootstrap.py`, затем `docker compose exec hometutor python ingest.py`.

---

1. `docker compose up -d` на сервере.
2. Nginx: [deploy/nginx/hometutor.conf.example](../deploy/nginx/hometutor.conf.example) — `/` → Streamlit :8501, `/api/` → FastAPI :8000.
3. HTTPS: `certbot --nginx`.
4. CI deploy (опционально): GitHub Actions job `deploy` при секретах `VPS_HOST`, `VPS_SSH_KEY` — см. [presentations/defense_deploy_plan.md](presentations/defense_deploy_plan.md).

Проверка после деплоя:

```bash
curl https://<your-domain>/health
curl -X POST https://<your-domain>/api/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <HOME_RAG_API_KEY>" \
  -d '{"question": "Что такое RAG?"}'
```

## Основные способы работы

### 1. FastAPI

Запуск:

```bash
python main.py
```

Главный endpoint:

- `POST /ask`

#### Опциональная защита REST (`HOME_RAG_API_KEY`)

Если в `.env` задан `HOME_RAG_API_KEY` (алиас `API_KEY`), защищённые маршруты (включая `POST /ask`) требуют заголовок:

```http
X-API-Key: <ваш_ключ>
```

Без ключа или с неверным ключом — `401` с `{"detail": "Invalid or missing API key"}`. Публичные проверки без ключа: `GET /health`, `GET /health/deep`, `GET /ui/bootstrap`.

Если `HOME_RAG_API_KEY` **не задан** — dev/demo режим: REST открыт (как раньше). Streamlit при наличии ключа в env передаёт его в API автоматически (`app/ui_client.py`).

Пример с ключом:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"question": "Что такое RAG?"}'
```

Минимальный пример (без ключа в dev):

```json
{
  "question": "Что такое RAG?"
}
```

Tutor-пример:

```json
{
  "question": "Объясни проще, как работает hybrid retrieval",
  "query_mode": "tutor",
  "session_id": "demo-session",
  "quiz_learning_mode": "understand_topic"
}
```

### 2. CLI

Запуск:

```bash
python ask.py
```

Опции:

- `--profile fast|quality`
- `--brief`
- `--log path.jsonl`

Важно: CLI не использует HTTP API — `ask.py` вызывает `app.query_service.answer_question` напрямую (в отличие от Streamlit, который ходит в API).

### 3. Streamlit UI

Запуск:

```bash
streamlit run app/ui/main.py
```

UI работает как локальный HTTP-клиент API и берет базовый URL из `UI_API_BASE_URL`.

Доступные разделы:

- `Mission Control`
- `Быстрый ответ`
- `Чат с тьютором`
- `Интерактивный Quiz`
- `Курс`
- `Адаптивный план`
- `Knowledge Graph`
- `Прогресс обучения`
- `История`
- `Темы`
- `Метрики`
- `Найти материалы`
- `Объяснить файл`
- `Чистый вид`
- `Flashcards` (колоды и повторение по SM-2)

`Mission Control` — домашний экран: SSR-баннер предлагает следующий шаг, а семь плиток открывают основные режимы без длинной ленты блоков. Плитка `Курс` активирует папку из индекса вместе со списком документов, а при переходе из плитки в раздел сверху появляется возврат `← Mission Control`.

Во вкладке **«Быстрый ответ»** теперь есть отдельный компактный слой прозрачности для retrieval routing. Пользователь видит безопасное пояснение профиля ответа и блок **«Почему этот маршрут»**, если debug-пayload уже содержит `retrieval_routing.selected_profile` / `effective_profile` / `fallback_reason`. Важно, что UI не показывает raw `retrieval_mode` как learner-facing control: технические названия остаются в debug-слое и внутренних контрактах.

В expert/debug-слое Quick Answer поверх старых метрик теперь дополнительно выводятся:
- `selected_profile` — что было запрошено или выбрано правилом;
- `effective_profile` — что реально сработало после fallback/gating;
- причина маршрута и источник решения (`manual`, `rule`, `cache` и т.д.), если они есть.

Это сознательно отделено от SSR: retrieval routing объясняет, **как был собран ответ по материалам**, а SSR объясняет, **какой следующий учебный шаг стоит сделать**.

<a id="us-35-quick-answer-ожидание"></a>

**Quick Answer (US-3.5): ожидание и подкрепление.** После нажатия «Получить ответ» интерфейс показывает одну педагогически нейтральную фразу о том, что система подбирает фрагменты из ваших материалов (формулировка выбирается по вопросу, без циклической анимации и без «техно»-терминов вроде retrieval/embeddings). Если ответ пришёл быстро (порог согласован с подписью «Время ответа» / корзиной «быстро») и есть хотя бы один источник при уверенности не ниже «низкой», может однократно показаться короткое позитивное сообщение. Это **UX-подкрепление момента ожидания**, а не утверждение об истинности или полноте ответа — проверяйте вывод по тексту ответа и карточкам источников.

Что умеет UI:

- обычные вопросы к базе знаний
- tutor-диалог с сохранением сессии
- `Контекст тьютора` и `Шаги оркестрации` в tutor chat поверх typed tutor payload
- переход из быстрого ответа в tutor (кнопка «Учить эту тему 5 минут» задаёт короткую цель сессии; в чате тьютора показывается компактная строка «Сейчас: …» и цель уходит в запросы к API как опциональные поля `tutor_goal_*`)
- при переходе из Quick Answer в Tutor сохраняется continuity-контекст (`topic`, `last_question`, `answer_summary`) в текущем `session_state`, чтобы Tutor стартовал не «с нуля»
- unified continuity UX: в `Чат с тьютором`, на Home и в `Мой прогресс` показывается компактный блок **«Текущий учебный контекст»** с темой, короткой причиной текущего шага и подсказкой следующего действия
- synthesis по теме или выборке документов
- learning plan
- quiz по теме или документу
- mastery / analytics / adaptive daily plan
- после переиндексации, если сработало восстановление mastery из истории профиля — бейдж **«Профиль обновлён после переиндексации»** (с датой в UTC) в панели профиля (AI) и на вкладке «Прогресс обучения»
- export в Markdown и Anki там, где это поддержано интерфейсом
- QR/JSON экспорт локального state из сайдбара
- **Flashcards:** генерация карточек из каталога документов, активного курса или загрузки файла, предпросмотр с правкой текста до сохранения, повторение due-очереди с прогрессом сессии

#### Flashcards

Три подвкладки: **Мои колоды**, **Создать новые**, **Повторение** (на вкладке «Повторение» в заголовке может отображаться число due-карточек).

**Создать новые**

- Источник: документ из каталога тем (после индексации) или загрузка файла (PDF, TXT, MD, DOCX).
- Число карточек при генерации задаётся слайдером (**5–20**).
- После генерации показывается **предпросмотр**: для каждой карточки можно изменить поля вопроса/ответа и теги, удалить карточку из списка.
- **Сохранить колоду** доступно, если осталось **не меньше пяти** карточек с непустыми вопросом и ответом (пустые пары не учитываются). Иначе интерфейс предупредит без отправки запроса на сервер.

**Повторение**

- Можно сузить область: колода и/или фильтр по тегам, затем **Загрузить очередь** (due-карточки с `next_review` не позже «сейчас»).
- Карточки идут по одной: сначала вопрос, кнопка «Показать ответ», затем четыре оценки (**Снова**, **Трудно**, **Хорошо**, **Легко**) — они соответствуют шагу SM-2 на сервере.
- Прогресс сессии: «карточка *k* из *N*».
- По завершении последней карточки показывается **сводка** по количеству нажатий по каждой оценке и строка **о ближайшем следующем повторении** среди карточек, которые вы успели оценить в этой сессии (ориентир по времени в UTC в подписи).
- Если запрос оценки к API завершился ошибкой, показывается сообщение об ошибке, **очередь не сдвигается** — можно повторить оценку.
- Если due-очередь пуста, показываются дата и количество ближайших запланированных карточек.
- Recovery-действие **«Разнести хвост очереди на 5 дней»** можно отменить из пустого состояния. Отмена возвращает только будущие карточки без истории повторения; карточки, уже оценённые после разнесения, сохраняют рассчитанные SM-2 даты.

**Заметка по API:** `POST /flashcards/decks` принимает массив `cards` длиной **не меньше пяти** элементов; меньше — ошибка валидации (обычно HTTP 400).
`POST /flashcards/generate` поддерживает `scope=course`: передайте `source_paths`, `course_id`, `course_title` и `folder_rel`, чтобы получить единый preview deck по документам активного курса.
После reveal ответа в review доступна кнопка «Не знаю, объясни»: она записывает SM-2 оценку `1`, открывает Tutor с целью по вопросу карточки и оставляет кнопку возврата к Flashcards.

#### Knowledge Graph (D3)

Вкладка **Knowledge Graph** (боковая панель «Ещё») показывает интерактивный граф курса: уровень заливки, кольцо mastery, пульсация frontier и клик по узлу → панель концепта с документами и мостом `_kgc` в Streamlit.

**Типы связей (легенда слева внизу):** compiler-связи (`prerequisite`, `precedes`, `part_of`, `related` и расширенные `extends` / `uses` / `contrasts`) отображаются разным цветом и штрихом; prerequisite из `concepts[].prerequisites` всегда помечен явно. Клик по строке легенды скрывает/показывает ребра выбранного типа (фильтр только внутри iframe, без rerun Streamlit). Если семантических связей ещё нет — честная подпись «пока нет (только prerequisites)».

**Evidence по ребру:** наведение — компактная подсказка (тип, документ, уверенность); клик — панель `#ep-panel` с полями из compiler (`evidence_doc_id` / label, `evidence_chunk_id` как ID, `confidence` или «н/д», бейджи «слабое evidence» / «выведено»). Текст фрагмента не выдумывается. У prerequisite-only ребер — «нет evidence».

**Диагностика (🔬):** помимо структурного KG-02 (циклы, orphans) блок **Качество компиляции** — `generation_id`, scope, число концептов и семантических связей, confidence p50, бейдж «Граф готов» / «Качество графа в процессе» (`gate_passed=false` не маскируется как готовый). При устаревшей привязке поколения — предупреждение пересобрать граф. Без sidecar — «Отчёт качества недоступен», граф всё равно рисуется.

Фильтр типов связей сочетается с фильтром уровней. Esc закрывает сначала панель evidence, затем панель узла.

### 4. Telegram

Бот использует тот же локальный backend и ту же SQLite-базу состояния.

Нужны переменные:

- `TELEGRAM_BOT_TOKEN`
- опционально `TELEGRAM_DAILY_REMINDER_CHAT_ID`
- опционально `TELEGRAM_DAILY_REMINDER_HOUR`

Важно:

- это не отдельное облачное приложение
- Telegram и Streamlit делят одно локальное состояние
- голос в Telegram сейчас не доведен до полноценного сценария из коробки

## Explain / Content

Файловые endpoints:

- `GET /explain/file`
- `GET /content/file`

Поддерживаемые форматы:

- `.txt`
- `.md`
- `.html`
- `.pdf`
- `.docx` (через `python-docx`)

Если файл удален или путь устарел после reindex, API вернет ошибку с подсказкой про переиндексацию.

## Sessions, Tutor и Quiz

Persistent multi-turn работает через `session_id`.

Tutor:

- идет через `POST /ask`
- включается `query_mode="tutor"`
- хранит историю в session store
- может возвращать tutor payload, inline quiz и learner profile metadata
- **Цикл обучения (контракт API):** в `tutor.tutor_cycle` — фаза (`phase`), приоритет шага (`default_next_step`: сначала due review, затем micro-quiz или продолжение диалога), состояние quiz/review; в ответе `POST /quiz/evaluate` — `diagnostic_feedback_status`: `recognized` | `recalled` | `misconception` | `cannot_apply`
- **Оркестрация (19.4+):** `tutor.orchestration_state` и `tutor.socratic.question_type` — стабильные поля для UI без опоры на сырой `debug`
- **Typed pipeline surfaces (E6.2+):** `tutor.tutor_orchestration_pipeline` и `tutor.tutor_pipeline` дают нормализованный summary шагов оркестрации и tutor pipeline для UI/API/read-only аналитики
- Политика персонализации (матрица целей/mastery/due): `tutor.tutor_cycle.personalization_policy`
- **Clamp signals (E6.1+):** `tutor.policy_clamped` и `tutor.policy_clamp_reasons` показывают, был ли следующий шаг ограничен политикой персонализации из-за due review, mastery gap или quiz emphasis

Scoped quiz:

- `POST /quiz/generate`
- scope: `document` или `topic`

Micro-quiz evaluation:

- `POST /quiz/evaluate`

Due reviews:

- `GET /review/due`

## Темы, Synthesis и Learning Plan

Knowledge workspace API:

- `GET /topics`
- `POST /synthesize`
- `POST /learning-plan`
- `GET /kb/overview`
- `GET /kb/search`
- `GET /kb/suggestions`

UI поверх этих маршрутов дает:

- каталог тем
- конспект по теме
- подборку связанных документов
- learning plan
- Course Workspace: кнопку «Активировать как курс» для папки документов и «Подготовить курс» для scoped synthesis + `/learning-plan` по документам активного курса; повторный запуск использует локальный JSON-кэш артефакта
- экспорт результата в Markdown/Anki там, где поддержано

## Прогресс и аналитика

Основные маршруты:

- `GET /dashboard/mastery`
- `GET /dashboard/coach_plan`
- `GET /dashboard/adaptive_daily_plan`
- `GET /dashboard/analytics`
- `GET /dashboard/offline_status`

Adaptive Daily Plan:

- сохраняется локально
- может пересчитываться при взаимодействиях и через dashboard endpoint
- отображается в UI на главной и в разделах прогресса/аналитики

Course Workspace в Progress:

- если активен StudyScope, вкладка «Прогресс обучения» показывает фильтр «Только активный курс»
- отдельная course panel считает документы, карточки, due today, освоенные карточки, последнюю тему Tutor и ближайшие пробелы по тегу `course:<id>`
- открытие панели пишет workflow event с metrics label `course_workspace`

## Экспорт и импорт состояния

Локальный sync:

- `GET /sync/export`
- `POST /sync/import`
- `GET /sync/telegram`

Важно:

- `POST /sync/import` перезаписывает локальное состояние
- QR-экспорт есть в UI через `app/sync_service.py`, но основным совместимым контрактом остаются export/import endpoints

## Важные переменные `.env`

### Провайдер и модели

- `OPENAI_API_KEY`
- `HOME_RAG_API_KEY` — опционально; при задании защищает REST (`X-API-Key`). Health/bootstrap остаются публичными.
- `LLM_API_BASE`
- `OPENAI_API_BASE`
- `EMBED_API_BASE`
- `LLM_MODEL`
- `EMBED_MODEL`
- `EVAL_JUDGE_LLM`
- `QUIZ_LLM_MODEL`
- `QUIZ_LEARNING_MODE_DEFAULT`
- `REWRITE_MODEL`
- `CLASSIFIER_MODEL`
- `SSR_LLM_API_BASE` — OpenAI-compatible endpoint для коротких SSR-объяснений в карточке adaptive plan (по умолчанию `http://127.0.0.1:8787`, типичный порт LM Studio). Пустая строка означает «как основной чат»: используется `LLM_API_BASE`. Корневой URL без пути нормализуется до `.../v1`.
- `SSR_LLM_API_KEY` — если не задан, берётся `OPENAI_API_KEY`; для loopback без ключа применяется заглушка (см. `app/provider.py`).
- `SSR_LLM_MODEL` — если не задан, используется `LLM_MODEL`; для LM Studio укажите id загруженной там модели.
- `SSR_ALLOW_MAIN_LLM_FALLBACK` — по умолчанию `false`: если отдельный loopback SSR endpoint недоступен, приложение падает явно вместо тихого переключения на основной `LLM_MODEL`. Ставьте `true` только если SSR-объяснениям разрешено использовать primary chat route.
- `ENABLE_SSR_LLM_PROFILING` — писать JSONL-профили вызовов SSR (включая `cache_hit` и шаблонные fallback); по умолчанию `true`.
- `SSR_LLM_PROFILE_LOG_DIR` — каталог файлов `ssr_llm_profile_YYYY-MM-DD.jsonl` (по умолчанию `logs/ssr_llm_profiles` от корня проекта).

### Pipeline и retrieval

- `ENABLE_REWRITE`
- `ENABLE_CLASSIFIER`
- `ENABLE_SELF_CORRECTION`
- `ENABLE_CONDENSE`
- `RAG_PROFILE`
- `RETRIEVAL_MODE`
- `SIMILARITY_TOP_K`
- `ENABLE_RERANKER`
- `RERANK_TOP_N`
- `RERANK_MODEL`
- `DOC_TOP_K`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `SPLIT_STRATEGY`
- `WINDOW_SIZE`

### Tutor и UI

- `CONDENSE_HISTORY_WINDOW`
- `CONDENSE_HISTORY_WINDOW_TUTOR`
- `ENABLE_TUTOR_INLINE_QUIZ`
- `TUTOR_INLINE_QUIZ_SEPARATE_LLM_CALL`
- `ENABLE_TUTOR_AUTO_QUIZ_LOOP`
- `ENABLE_TUTOR_PEDAGOGICAL_ORCHESTRATOR`
- `USER_STATE_DB`
- `UI_API_BASE_URL`
- `SHOW_TUTOR_DEV_TOOLS`

### Индекс, cache и summaries

- `COLLECTION_NAME`
- `SUMMARY_COLLECTION_NAME`
- `QUERY_ENGINE_CACHE_SIZE`
- `QUERY_ENGINE_TTL_SEC`
- `ENABLE_FAQ_CACHE`
- `FAQ_MIN_SCORE`
- `ENABLE_METADATA_ENRICHMENT`
- `ENABLE_DOCUMENT_SUMMARIES`

### Guardrails и observability

- `GUARDRAILS_MAX_QUESTION_LENGTH`
- `GUARDRAILS_BLOCK_ON_PROMPT_INJECTION`
- `GUARDRAILS_REQUIRE_SOURCES`
- `GUARDRAILS_FALLBACK_ON_EMPTY_ANSWER`
- `GUARDRAILS_FALLBACK_ON_MISSING_SOURCES`
- `GUARDRAILS_FALLBACK_ON_SUSPICIOUS_OUTPUT`
- `GUARDRAILS_FALLBACK_ON_PII_DETECTED`
- `ENABLE_ASYNC_QUALITY_JUDGE`
- `ASYNC_QUALITY_JUDGE_SAMPLE_RATE`
- `ENABLE_OTEL_TRACING`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_SERVICE_NAME`
- `OFFLINE_MODE`
- `OFFLINE_PROBE_LLM_ENDPOINT`

### Metrics storage

Эти переменные читаются напрямую в `app/metrics.py`:

- `METRICS_STORE_PATH`
- `METRICS_DASHBOARD_DB_PATH`
- `LLM_COST_LOG_DIR`

## Тесты и smoke-check

### Pre-flight: environment check

Запусти перед первым стартом и после каждого изменения модели или профиля:

```bash
python scripts/check_env.py
```

Скрипт проверяет:
- все required env vars (`OPENAI_API_KEY`) установлены;
- значения ключевых переменных (`LLM_MODEL`, `SSR_LLM_MODEL`, `QUIZ_LLM_MODEL`, `LLAMAINDEX_METADATA_FALLBACK_MODEL`) — источник (OS env, `.env`, или дефолт);
- **OS env override**: если переменная модели установлена в OS env и отличается от `config.env` — выводит предупреждение и PowerShell-команду для удаления;
- **Cloud model in local profile**: если `LLM_MODEL` / `SSR_LLM_MODEL` содержит `openai/`, `google/` и т. д. (cloud provider prefix), а `HOME_RAG_LOCAL_PROFILE=balanced` или `local_strict` — выводит WARNING (stale OS env);
- **LLAMAINDEX_METADATA_FALLBACK_MODEL**: если содержит `/` — LlamaIndex упадёт с ошибкой валидации; значение должно быть plain OpenAI model id (`gpt-4o-mini`).

Пример чистого вывода:
```
Environment check:
  Variable                            Status   Value
  ----------------------------------  -------  --------------------
  OPENAI_API_KEY                      SET      sk-o***da02
  LLM_MODEL                           default  gpt-4o-mini
  ...
All required environment variables are set.
```

Пример вывода при stale OS env:
```
OS environment override warnings:
  WARN: LLM_MODEL OS env='google/gemma-4-e4b' overrides config.env='qwen2.5-coder-7b-instruct'
  WARN: LLM_MODEL='google/gemma-4-e4b' looks like a cloud model but HOME_RAG_LOCAL_PROFILE='balanced'

  Hint: unset stale OS env vars (PowerShell):
    [System.Environment]::SetEnvironmentVariable('LLM_MODEL', $null, 'User')
    Then restart your terminal.
```

> **Почему это важно:** `load_dotenv("config.env")` не перезаписывает уже установленные переменные окружения. Стale OS env var (`LLM_MODEL=google/gemma-4-e4b` из старой сессии) молча выигрывает над `config.env` и вызывает реальные cloud API calls и ошибки LlamaIndex.

---

Defense eval (сравнение `vector_only` / `hybrid` / `bm25_only` на `demo_data`):

```bash
python scripts/build_demo_chroma.py
python scripts/run_defense_eval.py
pytest tests/test_defense_eval_dataset.py -q
```

```bash
python -m pytest
python scripts/smoke_check.py
python scripts/check_graph_expansion_gate.py
python scripts/check_graph_expansion_gate.py --profile strict
python scripts/smoke_graph_expansion_gate.py
python scripts/graph_expansion_compare.py --baseline-jsonl logs/graph_off.jsonl --candidate-jsonl logs/graph_on.jsonl
python scripts/graph_expansion_compare.py --baseline-jsonl logs/graph_off.jsonl --candidate-jsonl logs/graph_on.jsonl --profile strict --enforce-gate
python scripts/smoke_graph_expansion_compare.py --requests 32
python scripts/smoke_graph_expansion_compare.py --requests 32 --profile strict --enforce-gate
```

CI merge-gate для graph expansion живёт в `.github/workflows/graph-expansion-smoke-gate.yml` и использует строгий профиль smoke-check.

Tutor regression gate пока доступен как локальная ready-команда:

```bash
python scripts/check_tutor_regression_gate.py
python scripts/check_tutor_regression_gate.py --summary-only
```

Smoke/CI contour для tutor выделен в активный backlog `E6.6` и ещё не считается закрытым workflow-path.

Unified eval loop (все проверки одной командой):

```bash
python scripts/run_eval_loop.py --profile ci
python scripts/run_eval_loop.py --profile nightly --report-json logs/eval_report.json
python scripts/run_eval_loop.py --profile nightly --webhook --report-json logs/eval_report.json
```

Детальные фазы отдельно:

```bash
python scripts/run_prompt_smoke.py --report-json logs/prompt_smoke.json
python scripts/run_quality_benchmark.py --report-json logs/quality_benchmark.json
python scripts/run_router_eval.py --report-json logs/router_eval.json
```

Полный runbook для регулярных замеров и передачи результатов агенту: [eval_experimenter_runbook.md](eval_experimenter_runbook.md).

Offline eval:

```bash
python run_eval.py
python run_eval_compare.py
```

## Частые проблемы

<a id="ssr-lm-studio-profiles"></a>

### SSR / LM Studio и профили (advanced)

**Где в UI:** блок «Почему сейчас» на карточке плана (SSR explanation).

**Env:** см. список `SSR_*` и `ENABLE_SSR_LLM_PROFILING` в разделе [Важные переменные `.env`](#важные-переменные-env). Подробнее по полям JSONL, OTEL и сводке — [ssr_llm_profiling.md](ssr_llm_profiling.md). Агрегированная статистика:

```bash
python scripts/summarize_ssr_llm_profiles.py
```

**LM Studio не отвечает или другой порт:** проверьте, что сервер слушает тот же хост/порт, что в `SSR_LLM_API_BASE`. Если TCP к loopback недоступен, приложение по умолчанию выдаёт явную ошибку `SSR_ALLOW_MAIN_LLM_FALLBACK is not set`, чтобы не отправлять SSR-персональные данные через primary chat route. Для осознанного fallback на `get_llm()` / `LLM_MODEL` задайте `SSR_ALLOW_MAIN_LLM_FALLBACK=true`.

**Ошибки 401 / неверная модель:** для LM Studio задайте `SSR_LLM_MODEL` под загруженную модель; при удалённом endpoint без loopback-ключа понадобится `SSR_LLM_API_KEY` или `OPENAI_API_KEY`.

**В JSONL нет новых строк:**

- выключено профилирование: `ENABLE_SSR_LLM_PROFILING=false`;
- нет прав на каталог или диск переполнен — в логах будет предупреждение `ssr_llm_profile_write_failed`;
- вы не открывали экран с карточкой / не было событий SSR (записи идут только по факту попытки объяснения, в т.ч. `outcome=cache_hit`).

Метрики основного чата по-прежнему в `LLM_COST_LOG_DIR` / `cost_logs_*.jsonl`; SSR-профили — отдельные файлы по дате.

### REST возвращает 401 на `/ask`

- В `.env` задан `HOME_RAG_API_KEY`, а клиент не передаёт `X-API-Key`.
- Для локального UI: ключ должен совпадать в `.env` и в запросах Streamlit-клиента.
- `GET /health` без ключа должен отвечать `200` — если нет, проблема не в API-key guard.

### API не стартует

Проверьте:

- активирован ли `.venv`
- установлен ли `requirements.txt`
- заполнен ли `.env`

Запусти `python scripts/check_env.py` — скрипт покажет, если модель установлена из stale OS env.

### `/ui/bootstrap` медленный (> 3 s) при первом открытии

Первый запрос ожидаемо медленнее: FastAPI прогревает кэши в фоновых потоках (readiness scan, index stats, SSR semantic cache). При пустом индексе эти потоки стартуют сразу при запуске API. При заполненном индексе первый `/ui/bootstrap` должен укладываться в 800 ms–1.5 s.

Если постоянно > 3 s — запусти `python scripts/check_env.py`: stale OS env `LLM_MODEL` с cloud provider prefix вызывает реальные LLM API calls в критическом пути bootstrap.

### Индекс пустой

Проверьте:

- есть ли файлы в `data/`
- запускался ли `python ingest.py`
- что `GET /index/stats` показывает `documents_count > 0`

### `/ask` возвращает `503`

Обычно это значит одно из двух:

- индекс пустой (запусти `python ingest.py`)
- идет переиндексация

### Streamlit не видит API

Проверьте:

- запущен ли `python main.py`
- корректен ли `UI_API_BASE_URL`

### Не работает Telegram-бот

Проверьте `TELEGRAM_BOT_TOKEN` и убедитесь, что бот запускается на той же машине, где лежит локальное состояние.

### Mastery обнулилась после reindex

Не должно быть. После переиндексации `learner_model_service` восстанавливает mastery из профиля; если это сработало, в панели профиля и на вкладке «Прогресс обучения» появится бейдж **«Профиль обновлён после переиндексации»** (с датой в UTC). Если бейджа нет и прогресс действительно пропал — проверь, что `data/user_state.db` не был перезаписан и что `POST /sync/import` не был вызван с пустым bundle.

### Ответ обрывается или пустой

Проверь:

- не сработали ли output guardrails (`GUARDRAILS_FALLBACK_ON_EMPTY_ANSWER`, `GUARDRAILS_FALLBACK_ON_SUSPICIOUS_OUTPUT`) — fallback-ответ помечается в debug;
- хватает ли токенов в модели (`LLM_MODEL`, длинный контекст);
- не словился ли `RETRIEVAL_MODE=hybrid` на тяжёлом BM25 — попробуй `uvicorn app.api:app --workers 2`.

### `chroma_db/` занимает сотни МБ или гигабайты

Нормальный размер — **единицы МБ** для небольшого корпуса (2–50 документов). Аномальный рост означает, что в метаданных чанков хранится лишнее (целый документ, дублированные соседние блоки).

**Диагностика:**

```bash
python scripts/check_chroma_health.py
```

Выводит: размер файла, количество нод, медиану / p95 / max размера `_node_content`. Здоровое состояние — median < 8 KB. `FAIL` (> 30 KB) — нужна переиндексация.

**Лечение — полный сброс и повторная индексация:**

```bash
python scripts/fresh_start.py --confirm-token DELETE-ALL-LOCAL-HOME-RAG-DATA
```

После сброса запусти проверку снова — должно быть `[OK]`.

**Коренные причины (зафиксированные, исправлено 2026-06-01):**

| Проблема | Симптом | Исправление |
|---|---|---|
| `original_text` = весь документ в каждом чанке | median ~93 KB/node | `_apply_contextualized_chunks` больше не ставит `original_text` на уровне документа |
| PREV/NEXT `RelatedNodeInfo` дублировали метаданные | median ~270 KB/node | `_strip_relationship_metadata` очищает метаданные соседних ссылок |

Регрессионные тесты в `tests/test_ingestion_split_metadata.py` (тесты `test_apply_contextualized_chunks_does_not_store_full_doc_as_original_text` и `test_sentence_splitter_nodes_have_per_chunk_original_text`) ловят возврат этих дефектов автоматически.

---

## Куда дальше

- 🚀 **[user_guide.md](user_guide.md)** — hero + быстрый старт за 5 минут.
- 👣 **[quickstart.md](quickstart.md)** — пошаговый онбординг учебного цикла (10 шагов).
- 📸 **[quickstart_demo.md](quickstart_demo.md)** — smart-документ с реальными скриншотами.
- 🎬 **[user_scenarios.md](user_scenarios.md)** — каталог сценариев от простого к сложному с шот-листами для видео.
- 📚 **[api_reference.md](api_reference.md)** — полная таблица HTTP API.
- 🧠 **[personalized_learner_model.md](personalized_learner_model.md)** — модель ученика и Adaptive Daily Plan.
- 🧪 **[eval_experimenter_runbook.md](eval_experimenter_runbook.md)** — регулярные замеры качества.
- 🗺 **[cjm.md](cjm.md)** — customer journey и critical moments of truth.
