# Промпт: переоткрытие одного закрытого пакета (Step C)

**Назначение:** ручное **атомарное** переоткрытие одного `PACKAGE_ID` со статусом `closed` → `ready` с сохранением SSoT, без полного прогона `generate_audit_closed_packages_prompt`. После смены статуса **обязательно** синхронизируй [current_task.md](../current_task.md), чтобы autonomous и оператор не опирались на runtime-файл, всё ещё описывающий другой (устаревший) пакет.

**Когда использовать:** подтверждённый **INDEX_FAIL** или **DoD FAIL / STALE** по пакету; заполненный оператором **`REASON`**. Не заменяет аудит целиком — только исполняет **STEP C — REVERT PROCEDURE** из генератора.

**Канон (детали подшагов C.1–C.8):** [generate_audit_closed_packages_prompt.md](generate_audit_closed_packages_prompt.md) — блок `STEP C — REVERT PROCEDURE`.

**Связанные сценарии:**

- Батч переоткрытия за календарное окно: [reopen_prompt_closed_window_template.md](reopen_prompt_closed_window_template.md).
- Полный аудит закрытых пакетов: [generate_audit_closed_packages_prompt.md](generate_audit_closed_packages_prompt.md).

**Интерпретатор:** `.\.venv\Scripts\python.exe` (из корня репозитория).

**Префлайт (статус в SSoT + напоминание, без правок файлов):**

```bash
.\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package PACKAGE_ID [--reason "..."] [--today YYYY-MM-DD]
```

Тот же скрипт используют [epoch_demo_post_agent_smoke.md](archive/epoch_demo_post_agent_smoke.md) и промпт `package` в `print_epoch_demo_agent_prompts.py` для `epoch-demo`.

---

<a id="reopen-step-c-paste"></a>

## Текст для вставки в новый чат

```text
╔══════════════════════════════════════════════════════════════════╗
║  PACKAGE REOPEN — Step C (closed → ready), один пакет за раз
║  Источник правды: doc/backlog_registry.yaml + производные из lint
╚══════════════════════════════════════════════════════════════════╝

ПАРАМЕТРЫ (подставь вручную):
  PACKAGE_ID   = <например epoch-home-mode-preview-drawer>
  TODAY        = <YYYY-MM-DD, сегодня по календарю оператора>
  REASON       = <одна строка: INDEX_FAIL / DOD FAIL / STALE + краткая причина>
  PERIOD_SLUG  = <для сообщения коммита: YYYY-MM или YYYY-MM-DD__YYYY-MM-DD>

Полный канон подшагов: doc/team_workflow/generate_audit_closed_packages_prompt.md
  — блок «STEP C — REVERT PROCEDURE» (C.1 … C.8). Ниже — операционная выжимка
  + обязательный доп. шаг для doc/current_task.md (runtime-задача для агентов).

РОЛЬ:
  Только документы/registry из чек-листа Step C. Прикладной код (app/, tests/, scripts/)
  не менять, если задача — «чистое» переоткрытие индексов.

ПРЕДПРОВЕРКА:
  0) Опционально: .\.venv\Scripts\python.exe scripts/print_reopen_package_workflow.py --package PACKAGE_ID [--reason "..."]
     (подтверждает статус в SSoT и печатает путь к этому документу).
  1) В doc/backlog_registry.yaml у записи id == PACKAGE_ID должно быть status: closed
     (если иначе — уточни у оператора).
  2) Собери список US: covered_by == PACKAGE_ID в doc/user_stories_index.json
     и при необходимости doc/user_stories/*.md.

ВЫПОЛНИ ПО ПОРЯДКУ (атомарно для ОДНОГО PACKAGE_ID):

  C.1  doc/backlog_registry.yaml:
       status: closed → status: ready
       re_entry_condition: "audit $TODAY: $REASON"
       last_review: $TODAY

  C.2  doc/closed_iterations.md:
       В «Индекс Эпох» убери строку с PACKAGE_ID из индекса (см. канон).
       В «Recent» у соответствующего заголовка — пометка ⚠️ REOPENED $TODAY.
       Блоки Goal/Delivered не удалять.

  C.3  doc/user_stories_index.json:
       Для US, связанных с PACKAGE_ID: снять закрытие (status / closed_date / covered_by)
       строго по правилам репозитория и по тексту STEP C в generate_audit_closed_packages_prompt.md.
       После правки один раз:
         .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync

  C.4  doc/user_stories/<US>.md — только frontmatter для затронутых US.
       Согласуй с индексом C.3. Если lint ожидает иной статус (например open + covered_by: null
       при пакете ready) — исправь по WARN/FAIL lint, а не «на глаз».

  C.5  doc/cjm.md — метки MoT для PACKAGE_ID / затронутых US (см. канон Step C).

  C.6  doc/changelog.md — ТОЛЬКО append:
       ## Reopened: PACKAGE_ID ($TODAY)
       - Reason: $REASON
       - Affected US: <список>
       - Action: closed → ready; индекс closed_iterations обновлён

  C.7  Повторно:
       .\.venv\Scripts\python.exe scripts/backlog_registry_lint.py --sync-from-index --write-sync
       При принятом в команде режиме добавь --strict.
       Проверь, что doc/tasklist.md пересобран и PACKAGE_ID отражён как ready.

  ДОП. runtime (обязательно для этого репозитория):
       doc/current_task.md — приведи в соответствие с переоткрытым PACKAGE_ID (статус ready):
       autonomous-заголовок / goal / write-set / DoD и команды из записи PACKAGE_ID в
       doc/backlog_registry.yaml; archive/team_artifacts/<PACKAGE_ID>/; убери устаревшие
       ссылки на другой пакет как «текущий», если он больше не должен быть первым в работе.

  C.8  Один git-коммит на пакет (если политика сессии разрешает):
       git add doc/backlog_registry.yaml doc/closed_iterations.md doc/user_stories_index.json
            doc/changelog.md doc/tasklist.md doc/cjm.md doc/current_task.md doc/user_stories/<affected>.md
       git commit -m "audit($PERIOD_SLUG): reopen PACKAGE_ID — REASON"

ЗАПРЕЩЕНО:
  Менять только backlog_registry.yaml или только tasklist.md без остальных шагов C и без lint.
  Несколько PACKAGE_ID в одном коммите. Переписывать старые записи changelog.

ОТЧЁТ В ЧАТ:
  Таблица: PACKAGE_ID | affected US | изменённые файлы (+ current_task.md) | lint exit code | commit (если был).
```

---

## После переоткрытия

Вести пакет снова через конвейер: [generate_orchestration_prompt.md](generate_orchestration_prompt.md) (см. Next Actions в шаблоне аудита).
