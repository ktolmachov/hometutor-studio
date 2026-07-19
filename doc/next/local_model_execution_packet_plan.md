# Local Model Trust Contour — Execution Packet Plan

**Версия:** 1.2 (2026-07-19, после второго контр-аудита) · **База проверки:**
hometutor-studio HEAD `545d155` «113» · hometutor HEAD `c5182b9` «357»
**Источник:** эволюционный разбор №27 «Протокол суда пишет обвиняемый»
(`../presentations/evolutionary_analyses/27_local_model_trust_contour.html`,
артефакт https://claude.ai/code/artifact/4851e86d-8dc1-4b01-9f68-b75d6539138f)

Этот план — runtime-handoff. Перед кодом сверить фактический HEAD.

**Изменения v1.2 (отменяет решение v1.1 о переносе):** второй контр-аудит показал,
что перенос контура в `hometutor` был overcorrection — решение отменено и заменено
явным `target_repo_root`-параметром поверх уже существующей (но не используемой)
параметризации `repoRoot` в триггере. Добавлена транзакционная модель раннов
(per-run artifact directory), поэтапный append-only ledger, разделение VLCR на три
метрики, фикс дублирования контекста, честная (не автоматизированная в P0) политика
transient-fallback и 7 более мелких исправлений. Полная диспозиция — раздел
«Ответ на второй аудит» ниже. v1.1 (перенос) полностью описана и признана ошибочной
в этом же разделе — не воспроизводить.

---

## Контекст: диагноз разбора №27 (не изменился)

Локальный coding-контур для `qwen3-coder-next-q4ks` физически работает: живой прогон
strict no-op smoke против production-сервера прошёл за 2,9 с и записал evidence-only
`execution_contract.md`; 98/98 unit-тестов триггера зелёные. С параметрами по
умолчанию тот же прогон падает за 54 мс — `DEFAULT_MODEL` в
`scripts/llamacpp_agent_trigger.ts:22` всё ещё `qwen/qwen3-coder-next`, а сервер отдаёт
только `qwen3-coder-next-q4ks`. Порождающая причина — **trust inversion**:
`validatePatchAgainstWriteSet` (строка 748) сверяет diff с декларацией *самой модели*,
`extractTestCommands` (строка 804) берёт targeted tests из того же ответа.
Экземпляр `PAIN-02`.

---

## Ответ на второй аудит 2026-07-19 (диспозиция по каждому замечанию)

### Блокирующие

| # | Замечание | Вердикт | Решение в v1.2 |
|---|---|---|---|
| 1 | Перенос в hometutor противоречит разделению репозиториев; studio-SSoT не устраняется (пакеты всё равно в `doc/packets/`) — получается параллельный workflow в двух местах | **Принято, решение v1.1 отменено** | Проверено: `hometutor/AGENTS.md:11-13` — «Backlog, user stories и командный workflow-пайплайн... ведутся в отдельном репозитории hometutor-studio»; `hometutor/CLAUDE.md:39-43` — studio «not required for code changes... out of scope for this document». Перенос нарушал бы контракт, который сам проект декларирует. **Trigger, Task Compiler prompts, Runner и packet_policy остаются в hometutor-studio.** Target repo передаётся явным обязательным параметром (см. #2) |
| 2 | Compatibility-команда с абсолютным путём к скрипту не меняет `process.cwd()` — новый триггер снова читал бы не тот репозиторий | **Принято** (и стало причиной отмены переноса — сам факт, что абсолютный путь не решает проблему, показал, что перенос был лишним: реальный фикс не в *местоположении файла*, а в *параметре внутри процесса*) | Код-факт, подтверждён чтением: `applyPatch(repoRoot, diff)` (строка 498), `runTestCommands(repoRoot, commands)` (555), `gitChangedFiles(repoRoot)` (573), `revertPatch(repoRoot, diff)` (536), `buildReadSetContext(prompt, repoRoot, ...)` (146) — **все пять уже принимают `repoRoot` параметром**; жёстко закодирован только `process.cwd()` в пяти call sites (641, 820, 838, 841, 857). Новый env `LLAMACPP_TARGET_REPO_ROOT` (обязателен при вызове из Runner, fallback на `process.cwd()` для ручных прогонов) — один `const repoRoot = process.env.LLAMACPP_TARGET_REPO_ROOT ?? process.cwd();` и замена пяти констант. Task/contract paths уже абсолютны через `WORKFLOW_CURRENT_TASK_PATH`/`WORKFLOW_CURRENT_CONTRACT_PATH` — cwd на них не влияет |
| 3 | Нет транзакционной модели: patch может остаться применённым без verified run (пустой receipt, invalid contract, REJECT ревьюера, краш Runner) | **Принято** | Per-run artifact directory `logs/agent_exec/runs/<run_id>/`: `packet.snapshot.yaml`, `task.md`, `baseline.json`, `proposed.patch` (сырой diff из ответа модели), `applied.patch` (после hunk-normalize — то, что реально ушло в `git apply`), `receipt.json`, `execution_contract.md`, `test-output.txt`, `review.json` (появляется позже). Триггер получает новые env `LLAMACPP_PROPOSED_PATCH_PATH`/`LLAMACPP_APPLIED_PATCH_PATH`/`LLAMACPP_TEST_OUTPUT_PATH` и пишет туда сырые артефакты. На любом исходе кроме успешного review Runner выполняет `git apply -R --recount applied.patch` в `target_repo`; если revert не удаётся — терминальное состояние `manual_cleanup_required` с точной командой в логе, без повторных попыток |
| 4 | `verified` пишется раньше вердикта ревьюера | **Принято** | Ledger — append-only событийный журнал (не перезаписываемая строка): `preflight_rejected` → `local_dispatched` → один из `{local_completed_ok, local_completed_deterministic_failure, local_completed_policy_violation, local_completed_blocked_no_changes, local_unavailable_transient}` → (только из `_ok`) `executed_pending_review` → `{review_approved→verified, review_rejected}`. VLCR считает только строки, дошедшие до терминального `verified` |

### Существенные

| # | Замечание | Вердикт | Решение |
|---|---|---|---|
| 5 | Перенос добавляет больше сложности, чем убирает (Node toolchain в Python-репо, дубликат shared-runtime); исходная причина TS (переиспользование studio-инфраструктуры) после переноса исчезала | **Принято** | Снято отменой переноса (#1). Три варианта сравнены явно: (a) TS остаётся в studio + explicit target root — **выбран**, сохраняет один Node runtime и всю существующую `_trigger_shared.ts`-инфраструктуру; (b) Python executor в hometutor на stdlib/httpx+pytest — отклонён: дублирует уже написанные 910 строк работающей TS-логики без причины; (c) перенесённый TS со вторым Node toolchain — отклонён (это и была ошибка v1.1) |
| 6 | Node-контур не защищён CI; после переноса `test:agent` не стал бы regression gate | **Принято** (и уточнено фактом) | Проверено: `.github/workflows/test.yml` в studio запускает **только** `pytest tests/ -q` — vitest не гейтится CI **уже сегодня**, независимо от переноса. Это pre-existing gap, а не следствие переноса, но теперь он load-bearing: P0-1 добавляет шаг `npm ci && npm run test:trigger` в `test.yml` (tracked `package-lock.json` уже существует в studio — `package.json`/`package-lock.json` там штатные файлы) |
| 7 | Удаление studio-триггера сломает ссылки в `user_guide.md`/`roadmap.md`/`future_roadmap.md`/`workflow_trigger_orchestrator_design.md`/changelog | **Снято отменой переноса** | Файл `scripts/llamacpp_agent_trigger.ts` никуда не переезжает и не удаляется — вопрос ссылок не возникает. (Полный `rg`-аудит ссылок остаётся хорошей практикой перед любым будущим удалением чего-либо, но не требуется для P0) |
| 8 | Runner пакует excerpts по `ranges`, а триггер повторно вызовет `buildReadSetContext` и добавит начала тех же файлов — дублирование токенов, смешение authoritative/произвольного контекста, неожиданный `input_budget_exceeded` | **Принято** | Новый env `LLAMACPP_CONTEXT_PREPACKED=1`: если установлен, триггер **не** вызывает `buildReadSetContext` и использует `prompt` как есть — Runner уже встроил excerpts с sha256-проверенными диапазонами. Чтобы не дублировать текст financial-format-напоминания, из триггера экспортируется чистая функция `buildFormatReminder()` (выделяется рефакторингом уже существующего inline-блока в `buildReadSetContext`, строки 178-186) — Runner вызывает её же после сборки собственных excerpts |
| 9 | VLCR оптимистичен: `blocked_no_changes` выведен из знаменателя, что позволяет получать высокий VLCR при массовых отказах модели; baseline при пустом знаменателе — не `0%`, а `N/A` | **Принято** | VLCR разделена на три метрики (формулы и таблица исходов — ниже). `blocked_no_changes` **включён** в знаменатель Execution VLCR (это отказ модели на допущенном пакете, не нейтральный исход). Baseline — `N/A` (знаменатель 0), не `0%` |
| 10 | Transient cloud fallback заявлен, но cloud-adapter/reviewer-execution/`retry_of`-механизм в P0 не реализованы — `allowed_fallback` не должен подразумевать автоматику | **Принято** | P0 честно не включает cloud-adapter в Runner. `transient_unavailable` — **hard stop**, требующий ручного решения человека (человек вручную запускает существующий cloud-триггер как отдельный, вручную зарегистрированный run с `retry_of`). Автоматический cloud-fallback — явный scope P1/P2 после появления adapter'а, не текущая функциональность |

### Мелкие (все приняты)

| # | Замечание | Решение |
|---|---|---|
| 11 | `realpath(target_repo/write_path)` не работает для нового файла | Для каждого write-set пути: подниматься к ближайшему **существующему** родителю, realpath именно его, проверять containment внутри `target_repo`; путь без существующего родителя вплоть до `target_repo` — reject |
| 12 | «Не добавлять файлы» конфликтует с тестом на untracked-файл, созданный патчем | Формулировка промпта B исправлена: «не создавай файлы вне write-set» (создание нового файла, который **указан** в write-set, разрешено и ожидаемо) |
| 13 | `target_commit` нужно сравнивать полным SHA, не строковым префиксом | Runner выполняет `git rev-parse <target_commit>^{commit}` и `git rev-parse HEAD^{commit}` в `target_repo`, сравнивает полные 40-символьные SHA |
| 14 | Встроенный денилист неполон — не покрывает все hard zones из hometutor CLAUDE.md | Денилист расширен до полного списка Hard Rules: `app/config.py`, `app/provider.py`, `app/provider_openai.py`, `app/prompts/_impl.py`, `app/routers/*`, `app/api.py`, `app/pipeline_steps.py`, `app/pipeline_runner.py`, `app/user_state*.py`, `app/auth_service.py`, `app/guardrails.py`, `app/input_validation.py`, `migrations/**`, `.github/workflows/**`, `kilo.jsonc`, `.kilo/**`, `config.env`, `.env*` |
| 15 | `rollback_rule` декларативен — patch-артефакт нигде не хранится | Закрыто транзакционной моделью (#3): `applied.patch` — постоянный артефакт рана, `rollback_rule` теперь ссылается на реальный файл, не на обещание |
| 16 | «Не более 1 repair-попытки» — repair не входит в P0, формулировка вводит в заблуждение | Фраза убрана из «НЕ делать»; явно зафиксировано: P0 не реализует repair-retry вообще — deterministic failure = `FAILED`, без повторного вызова модели в рамках одного run |
| 17 | YAML-пример использует `risk: low \| medium \| high` как буквальное значение | Схема исправлена: `risk: low` с комментарием `# allowed: low | medium | high` |

Дополнительно подтверждена (без изменений) находка из первого аудита: два Kilo-конфига
(`kilo.jsonc` — instructions, `.kilo/kilo.jsonc` — модель) действительно существуют оба.

---

## Архитектурное решение (пересмотрено): контур остаётся в studio

**v1.1 отменяется.** Перенос `llamacpp_agent_trigger` в hometutor был ошибкой — решение
принято под давлением одного верного наблюдения (cwd-баг), но перепрыгнуло сразу к
самому дорогому исправлению, не проверив дешёвое. Дешёвое исправление уже лежало в
самом коде: пять функций триггера принимают `repoRoot` параметром, но пять call sites
жёстко используют `process.cwd()`. Правильный fix — один env-параметр, не переезд
910-строчного модуля в другой репозиторий с другим языком экосистемы.

**Итоговая архитектура:**

```text
hometutor-studio:  Task Compiler, packets (doc/packets/), packet_policy.ts,
                    run_execution_packet.ts, llamacpp_agent_trigger.ts (патченный),
                    ledger (logs/agent_exec/), backlog-машина (без изменений)
hometutor:         только target_repo для packet'ов, чьи write-set лежат в app/*.
                    Никакого нового кода, никакого Node toolchain, никаких новых файлов.
```

Runner резолвит `target_repo` из пакета (обязан быть в repo-allowlist), спавнит
триггер с `cwd = target_repo` **и** `LLAMACPP_TARGET_REPO_ROOT = target_repo` (оба —
на случай, если какой-то будущий код в триггере всё же обратится к `process.cwd()`
напрямую; на сегодня явный env — единственный обязательный канал).

---

## wave-trust-hardening (P0 — два хода, порядок строгий: P0-1 → P0-2)

### P0-1. Authoritative Trigger Hardening + target-repo parametrization

- **Problem:** вход контура мёртв (устаревший alias), выход доверяет декларации модели
  вместо задачи, а пять call sites триггера жёстко используют `process.cwd()` вместо
  уже существующего параметра `repoRoot`.
- **Evidence:** `scripts/llamacpp_agent_trigger.ts:22` (`DEFAULT_MODEL`); `:318,748`
  (validate против model-WRITE_SET); `:384,804` (tests из ответа модели); `:633`
  (input-budget без gate); `:728` (нет response.model/finish_reason/reasoning-gate);
  `:641,820,838,841,857` (`process.cwd()` вместо параметра `repoRoot`, который сами же
  функции `applyPatch`/`runTestCommands`/`revertPatch`/`gitChangedFiles`/
  `buildReadSetContext` уже объявляют на строках 498/555/536/573/146).
- **Proposed:**
  1. `DEFAULT_MODEL` → `"qwen3-coder-next-q4ks"`.
  2. Новая функция `resolveTargetRepoRoot()`: `process.env.LLAMACPP_TARGET_REPO_ROOT ?? process.cwd()`;
     заменить пять хардкод-вызовов `process.cwd()` (641, 820, 838, 841, 857) на неё.
  3. `extractTaskWriteSet(prompt)` (на базе протестированного `extractMarkdownListSection`);
     gates: `modelWriteSet ⊆ taskWriteSet` → `model_write_set_widening`;
     `changedPaths ⊆ taskWriteSet`.
  4. `extractTaskTestCommands(prompt)`; hard fail `model_proposed_unapproved_tests`;
     исполняются только task-команды.
  5. Hard gate `estimatePromptTokensApprox(packed) <= maxInputTokens` →
     `input_budget_exceeded` (до отправки запроса); default cap ≤ 20000
     (`doc/token_safety_registry.json:6 → hard_input_tokens: 20000`).
  6. Response-gates: `response.model === model`; `finish_reason === "stop"`;
     отсутствие `reasoning_content`/`reasoning`.
  7. Baseline-gate: `git status --porcelain=v1 -uall` (tracked + untracked) до apply;
     пересечение с write-set → `dirty_write_set`; changed-files после apply = дельта к
     baseline ∪ пути из diff.
  8. Флаг `no_changes: true` в fields при NO_CHANGES-исходе (для `blocked_no_changes`
     в P0-2).
  9. `LLAMACPP_CONTEXT_PREPACKED=1`: пропустить `buildReadSetContext`, использовать
     `prompt` как есть; выделить `buildFormatReminder()` как экспортируемую функцию
     (рефакторинг существующего inline-блока строк 178-186) для переиспользования
     Runner'ом без дублирования текста.
  10. Транзакционные артефакты: если заданы `LLAMACPP_PROPOSED_PATCH_PATH` /
      `LLAMACPP_APPLIED_PATCH_PATH` / `LLAMACPP_TEST_OUTPUT_PATH` — писать туда сырой
      diff до apply, нормализованный diff после hunk-normalize, и конкатенацию
      stdout/stderr тестов соответственно.
  11. Prompt B (system prompt) правка: «WRITE_SET — единственная граница; создание
      нового файла разрешено только если его путь входит в WRITE_SET» вместо
      абсолютного «не добавляй файлы».
  12. CI: добавить в `.github/workflows/test.yml` шаг `npm ci && npm run test:trigger`
      (package-lock.json уже tracked в studio) — закрывает pre-existing CI-gap (#6),
      не связанный с переносом.
- **Files:** `scripts/llamacpp_agent_trigger.ts`, `tests/trigger/llamacpp_agent_trigger.test.ts`,
  `doc/team_workflow/guides/agent_adapter_llamacpp.md`, `.env.example`,
  `.github/workflows/test.yml`.
- **Tests:** существующие 98 + новые: model-write-set шире task; model-tests вне
  task-tests; input сверх бюджета; `response.model` mismatch; `finish_reason != stop`;
  dirty baseline (tracked и untracked); untracked-файл, созданный патчем, — в
  changed-files; `LLAMACPP_TARGET_REPO_ROOT` меняет фактический repoRoot всех пяти
  операций (мок на другую temp-директорию, не `process.cwd()` тестового процесса);
  `LLAMACPP_CONTEXT_PREPACKED=1` — `buildReadSetContext` не вызывается, prompt не
  расширяется повторно.
- **DoD:** `npm.cmd run test:trigger` зелёный локально и в новом CI-шаге; live strict
  no-op против production runtime с явным `LLAMACPP_TARGET_REPO_ROOT=D:\Projects\hometutor`
  PASS; disposable real-patch smoke (1 файл в hometutor, 1 failing pytest, запуск из
  cwd=studio с `LLAMACPP_TARGET_REPO_ROOT`) PASS — это и есть регрессионный тест на
  исходный cwd-баг (#2); guide/`.env.example` без устаревших alias/batch.
- **Rollback:** revert одного коммита.
- **Исполнитель:** cloud/human. Локальной модели запрещено касаться файлов из write-set
  этого пакета.

### P0-2. Execution Packet Runner v0 + transactional ledger

- **Problem:** нет пути «готовый план → маленький проверяемый пакет → local model →
  evidence» вне backlog-orchestration; нечем измерить VLCR; patch может остаться
  применённым без завершённого verified-цикла; ledger не различает
  «локально прошло» от «прошло независимую проверку».
- **Evidence:** `workflow.py::_write_orchestration_current_task:314` (задачи только из
  backlog); `trigger_registry.ts::TRIGGER_REGISTRY:65-91` (llamacpp отсутствует);
  `AGENTS.md:138,162` (SSoT + предпочтительность workflow.py); 0 authoritative-прогонов
  в истории (6 строк метрик, все smoke 2026-06-29 на старом alias).
- **Proposed:** `scripts/run_execution_packet.ts` + `scripts/packet_policy.ts` (оба —
  в studio):
  1. Parse YAML-frontmatter пакета (схема ниже; путь — аргумент, обычно
     `doc/packets/PKT-*.md`).
  2. **packet_policy.ts** (единственный источник policy): allowlist репозиториев
     (`D:/Projects/hometutor`, `D:/Projects/hometutor-studio`); path-safety для
     read/write-set (relative-only, no `..`/drive/UNC; для write-set — realpath
     ближайшего существующего родителя, containment внутри `target_repo`); полный
     денилист из раздела «Мелкие #14»; `target_commit` через
     `git rev-parse <ref>^{commit}` (полный SHA, не строковый префикс); risk-recompute
     по детерминированным сигналам — расхождение с заявленным risk → reject.
  3. Pre-flight: схема полна; один git root из allowlist; commit совпадает (полный SHA);
     sha256 каждого read_set-элемента совпадает; `write_set ∩ денилист = ∅`;
     tests ⊆ allowlist; контекст-оценка ≤ `context_budget_tokens` (≤20000); worktree
     чист в write-set; dependencies verified. Провал → событие `preflight_rejected`,
     модель не вызывается.
  4. `run_id` (uuid); создать `logs/agent_exec/runs/<run_id>/`, записать
     `packet.snapshot.yaml` (frozen копия пакета + резолвленный target_commit-SHA) и
     `baseline.json` (снимок `git status --porcelain -uall` в target_repo).
  5. Событие `local_dispatched`; spawn триггера с `cwd = target_repo`,
     `LLAMACPP_TARGET_REPO_ROOT = target_repo`, `LLAMACPP_MODEL`,
     `WORKFLOW_CURRENT_TASK_PATH`/`WORKFLOW_CURRENT_CONTRACT_PATH` (абсолютные пути в
     run-директорию), `LLAMACPP_TRIGGER_TRIGGER_METRICS_PATH` →
     `logs/agent_exec/runs/<run_id>/receipt.json`, `LLAMACPP_PROPOSED_PATCH_PATH` /
     `LLAMACPP_APPLIED_PATCH_PATH` / `LLAMACPP_TEST_OUTPUT_PATH` → файлы той же
     run-директории, `LLAMACPP_MAX_INPUT_TOKENS = context_budget_tokens`,
     `LLAMACPP_CONTEXT_PREPACKED=1` (если Runner уже упаковал excerpts по ranges).
  6. Post-verify по коду выхода/receipt: receipt непуст (иначе `local_dispatched` без
     терминального успеха → `manual_cleanup_required`-проверка на предмет применённого
     патча); классификация в одно из:
     `local_completed_ok` / `local_completed_deterministic_failure` /
     `local_completed_policy_violation` / `local_completed_blocked_no_changes`
     (расширяет чистый NO_CHANGES-исход флагом `no_changes` из P0-1 п.8) /
     `local_unavailable_transient`.
  7. Если исход ≠ `local_completed_ok` **и** патч был применён (есть `applied.patch` и
     он не пуст) — выполнить `git apply -R --recount applied.patch` в `target_repo`;
     неудача отката → терминальное `manual_cleanup_required` с точной командой в логе.
  8. Если `local_completed_ok` — событие `executed_pending_review`; дальнейший переход
     в `verified`/`review_rejected` вручную по промпту C (в P0 — ручной шаг человека,
     не автоматизация) или через будущий P1-скрипт.
  9. Ledger — append-only `logs/agent_exec/ledger.jsonl`, одна строка на событие,
     `{packet_id, run_id, event, timestamp, ...}` — никогда не перезаписывается.
- **Files:** `scripts/run_execution_packet.ts`, `scripts/packet_policy.ts`,
  `tests/trigger/run_execution_packet.test.ts`, `tests/trigger/packet_policy.test.ts`,
  `doc/packets/PKT-TEMPLATE.md`, `doc/team_workflow/guides/execution_packets.md`.
- **Tests:** `npm.cmd run test:trigger -- tests/trigger/run_execution_packet.test.ts` и
  `... packet_policy.test.ts`. Обязательные негативные: absolute path, `..`-traversal,
  drive/UNC, symlink-escape (fixture), write-set в денилисте, sha256 mismatch,
  budget > 20000, risk-занижение, revert-после-policy-violation восстанавливает
  worktree, revert-failure → `manual_cleanup_required` без повторной попытки.
- **DoD:** unit-тесты PASS; один живой low-risk пакет (write-set в hometutor,
  запуск из studio) проходит до `executed_pending_review` с полным набором артефактов
  в run-директории; ручной review переводит его в `verified`; North star wired.
- **Rollback:** новые файлы — удалить; существующие пути не тронуты.
- **Dependencies:** P0-1.
- **Исполнитель:** только cloud/human — весь новый код закрыт для локальной модели.

---

## Контракт Execution Packet (схема v1.2)

```yaml
packet_id: PKT-2026-07-19-001
objective: one-sentence outcome
target_repo: D:/Projects/hometutor        # из allowlist; ровно один git root
target_commit: c5182b9                     # сравнивается как полный SHA через rev-parse
backlog_ref: null                          # опционально: id пакета из backlog_registry.yaml
risk: low                                  # allowed: low | medium | high
risk_reasons: [no-schema, no-security, single-module]
complexity_estimate: S                     # allowed: S | M (L => не для local)
read_set:
  - { path: app/x.py, sha256: "<hex>", ranges: null }
  - { path: tests/test_x.py, sha256: "<hex>", ranges: "1-80" }
write_set: [app/x.py]                     # ≤3 файлов для local; relative-only;
                                           # новый файл разрешён, если указан здесь
test_commands:
  - .\.venv\Scripts\python.exe -m pytest tests/test_x.py
forbidden_areas: []                        # ДОПОЛНЯЕТ встроенный денилист, не заменяет
dependencies: []
context_budget_tokens: 12000               # hard cap 20000 (token_safety_registry.json:6)
expected_patch_size: "<= 120 lines"        # null => допустим NO_CHANGES без blocked
invariants: ["process(QueryContext)->QueryContext сохранён"]
acceptance_criteria: ["test X проходит", "поведение Y не изменилось"]
rollback_rule: "revert из logs/agent_exec/runs/<run_id>/applied.patch; run → failed"
required_reviewer: cloud                   # allowed: cloud | human
allowed_fallback: none                     # allowed: cloud_executor | none;
                                           # cloud_executor в P0 == ручной шаг, не автоматика
execution_timeout_ms: 900000
```

Cloud генерирует содержательные поля (objective, декомпозиция, risk+reasons, read/write-set,
tests, invariants, acceptance, expected_patch_size, dependencies). `packet_policy.ts`
детерминированно перепроверяет всё до вызова модели; планнер-модель не является границей
безопасности. Локальная модель не имеет права расширять write_set, test_commands, budget,
timeout, fallback, forbidden_areas.

---

## VLCR: три метрики вместо одной (v1.2)

| Метрика | Формула | Что измеряет |
|---|---|---|
| **Execution VLCR** | `verified / (local_completed_ok + local_completed_deterministic_failure + local_completed_policy_violation + local_completed_blocked_no_changes)` — среди change-expected пакетов, реально отправленных модели | качество исполнения самой моделью, включая отказы (`blocked_no_changes` **не** выведен из знаменателя — это отказ модели, не нейтральный исход) |
| **Policy precision** | `(все compiled-пакеты − preflight_rejected) / все compiled-пакеты` | насколько compiler генерирует пакеты, реально проходящие детерминированный gate |
| **Availability** | `(eligible-раны − local_unavailable_transient) / eligible-раны` | инфраструктурная доступность локального сервера, отдельно от качества модели |

**Baseline:** каждая метрика — **`N/A`**, если знаменатель равен 0 (сейчас так и есть:
0 authoritative-прогонов в истории). Не заявлять `0%` там, где нет ни одного
измерения. **Target:** Execution VLCR ≥ 80% на shadow ≥10 change-expected пакетов
(KPI guide §8). Wiring: wire-in-P0 (ledger в P0-2). Вторичные: lead time, retries,
review defect rate; cloud tokens saved — UNKNOWN до логирования usage компилятора.

---

## Failure policy (v1.2)

| Класс | Примеры | Реакция |
|---|---|---|
| **policy violation** | write_set_violation, model_write_set_widening, unapproved_tests, dirty_write_set, input_budget_exceeded, response_model_mismatch, finish_reason≠stop, reasoning present, contract без evidence | **Hard stop.** Revert применённого патча (если был); → human; инцидент в ledger; 1 повтор на серии = стоп серии |
| **deterministic failure** | targeted_tests_failed, git_apply_failed после recount, invalid section order, no_allowed_test_commands, empty receipt | **Local run завершается как FAILED, патч откатывается.** Никакого автоматического cloud-fallback. Новый run (local повтор с исправленным пакетом или явный cloud run) — только вручную, новым `run_id` с `retry_of` |
| **transient** | server_unreachable, HTTP 503 Loading model (после backoff 3/8/15с), timeout до ответа, spawn failure | **Hard stop в P0** (`local_unavailable_transient`). Cloud-fallback — ручной шаг человека до появления P1/P2 adapter'а; `allowed_fallback: cloud_executor` в P0 не подразумевает автоматику |

---

## Routing policy

| Маршрут | Условия (все обязательны) |
|---|---|
| **local-direct** | risk=low (пересчитан packet_policy) ∧ write_set ≤3 ∧ один git root из allowlist ∧ вне денилиста ∧ есть authoritative failing test ∧ контекст-оценка ≤ budget ≤ 20000 ∧ dependencies verified ∧ worktree чист в write-set ∧ preflight `/v1/models` alias+ctx PASS |
| **cloud-plan → local-execute → cloud-review** | risk=medium по единственному сигналу, без security/schema; план обязан сузить write-set до ≤3, иначе → cloud |
| **Kilo interactive** | неясный repro, исследование, UI-вёрстка — human забирает пакет вручную; результат проходит тот же Evidence Gate как handoff |
| **cloud executor** | risk=high ∨ новые архитектурные решения ∨ декомпозиция в single-root невозможна ∨ local `local_unavailable_transient` (ручной перевод по решению человека) |
| **human escalation** | schema/migration, security/guardrails/auth, любое изменение `llamacpp_agent_trigger.ts`/`run_execution_packet.ts`/`packet_policy.ts` |

---

## Три готовых промпта

**A. Cloud planner/decomposer:**
```text
Ты — task compiler. Вход: план + текущие HEAD-коммиты репозиториев.
Разрежь план на Execution Packets по схеме v1.2 [YAML выше].
Правила: один git root на пакет (из allowlist); write-set ≤ 3 файлов для
risk=low; read_set — объекты {path, sha256, ranges?}; каждый пакет имеет
authoritative test_commands из allowlist проекта и проверяемые
acceptance_criteria; context_budget_tokens ≤ 20000 (default 12000); зоны
schema/security/provider/config/routers/prompts — всегда risk=high +
required_reviewer=human; двурепные задачи — два пакета с dependencies.
Не пиши код. Не назначай executor — это делает router. Выход: только
YAML-пакеты, без прозы.
```

**B. Local narrow patch executor** (добавка к system prompt триггера):
```text
Границы задачи заданы пакетом и не подлежат изменению.
WRITE_SET — единственная граница: создание нового файла разрешено только
если его путь входит в WRITE_SET. TESTS обязаны дословно повторять команды
из задачи. Ты не планируешь архитектуру, не предлагаешь рефакторинги вне
write-set. Если контекста не хватает или задача требует выхода за границы —
верни # NO_CHANGES и опиши блокер в RISKS (такой ответ классифицируется
как blocked, не как успех). Верни только секции
SUMMARY/READ_SET/WRITE_SET/PATCH/TESTS/RISKS/EXECUTION_CONTRACT_DRAFT.
```

**C. Cloud reviewer/verifier:**
```text
Ты — независимый reviewer. Вход: Execution Packet, applied.patch,
execution_contract.md, receipt.json, test-output.txt (из run-директории).
Проверь и дай вердикт APPROVE/REJECT + причины:
1) diff-пути ⊆ authoritative write-set пакета; 2) выполнены именно
authoritative tests и они PASS по exit code из receipt; 3) contract
содержит только факты, подтверждаемые applied.patch/test-output (укажи
любую самодекларацию); 4) invariants и acceptance_criteria соблюдены;
5) скрытые риски диффа. Ты не можешь одобрить то, что отклонил
детерминированный gate. Формат: VERDICT, VIOLATIONS[], RISKS[],
REQUIRED_FOLLOWUP[]. Твой APPROVE переводит run в терминальное verified;
REJECT — в review_rejected (патч уже откачен на этапе local run).
```

---

## wave-shadow-promotion (P1)

- **C1.** Пять реальных low-risk задач подряд (0 write-set violations, 0
  dirty-conflicts, tests PASS, evidence-only contract на каждой).
- **C2.** Shadow-серия ≥10 change-expected пакетов; каждый `executed_pending_review`
  — через промпт C вручную; auto-merge выключен весь P1.
- **C3.** `scripts/vlcr_report.ts` — агрегат `ledger.jsonl` → три метрики VLCR,
  lead time, retries.
- **C4.** Cloud-fallback adapter (делает `transient`/`policy_violation`-retry реальной
  автоматикой с `retry_of`) — только после C1-C3, отдельным пакетом.
- **DoD:** отчёт с реальными числами; promotion по hard gates (0 violations, 0
  ложных contracts, Execution VLCR ≥ 80%, воспроизводимость 1 контрольного пакета).

## wave-autonomy-expansion (P2 — только после promotion gates)

- **D1.** Auto-routing `local-direct` для классов, показавших ≥80% VLCR — только по ledger.
- **D2.** Kilo CLI как второй adapter (сначала проверить guard/relay на CLI-трафике).
- **D3.** Two-root через парные пакеты с `dependencies`.
- **D4.** workflow.py — окончательно compatibility mode.

---

## Миграция

| Было | Стало |
|---|---|
| `workflow.py --loop --skip-review --watch-contract --trigger-cmd "npx tsx scripts/deepseek_agent_trigger.ts" --agent continue --post-agent-no-dod-cache` | **Golden path (из корня studio):** `npx tsx scripts/run_execution_packet.ts doc/packets/PKT-<id>.md` |
| **Сохранить** | весь существующий контур studio без переезда: backlog-машину, cursor/deepseek triggers, orchestrator, `_trigger_shared.ts`, production launcher-цепочку; Kilo как интерактивное место |
| **Удалить из обязательного пути** | ничего не удаляется физически; backlog/orchestration-машина для packet-задач становится необязательной, не единственной |
| **Compatibility/manual mode** | `workflow.py` целиком; `--trigger-cmd` может по-прежнему вызывать `llamacpp_agent_trigger.ts` напрямую (с `LLAMACPP_TARGET_REPO_ROOT`, если target — hometutor) |
| **Возврат к облаку при недоступном local** | в P0 — ручной шаг (человек запускает cloud-trigger вручную); в P1/P2 — через C4 adapter, тот же Evidence Gate |

---

## НЕ делать (v1.2)

- Не переносить `llamacpp_agent_trigger`/Runner/Task Compiler в hometutor — решение
  проверено дважды и отменено; `hometutor/AGENTS.md`/`CLAUDE.md` явно исключают
  workflow-тулинг из этого репозитория.
- Не встраивать llama.cpp в `trigger_orchestrator.ts`/`trigger_registry.ts` (метрики
  раздвоены, 0 promotion-данных).
- Не делать Kilo control plane; CLI-adapter — не раньше P2.
- Не расширять trigger до two-root — решать декомпозицией пакетов.
- Не поднимать production ctx до 128K по умолчанию.
- Не давать локальной модели писать/менять `llamacpp_agent_trigger.ts`,
  `run_execution_packet.ts`, `packet_policy.ts` — без исключений.
- Не доверять WRITE_SET/TESTS/evidence, созданным моделью.
- Не делать автоматический cloud-fallback ни для deterministic failure, ни для
  transient в P0 — оба класса требуют явного ручного решения; автоматика — только C4 (P1).
- Не включать auto-routing по одному удачному smoke; не пропускать shadow-серию.
- Не редактировать `backlog_registry.yaml`; связь — только через `backlog_ref`.
- Не реализовывать repair-retry внутри триггера в P0 — deterministic failure = FAILED.
- Не превышать `context_budget_tokens` 20000 без явного изменения
  `doc/token_safety_registry.json` решением владельца.
- Не заявлять VLCR как `0%` при пустом знаменателе — это `N/A`, разные утверждения.
- Не считать `blocked_no_changes` нейтральным исходом, выведенным из VLCR-знаменателя.
- Не считать 95% strict quality Home Coder Benchmark доказательством качества на
  задачах hometutor: benchmark исполняемый (со скрытыми тестами), но задачи не из
  этого репозитория — вопрос закрывает только shadow-серия.

## UNKNOWNs и как проверить

| UNKNOWN | Проверка |
|---|---|
| Качество Qwen3-Coder-Next на реальных задачах hometutor | shadow-серия ≥10 пакетов, три метрики VLCR |
| Фактические `--batch/--ubatch/--no-mmap/--prio` работающего процесса | `Get-CimInstance Win32_Process -Filter "name='llama-server.exe'" \| Select CommandLine` |
| Работает ли kilo guard/relay для Kilo CLI-трафика | направить CLI на relay endpoint, прочитать `logs/kilo_relay.jsonl` |
| Поведение триггера на многофайловом реальном патче с `LLAMACPP_TARGET_REPO_ROOT` (был только 1-файловый smoke) | disposable rehearsal: 2 файла в hometutor + failing test, запуск из cwd=studio |
| Стоимость компиляции пакетов облаком | логировать usage в прогонах промпта A |
| Совместимость `LLAMACPP_CONTEXT_PREPACKED` с реальным multi-file read-set Runner'а | disposable rehearsal с ranges-excerpts на 2+ файлах |
