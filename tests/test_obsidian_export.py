"""Тесты конвертации документов в Obsidian-ready Markdown (app/obsidian_export.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import obsidian_export as oe


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture
def vault_env(tmp_path, monkeypatch):
    """Изолировать корпус/vault во временную папку и замокать локальную LLM."""
    data_dir = tmp_path / "data"
    (data_dir / "ИИ Агенты").mkdir(parents=True)
    monkeypatch.setattr(oe, "DATA_DIR", data_dir)

    calls: list[str] = []

    def _fake_complete(_llm, prompt, *, stage, **_kw):  # noqa: ANN001
        calls.append(stage)
        if stage.startswith("obsidian.export.map"):
            return _FakeResponse("- тезис из фрагмента")
        if stage.startswith("obsidian.export.merge"):
            return _FakeResponse("### Тема\n- сведённый тезис")
        return _FakeResponse("# 📝 Конспект: Тест\n\nГотовый конспект.")

    monkeypatch.setattr(oe, "_get_llm", lambda: object())
    monkeypatch.setattr(oe, "complete_with_resilience", _fake_complete)
    return data_dir, calls


def test_resolve_and_vault_target_mirror_structure(vault_env):
    data_dir, _ = vault_env
    src = data_dir / "ИИ Агенты" / "урок.txt"
    src.write_text("text", encoding="utf-8")

    resolved = oe.resolve_source("ИИ Агенты/урок.txt")
    assert resolved == src.resolve()

    target = oe.vault_target(resolved)
    expected_root = oe.vault_root()
    assert target == (expected_root / "ИИ Агенты" / "урок.md")
    assert oe.vault_rel_str(target) == "ИИ Агенты/урок.md"


def test_txt_converted_via_llm_with_frontmatter(vault_env):
    data_dir, calls = vault_env
    src = data_dir / "ИИ Агенты" / "урок.txt"
    src.write_text("Сырой транскрипт лекции. " * 50, encoding="utf-8")

    result = oe.to_obsidian_markdown("ИИ Агенты/урок.txt")

    assert result.action == "converted"
    assert result.target_abs.exists()
    body = result.target_abs.read_text(encoding="utf-8")
    assert "source_sha256:" in body
    assert "# 📝 Конспект" in body
    assert any(c == "obsidian.export.compose" for c in calls)


def test_cache_skips_unchanged_source(vault_env):
    src = vault_env[0] / "ИИ Агенты" / "урок.txt"
    src.write_text("Транскрипт. " * 30, encoding="utf-8")

    first = oe.to_obsidian_markdown("ИИ Агенты/урок.txt")
    assert first.action == "converted"

    vault_env[1].clear()  # сбросить лог LLM-вызовов
    second = oe.to_obsidian_markdown("ИИ Агенты/урок.txt")
    assert second.action == "cached"
    assert vault_env[1] == []  # повторных LLM-вызовов не было


def test_force_reconverts_even_if_cached(vault_env):
    src = vault_env[0] / "ИИ Агенты" / "урок.txt"
    src.write_text("Транскрипт. " * 30, encoding="utf-8")
    oe.to_obsidian_markdown("ИИ Агенты/урок.txt")

    forced = oe.to_obsidian_markdown("ИИ Агенты/урок.txt", force=True)
    assert forced.action == "converted"


def test_notes_cache_skips_map_reduce_on_retry(vault_env, monkeypatch):
    data_dir, calls = vault_env
    src = data_dir / "ИИ Агенты" / "retry.txt"
    src.write_text("Сырой транскрипт лекции. " * 60, encoding="utf-8")
    monkeypatch.setattr(oe, "_export_settings", lambda: (120, 0, 80, 4096))

    compose_attempts = 0

    def _flaky_complete(_llm, prompt, *, stage, **_kw):  # noqa: ANN001
        nonlocal compose_attempts
        calls.append(stage)
        if stage.startswith("obsidian.export.map"):
            return _FakeResponse("- тезис из фрагмента")
        if stage.startswith("obsidian.export.merge"):
            return _FakeResponse("### Тема\n- сведённый тезис")
        compose_attempts += 1
        if compose_attempts == 1:
            raise TimeoutError("compose timeout")
        return _FakeResponse("# 📝 Конспект: Retry\n\nГотовый конспект.")

    monkeypatch.setattr(oe, "complete_with_resilience", _flaky_complete)

    with pytest.raises(TimeoutError, match="compose timeout"):
        oe.to_obsidian_markdown("ИИ Агенты/retry.txt", force=True)

    target = oe.vault_target(src)
    cache_path = oe._notes_cache_path(target)
    assert cache_path.exists()
    assert "source_sha256:" in cache_path.read_text(encoding="utf-8")
    assert any(c.startswith("obsidian.export.map") for c in calls)
    assert any(c.startswith("obsidian.export.merge") for c in calls)

    calls.clear()
    result = oe.to_obsidian_markdown("ИИ Агенты/retry.txt", force=True)

    assert result.action == "converted"
    assert calls == ["obsidian.export.compose"]
    assert not cache_path.exists()


def test_notes_cache_invalidated_on_source_change(vault_env, monkeypatch):
    data_dir, calls = vault_env
    src = data_dir / "ИИ Агенты" / "changed.txt"
    src.write_text("Первая версия транскрипта. " * 60, encoding="utf-8")
    monkeypatch.setattr(oe, "_export_settings", lambda: (120, 0, 80, 4096))

    target = oe.vault_target(src)
    stale_hash = oe._sha256(src.read_text(encoding="utf-8"))
    oe._save_notes_cache(target, stale_hash, "### Старый кэш\n- старый тезис")

    src.write_text("Вторая версия транскрипта. " * 60, encoding="utf-8")
    result = oe.to_obsidian_markdown("ИИ Агенты/changed.txt", force=True)

    assert result.action == "converted"
    assert any(c.startswith("obsidian.export.map") for c in calls)
    assert any(c.startswith("obsidian.export.merge") for c in calls)
    assert not oe._notes_cache_path(target).exists()


def test_md_source_copied_without_llm(vault_env):
    data_dir, calls = vault_env
    src = data_dir / "ИИ Агенты" / "note.md"
    src.write_text("# Заголовок\n\nУже markdown.", encoding="utf-8")

    result = oe.to_obsidian_markdown("ИИ Агенты/note.md")
    assert result.action == "copied"
    assert calls == []  # markdown не прогоняется через LLM
    body = result.target_abs.read_text(encoding="utf-8")
    assert "source_sha256:" in body


# ---------------------------------------------------------------------------
# Шаг 4/5 Задачи 0: vault_root() = data/, конспект рядом с источником
# ---------------------------------------------------------------------------

def test_vault_root_is_data_dir(vault_env):
    """vault_root() должен указывать на DATA_DIR (= data/)."""
    data_dir, _ = vault_env
    assert oe.vault_root() == data_dir.resolve()


def test_vault_target_places_md_next_to_source(vault_env):
    """vault_target() кладёт .md рядом с .txt внутри data/."""
    data_dir, _ = vault_env
    src = data_dir / "ИИ Агенты" / "урок.txt"
    src.write_text("text", encoding="utf-8")
    target = oe.vault_target(src.resolve())
    assert target == (data_dir / "ИИ Агенты" / "урок.md").resolve()


def test_vault_obsidian_root_finds_dotobsidian_in_data(vault_env):
    """.obsidian/ в data/ признаётся корнем Obsidian-vault."""
    data_dir, _ = vault_env
    (data_dir / ".obsidian").mkdir(exist_ok=True)
    assert oe.vault_obsidian_root() == data_dir.resolve()


def test_vault_rel_str_relative_to_data(vault_env):
    """vault_rel_str() возвращает путь относительно data/ (без ведущего слеша)."""
    data_dir, _ = vault_env
    (data_dir / ".obsidian").mkdir(exist_ok=True)
    target = (data_dir / "ИИ Агенты" / "урок.md").resolve()
    rel = oe.vault_rel_str(target)
    assert rel == "ИИ Агенты/урок.md"


def test_obsidian_uri_vault_name_in_data(vault_env, monkeypatch):
    """obsidian_uri() строит vault=<name>&file=<rel> с именем vault из настроек."""
    data_dir, _ = vault_env
    (data_dir / ".obsidian").mkdir(exist_ok=True)

    class _FakeSettings:
        obsidian_vault_name = "data"

    monkeypatch.setattr(oe, "get_settings", lambda: _FakeSettings())

    target = (data_dir / "ИИ Агенты" / "урок.md").resolve()
    uri = oe.obsidian_uri(target)
    assert uri.startswith("obsidian://open?vault=data&file=")
    assert "урок.md" in uri or "%D1%83%D1%80%D0%BE%D0%BA.md" in uri


def test_local_konspekt_written_to_data_dir(vault_env):
    """to_obsidian_markdown() пишет результат в data/, а не в doc/конспекты/."""
    data_dir, _ = vault_env
    src = data_dir / "ИИ Агенты" / "урок.txt"
    src.write_text("Сырой транскрипт лекции. " * 50, encoding="utf-8")

    result = oe.to_obsidian_markdown("ИИ Агенты/урок.txt")

    assert result.action == "converted"
    assert str(result.target_abs).startswith(str(data_dir))
    assert result.target_abs.resolve() == (data_dir / "ИИ Агенты" / "урок.md").resolve()


def test_local_konspekt_has_konspekt_type_in_frontmatter(vault_env):
    """Сгенерированный конспект содержит type: konspekt для FlatMarkdownReader."""
    data_dir, _ = vault_env
    src = data_dir / "ИИ Агенты" / "урок.txt"
    src.write_text("Сырой транскрипт лекции. " * 50, encoding="utf-8")

    result = oe.to_obsidian_markdown("ИИ Агенты/урок.txt")

    body = result.target_abs.read_text(encoding="utf-8")
    assert "type: konspekt" in body
    assert "tags:" in body


def test_missing_source_raises(vault_env):
    with pytest.raises(FileNotFoundError):
        oe.to_obsidian_markdown("нет/такого.txt")


def test_split_chunks_respects_size():
    text = "Предложение. " * 2000
    chunks = oe._split_chunks(text, size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 600 for c in chunks)


def test_export_settings_reads_config(monkeypatch):
    """Настройки map_chunk/overlap/limit/max_tokens берутся из Settings."""
    from app.config import Settings

    fake = Settings(
        obsidian_export_map_chunk_chars=3000,
        obsidian_export_map_overlap_chars=100,
        obsidian_export_compose_input_limit=8000,
        obsidian_export_compose_max_tokens=16384,
    )
    monkeypatch.setattr(oe, "get_settings", lambda: fake)
    chunk, overlap, limit, max_tokens = oe._export_settings()
    assert chunk == 3000
    assert overlap == 100
    assert limit == 8000
    assert max_tokens == 16384
