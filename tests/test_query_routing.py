from app.query_routing import KEYWORD_QUERY, QA_QUERY, detect_query_type


def test_detect_query_type_returns_keyword_for_exact_identifier():
    assert detect_query_type("RFC-2024-003") == KEYWORD_QUERY


def test_detect_query_type_returns_keyword_for_short_uppercase_term():
    assert detect_query_type("OWASP") == KEYWORD_QUERY


def test_detect_query_type_returns_keyword_for_short_term_with_digits():
    assert detect_query_type("GPT-4.1") == KEYWORD_QUERY


def test_detect_query_type_returns_qa_for_regular_question():
    assert detect_query_type("What are the main RAG guardrails?") == QA_QUERY


def test_detect_query_type_keeps_question_with_acronym_as_qa():
    assert detect_query_type("What is RAG?") == QA_QUERY


def test_detect_query_type_returns_qa_for_russian_question():
    assert detect_query_type("\u0427\u0442\u043e \u0442\u0430\u043a\u043e\u0435 RAG?") == QA_QUERY


def test_detect_query_type_returns_qa_for_russian_question_without_question_mark():
    assert detect_query_type(
        "\u0427\u0442\u043e \u0442\u0430\u043a\u043e\u0435 OWASP"
    ) == QA_QUERY


def test_detect_query_type_returns_keyword_for_russian_exact_term():
    assert detect_query_type(
        "\u041e\u0432\u0430\u0441\u043f"
    ) == KEYWORD_QUERY


def test_detect_query_type_returns_keyword_for_short_path_like_query():
    assert detect_query_type("doc/adr-010") == KEYWORD_QUERY
