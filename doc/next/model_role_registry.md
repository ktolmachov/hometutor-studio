# Model Role Registry

> Date: 2026-06-03  
> Status: runtime contract companion for `app/provider.py`

## Runtime Contract

All LLM and embedding clients must be constructed through `app/provider.py`.
Application modules must not instantiate OpenAI-compatible clients directly and
must not read env variables directly for model routing.

| Role | Factory | Config | Intended Use |
|---|---|---|---|
| Primary answer | `get_llm()` | `LLM_MODEL`, `LLM_API_BASE`, `HOME_RAG_LOCAL_PROFILE`, `HOME_RAG_LLM_FALLBACK_*` | `/ask` RAG answer generation and primary chat path |
| Graph/concept | `get_graph_llm()` | `GRAPH_MODEL`, `GRAPH_LLM_API_BASE` | concept extraction, prerequisite chains, graph summaries, graph-aware tutor orchestration |
| Quiz generation | `get_quiz_llm_for_generation()` / `get_quiz_llm()` | `QUIZ_LLM_MODEL`, `QUIZ_LLM_API_BASE` | scoped quiz and micro-quiz generation |
| SSR why-now | `get_ssr_llm_resolved()` / `get_ssr_llm()` | `SSR_LLM_MODEL`, `SSR_LLM_API_BASE`, `SSR_LLM_API_KEY` | Smart Study Router explanation enrichment only |
| Query rewrite | `get_rewrite_llm()` | `REWRITE_MODEL` | query rewriting only |
| Query classification | `get_classifier_llm()` | `CLASSIFIER_MODEL` | query type / intent classification only |
| Evaluation judge | `get_judge_llm()` | `EVAL_JUDGE_LLM` | offline/eval-plane judging |
| Ingestion enrichment | `get_ingestion_llm()` | `INGESTION_MODEL` | metadata enrichment and extraction fallback |
| Inline quiz evaluation | `get_evaluate_llm()` | `EVALUATE_MODEL` | free-form quiz answer scoring |
| Embeddings | `get_embed_model()` | `EMBED_MODEL`, `EMBED_API_BASE`, `EMBED_DIMENSIONS` | indexing and retrieval embeddings |

## Guardrails

- `tests/test_model_role_contract.py` blocks direct `OpenAI(...)` construction
  outside `app/provider.py` and `app/provider_openai.py`.
- `tests/test_model_role_contract.py` blocks `get_llm()` imports/calls in
  graph-aware tutor orchestration modules.
- `tests/test_model_role_contract.py` keeps raw `os.getenv` / `os.environ`
  access inside a documented allowlist. New runtime settings should go through
  `get_settings()` / `get_retrieval_settings()`.

## Current Deliberate Exceptions

- `app/llm_local_circuit.py`: legacy low-level circuit-breaker knobs.
- `app/flashcard_service.py`: legacy E2E-only offline shortcut.
- `app/ingestion_env_diag.py`: diagnostic-only process environment comparison.

These exceptions should not be copied into new code.
