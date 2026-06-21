Да — делаем **боевой план, который можно прямо отдать в отдельную сессию агенту**. Смысл сильного хода: не пытаться “улучшить всё сразу”, а запустить **один архитектурный wave**, который переводит `run_autonomous` в режим настоящей инженерной платформы: event-driven, replayable, policy-governed, proof-based.

Ниже — готовый план \+ контекст \+ backlog \+ DoD \+ copy-paste prompt для отдельной сессии.

---

# **Autonomous Delivery Control Plane v3 — World-Class Hardening Plan**

## **0\. Контекст и цель**

Сейчас уже есть хороший v2-план: `pipeline_state.json`, `result.json`, `proof_bundle`, `current_task.meta.json`, stop-hook freshness, failure classifier, prompt routing registry и quality gates. В uploaded implementation plan прямо зафиксировано, что текущая проблема — критические решения всё ещё идут через markdown-семантику и интерпретацию exit-code/stdout, а прорыв — перевести pipeline в deterministic control plane, где агент выполняет только текущую задачу, а скрипты принимают решения.

Но для уровня “мирового класса” этого мало. Нужно добавить слой **runtime safety \+ replay \+ evals \+ governance**. Современные agent runtime-практики сходятся в одном: автономность должна опираться на durable execution/checkpoints, human-in-the-loop, tracing, guardrails, evals и policy enforcement, а не на длинные промпты. LangGraph описывает durable execution как сохранение прогресса в ключевых точках для pause/resume, восстановления после ошибок и human-in-the-loop; persistence/checkpoints дают time-travel debugging и fault-tolerant execution. ([LangChain Docs](https://docs.langchain.com/oss/python/langgraph/durable-execution?utm_source=chatgpt.com)) OpenAI Agents SDK также выделяет tracing, guardrails, evals и structured traces как основу для отладки и оценки agent workflows. ([developers.openai.com](https://developers.openai.com/api/docs/guides/agent-evals?utm_source=chatgpt.com))

## **Главная цель wave**

Перевести hometutor autonomous delivery из “event-driven pipeline v2”  
в “auditable, replayable, policy-governed, adversarially-tested agentic runtime”.

Короткая формула:

State machine decides.  
Policy engine restricts.  
Sandbox protects.  
Replay explains.  
Proof bundle closes.  
Evals measure.  
Human approves risky actions.  
Incidents improve the system.

---

# **1\. Принципы, которые нельзя нарушать**

## **Principle 1 — Prompt is not control plane**

Промпт не должен решать, продолжать ли pipeline. Он только объясняет агенту текущую задачу. Решение принимает `pipeline_state.json + result.json + policy.yaml`.

## **Principle 2 — Every critical action must leave durable evidence**

Любой `post-agent`, closure, retry, human approval, gate failure, command execution и proof result должен иметь артефакт в `logs/autonomous_runs/<run_id>/`.

## **Principle 3 — No closure without proof**

Пакет нельзя закрывать по словам агента. Только через `proof_bundle/manifest.json`, DoD output, write-set check, docs sync, budget report и lineage.

## **Principle 4 — Security is a first-class role**

OWASP Top 10 for LLM Applications включает prompt injection, insecure output handling, training data poisoning, denial of service, supply chain vulnerabilities и другие риски; prompt injection особенно важен, потому что смешивает инструкции и данные в одном языковом канале. ([OWASP Foundation](https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com)) Поэтому agentic pipeline должен иметь sandbox, command guard, approval protocol, adversarial evals и security-review gate.

## **Principle 5 — Reliability must be measured**

Нужно перейти от “кажется, работает” к SLI/SLO: closure success rate, false closure rate, proof completeness, write-set violation rate, recovery success rate, prompt-injection block rate. SRE-подход использует SLO и error budgets как data-driven способ управлять надёжностью сервиса. ([sre.google](https://sre.google/static/pdf/art-of-slos-howto-a5.pdf?utm_source=chatgpt.com))

---

# **2\. Рекомендуемый сильный ход: один wave из 5 пакетов**

Не надо начинать с 20 пакетов. Сначала нужен **Wave 1 — Runtime Trust Foundation**. Он даст фундамент, после которого остальные улучшения станут безопаснее.

## **Wave 1 — Runtime Trust Foundation**

| Порядок | Пакет | Почему именно сейчас |
| ----- | ----- | ----- |
| 1 | `epoch-control-plane-v3-core` | Структурный event/state protocol — база всего |
| 2 | `epoch-agent-sandbox-policy` | Сразу ограничить опасные действия агента |
| 3 | `epoch-durable-replay-time-travel` | Каждый run должен быть расследуемым и воспроизводимым |
| 4 | `epoch-proof-bundle-closure-gate` | Closure только через доказательства |
| 5 | `epoch-hook-final-step-gate` | Hook гарантирует freshness/proof/write-set, а не просто напоминает |

Именно такой порядок лучше текущего v2-плана: сначала protocol, потом безопасность, потом replay, потом closure trust, потом stop hook. Если сначала делать proof/hook без sandbox и replay, можно получить сильные gates, но слабую расследуемость и слабую защиту от опасных команд.

---

# **3\. Детальный план пакетов Wave 1**

## **Package 1 — `epoch-control-plane-v3-core`**

### **Goal**

Ввести единый machine-readable protocol для автономного pipeline: `pipeline_state.json`, `result.json`, event classes, `next_action`, `requires_human`, schema validation.

### **Problem**

Сейчас агент может читать stdout вроде “DoD drift”, “§Now empty”, “contract block not found” и сам решать, что делать. Это хрупко: поменяется текст — сломается логика.

### **Target architecture**

scripts/run\_autonomous.py  
  \-\> logs/autonomous\_runs/\<run\_id\>/result.json  
  \-\> pipeline\_state.json  
  \-\> doc/current\_task.meta.json  
  \-\> stdout remains human-readable, but automation reads JSON only

### **Files to create**

schemas/pipeline\_result.schema.json  
schemas/pipeline\_state.schema.json  
scripts/pipeline\_events.py  
scripts/pipeline\_state.py  
tests/test\_pipeline\_events.py  
tests/test\_run\_autonomous\_result\_json.py  
doc/team\_workflow/run\_autonomous\_runbook.md

### **Files to modify**

scripts/run\_autonomous.py  
scripts/pipeline\_status.py  
doc/team\_workflow/run\_autonomous\_prompt.md  
doc/team\_workflow/run\_autonomous.md

### **`result.json` minimal schema**

{  
  "schema\_version": "pipeline\_result.v1",  
  "run\_id": "2026-04-27T18-42-00Z\_epoch-x",  
  "package\_id": "epoch-x",  
  "agent": "cursor\_ai",  
  "exit\_code": 0,  
  "event": "PACKAGE\_CLOSED",  
  "severity": "info",  
  "requires\_human": false,  
  "retry\_allowed": false,  
  "next\_action": {  
    "type": "continue",  
    "command": ".\\\\.venv\\\\Scripts\\\\python.exe scripts/run\_autonomous.py \--agent cursor\_ai \--non-stop \--budget-profile strict"  
  },  
  "artifacts": {  
    "current\_task": "doc/current\_task.md",  
    "state": "pipeline\_state.json"  
  },  
  "created\_at": "2026-04-27T18:42:00Z"  
}

### **Events**

CURRENT\_TASK\_CREATED  
POST\_AGENT\_STARTED  
DOD\_PASS  
DOD\_FAIL  
DOD\_DRIFT  
PACKAGE\_CLOSED  
PROMOTING\_NEXT  
NEXT\_TASK\_CREATED  
SYNC\_LAG  
CONTRACT\_MISSING  
PROOF\_MISSING  
WRITE\_SET\_VIOLATION  
BUDGET\_BLOCK  
HARD\_GATE  
HUMAN\_APPROVAL\_REQUIRED  
UNKNOWN\_FATAL

### **DoD**

.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_pipeline\_events.py tests/test\_run\_autonomous\_result\_json.py \-v  
.\\.venv\\Scripts\\python.exe scripts/run\_autonomous.py \--smoke \--budget-profile strict  
.\\.venv\\Scripts\\python.exe scripts/pipeline\_status.py \--json  
Test-Path logs/autonomous\_runs/latest/result.json

### **Acceptance criteria**

* Every exit branch 0–7 emits valid `result.json`.  
* `result.json` validates against JSON Schema.  
* `requires_human=true` stops non-stop loop.  
* `pipeline_status.py --json` returns `state`, `package_id`, `last_event`, `next_action`.  
* `run_autonomous_prompt.md` no longer contains long exit-code interpretation table; it points to `result.json` and runbook.

---

## **Package 2 — `epoch-agent-sandbox-policy`**

### **Goal**

Запретить агенту опасные команды, forbidden paths, secret leakage и scope escalation.

### **Why now**

OpenAI safety guidance for agents recommends keeping tool approvals on, using guardrails, and running evals/trace graders to catch mistakes. Guardrails can be attached to inputs, outputs and tools; tool guardrails are especially important when function/tool calls have side effects. ([developers.openai.com](https://developers.openai.com/api/docs/guides/agent-builder-safety?utm_source=chatgpt.com))

### **Files to create**

doc/team\_workflow/agent\_sandbox\_policy.yaml  
scripts/agent\_sandbox.py  
scripts/command\_guard.py  
tests/test\_agent\_sandbox.py  
tests/test\_command\_guard.py

### **Policy example**

schema\_version: agent\_sandbox\_policy.v1

forbidden\_paths:  
  \- ".env"  
  \- ".env.\*"  
  \- "\*\*/secrets\*"  
  \- "\*\*/\*.pem"  
  \- "\*\*/\*.key"  
  \- ".git/\*\*"  
  \- "logs/\*\*/raw\_model\_output\*"

dangerous\_commands:  
  \- "rm \-rf"  
  \- "git reset \--hard"  
  \- "git clean \-fdx"  
  \- "curl | bash"  
  \- "Invoke-WebRequest \* | iex"  
  \- "pip install \--upgrade"  
  \- "npm audit fix \--force"

requires\_human\_approval:  
  \- dependency\_lock\_change  
  \- database\_migration  
  \- delete\_more\_than\_5\_files  
  \- network\_access  
  \- production\_config\_change  
  \- security\_policy\_change

allowed\_shell\_prefixes:  
  \- ".\\\\.venv\\\\Scripts\\\\python.exe"  
  \- "python"  
  \- "pytest"  
  \- "rg"  
  \- "git diff"  
  \- "git status"

### **Command guard behavior**

ALLOW     — command is safe  
WARN      — command allowed, but record in event log  
BLOCK     — command forbidden, emit result event COMMAND\_BLOCKED  
APPROVAL  — command requires approval artifact

### **DoD**

.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_agent\_sandbox.py tests/test\_command\_guard.py \-v  
.\\.venv\\Scripts\\python.exe scripts/command\_guard.py \--cmd "git clean \-fdx"  
.\\.venv\\Scripts\\python.exe scripts/command\_guard.py \--cmd ".\\\\.venv\\\\Scripts\\\\python.exe \-m pytest tests/test\_x.py \-v"

### **Acceptance criteria**

* Dangerous commands are blocked.  
* Forbidden path writes are blocked.  
* Dependency lock changes require approval.  
* Policy decision is emitted into `result.json` or `event_log.jsonl`.  
* Existing safe pytest/rg/git status commands still pass.

---

## **Package 3 — `epoch-durable-replay-time-travel`**

### **Goal**

Любой autonomous run должен быть расследуемым и частично воспроизводимым: event log, state snapshots, command log, diff snapshots, replay manifest.

### **Why**

Durable execution/persistence practices save workflow state at checkpoints and enable resume, time-travel debugging and fault-tolerant execution. ([LangChain Docs](https://docs.langchain.com/oss/python/langgraph/durable-execution?utm_source=chatgpt.com))

### **Files to create**

scripts/run\_recorder.py  
scripts/replay\_run.py  
scripts/diff\_runs.py  
schemas/replay\_manifest.schema.json  
tests/test\_run\_recorder.py  
tests/test\_replay\_run.py

### **Generated structure**

logs/autonomous\_runs/\<run\_id\>/  
  result.json  
  event\_log.jsonl  
  commands.jsonl  
  state\_snapshots/  
    001\_before\_task.json  
    002\_after\_agent.json  
    003\_before\_post\_agent.json  
    004\_after\_post\_agent.json  
  file\_diffs/  
    before.patch  
    after.patch  
  replay\_manifest.json

### **Event log example**

{"ts":"2026-04-27T18:41:00Z","event":"CURRENT\_TASK\_CREATED","package\_id":"epoch-x"}  
{"ts":"2026-04-27T18:44:12Z","event":"COMMAND\_STARTED","cmd\_hash":"sha256:..."}  
{"ts":"2026-04-27T18:44:20Z","event":"COMMAND\_FINISHED","exit\_code":0}

### **DoD**

.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_run\_recorder.py tests/test\_replay\_run.py \-v  
.\\.venv\\Scripts\\python.exe scripts/run\_autonomous.py \--smoke \--budget-profile strict  
.\\.venv\\Scripts\\python.exe scripts/replay\_run.py \--latest \--dry-run  
.\\.venv\\Scripts\\python.exe scripts/diff\_runs.py \--latest \--previous

### **Acceptance criteria**

* Every run creates `event_log.jsonl`.  
* State snapshots are written atomically.  
* `replay_run.py --dry-run` validates manifest and prints ordered replay plan.  
* `diff_runs.py` can compare two runs by event sequence, duration, result and changed files.

---

## **Package 4 — `epoch-proof-bundle-closure-gate`**

### **Goal**

`close_package.py` refuses closure unless `proof_bundle/manifest.json` exists and validates.

### **Files to create**

scripts/proof\_bundle.py  
schemas/proof\_manifest.schema.json  
tests/test\_proof\_bundle.py

### **Files to modify**

scripts/close\_package.py  
scripts/run\_autonomous.py  
tests/test\_close\_package.py

### **Proof bundle structure**

archive/team\_artifacts/\<PACKAGE\_ID\>/proof\_bundle/  
  manifest.json  
  execution\_contract.md  
  current\_task.meta.json  
  dod\_result.json  
  test\_output.txt  
  changed\_files.txt  
  git\_diff\_stat.txt  
  write\_set\_report.json  
  budget\_report.json  
  lineage.json

### **`manifest.json` minimal fields**

{  
  "schema\_version": "proof\_manifest.v1",  
  "package\_id": "epoch-x",  
  "run\_id": "2026-04-27T18-42-00Z\_epoch-x",  
  "git\_base": "abc123",  
  "git\_head": "def456",  
  "dod": {  
    "status": "PASS",  
    "commands": \[  
      {  
        "cmd": ".\\\\.venv\\\\Scripts\\\\python.exe \-m pytest tests/test\_x.py \-v",  
        "exit\_code": 0,  
        "output\_file": "test\_output.txt"  
      }  
    \]  
  },  
  "write\_set": {  
    "status": "PASS",  
    "report\_file": "write\_set\_report.json"  
  },  
  "budget": {  
    "status": "PASS",  
    "report\_file": "budget\_report.json"  
  }  
}

### **DoD**

.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_proof\_bundle.py tests/test\_close\_package.py \-v  
.\\.venv\\Scripts\\python.exe scripts/run\_autonomous.py \--smoke \--budget-profile strict  
Test-Path archive/team\_artifacts/epoch-demo/proof\_bundle/manifest.json

### **Acceptance criteria**

* Closure without proof bundle emits `event=PROOF_MISSING`.  
* `--force` still exists as human override, but writes `approval_required=true` or requires approval artifact.  
* Existing `dod_cache.json` is reused as `proof_bundle/dod_result.json`.  
* Legacy packages can still be closed through documented compatibility mode.

---

## **Package 5 — `epoch-hook-final-step-gate`**

### **Goal**

Cursor/Kilo/GUI stop hook должен блокировать окончание сессии, если proof stale, write-set нарушен, retry budget превышен или `result.json` старее изменений.

### **Files to create**

scripts/write\_set\_check.py  
tests/test\_write\_set\_check.py  
tests/test\_pipeline\_guard.py

### **Files to modify**

.cursor/hooks/pipeline\_guard.py  
scripts/run\_autonomous.py

### **Hook checks**

1\. pipeline\_state.state \== EXECUTING?  
2\. Есть ли свежий logs/autonomous\_runs/latest/result.json?  
3\. result.json newer than latest changed file?  
4\. actual changed files ⊆ current\_task.meta.json.allowed\_write\_set?  
5\. retry\_count \<= max\_retries?  
6\. proof\_bundle exists if closure was attempted?

### **DoD**

.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_pipeline\_guard.py tests/test\_write\_set\_check.py \-v  
Get-Content tests/fixtures/cursor\_stop\_event.json | .\\.venv\\Scripts\\python.exe .cursor/hooks/pipeline\_guard.py

### **Acceptance criteria**

* Missing proof → hook returns `followup_message`.  
* Stale proof → hook returns `followup_message`.  
* Write-set drift → hook returns `followup_message`.  
* Retry exceeded → hook returns blocker.  
* Clean state → hook allows stop.

---

# **4\. Что НЕ делать в этом wave**

Чтобы не раздуть scope:

Не делать пока:  
\- полноценный UI dashboard;  
\- multi-agent parallel execution;  
\- full skills router;  
\- architecture-review automation;  
\- migration of all legacy packages;  
\- rewriting all docs;  
\- full RAG quality eval layer;  
\- OpenTelemetry integration.

Это всё полезно, но после Wave 1\. Сейчас цель — **trust foundation**.

---

# **5\. Риски и защитные меры**

| Риск | Что может пойти не так | Защита |
| ----- | ----- | ----- |
| Backward compatibility | Старые команды ожидают прежний stdout/exit-code | result.json additive only, exit codes не менять |
| Hook regression | Cursor начнёт блокировать корректный stop | test-first для `.cursor/hooks/pipeline_guard.py` |
| Overengineering | Слишком много файлов за один пакет | Wave разбит на 5 пакетов |
| Schema churn | Схемы быстро меняются | `schema_version`, v1 namespace |
| Legacy packages | Старые пакеты без proof bundle | compatibility mode \+ documented `--force` |
| Token budget | Документы снова раздуются | `current_task.md ≤ 250 lines`, heavy context in `context_pack.md` |
| False security | Guardrails есть, но не тестируются | adversarial evals в следующем wave |

---

# **6\. Метрики успеха Wave 1**

После выполнения wave должны быть измеримы:

| Metric | Target |
| ----- | ----- |
| `result.json` coverage for post-agent exits | 100% |
| Valid schema rate | 100% |
| Closure without proof | 0 |
| Write-set violation accepted | 0 |
| Dangerous command accepted | 0 |
| Replay manifest generated | 100% |
| Hook false block rate on clean smoke | 0 |
| Smoke run success | PASS |
| Backward compatible exit-code behavior | PASS |

---

# **7\. Готовый prompt для отдельной сессии**

Ниже можно скопировать в отдельную сессию агента. Это не “общая просьба подумать”, а рабочий orchestration prompt для планирования и выполнения Wave 1\.

Ты работаешь в репозитории hometutor.

Задача: запланировать и начать выполнение Wave 1 — Runtime Trust Foundation  
для Autonomous Delivery Control Plane v3.

Главная цель:  
перевести autonomous delivery pipeline из markdown/exit-code driven workflow  
в auditable, replayable, policy-governed, proof-based agentic runtime.

Ключевой принцип:  
LLM agent выполняет только текущую задачу.  
Control plane принимает решения через pipeline\_state.json, result.json, policy.yaml,  
schema validation, proof bundle, hooks and gates.

Исходный контекст:  
1\. Текущий run\_autonomous pipeline уже является self-propagating loop.  
2\. В системе уже есть:  
   \- scripts/run\_autonomous.py  
   \- scripts/close\_package.py  
   \- scripts/pipeline\_status.py  
   \- .cursor/hooks/pipeline\_guard.py  
   \- doc/current\_task.md  
   \- archive/team\_artifacts/\<id\>/execution\_contract.md  
   \- archive/team\_artifacts/\<id\>/dod\_cache.json  
   \- doc/team\_workflow/run\_autonomous.md  
   \- doc/team\_workflow/run\_autonomous\_prompt.md  
3\. В текущем плане v2 уже предложены:  
   \- pipeline\_state.json  
   \- logs/autonomous\_runs/\<run\_id\>/result.json  
   \- schemas/\*.schema.json  
   \- proof\_bundle/manifest.json  
   \- doc/current\_task.meta.json  
   \- prompts\_registry.yaml  
4\. Не надо переписывать весь workflow.  
5\. Нужно внедрять маленькими пакетами, test-first, с backward compatibility.

Перед началом:  
\- Не читай весь проект целиком.  
\- Используй rg/head/targeted reads.  
\- Сначала проверь существующие функции и точки расширения.  
\- Не трогай файлы вне объявленного write-set.  
\- Не меняй exit codes 0–7.  
\- stdout/stderr поведение сохранить; result.json добавить как additive protocol.  
\- Для всех generated runtime artifacts использовать logs/ или archive/, не коммитить временные артефакты.  
\- Если обнаружишь расхождение с реальным кодом — скорректируй план и явно зафиксируй delta.

Wave 1 packages:

PACKAGE 1: epoch-control-plane-v3-core  
Goal:  
\- every scripts/run\_autonomous.py \--post-agent exit emits valid logs/autonomous\_runs/\<run\_id\>/result.json  
\- introduce pipeline\_state.json  
\- add pipeline\_status.py \--json  
\- extract exit-code semantics from prompt into runbook

Expected files:  
\- create schemas/pipeline\_result.schema.json  
\- create schemas/pipeline\_state.schema.json  
\- create scripts/pipeline\_events.py  
\- create scripts/pipeline\_state.py  
\- create tests/test\_pipeline\_events.py  
\- create tests/test\_run\_autonomous\_result\_json.py  
\- create doc/team\_workflow/run\_autonomous\_runbook.md  
\- modify scripts/run\_autonomous.py  
\- modify scripts/pipeline\_status.py  
\- modify doc/team\_workflow/run\_autonomous\_prompt.md  
\- modify doc/team\_workflow/run\_autonomous.md only minimally

DoD:  
.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_pipeline\_events.py tests/test\_run\_autonomous\_result\_json.py \-v  
.\\.venv\\Scripts\\python.exe scripts/run\_autonomous.py \--smoke \--budget-profile strict  
.\\.venv\\Scripts\\python.exe scripts/pipeline\_status.py \--json

Acceptance:  
\- every exit branch 0–7 writes valid result.json  
\- requires\_human=true stops non-stop loop  
\- pipeline\_status.py \--json includes state, package\_id, last\_event, next\_action  
\- run\_autonomous\_prompt.md no longer contains long exit-code interpretation table

PACKAGE 2: epoch-agent-sandbox-policy  
Goal:  
\- add command/path safety policy for agent execution  
\- block dangerous commands and forbidden writes  
\- require human approval for risky actions

Expected files:  
\- create doc/team\_workflow/agent\_sandbox\_policy.yaml  
\- create scripts/agent\_sandbox.py  
\- create scripts/command\_guard.py  
\- create tests/test\_agent\_sandbox.py  
\- create tests/test\_command\_guard.py

Policy must cover:  
\- forbidden paths: .env, .env.\*, \*\*/\*.pem, \*\*/\*.key, .git/\*\*  
\- dangerous commands: rm \-rf, git reset \--hard, git clean \-fdx, curl | bash, Invoke-WebRequest | iex  
\- approval-required actions: dependency lock change, DB migration, network access, security policy change

DoD:  
.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_agent\_sandbox.py tests/test\_command\_guard.py \-v

PACKAGE 3: epoch-durable-replay-time-travel  
Goal:  
\- every autonomous run creates replayable durable trace  
\- event\_log.jsonl, commands.jsonl, state snapshots, replay\_manifest.json

Expected files:  
\- create scripts/run\_recorder.py  
\- create scripts/replay\_run.py  
\- create scripts/diff\_runs.py  
\- create schemas/replay\_manifest.schema.json  
\- create tests/test\_run\_recorder.py  
\- create tests/test\_replay\_run.py  
\- integrate run\_recorder minimally into run\_autonomous.py or pipeline\_events.py

Generated structure:  
logs/autonomous\_runs/\<run\_id\>/  
  result.json  
  event\_log.jsonl  
  commands.jsonl  
  state\_snapshots/  
  file\_diffs/  
  replay\_manifest.json

DoD:  
.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_run\_recorder.py tests/test\_replay\_run.py \-v  
.\\.venv\\Scripts\\python.exe scripts/replay\_run.py \--latest \--dry-run

PACKAGE 4: epoch-proof-bundle-closure-gate  
Goal:  
\- close\_package refuses closure unless proof\_bundle/manifest.json validates  
\- reuse existing execution\_contract.md and dod\_cache.json

Expected files:  
\- create scripts/proof\_bundle.py  
\- create schemas/proof\_manifest.schema.json  
\- create tests/test\_proof\_bundle.py  
\- modify scripts/close\_package.py  
\- modify scripts/run\_autonomous.py  
\- extend tests/test\_close\_package.py if present

Proof bundle:  
archive/team\_artifacts/\<PACKAGE\_ID\>/proof\_bundle/  
  manifest.json  
  execution\_contract.md  
  current\_task.meta.json  
  dod\_result.json  
  test\_output.txt  
  changed\_files.txt  
  git\_diff\_stat.txt  
  write\_set\_report.json  
  budget\_report.json  
  lineage.json

DoD:  
.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_proof\_bundle.py tests/test\_close\_package.py \-v

Acceptance:  
\- closure without proof emits PROOF\_MISSING  
\- \--force remains possible but must be visible in result/proof/approval trail  
\- smoke package creates proof\_bundle/manifest.json

PACKAGE 5: epoch-hook-final-step-gate  
Goal:  
\- extend .cursor/hooks/pipeline\_guard.py  
\- block stop when proof is missing/stale, write-set drift exists, retry budget exceeded

Expected files:  
\- create scripts/write\_set\_check.py  
\- create tests/test\_write\_set\_check.py  
\- create tests/test\_pipeline\_guard.py  
\- modify .cursor/hooks/pipeline\_guard.py  
\- modify scripts/run\_autonomous.py to generate doc/current\_task.meta.json

Hook checks:  
\- pipeline\_state.state \== EXECUTING  
\- latest result.json exists  
\- result.json is newer than latest changed file  
\- actual changed files are subset of current\_task.meta.json.allowed\_write\_set  
\- retry\_count \<= max\_retries

DoD:  
.\\.venv\\Scripts\\python.exe \-m pytest tests/test\_pipeline\_guard.py tests/test\_write\_set\_check.py \-v

Execution strategy:  
1\. First produce a short implementation analysis:  
   \- actual existing files/functions found  
   \- exact insertion points  
   \- risks  
   \- updated write-set  
2\. Then implement PACKAGE 1 only.  
3\. Do not start PACKAGE 2 until PACKAGE 1 DoD is green.  
4\. Commit-style checkpoints are allowed only after green tests.  
5\. If token/budget/context gets too large, stop after PACKAGE 1 and write:  
   archive/team\_artifacts/epoch-control-plane-v3-core/handoff.md

Final output required:  
\- summary of completed package(s)  
\- changed files  
\- tests run and results  
\- generated artifacts  
\- blockers if any  
\- exact next command for continuing Wave 1

---

# **8\. Минимальный вариант для первой сессии, если хочешь максимально безопасно**

Если отдельная сессия может не потянуть весь wave, дай ей только первый пакет:

Выполни только PACKAGE 1: epoch-control-plane-v3-core.  
Не начинай PACKAGE 2\.  
Цель — result.json \+ pipeline\_state.json \+ schema tests \+ pipeline\_status.py \--json.

Это самый безопасный старт: один пакет, один фундаментальный эффект, минимальный риск расползания scope.

---

# **9\. Что делать после Wave 1**

После Wave 1 запускать Wave 2:

epoch-failure-classifier  
epoch-agent-evals-layer  
epoch-adversarial-eval-harness  
epoch-hitl-approval-protocol  
epoch-pipeline-concurrency-locks

Там уже появятся agent evals, adversarial cases, approval artifacts и lock-protocol. OpenAI рекомендует оценивать agent workflows через traces, graders, datasets and eval runs, а tracing помогает видеть model calls, tool calls, handoffs, guardrails и custom spans. ([developers.openai.com](https://developers.openai.com/api/docs/guides/agent-evals?utm_source=chatgpt.com))

---

# **10\. Короткий итог**

Сильный ход — **не добавлять ещё один большой промпт**, а запустить Wave 1:

epoch-control-plane-v3-core  
epoch-agent-sandbox-policy  
epoch-durable-replay-time-travel  
epoch-proof-bundle-closure-gate  
epoch-hook-final-step-gate

После этого `run_autonomous` станет не просто удобным автономным workflow, а настоящим **локальным agentic runtime**: с событиями, схемами, политиками, доказательствами, replay, sandbox и stop-gates. Это уже уровень инженерной платформы, а не набора промптов.

