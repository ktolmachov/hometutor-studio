# Командный AI-конвейер: инструкция для коллег

---

## Общие правила для промптов

Стандартные формулировки (Windows/PowerShell, SSoT, token budget, sync после реестра): [`_common_rules.md`](_common_rules.md).

## Быстрый старт — 2 команды

```bash
# 1. Посмотреть что делать прямо сейчас:
python scripts/workflow.py

# 2. Запустить следующий шаг:
python scripts/workflow.py --exec

# Без паузы на ревью YAML после plan-next → сразу генерация оркестрации:
python scripts/workflow.py --skip-review --exec

# Кондуктор (волна пакетов до closed; см. workflow_router.md — паузы IDE и контракт):
python scripts/workflow.py --loop --skip-review --watch-contract --agent cursor_ai
```

После паузы **`[PAUSE]`** или состояния **`ready_executing`**: выполните `doc/current_task.md` в IDE, создайте `archive/team_artifacts/<PACKAGE_ID>/execution_contract.md`, снова запустите ту же команду `--loop …`. Подробности и промпт для агента: [`workflow_router.md`](workflow_router.md#manual-ready-executing); канонический текст промпта — [`scripts/workflow_strings.py`](../../scripts/workflow_strings.py).

Если нужен конкретный агент: `python scripts/workflow.py --agent claude_code`  
Только статус без команды: `python scripts/workflow.py --status`  
Планирование без ручного ревью контракта: см. `--skip-review` в [`workflow_router.md`](workflow_router.md)

Полная документация роутера: [`workflow_router.md`](workflow_router.md)  
Подробный выбор: [`workflow_decision_tree.md`](workflow_decision_tree.md)

---

## Зачем это вообще нужно?

Когда вы работаете над проектом с AI-агентом (Claude, Codex, Cursor),
вы обычно делаете это так:

> "Эй, сделай мне фичу X."

Агент начинает что-то делать, спрашивает уточнения, уходит не в ту сторону,
пишет код в не тех файлах, забывает про тесты, не обновляет документацию.
Потом вы это чините, потом снова просите...

**Эта система решает другую задачу:**
вместо одного агента, которому вы объясняете всё с нуля каждый раз,
здесь работает **команда специализированных агентов** по чёткому процессу —
как настоящая команда разработки.

---

## Кому это полезно?

**Вам подойдёт, если:**

- Вы используете Claude Code, Cursor AI или Codex для разработки
- Ваш проект уже живёт больше месяца и у него есть backlog
- Вы хотите, чтобы агент понимал контекст задачи, а не просто "писал код"
- Вы устали объяснять одно и то же при каждом новом чате

**Особенно полезно:**

- Разработчик-одиночка, который хочет работать как мини-команда
- Небольшая команда (2–4 человека), где каждый носит несколько шляп
- Тимлид, который хочет делегировать рутинные части процесса агентам

---

## Как это работает — за 2 минуты

Представьте, что у вас есть команда из 6 специалистов:

```
Владелец продукта  →  Аналитик  →  Архитектор
                                        ↓
Тестировщик       ←  Разработчик  ←  Дизайнер
```

Каждый делает свою часть работы и передаёт результат следующему.
Никто не лезет в чужую зону. Тестировщик не пропускает плохой код.

**В этой системе каждую роль играет AI-агент** с заточенным промптом.
А вы — только **запускаете процесс** и **принимаете решения** на переломных моментах.

---

## Куда нажать первым делом

- Product Owner роутер для выбора planning/ideation/package/wave шага: [`product_owner_router.md`](product_owner_router.md)
- Дерево решений «какой промпт сейчас»: [`workflow_decision_tree.md`](workflow_decision_tree.md)
- Полный процесс и таблица этапов: [`process.md`](process.md)
- Проверка markdown-артефактов пайплайна: `npm run validate:team-artifacts -- --artifacts-dir archive/team_artifacts/<PACKAGE_ID>` (или `scripts/validate_team_artifact.py`)

---

## Три шага чтобы начать

### Шаг 1. Скажите агенту запустить генератор

Откройте ваш AI-агент (Claude Code, Cursor, Codex) и напишите:

```
Прочитай doc/team_workflow/generate_orchestration_prompt.md
TARGET_AGENT: claude_code
```

Вместо `claude_code` укажите ваш инструмент:
- `claude_code` — если используете Claude Code CLI
- `cursor_ai` — если работаете в Cursor AI
- `codex` — если используете OpenAI Codex CLI

### Шаг 2. Получите готовый промпт

Агент сам:
- Найдёт следующую задачу в вашем `doc/backlog_registry.yaml`
- Разберётся с контекстом (CJM, user stories, acceptance criteria)
- Сгенерирует полный промпт оркестратора под ваш инструмент

Если активных задач нет — предложит следующую из roadmap и спросит подтверждения.

### Шаг 3. Запустите сгенерированный промпт

Скопируйте результат и вставьте в **новый чат** вашего агента.
Дальше агент-оркестратор ведёт процесс сам, шаг за шагом.

---

## Что происходит внутри

Оркестратор последовательно запускает 8 шагов:

| Шаг | Роль | Что делает |
|-----|------|-----------|
| 1 | **Владелец продукта** | Берёт задачу из backlog, привязывает к CJM и user story |
| 2 | **Аналитик** | Расписывает сценарии (что дано / что делает пользователь / что происходит) |
| 3 | **Архитектор + Дизайнер** | Решают *как* делать: какие файлы трогать, как выглядит UI |
| 4 | **Разработчик** | Пишет код строго по контракту Архитектора |
| 5 | **Тестировщик** | Проверяет код: тесты, scope, качество. Выдаёт PASS или FAIL |
| 6–7 | **Разработчик + Тестировщик** | Если задача делится на части — повторяют для второй части |
| 8 | **Закрытие** | Обновляет документацию, changelog, backlog |

Вы вмешиваетесь только когда:
- Тестировщик говорит **FAIL** — нужно решить, фиксить или отложить
- Что-то непонятно аналитику или архитектору — нужна ваша экспертиза
- Нет активных задач — нужно подтвердить следующую

---

## Ключевая польза

### 1. Агент знает контекст вашего проекта

Вместо "напиши фичу X" — агент читает:
- Что уже сделано (закрытые итерации)
- Каким правилам следовать (conventions)
- Что важно для пользователя (CJM, user stories)
- Что нельзя ломать (регрессионные тесты)

### 2. Каждая роль делает только своё

Архитектор не пишет код. Разработчик не придумывает что делать.
Тестировщик не правит код — только находит проблему и возвращает разработчику.
Это устраняет главный баг AI-агентов: "сделал слишком много лишнего".

### 3. Качество встроено в процесс

Тестировщик обязан запустить реальные команды (`pytest`, `git diff`).
Он не может сказать "наверное всё хорошо" — только `PASS` или `FAIL` с доказательством.

### 4. Работает в любом инструменте

Один шаблон — три реализации: Claude Code, Cursor AI, Codex CLI.
Сменили инструмент? Поменяйте `TARGET_AGENT` в одной строке.

### 5. Артефакты сохраняются

Каждый шаг сохраняет результат в `archive/team_artifacts/<задача>/`.
Через месяц вы сможете понять, почему было принято то или иное решение.

---

## Что делать если агент остановился на середине?

Бывает: кончился контекст, тестировщик сказал FAIL, или вы хотите
передать задачу другому агенту или коллеге.

Вместо того чтобы объяснять всё с нуля, запустите **resume-генератор**:

```
Прочитай doc/team_workflow/generate_resume_prompt.md
TARGET_AGENT: claude_code
PACKAGE_ID: E15-A
```

Он сам:
- Найдёт папку `archive/team_artifacts/E15-A/` и проверит какие артефакты уже есть
- Определит с какого шага продолжать
- Если тестировщик вернул FAIL — извлечёт конкретный blocker
- Вшьёт все нужные артефакты как контекст в новый промпт
- Выдаст готовый промпт для вставки в агент

**Правило выбора:**

| Ситуация | Что запускать |
|----------|-------------|
| Владелец продукта не уверен: ideation, package, roadmap waves или execution? | [`product_owner_router.md`](product_owner_router.md) |
| Backlog пустой / все пакеты закрыты / нужно спланировать следующий | `generate_plan_next_prompt.md` |
| Plan-next вернул `blocker: no eligible plan-next candidate…` — нужен **один** согласованный package без автозаписи в реестр | [`product_owner_plan_package_prompt.md`](product_owner_plan_package_prompt.md) |
| Нужна **таблица** возможных направлений из CJM / user stories / roadmap перед выбором работы | [`generate_breakthrough_ideation_prompt.md`](generate_breakthrough_ideation_prompt.md) (`MODE=CANDIDATE_TABLE`, см. § «Как использовать») |
| Нужны **много** прорывных идей по уже выбранному TARGET (линзы, best practices, артефакт с диффами) | [`generate_breakthrough_ideation_prompt.md`](generate_breakthrough_ideation_prompt.md) (`TARGET` + `N_IDEAS`) |
| Есть ideation artifact и owner хочет оформить 3+ связанные идеи как волну | [`generate_roadmap_epoch_waves_prompt.md`](generate_roadmap_epoch_waves_prompt.md) |
| Есть активный пакет в `backlog_registry.yaml` (`ready`/`wip`) | `generate_orchestration_prompt.md` |
| Работа по `PACKAGE_ID` уже начиналась (есть `archive/team_artifacts/<ID>/`) | `generate_resume_prompt.md` |
| Нужно провести всю цепочку аудита закрытых пакетов end-to-end | `run_audit_chain_prompt.md` |
| Аудит закрытых пакетов за период (месяц, диапазон месяцев или дат) / верификация SSoT | `generate_audit_closed_packages_prompt.md` |
| Добить недостающее unit/e2e DoD-покрытие по уже созданным audit-группам | `generate_audit_packages_coverage_prompt.md` |
| Вручную переоткрыть **один** закрытый пакет (Step C, SSoT) без полного аудита | [`reopen_package_step_c_prompt.md`](reopen_package_step_c_prompt.md) · префлайт [`../scripts/print_reopen_package_workflow.py`](../scripts/print_reopen_package_workflow.py) |
| Полный refresh demo (YAML, Playwright demo specs, screenshots, `quickstart_demo.md`) | [`demo_scenarios_prompt_bundle.md`](demo_scenarios_prompt_bundle.md) |

**Почему шесть входов, а не один:**
Помимо них в той же таблице — ветки после блокера plan-next и для ideation (`product_owner_plan_package_prompt`, `generate_breakthrough_ideation_prompt`): они **не** заменяют шесть входов, а дают путь, пока в `backlog_registry.yaml` ещё нет принятого следующего контракта.
Планирование и исполнение разделены намеренно. `generate_plan_next_prompt` предлагает 1–3 кандидата с ranking и пишет контракт в `backlog_registry.yaml`, затем регенерирует `tasklist.md` — и останавливается до исполнения. `generate_orchestration_prompt` не планирует, он запускает оркестрацию по уже принятому контракту. Это снижает риск: человек ревьюит контракт до того, как агент начнёт писать код. `generate_audit_closed_packages_prompt` — периодическая верификация уже закрытых пакетов по параметру **`PERIOD`** (в т.ч. не только календарный месяц) с возможностью автоматического reopen/revert при FAIL/STALE. `generate_audit_packages_coverage_prompt` — отдельный шаг после группировки аудита: он проверяет полноту unit/e2e покрытия по связке package ↔ CJM ↔ US и добавляет только недостающие тесты/DoD-команды.
`run_audit_chain_prompt` — мастер-вход для всей audit-цепочки, когда нужно не просто сгенерировать один prompt, а довести состояние до согласованных audit prompt, group files, coverage prompt, reports, `_audit_raw.json` и `coverage_dod_analysis.md`.

### Цепочка аудита закрытых пакетов

Мастер-вход: [`run_audit_chain_prompt.md`](run_audit_chain_prompt.md).

1. Запустить [`generate_audit_closed_packages_prompt.md`](generate_audit_closed_packages_prompt.md) с `TARGET_AGENT`, `PERIOD`, `DEPTH`, `SCOPE`.
2. Выполнить сгенерированный `audit_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md`: он проверяет SSoT/DoD replay и создаёт audit-группы.
3. Проверять связанные пакеты безопасно через `doc/team_workflow/audit_groups_${PERIOD_SLUG}_${TARGET_AGENT}/group_*.md`.
4. Запустить [`generate_audit_packages_coverage_prompt.md`](generate_audit_packages_coverage_prompt.md), если нужно отдельным проходом добить тестовое покрытие.
5. Выполнить сгенерированный `audit_coverage_prompt_${PERIOD_SLUG}_${TARGET_AGENT}.md`: он пишет group coverage reports, обновляет `_audit_raw.json` и refresh `coverage_dod_analysis.md`.

---

## Часто задаваемые вопросы

**Q: Нужно ли всё настраивать с нуля?**

Нет. Для нового проекта достаточно иметь:
- `doc/backlog_registry.yaml` с хотя бы одной задачей; `doc/tasklist.md` можно генерировать из него
- `doc/cjm.md` с описанием пути пользователя
- `doc/user_stories/` с acceptance criteria

Если файлов нет — агент скажет какие создать.

---

**Q: Я работаю один, зачем мне 6 ролей?**

Потому что один человек (и один агент) совмещает все роли и теряет фокус.
Когда вы в режиме "разработчика", вы думаете о коде, а не о том, правильно ли
понята задача. Разделение ролей помогает думать об одной вещи за раз —
даже если все роли выполняет один агент последовательно.

---

**Q: А если агент сделает что-то не то?**

Процесс построен так, что плохой результат не проходит дальше.
Тестировщик блокирует некачественный код. Разработчик не может выйти
за пределы написанного Архитектором контракта. Аналитик не может придумать
требования — только детализировать то, что сказал Владелец продукта.

Каждый шаг — это checkpoint, а не слепое доверие агенту.

---

**Q: Cursor AI vs Claude Code — что лучше?**

| Если вам важно... | Возьмите |
|-------------------|---------|
| Работать прямо в IDE без переключений | Cursor AI |
| Параллельно запускать Архитектора и Дизайнера в одной команде | Claude Code или Cursor AI |
| Максимальный контекст (большой проект) | Claude Code (1M токенов) |
| Последовательная надёжность без сюрпризов | Codex CLI |

---

**Q: Что делать если агент "сломался" на середине?**

Каждый шаг сохраняет артефакт в файл. Можно перезапустить с любого шага,
прочитав нужный артефакт. Не нужно начинать с нуля.

---

## Файловая структура (для ориентации)

```
doc/backlog_registry.yaml            ← structured backlog SSoT for plan_next/orchestration
scripts/backlog_registry_lint.py     ← schema linter (exit 0 OK / 1 WARN / 2 FAIL)
doc/team_workflow/
  README.md                          ← вы здесь

  # — Входы в процесс (генераторы промптов) —
  workflow_router.md                 ← ⭐ единая точка входа: python scripts/workflow.py
  generate_plan_next_prompt.md       ← backlog пустой: предлагает 1–3 кандидата, пишет контракт
  generate_orchestration_prompt.md   ← контракт есть: генерирует промпт оркестрации
  generate_resume_prompt.md          ← работа идёт: подхватывает где остановились
  run_audit_chain_prompt.md          ← мастер-промпт всей audit/coverage цепочки
  generate_audit_closed_packages_prompt.md  ← аудит закрытых пакетов / верификация SSoT
  generate_audit_packages_coverage_prompt.md ← DoD coverage prompt по audit-группам
  reopen_package_step_c_prompt.md    ← один пакет: closed → ready (Step C)
  demo_scenarios_prompt_bundle.md    ← обновление demo-сценариев и quickstart

  # — Шаблоны и адаптеры —
  orchestrator_template.md           ← шаблон промпта (с плейсхолдерами)
  guides/agent_adapter_claude_code.md       ← адаптер для Claude Code
  guides/agent_adapter_codex.md             ← адаптер для Codex
  guides/agent_adapter_cursor_ai.md         ← адаптер для Cursor AI

  # — Роли —
  process.md                         ← описание всего процесса (подробно)
  product_owner.md                   ← промпт для роли PO
  analyst.md                         ← промпт для роли Аналитик
  architect.md                       ← промпт для роли Архитектор
  designer.md                        ← промпт для роли Дизайнер
  developer.md                       ← промпт для роли Разработчик
  tester.md                          ← промпт для роли Тестировщик

  # — Примеры —
  examples/
    example_flashcards_and_bugfix.md
    example_e15a_orchestration_level3_in_agent_claude_code.md
    example_e15a_orchestration_level3_in_agent_codex.md
    example_e15a_orchestration_level3_in_agent_cursor_ai.md

  # — SSR AI Vision —
  ssr_ai_vision/
    ssr_ai_vision_summary.md
    ssr_ai_vision_level1_prompt.md ... ssr_ai_vision_level5_prompt.md
    ssr_*_quick_start.md, ssr_*_audit_*.md, ssr_code_templates.md

  # — Живые operational guides —
  guides/
    workflow_cursor_sdk_trigger_guide.md
    workflow_deepseek_api_trigger_guide.md

  # — Архивные снимки внутри workflow —
  archive/
    audit_prompt_epic20-smart-study-router_codex.md
    audit_coverage_prompt_epic20-smart-study-router_codex.md
    epoch_demo_post_agent_smoke.md
    zero_click_delivery_analysis.md
    product_owner_router_ai_vision_enhancement.md

archive/doc_team_workflow/           ← legacy-архив вне корня workflow; north star: ≤48 `*.md` в корне `doc/team_workflow/` без подкаталогов
archive/team_workflow_snapshots/     ← одноразовые audit-снимки (не для навигации)
```

---

## Быстрый старт одной командой

```
Прочитай doc/team_workflow/generate_orchestration_prompt.md
TARGET_AGENT: claude_code
```

Вставьте в ваш агент. Он сделает остальное.

---

*Если что-то непонятно или не работает — смотрите живой пример:
`doc/team_workflow/examples/example_flashcards_and_bugfix.md`*
