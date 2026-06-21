import app.offline_service as osvc
from app.config import reset_settings_cache
from app.knowledge_graph import JsonKnowledgeGraph


def test_get_offline_status_respects_offline_mode(monkeypatch):
    reset_settings_cache()

    class S:
        offline_mode = True
        offline_probe_llm_endpoint = True
        llm_api_base = "https://example.invalid"

    monkeypatch.setattr(osvc, "get_settings", lambda: S())
    monkeypatch.setattr(osvc, "_probe_cache", None)
    out = osvc.get_offline_status(use_cache=False)
    assert out["offline_mode"] is True
    assert out["llm_reachable"] is None


def test_probe_llm_base_reachable_false(monkeypatch):
    reset_settings_cache()

    class S:
        llm_api_base = "https://127.0.0.1:9"  # closed port

    monkeypatch.setattr(osvc, "get_settings", lambda: S())
    assert osvc.probe_llm_base_reachable(timeout_sec=0.5) is False


def test_precompute_weak_topic_quizzes_uses_active_graph_scope(monkeypatch, tmp_path):
    reset_settings_cache()
    p = tmp_path / "offline_graph.json"
    p.write_text(
        '{"concepts":{"A":{"description":"","prerequisites":[]}},"documents":{},"edges":{}}',
        encoding="utf-8",
    )
    kg = JsonKnowledgeGraph(p)
    monkeypatch.setattr(osvc, "get_active_knowledge_graph", lambda: kg)
    monkeypatch.setattr(
        osvc,
        "weak_concepts_for_kg",
        lambda graph, threshold=60, limit=5: ["A"] if graph is kg else ["legacy"],
    )
    monkeypatch.setattr(
        "app.quiz_service.generate_scoped_quiz",
        lambda resource_type, topic: {"success": False, "error": "stubbed"},
    )

    out = osvc.precompute_weak_topic_quizzes(max_topics=5)

    assert out["weak_topics"] == ["A"]
