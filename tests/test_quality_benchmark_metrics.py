from quality_benchmark_metrics import aggregate_rates, source_hit_and_rr, word_jaccard


def test_word_jaccard_basic():
    assert word_jaccard("alpha beta gamma", "beta gamma delta") > 0.2


def test_source_hit_and_rr_first_rank():
    srcs = [
        {"file_name": "a.md", "relative_path": "x/a.md"},
        {"file_name": "b.md", "relative_path": "notes/b.md"},
    ]
    ok, rr = source_hit_and_rr(srcs, ["b.md"])
    assert ok and rr == 0.5


def test_aggregate_rates():
    rows = [
        {"source_hit": True, "reciprocal_rank": 1.0, "answer_relevancy": 0.5},
        {"source_hit": False, "reciprocal_rank": 0.0, "answer_relevancy": 0.0},
    ]
    agg = aggregate_rates(rows)
    assert agg["hit_rate"] == 0.5
    assert agg["mean_reciprocal_rank"] == 0.5
    assert agg["answer_relevancy"] == 0.25
