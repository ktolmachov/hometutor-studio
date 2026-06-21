# Demo Scenarios Prompt Bundle

Актуализировано: **2026-05-01**

Назначение: переиспользуемый bundle для актуализации demo-сценариев, demo e2e-тестов, скриншотов и `doc/quickstart_demo.md`.

Контур:

```text
doc/scenarios/*.yaml
  -> tests/e2e/demos/*.spec.ts
  -> doc/screenshots/<RUN>/<scenario_id>/   (RUN = YYYY-MM-DD, см. ниже)
  -> scripts/generate_demo_doc.py  (перед записью: пересобирает doc/screenshots/final/ из <RUN>/)
  -> doc/quickstart_demo.md  (картинки: screenshots/final/... — стабильные ссылки)
```

**Скриншоты по прогонам:** при новом съёме **не** трогаем папки прошлых прогонов. Каталог `doc/screenshots/<RUN>/` считаем **неизменяемым архивом**: повторно писать в тот же `<RUN>` нельзя — при съёмке того же сценария `DemoRecorder` очищает **только** `…/<RUN>/<scenario_id>/`. Для новой съёмки нужен **новый** `RUN` в формате `YYYY-MM-DD` (по умолчанию `localRunFolderName()` в `tests/e2e/fixtures/demo_recorder.ts`).

**`npm run demo:validate`:** скрипт `scripts/validate_demo_contract.py` запускается без `--screenshots-dir`; корень кадров выбирается так же, как в коде валидатора: `DEMO_SHOT_RUN` → иначе плоская вёрстка `doc/screenshots/scenario_*` → иначе **последний по имени** датированный `doc/screenshots/YYYY-MM-DD`. Чтобы не гадать, какой RUN подставился, для локального прогона надёжнее всегда задавать `$env:DEMO_SHOT_RUN` или явный `--screenshots-dir $SHOTS`.

Текущие demo-сценарии:

| Scenario | YAML | Demo spec | Screenshots (каталог прогона) |
|---|---|---|---|
| `scenario_01` | `doc/scenarios/scenario_01_first_answer.yaml` | `tests/e2e/demos/scenario_01_first_answer.spec.ts` | `doc/screenshots/<RUN>/scenario_01/` |
| `scenario_02` | `doc/scenarios/scenario_02_home_navigation.yaml` | `tests/e2e/demos/scenario_02_home_navigation.spec.ts` | `doc/screenshots/<RUN>/scenario_02/` |
| `scenario_03` | `doc/scenarios/scenario_03_answer_to_tutor.yaml` | `tests/e2e/demos/scenario_03_answer_to_tutor.spec.ts` | `doc/screenshots/<RUN>/scenario_03/` |
| `scenario_04` | `doc/scenarios/scenario_04_mini_quiz.yaml` | `tests/e2e/demos/scenario_04_mini_quiz.spec.ts` | `doc/screenshots/<RUN>/scenario_04/` |
| `scenario_05` | `doc/scenarios/scenario_05_flashcards_create.yaml` | `tests/e2e/demos/scenario_05_flashcards_create.spec.ts` | `doc/screenshots/<RUN>/scenario_05/` |
| `scenario_06` | `doc/scenarios/scenario_06_spaced_repetition.yaml` | `tests/e2e/demos/scenario_06_spaced_repetition.spec.ts` | `doc/screenshots/<RUN>/scenario_06/` |
| `scenario_07` | `doc/scenarios/scenario_07_progress_gaps.yaml` | `tests/e2e/demos/scenario_07_progress_gaps.spec.ts` | `doc/screenshots/<RUN>/scenario_07/` |
| `scenario_08` | `doc/scenarios/scenario_08_source_trust.yaml` | `tests/e2e/demos/scenario_08_source_trust.spec.ts` | `doc/screenshots/<RUN>/scenario_08/` |
| `scenario_09` | `doc/scenarios/scenario_09_personalized_plan.yaml` | `tests/e2e/demos/scenario_09_personalized_plan.spec.ts` | `doc/screenshots/<RUN>/scenario_09/` |
| `scenario_10` | `doc/scenarios/scenario_10_day2_resume.yaml` | `tests/e2e/demos/scenario_10_day2_resume.spec.ts` | `doc/screenshots/<RUN>/scenario_10/` |
| `scenario_11` | `doc/scenarios/scenario_11_anki_export.yaml` | `tests/e2e/demos/scenario_11_anki_export.spec.ts` | `doc/screenshots/<RUN>/scenario_11/` |
| `scenario_12` | `doc/scenarios/scenario_12_quiz_to_deck.yaml` | `tests/e2e/demos/scenario_12_quiz_to_deck.spec.ts` | `doc/screenshots/<RUN>/scenario_12/` |
| `scenario_13` | `doc/scenarios/scenario_13_course_workspace.yaml` | `tests/e2e/demos/scenario_13_course_workspace.spec.ts` | `doc/screenshots/<RUN>/scenario_13/` |
| `scenario_14` | `doc/scenarios/scenario_14_full_sync.yaml` | `tests/e2e/demos/scenario_14_full_sync.spec.ts` | `doc/screenshots/<RUN>/scenario_14/` |

Жесткий принцип: **YAML-манифест является source of truth**. Demo specs и screenshots должны быть производными от него.

---

## Master Prompt — Demo Refresh Orchestrator

Скопируй этот prompt в агента, если нужно пройти весь цикл: audit -> YAML -> demo specs -> screenshots -> quickstart -> review.

````markdown
# MASTER PROMPT — Demo Scenarios Refresh Orchestrator

Ты работаешь из корня репозитория.

Цель: полностью актуализировать demo-контур проекта:
- `doc/scenarios/*.yaml`
- `tests/e2e/demos/*.spec.ts`
- `doc/screenshots/<RUN>/<scenario_id>/` (`RUN`: `YYYY-MM-DD`)
- `doc/quickstart_demo.md`

Опорные README:
- `tests/e2e/README.md`
- `doc/scenarios/README.md`
- `doc/screenshots/README.md`

Текущие scenario IDs:
- `scenario_01`
- `scenario_02`
- `scenario_03`
- `scenario_04`
- `scenario_05`
- `scenario_06`
- `scenario_07`
- `scenario_08`
- `scenario_09`
- `scenario_10`
- `scenario_11`
- `scenario_12`
- `scenario_13`
- `scenario_14`

Главный инвариант:
- YAML — source of truth.
- Каждый `shots[].slug` из YAML должен иметь ровно один соответствующий `demo.shot(...)` в demo spec.
- Каждый screenshot PNG должен соответствовать slug из YAML.
- `meta.json` должен отражать фактически снятые кадры.
- Кадры хранятся под `doc/screenshots/<RUN>/<scenario_id>/`; при новом прогоне добавляется новая папка `RUN` (только дата), старые не удаляются.
- `doc/quickstart_demo.md` собирается из YAML + screenshots (тот же `--screenshots-dir`, что и у прогона); **картинки в markdown** — из `doc/screenshots/final/` (папка пересоздаётся при **публикации** `generate_demo_doc.py` без `--no-final-sync`; для черновика можно `--no-final-sync` + отдельный `--output`).

Ограничения проекта:
- Соблюдай `AGENTS.md`.
- Python-команды запускай через `.\.venv\Scripts\python.exe`, если venv доступен.
- Не запускай весь pytest suite.
- Не читай крупные файлы целиком.
- Не трогай unrelated files.
- Не делай bare `except`.
- Demo-сценарии с `offline_friendly: true` не должны требовать live LLM.
- `npm run demo:validate` без аргументов сам выбирает каталог кадров (`DEMO_SHOT_RUN` / плоская вёрстка / последний датированный RUN — как в `validate_demo_contract.py`). Чтобы не ошибиться, перед прогоном задавай `$env:DEMO_SHOT_RUN` или передавай `--screenshots-dir $SHOTS`.

Write-set:
- `doc/scenarios/scenario_*.yaml` (все 14 demo-сценариев)
- `tests/e2e/demos/scenario_*.spec.ts` (все 14 demo-specs)
- `doc/screenshots/<RUN>/scenario_*/**` (фактический `RUN` = прогон)
- `doc/screenshots/final/**` (пересоздаётся при публикации: `generate_demo_doc.py` без `--no-final-sync`)
- `doc/quickstart_demo.md`

Если нужно менять helper/harness-файл вне write-set, сначала остановись и объясни почему.

## Step 0 — Preflight

Выполни:

```powershell
Get-ChildItem doc\scenarios -Filter "scenario_*.yaml" | Sort-Object Name | Select-Object -ExpandProperty Name
Get-ChildItem tests\e2e\demos -Filter "scenario_*.spec.ts" | Sort-Object Name | Select-Object -ExpandProperty Name
Get-ChildItem doc\screenshots -Directory | Select-Object -ExpandProperty Name
# ожидаем подпапки RUN (YYYY-MM-DD); внутри — scenario_01..scenario_14
# при необходимости: $env:DEMO_SHOT_RUN='<YYYY-MM-DD>' чтобы demo:validate смотрел на нужный прогон (иначе авто-выбор — см. вступление к этому файлу)
npm run demo:validate
```

Затем проверь YAML parse:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -c "import pathlib, yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('doc/scenarios').glob('scenario_*.yaml')]; print('YAML OK')"
```

Если YAML не парсится — сначала исправь YAML.
Если `npm run demo:validate` падает на YAML/spec mismatch — сначала исправь контракт, не запускай Playwright.

## Step 1 — Contract Audit

Сравни для каждого сценария:
- YAML `id`
- YAML `shots[].slug`
- demo spec `demo.shot(...)`
- `doc/screenshots/<RUN>/<scenario_id>/meta.json`
- PNG names in screenshot dir

Составь внутреннюю таблицу:

```text
scenario_id | yaml_shots | demo_shots | meta_shots | png_files | status
```

Не переходи к правкам, пока не понял все расхождения.

## Step 2 — Update YAML

Актуализируй YAML только если нужно:
- slug-и должны быть стабильными и начинаться с `NN_`;
- `caption` должен описывать видимый кадр;
- `narration` должен звучать как короткая озвучка;
- `why`, `wow_moment`, `takeaway` должны быть демо-пригодными;
- `requires.openai_api_key`, `requires.offline_friendly`, `requires.e2e_env` должны быть честными.

Особые правила:
- `scenario_01`: если часть ответа live-зависимая, offline demo должен снимать placeholder или безопасный кадр.
- `scenario_02`: полностью offline.
- `scenario_05`: использовать `HOME_RAG_E2E_OFFLINE=1`; не закреплять `e2e_fc_section=create` на весь flow.
- `scenario_06/07/08/09`: фиксить offline-флэки точечно, без ослабления gate-проверок.
- `scenario_10/11/12/13/14`: те же правила что для `scenario_06..09`; все `offline_friendly: true` — не требовать live LLM; фиксить флэки точечно.

После правок снова проверь YAML parse.
Затем запусти быстрый контрактный gate:

```powershell
npm run demo:validate
```

## Step 3 — Update Demo Specs

Приведи demo specs к YAML:
- использовать `createDemoRecorder(page, 'scenario_XX')` с корнем вывода `doc/screenshots/<RUN>/` (тот же, что в Step 4 — `$SHOTS`), чтобы новый прогон не затирал соседние папки прогонов;
- каждый YAML shot снимается через `demo.shot(slug, { caption, narration })`;
- slug-и не придумывать заново;
- финализация через `demo.finalize('passed'|'failed')`;
- live-зависимые части не должны ломать offline прогон;
- `@demo` не должен влиять на smoke/nightly.

Для flashcards:
- не выбирай первый `input[type=file]` на странице;
- используй правильный uploader/dropzone для учебного файла;
- не держи `e2e_fc_section=create` после перехода к сохранению колоды.

## Step 4 — Build Screenshots and Quickstart

Каталог **конкретного** прогона (новая папка по дате `YYYY-MM-DD`; старые прогоны не удаляем):

```powershell
$RUN = Get-Date -Format 'yyyy-MM-dd'
$SHOTS = "doc/screenshots/$RUN"
$env:DEMO_SHOT_RUN = $RUN   # до `npm run test:e2e:demo`, если нужен тот же RUN, что у Python-шагов
```

- Harness demo-тестов (`createDemoRecorder` / корень вывода) пишет кадры в **новый** `$SHOTS/<scenario_id>/` (см. неизменяемый `<RUN>` выше). Не задавай `DEMO_SHOT_RUN` на существующий архивный каталог, если нужно сохранить его как есть.
- **`npm run demo:clean`**: удаляет только `doc/screenshots/final/`, `doc/quickstart_demo.md` и `dist` — **не** трогает `doc/screenshots/<RUN>/` с архивом прогонов.

Контракт, затем съём, затем сборка документа **с тем же** `--screenshots-dir`:

```powershell
npm run demo:validate
npm run test:e2e:demo
# если `npm run demo:build` ещё смотрит на плоский `doc/screenshots`, дублируй цепочку вручную с $SHOTS:
.\.venv\Scripts\python.exe scripts\make_demo_gifs.py --screenshots-dir $SHOTS
# Preview (не трогает doc\screenshots\final\ и doc\quickstart_demo.md):
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS --output doc\quickstart_demo.preview.md --no-final-sync
.\.venv\Scripts\python.exe scripts\validate_demo_contract.py --screenshots-dir $SHOTS --require-screenshots --strict-captures --require-unique-shots
# Публикация в репозиторий — пересборка doc\screenshots\final\ и запись doc\quickstart_demo.md (default output):
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS
```

Локальная отладка без копирования в `final/`: `python scripts/generate_demo_doc.py --no-final-sync` (с нужным `--screenshots-dir`).

> **Важно:** `npm run demo:build` **не** пробрасывает `--screenshots-dir` в Python-скрипты. Без явно установленного `$env:DEMO_SHOT_RUN` скрипты используют дефолтный `doc/screenshots/`, а не датированный `<RUN>/`. Для надёжной работы всегда используй явную цепочку с `$SHOTS`, как показано выше.

Если Python-шаги нужны по отдельности:

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS --output doc\quickstart_demo.preview.md --no-final-sync
```

Если команда падает из-за sandbox/network/браузерной инфраструктуры, зафиксируй точную ошибку и не маскируй ее ручным редактированием screenshots.

## Step 5 — Validate Artifacts

Проверь (подставь `$RUN` / `$SHOTS` того прогона, который только что снимал):

- `doc/screenshots/<RUN>/scenario_*/meta.json` (все 14 сценариев)
- PNG names match YAML slugs.
- `meta.json.status` не `failed`.
- **Все PNG внутри одного сценария байт-уникальны.** Дубликаты = между кадрами не было изменения UI. Обязательная проверка: `--require-unique-shots` у `validate_demo_contract.py`. Ручная диагностика в PowerShell (пример для одного сценария): `Get-ChildItem doc\screenshots\final\scenario_01\*.png | Get-FileHash | Group-Object Hash | Where-Object { $_.Count -gt 1 }` — не должно находить групп.
- `doc/quickstart_demo.md` и `doc/screenshots/final/` актуальны только после шага **публикации** (`generate_demo_doc.py --screenshots-dir $SHOTS` без `--no-final-sync`); сравнивай с YAML и `$SHOTS`, без устаревших «ещё не снят» для готовых кадров.

Полезная проверка:

```powershell
$RUN = Get-Date -Format 'yyyy-MM-dd'   # или точное имя папки прогона из `doc/screenshots`
$env:DEMO_SHOT_RUN = $RUN
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -c "import json, pathlib, yaml, os; run=os.environ['DEMO_SHOT_RUN']; root=pathlib.Path('doc/screenshots')/run; ok=True
for y in pathlib.Path('doc/scenarios').glob('scenario_*.yaml'):
    d=yaml.safe_load(y.read_text(encoding='utf-8'))
    sid=d['id']
    expected=[s['slug'] for s in d.get('shots', [])]
    meta_path=root/sid/'meta.json'
    if not meta_path.exists():
        print('MISSING META', sid, meta_path); ok=False; continue
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    actual=[s.get('slug') for s in meta.get('shots', [])]
    if expected != actual:
        print('SHOT MISMATCH', sid, expected, actual); ok=False
    if meta.get('status') == 'failed':
        print('FAILED META', sid); ok=False
print('DEMO ARTIFACTS OK' if ok else 'DEMO ARTIFACTS NEED FIX')
raise SystemExit(0 if ok else 1)"
```

Проще: `validate_demo_contract.py --screenshots-dir $SHOTS` (см. Step 4), где `$SHOTS = "doc/screenshots/$RUN"`.

## Step 6 — Final Review

Перед финальным ответом проверь diff:

```powershell
git diff -- doc/scenarios tests/e2e/demos doc/screenshots doc/quickstart_demo.md
```

Финальный ответ:
- перечисли измененные файлы;
- укажи, какие команды запускались и их статус;
- укажи число кадров по каждому scenario;
- отдельно отметь live/placeholder кадры;
- если что-то не удалось прогнать, назови конкретную причину.
````

---

## Prompt 1 — Demo Contract Audit

````markdown
# PROMPT 1 — Demo Contract Audit

Ты работаешь из корня репозитория.

Задача: провести аудит demo-контура и найти рассинхрон между:
- `doc/scenarios/scenario_*.yaml`
- `tests/e2e/demos/scenario_*.spec.ts`
- `doc/screenshots/<RUN>/<scenario_id>/meta.json`
- `doc/quickstart_demo.md`

Read-set:
- `tests/e2e/README.md`
- `doc/scenarios/README.md`
- `doc/screenshots/README.md`
- только нужные YAML/spec/meta по `scenario_01..scenario_14` (без лишних файлов)

Правила:
- YAML — source of truth.
- Не читать крупные файлы целиком.
- Не менять код на этом шаге.
- Проверить, что каждый YAML shot имеет соответствующий `demo.shot(...)`.
- Проверить, что slug-и совпадают 1:1.
- Проверить `requires.openai_api_key`, `offline_friendly`, `HOME_RAG_E2E_OFFLINE`.
- Проверить, нет ли устаревших screenshot-файлов, которых уже нет в YAML.
- Проверить, что сценарии demo остаются offline-safe, кроме явно условных live-кадров.

Результат:
1. Таблица `scenario -> YAML shots -> demo shots -> screenshots/meta`.
2. Список точечных правок.
3. Write-set для следующего агента.
4. Команды проверки.
````

---

## Prompt 2 — Актуализация YAML-сценариев

````markdown
# PROMPT 2 — Актуализация YAML-сценариев

Ты работаешь из корня репозитория.

Задача: актуализировать YAML-манифесты demo-сценариев:
- `doc/scenarios/scenario_*.yaml` (все 14 demo-сценариев)

Цель: сделать сценарии пригодными для свежего demo-прогона и документации.

Контракт:
- YAML — единственный источник правды.
- Каждый `shots[].slug` начинается с `NN_`.
- `caption` описывает видимый кадр.
- `narration` звучит как короткая озвучка для демо.
- `wow_moment` должен указывать на главный продающий кадр.
- `takeaway` должен отвечать: “что зритель запомнит”.
- `requires` должен честно отражать offline/live режим.
- Не добавлять сценарий в demo, если его нельзя воспроизвести текущим harness.

Особое внимание:
- `scenario_01`: первый ответ может иметь live/placeholder часть; не ломать offline-прогон.
- `scenario_02`: навигация должна быть полностью offline.
- `scenario_05`: использовать `HOME_RAG_E2E_OFFLINE=1`, карточки детерминированные.
- `scenario_06/07/08/09`: при флейках — только минимальные точечные фиксы, без ослабления gates.
- `scenario_10/11/12/13/14`: все `offline_friendly: true`; те же правила что для `scenario_06..09`.

После правок:
- Проверить YAML парсинг.
- Сформировать список ожидаемых screenshot-файлов.
- Не запускать полный test suite.
````

---

## Prompt 3 — Актуализация Demo E2E Tests

````markdown
# PROMPT 3 — Актуализация Demo E2E Tests

Ты работаешь из корня репозитория.

Задача: привести demo-тесты в соответствие с YAML-манифестами.

Write-set:
- `tests/e2e/demos/scenario_*.spec.ts` (все 14 demo-specs)
- при необходимости только локальные e2e helper-файлы, если без этого нельзя

Правила:
- Использовать `createDemoRecorder(page, 'scenario_XX')` с корнем `doc/screenshots/<RUN>/` (`RUN` только дата `YYYY-MM-DD`), чтобы кадры не затирали соседние прогоны.
- Каждый shot из YAML должен иметь ровно один `demo.shot(slug, { caption, narration })`.
- Slug/caption/narration брать из YAML, не дублировать смысл по памяти.
- В конце обязательно `demo.finalize('passed'|'failed')` в безопасном try/catch.
- Если live LLM недоступен, demo не должен падать: нужен placeholder/условный кадр.
- `@demo` не должен влиять на smoke/nightly.
- Не закреплять `e2e_fc_section=create` на весь flashcards-flow.
- Для flashcards upload выбирать правильный uploader, не первый `input[type=file]`.

Проверки:
- `npm run test:e2e:demo`
- если менялся doc build: `npm run demo:build`

Результат:
- Перечислить измененные файлы.
- Для каждого сценария указать: YAML shots совпадают с demo shots или нет.
````

---

## Prompt 4 — Пересборка Screenshots и Quickstart Demo

````markdown
# PROMPT 4 — Пересборка Screenshots и Quickstart Demo

Ты работаешь из корня репозитория.

Задача: пересобрать demo screenshots и `doc/quickstart_demo.md`.

Перед запуском:
- Убедиться, что YAML и demo specs синхронизированы.
- Проверить, что demo-сценарии offline-friendly там, где заявлено.
- Не запускать весь pytest suite.

Перед съёмкой задай дату прогона и путь (новая подпапка; старые кадры не удалять):

```powershell
$RUN = Get-Date -Format 'yyyy-MM-dd'
$SHOTS = "doc/screenshots/$RUN"
```

Команды:

```powershell
$env:DEMO_SHOT_RUN = $RUN   # согласовать с npm/Python до прогона
npm run demo:validate
# demo:clean не сносит doc/screenshots/<RUN>/ — только final + quickstart + dist
npm run test:e2e:demo
.\.venv\Scripts\python.exe scripts\make_demo_gifs.py --screenshots-dir $SHOTS
.\.venv\Scripts\python.exe scripts\validate_demo_contract.py --screenshots-dir $SHOTS --require-screenshots --strict-captures --require-unique-shots
# Preview (опционально):
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS --output doc\quickstart_demo.preview.md --no-final-sync
# Публикация — final/ + doc/quickstart_demo.md:
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS
```

> **Важно:** `npm run demo:build` **не** пробрасывает `--screenshots-dir`. Для датированного прогона задавай `$env:DEMO_SHOT_RUN` или всегда используй явную цепочку с `$SHOTS`. Проверки `doc/screenshots/final/` и `doc/quickstart_demo.md` относятся к шагу **публикации** (последняя команда выше), не к preview.

Если Python нужен только для preview:

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS --output doc\quickstart_demo.preview.md --no-final-sync
```

Проверить:
- `doc/screenshots/<RUN>/scenario_*/meta.json` (все 14 сценариев)
- PNG-файлы соответствуют slug-ам из YAML.
- `meta.json.status` не `failed`.
- После публикации: `doc/screenshots/final/scenario_*/` заполнен, `doc/quickstart_demo.md` ссылается на `screenshots/final/...`, нет “ещё не снят” для готовых кадров.

Результат:
1. Какие сценарии пересобраны.
2. Сколько кадров снято по каждому.
3. Какие кадры placeholder/live-dependent.
4. Команды и итоговый статус.
````

---

## Prompt 5 — Финальный Reviewer Gate

````markdown
# PROMPT 5 — Финальный Reviewer Gate

Ты работаешь из корня репозитория.

Задача: code-review актуализации demo-контура.

Проверить только:
- `doc/scenarios/*.yaml`
- `tests/e2e/demos/*.spec.ts`
- `doc/screenshots/**/meta.json`
- `doc/quickstart_demo.md`
- связанные README, если их меняли

Критерии блокера:
- YAML shot отсутствует в demo spec.
- Demo spec снимает shot, которого нет в YAML.
- `offline_friendly: true`, но тест требует live LLM.
- `OPENAI_API_KEY` нужен, но не отражен в `requires`.
- screenshot/meta не соответствует YAML.
- **Два PNG одного сценария байт-идентичны** (одинаковый хеш файла). Это прямой признак, что между `demo.shot(...)` не произошло никакого DOM-изменения — «анимированный разбор» фейковый. Проверяется `--require-unique-shots`.
- `demo:build` не проходит.
- Скриншоты устарели относительно текущего UI.
- Были изменены файлы вне заявленного write-set без причины.

Команды (согласуй `$RUN` / `$SHOTS` с веткой прогона, см. Master Prompt — Step 4; новый съём — **новый** `<RUN>`, не перезапись архива):

```powershell
$RUN = Get-Date -Format 'yyyy-MM-dd'
$SHOTS = "doc/screenshots/$RUN"
$env:DEMO_SHOT_RUN = $RUN
npm run demo:validate
npm run test:e2e:demo
# при необходимости: demo:build (с тем же DEMO_SHOT_RUN) или явная цепочка:
.\.venv\Scripts\python.exe scripts\make_demo_gifs.py --screenshots-dir $SHOTS
.\.venv\Scripts\python.exe scripts\generate_demo_doc.py --screenshots-dir $SHOTS
.\.venv\Scripts\python.exe scripts\validate_demo_contract.py --screenshots-dir $SHOTS --require-screenshots --strict-captures --require-unique-shots
```

Формат ответа:
- Findings first, по severity.
- Потом residual risks.
- Потом короткий итог: готово / не готово к merge.
````

---

## Fast Path

Если нужно просто запустить весь bundle одним агентом, используй **Master Prompt**.

Если нужно разделить работу между агентами:

1. `Prompt 1` — audit без правок.
2. `Prompt 2` — YAML.
3. `Prompt 3` — demo specs.
4. `Prompt 4` — screenshots + quickstart.
5. `Prompt 5` — review gate.

Рекомендуемая модель выполнения: сначала audit, потом YAML/spec sync, затем только пересборка артефактов. Каталоги `doc/screenshots/<RUN>/` остаются историей прогонов; актуальная ветка — имя папки прогона + согласованный `--screenshots-dir` в validate/build.
