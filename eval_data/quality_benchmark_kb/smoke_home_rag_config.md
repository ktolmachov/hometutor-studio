# Конфигурация home_rag

Финальная локальная модель для home_rag: **qwopus3.6-35b-a3b-v1-mtp**.

Все роли learning-plane используют одну и ту же модель:
- LLM_MODEL=qwopus3.6-35b-a3b-v1-mtp
- QUIZ_LLM_MODEL=qwopus3.6-35b-a3b-v1-mtp
- GRAPH_MODEL=qwopus3.6-35b-a3b-v1-mtp
- SSR_LLM_MODEL=qwopus3.6-35b-a3b-v1-mtp

Retrieval-профиль quality-first:
- RAG_PROFILE=quality
- RETRIEVAL_MODE=hybrid
- SIMILARITY_TOP_K=10
- ENABLE_RERANKER=true
- RERANK_TOP_N=4

LLM API endpoint: http://127.0.0.1:1234/v1 (LM Studio).

Уникальный якорь: **SMOKE_CONFIG_UNIQUE_2741**.
