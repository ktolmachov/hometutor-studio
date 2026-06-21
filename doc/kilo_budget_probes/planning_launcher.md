# Planning launcher path

Relay base URL for this run: `http://127.0.0.1:8791/v1`

[KILO-PROBE: PLANNING-LAUNCHER]

Проверка budget logic только для planning launcher.

Правила:
1. Это fresh Kilo session. Без reuse истории.
2. Выполни только команду:
   python scripts/generate_next_prompt.py --budget-profile strict
3. Если команда вернёт launcher, работай только по указанному prompt file.
4. Не открывай broad docs сверх launcher file.
5. Если relay предупреждает или блокирует - остановись и коротко зафиксируй blocker.
6. Цель: проверить, что planning path остаётся launcher-sized.
