# Адаптер: Cursor AI

Файл читается `generate_orchestration_prompt.md` в Phase 3.
Содержит значения плейсхолдеров шаблона для Cursor AI (Composer / Agent mode).

---

## Значения плейсхолдеров

```yaml
MAX_PARALLEL: 8

AGENT_SPAWN: |
  Cursor AI не имеет программного Agent tool как у Claude Code.
  Два варианта:
  A) Agents Window (Cursor 3): View → Agents → New Agent
     Каждый агент — отдельный Composer window в изолированном git worktree.
  B) Один Composer window: один агент последовательно меняет роль
     (менее предпочтительно, но проще).
  Рекомендация: Agents Window для Step 3 (parallel), Composer для остальных.

PARALLEL_SYNTAX: |
  Открыть Agents Window (View → Agents или Ctrl+Shift+A).
  По одному "New Agent" на каждую роль.
  Вставить промпт каждого агента в соответствующее окно.
  Дождаться Complete в окнах Agents Window.
  Затем вернуться в основной Composer window и продолжить.

READ_FILE: |
  @filename синтаксис в Composer:
    @doc/team_workflow/architect.md
    @doc/conventions.md
    @app/flashcard_service.py
  Для конкретных строк:
    @app/user_state.py:280-350
  Для семантического поиска по всему codebase:
    @codebase (использовать осторожно — дорого по токенам)
  Читать только нужные файлы — контекст 200K жёсткий.

WRITE_FILE: |
  Cursor сохраняет файлы через IDE:
  - Попросить агента "Save to: path/file.md" — Cursor предложит создать файл
  - Для артефактов: Run in terminal:
      mkdir -p archive/team_artifacts/{{PACKAGE_ID}}
      # агент пишет через IDE edit

RUN_CMD: |
  Встроенный терминал Cursor (Ctrl+` ):
    python -m pytest tests/test_flashcard_service.py -v
    git diff --name-only HEAD~5..HEAD
    grep -n "pattern" app/module.py
  Агент может запускать команды напрямую через terminal tool.
```

---

## Step 3: параллельный запуск в Agents Window

```text
═══ ОТКРЫТЬ AGENTS WINDOW ══════════════════════════════════════

View → Agents (или Ctrl+Shift+A)

═══ АГЕНТ 1: Architect ═════════════════════════════════════════
Нажать "New Agent" → назвать "{{PACKAGE_ID}} Architect"

Вставить:
  @doc/team_workflow/architect.md
  @archive/team_artifacts/{{PACKAGE_ID}}/2_analyst_spec.md
  @doc/conventions.md
  @doc/conventions_architecture.md
  @doc/adr.md
  @app/<target modules>
  @tests/test_<relevant>.py

  Act as Architect. Execute Prompt 1 from @doc/team_workflow/architect.md.
  [... instructions ...]
  Save to: archive/team_artifacts/{{PACKAGE_ID}}/3_architect_contract.md

═══ АГЕНТ 2: Designer ══════════════════════════════════════════
Нажать "New Agent" → назвать "{{PACKAGE_ID}} Designer"

Вставить:
  @doc/team_workflow/designer.md
  @archive/team_artifacts/{{PACKAGE_ID}}/2_analyst_spec.md
  @doc/cjm.md
  @app/ui/<target UI files>
  @app/ui_theme.css

  Act as Designer. Execute Prompt 1 from @doc/team_workflow/designer.md.
  [... instructions ...]
  Save to: archive/team_artifacts/{{PACKAGE_ID}}/4_designer_ui_spec.md

═══ ДОЖДАТЬСЯ COMPLETE В ОБОИХ ОКНАХ ══════════════════════════
═══ ВЕРНУТЬСЯ В ОСНОВНОЙ COMPOSER ══════════════════════════════
```

---

## Специфика передачи артефактов

В отличие от Claude Code, агенты Cursor видят **общую файловую систему**
(через общий или worktree-based git). Артефакты не нужно вставлять inline.

Вместо этого — `@` ссылки в следующем шаге:

```
# Step 4 (Developer) получает артефакты Step 3 через:
@archive/team_artifacts/{{PACKAGE_ID}}/3_architect_contract.md
@archive/team_artifacts/{{PACKAGE_ID}}/4_designer_ui_spec.md
```

---

## Управление контекстом (200K лимит)

| Ситуация | Действие |
|----------|---------|
| Контекст заполняется | `/compact` или новый Composer window |
| Большой файл (user_state.py ~800 строк) | `@user_state.py:280-350` (только нужные строки) |
| Семантический поиск нужен | `@codebase` — но ограниченно, дорого |
| Много файлов в Step 3 | Разбить на Architect (6 файлов) + Designer (5 файлов) |

Правило: держать контекст одного шага в пределах ~50K токенов.
Расчёт: 200K / 4 шага = ~50K на шаг.

---

## Multi-file edit (Step 8: Closure)

Cursor умеет редактировать несколько файлов в одном ответе.
Для Step 8 укажи все три doc-файла явно:

```
Apply these changes to close {{PACKAGE_ID}}:

@doc/backlog_registry.yaml — статус/closure; затем lint/sync derived по канону [doc/team_workflow/_common_rules.md](_common_rules.md)
@doc/changelog.md — add entry at top
@doc/closed_iterations.md — add closure block

[instructions for each file]
```

Cursor предложит `Apply All` — атомарное применение всех изменений.

---

## Обработка FAIL вердикта

```text
After Step 5 Tester completes, read:
@archive/team_artifacts/{{PACKAGE_ID}}/6a_tester_sp1.md

If contains "VERDICT: PASS" → continue to Step 6
If contains "VERDICT: CONDITIONAL PASS":
  Show conditions block to user.
  Ask: "Proceed to sp2? (y/n)"
If contains "VERDICT: FAIL":
  Extract the first line under "VERDICT: FAIL" — that is the blocker.
  Show to user: "Blocker: <line>"
  Ask: "Re-run Developer with this fix? (y/n)"
  If yes: re-run Step 4 with the blocker appended.
```

---

## Ограничения Cursor AI

| Ограничение | Влияние на оркестрацию |
|------------|------------------------|
| Контекст 200K (жёсткий) | Не добавлять лишние @files; читать части файлов |
| Composer 1.5 (не frontier) | Архитектурные решения могут требовать уточнений |
| Agents Window — flat peers | Нет родителя: агенты не координируют сами себя |
| Worktree isolation | Артефакты доступны через общую FS после записи |
| Нет программного Agent tool | Параллелизм через ручной Agents Window |

---

## SDK Trigger Integration

`cursor_agent_trigger.ts` использует Cursor TypeScript SDK (`@cursor/sdk`) для программного вызова агента из `trigger_orchestrator.ts`. Поток:

```
trigger_orchestrator.ts
  → spawnSync("npx tsx scripts/cursor_agent_trigger.ts", [taskPath])
    → Agent.prompt(taskContent, { local: { cwd }, model: "composer-2" })
    → ждёт execution_contract.md (started stall guard: CURSOR_TRIGGER_STARTED_STALL_TIMEOUT_MS)
    → пишет метрики в trigger_metrics.jsonl
    → exit code: 0 (finished) | 1 (error) | 3 (stall/transient)
```

Оркестратор читает exit code и метрики для routing:
- exit 0 → success, переходим к post-agent
- exit 1 с deterministic prefix → не retry, не fallback на cursor
- exit 3 (started_stall) → deterministic, оркестратор fallback на DeepSeek TUI

### Adaptive Demotion

Если cursor success rate в последних N метриках `trigger_orchestrator` < 40%, `creds.cursor` устанавливается в `false`. В этом случае:
- cursor не выбирается как primary trigger (стратегия деградирует до `direct_deepseek_tui`)
- cursor не используется как fallback (даже если `rawCreds.cursor = true`)
- метрики записывают `credentials_effective.cursor: false` и `adaptive_adjustments.cursor_demoted: true`

Для сброса demotion — нужно несколько успешных cursor итераций (rate поднимется выше порога).

---

## Cursor Rules (`.cursor/rules/`)

Проект уже имеет:
- `.cursor/rules/conventions.mdc` — always-on правила кода
- `.cursor/rules/workflow.mdc` — always-on правила процесса

Оба применяются автоматически к каждому Composer / Agents Window запросу.
Промпт оркестратора не должен дублировать их содержимое —
только ссылаться на файлы ролей `doc/team_workflow/<role>.md`.
