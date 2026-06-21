# План оптимизации входных токенов LLM

**Статус:** 🟡 Планирование  
**Дата создания:** 2026-04-19  
**Автор анализа:** Staff Engineer, LLM Architecture  
**Последнее обновление:** 2026-04-19  

---

## 📋 Оглавление

1. [Executive Summary](#executive-summary)
2. [Текущее состояние](#текущее-состояние)
3. [P0: Критическое (сегодня–завтра)](#p0-критическое-сегодня–завтра)
4. [P1: Ближайшее время (1–2 недели)](#p1-ближайшее-время-1–2-недели)
5. [P2: Архитектурные меры (3–4 недели)](#p2-архитектурные-меры-3–4-недели)
6. [Контрольные точки](#контрольные-точки)
7. [Риски и зависимости](#риски-и-зависимости)
8. [FAQ и troubleshooting](#faq-и-troubleshooting)

---

## Executive Summary

### Проблема
- **Базовый входной уровень:** 17–20k токенов (должно быть 3–5k)
- **Экстремальный выброс:** 83041 токенов в одном вызове
- **Потери на retry:** 3 идентичных ошибочных вызова × 46901 токенов
- **Общая переплата:** ~40–50% от необходимого расхода токенов

### Целевое состояние (после оптимизации)
- ✅ Базовый уровень: 6–8k токенов
- ✅ Максимум без особых причин: 15k токенов
- ✅ Нет выбросов > 20k
- ✅ Нет повторных retry одного payload
- ✅ Полная видимость breakdown токенов

### Ожидаемый результат
- **Снижение входных токенов на 40–60%**
- **Экономия $20–50 за 100 вызовов**
- **Улучшение latency** (меньше контекста = быстрее)
- **Лучшее качество** (меньше noise в контексте)

### Timeline
- **P0 (критическое):** 1–2 дня
- **P1 (среднесрочное):** 2–3 недели
- **P2 (архитектура):** 3–4 недели
- **Итого:** 1 месяц для полной оптимизации

---

## Текущее состояние

### Статистика из логов (19 апреля 2026)

| Метрика | Значение | Статус |
|---|---|---|
| Среднее входных токенов | 22,241 | 🔴 Критическое (должно 3–5k) |
| Максимум входных токенов | 83,041 | 🔴 Экстремальный выброс |
| Медиана входных токенов | 18,354 | 🔴 Завышена на 300–400% |
| Повторные retry в период | 3 | 🔴 Без дедупликации |
| Вызовов с input > 20k | 7 из 14 успешных (50%) | 🟡 Половина вызовов тяжёлые |
| Вызовов с низкой эффективностью (in >> out) | 8 из 17 (47%) | 🟡 Много контекста впустую |

### Выявленные проблемы

| # | Проблема | Вероятность | Влияние | Статус |
|---|---|---|---|---|
| 1 | Полная история диалога в каждом вызове | 80–90% | -12–15k токенов / вызов | ❌ Не исправлено |
| 2 | Необрезанный RAG или полные файлы | 85–95% | -5–10k базовый + выброс 80k | ❌ Не исправлено |
| 3 | Retry-петля без дедупликации | 95% | -93k впустую в текущий период | ❌ Не исправлено |
| 4 | Дублирование system prompt | 50–60% | -2–5k токенов / вызов | ❓ Не проверено |
| 5 | Неправильный выбор thinking-модели | 30–40% | -до 20% | ❓ Не проверено |

---

## P0: Критическое (сегодня–завтра)

### 🎯 Цель P0
**Остановить кровотечение входных токенов в течение 24 часов.**

- ✅ Убрать возможность отправки >50k входа
- ✅ Убрать retry-петли (дедупликация)
- ✅ Ограничить историю до 10–15 сообщений
- ✅ Начать логировать breakdown токенов

### Задача P0.1: Добавить hard limit на входные токены

**Приоритет:** 🔴 КРИТИЧЕСКОЕ  
**Estimated Time:** 2–4 часа  
**Owner:** Backend Engineer  
**Status:** ⏳ Ожидание

#### Описание
Добавить валидацию перед каждым вызовом LLM API, которая:
1. Блокирует запрос если входных токенов > 50000
2. Логирует WARNING если > 30000
3. Автоматически обрезает историю если > 25000
4. Всегда логирует текущий count входных токенов

#### Файлы для изменения
- `src/api/client.py` или `src/llm/base.py` (основной LLM client)
- `src/prompts/builder.py` (если есть отдельный builder)
- `tests/test_token_limits.py` (новый тест)

#### Реализация

**Шаг 1: Добавить функцию估算 токенов**
```python
# src/utils/token_counter.py
import tiktoken

def estimate_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Estimate number of tokens for given text."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback для неизвестных моделей
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def estimate_messages_tokens(messages: List[Dict], model: str) -> int:
    """Estimate tokens for messages array."""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""), model)
        total += 4  # overhead per message
    return total
```

**Шаг 2: Добавить валидацию в LLM client**
```python
# src/api/client.py (или где находится основной вызов)
from src.utils.token_counter import estimate_messages_tokens
import logging

logger = logging.getLogger(__name__)

HARD_LIMIT_INPUT = 50_000  # Блокировать выше этого
SOFT_LIMIT_INPUT = 30_000  # Логировать warning
TRIM_LIMIT_INPUT = 25_000  # Обрезать историю

class LLMClient:
    async def call(self, messages, model, **kwargs):
        """
        Основной метод вызова LLM с валидацией токенов.
        """
        # Считаем входные токены
        input_tokens = estimate_messages_tokens(messages, model)
        
        # Логируем текущий статус
        logger.info(
            f"LLM Call Info",
            extra={
                "model": model,
                "input_tokens": input_tokens,
                "num_messages": len(messages),
            }
        )
        
        # Проверка hard limit
        if input_tokens > HARD_LIMIT_INPUT:
            logger.error(
                f"Input tokens exceed hard limit: {input_tokens} > {HARD_LIMIT_INPUT}",
                extra={"messages_count": len(messages)}
            )
            raise ValueError(
                f"Input size too large ({input_tokens} tokens). "
                f"Max allowed: {HARD_LIMIT_INPUT}. "
                f"Please reduce context or history."
            )
        
        # Проверка мягкого лимита + автотрим
        if input_tokens > TRIM_LIMIT_INPUT:
            logger.warning(
                f"Input tokens above trim threshold: {input_tokens} > {TRIM_LIMIT_INPUT}",
                extra={"will_trim": True}
            )
            messages = self._trim_messages(messages, TRIM_LIMIT_INPUT, model)
            input_tokens = estimate_messages_tokens(messages, model)
            logger.info(f"After trim: {input_tokens} tokens")
        
        # Проверка warning threshold
        if input_tokens > SOFT_LIMIT_INPUT:
            logger.warning(
                f"Input tokens above soft limit: {input_tokens} > {SOFT_LIMIT_INPUT}"
            )
        
        # Отправить в API
        response = await self._call_api(messages, model, **kwargs)
        
        # Логировать результат
        output_tokens = response.get("usage", {}).get("output_tokens", 0)
        logger.info(
            f"LLM Response Info",
            extra={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_cost_estimate": self._estimate_cost(input_tokens, output_tokens, model),
            }
        )
        
        return response
    
    def _trim_messages(self, messages, target_tokens, model):
        """Обрезать историю если нужно."""
        # Обычно system message + последние N messages
        if messages and messages[0].get("role") == "system":
            system_msg = messages[0]
            rest = messages[1:]
        else:
            system_msg = None
            rest = messages
        
        # Оставить последние N сообщений
        # Примерно: 1000 токенов system + 500 на текущий запрос + rest на историю
        target_for_history = target_tokens - 1500
        
        trimmed = []
        current_tokens = 0
        
        # Берём в обратном порядке (от новых к старым)
        for msg in reversed(rest):
            msg_tokens = estimate_tokens(msg.get("content", ""), model)
            if current_tokens + msg_tokens > target_for_history:
                break
            trimmed.insert(0, msg)
            current_tokens += msg_tokens
        
        # Собираем финальный array
        result = []
        if system_msg:
            result.append(system_msg)
        result.extend(trimmed)
        
        logger.info(f"Trimmed from {len(messages)} to {len(result)} messages")
        return result
```

**Шаг 3: Тест для валидации**
```python
# tests/test_token_limits.py
import pytest
from src.api.client import LLMClient, HARD_LIMIT_INPUT

@pytest.mark.asyncio
async def test_hard_limit_blocks_large_input():
    """Проверить, что hard limit блокирует большие запросы."""
    client = LLMClient()
    
    # Составить messages с >50k токенов
    large_text = "x" * 200_000  # ~50k токенов
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": large_text},
    ]
    
    # Должен выбросить ошибку
    with pytest.raises(ValueError, match="Input size too large"):
        await client.call(messages, model="gpt-4")

@pytest.mark.asyncio
async def test_auto_trim_reduces_tokens():
    """Проверить, что auto-trim срабатывает."""
    client = LLMClient()
    
    # Составить messages с >25k но <50k токенов
    large_text = "x" * 100_000  # ~25k токенов
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Previous message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": large_text},
    ]
    
    # Должен обрезать, но не выбросить ошибку
    response = await client.call(messages, model="gpt-4")
    assert response is not None  # Success
```

#### Acceptance Criteria
- [ ] Запрос с >50k входных токенов выбросит ValueError
- [ ] Запрос с 30k–50k входных токенов логирует WARNING и автоматически обрезает историю
- [ ] Все вызовы логируют текущий count входных токенов
- [ ] Тесты проходят
- [ ] На логах из отчета (запись #5 с 83041) выбросится ошибка или обрежется

#### Успешность
✅ Выброс 83041 будет заблокирован или обрезан  
✅ Базовый уровень будет снижен на 5–10k токенов

---

### Задача P0.2: Внедрить request deduplication

**Приоритет:** 🔴 КРИТИЧЕСКОЕ  
**Estimated Time:** 2–4 часа  
**Owner:** Backend Engineer  
**Status:** ⏳ Ожидание

#### Описание
Убрать retry-петли, в которых идентичный запрос отправляется несколько раз подряд (как в записях #15–17: 46901 токенов, 3 раза).

Механизм:
1. Хешировать request payload (модель + messages + параметры)
2. Кэшировать результат на 5–10 секунд
3. Если запрос идентичен — вернуть кэшированный результат вместо повторного вызова

#### Файлы для изменения
- `src/api/client.py` (добавить кэширование)
- `src/utils/cache.py` (новый, LRU cache)

#### Реализация

**Шаг 1: Создать request cache**
```python
# src/utils/cache.py
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Optional

class RequestCache:
    """LRU cache for API requests with TTL."""
    
    def __init__(self, maxsize: int = 100, ttl_seconds: int = 10):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.timestamps = {}
    
    def _hash_request(self, model: str, messages: list, **kwargs) -> str:
        """Generate hash of request for deduplication."""
        # Не хешируем весь kwargs, только важные параметры
        request_dict = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature"),
            "max_tokens": kwargs.get("max_tokens"),
            "top_p": kwargs.get("top_p"),
        }
        
        request_str = json.dumps(request_dict, sort_keys=True, default=str)
        return hashlib.sha256(request_str.encode()).hexdigest()
    
    def get(self, model: str, messages: list, **kwargs) -> Optional[Any]:
        """Get cached response if exists and not expired."""
        request_hash = self._hash_request(model, messages, **kwargs)
        
        if request_hash not in self.cache:
            return None
        
        # Проверить TTL
        timestamp = self.timestamps.get(request_hash)
        if time.time() - timestamp > self.ttl_seconds:
            # Expired
            del self.cache[request_hash]
            del self.timestamps[request_hash]
            return None
        
        return self.cache[request_hash]
    
    def set(self, model: str, messages: list, response: Any, **kwargs):
        """Cache response."""
        request_hash = self._hash_request(model, messages, **kwargs)
        
        # Удалить если переполнено
        if len(self.cache) >= self.maxsize:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        
        self.cache[request_hash] = response
        self.timestamps[request_hash] = time.time()
        
        # Move to end (LRU)
        self.cache.move_to_end(request_hash)

# Глобальный cache
_request_cache = RequestCache(maxsize=100, ttl_seconds=10)

def get_request_cache() -> RequestCache:
    return _request_cache
```

**Шаг 2: Интегрировать в LLM client**
```python
# src/api/client.py
from src.utils.cache import get_request_cache
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    async def call(self, messages, model, **kwargs):
        """
        Основной метод с дедупликацией.
        """
        cache = get_request_cache()
        
        # Проверить кэш
        cached_response = cache.get(model, messages, **kwargs)
        if cached_response:
            logger.info(
                "Returning cached response (deduplication)",
                extra={
                    "model": model,
                    "messages_count": len(messages),
                }
            )
            return cached_response
        
        # Валидация токенов (из P0.1)
        input_tokens = estimate_messages_tokens(messages, model)
        if input_tokens > HARD_LIMIT_INPUT:
            raise ValueError(f"Input too large: {input_tokens}")
        
        logger.info(f"Making API call (not cached)", extra={"input_tokens": input_tokens})
        
        # Вызвать API
        response = await self._call_api(messages, model, **kwargs)
        
        # Кэшировать результат
        cache.set(model, messages, response, **kwargs)
        
        return response
```

**Шаг 3: Логирование retry**
```python
# В async retry wrapper (если есть)
import logging

logger = logging.getLogger(__name__)

async def call_with_retry(client, messages, model, max_retries=2, **kwargs):
    """Call with exponential backoff и логированием."""
    import asyncio
    
    for attempt in range(max_retries + 1):
        try:
            response = await client.call(messages, model, **kwargs)
            if attempt > 0:
                logger.info(
                    f"Succeeded after {attempt} retries",
                    extra={"model": model}
                )
            return response
        
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"API call failed, retrying in {wait_time}s",
                    extra={
                        "attempt": attempt + 1,
                        "error": str(e),
                        "next_backoff": wait_time,
                    }
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"API call failed after {max_retries} retries",
                    extra={"error": str(e)}
                )
                raise
```

#### Acceptance Criteria
- [ ] Два идентичных запроса подряд — второй вернёт кэшированный ответ
- [ ] Кэш работает 10 секунд, потом очищается (TTL)
- [ ] Максимум 100 entries в кэше (LRU вытеснение)
- [ ] Логируется каждый cache hit и retry
- [ ] Записи #15–17 (три идентичных ERR) — максимум одна реальная отправка

#### Успешность
✅ Retry-петля из 3 вызовов будет сокращена до 1  
✅ Экономия 93k входных токенов сразу

---

### Задача P0.3: Ограничить историю чата до 10–15 сообщений

**Приоритет:** 🔴 КРИТИЧЕСКОЕ  
**Estimated Time:** 1–2 часа  
**Owner:** Backend Engineer  
**Status:** ⏳ Ожидание

#### Описание
Вместо отправки полного диалога в модель, отправлять только последние 10–15 сообщений.

Это должно снизить базовый входной уровень с 17–20k до 4–6k токенов.

#### Файлы для изменения
- `src/prompts/builder.py` или `src/chat/message_builder.py`
- `tests/test_history_limit.py` (новый тест)

#### Реализация

**Текущее состояние (вероятное)**
```python
# ❌ ЧТО БЫЛО РАНЬШЕ
messages = [
    {"role": "system", "content": system_prompt},
    # ... весь диалог, 50+ сообщений
    {"role": "user", "content": "Latest query"},
]
```

**Желаемое состояние**
```python
# ✅ ЧТО ДОЛЖНО БЫТЬ
MAX_HISTORY_MESSAGES = 15

messages = [
    {"role": "system", "content": system_prompt},
    # ... только последние 15 сообщений из истории
    {"role": "user", "content": "Latest query"},
]
```

**Реализация в коде**
```python
# src/chat/message_builder.py (или переименовать существующий)

from typing import List, Dict

MAX_HISTORY_MESSAGES = 15

def build_messages_with_history_limit(
    system_prompt: str,
    chat_history: List[Dict],
    current_query: str,
    max_history: int = MAX_HISTORY_MESSAGES,
) -> List[Dict]:
    """
    Собрать messages array с ограничением на историю.
    
    Args:
        system_prompt: Системный prompt
        chat_history: Полная история диалога
        current_query: Текущий запрос от пользователя
        max_history: Максимум сообщений истории (def: 15)
    
    Returns:
        messages array готовый к отправке в LLM
    """
    messages = []
    
    # 1. System prompt (обязательно)
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # 2. История (последние N сообщений)
    # Если истории больше, берём только последние max_history
    if chat_history:
        history_to_send = chat_history[-max_history:]
        messages.extend(history_to_send)
    
    # 3. Текущий запрос
    messages.append({
        "role": "user",
        "content": current_query
    })
    
    return messages


# Альтернатива: если нужна более гибкая настройка
def build_messages_smart_history(
    system_prompt: str,
    chat_history: List[Dict],
    current_query: str,
    max_history_messages: int = 15,
    max_history_tokens: int = 5000,
) -> List[Dict]:
    """
    Собрать messages с обрезкой по количеству сообщений И по токенам.
    """
    from src.utils.token_counter import estimate_tokens
    
    messages = []
    
    # System
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # История с двумя ограничениями: по count и по tokens
    if chat_history:
        total_history_tokens = 0
        history_to_send = []
        
        # Идём от конца (новые сообщения) к началу (старые)
        for msg in reversed(chat_history):
            msg_tokens = estimate_tokens(msg.get("content", ""), model="gpt-3.5-turbo")
            
            # Проверим оба лимита
            if (len(history_to_send) >= max_history_messages or 
                total_history_tokens + msg_tokens > max_history_tokens):
                break
            
            history_to_send.insert(0, msg)
            total_history_tokens += msg_tokens
        
        messages.extend(history_to_send)
    
    # Current query
    messages.append({
        "role": "user",
        "content": current_query
    })
    
    return messages
```

**Интеграция в chat endpoint**
```python
# src/api/routes/chat.py (или эквивалент)
from src.chat.message_builder import build_messages_with_history_limit

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint for chat with history limit.
    """
    # Получить историю из DB/Redis
    chat_history = await get_chat_history(request.session_id)
    
    # Собрать messages с ограничением
    messages = build_messages_with_history_limit(
        system_prompt=SYSTEM_PROMPT,
        chat_history=chat_history,
        current_query=request.query,
        max_history=15,  # Может быть конфиг параметр
    )
    
    # Отправить в LLM (с валидацией из P0.1)
    response = await llm_client.call(messages, model="gpt-4")
    
    # Сохранить в историю
    await save_to_history(
        session_id=request.session_id,
        messages=[
            {"role": "user", "content": request.query},
            {"role": "assistant", "content": response["content"]},
        ]
    )
    
    return response
```

**Тест**
```python
# tests/test_history_limit.py
import pytest
from src.chat.message_builder import build_messages_with_history_limit
from src.utils.token_counter import estimate_messages_tokens

def test_history_limited_to_15_messages():
    """Проверить, что история ограничена 15 сообщениями."""
    # Составить историю из 50 сообщений
    history = [
        {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i}"
        }
        for i in range(50)
    ]
    
    messages = build_messages_with_history_limit(
        system_prompt="You are helpful.",
        chat_history=history,
        current_query="What's new?",
        max_history=15,
    )
    
    # System + last 15 history + current query = 17 messages
    assert len(messages) == 17
    
    # Проверить, что это последние 15
    assert messages[1]["content"] == "Message 35"  # 50-15 = 35
    assert messages[15]["content"] == "Message 49"  # последнее перед query


def test_messages_within_token_budget():
    """Проверить, что входные токены в приемлемом диапазоне."""
    history = [
        {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": "Sample message content " * 100,  # ~500 токенов
        }
        for i in range(30)
    ]
    
    messages = build_messages_with_history_limit(
        system_prompt="System prompt here",
        chat_history=history,
        current_query="Query",
        max_history=15,
    )
    
    tokens = estimate_messages_tokens(messages, model="gpt-3.5-turbo")
    
    # Должно быть примерно 7500 токенов (15 × 500)
    assert tokens < 10_000, f"Too many tokens: {tokens}"
```

#### Acceptance Criteria
- [ ] История ограничена 15 сообщениями по умолчанию (конфиг)
- [ ] История ограничена ~5k токенов (второй уровень защиты)
- [ ] Последние N сообщений выбираются корректно (FIFO удаление старых)
- [ ] Тесты проходят
- [ ] На примере из логов базовый входной уровень упадёт с 18k на 4–6k

#### Успешность
✅ Базовый уровень 17–20k → 4–6k  
✅ Экономия 12–15k токенов за вызов

---

### Задача P0.4: Логировать breakdown входных токенов

**Приоритет:** 🟡 ВАЖНОЕ  
**Estimated Time:** 2–4 часа  
**Owner:** Backend Engineer / DevOps (логирование)  
**Status:** ⏳ Ожидание

#### Описание
Логировать, откуда ровно взялись входные токены: system prompt, история, retrieved context, инструменты, текущий запрос.

Это нужно для диагностики скрытых проблем в будущем.

#### Файлы для изменения
- `src/api/client.py` (добавить логирование breakdown)
- `src/utils/logging_config.py` (настроить логирование в JSON)

#### Реализация

**Функция для подсчёта breakdown**
```python
# src/utils/token_breakdown.py
from typing import List, Dict, Optional
from src.utils.token_counter import estimate_tokens

class TokenBreakdown:
    """Детальный анализ входных токенов по компонентам."""
    
    def __init__(self):
        self.components = {}
    
    def add(self, component_name: str, text: str, model: str = "gpt-3.5-turbo"):
        """Добавить компонент и посчитать его токены."""
        tokens = estimate_tokens(text, model)
        self.components[component_name] = {
            "tokens": tokens,
            "chars": len(text),
        }
    
    def add_messages(self, messages: List[Dict], model: str = "gpt-3.5-turbo"):
        """Добавить сообщения и распределить по ролям."""
        user_tokens = 0
        assistant_tokens = 0
        system_tokens = 0
        
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tokens = estimate_tokens(content, model)
            
            if role == "user":
                user_tokens += tokens
            elif role == "assistant":
                assistant_tokens += tokens
            elif role == "system":
                system_tokens += tokens
        
        if system_tokens > 0:
            self.components["system_prompt"] = {
                "tokens": system_tokens,
                "messages_count": sum(1 for m in messages if m.get("role") == "system"),
            }
        if user_tokens > 0:
            self.components["user_messages"] = {
                "tokens": user_tokens,
                "messages_count": sum(1 for m in messages if m.get("role") == "user"),
            }
        if assistant_tokens > 0:
            self.components["assistant_messages"] = {
                "tokens": assistant_tokens,
                "messages_count": sum(1 for m in messages if m.get("role") == "assistant"),
            }
    
    def total(self) -> int:
        """Общее количество токенов."""
        return sum(c["tokens"] for c in self.components.values())
    
    def to_dict(self) -> Dict:
        """Экспортировать в dict для логирования."""
        return {
            "components": self.components,
            "total": self.total(),
        }
    
    def to_json(self) -> str:
        """Экспортировать в JSON."""
        import json
        return json.dumps(self.to_dict(), indent=2)


# Использование в client
def log_token_breakdown(messages, model, retrieved_context=None, tools=None):
    """Логировать детальный breakdown входных токенов."""
    from src.utils.token_counter import estimate_tokens
    import logging
    
    logger = logging.getLogger(__name__)
    breakdown = TokenBreakdown()
    
    # Анализировать messages
    breakdown.add_messages(messages, model)
    
    # Добавить retrieved context если есть
    if retrieved_context:
        context_text = "\n".join(retrieved_context)
        breakdown.add("retrieved_context", context_text, model)
    
    # Добавить tools descriptions если есть
    if tools:
        tools_text = json.dumps(tools, default=str)
        breakdown.add("tool_descriptions", tools_text, model)
    
    # Логировать
    logger.info(
        "Token Breakdown",
        extra={
            "token_breakdown": breakdown.to_dict(),
            "total_input_tokens": breakdown.total(),
        }
    )
    
    return breakdown
```

**Интеграция в LLM client**
```python
# src/api/client.py
from src.utils.token_breakdown import log_token_breakdown

class LLMClient:
    async def call(self, messages, model, retrieved_context=None, tools=None, **kwargs):
        """Основной метод с логированием breakdown."""
        
        # Логировать breakdown
        breakdown = log_token_breakdown(
            messages,
            model,
            retrieved_context=retrieved_context,
            tools=tools,
        )
        
        # Дальше как в P0.1 и P0.2...
        # ... (валидация, кэш, API call)
```

**Пример логирования**
```json
{
  "timestamp": "2026-04-19T12:00:00Z",
  "level": "INFO",
  "message": "Token Breakdown",
  "token_breakdown": {
    "components": {
      "system_prompt": {
        "tokens": 1200,
        "messages_count": 1
      },
      "user_messages": {
        "tokens": 800,
        "messages_count": 3
      },
      "assistant_messages": {
        "tokens": 4500,
        "messages_count": 3
      },
      "retrieved_context": {
        "tokens": 2100,
        "chars": 8400
      },
      "tool_descriptions": {
        "tokens": 450,
        "chars": 1800
      }
    },
    "total": 9050
  },
  "total_input_tokens": 9050
}
```

#### Acceptance Criteria
- [ ] Каждый LLM call логирует breakdown по компонентам
- [ ] Логирование структурировано (JSON format)
- [ ] Включает system, history (user + assistant), context, tools
- [ ] Логируется на INFO уровне для дальнейшего мониторинга
- [ ] Можно построить график расхода токенов по времени

#### Успешность
✅ Видимость источников раздутия входных токенов  
✅ Основа для следующих оптимизаций

---

### 📊 P0 Summary

| Задача | Time | Эффект | Status |
|---|---|---|---|
| P0.1: Hard limit на входные токены | 2–4h | -83k выброс | ⏳ |
| P0.2: Request deduplication (убрать retry-петлю) | 2–4h | -93k в этот период | ⏳ |
| P0.3: History limit до 15 сообщений | 1–2h | -12–15k за вызов | ⏳ |
| P0.4: Token breakdown логирование | 2–4h | Видимость + диагностика | ⏳ |
| **Итого P0** | **7–14 часов** | **40–50% экономии** | **⏳** |

**Ожидаемый результат после P0:**
- Базовое потребление входных токенов упадёт с 18k на 4–6k
- Максимум будет ограничен 50k
- Retry-петли будут предотвращены
- Полная видимость в логах

---

## P1: Ближайшее время (1–2 недели)

### 🎯 Цель P1
**Оптимизировать архитектуру передачи контекста, внедрить бюджетирование токенов.**

- ✅ Оптимизировать RAG retrieval (top_k, relevance filter)
- ✅ Внедрить budget-aware prompt builder
- ✅ Добавить retrieval compression
- ✅ Провести код ревью на дублирование system prompt
- ✅ Рассмотреть model selection logic

### Задача P1.1: Проверить и оптимизировать RAG retrieval

**Приоритет:** 🔴 КРИТИЧЕСКОЕ (после P0)  
**Estimated Time:** 3–5 дней  
**Owner:** Backend Engineer / ML Engineer (RAG)  
**Status:** ⏳ Ожидание

#### Описание
Оптимизировать параметры RAG retrieval:
1. Снизить `top_k` с текущего значения (предполагаемо 20+) до 3–5
2. Добавить relevance threshold (отбросить scores < 0.5)
3. Обрезать каждый chunk до разумного размера (500–1000 символов)
4. Логировать retrieved_context_tokens

#### Файлы для изменения
- `src/rag/retriever.py` или `src/retrieval/service.py`
- `src/rag/config.py` (RAG параметры)
- `tests/test_rag_optimization.py`

#### Реализация

**Текущее (предполагаемое)**
```python
# ❌ ЧТО МОЖЕТ БЫТЬ НЕПРАВИЛЬНО
def retrieve(query: str, top_k=20):
    # Получить top_k=20 документов
    docs = vector_db.search(query, top_k=20)
    # Вернуть как есть, без обрезки
    return docs
```

**Оптимизированное**
```python
# ✅ ЧТО ДОЛЖНО БЫТЬ
RAG_CONFIG = {
    "top_k": 5,  # Было может 20, теперь 5
    "relevance_threshold": 0.5,  # Отбросить <0.5
    "max_chunk_size": 1000,  # chars
    "max_total_context": 3000,  # tokens
}

def retrieve(
    query: str,
    top_k: int = RAG_CONFIG["top_k"],
    relevance_threshold: float = RAG_CONFIG["relevance_threshold"],
) -> List[Dict]:
    """
    Retrieve with optimization.
    """
    import logging
    from src.utils.token_counter import estimate_tokens
    
    logger = logging.getLogger(__name__)
    
    # 1. Получить документы
    docs = vector_db.search(query, top_k=top_k * 2)  # Overample для фильтра
    
    # 2. Фильтр по relevance score
    filtered_docs = [
        doc for doc in docs
        if doc.get("score", 0) >= relevance_threshold
    ]
    
    # Лимитировать по count
    filtered_docs = filtered_docs[:top_k]
    
    # 3. Обрезать каждый chunk
    for doc in filtered_docs:
        content = doc.get("content", "")
        if len(content) > RAG_CONFIG["max_chunk_size"]:
            doc["content"] = content[:RAG_CONFIG["max_chunk_size"]]
            doc["truncated"] = True
    
    # 4. Контролировать общий размер контекста
    total_tokens = 0
    result = []
    for doc in filtered_docs:
        doc_tokens = estimate_tokens(doc.get("content", ""))
        if total_tokens + doc_tokens > RAG_CONFIG["max_total_context"]:
            logger.warning(
                "Retrieved context exceeds token budget, truncating",
                extra={"total_tokens": total_tokens}
            )
            break
        
        result.append(doc)
        total_tokens += doc_tokens
    
    # 5. Логировать метрики
    context_text = "\n---\n".join(
        doc.get("content", "") for doc in result
    )
    logger.info(
        "Retrieved context",
        extra={
            "query": query,
            "documents_retrieved": len(result),
            "total_tokens": estimate_tokens(context_text),
            "relevance_scores": [doc.get("score") for doc in result],
        }
    )
    
    return result
```

**Конфиг файл**
```python
# src/rag/config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class RAGConfig:
    """Configuration for RAG retrieval."""
    
    # Search parameters
    top_k: int = 5  # Number of documents to retrieve
    relevance_threshold: float = 0.5  # Minimum relevance score (0-1)
    
    # Chunk parameters
    max_chunk_size: int = 1000  # Characters per chunk
    max_total_context: int = 3000  # Total tokens for all retrieved context
    
    # Advanced
    use_reranking: bool = False  # Use cross-encoder for reranking
    reranker_model: Optional[str] = None
    
    @classmethod
    def from_env(cls):
        """Load from environment variables."""
        import os
        return cls(
            top_k=int(os.getenv("RAG_TOP_K", 5)),
            relevance_threshold=float(os.getenv("RAG_THRESHOLD", 0.5)),
            max_chunk_size=int(os.getenv("RAG_CHUNK_SIZE", 1000)),
            max_total_context=int(os.getenv("RAG_MAX_CONTEXT", 3000)),
        )

# Использование
rag_config = RAGConfig.from_env()
```

**Тест**
```python
# tests/test_rag_optimization.py
import pytest
from src.rag.retriever import retrieve
from src.rag.config import RAGConfig
from src.utils.token_counter import estimate_tokens

def test_retrieval_respects_top_k():
    """Проверить, что retrieved docs <= top_k."""
    docs = retrieve("test query", top_k=5)
    assert len(docs) <= 5

def test_relevance_threshold_filtering():
    """Проверить фильтрацию по score."""
    docs = retrieve("test query", relevance_threshold=0.5)
    
    for doc in docs:
        assert doc.get("score", 0) >= 0.5

def test_chunk_size_limited():
    """Проверить, что chunks не больше max_chunk_size."""
    config = RAGConfig(max_chunk_size=1000)
    docs = retrieve("test query")
    
    for doc in docs:
        content = doc.get("content", "")
        assert len(content) <= config.max_chunk_size

def test_total_context_tokens_limited():
    """Проверить общий лимит токенов."""
    config = RAGConfig(max_total_context=3000)
    docs = retrieve("test query")
    
    total_content = "\n".join(doc.get("content", "") for doc in docs)
    total_tokens = estimate_tokens(total_content)
    
    assert total_tokens <= config.max_total_context
```

#### Acceptance Criteria
- [ ] `top_k` = 5 (или меньше)
- [ ] Relevance score filter = 0.5 minimum
- [ ] Каждый chunk ≤ 1000 символов
- [ ] Общий контекст ≤ 3000 токенов
- [ ] Логируется количество retrieved документов и total tokens
- [ ] Тесты проходят

#### Успешность
✅ RAG контекст снизится с ~10k на 3k токенов  
✅ Убрать нерелевантные результаты, улучшить качество

---

### Задача P1.2: Провести код ревью на дублирование system prompt

**Приоритет:** 🟡 ВАЖНОЕ  
**Estimated Time:** 4–6 часов (+ возможные исправления)  
**Owner:** Backend Engineer (code review)  
**Status:** ⏳ Ожидание

#### Описание
Найти и убрать дублирование system prompt и служебных инструкций в коде.

#### Файлы для проверки
- `src/prompts/` (все файлы)
- `src/api/client.py` (сборка messages)
- `src/chat/message_builder.py`
- `src/agent/` (если есть agent)
- `src/tools/` (tool descriptions)

#### Чеклист ревью

```markdown
## Code Review Checklist: System Prompt Duplication

### 1. System Prompt
- [ ] System prompt передаётся один раз в messages array
- [ ] System prompt не дублируется перед/после контекста
- [ ] System prompt не передаётся на каждой итерации agent loop
- [ ] System prompt не включается в tool outputs

### 2. Tool Descriptions
- [ ] Tool descriptions передаются один раз
- [ ] Не повторяются на каждый tool call
- [ ] Не дублируются в системе и в инструкциях

### 3. Instructions / Guidelines
- [ ] Инструкции для модели передаются один раз
- [ ] Не повторяются в разных секциях prompt'а
- [ ] Нет одних и тех же пояснений в разных местах

### 4. Metadata / Markers
- [ ] Служебные маркеры ("--- START ---", "--- END ---") используются минимально
- [ ] Нет излишних разделителей между секциями
- [ ] JSON структурирование предпочтительнее free text маркеров

### 5. Agent Loops (если есть)
- [ ] System prompt не переопределяется на каждой итерации
- [ ] Tool outputs не дублируют инструкции
- [ ] Final messages assembly не повторяет уже присутствующее

### 6. Multi-step Pipelines
- [ ] Каждый stage не передаёт наследованный system prompt
- [ ] Нет склейки промежуточных results с дублированием инструкций

### 7. Overall
- [ ] Total system prompt + instructions ≤ 2000 tokens
- [ ] Каждый новый вызов не передаёт одно и то же дважды
- [ ] Логирование покрывает все случаи дублирования
```

#### Инструменты для поиска

```bash
# Найти все вхождения системного prompt
grep -r "You are" src/ --include="*.py"

# Найти дублирование tool descriptions
grep -r "tools:" src/ --include="*.py" | head -20

# Найти все вхождения служебных маркеров
grep -r "---" src/ --include="*.py"

# Посчитать количество "system" role в codebase
grep -r '"role": "system"' src/ --include="*.py" | wc -l
```

#### Пример: после ревью

**Найденное дублирование (гипотетическое):**
```python
# ❌ БЫЛО НЕПРАВИЛЬНО
messages = [
    {"role": "system", "content": "You are helpful. ..."},  # Система 1
    {"role": "system", "content": "Additional instructions: ..."},  # Система 2
    {"role": "user", "content": query},
]

# Или в agent:
for iteration in range(max_iterations):
    messages = [
        {"role": "system", "content": system_prompt},  # Повторяется
        ...last_messages,
        {"role": "user", "content": tool_output},
    ]
```

**Исправление:**
```python
# ✅ ПРАВИЛЬНО
messages = [
    {
        "role": "system",
        "content": f"{base_instructions}\n\n{additional_instructions}"  # Один раз
    },
    {"role": "user", "content": query},
]

# В agent:
messages = [{"role": "system", "content": system_prompt}]  # Один раз

for iteration in range(max_iterations):
    # Добавить только новые messages, system уже есть
    messages.extend([
        {"role": "user", "content": tool_output},
        # ... next step
    ])
```

#### Acceptance Criteria
- [ ] Код ревью завершён
- [ ] Все вхождения system prompt задокументированы
- [ ] Дублирование найдено (если есть)
- [ ] Исправления сделаны (если требуются)
- [ ] Total system prompt ≤ 2000 tokens
- [ ] Логирование добавлено для контроля в будущем

#### Успешность
✅ Снижение system prompt с 2–3k на 1–1.5k токенов (если было дублирование)  
✅ Профилактика против регрессии в будущем

---

### Задача P1.3: Внедрить budget-aware prompt builder

**Приоритет:** 🟡 ВАЖНОЕ  
**Estimated Time:** 3–4 дня  
**Owner:** Backend Engineer  
**Status:** ⏳ Ожидание

#### Описание
Создать класс/функцию, которая собирает prompt с явным бюджетированием токенов.

Гарантирует, что:
1. System prompt получает выделенный бюджет (1500 токенов)
2. Retrieved context получает выделенный бюджет (3000 токенов)
3. History получает оставшейся бюджет (5000 токенов)
4. Query + tools получают минимум 500 токенов
5. Итого ≤ 15000 входных токенов

#### Файлы
- `src/prompts/budget_builder.py` (новый)
- `tests/test_budget_builder.py` (тест)

#### Реализация

```python
# src/prompts/budget_builder.py
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class TokenBudget:
    """Token budget для각 компонента prompt."""
    system_prompt: int = 1500
    retrieved_context: int = 3000
    chat_history: int = 5000
    query_and_tools: int = 1000
    buffer: int = 1000
    
    @property
    def total(self) -> int:
        return (
            self.system_prompt
            + self.retrieved_context
            + self.chat_history
            + self.query_and_tools
            + self.buffer
        )
    
    def set_total_budget(self, total: int):
        """Распределить бюджет пропорционально при изменении total."""
        ratio = total / self.total
        self.system_prompt = int(self.system_prompt * ratio * 0.1)
        self.retrieved_context = int(self.retrieved_context * ratio * 0.2)
        self.chat_history = int(self.chat_history * ratio * 0.45)
        self.query_and_tools = int(self.query_and_tools * ratio * 0.15)
        self.buffer = int(self.buffer * ratio * 0.1)


class BudgetAwarePromptBuilder:
    """
    Собирает prompt с контролем над расходом токенов.
    """
    
    def __init__(self, max_input_tokens: int = 15_000):
        self.max_input = max_input_tokens
        self.budget = TokenBudget()
        self.budget.set_total_budget(max_input_tokens)
    
    def build(
        self,
        system_prompt: str,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        retrieved_context: Optional[List[str]] = None,
        tools_definitions: Optional[str] = None,
    ) -> List[Dict]:
        """
        Собрать messages array с контролем бюджета.
        
        Args:
            system_prompt: Системный prompt
            query: Текущий пользовательский запрос
            chat_history: История (messages array)
            retrieved_context: Список документов из RAG
            tools_definitions: Описание tools в JSON
        
        Returns:
            messages array готовый к отправке в LLM
        """
        from src.utils.token_counter import estimate_tokens
        
        messages = []
        total_tokens = 0
        
        # 1. System prompt (обязательно, fixed budget)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt[:self.budget.system_prompt * 4]  # Примерно
            })
            system_tokens = estimate_tokens(system_prompt)
            total_tokens += system_tokens
            
            if system_tokens > self.budget.system_prompt:
                logger.warning(
                    f"System prompt exceeds budget: {system_tokens} > {self.budget.system_prompt}"
                )
        
        # 2. Tools definitions (if provided)
        tools_tokens = 0
        if tools_definitions:
            messages.append({
                "role": "system",
                "content": f"Available tools:\n{tools_definitions}"
            })
            tools_tokens = estimate_tokens(tools_definitions)
            total_tokens += tools_tokens
        
        # 3. Retrieved context (обрезать по бюджету)
        if retrieved_context:
            context_budget = self.budget.retrieved_context
            context_text = self._build_context(retrieved_context, context_budget)
            
            if context_text:
                messages.append({
                    "role": "system",
                    "content": f"Context:\n{context_text}"
                })
                context_tokens = estimate_tokens(context_text)
                total_tokens += context_tokens
        
        # 4. Chat history (обрезать по оставшемуся бюджету)
        if chat_history:
            remaining_budget = (
                self.max_input
                - total_tokens
                - estimate_tokens(query)
                - self.budget.buffer
            )
            trimmed_history = self._trim_history(
                chat_history,
                remaining_budget
            )
            messages.extend(trimmed_history)
            history_tokens = sum(
                estimate_tokens(msg.get("content", ""))
                for msg in trimmed_history
            )
            total_tokens += history_tokens
        
        # 5. Current query (обязательно)
        messages.append({
            "role": "user",
            "content": query
        })
        query_tokens = estimate_tokens(query)
        total_tokens += query_tokens
        
        # 6. Логировать результат
        logger.info(
            "Prompt built with budget control",
            extra={
                "total_input_tokens": total_tokens,
                "messages_count": len(messages),
                "budget_remaining": self.max_input - total_tokens,
                "breakdown": {
                    "system": system_tokens,
                    "context": context_tokens if retrieved_context else 0,
                    "history": history_tokens if chat_history else 0,
                    "query": query_tokens,
                    "tools": tools_tokens,
                }
            }
        )
        
        return messages
    
    def _build_context(self, documents: List[str], budget: int) -> str:
        """Собрать context с контролем размера."""
        from src.utils.token_counter import estimate_tokens
        
        context_parts = []
        current_tokens = 0
        
        for doc in documents:
            doc_tokens = estimate_tokens(doc)
            if current_tokens + doc_tokens > budget:
                logger.debug(f"Context truncated at {len(context_parts)} docs")
                break
            
            context_parts.append(doc)
            current_tokens += doc_tokens
        
        return "\n---\n".join(context_parts)
    
    def _trim_history(self, messages: List[Dict], budget: int) -> List[Dict]:
        """Обрезать историю по бюджету токенов."""
        from src.utils.token_counter import estimate_tokens
        
        result = []
        current_tokens = 0
        
        # Идти от конца (новые) к началу (старые)
        for msg in reversed(messages):
            msg_tokens = estimate_tokens(msg.get("content", ""))
            
            if current_tokens + msg_tokens > budget:
                logger.debug(f"History trimmed from {len(messages)} to {len(result)} messages")
                break
            
            result.insert(0, msg)
            current_tokens += msg_tokens
        
        return result


# Использование
def get_prompt_builder(max_tokens: int = 15_000) -> BudgetAwarePromptBuilder:
    return BudgetAwarePromptBuilder(max_tokens)
```

**Пример использования:**
```python
# В chat endpoint
builder = get_prompt_builder(max_tokens=15_000)

messages = builder.build(
    system_prompt="You are a helpful assistant...",
    query="What is the capital of France?",
    chat_history=chat_history,  # Будет автоматически обрезано
    retrieved_context=retrieved_docs,  # Будет контролироваться
    tools_definitions=tools_json,
)

response = await llm_client.call(messages, model="gpt-4")
```

**Тест:**
```python
# tests/test_budget_builder.py
import pytest
from src.prompts.budget_builder import BudgetAwarePromptBuilder
from src.utils.token_counter import estimate_messages_tokens

def test_builder_respects_max_budget():
    """Проверить, что builder не превышает max_input."""
    builder = BudgetAwarePromptBuilder(max_input_tokens=10_000)
    
    # Составить большие inputs
    system = "You are helpful " * 100
    query = "Test query" * 100
    history = [
        {
            "role": "user",
            "content": "Long message " * 500,
        } for _ in range(10)
    ]
    
    messages = builder.build(
        system_prompt=system,
        query=query,
        chat_history=history,
    )
    
    tokens = estimate_messages_tokens(messages, model="gpt-3.5-turbo")
    assert tokens <= 10_000, f"Exceeded budget: {tokens} > 10000"

def test_builder_preserves_critical_content():
    """Проверить, что не обрезается важное содержимое."""
    builder = BudgetAwarePromptBuilder(max_input_tokens=5_000)
    
    system = "You are helpful."
    query = "What is 2+2?"
    
    messages = builder.build(
        system_prompt=system,
        query=query,
    )
    
    # Query должен быть в messages
    assert any("2+2" in msg.get("content", "") for msg in messages)
```

#### Acceptance Criteria
- [ ] Builder собирает messages с явным бюджетированием
- [ ] Никогда не превышает max_input_tokens
- [ ] Логирует breakdown по компонентам
- [ ] Примеры документированы
- [ ] Тесты проходят

#### Успешность
✅ Гарантированная защита от перегрузки входных токенов  
✅ Предсказуемое распределение токенов по компонентам

---

### Задача P1.4: Внедрить retrieval compression

**Приоритет:** 🟢 ЖЕЛАТЕЛЬНОЕ  
**Estimated Time:** 2–3 дня (если нужна abstractive compression)  
**Owner:** ML Engineer или Backend Engineer  
**Status:** ⏳ Ожидание

#### Описание
Если retrieved context занимает >2000 токенов, сжать его перед вставкой в prompt.

Варианты:
1. **Extractive:** выбрать топ-1 по relevance
2. **Extractive:** выбрать top sentences из каждого doc
3. **Abstractive:** использовать LLM для summarization (дороже)

Рекомендация: начать с **extractive** (простая, быстрая).

#### Файлы
- `src/rag/compression.py` (новый)
- `src/prompts/budget_builder.py` (интегрировать)

#### Реализация (extractive)

```python
# src/rag/compression.py
from typing import List, Optional
from src.utils.token_counter import estimate_tokens
import logging

logger = logging.getLogger(__name__)

class RetrievalCompressor:
    """Compress retrieved context to fit token budget."""
    
    @staticmethod
    def compress_extractive(
        documents: List[str],
        target_tokens: int = 2000,
        keep_top_sentences: int = 3,
    ) -> List[str]:
        """
        Extractive compression: keep only top sentences from each doc.
        
        Args:
            documents: List of full documents
            target_tokens: Target token count
            keep_top_sentences: Sentences to keep per document
        
        Returns:
            Compressed documents
        """
        import re
        
        compressed = []
        current_tokens = 0
        
        for doc in documents:
            # Split на sentences (простой regex)
            sentences = re.split(r'[.!?]+', doc)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Взять первые N sentences
            condensed = ". ".join(sentences[:keep_top_sentences])
            doc_tokens = estimate_tokens(condensed)
            
            if current_tokens + doc_tokens > target_tokens:
                break
            
            compressed.append(condensed)
            current_tokens += doc_tokens
        
        logger.info(
            "Retrieved context compressed (extractive)",
            extra={
                "original_docs": len(documents),
                "compressed_docs": len(compressed),
                "original_tokens": sum(estimate_tokens(d) for d in documents),
                "compressed_tokens": current_tokens,
            }
        )
        
        return compressed
    
    @staticmethod
    async def compress_abstractive(
        documents: List[str],
        target_tokens: int = 2000,
        llm_client = None,  # Optional LLM client for summarization
    ) -> List[str]:
        """
        Abstractive compression: summarize each doc using LLM.
        More expensive, but better quality.
        """
        if not llm_client:
            logger.warning("LLM client not provided, falling back to extractive")
            return RetrievalCompressor.compress_extractive(documents, target_tokens)
        
        compressed = []
        tokens_per_doc = target_tokens // len(documents)
        
        for doc in documents:
            # Summarize using LLM
            summary_prompt = f"""Summarize the following text in {tokens_per_doc // 4} sentences:

{doc}

Summary:"""
            
            summary = await llm_client.call(
                messages=[
                    {
                        "role": "user",
                        "content": summary_prompt,
                    }
                ],
                model="gpt-3.5-turbo",  # Дешевле для summarization
                max_tokens=tokens_per_doc,
            )
            
            compressed.append(summary.get("content"))
        
        return compressed
```

**Интеграция в prompt builder:**
```python
# В BudgetAwarePromptBuilder._build_context()
def _build_context(self, documents: List[str], budget: int) -> str:
    """Собрать context с опциональной compression."""
    from src.utils.token_counter import estimate_tokens
    from src.rag.compression import RetrievalCompressor
    
    total_doc_tokens = sum(estimate_tokens(doc) for doc in documents)
    
    # Если слишком большой, сжать
    if total_doc_tokens > budget * 1.2:  # 20% над бюджетом
        logger.info(
            f"Context too large ({total_doc_tokens} > {budget}), compressing...",
            extra={"original_tokens": total_doc_tokens}
        )
        documents = RetrievalCompressor.compress_extractive(
            documents,
            target_tokens=budget,
        )
    
    context_parts = []
    current_tokens = 0
    
    for doc in documents:
        doc_tokens = estimate_tokens(doc)
        if current_tokens + doc_tokens > budget:
            break
        context_parts.append(doc)
        current_tokens += doc_tokens
    
    return "\n---\n".join(context_parts)
```

#### Acceptance Criteria
- [ ] Extraction compression работает и снижает размер на 30–40%
- [ ] Логируется original vs compressed размер
- [ ] Abstractive compression (optional) имеет fallback
- [ ] Тесты проходят

#### Успешность
✅ Retrieved context можно сжать с 5–10k на 2–3k токенов  
✅ Улучшение качества за счёт удаления noise

---

### 📊 P1 Summary

| Задача | Time | Эффект | Dependencies |
|---|---|---|---|
| P1.1: RAG optimization | 3–5 days | -3–5k tokens | P0.4 (logging) |
| P1.2: System prompt code review | 4–6 hours | -2–5k tokens (if duplication) | — |
| P1.3: Budget-aware builder | 3–4 days | +guarantee no overload | P0.1 (limits) |
| P1.4: Retrieval compression | 2–3 days | -2–3k tokens | P1.1 (RAG) |
| **Итого P1** | **10–18 дней** | **Дополнительно -10–15k** | **После P0** |

**Ожидаемый результат после P0 + P1:**
- Базовое потребление 4–6k токенов
- Максимум 15k в нормальных условиях
- Полная видимость и контроль расходов
- Масштабируемая архитектура для роста

---

## P2: Архитектурные меры (3–4 недели)

### 🎯 Цель P2
**Переструктурировать архитектуру для масштабируемого контекстного управления.**

### Задача P2.1: Разделить orchestration и final generation

**Приоритет:** 🟡 ЖЕЛАТЕЛЬНОЕ  
**Estimated Time:** 1–2 недели  
**Owner:** Backend Architect + Engineer  
**Status:** ⏳ Ожидание

#### Суть
Вместо одного массивного prompt со всем контекстом, разделить на этапы:
- **Stage 1 (Lightweight):** Routing/классификация (какой путь дальше?)
- **Stage 2 (Reasoning):** Основная логика с полным контекстом
- **Stage 3 (Generation):** Финальный ответ с минимальным контекстом

#### Пример

**До:**
```python
# ❌ Один большой prompt со всем
messages = [
    {"role": "system", "content": system + context + tools},  # 12k токенов
    {"role": "user", "content": query},
]
response = await llm_client.call(messages)  # 12k каждый раз
```

**После:**
```python
# ✅ Три этапа

# Stage 1: Routing (2k tokens)
route_messages = [
    {"role": "system", "content": "Classify the user request"},
    {"role": "user", "content": query},
]
route = await llm_client.call(route_messages)  # 2k

# Stage 2: Processing (10k tokens, если нужно)
if route == "needs_context":
    process_messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": f"Answer based on context: {query}"},
    ]
    result = await llm_client.call(process_messages)  # 10k
else:
    result = query  # Direct answer

# Stage 3: Generation (3k tokens)
final_messages = [
    {"role": "user", "content": f"Format answer: {result}"},
]
response = await llm_client.call(final_messages)  # 3k

# Total: 2k + (10k or 0) + 3k = 5–15k (instead of always 12k)
```

**Ожидаемый эффект:**
- Экономия на simple queries (только stage 1 + 3)
- Масштабируемость для сложных запросов
- Лучше контроль над контекстом на каждом этапе

**Результат:** Среднее потребление может упасть на 30–40%

---

### Задача P2.2: Ввести prompt contracts

**Приоритет:** 🟡 ЖЕЛАТЕЛЬНОЕ  
**Estimated Time:** 2–3 дня  
**Owner:** Backend Engineer  
**Status:** ⏳ Ожидание

#### Суть
Явно задать, какой максимум токенов может использовать каждый компонент.

#### Реализация

```python
# src/prompts/contracts.py
from dataclasses import dataclass

@dataclass
class PromptContract:
    """Контракт для prompt構築."""
    name: str
    max_system_tokens: int = 1500
    max_context_tokens: int = 3000
    max_history_tokens: int = 5000
    max_query_tokens: int = 1000
    max_total_tokens: int = 15000
    
    def validate(self, actual: dict) -> bool:
        """Проверить, соответствует ли актуальное использование контракту."""
        assert (
            actual["system"] <= self.max_system_tokens
        ), f"System tokens exceed: {actual['system']} > {self.max_system_tokens}"
        
        assert (
            actual["context"] <= self.max_context_tokens
        ), f"Context tokens exceed: {actual['context']} > {self.max_context_tokens}"
        
        assert (
            actual["total"] <= self.max_total_tokens
        ), f"Total tokens exceed: {actual['total']} > {self.max_total_tokens}"
        
        return True

# Примеры контрактов
SIMPLE_QUERY_CONTRACT = PromptContract(
    name="simple_query",
    max_system_tokens=800,
    max_context_tokens=1000,
    max_history_tokens=2000,
    max_total_tokens=5000,
)

COMPLEX_REASONING_CONTRACT = PromptContract(
    name="complex_reasoning",
    max_system_tokens=1500,
    max_context_tokens=5000,
    max_history_tokens=5000,
    max_total_tokens=15000,
)
```

**Использование:**
```python
contract = select_contract(query)  # simple_query или complex_reasoning
messages = builder.build(..., contract=contract)
contract.validate(token_breakdown)
```

---

### Задача P2.3: Хранить краткую state summary вместо полной истории

**Приоритет:** 🟡 ЖЕЛАТЕЛЬНОЕ  
**Estimated Time:** 3–4 дня  
**Owner:** Backend Engineer  
**Status:** ⏳ Ожидание

#### Суть
Для длинных диалогов, вместо хранения всех сообщений, хранить:
1. Краткую summary (что обсуждали)
2. Важные факты (ключевые точки)
3. Последние N сообщений (для контекста)

#### Реализация

```python
# src/chat/state_manager.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChatState:
    """Компактное представление состояния диалога."""
    session_id: str
    summary: str  # "User is building a TODO app. They prefer dark mode."
    key_facts: List[str]  # ["User location: NYC", "Using React.js"]
    last_n_messages: List[Dict]  # Последние 5 сообщений для контекста
    
    def to_prompt_context(self) -> str:
        """Преобразовать в текст для prompt."""
        context = f"Chat Summary: {self.summary}\n\n"
        
        if self.key_facts:
            context += "Key Facts:\n"
            for fact in self.key_facts:
                context += f"- {fact}\n"
        
        return context

class StateManager:
    """Управление состоянием диалога."""
    
    async def get_state(self, session_id: str) -> ChatState:
        """Получить текущее состояние."""
        # Загрузить из DB
        ...
    
    async def update_state(
        self,
        session_id: str,
        new_messages: List[Dict],
    ):
        """Обновить состояние с новыми сообщениями."""
        # Получить текущее состояние
        state = await self.get_state(session_id)
        
        # Если много сообщений, summarize старые
        if len(state.last_n_messages) > 20:
            old_messages = state.last_n_messages[:-5]
            new_summary = await self._summarize_messages(old_messages)
            state.summary += f" {new_summary}"
            state.last_n_messages = state.last_n_messages[-5:] + new_messages
        else:
            state.last_n_messages.extend(new_messages)
        
        # Обновить факты
        state.key_facts = await self._extract_key_facts(new_messages)
        
        # Сохранить
        await self._save_state(session_id, state)
    
    async def _summarize_messages(self, messages: List[Dict]) -> str:
        """Summarize сообщения используя LLM."""
        prompt = f"""Summarize the following conversation in 1-2 sentences:

{chr(10).join(msg['content'] for msg in messages)}

Summary:"""
        
        summary = await llm_client.call(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-3.5-turbo",
        )
        
        return summary
    
    async def _extract_key_facts(self, messages: List[Dict]) -> List[str]:
        """Extract important facts from messages."""
        # Использовать simpler extraction или regex
        # ...
        ...
```

---

### 📊 P2 Summary

| Задача | Time | Эффект | Status |
|---|---|---|---|
| P2.1: Orchestration stages | 1–2w | -30–40% на simple queries | ⏳ |
| P2.2: Prompt contracts | 2–3d | Гарантия контроля | ⏳ |
| P2.3: State summary | 3–4d | Масштабируемость | ⏳ |
| **Итого P2** | **2–3 недели** | **70–75% общая экономия** | **⏳** |

---

## Контрольные точки

### Milestone 1: P0 Завершено (End of Day 1–2)

**Проверка:**
```bash
# Запустить на реальных логах
python scripts/test_token_limits.py

# Ожидаемые результаты:
# - 83041 токенов → blocked or trimmed to 50k
# - 46901 x3 retry → deduplicated to 1 call
# - Базовый 18k → упал на 30–40%
```

**Metrics:**
- ✅ Все P0 задачи завершены
- ✅ Нет hard errors в логах
- ✅ Token breakdown логируется для каждого вызова
- ✅ Baseline input tokens < 15k

### Milestone 2: P1 Завершено (End of Week 2–3)

**Проверка:**
```bash
python scripts/analyze_token_usage.py --period week

# Ожидаемые результаты:
# - RAG context <= 3000 tokens
# - No duplication in system prompt
# - Budget builder используется везде
# - Input tokens baseline 6–8k
```

**Metrics:**
- ✅ Все P1 задачи завершены
- ✅ Budget контролируется явно
- ✅ Retrieval сжимается автоматически
- ✅ Стоимость упала на 45–50%

### Milestone 3: P2 Завершено (End of Week 4)

**Проверка:**
```bash
python scripts/full_optimization_report.py

# Ожидаемые результаты:
# - Orchestration stages работают
# - Prompt contracts соблюдаются
# - State summary для длинных диалогов
# - Input tokens baseline 4–6k
```

**Metrics:**
- ✅ Все P2 задачи завершены
- ✅ Архитектура масштабируемая
- ✅ Стоимость упала на 60–70%
- ✅ Качество не пострадал (A/B тест)

---

## Риски и зависимости

### Риски

| Риск | Вероятность | Влияние | Mitigation |
|---|---|---|---|
| Качество ответов упадёт из-за обрезки контекста | Средняя | Высокое | A/B тестирование, метрики качества |
| Мониторинг не покажет регрессию | Низкая | Высокое | Comprehensive logging, алерты |
| Кэш будет неправильно работать (false hits) | Низкая | Среднее | Unit tests, cache invalidation |
| RAG будет давать пустые результаты | Низкая | Среднее | Fallback к полным документам |
| Думающие модели будут работать хуже на обрезанном контексте | Средняя | Среднее | A/B тест, мониторинг |

### Зависимости

```
P0.1, P0.2, P0.3, P0.4 (Параллельно, независимо)
         ↓
    (Day 1–2)
         ↓
P1.1 RAG Optimization ← зависит от P0.4
P1.2 Code Review (Independent)
P1.3 Budget Builder ← зависит от P0.1, P0.4
P1.4 Retrieval Compression ← зависит от P1.1
         ↓
    (Week 2–3)
         ↓
P2.1, P2.2, P2.3 (Архитектурные, после основы)
         ↓
    (Week 3–4)
```

---

## FAQ и troubleshooting

### Q: Что если обрезание истории приведёт к потере контекста?
**A:** 
1. Начать с 15 сообщений, мониторить качество
2. Если качество упадёт, увеличить до 20–25
3. Для важных фактов использовать state summary (P2.3)
4. Имеет fallback на full history если нужно

### Q: Что если RAG будет давать нерелевантные результаты после снижения top_k?
**A:**
1. Проверить relevance threshold (не 0.5, может 0.6–0.7)
2. Добавить reranking (cross-encoder)
3. Если очень плохо, можно оставить top_k=7–10 для сложных queries
4. Мониторить quality metrics

### Q: Может ли request deduplication скрыть реальные ошибки?
**A:**
1. Cache TTL = 10 секунд, не вечный
2. Логировать каждый cache hit
3. Если ошибка persistent, retry на другой модели
4. Дедупликация только для идентичных payload

### Q: Что если hard limit будет блокировать необходимые запросы?
**A:**
1. Начать с 50k, потом потенциально повысить на 70k
2. Иметь override для особых случаев (с логированием)
3. Использовать budget builder для trim перед hard limit
4. Мониторить blocked requests

### Q: Как тестировать эти изменения без production?
**A:**
1. Unit тесты для каждого компонента
2. Integration тесты на синтетических данных
3. Staging environment с реальными логами
4. Canary deployment (10% трафика) перед полным rollout
5. A/B тест на качество (LLM evals)

### Q: Сколько времени займёт полная оптимизация?
**A:**
- **P0 (критическое):** 1–2 дня, даёт 40–50% экономии
- **P1 (среднесрочное):** 1–3 недели, даёт ещё 10–15%
- **P2 (архитектура):** 2–4 недели, даёт ещё 10–15%
- **Итого:** ~1 месяц для 60–70% экономии

---

## Приложение: Скрипты для анализа и мониторинга

### Скрипт 1: Анализ текущего состояния

```python
# scripts/analyze_token_usage.py
import json
from datetime import datetime, timedelta
import asyncio

async def main():
    # Загрузить логи за последний день
    logs = await get_logs_from_db(days=1)
    
    stats = {
        "total_calls": len(logs),
        "avg_input_tokens": 0,
        "max_input_tokens": 0,
        "p95_input_tokens": 0,
        "calls_above_15k": 0,
        "calls_above_30k": 0,
        "retries": 0,
        "errors": 0,
    }
    
    input_tokens = []
    for log in logs:
        tokens = log.get("input_tokens", 0)
        input_tokens.append(tokens)
        
        if tokens > 30000:
            stats["calls_above_30k"] += 1
        elif tokens > 15000:
            stats["calls_above_15k"] += 1
        
        if log.get("status") == "retry":
            stats["retries"] += 1
        elif log.get("status") == "error":
            stats["errors"] += 1
    
    input_tokens.sort()
    stats["avg_input_tokens"] = sum(input_tokens) / len(input_tokens)
    stats["max_input_tokens"] = max(input_tokens)
    stats["p95_input_tokens"] = input_tokens[int(len(input_tokens) * 0.95)]
    
    print(json.dumps(stats, indent=2))
    
    # Рекомендации
    if stats["avg_input_tokens"] > 15000:
        print("⚠️  RECOMMENDED: P0 optimization")
    elif stats["avg_input_tokens"] > 10000:
        print("⚠️  RECOMMENDED: P1 optimization")
    else:
        print("✅ Within acceptable range")

if __name__ == "__main__":
    asyncio.run(main())
```

### Скрипт 2: Проверка качества после оптимизации

```python
# scripts/check_quality_regression.py
import asyncio

async def compare_responses(query: str):
    """
    Сравнить ответы от оптимизированной и базовой версии.
    """
    # Версия 1: With full context (baseline)
    baseline_response = await call_baseline(query)
    
    # Версия 2: With optimized context
    optimized_response = await call_optimized(query)
    
    # Compare using LLM evals
    similarity = await eval_similarity(baseline_response, optimized_response)
    quality = await eval_quality(optimized_response)
    
    print(f"Query: {query}")
    print(f"Similarity: {similarity:.2%}")
    print(f"Quality: {quality:.2%}")
    print(f"Cost Reduction: {(1 - optimized_cost/baseline_cost):.2%}")
    
    return {
        "similarity": similarity,
        "quality": quality,
        "cost_reduction": cost_reduction,
    }

async def run_evals():
    """Run A/B test on ~100 queries."""
    test_queries = [...]  # Load from test set
    
    results = []
    for query in test_queries:
        result = await compare_responses(query)
        results.append(result)
    
    avg_similarity = sum(r["similarity"] for r in results) / len(results)
    avg_quality = sum(r["quality"] for r in results) / len(results)
    avg_cost_reduction = sum(r["cost_reduction"] for r in results) / len(results)
    
    print(f"\n=== SUMMARY ===")
    print(f"Avg Similarity: {avg_similarity:.2%} (target: >95%)")
    print(f"Avg Quality: {avg_quality:.2%} (target: >98%)")
    print(f"Cost Reduction: {avg_cost_reduction:.2%}")
    
    if avg_similarity > 0.95 and avg_quality > 0.98:
        print("✅ Optimization is safe to deploy!")
    else:
        print("❌ Need to adjust optimization parameters")

if __name__ == "__main__":
    asyncio.run(run_evals())
```

---

## P3: Токены агента разработки (Cursor AI)

**Тип:** Отдельная проблема — не runtime приложения, а development workflow.  
**Дата анализа:** 2026-04-19  
**Источник:** Анализ шаблонов промтов `doc/agent_workflow.md`

Шаблоны Planning Prompt и Architecture Review включают файлы целиком, что даёт 20–40k+ токенов на один agent-вызов Cursor AI.

### Файлы-нарушители (>5k токенов, включаются без предобработки)

| Файл | ~Токены | Промт | Проблема |
|---|---:|---|---|
| `doc/closed_iterations.md` | **17 254** | Planning | Читается целиком; промт говорит "last epoch only", агент игнорирует |
| `app/prompts.py` | **7 897** | ArchReview | Для проверки hardcoded prompts нужен grep, не Read |
| `app/knowledge_graph.py` | **5 553** | ArchReview | Нужны только signatures и imports |
| `app/query_service.py` | **5 111** | Planning + ArchReview | Крупнейший модуль; нужен только контракт |
| `doc/adr.md` | **5 069** | ArchReview Phase 3 | Весь журнал; достаточно summary-таблицы |

### Файлы 2k–5k токенов без ограничения в промте

`doc/cjm.md` (3 084), `app/tutor_orchestrator.py` (2 957), `app/learner_model_service.py` (2 890), `app/learning_plan_service.py` (2 654), `doc/architecture.md` (2 582), `app/config.py` (2 080).

### План устранения (приоритет по ROI)

| # | Действие | Эффект | Сложность |
|---|---|---|---|
| P3.0 | Разбить `doc/closed_iterations.md` по эпохам → `doc/epochs/e<N>.md`; в Planning Prompt ссылаться только на нужный файл | −15k токенов на Planning-вызов | Средняя |
| P3.1 | В ArchReview Phase 1: заменить Read `app/prompts.py` на `grep -n "^prompt\|^PROMPT" app/**/*.py \| grep -v prompts.py` | −8k токенов на ArchReview | Низкая (правка промта) |
| P3.2 | В ArchReview/Planning: крупные модули читать только signatures: `grep -n "^def \|^class " <file>` | −9k токенов | Низкая (правка промта) |
| P3.3 | В `doc/adr.md` добавить summary-таблицу статусов в начало; промт читает только её | −3k токенов | Низкая |
| P3.4 | В Planning Prompt: `doc/cjm.md` — добавить `section for target stage only` | −2k токенов | Низкая (правка промта) |
| P3.5 | Разбить `app/query_service.py` (1499 строк) — снижает стоимость и Planning, и ArchReview | −5k + структурная выгода | Высокая |

**Суммарный потенциал по P3.0–P3.4:** ~37k → 3–5k токенов на Planning-вызов (−85%).

---

## История версий плана

| Версия | Дата | Изменения |
|---|---|---|
| 1.0 | 2026-04-19 | Первоначальный план на основе анализа логов |
| 1.1 | 2026-04-19 | Добавлен P3: токены агента разработки (Cursor AI / agent_workflow шаблоны) |

---

**Документ готов к использованию. Начните с P0 сегодня.**

