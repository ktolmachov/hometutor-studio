# Адаптер: Claude Code

Файл читается `generate_orchestration_prompt.md` в Phase 3.
Содержит значения плейсхолдеров шаблона для Claude Code.

---

## Значения плейсхолдеров

```yaml
MAX_PARALLEL: 7

AGENT_SPAWN: |
  Use the Agent tool:
    Agent(
      subagent_type="general-purpose",
      model="claude-sonnet-4-6",
      description="<role>: <task>",
      prompt="""..."""
    )
  Role → model mapping (authoritative — see table below):
    PO, Analyst, Designer, Developer → claude-sonnet-4-6
    Architect                        → claude-opus-4-7
    Tester                           → claude-haiku-4-5-20251001
  Each Agent call runs in an isolated context window.
  Subagents cannot spawn their own subagents (max depth = 1).

PARALLEL_SYNTAX: |
  Launch BOTH agents in a SINGLE message (parallel execution).
  Put two Agent(...) calls in the same response — Claude Code runs them
  simultaneously. Do NOT send them in separate messages.

  Example for Step 3:
    [message contains two Agent tool calls simultaneously]
    Agent(subagent_type="Plan", model="claude-opus-4-7", description="Architect: ...", prompt="...")
    Agent(subagent_type="general-purpose", model="claude-sonnet-4-6", description="Designer: ...", prompt="...")

READ_FILE: |
  Use the Read tool:
    Read(file_path="path/to/file.md")
  Then INSERT the content inline into the next Agent's prompt string.
  Subagents do NOT automatically see parent context files —
  content must be embedded explicitly.
  For large files use: Read(file_path="...", offset=N, limit=M)

WRITE_FILE: |
  Use the Write tool:
    Write(file_path="archive/team_artifacts/.../artifact.md",
          content="...")
  Call Write immediately after the Agent completes — before the next step.

RUN_CMD: |
  Use the Bash tool directly in the subagent's prompt.
  Subagents spawned via Agent() receive full toolset, including Bash, Read, Glob, Grep.
  For Tester agents: add "You have Bash, Read, Glob, Grep tools." to the prompt header.
  Never assume test results without actual execution.
```

---

## Модели по ролям

| Роль | Модель | Причина |
|------|--------|---------|
| Product Owner | `claude-sonnet-4-6` | кросс-документный синтез + приоритизация: неверный пакет = 7 шагов впустую |
| Analyst | `claude-sonnet-4-6` | трассировка data flow по зрелой кодовой базе, edge cases, cross-cutting анализ |
| **Architect** | **`claude-opus-4-7`** | write-set контракт — ошибка планирования каскадирует на все шаги |
| Designer | `claude-sonnet-4-6` | понимание Streamlit-паттернов из кода, 4 состояния, коллизии session_state |
| Developer | `claude-sonnet-4-6` | реализация кода + дебаг тестов — Haiku ненадёжен с реальным кодом |
| Tester | `claude-haiku-4-5-20251001` | детерминированная проверка: git diff, pytest, структурный вердикт по DoD |

---

## Специфика передачи артефактов

Subagent изолирован — **не видит** файлы из контекста оркестратора автоматически.
Оркестратор должен:

1. `Read` артефакт предыдущей роли
2. Вставить содержимое **строкой прямо в `prompt=`**

Шаблон вставки в промпт:

```python
prev_artifact = Read("archive/team_artifacts/.../N_role_output.md").content

Agent(
  ...,
  prompt=f"""
    ...role instructions...

    Input from previous role:
    ===ARTIFACT===
    {prev_artifact}
    ===END===

    ...
  """
)
```

---

## Step 3: синтаксис параллельного запуска

```python
# Один message — два Agent tool calls одновременно:

Agent(
  subagent_type="Plan",
  model="claude-opus-4-7",
  description="Architect: contract {{PACKAGE_ID}}",
  prompt="""
    Role: Architect for home-rag_v2.
    Read: doc/team_workflow/architect.md
    [...]
    Save to: {{ARTIFACTS_DIR}}/3_architect_contract.md
  """
)

Agent(
  subagent_type="general-purpose",
  model="claude-sonnet-4-6",
  description="Designer: UI spec {{PACKAGE_ID}}",
  prompt="""
    Role: UX/UI Designer for home-rag_v2.
    Read: doc/team_workflow/designer.md
    [...]
    Save to: {{ARTIFACTS_DIR}}/4_designer_ui_spec.md
  """
)
# Оба вызова в одном ответе = параллельное выполнение
```

---

## Обработка FAIL вердикта

```python
verdict_file = Read("{{ARTIFACTS_DIR}}/6a_tester_sp1.md").content

if "VERDICT: PASS" in verdict_file:
    # continue to next step
elif "VERDICT: CONDITIONAL PASS" in verdict_file:
    # extract conditions block, show to user, ask to proceed
elif "VERDICT: FAIL" in verdict_file:
    # extract first line after "VERDICT: FAIL" — that is the blocker
    # show to user: "Blocker: <line>"
    # ask: "Re-run Developer? (y/n)"
    # if yes: re-run Step 4 Agent with blocker appended to prompt
```

---

## Ограничения Claude Code

| Ограничение | Влияние на оркестрацию |
|-------------|------------------------|
| Глубина агентов = 1 | Subagents не могут запускать Agent tool |
| Rate limit: 5-hour window | При длинном pipeline — возможен throttle |
| Context: 1M tokens | Практически не ограничивает |
| run_in_background | НЕ использовать для Developer/Tester — нужен output |
