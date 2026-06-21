from pathlib import Path

from app import index_diff


def test_index_diff_added_modified_deleted(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    f1 = data_dir / "a.txt"
    f1.write_text("one", encoding="utf-8")

    f2 = data_dir / "b.txt"
    f2.write_text("two", encoding="utf-8")

    monkeypatch.setattr(index_diff, "DATA_DIR", data_dir)
    index_diff.INDEX_META_PATH = tmp_path / "index_meta.json"

    snapshot1 = index_diff._build_snapshot_from_fs()
    index_diff._save_snapshot(snapshot1)

    f3 = data_dir / "c.txt"
    f3.write_text("three", encoding="utf-8")

    f1.write_text("one changed", encoding="utf-8")

    f2.unlink()

    diff = index_diff.get_index_diff()

    assert diff["summary"]["added"] == 1
    assert diff["summary"]["modified"] == 1
    assert diff["summary"]["deleted"] == 1


