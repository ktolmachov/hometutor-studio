import json

import pytest

from app.models import Message
from app.quiz_service import (
    InvalidMicroQuizQuestionError,
    build_flashcard_deck_request_from_interactive_quiz,
    format_correct_for_export,
    format_tutor_v2_markdown,
    generate_interactive_quiz,
    generate_micro_quiz,
    generate_self_check_quiz,
    normalize_quiz_question_for_evaluation,
    parse_quiz_json,
    parse_tutor_quiz_llm_json,
    parse_tutor_rag_response,
    process_micro_quiz_outcome,
    quiz_answer_correct,
    split_tutor_answer_and_quiz,
    topic_from_last_user_message,
    TUTOR_INLINE_QUIZ_MARKER,
    TUTOR_SOCRATIC_MARKER,
)


def test_parse_quiz_rejects_wrong_count():
    bad = '[{"question":"q","options":["a","b","c","d"],"correct_index":0}]'
    qs, err = parse_quiz_json(bad)
    assert qs == []
    assert err is not None


def _interactive_quiz_payload(overrides=None):
    payload = {
        "quiz_title": "Tutor check",
        "questions": [
            {
                "type": "multiple_choice",
                "q": "Pick retrieval.",
                "options": ["A. Search", "B. Paint", "C. Sleep", "D. Skip"],
                "correct": "a",
                "explanation": "Use search.",
                "concept": "retrieval",
            },
            {
                "type": "true_false",
                "q": "RAG uses sources.",
                "options": ["True", "False"],
                "correct": "yes",
                "explanation": "It grounds answers.",
                "concept": "RAG",
            },
            {
                "type": "fill_blank",
                "q": "The index stores ____.",
                "options": [],
                "correct": "chunks",
                "explanation": "Chunks are searched.",
                "concept": "index",
            },
            {
                "type": "ordering",
                "q": "Order the loop.",
                "options": ["A. Ingest", "B. Retrieve", "C. Answer"],
                "correct": [1, 2, 3],
                "explanation": "Pipeline order.",
                "concept": "pipeline",
            },
            {
                "type": "multiple_choice",
                "q": "Pick embedding role.",
                "options": ["A. Vectors", "B. Toast", "C. CSS", "D. Mail"],
                "correct": "D",
                "explanation": "Deliberately odd fixture.",
                "concept": "embedding",
            },
        ],
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_parse_tutor_quiz_llm_json_valid_fenced_v23():
    raw = "```json\n" + json.dumps(_interactive_quiz_payload()) + "\n```"
    quiz, err = parse_tutor_quiz_llm_json(raw, n_questions=5)
    assert err is None
    assert quiz is not None
    assert quiz["quiz_title"] == "Tutor check"
    assert len(quiz["questions"]) == 5
    assert quiz["questions"][0]["options"][0] == "Search"
    assert quiz["questions"][0]["correct"] == "A"
    assert quiz["questions"][1]["correct"] == "True"
    assert quiz["questions"][3]["correct"] == ["Ingest", "Retrieve", "Answer"]


def test_parse_tutor_quiz_llm_json_invalid_json():
    quiz, err = parse_tutor_quiz_llm_json("not-json")
    assert quiz is None
    assert err == "Ответ модели не похож на JSON-объект."


def test_parse_tutor_quiz_llm_json_wrong_question_count():
    payload = _interactive_quiz_payload(
        {"questions": _interactive_quiz_payload()["questions"][:4]}
    )
    quiz, err = parse_tutor_quiz_llm_json(json.dumps(payload), n_questions=5)
    assert quiz is None
    assert err == "Ожидалось ровно 5 вопросов в questions."


def test_parse_tutor_quiz_llm_json_requires_all_question_types():
    payload = _interactive_quiz_payload()
    payload["questions"][3] = {
        "type": "multiple_choice",
        "q": "Another MC.",
        "options": ["A. One", "B. Two", "C. Three", "D. Four"],
        "correct": "B",
        "explanation": "",
        "concept": "",
    }
    quiz, err = parse_tutor_quiz_llm_json(json.dumps(payload), n_questions=5)
    assert quiz is None
    assert err == "В квизе должны встретиться все типы вопросов; не хватает: ordering."


def test_parse_tutor_quiz_llm_json_ordering_accepts_string_positions_and_substrings():
    payload = _interactive_quiz_payload()
    payload["questions"][3]["options"] = ["A. Draft", "B. Review", "C. Ship"]
    payload["questions"][3]["correct"] = ["2", "Ship", "Dra"]
    quiz, err = parse_tutor_quiz_llm_json(json.dumps(payload), n_questions=5)
    assert err is None
    assert quiz is not None
    assert quiz["questions"][3]["correct"] == ["Review", "Ship", "Draft"]


def test_parse_tutor_quiz_llm_json_ordering_accepts_fuzzy_option_text():
    payload = _interactive_quiz_payload()
    payload["questions"][3]["options"] = [
        "1. Создать индекс и векторную базу",
        "2. Найти релевантные чанки",
        "3. Сгенерировать финальный ответ",
    ]
    payload["questions"][3]["correct"] = [
        "создание индекса и векторной базы",
        "извлечение релевантных чанков",
        "генерация финального ответа",
    ]
    quiz, err = parse_tutor_quiz_llm_json(json.dumps(payload, ensure_ascii=False), n_questions=5)
    assert err is None
    assert quiz is not None
    assert quiz["questions"][3]["correct"] == [
        "Создать индекс и векторную базу",
        "Найти релевантные чанки",
        "Сгенерировать финальный ответ",
    ]


def test_quiz_answer_correct_and_format_correct_for_export():
    payload = _interactive_quiz_payload()
    quiz, err = parse_tutor_quiz_llm_json(json.dumps(payload), n_questions=5)
    assert err is None
    assert quiz is not None
    mc, tf, fill, ordering = quiz["questions"][:4]
    assert quiz_answer_correct(mc, " a ")
    assert quiz_answer_correct(tf, "True")
    assert quiz_answer_correct(fill, " CHUNKS ")
    assert quiz_answer_correct(ordering, "A. Ingest; B. Retrieve; C. Answer")
    assert not quiz_answer_correct(ordering, "Retrieve, Ingest, Answer")
    assert format_correct_for_export(ordering) == '["Ingest", "Retrieve", "Answer"]'


def test_build_flashcard_deck_request_from_interactive_quiz_us_15_6():
    payload = _interactive_quiz_payload()
    quiz, err = parse_tutor_quiz_llm_json(json.dumps(payload), n_questions=5)
    assert err is None and quiz is not None
    quiz["identifier"] = "quiz-doc-1"
    body = build_flashcard_deck_request_from_interactive_quiz(quiz, quiz["questions"])
    assert body is not None
    assert body["source_type"] == "quiz"
    assert body["name"] == "Quiz: Tutor check"
    assert body["source_identifier"] == "quiz-doc-1"
    assert len(body["cards"]) == 5
    assert body["cards"][0]["front"] == "Pick retrieval."
    assert "Search" in body["cards"][0]["back"] or "A" in body["cards"][0]["back"]
    assert body["cards"][0]["tags"] == "retrieval"


def test_build_flashcard_deck_request_from_interactive_quiz_empty_returns_none():
    assert build_flashcard_deck_request_from_interactive_quiz({"quiz_title": "X"}, []) is None
    assert (
        build_flashcard_deck_request_from_interactive_quiz(
            {"quiz_title": "X"},
            [{"q": "", "correct": "a", "explanation": ""}],
        )
        is None
    )


def test_generate_interactive_quiz_calls_service_llm_with_prompt(monkeypatch):
    captured = {}

    class _QuizSettings:
        quiz_interactive_question_count = 5

    monkeypatch.setattr("app.config.get_settings", lambda: _QuizSettings())

    class _FakeResp:
        text = json.dumps(_interactive_quiz_payload())

    class _FakeLLM:
        def complete(self, prompt, **kwargs):
            captured["prompt"] = prompt
            captured["kwargs"] = kwargs
            return _FakeResp()

    class _FakeSettings:
        quiz_interactive_question_count = 5

    monkeypatch.setattr("app.quiz_service.get_quiz_llm_for_generation", lambda: _FakeLLM())
    monkeypatch.setattr("app.config.get_settings", lambda: _FakeSettings())
    quiz, err = generate_interactive_quiz(
        topic="retrieval",
        user_level="beginner",
        learned_concepts="chunks",
        recent_history="asked about RAG",
        concept_names="retrieval, chunks",
        learning_mode="exam_prep",
    )
    assert err is None
    assert quiz is not None
    assert quiz["quiz_title"] == "Tutor check"
    assert captured["kwargs"] == {"temperature": 0.2}
    assert "retrieval" in captured["prompt"]
    assert "beginner" in captured["prompt"]
    assert "chunks" in captured["prompt"]
    assert "asked about RAG" in captured["prompt"]
    assert "экзамен" in captured["prompt"].lower()


def test_generate_interactive_quiz_returns_parse_error(monkeypatch):
    class _FakeResp:
        text = "not-json"

    class _FakeLLM:
        def complete(self, prompt, **kwargs):
            return _FakeResp()

    monkeypatch.setattr("app.quiz_service.get_quiz_llm_for_generation", lambda: _FakeLLM())
    quiz, err = generate_interactive_quiz(
        topic="retrieval",
        user_level="beginner",
        learned_concepts="chunks",
        recent_history="asked about RAG",
        concept_names="retrieval, chunks",
        learning_mode=None,
    )
    assert quiz is None
    assert err == "Ответ модели не похож на JSON-объект."


def test_generate_interactive_quiz_accepts_letter_keyed_mc_options(monkeypatch):
    class _QuizSettings:
        quiz_interactive_question_count = 5

    monkeypatch.setattr("app.config.get_settings", lambda: _QuizSettings())

    payload = _interactive_quiz_payload()
    payload["questions"][0]["options"] = {
        "A": "A. correct option",
        "B": "B. distractor one",
        "C": "C. distractor two",
        "D": "D. distractor three",
    }

    class _FakeResp:
        text = json.dumps(payload)

    class _FakeLLM:
        def complete(self, prompt, **kwargs):
            return _FakeResp()

    class _FakeSettings:
        quiz_interactive_question_count = 5

    monkeypatch.setattr("app.quiz_service.get_quiz_llm_for_generation", lambda: _FakeLLM())
    monkeypatch.setattr("app.config.get_settings", lambda: _FakeSettings())
    quiz, err = generate_interactive_quiz(
        topic="retrieval",
        user_level="beginner",
        learned_concepts="chunks",
        recent_history="asked about RAG",
        concept_names="retrieval, chunks",
        learning_mode=None,
    )

    assert err is None
    assert quiz is not None
    assert quiz["questions"][0]["options"] == [
        "correct option",
        "distractor one",
        "distractor two",
        "distractor three",
    ]


def test_generate_self_check_quiz_short_text():
    qs, err = generate_self_check_quiz("short")
    assert qs == []
    assert err is not None


def test_split_tutor_answer_and_quiz_ok():
    raw = f"""Ответ про RAG.

Проверка:
1. Вопрос один?

{TUTOR_INLINE_QUIZ_MARKER}
{{"questions": [{{"type": "short_answer", "question": "Что такое retrieval?", "concept": "RAG", "difficulty": "recall"}}]}}
"""
    full, qs = split_tutor_answer_and_quiz(raw)
    assert TUTOR_INLINE_QUIZ_MARKER in full
    assert len(qs) == 1
    assert qs[0]["question"] == "Что такое retrieval?"
    assert qs[0]["concept"] == "RAG"


def test_split_tutor_answer_and_quiz_no_marker():
    full, qs = split_tutor_answer_and_quiz("Только текст без квиза.")
    assert full == "Только текст без квиза."
    assert qs == []


def test_parse_tutor_rag_response_socratic_and_quiz():
    raw = f"""Текст ответа.

{TUTOR_SOCRATIC_MARKER}
{{"type": "probing", "question": "Почему так?"}}

{TUTOR_INLINE_QUIZ_MARKER}
{{"questions": [{{"type": "short_answer", "question": "Q1", "concept": "c", "difficulty": "recall"}}]}}
"""
    full, soc, qs, teaching = parse_tutor_rag_response(raw)
    assert TUTOR_SOCRATIC_MARKER in full
    assert soc and soc["type"] == "probing"
    assert len(qs) == 1
    assert teaching is None


def test_parse_tutor_rag_response_v2_and_quiz():
    raw = f"""{{"teaching_summary": "Кратко про тему.",
"understanding_state": {{"what_you_understood": "w", "risk_gaps": "r", "what_to_do_now": "n"}},
"socratic_check": "Почему?",
"next_action": "Дальше",
"next_action_reason": "Так полезнее.",
"suggested_ctas": ["Объясни проще"],
"depth_level": "beginner",
"trust_signals": {{"sources_used": 1, "confidence": "medium", "coverage_warning": null}}
}}
{TUTOR_INLINE_QUIZ_MARKER}
{{"questions": [{{"type": "short_answer", "question": "Q1", "concept": "c", "difficulty": "recall"}}]}}
"""
    full, soc, qs, teaching = parse_tutor_rag_response(raw)
    assert "Кратко про тему" in full
    assert TUTOR_INLINE_QUIZ_MARKER not in full
    assert soc and soc["question"] == "Почему?"
    assert len(qs) == 1
    assert teaching and teaching.get("next_action") == "Дальше"


def test_format_tutor_v2_markdown_smoke():
    md = format_tutor_v2_markdown(
        {
            "teaching_summary": "T",
            "understanding_state": {
                "what_you_understood": "a",
                "risk_gaps": "b",
                "what_to_do_now": "c",
            },
            "socratic_check": None,
            "next_action": "n",
            "next_action_reason": "r",
            "suggested_ctas": ["X"],
            "depth_level": "advanced",
            "trust_signals": {"sources_used": 2, "confidence": "high", "coverage_warning": None},
        }
    )
    assert "T" in md and "Надёжность" in md


def test_topic_from_last_user_message_prefers_last_user():
    msgs = [
        Message(role="user", content="Первый вопрос"),
        Message(role="assistant", content="Ответ"),
        Message(role="user", content="Уточнение про chunking"),
    ]
    assert topic_from_last_user_message(msgs) == "Уточнение про chunking"


def test_topic_from_last_user_message_truncation():
    long = "x" * 200
    msgs = [Message(role="user", content=long)]
    out = topic_from_last_user_message(msgs, max_len=20)
    assert out is not None
    assert len(out) <= 20
    assert out.endswith("…")


def test_topic_from_last_user_message_empty():
    assert topic_from_last_user_message([]) is None
    assert topic_from_last_user_message([Message(role="assistant", content="only bot")]) is None


def test_generate_micro_quiz_offline_without_llm():
    q = generate_micro_quiz("тема теста", "intermediate", [], use_llm=False)
    assert q.get("correct_option") == "B"
    assert "options" in q and len(q["options"]) == 4
    assert "тема теста" in (q.get("question") or "")


def test_process_micro_quiz_outcome_smoke():
    qd = {
        "question": "Q",
        "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
        "correct_option": "B",
        "type": "recognition",
        "difficulty": "medium",
    }
    out = process_micro_quiz_outcome(
        qd,
        "B",
        current_topic="topic_x",
        current_mastery="intermediate",
    )
    assert out["quiz_feedback"].get("status") == "correct"
    assert "next_action" in out["recommended_next"]
    gam = out.get("gamification") or {}
    assert isinstance(out.get("xp"), int) and out["xp"] >= 5
    assert int(gam.get("xp_gained") or 0) == out["xp"]
    assert "retention_line" in out and "XP" in out["retention_line"]
    assert out.get("explanation") == ""


def test_process_micro_quiz_outcome_accepts_correct_index():
    qd = {
        "question": "Q",
        "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
        "correct_index": 1,
        "type": "recognition",
    }
    out = process_micro_quiz_outcome(
        qd,
        "B",
        current_topic="topic_x",
        current_mastery="intermediate",
    )
    assert out["quiz_feedback"].get("status") == "correct"


def test_process_micro_quiz_outcome_rejects_invalid_correct_option():
    qd = {
        "question": "Q",
        "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
        "correct_option": "X",
        "type": "recognition",
    }
    with pytest.raises(InvalidMicroQuizQuestionError):
        process_micro_quiz_outcome(
            qd,
            "A",
            current_topic="topic_x",
            current_mastery="intermediate",
        )


def test_normalize_quiz_question_maps_float_index():
    q = normalize_quiz_question_for_evaluation({"correct_index": 2.0})
    assert q["correct_option"] == "C"
