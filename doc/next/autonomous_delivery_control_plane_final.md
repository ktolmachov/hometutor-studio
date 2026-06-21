# Autonomous Delivery Control Plane v3 — Final Master Plan
<!-- Reviewed & patched: 2026-04-28. See inline ⚠️ FIXED notes for changes vs original draft. -->

## 1. Контекст и архитектурное видение

В рамках эволюции `run_autonomous` мы переходим от pipeline, управляемого текстом (markdown + exit-code stdout), к настоящему **agentic runtime**. 
Агент должен выполнять только текущую задачу. Все критические решения о продолжении, остановке, ретраях и закрытии пакета принимает детерминированный control plane через структурированные события, политики и доказательства (proofs).

Этот план объединяет изначальный v2 (покрытие базовых механик: event protocol, closure gates) и v3 (добавление sandbox, replay и evals) в единый **Master Plan**, чтобы ни одна важная деталь не была утеряна.

---

## 2. Принципы (Runtime Trust Foundation)

1. **Prompt is not control plane**: Промпт не решает, продолжать ли pipeline. Решение принимает `pipeline_state.json + result.json + policy.yaml`.
2. **Every critical action must leave durable evidence**: Любой `post-agent`, closure, retry, human approval должен оставлять артефакт в `logs/autonomous_runs/<run_id>/`.
3. **No closure without proof**: Пакет закрывается только через валидный `proof_bundle/manifest.json`.
4. **Security is a first-class role**: Встроенный sandbox, command guard и approval protocol для опасных действий.
5. **Reliability must be measured**: SLI/SLO для трёх метрик (определения для измерения):
   - `closure_success_rate = closed_packages / attempted_closures` (за окно).
   - `false_closure_rate = closures, где post-hoc gate (write-set drift / proof mismatch) нашёл нарушение / total_closures`.
   - `prompt_injection_block_rate = sandbox_blocks / sandbox_violations_total` (true-positive rate сэндбокса).
   *(реализуется в Wave 2: `epoch-autonomous-observability-dashboard`)*

---

## 3. Архитектурный Roadmap (Wave 1 & Wave 2)

### Wave 1 — Runtime Trust Foundation (Критический путь)
Фундамент, обеспечивающий контроль, безопасность и расследуемость каждого шага.
1. `epoch-control-plane-v3-core` — Структурный event/state protocol (`pipeline_state.json`, `result.json`).
2. `epoch-agent-sandbox-policy` — Sandbox и блокировка опасных действий агента.
3. `epoch-durable-replay-time-travel` — Time-travel snapshots и replay manifest для каждого run.
4. `epoch-proof-bundle-closure-gate` — Closure только через структурированные доказательства.
5. `epoch-hook-final-step-gate` — Hook проверяет свежесть proofs и write-set, а не просто напоминает.

### Wave 2 — Quality, Policy & Routing (Восстановлено из v2 + новые evals)
Оптимизация, маршрутизация и качество (multiplier packages).
6. `epoch-failure-classifier` — Карта exit codes -> named failure classes с declarative `next_action`.
7. `epoch-quality-gates-matrix` — Унификация pre-closure gates в `quality_gates.run_all()`.
8. `epoch-prompt-routing-registry` & `epoch-thin-current-task` — Единый `prompts_registry.yaml` и разделение task на thin `current_task.md` + `context_pack.md`.
9. `epoch-skills-jit-router` — `skills_router.yaml` для JIT-загрузки навыков.
10. `epoch-nonstop-wave-policy` — Безопасная wave-политика (max_tasks, time limits).
11. `epoch-agent-evals-layer` & `epoch-adversarial-eval-harness` — Adversarial testing и evals.
12. `epoch-hitl-approval-protocol` & `epoch-pipeline-concurrency-locks` — Human-in-the-loop approvals.
13. `epoch-autonomous-observability-dashboard` — CLI timeline (расширение `pipeline_status.py --json`, **уже существует**; добавить агрегацию из `logs/autonomous_runs/`) и визуализация `logs/`.
    **JSON-расширение (минимум):**
    ```json
    {
      "runs": [
        {
          "run_id": "string",
          "package_id": "string",
          "exit_code": 0,
          "duration_s": 0.0,
          "phase": "closed",
          "proof_ok": true,
          "started_at": "2026-04-28T10:20:00Z"
        }
      ],
      "stats": {
        "closure_success_rate": 1.0,
        "false_closure_rate": 0.0,
        "prompt_injection_block_rate": 0.0,
        "median_duration_s": 0.0
      }
    }
    ```
    Aggregation source: `logs/autonomous_runs/*/result.json` + `event_log.jsonl`.

---

## 4. Детальный план Wave 1 (для реализации в следующей сессии)

### Package 1: `epoch-control-plane-v3-core`
**Цель:** Каждый `--post-agent` exit создает `result.json`. Внедрение/доведение `pipeline_state.json`.

> ⚠️ FIXED v4 (STALE-PLAN): на 2026-04-28 базовые P1-файлы уже есть в репозитории: `scripts/pipeline_events.py`, `scripts/pipeline_state.py`, `schemas/pipeline_result.schema.json`, `schemas/pipeline_state.schema.json`, `tests/test_pipeline_events.py`, `tests/test_run_autonomous_result_json.py`. Следующий агент **не должен пересоздавать их с нуля**. Правильная работа P1: проверить соответствие контракту ниже, закрыть недостающие gaps, обновить тесты точечно.

> ⚠️ FIXED: `pipeline_status.py --json` **уже реализован** (строка 196). Не трогать.
> ⚠️ FIXED: `result.json` должен писаться в `logs/autonomous_runs/<run_id>/result.json`.
> Директория `logs/autonomous_runs/` **ещё не существует** — создать программно в `pipeline_events.py`. `logs/` уже в `.gitignore` рядом с `data/`/`.venv/` — отдельно `logs/autonomous_runs/` добавлять не требуется.
> ⚠️ FIXED v2 (CRIT-2): текущая схема `run_autonomous.py` (`os.environ.setdefault("HOME_RAG_RUN_ID", str(int(time.time())))`) **коллидирует** при subsecond/concurrent runs. Новое правило:
> ```python
> run_id = pipeline_events.get_or_create_run_id()
> # internally: existing HOME_RAG_RUN_ID or f"{int(time.time()*1000)}-{secrets.token_hex(3)}"
> ```
> Доступ к env **не размазывать по коду**: добавить `pipeline_events.get_or_create_run_id(env: MutableMapping[str, str] | None = None)`, а `run_autonomous.py` и `_perf_timer.py` перевести на этот helper. Это runtime correlation id для CLI/scripts, не настройка приложения; новые app-модули по-прежнему не читают env напрямую.
> Если `HOME_RAG_RUN_ID` уже задан (sub-script), переиспользуем — корреляция с `_perf_timer.py` сохранена. Если процесс top-level — генерируем ms+suffix и **экспортируем** в env для дочерних процессов (`env["HOME_RAG_RUN_ID"] = run_id` внутри helper).
> ⚠️ FIXED v3 (CRIT-2): `latest_run_id.txt` / singleton `current_run.json` остаются last-writer-wins при параллельных top-level runs. Вместо singleton — PID-scoped registry `logs/autonomous_runs/current/<pid>.json`:
> ```json
> {"run_id": "1714248000123-a1b2c3", "pid": 12345, "package_id": "epoch-control-plane-v3-core", "started_at": "2026-04-28T10:20:00Z"}
> ```
> Reader перечисляет `current/*.json`, отбрасывает stale PID и выбирает запись по `package_id`/свежести. Проверка PID через `pipeline_events.is_pid_alive(pid)`; внутри helper: POSIX `os.kill(pid, 0)`, Windows — `OpenProcess(SYNCHRONIZE)` + `WaitForSingleObject(..., 0)`. Не вызывать `os.kill(pid, 0)` напрямую в hook logic.

**Семантика `pipeline_state.json` (CRIT-1):**
- **Путь:** `logs/autonomous_runs/<run_id>/pipeline_state.json` (per-run, не singleton).
- **Поля (минимум):**
  ```json
  {
    "run_id": "string", "package_id": "string",
    "phase": "planning | execution | post_agent | closed | failed",
    "attempt": 0, "last_event_id": "string",
    "proof_status": "missing | partial | complete",
    "updated_at": "ISO-8601"
  }
  ```
- **Writer:** `scripts/pipeline_state.py::update(run_id, **fields)` — atomic write через `tempfile + os.replace` в той же директории. Вызов из `run_autonomous.py` на каждой смене фазы и из `close_package.py` на final transition.
- **Reader:** `pipeline_guard_logic.py` (P5), `close_package.py` (P4), `proof_bundle.py` (P4).
- Снятый snapshot уходит в `state_snapshots/` (детали в P3).

**Расположение `schemas/` (HIGH-3):** директория в **корне репо** (data-only, не Python package — НЕ создавать `__init__.py`). Резолв из кода: `Path(__file__).resolve().parents[1] / "schemas"` в `pipeline_events.py`.

**Orphan события (HIGH-5, anchor для P4):** при отсутствии `HOME_RAG_RUN_ID` (manual CLI invocations) `pipeline_events.emit()` пишет в `logs/autonomous_runs/_orphan/{YYYY-MM-DD}.jsonl` (общий orphan-лог, append-only). `ensure_run_dir(run_id=None)` возвращает orphan-путь.

- **Проверить/довести:** `schemas/pipeline_result.schema.json`, `schemas/pipeline_state.schema.json`, `scripts/pipeline_events.py` (должен включать `get_or_create_run_id()`, `ensure_run_dir(run_id)`, `is_pid_alive(pid)`, поддержку `_orphan/` и `current/<pid>.json`), `scripts/pipeline_state.py` (atomic update), `tests/test_pipeline_events.py` (orphan-режим, collision-free run_id, pid-registry cleanup), `tests/test_run_autonomous_result_json.py`.
- **Изменить только если gap подтверждён:** `scripts/run_autonomous.py` (использует `pipeline_events.get_or_create_run_id()`; пишет `result.json` + `pipeline_state.json` на каждом exit code), `scripts/_perf_timer.py` (читает run_id через helper/fallback без генерации нового unix-сек ID), `doc/team_workflow/run_autonomous_prompt.md` (изменять минимально, **запрещено** удалять таблицу exit-кодов — агенту нужны текстовые инструкции), `doc/team_workflow/run_autonomous_runbook.md` (создать/обновить, если отсутствует или устарел).
- **Не трогать:** `scripts/pipeline_status.py` (`--json` уже есть); `.gitignore` (`logs/` уже исключён рядом с `data/`).
- **DoD:** `pytest tests/test_pipeline_events.py tests/test_run_autonomous_result_json.py` (тесты создают run через `pipeline_events` и проверяют `result.json` + `pipeline_state.json` по схемам без запуска реального `--post-agent`).

> ⚠️ FIXED (DoD): `--smoke` и `--post-agent` **взаимно исключают** друг друга (строка 2067: `❌ --smoke cannot be combined with --post-agent`). `--smoke` явно отключает post-agent side effects. DoD **не должен** использовать `--smoke` для проверки генерации `result.json`. Правильная проверка — unit-тесты или `--post-agent --package epoch-demo` в изолированном sandbox.

### Package 2: `epoch-agent-sandbox-policy`
**Цель:** Запретить агенту опасные команды, запись в секреты и расширение scope.

> ⚠️ FIXED: `agent_sandbox_policy.yaml` не должен лежать в `doc/team_workflow/`. Правильное место — `policies/agent_sandbox_policy.yaml`.  
> ⚠️ FIXED: Граница между `agent_sandbox.py` и `command_guard.py` не определена — без этого агент создаст дублирующую или несвязную логику.  
> Правило разделения (HIGH-1, уточнённый контракт): **`command_guard.py`** — pure-функция без I/O. Сигнатура:
> ```python
> def check(cmd: list[str], policy: PolicyDoc) -> Verdict:  # Verdict = ("ALLOW" | "BLOCK", reason: str)
> ```
> Никаких глобальных state, никакой загрузки yaml. **`agent_sandbox.py`** — orchestrator: грузит `PolicyDoc = load_policy("policies/agent_sandbox_policy.yaml")` **один раз** на старте, передаёт в `command_guard.check(cmd, policy)`, оборачивает `subprocess.run`. Public API: `agent_sandbox.safe_run(cmd: list[str]) -> CompletedProcess`, raises `SandboxViolationError` при `BLOCK`.
> ⚠️ FIXED v4 (CRIT-14): sandbox как отдельный wrapper бесполезен, если существующие runner call-sites продолжают вызывать `subprocess.run(..., shell=True)` напрямую. P2 обязан включать integration plan:
> - заменить agent-controlled command execution в `scripts/run_autonomous.py`, `scripts/close_package.py`, `scripts/start_workflow.py` на `agent_sandbox.safe_run(...)` или явно помеченный internal-only helper;
> - оставить прямой `subprocess.run` только для фиксированных internal commands (`git status`, `git diff`, registry sync) с `# noqa`/комментарием `internal fixed command, not agent-controlled`;
> - запретить `shell=True` для agent-controlled commands; если shell нужен для PowerShell launcher text, sandbox проверяет уже распарсенный command template до запуска.
> Иначе DoD P2 считается failed даже если unit-тесты `command_guard` зелёные.

- **Создать/изменить:** `policies/agent_sandbox_policy.yaml`, `scripts/agent_sandbox.py`, `scripts/command_guard.py`, `tests/test_agent_sandbox.py`, `tests/test_command_guard.py`, и только те runner call-sites, где команда зависит от agent/task input.
- **DoD:** `command_guard.check(["git", "reset", "--hard"], policy)` → `("BLOCK", reason)`; `agent_sandbox.safe_run(["git", "reset", "--hard"])` → raises `SandboxViolationError`; тесты `command_guard` параметризованы и **не** делают I/O (policy строится в фикстуре); integration-тест доказывает, что agent-controlled dangerous command не доходит до `subprocess.run`; `rg "shell=True|subprocess.run" scripts/run_autonomous.py scripts/close_package.py scripts/start_workflow.py` не показывает новых незащищённых agent-controlled call-sites.

### Package 3: `epoch-durable-replay-time-travel`
**Цель:** Любой autonomous run должен быть расследуемым (`event_log.jsonl`, `commands.jsonl`, state snapshots).

> ⚠️ FIXED: Package 3 **расширяет** структуру `logs/autonomous_runs/<run_id>/`, созданную в Package 1 (`ensure_run_dir`). Не создавать директорию заново — переиспользовать `pipeline_events.ensure_run_dir(run_id)`.  
> ⚠️ FIXED: `event_log.jsonl` и `commands.jsonl` должны использовать тот же `run_id`, что и `result.json` из Package 1 — схема `run_id` зафиксирована в Package 1.

**Формат `state_snapshots/` (HIGH-4):**
- Writer — `run_recorder.py` (subscribe на каждый `pipeline_state.update()` через event-bus или explicit hook).
- Snapshot — копия `pipeline_state.json` в `state_snapshots/{seq:04d}_{event_name}.json`, где `seq` — monotonic counter (0001, 0002, …), `event_name` — slug вызывающего события (`phase_change`, `proof_complete`, …).
- Snapshot **не** включает git tree (для time-travel git reflog/diff достаточно).
- Снимки — append-only, `replay_run.py` восстанавливает состояние линейно по seq.

- **Создать:** `scripts/run_recorder.py` (snapshot writer + event_log appender), `scripts/replay_run.py`, `scripts/diff_runs.py`, `schemas/replay_manifest.schema.json`, тесты (`tests/test_run_recorder.py` включая `test_snapshots_monotonic` + `test_event_log_append_only`).
- **DoD:** После `--post-agent` в `logs/autonomous_runs/<run_id>/` присутствуют: `result.json`, `pipeline_state.json`, `event_log.jsonl`, `state_snapshots/{0001,0002,...}_*.json`; `replay_run.py --dry-run` валидирует манифест по `schemas/replay_manifest.schema.json`. `jsonschema` не указан в `requirements.txt`; либо добавить pinned dependency в `requirements.txt`, либо реализовать минимальную structural validation без новой зависимости. Нельзя молча добавить импорт, который работает только за счёт транзитивной зависимости.

### Package 4: `epoch-proof-bundle-closure-gate`
**Цель:** `close_package.py` требует `proof_bundle/manifest.json`.

> ⚠️ FIXED: В `run_autonomous.py` уже существует механизм "proof of execution" через `execution_contract.md` (hardgate exit 3, строка ~1200). Package 4 **не заменяет** его, а добавляет структурированный `proof_bundle/manifest.json` поверх. Нужно явно прописать совместимость: если `execution_contract.md` присутствует, `proof_bundle.py` читает его как один из источников proof.  
> ⚠️ FIXED v3: разделить два разных missing-proof сценария, иначе план противоречит текущему коду.  
> 1. Отсутствует legacy `execution_contract.md` в `run_autonomous.py --post-agent` → **exit 3** (существующий hard gate, не менять).  
> 2. `execution_contract.md` есть, но отсутствует/невалиден новый `proof_bundle/manifest.json` при closure validation → **exit 2** + событие `PROOF_MISSING` или `PROOF_TAMPERED`.  
> `PROOF_MISSING` — **имя события** в `event_log.jsonl`, не новый exit code. Не вводить exit 8+.
> ⚠️ FIXED: `proof_bundle/manifest.json` хранится в `logs/autonomous_runs/<run_id>/proof_bundle/manifest.json`, а не в корне пакета.

**Структура `proof_manifest.schema.json` (CRIT-5):** manifest содержит **ссылки** на артефакты-доказательства, не сами данные. Минимальные поля:
```json
{
  "run_id": "string", "package_id": "string", "generated_at": "ISO-8601",
  "artifacts": [
    {"path": "archive/team_artifacts/<id>/dod_cache.json", "sha256": "...", "kind": "dod_cache"},
    {"path": "archive/team_artifacts/<id>/execution_contract.md", "sha256": "...", "kind": "execution_contract"},
    {"path": "logs/autonomous_runs/<run_id>/event_log.jsonl", "sha256": "...", "kind": "event_log"}
  ],
  "git": {"head_sha": "...", "diff_sha256": "..."}
}
```
`proof_bundle.validate()` **пересчитывает** sha256 каждого артефакта и сравнивает с manifest — если расходится, exit 2 + событие `PROOF_TAMPERED`.

**Orphan событие (HIGH-5):** при отсутствии `HOME_RAG_RUN_ID` `close_package.py` пишет `PROOF_MISSING` в `logs/autonomous_runs/_orphan/{YYYY-MM-DD}.jsonl` (через `pipeline_events.emit()` с orphan-fallback из P1).

- **Создать:** `scripts/proof_bundle.py` (`build()`, `validate()`), `schemas/proof_manifest.schema.json`, тесты (`tests/test_proof_bundle.py` включая `test_validate_recomputes_sha256` + `test_orphan_event_on_missing_run_id`).
- **Изменить:** `scripts/close_package.py` (вызов `proof_bundle.validate()`; при ручном запуске без `HOME_RAG_RUN_ID` fallback на проверку `execution_contract.md` напрямую + emit в `_orphan/`), `scripts/run_autonomous.py` (генерация `proof_bundle/manifest.json` при успешном `--post-agent`).
- **DoD:** `run_autonomous.py --post-agent` без `execution_contract.md` по-прежнему возвращает exit 3. Closure с `execution_contract.md`, но без нового манифеста: `close_package.py`/post-agent closure gate возвращает exit 2, событие `PROOF_MISSING` записывается в `event_log.jsonl` (или `_orphan/`). При подделке артефакта (manifest хранит старый sha256, файл изменён) — exit 2, `PROOF_TAMPERED`. `dod_cache.json` **не** трактуется как proof — он лишь один из артефактов, верифицируемых через sha256.

### Package 5: `epoch-hook-final-step-gate`
**Цель:** Cursor/IDE stop hook проверяет freshness `result.json`, write-set нарушения и retry budget.

> ⚠️ FIXED: `.cursor/hooks/pipeline_guard.py` **отфильтрован `.cursorignore`** — агент не может читать его через индексацию. Edit/Write всё равно работают (фильтр касается auto-context discovery, не записи). Стратегия: вынести логику gate в `scripts/pipeline_guard_logic.py` (читаемый агентом), а `pipeline_guard.py` оставить thin wrapper. Тестируется только `pipeline_guard_logic`.
> ⚠️ FIXED v2 (HIGH-2): `write-set drift` проверяется **только** в pre-commit семантике — `git status --porcelain` (modified + untracked). Post-commit режим не нужен (close_package коммит делает позже, нет call-site). YAGNI — добавим, если появится потребность.

**Источник истины write-set (CRIT-3):** **НЕ** `archive/team_artifacts/<id>/execution_contract.md` (его пишет агент, тривиально подделывается). Источник = `doc/current_task.md` секция `## Write-Set` (генерируется orchestrator-промптом, агент не редактирует):
```markdown
## Write-Set
- scripts/pipeline_events.py
- scripts/pipeline_state.py
- schemas/pipeline_result.schema.json
- tests/test_pipeline_events.py
```
- `write_set_check.py` парсит `## Write-Set` из `doc/current_task.md` (markdown bullets с относительными путями).
- Pre-requisite: `scripts/generate_orchestration_prompt.py` обязан включать `## Write-Set` в `current_task.md`. Если ещё не делает — добавить как **обязательную под-задачу P5** (одно изменение в шаблоне промпта). Без этого P5 не блокирует drift корректно.
- Любой modified/untracked файл вне `## Write-Set` → drift.

**SSoT для active package (CRIT-6):** `pipeline_guard_logic.py` не должен заново реализовывать "первую ready/WIP запись" из YAML: при нескольких ready-пакетах это выберет неверный пакет. Использовать общий resolver из `start_workflow.py` / `generate_orchestration_prompt.py` (registry-first, Truth View order, active wave semantics, `status.casefold()`). `doc/tasklist.md § Now` — производный weekly view (lint sync с реестром); resolver **не** читает tasklist для выбора пакета и не использует его как fallback при отсутствии строк в YAML.

**Hook = advisory, runners = enforcing (CRIT-4):** Cursor stop-hook **не блокирует** агента — он лишь инжектит `followup_message`. Реальный enforcement — в python-runner'ах. Три call-sites одной gate-логики:
| Caller | Режим | Действие при violation |
|---|---|---|
| `.cursor/hooks/pipeline_guard.py` | advisory | `print(json.dumps({"followup_message": ...}))` |
| `scripts/run_autonomous.py` (pre-flight `--post-agent`) | enforcing | exit 2 + событие в `event_log.jsonl` |
| `scripts/close_package.py` | enforcing | exit 2 + событие в `event_log.jsonl` |
Все три импортируют `pipeline_guard_logic.evaluate(state) -> Verdict` — single source of truth.

**Migration & rollout (CRIT-7):** новые блокеры (drift, stale `result.json`, retry budget) — **breaking change** для in-flight пакетов (`archive/team_artifacts/E15-A`, `E16`, `E24-A` и др. не имеют `## Write-Set` в своих `current_task.md`).
- **Phase A (P5 deploy):** shadow mode — `pipeline_guard_logic` логирует violations в `event_log.jsonl` (`event_name: GATE_VIOLATION_SHADOW`), но **не** возвращает blocker exit-code. Hook продолжает инжектить followup info-only.
- **Phase B (отдельный пакет, после Wave 1):** включение enforcing через отдельный `policies/pipeline_gate_policy.yaml: gate_mode: enforcing`. Не смешивать rollout gate-логики с `policies/agent_sandbox_policy.yaml`: sandbox policy отвечает за команды, pipeline gate policy — за closure/drift/freshness. Pre-condition phase B: 0 GATE_VIOLATION_SHADOW за последние 7 дней.
- **Backfill (опционально):** `scripts/backfill_writeset.py` для in-flight пакетов — извлечь write-set из git-истории каждого пакета и записать в его `current_task.md`. Запустить если pre-flight найдёт > 0 active packages без `## Write-Set`.

- **Создать:** `policies/pipeline_gate_policy.yaml`, `scripts/pipeline_guard_logic.py` (вся проверочная логика, public API: `evaluate(ctx) -> Verdict`), `scripts/write_set_check.py` (parses `doc/current_task.md`, runs `git status --porcelain`), тесты (`tests/test_write_set_check.py`, `tests/test_pipeline_guard_logic.py` включая `test_shadow_mode_logs_only`).
- **Изменить:** `.cursor/hooks/pipeline_guard.py` (thin wrapper, импорт из `pipeline_guard_logic`, advisory output), `scripts/run_autonomous.py` (enforcing pre-flight в `--post-agent`), `scripts/close_package.py` (enforcing gate перед closure), `scripts/generate_orchestration_prompt.py` (вставка секции `## Write-Set` в шаблон `current_task.md`).
- **DoD:** Все три call-sites дают консистентный `Verdict` для одного и того же state; в shadow mode runners возвращают exit 0 даже при violation (только лог); тесты `pipeline_guard_logic` зелёные; ручная проверка: hook injects followup, run_autonomous (с `policies/pipeline_gate_policy.yaml: gate_mode: enforcing`) возвращает exit 2, close_package возвращает exit 2.

---

## 5. Готовый Prompt для старта сессии

Скопируйте этот блок текста и отдайте агенту в новой сессии:

```text
Ты работаешь в репозитории hometutor.

Задача: подготовить Wave 1 — Runtime Trust Foundation и начать выполнение только через штатный workflow  
для Autonomous Delivery Control Plane v3.

Главная цель:  
Перевести autonomous delivery pipeline из markdown/exit-code driven workflow  
в auditable, replayable, policy-governed, proof-based agentic runtime.

Ключевой принцип:  
LLM agent выполняет только текущую задачу.  
Control plane принимает решения через pipeline_state.json, result.json, policy.yaml,  
schema validation, proof bundle, hooks and gates.

Исходный контекст:  
1. Текущий run_autonomous pipeline уже является self-propagating loop.  
2. В системе уже есть: scripts/run_autonomous.py, scripts/close_package.py, scripts/pipeline_status.py, .cursor/hooks/pipeline_guard.py, doc/current_task.md.  
3. Нужно внедрять изменения маленькими пакетами, test-first, с backward compatibility.
4. Нельзя реализовывать код напрямую из этого master-plan: сначала должен быть активный package contract в `doc/backlog_registry.yaml` (пересобранный `doc/tasklist.md` — только зеркало для людей, не источник для resolver), затем execution task в `doc/current_task.md`.

Перед началом:  
- Не читай весь проект целиком. Используй rg/head/targeted reads.  
- Не трогай файлы вне объявленного write-set.  
- Не меняй exit codes 0–7. stdout/stderr поведение сохранить; result.json добавить как additive protocol.  
- Используй папки logs/ или archive/ для генерируемых runtime артефактов (не коммитить временные файлы).

Wave 1 packages:

Wave 1 packages — детальные требования смотри в **разделе 4** этого документа (источник истины).
Краткое summary ключевых правил, которые НЕЛЬЗЯ нарушить (полный текст — в разделе 4):

PACKAGE 1: epoch-control-plane-v3-core
- run_id = HOME_RAG_RUN_ID || f"{int(time.time()*1000)}-{secrets.token_hex(3)}" (НЕ просто unix-сек — коллизии при concurrent runs).
- Если top-level: export HOME_RAG_RUN_ID для дочерних процессов.
- Заменить latest_run_id.txt / singleton current_run.json → logs/autonomous_runs/current/<pid>.json; reader перечисляет live PID-записи и выбирает по package_id/свежести.
- Проверка PID только через pipeline_events.is_pid_alive(pid): POSIX os.kill(pid, 0), Windows OpenProcess/WaitForSingleObject. Не вызывать os.kill(pid, 0) напрямую.
- pipeline_state.json: per-run, поля {run_id, package_id, phase, attempt, last_event_id, proof_status, updated_at}; atomic write.
- schemas/ в корне репо, data-only (без __init__.py).
- При отсутствии HOME_RAG_RUN_ID — события идут в logs/autonomous_runs/_orphan/{date}.jsonl.
- pipeline_status.py НЕ трогать (--json уже есть, строка 196).
- logs/ уже в .gitignore — отдельную запись не добавлять.
- DoD: unit-тесты, НЕ --smoke (--smoke ⊥ --post-agent, строка 2067).

PACKAGE 2: epoch-agent-sandbox-policy
- command_guard.check(cmd: list[str], policy: PolicyDoc) -> Verdict — pure-функция, без I/O, policy инжектится параметром.
- agent_sandbox грузит policy один раз, оборачивает subprocess; safe_run raises SandboxViolationError.
- Файлы: policies/agent_sandbox_policy.yaml + scripts/{agent_sandbox,command_guard}.py + тесты.

PACKAGE 3: epoch-durable-replay-time-travel
- Переиспользовать pipeline_events.ensure_run_dir(run_id) из P1.
- state_snapshots/{seq:04d}_{event_name}.json — append-only копия pipeline_state.json после каждого update.
- Snapshot НЕ включает git tree.
- replay_run.py --dry-run валидирует манифест по schemas/replay_manifest.schema.json.

PACKAGE 4: epoch-proof-bundle-closure-gate
- proof_manifest содержит ССЫЛКИ (path + sha256) на dod_cache.json, execution_contract.md, event_log.jsonl, git diff hash. dod_cache.json — НЕ proof, лишь верифицируемый артефакт.
- proof_bundle.validate() пересчитывает sha256, при mismatch — exit 2 + PROOF_TAMPERED.
- При отсутствии HOME_RAG_RUN_ID: fallback на execution_contract.md + событие PROOF_MISSING в logs/autonomous_runs/_orphan/.
- run_autonomous.py уже имеет execution_contract.md hard gate exit 3 (~строка 1200) — НЕ удалять, P4 строится поверх.
- PROOF_MISSING — имя события, НЕ новый exit code. Missing legacy execution_contract.md в --post-agent остаётся exit 3; missing/tampered proof_manifest после legacy proof — exit 2. НЕ вводить exit 8+.
- proof_bundle/manifest.json путь: logs/autonomous_runs/<run_id>/proof_bundle/manifest.json.

PACKAGE 5: epoch-hook-final-step-gate
- ИСТОЧНИК write-set: doc/current_task.md секция ## Write-Set (генерируется orchestrator-промптом, НЕ архив-контракт от агента).
- Pre-requisite: scripts/generate_orchestration_prompt.py обязан вставлять ## Write-Set в шаблон current_task.md (если ещё нет — это под-задача P5).
- Active package: использовать общий resolver из start_workflow/generate_orchestration_prompt.py; registry-first; `doc/tasklist.md` не использовать как fallback для active package. Не выбирать "первую ready/WIP запись" вручную.
- Hook = advisory (followup_message), enforcement = в run_autonomous.py + close_package.py через общую pipeline_guard_logic.evaluate(). Три call-sites, single source of truth.
- write-set drift: git status --porcelain (modified + untracked) vs ## Write-Set. Только pre-commit семантика (post-commit режим НЕ нужен).
- Migration: deploy в SHADOW MODE — gate_mode: shadow в отдельном policies/pipeline_gate_policy.yaml; violations логируются как GATE_VIOLATION_SHADOW, runners возвращают exit 0. Phase B (отдельный пакет): включение enforcing после 7 дней без violations.
- .cursor/hooks/pipeline_guard.py отфильтрован .cursorignore от auto-discovery, но Edit/Write работают. Логика — в scripts/pipeline_guard_logic.py.

Execution strategy:  
1. Phase 0: verify whether `epoch-control-plane-v3-core` is already closed/active in `doc/backlog_registry.yaml` (при необходимости сверить производный `doc/tasklist.md` после `backlog_registry_lint --sync-from-index --write-sync`). If the code exists but the package is not closed, run the P1 DoD and close/sync through the normal workflow. If it is already closed, do not reopen it.
2. Only after `doc/current_task.md` exists for the active package: read that task and produce a short implementation analysis of insertion points.
3. If P1 is active: verify/finish PACKAGE 1 only. If P1 is already closed: start the next accepted Wave 1 package through the normal workflow (likely P2). Do not implement multiple packages in one session.
4. Commit-style checkpoints are allowed only after green tests.
5. If context gets too large, stop after PACKAGE 1 and write: archive/team_artifacts/epoch-control-plane-v3-core/handoff.md.

Final output required: summary of completed package(s), changed files, tests run, generated artifacts, exact next command for continuing Wave 1.
```

---

## 6. Реестр исправлений (patch log)

| # | Пакет | Ошибка | Исправление |
|---|-------|--------|-------------|
| 1 | P1 | `pipeline_status.py --json` уже реализован | Убран из write-set; `Do NOT modify` |
| 2 | P1 | DoD использовал `--smoke` для проверки `result.json` | `--smoke` и `--post-agent` взаимоисключают друг друга (строка 2067); DoD заменён на unit-тесты |
| 3 | P1 | `logs/` не в `.gitignore` | `logs/` уже в `.gitignore` рядом с `data/`/`.venv/`; задача убрана из write-set |
| 4 | P1 | Схема `run_id` ломала корреляцию с таймингами и коллидировала при parallel runs | `run_id` генерируется как `ms+random suffix` через `pipeline_events.get_or_create_run_id()`; активные runs пишутся в `logs/autonomous_runs/current/<pid>.json`, без singleton-файла |
| 5 | P1→P3 | P3 пересоздаёт директорию `logs/` созданную P1 | P3 переиспользует `pipeline_events.ensure_run_dir(run_id)` из P1 |
| 6 | P2 | `agent_sandbox_policy.yaml` в `doc/team_workflow/` | Перемещён в `policies/` (новая директория) |
| 7 | P2 | Граница между `agent_sandbox.py` и `command_guard.py` не определена | Зафиксирован контракт: `command_guard` = pure validator, `agent_sandbox` = orchestrator + subprocess wrapper |
| 8 | P4 | `PROOF_MISSING` трактовался как новый exit code (8+) и смешивал legacy proof с новым manifest gate | Это имя события в `event_log.jsonl`; отсутствующий legacy `execution_contract.md` остаётся exit 3, отсутствующий/битый `proof_manifest` после legacy proof — exit 2 |
| 9 | P4 | `proof_bundle` конфликтует с существующим `execution_contract.md`-gate (exit 3) | P4 строится поверх; `proof_bundle.py` принимает `execution_contract.md` как proof source |
| 10 | P4 | Путь `proof_bundle/manifest.json` не уточнён | Зафиксирован: `logs/autonomous_runs/<run_id>/proof_bundle/manifest.json` |
| 11 | P5 | `.cursor/hooks/pipeline_guard.py` нечитаем агентом (.cursorignore) | Логика вынесена в `scripts/pipeline_guard_logic.py`; hook = thin wrapper |
| 12 | P5 | `write-set drift` не определён операционально | Зафиксирован: `git status --porcelain` (modified + untracked) vs `doc/current_task.md § Write-Set`; только pre-commit semantics |
| 13 | W2-13 | `pipeline_status.py --json` заявлен как новый в Wave 2 | Исправлено: "расширение существующего `--json`" |
| 14 | Принцип 5 | SLI/SLO декларированы без привязки к пакету | Привязан к Wave 2: `epoch-autonomous-observability-dashboard` |

### 6.1 Вторая ревизия (2026-04-28) — критические остаточные ошибки

| # | Severity | Пакет | Ошибка | Исправление |
|---|----------|-------|--------|-------------|
| CRIT-1 | crit | P1 | `pipeline_state.json` упомянут как фундамент, но не специфицирован (путь, lifecycle, поля, writer, reader) | Добавлена подсекция "Семантика `pipeline_state.json`": per-run путь, минимальные поля, atomic writer в `pipeline_state.py`, readers — guard/close_package/proof_bundle |
| CRIT-2 | crit | P1 | `run_id == HOME_RAG_RUN_ID` (1-сек granularity) → коллизии при concurrent runs; `latest_run_id.txt` / singleton `current_run.json` race | Формула `ms+secrets.token_hex(3)` через `get_or_create_run_id()`; export в env для дочерних; PID-scoped `current/<pid>.json`; cross-platform `is_pid_alive()` |
| CRIT-3 | crit | P5 | Drift-чекер парсил `archive/.../execution_contract.md` (пишется агентом → подделка) | Источник истины — `doc/current_task.md § Write-Set` (генерируется orchestrator); добавлена под-задача обновления `generate_orchestration_prompt.py` |
| CRIT-4 | crit | P5 | Cursor stop-hook трактовался как enforcement (он advisory, инжектит followup) | Разделены три call-sites общей логики `pipeline_guard_logic.evaluate()`: hook (advisory), `run_autonomous.py` + `close_package.py` (enforcing exit 2) |
| CRIT-5 | crit | P4 | `dod_cache.json` использовался как proof (легко подделывается, lifecycle несовместим) | `proof_manifest` хранит sha256-ссылки на артефакты (включая `dod_cache.json`); `validate()` пересчитывает; mismatch → `PROOF_TAMPERED` |
| CRIT-6 | crit | P5 | Игнорирована миграция на `backlog_registry.yaml` SSoT | `pipeline_guard_logic` использует общий registry-first resolver из `start_workflow.py` / `generate_orchestration_prompt.py`; tasklist.md не участвует в выборе пакета |
| CRIT-7 | crit | P5 | Новые блокеры (drift, stale result, retry budget) — breaking change без migration plan | Добавлен Phase A (shadow mode, only logs `GATE_VIOLATION_SHADOW`) → Phase B (enforcing, отдельный пакет, после 7 дней без violations); опциональный `backfill_writeset.py` для in-flight пакетов |
| HIGH-1 | high | P2 | `command_guard.check(cmd)` без policy → нужен глобальный state | Сигнатура `check(cmd, policy)` — pure-функция; orchestrator грузит `PolicyDoc` один раз |
| HIGH-2 | high | P5 | `--mode pre-commit \| post-commit` — лишний режим, нет call-sites | Только pre-commit (`git status --porcelain`); YAGNI |
| HIGH-3 | high | P1 | `schemas/` location не обоснован (root vs `app/schemas/`) | Корень репо, data-only, без `__init__.py`, резолв через `Path(__file__).parents[1]` |
| HIGH-4 | high | P3 | `state_snapshots/` упомянут в DoD, но writer/format не описан | `run_recorder.py` пишет `{seq:04d}_{event}.json` после каждого `pipeline_state.update()`; append-only; без git tree |
| HIGH-5 | high | P1+P4 | `event_log.jsonl` некуда писать без `HOME_RAG_RUN_ID` | `logs/autonomous_runs/_orphan/{date}.jsonl` через `pipeline_events.emit()` orphan-fallback |
| LOW-1 | low | P1 | `.gitignore` line 5 → реально 4 | Заменено на "рядом с `data/` и `.venv/`" (без номера строки) |
| LOW-2 | low | §5 | Готовый промпт дублировал §4 (риск рассинхрона) | §5 заменён на сжатое summary + ссылку "детали в §4" |
| LOW-3 | low | W2 #13 | `pipeline_status.py --json` extension без полей | Добавлена JSON-схема: `runs[]` + `stats{}` |
| LOW-4 | low | Принцип 5 | SLI без формулы | Формулы `closure_success_rate`, `false_closure_rate`, `prompt_injection_block_rate` |

### 6.2 Третья ревизия (2026-04-28) — критические ошибки после сверки с кодом

| # | Severity | Пакет | Ошибка | Исправление |
|---|----------|-------|--------|-------------|
| CRIT-8 | crit | P1 | Замена `latest_run_id.txt` на singleton `current_run.json` всё ещё была last-writer-wins при параллельных top-level runs | Введён PID-scoped registry `logs/autonomous_runs/current/<pid>.json`; reader фильтрует live PID и выбирает запись по package_id/свежести |
| CRIT-9 | crit | P1 | Проверка `os.kill(pid, 0)` напрямую не portable для Windows-first проекта | Добавлен обязательный helper `pipeline_events.is_pid_alive(pid)` с POSIX и Windows реализациями; hook/guard не вызывают `os.kill` напрямую |
| CRIT-10 | crit | P4 | План смешивал два разных missing-proof exit path: legacy `execution_contract.md` и новый `proof_manifest` | Legacy отсутствие `execution_contract.md` в `--post-agent` остаётся exit 3; новый manifest gate после legacy proof возвращает exit 2 + `PROOF_MISSING`/`PROOF_TAMPERED` |
| CRIT-11 | crit | P5 | `pipeline_guard_logic` мог выбрать неверный active package через "первую ready/WIP запись" registry | Использовать общий resolver из `start_workflow.py` / `generate_orchestration_prompt.py`; tasklist не использовать для resolver |
| CRIT-12 | crit | P5 | `gate_mode` был помещён в sandbox policy, смешивая command sandbox и closure/drift rollout | Введён отдельный `policies/pipeline_gate_policy.yaml`; `agent_sandbox_policy.yaml` остаётся только для command guard |
| CRIT-13 | crit | §5 | Готовый стартовый prompt позволял реализовывать Wave 1 напрямую из master-plan, обходя accepted contract/current_task workflow | Добавлена Phase 0: активировать package contract через штатный workflow; код писать только после появления `doc/current_task.md` |
| HIGH-6 | high | P1 | Run id/env access размазывался бы по `run_autonomous.py` и `_perf_timer.py` | Добавлен `pipeline_events.get_or_create_run_id()` как единая runtime точка; новые app-модули env напрямую не читают |
| HIGH-7 | high | W2 #13 | JSON-пример для `pipeline_status.py --json` был невалидным JSON (`{"run_id", ...}`) | Заменён на валидный объект с явными ключами и примерными значениями |

### 6.3 Четвёртая ревизия (2026-04-28) — stale-plan и integration blockers

| # | Severity | Пакет | Ошибка | Исправление |
|---|----------|-------|--------|-------------|
| CRIT-14 | crit | P2 | Sandbox был описан как новый wrapper, но без обязательной интеграции в существующие runner call-sites; опасные agent-controlled команды могли продолжить идти через `subprocess.run(..., shell=True)` | P2 теперь требует интеграционный план: agent-controlled commands идут через `agent_sandbox.safe_run`, direct `subprocess.run` остаётся только для fixed internal commands с явным комментарием |
| CRIT-15 | crit | P1 | План называл P1 файлы новыми, хотя в текущем репозитории они уже существуют (`pipeline_events.py`, `pipeline_state.py`, схемы, тесты) | P1 переведён из "создать" в "проверить/довести"; следующий агент не должен пересоздавать уже реализованную основу |
| HIGH-8 | high | P3 | План требовал `jsonschema`, но `requirements.txt` его не содержит | DoD P3 теперь требует либо добавить pinned dependency в `requirements.txt`, либо использовать минимальную structural validation без новой зависимости |
