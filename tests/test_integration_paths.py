"""Tests for integration path redirection (prompt smoke / benchmark isolation)."""

from __future__ import annotations

from pathlib import Path

from app.config import BASE_DIR
from tests.integration_paths import apply_integration_layout_for_script


def test_apply_integration_layout_for_script_redirects_bm25_and_graph(tmp_path: Path) -> None:
    import app.graph_generation_paths as graph_paths
    import app.hybrid_retrieval as hybrid_retrieval

    restore = apply_integration_layout_for_script(tmp_path)
    try:
        assert hybrid_retrieval._bm25_persist_dir() == tmp_path / "chroma_db" / "bm25_index"
        assert graph_paths.GRAPH_GENERATIONS_ROOT == tmp_path / "data" / "graph_generations"
        assert graph_paths.STAGING_ROOT == graph_paths.GRAPH_GENERATIONS_ROOT / "staging"
        assert graph_paths.BY_GENERATION_ROOT == graph_paths.GRAPH_GENERATIONS_ROOT / "by_generation"
        assert graph_paths.generation_bundle_dir("gen1") == (
            tmp_path / "data" / "graph_generations" / "by_generation" / "gen1"
        )
    finally:
        restore()

    assert hybrid_retrieval._bm25_persist_dir() == BASE_DIR / "chroma_db" / "bm25_index"


def test_apply_integration_layout_for_script_redirects_telemetry(tmp_path: Path) -> None:
    import os

    import app.history_service as history_service
    import app.latency_budget as latency_budget
    import app.metrics_core as metrics_core

    orig_latency = latency_budget.LATENCY_BUDGET_JSONL
    orig_metrics = metrics_core.METRICS_STORE_PATH
    orig_dashboard = metrics_core.METRICS_DASHBOARD_DB_PATH
    orig_history = history_service.HISTORY_PATH

    restore = apply_integration_layout_for_script(tmp_path)
    try:
        logs_dir = tmp_path / "logs"
        assert latency_budget.LATENCY_BUDGET_JSONL == logs_dir / "latency_budget.jsonl"
        assert metrics_core.METRICS_STORE_PATH == logs_dir / "metrics_store.jsonl"
        assert metrics_core.METRICS_DASHBOARD_DB_PATH == logs_dir / "metrics_dashboard.db"
        assert history_service.HISTORY_PATH == logs_dir / "history.jsonl"
        assert os.environ["LLM_COST_LOG_DIR"] == str(logs_dir / "cost_logs")

        from app.config import get_settings

        assert Path(get_settings().llm_cost_log_dir) == logs_dir / "cost_logs"
    finally:
        restore()

    assert latency_budget.LATENCY_BUDGET_JSONL == orig_latency
    assert metrics_core.METRICS_STORE_PATH == orig_metrics
    assert metrics_core.METRICS_DASHBOARD_DB_PATH == orig_dashboard
    assert history_service.HISTORY_PATH == orig_history
