#!/usr/bin/env python3
"""
Печать эталонных промптов для агента: пакет ``epoch-demo`` (создание/переоткрытие + демо-код
в ``prompt_utils``) и отдельно — smoke ``run_autonomous.py --post-agent``. Префлайт reopen:
``scripts/print_reopen_package_workflow.py --package epoch-demo``.

Смысл: один вызов из чата, без копипаста длинного текста.

Пример:
  .\\.venv\\Scripts\\python.exe scripts/print_epoch_demo_agent_prompts.py
  .\\.venv\\Scripts\\python.exe scripts/print_epoch_demo_agent_prompts.py package
  .\\.venv\\Scripts\\python.exe scripts/print_epoch_demo_agent_prompts.py smoke
  .\\.venv\\Scripts\\python.exe scripts/print_epoch_demo_agent_prompts.py all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for _p in (ROOT, _SCRIPTS):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from script_stdio_utf8 import configure_stdio_utf8  # noqa: E402


# ---------------------------------------------------------------------------
# Prompt: epoch-demo package (create / reopen + demo function in prompt_utils)
# ---------------------------------------------------------------------------
PROMPT_EPOCH_DEMO_PACKAGE = r"""
Цель: (1) если пакета `epoch-demo` нет — создать минимальный каркас в `backlog_registry.yaml` и артефактах, затем регенерировать `tasklist.md`; (2) если пакет был закрыт — переоткрыть и подготовить к повторному прогону; (3) при **активной работе** пакета добавить в `scripts/prompt_utils.py` ровно **одну** демо-функцию, возвращающую строку (с однократным `uuid` внутри тела); (4) при **переоткрытии** после закрытия — **удалить эту функцию** из `prompt_utils.py` и сбросить артефакты пакета, чтобы сценарий можно было снова пройти с нуля. Запуск `run_autonomous --post-agent` — **не** в этом промпте.

Контекст:
- Репозиторий: корень checkout (каталог с `app/`, `doc/`, `scripts/`; не хардкодить букву диска)
- Python/проверки: .\.venv\Scripts\python.exe
- Разрушительные git-операции (`reset --hard`, `clean -fd`) — **только** с явным подтверждением в чате

---

## A. Детекция состояния

Определи одно из:

- **A1. Нет пакета:** в `doc/backlog_registry.yaml` нет записи `epoch-demo` со статусом `ready`/`wip`, нет synced generated view в `doc/tasklist.md`, нет `archive/team_artifacts/epoch-demo/`.
- **A2. Активен:** пакет в `backlog_registry.yaml` (`wip`/`ready`/`open`), generated view и контракт на месте.
- **A3. Закрыт:** статус `closed` в `doc/backlog_registry.yaml`, есть запись в `doc/closed_iterations.md` / и т.п.

Если **A2** и переоткрытие **не** требуется (только проверка) — можно остановиться с отчётом «уже в работе». Если нужен «чистый старт» при активном пакете — выполни раздел **C** + **D** по согласованию (как форс-ресет).

---

## B. Создание пакета (если A1)

1) **`doc/backlog_registry.yaml`**
   - Запись `epoch-demo` со статусом `ready` или `wip`.
   - Поля контракта:
     - **PACKAGE_ID:** `epoch-demo`
     - **Title:** коротко (smoke / demo)
     - **USER_STORIES:** `n/a (smoke)` — без выдуманных `US-x.y`, если не создаёшь реальные файлы stories
     - **OUTCOMES:** одна строка, достаточная для парсера
     - **TARGET_ARTIFACTS:** минимум `scripts/prompt_utils.py` (см. раздел D)
     - **DOD_COMMANDS:** одна **узкая** команда (не полный `pytest tests/`)
   - Пути в TARGET — только **существующие** в репо на момент правки (кроме явно создаваемого в D).

2) **`archive/team_artifacts/epoch-demo/`**
   - Создай каталог.
   - `execution_contract.md` — короткий placeholder (например `STARTED`), достаточный для жизненного цикла артефакта.

3) **Индексы**
   - `doc/tasklist.md` — **не редактировать вручную**; регенерировать через `backlog_registry_lint.py --sync-from-index --write-sync`.
   - `doc/user_stories/*.md`, `doc/user_stories_index.json` — **только** если в контракте реальные `US-x.y` и нужна связь; для `n/a` — **не трогай**.
   - `doc/changelog.md` — по политике команды (опционально одна строка о появлении пакета).

4) Линт registry (если правил): `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py`

---

## B2. Переоткрытие пакета (если A3)

0) **Префлайт:** `.\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo`.

1) **Если статус `closed` в registry:** выполни **полный** Step C по канону [doc/team_workflow/reopen_package_step_c_prompt.md](../../doc/team_workflow/reopen_package_step_c_prompt.md) — все индексы (включая `doc/closed_iterations.md` по правилам генератора), хвост `doc/changelog.md` при необходимости, `backlog_registry_lint.py --sync-from-index --write-sync`, и **`doc/current_task.md`** под `epoch-demo`. Краткие тезисы ниже **не** заменяют этот чек-лист.

2) В **`doc/backlog_registry.yaml`** после Step C у записи должны быть `ready`/`wip` и согласованный контракт (при необходимости восстанови поля из `closed_iterations` или предыдущего коммита).

3) **`doc/tasklist.md`** — только regenerated view после lint, не правь произвольный markdown вручную ради статуса.

4) **User stories** — только если пакет закрывал реальные US (у smoke `epoch-demo` часто пустой список): строго по тексту Step C в [generate_audit_closed_packages_prompt.md](../../doc/team_workflow/generate_audit_closed_packages_prompt.md). Иначе не трогай, кроме требований lint.

5) **`--auto-prepare-epoch-demo`** не заменяет Step C для пакета в `closed` после аудита — это каркас для отсутствующей записи / smoke, а не согласованное reopen по SSoT.

---

## C. Сброс при переоткрытии (обязательно перед повторным прогоном)

1) **`scripts/prompt_utils.py`**
   - **Удали целиком** демо-функцию из раздела D (точное имя — как при создании; без рефакторинга остального файла).
   - Проверь, что нет «осиротевших» импортов/вызовов только ради неё.

2) **`archive/team_artifacts/epoch-demo/execution_contract.md`**
   - Сбрось к короткому placeholder для нового прогона.

3) Проверка: `.\.venv\Scripts\python.exe -m py_compile scripts/prompt_utils.py`
   Узкий pytest — только если есть релевантный тест и вы договорились (не полный suite).

---

## D. Добавление кода в активной итерации (один раз за прогон пакета)

**Файл:** только `scripts/prompt_utils.py` (минимальный diff).

**Добавь одну функцию** с **фиксированным говорящим именем**, например:
- `epoch_demo_placeholder_text`
(имя должно быть уникальным и легко находимым через `grep`.)

**Смысл контракта:**

- Возвращает `str`.
- **Вариативность:** достаточно **один раз** в теле функции получить значение (например `uuid.uuid4()`) и **сразу** подставить его в возвращаемую строку (без состояния между вызовами, без лишней логики).
- Не тянуть тяжёлые зависимости; стандартная библиотека достаточна (`uuid` уже в stdlib).
- Не менять существующие публичные API; ничего не подключать к прод-пайплайну — только демо для пакета.
- Комментарий у функции: `# epoch-demo: temporary — remove on package reopen`

**Write-set в контракте `epoch-demo`:** укажи `scripts/prompt_utils.py` в **TARGET_ARTIFACTS** / write-set.

**Работа с файлом:** не читать `prompt_utils.py` целиком; правка — маленьким патчем; при сомнениях — `rg "def epoch_demo"` / сигнатуры.

---

## E. Ограничения

- Не запускать `run_autonomous.py` / `--post-agent` в этом промпте.
- Не запускать полный `pytest tests/`.
- Не трогать несвязанные модули кроме согласованного write-set.
- Для отката **всего** пакета по git, если когда-то понадобится шире, чем удаление одной функции — отдельное согласование; **в базовом сценарии переоткрытия** достаточно раздела C.

---

## F. Итоговый отчёт

- Состояние до: A1 | A2 | A3
- Сделано: create | reopen | reset artifacts | add function | remove function
- Имя демо-функции (если применимо)
- Список изменённых файлов
- `py_compile` / `backlog_registry_lint`: OK или FAIL (с причиной)
""".strip()


# ---------------------------------------------------------------------------
# Prompt: smoke run_autonomous --post-agent (реальный CLI)
# ---------------------------------------------------------------------------
PROMPT_POST_AGENT_SMOKE = r"""
Цель: выполнить быстрый smoke реального CLI-потока `run_autonomous.py --post-agent` на тестовом пакете `epoch-demo` и вручную проверить UX блокировок (не unit-тесты).

Контекст:
- Репозиторий: <REPO_ROOT> (корень checkout: есть каталоги `app/`, `scripts/`, `doc/`)
- ОС: Windows / PowerShell (или ваш терминал; команды ниже — вид для PowerShell из корня репо)
- Python: .\.venv\Scripts\python.exe из корня репозитория
- Пакет: `epoch-demo` — должен быть в `doc/backlog_registry.yaml`, производный `doc/tasklist.md` синхронизирован, есть `archive/team_artifacts/epoch-demo/execution_contract.md`
- Важно: скрипт `scripts/run_autonomous.py` НЕ переоткрывает пакет автоматически. Если в registry статус `closed`, переоткрытие делает исполнитель этого промпта ДО любого запуска `run_autonomous.py`.

Шаги:

1) Перейди в корень репозитория. Префлайт статуса:
   .\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package epoch-demo

2) Только если префлайт показал `registry status: 'closed'` — сразу выполни **автоматический полный Step C** (до шага 3), одной командой из корня репозитория:
   .\.venv\Scripts\python.exe scripts/reopen_epoch_demo_step_c.py --reason "smoke post-agent: registry closed before --post-agent"
   Скрипт выставляет `epoch-demo` в `ready`, при необходимости переводит **остальные** пакеты со статусом `ready`/`wip` в `proposed` (инвариант Truth View «один активный»; отключить: `--no-demote-other-active`), правит индексы/changelog/`doc/current_task.md` по канону для smoke-пакета `epoch-demo` и дважды вызывает `backlog_registry_lint.py --sync-from-index --write-sync` (второй раз с `--strict`). Он **не** делает git commit (C.8) и **не** сбрасывает `prompt_utils` / `execution_contract.md` — при необходимости сбрось артефакты по промпту `package` (`scripts/print_epoch_demo_agent_prompts.py package`) **после** успешного скрипта и до `run_autonomous.py`, если сценарий требует «чистый» прогон.
   Если автоматизация не подходит (другой пакет, спорный REASON, нестандартные US) — вручную полный Step C по `doc/team_workflow/reopen_package_step_c_prompt.md`, затем всё равно lint как в каноне.
   Если статус уже `ready`/`wip`, шаг 2 пропускаешь (скрипт при вызове тоже noop с кодом 0); достаточно актуального tasklist и `execution_contract.md`.

3) Только после выполнения шагов 1–2 запусти один реальный вызов:
   .\.venv\Scripts\python.exe scripts/run_autonomous.py --post-agent --package epoch-demo --budget-profile strict

   Опционально (без кэша DoD для этого прогона): добавь `--no-dod-cache`

4) Зафиксируй: exit code; ключевые строки stderr/stdout; ветку (verification_only / unknown / execution hard gate / DoD / другое).

5) UX: понятная причина блокировки; actionable next steps; согласованные подсказки (`allow_verification_only`, `evidence_inconclusive_allowed` где уместно); нет противоречий между сообщениями.

6) Краткий отчёт в чат: Command — Exit code — Branch — Key messages (3–8 строк) — UX PASS или FAIL — при FAIL: что не так и куда смотреть (файл/область).

7) **В конце отчёта** (если в шаге 2 сработал автодемоут боевых пакетов `ready`/`wip`→`proposed`, см. строку лога `Truth View: demoted …`, или ты вручную знаешь затронутый `PACKAGE_ID`): сгенерируй **готовый промпт для следующего чата** в отдельном блоке заголовка `### Follow-up: вернуть боевой пакет в ready`. Этот промпт исполнитель вставит в новый чат как есть (с подставленными значениями). Он должен явно требовать:
   - корень репо, интерпретатор `.\.venv\Scripts\python.exe`;
   - **инвариант Truth View:** в `doc/backlog_registry.yaml` среди `items` не более **одной** строки со статусом `ready` или `wip`; прежде чем возвращать боевой пакет `<PACKAGE_ID>` в `ready`, при необходимости **освободить слот** (например вернуть `epoch-demo` в `closed` и зафиксировать закрытие по канону, либо оставить только один активный пакет — выбрать согласованно с owner);
   - для целевого `<PACKAGE_ID>`: `status: ready` (и при необходимости поля по `doc/team_workflow/reopen_package_step_c_prompt.md` / owner);
   - затем `.\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync --strict`;
   - затем `.\.venv\Scripts\python.exe scripts/roadmap_sync_check.py` (ожидается PASS);
   - краткий итог: какой пакет снова единственный активный `ready`/`wip`, чем подтверждено.
   Если демоута не было (шаг 2 пропущен или список demoted пуст), шаг 7: одна строка «Follow-up не требуется (активные пакеты не понижались)».

Ограничения: не полный `pytest tests/` как замена этому smoke; без force-push; без несанкционированных правок CI.

Критерий готовности: один реальный запуск `--post-agent` выполнен, результат и UX оценены; при понижении боевых пакетов — в отчёте есть блок **Follow-up** из шага 7 (или явная строка что follow-up не нужен).
""".strip()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Print agent prompts for epoch-demo package work and post-agent smoke.",
    )
    p.add_argument(
        "which",
        nargs="?",
        default="all",
        choices=("package", "smoke", "all"),
        help="package = только промпт пакета; smoke = только post-agent smoke; all = оба (по умолчанию)",
    )
    return p


def main() -> int:
    configure_stdio_utf8()
    args = _build_parser().parse_args()
    sep = "\n\n" + "=" * 72 + "\n\n"
    if args.which == "package":
        print(PROMPT_EPOCH_DEMO_PACKAGE)
    elif args.which == "smoke":
        print(PROMPT_POST_AGENT_SMOKE)
    else:
        print(
            "=== Промпт 1/2: пакет epoch-demo (backlog_registry, generated tasklist, артефакты, демо-функция в prompt_utils) ===\n"
            + PROMPT_EPOCH_DEMO_PACKAGE
            + sep
            + "=== Промпт 2/2: smoke run_autonomous --post-agent ===\n"
            + PROMPT_POST_AGENT_SMOKE,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
