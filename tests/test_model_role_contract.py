"""Static guards for the home_rag model-role contract.

These checks are intentionally lightweight: they scan source files without
importing app modules, so a broken runtime dependency cannot hide a routing
regression.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

PROVIDER_OPENAI_ALLOWLIST = {
    "app/provider.py",
    "app/provider_openai.py",
}

RAW_ENV_ALLOWLIST = {
    "app/config.py",
    "app/flashcard_service.py",  # legacy E2E-only HOME_RAG_E2E_OFFLINE shortcut
    "app/ingestion_env_diag.py",  # diagnostic-only raw env comparison
    "app/llm_local_circuit.py",  # legacy low-level CB knobs
}

GRAPH_ORCHESTRATION_MODULES = {
    "app/orchestrator_router.py",
    "app/tutor_orchestrator.py",
}


def _app_py_files() -> list[Path]:
    return sorted(APP.rglob("*.py"))


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=_rel(path))


def test_openai_client_construction_stays_in_provider_layer() -> None:
    offenders: list[str] = []
    for path in _app_py_files():
        rel = _rel(path)
        if rel in PROVIDER_OPENAI_ALLOWLIST:
            continue
        tree = _parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "OpenAI":
                offenders.append(f"{rel}:{node.lineno}")
    assert offenders == []


def test_graph_orchestration_uses_graph_llm_not_primary_chat_llm() -> None:
    offenders: list[str] = []
    missing_graph_role: list[str] = []
    for rel in sorted(GRAPH_ORCHESTRATION_MODULES):
        path = ROOT / rel
        tree = _parse(path)
        imported_get_graph = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.provider":
                names = {alias.name for alias in node.names}
                if "get_llm" in names:
                    offenders.append(f"{rel}:{node.lineno}")
                if "get_graph_llm" in names:
                    imported_get_graph = True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "get_llm":
                offenders.append(f"{rel}:{node.lineno}")
        if not imported_get_graph:
            missing_graph_role.append(rel)
    assert offenders == []
    assert missing_graph_role == []


def test_app_raw_env_access_stays_in_documented_allowlist() -> None:
    offenders: list[str] = []
    for path in _app_py_files():
        rel = _rel(path)
        if rel in RAW_ENV_ALLOWLIST:
            continue
        tree = _parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "os" and node.attr in {"getenv", "environ"}:
                    offenders.append(f"{rel}:{node.lineno}:os.{node.attr}")
    assert offenders == []
