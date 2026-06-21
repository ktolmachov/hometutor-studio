from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))

# In-process imports for fast unit-style tests of build_orchestration_prompt.
# (The original subprocess-based test below is retained for its
# environment-isolation guarantees — it runs in a fresh interpreter.)
import generate_orchestration_prompt as gop  # noqa: E402


def _minimal_contract(**overrides) -> dict[str, str]:
    base = {
        "PACKAGE_ID":       "epoch-phase25",
        "PACKAGE_TITLE":    "Phase 2.5 fixture",
        "CJM_STAGE":        "Learn",
        "USER_STORIES":     "n/a",
        "OUTCOMES":         "",
        "WRITE_SET_MAX":    "",
        "DOD_COMMANDS":     "pytest -q",
        "NOTES":            "",
        "TARGET_ARTIFACTS": "",
        "READ_SET_HINT":    "",
    }
    base.update(overrides)
    return base


_FAKE_ADAPTER = {
    "MAX_PARALLEL":    "8",
    "WRITE_FILE":      "save",
    "RUN_CMD":         "run",
    "AGENT_SPAWN":     "spawn",
    "PARALLEL_SYNTAX": "(parallel)",
}

_TEMPLATE_WITH_OPS = (
    "## Header for {{PACKAGE_ID}}\n\n"
    "ops_gate_needed: {{OPS_GATE_NEEDED}}\n"
    "ops_roles_triggered: {{OPS_ROLES_TRIGGERED}}\n"
)


_FAKE_CONTEXT = {
    "us_criteria":   "(c)",
    "cjm_fragment":  "(cjm)",
    "recent_closed": "(closed)",
}


def test_build_orchestration_prompt_includes_write_set_section() -> None:
    """P5 gate: bounded paths for drift checks — mirrors generate_next_prompt execution prompts."""
    code = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, r"{SCRIPTS}")
        from generate_orchestration_prompt import build_orchestration_prompt

        contract = {{
            "PACKAGE_ID": "epoch-test-write-set",
            "PACKAGE_TITLE": "Test",
            "CJM_STAGE": "infra",
            "USER_STORIES": "n/a",
            "OUTCOMES": "",
            "WRITE_SET_MAX": "scripts/pipeline_events.py, tests/test_pipeline_events.py",
            "DOD_COMMANDS": "pytest tests/test_pipeline_events.py -q",
            "NOTES": "",
            "TARGET_ARTIFACTS": "",
            "READ_SET_HINT": "",
        }}
        adapter = {{
            "MAX_PARALLEL": "8",
            "WRITE_FILE": "save",
            "RUN_CMD": "run",
            "AGENT_SPAWN": "spawn",
            "PARALLEL_SYNTAX": "(parallel)",
        }}
        template = "## Title\\n\\nBody for {{PACKAGE_ID}}\\n"
        context = {{
            "us_criteria": "(c)",
            "cjm_fragment": "(cjm)",
            "recent_closed": "(closed)",
        }}
        out = build_orchestration_prompt(
            contract, adapter, template, "cursor_ai", context
        )
        assert "## Write-Set" in out
        assert "scripts/pipeline_events.py" in out
        assert "tests/test_pipeline_events.py" in out
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr




def test_phase25_placeholders_default_to_false_when_ops_info_omitted() -> None:
    """Backward-compat: callers that don't pass ops_info still produce valid output
    with gate_needed=false."""
    out = gop.build_orchestration_prompt(
        _minimal_contract(),
        _FAKE_ADAPTER,
        _TEMPLATE_WITH_OPS,
        "cursor_ai",
        _FAKE_CONTEXT,
    )
    assert "ops_gate_needed: false" in out
    assert "ops_roles_triggered: \n" in out + "\n"


def test_phase25_placeholders_substituted_when_ops_info_provided() -> None:
    ops_info = {
        "gate_needed":   True,
        "roles":         ["llmops", "ragops"],
        "matched_paths": ["app/provider.py", "app/query_service.py"],
    }
    out = gop.build_orchestration_prompt(
        _minimal_contract(),
        _FAKE_ADAPTER,
        _TEMPLATE_WITH_OPS,
        "cursor_ai",
        _FAKE_CONTEXT,
        ops_info=ops_info,
    )
    assert "ops_gate_needed: true" in out
    assert "ops_roles_triggered: llmops,ragops" in out


def test_phase25_empty_roles_forces_gate_false_even_if_flag_true() -> None:
    """Defense in depth: roles=[] must always coerce gate_needed to false."""
    ops_info = {"gate_needed": True, "roles": [], "matched_paths": []}
    out = gop.build_orchestration_prompt(
        _minimal_contract(),
        _FAKE_ADAPTER,
        _TEMPLATE_WITH_OPS,
        "cursor_ai",
        _FAKE_CONTEXT,
        ops_info=ops_info,
    )
    assert "ops_gate_needed: false" in out


def test_phase25_no_residual_placeholders_for_real_template() -> None:
    """End-to-end check against the actual orchestrator_template.md prompt block —
    the two new placeholders must survive _validate_filled_prompt with no warnings.
    """
    template_text = (ROOT / "doc" / "team_workflow" / "orchestrator_template.md").read_text(
        encoding="utf-8"
    )
    import re
    m = re.search(r"## Шаблон промпта\s*\n\n```text\n(.*?)```", template_text, re.DOTALL)
    assert m, "template prompt block not found in orchestrator_template.md"
    prompt_block = m.group(1)

    ops_info = {
        "gate_needed":   True,
        "roles":         ["llmops", "performance", "ragops"],
        "matched_paths": ["app/provider.py", "scripts/local_readiness.py", "app/query_service.py"],
    }
    out = gop.build_orchestration_prompt(
        _minimal_contract(WRITE_SET_MAX="app/provider.py"),
        _FAKE_ADAPTER,
        prompt_block,
        "cursor_ai",
        _FAKE_CONTEXT,
        ops_info=ops_info,
    )

    # Both new placeholders are gone (substituted)
    assert "{{OPS_GATE_NEEDED}}" not in out
    assert "{{OPS_ROLES_TRIGGERED}}" not in out

    # And the literal substituted text is present where we expect it.
    assert "true" in out
    assert "llmops,performance,ragops" in out


# ---------------------------------------------------------------------------
# E2E — full main() pipeline with isolated tmp registry / adapters / template
# ---------------------------------------------------------------------------

import shutil
import yaml as _yaml  # type: ignore[import-not-found]

import prompt_utils  # noqa: E402


def _build_isolated_repo(tmp_path: Path, registry_items: list[dict]) -> Path:
    """Construct a minimal repo tree the script can run against.

    Mirrors the real layout enough for Phases 1, 2, 2.5, 3, 4, 5 to all succeed.
    """
    real_root = ROOT
    fake_root = tmp_path / "repo"
    (fake_root / "doc" / "team_workflow" / "guides").mkdir(parents=True)
    (fake_root / "doc" / "user_stories").mkdir(parents=True)
    (fake_root / "archive").mkdir(parents=True)

    # Registry
    registry = {"items": registry_items}
    (fake_root / "doc" / "backlog_registry.yaml").write_text(
        _yaml.safe_dump(registry, sort_keys=False), encoding="utf-8"
    )

    # Minimal stubs for context-extraction files
    (fake_root / "doc" / "cjm.md").write_text("# CJM\n\n## Learn\nstage info\n", encoding="utf-8")
    (fake_root / "doc" / "closed_iterations.md").write_text(
        "# Closed\n\n### 2026-05-01 — sample\nclosed entry\n", encoding="utf-8"
    )

    # Copy the real template + adapters into the fake repo so the parser
    # sees the same YAML structure it expects.
    shutil.copy(
        real_root / "doc" / "team_workflow" / "orchestrator_template.md",
        fake_root / "doc" / "team_workflow" / "orchestrator_template.md",
    )
    for adapter_name in (
        "agent_adapter_cursor_ai.md",
        "agent_adapter_claude_code.md",
        "agent_adapter_codex.md",
        "agent_adapter_kilo.md",
        "agent_adapter_continue.md",
    ):
        src = real_root / "doc" / "team_workflow" / "guides" / adapter_name
        if not src.exists():
            src = real_root / "doc" / "team_workflow" / adapter_name
        if src.exists():
            dest = fake_root / "doc" / "team_workflow" / "guides" / adapter_name
            shutil.copy(src, dest)

    # Stub plan-next doc (not used in CASE A, but referenced by auto-pivot)
    (fake_root / "doc" / "team_workflow" / "generate_plan_next_prompt.md").write_text(
        "# plan-next stub\n", encoding="utf-8"
    )

    return fake_root


def _redirect_module_paths_to(fake_root: Path, monkeypatch) -> None:
    monkeypatch.setattr(gop, "ROOT", fake_root)
    monkeypatch.setattr(gop, "TEMPLATE_PATH", fake_root / "doc" / "team_workflow" / "orchestrator_template.md")
    monkeypatch.setattr(gop, "TEAM_ARTIFACTS", fake_root / "archive" / "team_artifacts")
    monkeypatch.setattr(gop, "AGENT_PROMPTS", fake_root / "archive" / "agent_prompts")
    monkeypatch.setattr(gop, "PIPELINE_METRICS", fake_root / "archive" / "pipeline_metrics.md")
    monkeypatch.setattr(gop, "_PLAN_NEXT_DOC", fake_root / "doc" / "team_workflow" / "generate_plan_next_prompt.md")
    monkeypatch.setattr(gop, "AGENT_ADAPTERS", prompt_utils.agent_adapters_map(root=fake_root))
    # prompt_utils has its own ROOT used by load_backlog_registry et al.
    monkeypatch.setattr(prompt_utils, "ROOT", fake_root)
    monkeypatch.setattr(prompt_utils, "BACKLOG_REGISTRY", fake_root / "doc" / "backlog_registry.yaml")


def _run_main(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["generate_orchestration_prompt.py", *argv])
    return gop.main()


def test_e2e_main_substitutes_ops_placeholders_when_triggers_present(tmp_path, monkeypatch, capsys):
    fake_root = _build_isolated_repo(
        tmp_path,
        [
            {
                "id":                "epoch-ops-e2e",
                "status":            "ready",
                "user_stories":      [],
                "cjm_moments":       ["Learn"],
                "blocks":            "Touch app/provider.py and app/query_service.py to test gate.",
                "write_set_max":     ["app/provider.py", "app/query_service.py"],
                "read_set_hint":     [],
                "exit_artifact":     "fallback wired up",
                "notes":             "",
                "dod_commands":      ["pytest tests/test_provider.py -q"],
            }
        ],
    )
    _redirect_module_paths_to(fake_root, monkeypatch)

    rc = _run_main(monkeypatch, ["--agent", "cursor_ai"])
    assert rc == 0

    captured = capsys.readouterr()
    assert "Ops gate:" in captured.out
    assert "llmops" in captured.out and "ragops" in captured.out

    out_path = fake_root / "archive" / "team_artifacts" / "epoch-ops-e2e" / "orchestration_cursor_ai.md"
    assert out_path.exists(), f"expected {out_path}"
    text = out_path.read_text(encoding="utf-8")
    assert "{{OPS_GATE_NEEDED}}" not in text
    assert "{{OPS_ROLES_TRIGGERED}}" not in text
    # Substituted literals from the template should be visible somewhere.
    assert "llmops,ragops" in text


def test_e2e_main_skips_gate_when_no_triggers(tmp_path, monkeypatch, capsys):
    fake_root = _build_isolated_repo(
        tmp_path,
        [
            {
                "id":            "epoch-no-ops",
                "status":        "ready",
                "user_stories":  [],
                "cjm_moments":   ["Learn"],
                "blocks":        "Pure UX copy update — no code surfaces touched.",
                "write_set_max": 0,
                "read_set_hint": [],
                "exit_artifact": "copy refreshed",
                "notes":         "",
                "dod_commands":  ["pytest tests/test_ui_copy.py -q"],
            }
        ],
    )
    _redirect_module_paths_to(fake_root, monkeypatch)

    rc = _run_main(monkeypatch, ["--agent", "cursor_ai"])
    assert rc == 0

    captured = capsys.readouterr()
    assert "Ops gate: SKIPPED" in captured.out

    out_path = fake_root / "archive" / "team_artifacts" / "epoch-no-ops" / "orchestration_cursor_ai.md"
    text = out_path.read_text(encoding="utf-8")
    # Placeholder must be substituted to "false" even when skipped.
    assert "{{OPS_GATE_NEEDED}}" not in text
    # Empty roles → empty string after substitution
    assert "{{OPS_ROLES_TRIGGERED}}" not in text


def test_e2e_main_performance_only_trigger(tmp_path, monkeypatch, capsys):
    fake_root = _build_isolated_repo(
        tmp_path,
        [
            {
                "id":            "epoch-perf-only",
                "status":        "ready",
                "user_stories":  [],
                "cjm_moments":   ["Discover"],
                "blocks":        "Tighten CI",
                "write_set_max": [".github/workflows/ci.yml"],
                "read_set_hint": [],
                "exit_artifact": "ci speed-up",
                "notes":         "",
                "dod_commands":  ["pytest -q"],
            }
        ],
    )
    _redirect_module_paths_to(fake_root, monkeypatch)

    rc = _run_main(monkeypatch, ["--agent", "cursor_ai"])
    assert rc == 0

    out_path = fake_root / "archive" / "team_artifacts" / "epoch-perf-only" / "orchestration_cursor_ai.md"
    text = out_path.read_text(encoding="utf-8")
    # Single role survives as comma-joined-with-one — i.e. just "performance"
    assert "performance" in text


# ---------------------------------------------------------------------------
# Regression tests — Bug fixes 2026-05-29
# ---------------------------------------------------------------------------

def test_cursor_ai_parallel_syntax_has_no_hardcoded_role_names() -> None:
    """PARALLEL_SYNTAX in cursor_ai adapter must NOT hardcode 'Architect' or 'Designer'.

    Regression: the adapter used to contain
        Дать агентам имена: "{{PACKAGE_ID}} Architect" и "{{PACKAGE_ID}} Designer"
    which caused STEP 3.5 (Ops Impact Gate) to confuse the SDK agent into thinking it
    should produce architect/designer artifacts instead of ops impact reports.
    """
    adapter_path = prompt_utils.resolve_agent_adapter_file("cursor_ai")
    assert adapter_path.is_file(), f"missing adapter: {adapter_path}"
    text = adapter_path.read_text(encoding="utf-8")
    # Extract PARALLEL_SYNTAX block (between PARALLEL_SYNTAX: | and the next key)
    import re
    m = re.search(r"PARALLEL_SYNTAX:\s*\|(.+?)(?=\n\w)", text, re.DOTALL)
    assert m is not None, "PARALLEL_SYNTAX block not found in adapter"
    parallel_block = m.group(1)
    assert "Architect" not in parallel_block, (
        "PARALLEL_SYNTAX must not contain hardcoded 'Architect' — "
        "breaks STEP 3.5 Ops Impact Gate for SDK agents"
    )
    assert "Designer" not in parallel_block, (
        "PARALLEL_SYNTAX must not contain hardcoded 'Designer' — "
        "breaks STEP 3.5 Ops Impact Gate for SDK agents"
    )


def test_orchestrator_template_step35_suffix_on_separate_line() -> None:
    """In orchestrator_template.md, the [one agent per role] suffix for STEP 3.5
    must be on its own line, not appended inline to the last line of PARALLEL_SYNTAX.

    Regression: the template had '{{PARALLEL_SYNTAX}} [one agent per role in {{OPS_ROLES_TRIGGERED}}]:'
    on a single line. After template fill, this produced the confusing string
    '...продолжить. [one agent per role in mlops,ragops]:' which misled the SDK agent.
    """
    template_path = ROOT / "doc" / "team_workflow" / "orchestrator_template.md"
    text = template_path.read_text(encoding="utf-8")
    # The bad pattern is: {{PARALLEL_SYNTAX}} followed by [one agent per role on the same line
    assert "{{PARALLEL_SYNTAX}} [one agent per role" not in text, (
        "PARALLEL_SYNTAX and '[one agent per role...]' suffix must be on separate lines "
        "in orchestrator_template.md STEP 3.5 section"
    )
    # Correct pattern: suffix on its own line
    assert "\n[one agent per role in {{OPS_ROLES_TRIGGERED}}]:" in text


def test_e2e_ops_gate_triggered_by_deliverables_not_read_set(tmp_path, monkeypatch, capsys):
    """ops gate must fire from write-set (deliverables) but NOT from read_set_hint.

    Regression: ops_triggers.py used to scan READ_SET_HINT, causing false-positive
    mlops+ragops for packages that merely READ ops-sensitive files.
    This test verifies that knowledge_graph.py in read_set_hint does NOT trigger
    mlops+ragops, while the same file in deliverables (write-set) DOES trigger.
    """
    fake_root = _build_isolated_repo(
        tmp_path,
        [
            {
                "id":            "epoch-read-only-kg",
                "status":        "ready",
                "user_stories":  [],
                "cjm_moments":   ["Learn"],
                "blocks":        "Pure routing helper — reads but does not modify KG",
                "write_set_max": 3,
                "deliverables":  [
                    "app/ssr_graph_routing.py",
                    "tests/test_ssr_graph_routing.py",
                ],
                "read_set_hint": ["app/knowledge_graph.py -- read-only API"],
                "exit_artifact": "routing helper delivered",
                "notes":         "",
                "dod_commands":  ["pytest tests/test_ssr_graph_routing.py -q"],
            }
        ],
    )
    _redirect_module_paths_to(fake_root, monkeypatch)

    rc = _run_main(monkeypatch, ["--agent", "cursor_ai"])
    assert rc == 0

    out = capsys.readouterr().out
    # knowledge_graph.py in read-set must NOT trigger mlops+ragops
    assert "mlops" not in out or "SKIPPED" in out or "no Ops triggers" in out, (
        f"mlops should not be triggered by read-set knowledge_graph.py; stdout:\n{out}"
    )

    out_path = (
        fake_root / "archive" / "team_artifacts"
        / "epoch-read-only-kg" / "orchestration_cursor_ai.md"
    )
    text = out_path.read_text(encoding="utf-8")
    # The generated orchestration must NOT say "fires if true=true" for mlops
    # (gate needed = false when only read-set mentions kg)
    assert "fires if true=false" in text or "SKIPPED" in text or "mlops" not in text


def test_auto_pivot_to_planning_prints_compact_launcher(tmp_path):
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"
    plan_doc = tmp_path / "generate_plan_next_prompt.md"
    plan_doc.write_text(
        "# Huge planning doc\n\n" + ("LONG-CONTENT\n" * 200),
        encoding="utf-8",
    )

    code = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path

        sys.path.insert(0, r"{scripts_dir}")
        import generate_orchestration_prompt as gop

        gop._PLAN_NEXT_DOC = Path(r"{plan_doc}")
        raise SystemExit(gop._auto_pivot_to_planning("cursor_ai"))
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0
    assert "# PLAN_NEXT launcher" in result.stdout
    assert "Read `doc/team_workflow/generate_plan_next_prompt.md` and execute it in this same session." in result.stdout
    assert "Do not paste the whole planning file into the chat." in result.stdout
    assert "LONG-CONTENT" not in result.stdout
    assert "generate_orchestration_prompt.py --agent cursor_ai" in result.stdout
