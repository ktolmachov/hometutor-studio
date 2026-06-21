<!--
Converted from D:/Downloads/LLM_Provider_Router_home_rag_v2.docx.
Generated mechanically from DOCX paragraphs and tables; review before treating as canonical architecture docs.
-->

# LLM Provider Router для home-rag_v2

Единая локальная модель + облачные модели OpenRouter/Yandex AI Studio по ролям

> Назначение документа: Собрать в одном месте контекст, 12 архитектурных пунктов, обновленный .env, routing policy, Yandex AI Studio adapter, модельную стратегию для RTX 4060 8GB и основу реализации LLM Provider Router.

## Контекст и исходные вводные

Проект home-rag_v2 использует гибридную схему: локальная LLM через LM Studio/Ollama для интерактивных задач и облачные LLM для специализированных ролей. В текущем конфиге уже есть OPENAI_API_BASE для OpenRouter, локальный LLM_API_BASE для LM Studio, отдельные роли EVAL_JUDGE_LLM, REWRITE_MODEL, CLASSIFIER_MODEL, INGESTION_MODEL, EVALUATE_MODEL, LLAMAINDEX_METADATA_FALLBACK_MODEL, SSR-блок и embeddings через OpenRouter.

Новая вводная: локальная видеокарта в ноутбуке — RTX 4060 Laptop 8GB. Это означает, что локально нужно держать одну универсальную модель, а не несколько моделей одновременно. Облачные модели можно выбирать по задаче и цена/качество.

> Ключевое решение: Локально — одна постоянно загруженная daily-driver модель. В облаке — специализированные модели под роли: judge, rewrite, classifier, coding, reasoning, graph, document, final synthesis.

## 1. Главная идея LLM Provider Router

LLM Provider Router — слой, который получает тип задачи, выбирает провайдера и модель, применяет fallback, валидирует ответ, оценивает стоимость и пишет trace. Это убирает жесткую привязку функций приложения к конкретным моделям.

## 2. Рекомендуемая локальная модель для RTX 4060 8GB

Для ноутбука с RTX 4060 8GB оптимальная единая локальная модель — Qwen2.5-Coder 7B Instruct в GGUF Q4_K_M/Q5_K_M через LM Studio. Она достаточно быстрая, хорошо работает с кодом, JSON, конфигами, .env, RAG-ответами, tutor/quiz/SSR.

## 3. Cloud-модели для будущего роутинга

Добавляется слой cloud-моделей по ролям: fast utility, coding fallback, reasoning, graph/long context, document/metadata. OpenRouter остается универсальным агрегатором, Yandex AI Studio добавляется как российский провайдер и fallback для больших моделей.

## 4. Цены OpenRouter для выбранных моделей

Цены нужно регулярно перепроверять, но в конфиге полезно зафиксировать справочные значения для оценки стоимости. Это позволит писать llm_router.jsonl и считать стоимость вызовов.

## 5. Архитектура LLM Provider Router

Архитектура строится вокруг task layer: feature layer вызывает router.call(task=...), router выбирает route, provider adapter выполняет запрос, response validator проверяет формат, trace logger пишет метрики.

## 6. Роли задач в Router

Каждая задача получает свою роль: local_chat, quiz, ssr, rewrite, classifier, judge, coding, reasoning, graph, document, metadata, final_synthesis. На старте тип задачи лучше передавать явно, а не пытаться угадывать всё автоматически.

## 7. Таблица routing policy

Routing policy фиксирует primary/fallback модель для каждой задачи, разрешение на local, ожидаемое качество, стоимость и ограничение контекста.

## 8. Минимальная реализация в коде

Достаточно enum задач, dataclass ModelRoute, registry ROUTES, provider adapters и cost estimator. Позже можно добавить бюджетные лимиты, кэш, ретраи и автоматический fallback.

## 9. Как Router должен принимать решение

Версия v1 — rule-based: вызывающий код явно передает task. Версия v2 — auto-router: intent classifier определяет fast/quality/graph/global и выбирает модельную роль.

## 10. Observability для Router

Каждый LLM-вызов должен логироваться: task, provider, model, input/output tokens, estimated cost, latency, status, fallback_used, errors. Без этого невозможно управлять качеством и бюджетом.

## 11. Защита от перерасхода

Нужны дневные/месячные бюджетные лимиты, лимиты контекста по ролям, блокировка frontier-моделей по умолчанию, сокращение контекста и fallback на дешевую модель.

## 12. Финальная recommended policy с Yandex AI Studio

Итоговая схема: Local LM Studio — быстрый worker; OpenRouter — дешевые и специализированные модели; Yandex AI Studio — российский fallback, Qwen/DeepSeek, final synthesis и сценарии с российской юрисдикцией.

## Обновленный .env: общий блок LLM Provider Router

```env
# =============================================================================
# LLM Provider Router
# =============================================================================
LLM_ROUTER_ENABLED=true

# === Local provider: one model only ===
LOCAL_PROVIDER=lmstudio
LOCAL_LLM_API_BASE=http://127.0.0.1:1234/v1
LOCAL_MAIN_MODEL=qwen2.5-coder-7b-instruct

# Backward-compatible local variables
LLM_API_BASE=http://127.0.0.1:1234/v1
LLM_MODEL=qwen2.5-coder-7b-instruct
QUIZ_LLM_MODEL=qwen2.5-coder-7b-instruct
SSR_LLM_MODEL=qwen2.5-coder-7b-instruct

# === OpenRouter provider ===
OPENAI_API_BASE=https://openrouter.ai/api/v1
CLOUD_PROVIDER=openrouter

CLOUD_FAST_MODEL=openai/gpt-4o-mini
CLOUD_CODING_MODEL=qwen/qwen-2.5-coder-32b-instruct
CLOUD_REASONING_MODEL=deepseek/deepseek-r1-distill-qwen-32b
CLOUD_GRAPH_MODEL=qwen/qwen3.5-35b-a3b
CLOUD_DOCUMENT_MODEL=google/gemma-4-31b-it

# === Backward-compatible role variables ===
EVAL_JUDGE_LLM=openai/gpt-4o-mini
REWRITE_MODEL=openai/gpt-4o-mini
CLASSIFIER_MODEL=openai/gpt-4o-mini
EVALUATE_MODEL=openai/gpt-4o-mini
INGESTION_MODEL=google/gemma-4-31b-it
LLAMAINDEX_METADATA_FALLBACK_MODEL=google/gemma-4-31b-it

```
## Новый .env-блок для Yandex AI Studio

```env
# =============================================================================
# Yandex AI Studio Provider
# =============================================================================
YANDEX_AI_STUDIO_ENABLED=true
YANDEX_AI_STUDIO_API_BASE=https://ai.api.cloud.yandex.net/v1

# Folder/project ID from Yandex Cloud
YANDEX_CLOUD_FOLDER=b1g1us8npnj05643a5ti

# Secret API key: keep only in .env, never commit to git
YANDEX_CLOUD_API_KEY=

# Main Yandex models
YANDEX_CLOUD_BIG_REASONING_MODEL=qwen3-235b-a22b-fp8/latest
YANDEX_CLOUD_GRAPH_MODEL=qwen3.5-35b/latest
YANDEX_CLOUD_REASONING_MODEL=deepseek-v3.2/latest

# Optional batch / cheaper models, if enabled in your folder
YANDEX_BATCH_QWEN32B_MODEL=qwen3-32b/latest
YANDEX_BATCH_QWEN30B_A3B_MODEL=qwen3-30b-a3b/latest
YANDEX_BATCH_DEEPSEEK_R1_32B_MODEL=deepseek-r1-distill-qwen-32b/latest
YANDEX_BATCH_GEMMA3_27B_MODEL=gemma3-27b-it/latest

```

## Справочная таблица моделей и цен

> Важно: Цены OpenRouter/Yandex могут меняться. Значения в таблице следует использовать как справочные и периодически сверять с личным кабинетом провайдера.

| Роль | Провайдер | Модель | Input | Output | Контекст | Применение |
| --- | --- | --- | --- | --- | --- | --- |
| fast / judge / rewrite / classifier | OpenRouter | openai/gpt-4o-mini | $0.15 / 1M | $0.60 / 1M | 128K | Дешевые служебные задачи |
| coding fallback | OpenRouter | qwen/qwen-2.5-coder-32b-instruct | $0.66 / 1M | $1.00 / 1M | 128K | Сложный код, C#/.NET, refactoring |
| reasoning | OpenRouter | deepseek/deepseek-r1-distill-qwen-32b | $0.29 / 1M | $0.29 / 1M | 128K | Reasoning, RCA, архитектурный анализ |
| graph / long context | OpenRouter | qwen/qwen3.5-35b-a3b | $0.139 / 1M | $1.00 / 1M | 262K | GraphRAG, relation extraction |
| document / metadata | OpenRouter | google/gemma-4-31b-it | $0.12 / 1M | $0.37 / 1M | 262K | Документы, summaries, metadata |
| final synthesis / РФ fallback | Yandex AI Studio | qwen3-235b-a22b-fp8/latest | см. Yandex pricing | см. Yandex pricing | зависит от модели | Финальный синтез, российская юрисдикция |
| reasoning fallback РФ | Yandex AI Studio | deepseek-v3.2/latest | см. Yandex pricing | см. Yandex pricing | зависит от модели | Reasoning fallback |

## Routing policy

| Task | Primary | Fallback | Local? | Комментарий |
| --- | --- | --- | --- | --- |
| local_chat | local qwen2.5-coder-7b | openai/gpt-4o-mini | Да | Обычный чат, быстрый RAG |
| quiz | local qwen2.5-coder-7b | openai/gpt-4o-mini | Да | Tutor/Quiz без облачной задержки |
| ssr | local qwen2.5-coder-7b | openai/gpt-4o-mini | Да | Короткие персональные объяснения |
| rewrite | openai/gpt-4o-mini | yandex qwen3.5-35b | Опц. | Стабильное дешёвое перефразирование |
| classifier | openai/gpt-4o-mini | local / yandex | Опц. | JSON intent / route classification |
| judge | openai/gpt-4o-mini | yandex deepseek-v3.2 | Нет | Независимая оценка |
| coding | qwen-2.5-coder-32b cloud | yandex qwen big | Опц. | Сложный код и refactoring |
| reasoning | deepseek-r1-distill-qwen-32b | yandex deepseek-v3.2 | Нет | Root cause, architecture trade-offs |
| graph | qwen3.5-35b-a3b | yandex qwen3.5-35b | Нет | GraphRAG, relations, long context |
| document | gemma-4-31b-it | yandex qwen3.5-35b | Опц. | Metadata, summaries, documents |
| final_synthesis | yandex qwen3-235b | openrouter qwen3.5-35b | Нет | Финальные ADR/документы |

## Целевая архитектура

```text
home-rag_v2
  ↓
Feature layer:
  - ask
  - quiz
  - ssr
  - ingestion
  - eval
  - graph
  ↓
LLM Task Layer:
  - local_chat
  - rewrite
  - classifier
  - judge
  - coding
  - reasoning
  - graph
  - document
  - final_synthesis
  ↓
LLM Provider Router:
  - route selection
  - model registry
  - fallback
  - cost estimate
  - JSON validation
  - tracing
  ↓
Providers:
  - Local LM Studio: qwen2.5-coder-7b-instruct
  - OpenRouter: gpt-4o-mini / Qwen / DeepSeek / Gemma
  - Yandex AI Studio: Qwen / DeepSeek via Responses API
  ↓
Observability:
  - logs/llm_router.jsonl
  - cost reports
  - latency reports
  - failure reports

```
## Provider aliases

```python
PROVIDERS = {
    "local": {
        "type": "openai_compatible_chat",
        "api_base": "http://127.0.0.1:1234/v1",
        "api_key_env": "LOCAL_LLM_API_KEY",
    },
    "openrouter": {
        "type": "openai_compatible_chat",
        "api_base": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
    },
    "yandex": {
        "type": "yandex_responses",
        "api_base": "https://ai.api.cloud.yandex.net/v1",
        "api_key_env": "YANDEX_CLOUD_API_KEY",
        "folder_env": "YANDEX_CLOUD_FOLDER",
        "model_uri_template": "gpt://{folder}/{model}",
    },
}

```
## Yandex AI Studio adapter

```python
import openai
from dataclasses import dataclass

@dataclass(frozen=True)
class YandexAIStudioConfig:
    api_key: str
    folder_id: str
    base_url: str = "https://ai.api.cloud.yandex.net/v1"

class YandexAIStudioClient:
    def __init__(self, config: YandexAIStudioConfig):
        self.config = config
        self.client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            project=config.folder_id,
        )

    def model_uri(self, model: str) -> str:
        return f"gpt://{self.config.folder_id}/{model}"

    def generate(self, model: str, input_text: str, instructions: str = "",
                 temperature: float = 0.3, max_output_tokens: int = 1000) -> str:
        response = self.client.responses.create(
            model=self.model_uri(model),
            temperature=temperature,
            instructions=instructions,
            input=input_text,
            max_output_tokens=max_output_tokens,
        )
        return response.output_text

```
## Cost estimator

```python
def estimate_cost_usd(input_tokens: int, output_tokens: int,
                      input_price_per_m: float, output_price_per_m: float) -> float:
    return (
        input_tokens / 1_000_000 * input_price_per_m
        + output_tokens / 1_000_000 * output_price_per_m
    )

```

## Observability и бюджетные ограничения

| Метрика | Зачем |
| --- | --- |
| llm_calls_total | Количество вызовов по task/model/provider |
| llm_cost_usd_total | Суммарная оценочная стоимость |
| llm_latency_ms | Задержка p50/p95 по ролям |
| llm_fallback_count | Сколько раз сработал fallback |
| llm_json_validation_errors | Ошибки structured output |
| llm_task_distribution | Какие задачи вызывают больше всего LLM |
| local_model_usage_ratio | Доля локальных вызовов |


```env
LLM_ROUTER_DAILY_BUDGET_USD=5.00
LLM_ROUTER_MONTHLY_BUDGET_USD=50.00
LLM_ROUTER_MAX_INPUT_TOKENS_FAST=8000
LLM_ROUTER_MAX_INPUT_TOKENS_GRAPH=64000
LLM_ROUTER_MAX_INPUT_TOKENS_DOCUMENT=128000
LLM_ROUTER_BLOCK_FRONTIER_BY_DEFAULT=true
```

## Настройки retrieval для RTX 4060 8GB

```env
RAG_PROFILE=fast
RETRIEVAL_MODE=vector_only
SIMILARITY_TOP_K=8
ENABLE_RERANKER=false
RERANK_TOP_N=3

# Embeddings лучше оставить в облаке, чтобы не конкурировать за VRAM.
EMBED_API_BASE=https://openrouter.ai/api/v1
EMBED_MODEL=perplexity/pplx-embed-v1-0.6b
EMBED_DIMENSIONS=1024

```

## План внедрения

| Шаг | Действие |
| --- | --- |
| 1 | Добавить .env-переменные для LLM_ROUTER, OpenRouter и Yandex AI Studio. |
| 2 | Создать ProviderAdapter интерфейс и три реализации: LocalLMStudioAdapter, OpenRouterAdapter, YandexAIStudioAdapter. |
| 3 | Вынести route registry в отдельный модуль app/llm/router.py или app/llm/provider_router.py. |
| 4 | Перевести rewrite/classifier/judge/document вызовы на router.call(task=...). |
| 5 | Добавить llm_router.jsonl trace: task, provider, model, tokens, cost, latency, fallback. |
| 6 | Добавить бюджетные лимиты и fallback strategy. |
| 7 | Позже добавить auto-router: intent → fast/quality/graph/global → task role. |

## Источники и примечания

OpenRouter model pages: цены и контекстные окна для openai/gpt-4o-mini, Qwen2.5-Coder 32B, DeepSeek R1 Distill Qwen 32B, Qwen3.5-35B-A3B, Gemma 4 31B.

Yandex AI Studio documentation: Responses API, OpenAI SDK, model URI gpt://<folder>/<model>, API key and folder/project ID.

Текущий config.env проекта: локальный LM Studio endpoint, OpenRouter endpoint, SSR, embeddings, retrieval settings, service-role model variables.

Цены могут измениться, поэтому в production нужно периодически обновлять price registry и сравнивать фактический usage/cost.
