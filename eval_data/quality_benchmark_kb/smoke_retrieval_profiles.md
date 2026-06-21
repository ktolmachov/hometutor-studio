# Retrieval-профили: fast и quality

## Fast-профиль
- RAG_PROFILE=fast
- RETRIEVAL_MODE=vector_only
- SIMILARITY_TOP_K=8
- ENABLE_RERANKER=false
- RERANK_TOP_N=3
- Назначение: быстрый ответ с меньшим числом retrieved chunks; подходит для демо и ситуаций с ограниченным временем.

## Quality-профиль
- RAG_PROFILE=quality
- RETRIEVAL_MODE=hybrid
- SIMILARITY_TOP_K=10
- ENABLE_RERANKER=true
- RERANK_TOP_N=4
- Назначение: максимальная релевантность; использует reranker и строгую проверку источников.

Уникальный якорь: **SMOKE_PROFILES_UNIQUE_6183**.
