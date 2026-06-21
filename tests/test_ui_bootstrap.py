from app import api_services


def test_get_ui_bootstrap_skips_topics_catalog(monkeypatch):
    monkeypatch.setattr(
        api_services,
        "_probe_local_llm_for_bootstrap",
        lambda: {"reachable": False, "error": "stub"},
    )
    monkeypatch.setattr(api_services, "get_index_stats", lambda: {"files": 3})
    monkeypatch.setattr(api_services, "is_base_services_ready", lambda: True)
    monkeypatch.setattr("app.knowledge_catalog._catalog_cache_get", lambda: {"topics": []})
    monkeypatch.setattr(
        api_services,
        "build_source_readiness_summary",
        lambda _data_dir, _settings: {
            "counts": {"text_ready": 0, "needs_ocr": 0, "problematic": 0},
            "stub": True,
        },
    )

    calls = {"overview": 0, "topics": 0}

    def _overview(*, services=None, catalog=None):
        calls["overview"] += 1
        assert catalog is not None
        return {"total_topics": 2}

    def _topics(*args, **kwargs):
        calls["topics"] += 1
        raise AssertionError("topics catalog must not be loaded in ui/bootstrap")

    monkeypatch.setattr(api_services, "get_kb_overview", _overview)
    monkeypatch.setattr(api_services, "get_topics_catalog", _topics, raising=False)

    out = api_services.get_ui_bootstrap()

    assert out == {
        "index_stats": {"files": 3},
        "kb_overview": {"total_topics": 2},
        "source_readiness": {
            "counts": {"text_ready": 0, "needs_ocr": 0, "problematic": 0},
            "stub": True,
        },
        "llm_local": {"reachable": False, "error": "stub"},
    }
    assert calls["overview"] == 1
    assert calls["topics"] == 0
