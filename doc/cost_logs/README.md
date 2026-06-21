# Cost Logs

This directory documents the LLM cost-log format and may contain historical
baseline artifacts from the early token-budget work.

Runtime cost logs are written to `logs/cost_logs/`, not to `doc/cost_logs/`.
The `logs/` tree is ignored by Git and is the project-standard location for
mutable runtime logs.

## Why Not `doc/`

`doc/` is for durable project documentation and curated reports. Daily JSONL
cost logs are runtime artifacts: they change during normal app, CLI, and agent
workflow execution. Keeping them under `doc/` causes unrelated Git churn and
conflicts with the storage convention in `doc/architecture.md`, where `logs/`
is the home for log files and metrics stores.

## Runtime Location

Default path:

```bash
logs/cost_logs/cost_logs_YYYY-MM-DD.jsonl
```

The application path is configured by `Settings.llm_cost_log_dir` in
`app/config.py` and must be accessed through `get_settings()`.

## Format

Each daily file is JSON Lines, one record per LLM call:

```json
{
  "timestamp": "2026-04-20T10:15:33.123456Z",
  "model": "grok-4.1-fast-thinking",
  "input_tokens": 10500,
  "output_tokens": 850,
  "cost_rub": 0.89,
  "package_id": "E14-B",
  "prompt_type": "planning",
  "status": "OK",
  "guards_applied": ["model_check", "hard_limit_check"]
}
```

## Fields

| Field | Description |
|---|---|
| `timestamp` | ISO 8601 UTC time |
| `model` | Model name |
| `input_tokens` | Input-token estimate |
| `output_tokens` | Output-token estimate |
| `cost_rub` | Estimated cost in RUB |
| `package_id` | Work package ID, when available |
| `prompt_type` | Prompt category, for example `planning`, `execution`, `verify` |
| `status` | `OK`, `CACHE_HIT`, `BLOCKED`, or `ERR` |
| `guards_applied` | Local guards that ran before or around the provider call |

`ERR` and `BLOCKED` records may also include `error_type`, `error_message`,
`prompt_stats`, and `provider_error`.

## Monitoring

Watch today's logs:

```bash
tail -f logs/cost_logs/cost_logs_$(date +%Y-%m-%d).jsonl | jq .
```

Find expensive calls:

```bash
cat logs/cost_logs/cost_logs_*.jsonl | jq 'select(.cost_rub > 5)'
```

Find blocked calls:

```bash
cat logs/cost_logs/cost_logs_*.jsonl | jq 'select(.status == "BLOCKED")'
```

## Reports

Weekly or curated reports belong in `doc/`, for example
`doc/cost_tracking.md`.

Ad hoc cost-log summaries are generated from `logs/cost_logs/cost_logs_*.jsonl`:

```bash
python scripts/summarize_cost_logs.py --limit-files 3 --top 5
```

The context-length gate uses the same runtime cost-log directory:

```bash
python scripts/check_llm_context_gate.py
```

Pipeline bottleneck reports are not cost-log summaries. They are generated
from `archive/team_artifacts/_timing/` by `scripts/analyze_bottlenecks.py` and
belong in `logs/bottlenecks/`:

```bash
python scripts/analyze_bottlenecks.py
```
