"""
Тесты для документов академической защиты проекта.

Feature: project-defense-materials
Spec: .kiro/specs/project-defense-materials/

Структурные тесты проверяют наличие обязательных элементов в документах.
Property-тест проверяет referential integrity: все ссылки на файлы должны существовать.
"""

import re
from pathlib import Path

import pytest


# ============================================================================
# Структурные тесты для defense_presenter_script.md
# ============================================================================


def test_defense_presenter_script_exists():
    """Проверка существования файла скрипта выступления."""
    script_path = Path("doc/presentations/defense_presenter_script.md")
    assert script_path.exists(), "Файл doc/presentations/defense_presenter_script.md не найден"


def test_defense_presenter_script_has_timecodes():
    """Проверка наличия таймкодов 0:00 и 3:00 (покрытие ровно 3 минут)."""
    script_path = Path("doc/presentations/defense_presenter_script.md")
    content = script_path.read_text(encoding="utf-8")
    
    assert "0:00" in content, "Таймкод 0:00 не найден в скрипте"
    assert "3:00" in content, "Таймкод 3:00 не найден в скрипте"


def test_defense_presenter_script_has_all_sections():
    """Проверка наличия всех 5 обязательных разделов с таймкодами."""
    script_path = Path("doc/presentations/defense_presenter_script.md")
    content = script_path.read_text(encoding="utf-8")
    
    required_sections = [
        "## 0:00",  # Постановка задачи
        "## 0:30",  # Архитектурное решение
        "## 1:15",  # Демонстрация ключевых функций
        "## 2:15",  # Процесс разработки
        "## 2:45",  # Итоги и дальнейшее развитие
    ]
    
    for section in required_sections:
        assert section in content, f"Раздел '{section}' не найден в скрипте"


def test_defense_presenter_script_has_key_phrases():
    """Проверка наличия ≥5 ключевых фраз формата 🎯 **Ключевая фраза."""
    script_path = Path("doc/presentations/defense_presenter_script.md")
    content = script_path.read_text(encoding="utf-8")
    
    # Подсчёт ключевых фраз
    key_phrase_pattern = r"🎯\s+\*\*Ключевая фраза"
    key_phrases = re.findall(key_phrase_pattern, content)
    
    assert len(key_phrases) >= 5, (
        f"Найдено {len(key_phrases)} ключевых фраз, ожидалось ≥5"
    )


def test_defense_presenter_script_has_qa_table():
    """Проверка наличия таблицы страховочных ответов (≥6 строк с |)."""
    script_path = Path("doc/presentations/defense_presenter_script.md")
    content = script_path.read_text(encoding="utf-8")
    
    # Подсчёт строк таблицы (строки с |, не являющиеся разделителями ---)
    lines = content.splitlines()
    table_rows = [
        line for line in lines
        if line.startswith("|") and "---" not in line
    ]
    
    assert len(table_rows) >= 6, (
        f"Найдено {len(table_rows)} строк таблицы, ожидалось ≥6 "
        "(заголовок + 5 строк ответов)"
    )


# ============================================================================
# Структурные тесты для defense_presentation.md
# ============================================================================


def test_defense_presentation_exists():
    """Проверка существования файла презентации."""
    presentation_path = Path("doc/presentations/defense_presentation.md")
    assert presentation_path.exists(), "Файл doc/presentations/defense_presentation.md не найден"


def test_defense_presentation_has_slides():
    """Проверка наличия ≥8 слайдов (заголовки ## Слайд)."""
    presentation_path = Path("doc/presentations/defense_presentation.md")
    content = presentation_path.read_text(encoding="utf-8")
    
    # Подсчёт слайдов
    slide_headings = [
        line for line in content.splitlines()
        if line.startswith("## Слайд")
    ]
    
    assert len(slide_headings) >= 8, (
        f"Найдено {len(slide_headings)} слайдов, ожидалось ≥8"
    )


def test_defense_presentation_has_toc():
    """Проверка наличия раздела Оглавление."""
    presentation_path = Path("doc/presentations/defense_presentation.md")
    content = presentation_path.read_text(encoding="utf-8")
    
    assert "## Оглавление" in content, "Раздел 'Оглавление' не найден в презентации"


def test_defense_presentation_has_metadata():
    """Проверка наличия метаданных 'Академическая защита' в тексте."""
    presentation_path = Path("doc/presentations/defense_presentation.md")
    content = presentation_path.read_text(encoding="utf-8")
    
    assert "Академическая защита" in content, (
        "Метаданные 'Академическая защита' не найдены в презентации"
    )


# ============================================================================
# Property-тест: Referential Integrity
# ============================================================================


@pytest.mark.parametrize("doc_path", [
    "doc/presentations/defense_presenter_script.md",
    "doc/presentations/defense_presentation.md",
])
def test_referential_integrity(doc_path):
    """
    Property 1: Referential Integrity
    
    For any file reference in the defense documents,
    the referenced path must exist in the repository.
    
    Feature: project-defense-materials
    Validates: Requirements 1.10, 4.2, 9.2
    """
    content = Path(doc_path).read_text(encoding="utf-8")
    
    # Извлечь все ссылки вида [text](path) где path не начинается с http
    refs = re.findall(r'\[.*?\]\(([^)]+)\)', content)
    # Фильтровать: только локальные ссылки (не http и не якоря #)
    local_refs = [
        r for r in refs 
        if not r.startswith("http") and not r.startswith("#")
    ]
    
    # Проверить существование каждой локальной ссылки
    for ref in local_refs:
        # Нормализовать путь относительно корня репозитория
        resolved = Path(ref)
        assert resolved.exists(), (
            f"Broken reference in {doc_path}: {ref}\n"
            f"Referenced file does not exist: {resolved.absolute()}"
        )


# ============================================================================
# Дополнительные проверки (опциональные)
# ============================================================================


def test_defense_presenter_script_language_is_russian():
    """Проверка что скрипт написан на русском языке (smoke-тест)."""
    script_path = Path("doc/presentations/defense_presenter_script.md")
    content = script_path.read_text(encoding="utf-8")
    
    # Простая эвристика: наличие русских слов
    russian_words = ["проект", "задача", "архитектура", "функции", "развитие"]
    found_russian = sum(1 for word in russian_words if word in content.lower())
    
    assert found_russian >= 3, (
        "Скрипт должен быть написан на русском языке "
        f"(найдено {found_russian}/5 ключевых русских слов)"
    )


def test_defense_presentation_language_is_russian():
    """Проверка что презентация написана на русском языке (smoke-тест)."""
    presentation_path = Path("doc/presentations/defense_presentation.md")
    content = presentation_path.read_text(encoding="utf-8")
    
    # Простая эвристика: наличие русских слов
    russian_words = ["продукт", "архитектура", "скриншоты", "процесс", "документы"]
    found_russian = sum(1 for word in russian_words if word in content.lower())
    
    assert found_russian >= 3, (
        "Презентация должна быть написана на русском языке "
        f"(найдено {found_russian}/5 ключевых русских слов)"
    )
