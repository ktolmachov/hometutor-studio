#!/usr/bin/env python3
"""
Pre-flight check: validate that required environment variables are set.
Usage: python scripts/check_env.py
Exit code 0 = OK, 1 = missing required vars.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Resolve project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
CONFIG_ENV_FILE = PROJECT_ROOT / "config.env"

# ---------------------------------------------------------------------------
# Parse config.env as a reference dict (before any dotenv loading alters env)
# ---------------------------------------------------------------------------
def _parse_env_file(path: Path) -> dict[str, str]:
    """Return key→value pairs from a dotenv-style file, stripping inline comments."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.split("#")[0].strip()
    return result

_config_env_defaults = _parse_env_file(CONFIG_ENV_FILE)

# ---------------------------------------------------------------------------
# Env var definitions: (name, required, default_or_None)
# ---------------------------------------------------------------------------
ENV_VARS: list[tuple[str, bool, str | None]] = [
    ("OPENAI_API_KEY",  True,  None),
    ("LLM_API_BASE",    False, "http://127.0.0.1:1234/v1"),
    ("LLAMAINDEX_METADATA_FALLBACK_MODEL", False, "gpt-4o-mini"),
    ("OPENAI_API_BASE", False, "https://openrouter.ai/api/v1"),
    ("LLM_MODEL",       False, "gpt-4o-mini"),
    ("EMBED_MODEL",     False, "perplexity/pplx-embed-v1-0.6b"),
    ("EMBED_DIMENSIONS", False, "1024"),
]

# Vars whose values should be masked in output
SECRET_NAMES = {"OPENAI_API_KEY"}


def mask(value: str) -> str:
    """Show first 4 and last 4 chars, mask the rest."""
    if len(value) <= 10:
        return value[:2] + "***" + value[-2:]
    return value[:4] + "***" + value[-4:]


def main() -> int:
    # --- .env existence check ---
    if not ENV_FILE.exists():
        print("WARNING: .env file not found at", ENV_FILE)
        if ENV_EXAMPLE.exists():
            print("  Hint: copy .env.example to .env and fill in your keys:")
            print(f"    cp {ENV_EXAMPLE.name} .env")
        print()

    # Load .env into os.environ (existing vars are NOT overwritten)
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        print("WARNING: python-dotenv not installed; reading os.environ only.\n")

    # --- Build summary table ---
    missing_required: list[str] = []
    rows: list[tuple[str, str, str]] = []

    for name, required, default in ENV_VARS:
        value = os.environ.get(name)

        if value:
            status = "SET"
            display = mask(value) if name in SECRET_NAMES else value
        elif default is not None:
            status = "default"
            display = default
        else:
            status = "MISSING"
            display = "-"
            if required:
                missing_required.append(name)

        rows.append((name, status, display))

    # --- Print table ---
    col_w = [max(len(r[i]) for r in rows) for i in range(3)]
    col_w[0] = max(col_w[0], len("Variable"))
    col_w[1] = max(col_w[1], len("Status"))
    col_w[2] = max(col_w[2], len("Value"))

    header = f"  {'Variable':<{col_w[0]}}  {'Status':<{col_w[1]}}  {'Value':<{col_w[2]}}"
    sep = f"  {'-' * col_w[0]}  {'-' * col_w[1]}  {'-' * col_w[2]}"

    print("Environment check:")
    print(header)
    print(sep)
    for name, status, display in rows:
        marker = "!!" if status == "MISSING" else "  "
        print(f"{marker}{name:<{col_w[0]}}  {status:<{col_w[1]}}  {display:<{col_w[2]}}")
    print()

    # --- OS env override warnings ---
    # Detect stale OS environment variables that silently override config.env.
    # load_dotenv without override=True respects pre-existing OS env vars, so a stale
    # exported value will shadow config.env even after the file is corrected.
    _MODEL_VARS = (
        "LLM_MODEL",
        "SSR_LLM_MODEL",
        "QUIZ_LLM_MODEL",
        "LLAMAINDEX_METADATA_FALLBACK_MODEL",
    )
    _CLOUD_PREFIXES = (
        "openai/", "google/", "anthropic/", "deepseek/",
        "qwen/", "meta-llama/", "mistralai/",
    )
    _LOCAL_PROFILES = {"balanced", "local_strict"}

    effective_profile = os.environ.get(
        "HOME_RAG_LOCAL_PROFILE",
        _config_env_defaults.get("HOME_RAG_LOCAL_PROFILE", "balanced"),
    )

    override_warnings: list[str] = []
    stale_vars: list[str] = []

    for var in _MODEL_VARS:
        os_val = os.environ.get(var, "")
        cfg_val = _config_env_defaults.get(var, "")
        if os_val and cfg_val and os_val != cfg_val:
            override_warnings.append(
                f"  WARN: {var} OS env={os_val!r} overrides config.env={cfg_val!r}"
            )
            stale_vars.append(var)
        effective_val = os_val or cfg_val
        if var == "LLAMAINDEX_METADATA_FALLBACK_MODEL" and "/" in effective_val:
            override_warnings.append(
                f"  WARN: {var}={effective_val!r} contains a provider prefix — "
                "LlamaIndex requires a plain OpenAI model ID (e.g. gpt-4o-mini)"
            )
        if (
            var in ("LLM_MODEL", "SSR_LLM_MODEL", "QUIZ_LLM_MODEL")
            and effective_val.startswith(_CLOUD_PREFIXES)
            and effective_profile in _LOCAL_PROFILES
        ):
            override_warnings.append(
                f"  WARN: {var}={effective_val!r} looks like a cloud model "
                f"but HOME_RAG_LOCAL_PROFILE={effective_profile!r} — "
                "may cause unexpected cloud LLM calls or LlamaIndex validation errors"
            )

    if override_warnings:
        print("OS environment override warnings:")
        for w in override_warnings:
            print(w)
        if stale_vars:
            print()
            print("  Hint: unset stale OS env vars (PowerShell):")
            for var in stale_vars:
                print(f"    [System.Environment]::SetEnvironmentVariable('{var}', $null, 'User')")
            print("    Then restart your terminal.")
        print()

    # --- Result ---
    if missing_required:
        print(f"ERROR: required variable(s) not set: {', '.join(missing_required)}")
        print("Set them in .env or export before running the app.")
        return 1

    print("All required environment variables are set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
