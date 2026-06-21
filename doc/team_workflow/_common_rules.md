# Общие правила для промптов `doc/team_workflow/`

Канонические фрагменты. В других промптах **не копировать дословно** — достаточно одной строки со ссылкой, например:

> См. [`_common_rules.md`](_common_rules.md#windows--powershell-терминал) (нужные подзаголовки).

---

## Windows / PowerShell (терминал)

**PowerShell 5.1 (дефолт Win10/11):** нельзя использовать цепочку в стиле cmd: `cd /d … && …` (`&&` здесь недоступен, `cd /d` — синтаксис cmd). **Запрещено** предлагать или выполнять такую обёртку через Shell tool.

**Интерпретатор Python:** из корня репозитория сначала `.\.venv\Scripts\python.exe` (см. [`AGENTS.md`](../../AGENTS.md)). Если `.venv` недоступен — допустим fallback `python` / `py`.

Если текущий каталог не корень репозитория — **одна** строка PowerShell с разделителем **`;`** (не `&&`):

```text
Set-Location -LiteralPath '<корень-репозитория>'; .\.venv\Scripts\python.exe <команда>
```

---

## SSoT: backlog и производные

`doc/backlog_registry.yaml` — **SSoT** статусов пакетов и волн.

`doc/tasklist.md` — **производный** weekly view; генерируется линтером из реестра.

**Запрещено:** вручную менять `tasklist.md`, чтобы «закрыть» пакет или переписать контракт. Менять только YAML, затем запускать sync (см. [Sync](#sync-регенерация-tasklist)).

**Умный роутер (`scripts/workflow.py`):** не открывает `doc/tasklist.md`, не сравнивает его с реестром и не выводит предупреждений о нём. Для маршрутизации `no_package` / `ready_fresh` / … использовать **только** `doc/backlog_registry.yaml`. В промптах и read-set агента при работе с роутером **запрещено** опираться на `tasklist.md` как на источник статуса пакета.

---

## Token budget (LLM / read-set)

- Целевой бюджет: **≤ ~12k входных токенов** на один LLM-вызов, когда возможно.
- **12k–20k:** сжать history/read-set перед отправкой.
- **> 20k:** не отправлять; остановиться и зафиксировать блокер.

Read-set: **макс. 3–5 файлов** на вызов (для рутины 2–3). Крупные модули и запрещённые full-read — по [`doc/token_safety.md`](../token_safety.md) и `scripts/check_readset.py`.

В многофазных сценариях (plan-next и т.п.) не раздувать суммарное чтение: уменьшать пул кандидатов или read-set, если фазы упираются в бюджет.

---

## Sync: регенерация tasklist

После любых правок статуса/контракта в `doc/backlog_registry.yaml` обязательно:

- если в реестре `schema_version >= 2` — сначала строгая проверка и sync:

  ```bash
  python scripts/backlog_registry_lint.py --strict --sync-from-index --write-sync
  ```

- иначе (legacy v1):

  ```bash
  python scripts/backlog_registry_lint.py --sync-from-index --write-sync
  ```

Из корня в PowerShell (типичный вид):

```powershell
.\.venv\Scripts\python.exe scripts\backlog_registry_lint.py --sync-from-index --write-sync
```
