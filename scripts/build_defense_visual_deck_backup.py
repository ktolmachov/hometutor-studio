"""Build a visual-first defense presentation PDF.

The Markdown deck is excellent as a detailed source, but imported presentation
tools usually benefit from a cleaner slide PDF: fewer words, larger images, and
real TrueType text. This builder creates that PDF with matplotlib.

Key improvements:
- Mermaid diagrams rendered as images (not text)
- Better font rendering with TrueType fonts
- Proper slide sizing and content alignment
- No overflow or clipping
"""

from __future__ import annotations

import argparse
import os
import textwrap
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib-cache").resolve()))

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42  # TrueType fonts
matplotlib.rcParams["ps.fonttype"] = 42   # TrueType fonts for PS
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc"
ASSETS = DOC / "screenshots"
PDF_ASSETS = ASSETS / "defense_pdf"

# 16:9 aspect ratio for presentation
W, H = 13.333, 7.5

# Color palette - professional and accessible
GREEN = "#2f8f67"
DARK = "#12362b"
TEXT = "#18241f"
MUTED = "#56645e"
SOFT = "#eef7f2"
LINE = "#c9ded3"
INK = "#0f172a"
ACCENT = "#1e7a5f"


def font(name: str, size: float, fallback_family: str = "sans-serif") -> FontProperties:
    """Get font with fallback support for cross-platform compatibility."""
    windows_path = Path("C:/Windows/Fonts") / name
    if windows_path.exists():
        return FontProperties(fname=str(windows_path), size=size)
    # Fallback to system fonts
    return FontProperties(family=fallback_family, size=size, weight="normal")


def bold_font(name: str, size: float) -> FontProperties:
    """Get bold font with fallback."""
    windows_path = Path("C:/Windows/Fonts") / name
    if windows_path.exists():
        return FontProperties(fname=str(windows_path), size=size)
    return FontProperties(family="sans-serif", size=size, weight="bold")


def mono_font(name: str, size: float) -> FontProperties:
    """Get monospace font with fallback."""
    windows_path = Path("C:/Windows/Fonts") / name
    if windows_path.exists():
        return FontProperties(fname=str(windows_path), size=size)
    return FontProperties(family="monospace", size=size)


FONT = font("arial.ttf", 18)
BOLD = bold_font("arialbd.ttf", 18)
MONO = mono_font("consola.ttf", 15)


def clean(text: str) -> str:
    replacements = {
        "→": "->",
        "↔": "<->",
        "✅": "Да",
        "❌": "Нет",
        "⚠": "Важно:",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def fig() -> tuple[plt.Figure, plt.Axes]:
    figure = plt.figure(figsize=(W, H), dpi=150, facecolor="white")
    axis = figure.add_axes((0, 0, 1, 1))
    axis.set_axis_off()
    return figure, axis


def title(ax: plt.Axes, text: str, subtitle: str | None = None) -> None:
    """Add title and optional subtitle to slide."""
    # Title
    ax.text(
        0.055, 0.90,  # Adjusted Y position
        clean(text), 
        ha="left", va="top", 
        color=DARK, 
        fontproperties=bold_font("arialbd.ttf", 26),  # Slightly smaller
        wrap=True
    )
    # Separator line
    ax.plot([0.055, 0.945], [0.835, 0.835], color=GREEN, lw=2.5, solid_capstyle="round")
    
    if subtitle:
        # Wrap subtitle if too long
        wrapped_subtitle = "\n".join(textwrap.wrap(clean(subtitle), width=100))
        ax.text(
            0.055, 0.80,  # Adjusted Y position
            wrapped_subtitle, 
            ha="left", va="top", 
            color=MUTED, 
            fontproperties=font("arial.ttf", 12.5),  # Slightly smaller
            linespacing=1.25
        )


def footer(ax: plt.Axes, label: str = "home-rag_v2 · local-first AI tutor") -> None:
    ax.plot([0.055, 0.945], [0.055, 0.055], color=LINE, lw=1.2)
    ax.text(0.945, 0.032, label, ha="right", va="bottom", color=MUTED, fontproperties=font("arial.ttf", 8.5))


def image(ax: plt.Axes, path: Path, box: tuple[float, float, float, float], border: bool = True) -> None:
    img = Image.open(path).convert("RGB")
    left, bottom, width, height = box
    img_ratio = img.width / img.height
    box_ratio = width / height
    if img_ratio > box_ratio:
        render_w = width
        render_h = width / img_ratio
        x = left
        y = bottom + (height - render_h) / 2
    else:
        render_h = height
        render_w = height * img_ratio
        x = left + (width - render_w) / 2
        y = bottom
    img_ax = ax.figure.add_axes((x, y, render_w, render_h))
    img_ax.imshow(img)
    img_ax.set_axis_off()
    if border:
        rect = plt.Rectangle((x, y), render_w, render_h, transform=ax.figure.transFigure, fill=False, lw=1.0, ec=LINE)
        ax.figure.patches.append(rect)


def bullets(ax: plt.Axes, items: list[str], x: float, y: float, width: int = 42, size: float = 15.5, gap: float = 0.075) -> None:
    current = y
    for item in items:
        wrapped = textwrap.wrap(clean(item), width=width)
        ax.text(x, current, "•", ha="left", va="top", color=GREEN, fontproperties=font("arialbd.ttf", size + 2))
        ax.text(x + 0.028, current, "\n".join(wrapped), ha="left", va="top", color=TEXT, fontproperties=font("arial.ttf", size), linespacing=1.22)
        current -= gap * max(1, len(wrapped))


def pill(ax: plt.Axes, x: float, y: float, text: str) -> None:
    ax.text(
        x,
        y,
        clean(text),
        ha="left",
        va="center",
        color=DARK,
        fontproperties=font("arialbd.ttf", 11),
        bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.18", fc=SOFT, ec=LINE, lw=1),
    )


def code(ax: plt.Axes, lines: list[str], box: tuple[float, float, float, float]) -> None:
    x, y, w, h = box
    rect = plt.Rectangle((x, y), w, h, transform=ax.transAxes, fc=INK, ec=INK, lw=0)
    ax.add_patch(rect)
    ax.text(x + 0.025, y + h - 0.045, "\n".join(lines), ha="left", va="top", color="#d7f5e4", fontproperties=MONO, linespacing=1.35)


def cover(pdf: PdfPages) -> None:
    f, ax = fig()
    ax.text(0.055, 0.89, "home-rag", ha="left", va="top", color=GREEN, fontproperties=bold_font("arialbd.ttf", 45))
    ax.text(0.31, 0.89, ": персональный AI-тьютор", ha="left", va="top", color="#050505", fontproperties=bold_font("arialbd.ttf", 39))
    ax.text(
        0.058,
        0.765,
        "Локальная система, которая превращает ваши PDF, DOCX и Markdown в обучение:\nответы с источниками -> тьютор -> quiz -> flashcards -> план повторения.",
        ha="left",
        va="top",
        color=TEXT,
        fontproperties=font("arial.ttf", 17),
        linespacing=1.28,
    )
    image(ax, PDF_ASSETS / "pdf_slide_01.png", (0.47, 0.17, 0.46, 0.48), border=False)
    pill(ax, 0.058, 0.23, "Без облака и подписок")
    pill(ax, 0.245, 0.23, "Полный цикл обучения")
    pill(ax, 0.455, 0.23, "Старт за 5 минут")
    footer(ax, "Академическая защита · май 2026")
    pdf.savefig(f, dpi=150)
    plt.close(f)


def slide_image_left(pdf: PdfPages, heading: str, sub: str, img: str, points: list[str]) -> None:
    f, ax = fig()
    title(ax, heading, sub)
    image(ax, PDF_ASSETS / img, (0.055, 0.14, 0.48, 0.58))  # Adjusted positions
    bullets(ax, points, 0.58, 0.70, width=36, size=15.5, gap=0.09)  # Adjusted
    footer(ax)
    pdf.savefig(f, dpi=150)
    plt.close(f)


def slide_image_right(pdf: PdfPages, heading: str, sub: str, img: str, points: list[str]) -> None:
    f, ax = fig()
    title(ax, heading, sub)
    bullets(ax, points, 0.065, 0.70, width=40, size=15.5, gap=0.088)  # Adjusted
    image(ax, PDF_ASSETS / img, (0.50, 0.13, 0.445, 0.59))  # Adjusted
    footer(ax)
    pdf.savefig(f, dpi=150)
    plt.close(f)


def slide_full_image(pdf: PdfPages, heading: str, sub: str, img_path: Path, points: list[str] | None = None) -> None:
    f, ax = fig()
    title(ax, heading, sub)
    image(ax, img_path, (0.06, 0.13, 0.88, 0.60))  # Adjusted
    if points:
        bullets(ax, points, 0.065, 0.18, width=58, size=12.5, gap=0.058)
    footer(ax)
    pdf.savefig(f, dpi=150)
    plt.close(f)


def draw_architecture_diagram(ax: plt.Axes, box: tuple[float, float, float, float]) -> None:
    """Draw architecture diagram using matplotlib."""
    x, y, w, h = box
    
    # Layer positions
    layer_height = h / 4.5
    gap = 0.015
    
    # Colors for layers
    ui_color = "#e3f2fd"
    api_color = "#fff3e0"
    service_color = "#f3e5f5"
    persist_color = "#e8f5e9"
    
    # Layer 4: UI Layer
    y4 = y + h - layer_height
    rect = plt.Rectangle((x, y4), w, layer_height - gap, fc=ui_color, ec=LINE, lw=1.5)
    ax.add_patch(rect)
    ax.text(x + w/2, y4 + layer_height/2, "Интерфейсный слой\nStreamlit UI · CLI · Telegram Bot", 
            ha="center", va="center", fontproperties=font("arial.ttf", 11), color=TEXT)
    
    # Layer 3: API Layer
    y3 = y4 - layer_height
    rect = plt.Rectangle((x, y3), w, layer_height - gap, fc=api_color, ec=LINE, lw=1.5)
    ax.add_patch(rect)
    ax.text(x + w/2, y3 + layer_height/2, "API слой — FastAPI :8000\n/ask · /flashcards · /kb · /admin", 
            ha="center", va="center", fontproperties=font("arial.ttf", 11), color=TEXT)
    
    # Layer 2: Service Layer
    y2 = y3 - layer_height
    rect = plt.Rectangle((x, y2), w, layer_height - gap, fc=service_color, ec=LINE, lw=1.5)
    ax.add_patch(rect)
    ax.text(x + w/2, y2 + layer_height/2, "Сервисный слой\nquery_service · tutor_orchestrator · knowledge_graph", 
            ha="center", va="center", fontproperties=font("arial.ttf", 11), color=TEXT)
    
    # Layer 1: Persistence Layer
    y1 = y2 - layer_height
    rect = plt.Rectangle((x, y1), w, layer_height - gap, fc=persist_color, ec=LINE, lw=1.5)
    ax.add_patch(rect)
    ax.text(x + w/2, y1 + layer_height/2, "Persistence слой\nSQLite (user_state.db) · Chroma (векторный индекс) · provider.py", 
            ha="center", va="center", fontproperties=font("arial.ttf", 11), color=TEXT)
    
    # Draw arrows between layers
    arrow_props = dict(arrowstyle='->', lw=2, color=GREEN)
    for y_from, y_to in [(y4, y3), (y3, y2), (y2, y1)]:
        ax.annotate('', xy=(x + w/2, y_to + layer_height - gap), 
                    xytext=(x + w/2, y_from + 0.01),
                    arrowprops=arrow_props)


def draw_rag_pipeline(ax: plt.Axes, box: tuple[float, float, float, float]) -> None:
    """Draw RAG pipeline diagram."""
    x, y, w, h = box
    
    # Pipeline steps
    steps = [
        ("1. CLASSIFY", "Router\nqa/overview/synthesis"),
        ("2. REWRITE", "Query Enricher\nулучшение запроса"),
        ("3. RETRIEVE", "Hybrid Search\nBM25 + Vector"),
        ("4. RERANK", "Cross-encoder\nточная оценка"),
        ("5. GENERATE", "LLM Generation\nответ + источники"),
    ]
    
    step_width = (w - 0.08) / len(steps)
    step_height = h * 0.6
    
    for i, (title, desc) in enumerate(steps):
        step_x = x + i * step_width + 0.02
        step_y = y + (h - step_height) / 2
        
        # Draw step box
        color = ["#e3f2fd", "#fff3e0", "#f3e5f5", "#e8f5e9", "#d4edda"][i]
        rect = plt.Rectangle((step_x, step_y), step_width - 0.02, step_height, 
                            fc=color, ec=LINE, lw=1.5, zorder=2)
        ax.add_patch(rect)
        
        # Add text
        ax.text(step_x + (step_width - 0.02) / 2, step_y + step_height * 0.7,
                title, ha="center", va="center", 
                fontproperties=bold_font("arialbd.ttf", 10), color=DARK)
        ax.text(step_x + (step_width - 0.02) / 2, step_y + step_height * 0.35,
                desc, ha="center", va="center", 
                fontproperties=font("arial.ttf", 8), color=TEXT)
        
        # Draw arrow to next step
        if i < len(steps) - 1:
            arrow_x = step_x + step_width - 0.02
            arrow_y = step_y + step_height / 2
            ax.annotate('', xy=(arrow_x + 0.02, arrow_y),
                       xytext=(arrow_x, arrow_y),
                       arrowprops=dict(arrowstyle='->', lw=2, color=GREEN, zorder=1))


def architecture(pdf: PdfPages) -> None:
    f, ax = fig()
    title(ax, "Архитектура: единое локальное состояние", "Streamlit, CLI и Telegram работают с одной SQLite/Chroma базой.")
    
    # Draw custom architecture diagram
    draw_architecture_diagram(ax, (0.075, 0.24, 0.85, 0.50))
    
    bullets(
        ax,
        [
            "Все входы используют одни сервисы: без дублирования логики.",
            "LLM и embeddings подключаются только через provider.py.",
            "Приватность обеспечивается архитектурой, а не обещанием.",
        ],
        0.11,
        0.19,
        width=78,
        size=13.5,
        gap=0.05,
    )
    footer(ax)
    pdf.savefig(f, dpi=150)
    plt.close(f)


def development(pdf: PdfPages) -> None:
    f, ax = fig()
    title(ax, "Процесс разработки: от ручного хаоса к управляемому циклу", "Backlog SSoT, role prompts, audit chain и воспроизводимые проверки.")
    code(
        ax,
        [
            "plan_next -> accepted package",
            "orchestration -> worker prompts + DoD",
            "audit_closed_packages -> evidence replay",
            "coverage_prompt -> missing tests",
        ],
        (0.065, 0.38, 0.43, 0.29),
    )
    bullets(
        ax,
        [
            "Каждая итерация оставляет след: backlog, changelog, tests, artifacts.",
            "Агенты работают не “на память”, а по контрактам и проверкам.",
            "Качество результата можно пересобрать и проверить заново.",
        ],
        0.56,
        0.68,
        width=36,
        size=17,
        gap=0.105,
    )
    footer(ax)
    pdf.savefig(f, dpi=150)
    plt.close(f)


def docs(pdf: PdfPages) -> None:
    f, ax = fig()
    title(ax, "Финальный результат", "Проект уже оформлен как инженерный продукт, а не только учебный прототип.")
    bullets(
        ax,
        [
            "FastAPI + Streamlit + CLI + Telegram поверх общего ядра.",
            "RAG pipeline с citation grounding, trust panel и guardrails.",
            "Учебный цикл: tutor, quiz, SRS, mastery tracking, adaptive plan.",
            "Документация, backlog registry и воспроизводимые команды сборки.",
        ],
        0.085,
        0.70,
        width=72,
        size=18,
        gap=0.1,
    )
    ax.text(0.085, 0.22, "Команда пересборки PDF:", color=MUTED, fontproperties=font("arial.ttf", 13), ha="left")
    code(ax, ["npm run docs:defense-pdf:visual"], (0.085, 0.105, 0.46, 0.09))
    footer(ax, "source: doc/presentations/defense_presentation.md + doc/screenshots/")
    pdf.savefig(f, dpi=150)
    plt.close(f)


def build(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output) as pdf:
        cover(pdf)
        slide_full_image(
            pdf,
            "Обзор продукта: проблема и решение",
            "Из разрозненной папки материалов — в персонального AI-тьютора.",
            ASSETS / "slide_01_product_overview.png",
        )
        slide_image_left(
            pdf,
            "Почему home-rag сильнее набора отдельных инструментов",
            "ChatGPT, Anki и Obsidian решают части задачи. home-rag закрывает цикл целиком.",
            "pdf_slide_02.png",
            [
                "Ответы именно по вашим файлам.",
                "Тьютор и quiz сохраняют контекст ответа.",
                "SRS и mastery превращают ответ в долгосрочное знание.",
            ],
        )
        slide_image_right(
            pdf,
            "Один инструмент для полного цикла обучения",
            "Ingest -> Quick Answer -> Tutor -> Micro-quiz -> Flashcards -> Mastery.",
            "pdf_slide_03.png",
            [
                "Пользователь не собирает workflow вручную.",
                "Состояние обучения хранится локально.",
                "Каждый шаг обновляет модель ученика.",
            ],
        )
        architecture(pdf)
        
        # Real product screenshot: Quick Answer
        f, ax = fig()
        title(ax, "Быстрый ответ с источниками", 
              "RAG retrieval находит релевантные фрагменты, LLM генерирует ответ с атрибуцией.")
        image(ax, ASSETS / "final/scenario_01/03_quick_answer_with_sources.png", (0.06, 0.13, 0.88, 0.60))
        bullets(
            ax,
            [
                "Ответ привязан к найденным источникам из ваших документов.",
                "Retrieval confidence показывает качество найденного контекста.",
                "Кликабельные источники для проверки модели.",
                "CTA 'Учить эту тему' запускает полный учебный цикл.",
            ],
            0.065,
            0.10,
            width=80,
            size=12,
            gap=0.042,
        )
        footer(ax)
        pdf.savefig(f, dpi=150)
        plt.close(f)
        
        # Real product screenshot: Tutor Handoff
        f, ax = fig()
        title(ax, "Переход от ответа к тьютору без потери контекста",
              "Быстрый ответ становится стартовой точкой для глубокого разбора.")
        image(ax, ASSETS / "final/scenario_03/02_tutor_context_handoff.png", (0.06, 0.13, 0.88, 0.60))
        bullets(
            ax,
            [
                "Тьютор знает тему, вопрос и источники из предыдущего ответа.",
                "Сократический диалог вытаскивает понимание через вопросы.",
                "Quiz проверяет только что разобранный материал.",
                "Карточки создаются из слабых мест автоматически.",
            ],
            0.065,
            0.10,
            width=80,
            size=12,
            gap=0.042,
        )
        footer(ax)
        pdf.savefig(f, dpi=150)
        plt.close(f)
        
        # Add RAG pipeline slide with custom diagram
        f, ax = fig()
        title(ax, "RAG Pipeline: 5-ступенчатая обработка запроса", 
              "От вопроса студента до ответа с источниками через classify, rewrite, retrieve, rerank, generate.")
        draw_rag_pipeline(ax, (0.075, 0.42, 0.85, 0.32))
        bullets(
            ax,
            [
                "Classify определяет тип запроса (qa/overview/synthesis).",
                "Rewrite улучшает формулировку для лучшего поиска.",
                "Retrieve использует гибридный поиск (BM25 + Vector).",
                "Rerank точно оценивает релевантность с cross-encoder.",
                "Generate создает ответ строго по найденным источникам.",
            ],
            0.085,
            0.37,
            width=78,
            size=13,
            gap=0.048,
        )
        footer(ax)
        pdf.savefig(f, dpi=150)
        plt.close(f)
        
        slide_image_left(
            pdf,
            "Trust RAG: ответы можно проверять",
            "Guardrails, citation grounding и confidence не дают модели “говорить из воздуха”.",
            "pdf_slide_08.png",
            [
                "Ответ привязан к найденным источникам.",
                "Trust-панель объясняет уверенность.",
                "Подсветка фрагментов ускоряет проверку.",
            ],
        )
        slide_image_right(
            pdf,
            "Переход от ответа к тьютору без потери контекста",
            "Быстрый ответ становится стартовой точкой для глубокого разбора.",
            "pdf_slide_05.png",
            [
                "Тьютор знает тему, вопрос и источники.",
                "Quiz проверяет только что разобранный материал.",
                "Карточки создаются из слабых мест, а не вручную.",
            ],
        )
        slide_image_left(
            pdf,
            "Course Workspace: папка становится курсом",
            "Отдельный scope, синтез курса, flashcards и изолированный прогресс.",
            "pdf_slide_04.png",
            [
                "Один клик активирует учебное пространство.",
                "План и вопросы ограничены материалами курса.",
                "Mastery dashboard показывает, что уже освоено.",
            ],
        )
        slide_image_right(
            pdf,
            "Модель ученика ведет следующий шаг",
            "Adaptive Daily Plan выбирает gap, review или новую тему.",
            "pdf_slide_07.png",
            [
                "Система сама приоритизирует день.",
                "Graduation убирает освоенное из активной нагрузки.",
                "Streak и due-карточки поддерживают ритм.",
            ],
        )
        slide_image_left(
            pdf,
            "Offline и приватность как архитектурное свойство",
            "Ollama/OpenAI-compatible provider переключается конфигом, без правок логики.",
            "pdf_slide_10.png",
            [
                "Данные и прогресс остаются на машине.",
                "Переиндексация безопасна и воспроизводима.",
                "Cloud можно включать только там, где это осознанно нужно.",
            ],
        )
        development(pdf)
        slide_image_right(
            pdf,
            "Для кого проект",
            "Лучший fit: студенты, power users, корпоративные пользователи и экономный offline-сценарий.",
            "pdf_slide_01.png",
            [
                "Студент получает личного тьютора по своим конспектам.",
                "Power user автоматизирует карточки и повторение.",
                "Корпоративный сценарий выигрывает от локальности.",
            ],
        )
        docs(pdf)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the visual defense deck PDF.")
    parser.add_argument("output", nargs="?", default=str(DOC / "defense_presentation.pdf"))
    args = parser.parse_args()
    build(Path(args.output))
    print(f"Rendered {args.output}")


if __name__ == "__main__":
    main()
