from __future__ import annotations

from pathlib import Path

import pytest

from app import smart_konspekt as sk


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeSettings:
    obsidian_export_materials_dir = "materials"
    obsidian_export_prompt_path = "doc/prompts/smart_lecture_konspekt_universal.md"
    obsidian_export_map_chunk_chars = 80
    obsidian_export_map_overlap_chars = 0
    obsidian_export_compose_input_limit = 120
    obsidian_export_compose_max_tokens = 4096
    smart_konspekt_transcript_budget = 120
    smart_konspekt_draft_budget = 80
    smart_konspekt_html_budget = 60
    smart_konspekt_pdf_budget = 40


@pytest.fixture
def konspekt_env(tmp_path, monkeypatch):
    root = tmp_path
    data_dir = root / "data"
    materials = root / "materials" / "Course" / "Lesson 1"
    materials.mkdir(parents=True)
    data_dir.mkdir()

    monkeypatch.setattr(sk, "BASE_DIR", root)
    monkeypatch.setattr(sk, "DATA_DIR", data_dir)
    monkeypatch.setattr(sk, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(sk, "get_obsidian_export_llm", lambda: object())
    monkeypatch.setattr(sk, "_load_universal_prompt", lambda: "UNIVERSAL PROMPT")

    calls: list[tuple[str, str, dict]] = []

    def _fake_complete(_llm, prompt, *, stage, **_kw):  # noqa: ANN001
        calls.append((stage, prompt, dict(_kw)))
        if stage == "smart_konspekt.map":
            return _FakeResponse("- mapped thesis")
        if stage == "smart_konspekt.merge":
            return _FakeResponse("### merged\n- thesis")
        return _FakeResponse("# Smart Konspekt\n\n## Terms\n\nГотово.")

    monkeypatch.setattr(sk, "complete_with_resilience", _fake_complete)
    return root, data_dir, materials, calls


def test_gather_lecture_inputs_classifies_by_role(konspekt_env):
    _root, _data_dir, materials, _calls = konspekt_env
    (materials / "a.txt").write_text("short", encoding="utf-8")
    (materials / "b.txt").write_text("long transcript", encoding="utf-8")
    (materials / "draft.md").write_text("# Draft", encoding="utf-8")
    (materials / "note.html").write_text("<h1>HTML</h1>", encoding="utf-8")
    (materials / "slides.pdf").write_bytes(b"%PDF-1.4")

    inputs = sk.gather_lecture_inputs("Course/Lesson 1")

    assert inputs.primary_transcript == materials / "b.txt"
    assert [p.name for p in inputs.drafts] == ["draft.md"]
    assert [p.name for p in inputs.html_notes] == ["note.html"]
    assert [p.name for p in inputs.presentations] == ["slides.pdf"]


def test_extract_text_html_strips_tags(konspekt_env):
    _root, _data_dir, materials, _calls = konspekt_env
    path = materials / "note.html"
    path.write_text("<html><body><h1>Title</h1><p>Hello <b>world</b></p></body></html>", encoding="utf-8")

    text = sk._extract_text(path)

    assert "Title" in text
    assert "Hello" in text
    assert "world" in text
    assert "<h1>" not in text


def test_extract_text_md_flat(konspekt_env):
    _root, _data_dir, materials, _calls = konspekt_env
    path = materials / "draft.md"
    path.write_text("# Draft\n\nBody", encoding="utf-8")

    assert sk._extract_text(path) == "# Draft\n\nBody"


def test_build_compose_context_respects_budgets():
    context = sk._build_compose_context(
        "T" * 20,
        "D" * 20,
        "H" * 20,
        "P" * 20,
        budgets={"transcript": 5, "draft": 6, "html": 7, "pdf": 8},
    )

    assert "TTTTT" in context
    assert "DDDDDD" in context
    assert "HHHHHHH" in context
    assert "PPPPPPPP" in context
    assert "TTTTTT" not in context


def test_universal_prompt_loaded_and_appended(konspekt_env):
    _root, _data_dir, materials, calls = konspekt_env
    (materials / "source.txt").write_text("lecture text " * 20, encoding="utf-8")

    sk.generate_smart_konspekt("Course/Lesson 1", force=True)

    compose_prompt = [prompt for stage, prompt, _kw in calls if stage == "smart_konspekt.compose"][0]
    assert compose_prompt.startswith("UNIVERSAL PROMPT")
    assert "# ВХОДНЫЕ МАТЕРИАЛЫ" in compose_prompt
    assert "mapped thesis" in compose_prompt


def test_generate_writes_konspekt_to_data(konspekt_env):
    _root, data_dir, materials, _calls = konspekt_env
    (materials / "source.txt").write_text("lecture text " * 20, encoding="utf-8")

    result = sk.generate_smart_konspekt("Course/Lesson 1", force=True)

    assert result.action == "generated"
    assert result.target_abs == (data_dir / "Course" / "Lesson 1.md").resolve()
    body = result.target_abs.read_text(encoding="utf-8")
    assert "type: konspekt" in body
    assert "# Smart Konspekt" in body


def test_partial_resume_skips_map_reduce(konspekt_env):
    _root, _data_dir, materials, calls = konspekt_env
    (materials / "source.txt").write_text("lecture text " * 20, encoding="utf-8")
    inputs = sk.gather_lecture_inputs("Course/Lesson 1")
    source_hash = sk._sha256_inputs(inputs)
    target = sk._target_path(inputs)
    sk._save_notes_cache(target, source_hash, "### cached\n- consolidated")

    result = sk.generate_smart_konspekt("Course/Lesson 1", force=True)

    assert result.action == "generated"
    assert result.stats.cache_used is True
    assert [stage for stage, _prompt, _kw in calls] == ["smart_konspekt.compose"]
    assert not sk._notes_cache_path(target).exists()


def test_reduce_notes_passes_explicit_merge_max_tokens(konspekt_env):
    _root, _data_dir, _materials, calls = konspekt_env

    consolidated, reduce_calls = sk._reduce_notes(
        object(),
        ["note A" * 50, "note B" * 50],
        None,
        compose_limit=100,
        max_tokens=8192,
    )

    assert reduce_calls >= 1
    assert "merged" in consolidated
    merge_kwargs = [kw for stage, _prompt, kw in calls if stage == "smart_konspekt.merge"]
    assert merge_kwargs
    assert all(kw["max_tokens"] == 8192 for kw in merge_kwargs)


def test_reduce_notes_stops_when_merge_does_not_shrink(monkeypatch):
    """Regression: oversized per-note merge outputs must not loop forever."""
    call_count = 0
    MAX_ALLOWED_CALLS = 50  # tripwire: any real infinite loop hits this long before pytest timeout

    def _oversized_merge(_llm, _prompt, *, stage, **_kw):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        assert call_count <= MAX_ALLOWED_CALLS, (
            f"_reduce_notes called LLM {call_count} times — infinite loop regression"
        )
        if stage == "smart_konspekt.merge":
            return _FakeResponse("x" * 15000)
        return _FakeResponse("")

    monkeypatch.setattr(sk, "complete_with_resilience", _oversized_merge)

    consolidated, reduce_calls = sk._reduce_notes(
        object(),
        ["a" * 15000, "b" * 15000],
        None,
        compose_limit=12000,
        max_tokens=8192,
    )

    assert reduce_calls == 0
    assert len(consolidated) == 12000
