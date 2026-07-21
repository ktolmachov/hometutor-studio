# Local Model Trust Contour — Execution Packet Plan

**Версия:** 1.6 (2026-07-21, docs-refresh: добавлена секция «Клиенты контура» —
явно разведены пути llamacpp-trigger / Cursor SDK trigger / Cursor→kilo_relay;
транзакционная модель и P0 v1.5 не изменены, т.к. код ещё не реализован) ·
**База проверки:** hometutor-studio HEAD на момент refresh `4c5c576` (сдвинулся с
`545d155` «113»); hometutor HEAD `c5182b9` «357» **не переснимался** этим проходом —
**обязательно сверить оба HEAD заново перед кодом**
**Источник:** эволюционный разбор №27 «Протокол суда пишет обвиняемый»
(`../presentations/evolutionary_analyses/27_local_model_trust_contour.html`,
артефакт https://claude.ai/code/artifact/4851e86d-8dc1-4b01-9f68-b75d6539138f)

Этот план — runtime-handoff. Перед кодом сверить фактический HEAD.

**История ревизий:** v1.1 предложила перенос контура в `hometutor` (отменено v1.2 —
код-факт: пять функций триггера уже принимают `repoRoot`, жёстко закодирован только
`process.cwd()`; workflow-тулинг явно исключён из hometutor его же `AGENTS.md:11-13`/
`CLAUDE.md:39-43`). v1.2 ввела transactional-модель, поэтапный ledger, разделение VLCR,
честную transient-политику — но её реализация содержала внутренние противоречия
(двойной revert, `verified` без исполнимого review-протокола, дырявый timeout/pytest
allowlist). Черновик v1.3 закрыл замечания третьего аудита, но при восстановлении из
лога обнаружились повреждённый фрагмент P0 и новые противоречия: отсутствующее состояние
`applied`, patch-budget после success-события, crash-window и незащищённая конкуренция.
v1.4 закрыла их явно, но self-review (четвёртый аудит, 2026-07-20) нашёл, что заявленный
терминал `verified` не порождает git-коммит (следующий пакет не может безопасно доверять
HEAD, а инвариант «lock снимается только на чистом дереве» в этой точке молча нарушался),
и что `change_expected: false` документирован в схеме как «NO_CHANGES — успех», но
`Prompt B` и ledger знают только один путь `# NO_CHANGES` → `blocked`, без исполнимого
success-состояния. **v1.5 закрывает оба разрыва явно; implementation разрешён только по
этой версии.** v1.6 — **docs-only refresh** (2026-07-21): транзакционная модель, схема
пакета, P0-1…P0-3, ledger и метрики v1.5 не тронуты (код всё ещё не реализован —
`run_execution_packet.ts`/`finalize_execution_packet.ts`/`packet_policy.ts`/
`execution_state.ts` отсутствуют в дереве, проверено `Glob`). Добавлена только секция
«Клиенты контура»: развести три реальных входа к локальной/проксируемой модели
(`llamacpp_agent_trigger.ts` как primary P0-executor; Cursor SDK trigger
`cursor_agent_trigger.ts`; Cursor/Kilo IDE → `kilo_proxy_relay.py`) и зафиксировать,
что trust inversion живёт **только** в local-executor path, а два клиентских пути
имеют иную trust-модель и не входят в знаменатель Execution VLCR без оговорок.

---

## Контекст: диагноз разбора №27 (не изменился)

Локальный coding-контур для `qwen3-coder-next-q4ks` физически работает: живой прогон
strict no-op smoke против production-сервера прошёл за 2,9 с и записал evidence-only
`execution_contract.md`; 98/98 unit-тестов триггера зелёные. С параметрами по
умолчанию тот же прогон падает за 54 мс — `DEFAULT_MODEL` в
`scripts/llamacpp_agent_trigger.ts:22` всё ещё `qwen/qwen3-coder-next`. Порождающая
причина — **trust inversion**: `validatePatchAgainstWriteSet` (строка 748) сверяет
diff с декларацией *самой модели*, `extractTestCommands` (строка 804) берёт targeted
tests из того же ответа. Экземпляр `PAIN-02`.

---

## Клиенты контура (llamacpp-trigger / Cursor SDK / kilo_relay) — v1.6

К локальной/проксируемой модели сегодня физически ведут **три разных входа**. Они
делят один production-runtime (`qwen3-coder-next-q4ks`, `n_ctx=65536`), но имеют
**разные trust-модели**, и их нельзя мерить одной метрикой без оговорок.

| # | Путь | Как вызывается | Что валидирует границы (write-set / tests) |
|---|---|---|---|
| **primary** | `scripts/llamacpp_agent_trigger.ts` (local OpenAI executor) | Runner/`workflow.py` спавнит процесс, cwd=target_repo | пока — **сама модель** (trust inversion §диагноз); после P0-1 — задача (`model ⊆ task`) |
| **A** | Cursor SDK trigger `scripts/cursor_agent_trigger.ts` | `npx tsx scripts/cursor_agent_trigger.ts <task.md>`; `CURSOR_API_KEY`, `CURSOR_MODEL` (дефолт `composer-2.5`), `local: { cwd: process.cwd() }` | платформенный агент Cursor + его tools; auto-approval режет **по инструментам, не по diff-путям** |
| **B** | Cursor/Kilo IDE → `scripts/kilo_proxy_relay.py` → upstream | OpenAI-compatible base URL на релей; upstream = LM Studio / llama.cpp / DeepSeek preset / cloud_budget | релей — **токен-компрессор + char-guard, не write-set/test gate**; diff не проверяет вообще |

**Ключевые факты (проверены кодом 2026-07-21):**

1. **Trust inversion живёт только в local-executor path.** Именно
   `llamacpp_agent_trigger.ts` сверяет diff с `parsed.writeSetRaw` (строка 748) и берёт
   tests из `parsed.testsRaw` (804). Пути A и B этой конкретной инверсии *не наследуют* —
   у них своя (и не лучшая) trust-модель, см. ниже. Метрики VLCR/Local-execution-success
   определены **только** для packet-контура над local-executor; смешивать их с A/B без
   явной оговорки — ошибка (искажает знаменатель).

2. **A. Cursor SDK trigger — не HTTP в relay.** `cursor_agent_trigger.ts` использует
   `@cursor/sdk` `Agent.prompt(...)` с `local: { cwd: process.cwd() }`; задача берётся из
   `argv[2] | WORKFLOW_CURRENT_TASK_PATH | doc/current_task.md`; нужен `CURSOR_API_KEY`.
   Это **облачный Agent API** с локальным cwd, а не local llama.cpp и не kilo_relay. Его
   evidence — `execution_contract.md`, но `requireSubstantiveContract: false`, а границы
   держит платформенный auto-approval по инструментам, не deterministic packet-policy.
   Поэтому в терминах плана Cursor SDK trigger — это **ручной/исследовательский вход**
   (аналог Kilo IDE в разборе), а не P0-executor: он не проходит через `packet_policy.ts`
   и revert-before-review, значит его нельзя засчитывать в Execution VLCR.

3. **B. kilo_relay не закрывает trust inversion — он ортогонален ей.**
   `kilo_proxy_relay.py` — OpenAI-compatible прокси, который **сжимает** тело
   `POST /v1/chat/completions` и применяет char-guard; он не читает и не валидирует diff.
   Плюс два footgun'а из review 2026-07-21: **C1** — вся strip-компрессия заточена под
   Cursor-XML, на Kilo (Roo/Cline, Markdown-секции) `strip_actions=[]`, экономия ≈ 0;
   **C2** — дефолт `SLIM_MODE=local` держит allowlist Cursor-имён (`Shell,Read,Write,Grep`),
   а реальные tools Kilo (`read_file,write_to_file,execute_command,search_files,apply_diff`)
   под него не попадают → `out.pop("tools")` ломает tool-calling. Для Kilo daily нужен
   явный `SLIM_MODE`/allowlist из Audit-лога. Вывод для плана: релей — инфраструктура
   доставки токенов, **не** элемент trust-контура; P0 write-set/test gate обязан жить в
   executor/Runner, а не в релее.

**Что это меняет в плане:** ничего в P0-1…P0-3 и транзакционной модели — они и так
описывают правильный (primary) путь. Секция лишь фиксирует, что A и B — соседние входы
с иной trust-моделью, чтобы будущий D2 (Kilo/Cursor как второй adapter, P2) не пытался
переиспользовать их auto-approval как замену Evidence Gate.

---

## Ответ на третий аудит и recovery-аудит v1.4 (2026-07-19)

### Подтверждено как сделано правильно (без изменений)

Отмена переноса в hometutor; `LLAMACPP_TARGET_REPO_ROOT` как минимальный фикс;
трёхстадийный переход `local_completed_ok → executed_pending_review → verified`
(концепт верен, протокол перехода — ниже, был неполон); per-run директория и
append-only ledger (концепт верен, владение rollback — ниже, было неполно);
идея разделения VLCR на несколько метрик; `N/A` вместо выдуманного `0%`; CI-пробел
с vitest — pre-existing, не следствие переноса.

### Блокирующие

| # | Замечание | Вердикт | Решение в v1.4 |
|---|---|---|---|
| 1 | Патч после REJECT может остаться применённым — reviewer-промпт врёт, что «уже откачен» | **Принято** | После успешных тестов Runner откатывает patch **до** `local_completed_ok`; только затем пишет `reverted_pending_review` и `executed_pending_review`. APPROVE через `finalize_execution_packet.ts` применяет frozen `applied.patch` заново; REJECT не меняет чистое дерево. |
| 2 | Двойной rollback: триггер уже сам откатывает при `targeted_tests_failed`; наличие `applied.patch` не равно факту применения | **Принято** | Источник истины — атомарный `patch_state.json`, а не наличие артефакта и не best-effort receipt. Состояния включают `prepared`, `applied`, `reverted_by_trigger`, `reverted_by_runner`, `reverted_pending_review`, `revert_failed`, `finalized_applied`. Runner делает reverse apply только из `applied`; все переходы идемпотентны. |
| 3 | Review-переход описан прозой, не существует как исполнимый протокол | **Принято** | Новый `finalize_execution_packet.ts` валидирует структурированный review, stale-state и state transition. Terminal-повтор — idempotent exit 0; незавершённое неподходящее состояние — invalid transition, exit non-zero. APPROVE делает `git apply --check`, apply и journal/event transition; REJECT только фиксирует terminal event. |
| 4 | Нет изоляции: конкурентный run/человек может изменить worktree; Runner может упасть между apply и revert | **Принято** | Repo-scoped exclusive lock удерживается от baseline до подтверждённого revert и повторно берётся finalize-командой. Атомарный journal пишется до/после каждого git-перехода. Новый recovery-путь fail-closed восстанавливает `prepared`/`applied` после crash либо ставит `manual_cleanup_required`; stale lock не снимается автоматически без проверки владельца. Disposable worktree остаётся усилением P1, но P0 больше не полагается на обещание «раны последовательны». |
| 5 | P1 (C4) описывает автоматический retry для `transient`/`policy_violation` — второе прямо противоречит failure policy, где policy violation всегда hard stop | **Принято** | Формулировка C4 исправлена: автоматизируется **только** transient-класс. Policy violation остаётся permanently human/incident-only во всех фазах (P0/P1/P2) без исключений — это не временное ограничение P0, а постоянное правило контура |

### Существенные

| # | Замечание | Решение |
|---|---|---|
| 6 | `evidence-only contract` не обеспечен кодом: общий gate (`_trigger_shared.ts:232`) принимает любой непустой текст кроме `STARTED`, а сам контракт включает `parsed.summary`/`parsed.risks` — свободный текст модели | Контракт разбивается на два явно подписанных блока: `## Evidence (deterministic)` — только из journal/receipt-фактов (target_commit, changed paths из реального diff, patch sha256, test commands + exit codes, sha256 вывода тестов) через новую функцию `buildDeterministicEvidenceBlock()`; `## Model Claims (untrusted)` — `summary`/`risks` как есть. Ни Runner, ни finalize не используют Model Claims для pass/fail; authoritative inputs — journal, `receipt.jsonl` и проверенный evidence-блок. |
| 7 | `execution_timeout_ms` — мёртвое поле: не ограничивает модель, тесты и весь run согласованно | Схема теперь задаёт общий monotonic `execution_timeout_ms` и вложенные `model_timeout_ms`/`test_timeout_ms`. Runner перед каждым этапом использует `min(stage_timeout, remaining)`; trigger получает `LLAMACPP_TIMEOUT_MS` и `LLAMACPP_TEST_TIMEOUT_MS`, test process — bounded `spawnSync` timeout. Packet policy проверяет caps и stage ≤ total. Windows process-tree kill остаётся честно помеченным residual risk и проверяется rehearsal-тестом. |
| 8 | Regex-allowlist pytest-команд (`\b`-граница) пропускает произвольный хвост: `--rootdir`, `--basetemp`, `-p`, `--pyargs`, пути вне репозитория | Regex заменяется на argv-парсинг (переиспользуется существующий `splitCommand`): токен 0 — точный executable, токены 1-2 — точно `-m pytest`, далее **только** relative test-пути без `-`-префикса, без `..`/abs/UNC, с realpath-containment внутри `target_repo` (опционально `::test_name` node-id суффикс). Пустой хвост (голый `pytest`, запуск всего) — reject. Npm-паттерн (`test:trigger -- tests/trigger/<name>.test.ts`) уже достаточно строг (полный anchored regex) — оставлен как есть |
| 9 | Схема смешивает model-декларации и детерминированные факты; `expected_patch_size` — невалидируемая строка | `target_commit`/SHA256 — claims компилятора, независимо проверяемые policy. Свободная строка заменена `change_expected`, `max_patch_lines`, `max_changed_files`. Trigger проверяет бюджет diff до apply; Runner повторяет проверку по frozen `applied.patch` до success events. |
| 10 | Ledger — событийный; метрики без предварительной свёртки по `run_id` рискуют двойным учётом и pending-ранами в знаменателе; «Policy precision» смешивает качество компилятора с внешним состоянием | Authoritative источник — per-run `events.jsonl` с monotonic sequence; global ledger — индекс под lock. Reducer валидирует state machine и отдельно показывает pending/corrupt runs. Метрики разделены на end-to-end VLCR, local execution success, review acceptance, compiler validity, dispatch eligibility и availability. |

### Документация

README (`doc/presentations/evolutionary_analyses/README.md:48,53`) всё ещё содержал
устаревшее «baseline 0%» для №27 в общем описании и центральной таблице, хотя строка
разбора №27 (136) уже была исправлена на `N/A` в предыдущей ревизии — рассинхронизация
исправлена этим же проходом (см. правки README ниже по цепочке коммитов).

Про невозможность независимо открыть Artifact-URL: ожидаемо (сторонние инструменты не
имеют доступа к приватным Claude Artifacts) — не является дефектом плана.

### Блокирующие (четвёртый аудит, self-review 2026-07-20)

| # | Замечание | Вердикт | Решение в v1.5 |
|---|---|---|---|
| 11 | `verified` — терминал, но finalize явно не коммитит (`DoD` v1.4: «finalize не создаёт commit»). Следующий пакет компилируется облаком «от текущего HEAD», но реальное содержимое файлов уже разошлось с HEAD из-за незакоммиченного `applied.patch`; независимая sha256-перепроверка `read_set` ловит это только если новый пакет читает те же файлы. Пересечение write_set с незакоммиченным diff ломает revert-before-review следующего рана (реверт пойдёт не к базовому коммиту). Дополнительно: инвариант «lock держится, пока дерево не станет чистым», явно заявленный для Runner (P0-2, тест «clean worktree before unlock»), в этой точке нарушается самим finalize | **Принято** | APPROVE делает `git commit` сразу после `git apply`, до записи `finalized_applied`/`verified` и до unlock — коммит, а не голый diff, становится терминальным результатом. HEAD снова единственный источник истины для следующего пакета; лок снимается только на чистом дереве без исключений. Подробности и crash-recovery — в транзакционной модели и P0-3 ниже |
| 12 | Схема пакета документирует `change_expected: false ⇒ NO_CHANGES ожидаем, не blocked` (комментарий в YAML), но `Prompt B` знает только одну причину `# NO_CHANGES` — «не хватило контекста» — и безусловно относит её к `blocked, не успех`; в ledger существует только `local_completed_blocked_no_changes`, отдельного success-состояния нет. Корректно предсказанный `change_expected:false` пакет физически не может попасть никуда, кроме «blocked», что искажает `Local execution success` | **Принято** | `Prompt B` получает `change_expected` явным полем задачи и различает два маркера: `# NO_CHANGES` (недостаточно контекста → blocked, как раньше) и `# NO_CHANGES_EXPECTED` (модель подтверждает, что изменений не требуется и `change_expected=false` → успех). Новое терминальное событие `local_completed_no_change_ok`, исключено из знаменателя Execution VLCR (как и все change_expected:false раны), но засчитывается в `Local execution success` |

### Существенные (четвёртый аудит)

| # | Замечание | Решение |
|---|---|---|
| 13 | Ветка «`git apply --check` не проходит despite passed stale-check» или «реальный `git apply` падает после успешного `--check`» не показана в транзакционной диаграмме finalize, хотя `finalize_apply_failed` заявлен в ledger как terminal | Явная третья ветка в диаграмме finalize: `--check` FAIL → `finalize_apply_failed` (terminal) → unlock, `patch_state` не меняется. Реальный `git apply` (после успешного `--check`), упавший частично — не ретраится автоматически, сразу `manual_cleanup_required`, симметрично остальным ambiguity-путям контура |
| 14 | `retry_of` используется в failure policy (deterministic failure) и в C4 (P1 auto-retry для transient), но отсутствует в самой YAML-схеме пакета | Добавлено поле `retry_of: null` в схему v1.5 (`packet_id`/`run_id` предыдущей попытки, если есть) |
| 15 | `Prompt A` ограничивает write-set ≤3 файлов только «для risk=low»; для risk=medium каких-либо явных caps не задано (risk=high и так обязателен required_reviewer=human по зонам schema/security/provider/config/routers/prompts) | Уточнено в `Prompt A`: cap ≤3 файла действует для **любого** risk-уровня, допущенного к local-исполнению в P0 (то есть фактически только risk=low — P0 не должен диспатчить medium/high локально; это явно зафиксировано ниже в «НЕ делать») |
| 16 | `allowed_fallback` — поле схемы, но в P0 fallback для transient всегда hard stop независимо от значения поля (авто-retry — только C4/P1); поле может создать у compiler-промпта ложное ожидание, что оно на что-то влияет уже в P0 | Комментарий в схеме уточнён: поле принимается и валидируется, но в P0 **игнорируется рантаймом** — эффект появляется только после C4 (P1) |

---

## Транзакционная модель v1.5 (journal + repo lock + revert-before-review + finalize commit)

Единственный источник истины — атомарно заменяемый
`logs/agent_exec/runs/<run_id>/patch_state.json`. `receipt.jsonl` остаётся отчётным
артефактом и не используется для решения, применён ли patch: существующий
`writeMetric()` пишет best-effort и при ошибке только предупреждает.

```text
not_applied              — apply не начинался или git apply завершился неуспешно
prepared                 — applied.patch заморожен; следующий шаг — git apply
applied                  — git apply завершился успешно; worktree содержит patch
reverted_by_trigger      — failing tests; trigger успешно откатил patch
reverted_by_runner       — post-apply policy/budget gate; Runner откатил patch
reverted_pending_review  — tests/gates PASS; Runner откатил patch до review
revert_failed            — reverse apply не удался; manual_cleanup_required
finalized_applying       — APPROVE; git apply успешен, commit ещё не подтверждён
                            (crash-window; см. crash recovery ниже)
finalized_applied        — APPROVE; git apply И git commit оба подтверждены (terminal,
                            дерево снова чистое — коммит закрывает diff)
```

Каждый journal-transition записывает `run_id`, `sequence`, `state`, `patch_sha256`,
`target_commit`, timestamp и причину через temp-file + atomic rename. Repo-scoped lock
берётся **до baseline** и удерживается до состояния, в котором worktree снова чист.
Finalize берёт тот же lock перед stale-check/apply. Lock содержит canonical repo root,
PID и start time; занятый или подозрительно stale lock снимается только явной
`--recover` командой после проверки владельца, не автоматически.

```text
lock → baseline → local_dispatched
  → trigger: prepared → git apply → applied → tests
       FAIL → reverted_by_trigger | revert_failed
       PASS → return Runner with state=applied
  → Runner: authoritative post-gates + patch budget
       FAIL → reverted_by_runner → terminal policy/deterministic failure
       PASS → reverse apply → reverted_pending_review
            → local_completed_ok → executed_pending_review → unlock
  → finalize: lock → stale-check
       REJECT → review_rejected → unlock
       APPROVE → git apply --check
            FAIL → finalize_apply_failed → unlock   (patch_state не меняется)
            OK   → git apply → finalized_applying
                 → git commit → finalized_applied
                 → review_approved → verified(commit_sha) → unlock
```

Crash recovery — часть P0, а не UNKNOWN: при старте Runner сканирует nonterminal
`patch_state.json`. Для `applied` выполняется один reverse apply; для `prepared`
сначала проверяются `git apply --check` и `git apply -R --check`, чтобы определить,
попал ли patch в дерево. Неоднозначность или неуспешный revert →
`manual_cleanup_required`, без догадок и повторных применений. После recovery run
не продолжается автоматически: создаётся terminal event `recovered_after_crash` или
`manual_cleanup_required`, дальнейшее решение принимает человек.

Симметричный recovery-путь существует для finalize: если при старте finalize видит
`patch_state=finalized_applying`, он проверяет `git status --porcelain -uall`. Дерево
дословно совпадает с ожидаемым результатом применения `applied.patch` (т.е. commit не
произошёл) → finalize довершает прерванный шаг: **один** `git commit`, затем дописывает
`finalized_applied`/`review_approved`/`verified`. Дерево уже чистое (commit успел пройти
до крэша, упало только событие) → commit не повторяется, finalize восстанавливает HEAD
sha, сверяет её с последним известным commit по journal и просто дописывает недостающие
terminal-события. Любое другое расхождение (дерево не совпадает ни с «после apply», ни
с «после commit») → `manual_cleanup_required`, без попыток угадать состояние.

---

## wave-trust-hardening (P0 — три хода: P0-1 → P0-2 → P0-3)

### P0-1. Authoritative Trigger Hardening + durable patch journal

- **Problem:** trigger сверяет write-set/tests с ответом модели, пять call sites используют
  `process.cwd()`, контракт смешивает evidence и model claims, а состояние patch и
  timeout тестов не являются надёжными.
- **Evidence:** `llamacpp_agent_trigger.ts:22` (неверный default alias), `:384-400`
  (regex test allowlist), `:748/804` (границы из ответа модели), `:820/838/841/857`
  (`process.cwd()` и внутренний revert), `_trigger_shared.ts:145-155` (best-effort
  metrics), `:232-239` (контракт считается готовым по непустому тексту).
- **Proposed:**
  1. Default model → `qwen3-coder-next-q4ks`; alias закрепить unit-тестом.
  2. `resolveTargetRepoRoot()`: `LLAMACPP_TARGET_REPO_ROOT` обязателен для Runner;
     fallback `process.cwd()` допустим только для явно помеченного manual-mode.
     Canonical realpath и git root валидируются внутри trigger повторно.
  3. Из task prompt извлечь authoritative `WRITE_SET`, `TESTS` и `change_expected`
     (передаётся trigger'у как `LLAMACPP_CHANGE_EXPECTED=0|1`, наравне с прочими
     frozen task-полями). Gates: `modelWriteSet ⊆ taskWriteSet`, `diffPaths ⊆
     taskWriteSet`, model tests должны дословно совпадать с task tests; выполняются
     только task tests. Ответ `# NO_CHANGES` при `change_expected=1` и ответ
     `# NO_CHANGES_EXPECTED` при `change_expected=0` — единственные легальные
     сочетания; обратные и смешанные комбинации — policy violation (модель нарушила
     контракт маркеров), не blocked и не success.
  4. Pytest-команды разбирать существующим `splitCommand`: точный
     `.\.venv\Scripts\python.exe -m pytest`, затем минимум один relative test path;
     никаких флагов, abs/UNC/traversal. Для node-id containment проверяется файловая
     часть до `::`. Npm-команда остаётся anchored на один `tests/trigger/*.test.ts`.
  5. Input hard cap ≤20000; response gates: exact model, `finish_reason=stop`, нет
     `reasoning`/`reasoning_content`; `LLAMACPP_CONTEXT_PREPACKED` — строгий `0|1`,
     не truthy-string.
  6. `LLAMACPP_MAX_PATCH_LINES` и `LLAMACPP_MAX_CHANGED_FILES`: diff-budget считается
     до apply, без `---/+++` headers; превышение → policy violation до изменения дерева.
  7. Baseline `git status --porcelain=v1 -uall`; post-verify — дельта к baseline,
     включая untracked files.
  8. Артефакты: `proposed.patch`, `applied.patch`, `test-output.txt`,
     `receipt.jsonl`, `execution_contract.md`. Пути передаются абсолютными env.
  9. Новый `LLAMACPP_PATCH_STATE_PATH`. Trigger атомарно пишет journal transitions:
     `not_applied → prepared → applied → reverted_by_trigger|revert_failed` либо
     оставляет `applied` для Runner после PASS. Наличие patch-файла состоянием не является.
  10. `execution_timeout_ms` — общий monotonic deadline Runner. Model timeout ←
      `min(model_timeout_ms, remaining)` через `LLAMACPP_TIMEOUT_MS`; test timeout ←
      `min(test_timeout_ms, remaining)` через `LLAMACPP_TEST_TIMEOUT_MS`, передаётся в
      `spawnSync(..., {timeout, killSignal:"SIGKILL"})`. Timeout всегда сохраняет
      `patch_state` и запускает единственный предусмотренный revert.
  11. Contract: `Evidence (deterministic)` строится только из commit/diff hash,
      changed paths, фактических argv/exit code/output SHA256. `Summary/Risks` модели
      переносятся в `Model Claims (untrusted)`. Новый validator требует полный
      deterministic-блок; общий nonempty-gate не является authoritative.
  12. CI: отдельные `actions/setup-node` с pinned major и npm cache, затем `npm ci`
      и `npm run test:trigger`; не полагаться на Node образа runner.
- **Files:** `scripts/llamacpp_agent_trigger.ts`, `scripts/_trigger_shared.ts`,
  `scripts/execution_state.ts`, `tests/trigger/llamacpp_agent_trigger.test.ts`,
  `tests/trigger/execution_state.test.ts`, `.github/workflows/test.yml`.
- **Tests:** task/model widening; untracked baseline; dangerous pytest flags;
  abs/UNC/traversal/node-id paths; patch budget before apply; model/test/run timeout;
  journal state on PASS/failing test/revert failure; metrics write failure does not
  erase journal; deterministic contract rejects missing/forged evidence fields.
- **DoD:** targeted Vitest PASS локально и в CI; disposable failing-test smoke
  заканчивается `reverted_by_trigger` и чистым target worktree.
- **Rollback:** revert изменённых файлов; удалить `execution_state.ts` и его тест.
- **Dependencies:** нет.
- **Исполнитель:** только cloud/human.

### P0-2. Execution Packet Runner v0 + lock/recovery/ledger

- **Problem:** нужен детерминированный compiler-to-executor gate, который не доверяет
  planner-модели и не оставляет target repo изменённым при failure/crash.
- **Proposed:**
  1. Разобрать YAML v1.5; пакет immutable после выдачи `run_id`.
  2. `packet_policy.ts`: repo allowlist, canonical realpath containment для существующих
     и новых путей, symlink/junction/case/traversal checks, встроенный glob-denylist,
     risk recompute, full `git rev-parse <ref>^{commit}`, SHA256 read-set; caps и
     соотношение `model_timeout_ms`/`test_timeout_ms` ≤ общего deadline.
  3. Разделить preflight: compiler-invalid (schema/allowlist/denylist) и
     dispatch-ineligible (stale commit/hash, dirty write-set, dependency/repo state).
  4. Создать run directory и frozen `packet.snapshot.yaml`, `baseline.json`,
     `events.jsonl`, `patch_state.json`. `events.jsonl` — authoritative для run;
     глобальный `ledger.jsonl` обновляется под отдельным ledger-lock и является индексом.
  5. Перед baseline взять repo-scoped exclusive lock по hash canonical repo root.
     Busy lock → fail-closed `repo_busy`; stale lock снимается только `--recover` после
     проверки PID/start metadata.
  6. Перед новым dispatch выполнить recovery scan nonterminal journals. `applied` и
     однозначно распознанный applied-`prepared` откатываются ровно один раз; ambiguity,
     dirty delta или revert failure → `manual_cleanup_required`.
  7. Spawn trigger с `cwd=target_repo`, target-root, frozen task/contract paths,
     budget/timeouts и per-run artifact paths. Runner deadline ограничен тем же
     `execution_timeout_ms`; timeout не классифицируется, пока journal не проверен.
  8. После trigger сначала валидировать journal, receipt schema, patch SHA256,
     changed paths, test argv/exit codes и patch budget. Никакие success events до
     завершения этих gates не пишутся.
  9. Если journal=`applied` и любой post-gate FAIL — один reverse apply →
     `reverted_by_runner`, затем terminal policy/deterministic event. Если PASS — один
     reverse apply → `reverted_pending_review`, затем `local_completed_ok` и
     `executed_pending_review`; только после чистого status lock освобождается.
  10. `reverted_by_trigger`/`not_applied` не откатываются Runner'ом.
      `revert_failed` немедленно даёт `manual_cleanup_required`.
- **Files:** `scripts/run_execution_packet.ts`, `scripts/packet_policy.ts`,
  `scripts/execution_state.ts`, `tests/trigger/run_execution_packet.test.ts`,
  `tests/trigger/packet_policy.test.ts`, `doc/packets/PKT-TEMPLATE.md`,
  `doc/team_workflow/guides/execution_packets.md`.
- **Tests:** path-safety matrix; repo/ledger lock contention; stale-lock fail-closed;
  crash after `prepared` и after `applied`; exactly-one reverse apply; no double revert
  after `reverted_by_trigger`; patch-budget gate occurs before success events; corrupted
  journal/receipt; illegal event sequence; clean worktree before unlock.
- **DoD:** один live low-risk packet доходит до `executed_pending_review`; target repo
  и baseline совпадают, journal=`reverted_pending_review`, все artifacts/hashes полны.
- **Rollback:** удалить новые Runner/policy файлы и docs; вернуть shared state changes.
- **Dependencies:** P0-1.
- **Исполнитель:** только cloud/human.

### P0-3. `finalize_execution_packet.ts` — исполнимый review-протокол

- **Problem:** переход `executed_pending_review → verified` был прозой без кода;
  reviewer-текст сам по себе не менял ledger/worktree (аудит #3).
- **Evidence:** отсутствие любого скрипта, читающего `review.json` и меняющего
  ledger/worktree в v1.2.
- **Proposed:** `scripts/finalize_execution_packet.ts --run-id <uuid> --review <path>`:
  1. Валидировать UUID `run_id`, разрешить run directory только внутри
     `logs/agent_exec/runs/`, прочитать authoritative `events.jsonl` и journal.
     Уже terminal run → идемпотентный no-op, exit 0. Любое другое nonterminal
     состояние, кроме `executed_pending_review` + `reverted_pending_review`, —
     invalid transition, exit non-zero.
  2. Ограничить размер review, распарсить как структуру
     `{verdict: APPROVE|REJECT, violations[], risks[], required_followup[]}` и атомарно
     заморозить копию + SHA256 в run directory до любого решения. Для APPROVE
     `violations` обязан быть пуст; свободный текст и противоречивый verdict отклоняются.
  3. Взять тот же repo-scoped lock. **Stale-check:** `git rev-parse HEAD^{commit}` ==
     `packet.snapshot.yaml.target_commit_resolved`? `git status --porcelain -uall`
     совпадает с `baseline.json`? Нет → событие `stale_finalize` (terminal), exit
     ненулевой, человек пересобирает пакет от нового HEAD.
  4. `APPROVE` → повторно проверить SHA256 frozen patch, `git apply --check`; при FAIL —
     событие `finalize_apply_failed` (terminal), `patch_state` не меняется, unlock. При
     OK → `git apply applied.patch` → journal `finalized_applying` → `git commit -m
     "[run_id] <packet_id>"` (сообщение строится из journal/packet-метаданных, не из
     model claims) → journal `finalized_applied` → события `review_approved`,
     `verified` (с полем `commit_sha`), освободить lock. Если процесс упал после apply
     до commit или после commit до event append, повторный finalize распознаёт точку
     прерывания по journal + `git status` (см. «Crash recovery» в транзакционной
     модели) и либо довершает commit ровно один раз, либо только дописывает
     недостающие terminal-события — но никогда не применяет и не коммитит patch дважды.
  5. `REJECT` → событие `review_rejected` (terminal); никаких действий с деревом.
- **Files:** `scripts/finalize_execution_packet.ts`,
  `tests/trigger/finalize_execution_packet.test.ts`.
- **Tests:** APPROVE happy-path (apply+commit); REJECT happy-path; повторный вызов
  после terminal-состояния — идемпотентный no-op; некорректный `review.json`; вызов на
  ране не в `executed_pending_review` (например, ещё `local_dispatched`) — reject;
  stale target_repo → `stale_finalize`; `git apply --check` FAIL → `finalize_apply_failed`,
  дерево не тронуто; repo-lock contention; crash после apply до commit (recovery
  довершает commit один раз); crash после commit до event append (recovery не коммитит
  повторно); tampered patch SHA256; apply и commit не происходят дважды.
- **DoD:** все тесты PASS; ручной прогон одного живого пакета: APPROVE реально
  применяет патч и коммитит его — он виден в `git log -1 -- <write-set>` с `commit_sha`,
  совпадающим с event-payload, дерево после этого чистое; REJECT оставляет дерево
  нетронутым.
- **Rollback:** новый файл — удалить; если уже был выполнен live-прогон с реальным
  `git commit`, откат также требует `git revert` этого коммита (не голого рабочего
  дерева) — явно отметить в runbook, т.к. это первая точка плана, где finalize
  необратимо меняет git-историю.
- **Dependencies:** P0-2.
- **Исполнитель:** только cloud/human.

---

## Контракт Execution Packet (схема v1.5)

```yaml
packet_id: PKT-2026-07-19-001
objective: one-sentence outcome
target_repo: D:/Projects/hometutor        # из allowlist; ровно один git root
target_commit: c5182b9                     # ЗАЯВКА компилятора; packet_policy
                                            # независимо перепроверяет полным SHA
                                            # (git rev-parse ^{commit}) — расхождение
                                            # => preflight_rejected(stale_packet)
backlog_ref: null
retry_of: null                             # packet_id/run_id провалившейся попытки,
                                            # если этот пакет — ручной retry (только
                                            # deterministic-failure класс в P0)
risk: low                                  # allowed: low | medium | high;
                                            # P0 диспатчит локально ТОЛЬКО risk=low —
                                            # medium/high компилируются, но local
                                            # dispatch для них не реализован до P1/P2
risk_reasons: [no-schema, no-security, single-module]
complexity_estimate: S                     # allowed: S | M (L => не для local)
read_set:
  - { path: app/x.py, sha256: "<hex>", ranges: null }   # sha256 — ЗАЯВКА компилятора,
  - { path: tests/test_x.py, sha256: "<hex>", ranges: "1-80" }  # тоже перепроверяется
write_set: [app/x.py]                     # ≤3 файлов для risk=low (единственный risk,
                                           # допущенный к local dispatch в P0);
                                           # relative-only; новый файл ОК, если путь
                                           # в write_set
test_commands:
  - .\.venv\Scripts\python.exe -m pytest tests/test_x.py   # только пути, без флагов (v0)
forbidden_areas: []                        # ДОПОЛНЯЕТ встроенный денилист
dependencies: []
context_budget_tokens: 12000               # hard cap 20000
change_expected: true                      # false => модель обязана вернуть
                                            # # NO_CHANGES_EXPECTED (успех,
                                            # local_completed_no_change_ok), а не
                                            # # NO_CHANGES (blocked); см. Prompt B
max_patch_lines: 120                       # Runner проверяет по факту applied.patch
max_changed_files: 3
invariants: ["process(QueryContext)->QueryContext сохранён"]
acceptance_criteria: ["test X проходит", "поведение Y не изменилось"]
rollback_rule: "revert-after-success + finalize re-apply; см. Транзакционная модель"
required_reviewer: cloud                   # allowed: cloud | human
allowed_fallback: none                     # allowed: cloud_executor | none;
                                           # применяется ТОЛЬКО к transient-классу,
                                           # НИКОГДА к policy_violation; в P0 поле
                                           # валидируется, но игнорируется рантаймом —
                                           # эффект появляется только с C4 (P1)
execution_timeout_ms: 900000                # общий monotonic deadline; cap 1800000
model_timeout_ms: 600000                    # <= execution_timeout_ms
test_timeout_ms: 120000                     # <= execution_timeout_ms; также bounded remaining
```

Локальная модель не имеет права расширять write_set, test_commands, budget, timeout,
fallback, forbidden_areas, patch-бюджет.

---

## Ledger: событийная модель v1.5

```text
preflight_rejected                          (terminal)
local_dispatched
  → local_completed_ok → executed_pending_review
       → review_approved → verified(commit_sha)   (terminal)
       → review_rejected                     (terminal)
       → stale_finalize                      (terminal, требует пересборки пакета)
       → finalize_apply_failed               (terminal, human escalation; --check FAIL)
  → local_completed_no_change_ok              (terminal; change_expected=false,
                                                # NO_CHANGES_EXPECTED подтверждён — успех,
                                                исключён из знаменателя Execution VLCR)
  → local_completed_deterministic_failure     (terminal)
  → local_completed_policy_violation          (terminal)
  → local_completed_blocked_no_changes        (terminal; # NO_CHANGES —
                                                недостаточно контекста, а не
                                                change_expected=false)
  → local_unavailable_transient               (terminal)
  → manual_cleanup_required                   (terminal, revert_failed)
  → recovered_after_crash                     (terminal, worktree restored)
```

`vlcr_report.ts` читает authoritative per-run `events.jsonl`, группирует по `run_id`,
проверяет monotonic `sequence` и легальность переходов. `corrupt_run_id` и pending runs
показываются отдельно и не растворяются в знаменателях. Глобальный `ledger.jsonl` —
индекс для навигации, а не единственное место восстановления истины.

---

## Метрики (v1.5 — end-to-end отдельно от качества модели)

| Метрика | Формула | Baseline | Target |
|---|---|---|---|
| **Execution VLCR (end-to-end)** | `verified ÷ eligible dispatched change-expected runs`; stale/recovery/manual-cleanup считаются неуспехом контура; `local_completed_no_change_ok` вне знаменателя (не change-expected outcome) | **N/A** (знаменатель 0) | ≥80% на shadow ≥10 (KPI guide §8) |
| **Local execution success** | `(local_completed_ok + local_completed_no_change_ok) ÷ non-transient local terminal attempts` | N/A | изолирует качество executor от review/finalize; корректно предсказанный NO_CHANGES засчитывается как успех, а не как blocked |
| **Review acceptance** | `verified ÷ (verified + review_rejected)` | N/A | качество принятых локальных drafts |
| **Compiler validity rate** | `(compiled − отклонены по схеме/allowlist/денилисту) ÷ compiled` | N/A | чистое качество Task Compiler |
| **Dispatch eligibility rate** | `(валидные − отклонены по commit/worktree/sha256-staleness) ÷ валидные` | N/A | отдельно от компилятора — фактор времени |
| **Availability** | `(eligible-раны − local_unavailable_transient) ÷ eligible-раны` | N/A | инфраструктура сервера |

Вторичные: lead time, review defect rate, `corrupt_run_id` rate (должен быть 0);
cloud tokens saved — UNKNOWN до логирования usage компилятора.

---

## Failure policy (v1.5)

| Класс | Реакция |
|---|---|
| **policy violation** | Hard stop навсегда, во всех фазах P0/P1/P2 без исключений. Revert (если `patch_state=applied` на момент обнаружения) → human → инцидент в ledger |
| **deterministic failure** | Local run = FAILED; revert выполнен единственным владельцем ветки (`reverted_by_trigger` или `reverted_by_runner`) либо не требовался. Новый run — только вручную, новым `run_id` с `retry_of` |
| **transient** | Hard stop в P0 (`local_unavailable_transient`), ручной cloud-run человеком. **Только** этот класс подлежит будущей автоматизации в P1 (C4) — policy violation автоматизации не подлежит никогда |

---

## Три готовых промпта

**A. Cloud planner/decomposer:**
```text
Ты — task compiler. Вход: план + текущие HEAD-коммиты репозиториев.
Разрежь план на Execution Packets по схеме v1.5 [YAML выше].
target_commit и read_set[].sha256, которые ты укажешь, — твои ЗАЯВКИ:
детерминированный packet_policy независимо перепроверит их против
реального репозитория перед вызовом любой модели; расхождение отклоняет
пакет целиком, а не исправляется автоматически. Правила: один git root
на пакет (из allowlist); risk=low — единственный уровень, который P0
диспатчит локально, write-set ≤ 3 файлов; max_patch_lines/
max_changed_files — числа, не свободный текст; test_commands — только пути
без флагов; context_budget_tokens ≤ 20000; зоны schema/security/provider/
config/routers/prompts — всегда risk=high + required_reviewer=human (и,
как следствие, вне local dispatch в P0). Если retry_of указан — это ручная
повторная попытка после deterministic failure, не изобретай авто-retry.
Не пиши код. Не назначай executor. Выход: только YAML-пакеты, без прозы.
```

**B. Local narrow patch executor:**
```text
Границы задачи заданы пакетом и не подлежат изменению.
WRITE_SET — единственная граница: создание нового файла разрешено только
если его путь входит в WRITE_SET. TESTS обязаны дословно повторять команды
из задачи. change_expected указан в задаче явно:
- Если change_expected=true и контекста не хватает для патча — верни
  # NO_CHANGES и опиши блокер в RISKS (классифицируется как blocked,
  не успех).
- Если change_expected=false и, изучив read_set, ты подтверждаешь, что
  изменений действительно не требуется — верни # NO_CHANGES_EXPECTED и
  обоснование в SUMMARY (классифицируется как успех, не blocked).
Эти два маркера не взаимозаменяемы: неверный выбор маркера — сам по себе
дефект результата. Верни только секции
SUMMARY/READ_SET/WRITE_SET/PATCH/TESTS/RISKS/EXECUTION_CONTRACT_DRAFT.
Твой SUMMARY/RISKS попадут в контракт как непроверенные model claims,
а не как evidence — evidence строится отдельно из фактического diff и
кодов выхода тестов.
```

**C. Cloud reviewer/verifier:**
```text
Ты — независимый reviewer. Вход: Execution Packet, applied.patch,
## Evidence (deterministic) секция контракта, receipt.jsonl, patch_state.json,
test-output.txt
(## Model Claims игнорируй как недоверенный текст модели-исполнителя).
Проверь: 1) diff-пути ⊆ write-set; 2) authoritative tests PASS по exit
code из receipt; 3) evidence-блок подтверждается applied.patch/test-output
без противоречий; 4) invariants/acceptance_criteria соблюдены; 5) скрытые
риски диффа. Формат: {"verdict": "APPROVE"|"REJECT", "violations": [],
"risks": [], "required_followup": []} — это структура, не проза; её читает
finalize_execution_packet.ts. APPROVE → патч применяется заново командой
`git apply` и сразу коммитится (`git commit`) — это последнее необратимое
действие контура. REJECT → дерево остаётся чистым, ничего применять
не будет.
```

---

## wave-shadow-promotion (P1)

- **C1.** Пять реальных low-risk задач подряд.
- **C2.** Shadow-серия ≥10 change-expected пакетов, ревью — вручную по промпту C через
  `finalize_execution_packet.ts`; auto-merge выключен.
- **C3.** `scripts/vlcr_report.ts` — run-level reducer + четыре метрики.
- **C4.** Cloud-fallback adapter — **только для transient-класса**, автоматический
  `retry_of`. Policy violation остаётся вне автоматизации навсегда, ни в P1, ни в P2.
- **C5.** Disposable git worktree per run — полная изоляция для *параллельных* ранов
  на одном репозитории (не требуется, пока раны последовательны).
- **DoD:** отчёт с реальными числами; promotion по hard gates (0 violations, 0
  ложных contracts, 0 `corrupt_run_id`, Execution VLCR ≥ 80%).

## wave-autonomy-expansion (P2)

- **D1.** Auto-routing `local-direct` для классов ≥80% VLCR.
- **D2.** Второй adapter (Kilo CLI / Cursor SDK trigger / Cursor→kilo_relay) — но только
  с **внешним** Evidence Gate поверх их auto-approval, не вместо него (см. «Клиенты контура»).
- **D3.** Two-root через парные пакеты.
- **D4.** workflow.py — compatibility mode.

---

## Миграция

Архитектурная граница v1.2 сохраняется: контур остаётся в studio. Golden path v1.5 —
`npx tsx scripts/run_execution_packet.ts doc/packets/PKT-<id>.md` из корня studio,
затем `npx tsx scripts/finalize_execution_packet.ts --run-id <id> --review review.json`
после ручного ревью. При APPROVE `finalize` сам создаёт commit — ручного шага
«закоммитить применённый патч» в golden path нет и быть не должно (см. блокирующее
замечание #11 и обновлённую транзакционную модель). Перед новым dispatch Runner
выполняет recovery scan; обе команды используют один repo lock и per-run journal.
`workflow.py` и существующий backlog-контур не меняются.

Golden path контура — только primary local-executor path. Cursor SDK trigger
(`cursor_agent_trigger.ts`) и Cursor/Kilo→`kilo_proxy_relay.py` остаются **ручными
исследовательскими входами** (см. секцию «Клиенты контура»): они не проходят через
`packet_policy.ts`/revert-before-review и не пишут в packet-ledger, поэтому их прогоны
не попадают в Execution VLCR. Их промотирование во второй adapter — задача P2 (D2), и
только после того, как Evidence Gate станет для них внешним, а не их собственным
auto-approval.

---

## НЕ делать (v1.5)

- Не переносить контур в hometutor (проверено дважды, отменено).
- Не давать Runner'у откатывать `reverted_by_trigger`/`revert_failed`/`not_applied` —
  единственная законная точка Runner-revert: сразу после `patch_state=applied`.
- Не оставлять патч применённым между local-этапом и review — revert-after-success
  обязателен, не опционален.
- Не оставлять `applied.patch` незакоммиченным после `verified` — `finalize` обязан
  закоммитить его в рамках APPROVE, до unlock; следующий пакет не должен доверять
  HEAD, если между ним и предыдущим `verified` не было commit.
- Не диспатчить risk=medium/high локально в P0 — только risk=low; write-set cap
  ≤3 файла действует для любого пакета, реально ушедшего в local dispatch.
- Не путать `# NO_CHANGES` (недостаточно контекста → blocked) с
  `# NO_CHANGES_EXPECTED` (change_expected=false подтверждён → успех) — это разные
  маркеры с разными terminal-событиями, не один и тот же случай.
- Не автоматизировать policy_violation ни в одной фазе.
- Не доверять `parsed.summary`/`parsed.risks` как evidence — только как model claims.
- Не запускать тесты без `LLAMACPP_TEST_TIMEOUT_MS`.
- Не разрешать флаги в pytest test_commands в v0 (только relative test-пути).
- Не принимать `target_commit`/sha256 от компилятора без независимой перепроверки.
- Не считать метрики без предварительной группировки по `run_id` и валидации
  легальности переходов.
- Не заявлять baseline как `0%` при пустом знаменателе — только `N/A`.
- Не редактировать `backlog_registry.yaml`.
- Не поднимать production ctx до 128K по умолчанию.
- Не считать 95% strict quality Home Coder Benchmark доказательством качества на
  задачах hometutor — вопрос закрывает только shadow-серия.
- Не засчитывать прогоны Cursor SDK trigger или Cursor/Kilo→kilo_relay в Execution VLCR
  или Local execution success: у них другая trust-модель (auto-approval по инструментам /
  голый токен-компрессор), они не проходят packet_policy и revert-before-review.
- Не считать `kilo_proxy_relay.py` элементом trust-контура: он сжимает токены и держит
  char-guard, но diff/write-set не валидирует — write-set/test gate обязан жить в
  executor/Runner, а не в релее.
- Не запускать relay-путь (B) с дефолтным `SLIM_MODE=local` для Kilo без явного allowlist
  из Audit-лога — Cursor-имена tools выкинут Kilo-tools (review C2).

## UNKNOWNs

| UNKNOWN | Проверка |
|---|---|
| Качество Qwen3-Coder-Next на реальных задачах hometutor | shadow-серия ≥10 пакетов |
| Полнота SIGKILL против process-tree на Windows при test-timeout | disposable rehearsal с намеренно зависающим тестом |
| Фактические `--batch/--ubatch/--no-mmap/--prio` работающего процесса | `Get-CimInstance Win32_Process -Filter "name='llama-server.exe'" \| Select CommandLine` |
| Поведение `finalize_execution_packet.ts` при действительно устаревшем HEAD | disposable rehearsal: сменить HEAD вручную между local-этапом и finalize |
| Стоимость компиляции пакетов облаком | логировать usage в прогонах промпта A |
| Можно ли Cursor SDK trigger (path A) обвязать внешним Evidence Gate вместо platform auto-approval | эксперимент D2 (P2): прогнать пакет через `cursor_agent_trigger.ts` и проверить, виден ли diff Runner'у до принятия |
| Реальные tool-имена Kilo для relay-allowlist (path B) | Audit-сессия на живом Kilo (`SLIM_MODE=off`) → собрать имена из JSONL, review §2 C2 |
