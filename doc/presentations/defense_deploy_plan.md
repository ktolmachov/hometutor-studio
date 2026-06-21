# План доработок к защите — 6 задач

> **Статус:** артефакты HF/demo/eval/nginx/CI в репозитории; публичный URL — после push на HF Spaces или настройки VPS + секретов GitHub.  
> **Приоритет:** задачи 1–3 критические (закрывают явные требования), 4–6 усиливают аргументацию  
> **Целевая дата:** до защиты

---

## Задача 1 — Публичный деплой (КРИТИЧЕСКИЙ)

> **Требование:** «Приложение должно быть развёрнуто и доступно онлайн»

### Варианты хостинга — сравнение

| Хостинг | Streamlit | FastAPI | Ollama | Стоимость | Сложность | Рекомендация |
|---|---|---|---|---|---|---|
| **Hugging Face Spaces** | ✅ нативно | ⚠️ только в demo/Docker Space | ❌ нет GPU free | Бесплатно | ★☆☆ Просто | ✅ **Demo UI + cloud LLM** |
| **RUVDS** | ✅ Docker | ✅ Docker | ⚠️ CPU медленно / GPU тариф | от 250 ₽/мес | ★★☆ Средне | ✅ **Full stack VPS** |
| **Vercel** | ❌ serverless не держит Streamlit | ⚠️ только stateless API | ❌ | Бесплатно | ★★★ Сложно | ⚠️ Не основной вариант |
| **Hetzner CX11** | ✅ Docker | ✅ Docker | ⚠️ CPU-only медленно | €4/мес | ★★☆ Средне | ✅ Full stack VPS |
| **Streamlit Cloud** | ✅ нативно | ❌ | ❌ | Бесплатно | ★☆☆ Просто | ⚠️ Только UI |

> **Vercel подробнее:** FastAPI можно адаптировать под Python Serverless Function, но текущий проект зависит от долгоживущего Streamlit-процесса, локального состояния, индекса и фоновых операций. Vercel подходит только для отдельного stateless REST API после рефакторинга; для защиты не является вариантом полного стека.

---

### Вариант A: Hugging Face Spaces — рекомендуется для демо

**Что разворачивается:** demo UI с заранее подготовленными публичными данными и cloud LLM. FastAPI внутри Space допустим только как demo-упрощение или через Docker Space.  
**Что не разворачивается:** Ollama (нет GPU на free tier → cloud LLM через API-ключ)  
**URL:** `https://huggingface.co/spaces/<username>/hometutor`

#### Шаги

**1. Выбрать один режим HF Spaces**
```python
# Вариант для защиты: Streamlit demo-only.
# app_file в README должен указывать на реальную точку входа UI.
# Если нужен FastAPI рядом с UI — использовать Docker Space, а не SDK streamlit.
```

**2. Создать `README.md` в формате HF Spaces**
```yaml
---
title: ИИ-тьютор с RAG
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: "1.32.0"
app_file: app/ui/main.py
pinned: false
---
```

**3. Создать `.env.spaces` для demo-режима**
```bash
# Demo-режим: cloud LLM (без Ollama), demo data
OPENAI_API_BASE=https://openrouter.ai/api/v1
OPENAI_API_KEY=<secrets в HF Settings>
LLM_MODEL=mistralai/mistral-7b-instruct:free
DEMO_MODE=true
DATA_PATH=./demo_data
```

**4. Подготовить `demo_data/`**
- 3–5 публичных учебных документа (например, отрывки из открытых учебников)
- Заранее проиндексировать и закоммитить `demo_chroma_db/` в репозиторий (иначе индексация при каждом старте)

**5. Деплой**
```bash
git remote add spaces https://huggingface.co/spaces/<username>/hometutor
git push spaces main
```

**Ограничения для защиты:** явно указать на слайде — «HF Spaces = demo-режим с cloud LLM и публичными demo data; production/local-first = Docker/localhost с Ollama или VPS».

---

### Вариант B: RUVDS — рекомендуется для полного стека

**Тариф:** RUVDS SSD-2 (2 vCPU, 4 GB RAM, 50 GB SSD) — ~600 ₽/мес  
**ОС:** Ubuntu 22.04  
**Что разворачивается:** полный стек — FastAPI + Streamlit + ChromaDB. Ollama на CPU возможна, но для демо лучше cloud LLM или GPU/VPS тариф: 2 vCPU / 4 GB RAM может отвечать слишком медленно.

#### Шаги

**1. Первоначальная настройка сервера**
```bash
# На RUVDS сервере
apt update && apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx
systemctl enable docker

# Создать пользователя deploy
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
```

**2. Клонировать репозиторий**
```bash
su - deploy
git clone https://github.com/<username>/hometutor-studio.git
cd hometutor-studio
cp .env.example .env
# Отредактировать .env: LLM_MODEL, OPENAI_API_KEY, HOME_RAG_API_KEY и т.д.
```

**3. Nginx конфиг (`/etc/nginx/sites-available/hometutor`)**
```nginx
server {
    listen 80;
    server_name <your-domain.ru>;

    # Streamlit UI
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";  # WebSocket для Streamlit
        proxy_set_header Host $host;
    }

    # FastAPI REST
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**4. HTTPS через Let's Encrypt**
```bash
certbot --nginx -d <your-domain.ru>
```

**5. Запуск**
```bash
cd hometutor-studio
docker-compose up -d
```

**6. Проверка**
```bash
curl https://<your-domain.ru>/health   # → {"status": "ok"}
# Открыть https://<your-domain.ru> в браузере → Streamlit UI
```

---

## Задача 2 — CI/build: `.github/workflows/ci.yml` (КРИТИЧЕСКИЙ)

> **Требование:** «Настроен автоматический деплой»

### Текущий безопасный минимум

В репозиторий добавлен `.github/workflows/ci.yml`: `ruff` + focused pytest + Docker build. Это уже проверяемый CI/build gate. Полный автодеплой через SSH нужно добавлять только после появления VPS, домена и GitHub Secrets.

### Следующий шаг для автодеплоя

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ── Тесты ──────────────────────────────────────────────────
  test:
    name: Tests & Lint
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest ruff

      - name: Lint (ruff)
        run: ruff check app/ --output-format=github

      - name: Run tests
        env:
          # Мокаем LLM — тесты не делают реальных вызовов
          OPENAI_API_KEY: test-key
          OPENAI_API_BASE: http://localhost:11434/v1
          LLM_MODEL: mock
          EMBED_MODEL: mock
        run: |
          python -m pytest tests/ \
            --ignore=tests/test_integration_retrieval.py \
            --tb=short \
            -q

  # ── Docker Build ───────────────────────────────────────────
  build:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

  # ── Deploy (SSH на VPS) ────────────────────────────────────
  deploy:
    name: Deploy to VPS
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: deploy
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd hometutor-studio
            git pull origin main
            docker-compose pull
            docker-compose up -d --remove-orphans
            docker system prune -f
```

### Secrets, которые нужно добавить в GitHub → Settings → Secrets

| Secret | Значение |
|---|---|
| `VPS_HOST` | IP или домен RUVDS/Hetzner сервера |
| `VPS_SSH_KEY` | Приватный SSH-ключ для пользователя `deploy` |

### Что показывать на защите до подключения VPS

```
GitHub → Actions → CI
├── Tests and lint
└── Docker build

SSH deploy — следующий шаг после настройки VPS_HOST / VPS_SSH_KEY.
```

---

## Задача 3 — Confidence score: tooltip в UI (КРИТИЧЕСКИЙ)

> **Проблема:** комиссия может спутать «confidence 87%» с «вероятностью правильности ответа»

### Что изменить в Streamlit UI

Найти место, где отображается confidence score, и добавить:

```python
# Было:
st.metric("Confidence", f"{confidence:.0%}")

# Стало:
st.metric(
    label="Confidence поиска",
    value=f"{confidence:.0%}",
    help=(
        "Качество найденных источников: насколько хорошо система нашла "
        "релевантные фрагменты. НЕ является вероятностью правильности ответа — "
        "всегда проверяйте источники."
    )
)
```

Или в markdown под ответом:

```python
st.caption(
    f"🔍 Confidence поиска: **{confidence:.0%}** "
    f"— качество найденных источников, не вероятность правильности"
)
```

---

## Задача 4 — Мини eval-run (УСИЛЕНИЕ)

> **Цель:** превратить «качество RAG высокое» в «вот конкретные результаты»

### Структура eval-набора

**Файл:** `eval/eval_dataset.json`

```json
{
  "version": "1.0",
  "date": "2026-05-XX",
  "model": "qwen2.5:7b-instruct",
  "retrieval_mode": "hybrid",
  "questions": [
    {
      "id": "q01",
      "question": "Что такое retrieval-augmented generation?",
      "expected_topics": ["векторный поиск", "LLM", "источники"],
      "ground_truth_source": "lecture_01.pdf"
    }
  ]
}
```

**Файл:** `eval/eval_results_YYYY-MM-DD.json`

```json
{
  "run_id": "eval-2026-05-XX",
  "summary": {
    "total_questions": 15,
    "faithfulness_pass": 13,
    "source_found": 14,
    "avg_confidence": 0.78,
    "avg_latency_sec": 3.2
  },
  "by_mode": {
    "vector_only":  {"source_found": 11, "faithfulness_pass": 10},
    "hybrid":       {"source_found": 14, "faithfulness_pass": 13},
    "keyword_only": {"source_found":  9, "faithfulness_pass":  8}
  }
}
```

### Протокол ручного eval (2–3 часа)

```
1. Взять 15 вопросов по demo_data (5 простых, 5 средних, 5 сложных)
2. Для каждого вопроса прогнать в трёх режимах: vector_only / hybrid / keyword
3. Оценить вручную по двум критериям:
   - source_found: правильный источник попал в top-3? (да/нет)
   - faithfulness: ответ полностью из источников, без фантазий? (да/нет)
4. Зафиксировать latency (секунды)
5. Сохранить в eval_results_YYYY-MM-DD.json
```

### Таблица для слайда

| Режим поиска | Источник найден | Faithfulness | Avg latency |
|---|---|---|---|
| Только векторный | 11/15 (73%) | 10/15 (67%) | 2.1 сек |
| **Гибридный (hybrid)** | **14/15 (93%)** | **13/15 (87%)** | **3.2 сек** |
| Только ключевые слова | 9/15 (60%) | 8/15 (53%) | 0.8 сек |

> *Запустить и вставить реальные числа вместо примеров выше*

---

## Задача 5 — Проверить аутентификацию (ПРОВЕРКА)

> **Цель:** убедиться, что заявленная auth работает ровно так, как описано на защите

### Тест-сценарий (выполнить вручную)

```bash
# 1. Запустить приложение
docker-compose up -d

# 2. Запрос БЕЗ ключа → ожидаем 401 или 403
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
# Ожидаемый ответ: {"detail": "Not authenticated"}, статус 401

# 3. Запрос С ключом → ожидаем 200
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your_key_from_env>" \
  -d '{"question": "test"}'
# Ожидаемый ответ: {"answer": "...", "sources": [...]}

# 4. Проверить health endpoint (должен быть публичным)
curl http://localhost:8000/health
# Ожидаемый ответ: {"status": "ok"} без авторизации
```

### Реализованный вариант

```python
# app/api_auth.py — dependency для защищённых REST endpoints
from typing import Annotated

from fastapi import Header, HTTPException
from app.config import get_settings

async def require_api_key(x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None):
    expected = (get_settings().home_rag_api_key or "").strip()
    if not expected:
        return  # Auth не настроена — dev/demo mode
    if (x_api_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
```

```python
# app/config.py
class Settings(BaseSettings):
    home_rag_api_key: str | None = None  # HOME_RAG_API_KEY / API_KEY
```

```bash
# .env
HOME_RAG_API_KEY=your-secret-key-here
```

---

## Задача 6 — Таблица сравнения retrieval (УСИЛЕНИЕ)

> **Цель:** доказать, что гибридный поиск — осознанный выбор, а не украшение

Результаты из Задачи 4 вставить в слайд 6 (RAG-pipeline).

### Дополнение к слайду 6

```markdown
### Доказательство: гибридный поиск лучше

Eval-run: 15 вопросов, demo corpus, модель qwen2.5:7b

| Режим | Источник в top-3 | Faithfulness | Latency |
|---|---|---|---|
| vector_only | 73% | 67% | 2.1с |
| **hybrid** | **93%** | **87%** | 3.2с |
| keyword_only | 60% | 53% | 0.8с |

Вывод: гибридный режим +20pp к источникам, +20pp к faithfulness
при приемлемом overhead +1.1 секунды.
Для точных терминов (названия алгоритмов, аббревиатуры) — keyword помогает там,
где vector промахивается.
```

---

## Обновление Слайда 10 в defense_presentation_v3.md

*После выполнения задач 1–2 обновить слайд — заменить «📋 Инструкция готова» и «📋 Возможен» на конкретные результаты*

---

## Чеклист выполнения

| # | Задача | Файлы | Статус |
|---|---|---|---|
| 1A | HF Spaces деплой | `deploy/hf-spaces/README.md`, `deploy/hf-spaces/.env.spaces.example`, `demo_data/`, `demo_chroma_db/`, `scripts/build_demo_chroma.py` | ✅ артефакты в репо; push на HF — вручную |
| 1B | RUVDS деплой | `deploy/nginx/hometutor.conf.example`, `docker-compose.yml`, SSL | 🟡 шаблон nginx; VPS/SSL — вручную |
| 2 | CI/build workflow | `.github/workflows/ci.yml` | ✅ CI + docker-build; SSH deploy при `VPS_HOST`/`VPS_SSH_KEY` |
| 3 | Confidence tooltip | `app/ui/query_tab_answer_section.py` | ✅ |
| 4 | Eval-run | `eval/eval_dataset.json`, `eval/eval_results_2026-05-20.json`, `scripts/run_defense_eval.py` | ✅ retrieval-only прогон |
| 5 | Auth check | `app/api_auth.py`, `app/api.py`, `tests/test_api.py` | ✅ pytest: 401 без ключа, 200 с ключом |
| 6 | Retrieval comparison | Таблица в `defense_presentation_v3.md` слайд 6 | ✅ |
| — | Обновить Слайд 10 | `defense_presentation_v3.md` | ✅ убраны неподтверждённые URL/deploy claims |

---

<sub>📅 Версия 1.0 · май 2026 · Согласован</sub>
