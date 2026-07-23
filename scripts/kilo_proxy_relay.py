#!/usr/bin/env python3
r"""Local relay/proxy for inspecting Kilo/OpenAI-compatible chat payloads.

Listens on http://127.0.0.1:8787 and forwards to ``KILO_RELAY_UPSTREAM``
(LM Studio by default for ``SLIM_MODE=local``; при ``cloud_budget`` и пустом
``KILO_RELAY_UPSTREAM`` — при ``cloud_budget`` дефолт ``https://api.vsegpt.ru``, см. ``effective_upstream_base``).

Logs one JSON object per request to a JSONL file with:
- URL/path/method
- redacted headers
- raw request/response body, only when ``KILO_RELAY_FULL_BODY=1`` (default: off)
- body length
- rough token estimate
- per-message char stats
- response status/body preview

Also prints one mini-stats line per request to stderr (body/msgs/tools/guard/stream/elapsed).

Usage::

  python scripts/kilo_proxy_relay.py

  Windows (из корня репозитория)::

      .venv\Scripts\python.exe scripts/kilo_proxy_relay.py

Эксплуатация (стриминг, LM Studio, JSONL): ``doc/kilo_proxy_relay.md``.

Environment variables:
  KILO_RELAY_HOST=127.0.0.1
  KILO_RELAY_PORT=8787
  KILO_RELAY_UPSTREAM=   # пусто: local → http://127.0.0.1:1234; cloud_budget → KILO_RELAY_CLOUD_DEFAULT_UPSTREAM
  KILO_RELAY_CLOUD_DEFAULT_UPSTREAM=https://api.vsegpt.ru
  KILO_RELAY_UPSTREAM_TIMEOUT=120
  KILO_RELAY_LOG=logs/kilo_relay.jsonl
  KILO_RELAY_PREVIEW_CHARS=800
  KILO_RELAY_FULL_BODY=0   # opt-in ("1"/"true"/"yes"/"on"): default is OFF (secure by default)
  KILO_RELAY_CONTENT_STATS=1  # default ON: JSONL content_stats (fragments/paths/kinds/tools)
  KILO_RELAY_MESSAGE_STATS=0  # opt-in: keep per-message previews in JSONL (bloated)
  KILO_RELAY_WARN_BODY_CHARS=70000
  KILO_RELAY_MAX_BODY_CHARS=90000
  KILO_RELAY_HARD_BLOCK_BODY_CHARS=110000
  KILO_RELAY_MAX_MESSAGES=15
  KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS=24000
  KILO_RELAY_MAX_TOOLS=16
  KILO_RELAY_GUARD_MODE=warn   # cloud_budget: если unset → block (compress regression ≠ pass 100k+ upstream)
  KILO_RELAY_SESSION_WARN_TOKENS=20000      # original (pre-compress) session health
  KILO_RELAY_SESSION_WARN_MESSAGES=40
  KILO_RELAY_SESSION_WARN_BODY_CHARS=110000

  DeepSeek preset (relay → DeepSeek's OpenAI-compatible cloud API instead of llama.cpp):
  KILO_RELAY_UPSTREAM_PRESET=deepseek   # activates the preset below; explicit KILO_RELAY_UPSTREAM
                                         # still wins (and disables the preset's auth/model rewrite too)
  DEEPSEEK_API_BASE=https://api.deepseek.com   # default if unset. Canonical DeepSeek quickstart
                                                # base_url (curl example: POST .../chat/completions).
                                                # Combined with Kilo's incoming /v1/chat/completions
                                                # path this yields .../v1/chat/completions, which
                                                # DeepSeek's own WorkBuddy integration docs also use
                                                # for that exact endpoint — this does NOT imply every
                                                # /v1/* path (models, token-counting, ...) is aliased
                                                # the same way, only chat completions is confirmed.
  DEEPSEEK_MODEL=deepseek-v4-pro   # default if unset; forced into payload["model"]. Context: 1M
                                    # tokens (deepseek-v4-pro/-flash, released 2026-04).
  DEEPSEEK_API_KEY=...                             # required when preset=deepseek; relay fails fast if missing
  DEEPSEEK_ALLOW_CUSTOM_HOST=1   # required if DEEPSEEK_API_BASE's host isn't api.deepseek.com
                                  # (e.g. a corporate proxy in front of DeepSeek) — otherwise the
                                  # relay refuses to start (a typo'd host would leak the real key
                                  # there via the unconditional Authorization override). https
                                  # scheme is required unconditionally, no opt-out.

  Kimi / Moonshot preset (OpenAI-compatible cloud API):
  KILO_RELAY_UPSTREAM_PRESET=kimi   # activates; explicit KILO_RELAY_UPSTREAM still wins (auth/model off)
  KIMI_API_KEY=...                  # required when preset=kimi; fail-fast if missing
  KIMI_BASE_URL=https://api.moonshot.ai/v1   # OpenAI-SDK style (with /v1). Relay strips trailing /v1
                                              # before joining Cursor's /v1/chat/completions path so the
                                              # upstream URL is .../v1/chat/completions once, not /v1/v1/...
  KIMI_MODEL=kimi-k3                # default; also allowed: kimi-k2.7-code-highspeed
  KIMI_ALLOW_CUSTOM_HOST=1          # required if KIMI_BASE_URL host isn't api.moonshot.ai
  DEEPSEEK_THINKING=disabled        # optional: "enabled"/"disabled". DeepSeek V4 defaults to
                                     # thinking.type=enabled + reasoning_effort=high when unset —
                                     # can silently inflate output tokens/latency/cost on every
                                     # request. Unset here = relay does not touch the field at all.
  DEEPSEEK_REASONING_EFFORT=high    # optional: "high"/"max" (DeepSeek's only two real levels; it
                                     # silently maps low/medium up to high and xhigh up to max, so
                                     # this relay does not offer the fake illusion of finer control).
                                     # Only meaningful when thinking is enabled/unset; rejected at
                                     # startup if DEEPSEEK_THINKING=disabled is also set (would be
                                     # a no-op DeepSeek silently ignores).
  Relay replaces the client's Authorization header with ``Bearer $DEEPSEEK_API_KEY`` for every
  request while the preset is active — Kilo's own dummy relay key is never forwarded to DeepSeek.
  It also strips Cookie/Proxy-Authorization/other client-side auth headers before forwarding to
  DeepSeek specifically (a real internet host has no legitimate reason to see them), and strips
  Accept-Encoding from every outgoing request to every upstream (this relay never decompresses
  responses, so it must not advertise gzip support upstream while stripping Content-Encoding from
  what it hands back to the client).

  Payload compatibility fixes applied while the DeepSeek preset is active (confirmed via
  DeepSeek's own oh_my_pi agent-integration guide — all four cause a hard HTTP 400 if left as-is):
  - ``role: "developer"`` messages are rewritten to ``role: "system"`` (DeepSeek rejects "developer").
  - ``tool_choice`` is stripped whenever thinking mode is effectively active (DeepSeek's own
    default when DEEPSEEK_THINKING is unset), since DeepSeek rejects tool_choice in thinking mode.
  - ``max_completion_tokens`` is renamed to ``max_tokens`` (or dropped if both are present).
  - An assistant tool-call message with ``content: null`` gets ``content: ""`` (DeepSeek requires
    non-null content on tool-call messages).
  Effective overrides (model/thinking/reasoning_effort/compatibility_fixes) are recorded
  per-request under ``deepseek_overrides`` in the JSONL log.

  KNOWN GAP (not fixed by this relay — stateful, not a single-request payload fact like the fixes
  above): DeepSeek requires the assistant's ``reasoning_content`` from a tool-call turn to be
  threaded back into every subsequent request in that conversation, or the API returns HTTP 400.
  This relay proxies whatever message history Kilo constructs; it does not verify or repair that
  history across requests. Kilo's compatibility with DeepSeek's reasoning_content replay
  convention has not been confirmed (no captured multi-turn trace, no Kilo adapter source
  reviewed) — a multi-turn agentic tool-calling loop through this preset may fail on the second
  tool round-trip. This has NOT been tested end-to-end.

  Стриминг ответа (Cursor шлёт stream:true по умолчанию):
  релей **проксирует поток** в клиент: те же байты, что от LM Studio, без HTTP chunked
  (chunked ломал разбор ответа в Cursor). Откат к полной буферизации: KILO_RELAY_BUFFER_STREAM=1

  Local LM (рекомендуется для Cursor → локальная 8B через LM Studio):

  Сжатие **включено по умолчанию** (если переменная не задана, подставляется
  ``KILO_RELAY_SLIM_MODE=local``). Ядро — **4 инструмента**: Shell, Read,
  Write, Grep (без MCP/Task/Web/Notebook и пр.). **Glob** — только при
  ``KILO_RELAY_LOCAL_INCLUDE_GLOB=1``. **StrReplace** — при
  ``KILO_RELAY_LOCAL_INCLUDE_STRREPLACE=1``.
  По умолчанию в ``local``: вырезается тяжёлый блок ``role:system`` Cursor
  (замена на короткий stub — см. ниже); отключить: ``KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM=1``.
  Вырезание большого блока ``<rules>...</rules>`` с правилами: только если
  ``KILO_RELAY_LOCAL_STRIP_CURSOR_RULES=1``.
  Свой текст system-stub: ``KILO_RELAY_CURSOR_SYSTEM_STUB=...``

  Основные переменные:

  KILO_RELAY_SLIM_MODE=local   # явно; или off / passthrough; или cloud_budget / budget_cloud
  KILO_RELAY_TOOLS_ALLOWLIST=Read,Shell,...  # local: иначе ядро из 4 tool; cloud_budget: задать = ограничить tools

  Режим cloud_budget (релей → облачный провайдер; экономия входа без stub system):
  KILO_RELAY_CLOUD_BUDGET_TOOL_DESC_MAX=120   # 0 = не резать description tools; по умолчанию 120
  KILO_RELAY_CLOUD_BUDGET_NO_PURGE_SCHEMA=1   # не чистить descriptions в JSON parameters
  KILO_RELAY_CLOUD_BUDGET_STRIP_USER_INFO=1
  KILO_RELAY_CLOUD_BUDGET_STRIP_TASK_MANAGEMENT=1
  KILO_RELAY_CLOUD_BUDGET_STRIP_CURSOR_RULES=1
  KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM=1   # stub system (CloudBudget launcher включает)
  KILO_RELAY_CLOUD_BUDGET_SIMPLE_CHAT_MAX_USER_CHARS=700  # если задано — снятие tools на короткой реплике
  KILO_RELAY_CLOUD_BUDGET_KEEP_LAST_MESSAGES=14   # opt-in Tier B: system + последние N (0=выкл); было 24
  KILO_RELAY_CLOUD_BUDGET_MAX_TOOL_RESULT_CHARS=1500  # opt-in Tier B: cap role=tool (0=выкл); 1500 after 2026-07-23 audit
  KILO_RELAY_CLOUD_BUDGET_TRIM_TOOLS=1   # opt-in: coding-core allowlist (~6–10 tools); drops agent/recall/webfetch tax
  KILO_RELAY_CLOUD_BUDGET_TOOLS_ALLOWLIST=read,write,edit,grep,glob,bash  # optional explicit list (wins over TRIM)
  # В cloud_budget generic KILO_RELAY_KEEP_LAST_MESSAGES / KILO_RELAY_MAX_TOOL_RESULT_CHARS НЕ fallback — только *_CLOUD_BUDGET_*
  # 14/1500 — канон после live log 2026-07-23 (не резать keep_last вслепую; сначала новый чат при original≫15).
  KILO_RELAY_KEEP_LAST_MESSAGES=0   # для off/local (не cloud_budget)
  KILO_RELAY_MAX_TOOL_RESULT_CHARS=0

  KILO_RELAY_LOCAL_INCLUDE_GLOB=1
  KILO_RELAY_LOCAL_INCLUDE_STRREPLACE=1
  KILO_RELAY_LOCAL_KEEP_USER_INFO=1   # не вырезать <user_info>
  KILO_RELAY_LOCAL_KEEP_CURSOR_SYSTEM=1   # не заменять длинный system Cursor
  KILO_RELAY_LOCAL_STRIP_CURSOR_RULES=1   # вырезать <rules>...</rules>
  KILO_RELAY_REPLACE_CURSOR_SYSTEM=1   # вручную при SLIM_MODE=off — замена system stub
  KILO_RELAY_CURSOR_SYSTEM_STUB=text   # текст stub (переопределяет короткий дефолт)
  KILO_RELAY_SIMPLE_CHAT_STRIP_TOOLS=0  # не убирать tools на короткой реплике
  KILO_RELAY_SIMPLE_CHAT_MAX_USER_CHARS=700   # порог «простой реплики»

  Ручной режим (payload как у Cursor, только отдельные флаги вырезания),
  если ``KILO_RELAY_SLIM_MODE=off``:

  KILO_RELAY_TOOLS_ALLOWLIST=Shell,Read,Write,Grep
  KILO_RELAY_STRIP_AVAILABLE_SKILLS_XML=1
  KILO_RELAY_STRIP_MCP_SERVERS_XML=1
  KILO_RELAY_STRIP_MCP_FILE_SYSTEM_XML=1
  KILO_RELAY_STRIP_TIMESTAMP_XML=1
  KILO_RELAY_STRIP_USER_INFO_XML=1
  KILO_RELAY_STRIP_SYSTEM_REMINDER_XML=1
  KILO_RELAY_STRIP_AGENT_SKILLS_OUTER_XML=1
  KILO_RELAY_SHRINK_TOOL_DESCRIPTIONS=1
  KILO_RELAY_TOOL_DESCRIPTION_MAX_CHARS=80

  Cursor: OpenAI-compatible **base URL должен указывать на этот relay**, а не на
  порт LM Studio напрямую — иначе сжатие не применяется.

"""

from __future__ import annotations

import http.client
import json
import os
import socket
import ssl
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    """Refuse a second listener on the same host:port (Windows SO_REUSEADDR footgun)."""

    allow_reuse_address = False

    def server_bind(self) -> None:
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            # Must be set before bind; prevents two kilo_proxy_relay.py on :8787.
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

def _configure_stdio_utf8() -> None:
    """Avoid UnicodeEncodeError on Windows cp1252 consoles / redirected logs.

    Start-KiloRelayDaily.ps1 redirects relay stdout/stderr to files; without
    UTF-8 reconfigure, print() of Russian startup lines kills the process
    before serve_forever (endpoint 8787 never becomes ready).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                # line_buffering=True: flush startup diagnostics immediately when
                # PowerShell redirects relay stdout/stderr to files.
                reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
            except Exception:  # noqa: BLE001 - best-effort on exotic streams
                pass


def _safe_print(text: str = "", *, file=None) -> None:
    """Print *text* without crashing on narrow encodings (cp1252, etc.)."""
    target = sys.stdout if file is None else file
    try:
        print(text, file=target, flush=True)
        return
    except UnicodeEncodeError:
        pass
    encoding = getattr(target, "encoding", None) or "utf-8"
    try:
        raw = (text + "\n").encode(encoding, errors="replace")
        buffer = getattr(target, "buffer", None)
        if buffer is not None:
            buffer.write(raw)
            buffer.flush()
            return
    except Exception:  # noqa: BLE001 - last-resort ASCII fallback
        pass
    print(
        text.encode("ascii", errors="replace").decode("ascii"),
        file=target,
        flush=True,
    )


sys.path.insert(0, str(Path(__file__).resolve().parent))
from _kilo_guard import (  # noqa: E402
    GuardDecision,
    GuardThresholds,
    SessionHealth,
    SessionHealthThresholds,
    estimate_tokens_from_chars,
    evaluate_guard,
    evaluate_session_health,
    preview,
    summarize_body,
    suffix_preview,
)
from _kilo_relay_compress import (  # noqa: E402
    compress_chat_completion,
    is_cloud_budget_slim_mode,
    relay_compress_any_enabled,
    relay_compress_config_from_env,
    validate_slim_mode,
)
from _kilo_prompt_stats import analyze_body_text  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = os.getenv("KILO_RELAY_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("KILO_RELAY_PORT", "8787"))
# Дефолт для пустого KILO_RELAY_UPSTREAM при SLIM_MODE=cloud_budget (раньше — vsegpt как основной прокси).
CLOUD_BUDGET_DEFAULT_UPSTREAM = "https://api.vsegpt.ru"
# DeepSeek preset: KILO_RELAY_UPSTREAM_PRESET=deepseek routes to DeepSeek's OpenAI-compatible API.
# Canonical base_url per DeepSeek's quickstart docs is https://api.deepseek.com (curl example:
# POST https://api.deepseek.com/chat/completions). DeepSeek also documents a /v1-suffixed path
# for some integrations (e.g. the WorkBuddy guide uses https://api.deepseek.com/v1/chat/completions),
# so both forms work — no path rewriting is needed: this base (without /v1) + Kilo's incoming
# /v1/chat/completions path already produces a documented-working URL with exactly one /v1.
DEEPSEEK_DEFAULT_API_BASE = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-pro"
# Kimi / Moonshot: official OpenAI-SDK base_url includes /v1; see strip_openai_compat_v1_suffix().
KIMI_DEFAULT_API_BASE = "https://api.moonshot.ai/v1"
KIMI_DEFAULT_MODEL = "kimi-k3"
KIMI_ALLOWED_MODELS = frozenset({"kimi-k3", "kimi-k2.7-code-highspeed"})
KIMI_CANONICAL_HOST = "api.moonshot.ai"


_DEEPSEEK_VALID_THINKING = frozenset({"enabled", "disabled"})
# DeepSeek V4's actual documented reasoning_effort levels are high/max (its API silently maps
# low/medium up to high, xhigh up to max) -- offering low/medium here would be a fake illusion
# of granularity DeepSeek itself doesn't provide, and would silently swallow a genuine request
# for max effort if someone assumed "high" was the ceiling.
_DEEPSEEK_VALID_REASONING_EFFORT = frozenset({"high", "max"})
# "warn" (default): print + log the missing-reasoning_content signal but still forward the
# request (relay isn't independently certain enough of DeepSeek's exact validation timing to
# reject real user requests by default). "block": return a local error instead of spending a
# paid call that official docs say will very likely 400 anyway.
_DEEPSEEK_VALID_REASONING_CONTENT_GUARD = frozenset({"warn", "block"})


def deepseek_config_from_env(environ: dict[str, str]) -> dict[str, str | None] | None:
    """Return DeepSeek routing config, or None if ``KILO_RELAY_UPSTREAM_PRESET`` != deepseek.

    Fails fast (RuntimeError) if the preset is requested without ``DEEPSEEK_API_KEY`` —
    forwarding Kilo's dummy relay key to a real cloud provider would silently 401.

    ``thinking``/``reasoning_effort`` are None unless explicitly set — DeepSeek V4 defaults to
    thinking.type=enabled + reasoning_effort=high per its own API reference, which can silently
    inflate output tokens/latency/cost on every daily-coding request. This relay does not
    override that default on its own (would be an invisible quality/behavior change); it only
    exposes ``DEEPSEEK_THINKING``/``DEEPSEEK_REASONING_EFFORT`` as an explicit opt-in knob.
    """
    preset = (environ.get("KILO_RELAY_UPSTREAM_PRESET") or "").strip().lower()
    if preset != "deepseek":
        return None
    api_key = (environ.get("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "KILO_RELAY_UPSTREAM_PRESET=deepseek requires DEEPSEEK_API_KEY in the environment."
        )
    thinking = (environ.get("DEEPSEEK_THINKING") or "").strip().lower() or None
    if thinking is not None and thinking not in _DEEPSEEK_VALID_THINKING:
        raise RuntimeError(f"DEEPSEEK_THINKING must be one of {sorted(_DEEPSEEK_VALID_THINKING)}, got {thinking!r}.")
    reasoning_effort = (environ.get("DEEPSEEK_REASONING_EFFORT") or "").strip().lower() or None
    if reasoning_effort is not None and reasoning_effort not in _DEEPSEEK_VALID_REASONING_EFFORT:
        raise RuntimeError(
            f"DEEPSEEK_REASONING_EFFORT must be one of {sorted(_DEEPSEEK_VALID_REASONING_EFFORT)}, "
            f"got {reasoning_effort!r}."
        )
    if reasoning_effort is not None and thinking == "disabled":
        raise RuntimeError(
            "DEEPSEEK_REASONING_EFFORT is meaningless with DEEPSEEK_THINKING=disabled — unset "
            "one of them (reasoning_effort only applies while thinking mode is active)."
        )
    reasoning_content_guard = (environ.get("DEEPSEEK_REASONING_CONTENT_GUARD") or "warn").strip().lower()
    if reasoning_content_guard not in _DEEPSEEK_VALID_REASONING_CONTENT_GUARD:
        raise RuntimeError(
            f"DEEPSEEK_REASONING_CONTENT_GUARD must be one of {sorted(_DEEPSEEK_VALID_REASONING_CONTENT_GUARD)}, "
            f"got {reasoning_content_guard!r}."
        )
    base = (environ.get("DEEPSEEK_API_BASE") or DEEPSEEK_DEFAULT_API_BASE).strip().rstrip("/")
    validate_deepseek_api_base(base, environ)
    return {
        "base": base,
        "model": (environ.get("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL).strip(),
        "api_key": api_key,
        "thinking": thinking,
        "reasoning_effort": reasoning_effort,
        "reasoning_content_guard": reasoning_content_guard,
    }


def validate_deepseek_api_base(base: str, environ: dict[str, str]) -> None:
    """Fail fast on a base URL that would send the real DeepSeek key to the wrong place.

    A typo'd/mis-set DEEPSEEK_API_BASE (http scheme, or an unexpected host) combined with the
    unconditional Authorization override in _handle_proxy would leak the real key to that host.
    Requires https + the canonical DeepSeek host unless DEEPSEEK_ALLOW_CUSTOM_HOST=1 is set
    explicitly (e.g. for a corporate proxy in front of DeepSeek).
    """
    parsed = urlsplit(base)
    allow_custom = (environ.get("DEEPSEEK_ALLOW_CUSTOM_HOST") or "").strip().lower() in {"1", "true", "yes", "on"}
    if parsed.scheme != "https":
        raise RuntimeError(
            f"DEEPSEEK_API_BASE must use https (got {base!r}) — refusing to send the real "
            "DeepSeek API key over a non-https scheme."
        )
    if not allow_custom and parsed.hostname != "api.deepseek.com":
        raise RuntimeError(
            f"DEEPSEEK_API_BASE host {parsed.hostname!r} is not api.deepseek.com. Set "
            "DEEPSEEK_ALLOW_CUSTOM_HOST=1 explicitly if this is intentional (e.g. a proxy in "
            "front of DeepSeek) — otherwise this looks like a misconfiguration that would send "
            "the real API key to an unexpected host."
        )


def strip_openai_compat_v1_suffix(base: str) -> str:
    """Normalize an OpenAI-SDK ``base_url`` (often ends with ``/v1``) for path-join.

    Cursor/Kilo hit the relay as ``/v1/chat/completions``. Upstream URL is
    ``UPSTREAM_BASE + path``. If ``UPSTREAM_BASE`` already ends with ``/v1``, the result is the
    broken ``.../v1/v1/chat/completions``. Moonshot documents ``https://api.moonshot.ai/v1`` as
    the SDK base — strip that suffix here so join yields a single ``/v1``.
    """
    cleaned = base.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[:-3].rstrip("/")
    return cleaned


def kimi_config_from_env(environ: dict[str, str]) -> dict[str, str] | None:
    """Return Kimi/Moonshot routing config, or None if ``KILO_RELAY_UPSTREAM_PRESET`` != kimi.

    Fails fast without ``KIMI_API_KEY``. ``base`` is stored *without* a trailing ``/v1`` so
    ``UPSTREAM_BASE + /v1/chat/completions`` matches Moonshot's documented HTTP path.
    """
    preset = (environ.get("KILO_RELAY_UPSTREAM_PRESET") or "").strip().lower()
    if preset != "kimi":
        return None
    api_key = (environ.get("KIMI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "KILO_RELAY_UPSTREAM_PRESET=kimi requires KIMI_API_KEY in the environment."
        )
    model = (environ.get("KIMI_MODEL") or KIMI_DEFAULT_MODEL).strip()
    if model not in KIMI_ALLOWED_MODELS:
        raise RuntimeError(
            f"KIMI_MODEL must be one of {sorted(KIMI_ALLOWED_MODELS)}, got {model!r}."
        )
    raw_base = (environ.get("KIMI_BASE_URL") or KIMI_DEFAULT_API_BASE).strip()
    validate_kimi_api_base(raw_base, environ)
    return {
        "base": strip_openai_compat_v1_suffix(raw_base),
        "model": model,
        "api_key": api_key,
    }


def validate_kimi_api_base(base: str, environ: dict[str, str]) -> None:
    """Fail fast on a base URL that would send the real Kimi key to the wrong place."""
    parsed = urlsplit(base.strip())
    allow_custom = (environ.get("KIMI_ALLOW_CUSTOM_HOST") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if parsed.scheme != "https":
        raise RuntimeError(
            f"KIMI_BASE_URL must use https (got {base!r}) — refusing to send the real "
            "Kimi API key over a non-https scheme."
        )
    if not allow_custom and parsed.hostname != KIMI_CANONICAL_HOST:
        raise RuntimeError(
            f"KIMI_BASE_URL host {parsed.hostname!r} is not {KIMI_CANONICAL_HOST}. Set "
            "KIMI_ALLOW_CUSTOM_HOST=1 explicitly if this is intentional (e.g. a proxy) — "
            "otherwise this looks like a misconfiguration that would send the real API key "
            "to an unexpected host."
        )


_DEEPSEEK_DEVELOPER_ROLE = "developer_role_to_system"
_DEEPSEEK_NULL_TOOL_CONTENT = "null_tool_call_content_to_empty"
_DEEPSEEK_MAX_TOKENS_RENAME = "max_completion_tokens_to_max_tokens"
_DEEPSEEK_MAX_TOKENS_DROP = "dropped_redundant_max_completion_tokens"
_DEEPSEEK_TOOL_CHOICE_STRIP = "stripped_tool_choice_thinking_mode"


def effective_thinking_type(payload: dict[str, Any]) -> str:
    """Resolve the thinking mode that will actually be sent to DeepSeek for this payload.

    Reads ``payload["thinking"]["type"]`` directly rather than the env-derived ``cfg`` dict.
    By the point this runs in ``_handle_proxy``, an explicit ``DEEPSEEK_THINKING`` env override
    has already been written into ``payload["thinking"]`` (see the model/thinking/reasoning_effort
    rewrite block above) — so reading the payload itself picks up, in the correct order: the env
    override if one was set, else whatever the client itself sent, else DeepSeek's own default.

    Confirmed bug this replaces: both ``apply_deepseek_compatibility`` and
    ``detect_missing_reasoning_content`` used to read only the env ``cfg`` dict, so a client that
    sent ``{"thinking": {"type": "disabled"}}`` with no env override was treated as thinking-enabled
    (DeepSeek's default) — incorrectly stripping ``tool_choice`` and raising a false
    missing-reasoning_content warning for a payload that never needed either.
    """
    thinking = payload.get("thinking")
    if isinstance(thinking, dict):
        declared = thinking.get("type")
        if declared in _DEEPSEEK_VALID_THINKING:
            return declared
    return "enabled"  # DeepSeek's own default when the payload doesn't specify


def apply_deepseek_compatibility(payload: dict[str, Any]) -> list[str]:
    """Normalize known DeepSeek V4 payload incompatibilities; mutates ``payload`` in place.

    All four confirmed incompatible via DeepSeek's own oh_my_pi agent-integration guide.
    The guide explicitly ties ``HTTP 400`` to the tool/thinking-mode fields (``tool_choice``
    in thinking mode, null tool-call ``content``); ``developer`` role and
    ``max_completion_tokens`` are documented as unsupported/wrong-field there too, but the
    guide's own wording links the explicit 400 warning to the tool/thinking fields specifically
    — treat all four as confirmed-incompatible, not all four as independently 400-proven by a
    live test on this relay's part.
    - ``role: "developer"`` is rejected -> merged into ``system``.
    - ``tool_choice`` is rejected while thinking mode is active (DeepSeek's own default when
      DEEPSEEK_THINKING is unset is thinking=enabled, so this applies unless explicitly disabled).
    - Token limit must be ``max_tokens``, not ``max_completion_tokens``.
    - An assistant tool-call message with ``content: null`` is rejected -> set to ``""``.

    These are stateless, single-request payload facts (unlike reasoning_content, which requires
    cross-turn conversation history the relay does not own) — safe to fix here.

    Returns the list of fix names actually applied (for ``deepseek_overrides`` logging).
    """
    applied: list[str] = []

    messages = payload.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "developer":
                msg["role"] = "system"
                applied.append(_DEEPSEEK_DEVELOPER_ROLE)
            if msg.get("role") == "assistant" and msg.get("tool_calls") and msg.get("content") is None:
                msg["content"] = ""
                applied.append(_DEEPSEEK_NULL_TOOL_CONTENT)

    if "max_completion_tokens" in payload:
        if "max_tokens" not in payload:
            payload["max_tokens"] = payload.pop("max_completion_tokens")
            applied.append(_DEEPSEEK_MAX_TOKENS_RENAME)
        else:
            payload.pop("max_completion_tokens")
            applied.append(_DEEPSEEK_MAX_TOKENS_DROP)

    if effective_thinking_type(payload) == "enabled" and "tool_choice" in payload:
        payload.pop("tool_choice")
        applied.append(_DEEPSEEK_TOOL_CHOICE_STRIP)

    return applied


_DEEPSEEK_MISSING_REASONING_CONTENT_WARNING = "assistant_tool_call_missing_reasoning_content"


def detect_missing_reasoning_content(payload: dict[str, Any]) -> list[str]:
    """Stateless detection for the one DeepSeek incompatibility this relay cannot repair.

    DeepSeek requires an assistant tool-call turn's ``reasoning_content`` to be threaded back
    into every subsequent request in that conversation, or the API returns HTTP 400. The relay
    cannot *restore* a reasoning_content that Kilo's own history never carried forward (that
    requires state across requests this relay does not own) — it can only detect, in THIS
    payload, that the pattern DeepSeek's docs say causes 400 is present.

    Pure detection only — returns the list of warning names found (empty if none). Whether the
    caller merely logs this or acts on it before forwarding (see ``DEEPSEEK_REASONING_CONTENT_GUARD``
    in ``_handle_proxy``) is a separate decision; this function makes no I/O and blocks nothing.
    """
    if effective_thinking_type(payload) != "enabled":
        return []
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return []
    for msg in messages:
        if (
            isinstance(msg, dict)
            and msg.get("role") == "assistant"
            and msg.get("tool_calls")
            and not msg.get("reasoning_content")
        ):
            return [_DEEPSEEK_MISSING_REASONING_CONTENT_WARNING]
    return []


def effective_upstream_base(environ: dict[str, str]) -> str:
    """База upstream без завершающего слэша.

    Приоритет: явный ``KILO_RELAY_UPSTREAM`` (всегда побеждает) > DeepSeek / Kimi preset
    (``KILO_RELAY_UPSTREAM_PRESET=deepseek|kimi``) > ``SLIM_MODE=cloud_budget`` дефолт
    (``CLOUD_BUDGET_DEFAULT_UPSTREAM`` / ``KILO_RELAY_CLOUD_DEFAULT_UPSTREAM``) >
    LM Studio ``http://127.0.0.1:1234``.
    """
    raw = (environ.get("KILO_RELAY_UPSTREAM") or "").strip().rstrip("/")
    if raw:
        return raw
    deepseek = deepseek_config_from_env(environ)
    if deepseek is not None:
        return deepseek["base"]
    kimi = kimi_config_from_env(environ)
    if kimi is not None:
        return kimi["base"]
    slim = environ.get("KILO_RELAY_SLIM_MODE", "local")
    if is_cloud_budget_slim_mode(slim):
        return (environ.get("KILO_RELAY_CLOUD_DEFAULT_UPSTREAM") or CLOUD_BUDGET_DEFAULT_UPSTREAM).strip().rstrip(
            "/"
        )
    return (environ.get("KILO_RELAY_UPSTREAM_DEFAULT_LOCAL") or "http://127.0.0.1:1234").strip().rstrip("/")


def _deepseek_actually_active(environ: dict[str, str]) -> bool:
    """Whether DeepSeek is the ACTUAL resolved provider, not merely whether the preset var is set.

    ``effective_upstream_base()`` already gives explicit ``KILO_RELAY_UPSTREAM`` top priority over
    the DeepSeek preset. DeepSeek-specific behavior (Authorization override, model rewrite) must
    respect that same precedence — otherwise a stale ``KILO_RELAY_UPSTREAM_PRESET=deepseek`` left
    over from a previous run, combined with an explicit raw ``KILO_RELAY_UPSTREAM`` override,
    would route to the raw upstream while still leaking the real DeepSeek API key to it and
    rewriting the model — confirmed by direct testing, not hypothetical.
    """
    raw = (environ.get("KILO_RELAY_UPSTREAM") or "").strip()
    if raw:
        return False
    return (environ.get("KILO_RELAY_UPSTREAM_PRESET") or "").strip().lower() == "deepseek"


def _kimi_actually_active(environ: dict[str, str]) -> bool:
    """Whether Kimi is the ACTUAL resolved provider (same raw-override precedence as DeepSeek)."""
    raw = (environ.get("KILO_RELAY_UPSTREAM") or "").strip()
    if raw:
        return False
    return (environ.get("KILO_RELAY_UPSTREAM_PRESET") or "").strip().lower() == "kimi"


UPSTREAM_BASE = effective_upstream_base(dict(os.environ))
DEEPSEEK_CFG = deepseek_config_from_env(dict(os.environ)) if _deepseek_actually_active(dict(os.environ)) else None
KIMI_CFG = kimi_config_from_env(dict(os.environ)) if _kimi_actually_active(dict(os.environ)) else None
_t_raw = os.getenv("KILO_RELAY_UPSTREAM_TIMEOUT", "120").strip()
UPSTREAM_TIMEOUT = float(_t_raw if _t_raw else "120")
LOG_PATH = (ROOT / os.getenv("KILO_RELAY_LOG", "logs/kilo_relay.jsonl")).resolve()
PREVIEW_CHARS = int(os.getenv("KILO_RELAY_PREVIEW_CHARS", "800"))
def log_full_body_from_env(environ: dict[str, str]) -> bool:
    """Secure by default: full-body logging OFF unless explicitly opted into.

    Start-KiloRelayDaily.ps1 already sets KILO_RELAY_FULL_BODY explicitly either way; a direct
    `python kilo_proxy_relay.py` run must not silently dump source/credentials/paths to disk.
    """
    return (environ.get("KILO_RELAY_FULL_BODY") or "0").strip().lower() in {"1", "true", "yes", "on"}


LOG_FULL_BODY = log_full_body_from_env(dict(os.environ))


def normalize_chat_completions_path(path: str) -> str:
    """Recognize /v1/chat/completions regardless of trailing slash or query string.

    Also treats a bare /chat/completions as equivalent (defensive: some OpenAI-compatible
    clients/providers omit the /v1 prefix) so compression/guard/model-rewrite aren't silently
    skipped just because of URL shape.
    """
    normalized = urlsplit(path).path.rstrip("/")
    if normalized in ("/v1/chat/completions", "/chat/completions"):
        return "/v1/chat/completions"
    return normalized
WARN_BODY_CHARS = int(os.getenv("KILO_RELAY_WARN_BODY_CHARS", "70000"))
MAX_BODY_CHARS = int(os.getenv("KILO_RELAY_MAX_BODY_CHARS", "90000"))
HARD_BLOCK_BODY_CHARS = int(os.getenv("KILO_RELAY_HARD_BLOCK_BODY_CHARS", "110000"))
MAX_MESSAGES = int(os.getenv("KILO_RELAY_MAX_MESSAGES", "15"))
MAX_LARGEST_MESSAGE_CHARS = int(os.getenv("KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS", "24000"))
MAX_TOOLS = int(os.getenv("KILO_RELAY_MAX_TOOLS", "16"))


def _resolve_guard_mode(env: dict[str, str], *, slim_mode: str) -> str:
    """``warn`` by default; ``cloud_budget`` defaults to ``block`` when unset.

    After compress is proven, block mode is the safety net: a compressor
    regression must not forward a 1MB original body upstream. Explicit
    ``KILO_RELAY_GUARD_MODE`` always wins.
    """
    raw = (env.get("KILO_RELAY_GUARD_MODE") or "").strip().lower()
    if raw:
        return raw
    if is_cloud_budget_slim_mode(slim_mode):
        return "block"
    return "warn"


_SLIM_FOR_GUARD = os.getenv("KILO_RELAY_SLIM_MODE", "local")
try:
    _SLIM_FOR_GUARD = validate_slim_mode(_SLIM_FOR_GUARD)
except ValueError:
    _SLIM_FOR_GUARD = "local"
GUARD_MODE = _resolve_guard_mode(dict(os.environ), slim_mode=_SLIM_FOR_GUARD)
THRESHOLDS = GuardThresholds(
    warn_body_chars=WARN_BODY_CHARS,
    max_body_chars=MAX_BODY_CHARS,
    hard_block_body_chars=HARD_BLOCK_BODY_CHARS,
    max_messages=MAX_MESSAGES,
    max_largest_message_chars=MAX_LARGEST_MESSAGE_CHARS,
    max_tools=MAX_TOOLS,
)
SESSION_HEALTH_THRESHOLDS = SessionHealthThresholds.from_env()
SSL_CONTEXT = ssl.create_default_context()
LOG_LOCK = threading.Lock()
RELAY_COMPRESS_CFG = relay_compress_config_from_env(dict(os.environ))
RELAY_COMPRESS_ACTIVE = relay_compress_any_enabled(RELAY_COMPRESS_CFG)
BUFFER_STREAM = os.getenv("KILO_RELAY_BUFFER_STREAM", "0").strip().lower() in {"1", "true", "yes", "on"}
# Compact pollution stats in JSONL (fragment/path/tool breakdown). Default ON.
CONTENT_STATS = os.getenv("KILO_RELAY_CONTENT_STATS", "1").strip().lower() not in {"0", "false", "no", "off"}
# Keep per-message previews in JSONL (bloated). Default OFF when content_stats covers audit needs.
MESSAGE_STATS_IN_LOG = os.getenv("KILO_RELAY_MESSAGE_STATS", "0").strip().lower() in {"1", "true", "yes", "on"}
# Hop-by-hop / пересчитываемые у прокси — не копируем с upstream на клиент
_SKIP_PROXY_RESPONSE_HEADERS = frozenset(
    {"content-length", "transfer-encoding", "connection", "content-encoding", "keep-alive"}
)
READ_CHUNK = 65536


def sanitize_request_summary_for_log(summary: dict[str, Any]) -> dict[str, Any]:
    """Drop heavy previews/message_stats from JSONL unless explicitly enabled."""
    out = dict(summary)
    if MESSAGE_STATS_IN_LOG or LOG_FULL_BODY:
        return out
    out.pop("message_stats", None)
    out.pop("body_preview_start", None)
    out.pop("body_preview_end", None)
    return out


def _payload_stream_enabled(value: Any) -> bool:
    """Тот же смысл, что OpenAI stream: true — tolerates int 1 / строку (хрупкие клиенты/прокси)."""
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int) and value == 1:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return False


def _format_for_dump(val: Any) -> str:
    if isinstance(val, frozenset):
        return repr(sorted(val))
    return repr(val)


def _startup_budget_warnings(environ: dict[str, str] | None = None) -> list[str]:
    """Non-fatal operator hints (cloud preset without cloud_budget, default local, …)."""
    env = dict(os.environ) if environ is None else environ
    warnings: list[str] = []
    if _deepseek_actually_active(env):
        provider = "DeepSeek"
    elif _kimi_actually_active(env):
        provider = "Kimi"
    else:
        return warnings
    slim_raw = env.get("KILO_RELAY_SLIM_MODE")
    if slim_raw is None or not str(slim_raw).strip():
        warnings.append(
            f"WARN: {provider} preset active but KILO_RELAY_SLIM_MODE unset "
            "(defaults to local: system stub + Cursor tool allowlist). "
            f"For Cursor→{provider} without quality loss set KILO_RELAY_SLIM_MODE=cloud_budget."
        )
        return warnings
    try:
        slim = validate_slim_mode(str(slim_raw))
    except ValueError:
        return warnings
    if slim in {"off", "passthrough", "false", "0", "no", "disabled"}:
        warnings.append(
            f"WARN: {provider} preset active with SLIM_MODE=off — no input compression. "
            f"For Cursor→{provider} prefer KILO_RELAY_SLIM_MODE=cloud_budget."
        )
    elif slim == "local":
        warnings.append(
            f"WARN: {provider} preset + SLIM_MODE=local stubs Cursor system and restricts tools. "
            f"For Cursor→{provider} without quality loss use KILO_RELAY_SLIM_MODE=cloud_budget."
        )
    return warnings


def build_startup_modes_report_lines(bound_host: str, bound_port: int) -> list[str]:
    """Human-readable snapshot of relay bind guard compress + env (KILO_RELAY_*)."""
    env_snapshot = dict(os.environ)
    deepseek_active = _deepseek_actually_active(env_snapshot)
    kimi_active = _kimi_actually_active(env_snapshot)
    slim_raw = os.environ.get("KILO_RELAY_SLIM_MODE", "<unset → default local>")
    cloud_budget_default_host = (
        not (os.environ.get("KILO_RELAY_UPSTREAM") or "").strip()
        and is_cloud_budget_slim_mode(os.environ.get("KILO_RELAY_SLIM_MODE", "local"))
        and not deepseek_active
        and not kimi_active
    )
    lines: list[str] = [
        "=== kilo_proxy_relay: режим текущего запуска ===",
        "[bind]",
        f"  KILO_RELAY_HOST preference={DEFAULT_HOST!r}",
        f"  KILO_RELAY_PORT preference={DEFAULT_PORT}",
        f"  LISTEN EFFECTIVE=http://{bound_host}:{bound_port}/",
        "[upstream]",
        f"  KILO_RELAY_UPSTREAM raw={os.environ.get('KILO_RELAY_UPSTREAM', '')!r}",
        f"  UPSTREAM_BASE used={UPSTREAM_BASE!r}"
        + (
            " ← default host for cloud_budget (api.vsegpt.ru; переопределите KILO_RELAY_CLOUD_DEFAULT_UPSTREAM)"
            if cloud_budget_default_host
            else ""
        ),
        f"  KILO_RELAY_UPSTREAM_TIMEOUT effective={UPSTREAM_TIMEOUT!r}",
        "[logging]",
        f"  KILO_RELAY_LOG → {LOG_PATH}",
        f"  KILO_RELAY_FULL_BODY={'yes' if LOG_FULL_BODY else 'no'} PREVIEW_CHARS={PREVIEW_CHARS}",
        f"  KILO_RELAY_CONTENT_STATS={'yes' if CONTENT_STATS else 'no'} "
        f"MESSAGE_STATS_IN_LOG={'yes' if MESSAGE_STATS_IN_LOG else 'no'}",
        "[proxy]",
        f"  KILO_RELAY_BUFFER_STREAM={'yes' if BUFFER_STREAM else 'no'} "
        f"(yes = полный буфер upstream, как до стрим-пути)",
        "[guard / _kilo_guard]",
        "  mode/threshold (effective)",
        f"    GUARD_MODE={GUARD_MODE!r}",
        f"    warn_body_chars={THRESHOLDS.warn_body_chars}",
        f"    max_body_chars={THRESHOLDS.max_body_chars}",
        f"    hard_block_body_chars={THRESHOLDS.hard_block_body_chars}",
        f"    max_messages={THRESHOLDS.max_messages}",
        f"    max_largest_message_chars={THRESHOLDS.max_largest_message_chars}",
        f"    max_tools={THRESHOLDS.max_tools}",
        "    note: warn/soft_block/hard_block are labels; HTTP 413 only when GUARD_MODE=block",
        "  session health (original / pre-compress — does not HTTP-block)",
        f"    warn_estimated_tokens={SESSION_HEALTH_THRESHOLDS.warn_estimated_tokens}",
        f"    warn_messages={SESSION_HEALTH_THRESHOLDS.warn_messages}",
        f"    warn_body_chars={SESSION_HEALTH_THRESHOLDS.warn_body_chars}",
        "    note: when triggered → stderr `session=bloated … recommend=new_chat`",
        "[compress / _kilo_relay_compress]",
        f"  RELAY_COMPRESS_ACTIVE={'yes' if RELAY_COMPRESS_ACTIVE else 'no'}",
    ]
    if RELAY_COMPRESS_ACTIVE:
        d = asdict(RELAY_COMPRESS_CFG)
        for key in sorted(d.keys()):
            lines.append(f"  compress.{key}={_format_for_dump(d[key])}")
    else:
        lines.append(f"  compress inactive (KILO_RELAY_SLIM_MODE={slim_raw!r}; full dump omitted)")

    lines.append("[deepseek preset]")
    if DEEPSEEK_CFG is not None:
        lines.append(f"  active=yes base={DEEPSEEK_CFG['base']!r} model={DEEPSEEK_CFG['model']!r}")
        lines.append(f"  thinking={DEEPSEEK_CFG.get('thinking')!r} reasoning_effort={DEEPSEEK_CFG.get('reasoning_effort')!r}")
    elif (os.environ.get("KILO_RELAY_UPSTREAM_PRESET") or "").strip().lower() == "deepseek":
        lines.append("  active=no (raw KILO_RELAY_UPSTREAM overrides preset; auth/model rewrite off)")
    else:
        lines.append("  active=no")

    lines.append("[kimi preset]")
    if KIMI_CFG is not None:
        lines.append(f"  active=yes base={KIMI_CFG['base']!r} model={KIMI_CFG['model']!r}")
        lines.append(f"  allowed_models={sorted(KIMI_ALLOWED_MODELS)!r}")
    elif (os.environ.get("KILO_RELAY_UPSTREAM_PRESET") or "").strip().lower() == "kimi":
        lines.append("  active=no (raw KILO_RELAY_UPSTREAM overrides preset; auth/model rewrite off)")
    else:
        lines.append("  active=no")

    lines.append("[env overrides KILO_RELAY_*]")
    lines.append(f"  KILO_RELAY_SLIM_MODE raw={slim_raw!r}")
    for name in sorted(k for k in os.environ if k.startswith("KILO_RELAY_")):
        if name == "KILO_RELAY_SLIM_MODE":
            continue
        lines.append(f"  {name}={os.environ[name]!r}")
    for warn in _startup_budget_warnings(env_snapshot):
        lines.append(warn)
    lines.append("=== конец режимов ===")
    return lines


def print_startup_modes(bound_host: str, bound_port: int) -> None:
    for ln in build_startup_modes_report_lines(bound_host, bound_port):
        if ln.startswith("WARN:"):
            _safe_print(ln, file=sys.stderr)
        else:
            _safe_print(ln)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact anything is_sensitive_header_name flags before this ever reaches the JSONL log.

    Confirmed bug (fixed here): previously only matched "Authorization" and names containing
    "api-key" or ending in "key" — Cookie, Proxy-Authorization, X-Auth-Token and similar
    credential headers were written to disk in plaintext, unconditionally, on every request.
    """
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            redacted[key] = "Bearer ***REDACTED***"
        elif is_sensitive_header_name(key):
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def _override_authorization(headers: dict[str, str], bearer_token: str) -> None:
    """Replace whatever Authorization Kilo sent (its dummy relay key) with the real upstream key."""
    for key in [k for k in headers if k.lower() == "authorization"]:
        del headers[key]
    headers["Authorization"] = f"Bearer {bearer_token}"


def write_jsonl(record: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with LOG_LOCK:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line)


_COMPACT_REQUEST_KEYS = (
    "json_valid",
    "model",
    "messages_count",
    "tools_count",
    "body_chars",
    "estimated_tokens",
    "total_message_chars",
    "largest_message_chars",
    "role_chars",
)


def compact_request_stats(summary: dict[str, Any]) -> dict[str, Any]:
    """Drop previews from summarize_body for JSONL original/forwarded pair."""
    return {k: summary[k] for k in _COMPACT_REQUEST_KEYS if k in summary}


def normalize_usage_dict(usage: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_tokens_details", "completion_tokens_details"):
        if key in usage:
            out[key] = usage[key]
    return out


def extract_usage_from_response_body(body_text: str) -> dict[str, Any] | None:
    """Parse OpenAI-style usage from JSON body or last SSE data: event that carries usage."""
    if not body_text:
        return None
    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("usage"), dict):
        return normalize_usage_dict(payload["usage"])

    last: dict[str, Any] | None = None
    for line in body_text.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("usage"), dict):
            last = normalize_usage_dict(obj["usage"])
    return last


def _content_stats_glance(content_stats: dict[str, Any] | None) -> list[str]:
    """Short stderr hints from content_stats.

    ``top_kind`` / ``top_path`` prefer *original* (pre-compress pollution size).
    ``top_frag`` prefers *forwarded* so stripped XML (skills/rules/…) does not
    keep showing up after cloud_budget already removed it from the upstream body.
    """
    if not isinstance(content_stats, dict):
        return []
    original = content_stats.get("original")
    forwarded = content_stats.get("forwarded")
    bulk = original if isinstance(original, dict) else forwarded
    if not isinstance(bulk, dict):
        return []
    parts: list[str] = []
    kinds = bulk.get("kind_chars")
    if isinstance(kinds, dict) and kinds:
        top_kind, top_chars = next(iter(kinds.items()))
        parts.append(f"top_kind={top_kind}:{top_chars}")
    paths = bulk.get("path_chars")
    if isinstance(paths, list) and paths:
        row0 = paths[0]
        if isinstance(row0, dict) and row0.get("path") is not None:
            parts.append(f"top_path={row0['path']}:{row0.get('chars', '?')}")
    # Prefer forwarded fragments when that side was computed (even if empty —
    # empty means strips worked; do not fall back to original and re-show them).
    if isinstance(forwarded, dict):
        frags = forwarded.get("fragment_chars")
    else:
        frags = bulk.get("fragment_chars")
    if isinstance(frags, dict) and frags:
        fk, fc = next(iter(frags.items()))
        parts.append(f"top_frag={fk}:{fc}")
    return parts


def format_request_mini_stats(
    *,
    method: str,
    path: str,
    status: int,
    elapsed_ms: float,
    request_summary: dict[str, Any],
    guard_level: str,
    guard_mode: str,
    guard_blocked: bool,
    stream: bool,
    compress_summary: dict[str, Any] | None = None,
    request_original: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    content_stats: dict[str, Any] | None = None,
    response_chars: int | None = None,
    error: str | None = None,
    session_health: SessionHealth | None = None,
) -> str:
    """One-line console summary after each proxied request (stderr)."""
    parts: list[str] = [
        f"[relay] {method} {path} → {status}",
        f"{elapsed_ms:g}ms",
    ]
    fwd_chars = request_summary.get("body_chars")
    orig_chars = request_original.get("body_chars") if isinstance(request_original, dict) else None
    if orig_chars is not None and fwd_chars is not None and orig_chars != fwd_chars:
        parts.append(f"body_orig={orig_chars}")
        est = request_summary.get("estimated_tokens")
        if est is not None:
            parts.append(f"body_fwd={fwd_chars} (~{est} tok)")
        else:
            parts.append(f"body_fwd={fwd_chars}")
    elif fwd_chars is not None:
        est = request_summary.get("estimated_tokens")
        label = "body_fwd" if request_original is not None else "body"
        if est is not None:
            parts.append(f"{label}={fwd_chars} (~{est} tok)")
        else:
            parts.append(f"{label}={fwd_chars}")
    stats_src = request_summary if request_summary.get("json_valid") else (
        request_original if isinstance(request_original, dict) and request_original.get("json_valid") else None
    )
    if stats_src:
        parts.append(f"msgs={stats_src.get('messages_count', 0)}")
        parts.append(f"tools={stats_src.get('tools_count', 0)}")
        largest = stats_src.get("largest_message_chars")
        if largest:
            parts.append(f"max_msg={largest}")
        model = stats_src.get("model")
        if model:
            parts.append(f"model={model}")
    blocked_txt = "yes" if guard_blocked else "no"
    parts.append(f"guard={guard_level} mode={guard_mode} blocked={blocked_txt}")
    parts.append("stream=yes" if stream else "stream=no")
    if isinstance(compress_summary, dict) and compress_summary.get("enabled"):
        saved = compress_summary.get("chars_saved_estimate")
        if saved is not None:
            parts.append(f"saved={saved}")
        hist_dropped = compress_summary.get("messages_dropped_history")
        if hist_dropped:
            parts.append(f"hist_cut={hist_dropped}")
        tr_capped = compress_summary.get("tool_results_capped")
        if tr_capped:
            parts.append(f"tr_capped={tr_capped}")
    if isinstance(usage, dict):
        pin = usage.get("prompt_tokens")
        pout = usage.get("completion_tokens")
        if pin is not None or pout is not None:
            parts.append(f"in={pin if pin is not None else '?'} out={pout if pout is not None else '?'}")
    parts.extend(_content_stats_glance(content_stats))
    if session_health is not None and session_health.recommend_new_chat:
        parts.append(
            f"session=bloated orig_msgs={session_health.original_messages} "
            f"orig_tok≈{session_health.original_estimated_tokens} recommend=new_chat"
        )
    if response_chars is not None:
        parts.append(f"resp={response_chars}")
    if error:
        parts.append(f"err={error}")
    return " ".join(parts)


@dataclass
class UpstreamResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    error: str | None = None


def build_guard_response(decision: GuardDecision, request_summary: dict[str, Any]) -> UpstreamResponse:
    message = (
        "Blocked by local Kilo relay guard before provider call. "
        f"Level: {decision.level}. "
        f"Reasons: {', '.join(decision.reasons)}. "
        "Reduce session history/read-set or start a fresh session."
    )
    payload = {
        "error": {
            "message": message,
            "code": "relay_context_guard_blocked",
            "guard_mode": GUARD_MODE,
            "guard_level": decision.level,
            "reasons": decision.reasons,
            "risk_flags": decision.risk_flags,
            "request_stats": {
                "body_chars": request_summary.get("body_chars"),
                "messages_count": request_summary.get("messages_count"),
                "largest_message_chars": request_summary.get("largest_message_chars"),
                "tools_count": request_summary.get("tools_count"),
            },
        }
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return UpstreamResponse(
        status=413,
        headers={"content-type": "application/json; charset=utf-8"},
        body=body,
        error="blocked by local relay guard",
    )


def build_reasoning_content_guard_response(warnings: list[str]) -> UpstreamResponse:
    """Local, free error for DEEPSEEK_REASONING_CONTENT_GUARD=block — used only when an
    assistant tool-call message is missing reasoning_content while thinking mode is active,
    which DeepSeek's own docs say causes HTTP 400. Saves the paid upstream call entirely."""
    payload = {
        "error": {
            "message": (
                "Blocked by local Kilo relay before provider call: an assistant message with "
                "tool_calls is missing reasoning_content while DeepSeek thinking mode is active. "
                "DeepSeek's API returns HTTP 400 for this pattern. Set "
                "DEEPSEEK_REASONING_CONTENT_GUARD=warn to forward anyway, or fix the client's "
                "history to carry reasoning_content forward."
            ),
            "code": "relay_deepseek_reasoning_content_missing",
            "warnings": warnings,
        }
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return UpstreamResponse(
        status=422,
        headers={"content-type": "application/json; charset=utf-8"},
        body=body,
        error="blocked by local relay: missing reasoning_content",
    )


def _write_wfile_best_effort(wfile: Any, data: bytes) -> None:
    """Write response body; ignore client disconnect (cancel / UI closed socket)."""
    try:
        wfile.write(data)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        return


def _send_compress_trace_headers(handler: BaseHTTPRequestHandler, compress_summary: dict[str, Any]) -> None:
    if not isinstance(compress_summary, dict) or not compress_summary.get("enabled"):
        return
    handler.send_header("X-Kilo-Relay-Via", "1")
    handler.send_header("X-Kilo-Relay-Tools-Before", str(compress_summary.get("tools_before", "")))
    handler.send_header("X-Kilo-Relay-Tools-After", str(compress_summary.get("tools_after", "")))
    handler.send_header(
        "X-Kilo-Relay-Chars-Saved",
        str(compress_summary.get("chars_saved_estimate", "")),
    )
    stub = compress_summary.get("cursor_system_stubbed")
    handler.send_header("X-Kilo-Relay-System-Stubbed", "1" if stub else "0")


# Hop-by-hop headers (RFC 7230 §6.1 / RFC 9112) plus Accept-Encoding: this relay never
# decompresses responses and already strips Content-Encoding from what it hands back to the
# client, so advertising gzip/deflate/br support to upstream would risk handing the client
# undecodable compressed bytes with no header telling it so (mitigates the main gzip-corruption
# scenario; does not itself guarantee upstream never compresses — a belt-and-suspenders fix
# would decode the response or preserve Content-Encoding instead of stripping it).
# transfer-encoding/proxy-connection were a confirmed gap: this handler has no chunked
# request-body support (reads only Content-Length), so forwarding a stray
# Transfer-Encoding: chunked from the client would misrepresent the framing of what's actually
# being sent — RFC 9112 treats incorrect framing headers as a request-smuggling risk class.
_ALWAYS_STRIP_REQUEST_HEADERS = frozenset(
    {
        "host", "content-length", "connection", "accept-encoding",
        "te", "trailer", "upgrade", "keep-alive", "transfer-encoding", "proxy-connection",
    }
)


def _connection_listed_headers(headers: dict[str, str]) -> set[str]:
    """RFC 7230 §6.1: Connection may list additional header names that are hop-by-hop for this
    specific message (e.g. ``Connection: X-Internal`` means X-Internal must not be forwarded)."""
    listed: set[str] = set()
    for key, value in headers.items():
        if key.lower() == "connection":
            listed.update(part.strip().lower() for part in value.split(",") if part.strip())
    return listed


# Single source of truth for "this header name looks like it carries a credential/session
# secret" — used both to decide what NOT to forward to a real internet host (DeepSeek) and
# what MUST be redacted before writing to the JSONL log (including *response* headers from
# upstream, e.g. Set-Cookie — session cookies from a real provider response are just as
# sensitive as request-side credentials). Previously these were two separate, inconsistent
# lists: the forward-filter caught Cookie/Proxy-Authorization/etc., but redact_headers() below
# only ever matched "Authorization" and names containing "api-key" or ending in "key" — meaning
# Cookie/Proxy-Authorization/X-Auth-Token/custom session headers were written to disk in
# plaintext on every single request, unconditionally (not gated by KILO_RELAY_FULL_BODY).
# Confirmed bug, fixed by unifying both call sites on one classifier with deliberately broad
# substrings (favors over-redaction of a non-secret debug header over missing a real secret).
_SENSITIVE_HEADER_EXACT_NAMES = frozenset(
    {
        "authorization", "cookie", "cookie2", "set-cookie", "set-cookie2",
        "proxy-authorization", "authentication-info", "proxy-authentication-info",
        "x-api-key", "x-auth-token", "x-access-token", "x-csrf-token",
        "x-session-token", "x-refresh-token", "x-bearer-token", "x-amz-security-token",
    }
)
_SENSITIVE_HEADER_SUBSTRINGS = ("cookie", "token", "secret", "auth", "session")


def is_sensitive_header_name(name: str) -> bool:
    """Whether a header name commonly carries a credential/session value.

    Deliberately broad — substring match on "cookie"/"token"/"secret"/"auth"/"session" catches
    custom/vendor header naming conventions this relay hasn't seen yet, not just the literal
    names above. Over-redacting an occasional non-secret debug header (e.g. WWW-Authenticate)
    is an acceptable cost; missing a real credential is not.
    """
    low = name.lower()
    if low in _SENSITIVE_HEADER_EXACT_NAMES:
        return True
    if low.endswith("key"):
        return True
    return any(s in low for s in _SENSITIVE_HEADER_SUBSTRINGS)


def _prepare_upstream_request_headers(headers: dict[str, str]) -> dict[str, str]:
    """Filter client headers before forwarding upstream.

    Always strips hop-by-hop/recomputed headers, Accept-Encoding (see comment above), and any
    header dynamically listed inside the client's own Connection header. When a cloud preset
    (DeepSeek or Kimi) is active, additionally drops every header ``is_sensitive_header_name``
    flags except Authorization itself (already overwritten with the real upstream key by
    ``_override_authorization`` and must be forwarded) — a real internet host has no legitimate
    reason to see the client's own Cookie/Proxy-Authorization/session headers. This is still a
    blocklist, not an allowlist: unmatched headers (User-Agent, Accept, X-Request-ID, Forwarded,
    other custom X-* headers) are still forwarded as-is.
    """
    strip = set(_ALWAYS_STRIP_REQUEST_HEADERS) | _connection_listed_headers(headers)
    if DEEPSEEK_CFG is not None or KIMI_CFG is not None:
        strip |= {k.lower() for k in headers if k.lower() != "authorization" and is_sensitive_header_name(k)}
    return {k: v for k, v in headers.items() if k.lower() not in strip}


def _copy_upstream_response_headers(handler: BaseHTTPRequestHandler, upstream_headers: dict[str, str]) -> None:
    for key, value in upstream_headers.items():
        if key.lower() in _SKIP_PROXY_RESPONSE_HEADERS:
            continue
        handler.send_header(key, value)


def _send_json_client(handler: BaseHTTPRequestHandler, status: int, headers: dict[str, str], body: bytes) -> None:
    handler.send_response(status)
    _copy_upstream_response_headers(handler, headers)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    _write_wfile_best_effort(handler.wfile, body)


def forward_request_streaming(
    method: str,
    path: str,
    headers: dict[str, str],
    body: bytes,
    handler: BaseHTTPRequestHandler,
    compress_summary: dict[str, Any],
) -> UpstreamResponse:
    """Проксировать SSE: те же байты, что от upstream, без HTTP chunked.

    Ручной Transfer-Encoding: chunked через BaseHTTPRequestHandler давал клиенту
    Cursor «Error parsing response» / невалидный JSON (фрагменты или артефакты).
    RFC 7230: при отсутствии Content-Length и TE тело до закрытия соединения.
    HTTP/1.0 + Connection: close — максимально совместимый вариант для потока.
    """
    upstream_url = f"{UPSTREAM_BASE}{path}"
    req_headers = _prepare_upstream_request_headers(headers)
    request = Request(upstream_url, data=body, headers=req_headers, method=method)
    accumulated = bytearray()
    try:
        resp = urlopen(request, timeout=UPSTREAM_TIMEOUT, context=SSL_CONTEXT)
    except HTTPError as exc:
        err_body = exc.read()
        _send_json_client(handler, exc.code, dict(exc.headers.items()), err_body)
        return UpstreamResponse(status=exc.code, headers=dict(exc.headers.items()), body=err_body, error=str(exc))
    except URLError as exc:
        err = json.dumps({"error": {"message": str(exc.reason), "code": "relay_upstream_unreachable"}}).encode("utf-8")
        _send_json_client(
            handler,
            502,
            {"content-type": "application/json; charset=utf-8"},
            err,
        )
        return UpstreamResponse(
            status=502,
            headers={"content-type": "application/json; charset=utf-8"},
            body=err,
            error=str(exc),
        )
    try:
        status = resp.status
        resp_headers = dict(resp.headers.items())
        # Ответ без chunked: иначе Cursor/OpenAI-клиент ломает разбор SSE/JSON.
        handler.protocol_version = "HTTP/1.0"
        handler.send_response(status)
        _send_compress_trace_headers(handler, compress_summary)
        _copy_upstream_response_headers(handler, resp_headers)
        handler.send_header("Connection", "close")
        handler.close_connection = True
        handler.end_headers()

        client_gone = False
        wfile = handler.wfile
        read_err: str | None = None
        while True:
            try:
                chunk = resp.read(READ_CHUNK)
            except (OSError, http.client.IncompleteRead) as exc:
                read_err = str(exc)
                break
            if not chunk:
                break
            accumulated.extend(chunk)
            if client_gone:
                continue
            try:
                wfile.write(chunk)
                wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                client_gone = True

        return UpstreamResponse(status=status, headers=resp_headers, body=bytes(accumulated), error=read_err)
    finally:
        resp.close()


def forward_request(method: str, path: str, headers: dict[str, str], body: bytes) -> UpstreamResponse:
    upstream_url = f"{UPSTREAM_BASE}{path}"
    req_headers = _prepare_upstream_request_headers(headers)
    request = Request(upstream_url, data=body, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=UPSTREAM_TIMEOUT, context=SSL_CONTEXT) as resp:
            try:
                body = resp.read()
            except (OSError, http.client.IncompleteRead) as exc:
                err = json.dumps(
                    {"error": {"message": str(exc), "code": "relay_upstream_read_error"}},
                    ensure_ascii=False,
                ).encode("utf-8")
                return UpstreamResponse(
                    status=502,
                    headers={"content-type": "application/json; charset=utf-8"},
                    body=err,
                    error=str(exc),
                )
            return UpstreamResponse(
                status=resp.status,
                headers=dict(resp.headers.items()),
                body=body,
            )
    except HTTPError as exc:
        return UpstreamResponse(
            status=exc.code,
            headers=dict(exc.headers.items()),
            body=exc.read(),
            error=str(exc),
        )
    except URLError as exc:
        err = json.dumps({"error": {"message": str(exc.reason), "code": "relay_upstream_unreachable"}}).encode("utf-8")
        return UpstreamResponse(
            status=502,
            headers={"content-type": "application/json; charset=utf-8"},
            body=err,
            error=str(exc),
        )


class RelayHandler(BaseHTTPRequestHandler):
    server_version = "KiloRelay/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        message = "%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args)
        sys.stderr.write(message)

    def log_request(self, code: Any = "-", size: Any = "-") -> None:  # noqa: ANN401
        # Default access line is replaced by format_request_mini_stats after the request.
        return

    def do_POST(self) -> None:  # noqa: N802
        self._handle_proxy()

    def do_GET(self) -> None:  # noqa: N802
        self._handle_proxy()

    def _handle_proxy(self) -> None:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        content_length = int(self.headers.get("Content-Length") or "0")
        # Immediate visibility: long upstream calls otherwise look like "relay is silent".
        _safe_print(
            f"[relay] → {self.command} {self.path} bytes={content_length} id={request_id[:8]}",
            file=sys.stderr,
        )
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        body_text = raw_body.decode("utf-8", errors="replace")
        request_headers = {k: v for k, v in self.headers.items()}
        if DEEPSEEK_CFG is not None:
            _override_authorization(request_headers, DEEPSEEK_CFG["api_key"])
        elif KIMI_CFG is not None:
            _override_authorization(request_headers, KIMI_CFG["api_key"])
        forwarded_body_bytes = raw_body
        compress_summary: dict[str, Any] = {"enabled": False}
        stream_source: dict[str, Any] | None = None
        request_original: dict[str, Any] | None = (
            compact_request_stats(summarize_body(body_text, PREVIEW_CHARS)) if raw_body else None
        )
        content_stats_original: dict[str, Any] | None = None
        content_stats_forwarded: dict[str, Any] | None = None

        chat_path = normalize_chat_completions_path(self.path)
        if CONTENT_STATS and raw_body and chat_path == "/v1/chat/completions":
            content_stats_original = analyze_body_text(body_text)

        deepseek_overrides: dict[str, Any] = {}
        kimi_overrides: dict[str, Any] = {}
        reasoning_content_blocked = False
        if chat_path == "/v1/chat/completions" and raw_body:
            try:
                payload_json = json.loads(body_text)
            except json.JSONDecodeError:
                payload_json = None
            if isinstance(payload_json, dict):
                payload_overridden = False
                if DEEPSEEK_CFG is not None:
                    if payload_json.get("model") != DEEPSEEK_CFG["model"]:
                        payload_json["model"] = DEEPSEEK_CFG["model"]
                        payload_overridden = True
                        deepseek_overrides["model"] = DEEPSEEK_CFG["model"]
                    if DEEPSEEK_CFG["thinking"] is not None:
                        payload_json["thinking"] = {"type": DEEPSEEK_CFG["thinking"]}
                        payload_overridden = True
                        deepseek_overrides["thinking"] = DEEPSEEK_CFG["thinking"]
                    if DEEPSEEK_CFG["reasoning_effort"] is not None:
                        payload_json["reasoning_effort"] = DEEPSEEK_CFG["reasoning_effort"]
                        payload_overridden = True
                        deepseek_overrides["reasoning_effort"] = DEEPSEEK_CFG["reasoning_effort"]
                    compat_fixes = apply_deepseek_compatibility(payload_json)
                    if compat_fixes:
                        payload_overridden = True
                        deepseek_overrides["compatibility_fixes"] = compat_fixes
                    reasoning_warnings = detect_missing_reasoning_content(payload_json)
                    if reasoning_warnings:
                        deepseek_overrides["warnings"] = reasoning_warnings
                        # Surfaced now, before the upstream call — not just written to JSONL
                        # after the (possibly paid) request already completed.
                        _safe_print(
                            f"[relay] WARN DeepSeek reasoning_content: {', '.join(reasoning_warnings)} "
                            f"(request_id={request_id}; DEEPSEEK_REASONING_CONTENT_GUARD="
                            f"{DEEPSEEK_CFG['reasoning_content_guard']})",
                            file=sys.stderr,
                        )
                        if DEEPSEEK_CFG["reasoning_content_guard"] == "block":
                            reasoning_content_blocked = True
                elif KIMI_CFG is not None:
                    if payload_json.get("model") != KIMI_CFG["model"]:
                        payload_json["model"] = KIMI_CFG["model"]
                        payload_overridden = True
                        kimi_overrides["model"] = KIMI_CFG["model"]
                if RELAY_COMPRESS_ACTIVE:
                    comp = compress_chat_completion(payload_json, RELAY_COMPRESS_CFG)
                    shrunk_text = json.dumps(comp.payload, ensure_ascii=False)
                    forwarded_body_bytes = shrunk_text.encode("utf-8")
                    body_text = shrunk_text
                    compress_summary = comp.to_log_dict()
                    stream_source = comp.payload
                else:
                    stream_source = payload_json
                    if payload_overridden:
                        rewritten_text = json.dumps(payload_json, ensure_ascii=False)
                        forwarded_body_bytes = rewritten_text.encode("utf-8")
                        body_text = rewritten_text

        request_summary = summarize_body(body_text, PREVIEW_CHARS)
        if CONTENT_STATS and chat_path == "/v1/chat/completions" and body_text:
            content_stats_forwarded = analyze_body_text(body_text)
        session_health = (
            evaluate_session_health(content_stats_original, thresholds=SESSION_HEALTH_THRESHOLDS)
            if chat_path == "/v1/chat/completions"
            else evaluate_session_health(None, thresholds=SESSION_HEALTH_THRESHOLDS)
        )
        guard = evaluate_guard(
            chat_path,
            body_text,
            request_summary,
            thresholds=THRESHOLDS,
            mode=GUARD_MODE,
        )
        wants_stream = (
            not BUFFER_STREAM
            and not guard.block
            and not reasoning_content_blocked
            and stream_source is not None
            and _payload_stream_enabled(stream_source.get("stream"))
        )
        if guard.block:
            upstream = build_guard_response(guard, request_summary)
        elif reasoning_content_blocked:
            upstream = build_reasoning_content_guard_response(deepseek_overrides.get("warnings", []))
        elif wants_stream:
            upstream = forward_request_streaming(
                self.command,
                self.path,
                request_headers,
                forwarded_body_bytes,
                self,
                compress_summary,
            )
        else:
            upstream = forward_request(self.command, self.path, request_headers, forwarded_body_bytes)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        response_body_text = upstream.body.decode("utf-8", errors="replace")
        usage = extract_usage_from_response_body(response_body_text)
        record: dict[str, Any] = {
            "ts": now_iso(),
            "request_id": request_id,
            "method": self.command,
            "path": self.path,
            "upstream_url": f"{UPSTREAM_BASE}{self.path}",
            "request_headers": redact_headers(request_headers),
            "request_original": request_original,
            "request": sanitize_request_summary_for_log(request_summary),
            "content_stats": {
                "original": content_stats_original,
                "forwarded": content_stats_forwarded,
            }
            if CONTENT_STATS
            else None,
            "relay_compress": compress_summary,
            "deepseek_overrides": deepseek_overrides,
            "kimi_overrides": kimi_overrides,
            "guard": {
                "mode": GUARD_MODE,
                "level": guard.level,
                "blocked": guard.block,
                "reasons": guard.reasons,
                "risk_flags": guard.risk_flags,
            },
            "session_health": {
                "level": session_health.level,
                "recommend_new_chat": session_health.recommend_new_chat,
                "reasons": session_health.reasons,
                "original_messages": session_health.original_messages,
                "original_estimated_tokens": session_health.original_estimated_tokens,
                "original_body_chars": session_health.original_body_chars,
            },
            "response": {
                "status": upstream.status,
                "headers": redact_headers(upstream.headers),
                "chars": len(response_body_text),
                "estimated_tokens": estimate_tokens_from_chars(response_body_text),
                "preview_start": preview(response_body_text, PREVIEW_CHARS),
                "preview_end": suffix_preview(response_body_text, PREVIEW_CHARS),
                "error": upstream.error,
                "usage": usage,
            },
            "elapsed_ms": elapsed_ms,
        }
        if LOG_FULL_BODY:
            record["request"]["body_raw"] = body_text
            record["response"]["body_raw"] = response_body_text
        write_jsonl(record)
        _safe_print(
            format_request_mini_stats(
                method=self.command,
                path=self.path,
                status=upstream.status,
                elapsed_ms=elapsed_ms,
                request_summary=request_summary,
                guard_level=guard.level,
                guard_mode=GUARD_MODE,
                guard_blocked=guard.block,
                stream=wants_stream,
                compress_summary=compress_summary,
                request_original=request_original,
                usage=usage,
                content_stats=record.get("content_stats"),
                response_chars=len(response_body_text),
                error=upstream.error,
                session_health=session_health,
            ),
            file=sys.stderr,
        )

        if wants_stream:
            return

        self.send_response(upstream.status)
        _send_compress_trace_headers(self, compress_summary)
        _copy_upstream_response_headers(self, upstream.headers)
        self.send_header("Content-Length", str(len(upstream.body)))
        self.end_headers()
        _write_wfile_best_effort(self.wfile, upstream.body)


def _candidate_ports(preferred: int) -> list[int]:
    if preferred == 0:
        return [0]
    candidates = [preferred]
    for extra in (1, 2, 3):
        candidates.append(preferred + extra)
    candidates.append(0)
    return candidates


def _bind_server() -> ExclusiveThreadingHTTPServer:
    errors: list[str] = []
    for port in _candidate_ports(DEFAULT_PORT):
        try:
            return ExclusiveThreadingHTTPServer((DEFAULT_HOST, port), RelayHandler)
        except OSError as exc:
            errors.append(f"{DEFAULT_HOST}:{port} -> {exc}")
    error_text = "; ".join(errors) if errors else "no bind attempts recorded"
    raise OSError(f"Could not bind relay server. Attempts: {error_text}")


def main() -> int:
    _configure_stdio_utf8()
    server = _bind_server()
    host, port = server.server_address
    _safe_print(f"Relay listening on http://{host}:{port}")
    _safe_print(f"KILO_RELAY_UPSTREAM / upstream base: {UPSTREAM_BASE}")
    _safe_print(f"Log file: {LOG_PATH}")
    print_startup_modes(host, port)
    if port != DEFAULT_PORT and DEFAULT_PORT != 0:
        _safe_print(
            f"WARN: preferred port {DEFAULT_PORT} busy — listening on {port}. "
            f"Cursor OpenAI Base URL must use http://{host}:{port}/v1 (not :{DEFAULT_PORT}).",
            file=sys.stderr,
        )
    _safe_print(
        f"Awaiting HTTP. Cursor OpenAI-compatible Base URL must be "
        f"http://{host}:{port}/v1 — not api.deepseek.com / api.moonshot.ai. "
        f"Probe: GET http://{host}:{port}/v1/models → expect '[relay] → GET' here. "
        f"Silence = traffic bypasses this process (wrong Base URL / second relay / Cursor Cloud).",
        file=sys.stderr,
    )
    if RELAY_COMPRESS_ACTIVE and DEEPSEEK_CFG is None:
        _safe_print(
            "relay: Если в LM Studio по-прежнему полный список tools → "
            "в Cursor базовый URL OpenAI совместимого API должен быть этот relay, "
            "а не LM Studio напрямую.",
            file=sys.stderr,
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
