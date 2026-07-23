"""Pure, importable budget/guard logic shared by relay, simulator and gate.

No env reads here — thresholds are injected. No I/O, no side effects.
`scripts/kilo_proxy_relay.py` and `scripts/kilo_budget_simulate.py` both call
`evaluate_guard()` so runtime and static-analysis verdicts can never drift.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


DEFAULT_PREVIEW_CHARS = 800

RISK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("doc\\\\backlog_registry.yaml", "full backlog registry injected"),
    ("generate_plan_next_prompt.md", "planning prompt injected"),
    ("generate_orchestration_prompt.md", "orchestration prompt injected"),
    ("closed_iterations.md", "closed iterations injected"),
    ("current_task.payload.md", "current task payload injected"),
    ("Zero-Click Delivery Pipeline", "zero-click workflow task injected"),
    ("<available_skills>", "full available_skills block injected"),
    ('"type":"function"', "tool schemas injected"),
    ("kilo_local_recall", "session recall tool schema injected"),
)

WORKFLOW_COMBO_LABELS: frozenset[str] = frozenset(
    {
        "full backlog registry injected",
        "planning prompt injected",
        "closed iterations injected",
        "current task payload injected",
        "zero-click workflow task injected",
    }
)


@dataclass(frozen=True)
class GuardThresholds:
    warn_body_chars: int = 70000
    max_body_chars: int = 90000
    hard_block_body_chars: int = 110000
    # Raised from 8 → 15: a fresh Kilo session with CLAUDE.md + 5 memory files +
    # available_skills already uses ~8-9 system messages before any conversation.
    # Threshold of 8 was too tight and caused soft_block on every first turn.
    # 15 allows the injection overhead (8) + ~4 conversation turns + headroom.
    max_messages: int = 15
    max_largest_message_chars: int = 24000
    # Raised from 13 → 16: Cursor agent sessions routinely ship ~16 tools
    # (builtin + MCP). Threshold of 13 made every turn a perpetual warn.
    max_tools: int = 16

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "GuardThresholds":
        src = env if env is not None else os.environ
        return cls(
            warn_body_chars=int(src.get("KILO_RELAY_WARN_BODY_CHARS", "70000")),
            max_body_chars=int(src.get("KILO_RELAY_MAX_BODY_CHARS", "90000")),
            hard_block_body_chars=int(src.get("KILO_RELAY_HARD_BLOCK_BODY_CHARS", "110000")),
            max_messages=int(src.get("KILO_RELAY_MAX_MESSAGES", "15")),
            max_largest_message_chars=int(src.get("KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS", "24000")),
            max_tools=int(src.get("KILO_RELAY_MAX_TOOLS", "16")),
        )


@dataclass
class GuardDecision:
    block: bool
    level: str
    reasons: list[str]
    risk_flags: list[str]


# Kept as alias for clarity; simulator code uses GuardVerdict wording.
GuardVerdict = GuardDecision


def estimate_tokens_from_chars(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def preview(text: str, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]


def suffix_preview(text: str, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def summarize_message_content(content: Any, preview_limit: int = DEFAULT_PREVIEW_CHARS) -> dict[str, Any]:
    if isinstance(content, str):
        return {
            "kind": "text",
            "chars": len(content),
            "preview_start": preview(content, preview_limit),
            "preview_end": suffix_preview(content, preview_limit),
        }
    if isinstance(content, list):
        part_stats: list[dict[str, Any]] = []
        total_chars = 0
        for idx, part in enumerate(content):
            serialized = json.dumps(part, ensure_ascii=False)
            total_chars += len(serialized)
            part_stats.append(
                {
                    "index": idx,
                    "type": part.get("type") if isinstance(part, dict) else type(part).__name__,
                    "chars": len(serialized),
                    "preview_start": preview(serialized, 240),
                }
            )
        return {"kind": "parts", "chars": total_chars, "parts": part_stats}
    serialized = json.dumps(content, ensure_ascii=False)
    return {
        "kind": type(content).__name__,
        "chars": len(serialized),
        "preview_start": preview(serialized, preview_limit),
        "preview_end": suffix_preview(serialized, preview_limit),
    }


def summarize_body(body_text: str, preview_limit: int = DEFAULT_PREVIEW_CHARS) -> dict[str, Any]:
    """Compute request-shape stats from a JSON body. Pure: identical to relay output."""
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        return {
            "json_valid": False,
            "body_chars": len(body_text),
            "estimated_tokens": estimate_tokens_from_chars(body_text),
            "body_preview_start": preview(body_text, preview_limit),
            "body_preview_end": suffix_preview(body_text, preview_limit),
        }

    messages = payload.get("messages")
    tools = payload.get("tools")
    message_stats: list[dict[str, Any]] = []
    total_message_chars = 0
    role_chars: dict[str, int] = {}
    if isinstance(messages, list):
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role") or "unknown")
            content_summary = summarize_message_content(msg.get("content"), preview_limit)
            chars = int(content_summary.get("chars") or 0)
            total_message_chars += chars
            role_chars[role] = role_chars.get(role, 0) + chars
            message_stats.append(
                {
                    "index": idx,
                    "role": role,
                    "chars": chars,
                    "summary": content_summary,
                }
            )

    return {
        "json_valid": True,
        "model": payload.get("model"),
        "messages_count": len(messages) if isinstance(messages, list) else 0,
        "tools_count": len(tools) if isinstance(tools, list) else 0,
        "body_chars": len(body_text),
        "estimated_tokens": estimate_tokens_from_chars(body_text),
        "total_message_chars": total_message_chars,
        "largest_message_chars": max((m["chars"] for m in message_stats), default=0),
        "role_chars": role_chars,
        "message_stats": message_stats,
        "body_preview_start": preview(body_text, preview_limit),
        "body_preview_end": suffix_preview(body_text, preview_limit),
    }


def detect_risk_flags(body_text: str) -> list[str]:
    flags: list[str] = []
    for pattern, label in RISK_PATTERNS:
        if pattern in body_text:
            flags.append(label)
    return flags


def evaluate_guard(
    path: str,
    body_text: str,
    request_summary: dict[str, Any],
    *,
    thresholds: GuardThresholds,
    mode: str = "warn",
) -> GuardDecision:
    """Pure guard verdict. Mirrors the historical relay logic exactly."""
    warn_reasons: list[str] = []
    soft_block_reasons: list[str] = []
    hard_block_reasons: list[str] = []
    body_chars = int(request_summary.get("body_chars") or 0)
    messages_count = int(request_summary.get("messages_count") or 0)
    largest_message_chars = int(request_summary.get("largest_message_chars") or 0)
    tools_count = int(request_summary.get("tools_count") or 0)

    if path == "/v1/chat/completions":
        if body_chars > thresholds.warn_body_chars:
            warn_reasons.append(f"body_chars>{thresholds.warn_body_chars} ({body_chars})")
        if body_chars > thresholds.max_body_chars:
            soft_block_reasons.append(f"body_chars>{thresholds.max_body_chars} ({body_chars})")
        if body_chars > thresholds.hard_block_body_chars:
            hard_block_reasons.append(f"body_chars>{thresholds.hard_block_body_chars} ({body_chars})")
        if messages_count > thresholds.max_messages:
            soft_block_reasons.append(f"messages_count>{thresholds.max_messages} ({messages_count})")
        if largest_message_chars > thresholds.max_largest_message_chars:
            warn_reasons.append(
                f"largest_message_chars>{thresholds.max_largest_message_chars} ({largest_message_chars})"
            )
        if tools_count > thresholds.max_tools:
            warn_reasons.append(f"tools_count>{thresholds.max_tools} ({tools_count})")

    risk_flags = detect_risk_flags(body_text)

    if (
        path == "/v1/chat/completions"
        and len(WORKFLOW_COMBO_LABELS.intersection(risk_flags)) >= 3
    ):
        soft_block_reasons.append("workflow_context_combo>=3")

    if hard_block_reasons:
        level = "hard_block"
    elif soft_block_reasons:
        level = "soft_block"
    elif warn_reasons:
        level = "warn"
    else:
        level = "ok"

    reasons = hard_block_reasons + soft_block_reasons + warn_reasons
    block = mode == "block" and level in {"soft_block", "hard_block"}
    return GuardDecision(block=block, level=level, reasons=reasons, risk_flags=risk_flags)
