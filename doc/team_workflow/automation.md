# Автоматизация командного процесса

Актуализировано: **2026-05-03**

## Обзор

Этот документ описывает, как автоматизировать конвейер ролей из [`process.md`](process.md) с помощью AI-агентов (Claude Code, Cursor, или аналогичных). Каждая роль реализуется как отдельный агентский поток с заточенным промптом.

**Следующий шаг без матрицы решений:** [`workflow_router.md`](workflow_router.md) — обёртка над `scripts/workflow.py` (в т.ч. кондуктор `--loop --skip-review --watch-contract`). Формулировки промпта для агента в консоли роутера — единый источник в [`../../scripts/workflow_strings.py`](../../scripts/workflow_strings.py).

## Архитектура автоматизации

```
┌─────────────────────────────────────────────────────────┐
│                    Оркестратор (Human)                   │
│  Запускает роли последовательно, проверяет handoff'ы    │
└──────────┬──────────────────────────────────────────────┘
           │
           │  1. Запуск PO
           v
┌──────────────────┐    artifact: package.md
│  Agent: PO       │────────────────────────┐
│  prompt: PO #1   │                        │
└──────────────────┘                        v
                                 ┌──────────────────┐    artifact: spec.md
                                 │  Agent: Analyst   │──────────────┐
                                 │  prompt: AN #1    │              │
                                 └──────────────────┘              v
                                              ┌────────────────────────────────┐
                                              │        Параллельно:            │
                                              │  ┌──────────────────┐          │
                                              │  │ Agent: Architect │ contract │
                                              │  │ prompt: AR #1    │──────┐   │
                                              │  └──────────────────┘      │   │
                                              │  ┌──────────────────┐      │   │
                                              │  │ Agent: Designer  │ ui   │   │
                                              │  │ prompt: DS #1    │──┐   │   │
                                              │  └──────────────────┘  │   │   │
                                              └────────────────────────┼───┼───┘
                                                                       v   v
                                                            ┌──────────────────┐
                                                            │  Agent: Developer │
                                                            │  prompt: DEV #1   │
                                                            └────────┬─────────┘
                                                                     │ code + tests
                                                                     v
                                                            ┌──────────────────┐
                                                            │  Agent: Tester   │
                                                            │  prompt: TST #1  │
                                                            └────────┬─────────┘
                                                                     │
                                                              PASS ──┤── FAIL
                                                                     │     │
                                                                 closure   │
                                                                     back to DEV
```

## Уровни автоматизации

### Уровень 1: Ручная оркестрация (текущий)

**Как работает:** человек копирует промпт роли, вставляет в агент, получает артефакт, передаёт следующей роли.

**Реализация:**

1. Открыть новый чат / поток агента.
2. Вставить промпт из файла роли (например, `product_owner.md` → Промпт 1).
3. Заполнить параметры (`<PACKAGE_ID>`, входные данные от предыдущей роли).
4. Получить артефакт.
5. Проверить артефакт (human review).
6. Открыть новый чат для следующей роли с артефактом предыдущей.

**Плюсы:** полный контроль, можно корректировать на каждом шаге.
**Минусы:** ручное копирование, риск потери контекста между шагами.

**Чеклист для каждого шага:**

```
□ Промпт скопирован из файла роли
□ Параметры заполнены (package ID, входные данные)
□ Агент работает в отдельном потоке (не в потоке предыдущей роли)
□ Артефакт получен и проверен
□ Артефакт сохранён (для передачи следующей роли)
□ Следующая роль запущена с артефактом
```

### Уровень 2: Скриптовая оркестрация

**Как работает:** скрипт автоматизирует последовательность вызовов ролей через Claude API или Claude Code CLI.

**Реализация:**

```bash
#!/bin/bash
# scripts/run_team_pipeline.sh
#
# Использование: ./scripts/run_team_pipeline.sh <package-id>
#
# Требует: claude CLI в PATH, настроенный API ключ

PACKAGE_ID="$1"
ARTIFACTS_DIR="archive/team_artifacts/${PACKAGE_ID}"
mkdir -p "$ARTIFACTS_DIR"

echo "=== Phase 1: Product Owner ==="
claude --print \
  --system-prompt "$(cat doc/team_workflow/product_owner.md)" \
  "Execute Prompt 1: Planning next package. Package ID: ${PACKAGE_ID}" \
  > "${ARTIFACTS_DIR}/1_po_package.md"

echo "=== Phase 2: Analyst ==="
claude --print \
  --system-prompt "$(cat doc/team_workflow/analyst.md)" \
  "Execute Prompt 1: Detail specification.
   Package ID: ${PACKAGE_ID}
   Input from PO:
   $(cat ${ARTIFACTS_DIR}/1_po_package.md)" \
  > "${ARTIFACTS_DIR}/2_analyst_spec.md"

echo "=== Phase 3+4: Architect + Designer (parallel) ==="
claude --print \
  --system-prompt "$(cat doc/team_workflow/architect.md)" \
  "Execute Prompt 1: Execution contract.
   Package ID: ${PACKAGE_ID}
   Analyst spec:
   $(cat ${ARTIFACTS_DIR}/2_analyst_spec.md)" \
  > "${ARTIFACTS_DIR}/3_architect_contract.md" &
PID_ARCH=$!

claude --print \
  --system-prompt "$(cat doc/team_workflow/designer.md)" \
  "Execute Prompt 1: UI specification.
   Package ID: ${PACKAGE_ID}
   Analyst spec:
   $(cat ${ARTIFACTS_DIR}/2_analyst_spec.md)" \
  > "${ARTIFACTS_DIR}/4_designer_ui_spec.md" &
PID_DESIGN=$!

wait $PID_ARCH $PID_DESIGN

echo "=== Phase 5: Developer ==="
claude \
  "Execute the developer role.
   Package ID: ${PACKAGE_ID}
   Execution contract:
   $(cat ${ARTIFACTS_DIR}/3_architect_contract.md)
   UI specification:
   $(cat ${ARTIFACTS_DIR}/4_designer_ui_spec.md)"
# Developer writes code interactively — no --print

echo "=== Phase 6: Tester ==="
COMMIT_RANGE=$(git log --oneline -10 | tail -1 | cut -d' ' -f1)..HEAD
claude --print \
  "Execute the tester role.
   Package ID: ${PACKAGE_ID}
   Contract: ${ARTIFACTS_DIR}/3_architect_contract.md
   COMMIT_RANGE: ${COMMIT_RANGE}
   PACKAGE_TYPE: mixed" \
  > "${ARTIFACTS_DIR}/6_tester_verdict.md"

echo "=== Pipeline complete ==="
echo "Artifacts in: ${ARTIFACTS_DIR}"
echo "Verdict: $(head -5 ${ARTIFACTS_DIR}/6_tester_verdict.md)"
```

**Плюсы:** воспроизводимость, артефакты сохраняются, параллелизм Architect+Designer.
**Минусы:** нет human-in-the-loop между шагами (нужно добавить паузы при необходимости).

### Уровень 3: Агентная оркестрация через Claude Code

**Как работает:** мета-агент (Claude Code) управляет подагентами, передавая артефакты между ними.

**Реализация через Agent tool:**

```text
Промпт для мета-оркестратора:

You are a team orchestrator for hometutor. Your job is to run the
team pipeline for package <PACKAGE_ID>.

The team workflow is described in doc/team_workflow/process.md.
Role prompts are in doc/team_workflow/<role>.md.

Execute these steps:
1. Launch Agent with PO role prompt → get package definition
2. Launch Agent with Analyst role prompt + PO output → get specification
3. Launch TWO Agents in parallel:
   a. Architect role prompt + Analyst output → execution contract
   b. Designer role prompt + Analyst output → UI specification
4. Launch Agent with Developer role prompt + contract + UI spec → code
5. Launch Agent with Tester role prompt + contract + commit range → verdict

After each step, review the output before proceeding.
If any step produces an escalation, pause and ask the user.

Prompt sync guard (Architect review prompt):
- Before running Architect Prompt 2, run:
  `python scripts/sync_architecture_review_prompt.py --check`
- If out of sync, run:
  `python scripts/sync_architecture_review_prompt.py`

Save all artifacts to archive/team_artifacts/<PACKAGE_ID>/.
```

**Плюсы:** полная автоматизация в одном сеансе, параллелизм через Agent tool.
**Минусы:** большой расход контекста, нужен human review между шагами.

### Уровень 4: CI/CD интеграция

**Как работает:** pipeline запускается автоматически при определённых событиях.

**Триггеры:**

| Событие | Что запускается |
|---------|----------------|
| PO обновил `backlog_registry.yaml` с новым пакетом | Analyst → Architect → Designer |
| Developer создал PR | Tester (verify + regression) |
| Epoch closed | Architect (architecture review) |
| Bi-weekly schedule | PO (backlog prioritization) |
| Merge >10 files | Architect (coupling + anti-patterns check) |

**GitHub Actions workflow (концепт):**

```yaml
# .github/workflows/team_verify.yml
name: Team Verify on PR

on:
  pull_request:
    branches: [main]

jobs:
  tester:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run regression suite
        run: |
          python -m pytest tests/ --tb=short --junitxml=test-results.xml
      
      - name: Run eval gates
        run: |
          python scripts/run_eval_loop.py --profile ci \
            --report-json eval_report.json
      
      - name: AI Tester review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude --print \
            "Role: Tester. Verify this PR.
             Changed files: $(git diff --name-only origin/main...HEAD)
             Test results: $(cat test-results.xml | head -50)
             Eval report: $(cat eval_report.json | head -50)
             Contract: check archive/team_artifacts/" \
            > pr_review.md
      
      - name: Post review comment
        uses: actions/github-script@v7
        with:
          script: |
            const review = require('fs').readFileSync('pr_review.md', 'utf8');
            github.rest.issues.createComment({
              ...context.repo,
              issue_number: context.issue.number,
              body: review
            });
```

## Хранение артефактов

```
archive/team_artifacts/
  E15-A/
    1_po_package.md
    2_analyst_spec.md
    3_architect_contract.md
    4_designer_ui_spec.md
    5_developer_output.md
    6_tester_verdict.md
  E15-B/
    ...
```

Артефакты каждого пакета хранятся вместе. Это позволяет:
- Восстановить контекст решений
- Сравнить план с результатом
- Использовать как reference для planning следующих пакетов

## Рекомендуемый путь внедрения

```
Сейчас:    Уровень 1 (ручная оркестрация)
           ↓ Освоить все роли, отладить промпты
Через 2-3 пакета: Уровень 2 (скриптовая)
           ↓ Стабилизировать формат артефактов
Через эпоху: Уровень 3 (агентная)
           ↓ Добавить CI gates
Зрелость:  Уровень 4 (CI/CD)
```

### Шаг 1: Отработка на одном пакете (Уровень 1)

1. Выбрать небольшой пакет (2-3 файла в write-set).
2. Пройти все 6 ролей вручную.
3. Зафиксировать: какие промпты работают, какие нужно доработать.
4. Сохранить артефакты как reference.

### Шаг 2: Скриптование (Уровень 2)

1. Создать `scripts/run_team_pipeline.sh`.
2. Добавить human-review паузы между шагами.
3. Автоматизировать сохранение артефактов.

### Шаг 3: Агентная оркестрация (Уровень 3)

1. Написать мета-промпт для оркестратора.
2. Настроить параллелизм Architect + Designer.
3. Добавить авто-эскалацию при проблемах.

### Шаг 4: CI/CD (Уровень 4)

1. Tester на каждый PR (regression + verify).
2. Architect review после эпохи.
3. PO backlog prioritization по расписанию.

## Метрики процесса

Для оценки эффективности автоматизации отслеживать:

| Метрика | Как измерять | Целевое значение |
|---------|-------------|-----------------|
| Cycle time (пакет) | От PO до PASS | < 1 рабочий день |
| Rework rate | FAIL / (PASS + FAIL) | < 20% |
| Scope creep | Файлы за пределами write-set | 0 |
| Doc drift | Несинхронизированные docs после closure | 0 |
| Regression rate | Новые failures в regression suite | 0 |

