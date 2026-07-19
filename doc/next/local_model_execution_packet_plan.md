# Local Model Trust Contour — Execution Packet Plan

**Версия:** 1.1 (2026-07-19, после контр-аудита) · **База проверки:** hometutor-studio
HEAD `545d155` «113» · hometutor HEAD `c5182b9` «357»
**Источник:** эволюционный разбор №27 «Протокол суда пишет обвиняемый»
(`../presentations/evolutionary_analyses/27_local_model_trust_contour.html`,
артефакт https://claude.ai/code/artifact/4851e86d-8dc1-4b01-9f68-b75d6539138f)

Этот план — runtime-handoff. Перед кодом сверить фактический HEAD: detail-планы серии
могут отставать.

**Изменения v1.1:** принят контр-аудит (7 критичных + 8 дополнительных замечаний);
главное архитектурное решение — **контур локального исполнения переносится в
`D:\Projects\hometutor`** (`scripts/agent_exec/`), studio остаётся домом backlog-машины
и процессных артефактов (пакеты, планы, разборы). Полная диспозиция по каждому
замечанию — в разделе «Ответ на аудит» ниже.

---

## Контекст: диагноз разбора №27 (не изменился)

Локальный coding-контур для `qwen3-coder-next-q4ks` физически работает: живой прогон
strict no-op smoke против production-сервера прошёл за 2,9 с и записал evidence-only
`execution_contract.md`; 98/98 unit-тестов триггера зелёные. Но с параметрами по
умолчанию тот же прогон падает за 54 мс — `DEFAULT_MODEL` в
`scripts/llamacpp_agent_trigger.ts:22` всё ещё `qwen/qwen3-coder-next`, а сервер отдаёт
только `qwen3-coder-next-q4ks`. Порождающая причина — **trust inversion**:
`validatePatchAgainstWriteSet` (строка 748) сверяет diff с декларацией *самой модели*,
`extractTestCommands` (строка 804) берёт targeted tests из того же ответа; извлечения
authoritative write-set/tests из задачи нет вообще. Экземпляр `PAIN-02`.

---

## Ответ на аудит 2026-07-19 (диспозиция по каждому замечанию)

### Критичные

| # | Замечание | Вердикт | Как исправлено в v1.1 |
|---|---|---|---|
| 1 | Не определено, где запускается trigger; `process.cwd()`-семантика при Runner в studio и `target_repo=hometutor` | **Принято** | Решается структурно переносом контура в hometutor (`scripts/agent_exec/`): для основного класса пакетов cwd = repo диффа by construction. Для любых пакетов Runner обязан спавнить trigger с явным `cwd = target_repo` и передавать абсолютные пути task/contract/metrics через env. Дополнительный аргумент за перенос: при spawn из cwd=hometutor `npx tsx` не найдёт tsx в node_modules studio — кросс-репозиторный запуск требовал бы хрупких абсолютных путей к бинарям |
| 2 | Чтение last-row общего `llamacpp_agent_trigger.jsonl` небезопасно (stale/concurrent); ошибка записи метрик нефатальна | **Принято** | Per-run receipt: Runner генерирует `run_id` (uuid) и передаёт уникальный путь метрик через уже существующий env-override `LLAMACPP_TRIGGER_TRIGGER_METRICS_PATH` (механизм проверен живым прогоном 2026-07-19 — метрики ушли в scratchpad-файл). Runner читает **только** свой receipt-файл; пустой/отсутствующий receipt = FAIL (нет evidence — нет успеха). Ledger-запись содержит `packet_id + run_id`, сопоставление точное, не last-row |
| 3 | Пути из пакета не защищены: нет repo-allowlist, realpath containment, запрета absolute/UNC/drive/traversal/symlink; `forbidden_areas` создаёт planner-модель | **Принято** | Новый детерминированный модуль `packet_policy.ts` (см. P0-2): (a) allowlist репозиториев — только `D:/Projects/hometutor` и `D:/Projects/hometutor-studio`; (b) каждый путь read/write-set: relative-only, запрет `..`, drive-префиксов, UNC, `realpath(target_repo/path)` обязан лежать внутри `realpath(target_repo)` (закрывает symlink/junction escape); (c) **встроенный в код денилист** (config/provider/guardrails/auth/migrations/.github/workflows/`scripts/agent_exec/**`/kilo-конфиги/.env*) — `forbidden_areas` из пакета только дополняет его, planner не является границей безопасности |
| 4 | Golden path конфликтует со studio-правилами: `backlog_registry.yaml` = SSoT, `workflow.py` = предпочтительный маршрут | **Принято** (подтверждено: `AGENTS.md:138` «единственный источник истины», `:162` «предпочитать ручному выбору») | Перенос контура в hometutor выводит packet-путь из-под studio-SSoT: пакеты авторятся в studio как процессные артефакты (`doc/packets/`), исполняются в hometutor. В P0-2 добавлен ADR (`doc/team_workflow/adr_execution_packets.md` + строка в `AGENTS.md`): два маршрута сосуществуют — backlog-driven (workflow.py, SSoT registry) и plan-driven (packets); опциональное поле `backlog_ref` связывает пакет с зарегистрированным backlog-пакетом, когда работа backlog-driven |
| 5 | `targeted_tests_failed` и др. детерминированные ошибки не должны автоматически уходить в cloud fallback (нарушение контракта integration report §12) | **Принято** | Класс «quality fallback» удалён. Детерминированные провалы (targeted_tests_failed, git_apply_failed, invalid sections, no_allowed_tests) **завершают local run как FAILED**; результат фиксируется в ledger. Повторное облачное исполнение — только как новый явно зарегистрированный run (новый `run_id`, ссылка `retry_of`), решение принимает router/человек, не автоматика. Автоматический fallback остаётся только для transient-класса (server_unreachable, 503 после backoff, timeout до ответа, spawn failure) |
| 6 | `# NO_CHANGES` при недостатке контекста возвращается как `status=ok` и загрязняет VLCR | **Принято** | Введён исход `blocked_no_changes`: если пакет change-expected (есть failing test / expected_patch_size), а diff = NO_CHANGES — Runner классифицирует run как `blocked_no_changes`, он исключается и из числителя, и из знаменателя VLCR (отдельная метрика blocked rate). Формула VLCR зафиксирована ниже |
| 7 | Dirty baseline не учитывает untracked; проверка полного `git diff` конфликтует с разрешёнными пользовательскими изменениями вне write-set | **Принято** | Baseline = `git status --porcelain=v1 -uall` (tracked + untracked) до apply; hard fail только при пересечении baseline-изменений с write-set. Post-verify считает **дельту относительно baseline, ограниченную write-set** — пользовательские изменения вне write-set не мешают и не попадают в contract. Отдельно закрывается смежный дефект: новые файлы, созданные патчем, не видны в `git diff --name-only` (untracked) — changed-files брать из diff-путей патча + дельты статуса, не из голого git diff |

### Дополнительные

| # | Замечание | Вердикт | Как исправлено |
|---|---|---|---|
| 8 | `context_budget_tokens: 24000` нарушает studio-правило 20K | **Принято** (подтверждено: `doc/token_safety_registry.json:6` → `"hard_input_tokens": 20000`) | Схема: `context_budget_tokens ≤ 20000` (hard cap, default 12000 = target из guide §4). Runner выставляет `LLAMACPP_MAX_INPUT_TOKENS = context_budget_tokens` для каждого run; trigger-дефолт 24000 остаётся только как верхний потолок вне packet-пути |
| 9 | `read_set` из одних путей недостаточен: trigger режет начало файла | **Принято** | Элемент read_set — объект `{path, sha256, ranges?}`; sha256 обязателен (детект stale-пакета при `HEAD != target_commit` по содержимому), ranges/symbols — опционально в v0. Excerpts по ranges рендерит Runner в task-view; naive-slicing триггера остаётся только fallback'ом |
| 10 | Не копировать «упрощённый» `classifyRiskWithScore` — вторая расходящаяся policy | **Принято** | Пересчёт риска пакета — **новый** модуль `scripts/agent_exec/packet_policy.ts` (единственный источник packet-политики: risk recompute по детерминированным сигналам, routing-пороги, денилист). Явно НЕ импортировать и НЕ копировать `classifyRiskWithScore` — тот остаётся только в legacy-оркестраторе studio |
| 11 | Противоречие: «подпакеты Runner можно доверить локальной модели» vs «самомодификация запрещена навсегда» | **Принято** | Разрешение удалено. Весь код контура (trigger/runner/policy/tests контура) — только cloud/human, без исключений. `scripts/agent_exec/**` внесён во встроенный денилист write-set (см. #3) |
| 12 | Порог ≥70% слабее принятого KPI ≥80%; формула VLCR и учёт no-op/reject/fallback не зафиксированы | **Принято** | Target приведён к guide §8: **≥80%**. Формула и таксономия исходов зафиксированы ниже |
| 13 | Путь `.kilo/kilo.jsonc` неверен — файл в корне как `kilo.jsonc` | **Отклонено частично** (проверено live 2026-07-19) | В hometutor существуют **оба** файла: корневой `kilo.jsonc` содержит только `instructions: [".kilo/rules/hometutor-agent.md"]`, а модель `llamacpp-local/qwen3-coder-next-q4ks` задаётся именно в `.kilo/kilo.jsonc`. Цитата разбора корректна для утверждения о модели; формулировка уточнена: «конфиг разнесён по kilo.jsonc (instructions) и .kilo/kilo.jsonc (model)» |
| 14 | P0-2 не содержит точной команды targeted tests | **Принято** | Зафиксированы точные команды (см. P0-1/P0-2 Tests/DoD) |
| 15 | «Synthetic benchmark» — неточная формулировка | **Принято** | Заменено на точную: Home Coder Benchmark — исполняемые задачи со скрытыми тестами, но **не из репозитория hometutor**; проблема — распределение задач, а не «синтетичность» |

---

## Решение о переносе: контур исполнения живёт в hometutor

**Вопрос владельца:** перенести ли `llamacpp_agent_trigger` и скрипты ai-agent workflow
в `D:\Projects\hometutor` для упрощения процесса?

**Вердикт: да, но со строгим скоупом.** Переносится **контур локального исполнения
пакетов**: `llamacpp_agent_trigger.ts` + минимальный shared-рантайм + новый Runner +
их тесты → `hometutor/scripts/agent_exec/`. **Не переносятся:** `workflow.py`,
cursor/deepseek-триггеры, `trigger_orchestrator.ts`, `_trigger_shared.ts` — это
backlog-машина studio, она остаётся на месте и продолжает работать как раньше.

Почему перенос, а не `cwd`-параметризация из studio:

1. **Структурно закрывает аудит #1:** основной target_repo — hometutor; исполнение
   в том же репозитории убирает целый класс cwd/path-ошибок by construction, а не
   параметром. Кросс-репо spawn дополнительно хрупок: `npx tsx` из cwd=hometutor не
   резолвит tsx из node_modules studio.
2. **Закрывает аудит #4:** packet-путь выходит из-под studio-SSoT (`backlog_registry` +
   workflow.py); в hometutor его регулирует собственный CLAUDE.md.
3. Всё окружение исполнения уже там: `.venv` + pytest (targeted tests пакетов),
   Kilo-конфиг с верным production alias, logs/.
4. Цель владельца — упрощение: один репозиторий для «кодим hometutor локальной моделью».

Цена переноса (признана, принята):

- В hometutor нет корневой node-инфраструктуры (проверено: `package.json`/`node_modules`
  отсутствуют) — P0-1 добавляет минимальный корневой `package.json` (devDeps: tsx,
  vitest, pinned) + `node_modules` в `.gitignore`. Doc-sync hometutor CLAUDE.md обязателен.
- `_trigger_shared.ts` (785 строк) общий для cursor/deepseek — его не переносим.
  В hometutor выделяется **урезанный** `scripts/agent_exec/_exec_shared.ts` (только
  используемое llamacpp-триггером: runTrigger-каркас, logger, metrics, contract-хелперы,
  ~300 строк). Это осознанная, документированная граница двух рантаймов (packet-контур ↔
  legacy studio triggers), а не молчаливый дрейф; сведение — кандидат P2.
- Анти-PAIN-01: studio-копия `llamacpp_agent_trigger.ts` + её тест **удаляются** в том же
  P0-1 (git rm; история git — механизм отката) **после** зелёных тестов в hometutor и
  с явным owner sign-off (permanent delete — прерогатива владельца). До sign-off —
  deprecation-заголовок в файле. Legacy-вызов из workflow.py остаётся возможен:
  `--trigger-cmd "npx tsx D:\Projects\hometutor\scripts\agent_exec\llamacpp_agent_trigger.ts"`.

Разделение ответственности после переноса:

```text
hometutor-studio: пакеты (doc/packets/), планы, разборы, ADR, backlog-машина
hometutor:        контур исполнения (scripts/agent_exec/), receipts/ledger (logs/agent_exec/)
```

---

## wave-trust-hardening (P0 — два хода, порядок строгий: P0-1 → P0-2)

### P0-1. Relocation + Authoritative Trigger Hardening

- **Problem:** вход контура мёртв (устаревший alias), выход доверяет декларации модели
  вместо задачи, а сам контур живёт не в том репозитории, где применяет диффы.
- **Evidence:** `scripts/llamacpp_agent_trigger.ts:22` (`DEFAULT_MODEL`); `:318,748`
  (validate против model-WRITE_SET); `:384,804` (tests из ответа модели); `:633`
  (input-budget без gate); `:728` (нет response.model/finish_reason/reasoning-gate);
  `:857` (нет baseline, untracked-слепота). Живой прогон: default alias → `exit 2`/54мс;
  corrected → PASS/2860мс.
- **Proposed:**
  1. Создать `hometutor/scripts/agent_exec/`: перенесённый `llamacpp_agent_trigger.ts`,
     урезанный `_exec_shared.ts`, тесты в `scripts/agent_exec/tests/`. Корневой
     `package.json` (tsx, vitest, pinned; script `"test:agent": "vitest run scripts/agent_exec/tests/"`),
     `node_modules` в `.gitignore`.
  2. `DEFAULT_MODEL` → `"qwen3-coder-next-q4ks"`.
  3. `extractTaskWriteSet(prompt)` (на базе перенесённого протестированного
     `extractMarkdownListSection`); gates: `modelWriteSet ⊆ taskWriteSet` → иначе
     `model_write_set_widening`; `changedPaths ⊆ taskWriteSet`.
  4. `extractTaskTestCommands(prompt)`; hard fail `model_proposed_unapproved_tests`;
     исполняются только task-команды. Allowlist обновить под hometutor:
     `.\.venv\Scripts\python.exe -m pytest ...` + `npm.cmd run test:agent -- scripts/agent_exec/tests/<name>.test.ts`.
  5. Hard gate `estimatePromptTokensApprox(packed) <= maxInputTokens` →
     `input_budget_exceeded` (до отправки запроса).
  6. Response-gates: `response.model === model`; `finish_reason === "stop"`;
     отсутствие `reasoning_content`/`reasoning`.
  7. Baseline-gate: снимок `git status --porcelain=v1 -uall` до apply; пересечение с
     write-set → `dirty_write_set` hard fail; changed-files после apply = дельта к
     baseline ∪ пути из diff (закрывает untracked-слепоту новых файлов).
  8. Явный флаг `no_changes: true` в fields при NO_CHANGES-исходе (для классификации
     `blocked_no_changes` Runner'ом в P0-2).
  9. Studio: deprecation-заголовок в старом файле; после зелёного DoD и owner sign-off —
     `git rm scripts/llamacpp_agent_trigger.ts tests/trigger/llamacpp_agent_trigger.test.ts`
     + правка `package.json` studio не требуется (`test:trigger` глоб останется валидным).
- **Files (hometutor):** `scripts/agent_exec/llamacpp_agent_trigger.ts`,
  `scripts/agent_exec/_exec_shared.ts`, `scripts/agent_exec/tests/llamacpp_agent_trigger.test.ts`,
  `package.json`, `.gitignore`, `CLAUDE.md` (doc-sync: новый каталог и команда тестов).
  **Files (studio):** `scripts/llamacpp_agent_trigger.ts` (deprecate→delete),
  `tests/trigger/llamacpp_agent_trigger.test.ts` (delete),
  `doc/team_workflow/guides/agent_adapter_llamacpp.md` (alias, 512/128,
  `--no-mmap --prio 2`, новый путь контура), `.env.example`.
- **Tests:** `npm.cmd run test:agent` (hometutor) — перенесённые 20+ кейсов и новые
  негативные: model-write-set шире task; model-tests вне task-tests; input сверх бюджета;
  `response.model` mismatch; `finish_reason != stop`; dirty baseline (tracked и untracked);
  untracked-файл, созданный патчем, попадает в changed-files.
- **DoD:** `npm.cmd run test:agent` зелёный; live strict no-op против production runtime
  из cwd=hometutor PASS; disposable real-patch smoke (1 файл, 1 failing pytest) PASS;
  guide/`.env.example` без устаревших alias/batch; studio-копия удалена (после sign-off)
  или несёт deprecation-заголовок.
- **Rollback:** hometutor — revert коммита; studio — restore из git-истории.
- **Исполнитель:** cloud/human. Локальной модели запрещено касаться `scripts/agent_exec/**`.

### P0-2. Execution Packet Runner v0 + ledger + ADR

- **Problem:** нет пути «готовый план → маленький проверяемый пакет → local model →
  evidence» вне backlog-orchestration; нечем измерить VLCR (0 authoritative-прогонов
  в истории — 6 строк метрик, все smoke 2026-06-29); packet-путь не легализован
  относительно studio-SSoT.
- **Evidence:** `workflow.py::_write_orchestration_current_task:314` (генерация задач
  только из backlog); `trigger_registry.ts::TRIGGER_REGISTRY:65-91` (llamacpp
  отсутствует); `AGENTS.md:138,162` (SSoT + предпочтительность workflow.py);
  раздвоение метрик (orchestrator читает `trigger_metrics.jsonl`, llamacpp пишет свой).
- **Proposed:** `hometutor/scripts/agent_exec/run_execution_packet.ts` +
  `scripts/agent_exec/packet_policy.ts`:
  1. Parse YAML-frontmatter пакета (схема ниже; путь к пакету — аргумент, обычно
     `D:\Projects\hometutor-studio\doc\packets\PKT-*.md`).
  2. **packet_policy.ts** (единственный источник политики): allowlist репозиториев;
     path-safety (relative-only, no `..`/drive/UNC, realpath containment внутри
     target_repo, symlink/junction escape reject); встроенный денилист
     (`app/config.py`, `app/provider.py`, `app/provider_openai.py`, `app/guardrails.py`,
     `app/input_validation.py`, `app/auth*`, `app/user_state_db.py` (schema),
     `migrations/**`, `.github/workflows/**`, `scripts/agent_exec/**`, `kilo.jsonc`,
     `.kilo/**`, `config.env`, `.env*`); risk-recompute по детерминированным сигналам
     (число файлов, зоны, наличие failing test, контекст-оценка) — расхождение с
     заявленным risk → reject.
  3. Pre-flight: схема полна; один git root; `HEAD == target_commit`; sha256 каждого
     read_set-элемента совпадает; `write_set ∩ денилист = ∅`; tests ⊆ allowlist;
     контекст-оценка ≤ `context_budget_tokens` (≤20000); worktree чист в write-set;
     dependencies verified. Любой провал → `rejected_preflight`, модель не вызывается.
  4. Запуск: `run_id` (uuid); spawn триггера с `cwd = target_repo` и env:
     `LLAMACPP_MODEL`, `WORKFLOW_CURRENT_TASK_PATH` (абсолютный),
     `WORKFLOW_CURRENT_CONTRACT_PATH` (абсолютный),
     `LLAMACPP_TRIGGER_TRIGGER_METRICS_PATH` → per-run receipt
     `logs/agent_exec/receipts/<run_id>.jsonl`,
     `LLAMACPP_MAX_INPUT_TOKENS = context_budget_tokens`.
  5. Post-verify: receipt существует и непуст (иначе FAIL); contract substantive;
     дельта изменений относительно baseline ⊆ write-set (изменения пользователя вне
     write-set игнорируются); tests exit 0 из receipt.
  6. Классификация исхода (таксономия ниже) и запись в
     `logs/agent_exec/verified_packets.jsonl`: `{packet_id, run_id, executor, risk,
     outcome, receipt_path, retry_of?}`.
  7. **ADR:** `hometutor-studio/doc/team_workflow/adr_execution_packets.md` — два
     сосуществующих маршрута (backlog-driven ↔ plan-driven packets), поле `backlog_ref`,
     границы ответственности репозиториев; + одна строка-ссылка в `AGENTS.md`.
- **Files (hometutor):** `scripts/agent_exec/run_execution_packet.ts`,
  `scripts/agent_exec/packet_policy.ts`, `scripts/agent_exec/tests/run_execution_packet.test.ts`,
  `scripts/agent_exec/tests/packet_policy.test.ts`.
  **Files (studio):** `doc/packets/PKT-TEMPLATE.md`,
  `doc/team_workflow/guides/execution_packets.md`,
  `doc/team_workflow/adr_execution_packets.md`, `AGENTS.md` (одна строка).
- **Tests:** `npm.cmd run test:agent -- scripts/agent_exec/tests/run_execution_packet.test.ts`
  и `npm.cmd run test:agent -- scripts/agent_exec/tests/packet_policy.test.ts`.
  Обязательные негативные кейсы policy: absolute path, `..`-traversal, drive/UNC,
  symlink-escape (fixture), write-set в денилисте, sha256 mismatch, budget > 20000,
  risk-занижение.
- **DoD:** unit-тесты PASS; один живой low-risk пакет end-to-end в shadow-режиме
  (auto-merge выключен, cloud-ревью диффа вручную) с полной записью в ledger;
  ADR добавлен; North star wired.
- **Rollback:** новые файлы — удалить; ADR — revert; существующие пути не тронуты.
- **Dependencies:** P0-1.
- **Исполнитель:** только cloud/human — весь контур (`scripts/agent_exec/**`) закрыт
  для локальной модели без исключений (устранённое противоречие v1.0).

---

## Контракт Execution Packet (схема v1.1)

```yaml
packet_id: PKT-2026-07-19-001
objective: one-sentence outcome
target_repo: D:/Projects/hometutor        # из allowlist; ровно один git root
target_commit: c5182b9
backlog_ref: null                          # опционально: id пакета из backlog_registry.yaml
risk: low | medium | high
risk_reasons: [no-schema, no-security, single-module]
complexity_estimate: S | M                # L → не для local
read_set:
  - { path: app/x.py, sha256: "<hex>", ranges: null }
  - { path: tests/test_x.py, sha256: "<hex>", ranges: "1-80" }
write_set: [app/x.py]                     # ≤3 файлов для local; relative-only
test_commands:
  - .\.venv\Scripts\python.exe -m pytest tests/test_x.py
forbidden_areas: []                        # ДОПОЛНЯЕТ встроенный денилист, не заменяет
dependencies: []
context_budget_tokens: 12000               # hard cap 20000 (token_safety_registry)
expected_patch_size: "<= 120 lines"        # null => allow no-op (иначе NO_CHANGES = blocked)
invariants: ["process(QueryContext)->QueryContext сохранён"]
acceptance_criteria: ["test X проходит", "поведение Y не изменилось"]
rollback_rule: "git apply -R patch; run помечается failed"
required_reviewer: cloud | human
allowed_fallback: cloud_executor | none    # применяется ТОЛЬКО к transient-классу
execution_timeout_ms: 900000
```

Cloud генерирует содержательные поля (objective, декомпозиция, risk+reasons, read/write-set,
tests, invariants, acceptance, expected_patch_size, dependencies). `packet_policy.ts`
детерминированно перепроверяет всё до вызова модели; планнер-модель не является границей
безопасности. Локальная модель не имеет права расширять write_set, test_commands, budget,
timeout, fallback, forbidden_areas.

---

## VLCR: формула и таксономия исходов (зафиксировано, v1.1)

Каждый run получает ровно один `outcome`:

| Outcome | Условие | VLCR-числитель | VLCR-знаменатель |
|---|---|---|---|
| `verified` | реальный patch; дельта ⊆ authoritative write-set; authoritative tests PASS; 0 ручных правок; contract valid; cloud review APPROVE | ✔ | ✔ |
| `failed` | детерминированный провал после вызова модели (tests failed, apply failed, invalid response) | ✘ | ✔ |
| `policy_violation` | write-set violation, widening, unapproved tests, budget, response-model, dirty, reasoning | ✘ | ✔ + kill switch |
| `blocked_no_changes` | пакет change-expected, ответ NO_CHANGES | ✘ | ✘ (отдельный blocked rate) |
| `rejected_preflight` | policy reject до вызова модели | ✘ | ✘ (отдельный reject rate) |
| `transient_unavailable` | сервер недоступен/503/timeout до ответа | ✘ | ✘ (availability-метрика) |

```text
VLCR = |verified| / (|verified| + |failed| + |policy_violation|)
```

**Target: ≥ 80%** (выровнено с KPI guide §8) на shadow-серии ≥10 change-expected пакетов.
Baseline: 0% (verified-пакетов не существует). Wiring: wire-in-P0 (ledger в P0-2).
Вторичные: blocked rate, reject rate, review defect rate, lead time, retries;
cloud tokens saved — UNKNOWN до логирования usage компилятора.

---

## Failure policy (v1.1 — без quality-fallback)

| Класс | Примеры | Реакция |
|---|---|---|
| **policy violation** | write_set_violation, model_write_set_widening, unapproved_tests, dirty_write_set, input_budget_exceeded, response_model_mismatch, finish_reason≠stop, reasoning present, contract без evidence | **Hard stop. Никакого fallback.** → human, инцидент в ledger; 1 повтор на серии = стоп серии |
| **deterministic failure** | targeted_tests_failed (патч откачен), git_apply_failed после recount, invalid section order, no_allowed_test_commands, empty receipt | **Local run завершается как FAILED и фиксируется.** Автоматического cloud-перезапуска нет. Новый run (local повтор с исправленным пакетом или cloud executor) — только явно, новым `run_id` с `retry_of`, по решению router/человека |
| **transient** | server_unreachable, HTTP 503 Loading model (после backoff 3/8/15с), timeout до ответа, spawn failure | Retry по backoff; затем — если `allowed_fallback: cloud_executor` — новый run на cloud executor, помечен `transient`; иначе стоп |

---

## Routing policy (без изменений по существу; порог контекста уточнён)

| Маршрут | Условия (все обязательны) |
|---|---|
| **local-direct** | risk=low (пересчитан packet_policy) ∧ write_set ≤3 ∧ один git root из allowlist ∧ вне денилиста ∧ есть authoritative failing test ∧ контекст-оценка ≤ budget ≤ 20000 ∧ dependencies verified ∧ worktree чист в write-set ∧ preflight `/v1/models` alias+ctx PASS |
| **cloud-plan → local-execute → cloud-review** | risk=medium по единственному сигналу (4–5 файлов ИЛИ API-поверхность), без security/schema; план обязан сузить write-set до ≤3, иначе → cloud |
| **Kilo interactive** | неясный repro, исследование, UI-вёрстка — human забирает пакет вручную; результат проходит тот же Evidence Gate как handoff |
| **cloud executor** | risk=high ∨ новые архитектурные решения ∨ декомпозиция в single-root невозможна ∨ local transient (по `allowed_fallback`) |
| **human escalation** | schema/migration, security/guardrails/auth, любое изменение `scripts/agent_exec/**` |

---

## Три готовых промпта

**A. Cloud planner/decomposer:**
```text
Ты — task compiler. Вход: план + текущие HEAD-коммиты репозиториев.
Разрежь план на Execution Packets по схеме v1.1 [YAML выше].
Правила: один git root на пакет (из allowlist); write-set ≤ 3 файлов для
risk=low; read_set — объекты {path, sha256, ranges?}; каждый пакет имеет
authoritative test_commands из allowlist проекта и проверяемые
acceptance_criteria; context_budget_tokens ≤ 20000 (default 12000); зоны
schema/security/provider/config — всегда risk=high + required_reviewer=human;
двурепные задачи — два пакета с dependencies. Не пиши код. Не назначай
executor — это делает router. Выход: только YAML-пакеты, без прозы.
```

**B. Local narrow patch executor** (добавка к system prompt триггера):
```text
Границы задачи заданы пакетом и не подлежат изменению.
WRITE_SET обязан быть подмножеством Write-set из задачи; TESTS обязаны
дословно повторять команды из задачи. Ты не планируешь архитектуру,
не предлагаешь рефакторинги вне write-set, не добавляешь файлы.
Если контекста не хватает или задача требует выхода за границы —
верни # NO_CHANGES и опиши блокер в RISKS (такой ответ будет
классифицирован как blocked, не как успех). Верни только секции
SUMMARY/READ_SET/WRITE_SET/PATCH/TESTS/RISKS/EXECUTION_CONTRACT_DRAFT.
```

**C. Cloud reviewer/verifier:**
```text
Ты — независимый reviewer. Вход: Execution Packet, unified diff,
execution_contract.md, receipt-файл run'а (metrics), вывод тестов.
Проверь и дай вердикт APPROVE/REJECT + причины:
1) diff-пути ⊆ authoritative write-set пакета; 2) выполнены именно
authoritative tests и они PASS по exit code из receipt; 3) contract
содержит только факты, подтверждаемые diff/receipt (укажи любую
самодекларацию); 4) invariants и acceptance_criteria соблюдены;
5) скрытые риски диффа (поведенческие, security, конвенции проекта).
Ты не можешь одобрить то, что отклонил детерминированный gate.
Формат: VERDICT, VIOLATIONS[], RISKS[], REQUIRED_FOLLOWUP[].
```

---

## wave-shadow-promotion (P1)

- **C1.** Пять реальных low-risk задач подряд (promotion-порог guide §8: 0 write-set
  violations, 0 dirty-conflicts, tests PASS, fallback=false, evidence-only contract).
- **C2.** Shadow-серия ≥10 change-expected пакетов; каждый local-дифф — через промпт C;
  auto-merge выключен весь P1.
- **C3.** `scripts/agent_exec/vlcr_report.ts` — агрегат ledger + receipts → VLCR,
  blocked/reject rate, lead time, retries, review defect rate.
- **DoD:** отчёт с реальными числами по всем метрикам; решение о promotion по
  hard gates (0 violations, 0 ложных contracts, VLCR ≥ 80%, воспроизводимость
  1 контрольного пакета).

## wave-autonomy-expansion (P2 — только после promotion gates)

- **D1.** Auto-routing `local-direct` для классов, показавших ≥80% VLCR — только по ledger.
- **D2.** Kilo CLI как второй adapter (сначала проверить guard/relay на CLI-трафике).
- **D3.** Two-root через парные пакеты с `dependencies`.
- **D4.** Свести `_exec_shared.ts` и `_trigger_shared.ts` (устранить bounded-дубликацию)
  либо зафиксировать раздельность постоянным решением; workflow.py — окончательно
  compatibility mode.

---

## Миграция

| Было | Стало |
|---|---|
| `workflow.py --loop --skip-review --watch-contract --trigger-cmd "npx tsx scripts/deepseek_agent_trigger.ts" --agent continue --post-agent-no-dod-cache` | **Golden path (из корня hometutor):** `npx tsx scripts/agent_exec/run_execution_packet.ts D:\Projects\hometutor-studio\doc\packets\PKT-<id>.md` |
| **Сохранить** | backlog-машину studio (workflow.py, cursor/deepseek triggers, orchestrator, `_trigger_shared.ts`); production launcher-цепочку; Kilo как интерактивное место (конфиг уже верный: `kilo.jsonc` instructions + `.kilo/kilo.jsonc` model) |
| **Удалить из обязательного пути** | backlog/orchestration-машину для packet-задач; studio-копию llamacpp-триггера (git rm после sign-off) |
| **Compatibility/manual mode** | `workflow.py` целиком; legacy-вызов нового триггера: `--trigger-cmd "npx tsx D:\Projects\hometutor\scripts\agent_exec\llamacpp_agent_trigger.ts"`; Kilo interactive как ручной executor любого пакета |
| **Возврат к облаку при недоступном local** | только transient-класс: pre-flight `/v1/models` FAIL → новый run на cloud executor по `allowed_fallback`, тот же Evidence Gate |

---

## НЕ делать (v1.1)

- Не встраивать llama.cpp в `trigger_orchestrator.ts`/`trigger_registry.ts` (метрики
  раздвоены + 0 promotion-данных; после переноса — тем более: разные репозитории).
- Не переносить workflow.py/cursor/deepseek/orchestrator в hometutor — backlog-машина
  остаётся в studio; переносится только контур исполнения пакетов.
- Не делать Kilo control plane; CLI-adapter — не раньше P2.
- Не расширять trigger до two-root — решать декомпозицией пакетов.
- Не поднимать production ctx до 128K по умолчанию.
- Не давать локальной модели писать/менять любой код `scripts/agent_exec/**` —
  без исключений (в v1.0 здесь было противоречие; снято).
- Не доверять WRITE_SET/TESTS/evidence, созданным моделью, даже временно.
- Не делать автоматический cloud-fallback после детерминированных провалов —
  только новый явный run с `retry_of`.
- Не включать auto-routing по одному удачному smoke; не пропускать shadow-серию.
- Не редактировать `backlog_registry.yaml`; связь с backlog — только через `backlog_ref`.
- Не давать модели больше 1 repair-попытки.
- Не превышать `context_budget_tokens` 20000 без явного изменения
  `doc/token_safety_registry.json` решением владельца.
- Не считать 95% strict quality Home Coder Benchmark доказательством качества на
  задачах hometutor: benchmark исполняемый (со скрытыми тестами), но задачи не из
  этого репозитория — распределение другое; вопрос закрывает только shadow-серия.

## UNKNOWNs и как проверить

| UNKNOWN | Проверка |
|---|---|
| Качество Qwen3-Coder-Next на реальных задачах hometutor (benchmark-задачи исполняемые, но не из этого репозитория) | shadow-серия ≥10 пакетов, VLCR + review defect rate |
| Фактические `--batch/--ubatch/--no-mmap/--prio` работающего процесса (API их не отдаёт) | `Get-CimInstance Win32_Process -Filter "name='llama-server.exe'" \| Select CommandLine` |
| Работает ли kilo guard/relay для Kilo CLI-трафика | направить CLI на relay endpoint, прочитать `logs/kilo_relay.jsonl` |
| Поведение триггера на многофайловом реальном патче с новым alias (был только 1-файловый smoke) | disposable rehearsal: 2 файла + failing test |
| Стоимость компиляции пакетов облаком | логировать usage в прогонах промпта A |
| Совместимость vitest-тестов триггера после переноса (пути, mocks) | прогон `npm.cmd run test:agent` в hometutor до удаления studio-копии |
