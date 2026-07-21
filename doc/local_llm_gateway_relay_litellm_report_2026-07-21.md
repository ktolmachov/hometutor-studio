# Локальная LLM-инфраструктура: Kilo Proxy Relay, LiteLLM и Open Notebook

**Дата:** 2026-07-21  
**Цель:** сравнить маршруты Kilo к локальной модели, найти причины token overhead и определить план доработок.

## Итоговое решение

```text
Kilo → kilo_proxy_relay:8787 → llama.cpp:8080
```

LiteLLM подключается опционально:

```text
Kilo → kilo_proxy_relay → LiteLLM:4000 → llama.cpp:8080
Open Notebook → http://litellm:4000/v1 → llama.cpp RAG runtime
```

### Роли

- `kilo_proxy_relay`: Kilo payload audit, compression, guard, MCP/skills/history attribution.
- `LiteLLM`: aliases, auth, retries, routing, callbacks и общий gateway.
- `llama.cpp`: inference, tokenizer, timings, KV cache, model identity.
- `HomeTutor`: authoritative RAG, citations, source-id integrity, refusal и gates.
- `Open Notebook`: workspace и exploratory research.

## P0 для kilo_proxy_relay

1. Явный upstream `http://127.0.0.1:8080` или fail-fast.
2. `KILO_RELAY_FULL_BODY=0` по умолчанию.
3. Режим `audit` без изменения payload.
4. Одновременный лог original и forwarded request.
5. Точный `/v1/chat/completions/input_tokens`.
6. Dynamic token guard по `meta.n_ctx`.
7. Профили `local_coder_64k` и `local_coder_128k`.

## P0 для LiteLLM/Open Notebook

1. Раздельные configs для RAG и coding.
2. `drop_params=false` для strict Kilo diagnostics.
3. Зафиксировать image digest вместо `main-latest`.
4. Open Notebook внутри Compose использует `http://litellm:4000/v1`.
5. Identity gate: LiteLLM alias + upstream llama.cpp alias/context.
6. Порты только на `127.0.0.1`, secrets из `.env`.

## A/B runs

| Run | Маршрут |
|---|---|
| A | Kilo → llama.cpp |
| B | Kilo → relay audit → llama.cpp |
| C | Kilo → relay compression → llama.cpp |
| D | Kilo → LiteLLM → llama.cpp |
| E | Kilo → relay → LiteLLM → llama.cpp |

Измерять original/forwarded tokens, system/tools/MCP/skills/history/tool-results overhead, TTFT, prompt/decode TPS, latency, model identity, JSON Schema и tool calling.

## Финальный статус

```text
LLAMA_CPP_RUNTIME=KEEP
KILO_PROXY_RELAY=HARDEN_AND_PROMOTE
LITELLM=OPTIONAL_SHARED_GATEWAY
OPEN_NOTEBOOK=WORKSPACE
HOMETUTOR=AUTHORITATIVE_RAG
NODE_DIAGNOSTIC_PROXY=MERGE_FEATURES_THEN_RETIRE
NEXT_STEP=P0_RELAY_AUDIT_AND_TOKEN_ACCOUNTING
```

Полная версия с таблицами, конфигурациями и roadmap находится в DOCX-отчёте.
