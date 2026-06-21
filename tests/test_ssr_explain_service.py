"""Server-side /ssr/explain streaming contract tests."""

from __future__ import annotations

from types import SimpleNamespace

from app import ssr_explain_service as svc


def test_stream_explanation_uses_low_token_cap(monkeypatch):
    captured: dict[str, int] = {}

    class _Delta:
        def __init__(self, text: str) -> None:
            self.delta = text

    class _StreamLlm:
        api_base = "http://127.0.0.1:8787"

        def stream_chat(self, _messages, **kwargs):
            captured["max_tokens"] = int(kwargs["max_tokens"])
            yield _Delta("Коротко.")

    monkeypatch.setattr(svc, "_cache_get_exact", lambda _key: None)
    monkeypatch.setattr(svc, "_cache_put_exact", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "get_ssr_llm_resolved", lambda: (_StreamLlm(), False))
    monkeypatch.setattr(svc, "ssr_llm_shares_main_api_base", lambda: False)
    monkeypatch.setattr("app.llm_local_circuit.is_open", lambda _base: False)
    monkeypatch.setattr(
        "app.ssr_explanation_tier_gate.decide_explanation_tier",
        lambda *_args, **_kwargs: SimpleNamespace(tier="llm"),
    )

    tokens = list(
        svc.stream_explanation_tokens(
            {},
            hint_kind="cards_due",
            primary_label_ru="Карточки",
            why_now_ru="Пора повторить",
            primary_nav="flashcards_review",
            evidence_ledger=["sm2_due"],
        )
    )

    assert tokens == ["Коротко."]
    assert captured["max_tokens"] == svc.SSR_EXPLANATION_MAX_TOKENS
    assert captured["max_tokens"] <= 120
