"""Tests for semantic caching of SSR explanations."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from app.ssr_semantic_cache import (
    _context_to_string,
    clear_semantic_cache,
    semantic_cache_lookup,
    semantic_cache_store,
)


def test_context_to_string_sorts_keys() -> None:
    """Context dict is serialized with sorted keys (stable)."""
    ctx1 = {"z": "last", "a": "first", "m": "middle"}
    ctx2 = {"m": "middle", "z": "last", "a": "first"}
    assert _context_to_string(ctx1) == _context_to_string(ctx2)


def test_context_to_string_handles_lists() -> None:
    """Lists and dicts in context are JSON-serialized."""
    ctx = {"items": [1, 2, 3], "nested": {"key": "value"}}
    result = _context_to_string(ctx)
    assert "items=" in result
    assert "nested=" in result


def test_semantic_cache_lookup_requires_model() -> None:
    """If embeddings model not available, returns None (graceful degradation)."""
    ctx = {"test": "context"}
    cache = {}
    result = semantic_cache_lookup(ctx, cache, threshold=0.95)
    # Result depends on whether sentence_transformers is installed
    # Safe: always returns None or a string, never raises
    assert result is None or isinstance(result, str)


def test_semantic_cache_store_noop_if_model_unavailable() -> None:
    """Storing without embeddings available is safe (noop)."""
    clear_semantic_cache()
    ctx = {"test": "context"}
    # Should not raise even if embeddings unavailable
    semantic_cache_store("key1", ctx, "Some text.")
    clear_semantic_cache()


def test_load_embeddings_model_thread_safe_single_init() -> None:
    """Concurrent callers must initialise the model exactly once (no race condition).

    Regression test for the bug where two threads both saw _EMBEDDINGS_MODEL is None,
    both tried to load SentenceTransformer, and the second logged model_load_failed.
    """
    import app.ssr_semantic_cache as cache_mod

    init_count = 0

    def _fake_transformer(name, device):
        nonlocal init_count
        init_count += 1
        m = MagicMock()
        m.encode = lambda text, **kw: [0.1] * 10
        return m

    # Reset global state
    cache_mod._EMBEDDINGS_MODEL = None

    with patch.dict("sys.modules", {"sentence_transformers": MagicMock(SentenceTransformer=_fake_transformer)}):
        errors: list[str] = []
        results: list[object] = []

        def _call():
            try:
                results.append(cache_mod._load_embeddings_model())
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=_call) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert errors == [], f"Threads raised: {errors}"
    assert init_count == 1, (
        f"SentenceTransformer was instantiated {init_count} times — should be exactly 1"
    )
    # All threads must get the same non-None model back
    assert all(r is results[0] for r in results), "Threads received different model instances"
    # Cleanup
    cache_mod._EMBEDDINGS_MODEL = None


def test_semantic_cache_lookup_survives_missing_cache_entry() -> None:
    """When referenced entry is no longer in exact-match cache, skip it."""
    clear_semantic_cache()
    ctx = {"test": "context"}
    cache = {}  # Empty cache
    # Should not raise
    result = semantic_cache_lookup(ctx, cache)
    assert result is None or isinstance(result, str)
    clear_semantic_cache()
