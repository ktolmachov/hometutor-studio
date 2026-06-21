from app.ui.source_cards import _route_label_ru, _score_trust_caption


def test_route_label_ru_known_modes():
    assert "вектор" in _route_label_ru("vector_only")
    assert "гибрид" in _route_label_ru("hybrid")
    assert "FAQ" in _route_label_ru("faq_cache")


def test_score_trust_caption_buckets():
    assert "высокая" in _score_trust_caption(0.9)
    assert "умеренная" in _score_trust_caption(0.5)
    assert "низкий" in _score_trust_caption(0.1)
    assert "не передана" in _score_trust_caption(None)
