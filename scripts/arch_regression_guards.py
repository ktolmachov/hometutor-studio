#!/usr/bin/env python3
"""Architecture regression checks from doc/arch_review_baseline.yaml.

Windows-first counterpart to ``scripts/arch_regression_guards.sh``.
Keep checks dependency-light so they can run in fresh agent sessions.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _force_utf8_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _iter_py_files(rel_dir: str) -> list[Path]:
    return sorted((ROOT / rel_dir).rglob("*.py"))


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _check_no_unexpected_os_environ() -> bool:
    allowed = {
        "app/config.py",
        "app/ingestion_env_diag.py",  # allowlist: AR-2026-05-17-003 diagnostic-only env comparison
    }
    bad: list[str] = []
    for path in _iter_py_files("app"):
        rel = _relative(path)
        if rel in allowed:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "os.environ[" in line:
                bad.append(f"{rel}:{lineno}:{line.strip()}")
    if bad:
        print("FAIL: unexpected os.environ access")
        print("\n".join(bad))
        return False
    print("OK: os.environ access guard")
    return True


def _check_logging_config_uses_settings() -> bool:
    text = _read_text("app/logging_config.py")
    if "os.environ" in text:
        print("FAIL: app/logging_config.py reads raw environment")
        return False
    print("OK: logging_config uses Settings")
    return True


def _check_knowledge_graph_sqlite_owner() -> bool:
    # AR-2026-05-17-002: kg.sqlite I/O belongs to app/knowledge_graph_bundle.py.
    text = _read_text("app/knowledge_graph.py")
    if "sqlite3.connect" in text:
        print("FAIL: app/knowledge_graph.py opens sqlite3 directly (AR-2026-05-17-002)")
        return False
    print("OK: knowledge_graph delegates bundle SQLite I/O")
    return True


def _check_function_size(rel_path: str, func_name: str, max_lines: int) -> bool:
    tree = ast.parse((ROOT / rel_path).read_bytes())
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            size = (node.end_lineno or node.lineno) - node.lineno
            if size > max_lines:
                bad.append(f"{rel_path}:{node.lineno}: {func_name} is {size} lines")
    if bad:
        print(f"FAIL: {func_name} too large")
        print("\n".join(bad))
        return False
    print(f"OK: {func_name} size")
    return True


def _check_file_line_count(rel_path: str, max_lines: int) -> bool:
    lines = len((ROOT / rel_path).read_text(encoding="utf-8").splitlines())
    if lines > max_lines:
        print(f"FAIL: {rel_path} has {lines} lines; max allowed is {max_lines}")
        return False
    print(f"OK: {rel_path} line count ({lines}/{max_lines})")
    return True


def _check_file_max_function_size(rel_path: str, max_lines: int) -> bool:
    tree = ast.parse((ROOT / rel_path).read_bytes())
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            size = (node.end_lineno or node.lineno) - node.lineno + 1
            if size > max_lines:
                bad.append(f"{rel_path}:{node.lineno}: {node.name} is {size} lines")
    if bad:
        print(f"FAIL: {rel_path} function size")
        print("\n".join(bad))
        return False
    print(f"OK: {rel_path} max function size <= {max_lines}")
    return True


def _check_broad_exceptions_annotated(rel_paths: tuple[str, ...]) -> bool:
    bad: list[str] = []
    for rel_path in rel_paths:
        for lineno, line in enumerate(_read_text(rel_path).splitlines(), 1):
            if "except Exception" in line and not ("noqa" in line and "BLE001" in line):
                bad.append(f"{rel_path}:{lineno}:{line.strip()}")
    if bad:
        print("FAIL: broad exceptions missing noqa: BLE001")
        print("\n".join(bad))
        return False
    print("OK: selected broad exceptions annotated")
    return True


def _check_no_f811_suppression_in_app() -> bool:
    bad: list[str] = []
    for path in _iter_py_files("app"):
        rel = _relative(path)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "noqa" in line and "F811" in line:
                bad.append(f"{rel}:{lineno}:{line.strip()}")
    if bad:
        print("FAIL: app/ contains F811 redefinition suppression")
        print("\n".join(bad))
        return False
    print("OK: no F811 suppression in app/")
    return True


def _check_no_new_unannotated_broad_exceptions() -> bool:
    legacy_unannotated = {
        "app/event_tracking.py:65",
        "app/export_utils.py:103",
        "app/flashcard_service.py:155",
        "app/flashcard_service.py:189",
        "app/hybrid_retrieval.py:54",
        "app/hybrid_retrieval.py:67",
        "app/metrics_slo.py:427",
        "app/middleware.py:98",
        "app/offline_service.py:48",
        "app/offline_service.py:119",
        "app/pipeline_factory.py:128",
        "app/query_tutor_context.py:319",
        "app/session_store.py:340",
        "app/ssr_semantic_cache.py:52",
        "app/telegram_handlers.py:127",
        "app/telegram_handlers.py:148",
        "app/telegram_handlers.py:161",
        "app/telegram_handlers.py:186",
        "app/telegram_handlers.py:250",
        "app/telegram_handlers.py:278",
        "app/telegram_notifications.py:55",
        "app/ui/config_env_banner.py:24",
        "app/ui/data_views.py:135",
        "app/ui/data_views.py:211",
        "app/ui/data_views.py:324",
        "app/ui/data_views.py:359",
        "app/ui/interactive_quiz.py:301",
        "app/ui/interactive_quiz.py:467",
        "app/ui/query_tab_ask_panel.py:224",
        "app/ui/query_tab_ask_panel.py:234",
        "app/ui/source_cards.py:124",
        "app/ui/source_cards.py:152",
        "app/ui/source_cards.py:196",
        "app/ui/topics_tab_plan_subtab.py:98",
        "app/ui/topics_tab_plan_subtab.py:123",
        "app/ui/topics_tab_plan_subtab.py:218",
        "app/ui/topics_tab_plan_subtab.py:238",
        "app/ui/topics_tab_synthesis_subtab.py:55",
        "app/voice_service.py:57",
        "app/voice_service.py:71",
        "app/voice_service.py:97",
        "app/voice_service.py:117",
    }
    pattern = re.compile(r"^\s*except\s+Exception\b")
    bad: list[str] = []
    for path in _iter_py_files("app"):
        rel = _relative(path)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            marker = f"{rel}:{lineno}"
            if pattern.search(line) and not ("noqa" in line and "BLE001" in line) and marker not in legacy_unannotated:
                bad.append(f"{marker}:{line.strip()}")
    if bad:
        print("FAIL: new broad exceptions missing noqa: BLE001")
        print("\n".join(bad))
        return False
    print("OK: no new unannotated broad exceptions in app/")
    return True


def _check_no_new_backend_ui_imports() -> bool:
    legacy_backend_ui_imports: set[str] = set()
    bad: list[str] = []
    pattern = re.compile(r"\b(from\s+app\.ui|import\s+app\.ui)")
    for path in sorted((ROOT / "app").glob("*.py")):
        rel = _relative(path)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            marker = f"{rel}:{lineno}"
            if pattern.search(line) and marker not in legacy_backend_ui_imports:
                bad.append(f"{marker}:{line.strip()}")
    if bad:
        print("FAIL: backend modules import from app.ui")
        print("\n".join(bad))
        return False
    print("OK: no new backend app.ui imports")
    return True


def _check_app_modules_documented_or_classified() -> bool:
    legacy_undocumented = {
        "app/adversarial_test_runner.py",
        "app/answer_parser.py",
        "app/api_auth.py",
        "app/api_models_extensions.py",
        "app/api_models_main.py",
        "app/dummy.py",
        "app/educational_metrics_service.py",
        "app/eval_retrieval_comparison.py",
        "app/ingestion_chunk_metadata.py",
        "app/ingestion_enrichment.py",
        "app/ingestion_env_diag.py",
        "app/ingestion_extracted_cache.py",
        "app/ingestion_sections.py",
        "app/ingestion_support.py",
        "app/knowledge_catalog.py",
        "app/knowledge_graph_payload.py",
        "app/knowledge_insights.py",
        "app/knowledge_planning.py",
        "app/knowledge_synthesis.py",
        "app/knowledge_text.py",
        "app/learner_model_history.py",
        "app/metrics_slo.py",
        "app/provider_openai.py",
        "app/query_faq_cache.py",
        "app/quiz_micro.py",
        "app/quiz_micro_receipt.py",
        "app/quiz_parse.py",
        "app/quiz_scoped.py",
        "app/session_analytics_parser.py",
        "app/ssr_ai/eval_harness.py",
        "app/tutor_context_parser.py",
        "app/ui/adaptive_plan_widgets.py",
        "app/ui/anki_export.py",
        "app/ui/answer_helpers.py",
        "app/ui/breadcrumb.py",
        "app/ui/cockpit_rotator.py",
        "app/ui/config_env_banner.py",
        "app/ui/continuity_bridge.py",
        "app/ui/course_prepare_view.py",
        "app/ui/daily_briefing.py",
        "app/ui/data_views.py",
        "app/ui/debug_panel.py",
        "app/ui/expert_controls.py",
        "app/ui/flashcards_read_cache.py",
        "app/ui/flashcards_sections.py",
        "app/ui/focus_mode.py",
        "app/ui/fragments.py",
        "app/ui/hero.py",
        "app/ui/index_labels.py",
        "app/ui/latency_budget_sync.py",
        "app/ui/learner_profile_panel.py",
        "app/ui/longform.py",
        "app/ui/mission_control_first_session.py",
        "app/ui/pages/3_Мой_прогресс.py",
        "app/ui/pages/4_Аналитика.py",
        "app/ui/pages/feedback_insights.py",
        "app/ui/print_view.py",
        "app/ui/qa_wait_ux.py",
        "app/ui/query_tab_ask_panel.py",
        "app/ui/query_tab_helpers.py",
        "app/ui/query_tab_sidebar.py",
        "app/ui/quiz_learning_mode_widgets.py",
        "app/ui/session_state.py",
        "app/ui/sidebar.py",
        "app/ui/source_cards.py",
        "app/ui/streamlit_activity.py",
        "app/ui/study_scope.py",
        "app/ui/styles.py",
        "app/ui/topics_tab_filters.py",
        "app/ui/topics_tab_left_column.py",
        "app/ui/topics_tab_plan_subtab.py",
        "app/ui/topics_tab_synthesis_subtab.py",
        "app/ui/tutor_chat_footer.py",
        "app/ui/tutor_chat_header.py",
        "app/ui/tutor_chat_quiz.py",
        "app/ui/tutor_chat_session.py",
        "app/ui/weekly_study_narrative_ui.py",
        "app/user_state_archive.py",
        "app/user_state_db.py",
        "app/user_state_lineage.py",
    }
    text = _read_text("doc/architecture.md")
    bad: list[str] = []
    for path in _iter_py_files("app"):
        rel = _relative(path)
        name = path.stem
        if name == "__init__" or name.startswith("_") or rel in legacy_undocumented:
            continue
        if rel not in text and name not in text:
            bad.append(rel)
    if bad:
        print("FAIL: app modules missing from doc/architecture.md Module Reference")
        print("\n".join(bad))
        return False
    print("OK: app modules documented or explicitly classified as legacy debt")
    return True


def _check_adr_registry_complete() -> bool:
    lines = _read_text("doc/adr.md").splitlines()
    actual = sum(1 for line in lines if line.startswith("## ADR-"))
    registry_lines = [line for line in lines if line.startswith("| [0")]
    external = sum(1 for line in registry_lines if ".md)" in line)
    registry = len(registry_lines)
    if actual + external == registry:
        print("OK: ADR registry complete")
        return True
    print(f"FAIL: {actual} inline ADRs + {external} external ADRs but {registry} in registry")
    return False


def _check_adr_020_present() -> bool:
    text = _read_text("doc/adr.md")
    if "ADR-020" in text and "Smart Study Router" in text:
        print("OK: ADR-020 present")
        return True
    print("FAIL: ADR-020 missing")
    return False


def _check_adr_023_present() -> bool:
    from pathlib import Path
    path = Path("doc/adr_023_ssr_graph_routing.md")
    if path.exists() and "SSR Graph Routing" in path.read_text(encoding="utf-8"):
        print("OK: ADR-023 (SSR graph routing) present")
        return True
    print("FAIL: ADR-023 missing or incomplete")
    return False


def _check_adr_025_present() -> bool:
    path = ROOT / "doc/adr_025_course_graph_compiler.md"
    if path.exists() and "Course Graph Compiler" in path.read_text(encoding="utf-8"):
        print("OK: ADR-025 (course graph compiler) present")
        return True
    print("FAIL: ADR-025 missing or incomplete")
    return False


def _check_session_tape_adr_accepted() -> bool:
    text = _read_text("doc/adr.md")
    registry_line = next((line for line in text.splitlines() if "[022b]" in line), "")
    if "| Accepted |" in registry_line and "**Статус:** Accepted" in text[text.find('<a id="adr-022-session-tape"'):]:
        print("OK: ADR-022b session tape accepted")
        return True
    print("FAIL: implemented ADR-022b session tape is not Accepted")
    return False


def _check_ssr_modules_documented() -> bool:
    text = _read_text("doc/architecture.md")
    modules = (
        "retrieval_router",
        "smart_study_router",
        "smart_study_recommendation",
        "smart_study_evidence",
        "smart_study_ssr_ml",
        "ssr_ai",
        "ssr_pregeneration",
        "ssr_semantic_cache",
        "ssr_explanation_cache",
        "ssr_explain_service",
        "ssr_context_builder",
        "ssr_weekly_planner",
        "ssr_weekly_narrative",
        "ssr_feedback_collection",
        "ssr_misroute_policy",
        "ssr_llm_profile_summary",
        "ssr_llm_profiling",
        "ssr_ml_monitoring",
        "ssr_ml_reranking",
        "user_state_ssr_feedback",
        "llm_local_circuit",
        "llm_local_health",
        "offline_service",
        "adaptive_plan_step_text",
        "adaptive_plan_card",
        "adaptive_plan_llm_enrichment",
        "adaptive_plan_llm_explanation",
        "llm_local_banner",
        "offline_banner",
        "quick_answer",
        "mission_control",
        "course_cockpit",
        "smart_study_scoring",
        "resume_cards_due",
        "resume_cards_smart_study",
        "resume_cards_tutor",
        "query_tab_answer_section",
        "query_tab_poll",
        "tutor_chat_controls",
        "topics_tab_right_column",
        "tutor_mastery_forecast_panel",
        "kb_fetch",
        # AR-2026-05-29-007: 13 new modules added 2026-05-29
        "eval_baseline",
        "eval_helpers",
        "latency_budget",
        "session_tape",
        "session_replay",
        "first_session_builder",
        "smart_study_recovery_ladder",
        "smart_study_route_simulator",
        "ssr_graph_routing",
        "ssr_explanation_tier_gate",
        "dashboards_graph",
        "dashboards_progress",
        "debug_session_tape",
        "retrieval_cache_discovery",
        "user_state_weekly_narrative",
        "flashcards_review_receipt",
        "due_queue_display",
        "resume_cards_recovery_ladder",
        "routers/ssr",
        "course_graph_compiler",
        "eval_ragas_backend",
        "konspekt_discovery",
        "langfuse_dataset",
        "obsidian_export",
        "prompts/course_graph_extraction",
        "smart_konspekt",
        "ui/knowledge_graph_d3",
    )
    missing = [module for module in modules if module not in text]
    if missing:
        print("FAIL: SSR/module reference entries missing")
        print("\n".join(missing))
        return False
    print("OK: SSR/module reference entries")
    return True


def _check_numpy_declared_if_used() -> bool:
    used = False
    for root in ("app", "scripts", "tests"):
        for path in _iter_py_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"(?m)^(import numpy|from numpy)", text):
                used = True
                break
        if used:
            break
    declared = re.search(r"(?m)^numpy==", _read_text("requirements.txt")) is not None
    if used and not declared:
        print("FAIL: numpy used but not declared in requirements.txt")
        return False
    print("OK: numpy dependency declaration")
    return True


def _check_orchestrator_chat_wrapper() -> bool:
    bad: list[str] = []
    for rel_path in ("app/orchestrator_router.py", "app/tutor_orchestrator.py"):
        for lineno, line in enumerate(_read_text(rel_path).splitlines(), 1):
            stripped = line.strip()
            if ".chat(" in line and "chat_with_resilience" not in line and not stripped.startswith("#"):
                bad.append(f"{rel_path}:{lineno}:{stripped}")
    if bad:
        print("FAIL: direct llm.chat() outside resilience wrapper")
        print("\n".join(bad))
        return False
    print("OK: orchestrator chat resilience wrapper")
    return True


def _check_no_ui_knowledge_graph_imports() -> bool:
    pattern = re.compile(r"^\s*from\s+app\.knowledge_graph\s+import\b")
    bad: list[str] = []
    ui_root = ROOT / "app" / "ui"
    for path in sorted(ui_root.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                bad.append(f"{_relative(path)}:{lineno}:{line.strip()}")
    if bad:
        print("FAIL: UI importing knowledge_graph directly")
        print("\n".join(bad))
        return False
    print("OK: no direct UI knowledge_graph imports")
    return True


def _check_team_workflow_top_level_md_count() -> bool:
    """North star wave-workflow-dx: cap root markdown files under doc/team_workflow (no subdirs)."""
    team_dir = ROOT / "doc" / "team_workflow"
    limit = 50
    md_files = [p for p in team_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md"]
    count = len(md_files)
    if count > limit:
        print(f"FAIL: doc/team_workflow has {count} top-level *.md files; max {limit}")
        return False
    print(f"OK: doc/team_workflow top-level *.md count ({count}/{limit})")
    return True


def _check_prompt_boundary_docs() -> bool:
    docs = (
        "doc/architecture.md",
        "doc/conventions.md",
        "doc/conventions_reference.md",
    )
    bad: list[str] = []
    if (ROOT / "app" / "prompts.py").exists():
        bad.append("app/prompts.py exists; prompt registry should remain app/prompts/")
    if not (ROOT / "app" / "prompts" / "__init__.py").exists():
        bad.append("app/prompts/__init__.py is missing")
    for rel_path in docs:
        for lineno, line in enumerate(_read_text(rel_path).splitlines(), 1):
            if "app/prompts.py" in line:
                bad.append(f"{rel_path}:{lineno}:{line.strip()}")
    if bad:
        print("FAIL: prompt boundary docs reference removed app/prompts.py")
        print("\n".join(bad))
        return False
    print("OK: prompt boundary docs")
    return True


def _check_api_reference_selected_endpoints() -> bool:
    api_doc = _read_text("doc/api_reference.md")
    router_text = "\n".join(
        _read_text(rel_path)
        for rel_path in (
            "app/routers/knowledge.py",
            "app/routers/metrics.py",
            "app/routers/admin.py",
        )
    )
    endpoints = (
        "/kb/source-readiness",
        "/metrics/educational",
        "/metrics/mastery-validation",
        "/learner-state/diagnostics",
    )
    bad: list[str] = []
    for endpoint in endpoints:
        if endpoint not in router_text:
            bad.append(f"{endpoint}: missing from routers")
        if endpoint not in api_doc:
            bad.append(f"{endpoint}: missing from doc/api_reference.md")
    if bad:
        print("FAIL: selected API endpoints missing from docs or routers")
        print("\n".join(bad))
        return False
    print("OK: selected API reference endpoints")
    return True


def _check_inline_import_logging() -> bool:
    """Guard: inline import logging должен быть на строке с except Exception, имеющей # noqa: BLE001."""
    violations: list[str] = []
    for py_file in _iter_py_files("app"):
        lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            # Ищем inline import logging
            if re.match(r"\s+import logging", line) and "logging.getLogger" in line:
                # Проверяем предыдущую строку — должна быть except Exception с noqa: BLE001
                prev_line = lines[i - 1] if i > 0 else ""
                if not (re.match(r"\s+except Exception", prev_line) and "noqa" in prev_line and "BLE001" in prev_line):
                    violations.append(f"{_relative(py_file)}:{i+1}")
    if violations:
        print(f"FAIL: {len(violations)} inline import logging without proper noqa:BLE001 on except Exception")
        for v in violations[:10]:
            print(f"  {v}")
        return False
    print("OK: no unannotated inline import logging")
    return True


def _check_tutor_chat_app_import_fanout(max_modules: int = 15) -> bool:
    """AR-2026-05-08-004: tutor_chat.py keeps a thin facade (ImportFrom + import app.*)."""
    rel_path = "app/ui/tutor_chat.py"
    tree = ast.parse((ROOT / rel_path).read_bytes())
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                mods.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    mods.add(alias.name)
    count = len(mods)
    if count > max_modules:
        print(f"FAIL: {rel_path} app import fan-out is {count}; max allowed {max_modules}")
        for mod in sorted(mods):
            print(f"  {mod}")
        return False
    print(f"OK: tutor_chat.py app import fan-out ({count}/{max_modules})")
    return True


def _check_pipeline_steps_broad_exceptions_annotated() -> bool:
    bad: list[str] = []
    rel_path = "app/pipeline_steps.py"
    for lineno, line in enumerate(_read_text(rel_path).splitlines(), 1):
        if "except Exception" in line and "noqa" not in line and "BLE001" not in line:
            bad.append(f"{rel_path}:{lineno}:{line.strip()}")
    if bad:
        print("FAIL: pipeline_steps broad exceptions missing noqa: BLE001")
        print("\n".join(bad))
        return False
    print("OK: pipeline_steps broad exceptions annotated")
    return True


def main() -> int:
    _force_utf8_stdio()
    checks = (
        _check_no_unexpected_os_environ,
        _check_logging_config_uses_settings,
        _check_knowledge_graph_sqlite_owner,
        lambda: _check_function_size("app/query_service.py", "_assemble_rag_result", 150),
        lambda: _check_function_size("app/ingestion.py", "build_index", 200),
        lambda: _check_file_line_count("app/ingestion.py", 2100),
        lambda: _check_file_line_count("app/smart_study_router.py", 700),
        # AR-2026-05-17-004: scoring helpers belong in smart_study_scoring.py.
        lambda: _check_file_line_count("app/smart_study_recommendation.py", 600),
        # AR-2026-05-17-001: resume_cards.py must stay a small public facade.
        lambda: _check_file_line_count("app/ui/resume_cards.py", 600),
        # AR-2026-05-17-005: UI modules split into focused render/helper files.
        lambda: _check_file_line_count("app/ui/adaptive_plan_card.py", 600),
        lambda: _check_file_line_count("app/ui/adaptive_plan_llm_enrichment.py", 600),
        lambda: _check_file_line_count("app/ui/tutor_chat_render.py", 600),
        lambda: _check_file_max_function_size("app/ui/adaptive_plan_card.py", 120),
        # AR-2026-05-22-003 & -004: eval_service.py and ui/dashboards.py line/function guards
        lambda: _check_file_line_count("app/eval_service.py", 1000),
        lambda: _check_file_line_count("app/ui/dashboards.py", 700),
        lambda: _check_file_max_function_size("app/eval_service.py", 120),
        lambda: _check_file_max_function_size("app/ui/dashboards.py", 200),
        # AR-2026-05-29-002/003/004/005: line-count guards for newly oversized modules
        lambda: _check_file_line_count("app/ui/resume_cards_smart_study.py", 600),
        lambda: _check_file_line_count("app/retrieval_cache.py", 600),
        lambda: _check_file_line_count("app/ui/mission_control.py", 600),
        lambda: _check_file_line_count("app/learner_model_service.py", 700),
        lambda: _check_file_line_count("app/query_service.py", 800),
        _check_adr_registry_complete,
        _check_adr_020_present,
        _check_adr_023_present,
        _check_adr_025_present,
        _check_session_tape_adr_accepted,
        _check_no_f811_suppression_in_app,
        _check_no_new_unannotated_broad_exceptions,
        _check_no_new_backend_ui_imports,
        _check_app_modules_documented_or_classified,
        _check_ssr_modules_documented,
        _check_numpy_declared_if_used,
        _check_orchestrator_chat_wrapper,
        _check_no_ui_knowledge_graph_imports,
        _check_prompt_boundary_docs,
        _check_api_reference_selected_endpoints,
        _check_inline_import_logging,
        _check_tutor_chat_app_import_fanout,
        _check_pipeline_steps_broad_exceptions_annotated,
        lambda: _check_broad_exceptions_annotated(
            (
                "app/llm_resilience.py",
                "app/ui/adaptive_plan_card.py",
                "app/ui/home_hub.py",
                "app/ui/course_cockpit.py",
                "app/api.py",
                "app/ui/sidebar.py",
                "app/ui/topics_tab_right_column.py",
                "app/ui/flashcards_ui.py",
                "app/ui/tutor_chat_response_render.py",
                "app/ui/tutor_mastery_forecast_panel.py",
                "app/ui/dashboards.py",
                "app/ui/query_tab_answer_section.py",
                "app/ui/resume_cards_due.py",
                "app/ui/scoped_quiz.py",
                "app/ui/tutor_chat_controls.py",
                "app/ui/main.py",
                "app/ui/offline_banner.py",
                "app/query_service.py",
                "app/quiz_service.py",
                "app/index_diff.py",
                "app/ingestion_content_state.py",
                "app/index_registry.py",
                "app/retrieval_cache.py",
                "app/ui/topics_tab_plan_subtab.py",
                "app/ui/topics_tab.py",
                "app/ui/knowledge_graph_d3.py",
                "app/obsidian_export.py",
                "app/flashcard_service.py",
                "app/prompt_smoke_checks.py",
            )
        ),
        _check_team_workflow_top_level_md_count,
    )
    ok = True
    for check in checks:
        try:
            ok = check() and ok
        except Exception as exc:  # noqa: BLE001 - guard must report heterogeneous parser/IO failures.
            print(f"FAIL: {getattr(check, '__name__', 'check')} crashed: {exc}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
