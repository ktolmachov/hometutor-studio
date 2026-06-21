# hometutor — personal tutor from your own notes

> **Положи папку с конспектами → получи личного тьютора с квизами, повторениями и планом на день. Локально. За 5 минут.**

<sub>Дата: 2026-04-22 · Версия: competition pitch v1 · Один документ, одна страница, одна цель — победить.</sub>

---

## Проблема

Самостоятельное обучение по своим материалам **сломано**:

- **ChatGPT** — отвечает, но не помнит прогресс, не проверяет, не повторяет. Материалы уходят в облако.
- **NotebookLM** — отвечает по документам, но нет квизов, SRS, адаптивного плана. Облако.
- **Anki** — только повторение, без понимания и без ответов.
- **Obsidian** — красиво, но не учит.

Ученик вынужден **собирать цикл из 3–4 тулов вручную** и переключаться между ними, теряя контекст каждый раз.

## Решение

**hometutor собирает полный учебный цикл в одном локальном инструменте:**

```text
твои файлы → ответ с источниками → тьютор + квиз → флэшкарты → adaptive plan → concept graduation
```

Всё в `data/user_state.db`. Всё доступно через Streamlit, Telegram, CLI и API.

## Чем мы отличаемся (одной таблицей)

| Возможность | ChatGPT | NotebookLM | Anki | Obsidian | **hometutor** |
|---|:---:|:---:|:---:|:---:|:---:|
| Ответы по своим файлам с источниками | ~ | ✅ | ❌ | ~ | ✅ |
| Сократический тьютор | ~ | ❌ | ❌ | ❌ | ✅ |
| Мини-квизы после ответа | ❌ | ❌ | ❌ | ❌ | ✅ |
| Spaced repetition (SM-2) | ❌ | ❌ | ✅ | ❌ | ✅ |
| Adaptive Daily Plan | ❌ | ❌ | ~ | ❌ | ✅ |
| **Concept graduation** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Course Workspace** (папка → курс 1 кликом) | ❌ | ~ | ❌ | ❌ | ✅ |
| Trust-панель с подсветкой фрагмента | ❌ | ~ | ❌ | ❌ | ✅ |
| **Local-first, офлайн-ready** | ❌ | ❌ | ✅ | ✅ | ✅ |
| 4 канала (UI/API/Telegram/CLI) на общем state | ❌ | ❌ | ❌ | ❌ | ✅ |

## Три killer-фичи (которых нет ни у кого)

### 1. Полный учебный цикл в одном инструменте

Ответ → тьютор → квиз → флэшкарта → adaptive plan → graduation. Переключения между режимами **сохраняют контекст**. Кнопка «Учить эту тему 5 минут» под любым ответом.

→ Видео: [scenario_01](screenshots/scenario_01/demo.gif)

### 2. Concept Graduation — единственная механика «освоено»

Концепт, стабильно удержанный на transfer-уровне **более 7 дней**, получает статус `graduated` и **больше не возвращается** в adaptive daily plan. Ни один конкурент не даёт ощущение «финиша темы».

→ Сценарий: [user_scenarios.md § 10](user_scenarios.md#сценарий-10--mastery-и-graduation)

### 3. Course Workspace — папка превращается в курс одной кнопкой

В `data/ML-Course/` 25 PDF-лекций. Клик «Активировать как курс» → synthesis + learning plan + флэшкарты + отдельная панель прогресса по тегу `course:<id>`. За минуту.

→ Видео: [scenario_05](screenshots/scenario_05/demo.gif)

## Доказательства (работает, не галлюцинирует, проверяемо)

| Что | Артефакт |
|---|---|
| Сценарии с реальными скриншотами | [quickstart_demo.md](quickstart_demo.md) — 3 GIF + 13 PNG, снято Playwright'ом |
| 14 сценариев от простого к продвинутому | [user_scenarios.md](user_scenarios.md) |
| Пошаговый онбординг за 10 шагов | [quickstart.md](quickstart.md) |
| 50+ e2e-тестов (smoke + nightly + demo) | [tests/e2e/README.md](../tests/e2e/README.md) |
| Встроенный Eval Loop: hit-rate, MRR, latency, cost | `python scripts/run_eval_loop.py --profile nightly` |
| SLO-гейты + webhook-алерты | `SLO_MAX_P95_LATENCY_MS`, `SLO_MIN_JUDGE_SCORE`, `ALERT_WEBHOOK_URL` |
| Руководство для регулярных замеров | [eval_experimenter_runbook.md](eval_experimenter_runbook.md) |
| Customer Journey Map с 13 moments of truth | [cjm.md](cjm.md) |
| Архитектура и границы | [vision.md](vision.md), [architecture.md](architecture.md) |

## Технический стек (local-first, production-grade)

- **Retrieval:** Chroma + BM25 (hybrid) + two-stage doc→chunk + reranker.
- **LLM:** любой OpenAI-совместимый (OpenRouter, OpenAI, **локальный Ollama**). Hybrid: chat облачный, эмбеддинги локальные.
- **Guardrails:** prompt injection (EN/RU), PII, пустые ответы, утечка инструкций.
- **Pipeline:** query rewrite → classify → retrieve → rerank → guardrails → answer → judge (async).
- **Tutor orchestration:** pedagogical router с policy clamp (due review / mastery gap / quiz emphasis).
- **State:** SQLite (WAL), snapshot-history, reindex-preservation of mastery, export/import/QR-sync.
- **Observability:** metrics store, cost/quality dashboard, OTEL tracing.
- **E2E:** Playwright (49 smoke + 9 nightly + 3 demo), CI gates, регрессионные гейты tutor.

## Быстрый старт для жюри

Три команды:

```bash
git clone <repo> && cd hometutor-studio
copy .env.example .env                    # впишите OPENAI_API_KEY (или используйте Ollama)
docker compose up --build
```

→ http://localhost:8501

Ещё быстрее — запустите **Jury Demo Kit**, который прогонит demo-тесты, соберёт GIF и pitch-package одной командой:

```bash
npm run demo:kit
```

Артефакт — `doc/quickstart_demo.md` + `doc/screenshots/*/demo.gif` + этот файл.

## Команда принципов

1. **Local-first, always.** Твои материалы не покидают твою машину.
2. **Учебный цикл, а не чат.** Мы меряем не число токенов, а освоенные концепты.
3. **Доверие до фрагмента.** Каждый тезис — с кликабельным источником.
4. **Один инструмент — много каналов.** Учись там, где удобно: UI, Telegram, CLI, API.
5. **Встроенное качество.** Eval Loop и SLO — не отчёт, а merge-gate.

---

## Слоган для слайда

> **«hometutor — это личный тьютор, которого ты не арендуешь у OpenAI. Он у тебя уже есть — в папке `data/`.»**

## Три фразы, которые запомнит жюри

1. **«Учебный цикл в одном инструменте — то, что ChatGPT + Anki + Obsidian делают втроём, hometutor делает сам.»**
2. **«Concept graduation — единственная механика на рынке, где продукт говорит "это ты освоил, я больше тебя не спрашиваю".»**
3. **«Отключи интернет и убедись: всё работает.»**

---

<sub>Приложения: [quickstart.md](quickstart.md) · [user_scenarios.md](user_scenarios.md) · [quickstart_demo.md](quickstart_demo.md) · [presenter_script.md](presenter_script.md)</sub>
