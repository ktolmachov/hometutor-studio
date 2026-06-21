# Orchestration launcher path

Relay base URL for this run: `http://127.0.0.1:8791/v1`

[KILO-PROBE: ORCH-LAUNCHER]

Проверка логики лимитов и budget guard только для orchestration launcher.

Правила:
1. Это fresh Kilo session. Не используй историю прошлых задач.
2. Выполни только команду:
   python scripts/generate_orchestration_prompt.py --agent kilo --budget-profile strict
3. Дальше следуй только launcher-указанию из stdout.
4. Не открывай backlog/history docs, если launcher не требует ровно один файл.
5. Если read-set начинает расширяться или relay блокирует запрос, остановись.
6. Цель: проверить pointer-only handoff и guard behavior, а не выполнить весь pipeline.
