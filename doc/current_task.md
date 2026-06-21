# TASK: Post-Closure SSoT Audit for flashcard-handoff-fast-path-v1

Вы только что успешно закрыли пакет `flashcard-handoff-fast-path-v1`. Теперь необходимо верифицировать консистентность индексов (SSoT).

## Шаг 1: Генерация промпта аудита
Прочитайте файл `doc/team_workflow/generate_audit_closed_packages_prompt.md` и выполните его инструкции (Phase A1-A4).
Используйте следующие входные параметры:
- `TARGET_AGENT`: cursor_ai
- `PERIOD`: 2026-06-20..2026-06-20
- `PACKAGE`: flashcard-handoff-fast-path-v1
- `SCOPE`: closed
- `DEPTH`: index_only

## Шаг 2: Выполнение аудита
Прочитайте и выполните сгенерированный промпт (он будет сохранён в `doc/team_workflow/`).
Выполните шаги A, B, C, D. (Тесты перепроходить не нужно, так как `DEPTH=index_only`).
Сохраните итоговый отчёт (Шаг D).

## MANDATORY FINAL STEP
После того как отчёт сохранён и все индексы проверены, возобновите конвейер (переход к следующей задаче) с помощью команды:

```bash
.\.venv\Scripts\python.exe scripts/run_autonomous.py --agent cursor_ai --budget-profile strict --allow-empty-generator
```
