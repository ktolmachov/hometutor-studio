# Task: актуализировать разбор №27 + план Execution Packet под Cursor trigger / kilo_relay

**Дата задачи:** 2026-07-21  
**Тип:** docs-only refresh (без кода контура, без backlog)  
**Исполнитель:** Cursor Agent (`scripts/cursor_agent_trigger.ts`) **или** Cursor IDE → `kilo_proxy_relay` → local/cloud upstream  
**Язык ответа:** русский

---

## Goal

Актуализировать пару артефактов №27 так, чтобы они отражали **текущий** coding-контур studio на 2026-07-21:

1. `doc/presentations/evolutionary_analyses/27_local_model_trust_contour.html`
2. `doc/next/local_model_execution_packet_plan.md` (сейчас v1.5, база 2026-07-20)

Включить в разбор/план **два реальных клиента** до локальной/проксируемой модели:

| Путь | Как вызывается | Auth / endpoint |
|---|---|---|
| **A. Cursor SDK trigger** | `npx tsx scripts/cursor_agent_trigger.ts <task.md>` | `CURSOR_API_KEY`, модель `CURSOR_MODEL` (дефолт `composer-2.5`), cwd = studio |
| **B. Cursor API через kilo_relay** | Cursor/Kilo IDE → OpenAI-compatible base → `scripts/kilo_proxy_relay.py` | upstream: LM Studio / llama.cpp / DeepSeek preset / cloud_budget; compress+guard |

Диагноз **trust inversion** (модель декларирует write-set/tests сама себе) **не отменять** — уточнить, как он проявляется на путях A и B, и что из плана v1.5 остаётся P0.

---

## Scope

**Сделать:**
1. Сверить факты плана/разбора с кодом и docs среза 2026-07-21 (см. Read-set).
2. Обновить HTML №27: слайды про «что есть в коде», боли, P0–P2, golden path — добавить ветку Cursor trigger + kilo_relay; поправить устаревшие даты/версии/статусы.
3. Поднять план до **v1.6**: новая секция «Клиенты контура (llamacpp / Cursor SDK / kilo_relay)»; скорректировать миграцию/UNKNOWNs/НЕ делать; сохранить transactional-модель v1.5, если код ещё не реализован.
4. Синхронизировать одну строку таблицы №27 в `doc/presentations/evolutionary_analyses/README.md` (версия плана, дата, outcome) — **только строку №27**, не весь README.
5. Записать `archive/team_artifacts/_adhoc/local_model_trust_contour_refresh/execution_contract.md`.

**Не делать:**
- Реализацию P0-1/P0-2/P0-3 / новых `.ts` скриптов.
- Правки `backlog_registry.yaml` / `tasklist.md`.
- Перенос контура в hometutor.
- Полный rewrite HTML с нуля; не трогать другие разборы.
- Не менять `scripts/kilo_proxy_relay.py` / compress / trigger-код в этом таске.

---

## Write-set (макс. 4 файла)

1. `doc/presentations/evolutionary_analyses/27_local_model_trust_contour.html`
2. `doc/next/local_model_execution_packet_plan.md`
3. `doc/presentations/evolutionary_analyses/README.md` — **только** строка/абзацы про №27
4. `archive/team_artifacts/_adhoc/local_model_trust_contour_refresh/execution_contract.md` — создать каталог при необходимости

---

## Read-set (строго; section-only / signatures)

**Обязательно (сжато):**
1. Этот файл целиком.
2. `doc/next/local_model_execution_packet_plan.md` — header + «Контекст» + «Три готовых промпта» + «Миграция» + «НЕ делать» + «UNKNOWNs» (не весь файл подряд, если уже в контексте).
3. HTML №27 — только заголовки слайдов + блоки про боль/P0/VLCR/golden path (`rg "<h[123]|VLCR|P0|trust|validatePatch"`).
4. `scripts/cursor_agent_trigger.ts` — docstring + `runTrigger` config (model/env/exit codes).
5. `doc/kilo_proxy_relay.md` — § назначение, Kilo vs Cursor, System prompt Cursor, таблица статусов (не весь файл).
6. `doc/next/kilo_relay_daily_architecture_review_2026-07-21.md` — только executive findings C1/C2 + статус правок (head ~120 строк).

**По требованию (1–2 точечных `rg`, не full-read):**
- `scripts/llamacpp_agent_trigger.ts` — `DEFAULT_MODEL`, `validatePatchAgainstWriteSet`, `extractTestCommands`
- `scripts/_trigger_shared.ts` — evidence-only gate / contract markers
- `doc/presentations/evolutionary_analyses/README.md` — строка `| 27 |`

**Запрещено full-read:** `backlog_registry.yaml`, epoch-файлы, changelog целиком, тяжёлые test suites.

Перед чтением: `.\.venv\Scripts\python.exe scripts/check_readset.py <files…>` — при WARN/BLOCK сжать.

---

## Fact anchors (проверить кодом, не копировать вслепую)

- План сейчас **v1.5** (2026-07-20); README №27 может всё ещё ссылаться на **v1.4** — выровнять.
- `cursor_agent_trigger.ts`: task = `argv[2] | WORKFLOW_CURRENT_TASK_PATH | doc/current_task.md`; нужен `CURSOR_API_KEY`; это **Cursor SDK**, не прямой HTTP в relay.
- `kilo_proxy_relay.py`: прокси OpenAI-compatible; `SLIM_MODE=local` заточен под **Cursor** tool names; для Kilo нужен явный `SLIM_MODE`/allowlist (см. review 2026-07-21 C1/C2).
- Trust inversion живёт в **local executor path** (`llamacpp_agent_trigger` / будущий packet runner). Cursor SDK path — другой trust model (платформенный агент + tools); не смешивать метрики VLCR без оговорок.
- Implementation P0 плана — всё ещё ⬜, если в дереве нет `run_execution_packet.ts` / `finalize_execution_packet.ts` (проверить `Glob`/`rg` перед утверждением).

---

## DoD

1. HTML №27: явная секция/слайд(ы) про пути A (Cursor SDK trigger) и B (Cursor→kilo_relay); дата/версия согласованы с планом.
2. План = **v1.6** с changelog ревизии; секция клиентов; P0 не размыт; промпты A/B/C сохранены или минимально уточнены под dual-client.
3. README строка №27: версия плана v1.6, дата 2026-07-21, status без ложного «implementation ✅».
4. Нет правок вне write-set.
5. `execution_contract.md` заполнен по шаблону ниже.
6. Токен-дисциплина соблюдена (нет full-read forbidden).

---

## Output format (обязательный порядок)

1. Краткий diff-intent (bullet: что меняется в каждом файле write-set).
2. Правки файлов.
3. **MANDATORY FINAL STEP** — создать/обновить:

`archive/team_artifacts/_adhoc/local_model_trust_contour_refresh/execution_contract.md`

```markdown
# execution_contract — local_model_trust_contour_refresh

status: DONE
date: 2026-07-21
change_expected: true

## Evidence (deterministic)
- files_changed: (список из реального diff)
- plan_version_before → after:
- read_set_used:
- commands_run: (check_readset / rg / glob — с exit codes)

## Model Claims (untrusted)
- summary:
- risks:
- open_questions:
```

Если после чтения фактов выяснится, что документы уже согласованы и менять нечего:
верни в ответе маркер `# NO_CHANGES_EXPECTED` и всё равно напиши evidence-only contract с обоснованием.

Если контекста не хватает для безопасной правки:
верни `# NO_CHANGES` + блокер в risks (это **не** успех).

---

## Invocation

### Cursor SDK trigger (облачный Agent API)

```powershell
cd D:\Projects\hometutor-studio
$env:CURSOR_API_KEY = "<key>"   # если ещё не задан
# опционально: $env:CURSOR_MODEL = "composer-2.5"
npx tsx scripts/cursor_agent_trigger.ts doc/next/local_model_trust_contour_refresh_task.md
```

### Cursor IDE через kilo_relay (локальная / proxy модель)

1. Поднять релей (пример local):
   ```powershell
   $env:KILO_RELAY_SLIM_MODE = "local"
   .\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py
   ```
2. В Cursor: OpenAI-compatible base URL → `http://127.0.0.1:<relay-port>/v1` (порт из баннера релея).
3. В Agent/Chat вставить **только** тело этого task-файла (или `@`-ссылку на него) — без длинной истории чата.
4. Не включать лишний MCP/skills; для local stub system уже режется релеем.

### Не путать

- `cursor_agent_trigger.ts` ≠ HTTP в kilo_relay.
- `llamacpp_agent_trigger.ts` — отдельный local OpenAI path (остаётся в плане как primary P0 executor, пока packet runner не реализован).
