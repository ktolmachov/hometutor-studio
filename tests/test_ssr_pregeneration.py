"""Tests for background SSR explanation pre-generation."""
from __future__ import annotations

import time

import pytest

from app.smart_study_router import build_smart_study_recommendation
from app.ssr_pregeneration import trigger_ssr_pregeneration_async


@pytest.fixture()
def rec():
    return build_smart_study_recommendation(surface="home", flashcard_due_n=1)


def test_pregeneration_noop_timeout(rec) -> None:
    """Trigger with short timeout — should not raise, even if it times out."""
    # Just verify it doesn't raise
    trigger_ssr_pregeneration_async(rec, timeout_sec=0.01)
    time.sleep(0.1)


def test_pregeneration_noop_with_no_llm(rec) -> None:
    """Pre-generation with no LLM available — should not raise."""
    # This test verifies graceful degradation; actual LLM call may fail
    # but the async wrapper should not propagate the error
    trigger_ssr_pregeneration_async(rec, weak_concept="test", timeout_sec=2.0)
