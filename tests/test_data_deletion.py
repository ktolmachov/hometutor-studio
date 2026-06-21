"""Tests for scripts/delete_all_data.py — локальный data deletion + verification."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "delete_all_data.py"


@pytest.fixture(scope="module")
def deletion_mod():
    spec = importlib.util.spec_from_file_location("delete_all_data", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_settings(tmp_path: Path):
    from app.config import Settings

    base = tmp_path
    data = base / "data"
    logs = base / "logs"
    chroma = base / "chroma_db"
    return Settings.model_construct(
        user_state_db=str(data / "user_state.db"),
        metrics_store_path=logs / "metrics_store.jsonl",
        metrics_dashboard_db_path=logs / "metrics_dashboard.db",
        llm_cost_log_dir=logs / "cost_logs",
        feedback_path=logs / "feedback.jsonl",
        history_path=logs / "history.jsonl",
        faq_memory_path=base / "faq_memory.jsonl",
        index_meta_path=base / "index_meta.json",
        index_registry_path=base / "index_registry.json",
        index_registry_lock_path=base / "index_registry.json.lock",
        active_index_state_path=chroma / "active_index.json",
    )


def _seed_deletion_fixtures(tmp_path: Path, settings) -> None:
    from app.config import CHROMA_DIR, DATA_DIR

    chroma = CHROMA_DIR
    chroma.mkdir(parents=True, exist_ok=True)
    (chroma / "active_index.json").write_text("{}", encoding="utf-8")
    (chroma / "x.sqlite").write_text("x", encoding="utf-8")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "concept_graph.json").write_text("{}", encoding="utf-8")
    gg = DATA_DIR / "graph_generations"
    gg.mkdir(parents=True, exist_ok=True)
    (gg / "a.json").write_text("1", encoding="utf-8")

    cache = Path(settings.user_state_db).parent / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "course_artifacts.json").write_text("{}", encoding="utf-8")

    Path(settings.user_state_db).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.user_state_db).write_text("sqlite", encoding="utf-8")

    Path(settings.metrics_store_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.metrics_store_path).write_text("\n", encoding="utf-8")
    Path(settings.metrics_dashboard_db_path).write_bytes(b"")
    Path(settings.feedback_path).write_text("\n", encoding="utf-8")
    Path(settings.history_path).write_text("\n", encoding="utf-8")
    Path(settings.faq_memory_path).write_text("\n", encoding="utf-8")
    Path(settings.index_meta_path).write_text("{}", encoding="utf-8")
    Path(settings.index_registry_path).write_text("{}", encoding="utf-8")
    Path(settings.index_registry_lock_path).write_text("lock", encoding="utf-8")

    cost = Path(settings.llm_cost_log_dir)
    cost.mkdir(parents=True, exist_ok=True)
    (cost / "run1.jsonl").write_text("{}", encoding="utf-8")


def test_delete_rejects_wrong_token(deletion_mod, tmp_path, monkeypatch):
    from app import config as config_mod

    fake = _fake_settings(tmp_path)
    monkeypatch.setattr(config_mod, "get_settings", lambda: fake)
    monkeypatch.setattr(config_mod, "CHROMA_DIR", tmp_path / "chroma_db")
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config_mod, "LOG_DIR", tmp_path / "logs")

    with pytest.raises(ValueError, match="Подтверждение отклонено"):
        deletion_mod.delete_all_local_data(confirm_token="WRONG")


def test_verify_only_flags_remaining(deletion_mod, tmp_path, monkeypatch):
    from app import config as config_mod

    fake = _fake_settings(tmp_path)
    monkeypatch.setattr(config_mod, "get_settings", lambda: fake)
    monkeypatch.setattr(config_mod, "CHROMA_DIR", tmp_path / "chroma_db")
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config_mod, "LOG_DIR", tmp_path / "logs")

    _seed_deletion_fixtures(tmp_path, fake)
    ok, left = deletion_mod.verify_deletion_complete()
    assert ok is False
    assert len(left) > 0

    rc = deletion_mod.main(["--verify-only"])
    assert rc == 2


def test_delete_all_then_verify_ok(deletion_mod, tmp_path, monkeypatch):
    from app import config as config_mod

    fake = _fake_settings(tmp_path)
    monkeypatch.setattr(config_mod, "get_settings", lambda: fake)
    monkeypatch.setattr(config_mod, "CHROMA_DIR", tmp_path / "chroma_db")
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config_mod, "LOG_DIR", tmp_path / "logs")

    _seed_deletion_fixtures(tmp_path, fake)

    out = deletion_mod.delete_all_local_data(confirm_token=deletion_mod.CONFIRM_TOKEN)
    assert out["verify_ok"] is True
    assert out["remaining"] == []

    ok, left = deletion_mod.verify_deletion_complete()
    assert ok and left == []

    rc = deletion_mod.main(["--verify-only"])
    assert rc == 0

    corpus = tmp_path / "data" / "keep_corpus.txt"
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text("not deleted", encoding="utf-8")
    assert corpus.exists()


def test_main_requires_confirm_or_verify(deletion_mod):
    with pytest.raises(SystemExit) as exc:
        deletion_mod.main([])
    assert exc.value.code == 2
