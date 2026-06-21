#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup token validation hooks in global IDE settings.
Windows paths: %APPDATA%, %USERPROFILE%
"""

import json
import os
import sys
from pathlib import Path

# Fix encoding on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Конфиги IDE и их пути (Windows)
IDE_CONFIGS = {
    "Cursor AI": Path.home() / ".cursor" / "settings.json",
    "Zed": Path.home() / ".config" / "zed" / "settings.json",
    "VS Code": Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json",
}

HOOK_CONFIG = {
    "hooks": {
        "UserPromptSubmit": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python scripts/validate_token_budget.py",
                        "statusMessage": "🔍 Validating token budget...",
                        "timeout": 10,
                        "asyncRewake": True,
                        "rewakeSummary": "Token validation complete"
                    }
                ]
            }
        ]
    }
}


def merge_json(existing, new_hooks):
    """Merge new hooks into existing config."""
    if "hooks" not in existing:
        existing["hooks"] = {}

    if "UserPromptSubmit" not in existing["hooks"]:
        existing["hooks"]["UserPromptSubmit"] = new_hooks["hooks"]["UserPromptSubmit"]
    else:
        # Check if hook already exists
        for new_hook in new_hooks["hooks"]["UserPromptSubmit"]:
            if new_hook not in existing["hooks"]["UserPromptSubmit"]:
                existing["hooks"]["UserPromptSubmit"].append(new_hook)

    return existing


def setup_ide(ide_name, config_path):
    """Setup hooks for a single IDE."""
    print(f"\n📝 {ide_name}")
    print(f"   Path: {config_path}")

    if not config_path.exists():
        print(f"   ⚠️  Config not found. Creating...")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(HOOK_CONFIG, f, indent=2)
        print(f"   ✅ Created with hooks")
        return True

    try:
        with open(config_path, 'r') as f:
            existing = json.load(f)

        merged = merge_json(existing, HOOK_CONFIG)

        with open(config_path, 'w') as f:
            json.dump(merged, f, indent=2)

        print(f"   ✅ Hooks added/updated")
        return True
    except json.JSONDecodeError:
        print(f"   ❌ Invalid JSON. Skipping.")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("🚀 IDE Global Hooks Setup")
    print("=" * 60)

    success_count = 0

    for ide_name, config_path in IDE_CONFIGS.items():
        if setup_ide(ide_name, config_path):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"✅ Setup complete: {success_count}/{len(IDE_CONFIGS)} IDE configs updated")
    print("=" * 60)

    # Manual instructions for unknown IDEs
    print("\n⚠️  Kilo & Genemi:")
    print("   Unable to auto-detect. Please provide paths or:")
    print("   1. Manually add hooks using templates below")
    print("   2. Create issue with IDE config path")

    print("\n📋 Template for any IDE:")
    print(json.dumps(HOOK_CONFIG, indent=2))


if __name__ == "__main__":
    main()
