# Zero-Click Autonomous Delivery

Updated: **2026-04-22**

Self-Propagating Delivery Loop — конвейер полностью замкнут: агент сам закрывает пакет и сам генерирует следующую задачу.

---

## Архитектура: Self-Propagating Loop

```
Human: python scripts/run_autonomous.py
       ↓  создаёт doc/current_task.md (с Mandatory Final Step внутри)
Agent: читает файл → реализует → запускает --post-agent → запускает run_autonomous
       ↓  post_agent: DoD → close_package → генерирует следующий doc/current_task.md
Agent: читает следующий файл → ...
```

**Cursor hook (`stop`)** страхует: если агент забыл запустить `--post-agent` — Cursor инжектирует напоминание в следующем followup.

---

## Команды

```powershell
# Запустить конвейер (создаёт doc/current_task.md)
python scripts/run_autonomous.py --agent cursor_ai

# Закрыть пакет после выполнения задачи агентом (+ цепная генерация следующей)
python scripts/run_autonomous.py --post-agent --package <id>

# Полный автономный цикл через claude-code (TDD loop без человека)
python scripts/run_autonomous.py --agent claude_code

# Статус конвейера одной командой
python scripts/pipeline_status.py

# PowerShell-лаунчеры (также работают)
powershell -ExecutionPolicy Bypass -File scripts/run_autonomous.ps1 -TargetAgent cursor_ai
scripts\run_autonomous.bat claude_code
```

---

## Как работает под капотом

1. **`run_autonomous.py`** → `start_workflow.py` определяет действие (PLAN_NEXT / EXECUTION_AUTO / ORCHESTRATION / RESUME) и сложность пакета.
2. Генерирует промпт через `generate_next_prompt.py` или `generate_orchestration_prompt.py`.
3. **GUI агенты** (`cursor_ai`, `codex`): пишет `doc/current_task.md` с **Mandatory Final Step** внутри — агент обязан запустить `--post-agent` и `run_autonomous.py` в конце сессии.
4. **CLI агент** (`claude_code`): запускает `claude -p -` (через stdin), после завершения прогоняет DoD, при ошибках — Resume TDD loop, при успехе — автоматически закрывает пакет.
5. **`post_agent()`**: DoD → `close_package.py` → `run_autonomous.py` (цепная генерация следующего task file).
6. **`pipeline_guard.py`** (Cursor `stop` hook): при завершении сессии с незакрытым `ready`-пакетом и свежим `doc/current_task.md` — инжектирует followup с точной командой.

---

## Для AI Агентов

Единственная точка входа — **`doc/current_task.md`**.

Файл содержит всё необходимое: контракт, DoD, read-set, constraints. В конце файла — **Mandatory Final Step** с двумя shell-командами, которые агент обязан выполнить после реализации. Этот шаг замыкает конвейер.
