# Autonomous Kilo handoff path

Relay base URL for this run: `http://127.0.0.1:8791/v1`

[KILO-PROBE: AUTONOMOUS-HANDOFF]

Проверка Kilo handoff logic для run_autonomous.

Правила:
1. Это fresh Kilo session. Без истории прошлых workflow.
2. Выполни только команду:
   python scripts/run_autonomous.py --agent kilo --budget-profile strict
3. После этого прочитай только `doc/current_task.md`.
4. Выполни только первый указанный шаг handoff-а.
5. Если task требует новый этап, planning или execution в отдельной сессии - остановись, не продолжай здесь.
6. Не открывай backlog/history docs, если task явно не указывает ровно один файл.
7. Цель: проверить, что Kilo path теперь разделён на fresh-session phases.
