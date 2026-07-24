# Evolutionary Wave Continuation Prompt Template

**Назначение:** reusable-шаблон для продолжения реализации по эволюционным
разборам, когда нужно работать одновременно с runtime-репозиторием `hometutor`
и planning/workflow-репозиторием `hometutor-studio`.

**Когда использовать:** перед стартом новой волны реализации после аудита
`doc/presentations/evolutionary_analyses/README.md`.

**Как использовать:** замени все `{{PLACEHOLDER}}`, затем передай агенту как
стартовый execution prompt. Не удаляй ограничения и финальный doc-sync.

---

```text
Работаем по runtime-репозиторию {{RUNTIME_REPO}} и studio-репозиторию {{STUDIO_REPO}}.

Срез статуса: {{SNAPSHOT_DATE}}.
Текущая волна: {{WAVE_ID}} — {{WAVE_NAME}}.

Сначала прочитай строго в этом порядке:
1. {{STUDIO_README_PATH}}
   — особенно разделы: {{STUDIO_README_SECTIONS}}.
2. {{PRIMARY_PLAN_PATH}}
   — актуальная версия плана {{PLAN_VERSION}} или новее, если появилась.
   Выдели: {{PLAN_P0_ITEMS}}, контракты, policy, ledger, locks, smoke/DoD и запреты.
3. {{RUNTIME_REPORT_PATH}}
4. {{RUNTIME_USER_GUIDE_PATH}}
   — секция {{RUNTIME_USER_GUIDE_SECTION}}.

Текущий подтверждённый статус, не переписывать, только опираться:
- {{CONFIRMED_STATUS_1}}
- {{CONFIRMED_STATUS_2}}
- {{CONFIRMED_STATUS_3}}
- {{CONFIRMED_STATUS_4}}

Границы работы:
- Runtime repo: {{RUNTIME_ALLOWED_SCOPE}}.
- Studio repo: {{STUDIO_ALLOWED_SCOPE}}.
- Не трогать: {{DO_NOT_TOUCH_SCOPE}}.
- Workflow/agent tooling живёт в: {{WORKFLOW_TOOLING_REPO}}.
- Источник истины для текущей волны: {{SOURCE_OF_TRUTH_PLAN}}.

Цель ближайшей волны, строго последовательно:
1. Реализовать {{P0_1_ID}} {{P0_1_NAME}}:
   - {{P0_1_TASK_1}}
   - {{P0_1_TASK_2}}
   - {{P0_1_TASK_3}}

2. Затем реализовать {{P0_2_ID}} {{P0_2_NAME}}:
   - {{P0_2_TASK_1}}
   - {{P0_2_TASK_2}}
   - {{P0_2_TASK_3}}

3. Затем реализовать {{P0_3_ID}} {{P0_3_NAME}}:
   - {{P0_3_TASK_1}}
   - {{P0_3_TASK_2}}
   - {{P0_3_TASK_3}}

Жёсткие ограничения:
- Не заявлять {{WAVE_ID}} shipped без реальных файлов реализации, тестов и успешного smoke.
- Не включать в метрику {{METRIC_NAME}}: {{EXCLUDED_PATHS_OR_SIGNALS}}.
- Не добавлять {{FORBIDDEN_APPROACHES}} без отдельного явного решения владельца.
- Перед любыми правками проверить dirty worktree и не трогать чужие изменения.
- Не изобретать новые контракты вне {{PLAN_VERSION}}. Если план требует уточнения — остановиться и зафиксировать вопрос.
- Не смешивать текущую волну с: {{UNRELATED_WAVES_OR_TASKS}}.
- Optional polish выполнять только после полного закрытия P0 и только если остаётся время.

Минимальная проверка качества перед claim «готово»:
- Unit/integration tests:
  - {{TEST_COMMAND_1}}
  - {{TEST_COMMAND_2}}
- Smoke:
  - {{SMOKE_CASE_1}}
  - {{SMOKE_CASE_2}}
- Метрики в отчёте:
  - {{METRIC_1}}
  - {{METRIC_2}}
  - {{METRIC_3}}

Финальный doc-sync только после зелёных тестов и smoke:
- Обновить оба README:
  - {{RUNTIME_REPO}}\README.md
  - {{STUDIO_REPO}}\doc\presentations\evolutionary_analyses\README.md
- В обоих README отметить:
  - фактически закрытые пункты {{P0_ITEMS}};
  - новый live/outcome статус;
  - новый baseline метрик, если знаменатель > 0;
  - оставшиеся хвосты по важности;
  - следующий рекомендуемый шаг;
  - не придумывать новые разборы.

Порядок работы внутри сессии:
1. Прочитай указанные файлы.
2. Явно подтверди понимание текущего статуса и границ.
3. Составь короткий executable checklist по {{P0_SEQUENCE}} с файлами, которые будут созданы/изменены.
4. Реализуй строго по checklist.
5. Запускай тесты на каждом значимом шаге.
6. Прогони минимальную проверку.
7. Только после зелёных тестов и smoke выполни doc-sync.
8. В конце выдай короткий отчёт:
   - что сделано;
   - что осталось;
   - какие файлы появились/изменены;
   - результаты тестов;
   - результаты smoke;
   - следующий шаг.

Начинай с чтения файлов. Не пиши код, пока не подтвердишь статус и границы.
```
