# Defense Presentation Changelog

## [2.0.0] - 2026-05-06

### 🎯 Главные улучшения

#### ✅ Правильные шрифты
- **Было:** Type3 (растровые) шрифты
- **Стало:** Type0 (TrueType/OpenType) шрифты
- **Эффект:** Векторный текст, идеальный для импорта в презентационные инструменты

#### ✅ Диаграммы вместо текста
- **Было:** Mermaid-код отображался как plain text
- **Стало:** Векторные диаграммы, нарисованные matplotlib
  - Архитектурная диаграмма (4 слоя)
  - RAG pipeline диаграмма (5 шагов)

#### ✅ Оптимизация размера
- **Было:** 18.17 MB
- **Стало:** 2.47 MB
- **Улучшение:** 86% уменьшение

#### ✅ Качество рендеринга
- DPI: 150 для всех слайдов
- Формат: 16:9 (13.33" × 7.5")
- Страниц: 14 (добавлен RAG pipeline слайд)

### Added
- `scripts/build_defense_visual_deck.py` - улучшенный генератор с matplotlib
- `scripts/check_pdf_quality.py` - анализатор качества PDF
- `doc/defense_presentation_improvements.md` - полная документация улучшений
- Функция `draw_architecture_diagram()` - векторная архитектурная диаграмма
- Функция `draw_rag_pipeline()` - векторная диаграмма RAG pipeline
- Fallback для шрифтов (кросс-платформенность)

### Changed
- Все шрифты теперь Type0 (TrueType) вместо Type3
- DPI увеличен до 150 для лучшего качества
- Автоматический перенос длинных подзаголовков
- Улучшенный line spacing (1.3 для субтитров, 1.22 для bullets)

### Fixed
- Mermaid-диаграммы теперь отображаются как изображения
- Нет overflow содержимого за границы слайдов
- Правильное встраивание шрифтов в PDF
- Эмодзи заменяются на текст (функция `clean()`)

### Technical Details
```
Format:        PDF 1.4
Pages:         14
Size:          2.47 MB
Aspect Ratio:  16:9 (1.78:1)
Fonts:         Type0 (TrueType)
  - ArialMT
  - Arial-BoldMT
  - Consolas
DPI:           150
Creator:       Matplotlib v3.10.9
```

### Commands
```bash
# Генерация презентации
npm run docs:defense-pdf:visual

# Проверка качества
.\.venv\Scripts\python.exe scripts/check_pdf_quality.py doc/defense_presentation.pdf
```

---

## [1.0.0] - 2026-05-06

### Initial Release
- Первая версия презентации
- Markdown → PDF через puppeteer
- Базовая верстка слайдов
- 13 страниц
- Размер: ~18 MB

---

**Формат:** [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
**Версионирование:** [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
