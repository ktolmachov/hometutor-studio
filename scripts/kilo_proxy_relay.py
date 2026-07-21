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
  KILO_RELAY_WARN_BODY_CHARS=70000
  KILO_RELAY_MAX_BODY_CHARS=90000
  KILO_RELAY_HARD_BLOCK_BODY_CHARS=110000
  KILO_RELAY_MAX_MESSAGES=15
  KILO_RELAY_MAX_LARGEST_MESSAGE_CHARS=24000
  KILO_RELAY_MAX_TOOLS=13
  KILO_RELAY_GUARD_MODE=warn

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
  DEEPSEEK_THINKING=disabled        # optional: "enabled"/"disabled". DeepSeek V4 defaults to
                                     # thinking.type=enabled + reasoning_effort=high when unset —
                                     # can silently inflate output tokens/latency/cost on every
                                     # request. Unset here = relay does not touch the field at all.
  DEEPSEEK_REASONING_EFFORT=high    # optional: "high"/"max" (DeepSeek's only two real levels; it
                                     # silently maps low/medium up to high and xhigh up to max, so
                                     # this relay does not offer the fake illusion of finer control).
                                     # Only meaningful when thinking is enabled.
  Relay replaces the client's Authorization header with ``Bearer $DEEPSEEK_API_KEY`` for every
  request while the preset is active — Kilo's own dummy relay key is never forwarded to DeepSeek.

  KNOWN GAP (not fixed by this relay): DeepSeek requires the assistant's ``reasoning_content``
  from a tool-call turn to be threaded back into every subsequent request in that conversation,
  or the API returns HTTP 400. This relay proxies whatever message history Kilo constructs; it
  does not verify or repair that history. Kilo was not written against DeepSeek's reasoning_content
  convention, so a multi-turn agentic tool-calling loop through this preset may fail on the very
  first tool round-trip until Kilo's own client-side history handling is confirmed compatible —
  this has NOT been tested end-to-end.
  Effective overrides (model/thinking/reasoning_effort) are recorded per-request under
  ``deepseek_overrides`` in the JSONL log.

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
  KILO_RELAY_CLOUD_BUDGET_REPLACE_CURSOR_SYSTEM=1   # редко: заменить system stub-ом
  KILO_RELAY_CLOUD_BUDGET_SIMPLE_CHAT_MAX_USER_CHARS=700  # если задано — снятие tools на короткой реплике

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
    estimate_tokens_from_chars,
    evaluate_guard,
    preview,
    summarize_body,
    suffix_preview,
)
from _kilo_relay_compress import (  # noqa: E402
    compress_chat_completion,
    is_cloud_budget_slim_mode,
    relay_compress_any_enabled,
    relay_compress_config_from_env,
)


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


_DEEPSEEK_VALID_THINKING = frozenset({"enabled", "disabled"})
# DeepSeek V4's actual documented reasoning_effort levels are high/max (its API silently maps
# low/medium up to high, xhigh up to max) -- offering low/medium here would be a fake illusion
# of granularity DeepSeek itself doesn't provide, and would silently swallow a genuine request
# for max effort if someone assumed "high" was the ceiling.
_DEEPSEEK_VALID_REASONING_EFFORT = frozenset({"high", "max"})


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
    return {
        "base": (environ.get("DEEPSEEK_API_BASE") or DEEPSEEK_DEFAULT_API_BASE).strip().rstrip("/"),
        "model": (environ.get("DEEPSEEK_MODEL") or DEEPSEEK_DEFAULT_MODEL).strip(),
        "api_key": api_key,
        "thinking": thinking,
        "reasoning_effort": reasoning_effort,
    }


def effective_upstream_base(environ: dict[str, str]) -> str:
    """База upstream без завершающего слэша.

    Приоритет: явный ``KILO_RELAY_UPSTREAM`` (всегда побеждает) > DeepSeek preset
    (``KILO_RELAY_UPSTREAM_PRESET=deepseek``) > ``SLIM_MODE=cloud_budget`` дефолт
    (``CLOUD_BUDGET_DEFAULT_UPSTREAM`` / ``KILO_RELAY_CLOUD_DEFAULT_UPSTREAM``) >
    LM Studio ``http://127.0.0.1:1234``.
    """
    raw = (environ.get("KILO_RELAY_UPSTREAM") or "").strip().rstrip("/")
    if raw:
        return raw
    deepseek = deepseek_config_from_env(environ)
    if deepseek is not None:
        return deepseek["base"]
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


UPSTREAM_BASE = effective_upstream_base(dict(os.environ))
DEEPSEEK_CFG = deepseek_config_from_env(dict(os.environ)) if _deepseek_actually_active(dict(os.environ)) else None
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
MAX_TOOLS = int(os.getenv("KILO_RELAY_MAX_TOOLS", "13"))
GUARD_MODE = os.getenv("KILO_RELAY_GUARD_MODE", "warn").strip().lower()
THRESHOLDS = GuardThresholds(
    warn_body_chars=WARN_BODY_CHARS,
    max_body_chars=MAX_BODY_CHARS,
    hard_block_body_chars=HARD_BLOCK_BODY_CHARS,
    max_messages=MAX_MESSAGES,
    max_largest_message_chars=MAX_LARGEST_MESSAGE_CHARS,
    max_tools=MAX_TOOLS,
)
SSL_CONTEXT = ssl.create_default_context()
LOG_LOCK = threading.Lock()
RELAY_COMPRESS_CFG = relay_compress_config_from_env(dict(os.environ))
RELAY_COMPRESS_ACTIVE = relay_compress_any_enabled(RELAY_COMPRESS_CFG)
BUFFER_STREAM = os.getenv("KILO_RELAY_BUFFER_STREAM", "0").strip().lower() in {"1", "true", "yes", "on"}
# Hop-by-hop / пересчитываемые у прокси — не копируем с upstream на клиент
_SKIP_PROXY_RESPONSE_HEADERS = frozenset(
    {"content-length", "transfer-encoding", "connection", "content-encoding", "keep-alive"}
)
READ_CHUNK = 65536


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


def build_startup_modes_report_lines(bound_host: str, bound_port: int) -> list[str]:
    """Human-readable snapshot of relay bind guard compress + env (KILO_RELAY_*)."""
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
            if not (os.environ.get("KILO_RELAY_UPSTREAM") or "").strip()
            and is_cloud_budget_slim_mode(os.environ.get("KILO_RELAY_SLIM_MODE", "local"))
            else ""
        ),
        f"  KILO_RELAY_UPSTREAM_TIMEOUT effective={UPSTREAM_TIMEOUT!r}",
        "[logging]",
        f"  KILO_RELAY_LOG → {LOG_PATH}",
        f"  KILO_RELAY_FULL_BODY={'yes' if LOG_FULL_BODY else 'no'} PREVIEW_CHARS={PREVIEW_CHARS}",
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
        "[compress / _kilo_relay_compress]",
        f"  RELAY_COMPRESS_ACTIVE={'yes' if RELAY_COMPRESS_ACTIVE else 'no'}",
    ]
    d = asdict(RELAY_COMPRESS_CFG)
    for key in sorted(d.keys()):
        lines.append(f"  compress.{key}={_format_for_dump(d[key])}")

    slim_raw = os.environ.get("KILO_RELAY_SLIM_MODE", "<unset → default local>")
    lines.append("[env overrides KILO_RELAY_*]")
    lines.append(f"  KILO_RELAY_SLIM_MODE raw={slim_raw!r}")
    for name in sorted(k for k in os.environ if k.startswith("KILO_RELAY_")):
        if name == "KILO_RELAY_SLIM_MODE":
            continue
        lines.append(f"  {name}={os.environ[name]!r}")
    lines.append("=== конец режимов ===")
    return lines


def print_startup_modes(bound_host: str, bound_port: int) -> None:
    for ln in build_startup_modes_report_lines(bound_host, bound_port):
        _safe_print(ln)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        low = key.lower()
        if low == "authorization":
            redacted[key] = "Bearer ***REDACTED***"
        elif "api-key" in low or low.endswith("key"):
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
    req_headers = {k: v for k, v in headers.items() if k.lower() not in {"host", "content-length", "connection"}}
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
    req_headers = {k: v for k, v in headers.items() if k.lower() not in {"host", "content-length", "connection"}}
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

    def do_POST(self) -> None:  # noqa: N802
        self._handle_proxy()

    def do_GET(self) -> None:  # noqa: N802
        self._handle_proxy()

    def _handle_proxy(self) -> None:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        content_length = int(self.headers.get("Content-Length") or "0")
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        body_text = raw_body.decode("utf-8", errors="replace")
        request_headers = {k: v for k, v in self.headers.items()}
        if DEEPSEEK_CFG is not None:
            _override_authorization(request_headers, DEEPSEEK_CFG["api_key"])
        forwarded_body_bytes = raw_body
        compress_summary: dict[str, Any] = {"enabled": False}
        stream_source: dict[str, Any] | None = None

        chat_path = normalize_chat_completions_path(self.path)
        deepseek_overrides: dict[str, Any] = {}
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
            and stream_source is not None
            and _payload_stream_enabled(stream_source.get("stream"))
        )
        if guard.block:
            upstream = build_guard_response(guard, request_summary)
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
        record: dict[str, Any] = {
            "ts": now_iso(),
            "request_id": request_id,
            "method": self.command,
            "path": self.path,
            "upstream_url": f"{UPSTREAM_BASE}{self.path}",
            "request_headers": redact_headers(request_headers),
            "request": request_summary,
            "relay_compress": compress_summary,
            "deepseek_overrides": deepseek_overrides,
            "guard": {
                "mode": GUARD_MODE,
                "level": guard.level,
                "blocked": guard.block,
                "reasons": guard.reasons,
                "risk_flags": guard.risk_flags,
            },
            "response": {
                "status": upstream.status,
                "headers": redact_headers(upstream.headers),
                "chars": len(response_body_text),
                "estimated_tokens": estimate_tokens_from_chars(response_body_text),
                "preview_start": preview(response_body_text, PREVIEW_CHARS),
                "preview_end": suffix_preview(response_body_text, PREVIEW_CHARS),
                "error": upstream.error,
            },
            "elapsed_ms": elapsed_ms,
        }
        if LOG_FULL_BODY:
            record["request"]["body_raw"] = body_text
            record["response"]["body_raw"] = response_body_text
        write_jsonl(record)

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


def _bind_server() -> ThreadingHTTPServer:
    errors: list[str] = []
    for port in _candidate_ports(DEFAULT_PORT):
        try:
            return ThreadingHTTPServer((DEFAULT_HOST, port), RelayHandler)
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
    if RELAY_COMPRESS_ACTIVE:
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
