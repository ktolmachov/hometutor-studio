"""Unit tests for prompt smoke heuristics."""

from __future__ import annotations

import json
from pathlib import Path

from app.prompt_smoke_checks import evaluate_prompt_smoke_expect


def test_expect_min_and_any_of():
    ok, d = evaluate_prompt_smoke_expect(
        "В тексте есть маркер RAG_ALPHA_UNIQUE_7741 для проверки.",
        {"min_answer_chars": 10, "any_of_substrings": ["RAG_ALPHA", "7741"]},
    )
    assert ok is True
    assert d.get("any_of_substrings") is True


def test_expect_forbidden():
    ok, d = evaluate_prompt_smoke_expect("Ответ без кода", {"forbidden_substrings": ["```"]})
    assert ok is True
    ok2, _ = evaluate_prompt_smoke_expect("```python\nx\n```", {"forbidden_substrings": ["```"]})
    assert ok2 is False


def test_expect_sources_and_debug_keys():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ с источником и debug.",
        {
            "min_answer_chars": 10,
            "min_source_count": 1,
            "required_debug_keys": ["total_answer_ms", "token_usage"],
        },
        sources=[{"id": "doc1"}],
        debug={"total_answer_ms": 12.3, "token_usage": {"total": {"total_tokens": 9}}},
    )
    assert ok is True
    assert d["min_source_count"] is True
    assert d["required_debug_keys"]["total_answer_ms"] is True


def test_debug_gates_fail_closed_when_required_fields_are_missing():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {
            "require_no_fallback": True,
            "require_model": "qwen/qwen3.6-27b",
            "max_reasoning_tokens": 0,
        },
        debug={},
    )

    assert ok is False
    assert d["require_no_fallback"] is False
    assert d["require_no_fallback_missing"] is True
    assert d["require_model"] is False
    assert d["llm_model_actual"] is None
    assert d["max_reasoning_tokens"] is False
    assert d["reasoning_tokens_missing"] is True


def test_debug_gates_pass_with_local_model_no_fallback_and_no_reasoning():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {
            "require_no_fallback": True,
            "require_model": "qwen/qwen3.6-27b",
            "max_reasoning_tokens": 0,
        },
        debug={
            "fallback_used": False,
            "llm_model": "qwen/qwen3.6-27b",
            "token_usage": {"reasoning_tokens": 0},
        },
    )

    assert ok is True
    assert d["require_no_fallback"] is True
    assert d["require_model"] is True
    assert d["max_reasoning_tokens"] is True


def test_debug_gates_accept_model_allowlist_and_missing_reasoning_when_explicit():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {
            "require_no_fallback": True,
            "require_model": ["qwen/qwen3.6-27b", "qwopus3.6-35b-a3b-v1-mtp"],
            "max_reasoning_tokens": 0,
            "allow_missing_reasoning_tokens": True,
        },
        debug={
            "fallback_used": False,
            "llm_model": "qwopus3.6-35b-a3b-v1-mtp",
            "token_usage": {"total": {"prompt_tokens": 1}},
        },
    )

    assert ok is True
    assert d["require_model"] is True
    assert d["llm_model_allowed"] == ["qwen/qwen3.6-27b", "qwopus3.6-35b-a3b-v1-mtp"]
    assert d["max_reasoning_tokens"] is True
    assert d["reasoning_tokens_missing_allowed"] is True


def test_expect_max_answer_chars():
    ok, d = evaluate_prompt_smoke_expect("short", {"max_answer_chars": 10})
    assert ok is True
    assert d["max_answer_chars"] is True
    ok2, d2 = evaluate_prompt_smoke_expect("x" * 11, {"max_answer_chars": 10})
    assert ok2 is False
    assert d2["max_answer_chars"] is False


def test_expect_default_nonempty():
    ok, d = evaluate_prompt_smoke_expect("x" * 12, None)
    assert ok is True
    assert d["length"] == 12


def test_prompt_smoke_cases_json_schema():
    root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / "eval_data" / "prompt_smoke_cases.json").read_text(encoding="utf-8"))
    cases = raw.get("cases") or []
    assert len(cases) >= 10
    for c in cases:
        assert c.get("id")
        assert c.get("question")
        assert (c.get("query_mode") or "qa") in ("qa", "tutor")
        expect = c.get("expect") or {}
        assert "min_answer_chars" in expect


def test_require_system_user_gate_passes_for_tutor_contract():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"require_system_user": True},
        debug={
            "prompt_role_contract": {
                "format": "system_user",
                "reason": "Tutor RAG v2 ChatPromptTemplate (SYSTEM + USER)",
            }
        },
    )
    assert ok is True
    assert d["require_system_user"] is True


def test_require_system_user_gate_fails_when_contract_missing():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"require_system_user": True},
        debug={},
    )
    assert ok is False
    assert d["require_system_user"] is False
    assert d["require_system_user_missing"] is True


def test_length_text_overrides_length_gates_but_not_substrings():
    # Видимый ответ длинный (скаффолд), модельный текст короткий: длина по length_text.
    visible = "### Кратко\n" + "x" * 200 + "\n### Надёжность\nмаркер MARKER_42"
    ok, d = evaluate_prompt_smoke_expect(
        visible,
        {"max_answer_chars": 50, "any_of_substrings": ["MARKER_42"]},
        length_text="короткий текст",
    )
    assert ok is True
    assert d["max_answer_chars"] is True
    assert d["any_of_substrings"] is True  # подстроки ищутся в полном видимом ответе
    assert d["length"] == len("короткий текст")
    assert d["answer_chars"] == len(visible.strip())

    ok2, d2 = evaluate_prompt_smoke_expect(
        visible,
        {"max_answer_chars": 50},
        length_text="y" * 51,
    )
    assert ok2 is False
    assert d2["max_answer_chars"] is False


def test_require_system_user_wire_roles_gate():
    contract_dbg = {
        "prompt_role_contract": {"format": "system_user", "reason": "test"},
    }
    # Роли с провода соответствуют контракту.
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"require_system_user": True},
        debug={**contract_dbg, "chat_message_roles": [["system", "user"]]},
    )
    assert ok is True
    assert d["require_system_user_wire"] is True

    # Generation ушёл user-only — контракт реестра верный, но провод его нарушил.
    ok2, d2 = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"require_system_user": True},
        debug={**contract_dbg, "chat_message_roles": [["user"]]},
    )
    assert ok2 is False
    assert d2["require_system_user_wire"] is False

    # Ролей нет (другой провайдер/нет записи) — решает только контракт реестра.
    ok3, d3 = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"require_system_user": True},
        debug=contract_dbg,
    )
    assert ok3 is True
    assert "require_system_user_wire" not in d3


def test_allow_user_only_stage_resolves_from_registry():
    ok, d = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"allow_user_only_stage": "quiz.inline.followup"},
        debug={},
    )
    assert ok is True
    assert d["allow_user_only_stage"] is True
    assert d["llm_stage_role_contract"]["format"] == "user_only"

    ok2, d2 = evaluate_prompt_smoke_expect(
        "Ответ.",
        {"allow_user_only_stage": "not_in_allowlist_stage"},
        debug={},
    )
    assert ok2 is False
    assert d2["allow_user_only_stage"] is False


def test_usage_cost_generation_message_roles_roundtrip():
    from app.usage_cost import (
        begin_llm_generation_token_accumulation,
        consume_llm_generation_message_roles,
        record_llm_chat_message_roles,
    )

    # Без открытого window запись игнорируется.
    consume_llm_generation_message_roles()
    record_llm_chat_message_roles(["system", "user"])
    assert consume_llm_generation_message_roles() is None

    begin_llm_generation_token_accumulation()
    record_llm_chat_message_roles(["system", "user"])
    record_llm_chat_message_roles(["user"])
    assert consume_llm_generation_message_roles() == [["system", "user"], ["user"]]
    # Window закрыт после consume.
    assert consume_llm_generation_message_roles() is None


def test_homework_prompt_uses_system_and_user_roles():
    from llama_index.core.base.llms.types import MessageRole

    from app.prompts import format_chat_prompt_text, get_homework_prompt, get_prompt_role_contract

    tpl = get_homework_prompt("hint")
    msgs = tpl.format_messages(context_str="ctx", query_str="q")
    assert len(msgs) == 2
    assert msgs[0].role == MessageRole.SYSTEM
    assert msgs[1].role == MessageRole.USER
    rendered = format_chat_prompt_text(tpl, context_str="ctx", query_str="q")
    assert "ctx" in rendered and "q" in rendered
    assert get_prompt_role_contract("homework")["format"] == "system_user"


def test_build_quiz_micro_chat_messages_uses_system_and_user_roles():
    from llama_index.core.base.llms.types import MessageRole

    from app.prompts import build_quiz_micro_chat_messages

    msgs = build_quiz_micro_chat_messages(
        mode_block="",
        topic="RAG",
        mastery_level="intermediate",
        difficulty_band="medium",
        hints="—",
    )
    assert len(msgs) == 2
    assert msgs[0].role == MessageRole.SYSTEM
    assert msgs[1].role == MessageRole.USER
    assert "JSON" in msgs[0].content
    assert "RAG" in msgs[1].content
