"""Режимы шаблонов промпта квиза (QUIZ_LEARNING_MODE_*)."""

from app.prompts import (
    normalize_quiz_learning_mode,
    quiz_interactive_mode_block,
    quiz_mc_mode_block,
)


def test_normalize_quiz_learning_mode_defaults():
    assert normalize_quiz_learning_mode(None) == "default"
    assert normalize_quiz_learning_mode("") == "default"
    assert normalize_quiz_learning_mode("auto") == "default"
    assert normalize_quiz_learning_mode("understand_topic") == "understand_topic"
    assert normalize_quiz_learning_mode("EXAM_PREP") == "exam_prep"


def test_normalize_quiz_learning_mode_aliases():
    assert normalize_quiz_learning_mode("exam") == "exam_prep"
    assert normalize_quiz_learning_mode("homework") == "solve_homework"


def test_quiz_mc_mode_block_non_empty_for_exam():
    b = quiz_mc_mode_block("exam_prep")
    assert "экзамен" in b.lower()


def test_quiz_interactive_mode_block_empty_for_default():
    assert quiz_interactive_mode_block("default") == ""


def test_self_check_prompt_has_mode_placeholder():
    from app.prompts import QUIZ_SELF_CHECK_PROMPT

    s = QUIZ_SELF_CHECK_PROMPT.format(
        mode_block="MODE_MARKER\n",
        title="t",
        context_str="x" * 200,
        adaptive_profile="тестовый профиль",
    )
    assert "MODE_MARKER" in s
    assert "Правила:" in s


def test_generate_scoped_quiz_passes_learning_mode_into_llm_prompt(monkeypatch):
    """learning_mode меняет текст промпта (режим «экзамен»)."""
    from app import quiz_service

    captured: list[str] = []

    _one_q = (
        '{"question":"q","options":["a","b","c","d"],"correct_index":0,'
        '"difficulty":"recognition","explanation":""}'
    )

    class _FakeResp:
        text = "[" + ",".join([_one_q] * 6) + "]"
        source_nodes = []

    class _FakeLLM:
        def complete(self, prompt, **kwargs):
            captured.append(prompt)
            return _FakeResp()

    monkeypatch.setattr(quiz_service, "get_quiz_llm_for_generation", lambda: _FakeLLM())

    def _fake_explain(ident: str):
        return {"content_preview": "x" * 200}

    monkeypatch.setattr("app.explain_service.explain_file", _fake_explain)

    out = quiz_service.generate_scoped_quiz(
        "document",
        "notes/a.md",
        num_questions=6,
        difficulty="adaptive",
        learning_mode="exam_prep",
    )
    assert out.get("success") is True
    assert captured, "LLM.complete should run"
    assert "экзамен" in captured[0].lower()
