from app.prompts import select_prompt_id


def test_select_prompt_id_defaults_to_qa_for_unknown_type():
    assert select_prompt_id("unknown") == "qa"


def test_select_prompt_id_returns_known_query_type():
    assert select_prompt_id("overview") == "overview"


def test_select_prompt_id_forces_keyword_for_bm25_mode():
    assert select_prompt_id("qa", retrieval_mode="bm25_only") == "keyword"
