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
#
# A doubled-backslash escape sequence shown as literal text (e.g. a
# tool_result echoing source that contains `\n` as two raw chars, backslash +
# n, rather than an actual newline, or a JSON-in-JSON re-escaped path like
# `D:\\Projects\\report.txt`) can satisfy the Windows-abs alternative below —
# a single letter + ":" + backslash-separated segments is not enough on its
# own to distinguish a real one-letter-adjacent escape stub ("y:\\n" -> "y://n"
# after backslash->slash normalization) from a genuine multi-segment or
# doubled-escaped real path. An earlier fix tried to solve this by excluding
# backslash from the regex's own segment character class and requiring >=2
# segments or a file extension — that closed the false positive but also lost
# real matches it shouldn't have: single-segment drive-root paths like
# `C:\Windows` (no extension, one segment) and JSON-re-escaped multi-segment
# paths (each "segment" boundary is a doubled backslash, which the excluded
# Windows paths need a little more structure than the Unix/repo-relative
# branches: allow doubled backslashes from JSON-re-escaped text and spaces in
# directory names, but do not start in the middle of another token and do not
# let escape stubs like `y:\\n` rank as real paths.
_PATH_EXT = r"(?:md|py|ts|tsx|js|json|yaml|yml|html|css|txt|ps1|sh|exe|bat|cmd|toml|ini|cfg|log)"
_PATH_RIGHT_BOUNDARY = r"(?=$|[\s)\"'\]}>:;,])"
_WIN_SEG = r"[^\\/\r\n\"'<>|:*?]+?"
_WIN_SEG_NO_SPACE = r"[^\s\\/\r\n\"'<>|:*?]+"
_WIN_WITH_EXT = rf"[A-Za-z]:\\+(?:{_WIN_SEG}\\+)*{_WIN_SEG}\.{_PATH_EXT}{_PATH_RIGHT_BOUNDARY}"
_WIN_NO_SPACE = (
    rf"[A-Za-z]:\\+(?:{_WIN_SEG_NO_SPACE}\\+)*{_WIN_SEG_NO_SPACE}"
    rf"(?!\s+[^\\/\r\n]*\\){_PATH_RIGHT_BOUNDARY}"
)
_PATH_PATTERN = (
    r"(?<![A-Za-z0-9_./\\-])"
    r"(?P<p>"
    f"{_WIN_WITH_EXT}|{_WIN_NO_SPACE}"
    r"|/(?:Users|home|var|tmp|opt)/[^\s\"'<>|]+"  # Unix abs (common roots)
    r"|(?:(?:doc|scripts|app|tests|archive|\.cursor)[/\\][^\s\"'<>|]+)"  # repo-relative
    r"|(?:AGENTS\.md|CLAUDE\.md|README\.md|conventions(?:_architecture|_reference)?\.md|"
    r"token_safety(?:_registry)?\.(?:md|json)|backlog_registry\.yaml|tasklist\.md)"
    r")"
)
_PATH_RE = re.compile(_PATH_PATTERN, re.IGNORECASE)

_EXT_RE = re.compile(rf"\.{_PATH_EXT}\b", re.IGNORECASE)
# Post-normalize junk: escape stubs and collapsed-drive noise from old logs / edge cases.
_JUNK_PATH_KEY_RE = re.compile(
    r"^[a-z]:/{1,2}[ntr]$"  # y:/n, e://n, n:/t …
    r"|^[a-z]:/{1,2}x[0-9a-f]{2}$"  # e:/x20
    r"|^[a-z]:/{1,2}u[0-9a-f]{4}$",  # e:/u1234
    re.IGNORECASE,
)
_MULTI_SLASH_RE = re.compile(r"/{2,}")


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
    """Count XML/Cursor fragment sizes.

    ``mcp_meta`` is residual only: spans already matched by specific ``mcp_*``
    patterns (e.g. ``mcp_file_system``) are not counted again.
    """
    counts: dict[str, int] = {}
    covered_mcp_spans: list[tuple[int, int]] = []
    mcp_meta_pattern: re.Pattern[str] | None = None
    for name, pattern in _FRAGMENT_PATTERNS:
        if name == "mcp_meta":
            mcp_meta_pattern = pattern
            continue
        total = 0
        for match in pattern.finditer(text):
            total += len(match.group(0))
            if name.startswith("mcp_"):
                covered_mcp_spans.append((match.start(), match.end()))
        if total:
            counts[name] = total
    if mcp_meta_pattern is not None:
        residual = 0
        for match in mcp_meta_pattern.finditer(text):
            if any(start <= match.start() and match.end() <= end for start, end in covered_mcp_spans):
                continue
            if any(match.start() < end and match.end() > start for start, end in covered_mcp_spans):
                continue
            residual += len(match.group(0))
        if residual:
            counts["mcp_meta"] = residual
    return counts


def normalize_path_key(raw: str) -> str:
    text = raw.strip().strip("\"'`")
    text = _MULTI_SLASH_RE.sub("/", text.replace("\\", "/"))
    # Drop trailing punctuation from prose / dangling separators.
    text = text.rstrip(").,]}>:;'/\\")
    lower = text.lower()
    for project_marker in ("hometutor-studio/",):
        project_idx = lower.rfind(project_marker)
        if project_idx >= 0:
            root_start = project_idx + len(project_marker)
            for rel_root in ("doc/", "scripts/", "app/", "tests/", ".cursor/"):
                idx = lower.find(rel_root, root_start)
                if idx >= 0:
                    return text[idx:]
    for name in ("agents.md", "claude.md", "backlog_registry.yaml", "token_safety_registry.json"):
        if lower.endswith(name) or lower.endswith("/" + name):
            # keep basename for cross-root identity
            return text.rsplit("/", 1)[-1]
    if len(text) > 180:
        return "…" + text[-177:]
    return text


def is_plausible_path_key(key: str) -> bool:
    """Reject escape-sequence stubs and other non-file keys that pollute top_paths."""
    if not key or len(key) < 4:
        return False
    if _JUNK_PATH_KEY_RE.match(key):
        return False
    if "://" in key and not key.lower().startswith(("http://", "https://", "file://")):
        # y://n style (drive + doubled slash) — never a real filesystem path here
        return False
    return True


def path_char_contributions(text: str) -> dict[str, int]:
    """Attribute nearby chars to path mentions (window heuristic, not exact file bytes)."""
    contrib: dict[str, int] = defaultdict(int)
    for match in _PATH_RE.finditer(text):
        key = normalize_path_key(match.group("p"))
        if not is_plausible_path_key(key):
            continue
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 200)
        # Fixed ±200 char window around the path mention (ranking heuristic, not file bytes).
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
            ext_chars[m.group(0).lstrip(".").lower()] += int(row["chars"])

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
