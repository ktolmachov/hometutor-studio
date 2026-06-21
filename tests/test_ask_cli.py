import os
import sys
import types
from io import StringIO

import ask


def test_main_passes_profile_without_env_mutation(monkeypatch):
    captured = {}
    monkeypatch.delenv("RAG_PROFILE", raising=False)

    fake_module = types.ModuleType("app.query_service")

    def fake_answer_question(question, options):
        captured["profile"] = options.rag_profile
        return {"answer": "ok", "sources": []}

    fake_module.answer_question = fake_answer_question

    monkeypatch.setitem(sys.modules, "app.query_service", fake_module)
    monkeypatch.setattr(
        ask,
        "_parse_args",
        lambda: types.SimpleNamespace(profile="quality", brief=True, log=None),
    )

    inputs = iter(["", "", "", "", "test question", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    ask.main()

    assert captured["profile"] == "quality"
    assert os.environ.get("RAG_PROFILE") is None


def test_main_uses_shared_input_validation_and_reprompts(monkeypatch):
    captured = {}

    fake_module = types.ModuleType("app.query_service")

    def fake_answer_question(question, options):
        captured["question"] = question
        captured["options"] = options
        return {"answer": "ok", "sources": []}

    fake_module.answer_question = fake_answer_question

    monkeypatch.setitem(sys.modules, "app.query_service", fake_module)
    monkeypatch.setattr(
        ask,
        "_parse_args",
        lambda: types.SimpleNamespace(profile=None, brief=True, log=None),
    )

    inputs = iter([" docs ", "   ", " note.md ", "", "   ", " \nhello   world\n ", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    stdout = StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    ask.main()

    assert captured["question"] == "hello world"
    assert captured["options"].folder == "docs"
    assert captured["options"].folder_rel is None
    assert captured["options"].file_name == "note.md"
    assert captured["options"].relative_path is None
    assert "question_empty" in stdout.getvalue()


def test_main_non_interactive_uses_cli_question_and_filters(monkeypatch):
    captured = {}
    fake_module = types.ModuleType("app.query_service")

    def fake_answer_question(question, options):
        captured["question"] = question
        captured["options"] = options
        return {"answer": "ok", "sources": []}

    fake_module.answer_question = fake_answer_question
    monkeypatch.setitem(sys.modules, "app.query_service", fake_module)
    monkeypatch.setattr(
        ask,
        "_parse_args",
        lambda: types.SimpleNamespace(
            profile="quality",
            brief=True,
            log=None,
            question="  one-shot question  ",
            folder=None,
            folder_rel=" lessons ",
            file_name=" lesson.md ",
            relative_path=None,
            non_interactive=True,
            exit_after_one=False,
            query_mode=None,
            session_id=None,
            new_session=False,
        ),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(AssertionError(prompt)))

    ask.main()

    assert captured["question"] == "one-shot question"
    assert captured["options"].folder_rel == "lessons"
    assert captured["options"].file_name == "lesson.md"


def test_main_non_interactive_requires_question(monkeypatch):
    monkeypatch.setattr(
        ask,
        "_parse_args",
        lambda: types.SimpleNamespace(
            profile=None,
            brief=True,
            log=None,
            question=None,
            non_interactive=True,
            query_mode=None,
            session_id=None,
            new_session=False,
        ),
    )

    try:
        ask.main()
        assert False, "Expected SystemExit"
    except SystemExit as exc:
        assert "requires --question" in str(exc)
