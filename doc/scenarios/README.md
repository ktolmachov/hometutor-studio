# Манифесты сценариев

Каждый YAML-файл в этой папке — **source of truth** для одного сценария из [user_scenarios.md](../user_scenarios.md).

## Схема

```yaml
id: scenario_XX              # уникальный id (латиница, для путей)
title: "Читаемое название"
level: "🟢|🔵|🟣|⚡ Уровень"
persona: "Короткое описание героя"
duration_min: 5              # ожидаемое время сценария
why: |
  Зачем это показываем. В одну-две фразы, продающие.
requires:
  openai_api_key: false      # нужен ли live LLM
  offline_friendly: true     # можно ли снимать в offline
  e2e_env:                   # доп. env для Playwright стека
    HOME_RAG_E2E_OFFLINE: "1"
  notes: |                   # (опционально) комментарии по стенду
    ...
wow_moment: |
  Главный кадр-гвоздь. 1–2 фразы.
takeaway: |
  Что зритель должен запомнить.
scenario_link: "user_scenarios.md#..."   # якорь в каталоге сценариев

shots:
  - slug: "01_имя_кадра"     # префикс 01/02/... задаёт порядок
    caption: "Подпись кадра"
    narration: "Текст озвучки/нарратив для ролика"
    duration_sec: 3          # рекомендация для видео
```

## Правила

1. **Один сценарий = один YAML.** Имя файла: `scenario_<num>_<slug>.yaml`.
2. **Shots ориентированы на кадры видео.** `slug` начинается с двузначного номера для сортировки.
3. **YAML — единственный источник.** Demo-тест (`tests/e2e/demos/*.spec.ts`) читает YAML и по slug-ам снимает скриншоты; генератор документа (`scripts/generate_demo_doc.py`) тоже читает YAML. Если меняется сценарий — меняется только YAML, остальное — консистентно.
4. **offline_friendly: true** — сценарий доступен в smoke-прогоне без OPENAI_API_KEY.

## Как связаны артефакты

```
doc/scenarios/scenario_05_flashcards_create.yaml
             │
             ├─→ tests/e2e/demos/scenario_05_flashcards_create.spec.ts  (читает shots)
             │         │
             │         └─→ doc/screenshots/scenario_05/01_flashcards_section.png
             │             doc/screenshots/scenario_05/02_create_new_upload.png
             │             doc/screenshots/scenario_05/meta.json        (время, размер)
             │
             └─→ scripts/generate_demo_doc.py  (читает YAML + screenshots)
                         │
                         └─→ doc/quickstart_demo.md
```

## Добавление нового сценария

1. Каркас YAML + demo spec:
   ```powershell
   .\.venv\Scripts\python.exe scripts/scaffold_demo_scenario.py --slug my_feature --title "Название сценария" --update-order
   # или: npm run demo:scaffold -- --slug my_feature --title "Название сценария" --update-order
   ```
2. Допишите поля в YAML и реализуйте навигацию в `tests/e2e/demos/*.spec.ts`.
3. Добавьте раздел в `doc/user_scenarios.md`, если его ещё нет.
4. Полный цикл съёмки и публикации:
   ```powershell
   .\.venv\Scripts\python.exe scripts/demo_workflow.py full --scenario-id scenario_XX
   # или: npm run demo:refresh -- --scenario-id scenario_XX
   ```
5. Quality gate (strict):
   ```powershell
   npm run demo:validate -- --screenshots-dir doc/screenshots/final --require-screenshots --strict-captures --require-unique-shots
   ```

Подробнее: `scripts/demo_workflow.py` (list/preflight/capture/preview/publish/full), PowerShell-обёртки `scripts/run_demo_refresh.ps1` и `scripts/run_scaffold_demo.ps1`.

## Актуализация витрины после разбора №11

Для подготовки агент-сессии по обновлению сценариев используйте helper:

```powershell
python doc/scenarios/generate_scenario_refresh_prompt.py
```

Скрипт не вызывает LLM: он печатает prompt для проверки freshness gap, добавления
или ревизии YAML-манифестов слепых зон, синхронизации с
`doc/next/usage_scenarios_refresh_plan.md` и сверки с парным жанром
[`daily_use_stories`](../presentations/daily_use_stories/README.md).

Daily-use stories — не замена YAML/e2e-доказательствам. Helper включает их как
контекст ритуалов («Пять дней с hometutor»), но требует сохранять evidence-сноски:
витрина `quickstart_demo.md` доказывает момент через кадры, daily-use stories
объясняют ежедневную привычку через проверяемые сценарии и код.
