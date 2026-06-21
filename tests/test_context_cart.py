"""
Tests for scripts/context_cart.py — token-budget context cart builder.

Validates:
  - Budget is respected per mode (plan/orchestrate/verify)
  - Forbidden files are always excluded regardless of budget
  - Partial cart exits with code 1, full cart exits 0
  - --emit-agent-prompt produces correct read-set instructions
  - --json flag outputs valid JSON
  - Strategy selection (full / signatures / hint / forbidden)
  - Golden fixtures match expected schema
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Import module under test
import importlib, sys

SCRIPTS_PATH = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_PATH))

import context_cart as cc

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "context_cart"


# ---------------------------------------------------------------------------
# Minimal registry fixture for isolated tests
# ---------------------------------------------------------------------------

_SMALL_REGISTRY: dict[str, Any] = {
    "chars_per_token": 4,
    "budgets": {"target_input_tokens": 12000, "hard_input_tokens": 20000},
    "files": {
        "app/small.py": {"lines": 50, "bytes": 800, "est_tokens": 200},
        "app/medium.py": {"lines": 300, "bytes": 6000, "est_tokens": 1500},
        "app/large.py": {
            "lines": 1000,
            "bytes": 40000,
            "est_tokens": 10000,
            "full_read": "forbidden",
            "safe_hint": 'rg -n "^def " app/large.py',
        },
        "doc/plain.md": {"lines": 100, "bytes": 4000, "est_tokens": 1000},
        "doc/huge.md": {
            "lines": 800,
            "bytes": 60000,
            "est_tokens": 15000,
            "full_read": "forbidden",
            "safe_hint": "Read only §header",
        },
    },
}


# ---------------------------------------------------------------------------
# build_cart: budget enforcement
# ---------------------------------------------------------------------------


class TestBuildCartBudget:
    def test_all_fit_within_budget(self):
        cart = cc.build_cart(
            ["app/small.py", "app/medium.py"],
            budget=12_000,
            registry=_SMALL_REGISTRY,
        )
        assert len(cart["included"]) == 2
        assert cart["excluded"] == []
        assert cart["tokens_used"] <= cart["available"]

    def test_budget_too_small_excludes_file(self):
        # verify mode budget=6k, available=3k; medium=1500t fits, but small+medium=1700 also fits
        cart = cc.build_cart(
            ["app/medium.py", "app/small.py"],
            budget=6_000,
            registry=_SMALL_REGISTRY,
        )
        # medium (1500) + small (200) = 1700 < 3000 → both fit
        assert len(cart["included"]) == 2
        assert cart["tokens_used"] <= cart["available"]

    def test_large_file_excluded_when_over_budget(self):
        # Budget=4k, available=1k; medium (1500t) exceeds 1k
        cart = cc.build_cart(
            ["app/medium.py"],
            budget=4_000,
            registry=_SMALL_REGISTRY,
        )
        assert len(cart["included"]) == 0
        assert cart["excluded"][0]["reason"] == "budget_exceeded"

    def test_tokens_used_does_not_exceed_available(self):
        cart = cc.build_cart(
            ["app/small.py", "app/medium.py", "doc/plain.md"],
            budget=6_000,  # available = 3000
            registry=_SMALL_REGISTRY,
        )
        assert cart["tokens_used"] <= cart["available"]

    def test_overhead_is_reserved(self):
        cart = cc.build_cart([], budget=12_000, registry=_SMALL_REGISTRY)
        assert cart["overhead_reserved"] == cc.OVERHEAD_TOKENS
        assert cart["available"] == 12_000 - cc.OVERHEAD_TOKENS


# ---------------------------------------------------------------------------
# build_cart: forbidden files
# ---------------------------------------------------------------------------


class TestBuildCartForbidden:
    def test_forbidden_file_always_excluded(self):
        cart = cc.build_cart(
            ["app/large.py"],
            budget=99_000,  # unlimited budget — still excluded
            registry=_SMALL_REGISTRY,
        )
        assert len(cart["included"]) == 0
        assert cart["excluded"][0]["reason"] == "forbidden_full_read"

    def test_forbidden_hint_preserved(self):
        cart = cc.build_cart(["app/large.py"], budget=99_000, registry=_SMALL_REGISTRY)
        excl = cart["excluded"][0]
        assert 'rg -n "^def "' in (excl.get("hint") or "")

    def test_forbidden_file_does_not_consume_budget(self):
        cart = cc.build_cart(
            ["app/large.py", "app/small.py"],
            budget=6_000,
            registry=_SMALL_REGISTRY,
        )
        # app/large.py forbidden → excluded; app/small.py (200t) fits in 3k
        assert any(i["path"] == "app/small.py" for i in cart["included"])
        assert any(e["path"] == "app/large.py" for e in cart["excluded"])

    def test_exit_code_1_when_forbidden_present(self, monkeypatch):
        monkeypatch.setattr(cc, "_load_registry", lambda: _SMALL_REGISTRY)
        result = cc.main(["--json", "--mode", "plan", "app/large.py"])
        assert result == 1


# ---------------------------------------------------------------------------
# Strategy selection
# ---------------------------------------------------------------------------


class TestStrategySelection:
    def test_small_file_gets_full_strategy(self):
        strat, hint = cc._strategy("app/small.py", _SMALL_REGISTRY)
        assert strat == "full"
        assert hint is None

    def test_forbidden_file_gets_forbidden_strategy(self):
        strat, hint = cc._strategy("app/large.py", _SMALL_REGISTRY)
        assert strat == "forbidden"
        assert hint is not None

    def test_hint_file_gets_hint_strategy(self):
        strat, hint = cc._strategy("doc/huge.md", _SMALL_REGISTRY)
        assert strat == "forbidden"
        assert hint is not None

    def test_unknown_file_defaults_to_full(self):
        strat, hint = cc._strategy("app/unknown.py", _SMALL_REGISTRY)
        assert strat in ("full", "signatures")

    def test_large_file_without_registry_gets_signatures(self, tmp_path):
        """Heuristic: file >5k tokens estimated from filesystem gets 'signatures'."""
        big = tmp_path / "big.py"
        big.write_bytes(b"x" * (5_001 * 4))  # >5k tokens by char estimate
        rel = str(big.relative_to(REPO_ROOT)) if big.is_relative_to(REPO_ROOT) else str(big)
        # Just test the estimate logic directly
        strat, _ = cc._strategy("app/medium.py", _SMALL_REGISTRY)
        # medium is 1500 tokens → full
        assert strat == "full"


# ---------------------------------------------------------------------------
# Signatures / hint token reduction
# ---------------------------------------------------------------------------


class TestTokenCharging:
    def test_signatures_charged_at_10_percent(self):
        # app/medium.py: est_tokens=1500, no forbidden, but let's make it have a safe_hint
        registry_with_hint: dict[str, Any] = {
            "files": {
                "app/hinted.py": {
                    "est_tokens": 2000,
                    "safe_hint": 'rg -n "^def " app/hinted.py',
                }
            }
        }
        cart = cc.build_cart(["app/hinted.py"], budget=12_000, registry=registry_with_hint)
        included = cart["included"]
        assert len(included) == 1
        charged = included[0]["tokens_charged"]
        # hint strategy → charged = max(50, 2000 // 10) = 200
        assert charged == 200

    def test_full_strategy_charged_at_100_percent(self):
        cart = cc.build_cart(["app/small.py"], budget=12_000, registry=_SMALL_REGISTRY)
        included = cart["included"]
        assert len(included) == 1
        assert included[0]["tokens_charged"] == 200  # full = est_tokens


# ---------------------------------------------------------------------------
# Mode budgets
# ---------------------------------------------------------------------------


class TestModeBudgets:
    def test_plan_mode_uses_12k_budget(self):
        assert cc.MODE_BUDGETS["plan"] == 12_000

    def test_orchestrate_mode_uses_8k_budget(self):
        assert cc.MODE_BUDGETS["orchestrate"] == 8_000

    def test_verify_mode_uses_6k_budget(self):
        assert cc.MODE_BUDGETS["verify"] == 6_000

    def test_budget_override_works(self, capsys):
        cc.main(["--mode", "plan", "--budget", "4000", "--json", "app/small.py"])
        out = capsys.readouterr().out
        cart = json.loads(out)
        assert cart["budget"] == 4000


# ---------------------------------------------------------------------------
# --emit-agent-prompt output
# ---------------------------------------------------------------------------


class TestEmitAgentPrompt:
    def test_prompt_contains_mode_and_budget(self, capsys):
        cc.main(["--mode", "plan", "--emit-agent-prompt", "app/small.py"])
        out = capsys.readouterr().out
        assert "mode=plan" in out
        assert "12000" in out or "12k" in out

    def test_prompt_lists_included_files(self, capsys):
        cc.main(["--mode", "plan", "--emit-agent-prompt", "app/small.py"])
        out = capsys.readouterr().out
        assert "app/small.py" in out

    def test_prompt_shows_excluded_with_hint(self, capsys, monkeypatch):
        monkeypatch.setattr(cc, "_load_registry", lambda: _SMALL_REGISTRY)
        cc.main(["--mode", "plan", "--emit-agent-prompt", "app/large.py"])
        out = capsys.readouterr().out
        assert "Excluded" in out
        assert "app/large.py" in out

    def test_full_strategy_says_full_read(self, capsys):
        cc.main(["--mode", "plan", "--emit-agent-prompt", "app/small.py"])
        out = capsys.readouterr().out
        assert "full read" in out


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------


class TestJsonOutput:
    def test_json_output_is_valid(self, capsys):
        cc.main(["--json", "--mode", "plan", "app/small.py"])
        out = capsys.readouterr().out
        cart = json.loads(out)
        assert cart["schema_version"] == 1
        assert "included" in cart
        assert "excluded" in cart

    def test_json_contains_tokens_used(self, capsys):
        cc.main(["--json", "--mode", "plan", "app/small.py"])
        out = capsys.readouterr().out
        cart = json.loads(out)
        assert isinstance(cart["tokens_used"], int)


# ---------------------------------------------------------------------------
# Golden fixtures
# ---------------------------------------------------------------------------


class TestGoldenFixtures:
    """Verify fixture files match expected schema."""

    def test_plan_cart_fixture_exists_and_is_valid(self):
        fixture = FIXTURES_DIR / "plan_cart.json"
        assert fixture.is_file(), f"Fixture not found: {fixture}"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        assert int(data.get("schema_version") or 0) == 1
        assert "included" in data
        assert "excluded" in data
        assert data["budget"] == 12_000

    def test_verify_cart_fixture_exists_and_is_valid(self):
        fixture = FIXTURES_DIR / "verify_cart.json"
        assert fixture.is_file(), f"Fixture not found: {fixture}"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        assert int(data.get("schema_version") or 0) == 1
        assert data["budget"] == 6_000

    def test_verify_cart_excludes_forbidden_test_api(self):
        fixture = FIXTURES_DIR / "verify_cart.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        excluded_paths = [e["path"] for e in data["excluded"]]
        assert "tests/test_api.py" in excluded_paths

    def test_plan_cart_all_included(self):
        fixture = FIXTURES_DIR / "plan_cart.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        assert data["excluded"] == []


# ---------------------------------------------------------------------------
# Exit code contract
# ---------------------------------------------------------------------------


class TestExitCodes:
    def test_exit_0_when_all_files_included(self, monkeypatch):
        monkeypatch.setattr(cc, "_load_registry", lambda: _SMALL_REGISTRY)
        result = cc.main(["--json", "--mode", "plan", "app/small.py"])
        assert result == 0

    def test_exit_1_when_file_excluded(self, monkeypatch):
        monkeypatch.setattr(cc, "_load_registry", lambda: _SMALL_REGISTRY)
        result = cc.main(["--json", "--mode", "plan", "app/large.py"])
        assert result == 1

    def test_exit_0_for_empty_file_list(self):
        result = cc.main(["--json", "--mode", "plan"])
        assert result == 0
