#!/usr/bin/env python3
"""Verify that all performance fixes are properly implemented in the codebase."""

import sys
from pathlib import Path

def check_file_contains(filepath: Path, patterns: list[str], description: str) -> bool:
    """Check if file contains all required patterns."""
    if not filepath.exists():
        print(f"  [FAIL] File not found: {filepath}")
        return False

    content = filepath.read_text(encoding="utf-8")
    missing = []

    for pattern in patterns:
        if pattern not in content:
            missing.append(pattern)

    if missing:
        print(f"  [FAIL] {description}")
        for pattern in missing:
            print(f"     Missing: {pattern[:60]}...")
        return False

    print(f"  [PASS] {description}")
    return True

def main():
    root = Path(__file__).parent
    results = []

    print("=" * 70)
    print("VERIFYING PERFORMANCE FIXES")
    print("=" * 70)

    # Fix #1: BM25 cache warmup aligned to profile
    print("\n[Fix #1] BM25 Cache Warmup Aligned to Profile")
    results.append(check_file_contains(
        root / "app" / "api.py",
        [
            'r_settings = get_retrieval_settings()',
            'profile = (r_settings.rag_profile or "fast").strip().lower() or "fast"',
            'if profile == "fast":',
            'top_k = min(r_settings.similarity_top_k, 2)',
            'get_bm25_retriever(collection, similarity_top_k=top_k, filters=None)',
        ],
        "Warmup uses profile-specific top_k"
    ))

    # Fix #2: Multi-variant BM25 cache
    print("\n[Fix #2] Multi-Variant BM25 Cache Architecture")
    results.append(check_file_contains(
        root / "app" / "hybrid_retrieval.py",
        [
            '_cached_bm25_retrievers: dict[int, BM25Retriever] = {}',
            'if similarity_top_k in _cached_bm25_retrievers:',
            '_cached_bm25_retrievers[similarity_top_k] = retriever',
            '_cached_bm25_retrievers.clear()',
        ],
        "Cache stores multiple top_k values"
    ))

    # Fix #3: Token reduction (top_k=2 for fast)
    print("\n[Fix #3] Token Reduction (top_k=2 for Fast Profile)")
    results.append(check_file_contains(
        root / "app" / "pipeline_factory.py",
        [
            'if profile == "fast":',
            '"similarity_top_k": min(r.similarity_top_k, 2),',
        ],
        "Fast profile uses min(top_k, 2)"
    ))

    # Fix #4: Local Gemma 4B LLM
    print("\n[Fix #4] Local Gemma 4B Configuration")
    results.append(check_file_contains(
        root / ".env",
        [
            'LLM_MODEL=google/gemma-4-e4b',
            'OPENAI_API_BASE=http://127.0.0.1:1234/api/v1',
        ],
        ".env configured for local Gemma 4B"
    ))

    # Fix #5: Mastery dashboard caching
    print("\n[Fix #5] Mastery Dashboard Caching")
    results.append(check_file_contains(
        root / "app" / "ui" / "home_hub.py",
        [
            '@st.cache_data',
            'ttl=30',
            'def _fetch_mastery_dashboard',
        ],
        "Mastery dashboard fetch is cached with 30s TTL"
    ))

    # Fix #6: Bootstrap warmup threads
    print("\n[Fix #6] Bootstrap Warmup Threads")
    results.append(check_file_contains(
        root / "app" / "api.py",
        [
            'def _bm25_warmup_background',
            'def _catalog_warmup_background',
            'def _readiness_warmup_background',
            'def _index_stats_warmup_background',
            'target=_bm25_warmup_background',
            'target=_catalog_warmup_background',
            'daemon=True',
        ],
        "Warmup daemon threads are spawned"
    ))

    # Bonus: Quality documentation
    print("\n[Bonus] Quality Assessment Documentation")
    results.append(check_file_contains(
        root / "doc" / "gemma4b_quality_assessment.md",
        [
            'Quality Monitoring Plan',
            'Source Hit Rate',
            'Expected with Gemma 4B',
        ],
        "Quality assessment guide exists"
    ))

    results.append(check_file_contains(
        root / "doc" / "gemma4b_test_checklist.md",
        [
            'Quick Tests',
            'Red Flags to Watch For',
            'Success Criteria',
        ],
        "Testing checklist guide exists"
    ))

    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"[PASS] ALL FIXES VERIFIED ({passed}/{total})")
        print("\nAll performance optimizations are properly implemented!")
        print("\nNext steps:")
        print("  1. Start LM Studio with Gemma 4B model")
        print("  2. Run: python main.py")
        print("  3. Follow TESTING_FIXES.md for manual verification")
        return 0
    else:
        print(f"[FAIL] SOME FIXES MISSING ({passed}/{total})")
        print("\nCheck the errors above and re-run after fixing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
