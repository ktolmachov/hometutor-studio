from app.ui.adaptive_plan_card import (
    block_badge_label,
    build_plan_progress_summary,
    build_plan_step_reason,
    get_primary_plan_block,
    get_primary_plan_block_from_plan,
    _normalize_plan_concepts_delta,
    tutor_prompt_for_block,
)


def test_get_primary_plan_block_skips_auto_loop_when_possible():
    blocks = [
        {"type": "auto_loop", "description": "background loop"},
        {"type": "review", "concept": "RAG basics"},
        {"type": "new", "concept": "Chunking"},
    ]

    idx, block = get_primary_plan_block(blocks) or (-1, {})

    assert idx == 1
    assert block["type"] == "review"


def test_get_primary_plan_block_falls_back_to_auto_loop_only_plan():
    idx, block = get_primary_plan_block([{"type": "auto_loop", "description": "only"}]) or (-1, {})

    assert idx == 0
    assert block["type"] == "auto_loop"


def test_get_primary_plan_block_from_plan_prefers_explicit_contract():
    plan = {
        "primary_block": {
            "type": "gap",
            "concept": "Embeddings",
            "description": "close the gap",
        },
        "blocks": [
            {"type": "auto_loop", "description": "only fallback"},
            {"type": "review", "concept": "RAG basics"},
        ],
    }

    primary = get_primary_plan_block_from_plan(plan)

    assert isinstance(primary, dict)
    assert primary["type"] == "gap"
    assert primary["concept"] == "Embeddings"


def test_build_plan_step_reason_and_prompt_for_gap_block():
    block = {"type": "gap", "concept": "Embeddings"}

    reason = build_plan_step_reason(block)
    prompt = tutor_prompt_for_block(block)

    assert "Embeddings" in reason
    assert "позаниматься" in reason
    assert "Embeddings" in prompt
    assert "пробел" not in reason.lower()


def test_placeholder_gap_block_hides_technical_slug():
    block = {"type": "gap", "concept": "general"}

    assert "general" not in build_plan_step_reason(block).lower()
    assert "general" not in tutor_prompt_for_block(block).lower()

    from app.ui.adaptive_plan_card import _block_concept_line

    line = _block_concept_line(block)
    assert "general" not in line.lower()
    assert "чат" in line.lower()


def test_block_badge_and_progress_summary():
    assert block_badge_label({"type": "review"}) == "REVIEW"
    assert block_badge_label({"type": "motivation"}) == "FOCUS"

    active = build_plan_progress_summary(progress_done=1, total_blocks=4, daily_xp=35)
    done = build_plan_progress_summary(progress_done=4, total_blocks=4, daily_xp=80)
    empty = build_plan_progress_summary(progress_done=0, total_blocks=0, daily_xp=12)

    assert "Сделано 1/4 блоков" in active
    assert "35 XP" in active
    assert "План на сегодня закрыт" in done
    assert "пока нет шагов" in empty


def test_changed_delta_normalization_keeps_only_current_concepts():
    plan = {
        "blocks": [
            {"type": "review", "concept": "RAG basics"},
            {"type": "gap", "concept": "Embeddings"},
        ]
    }
    delta = {
        "added": ["RAG basics", "orphan"],
        "removed": ["legacy topic", "legacy topic"],
    }

    added, removed = _normalize_plan_concepts_delta(plan, delta)

    assert added == ["RAG basics"]
    assert removed == ["legacy topic"]
