# Workflow Для Агентов — Test Bundles + Low-Budget Templates

Часть split-карты [`doc/agent_workflow.md`](agent_workflow.md).
Этот файл содержит: **Low-Budget шаблоны (Micro-Plan/Execute/Verify) и все стандартные test bundles по зонам (Tutor/API/UI/Persistence/Graph/Eval/Unified)**.

Другие части split-карты:
- [`agent_workflow_rules.md`](agent_workflow_rules.md) — Token Budget & Retry Safety
- [`agent_workflow_cycle.md`](agent_workflow_cycle.md) — базовый цикл, параллелизм, A/B/C split
- [`agent_workflow_templates.md`](agent_workflow_templates.md) — planning/verify/contract/task templates
- [`agent_workflow_arch_review.md`](agent_workflow_arch_review.md) — architecture review (5 фаз)

Перед закрытием пакета с артефактами оркестратора: проверка канонических файлов — [`scripts/validate_team_artifact.py`](../scripts/validate_team_artifact.py) или `npm run validate:team-artifacts -- --artifacts-dir archive/team_artifacts/<PACKAGE_ID>` (см. [`team_workflow/process.md`](team_workflow/process.md)).

---

## Low-Budget Шаблоны

Для среднебюджетных и дешёвых моделей (Haiku, Gemini Flash, GPT-4o mini и аналогов). Цель: **до 2k входных токенов** на один запрос.

`Micro-Plan` — fallback-режим, а не planning default.
По умолчанию используйте `Шаблон planning prompt` выше; `Micro-Plan` нужен только для очень жёсткого token budget.

### Micro-Plan (~1,500 токенов, Strict Read-set)

```text
Goal: plan <epoch-package> ONLY.

Read ONLY (max 3 files, no exceptions):
1. <target-file.py> — class/function signatures only (no full body)
2. <target-test.py> — existing patterns only
3. [OPTIONAL] Single entry from doc/backlog_registry.yaml for <target-package> only

Ignore prior responses/tools. Fresh context only.

Output (strict format):
- Package goal: 1 sentence tied to user pain
- Write-set: max 3 files
- Do-not-touch: max 5 items
- DoD: 1 pytest command + 1 observable result
- Copy-paste execution prompt (use Micro-Execute template below)

Rules:
- No code. Plan only.
- Do NOT read doc/epochs, doc/cjm.md, doc/closed_iterations.md, full backlog_registry.yaml, or full tasklist.
- If context is missing, ask ONE clarifying question only.
- If overlap/split or AC gap requires PO: one line HANDOFF_SIGNAL: <gap> → layer scope_po — then stop.
- Total output: max 300 words.
```

### Micro-Execute (~1,200 токенов, Strict Context)

```text
Goal: close <package-id>: <1-line outcome>.

Read ONLY (max 2 files):
- <file1.py> — target file section/signatures first if >600 lines
- <file2.py> — target test pattern or one test case

Ignore prior responses/tools. Fresh context only.

DoD: <pytest command> green.
Do not touch: <list, max 5 items>.
Owner/write-set files are not read-set; do not read owner files fully unless listed above.

Output:
- Files changed (path:line)
- Test result (pass/fail)
- Risk (1 line or "none")
```

### Micro-Verify (~800 токенов, Minimal Context)

```text
Goal: verify <package-id>.

Contract DoD: <command> → <expected result>.
Diff range: <COMMIT_RANGE>.

Ignore prior responses/tools. Fresh context only.

Steps:
1. Run: <command>
2. Check diff touches ONLY: <write-set>
3. Check diff does NOT touch: <do-not-touch list>

Output:
- PASS / CONDITIONAL PASS / FAIL
- Scope violation: yes/no
- Test result: pass/fail
- If FAIL: exact blocker (file:line), no commentary
```

### Правила использования low-budget шаблонов

- Один запрос = один шаблон, один пакет.
- Не добавлять файлов сверх указанных в шаблоне.
- Если модель начинает читать лишние файлы — перезапустить с явным `Read ONLY`.
- Для Architecture Review использовать только `arch-*` фазы (см. выше), не полный шаблон.

---

## Стандартные Test Bundles

Ниже не полный список всех тестов репозитория, а рекомендуемые готовые наборы для типовых agent-задач.

### Быстрый Выбор Проверки

| Тип изменения | Что запускать |
|---|---|
| Tutor core / orchestration / prompts | `tests/test_tutor_personalization_policy.py tests/test_tutor_orchestrator.py tests/test_pipeline_steps.py tests/test_tutor_prompts.py` |
| Tutor payload / `/ask` / typed contracts | `tests/test_query_service.py tests/test_tutor_learner_contract.py tests/test_api.py` |
| Tutor UI read-paths | `tests/test_ui_helpers.py tests/test_api.py tests/test_query_service.py` |
| Полный tutor surface slice | `tests/test_tutor_learner_contract.py tests/test_ui_helpers.py tests/test_query_service.py tests/test_api.py` |
| Persistence / learner state | `tests/test_user_state.py tests/test_learner_model_service.py tests/test_learning_plan_service.py` |
| Graph metrics / compare / gate / debug UI | `tests/test_metrics.py tests/test_debug_panel.py tests/test_graph_expansion_benchmark.py tests/test_check_graph_expansion_gate.py tests/test_graph_expansion_compare.py tests/test_smoke_graph_expansion_gate.py tests/test_smoke_graph_expansion_compare.py` |
| Graph ready commands | `python scripts/check_graph_expansion_gate.py`, `python scripts/check_graph_expansion_gate.py --profile strict`, `python scripts/smoke_graph_expansion_gate.py` |
| Tutor ready commands | `python scripts/check_tutor_regression_gate.py`, `python scripts/check_tutor_regression_gate.py --summary-only` |
| Eval / answer quality / CI gate | `tests/test_eval_answer_quality.py tests/test_eval_ci_gate.py tests/test_eval_golden_qa_contract.py`; integration: `pytest -m integration tests/test_integration_retrieval.py` |
| Eval CI gate ready command | `python scripts/eval_ci_gate.py --baseline tests/eval/results/baseline.json --thresholds tests/eval/thresholds.json` |
| Unified eval loop | `python scripts/run_eval_loop.py --profile ci --report-json unified_eval_report.json`, `python -m pytest tests/test_eval_loop.py` |

Если change попадает сразу в две зоны, лучше брать объединённый bundle, а не только самый узкий.

### Tutor Core

Когда использовать:

- orchestration logic;
- tutor policy;
- tutor prompts;
- pipeline trace tutor-path.

Команды:

```bash
python -m pytest tests/test_tutor_personalization_policy.py tests/test_tutor_orchestrator.py tests/test_pipeline_steps.py tests/test_tutor_prompts.py
```

### Tutor API / Typed Contracts

Когда использовать:

- `app/query_service.py`;
- `app/api_models.py`;
- `app/tutor_learner_contract.py`;
- tutor payload / session metadata / `/ask`.

Команды:

```bash
python -m pytest tests/test_query_service.py tests/test_tutor_learner_contract.py tests/test_api.py
```

### Tutor UI Read-Paths

Когда использовать:

- `app/ui/helpers.py`;
- `app/ui/main.py`;
- `app/ui/resume_cards.py`;
- `app/ui/tutor_mastery_forecast_panel.py`.

Команды:

```bash
python -m pytest tests/test_ui_helpers.py tests/test_api.py tests/test_query_service.py
```

Если изменения затрагивают только presentation/helper-логику, можно начать с более узкого прогона:

```bash
python -m pytest tests/test_ui_helpers.py
```

### Tutor Full Surface Bundle

Когда использовать:

- изменения одновременно в typed payload и tutor UI;
- закрытие slice уровня `E6.2` / `E6.5`.

Команды:

```bash
python -m pytest tests/test_tutor_learner_contract.py tests/test_ui_helpers.py tests/test_query_service.py tests/test_api.py
```

### Persistence / Learner State

Когда использовать:

- `app/user_state.py`;
- `app/adaptive_plan.py`;
- learner model / learning plan state.

Команды:

```bash
python -m pytest tests/test_user_state.py tests/test_learner_model_service.py tests/test_learning_plan_service.py
```

### Graph Retrieval / Observability

Когда использовать:

- `app/metrics.py`;
- `app/graph_retrieval.py`;
- `app/ui/debug_panel.py`;
- graph benchmark/compare/gate scripts.

Команды:

```bash
python -m pytest tests/test_metrics.py tests/test_debug_panel.py tests/test_graph_expansion_benchmark.py tests/test_check_graph_expansion_gate.py tests/test_graph_expansion_compare.py tests/test_smoke_graph_expansion_gate.py tests/test_smoke_graph_expansion_compare.py
```

### Graph Ready Commands

Когда использовать:

- перед merge для graph gate / smoke / compare изменений;
- при изменениях в `scripts/check_graph_expansion_gate.py`, `scripts/smoke_graph_expansion_gate.py`, `scripts/graph_expansion_compare.py`.

Команды:

```bash
python scripts/check_graph_expansion_gate.py
python scripts/check_graph_expansion_gate.py --profile strict
python scripts/smoke_graph_expansion_gate.py
```

### Tutor Ready Commands

Когда использовать:

- для изменений в tutor regression contour;
- для `E6.6`-подобных задач.

Команды:

```bash
python scripts/check_tutor_regression_gate.py
python scripts/check_tutor_regression_gate.py --summary-only
```

### Eval / Answer Quality / CI Gate

Когда использовать:

- `tests/eval/run_eval.py` и `tests/eval/golden_qa.jsonl`;
- `scripts/eval_ci_gate.py` и `tests/eval/results/baseline.json`;
- `tests/test_eval_answer_quality.py`, `tests/test_eval_ci_gate.py`, `tests/test_eval_golden_qa_contract.py`;
- `tests/test_integration_retrieval.py`;
- любые изменения в eval-контуре (guard логика, dataset, thresholds, baseline).

Команды (unit):

```bash
python -m pytest tests/test_eval_answer_quality.py tests/test_eval_ci_gate.py tests/test_eval_golden_qa_contract.py
# integration (реальный API): отдельно, см. pytest.ini
python -m pytest -m integration tests/test_integration_retrieval.py
```

Smoke-прогон eval без LLM (mock-режим, только структурная проверка):

```bash
python tests/eval/run_eval.py --mock --quiet --report-json tests/eval/results/_smoke_run.json
```

CI gate против baseline:

```bash
python scripts/eval_ci_gate.py --baseline tests/eval/results/baseline.json --thresholds tests/eval/thresholds.json --report-json tests/eval/results/_smoke_gate.json
```

Live-прогон (с OPENAI_API_KEY) для регенерации baseline:

```bash
python tests/eval/run_eval.py --report-json tests/eval/results/baseline.json
```

> **Важно:** `--mock --report-json baseline.json` заблокирован guard'ом — команда вернёт ошибку и не перезапишет файл. Для регенерации baseline нужен live-прогон с реальным ключом.

### Unified Eval Loop

Когда использовать:

- изменения в eval / quality / SLO / CI gate контуре;
- перед nightly или ручной сверкой качества, когда нужен один JSON-артефакт.

Команды:

```bash
python scripts/run_eval_loop.py --profile ci --report-json unified_eval_report.json
python -m pytest tests/test_eval_loop.py
```

Для nightly-проверки с LLM-ключом:

```bash
python scripts/run_eval_loop.py --profile nightly --report-json unified_eval_report.json
```

Если появится отдельный smoke-script или CI workflow, его нужно добавить сюда как стандартную команду, а не держать только в `backlog_registry.yaml` / generated `tasklist`.
