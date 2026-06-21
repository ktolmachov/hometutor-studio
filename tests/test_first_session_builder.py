from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services import first_session_builder as fsb


def _fake_retrieve(_query: str, source_paths: list[str], _top_k: int) -> list[dict]:
    path = source_paths[0] if source_paths else "Course/a.md"
    return [{"source_paths": [path], "chunk_ids": ["chunk-1"]}]


def _settings(profile: str):
    return type(
        "S",
        (),
        {
            "home_rag_local_profile": profile,
            "lmstudio_api_base": "http://127.0.0.1:1234/v1",
            "openai_api_base": "http://127.0.0.1:1234/v1",
        },
    )()


def test_balanced_healthy_local_builds_full_artifact(monkeypatch) -> None:
    monkeypatch.setattr(fsb, "get_settings", lambda: _settings("balanced"))
    monkeypatch.setattr(fsb, "is_open", lambda _base: False)
    llm = MagicMock()
    llm.complete.return_value = MagicMock(text="Краткий черновик ответа.")
    monkeypatch.setattr(fsb, "get_llm", lambda: llm)

    artifact = fsb.build_first_session_artifact(
        course_id="ML-Course",
        source_paths=["ML-Course/intro.md", "ML-Course/lec1.md"],
        retrieve_fn=_fake_retrieve,
    )

    assert artifact["baseline_mission"]["title"]
    assert artifact["outline_blocks"]
    assert len(artifact["seed_questions"]) == 3
    assert artifact["seed_questions"][0]["retrieval_trace"]["source_paths"]
    assert artifact["seed_questions"][0]["draft_answer"] == "Краткий черновик ответа."
    llm.complete.assert_called()


def test_local_strict_never_calls_get_llm(monkeypatch) -> None:
    monkeypatch.setattr(fsb, "get_settings", lambda: _settings("local_strict"))
    monkeypatch.setattr(fsb, "is_open", lambda _base: False)
    calls: list[str] = []

    def _boom():
        calls.append("get_llm")
        raise AssertionError("get_llm must not run under local_strict")

    monkeypatch.setattr(fsb, "get_llm", _boom)

    artifact = fsb.build_first_session_artifact(
        course_id="ML-Course",
        source_paths=["ML-Course/intro.md"],
        retrieve_fn=_fake_retrieve,
    )

    assert calls == []
    assert all(seed["draft_answer"] is None for seed in artifact["seed_questions"])


def test_balanced_cb_open_skips_draft(monkeypatch) -> None:
    monkeypatch.setattr(fsb, "get_settings", lambda: _settings("balanced"))
    monkeypatch.setattr(fsb, "is_open", lambda _base: True)
    monkeypatch.setattr(
        fsb,
        "get_llm",
        lambda: (_ for _ in ()).throw(AssertionError("get_llm must not run when CB open")),
    )

    artifact = fsb.build_first_session_artifact(
        course_id="ML-Course",
        source_paths=["ML-Course/intro.md"],
        retrieve_fn=_fake_retrieve,
    )

    assert all(seed["draft_answer"] is None for seed in artifact["seed_questions"])
    assert artifact["seed_questions"][0]["retrieval_trace"]["source_paths"]


def test_per_candidate_failure_others_still_written(tmp_path, monkeypatch) -> None:
    from app import ingestion_support as ing_sup
    from app.course_cache import first_session_artifact_path

    cache_root = tmp_path / "cache" / "real"
    monkeypatch.setattr("app.course_cache.first_session_cache_root", lambda: cache_root)

    docs_root = tmp_path / "docs"
    for name in ("CourseA", "CourseB"):
        folder = docs_root / name
        folder.mkdir(parents=True)
        for idx in range(3):
            (folder / f"{idx}.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(fsb, "get_settings", lambda: _settings("local_strict"))
    monkeypatch.setattr(fsb, "is_open", lambda _base: False)

    original = fsb.build_first_session_artifact

    def _build(*, course_id, **kwargs):
        if course_id == "CourseA":
            raise RuntimeError("boom")
        return original(course_id=course_id, **kwargs)

    monkeypatch.setattr(ing_sup, "build_first_session_artifact", _build)

    ing_sup.run_first_session_precompute_tail(
        docs_root=docs_root,
        retrieve_fn=_fake_retrieve,
        logger=MagicMock(),
    )

    assert not first_session_artifact_path("CourseA", cache_root=cache_root).exists()
    assert first_session_artifact_path("CourseB", cache_root=cache_root).exists()


def test_tail_hook_does_not_raise_on_candidate_failure(tmp_path, monkeypatch) -> None:
    from app import ingestion_support as ing_sup

    docs_root = tmp_path / "docs"
    folder = docs_root / "OnlyCourse"
    folder.mkdir(parents=True)
    for idx in range(3):
        (folder / f"{idx}.md").write_text("x", encoding="utf-8")

    monkeypatch.setattr(ing_sup, "build_first_session_artifact", lambda **_kw: (_ for _ in ()).throw(RuntimeError("fail")))

    ing_sup.run_first_session_precompute_tail(
        docs_root=docs_root,
        retrieve_fn=_fake_retrieve,
        logger=MagicMock(),
    )
