"""Tests for scripts/validate_smart_konspekt.py."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import validate_smart_konspekt as vsk  # noqa: E402


def _args(**overrides):
    class Args:
        profile = "cloud"
        expect_source_sha = True
        expect_presentation = True
        expect_presentation_sha = True
        allow_direct_youtube = False
        strict = False

    args = Args()
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_validate_cloud_konspekt_ok(tmp_path: Path) -> None:
    path = tmp_path / "konspekt.md"
    path.write_text(
        """---
source: "lesson"
source_sha256: abc
presentation: "slides.pdf"
presentation_sha256: def
generated: 2026-06-09
type: konspekt
tags: [конспект, lecture, Agentic Loop]
---

# 📝 Конспект: Lesson

## 🔁 Agentic Loop и условия выхода

ReAct uses action and observation.

### Условия успешного выхода

| Условие | Что означает | Пример |
|---|---|---|

### Ограничительные условия выхода

| Условие | Зачем нужно | Что делать |
|---|---|---|

## 🖼 Что важно из презентации

| Слайды | Визуальный материал | Что нужно запомнить | Где использовано |
|---|---|---|---|

**Как читать визуалы:** восстановить схему.

**Мини-проверка по презентации:** нарисовать две схемы.

## 🧑‍🏫 Объяснение внешнего эксперта простыми словами

## 🧯 Проверка точности и неточности

## 🧬 Каркас знаний

## 🎓 Учебные артефакты для повторения

### Flashcards

### Quiz

### Spaced repetition plan

## ✅ Рубрика качества конспекта

## 🌐 Дополнительные материалы для глубокого изучения

#### Русскоязычные материалы

- [Материал](https://habr.com/ru/articles/1/) — проверенный материал.

### Видео

- [Видео](https://example.com/video-course) — проверенная страница с видео.
""",
        encoding="utf-8",
    )

    result = vsk.validate(path, _args())

    assert result.errors == []


def test_validate_cloud_konspekt_catches_regressions(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_text(
        """---
source: "lesson"
generated: 2026-06-09
type: konspekt
tags: [конспект, lecture]
self_eval: 5
---

# 📝 Конспект

ReAct action observation stop condition.

## 🌐 Дополнительные материалы для глубокого изучения

### Видео

- [Bad](https://www.youtube.com/watch?v=abcdefghijk) — direct YouTube.
- [Anthropic](https://www.anthropic.com/research/building-effective-agents) — old URL.
""",
        encoding="utf-8",
    )

    result = vsk.validate(path, _args())

    assert "YAML: self_eval запрещен; оценки должны быть только в рубрике качества." in result.errors
    assert "YAML: ожидался source_sha256, но поле отсутствует." in result.errors
    assert "YAML: ожидалось поле presentation, но оно отсутствует." in result.errors
    assert "YAML: ожидался presentation_sha256, но поле отсутствует." in result.errors
    assert "Agentic Loop: тема есть в тексте, но нет отдельного раздела." in result.errors
    assert "URL: Anthropic Building Effective Agents должен быть /engineering/building-effective-agents." in result.errors
    assert "URL: прямые youtube.com/watch?v= запрещены без явной проверки (--allow-direct-youtube)." in result.errors
