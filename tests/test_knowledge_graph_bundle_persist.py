"""Персистентность KG bundle: UTF-8 для property graph (Windows cp1252)."""

from __future__ import annotations

from app.knowledge_graph_bundle import PROPERTY_GRAPH_STORE_NAME, persist_graph_bundle_to_dir


def test_persist_property_graph_writes_utf8_cyrillic(tmp_path):
    bundle = tmp_path / "bundle"
    data = {
        "concepts": {"Тема_кириллица": {"summary": "Описание"}},
        "documents": {},
    }
    persist_graph_bundle_to_dir(bundle, data)
    text = (bundle / PROPERTY_GRAPH_STORE_NAME).read_text(encoding="utf-8")
    assert "Тема_кириллица" in text
    assert "Описание" in text
