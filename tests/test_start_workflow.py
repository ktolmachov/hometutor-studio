from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import start_workflow as sw  # noqa: E402


def test_no_active_package_routes_to_plan_next():
    decision = sw.decide_next_step({"package": None, "rows": [], "contract": {}, "work_state": None})
    assert decision["action"] == "PLAN_NEXT"
    assert "generate_orchestration_prompt.py" in " ".join(decision["command"])


def test_execution_ready_routes_to_resume():
    state = {
        "package": "epoch-foo",
        "status": "ready",
        "work_state": sw.WORK_STATE_EXECUTION_READY,
        "contract": {"WRITE_SET_MAX": "- app/foo.py", "DOD_COMMANDS": "pytest tests/test_foo.py -v"},
    }
    decision = sw.decide_next_step(state)
    assert decision["action"] == "RESUME"
    assert "--resume" in decision["command"]


def test_high_complexity_routes_to_orchestration():
    state = {
        "package": "epoch-complex",
        "status": "ready",
        "work_state": "fresh",
        "contract": {
            "WRITE_SET_MAX": "- app/a.py\n- app/b.py\n- app/c.py\n- tests/test_a.py\n- tests/test_b.py",
            "USER_STORIES": "US-1.1, US-1.2",
            "OUTCOMES": "- one\n- two\n- three\n- four",
            "READ_SET_HINT": "- a\n- b\n- c\n- d\n- e",
            "DOD_COMMANDS": "pytest a; pytest b; python check.py",
        },
    }
    decision = sw.decide_next_step(state, agent="codex")
    assert decision["action"] == "ORCHESTRATION"
    assert decision["command"][1:4] == ["scripts/generate_orchestration_prompt.py", "--agent", "codex"]
    assert decision["command"][0].endswith("python.exe") or decision["command"][0] == "python"


def test_kilo_routes_to_own_orchestration_adapter():
    state = {
        "package": "epoch-kilo",
        "status": "ready",
        "work_state": "fresh",
        "contract": {
            "WRITE_SET_MAX": "- app/a.py\n- app/b.py\n- app/c.py\n- tests/test_a.py\n- tests/test_b.py",
            "USER_STORIES": "US-1.1, US-1.2",
            "OUTCOMES": "- one\n- two\n- three\n- four",
            "READ_SET_HINT": "- a\n- b\n- c\n- d\n- e",
            "DOD_COMMANDS": "pytest a; pytest b; python check.py",
        },
    }
    decision = sw.decide_next_step(state, agent="kilo")
    assert decision["action"] == "ORCHESTRATION"
    assert decision["command"][1:4] == ["scripts/generate_orchestration_prompt.py", "--agent", "kilo"]


def test_continue_routes_to_own_orchestration_adapter():
    state = {
        "package": "epoch-continue",
        "status": "ready",
        "work_state": "fresh",
        "contract": {
            "WRITE_SET_MAX": "- app/a.py\n- app/b.py\n- app/c.py\n- tests/test_a.py\n- tests/test_b.py",
            "USER_STORIES": "US-1.1, US-1.2",
            "OUTCOMES": "- one\n- two\n- three\n- four",
            "READ_SET_HINT": "- a\n- b\n- c\n- d\n- e",
            "DOD_COMMANDS": "pytest a; pytest b; python check.py",
        },
    }
    decision = sw.decide_next_step(state, agent="continue")
    assert decision["action"] == "ORCHESTRATION"
    assert decision["command"][1:4] == ["scripts/generate_orchestration_prompt.py", "--agent", "continue"]


def test_compact_package_routes_to_execution_auto():
    state = {
        "package": "epoch-simple",
        "status": "ready",
        "work_state": "fresh",
        "contract": {
            "WRITE_SET_MAX": "- app/foo.py\n- tests/test_foo.py",
            "USER_STORIES": "US-1.1",
            "OUTCOMES": "- foo works\n- foo shows",
            "DOD_COMMANDS": "pytest tests/test_foo.py -v",
        },
    }
    decision = sw.decide_next_step(state)
    assert decision["action"] == "EXECUTION_AUTO"
    assert decision["command"][1] == "scripts/generate_next_prompt.py"
    assert decision["command"][0].endswith("python.exe") or decision["command"][0] == "python"


def test_proposed_package_routes_to_plan_next_not_execution_auto():
    """proposed/open packages lack an accepted contract — must not jump to EXECUTION_AUTO."""
    state = {
        "package": "multi-query-expansion-v1",
        "status": "proposed",
        "work_state": "fresh",
        "contract": {
            "PACKAGE_ID": "multi-query-expansion-v1",
            "WRITE_SET_MAX": "6",
            "OUTCOMES": "Rewrite/hybrid/rerank already shipped — gap is multi-query only.",
            "DOD_COMMANDS": "",
        },
    }
    decision = sw.decide_next_step(state)
    assert decision["action"] == "PLAN_NEXT"
    assert "generate_orchestration_prompt.py" in " ".join(str(c) for c in decision["command"])
    assert "--package" in decision["command"]
    assert "multi-query-expansion-v1" in decision["command"]


def test_medium_complexity_routes_to_orchestration():
    """medium complexity must now route to orchestration, not execution_auto."""
    state = {
        "package": "epoch-medium",
        "status": "ready",
        "work_state": "fresh",
        "contract": {"COMPLEXITY": "medium"},
    }
    decision = sw.decide_next_step(state)
    assert decision["action"] == "ORCHESTRATION"
    assert "generate_orchestration_prompt.py" in " ".join(decision["command"])


# ---------------------------------------------------------------------------
# Regression: PLAN_NEXT bypasses complexity routing when load_state loses package
# ---------------------------------------------------------------------------
# Исторический сценарий: только tasklist.md → при устаревшем § Now state["package"]
# мог стать None → PLAN_NEXT → orchestration без --package обходила classify_complexity.
# Сейчас: load_state берёт Truth View из реестра; run_autonomous при рассинхроне может
# дернуть backlog_registry_lint и перезапустить цикл (ready в YAML без отображения в derived tasklist).
# ---------------------------------------------------------------------------


def test_stale_tasklist_plan_next_is_not_execution_auto():
    """decide_next_step with empty state always returns PLAN_NEXT, never EXECUTION_AUTO.

    Фиксирует триггер PLAN_NEXT при отсутствии package в state; цикл обхода рассинхронизации
    реестра и производного tasklist — в run_autonomous (lint / restart).
    """
    decision = sw.decide_next_step({"package": None, "rows": [], "contract": {}, "work_state": None})
    assert decision["action"] == "PLAN_NEXT"
    # Confirm the command that would be sent bypasses classify_package_complexity
    cmd_str = " ".join(str(c) for c in decision["command"])
    assert "generate_orchestration_prompt.py" in cmd_str
    assert "--package" not in cmd_str  # no package → subprocess auto-selects from registry


def test_load_state_finds_package_from_registry_even_with_stale_tasklist(monkeypatch):
    """load_state() находит пакет по `parse_truth_view_from_registry()`, не по файлу tasklist.

    Регрессия прежнего поведения (маршрут по markdown § Now): при активной строке в Truth View
    реестра пакет и контракт доступны, complexity routing не обходится через PLAN_NEXT.
    """
    # Registry returns a ready package (simulates real registry state).
    monkeypatch.setattr(sw, "parse_truth_view_from_registry",
                        lambda: [{"package": "epoch-trust-demo", "status": "ready"}])

    monkeypatch.setattr(sw, "detect_work_state", lambda _pid: "fresh")

    state = sw.load_state()
    assert state.get("package") == "epoch-trust-demo"

    # Complexity routing now works correctly — low-score package goes EXECUTION_AUTO,
    # not ORCHESTRATION (the bug was that complexity was never checked).
    state["contract"] = {
        "WRITE_SET_MAX": "- app/foo.py",
        "DOD_COMMANDS": "pytest tests/test_foo.py -v",
    }
    decision = sw.decide_next_step(state)
    assert decision["action"] == "EXECUTION_AUTO", (
        "Low-complexity package must route to EXECUTION_AUTO, not bypass via PLAN_NEXT"
    )


def test_load_state_epoch_demo_resolves_from_registry_when_not_in_active_rows(monkeypatch):
    """Явный `load_state("epoch-demo")`: контракт из реестра, даже если пакета нет в active Truth View."""
    monkeypatch.setattr(
        sw,
        "parse_truth_view_from_registry",
        lambda: [{"package": "epoch-trust-demo", "status": "ready"}],
    )
    monkeypatch.setattr(sw, "detect_work_state", lambda _pid: "fresh")

    state = sw.load_state("epoch-demo")
    assert state.get("package") == "epoch-demo"
    assert "DOD_COMMANDS" in (state.get("contract") or {})


def test_load_state_does_not_allow_contract_only_fallback_for_other_packages(monkeypatch):
    """Guardrail: id без записи в реестре не получает package (ни tasklist, ни in-memory блок)."""
    monkeypatch.setattr(
        sw,
        "parse_truth_view_from_registry",
        lambda: [{"package": "epoch-trust-demo", "status": "ready"}],
    )
    monkeypatch.setattr(sw, "detect_work_state", lambda _pid: "fresh")

    state = sw.load_state("some-random-not-in-registry-xyz")
    assert state.get("package") is None
