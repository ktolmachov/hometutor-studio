# Capturing a real Kilo injection fixture

Пошаговый процесс обновления `fixtures/kilo_injection_captured.json` из живой Kilo-сессии.

## Steps

1. Запусти relay:
   `.\.venv\Scripts\python.exe scripts/kilo_proxy_relay.py`  
   Эксплуатация (стриминг, env, логи Studio): [kilo_proxy_relay.md](kilo_proxy_relay.md).
2. Направь Kilo на relay endpoint.
3. Открой свежую Kilo-сессию (без истории).
4. Отправь probe marker, например: `orch_launcher_capture_probe_YYYYMMDD`.
5. Останови relay (`Ctrl+C`), проверь `logs/kilo_relay.jsonl`.
6. Сними fixture:
   `.\.venv\Scripts\python.exe scripts/kilo_budget_simulate.py capture --from-jsonl logs/kilo_relay.jsonl --probe orch_launcher_capture_probe_YYYYMMDD -o fixtures/kilo_injection_captured.json`
7. Проверь diff:
   `git diff fixtures/kilo_injection_captured.json`
8. Проверка gate:
   `.\.venv\Scripts\python.exe scripts/kilo_budget_gate.py --dry-run`
9. Закоммить обновление отдельным коммитом.

## How often

- После заметных изменений в `CLAUDE.md` или memory.
- После обновления Kilo.
- Периодически (например, раз в месяц) как sanity-check.
