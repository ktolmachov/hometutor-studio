"""PedagogicalRouter: оркестратор без полного RAG-пути."""

from app.orchestrator_router import PedagogicalRouter


def test_router_default_llm_uses_graph_role(monkeypatch):
    class GraphLlm:
        marker = "graph"

    monkeypatch.setattr("app.orchestrator_router.get_graph_llm", lambda: GraphLlm())

    router = PedagogicalRouter()

    assert router._llm.marker == "graph"


def test_route_and_execute_skips_llm_agents_by_default(monkeypatch):
    def fake_invoke(**kwargs):
        assert "knowledge_graph_subgraph_override" in kwargs
        return (
            {
                "reasoning_steps": ["a", "b", "c", "d"],
                "selected_agent": "ConceptExplainer",
                "rationale": "test",
                "parameters": {
                    "focus_concepts": [],
                    "question_type": "probing",
                    "depth": "intermediate",
                    "motivation_link": "",
                },
                "should_trigger_microquiz": False,
                "next_best_action": "",
                "confidence_score": 0.9,
            },
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    monkeypatch.setattr(
        "app.orchestrator_router.invoke_pedagogical_orchestrator_llm",
        fake_invoke,
    )

    class DummyLlm:
        def chat(self, *a, **k):
            raise AssertionError("agent LLM should not run when execute_agents=False")

    r = PedagogicalRouter(llm=DummyLlm())
    state = r.route_and_execute(
        {
            "current_topic": "T",
            "mastery_level": "intermediate",
            "learning_goal": "understand_topic",
            "preferred_style": "balanced",
            "quiz_difficulty": "recognition",
            "user_message": "Что такое T?",
        },
        execute_agents=False,
    )
    assert state["selected_agent"] == "ConceptExplainer"
    assert "personalized_subgraph" in state
    assert "agent_response" not in state
