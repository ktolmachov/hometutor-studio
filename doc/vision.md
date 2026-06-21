# Видение продукта

Актуализировано по коду на **2026-05-23** (сводка поставки: [`doc/roadmap.md`](roadmap.md)).

## Снимок: стек и границы

Один **локальный** инстанс учебного ассистента над папкой `data/`: входы **Streamlit** (основной UX, Mission Control), **FastAPI** (`POST /ask` и REST API), **CLI** и **Telegram** — поверх общего backend и SQLite-состояния. Индекс — **Chroma** + llama-index; LLM/embeddings — через провайдер в коде (`app/provider.py`, настройки из `.env`). **Smart Study Router** (SSR) с AI Vision L1-L2 — ML forgetting curve + LLM-персонализированные объяснения. Инварианты: **local-first**, ответы **с привязкой к источникам**, цикл «ответ → tutor → quiz → review/plan → SSR next action», а не разовый Q&A.

**Вне текущих целей:** multi-tenant SaaS, облачная синхронизация аккаунта между устройствами, полноценный offline LLM из коробки, универсальный explain для всех ingest-форматов.

Инженерная карта модулей, пайплайн и соглашения по коду — в **`doc/architecture.md`** и **`doc/conventions.md`** (TL;DR + ссылки); здесь не дублируем списки файлов и контрактов.

## Что это за продукт сейчас

По смыслу для пользователя это:

- поиск и ответы по своим документам с источниками
- tutor-режим и многоходовые сессии с expert controls
- quiz, spaced repetition и adaptive daily plan
- темы, synthesis, learning plan
- Smart Study Router — умная подсказка следующего учебного шага с объяснением
- Mission Control — единый навигационный экран с 7 направлениями
- course mode с cockpit, graduation, homework playbook
- RAG profiles (ADR-021) — graph-aware retrieval + prompt selector
- прогресс и метрики в UI

## Для кого

Один локальный пользователь с учебными материалами, которому нужен полный цикл обучения, а не только поиск.

## Ценность

1. Найти ответ по своим материалам.
2. Развернуть в tutor-объяснение.
3. Проверить понимание quiz-ом.
4. Вернуться к слабым местам через review и план.
5. Продолжать тему, а не один вопрос.

## Ближайший вектор развития

- **Production deployment**: Docker → VPS, CI/CD, health monitoring
- **AI Vision L3-L5** (gated): weekly planner optimization, graph-concept routing, feedback policy learning — при наличии 1000+ real samples
- **Real-world A/B testing**: ML serving activation после порога данных
- observability и надёжность без поломки local-first
- breakthrough ideation: gamification, collaborative learning, mobile PWA

## Как читать roadmap рядом с этим документом

- `vision.md` — продукт и границы (этот файл)
- `roadmap.md` — сводная карта эпох, волн и ссылок на SSoT
- `product_idea.md` — более широкий нарратив и гипотезы
- `backlog_registry.yaml` — рабочий инженерный roadmap / SSoT
- `tasklist.md` — производный weekly view

Если что-то в roadmap конфликтует с этим файлом или кодом, верить нужно коду и `Live`-документам.
