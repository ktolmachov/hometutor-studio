"""Текстовые хелперы debug UI без Streamlit."""
from app.ui.debug_panel import (
    graph_expansion_chip_labels_for_ui,
    graph_expansion_provenance_lines_for_ui,
    graph_expansion_rows_for_ui,
    graph_expansion_trust_caption_ru,
)
from app.ui.helpers import retrieval_route_demotion_badge


def test_graph_expansion_rows_skipped():
    rows = graph_expansion_rows_for_ui(
        {"graph_expansion_ms": 2.5, "skipped": True, "reason": "query_type"}
    )
    assert any("пропуск" in v for _, v in rows)
    assert any("тип запроса" in v for _, v in rows)


def test_graph_expansion_rows_applied():
    rows = graph_expansion_rows_for_ui(
        {
            "ok": True,
            "graph_expansion_ms": 40.0,
            "extra_chunk_count": 3,
            "concepts_touched": 5,
            "hops_applied": 2,
            "max_hops": 3,
        }
    )
    d = dict(rows)
    assert d["Доп. чанков"] == "3"
    assert d["Концептов"] == "5"
    assert d["Волн обхода"] == "2"
    assert d["Лимит волн"] == "3"


def test_graph_expansion_rows_error():
    rows = graph_expansion_rows_for_ui({"ok": False, "graph_expansion_ms": 1.0, "error": "kg down"})
    assert any("ошибка" in v for _, v in rows)
    assert any("kg down" in v for _, v in rows)


def test_graph_expansion_rows_empty():
    assert graph_expansion_rows_for_ui(None) == []
    assert graph_expansion_rows_for_ui({}) == []


def test_graph_expansion_provenance_lines_and_chips():
    ge = {
        "seed_doc_ids": ["d1.md"],
        "added_doc_ids": ["d2.md"],
        "concept_route_sample": [
            {"concept_id": "T1", "hop": 0, "relation": "seed", "via_concept": None},
            {"concept_id": "T2", "hop": 1, "relation": "related", "via_concept": "T1"},
        ],
        "added_doc_reason_sample": [
            {
                "doc_id": "d2.md",
                "reasons": [
                    {"concept_id": "T2", "hop": 1, "relation": "related", "via_concept": "T1"},
                ],
            }
        ],
    }
    chips = graph_expansion_chip_labels_for_ui(ge)
    assert "seed: d1.md" in chips
    assert "+doc: d2.md" in chips
    lines = graph_expansion_provenance_lines_for_ui(ge)
    assert any("Концепт `T1` взят как seed" in line for line in lines)
    assert any("Документ `d2.md` добавлен через `T2`" in line for line in lines)


def test_graph_expansion_trust_caption_suppressed_when_effective_graph_false():
    dbg = {
        "retrieval_routing": {"effective_graph_augmented": False},
        "pipeline_trace": {
            "graph_expansion": {"ok": True, "extra_chunk_count": 3},
        },
    }
    assert graph_expansion_trust_caption_ru(dbg) is None


def test_retrieval_route_demotion_badge_for_uplift_gate_blocked():
    badge = retrieval_route_demotion_badge(
        {
            "retrieval_routing": {
                "selected_profile": "graph_aware",
                "effective_profile": "quality",
                "fallback_reason": "uplift_gate_blocked",
            }
        }
    )
    assert badge == "демotion: gate качества"
