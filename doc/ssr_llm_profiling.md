# SSR LLM: профили и сравнение с основным чатом

Карточка **«Умный следующий шаг»** при включённом профилировании пишет одну
JSONL-строку на попытку персонализации текста «Почему сейчас». LLM здесь
меняет только объяснение; routing decision (`hint_kind`, `primary_nav`) уже
принят детерминированным SSR.

## Где лежат файлы

| Данные | Путь |
|---|---|
| SSR-профили | `logs/ssr_llm_profiles/ssr_llm_profile_YYYY-MM-DD.jsonl` |
| Учёт вызовов основного LLM | `logs/cost_logs/cost_logs_YYYY-MM-DD.jsonl` |

Переменные окружения: `SSR_LLM_PROFILE_LOG_DIR`,
`ENABLE_SSR_LLM_PROFILING`, модели/базы `SSR_LLM_*` и `LLM_MODEL`
(см. `.env.example`). Конфиг читать только через `app.config.get_settings()`.

## JSONL schema

Sample row:

```json
{
  "kind": "ssr_llm_explanation",
  "event_id": "5e2d9bb5-9f4a-4b33-a9e5-9a6b8f6c6d7f",
  "timestamp": "2026-05-11T08:30:12.120Z",
  "prompt_version": "1.2",
  "outcome": "llm_success",
  "latency_ms": 238.41,
  "main_llm_model": "gpt-4.1-mini",
  "configured_ssr_model": "local-qwen",
  "effective_model": "local-qwen",
  "ssr_api_base": "http://127.0.0.1:8787/v1",
  "used_main_chat_client": false,
  "total_tokens": 214,
  "token_hard_cap_hit": false,
  "error_type": null,
  "hint_kind": "cards_due",
  "primary_nav": "flashcards_review"
}
```

| Field | Type | Required | Notes |
|---|---:|---:|---|
| `kind` | string | yes | Always `ssr_llm_explanation`. |
| `event_id` | UUID string | yes | Per-row id; see correlation caveat below. |
| `timestamp` | ISO-8601 UTC | yes | Used for time-window joins with cost logs. |
| `prompt_version` | string | yes | From `SSR_LLM_EXPLANATION_PROMPT_VERSION`. |
| `outcome` | enum | yes | See enum below. |
| `latency_ms` | number/null | yes | Rounded milliseconds; cache hit is `0.0`. |
| `main_llm_model` | string | yes | Current main chat model. |
| `configured_ssr_model` | string/null | yes | Explicit SSR model override, if any. |
| `effective_model` | string/null | yes | Actual model used by the client. |
| `ssr_api_base` | string/null | yes | Normalized OpenAI-compatible base. |
| `used_main_chat_client` | boolean | yes | True when SSR fell back to main chat client. |
| `total_tokens` | integer/null | yes | Provider usage if available. |
| `token_hard_cap_hit` | boolean | yes | True when prompt budget forced fallback. |
| `error_type` | string/null | yes | Exception class/category for `outcome=error`. |
| `hint_kind` | string/null | yes | SSR source signal. |
| `primary_nav` | string/null | yes | Final CTA target. |
| `extra` | object | no | Optional diagnostics; must be PII-scrubbed. |

`outcome` enum:

- `cache_hit`
- `llm_success`
- `template_fallback_timeout`
- `template_fallback_empty`
- `template_fallback_token_budget`
- `error`

## Retention and privacy

Profiles are local diagnostic logs. They must not include raw user prompts,
document excerpts, learner names, API keys, or model output text. Keep only
routing metadata, model ids, latency, token counts, and bounded error labels.

Recommended retention: keep daily files for 30 days in development and 7 days
for shared demo environments. Rotation is not yet automated; add cleanup to the
same maintenance path that owns local logs before enabling this in long-running
installations.

## Сводка из консоли

PowerShell:

```bash
.\.venv\Scripts\python.exe scripts/summarize_ssr_llm_profiles.py
.\.venv\Scripts\python.exe scripts/summarize_ssr_llm_profiles.py --last-files 7 --json
```

POSIX:

```bash
python scripts/summarize_ssr_llm_profiles.py
python scripts/summarize_ssr_llm_profiles.py --last-files 7 --json
```

## OpenTelemetry

При `ENABLE_OTEL_TRACING=true` и непустом `OTEL_EXPORTER_OTLP_ENDPOINT`
создаётся span `ssr_llm_explanation`. При выключенном OTEL tracing path —
no-op; profiling JSONL продолжает работать независимо.

Expected attributes:

- `ssr.event_id`
- `ssr.outcome`
- `ssr.effective_model`
- `ssr.used_main_chat_client`
- `ssr.latency_ms`
- `ssr.total_tokens`
- `ssr.hint_kind`
- `ssr.primary_nav`

`OTEL_SERVICE_NAME` задаёт service resource, default `home-rag`. Sampling
defaults to SDK exporter defaults; если нужен sampling ниже 100%, задавать его
в OTEL Collector/SDK конфиге, а не в SSR policy.

## Корреляция с cost logs

Прямой общий `event_id` между SSR profile и cost log сейчас не проставляется в
cost log. Безопасный временный join: `timestamp ± 5s` + `effective_model/model`
+ `prompt_type`/stage when available. Caveat: параллельные вызовы могут дать
ложные совпадения. Рекомендуемый fix для следующего пакета — ввести `audit_id`
и прокинуть его в SSR JSONL, cost log и OTEL span (`ssr.audit_id`).

## Сравнение с основным LLM

SSR:

- агрегировать `outcome`, `effective_model`, процент `used_main_chat_client`;
- считать p50/p95 `latency_ms` для `outcome=llm_success`;
- отдельно смотреть `template_fallback_*` и `error`.

Основной чат:

- те же сутки в `cost_logs_*.jsonl`;
- поля `model`, `input_tokens`, `output_tokens`, при необходимости `prompt_type`.

Operational targets для SSR explanation:

| Metric | Target |
|---|---:|
| p95 latency for `llm_success` | ≤ 1500 ms |
| fallback rate excluding `cache_hit` | < 5% |
| `used_main_chat_client` rate | < 10% in local-model demos |
| `template_fallback_token_budget` | 0 in normal UI flows |
| `error` rate | < 1% |
