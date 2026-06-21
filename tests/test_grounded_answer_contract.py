import json

import pytest

import app.guardrails as guardrails
from app.config import get_settings
from app.grounded_answer import (
    AbstainResponse,
    GroundedAnswerSchema,
    apply_grounded_validation,
    build_provenance_ledger,
    evaluate_abstain_rate_gate,
    load_abstain_rate_baseline_summary,
    validate_and_normalize,
)
from app.guardrails import get_safe_fallback_message


def _sample_sources(*, graph_evidence: list | None = None) -> list[dict]:
    source = {
        "cite_index": 1,
        "relative_path": "data/test.txt",
        "text": "snippet",
        "score": 0.9,
    }
    if graph_evidence is not None:
        source["graph_evidence"] = graph_evidence
    return [source]


def test_is_abstain_phrase_matches_guardrails_fallback_phrases(monkeypatch):
    monkeypatch.setattr(
        guardrails,
        "get_settings",
        lambda: type(
            "S",
            (),
            {"guardrails_require_sources": True},
        )(),
    )
    phrase = get_safe_fallback_message("missing_sources")
    assert guardrails.is_abstain_phrase(phrase) is True
    assert guardrails._looks_like_safe_fallback_message(phrase) is True


def test_abstain_phrase_maps_to_abstain_response():
    phrase = "Недостаточно данных для ответа."
    result = validate_and_normalize(phrase, [], strict=True)
    assert result.answer_status == "abstain"
    assert isinstance(result.schema, AbstainResponse)
    assert result.schema.reason_code == "model_abstain"


def test_valid_inline_citation_is_grounded():
    answer = "Retrieval объединяет поиск и генерацию [1]."
    result = validate_and_normalize(answer, _sample_sources(), strict=True)
    assert result.answer_status == "grounded"
    assert isinstance(result.schema, GroundedAnswerSchema)
    assert result.schema.facts[0].provenance[0].cite_index == 1


def test_sources_footer_is_not_treated_as_uncited_fact():
    answer = "Retrieval объединяет поиск и генерацию [1].\n\nИсточники: [data/test.txt]"
    result = validate_and_normalize(answer, _sample_sources(), strict=True)

    assert result.answer_status == "grounded"
    assert isinstance(result.schema, GroundedAnswerSchema)
    assert len(result.schema.facts) == 1


def test_sources_footer_in_long_paragraph_is_ignored():
    answer = (
        "Retrieval объединяет поиск и генерацию в одном конвейере, где сначала находят релевантные "
        "фрагменты, а затем модель формирует ответ на их основе с опорой на найденный контекст [1]. "
        "Источники: [data/test.txt]"
    )
    result = validate_and_normalize(answer, _sample_sources(), strict=True)

    assert result.answer_status == "grounded"
    assert len(result.schema.facts) == 1
    assert "missing_provenance" not in result.debug["validation_errors"]


def test_invalid_cite_index_coerces_abstain_in_strict_mode():
    answer = "Факт без источника [9]."
    result = validate_and_normalize(answer, _sample_sources(), strict=True)
    assert result.answer_status == "abstain"
    assert result.debug["abstain_reason_code"] == "insufficient_provenance"
    assert "invalid_cite_index:9" in result.debug["validation_errors"]


def test_out_of_range_cite_on_one_block_still_grounded_when_other_blocks_valid():
    sources = [
        {"cite_index": 1, "relative_path": "data/a.md", "text": "a", "score": 0.9},
        {"cite_index": 2, "relative_path": "data/b.md", "text": "b", "score": 0.8},
    ]
    answer = (
        "Первый факт по контексту [1]. "
        "Второй факт по контексту [2]. "
        "Третий факт с неверной ссылкой [3]."
    )
    result = validate_and_normalize(answer, sources, strict=True)
    assert result.answer_status == "grounded"
    assert result.debug["schema_validated"] is True
    assert "invalid_cite_index:3" in result.debug["validation_errors"]
    assert len(result.schema.facts) >= 1
    assert all(fact.provenance for fact in result.schema.facts)


def test_out_of_range_cite_in_long_answer_drops_sentence_rest_grounded():
    """Sentence-split path (>240 chars): [3] out-of-range sentence dropped, rest grounded."""
    sources = [
        {"cite_index": 1, "relative_path": "data/a.md", "text": "a", "score": 0.9},
        {"cite_index": 2, "relative_path": "data/b.md", "text": "b", "score": 0.8},
    ]
    answer = (
        "Агентный RAG объединяет извлечение и генерацию, причём агент сам решает, "
        "какие источники запросить и в каком порядке, опираясь на найденный контекст [1]. "
        "Затем модель формирует ответ строго по найденным фрагментам, не добавляя внешних фактов [2]. "
        "Дополнительный механизм рефлексии повышает качество ответа по итогам нескольких итераций [3]. "
        "Источники: [data/a.md], [data/b.md]"
    )
    assert len(answer) > 240
    result = validate_and_normalize(answer, sources, strict=True)
    assert result.answer_status == "grounded"
    assert result.debug["schema_validated"] is True
    assert "invalid_cite_index:3" in result.debug["validation_errors"]
    assert all(fact.provenance for fact in result.schema.facts)


def test_uncited_sentence_in_long_answer_is_grounded():
    """Sentence-split path (>240 chars): transitional sentence without cite is dropped, rest grounded."""
    sources = [
        {"cite_index": 1, "relative_path": "data/a.md", "text": "a", "score": 0.9},
        {"cite_index": 2, "relative_path": "data/b.md", "text": "b", "score": 0.8},
    ]
    answer = (
        "Агентный RAG объединяет извлечение и генерацию, опираясь на найденный контекст [1]. "
        "Это особенно полезно, когда вопрос требует нескольких источников и шагов рассуждения. "
        "Модель формирует ответ строго по найденным фрагментам [2]. "
        "Источники: [data/a.md], [data/b.md]"
    )
    assert len(answer) > 240
    result = validate_and_normalize(answer, sources, strict=True)
    assert result.answer_status == "grounded"
    assert result.debug["schema_validated"] is True
    assert "missing_provenance" in result.debug["validation_errors"]


def test_all_uncited_blocks_in_long_answer_abstains():
    """If no block has a valid cite, the answer should abstain even with real text."""
    sources = [
        {"cite_index": 1, "relative_path": "data/a.md", "text": "a", "score": 0.9},
    ]
    answer = (
        "Агентный RAG объединяет извлечение и генерацию ответов на основе найденных документов. "
        "Это очень полезный подход, когда нужен точный и обоснованный ответ на вопрос пользователя. "
        "Модель формирует ответ строго по найденным фрагментам, не добавляя внешних фактов."
    )
    assert len(answer) > 240
    result = validate_and_normalize(answer, sources, strict=True)
    assert result.answer_status == "abstain"


def test_zero_fact_body_coerces_abstain():
    result = validate_and_normalize("   ", _sample_sources(), strict=True)
    assert result.answer_status == "abstain"
    assert result.debug["abstain_reason_code"] == "insufficient_provenance"


def test_graph_evidence_provenance_type():
    sources = _sample_sources(graph_evidence=[{"id": "ev-1", "confidence": 0.8}])
    answer = "Graph-augmented fact [1]."
    result = validate_and_normalize(answer, sources, strict=True)
    prov = result.schema.facts[0].provenance[0]
    assert prov.provenance_type == "graph_evidence"
    assert prov.graph_evidence_id == "ev-1"


def test_tutor_soft_mode_keeps_answer_text(monkeypatch):
    monkeypatch.setattr(
        "app.grounded_answer.get_settings",
        lambda: get_settings().model_copy(update={"grounded_answer_strict_tutor": False}),
    )
    result = apply_grounded_validation(
        answer_text="Unverified tutor fact.",
        sources=_sample_sources(),
        query_mode="tutor",
        homework_mode=False,
        assistance_level=None,
        cache_hit=False,
    )
    assert result.answer_status == "abstain"
    assert result.answer_text == "Unverified tutor fact."
    assert result.debug["validation_errors"]


def test_kill_switch_skips_validation(monkeypatch):
    monkeypatch.setattr(
        "app.grounded_answer.get_settings",
        lambda: get_settings().model_copy(update={"grounded_answer_contract_enabled": False}),
    )
    result = apply_grounded_validation(
        answer_text="No citations here.",
        sources=[],
        query_mode="qa",
        homework_mode=False,
        assistance_level=None,
        cache_hit=False,
    )
    assert result.skipped is True
    assert result.answer_status is None


def test_faq_cache_hit_skips_validation(monkeypatch):
    result = apply_grounded_validation(
        answer_text="Cached answer without cites.",
        sources=[],
        query_mode="qa",
        homework_mode=False,
        assistance_level=None,
        cache_hit=True,
    )
    assert result.skipped is True


def test_two_stage_early_path_skips_validation():
    result = apply_grounded_validation(
        answer_text="Extractive выжимка without inline cites.",
        sources=_sample_sources(),
        query_mode="qa",
        homework_mode=False,
        assistance_level=None,
        cache_hit=False,
        answer_path_mode="two_stage_early",
    )
    assert result.skipped is True
    assert result.answer_status is None


def test_pii_answer_skips_validation_for_guardrails():
    result = apply_grounded_validation(
        answer_text="Contact me at test@example.com [1]",
        sources=_sample_sources(),
        query_mode="qa",
        homework_mode=False,
        assistance_level=None,
        cache_hit=False,
    )
    assert result.skipped is True


def test_provenance_ledger_shape_for_grounded_answer():
    schema = GroundedAnswerSchema(
        facts=[
            {
                "text": "Fact A [1]",
                "provenance": [{"cite_index": 1, "relative_path": "data/a.md", "provenance_type": "source"}],
            }
        ]
    )
    ledger = build_provenance_ledger(schema)
    assert ledger == [
        {
            "fact_text": "Fact A [1]",
            "cite_index": 1,
            "relative_path": "data/a.md",
            "provenance_type": "source",
        }
    ]


def test_provenance_ledger_abstain_exports_reason_only():
    abstain = AbstainResponse(abstain=True, reason_code="insufficient_provenance", message="n/a")
    ledger = build_provenance_ledger(abstain, retrieval_confidence={"level": "low"})
    assert ledger["abstain"] is True
    assert ledger["reason_code"] == "insufficient_provenance"
    assert ledger["retrieval_confidence"] == {"level": "low"}


def test_weak_context_disclaimer_is_not_counted_as_fact(settings_env):
    settings_env({"RETRIEVAL_WEAK_CONTEXT_DISCLAIMER": "Weak context warning."})
    answer = "Weak context warning.\n\nActual fact [1]."
    result = validate_and_normalize(answer, _sample_sources(), strict=True)
    assert result.answer_status == "grounded"
    assert len(result.schema.facts) == 1
    assert "Weak context" not in result.schema.facts[0].text


def test_homework_relaxed_assistance_allows_missing_provenance():
    answer = "Hint-level explanation without inline cite."
    result = validate_and_normalize(
        answer,
        _sample_sources(),
        strict=True,
        homework_mode=True,
        assistance_level="full_solution",
    )
    assert result.answer_status == "grounded"


def test_abstain_rate_gate_threshold_contract(monkeypatch):
    baseline = {"abstain_rate": 0.12, "baseline_id": "eval-baseline-v1"}
    gate = evaluate_abstain_rate_gate(0.21, baseline, max_delta_pp=10.0)
    assert gate["baseline_id"] == "eval-baseline-v1"
    assert gate["passed"] is True
    assert gate["delta_pp"] == pytest.approx(9.0)

    gate_fail = evaluate_abstain_rate_gate(0.24, baseline, max_delta_pp=10.0)
    assert gate_fail["passed"] is False
    assert gate_fail["delta_pp"] == pytest.approx(12.0)


def test_load_abstain_rate_baseline_summary_reads_settings_path(monkeypatch, tmp_path):
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps({"summary": {"abstain_rate": 0.1, "baseline_id": "fixture"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.grounded_answer.get_settings",
        lambda: get_settings().model_copy(update={"eval_baseline_json": str(baseline_path)}),
    )
    summary = load_abstain_rate_baseline_summary()
    assert summary["baseline_id"] == "fixture"
    assert summary["abstain_rate"] == 0.1


def test_optional_fenced_json_grounded_payload():
    answer = '```json\n{"grounded": true, "facts": [{"text": "JSON fact", "provenance": [{"cite_index": 1, "provenance_type": "source"}]}]}\n```'
    result = validate_and_normalize(answer, _sample_sources(), strict=True)
    assert result.answer_status == "grounded"
    assert result.schema.facts[0].text == "JSON fact"
