"""Tests for scripts/export_slide_assets.py — парсинг слайдов, префиксов и конспекта."""

import pytest

import export_slide_assets as esa


class TestParseSlidesSpec:
    def test_list_and_ranges(self):
        assert esa.parse_slides_spec("3,5-7,19", 65) == [3, 5, 6, 7, 19]

    def test_dedupe_and_sort(self):
        assert esa.parse_slides_spec("7,3,3,5-6,5", 10) == [3, 5, 6, 7]

    def test_single_page(self):
        assert esa.parse_slides_spec("1", 1) == [1]

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match="вне диапазона"):
            esa.parse_slides_spec("99", 65)
        with pytest.raises(ValueError, match="вне диапазона"):
            esa.parse_slides_spec("0", 65)

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError, match="задом наперед"):
            esa.parse_slides_spec("7-5", 65)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="пуст"):
            esa.parse_slides_spec(" , ", 65)


class TestSanitizePrefix:
    def test_spaces_to_underscores(self):
        assert esa.sanitize_prefix("урок 4") == "урок_4"

    def test_strips_invalid_filename_chars(self):
        assert esa.sanitize_prefix('урок<4>: "прод"?') == "урок4_прод"

    def test_strips_edge_dots_and_underscores(self):
        assert esa.sanitize_prefix(" .урок_4_. ") == "урок_4"

    def test_empty_result_raises(self):
        with pytest.raises(ValueError, match="префикс"):
            esa.sanitize_prefix("???")


class TestParseKonspektSlides:
    KONSPEKT = """\
## 🖼 Визуальная выжимка: слайды, которые нужно помнить

### Слайд 3: 200 OK != OK

![Слайд 3](assets/урок_4_slide_03.png)

**Главный вывод:** технический успех не равен смысловому.

### Слайд 12 (стр. 12–14): online-гейты

> **Визуальный brief:** таблица гейтов.

## 📌 Ключевые темы

Формула со слайда: ![Бюджет](assets/урок_4_slide_26.png)
"""

    def test_collects_headings_and_links(self):
        pages, prefixes = esa.parse_konspekt_slides(self.KONSPEKT)
        assert pages == [3, 12, 26]
        assert prefixes == {"урок_4"}

    def test_no_slides_raises(self):
        with pytest.raises(ValueError, match="--slides"):
            esa.parse_konspekt_slides("# Конспект без визуальной выжимки")

    def test_heading_without_link_counts(self):
        pages, prefixes = esa.parse_konspekt_slides("### Слайд 7: три контура")
        assert pages == [7]
        assert prefixes == set()

    def test_heading_with_plural_range(self):
        pages, _ = esa.parse_konspekt_slides("### Слайды 8–12: LLM и ограничения")
        assert pages == [8, 9, 10, 11, 12]

    def test_heading_with_build_pages_takes_leading_number(self):
        pages, _ = esa.parse_konspekt_slides("### Слайд 12 (стр. 12–14): online-гейты")
        assert pages == [12]

    def test_heading_with_dash_before_title_not_a_range(self):
        pages, _ = esa.parse_konspekt_slides("### Слайд 7 — Три контура отказа")
        assert pages == [7]
