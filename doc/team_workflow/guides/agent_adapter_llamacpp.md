# Адаптер: llama.cpp / Qwen3-Coder-Next

Файл предназначен для разработки локального `agent_adapter_llamacpp` и
будущей интеграции локальной coding-модели в team workflow.

Целевая модель первого этапа: `qwen/qwen3-coder-next`. Основной режим:
локальная разработка кода приложения через llama.cpp OpenAI-compatible server.

---

## Значения плейсхолдеров

```yaml
MAX_PARALLEL: 1

AGENT_SPAWN: |
  llama.cpp adapter на первом этапе работает как один последовательный
  локальный coding-агент: узкий doc/current_task.md -> Developer-style patch
  по write-set -> отдельный Tester/Reviewer gate в новом context.

PARALLEL_SYNTAX: |
  [SEQUENTIAL - llama.cpp adapter не должен иметь native parallel sub-agents]
  Если нужны Architect и Designer, запускать их отдельными sessions. Для
  локальной coding-модели предпочтительнее не поручать широкий Step 3, а
  использовать ее как Step 4 Developer executor.

READ_FILE: |
  Читать файлы через явные shell-команды из корня проекта:
    rg -n "pattern" path/to/file.py
    Get-Content path/to/file.py | Select-Object -First 120
    Get-Content path/to/file.py | Select-Object -Last 120
  Для крупных файлов запрещать full-read. Давать модели только signatures,
  нужный диапазон строк или результаты rg по safe_hint из token registry.

WRITE_FILE: |
  Стартовый режим: модель возвращает только fenced unified diff. Adapter
  извлекает changed paths, проверяет WRITE_SET, делает git apply --check,
  применяет patch через controlled layer и запускает targeted checks.
  Workflow artifact execution_contract.md собирается adapter'ом только из
  фактического git diff, команд, exit code и test evidence.

RUN_CMD: |
  Команды запускать из корня проекта, Python только через venv:
    .\.venv\Scripts\python.exe -m pytest tests/test_<area>.py
    .\.venv\Scripts\python.exe scripts/check_readset.py <files>
    .\.venv\Scripts\python.exe scripts/lint_agent_prompts.py
    git diff --name-only
  Полный suite не запускать без явного запроса. Для локального агента лучше
  один маленький test bundle за итерацию.
```

---

## 1. Назначение адаптера

`agent_adapter_llamacpp` нужен не как замена Cursor/Claude/Codex во всем
конвейере, а как локальный исполнитель узких coding-задач:

- исправить баг в 1-3 файлах;
- добавить небольшой сервисный метод с тестом;
- обновить локальную документацию по уже понятному изменению;
- выполнить cleanup в пределах строгого write-set;
- быстро получить patch без внешних API и без расходов на cloud tokens.

`qwen/qwen3-coder-next` - лучший основной локальный coding-кандидат, но
стартовый дизайн должен учитывать менее надежный long-context, риск потери
инструкций и слабый self-review на длинных пакетах. Скорость и latency зависят
от quant/offload; перед auto-selection нужно измерять duration, tokens/sec и
time-to-first-token на реальных задачах.

---

## 2. Рекомендуемая архитектура

### Phase 0 - ручной adapter-only режим

Создать и использовать `agent_adapter_llamacpp.md` как синтаксический профиль
для `generate_orchestration_prompt.md`, но не включать автоматический trigger.

Режим работы:

1. `workflow.py` генерирует `doc/current_task.md`.
2. Человек или оболочка отправляет сжатый prompt в локальный llama.cpp server.
3. Модель возвращает patch proposal.
4. Изменения применяются вручную или controlled patch layer.
5. targeted tests запускаются обычным проектным способом.
6. По факту выполнения пишется `execution_contract.md`.

Это самый безопасный старт: можно измерить качество модели без риска, что
автоматический trigger начнет портить write-set.

### Phase 1 - локальный trigger

После 5-10 успешных ручных прогонов добавить `scripts/llamacpp_agent_trigger.ts`
по паттерну существующих TypeScript triggers: task -> llama.cpp `/v1` ->
patch proposal -> controlled apply -> targeted tests -> contract.

Статус на 2026-06-21: Phase 1 trigger реализован, прошел live smoke в
disposable repo и затем hardened live smoke после усиления system prompt.
Ключевое исправление после первого live run: локальная OpenAI-compatible
API-модель не имеет file tools, поэтому trigger сам извлекает `Read-set` из
`current_task.md`, читает файлы из repo и добавляет
`CONTEXT EXCERPTS FROM READ_SET` в prompt с лимитами
`LLAMACPP_CONTEXT_MAX_CHARS` и `LLAMACPP_CONTEXT_FILE_MAX_CHARS`. Prompt теперь
явно запрещает ссылаться на содержимое файлов, отсутствующее в context excerpts.

Почему TypeScript: текущая trigger-инфраструктура уже использует
`scripts/_trigger_shared.ts`, `trigger_registry.ts`, heartbeat, metrics и
spawn через `trigger_orchestrator.ts`. Новый trigger лучше встроить туда, а не
создавать отдельную Python-ветку.

### Phase 2 - orchestrator integration

Добавить в `trigger_registry.ts` новый executor:

```text
id: llamacpp
roles: executor, local_reviewer_lite
strengths: local coding, narrow patches, no cloud dependency
limits: slow, context-sensitive, no broad planning by default
```

Обнаружение доступности:

- `LLAMACPP_BASE_URL`, default `http://127.0.0.1:8080/v1`;
- `LLAMACPP_MODEL`, default `qwen/qwen3-coder-next`;
- primary health/model check: `GET /v1/models`;
- optional `LLAMACPP_API_KEY` для совместимости с OpenAI clients.

`LLAMACPP_MODEL` должен точно совпадать с llama.cpp `--alias`. Для этого
trigger проверяет, что `/v1/models` содержит `id == "qwen/qwen3-coder-next"`
или alias с тем же значением. `GET /health` допустим только как дополнительная
проверка процесса, но не заменяет проверку model id.

В strategy matrix локальный trigger должен быть fallback/primary только для
low-risk и части medium-risk задач. High-risk пакеты не отдавать ему без
planner/reviewer gate.

---

## 3. Контракт trigger

Минимальный `llamacpp_agent_trigger.ts` должен:

1. Читать task path из argv или `WORKFLOW_CURRENT_TASK_PATH`.
2. Сжимать prompt до локального budget.
3. Проверять `/v1/models` и точное совпадение `LLAMACPP_MODEL` с alias.
4. Отправлять запрос в llama.cpp server.
5. Требовать structured response:
   - `SUMMARY`;
   - `READ_SET`;
   - `WRITE_SET`;
   - `PATCH`;
   - `TESTS`;
   - `RISKS`;
   - `EXECUTION_CONTRACT_DRAFT`.
6. Проверять порядок секций и отсутствие `<think>`.
7. Извлекать fenced unified diff из `PATCH`.
8. Валидировать changed paths:
   - `WRITE_SET=[]` + любой real diff = hard fail;
   - changed paths must be subset of `WRITE_SET`.
9. Нормализовать LF/BOM и hunk counts.
10. Выполнять `git apply --check`; при line-count дефектах допустим
    `git apply --recount --check`.
11. Делать не больше 1 repair attempt; затем hard fail.
12. Применять patch только через controlled apply.
13. Запускать targeted tests.
14. Писать `execution_contract.md` только из реального diff/test evidence.
15. Писать metrics в `trigger_metrics.jsonl`.

Нельзя считать успешным ответ модели без changed files, test evidence или
явного documented no-op. Файл `execution_contract.md` со статусом `STARTED`
должен обрабатываться так же строго, как в Cursor trigger.

Модель может дать `EXECUTION_CONTRACT_DRAFT`, но это только черновик. Финальный
contract формирует adapter из фактов: примененный diff, changed files, команды,
exit codes, test output и known risks.

---

## 4. Prompt budget для локальной модели

Стартовые лимиты лучше сделать консервативными, даже если сервер поддерживает
большой context window.

| Параметр | Стартовое значение | Причина |
|---|---:|---|
| `LLAMACPP_MAX_INPUT_TOKENS` | 24000 | меньше риск забыть write-set и DoD |
| `LLAMACPP_TARGET_INPUT_TOKENS` | 12000 | совпадает с project token safety target |
| `LLAMACPP_MAX_OUTPUT_TOKENS` | 6000 | достаточно для patch + contract |
| `LLAMACPP_TEMPERATURE` | 0.15-0.25 | стабильнее для кода |
| `LLAMACPP_TOP_P` | 0.8-0.95 | оставить немного вариативности |
| `LLAMACPP_REPEAT_PENALTY` | 1.05-1.15 | снижает зацикливание |
| `LLAMACPP_TIMEOUT_MS` | 900000 | локальная генерация может быть долгой |
| `LLAMACPP_CONTEXT_MAX_CHARS` | 60000 | общий лимит read-set excerpts |
| `LLAMACPP_CONTEXT_FILE_MAX_CHARS` | 20000 | лимит одного файла из read-set |

Если модель начинает терять инструкции, снижать не temperature, а размер
prompt: меньше файлов, меньше истории, отдельные sessions для ролей.

Budget `24000 + 6000` требует server context около `32768`. При `ctx-size
16384` trigger должен снижать input/output caps или останавливать run до
запроса модели.

---

## 5. Контекстная стратегия

Для локального агента главный выигрыш дает не размер окна, а качество упаковки
контекста.

### Что давать в prompt

Давать `doc/current_task.md`, 3-5 файлов или excerpts, expected tests и
compact hard constraints. Для больших файлов использовать signatures, `rg`
и диапазоны строк. Не давать весь backlog, все `doc/conventions*.md`, старые
обсуждения, несколько ролей одновременно и full diff репозитория.

### Рекомендуемый prompt scaffold

```text
You are local llama.cpp coding executor for hometutor.
Model: qwen/qwen3-coder-next. Mode: narrow patch executor.
Obey write-set, AGENTS.md, doc/conventions*.md, and venv Python command.
Input: <doc/current_task.md> + <only relevant snippets>.
Return: SUMMARY, READ_SET, WRITE_SET, PATCH, TESTS, RISKS,
EXECUTION_CONTRACT_DRAFT.
```

---

## 6. Режимы применения patch

### Безопасный стартовый режим

Модель не пишет в файловую систему. Она возвращает fenced unified diff. Adapter:

1. проверяет paths против write-set;
2. нормализует line endings и hunk counts;
3. выполняет `git apply --check`;
4. при corrupt hunk counts пробует `git apply --recount --check`;
5. применяет patch;
6. показывает `git diff --name-only`;
7. запускает targeted tests;
8. собирает `execution_contract.md` из фактов.

### Автоматический режим позже

Разрешить trigger самому применять patch только после появления parser-based
валидации diff, hard fail на выход за write-set, запрета binary/generated
правок без явной команды, normal/recount apply gates и metrics по каждой
итерации. Rollback - только своих изменений, без `git reset --hard`.

---

## 7. Критерии маршрутизации

Хорошие задачи для `llamacpp`: low-risk bugfix, один сервис + один тест,
локальная документация, маленькая typing/validation правка, prompts/docs без
runtime side effects.

Плохие задачи для первого этапа: schema/migration/user_state persistence,
security/guardrails/input validation, multi-router API contract, большие UI
перестройки, provider/config changes, write-set больше 5 файлов или задачи,
где нужен длинный закрытый history context.

Для medium-risk задач использовать связку:

```text
DeepSeek/API or human plan -> llama.cpp execute -> separate review/test gate
```

Для high-risk задач:

```text
llama.cpp только как patch assistant, не как autonomous executor
```

---

## 8. Метрики качества

В `trigger_metrics.jsonl` для llama.cpp стоит писать: event/model/base_url,
input/output token estimates, tokens/sec, time-to-first-token, duration,
patch files, tests run/status, contract status, hunk normalization/recount flags,
repair/fallback flags и failure kind.

Минимальные KPI перед включением в orchestrator auto-selection:

- 5 успешных low-risk задач подряд;
- 0 выходов за write-set;
- не менее 80% задач проходят targeted tests без ручного исправления patch;
- средняя длительность приемлема для локального цикла;
- ни одного `execution_contract.md` без реального evidence.
- 0 successful runs с `adapter_fallback_used=True`, если fallback явно не
  разрешен для task class. Fallback - не failure, но отдельный quality signal.

---

## 9. Локальный запуск llama.cpp server

Workflow ожидает OpenAI-compatible endpoint llama.cpp (`/v1`) и model alias,
совпадающий с `LLAMACPP_MODEL`.

Рекомендуемый launcher для текущего локального server pack:

```powershell
cd D:\AI\llama_cpp_server_pack_v1
pwsh -ExecutionPolicy Bypass -File .\Start-Qwen3-Coder-Next-LlamaCpp-AgentAdapter-AutoFit.ps1 `
  -StopExisting `
  -PersistTriggerEnv
```

Если autodetect не нашел GGUF:

```powershell
pwsh -ExecutionPolicy Bypass -File .\Start-Qwen3-Coder-Next-LlamaCpp-AgentAdapter-AutoFit.ps1 `
  -ModelPath "D:\AI\models\gguf\Qwen3-Coder-Next-Q4_K_M.gguf" `
  -StopExisting `
  -PersistTriggerEnv
```

Стартовый launch contract:

| Параметр | Значение |
|---|---|
| alias | `qwen/qwen3-coder-next` |
| ctx-size | `32768` |
| parallel | `1` |
| batch-size | `2048` |
| ubatch-size | `512` |
| flash-attn | `auto` |
| KV cache | `q8_0/q8_0` |
| reasoning | `off` |
| metrics | `on` |
| temperature | `0.20` |
| top_p | `0.90` |
| repeatPenalty | `1.10` |

Для 2x RTX 5070 Ti 16GB фактически подтвердился AutoFit-профиль: не задавать
опасные fixed параметры `--n-gpu-layers 999`, `--tensor-split 1,1`,
`--split-mode layer`. Сервер должен сам подобрать offload. Если Q4_K_M/UD-Q4_K_M
уходит в paging или OOM, снижать quant: Q4_K_S/UD-Q4_K_S, затем Q3_K_M.

Trigger env:

```powershell
$env:LLAMACPP_BASE_URL = "http://127.0.0.1:8080/v1"
$env:LLAMACPP_MODEL = "qwen/qwen3-coder-next"
$env:LLAMACPP_MAX_INPUT_TOKENS = "24000"
$env:LLAMACPP_MAX_OUTPUT_TOKENS = "6000"
$env:LLAMACPP_TIMEOUT_MS = "900000"
```

Smoke для alias:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/models | ConvertTo-Json -Depth 5
```

Критерий: `data[].id` или `aliases[]` содержит `qwen/qwen3-coder-next`, а
`meta.n_ctx` не меньше `32768`.

Latest validation 2026-06-28:

```text
coding benchmark: ACCEPTED_SINGLE_MODEL_CANDIDATE
benchmark date: 2026-06-28
score: 94.89
quality: 13.5/13.5
avg tps: 63.2
decision: accepted for local coding benchmark

local trigger endpoint: http://127.0.0.1:8080/v1
/v1/models: PASS
model alias: qwen/qwen3-coder-next
ctx: 32768
identity smoke: PASS
response.model: qwen/qwen3-coder-next
marker: CODER_NEXT_OK
finish_reason: stop
identity latency_ms: 1230
strict no-op trigger smoke: PASS
disposable real patch trigger rehearsal: PASS
write_set_validation: PASS
git_apply_check: PASS
targeted_tests: PASS
execution_contract.md: generated from evidence
hunk_count_normalized: True
recount_used: False
repair_used: False
adapter_fallback_used: False
trigger regression suite: 7 files / 97 tests PASS
```

Verdict: `qwen/qwen3-coder-next` is accepted as the current single local
coding-trigger candidate for controlled low-risk patch execution. Keep the
existing gates: exact alias check, `ctx >= 32768`, strict structured sections,
no hidden thinking, fenced diff, write-set subset validation, `git apply --check`,
targeted tests, and evidence-only `execution_contract.md`.

Validated locally:

```text
# [two-root] Two-repo project: resolve app/** and requirements.txt against CODE_ROOT
# (editable install of `hometutor`: `pip show hometutor` -> "Editable project location");
# resolve doc/**, tests/**, scripts/** against the current cwd (DOCS_ROOT).
# Run git per-root: `git -C <CODE_ROOT> ...` for app code, `git -C <cwd> ...` for docs/tests.
strict no-op smoke: PASS
disposable real patch smoke: PASS
llamacpp_agent_trigger live smoke: PASS
hardened live smoke: PASS
model: qwen/qwen3-coder-next
ctx: 32768
read-set context injection: PASS
changed path: app/math_utils.py
WRITE_SET: ["app/math_utils.py"]
hunk_count_normalized: True
git_apply_check: PASS
targeted_tests: PASS
execution_contract.md: generated from evidence
metrics: recount_used=false, repair_used=false, adapter_fallback_used=false
context_chars: 725
context_files_count: 2
context_truncated: false
duration_ms: 9839
```

Hardened live smoke дополнительно подтвердил:

- no-tools system prompt contract: модель использует только task text и
  `CONTEXT EXCERPTS FROM READ_SET`;
- `TESTS` allowlist поддерживает проектный pytest и
  `npm.cmd run test:trigger -- tests/trigger/<name>.test.ts`;
- shell chaining в `TESTS` отсекается (`|`, `;`, `&`, backticks);
- `HTTP 503 Loading model` обрабатывается trigger-side retry/backoff
  `3s -> 8s -> 15s`, затем `server_loading_timeout`.

---

## 10. Практическое руководство

### Первый рабочий сценарий

1. Выбрать low-risk пакет с write-set до 3 файлов.
2. Сгенерировать `doc/current_task.md` обычным workflow.
3. Сжать read-set через `rg` и фрагменты файлов.
4. Отправить scaffold из раздела 5 в локальную модель.
5. Adapter нормализует diff, выполняет `git apply --check`, применяет patch,
   запускает targeted tests и проверяет `git diff --name-only`.
6. Записать `execution_contract.md` с evidence.
7. Запустить `run_autonomous.py --post-agent` через существующий workflow.

После появления trigger использовать его через `trigger_orchestrator.ts`.
Для отладки оставить прямой вызов `npx tsx scripts/llamacpp_agent_trigger.ts
doc/current_task.md`.

Перед первой реальной задачей обязательны два smoke:

- strict no-op: sections, order, no `<think>`, `PATCH` = `# NO_CHANGES`;
- disposable real patch: failing test -> model patch -> write-set validation ->
  hunk normalization -> `git apply --check` -> apply -> targeted tests.

---

## 11. Failure modes и реакции

Hard fail на выход за write-set, `WRITE_SET=[]` + real diff, contract без
evidence, invalid section order, `<think>` и invalid patch. При corrupt hunk
counts использовать normalize/recount fallback, но не больше 1 repair attempt.
При `HTTP 503 Loading model` trigger делает короткий retry/backoff; после
исчерпания попыток возвращает `server_loading_timeout`. При медленной генерации
уменьшать read-set/output cap. Self-review держать отдельным gate.

Optional last-resort fallback для простых one-line patches допустим только в
controlled adapter layer: changed path ровно один, path входит в `WRITE_SET`,
removed line ровно одна, added line ровно одна, removed line встречается в файле
ровно один раз, targeted tests обязательны.

На 2026-06-21 в `scripts/llamacpp_agent_trigger.ts` реализован happy-path
compiler loop: sections/order/no-think, no-tools prompt contract, read-set
context injection, write-set gate, hunk normalization, `git apply --check/apply`,
targeted tests и contract from evidence. Не считать закрытыми до отдельной
задачи: модельный repair attempt и guarded one-line fallback; они остаются
backlog перед расширением за пределы Phase 1 low-risk.

---

## 12. Definition of Done для разработки adapter

- `agent_adapter_llamacpp.md` добавлен в guides.
- `llamacpp_agent_trigger.ts` использует `_trigger_shared.ts`.
- Direct debug/live run работает через `npx tsx scripts/llamacpp_agent_trigger.ts`.
- Перед orchestrator auto-selection: `prompt_utils.py` знает alias `llamacpp`,
  `trigger_registry.ts` содержит capabilities/limits, а orchestrator выбирает
  llama.cpp только для low-risk по умолчанию.
- Есть `/v1/models` alias check.
- Есть strict no-op smoke.
- Есть real patch smoke в disposable repo.
- Есть hardened live smoke после no-tools prompt hardening, npm trigger-test
  allowlist и `HTTP 503 Loading model` retry.
- Есть negative tests: write-set violation, empty patch, STARTED-only contract,
  timeout, invalid response, `<think>`, bad section order, corrupt patch,
  unsafe targeted test commands.
- Метрики пишутся в общий `trigger_metrics.jsonl`.

---

## 13. Главная рекомендация

Начинать не с полной автономности, а с локального "patch executor with gates".
`qwen/qwen3-coder-next` стоит использовать как сильного локального coding
кандидата, но качество workflow даст не сама модель, а жесткая упаковка задачи:
малый write-set, короткий read-set, structured output, controlled patch apply,
targeted tests и отдельный review gate.
