# Workflow Для Агентов

Актуализировано по коду и процессу на 2026-05-01.

Этот документ описывает, как использовать coding agents в `home-rag_v2` так, чтобы они помогали быстрее, а не создавали конфликты и скрытые регрессии.

## Короткая Версия

Рабочий цикл для агента:

1. Сначала изучить код и актуальный беклог в `doc/backlog_registry.yaml` (при необходимости — производный `doc/tasklist.md` после sync).
2. Потом зафиксировать цель, scope и критерий готовности.
3. Делать только свой write-set.
4. Проверять результат целевыми тестами.
5. Синхронизировать документацию, если изменился контракт, UI или roadmap-статус.

Если агент начинает трогать лишние файлы или уходит в сторону, лучше перезапустить поток с более узкой постановкой, чем лечить длинный диалог.

## Источники Истины

- Текущее состояние backlog и owner-зон: `doc/backlog_registry.yaml` (SSoT); `doc/tasklist.md` — производный weekly view после `scripts/backlog_registry_lint.py --sync-from-index --write-sync`
- Текущее состояние кода: `app/*`, `tests/*`, `scripts/*` (это source map, не read-set; не читать папки целиком)
- История уже закрытых slices: `doc/closed_iterations.md`
- Актуальные инженерные соглашения: `doc/conventions.md`

Если документация конфликтует с кодом и реестром, сначала верить коду и `doc/backlog_registry.yaml`, затем синхронизировать производные (`tasklist.md` и проч.).

---

## Навигация (split-map)

Этот файл — slim index. Подробности — в topic-файлах:

| Когда читать | Файл | Содержимое |
|---|---|---|
| Перед каждым LLM-вызовом | [`agent_workflow_rules.md`](agent_workflow_rules.md) | Token Budget & Retry Safety v1 (7 правил) |
| Веду пакет (как работать) | [`agent_workflow_cycle.md`](agent_workflow_cycle.md) | Scan→Plan→Edit→Verify→Sync; параллелизм; A/B/C split |
| Составляю prompt для пакета | [`agent_workflow_templates.md`](agent_workflow_templates.md) | Planning / Verify / Contract / Task Assignment templates |
| Периодический arch review (раз в квартал) | [`agent_workflow_arch_review.md`](agent_workflow_arch_review.md) | 5 фаз arch audit + output format |
| Выбираю тесты / low-budget fallback | [`agent_workflow_test_bundles.md`](agent_workflow_test_bundles.md) | Стандартные test bundles + Micro-Plan/Execute/Verify |
| Проверяю бюджет Kilo / предотвращаю overflow | [`kilo_budget_system.md`](kilo_budget_system.md) | Gate + Simulator + Calibrator — predict-and-prevent |
| Выполняю remediation по бюджету Kilo | [`kilo_budget_remediation_plan.md`](archive/kilo_budget_remediation_plan.md) | Wave 4 execution checklist (P0-P3) |
| Ежедневная команда + интерпретация | [`team_workflow/budget_health_prompt.md`](team_workflow/budget_health_prompt.md) | Команды, margins, диагностика, override |
| Командный пайплайн (роли, STEP 1–8), HANDOFF_SIGNAL | [`team_workflow/process.md`](team_workflow/process.md) + [`prompts_usage_guide.md`](prompts_usage_guide.md) | Таблица этапов, дерево решений, проверка артефактов `scripts/validate_team_artifact.py` |
| Следующий шаг без матрицы состояний | [`team_workflow/workflow_router.md`](team_workflow/workflow_router.md) + `scripts/workflow.py` | Кондуктор `--loop`, якоря в документе; тексты промпта агента — [`scripts/workflow_strings.py`](../scripts/workflow_strings.py) |

Split произведён 2026-04-20 (см. `doc/tasklist.md § epoch-agent-workflow-split Contract`).
До этой даты — единый монолит (historical). Inbound-ссылки на
`doc/agent_workflow.md` без анкера резолвятся на этот slim index.

---

## Чек Перед Merge

- изменены только owner-файлы;
- нет случайных побочных правок;
- целевые тесты запущены или явно объяснено, почему не запускались;
- docs синхронизированы, если контракт изменился;
- итог можно коротко описать в 3-5 предложениях;
- при срыве outcome или FAIL верификации в отчёте есть **`HANDOFF_SIGNAL: …`** (см. [`team_workflow/developer.md`](team_workflow/developer.md) / [`team_workflow/tester.md`](team_workflow/tester.md)); для артефактов оркестратора при необходимости прогоните [`scripts/validate_team_artifact.py`](../scripts/validate_team_artifact.py) или `npm run validate:team-artifacts -- --artifacts-dir archive/team_artifacts/<PACKAGE_ID>`.

## Практическое Правило Для Этого Репозитория

Для `home-rag_v2` безопасный дефолт такой:

- любая задача больше чем на один файл начинается с `scan -> plan -> owner split`;
- любые изменения в tutor-контуре заканчиваются целевыми тестами;
- `doc/backlog_registry.yaml` — главный truth source по пакетам; `doc/tasklist.md` — краткий производный обзор;
- параллелим только независимые write-set'ы;
- если агент ушёл в сторону, запускаем новый поток с более узкой постановкой.

## Verification-Only Маркеры (минимум)

- `allow_verification_only` — marker в контракте пакета, который разрешает intentional verification-only closure.
- `evidence_inconclusive_allowed` — marker в `execution_contract.md` только для случая, когда git change-proof inconclusive (нет явного подтверждения по `diff-tree`).
- Базовое требование неизменно: в `Pre-existing delivery evidence` нужны commit SHA и concrete file paths.
