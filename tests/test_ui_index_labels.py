from app.ui.index_labels import index_version_label


def test_index_version_label_empty():
    assert index_version_label(None) == ""
    assert index_version_label({}) == ""


def test_index_version_label_joins():
    assert index_version_label({"collection_name": "c", "last_indexed_at": "2024-01-01"}) == "c:2024-01-01"
