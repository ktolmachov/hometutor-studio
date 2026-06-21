"""E24-A: tutor goal context on QueryOptions, /ask validation, and learner_profile."""

from app.api_requests import AskRequest
from app.ask_goal_snapshot_merge import merge_learner_goal_snapshot_into_ask
from app.input_validation import prepare_ask_request
from app.models import QueryOptions
from app.tutor_orchestrator import build_learner_goal_context_dict, build_tutor_session_state


def test_query_options_cache_key_includes_tutor_goal_fields():
    base = QueryOptions(folder="a")
    with_goal = QueryOptions(folder="a", tutor_goal_subtopic="rag", tutor_goal_time_budget_min=5)
    assert base.cache_key() != with_goal.cache_key()
    hash(with_goal.cache_key())


def test_prepare_ask_request_normalizes_tutor_goal_time_budget():
    class Req:
        question = "hello"
        tutor_goal_time_budget_min = 500

    out = prepare_ask_request(Req())
    assert out.options.tutor_goal_time_budget_min is None

    class Req2:
        question = "hello"
        tutor_goal_time_budget_min = 15

    out2 = prepare_ask_request(Req2())
    assert out2.options.tutor_goal_time_budget_min == 15


def test_prepare_ask_request_truncates_long_goal_string():
    class Req:
        question = "hello"
        tutor_goal_desired_outcome = "x" * 600

    out = prepare_ask_request(Req())
    assert out.options.tutor_goal_desired_outcome is not None
    assert len(out.options.tutor_goal_desired_outcome) == 512


def test_build_learner_goal_context_dict_stable_keys():
    g = build_learner_goal_context_dict(
        topic="Topic",
        preferred_style="balanced",
        learning_goal="exam_prep",
        tutor_goal_subtopic="sub",
        tutor_goal_target_level="recall",
        tutor_goal_desired_outcome="learn X",
        tutor_goal_time_budget_min=7,
    )
    assert set(g.keys()) == {
        "topic",
        "subtopic",
        "target_level",
        "desired_outcome",
        "time_budget_min",
        "preferred_style",
        "learning_goal",
    }
    assert g["topic"] == "Topic"
    assert g["time_budget_min"] == 7


def test_merge_learner_goal_snapshot_fills_missing_tutor_goal_fields(monkeypatch):
    monkeypatch.setattr(
        "app.ask_goal_snapshot_merge.get_learner_goal_snapshot",
        lambda: {
            "goal_context": {
                "subtopic": "snap-sub",
                "target_level": "recall",
                "desired_outcome": "learn it",
                "time_budget_min": 12,
            }
        },
    )
    req = AskRequest(question="hi")
    merged = merge_learner_goal_snapshot_into_ask(req)
    out = prepare_ask_request(merged)
    assert out.options.tutor_goal_subtopic == "snap-sub"
    assert out.options.tutor_goal_target_level == "recall"
    assert out.options.tutor_goal_desired_outcome == "learn it"
    assert out.options.tutor_goal_time_budget_min == 12


def test_merge_learner_goal_snapshot_respects_explicit_tutor_goal_fields(monkeypatch):
    monkeypatch.setattr(
        "app.ask_goal_snapshot_merge.get_learner_goal_snapshot",
        lambda: {
            "goal_context": {
                "subtopic": "from-snap",
                "target_level": "from-tl",
                "time_budget_min": 99,
            }
        },
    )
    req = AskRequest(
        question="hi",
        tutor_goal_subtopic="explicit-sub",
        tutor_goal_time_budget_min=5,
    )
    merged = merge_learner_goal_snapshot_into_ask(req)
    out = prepare_ask_request(merged)
    assert out.options.tutor_goal_subtopic == "explicit-sub"
    assert out.options.tutor_goal_time_budget_min == 5
    assert out.options.tutor_goal_target_level == "from-tl"


def test_merge_learner_goal_snapshot_no_row_unchanged(monkeypatch):
    monkeypatch.setattr("app.ask_goal_snapshot_merge.get_learner_goal_snapshot", lambda: None)
    req = AskRequest(question="hi")
    merged = merge_learner_goal_snapshot_into_ask(req)
    out = prepare_ask_request(merged)
    assert out.options.tutor_goal_subtopic is None
    assert out.options.tutor_goal_time_budget_min is None


def test_build_tutor_session_state_adds_goal_context_to_learner_profile():
    st = build_tutor_session_state(
        current_topic="algebra",
        mastery_level="beginner",
        preferred_style="examples",
        learning_goal="understand_topic",
        quiz_difficulty="recognition",
        tutor_goal_subtopic="linear",
        tutor_goal_time_budget_min=5,
    )
    lp = st["learner_profile"]
    assert isinstance(lp.get("goal_context"), dict)
    assert lp["goal_context"]["subtopic"] == "linear"
    assert lp["goal_context"]["time_budget_min"] == 5
    assert lp["goal_context"]["topic"] == "algebra"
    assert st["learner_goal_context"] == lp["goal_context"]
