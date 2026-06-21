# DeepSeek API trigger experiment (`--trigger-cmd`)

**Связь:** умный роутер [`workflow_router.md`](../workflow_router.md) · скрипт `scripts/deepseek_agent_trigger.ts` · adapter [`agent_adapter_continue.md`](agent_adapter_continue.md)

> Статус: **эксперимент / handoff-only**. Этот wrapper вызывает DeepSeek OpenAI-compatible Chat API. У Chat API нет локальных file/shell tools, поэтому `scripts/deepseek_agent_trigger.ts` не является production executor и не должен использоваться как путь zero-click delivery.
>
> Результат эксперимента: Chat API path полезен как диагностический handoff (`BLOCKED: no local tool access`) и как proof-gate упражнение, но реальное исполнение должно идти через локальный агент. Целевой план: [`workflow_deepseek_tui_trigger_implementation_plan.md`](workflow_deepseek_tui_trigger_implementation_plan.md).

---

## 1. Назначение

Роутер `workflow.py --loop --skip-review --watch-contract` сначала генерирует `doc/current_task.md`, затем может запустить команду из `--trigger-cmd`.

Для DeepSeek Chat API эта связка теперь считается **экспериментальной**:

```powershell
.\.venv\Scripts\python.exe scripts\workflow.py --loop --skip-review --watch-contract `
  --trigger-cmd "npx tsx scripts/deepseek_agent_trigger.ts" `
  --agent continue --post-agent-no-dod-cache
```

`--agent continue` важен для корректной attribution и `orchestration_continue.md`, но этот command не исполняет задачу в репозитории. Ожидаемый честный результат для orchestration/code пакетов — `BLOCKED: no local tool access` и остановка кондуктора для ручного IDE/TUI handoff.

Production-варианты:

- Cursor SDK: [`workflow_cursor_sdk_trigger_guide.md`](workflow_cursor_sdk_trigger_guide.md)
- DeepSeek TUI executor: [`workflow_deepseek_tui_trigger_implementation_plan.md`](workflow_deepseek_tui_trigger_implementation_plan.md)

---

## 2. Предварительные требования

1. Node.js и npm доступны в `PATH`.
2. В корне репозитория один раз выполнено:
   ```powershell
   npm install
   ```
3. В окружении текущего PowerShell задан ключ:
   ```powershell
   $env:DEEPSEEK_API_KEY = "sk-..."
   ```
4. Опционально можно переопределить модель:
   ```powershell
   $env:DEEPSEEK_MODEL = "deepseek-reasoner"
   ```

`workflow.py` не загружает `.env` сам по себе. Дочерний `npx tsx ...` наследует переменные окружения только из процесса, в котором запущен `workflow.py`.

---

## 3. Что эксперимент показал

1. `workflow.py` находит активный пакет в `doc/backlog_registry.yaml`.
2. `run_autonomous.py` генерирует `doc/current_task.md`.
3. `workflow.py` передаёт путь к задаче через `WORKFLOW_CURRENT_TASK_PATH`.
4. `deepseek_agent_trigger.ts` читает задачу и вызывает DeepSeek Chat API.
5. Для code/orchestration пакетов Chat API не может читать/писать repo files и должен вернуть `BLOCKED: no local tool access`.
6. `run_autonomous.py --post-agent` распознаёт такой контракт как chat-api handoff и возвращает exit `11`; пакет не закрывается.
7. Реальную работу нужно выполнить в агенте с локальными file tools, затем заменить `execution_contract.md` на настоящий `EXECUTION_PROOF:`.

---

## 4. Перед orchestration-пакетом

Если пакет идёт через orchestration, сначала сгенерируйте Continue-specific документ:

```powershell
.\.venv\Scripts\python.exe scripts\generate_orchestration_prompt.py --agent continue
```

После этого loop-команда выше создаст `doc/current_task.md` со ссылкой на `archive/team_artifacts/<PACKAGE_ID>/orchestration_continue.md`.

---

## 5. Что передаётся trigger-у

| Переменная | Смысл |
|------------|-------|
| `WORKFLOW_CURRENT_TASK_PATH` | Абсолютный путь к `doc/current_task.md` |
| `DEEPSEEK_API_KEY` | Ключ DeepSeek API из окружения |
| `DEEPSEEK_MODEL` | Опциональная модель, если нужно переопределить default |
| `DEEPSEEK_TRIGGER_HEARTBEAT_MS` | Интервал heartbeat; `0` отключает |
| `DEEPSEEK_TRIGGER_STARTED_STALL_TIMEOUT_MS` | Guard для зависшего `STARTED` marker; `0` отключает |

Метрики пишутся в `archive/team_artifacts/_metrics/deepseek_agent_trigger.jsonl`.

---

## 6. Формат proof-gate

DeepSeek API сам по себе не имеет локального tool executor. Поэтому `deepseek_agent_trigger.ts` не должен превращать рассуждение модели в evidence. Валидный ответ должен начинаться с:

```text
EXECUTION_PROOF:
Changed files:
Verification:
```

Trigger принимает:

- блок `EXECUTION_PROOF:` с секциями `Changed files:` и `Verification:` только для текстовых/диагностических случаев, где proof действительно получен вне локальных file tools;
- `BLOCKED: no local tool access` — допустимый сигнал «модель не имеет доступа к репо»; контракт записывается, `run_autonomous.py --post-agent` возвращает exit `11`, а `workflow.py --loop` останавливает кондуктор.

Trigger отклоняет (rc=2):

- план выполнения без `EXECUTION_PROOF:` (фразы `I'll start...`, `I will read...`);
- команды создания `STARTED` / чтения orchestration (`cat archive/...`, `get-content`);
- текст без `Changed files:` и `Verification:` после маркера `EXECUTION_PROOF:`.

Если trigger завершился с `invalid_contract`, это ожидаемый отказ: пакет не должен переходить к `post-agent`, пока нет реального execution proof.

---

## 7. Troubleshooting

| Симптом | Действие |
|---------|----------|
| `DEEPSEEK_API_KEY must be set` | Задать переменную в том же PowerShell до запуска `workflow.py`. |
| `DeepSeek API returned status 401/403` | Проверить ключ, права и отсутствие пробелов в значении env. |
| `DeepSeek returned empty content` | Повторить запуск; если повторяется, проверить модель и prompt size. |
| `execution_contract.md` остался только `STARTED` | Trigger остановит run по stall timeout; перезапустить после проверки задачи. |
| `generated execution_contract.md rejected` / `invalid_contract` | Модель вернула план или неполный proof. Нужен ответ в формате `EXECUTION_PROOF:` с `Changed files:` и `Verification:`. Если на диске остался старый контракт, удалить/перезаписать его перед повторным loop. |
| `--post-agent` вернул **11** (`chat-api handoff`) | Контракт содержит `BLOCKED: no local tool access`. Это ожидаемый итог эксперимента для Chat API. Выполните оркестрацию в IDE/TUI-агенте, замените контракт на реальный proof, затем перезапустите `--loop`. |
| `--post-agent` закрылся с ненулевым кодом | Смотреть DoD/evidence output; trigger уже выполнил только веху 1/3. |

---

## 8. Связанные файлы

- Cursor SDK trigger: [`workflow_cursor_sdk_trigger_guide.md`](workflow_cursor_sdk_trigger_guide.md)
- DeepSeek TUI target plan: [`workflow_deepseek_tui_trigger_implementation_plan.md`](workflow_deepseek_tui_trigger_implementation_plan.md)
- Router overview: [`workflow_router.md`](../workflow_router.md)
- Adapter: [`agent_adapter_continue.md`](agent_adapter_continue.md)
- Trigger implementation: `scripts/deepseek_agent_trigger.ts`
