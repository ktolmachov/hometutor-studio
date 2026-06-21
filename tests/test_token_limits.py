"""Tests for token counting and validation utilities (P0.1)."""

from __future__ import annotations

import pytest
from app.token_utils import (
    estimate_tokens,
    estimate_messages_tokens,
    TokenValidator,
)


class TestEstimateTokens:
    """Tests for token estimation functions."""

    def test_estimate_tokens_empty_string(self):
        """Empty string should return 0 tokens."""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_short_text(self):
        """Short text should return reasonable token count."""
        text = "Hello, world!"
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < 20  # Should be a few tokens

    def test_estimate_tokens_long_text(self):
        """Long text should scale with length."""
        short = "Hello world"
        long = short * 100

        short_tokens = estimate_tokens(short)
        long_tokens = estimate_tokens(long)

        # Longer text should have significantly more tokens
        assert long_tokens > short_tokens
        assert long_tokens > short_tokens * 50  # At least 50x more

    def test_estimate_tokens_different_models(self):
        """Different models may have different token estimates."""
        text = "This is a test string for token estimation."

        tokens_gpt4 = estimate_tokens(text, model="gpt-4o")
        tokens_gpt35 = estimate_tokens(text, model="gpt-3.5-turbo")

        # Both should return positive numbers
        assert tokens_gpt4 > 0
        assert tokens_gpt35 > 0


class TestEstimateMessagesTokens:
    """Tests for messages array token estimation."""

    def test_empty_messages(self):
        """Empty messages array should return 0 tokens."""
        assert estimate_messages_tokens([]) == 0

    def test_single_message(self):
        """Single message should be counted correctly."""
        messages = [
            {
                "role": "user",
                "content": "Hello, assistant!",
            }
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0
        # Should include message overhead + content
        assert tokens >= 4

    def test_messages_count(self):
        """Multiple messages should accumulate tokens."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello! How can I help?"},
            {"role": "user", "content": "Tell me a joke"},
        ]
        tokens = estimate_messages_tokens(messages)

        # Each message has ~4 tokens overhead + content
        # Total should be at least 4 * 4 + some content
        assert tokens >= 20

    def test_message_overhead(self):
        """Messages should include per-message overhead."""
        msg_with_empty = [{"role": "user", "content": ""}]
        msg_with_content = [{"role": "user", "content": "Hello"}]

        tokens_empty = estimate_messages_tokens(msg_with_empty)
        tokens_with = estimate_messages_tokens(msg_with_content)

        # Content should add tokens
        assert tokens_with > tokens_empty


class TestTokenValidator:
    """Tests for TokenValidator class."""

    def test_validate_normal_messages(self):
        """Normal-sized messages should pass validation."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "What is 2+2?"},
        ]

        validated, tokens = TokenValidator.validate_and_trim(messages)

        assert len(validated) == len(messages)
        assert tokens > 0
        assert tokens < TokenValidator.HARD_LIMIT_INPUT

    def test_validate_large_messages_raises_error(self):
        """Messages exceeding hard limit should raise ValueError."""
        # Create a message that will exceed hard limit
        large_content = "x" * 500_000  # ~125k tokens

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": large_content},
        ]

        with pytest.raises(ValueError, match="Input size too large"):
            TokenValidator.validate_and_trim(messages)

    def test_auto_trim_large_history(self):
        """Auto-trim should work without raising error for large history."""
        # Create messages with significant size
        messages = [
            {"role": "system", "content": "You are helpful."},
        ]

        # Add messages to create substantial history
        for i in range(30):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({
                "role": role,
                "content": f"Message {i}: " + "x" * 1000,  # ~250 tokens each
            })

        # Should validate without raising error
        # (might trim or not depending on total tokens)
        validated, tokens = TokenValidator.validate_and_trim(
            messages,
            auto_trim=True,
        )

        # Should still be valid after validation
        assert len(validated) > 0
        assert validated[0]["role"] == "system"
        assert tokens <= TokenValidator.HARD_LIMIT_INPUT

    def test_auto_trim_disabled(self):
        """When auto_trim=False, should not trim."""
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "x" * 5_000},
        ]

        validated, tokens = TokenValidator.validate_and_trim(
            messages,
            auto_trim=False,
        )

        # Without auto-trim, messages might not be trimmed
        # (but won't exceed hard limit)
        assert tokens <= TokenValidator.HARD_LIMIT_INPUT

    def test_trim_messages_preserves_system(self):
        """Trimming should preserve system message."""
        messages = [
            {"role": "system", "content": "SYSTEM_PROMPT_MARKER"},
            {"role": "user", "content": "x" * 1_000},
            {"role": "assistant", "content": "y" * 1_000},
            {"role": "user", "content": "z" * 1_000},
        ]

        trimmed = TokenValidator._trim_messages(messages, model="gpt-4o")

        # System message should be first
        assert trimmed[0]["role"] == "system"
        assert "SYSTEM_PROMPT_MARKER" in trimmed[0]["content"]

    def test_trim_messages_keeps_recent(self):
        """Trimming should keep more recent messages."""
        messages = [
            {"role": "system", "content": "System"},
        ]

        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({
                "role": role,
                "content": f"MARKER_{i}",
            })

        trimmed = TokenValidator._trim_messages(messages, model="gpt-4o")

        # Should keep recent messages
        trimmed_content = [m["content"] for m in trimmed]
        # More recent markers should be present
        assert any("MARKER_1" in content for content in trimmed_content)

    def test_hard_limit_constant(self):
        """Hard limit should be 50k."""
        assert TokenValidator.HARD_LIMIT_INPUT == 50_000

    def test_soft_limit_constant(self):
        """Soft limit should be 30k."""
        assert TokenValidator.SOFT_LIMIT_INPUT == 30_000

    def test_trim_threshold_constant(self):
        """Trim threshold should be 25k."""
        assert TokenValidator.TRIM_THRESHOLD == 25_000


class TestIntegration:
    """Integration tests."""

    def test_realistic_conversation(self):
        """Test realistic conversation flow."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful educational assistant.",
            },
            {
                "role": "user",
                "content": "What are the main topics in calculus?",
            },
            {
                "role": "assistant",
                "content": "Calculus covers limits, derivatives, and integrals.",
            },
            {
                "role": "user",
                "content": "Can you explain limits?",
            },
        ]

        validated, tokens = TokenValidator.validate_and_trim(messages)

        # Should pass validation
        assert len(validated) == len(messages)
        assert tokens > 0
        assert tokens < TokenValidator.SOFT_LIMIT_INPUT

    def test_token_growth_with_history(self):
        """Token count should grow as history grows."""
        messages_1 = [
            {"role": "user", "content": "Hi"},
        ]

        messages_2 = messages_1 + [
            {"role": "assistant", "content": "Hello!"},
        ]

        tokens_1 = estimate_messages_tokens(messages_1)
        tokens_2 = estimate_messages_tokens(messages_2)

        assert tokens_2 > tokens_1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
