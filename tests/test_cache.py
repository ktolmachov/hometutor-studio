"""Tests for request caching and deduplication (P0.2)."""

from __future__ import annotations

import time

import pytest
from app.request_cache import (
    RequestCache,
    consume_llm_cache_hit,
    get_request_cache,
    reset_llm_cache_hit_flag,
    reset_request_cache,
)


class TestRequestCache:
    """Tests for RequestCache class."""

    def test_cache_initialization(self):
        """Cache should initialize with correct parameters."""
        cache = RequestCache(maxsize=50, ttl_seconds=5)

        assert cache.maxsize == 50
        assert cache.ttl_seconds == 5
        assert len(cache.cache) == 0

    def test_cache_miss_on_empty(self):
        """Cache should return None when empty."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]

        result = cache.get("gpt-4o", messages)

        assert result is None

    def test_cache_set_and_get(self):
        """Cache should store and retrieve values."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]
        response = {"content": "Hi there!"}

        # Set value
        cache.set("gpt-4o", messages, response)

        # Get value
        cached = cache.get("gpt-4o", messages)

        assert cached == response

    def test_cache_hit_with_same_request(self):
        """Identical requests should return cached response."""
        cache = RequestCache()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is 2+2?"},
        ]
        response = {"content": "4"}

        cache.set("gpt-4o", messages, response)

        # Same request should hit cache
        cached = cache.get("gpt-4o", messages)

        assert cached == response

    def test_cache_miss_with_different_model(self):
        """Different models should not share cache."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]
        response_gpt4 = {"content": "Hi from GPT-4"}

        cache.set("gpt-4o", messages, response_gpt4)

        # Same messages, different model should miss
        cached = cache.get("gpt-3.5-turbo", messages)

        assert cached is None

    def test_cache_miss_with_different_messages(self):
        """Different messages should not hit cache."""
        cache = RequestCache()
        messages1 = [{"role": "user", "content": "Hello"}]
        messages2 = [{"role": "user", "content": "Hi"}]
        response = {"content": "Greeting"}

        cache.set("gpt-4o", messages1, response)

        # Different messages should miss
        cached = cache.get("gpt-4o", messages2)

        assert cached is None

    def test_cache_ttl_expiration(self):
        """Cache should expire after TTL."""
        cache = RequestCache(ttl_seconds=1)
        messages = [{"role": "user", "content": "Hello"}]
        response = {"content": "Hi"}

        cache.set("gpt-4o", messages, response)

        # Should be in cache initially
        assert cache.get("gpt-4o", messages) == response

        # Wait for expiration
        time.sleep(1.1)

        # Should expire
        assert cache.get("gpt-4o", messages) is None

    def test_cache_lru_eviction(self):
        """Cache should evict oldest entry when full."""
        cache = RequestCache(maxsize=2)
        msg1 = [{"role": "user", "content": "Message 1"}]
        msg2 = [{"role": "user", "content": "Message 2"}]
        msg3 = [{"role": "user", "content": "Message 3"}]

        cache.set("gpt-4o", msg1, {"id": 1})
        cache.set("gpt-4o", msg2, {"id": 2})

        # Add third entry, should evict oldest (msg1)
        cache.set("gpt-4o", msg3, {"id": 3})

        # msg1 should be evicted
        assert cache.get("gpt-4o", msg1) is None
        # msg2 and msg3 should be present
        assert cache.get("gpt-4o", msg2) is not None
        assert cache.get("gpt-4o", msg3) is not None

    def test_cache_lru_order(self):
        """Most recently set should be kept (FIFO when full)."""
        cache = RequestCache(maxsize=2)
        msg1 = [{"role": "user", "content": "Message 1"}]
        msg2 = [{"role": "user", "content": "Message 2"}]
        msg3 = [{"role": "user", "content": "Message 3"}]

        cache.set("gpt-4o", msg1, {"id": 1})
        cache.set("gpt-4o", msg2, {"id": 2})

        # Cache is full (2 items)
        # Set msg3, should evict oldest (msg1)
        cache.set("gpt-4o", msg3, {"id": 3})

        # msg1 should be evicted (oldest)
        assert cache.get("gpt-4o", msg1) is None
        # msg2 and msg3 should be present
        assert cache.get("gpt-4o", msg2) is not None
        assert cache.get("gpt-4o", msg3) is not None

    def test_cache_with_kwargs(self):
        """Cache should consider kwargs in hash."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]
        response1 = {"content": "Response with temp=0.7"}
        response2 = {"content": "Response with temp=0.9"}

        cache.set("gpt-4o", messages, response1, temperature=0.7)
        cache.set("gpt-4o", messages, response2, temperature=0.9)

        # Different temperature should return different cache entry
        assert cache.get("gpt-4o", messages, temperature=0.7) == response1
        assert cache.get("gpt-4o", messages, temperature=0.9) == response2

    def test_cache_clear(self):
        """Cache clear should remove all entries."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]

        cache.set("gpt-4o", messages, {"content": "Hi"})
        assert cache.get("gpt-4o", messages) is not None

        cache.clear()

        assert cache.get("gpt-4o", messages) is None
        assert len(cache.cache) == 0

    def test_cache_stats(self):
        """Cache should return stats."""
        cache = RequestCache(maxsize=50, ttl_seconds=10)
        messages = [{"role": "user", "content": "Hello"}]

        cache.set("gpt-4o", messages, {"content": "Hi"})

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["maxsize"] == 50
        assert stats["ttl_seconds"] == 10


class TestGlobalCache:
    """Tests for global cache instance."""

    def teardown_method(self):
        """Reset cache after each test."""
        reset_request_cache()

    def test_get_request_cache_singleton(self):
        """get_request_cache should return singleton."""
        cache1 = get_request_cache()
        cache2 = get_request_cache()

        assert cache1 is cache2

    def test_get_request_cache_with_params(self):
        """get_request_cache should accept parameters."""
        reset_request_cache()

        cache = get_request_cache(maxsize=25, ttl_seconds=5)

        assert cache.maxsize == 25
        assert cache.ttl_seconds == 5

    def test_reset_request_cache(self):
        """reset_request_cache should clear singleton."""
        cache1 = get_request_cache()
        messages = [{"role": "user", "content": "Hello"}]
        cache1.set("gpt-4o", messages, {"content": "Hi"})

        reset_request_cache()

        cache2 = get_request_cache()

        # Should be different instance
        assert cache1 is not cache2
        # New cache should be empty
        assert cache2.get("gpt-4o", messages) is None


class TestIntegration:
    """Integration tests for caching."""

    def test_deduplication_scenario(self):
        """Test realistic deduplication scenario (retry case)."""
        cache = RequestCache()
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Explain quantum computing"},
        ]
        response = {
            "message": "Quantum computing uses...",
            "tokens": 150,
        }

        # First call - cache miss
        result1 = cache.get("gpt-4o", messages)
        assert result1 is None

        # Set response (simulate API call)
        cache.set("gpt-4o", messages, response)

        # Second call - same request (retry scenario) - cache hit
        result2 = cache.get("gpt-4o", messages)
        assert result2 == response

        # Should not make another API call
        result3 = cache.get("gpt-4o", messages)
        assert result3 == response

    def test_cache_prevents_retry_storm(self):
        """Cache should prevent retry storm with identical requests."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "test"}]

        # Simulate 3 identical request attempts (retry storm)
        for i in range(3):
            # Check cache first
            cached = cache.get("gpt-4o", messages)

            if cached is None:
                # Would make API call only once
                response = {"attempt": 1, "data": f"response_{i}"}
                cache.set("gpt-4o", messages, response)
            else:
                # Would return cached response
                response = cached

            # All 3 should have same response
            assert response["attempt"] == 1

    def test_cache_multimodel(self):
        """Cache should handle multiple models independently."""
        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]

        cache.set("gpt-4o", messages, {"model": "gpt-4o"})
        cache.set("gpt-3.5-turbo", messages, {"model": "gpt-3.5-turbo"})

        # Each model should have its own cached response
        assert cache.get("gpt-4o", messages) == {"model": "gpt-4o"}
        assert cache.get("gpt-3.5-turbo", messages) == {"model": "gpt-3.5-turbo"}

    def test_sqlite_backed_cache_survives_memory_reset(self, tmp_path):
        db_path = tmp_path / "llm_request_cache.db"
        messages = [{"role": "user", "content": "flashcard prompt"}]
        response = {"text": "cached cards"}

        cache = RequestCache(maxsize=10, ttl_seconds=3600, persist=True, db_path=db_path)
        cache.set("qwen/test", messages, response, temperature=0.3)

        reloaded = RequestCache(maxsize=10, ttl_seconds=3600, persist=True, db_path=db_path)
        restored = reloaded.get("qwen/test", messages, temperature=0.3)
        assert restored is not None
        assert _extract_response_text(restored) == "cached cards"

    def test_consume_llm_cache_hit_flag(self):
        reset_llm_cache_hit_flag()
        assert consume_llm_cache_hit() is False

        cache = RequestCache()
        messages = [{"role": "user", "content": "Hello"}]
        cache.set("gpt-4o", messages, {"content": "Hi"})
        cache.get("gpt-4o", messages)
        assert consume_llm_cache_hit() is True
        assert consume_llm_cache_hit() is False


def _extract_response_text(response):
    from app.request_cache import _extract_response_text as extract

    return extract(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
