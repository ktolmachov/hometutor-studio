"""Compact content-pollution stats for OpenAI-compatible chat payloads.

Used by ``kilo_proxy_relay`` JSONL (no full body / no per-message previews).
Pure: no env reads, no I/O.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

# XML / Cursor operational blocks (aligned with _kilo_relay_compress strip targets + common Cursor tags).
_FRAGMENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("available_skills", re.compile(r"<available_skills\b[^>]*>.*?</available_skills\s*>", re.DOTALL | re.IGNORECASE)),
    ("agent_skills", re.compile(r"<agent_skills\b[^>]*>.*?</agent_skills\s*>", re.DOTALL | re.IGNORECASE)),
    ("mcp_file_system", re.compile(r"<mcp_file_system\b[^>]*>.*?</mcp_file_system\s*>", re.DOTALL | re.IGNORECASE)),
    ("mcp_file_system_servers", re.compile(r"<mcp_file_system_servers\b[^>]*>.*?</mcp_file_system_servers\s*>", re.DOTALL | re.IGNORECASE)),
    ("terminal_files_information", re.compile(r"<terminal_files_information\b[^>]*>.*?</terminal_files_information\s*>", re.DOTALL | re.IGNORECASE)),
    ("task_management", re.compile(r"<task_management\b[^>]*>.*?</task_management\s*>", re.DOTALL | re.IGNORECASE)),
    ("rules", re.compile(r"<rules\b[^>]*>.*?</rules\s*>", re.DOTALL | re.IGNORECASE)),
    ("user_info", re.compile(r"<user_info\b[^>]*>.*?</user_info\s*>", re.DOTALL | re.IGNORECASE)),
    ("timestamp", re.compile(r"<timestamp\b[^>]*>.*?</timestamp\s*>", re.DOTALL | re.IGNORECASE)),
    ("mode_selection", re.compile(r"<mode_selection\b[^>]*>.*?</mode_selection\s*>", re.DOTALL | re.IGNORECASE)),
    ("agent_transcripts", re.compile(r"<agent_transcripts\b[^>]*>.*?</agent_transcripts\s*>", re.DOTALL | re.IGNORECASE)),
    ("system_reminder", re.compile(r"<system[_-]reminder\b[^>]*>.*?</system[_-]reminder\s*>", re.DOTALL | re.IGNORECASE)),
    ("user_query", re.compile(r"<user_query\b[^>]*>.*?</user_query\s*>", re.DOTALL | re.IGNORECASE)),
    ("open_and_recently_viewed_files", re.compile(r"<open_and_recently_viewed_files\b[^>]*>.*?</open_and_recently_viewed_files\s*>", re.DOTALL | re.IGNORECASE)),
    ("citing_code", re.compile(r"<citing_code\b[^>]*>.*?</citing_code\s*>", re.DOTALL | re.IGNORECASE)),
    ("communication", re.compile(r"<communication\b[^>]*>.*?</communication\s*>", re.DOTALL | re.IGNORECASE)),
    ("agent_skills_cursor", re.compile(r"<agent_skill\b[^>]*>.*?</agent_skill\s*>", re.DOTALL | re.IGNORECASE)),
    ("mcp_meta", re.compile(r"<mcp_[a-z0-9_-]+\b[^>]*>.*?</mcp_[a-z0-9_-]+\s*>", re.DOTALL | re.IGNORECASE)),
)

# Paths that typically bloat agent context when read in full.
_PATH_RE = re.compile(
    r"(?P<p>"
    r"[A-Za-z]:\\(?:[^\s\"'<>|]+\\)*[^\s\"'<>|]+"  # Windows abs
    r"|/(?:Users|home|var|tmp|opt)/[^\s\"'<>|]+"  # Unix abs (common roots)
    r"|(?:(?:doc|scripts|app|tests|archive|\.cursor)/[^\s\"'<>|]+)"  # repo-relative
    r"|(?:AGENTS\.md|CLAUDE\.md|README\.md|conventions(?:_architecture|_reference)?\.md|"
    r"token_safety(?:_registry)?\.(?:md|json)|backlog_registry\.yaml|tasklist\.md)"
    r")",
    re.IGNORECASE,
)

_EXT_RE = re.compile(r"\.(md|py|ts|tsx|js|json|yaml|yml|html|css|txt|ps1|sh)\b", re.IGNORECASE)


def message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                else:
                    chunks.append(json.dumps(part, ensure_ascii=False))
            else:
                chunks.append(str(part))
        return "\n".join(chunks)
    if content is None:
        return ""
    return json.dumps(content, ensure_ascii=False)


def fragment_char_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, pattern in _FRAGMENT_PATTERNS:
        total = 0
        for match in pattern.finditer(text):
            total += len(match.group(0))
        if total:
            counts[name] = total
    return counts


def normalize_path_key(raw: str) -> str:
    text = raw.strip().strip("\"'`")
    text = text.replace("\\", "/")
    # Drop trailing punctuation from prose.
    text = text.rstrip(").,]}>:;'")
    lower = text.lower()
    for marker in ("/doc/", "/scripts/", "/app/", "/tests/", "/.cursor/"):
        idx = lower.rfind(marker)
        if idx >= 0:
            return text[idx + 1 :]
    for name in ("agents.md", "claude.md", "backlog_registry.yaml", "token_safety_registry.json"):
        if lower.endswith(name) or lower.endswith("/" + name):
            # keep basename for cross-root identity
            return text.rsplit("/", 1)[-1]
    if len(text) > 180:
        return "…" + text[-177:]
    return text


def path_char_contributions(text: str) -> dict[str, int]:
    """Attribute nearby chars to path mentions (window heuristic, not exact file bytes)."""
    contrib: dict[str, int] = defaultdict(int)
    for match in _PATH_RE.finditer(text):
        key = normalize_path_key(match.group("p"))
        if not key or len(key) < 3:
            continue
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 200)
        # Prefer larger attribution when path sits inside a big tool dump: use span until next path/gap.
        contrib[key] += max(len(match.group("p")), end - start)
    return dict(contrib)


def tool_schema_stats(tools: Any) -> dict[str, Any]:
    if not isinstance(tools, list):
        return {"tools_count": 0, "tools_schema_chars": 0, "by_name": []}
    by_name: list[dict[str, Any]] = []
    total = 0
    for tool in tools:
        blob = json.dumps(tool, ensure_ascii=False)
        total += len(blob)
        name = "?"
        if isinstance(tool, dict):
            fn = tool.get("function")
            if isinstance(fn, dict) and fn.get("name"):
                name = str(fn["name"])
            elif tool.get("name"):
                name = str(tool["name"])
        by_name.append({"name": name, "chars": len(blob)})
    by_name.sort(key=lambda r: int(r["chars"]), reverse=True)
    return {"tools_count": len(by_name), "tools_schema_chars": total, "by_name": by_name}


def _message_kind(role: str, text: str, msg: dict[str, Any]) -> str:
    if role == "tool":
        return "tool_result"
    if role == "assistant" and msg.get("tool_calls"):
        return "assistant_tool_calls"
    if role == "system":
        return "system"
    if "<user_query>" in text.lower():
        return "user_query"
    if role == "user":
        return "user"
    if role == "assistant":
        return "assistant"
    return role or "unknown"


def analyze_chat_payload(
    payload: dict[str, Any],
    *,
    top_messages: int = 20,
    top_paths: int = 40,
) -> dict[str, Any]:
    """Build compact pollution stats for one chat.completions JSON object."""
    messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
    tools_info = tool_schema_stats(payload.get("tools"))

    role_chars: dict[str, int] = defaultdict(int)
    kind_chars: dict[str, int] = defaultdict(int)
    fragment_chars: dict[str, int] = defaultdict(int)
    path_chars: dict[str, int] = defaultdict(int)
    path_hits: dict[str, int] = defaultdict(int)
    per_message: list[dict[str, Any]] = []

    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "unknown")
        text = message_text(msg.get("content"))
        # tool_calls on assistant also cost tokens
        extra = ""
        if msg.get("tool_calls"):
            extra = json.dumps(msg.get("tool_calls"), ensure_ascii=False)
        chars = len(text) + len(extra)
        role_chars[role] += chars
        kind = _message_kind(role, text, msg)
        kind_chars[kind] += chars

        frags = fragment_char_counts(text)
        for k, v in frags.items():
            fragment_chars[k] += v

        paths = path_char_contributions(text + "\n" + extra)
        top_local_paths = sorted(paths.items(), key=lambda kv: kv[1], reverse=True)[:8]
        for p, c in paths.items():
            path_chars[p] += c
            path_hits[p] += 1

        per_message.append(
            {
                "index": idx,
                "role": role,
                "kind": kind,
                "chars": chars,
                "fragments": sorted(frags.keys()),
                "paths": [p for p, _ in top_local_paths],
            }
        )

    per_message.sort(key=lambda m: int(m["chars"]), reverse=True)
    top = per_message[: max(0, top_messages)]

    path_rows = [
        {"path": p, "chars": path_chars[p], "hits": path_hits[p]}
        for p in path_chars
    ]
    path_rows.sort(key=lambda r: int(r["chars"]), reverse=True)
    path_rows = path_rows[: max(0, top_paths)]

    # Extension rollup from path keys
    ext_chars: dict[str, int] = defaultdict(int)
    for row in path_rows:
        m = _EXT_RE.search(str(row["path"]))
        if m:
            ext_chars[m.group(1).lower()] += int(row["chars"])

    total_message_chars = sum(role_chars.values())
    return {
        "messages_count": len(messages),
        "total_message_chars": total_message_chars,
        "estimated_tokens": total_message_chars // 4,
        "role_chars": dict(sorted(role_chars.items(), key=lambda kv: kv[1], reverse=True)),
        "kind_chars": dict(sorted(kind_chars.items(), key=lambda kv: kv[1], reverse=True)),
        "fragment_chars": dict(sorted(fragment_chars.items(), key=lambda kv: kv[1], reverse=True)),
        "tools": tools_info,
        "path_chars": path_rows,
        "ext_chars": dict(sorted(ext_chars.items(), key=lambda kv: kv[1], reverse=True)),
        "top_messages": top,
    }


def analyze_body_text(body_text: str, **kwargs: Any) -> dict[str, Any] | None:
    if not body_text:
        return None
    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError:
        return {"json_valid": False, "body_chars": len(body_text)}
    if not isinstance(payload, dict):
        return {"json_valid": False, "body_chars": len(body_text)}
    stats = analyze_chat_payload(payload, **kwargs)
    stats["json_valid"] = True
    stats["body_chars"] = len(body_text)
    return stats
