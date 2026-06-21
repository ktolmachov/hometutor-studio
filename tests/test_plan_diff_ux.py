from app.ui.adaptive_plan_card import _normalize_plan_concepts_delta


def test_normalize_plan_concepts_delta_filters_non_current_and_duplicates():
    plan = {
        "blocks": [
            {"type": "review", "concept": "vectors"},
            {"type": "gap", "concept": "graphs"},
            {"type": "review", "concept": "vectors"},
        ]
    }
    delta = {
        "added": ["vectors", "vectors", "missing", "  "],
        "removed": ["bm25", "bm25", ""],
    }

    added, removed = _normalize_plan_concepts_delta(plan, delta)

    assert added == ["vectors"]
    assert removed == ["bm25"]


def test_normalize_plan_concepts_delta_empty_inputs():
    added, removed = _normalize_plan_concepts_delta({"blocks": []}, {"added": [], "removed": []})
    assert added == []
    assert removed == []
