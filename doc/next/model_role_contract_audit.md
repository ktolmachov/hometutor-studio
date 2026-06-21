# Model-Role Contract Audit

> **Дата:** 2026-06-02  
> **Статус:** no-code audit note  
> **Основание:** `config.env`, финальное решение по `qwen/qwen3.6-27b`, `doc/next/localhost_balance_course_delight_breakthrough.md`  
> **Кодовые доработки:** не выполнялись

---

## Цель

Проверить, как runtime сейчас разводит роли моделей:

- learning-plane: `LLM_MODEL`, `QUIZ_LLM_MODEL`, `GRAPH_MODEL`, `SSR_LLM_MODEL`;
- secondary/evaluation-plane: `EVAL_JUDGE_LLM`, `REWRITE_MODEL`, `CLASSIFIER_MODEL`, `INGESTION_MODEL`, `EVALUATE_MODEL`;
- privacy/routing: `HOME_RAG_DATA_MODE`, `HOME_RAG_LLM_FALLBACK_*`.

Новый целевой контракт:

```env
LLM_MODEL=qwen/qwen3.6-27b
QUIZ_LLM_MODEL=qwen/qwen3.6-27b
SSR_LLM_MODEL=qwen/qwen3.6-27b
GRAPH_LLM_API_BASE=http://127.0.0.1:1234/v1
GRAPH_MODEL=qwen/qwen3.6-27b
```

---

## Executive Summary

Аудит нашёл один blocker и несколько high-priority несоответствий.

Главный blocker: `GRAPH_MODEL` и `GRAPH_LLM_API_BASE` есть в `config.env`, но в typed `Settings` нет соответствующих полей. Так как `SettingsConfigDict(extra="ignore")`, эти env keys сейчас не становятся частью runtime settings. Значит новый graph/concept contract пока документирован, но не исполняется кодом.

Второй важный риск: secondary cloud roles заданы как `openai/...` / `google/...`, но `get_judge_llm()`, `get_rewrite_llm()`, `get_classifier_llm()`, `get_ingestion_llm()` и `get_evaluate_llm()` строят клиентов на `_lmstudio_api_base()`, а не на cloud/OpenRouter base. Исключение: `get_quiz_llm()` уже умеет auto-route cloud model -> `OPENAI_API_BASE`.

Третий риск: primary chat fallback включён при `HOME_RAG_DATA_MODE=real`. Это не обязательно баг, но без явного consent/route guard это конфликтует с local-first privacy posture.

### Follow-up 2026-06-03

Закрыто кодовым пакетом `model-role provider hardening`:

- `GRAPH_LLM_API_BASE` и `GRAPH_MODEL` добавлены в typed `Settings`.
- Добавлен `get_graph_llm()` для local graph/concept role.
- Secondary cloud roles получили общий role routing: `openai/...` и `google/...` идут на `OPENAI_API_BASE`, local ids вроде `qwen/qwen3.6-27b` остаются на LM Studio base.
- Добавлены targeted tests для graph settings, graph LLM и routing ролей judge/rewrite/classifier/ingestion/evaluate.

Остаётся отдельным следующим пакетом: privacy/consent gate для `HOME_RAG_DATA_MODE=real` и transparent source metadata (`local|cloud|cached`) в API/UI/session tape.

Follow-up 2026-06-03, package `transparent localhost balance guard`: privacy/consent gate and `/ask` source metadata are implemented for primary chat. Real data requires explicit `HOME_RAG_LLM_CLOUD_CONSENT=true` before cloud fallback; demo data may use fallback. `/ask` debug and `pipeline_trace.generate_stage` now expose `llm_source`, `llm_model`, `llm_api_base`, `fallback_used`, `llm_profile`, and latency metadata.

Follow-up 2026-06-03, package `UI transparency`: Streamlit Q&A answer area, status sidebar, and debug panel render the source badge (`Local` / `Cloud` / `Cache`), model, fallback marker, profile, and latency. Cloud answers also show the env-level consent notice.

Follow-up 2026-06-03, package `graph-role tutor orchestration enforcement`:

- `app.tutor_orchestrator.invoke_pedagogical_orchestrator_llm()` now uses `get_graph_llm()` for the graph-aware pedagogical routing decision.
- `app.orchestrator_router.PedagogicalRouter` now defaults to `get_graph_llm()` for personalized subgraph agent reasoning and self-correction.
- Micro-quiz generation remains on quiz role (`get_quiz_llm_for_generation()`), not graph role.
- Added targeted tests to prevent regressions back to primary chat `get_llm()`.

Follow-up 2026-06-03, package `model-role static guard`: `doc/next/model_role_registry.md` is now the compact role registry, and `tests/test_model_role_contract.py` guards provider-only client construction, graph-role tutor orchestration, and raw env access allowlists.

Remaining future work: add a user-facing consent control instead of relying only on env-level `HOME_RAG_LLM_CLOUD_CONSENT`.

---

## Findings

### P0. `GRAPH_MODEL` не подключён к typed settings — resolved 2026-06-03

**Evidence:**

- `config.env` задаёт `GRAPH_LLM_API_BASE=http://127.0.0.1:1234/v1` и `GRAPH_MODEL=qwen/qwen3.6-27b`.
- `app/config.py:51-54` включает `extra="ignore"`.
- В `app/config.py` есть graph retrieval параметры, но нет `graph_llm_api_base` / `graph_model`.
- `rg "GRAPH_MODEL|GRAPH_LLM|graph_model"` по `app/` не нашёл runtime-потребителя этих env keys.

**Impact:** Course graph analysis, concept extraction, prerequisite chains и Smart Study Router support не могут гарантированно использовать `qwen/qwen3.6-27b` как local graph/concept model. Сейчас graph keys являются advisory config, а не исполняемым runtime contract.

**Recommendation:** выполнено в `app/config.py`:

```python
graph_llm_api_base: str | None = Field(
    default=None,
    validation_alias=AliasChoices("GRAPH_LLM_API_BASE"),
)
graph_model: str | None = Field(
    default=None,
    validation_alias=AliasChoices("GRAPH_MODEL"),
)
```

Provider factory `get_graph_llm()` добавлен в `app/provider.py`.

### P1. Secondary cloud roles используют local API base — resolved 2026-06-03

**Evidence:**

- `app/provider.py:430-446` `get_judge_llm()` выбирает `s.eval_judge_llm or s.llm_model`, но `api_base=_lmstudio_api_base(s)`.
- `app/provider.py:449-460` `get_rewrite_llm()` выбирает `s.rewrite_model or s.llm_model`, но `api_base=_lmstudio_api_base(s)`.
- `app/provider.py:463-474` `get_classifier_llm()` выбирает `s.classifier_model or s.llm_model`, но `api_base=_lmstudio_api_base(s)`.
- `app/provider.py:504-515` `get_ingestion_llm()` выбирает `s.ingestion_model or s.llm_model`, но `api_base=_lmstudio_api_base(s)`.
- `app/provider.py:518-528` `get_evaluate_llm()` выбирает `s.evaluate_model or s.llm_model`, но `api_base=_lmstudio_api_base(s)`.
- `config.env` задаёт these roles как `openai/gpt-4o-mini` и `google/gemma-4-31b-it`.

**Impact:** при включении rewrite/classifier/eval/ingestion/evaluate runtime может отправить cloud model id на локальный LM Studio endpoint. Это даст ошибку model not found или, хуже, ложное ощущение, что cloud role работает.

**Recommendation:** выполнено через shared resolver для role-specific LLM:

- если model выглядит cloud/provider-prefixed (`openai/`, `google/`, `anthropic/`, `deepseek/`, etc.) -> `OPENAI_API_BASE`;
- если model local/bare local id -> `LMSTUDIO_API_BASE`;
- explicit role api base можно добавить позже, если понадобится.

Минимальный первый шаг выполнен для judge/rewrite/classifier/ingestion/evaluate.

### P1. Cloud model detection слишком узкий

**Evidence:**

- `get_quiz_llm()` auto-routes cloud model через `_is_cloud_model()` (`app/provider.py:488-495`).
- `_is_cloud_model()` покрывает `gpt-4o`, `gpt-4`, `claude`, `gemini`, но не покрывает provider-prefixed ids вроде `google/gemma-4-31b-it`.

**Impact:** `INGESTION_MODEL=google/gemma-4-31b-it` не будет корректно распознаваться как cloud/provider model при переносе resolver logic из quiz на secondary roles, если не расширить detector.

**Recommendation:** заменить `_is_cloud_model()` на `_is_remote_model_id()` с provider-prefix allowlist:

```text
openai/, google/, anthropic/, deepseek/, qwen/, mistralai/, meta-llama/
```

При этом local LM Studio ids тоже могут содержать slash (`qwen/qwen3.6-27b`), поэтому детектор должен учитывать не только slash, но и выбранную роль/base. Для `LLM_MODEL=qwen/qwen3.6-27b` slash не должен автоматически означать cloud, потому что primary local base уже зафиксирован как LM Studio.

### P1. `HOME_RAG_DATA_MODE=real` + fallback enabled требует explicit consent gate

**Evidence:**

- `app/config.py:348-356` задаёт `home_rag_data_mode` и `home_rag_llm_fallback_enabled`.
- `app/provider.py:343-362` в `balanced` при open circuit breaker и ready fallback возвращает fallback LLM.
- В `config.env`: `HOME_RAG_DATA_MODE=real`, `HOME_RAG_LLM_FALLBACK_ENABLED=true`, `HOME_RAG_LLM_FALLBACK_MODEL=openai/gpt-4o-mini`.

**Impact:** primary chat может уйти в cloud в режиме real data. Это может быть корректно только если есть UI/user consent или route-level policy, но сам provider сейчас не проверяет `home_rag_data_mode`.

**Recommendation:** перед rollout Transparent Localhost Balance добавить policy layer:

- `real` + no explicit consent -> no cloud fallback;
- `demo` + fallback enabled -> fallback allowed;
- telemetry/source badge обязательно показывает `local|cloud|cached`.

### P2. SSR local-first работает, но fallback на main LLM может привести к cloud fallback

**Evidence:**

- `app/provider.py:373-396` `get_ssr_llm_resolved()` использует dedicated `ssr_llm_api_base` / `ssr_llm_model`.
- `app/provider.py:384-385` если loopback SSR недоступен, возвращает `get_llm(), True`.
- `app/ssr_explain_service.py:156-158` учитывает `ssr_used_main_llm`.

**Impact:** если SSR loopback down, SSR explanation может пойти в main primary route. При `balanced` и open CB main route может уйти в cloud fallback. Для local-first graph/SSR posture это должно быть явным UX/policy решением.

**Recommendation:** добавить SSR policy: для `HOME_RAG_DATA_MODE=real` SSR loopback down -> template fallback / no LLM, а не automatic cloud fallback. Для demo можно разрешить cloud fallback с source metadata.

### P2. Ingestion role dormant by config, но defaults в code противоположные

**Evidence:**

- В `config.env`: `ENABLE_METADATA_ENRICHMENT=false`, `ENABLE_DOCUMENT_SUMMARIES=false`.
- В `app/config.py:195-196` defaults: `enable_metadata_enrichment=True`, `enable_document_summaries=True`.
- `app/ingestion_enrichment.py` вызывает enrichment только при этих flags.

**Impact:** tracked `config.env` защищает текущий сценарий, но если `config.env` не загрузится или OS env переопределит значения, ingestion LLM может стать активным.

**Recommendation:** для local-first posture рассмотреть изменение code defaults на `False`, а включение enrichment делать явным. Это не срочно, но снижает риск unexpected cloud/document-derived calls.

---

## Confirmed Good

- `LLM_MODEL` и `QUIZ_LLM_MODEL` есть в `Settings` (`app/config.py:76`, `app/config.py:86`).
- `get_llm()` разделяет `local_strict`, `balanced`, `cloud_fast` и умеет fallback через `HOME_RAG_LLM_FALLBACK_*` (`app/provider.py:308-369`).
- `get_quiz_llm()` уже имеет auto-routing по модели и explicit `QUIZ_LLM_API_BASE` override (`app/provider.py:477-501`).
- SSR имеет dedicated base/model route и local loopback key fallback (`app/provider.py:373-401`).
- Rewrite/classifier steps используют provider factories, а не прямые clients (`app/pipeline_steps.py:175-218`).
- Прямых OpenAI/LLM client constructions вне `app/provider.py` не найдено, кроме wrapper module `app/provider_openai.py`.

---

## Recommended Next Write-Set

Если переходить к коду, минимальный безопасный пакет:

```text
app/config.py
app/provider.py
tests/test_config.py
tests/test_provider.py
doc/changelog.md
```

Scope:

1. Добавить `graph_llm_api_base` / `graph_model` в `Settings`.
2. Добавить `get_graph_llm()` или resolver-only helper.
3. Обобщить role routing для judge/rewrite/classifier/ingestion/evaluate.
4. Добавить tests:
   - `GRAPH_MODEL` читается из env;
   - graph LLM использует local base/model;
   - `REWRITE_MODEL=openai/gpt-4o-mini` идёт на `OPENAI_API_BASE`;
   - `INGESTION_MODEL=google/gemma-4-31b-it` не идёт на LM Studio;
   - primary `LLM_MODEL=qwen/qwen3.6-27b` остаётся на local base.

Отдельным пакетом после этого:

```text
app/provider.py
app/llm_resilience.py
app/api_models.py
Streamlit UI
tests/test_query_service.py
doc/changelog.md
```

Scope: consent/source metadata для `HOME_RAG_DATA_MODE=real` и transparent fallback badge.

---

## Suggested Order

1. **Fix model-role runtime contract**: graph settings + role-specific api base routing.
2. **Add privacy gate**: real data cannot silently use cloud fallback.
3. **Expose source metadata**: local/cloud/cached in API/UI/session tape.
4. **Only then continue Course Delight**: folder -> course -> graph DNA -> Golden E2E.

---

## Bottom Line

Документы и `config.env` уже говорят правильную новую стратегию: `qwen/qwen3.6-27b` как balanced local model для learning core. Код пока частично живёт в старой модели мира: graph env keys не подключены, а secondary cloud roles не имеют корректного cloud routing.

Следующий кодовый пакет должен быть не feature work, а маленький LLM provider/config hardening package. Это даст устойчивую основу для Course Delight без скрытых cloud calls и без model-id/base mismatch.
