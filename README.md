# hometutor

**Что это:** локальный учебный RAG поверх ваших файлов в `data/`: ответы с источниками, чат-тьютор, spaced repetition и adaptive plan — без отдельного облачного продукта. Идея и сценарии: [doc/product_idea.md](doc/product_idea.md); сводная карта эпох и волн: [doc/roadmap.md](doc/roadmap.md).

> 🏆 **Для жюри конкурса:** начните с [doc/pitch.md](doc/pitch.md) (one-page battle card) и [doc/quickstart_demo.md](doc/quickstart_demo.md) (реальные GIF из продукта). Скрипт выступления на 3 минуты — [doc/presenter_script.md](doc/presenter_script.md). Собрать полный ZIP-пакет: `npm run demo:kit`.

**Демо-путь — учебный цикл** (как связаны шаги после установки):

```text
локальные файлы (data/) → ответ с источниками → тьютор и мини-квиз → вкладка «Мой прогресс» → выпуск концепции при освоении
```

- **Для кого:** самостоятельное обучение по своим конспектам и курсам, офлайн-first.
- **Не для кого:** готовый мультиарендный SaaS, синхронизация между устройствами без вашей инфраструктуры.

## Быстрый старт (Localhost-only — основной путь)

Самый надёжный локальный путь на Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
# В .env задайте OPENAI_API_KEY=local для локального провайдера или реальный ключ.
.\scripts\local_start.ps1 -SkipPip
```

Перед запуском wrapper вызывает readiness gate:

```powershell
.\.venv\Scripts\python.exe scripts\local_readiness.py
```

Он проверяет `.venv`, `.env`, каталоги `data/` / `chroma_db` / `logs`, порты `8000/8501`,
локальные provider URLs и, опционально, уже запущенные health endpoints:

```powershell
npm run local:check
npm run local:check:running
```

- **API:** http://127.0.0.1:8000
- **UI (Streamlit):** http://127.0.0.1:8501

Индексация после добавления файлов в `data/`: `.\.venv\Scripts\python.exe ingest.py`.

## Быстрый старт (Docker)

1. **Клонировать** репозиторий и перейти в каталог проекта.
2. **`copy .env.example .env`** и задать минимум **`OPENAI_API_KEY`** (остальное — по умолчанию из `.env.example`).
3. **`docker compose up --build`**

Перед первым запуском на хосте: **`python scripts/bootstrap.py`**. Тома: `./data` → `/app/data`, `./chroma_db` → `/app/chroma_db`, `./logs` → `/app/logs` (см. [docker-compose.yml](docker-compose.yml)).

- **API:** http://127.0.0.1:8000
- **UI (Streamlit):** http://127.0.0.1:8501

Индексация: `docker compose exec hometutor python ingest.py`.

**LM Studio на хосте:** `docker compose -f docker-compose.yml -f docker-compose.lmstudio.yml up` или `host.docker.internal` в `.env` — [deploy/docker/env.docker.example](deploy/docker/env.docker.example).

## Локальная установка (без Docker)

Требуется Python **3.10+**.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Заполните в `.env` как минимум **`OPENAI_API_KEY`**. Проверка: `python scripts/bootstrap.py` или `pytest tests/test_user_state.py`.

Проверка промптов и пайплайна на mini-KB (без ваших `data/`): `python scripts/run_prompt_smoke.py` (отчёт JSON в stdout; опционально `--strict` по эвристикам). Регрессия retrieval: `python scripts/run_quality_benchmark.py`; оркестратор тьютора: `python scripts/run_router_eval.py`.

### Локальный провайдер (Ollama) для integration-тестов

Проект использует OpenAI-совместимый API, поэтому можно запускать retrieval integration локально без OpenRouter/OpenAI.

1. Поднимите Ollama и модели:

```bash
ollama serve
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

2. Пропишите в `.env`:

```bash
OPENAI_API_KEY=local
OPENAI_API_BASE=http://127.0.0.1:11434/v1
EMBED_API_BASE=http://127.0.0.1:11434/v1
LLM_MODEL=qwen2.5:7b-instruct
EMBED_MODEL=nomic-embed-text
EMBED_DIMENSIONS=768
```

3. Запустите integration retrieval (в обычном `pytest` маркер `integration` отключён — см. `pytest.ini`):

```bash
python -m pytest -m integration tests/test_integration_retrieval.py -q
```

Если указать только путь к файлу без `-m integration`, тесты будут **deselected**. Альтернатива: `python -m pytest --override-ini=addopts= tests/test_integration_retrieval.py -q`.

Или одной командой через helper-скрипт (временно выставляет env в текущем процессе):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_integration_local.ps1
```

Если env уже настроен, используйте короткий запуск integration без подтягивания моделей:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_integration.ps1 -PytestArgs @("--collect-only","-q")
```

Общий прогон в два этапа (сначала non-integration, затем integration):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1
```

Если integration нужно поднять локально через Ollama автоматически:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1 -UseLocalOllama -SkipPull
```

**Гибрид (облачный чат + локальные эмбеддинги):** чат идёт на `OPENAI_API_BASE` (например OpenRouter), эмбеддинги — на `EMBED_API_BASE` (например Ollama). Готовый блок переменных и таймаутов для слабого CPU — в `.env.example` (секция `HYBRID: cloud LLM + local embeddings`).

#### Troubleshooting (коротко)

- `No embedding data received`:
  - проверьте локальный endpoint если: `EMBED_API_BASE=http://127.0.0.1:11434/v1`;
  - убедитесь, что `ollama serve` запущен и модель подтянута: `ollama pull nomic-embed-text`.
  - для OpenRouter проверьте live-модель: `perplexity/pplx-embed-v1-0.6b` сейчас возвращает embeddings, а `openai/text-embedding-3-small` может отвечать `No successful provider responses`.
- `'... is not a valid OpenAIEmbeddingModelType'`:
  - для OpenRouter используйте модель из `GET /api/v1/embeddings/models`, например `EMBED_MODEL=perplexity/pplx-embed-v1-0.6b`;
  - если локальная модель — `nomic-embed-text`, сделайте alias:
    `ollama cp nomic-embed-text text-embedding-3-small`.
- Быстрая проверка embeddings:
  - `.\.venv\Scripts\python.exe -c "from app.provider import get_embed_model; print(len(get_embed_model().get_text_embedding('ping')))"`;
  - если видите число из `EMBED_DIMENSIONS` (например `1024` для `perplexity/pplx-embed-v1-0.6b`) — embeddings работают.

Положите файлы в `data/`, затем индексация:

```bash
python ingest.py
```

Флаг **`python ingest.py -y`** пропускает вопрос про сброс; **`python ingest.py --reset -y`** — явный полный rebuild.

Fast reindex notes:
- Answer `n` to the reset prompt for the normal path. When files and indexing settings are unchanged, ingest exits early with `INGEST_SUMMARY run_kind=noop` before PDF parsing or embedding preflight.
- Parsed fragments are cached in `chroma_db/ingestion_extracted_documents.json`; unchanged files reuse this extraction cache during partial reindex and reset rebuilds.
- Use `--reset` only when you intentionally want to rebuild the active collections. Reset still may reuse the extraction cache, but it cannot no-op.
- For large PDF sets, tune `DOC_LOAD_NUM_WORKERS` first; then try `EMBED_BATCH_SIZE` and `EMBED_NUM_WORKERS` if embedding is the remaining bottleneck.

API и UI:

```bash
python main.py
streamlit run app/ui/main.py
```

## E2E (Playwright, deterministic)

Для браузерного smoke-прогона есть отдельный профиль с изолированной SQLite-базой:

```bash
npm run test:e2e
```

Что важно:
- раннер поднимает свой FastAPI+Streamlit стек;
- используется `USER_STATE_DB=.e2e/user_state_e2e.db` (не трогает `data/user_state.db`);
- перед стартом pre-seedится `onboarding_v1_done=1`, чтобы убрать флак первого ререндера.

Если хотите прогонять тесты против уже запущенного вручную UI/API, используйте:

```bash
set PLAYWRIGHT_SKIP_WEBSERVER=1
npm run test:e2e
```

Подробности: [doc/user_guide.md](doc/user_guide.md) и [doc/user_guide_details.md](doc/user_guide_details.md).

Публичный demo (Hugging Face Spaces, фиксированный `demo_data/`): [deploy/hf-spaces/README.md](deploy/hf-spaces/README.md).
