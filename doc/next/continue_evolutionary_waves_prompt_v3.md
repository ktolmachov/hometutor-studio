# Continuation prompt v3 — evolutionary waves (SSoT-gated)

Продолжи реализацию волн из серии эволюционных разборов.

Контекст:
- Runtime-репозиторий: D:\Projects\hometutor
- Studio/backlog-документы: D:\Projects\hometutor-studio
- Индекс серии: D:\Projects\hometutor-studio\doc\presentations\evolutionary_analyses\README.md
- Detail-plan'ы лежат в D:\Projects\hometutor-studio\doc\next\

## Шаг 0 — состояние репозитория (обязательно перед всем остальным)

Выполни `git status` (и при необходимости `git diff --stat`) в `D:\Projects\hometutor`.

- Если рабочее дерево грязное (staged/unstaged/untracked изменения), а объяснения этому
  нет в текущем `current_task.md` — **это не твоя работа и не твой контекст**. Не строй
  поверх, не переписывай, не удаляй. Зафиксируй список изменённых/новых файлов отдельным
  пунктом в финальном отчёте сессии как «pre-existing uncommitted state, requires owner
  decision» — и переходи к шагу 1 как обычно (грязное дерево само по себе не блокирует
  анализ SSoT, но обязано быть явно назван, а не молча проигнорировано или молча принято
  за основу).
- Если дерево чистое — просто отметь это в финальном отчёте одной строкой.

## Шаг 1 — обязательное чтение

1. D:\Projects\hometutor\AGENTS.md
2. D:\Projects\hometutor\docs\conventions.md
3. D:\Projects\hometutor-studio\doc\presentations\evolutionary_analyses\README.md
4. SSoT studio при выборе следующего package:
   - D:\Projects\hometutor-studio\doc\backlog_registry.yaml
   - D:\Projects\hometutor-studio\doc\current_task.md
   - D:\Projects\hometutor-studio\doc\tasklist.md (при необходимости)
5. Связанный detail-plan выбранной волны из README (см. карту волн ниже).
6. Если по итогам анализа тебе нужно вывести «точную команду/шаг для активации через
   штатный workflow» — источник этой команды: `D:\Projects\hometutor-studio\scripts\workflow.py`
   (прочитай его usage/`--help`/docstring) и любые файлы `doc/team_workflow/*`, если они
   существуют в этом checkout. Не выдумывай синтаксис команды — бери его из скрипта.

## Важно

- README — индекс разборов, а не SSoT исполнения.
- Detail-plan'ы — каталог кандидатов, не разрешение на runtime-изменения.
- Не объявляй runtime snapshot из разборов shipped/accepted без проверки SSoT.
- Не реализуй proposed-кандидата напрямую, если он не принят workflow'ом.
- **Если active/accepted package нет — STOP**: не меняй runtime-код, верни shortlist
  следующей волны и точную команду/шаг для активации через штатный workflow (см. шаг 1.6).
- **Если current_task.md указывает на другой package — STOP**: не меняй runtime-код,
  объясни расхождение и верни точный следующий шаг.
- Если package уже active/accepted и есть current_task.md — реализуй только этот package,
  не весь wave.
- Write-set соблюдать строго. Не делать попутный рефакторинг.
- Runtime-docs обновлять только если изменился публичный API, UI-поведение, архитектура,
  config или persistence.
- Python-команды в D:\Projects\hometutor запускать только через:
  - `.\.venv\Scripts\python.exe -m pytest` — targeted-тесты по затронутым зонам (только их,
    не полный сьют).
  - `.\.venv\Scripts\python.exe -m ruff check <изменённые файлы>` — разрешено и рекомендуется
    как финальная проверка write-set перед отчётом (не обязательно, если ruff недоступен в
    окружении — тогда просто отметь это в отчёте).
  Никаких других shell-команд, меняющих состояние (миграции БД, скрипты записи), без
  отдельного явного разрешения.

## Критичные инварианты реализации

(закреплены по итогам код-ревью предыдущих раундов — нарушение любого из них равно
дефекту, даже если тесты проходят)

- `mastery_vector` должен использовать только canonical concept id из active knowledge graph.
- Не писать в `mastery_vector` свободный текст, названия тегов, human topic title или имя файла.
- Если сигнал пришёл из tutor/flashcard, сначала сопоставь его с canonical cid; если cid не
  найден — не загрязняй `mastery_vector` (тихо пропусти запись, не изобретай fallback-ключ).
- `sessions_completed` = только завершённые учебные сессии (квиз). tutor/flashcard события
  считать отдельными interaction-счётчиками, не увеличивать `sessions_completed`.
- Не менять старую семантику quiz без явного задания: quiz может перезаписывать mastery
  score, включая понижение (не делать mastery монотонно неубывающим для quiz-пути).
- Не добавлять LLM там, где план требует deterministic/persistence/state update.
- Не добавлять новые экраны, если package требует невидимую state/persistence доработку.

## Карта волн (README, 2026-07-12)

1. **Knowledge Fate / петля памяти**
   plan: `doc/next/knowledge_fate_memory_loop_plan.md` · порядок: A1 → A2 → B2 → B1 → C1 → C2

2. **First Ten Minutes / onboarding**
   plan: `doc/next/first_ten_minutes_onboarding_plan.md` · порядок: A1 → A2 → B2 → B1 → B3 → C1 → C2

3. **Material as Product**
   plan: `doc/next/material_as_product_quality_plan.md` · порядок: A1 → A2 → B2 → B1 → C2 → C1

4. **Agent as One Button**
   plan: `doc/next/agent_as_one_button_plan.md` · порядок: A1 → A2 → B1 → B2 → C1
   Дополнительно сверить `D:\Projects\hometutor\docs\agent_roadmap.md`.

5. **Trust Under Load / provider**
   plan: `doc/next/trust_under_load_provider_plan.md` · порядок: A1 → A2 → B1 → C1

6. **Infographics / living map**
   plan: `doc/next/infographics_living_map_plan.md` · порядок: A1 → A2 → B1 → C1 → C2

7. **Learning Plan**
   plan: `doc/next/learning_plan_single_source_plan.md` · статус: A/B/C shipped, не начинать
   заново; только проверять, если SSoT явно указывает на follow-up.

8. **Invisible Half (метаразбор — не отдельная волна с собственным id)**
   plan: `doc/next/invisible_half_closure_plan.md`.
   **Важно про структуру:** это не каталог с собственными кандидатами A1/A2/wave-id, а
   синтез поверх уже существующих кандидатов волн №1 и №5. В `backlog_registry.yaml` нет и
   не должно быть записи `wave-invisible-half` — не ищи её. Реальные кандидаты на промоут:
   - «Ход 1 / След» = A1+A2 из `knowledge_fate_memory_loop_plan.md` (→ `wave-memory-loop-closure`)
   - «Ход 2 / Честность» = A1+A2 из `trust_under_load_provider_plan.md` (→ `wave-provider-circuit-honesty`)
   README/разбор №8 использовать как карту приоритетов и обоснование, не как SSoT.

## Задача сессии

1. Выполни шаг 0 (git status) и зафиксируй результат.
2. Определи, какая wave/package сейчас является следующей по SSoT (backlog_registry.yaml
   `active_wave_id` → `current_task.md`).
3. Если active/accepted package есть и совпадает с одной из волн 1–8 — реализуй ровно этот
   package в D:\Projects\hometutor.
4. Если active/accepted package нет, или он не связан ни с одной из волн 1–8, или есть
   расхождение с current_task.md — **остановись без runtime-изменений** и дай:
   - shortlist следующей волны/package (с обоснованием, почему она следующая по
     эффект/усилие и по README-приоритету);
   - точную команду/шаг для активации через штатный workflow (источник — шаг 1.6).
5. Обнови runtime-docs только при изменении публичного API, UI-поведения, архитектуры,
   config или persistence.
6. Запусти только затронутые тесты (+ ruff по изменённым файлам, если доступен).
7. В финале дай:
   - состояние рабочего дерева на старте (чистое / pre-existing uncommitted state — что
     именно);
   - выбранную wave/package и почему;
   - что было реализовано или почему STOP;
   - изменённые файлы;
   - тесты и их результат;
   - что осталось;
   - точную следующую команду/шаг для продолжения wave.
