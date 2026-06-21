"""Резервное копирование индекса и политика lifecycle (итерация 16 tail)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from app.index_backup import (
    BACKUP_SCHEMA_VERSION,
    MANIFEST_NAME,
    collect_backup_entries,
    create_backup_zip,
    restore_backup_zip,
)
from app.index_lifecycle import apply_index_activation_hooks, lifecycle_policy_summary


def test_collect_backup_entries_minimal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "proj"
    (base / "chroma_db" / "sub").mkdir(parents=True)
    (base / "chroma_db" / "sub" / "a.bin").write_bytes(b"x")
    reg = base / "index_registry.json"
    reg.write_text('{"schema_version":1}', encoding="utf-8")

    monkeypatch.setattr("app.index_backup.CHROMA_DIR", base / "chroma_db")
    monkeypatch.setattr("app.index_backup.REGISTRY_PATH", reg)
    monkeypatch.setattr("app.index_backup.INDEX_META_PATH", base / "missing_meta.json")
    monkeypatch.setattr("app.index_backup.DATA_DIR", base / "data")
    (base / "data").mkdir(parents=True)

    entries = collect_backup_entries(base_dir=base, include_concept_graph=False, include_faq_memory=False)
    arcs = {e[0] for e in entries}
    assert "index_registry.json" in arcs
    assert any("chroma_db" in a for a in arcs)


def test_backup_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "proj"
    (base / "chroma_db").mkdir(parents=True)
    (base / "chroma_db" / "x.sqlite3").write_text("sqlite", encoding="utf-8")
    reg = base / "index_registry.json"
    reg.write_text(json.dumps({"schema_version": 1, "index_version": 2}), encoding="utf-8")

    monkeypatch.setattr("app.index_backup.CHROMA_DIR", base / "chroma_db")
    monkeypatch.setattr("app.index_backup.REGISTRY_PATH", reg)
    monkeypatch.setattr("app.index_backup.INDEX_META_PATH", base / "index_meta.json")
    meta = base / "index_meta.json"
    meta.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.index_backup.DATA_DIR", base / "data")
    (base / "data").mkdir(parents=True)

    archive = tmp_path / "b.zip"
    create_backup_zip(archive, base_dir=base, include_concept_graph=False, include_faq_memory=False)

    with zipfile.ZipFile(archive, "r") as zf:
        assert MANIFEST_NAME in zf.namelist()
        man = json.loads(zf.read(MANIFEST_NAME).decode("utf-8"))
        assert man["schema_version"] == BACKUP_SCHEMA_VERSION

    target = tmp_path / "restored"
    target.mkdir(parents=True)
    restore_backup_zip(archive, base_dir=target)

    assert (target / "index_registry.json").exists()
    assert (target / "chroma_db" / "x.sqlite3").read_text(encoding="utf-8") == "sqlite"


def test_restore_backup_zip_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(MANIFEST_NAME, json.dumps({"schema_version": BACKUP_SCHEMA_VERSION}))
        zf.writestr("../escape.txt", "owned")

    target = tmp_path / "restored"
    target.mkdir()

    with pytest.raises(ValueError, match="Unsafe backup member path"):
        restore_backup_zip(archive, base_dir=target)

    assert not (tmp_path / "escape.txt").exists()


def test_apply_index_activation_hooks_syncs_learner_lineage(
    settings_env,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После активации индекса eager-sync переносит stale spaced_repetition в archive."""
    import app.user_state as user_state

    db_path = tmp_path / "user_state.db"
    settings_env({"USER_STATE_DB": str(db_path)})

    def _seed(conn) -> None:
        user_state._ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO spaced_repetition(
                concept, easiness, interval_days, repetitions, next_review, last_review,
                generation_id, index_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("c1", 2.5, 1, 0, None, None, "gen_old", 1),
        )
        conn.commit()

    user_state._with_db(_seed)

    monkeypatch.setattr(
        user_state,
        "get_current_learner_state_lineage",
        lambda: {"generation_id": "gen_new", "index_version": 2},
    )

    out = apply_index_activation_hooks(reset=False)
    assert out.get("learner_state_lineage", {}).get("generation_id") == "gen_new"

    def _check(conn) -> tuple[int, int]:
        user_state._ensure_schema(conn)
        live = conn.execute(
            "SELECT COUNT(*) AS n FROM spaced_repetition WHERE concept = ?",
            ("c1",),
        ).fetchone()["n"]
        arch = conn.execute(
            "SELECT COUNT(*) AS n FROM spaced_repetition_archive WHERE concept = ?",
            ("c1",),
        ).fetchone()["n"]
        return int(live), int(arch)

    live_n, arch_n = user_state._with_db(_check)
    assert live_n == 0
    assert arch_n == 1


def test_apply_index_activation_hooks_clears_faq_when_enabled(
    settings_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[int] = []

    def _stub() -> None:
        called.append(1)

    monkeypatch.setattr("app.faq_memory.clear_faq_memory_file", _stub)
    settings_env({"CLEAR_FAQ_ON_INDEX_ACTIVATION": "true"})
    apply_index_activation_hooks(reset=True)
    assert called == [1]


def test_clear_faq_memory_file_truncates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.faq_memory as faq_memory

    p = tmp_path / "faq_memory.jsonl"
    p.write_text('{"q":1}\n', encoding="utf-8")
    monkeypatch.setattr(faq_memory, "FAQ_MEMORY_PATH", p)
    faq_memory.clear_faq_memory_file()
    assert p.read_text(encoding="utf-8") == ""


def test_lifecycle_policy_summary() -> None:
    s = lifecycle_policy_summary()
    assert "clear_faq_on_index_activation" in s
    assert "doc/index_lifecycle.md" in s["note"]
