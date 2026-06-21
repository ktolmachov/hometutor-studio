# Zero-Click Delivery — стартовый промпт (non-stop)

Скопируй блок целиком в Composer (Ctrl+I).

```text
Запусти Zero-Click Delivery (non-stop):

**Смысл «Zero-Click» здесь:** автоматический цикл `run_autonomous.py --non-stop` (current_task →
MANDATORY FINAL STEP / --post-agent → promote следующего пакета). Это **не** то же самое, что
полностью без участия человека **plan-next**: `generate_plan_next_prompt.md` Phase 6 по дизайну
ждёт явный accept кандидата перед записью в реестр.

Канонические правила (**SSoT / производные**, **PowerShell / venv**, **sync после YAML**): [`_common_rules.md`](_common_rules.md).

1. Прогон (без pre-smoke):
   - Предпочтительно: открыть терминал с **рабочей директорией = корень репозитория** и выполнить **только** строку ниже (без `cd`, без `&&`):
   .\.venv\Scripts\python.exe scripts/run_autonomous.py --agent cursor_ai --non-stop --budget-profile strict --non-stop-max-next-tasks 5
   - Если cwd не корень: **одна** строка PowerShell, разделитель **`;`** (не `&&`):
   Set-Location -LiteralPath '<корень-репозитория>'; .\.venv\Scripts\python.exe scripts/run_autonomous.py --agent cursor_ai --non-stop --budget-profile strict --non-stop-max-next-tasks 5
   - Допустимо иначе: две отдельные команды — сначала `Set-Location -LiteralPath '<корень-репозитория>'`, на **следующей строке** та же строка с `.\.venv\Scripts\python.exe …`.

Для старта pipeline использовать параметры строго как в п.1 (длинную цепочку можно увеличить, напр. `--non-stop-max-next-tasks 50`). Не добавлять флаги, не убирать `--non-stop`. При ручном первом запуске `--non-stop-chain-step` обычно **0** (счётчик глубины цепочки); в хвосте `current_task.md` он пробрасывается автоматически в команду следующего `--post-agent`. `--post-agent` и пересоздание промпта (exit 4) — отдельные команды, см. п.3.

**Архитектурное ограничение non-stop:** цепочка «следующий пакет» после `post_agent()` должна продолжаться **новым процессом** `python scripts/run_autonomous.py ...` (как в MANDATORY FINAL STEP). Внутренний вход CLI в том же интерпретаторе рекурсивно **запрещён** охранником `_run_autonomous_in_process`: иначе растёт стек без границ (OOM на длинных волнах).

**Различия агентов (MANDATORY FINAL STEP):** **Kilo** — pointer-first: после успешного Step B (`--post-agent`) часто нужна **остановка сессии** и новая сессия для следующего указателя. **Cursor / Codex** в `--non-stop`: после Step C продолжай в **той же** GUI-сессии. **Claude Code** — синхронный CLI-путь с TDD loop в скрипте.

2. Открой `doc/current_task.md` и выполни задачу строго в рамках объявленных read-set/write-set.
   В конце файла есть MANDATORY FINAL STEP (или MANDATORY CHAIN) — обязательно выполни его через Shell tool.

3. Семантика exit-кодов — быстрая справка:

   ```bash
   # Получить подробное объяснение и recovery-команды для любого кода:
   .\.venv\Scripts\python.exe scripts/run_autonomous.py --explain-exit <N>
   ```

   | Код | Группа | Одна строка | Recovery |
   |-----|--------|-------------|----------|
   | 0 | Успех | post-agent OK, цепочка остановлена | — |
   | 10 | Успех non-stop | OK, читать `current_task.md` | `python scripts/workflow.py` |
   | 1 | DoD FAIL | тесты упали или max-loops | исправить код, `--post-agent` |
   | 2 | Registry gate | пакет не найден или реестр / производные не sync | `backlog_registry_lint.py --write-sync` |
   | 3 | Контракт отсутствует | нет `execution_contract.md` | `workflow.py --exec` → выполнить STEP 1–N |
   | 4 | DoD drift | DoD ослаблен без обновления реестра | `generate_orchestration_prompt.py --force` |
   | 5 | Verification-only | нет evidence block / нет `allow_verification_only`; если evidence commit меняет write-set, post-agent повышает режим до execution | добавить `Pre-existing delivery evidence:` или указать корректный delivery commit |
   | 6 | closure unknown | нет git-изменений или write-set пуст | проверить `git diff HEAD` |
   | 7 | Write-set mismatch | git-изменения не пересекаются с write-set | `generate_orchestration_prompt.py --force` |
   | 8 | CLI / context | неверные аргументы или context gate | проверить флаги, `check_llm_context_gate.py` |
   | 9 | Lock | другой процесс держит lock | дождаться или снять lock по pid |

4. Если пакет типа `idea-*` или `e*` и фича уже реализована (verification-only):
   - Заполни archive/team_artifacts/<package_id>/execution_contract.md блоком:
       Pre-existing delivery evidence:
       - commit: <sha 7-40 chars, изменивший хотя бы один referenced path>
       - files: <существующие пути в репо>
   - Добавь в Notes регистри-записи: allow_verification_only — <описание>.
   - Затем запускай --post-agent.
   - Если evidence commit реально меняет хотя бы один path из write-set пакета,
     `--post-agent` закрывает как `execution` без ручного `allow_verification_only`.

Не дублируй сценарии A/B/C — они описаны внутри `doc/current_task.md`.
```

## Статус конвейера в любой момент

```bash
.\.venv\Scripts\python.exe scripts/pipeline_status.py
```
