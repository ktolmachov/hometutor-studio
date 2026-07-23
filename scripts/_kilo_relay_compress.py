"""Cursor → LM / облако: slim OpenAI `/v1/chat/completions` bodies.

Tokens are dominated by tool JSON schemas + XML/noise Cursor injects per request.

Режимы ``KILO_RELAY_SLIM_MODE``: ``local`` (stub system + allowlist tools), ``cloud_budget``
(полный platform system + tools с opt-in trim, срез XML-шума и раздува схемы), ``off``.

Pure transforms (no env reads except via `relay_compress_config_from_env`).
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any

AVAILABLE_SKILLS_RE = re.compile(r"<available_skills>.*?</available_skills>", re.DOTALL | re.IGNORECASE)
MCP_SERVERS_RE = re.compile(r"<mcp_file_system_servers>.*?</mcp_file_system_servers>", re.DOTALL | re.IGNORECASE)
MCP_FILE_SYSTEM_RE = re.compile(
    r"<mcp_file_system\b[^>]*>.*?</mcp_file_system\s*>",
    re.DOTALL | re.IGNORECASE,
)
TERMINAL_FILES_INFO_RE = re.compile(
    r"<terminal_files_information>.*?</terminal_files_information>",
    re.DOTALL | re.IGNORECASE,
)
TASK_MANAGEMENT_RE = re.compile(r"<task_management>.*?</task_management>", re.DOTALL | re.IGNORECASE)
RULES_CURSOR_RE = re.compile(r"<rules\b[^>]*>.*?</rules\s*>", re.DOTALL | re.IGNORECASE)
TIMESTAMP_RE = re.compile(r"<timestamp>.*?</timestamp>", re.DOTALL | re.IGNORECASE)
USER_INFO_RE = re.compile(r"<user_info>.*?</user_info>", re.DOTALL | re.IGNORECASE)
MODE_SELECTION_RE = re.compile(r"<mode_selection>.*?</mode_selection>", re.DOTALL | re.IGNORECASE)
AGENT_TRANSCRIPTS_RE = re.compile(r"<agent_transcripts>.*?</agent_transcripts>", re.DOTALL | re.IGNORECASE)
SYSTEM_REMINDER_RE = re.compile(r"<system_reminder>.*?</system_reminder>", re.DOTALL | re.IGNORECASE)
SYSTEM_REMINDER_DASH_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL | re.IGNORECASE)
AGENT_SKILLS_XML_RE = re.compile(r"<agent_skills\b[^>]*>.*?</agent_skills\s*>", re.DOTALL | re.IGNORECASE)
ORPHAN_AGENT_SKILLS_CLOSE_RE = re.compile(r"</agent_skills\s*>", re.IGNORECASE)

# MVC set for local throughput; optional Glob via KILO_RELAY_LOCAL_INCLUDE_GLOB=1
DEFAULT_LOCAL_TOOLS = frozenset({"Shell", "Read", "Write", "Grep"})
# Opt-in cloud_budget trim (KILO_RELAY_CLOUD_BUDGET_TRIM_TOOLS=1): coding core only.
# Includes both Cursor PascalCase and Kilo lowercase names (allowlist is casefold).
# Omits agent_manager / background_process / webfetch / recall / task UI tools —
# ~1k tok/req schema tax when those idle schemas are dropped.
DEFAULT_CLOUD_BUDGET_TOOLS = frozenset(
    {
        "Shell",
        "Read",
        "Write",
        "StrReplace",
        "Grep",
        "Glob",
        "Delete",
        "bash",
        "read",
        "write",
        "edit",
        "grep",
        "glob",
    }
)
DEFAULT_CURSOR_SYSTEM_STUB = (
    "(Relay: стандартный длинный system-prompt Cursor пропущен.) "
    "Ты кодовый помощник в IDE. Следуй тексту пользователя из <user_query> и отвечай кратко. "
    "Используй только описанные в запросе tools. "
    "Если спрашивают, какая ты модель, назови значение поля model из JSON тела запроса к API."
)

# One-line descriptions — replace Cursor's multi-KB prose.
LOCAL_TOOL_SUMMARY = {
    "Shell": "Run shell command.",
    "Read": "Read file.",
    "Write": "Write or overwrite file.",
    "Grep": "Ripgrep search.",
    "Glob": "Find files by glob.",
    "StrReplace": "Replace text in file.",
}


def _env_truthy(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _truncate_desc(text: str, max_chars: int) -> str:
    if max_chars <= 0 or not isinstance(text, str):
        return text
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    if max_chars <= 1:
        return "…"
    return stripped[: max_chars - 1].rstrip() + "…"


def _collect_function_tool_names_removed(tools: list[Any], allowlist: frozenset[str]) -> tuple[list[Any], list[str]]:
    kept: list[Any] = []
    removed: list[str] = []
    allowlist_ci = {name.casefold() for name in allowlist}
    for item in tools:
        if not isinstance(item, dict) or item.get("type") != "function":
            removed.append("_non_function_drop")
            continue
        fn = item.get("function")
        name = fn.get("name") if isinstance(fn, dict) else None
        if not isinstance(name, str):
            removed.append("__invalid_tool_name__")
            continue
        if name.casefold() in allowlist_ci:
            kept.append(item)
        else:
            removed.append(name)
    return kept, removed


def _shrink_description_fields(node: Any, max_chars: int) -> None:
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "description" and isinstance(val, str):
                node[key] = _truncate_desc(val, max_chars)
            else:
                _shrink_description_fields(val, max_chars)
    elif isinstance(node, list):
        for item in node:
            _shrink_description_fields(item, max_chars)


def _purge_schema_descriptions(node: Any) -> None:
    """Drop description strings inside JSON Schema (massive Cursor overhead)."""
    if isinstance(node, dict):
        for key in list(node.keys()):
            val = node[key]
            if key == "description":
                node.pop(key, None)
                continue
            _purge_schema_descriptions(val)
    elif isinstance(node, list):
        for item in node:
            _purge_schema_descriptions(item)


def _apply_local_tool_summaries(payload_tools: list[Any]) -> None:
    """Replace top-level tool.function.description only; parameter prose removed separately."""
    for entry in payload_tools:
        if not isinstance(entry, dict) or entry.get("type") != "function":
            continue
        fn = entry.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not isinstance(name, str):
            continue
        fn["description"] = LOCAL_TOOL_SUMMARY.get(name, name)


def _rewrite_string_content(body: str, cfg: RelayCompressConfig) -> tuple[str, list[str]]:
    actions: list[str] = []
    out = body
    if cfg.strip_mcp_file_system_xml and MCP_FILE_SYSTEM_RE.search(out):
        out = MCP_FILE_SYSTEM_RE.sub("[mcp_file_system omitted]", out)
        actions.append("strip_mcp_file_system")
    if cfg.strip_mcp_servers_xml and MCP_SERVERS_RE.search(out):
        out = MCP_SERVERS_RE.sub("[mcp_file_system_servers omitted]", out)
        actions.append("strip_mcp_file_system_servers")
    if cfg.strip_available_skills_xml and AVAILABLE_SKILLS_RE.search(out):
        out = AVAILABLE_SKILLS_RE.sub("[available_skills omitted]", out)
        actions.append("strip_available_skills")
    if cfg.strip_terminal_files_information_xml and TERMINAL_FILES_INFO_RE.search(out):
        out = TERMINAL_FILES_INFO_RE.sub("[terminal_files_information omitted]", out)
        actions.append("strip_terminal_files_information")
    if cfg.strip_task_management_xml and TASK_MANAGEMENT_RE.search(out):
        out = TASK_MANAGEMENT_RE.sub("[task_management omitted]", out)
        actions.append("strip_task_management")
    if cfg.strip_cursor_rules_xml and RULES_CURSOR_RE.search(out):
        out = RULES_CURSOR_RE.sub("[rules omitted]", out)
        actions.append("strip_rules")
    if cfg.strip_timestamp_xml and TIMESTAMP_RE.search(out):
        out = TIMESTAMP_RE.sub("[timestamp omitted]", out)
        actions.append("strip_timestamp")
    if cfg.strip_user_info_xml and USER_INFO_RE.search(out):
        out = USER_INFO_RE.sub("[user_info omitted]", out)
        actions.append("strip_user_info")
    if cfg.strip_mode_selection_xml and MODE_SELECTION_RE.search(out):
        out = MODE_SELECTION_RE.sub("[mode_selection omitted]", out)
        actions.append("strip_mode_selection")
    if cfg.strip_agent_transcripts_xml and AGENT_TRANSCRIPTS_RE.search(out):
        out = AGENT_TRANSCRIPTS_RE.sub("[agent_transcripts omitted]", out)
        actions.append("strip_agent_transcripts")
    if cfg.strip_system_reminder_xml:
        if SYSTEM_REMINDER_RE.search(out):
            out = SYSTEM_REMINDER_RE.sub("[system_reminder omitted]", out)
            actions.append("strip_system_reminder_underscore")
        if SYSTEM_REMINDER_DASH_RE.search(out):
            out = SYSTEM_REMINDER_DASH_RE.sub("[system-reminder omitted]", out)
            actions.append("strip_system_reminder_hyphen")
    if cfg.strip_agent_skills_outer_xml:
        if AGENT_SKILLS_XML_RE.search(out):
            out = AGENT_SKILLS_XML_RE.sub("[agent_skills omitted]", out)
            actions.append("strip_agent_skills_xml")
        if ORPHAN_AGENT_SKILLS_CLOSE_RE.search(out):
            out = ORPHAN_AGENT_SKILLS_CLOSE_RE.sub("", out)
            actions.append("strip_orphan_agent_skills_close")
    return out, actions


def _compress_message_strings(payload: dict[str, Any], cfg: RelayCompressConfig) -> list[str]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return []

    all_actions: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        raw = msg.get("content")
        if isinstance(raw, str):
            new_s, acts = _rewrite_string_content(raw, cfg)
            if new_s != raw:
                msg["content"] = new_s
                all_actions.extend(acts)
        elif isinstance(raw, list):
            for part in raw:
                if isinstance(part, dict) and part.get("type") == "text":
                    tex = part.get("text")
                    if isinstance(tex, str):
                        new_t, acts = _rewrite_string_content(tex, cfg)
                        if new_t != tex:
                            part["text"] = new_t
                            all_actions.extend(acts)

    return sorted(set(all_actions))


def _extract_last_user_text(payload: dict[str, Any]) -> str:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return ""
    collected: list[str] = []
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        raw = msg.get("content")
        if isinstance(raw, str):
            collected.append(raw)
        elif isinstance(raw, list):
            for part in raw:
                if isinstance(part, dict) and part.get("type") == "text":
                    t = part.get("text")
                    if isinstance(t, str):
                        collected.append(t)
        break
    return "\n".join(collected)


def _qualifies_simple_chat(payload: dict[str, Any], max_user_chars: int) -> bool:
    if max_user_chars <= 0:
        return False
    text = _extract_last_user_text(payload)
    s = text.strip()
    if not s or len(s) > max_user_chars:
        return False
    # Heuristic: skip if user likely pastes code or paths (keep tools).
    if "```" in s or s.count("/") > 8 or s.count("\\") > 8:
        return False
    return True


def _end_of_tool_call_group(messages: list[Any], start: int) -> int:
    """Return index just after the assistant+tool group that begins at ``start``.

    If ``messages[start]`` is an assistant with ``tool_calls``, skip it and every
    immediately following ``role == "tool"`` message. Otherwise advance by one.
    """
    if start >= len(messages):
        return start
    nxt = start + 1
    head = messages[start]
    if (
        isinstance(head, dict)
        and head.get("role") == "assistant"
        and isinstance(head.get("tool_calls"), list)
        and head["tool_calls"]
    ):
        while nxt < len(messages) and isinstance(messages[nxt], dict) and messages[nxt].get("role") == "tool":
            nxt += 1
    return nxt


def _history_window_bounds(messages: list[Any], keep_last_messages: int) -> tuple[int, int]:
    """Return ``(lead_end, cut_at)``: the kept window is ``messages[:lead_end] +
    messages[cut_at:]``.

    ``lead_end`` covers any leading ``system`` messages (always kept — they carry
    the platform prompt / tool-use rules, not per-turn history).

    ``cut_at`` starts at ``len(messages) - keep_last_messages`` and is walked
    backward past any leading ``role == "tool"`` message, so the kept tail never
    opens on a dangling tool-result whose triggering ``assistant`` message (with
    the matching ``tool_calls`` entry) got cut — that would send an invalid
    message chain upstream. Tool-result messages always directly follow their
    triggering assistant message in this format, so walking back one message at
    a time terminates at that assistant message (or at ``lead_end``).

    If that tool-safe expansion would keep more than ``keep_last_messages``
    non-system messages (typical with a large parallel tool_calls batch on the
    cut boundary), skip whole older assistant+tool groups until the non-system
    tail fits — unless skipping would drop the entire conversation (then keep
    the oversized latest group rather than an empty tail).
    """
    lead_end = 0
    while lead_end < len(messages) and isinstance(messages[lead_end], dict) and messages[lead_end].get("role") == "system":
        lead_end += 1

    if len(messages) - lead_end <= keep_last_messages:
        return lead_end, lead_end

    cut_at = len(messages) - keep_last_messages
    while cut_at > lead_end and isinstance(messages[cut_at], dict) and messages[cut_at].get("role") == "tool":
        cut_at -= 1

    while (len(messages) - cut_at) > keep_last_messages and cut_at < len(messages):
        nxt = _end_of_tool_call_group(messages, cut_at)
        if nxt >= len(messages):
            # Latest group alone exceeds the budget — keep it (valid chain)
            # rather than forwarding only the system lead.
            break
        cut_at = nxt
        while cut_at < len(messages) and isinstance(messages[cut_at], dict) and messages[cut_at].get("role") == "tool":
            cut_at += 1

    return lead_end, cut_at


def _apply_history_window(payload: dict[str, Any], keep_last_messages: int) -> tuple[bool, int]:
    """Keep leading ``system`` message(s) + the last ``keep_last_messages`` of
    the rest, extended as needed to avoid an orphaned tool-result message.
    Returns ``(changed, messages_dropped)``."""
    if keep_last_messages <= 0:
        return False, 0
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return False, 0
    lead_end, cut_at = _history_window_bounds(messages, keep_last_messages)
    if cut_at <= lead_end:
        return False, 0
    dropped = cut_at - lead_end
    payload["messages"] = messages[:lead_end] + messages[cut_at:]
    return True, dropped


def _cap_text_chars(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    dropped = len(text) - max_chars
    return text[:max_chars] + f"\n…[truncated by relay: {dropped} more chars]", True


def _cap_message_content(content: Any, max_chars: int) -> tuple[Any, bool]:
    """Cap a message's ``content`` (str or list-of-parts) to ``max_chars``,
    keeping the head — matching ``_truncate_desc``'s head-keep convention — and
    appending a marker with the dropped char count."""
    if isinstance(content, str):
        return _cap_text_chars(content, max_chars)
    if isinstance(content, list):
        changed = False
        new_parts: list[Any] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                new_text, part_changed = _cap_text_chars(part["text"], max_chars)
                if part_changed:
                    part = {**part, "text": new_text}
                    changed = True
            new_parts.append(part)
        return new_parts, changed
    return content, False


def _cap_tool_result_chars(payload: dict[str, Any], max_chars: int) -> tuple[bool, int]:
    """Cap the content of every ``role == "tool"`` message to ``max_chars``.
    Returns ``(changed, messages_capped)``."""
    if max_chars <= 0:
        return False, 0
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return False, 0
    capped = 0
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "tool":
            continue
        new_content, changed = _cap_message_content(msg.get("content"), max_chars)
        if changed:
            msg["content"] = new_content
            capped += 1
    return capped > 0, capped


def _apply_cursor_system_stub(payload: dict[str, Any], stub: str) -> bool:
    """Replace every ``role == system`` message content with ``stub``."""
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return False
    changed = False
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "system":
            continue
        if msg.get("content") != stub:
            msg["content"] = stub
            changed = True
    return changed


@dataclass
class RelayCompressConfig:
    """If `tools_allowlist` is None → do not drop tools (unless simple-chat path drops all)."""

    tools_allowlist: frozenset[str] | None = None
    tool_description_max_chars: int = 0
    strip_available_skills_xml: bool = False
    strip_mcp_servers_xml: bool = False
    strip_mcp_file_system_xml: bool = False
    strip_timestamp_xml: bool = False
    strip_user_info_xml: bool = False
    strip_mode_selection_xml: bool = False
    strip_agent_transcripts_xml: bool = False
    strip_system_reminder_xml: bool = False
    strip_agent_skills_outer_xml: bool = False
    strip_terminal_files_information_xml: bool = False
    strip_task_management_xml: bool = False
    strip_cursor_rules_xml: bool = False
    replace_cursor_system_content: bool = False
    cursor_system_stub_text: str = DEFAULT_CURSOR_SYSTEM_STUB
    use_local_tool_summaries: bool = False
    purge_parameter_descriptions: bool = False
    simple_chat_strip_tools_max_user_chars: int = 0
    slim_mode_label: str = ""
    keep_last_messages: int = 0
    max_tool_result_chars: int = 0


@dataclass
class CompressResult:
    payload: dict[str, Any]
    tools_before: int
    tools_after: int
    tool_names_removed: list[str]
    shrink_applied: bool
    tool_description_limit: int
    chars_saved_estimate: int
    strip_actions: list[str] = field(default_factory=list)
    simple_chat_tools_dropped: bool = False
    tool_choice_forced_none: bool = False
    slim_mode_label: str = ""
    cursor_system_stubbed: bool = False
    messages_before: int = 0
    messages_after: int = 0
    messages_dropped_history: int = 0
    tool_results_capped: int = 0

    def to_log_dict(self) -> dict[str, Any]:
        ct = self.chars_saved_estimate
        return {
            "enabled": True,
            "slim_mode": (self.slim_mode_label or None),
            "cursor_system_stubbed": self.cursor_system_stubbed,
            "tools_before": self.tools_before,
            "tools_after": self.tools_after,
            "tool_names_removed": self.tool_names_removed,
            "shrink_tool_descriptions_applied": self.shrink_applied,
            "tool_description_limit": self.tool_description_limit,
            "strip_actions": self.strip_actions,
            "chars_saved_estimate": ct,
            "estimated_tokens_saved_approx": max(1, ct // 4) if ct else 0,
            "simple_chat_tools_dropped": self.simple_chat_tools_dropped,
            "tool_choice_forced_none": self.tool_choice_forced_none,
            "messages_before": self.messages_before,
            "messages_after": self.messages_after,
            "messages_dropped_history": self.messages_dropped_history,
            "tool_results_capped": self.tool_results_capped,
        }


def compress_chat_completion(payload: dict[str, Any], cfg: RelayCompressConfig) -> CompressResult:
    """Return a deep copy of `payload` with optional slimming."""
    out = copy.deepcopy(payload)
    body_before = json.dumps(out, ensure_ascii=False)
    chars_before_all = len(body_before)

    tools = out.get("tools")
    tools_before = len(tools) if isinstance(tools, list) else 0
    tool_names_removed: list[str] = []
    shrunk = False
    simple_drop = False
    forced_none = False

    messages_before = len(out["messages"]) if isinstance(out.get("messages"), list) else 0
    _, messages_dropped_history = _apply_history_window(out, cfg.keep_last_messages)
    messages_after = len(out["messages"]) if isinstance(out.get("messages"), list) else messages_before

    strip_actions = _compress_message_strings(out, cfg)

    _, tool_results_capped = _cap_tool_result_chars(out, cfg.max_tool_result_chars)
    if tool_results_capped:
        strip_actions = sorted({*strip_actions, "cap_tool_result_chars"})
    if messages_dropped_history:
        strip_actions = sorted({*strip_actions, "history_window"})

    stubbed = False
    if cfg.replace_cursor_system_content and _apply_cursor_system_stub(out, cfg.cursor_system_stub_text):
        stubbed = True
        strip_actions = sorted({*strip_actions, "stub_cursor_system_roles"})

    if cfg.simple_chat_strip_tools_max_user_chars > 0 and _qualifies_simple_chat(
        out, cfg.simple_chat_strip_tools_max_user_chars
    ):
        if isinstance(out.get("tools"), list) and out["tools"]:
            tool_names_removed = [str(t.get("function", {}).get("name", "?")) for t in out["tools"] if isinstance(t, dict)]
            out.pop("tools", None)
            out["tool_choice"] = "none"
            simple_drop = True
            forced_none = True

    tools = out.get("tools")
    if isinstance(tools, list) and cfg.tools_allowlist is not None and not simple_drop:
        kept, removed = _collect_function_tool_names_removed(tools, cfg.tools_allowlist)
        if len(kept) != len(tools):
            tool_names_removed = removed
            if not kept:
                out.pop("tools", None)
            else:
                out["tools"] = kept

    tools_for_shrink = out.get("tools")
    tools_after = len(tools_for_shrink) if isinstance(tools_for_shrink, list) else 0

    if isinstance(tools_for_shrink, list) and tools_for_shrink:
        if cfg.use_local_tool_summaries:
            _apply_local_tool_summaries(tools_for_shrink)
            shrunk = True
        if cfg.purge_parameter_descriptions:
            for entry in tools_for_shrink:
                if not isinstance(entry, dict):
                    continue
                fn = entry.get("function")
                if isinstance(fn, dict) and isinstance(fn.get("parameters"), dict):
                    _purge_schema_descriptions(fn["parameters"])
            shrunk = True
        if cfg.tool_description_max_chars > 0 and not cfg.use_local_tool_summaries:
            for entry in tools_for_shrink:
                if isinstance(entry, dict):
                    _shrink_description_fields(entry, cfg.tool_description_max_chars)
            shrunk = True

    body_after = json.dumps(out, ensure_ascii=False)
    chars_after_all = len(body_after)

    desc_limit = 0
    if shrunk:
        desc_limit = 1 if cfg.use_local_tool_summaries else cfg.tool_description_max_chars

    return CompressResult(
        payload=out,
        tools_before=tools_before,
        tools_after=tools_after,
        tool_names_removed=tool_names_removed,
        shrink_applied=shrunk,
        tool_description_limit=desc_limit,
        chars_saved_estimate=max(0, chars_before_all - chars_after_all),
        strip_actions=strip_actions,
        simple_chat_tools_dropped=simple_drop,
        tool_choice_forced_none=forced_none,
        slim_mode_label=cfg.slim_mode_label,
        cursor_system_stubbed=stubbed,
        messages_before=messages_before,
        messages_after=messages_after,
        messages_dropped_history=messages_dropped_history,
        tool_results_capped=tool_results_capped,
    )


def parse_tools_allowlist(raw: str) -> frozenset[str] | None:
    text = raw.strip()
    if not text:
        return None
    names = tuple(p.strip() for p in text.split(",") if p.strip())
    if not names:
        return None
    return frozenset(names)


_SLIM_OFF = frozenset({"off", "passthrough", "false", "0", "no", "disabled"})
_SLIM_CLOUD_BUDGET = frozenset({"cloud_budget", "budget_cloud"})
_SLIM_LOCAL = frozenset({"local"})
_SLIM_KNOWN = _SLIM_OFF | _SLIM_CLOUD_BUDGET | _SLIM_LOCAL


def validate_slim_mode(slim_setting: str) -> str:
    """Normalize and validate ``KILO_RELAY_SLIM_MODE``; raise on unknown tokens.

    Unknown values used to fall through to the ``local`` pack (Cursor allowlist +
    system stub) — a silent footgun for typos. Empty / whitespace → ``local``.
    """
    token = slim_setting.strip().lower()
    if not token:
        return "local"
    if token not in _SLIM_KNOWN:
        known = ", ".join(sorted(_SLIM_KNOWN))
        raise ValueError(
            f"Unknown KILO_RELAY_SLIM_MODE={slim_setting!r}. "
            f"Expected one of: {known}."
        )
    return token


def _slim_mode_flags(slim_setting: str) -> tuple[bool, bool, bool]:
    """Return (is_off, is_cloud_budget, is_local). Caller must validate first."""
    token = slim_setting.strip().lower()
    is_off = token in _SLIM_OFF
    is_cloud_budget = token in _SLIM_CLOUD_BUDGET
    is_local = not is_off and not is_cloud_budget
    return is_off, is_cloud_budget, is_local


def is_cloud_budget_slim_mode(slim_setting: str) -> bool:
    return slim_setting.strip().lower() in _SLIM_CLOUD_BUDGET


def relay_compress_config_from_env(env: dict[str, str]) -> RelayCompressConfig:
    slim_setting = validate_slim_mode(env.get("KILO_RELAY_SLIM_MODE", "local"))
    slim_raw_display = slim_setting
    _, is_cloud_budget, is_local = _slim_mode_flags(slim_setting)
    allow = parse_tools_allowlist(env.get("KILO_RELAY_TOOLS_ALLOWLIST", ""))

    strip_skills = _env_truthy(env.get("KILO_RELAY_STRIP_AVAILABLE_SKILLS_XML", ""))
    strip_mcp = _env_truthy(env.get("KILO_RELAY_STRIP_MCP_SERVERS_XML", ""))
    strip_mcp_fs = _env_truthy(env.get("KILO_RELAY_STRIP_MCP_FILE_SYSTEM_XML", ""))
    strip_ts = _env_truthy(env.get("KILO_RELAY_STRIP_TIMESTAMP_XML", ""))
    strip_ui = _env_truthy(env.get("KILO_RELAY_STRIP_USER_INFO_XML", ""))
    strip_mode = _env_truthy(env.get("KILO_RELAY_STRIP_MODE_SELECTION_XML", ""))
    strip_at = _env_truthy(env.get("KILO_RELAY_STRIP_AGENT_TRANSCRIPTS_XML", ""))
    strip_sr = _env_truthy(env.get("KILO_RELAY_STRIP_SYSTEM_REMINDER_XML", ""))
    strip_asw = _env_truthy(env.get("KILO_RELAY_STRIP_AGENT_SKILLS_OUTER_XML", ""))
    strip_term = _env_truthy(env.get("KILO_RELAY_STRIP_TERMINAL_FILES_INFORMATION_XML", ""))
    strip_tm = _env_truthy(env.get("KILO_RELAY_STRIP_TASK_MANAGEMENT_XML", ""))
    strip_rules = _env_truthy(env.get("KILO_RELAY_STRIP_CURSOR_RULES_XML", ""))
    stub_text_raw = env.get("KILO_RELAY_CURSOR_SYSTEM_STUB", "").strip()
    stub_text = stub_text_raw if stub_text_raw else DEFAULT_CURSOR_SYSTEM_STUB

    max_desc = int(env.get("KILO_RELAY_TOOL_DESCRIPTION_MAX_CHARS", "0") or "0")
    if env.get("KILO_RELAY_SHRINK_TOOL_DESCRIPTIONS", "").strip().lower() in {"1", "true", "yes"} and max_desc <= 0:
        max_desc = 80

    replace_sys = _env_truthy(env.get("KILO_RELAY_REPLACE_CURSOR_SYSTEM", ""))
    keep_last_messages = int(env.get("KILO_RELAY_KEEP_LAST_MESSAGES", "0") or "0")
    max_tool_result_chars = int(env.get("KILO_RELAY_MAX_TOOL_RESULT_CHARS", "0") or "0")
    use_summaries = False
    purge_params = False
    simple_max = int(env.get("KILO_RELAY_SIMPLE_CHAT_MAX_USER_CHARS", "0") or "0")
    label = ""

    if is_cloud_budget:
        # Облако (Sonnet/GPT…) через релей: срез шума в user-тексте и жира схемы tools,
        # без замены платформенного system и без обрезки списка tools.
        label = slim_raw_display or "cloud_budget"
        strip_skills = True
        strip_mcp = True
        strip_mcp_fs = True
        strip_ts = True
        strip_mode = True
        strip_ui = _env_truthy(env.get("KILO_RELAY_CLOUD_BUDGET_STRIP_USER_INFO", "0"))
        strip_at = True
        strip_sr = True
        strip_asw = True
        strip_term = True
        strip_tm = _env_truthy(env.get("KILO_RELAY_CLOUD_BUDGET_STRIP_TASK_MANAGEMENT", "0"))
        strip_rules = _env_truthy(env.get("KILO_RELAY_CLOUD_BUDGET_STRIP_CURSOR_RULES", "0"))
        replace_sys = _env_truthy(env.get("KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM", "0"))
        use_summaries = False
        purge_params = not _env_truthy(env.get("KILO_RELAY_CLOUD_BUDGET_NO_PURGE_SCHEMA", "0"))
        raw_cd = env.get("KILO_RELAY_CLOUD_BUDGET_TOOL_DESC_MAX", "120").strip()
        max_desc = 0 if raw_cd in {"", "0"} else int(raw_cd)
        sc = env.get("KILO_RELAY_CLOUD_BUDGET_SIMPLE_CHAT_MAX_USER_CHARS", "").strip()
        if sc:
            simple_max = int(sc)
        # Tier B (history budget) — opt-in only: unset ⇒ 0 ⇒ no-op, matching
        # every other KILO_RELAY_CLOUD_BUDGET_* toggle's default-off convention.
        keep_last_messages = int(env.get("KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES", "0") or "0")
        max_tool_result_chars = int(env.get("KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS", "0") or "0")
        # Opt-in tool-schema trim. Explicit allowlist wins; else DEFAULT_CLOUD_BUDGET_TOOLS
        # when TRIM_TOOLS=1. Default remains "forward all tools" (Cursor/Kilo may need them) —
        # so the generic KILO_RELAY_TOOLS_ALLOWLIST (set at the top of this function, meant for
        # `local`/`off`) must NOT leak through here; matches the same two-tier convention already
        # enforced for keep_last_messages/max_tool_result_chars above (generic vars don't fall
        # back into cloud_budget, only *_CLOUD_BUDGET_* ones do).
        cloud_allow = parse_tools_allowlist(env.get("KILO_RELAY_CLOUD_BUDGET_TOOLS_ALLOWLIST", ""))
        if cloud_allow is not None:
            allow = cloud_allow
        elif _env_truthy(env.get("KILO_RELAY_CLOUD_BUDGET_TRIM_TOOLS", "0")):
            allow = frozenset(DEFAULT_CLOUD_BUDGET_TOOLS)
        else:
            allow = None
    elif is_local:
        label = slim_raw_display or "local(default)"
        if allow is None:
            allow = set(DEFAULT_LOCAL_TOOLS)
            if _env_truthy(env.get("KILO_RELAY_LOCAL_INCLUDE_GLOB", "0")):
                allow.add("Glob")
            if _env_truthy(env.get("KILO_RELAY_LOCAL_INCLUDE_STRREPLACE", "0")):
                allow.add("StrReplace")
            allow = frozenset(allow)
        strip_skills = True
        strip_mcp = True
        strip_mcp_fs = True
        strip_ts = True
        strip_mode = True
        if not _env_truthy(env.get("KILO_RELAY_LOCAL_KEEP_USER_INFO", "0")):
            strip_ui = True
        strip_at = True
        strip_sr = True
        strip_asw = True
        strip_term = True
        strip_tm = True
        if _env_truthy(env.get("KILO_RELAY_LOCAL_STRIP_CURSOR_RULES", "0")):
            strip_rules = True
        if not _env_truthy(env.get("KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM", "0")):
            replace_sys = True
        use_summaries = True
        purge_params = True
        max_desc = 0
        if simple_max <= 0 and _env_truthy(env.get("KILO_RELAY_SIMPLE_CHAT_STRIP_TOOLS", "1")):
            simple_max = int(env.get("KILO_RELAY_SIMPLE_CHAT_MAX_USER_CHARS_DEFAULT", "700") or "700")

    return RelayCompressConfig(
        tools_allowlist=allow,
        tool_description_max_chars=max_desc,
        strip_available_skills_xml=strip_skills,
        strip_mcp_servers_xml=strip_mcp,
        strip_mcp_file_system_xml=strip_mcp_fs,
        strip_timestamp_xml=strip_ts,
        strip_user_info_xml=strip_ui,
        strip_mode_selection_xml=strip_mode,
        strip_agent_transcripts_xml=strip_at,
        strip_system_reminder_xml=strip_sr,
        strip_agent_skills_outer_xml=strip_asw,
        strip_terminal_files_information_xml=strip_term,
        strip_task_management_xml=strip_tm,
        strip_cursor_rules_xml=strip_rules,
        replace_cursor_system_content=replace_sys,
        cursor_system_stub_text=stub_text,
        use_local_tool_summaries=use_summaries,
        purge_parameter_descriptions=purge_params,
        simple_chat_strip_tools_max_user_chars=simple_max,
        slim_mode_label=label,
        keep_last_messages=keep_last_messages,
        max_tool_result_chars=max_tool_result_chars,
    )


def relay_compress_any_enabled(cfg: RelayCompressConfig) -> bool:
    return bool(
        bool(cfg.slim_mode_label)
        or cfg.tools_allowlist is not None
        or cfg.tool_description_max_chars > 0
        or cfg.strip_available_skills_xml
        or cfg.strip_mcp_servers_xml
        or cfg.strip_mcp_file_system_xml
        or cfg.strip_timestamp_xml
        or cfg.strip_user_info_xml
        or cfg.strip_mode_selection_xml
        or cfg.strip_agent_transcripts_xml
        or cfg.strip_system_reminder_xml
        or cfg.strip_agent_skills_outer_xml
        or cfg.strip_terminal_files_information_xml
        or cfg.strip_task_management_xml
        or cfg.strip_cursor_rules_xml
        or cfg.replace_cursor_system_content
        or cfg.simple_chat_strip_tools_max_user_chars > 0
        or cfg.keep_last_messages > 0
        or cfg.max_tool_result_chars > 0
    )
