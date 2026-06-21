import random

import pytest

from app.log_masking_policy import (
    MaskingSink,
    assert_sink_payload_clean,
    contains_unmasked_pii,
    describe_sink_policy,
    get_sink_masked_fields,
    list_sink_policies,
    redact_for_sink,
    redact_sink_payload,
    should_mask_field,
)

PII_SAMPLES = [
    ("email", "contact@test.example.com"),
    ("phone", "+7 999 123-45-67"),
    ("openai_key", "sk-abcdefghijklmnop"),
    ("generic_secret", "api_key=supersecret123"),
]


def test_list_sink_policies_covers_all_sinks():
    policies = list_sink_policies()
    assert {row["sink"] for row in policies} == {sink.value for sink in MaskingSink}
    for row in policies:
        assert row["masked_fields"]
        assert row["redactor"] == "guardrails.redact_sensitive_text"


def test_should_mask_field_respects_sink_field_map():
    assert should_mask_field(MaskingSink.OTEL_TRACE, "input")
    assert not should_mask_field(MaskingSink.OTEL_TRACE, "trace_id")


@pytest.mark.parametrize("sink", list(MaskingSink))
@pytest.mark.parametrize("pii_kind,pii_value", PII_SAMPLES)
def test_redact_sink_payload_removes_pii_from_masked_fields(sink, pii_kind, pii_value):
    payload = {
        "question": f"please email {pii_value}",
        "trace_id": "trace-ok",
    }
    cleaned = redact_sink_payload(sink, payload)
    assert pii_value not in cleaned.get("question", "")
    assert cleaned["trace_id"] == "trace-ok"
    assert_sink_payload_clean(sink, cleaned)


@pytest.mark.parametrize("sink", list(MaskingSink))
def test_redact_for_sink_on_nested_metadata(sink):
    nested = {"user": "user@example.com", "note": "token: abcdefgh"}
    out = redact_for_sink(sink, "metadata", nested)
    if should_mask_field(sink, "metadata"):
        assert "user@example.com" not in str(out)
        assert "abcdefgh" not in str(out)
    else:
        assert out == nested


def test_contains_unmasked_pii_detects_leaks():
    assert contains_unmasked_pii("mail me at user@example.com")
    assert not contains_unmasked_pii("[REDACTED_EMAIL]")


def test_property_random_embedded_pii_never_survives_masked_fields():
    rng = random.Random(42)
    for _ in range(40):
        pii_value = rng.choice(PII_SAMPLES)[1]
        for sink in MaskingSink:
            for field in get_sink_masked_fields(sink):
                text = f"prefix-{rng.randint(0, 999)}-{pii_value}-suffix"
                redacted = redact_for_sink(sink, field, text)
                assert pii_value not in str(redacted)


def test_describe_sink_policy_is_stable():
    policy = describe_sink_policy(MaskingSink.LANGFUSE_EXPORT)
    assert policy["sink"] == "langfuse_export"
    assert "input" in policy["masked_fields"]
