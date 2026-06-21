# Loop Metrics Gate Runbook (US-14.4)
1. Запусти `npm run test:loop-gate:ops` и зафиксируй текст ошибки/alert.
2. Открой свежий артефакт `logs/loop_metrics_gate_latest.json`.
3. Проверь историю: `npm run test:loop-gate:summary` (status_breakdown, recent_failures).
4. Если `pass_rate_below_threshold` или `fail_count_above_threshold` — это operational fail.
5. Если `no_gate_snapshots_in_window` — сначала создай снапшот: `npm run test:loop-gate:record`.
6. Прогони тест №1: `python -m pytest tests/test_e11_learning_loop.py -k "loop_runtime_metrics_gate_contract or record_loop_transition_emits_dead_end_safe_metric" -v`.
7. Прогони тест №2: `python -m pytest tests/test_e9_7_continuity_bridge.py -v`.
8. Если падает gate-контракт, проверь `app/ui/scoped_quiz.py` и `app/ui/quiz_panel.py` (route/dead-end/primary CTA).
9. Владелец фикса: **tutor_contour_owner** (package owner `epoch-5min-loop-polish`), при infra-сбое подключай `repo_ci_owner`.
10. После фикса: `npm run test:loop-gate:ops` должен быть PASS, затем обнови `logs/loop_metrics_gate_latest.json`.
