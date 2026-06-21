# hometutor — Agent Instructions

Этот файл читается агентами Codex CLI и совместимыми инструментами
автоматически при запуске в корне проекта.

Полные соглашения: `doc/conventions.md` (TL;DR + навигация).
Детали архитектуры: `doc/conventions_architecture.md`, `doc/conventions_reference.md`.
При конфликте — приоритет у `doc/conventions*.md` и кода.

Назначение файла — короткий always-on контракт. Изменчивые данные не
дублировать: использовать SSoT-файлы и проверочные скрипты ниже.

---

## Что это за проект

Локальный учебный ассистент над папкой `data/`: FastAPI (порт 8000) +
Streamlit UI (порт 8501) + CLI + Telegram бот. Индекс — Chroma + llama-index.
LLM/embeddings — через провайдер в `app/provider.py` (настройки из `.env`).

Инварианты: **local-first**, ответы с привязкой к источникам,
цикл «ответ → tutor → quiz → spaced repetition → план».

---

## Жёсткие правила (нарушение = blocker)

- **Конфиг:** только `get_settings()` / `get_retrieval_settings()` из `app/config.py`.
  Нельзя читать env-переменные напрямую нигде кроме `config.py`.

- **LLM / embeddings:** только `app/provider.py`.
  Нельзя создавать клиенты OpenAI/LLM напрямую в других модулях.

- **Промпты:** только пакет `app/prompts/` (тяжёлая реализация — `app/prompts/_impl.py`).
  Нельзя хардкодить промпты в роутерах, сервисах или UI.

- **HTTP роутеры:** endpoint-логика только в `app/routers/*`
  (+ shared contracts/helpers в `app/api_requests.py`, `app/api_models.py`).
  Нельзя добавлять endpoint-логику в `app/api.py` напрямую.
  Регистрация через `include_router` в `app/api.py`.

- **Pipeline шаги:** контракт `process(QueryContext) -> QueryContext`.
  Нельзя нарушать сигнатуру.

- **DB / persistence:** user-state таблицы — только через `_with_db()` /
  CRUD-хелперы из `app/user_state.py`. Отдельные локальные SQLite-хранилища
  допустимы только как документированные store wrappers / artifacts
  (см. `doc/conventions_architecture.md`).
  Нельзя открывать ad hoc SQLite-соединения в сервисах, роутерах или UI.

- **Guardrails:** все точки входа (API, CLI, UI, Telegram) должны проходить
  через `app/guardrails.py` / `app/input_validation.py`.

- **Bare except:** запрещены. Широкие `except Exception` только
  с `# noqa: BLE001` и явным обоснованием в комментарии.

- **Write-set:** изменять только файлы из заявленного write-set задачи.
  Попутный рефакторинг соседних модулей — запрещён.

- **Python для всех агентов:** для Codex, Cursor, Claude Code и других
  совместимых агентов для всех Python-команд в этом проекте сначала
  использовать интерпретатор `.\.venv\Scripts\python.exe` из корня репозитория.
  Если `.venv` недоступен, только тогда разрешён fallback
  на `python` или `py` из `PATH`.

---

## Token Budget & Retry Safety

Полные правила: `doc/agent_workflow_rules.md`. SSoT размеров и `full_read: forbidden`: `doc/token_safety_registry.json`.

- **≤ 12k токенов** — целевой.
- **12k–20k** — сжать history и read-set.
- **> 20k** — стоп, отчёт о блокере.
- **Read-set: max 3–5 файлов** (рутина — 2–3). Только из явного read-set.
- Для крупных файлов: signatures / секция / `rg` по `safe_hint` — не full-read.
- После ERR: 1 ретрай с сокращённым контекстом, затем стоп.

Проверка перед отправкой:
```bash
.\.venv\Scripts\python.exe scripts/check_readset.py <file>...
.\.venv\Scripts\python.exe scripts/lint_agent_prompts.py
.\.venv\Scripts\python.exe scripts/check_llm_context_gate.py
```

Planning prompt: canonical template из `doc/agent_workflow_templates.md`. Reasoning-модель — только с явным одобрением.

---

## Стиль кода

- PEP 8; говорящие имена; комментарии только для неочевидной логики.
- KISS: маленькие модули, явные зависимости, без лишних абстракций.
- Без feature flags, без backwards-compatibility shims без явной нужды.

---

## Тесты

После изменений запускать **только затронутые тесты**. Префикс везде — `.\.venv\Scripts\python.exe -m pytest` (fallback: `python` / `py`).

Bundles по зонам изменений:

| Зона | Файлы |
|------|-------|
| Flashcards | `tests/test_flashcard_service.py` |
| API / contracts | `tests/test_query_service.py tests/test_api.py` |
| Tutor core | `tests/test_tutor_orchestrator.py tests/test_pipeline_steps.py` |
| Persistence | `tests/test_user_state.py tests/test_learner_model_service.py` |
| Graph | `tests/test_metrics.py tests/test_graph_expansion_benchmark.py` |
| UI helpers | `tests/test_ui_helpers.py` |

Если в env заданы `PYTHONHOME` / `PYTHONPATH` — снять их или добавить `-E` к интерпретатору (детали — комментарий в `pytest.ini`). Reranker в pytest всегда `False` (conftest). E2E smoke (`npm run test:e2e:smoke`) и `HOME_RAG_E2E_OFFLINE` — см. `tests/e2e/README.md`.

Полный suite — только при явном запросе. Retrieval integration: `-m integration tests/test_integration_retrieval.py`.

---

## Документация (doc-sync)

Обновлять документацию, если изменились:
- Публичный API-контракт → `doc/api_reference.md`
- UI-поведение → `doc/user_guide.md`, `doc/user_guide_details.md`
- Roadmap статус → `doc/backlog_registry.yaml` (**SSoT**; `doc/tasklist.md` — DERIVED, не редактировать вручную)
  После правки в yaml: `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync`
  (fallback: `python` / `py`, если `.venv` недоступен).
- Архитектура → `doc/architecture.md`, `doc/conventions_architecture.md`
- Настройки → `.env.example`

Минимальный update при закрытии задачи: `doc/changelog.md` + `doc/backlog_registry.yaml`.

Checklist смены статуса пакета: `backlog_registry.yaml` → `closed_iterations.md` → `changelog.md` → затронутые `doc/user_stories/*.md` (`status` / `covered_by` / `closed_date`) → пересобрать `doc/user_stories_index.json`.

---

## Активный backlog

`doc/backlog_registry.yaml` — единственный источник истины о текущих задачах,
приоритете, owner'ах и статусах. `doc/tasklist.md` — производный weekly view,
генерируемый через `scripts/backlog_registry_lint.py --sync-from-index --write-sync`.
Детали закрытых итераций не дублируются в `tasklist` — см. `doc/closed_iterations.md`.

Правила backlog: `doc/roadmap_governance.md`.

---

## Источники истины

| Что | Где |
|-----|-----|
| Текущие задачи | `doc/backlog_registry.yaml` |
| Соглашения | `doc/conventions.md` |
| Закрытые итерации | `doc/closed_iterations.md` |
| ADR | `doc/adr.md` |

При конфликте: код и `backlog_registry.yaml` важнее производных markdown-файлов.

---

## Командный конвейер (Team Workflow)

Промпты ролей: `doc/team_workflow/`. Умный роутер: `scripts/workflow.py` (предпочитать ручному выбору) — см. [`doc/team_workflow/workflow_router.md`](doc/team_workflow/workflow_router.md). SSoT строк: [`scripts/workflow_strings.py`](scripts/workflow_strings.py).

Точки входа (все пути относительно `doc/team_workflow/`):

| Ситуация | Что запускать |
|---|---|
| Backlog пустой / нужно спланировать следующий | `generate_plan_next_prompt.md` |
| Активный пакет в `backlog_registry.yaml` (`ready`/`wip`) | `generate_orchestration_prompt.md` |
| Работа по `PACKAGE_ID` уже начиналась (`archive/team_artifacts/<ID>/`) | `generate_resume_prompt.md` |
| Полная цепочка аудита закрытых пакетов end-to-end | `run_audit_chain_prompt.md` |
| Аудит закрытых пакетов за период | `generate_audit_closed_packages_prompt.md` |
| Добивка DoD-покрытия по audit-группам | `generate_audit_packages_coverage_prompt.md` |
