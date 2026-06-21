"""Изоляция путей data/chroma/registry для integration-тестов (US-12.3)."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

_BM25_PERSIST_SUBDIR = "bm25_index"


def _graph_generation_roots(data_dir: Path) -> tuple[Path, Path, Path]:
    graph_root = data_dir / "graph_generations"
    return graph_root, graph_root / "staging", graph_root / "by_generation"


def _patch_graph_generation_paths(
    data_dir: Path,
    *,
    saved: list[tuple[object, str, object]] | None = None,
    monkeypatch: MonkeyPatch | None = None,
) -> tuple[Path, Path, Path]:
    import app.graph_generation_paths as graph_paths

    graph_root, staging_root, by_generation_root = _graph_generation_roots(data_dir)
    if monkeypatch is not None:
        monkeypatch.setattr(graph_paths, "GRAPH_GENERATIONS_ROOT", graph_root)
        monkeypatch.setattr(graph_paths, "STAGING_ROOT", staging_root)
        monkeypatch.setattr(graph_paths, "BY_GENERATION_ROOT", by_generation_root)
    else:
        assert saved is not None
        saved.extend(
            [
                (graph_paths, "GRAPH_GENERATIONS_ROOT", graph_paths.GRAPH_GENERATIONS_ROOT),
                (graph_paths, "STAGING_ROOT", graph_paths.STAGING_ROOT),
                (graph_paths, "BY_GENERATION_ROOT", graph_paths.BY_GENERATION_ROOT),
            ]
        )
        graph_paths.GRAPH_GENERATIONS_ROOT = graph_root
        graph_paths.STAGING_ROOT = staging_root
        graph_paths.BY_GENERATION_ROOT = by_generation_root
    return graph_root, staging_root, by_generation_root


def _patch_bm25_persist_dir(
    chroma_dir: Path,
    *,
    saved: list[tuple[object, str, object]] | None = None,
    monkeypatch: MonkeyPatch | None = None,
) -> Path:
    import app.hybrid_retrieval as hybrid_retrieval

    persist_dir = chroma_dir / _BM25_PERSIST_SUBDIR

    def _tmp_bm25_persist_dir() -> Path:
        return persist_dir

    if monkeypatch is not None:
        monkeypatch.setattr(hybrid_retrieval, "_bm25_persist_dir", _tmp_bm25_persist_dir)
    else:
        assert saved is not None
        saved.append((hybrid_retrieval, "_bm25_persist_dir", hybrid_retrieval._bm25_persist_dir))
        hybrid_retrieval._bm25_persist_dir = _tmp_bm25_persist_dir  # type: ignore[assignment]
    return persist_dir


def _patch_telemetry_paths(
    root: Path,
    *,
    saved: list[tuple[object, str, object]] | None = None,
    monkeypatch: MonkeyPatch | None = None,
) -> Path:
    """Перенаправить операционную телеметрию в ``root/logs``.

    Без этого smoke/benchmark/integration-прогоны пишут hard-breach события и
    usage-метрики в боевые ``logs/latency_budget.jsonl``, ``logs/metrics_store.jsonl``,
    ``logs/history.jsonl`` и ``logs/cost_logs`` — искажая дашборды латентности и стоимости.
    Константы модулей захватываются при import, поэтому env-переменных недостаточно.
    """
    import app.history_service as history_service
    import app.latency_budget as latency_budget
    import app.metrics_core as metrics_core

    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    targets: list[tuple[object, str, Path]] = [
        (latency_budget, "LATENCY_BUDGET_JSONL", logs_dir / "latency_budget.jsonl"),
        (metrics_core, "METRICS_STORE_PATH", logs_dir / "metrics_store.jsonl"),
        (metrics_core, "METRICS_DASHBOARD_DB_PATH", logs_dir / "metrics_dashboard.db"),
        (history_service, "HISTORY_PATH", logs_dir / "history.jsonl"),
    ]
    if monkeypatch is not None:
        for mod, name, value in targets:
            monkeypatch.setattr(mod, name, value)
    else:
        assert saved is not None
        for mod, name, value in targets:
            saved.append((mod, name, getattr(mod, name)))
            setattr(mod, name, value)
    return logs_dir


def apply_integration_fs_layout(monkeypatch: MonkeyPatch, root: Path) -> tuple[Path, Path]:
    """
    Перенаправляет data/chroma и связанные артефакты в ``root`` (временная директория).

    Возвращает ``(data_dir, chroma_dir)``.
    """
    data_dir = root / "data"
    chroma_dir = root / "chroma_db"
    data_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    meta_path = root / "index_meta.json"

    import app.config as cfg

    monkeypatch.setattr(cfg, "DATA_DIR", data_dir)
    monkeypatch.setattr(cfg, "CHROMA_DIR", chroma_dir)

    import app.ingestion as ingestion

    monkeypatch.setattr(ingestion, "DATA_DIR", data_dir)
    monkeypatch.setattr(ingestion, "CHROMA_DIR", chroma_dir)

    import app.index_diff as index_diff

    monkeypatch.setattr(index_diff, "DATA_DIR", data_dir)
    monkeypatch.setattr(index_diff, "CHROMA_DIR", chroma_dir)
    monkeypatch.setattr(index_diff, "INDEX_META_PATH", meta_path)

    import app.faq_memory as faq_memory

    monkeypatch.setattr(faq_memory, "CHROMA_DIR", chroma_dir)

    import app.retrieval_cache as retrieval_cache

    monkeypatch.setattr(retrieval_cache, "_chroma_dir", lambda: chroma_dir)

    import app.index_registry as index_registry

    monkeypatch.setattr(index_registry, "REGISTRY_PATH", root / "index_registry.json")
    monkeypatch.setattr(index_registry, "REGISTRY_LOCK_PATH", root / "index_registry.json.lock")
    monkeypatch.setattr(index_registry, "LEGACY_ACTIVE_INDEX_PATH", chroma_dir / "active_index.json")

    monkeypatch.setenv("USER_STATE_DB", str(root / "user_state.db"))
    monkeypatch.setenv("INDEX_META_PATH", str(meta_path))
    monkeypatch.setenv("ACTIVE_INDEX_STATE_PATH", str(chroma_dir / "active_index.json"))
    monkeypatch.setenv("INDEX_REGISTRY_PATH", str(root / "index_registry.json"))
    monkeypatch.setenv("INDEX_REGISTRY_LOCK_PATH", str(root / "index_registry.json.lock"))
    monkeypatch.setenv("ENABLE_METADATA_ENRICHMENT", "false")
    monkeypatch.setenv("ENABLE_DOCUMENT_SUMMARIES", "false")
    # Integration-тесты используют OPENAI_API_BASE для эмбеддингов (индексация + запросы).
    # EMBED_API_BASE сброшен в "" → embed_api_base_resolved вернёт OPENAI_API_BASE.
    # КРИТИЧНО: не удаляем переменную — pydantic-settings перечитает .env и подхватит Ollama.
    monkeypatch.setenv("EMBED_API_BASE", "")
    monkeypatch.setenv("EMBED_MODEL", "text-embedding-3-small")

    _patch_graph_generation_paths(data_dir, monkeypatch=monkeypatch)
    _patch_bm25_persist_dir(chroma_dir, monkeypatch=monkeypatch)
    logs_dir = _patch_telemetry_paths(root, monkeypatch=monkeypatch)
    # Cost-логи читаются из settings на call-time — env + reset_settings_cache ниже.
    monkeypatch.setenv("METRICS_STORE_PATH", str(logs_dir / "metrics_store.jsonl"))
    monkeypatch.setenv("METRICS_DASHBOARD_DB_PATH", str(logs_dir / "metrics_dashboard.db"))
    monkeypatch.setenv("LLM_COST_LOG_DIR", str(logs_dir / "cost_logs"))
    monkeypatch.setenv("HISTORY_PATH", str(logs_dir / "history.jsonl"))

    from app.config import reset_settings_cache

    reset_settings_cache()
    return data_dir, chroma_dir


def apply_integration_layout_for_script(root: Path) -> Callable[[], None]:
    """
    То же перенаправление путей без pytest (для ``scripts/run_quality_benchmark.py``).

    Возвращает ``restore()`` для отката атрибутов модулей и очистки os.environ.
    """
    data_dir = root / "data"
    chroma_dir = root / "chroma_db"
    data_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    meta_path = root / "index_meta.json"

    import app.config as cfg
    import app.faq_memory as faq_memory
    import app.index_diff as index_diff
    import app.index_registry as index_registry
    import app.ingestion as ingestion
    import app.retrieval_cache as retrieval_cache

    saved: list[tuple[object, str, object]] = [
        (cfg, "DATA_DIR", cfg.DATA_DIR),
        (cfg, "CHROMA_DIR", cfg.CHROMA_DIR),
        (ingestion, "DATA_DIR", ingestion.DATA_DIR),
        (ingestion, "CHROMA_DIR", ingestion.CHROMA_DIR),
        (index_diff, "DATA_DIR", index_diff.DATA_DIR),
        (index_diff, "CHROMA_DIR", index_diff.CHROMA_DIR),
        (index_diff, "INDEX_META_PATH", index_diff.INDEX_META_PATH),
        (faq_memory, "CHROMA_DIR", faq_memory.CHROMA_DIR),
        (index_registry, "REGISTRY_PATH", index_registry.REGISTRY_PATH),
        (index_registry, "REGISTRY_LOCK_PATH", index_registry.REGISTRY_LOCK_PATH),
        (index_registry, "LEGACY_ACTIVE_INDEX_PATH", index_registry.LEGACY_ACTIVE_INDEX_PATH),
    ]

    cfg.DATA_DIR = data_dir
    cfg.CHROMA_DIR = chroma_dir
    ingestion.DATA_DIR = data_dir
    ingestion.CHROMA_DIR = chroma_dir
    index_diff.DATA_DIR = data_dir
    index_diff.CHROMA_DIR = chroma_dir
    index_diff.INDEX_META_PATH = meta_path
    faq_memory.CHROMA_DIR = chroma_dir
    index_registry.REGISTRY_PATH = root / "index_registry.json"
    index_registry.REGISTRY_LOCK_PATH = root / "index_registry.json.lock"
    index_registry.LEGACY_ACTIVE_INDEX_PATH = chroma_dir / "active_index.json"

    _orig_chroma_dir = retrieval_cache._chroma_dir

    def _tmp_chroma():
        return chroma_dir

    retrieval_cache._chroma_dir = _tmp_chroma  # type: ignore[assignment]

    _patch_graph_generation_paths(data_dir, saved=saved)
    _patch_bm25_persist_dir(chroma_dir, saved=saved)
    logs_dir = _patch_telemetry_paths(root, saved=saved)

    env_keys = (
        "USER_STATE_DB",
        "INDEX_META_PATH",
        "ACTIVE_INDEX_STATE_PATH",
        "INDEX_REGISTRY_PATH",
        "INDEX_REGISTRY_LOCK_PATH",
        "ENABLE_METADATA_ENRICHMENT",
        "ENABLE_DOCUMENT_SUMMARIES",
        "EMBED_API_BASE",
        "EMBED_MODEL",
        "METRICS_STORE_PATH",
        "METRICS_DASHBOARD_DB_PATH",
        "LLM_COST_LOG_DIR",
        "HISTORY_PATH",
    )
    env_saved: dict[str, str | None] = {k: os.environ.get(k) for k in env_keys}

    os.environ["USER_STATE_DB"] = str(root / "user_state.db")
    os.environ["INDEX_META_PATH"] = str(meta_path)
    os.environ["ACTIVE_INDEX_STATE_PATH"] = str(chroma_dir / "active_index.json")
    os.environ["INDEX_REGISTRY_PATH"] = str(root / "index_registry.json")
    os.environ["INDEX_REGISTRY_LOCK_PATH"] = str(root / "index_registry.json.lock")
    os.environ["ENABLE_METADATA_ENRICHMENT"] = "false"
    os.environ["ENABLE_DOCUMENT_SUMMARIES"] = "false"
    os.environ["EMBED_API_BASE"] = ""
    os.environ["EMBED_MODEL"] = "text-embedding-3-small"
    # Cost-логи (llm_guards) читают settings на call-time — env + reset ниже достаточно.
    os.environ["METRICS_STORE_PATH"] = str(logs_dir / "metrics_store.jsonl")
    os.environ["METRICS_DASHBOARD_DB_PATH"] = str(logs_dir / "metrics_dashboard.db")
    os.environ["LLM_COST_LOG_DIR"] = str(logs_dir / "cost_logs")
    os.environ["HISTORY_PATH"] = str(logs_dir / "history.jsonl")

    from app.config import reset_settings_cache

    reset_settings_cache()

    def restore() -> None:
        retrieval_cache._chroma_dir = _orig_chroma_dir  # type: ignore[assignment]
        for mod, name, val in saved:
            setattr(mod, name, val)
        for k, old in env_saved.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old
        reset_settings_cache()

    return restore
