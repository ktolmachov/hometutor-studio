"""Build a visual-first 16:9 expert defense presentation PDF.

The detailed Markdown deck remains the long-form source. This script creates a
curated expert deck with real TrueType text, large visuals, and stable slide
coordinates. All drawing uses axes coordinates to avoid drifting titles.
"""

from __future__ import annotations

import argparse
import os
import textwrap
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib-cache").resolve()))

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc"
ASSETS = DOC / "screenshots"
PDF_ASSETS = ASSETS / "defense_pdf"
FINAL_ASSETS = ASSETS / "final"

SLIDE_W = 13.333
SLIDE_H = 7.5

GREEN = "#2f8f67"
DARK = "#12362b"
TEXT = "#17201c"
MUTED = "#5a6862"
SOFT = "#eef7f2"
LINE = "#c9ded3"
INK = "#101827"
BLUE = "#2f6f9f"
AMBER = "#c47f24"
PURPLE = "#8057a8"
RED = "#b65f5f"


def font(name: str, size: float, weight: str = "normal") -> FontProperties:
    path = Path("C:/Windows/Fonts") / name
    if path.exists():
        return FontProperties(fname=str(path), size=size)
    return FontProperties(family="DejaVu Sans", size=size, weight=weight)


REG = "arial.ttf"
BOLD = "arialbd.ttf"
MONO = "consola.ttf"


def clean(text: str) -> str:
    replacements = {
        "→": "->",
        "↔": "<->",
        "✅": "Да",
        "❌": "Нет",
        "⚠": "Важно:",
        "🎯": "",
        "📚": "",
        "📊": "",
        "🔍": "",
        "🔒": "",
        "🧭": "",
        "🖥️": "",
        "☁️": "",
        "👥": "",
        "⚖️": "",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return " ".join(text.split())


def new_slide() -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=150, facecolor="white")
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    return fig, ax


def ax_text(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    *,
    size: float,
    bold: bool = False,
    color: str = TEXT,
    ha: str = "left",
    va: str = "top",
    width: int | None = None,
    linespacing: float = 1.2,
) -> None:
    content = clean(text)
    if width:
        content = "\n".join(textwrap.wrap(content, width=width))
    ax.text(
        x,
        y,
        content,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        color=color,
        fontproperties=font(BOLD if bold else REG, size, "bold" if bold else "normal"),
        linespacing=linespacing,
    )


def title(ax: plt.Axes, heading: str, subtitle: str | None = None) -> None:
    ax_text(ax, 0.055, 0.925, heading, size=26, bold=True, color=DARK, width=68)
    ax.plot([0.055, 0.945], [0.845, 0.845], transform=ax.transAxes, color=GREEN, lw=2.5)
    if subtitle:
        ax_text(ax, 0.055, 0.81, subtitle, size=12.6, color=MUTED, width=112, linespacing=1.18)


def footer(ax: plt.Axes, label: str = "home-rag_v2 · local-first AI tutor") -> None:
    ax.plot([0.055, 0.945], [0.055, 0.055], transform=ax.transAxes, color=LINE, lw=1.1)
    ax_text(ax, 0.945, 0.032, label, size=8.6, color=MUTED, ha="right", va="bottom")


def add_image(ax: plt.Axes, path: Path, box: tuple[float, float, float, float], border: bool = True) -> None:
    left, bottom, width, height = box
    img = Image.open(path).convert("RGB")
    ratio = img.width / img.height
    box_ratio = width / height
    if ratio > box_ratio:
        render_w = width
        render_h = width / ratio
        x = left
        y = bottom + (height - render_h) / 2
    else:
        render_h = height
        render_w = height * ratio
        x = left + (width - render_w) / 2
        y = bottom
    img_ax = ax.figure.add_axes((x, y, render_w, render_h))
    img_ax.imshow(img)
    img_ax.set_axis_off()
    if border:
        rect = plt.Rectangle((x, y), render_w, render_h, transform=ax.figure.transFigure, fill=False, lw=1.0, ec=LINE)
        ax.figure.patches.append(rect)


def bullet_list(
    ax: plt.Axes,
    items: Iterable[str],
    x: float,
    y: float,
    *,
    width: int = 42,
    size: float = 15.5,
    gap: float = 0.084,
) -> None:
    current = y
    for item in items:
        lines = textwrap.wrap(clean(item), width=width)
        ax_text(ax, x, current, "•", size=size + 3, bold=True, color=GREEN)
        ax_text(ax, x + 0.028, current, "\n".join(lines), size=size, color=TEXT, linespacing=1.18)
        current -= gap * max(1, len(lines))


def pill(ax: plt.Axes, x: float, y: float, text: str) -> None:
    ax.text(
        x,
        y,
        clean(text),
        transform=ax.transAxes,
        ha="left",
        va="center",
        color=DARK,
        fontproperties=font(BOLD, 11),
        bbox=dict(boxstyle="round,pad=0.34,rounding_size=0.16", fc=SOFT, ec=LINE, lw=1),
    )


def code_box(ax: plt.Axes, lines: list[str], box: tuple[float, float, float, float]) -> None:
    x, y, w, h = box
    ax.add_patch(plt.Rectangle((x, y), w, h, transform=ax.transAxes, fc=INK, ec=INK, lw=0))
    ax.text(
        x + 0.025,
        y + h - 0.045,
        "\n".join(lines),
        transform=ax.transAxes,
        ha="left",
        va="top",
        color="#d7f5e4",
        fontproperties=font(MONO, 13.5),
        linespacing=1.35,
    )


def save(pdf: PdfPages, fig: plt.Figure, previews: list[Path] | None, index: int) -> None:
    pdf.savefig(fig, dpi=150)
    if previews is not None:
        fig.savefig(previews[index - 1], dpi=120, facecolor="white")
    plt.close(fig)


def cover(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    ax_text(ax, 0.055, 0.89, "home-rag", size=43, bold=True, color=GREEN)
    ax_text(ax, 0.30, 0.89, ": персональный AI-тьютор", size=36, bold=True, color="#050505")
    ax_text(
        ax,
        0.058,
        0.75,
        "Локальная система, которая превращает ваши PDF, DOCX и Markdown в обучение: ответы с источниками, тьютор, quiz, flashcards и план повторения.",
        size=17,
        width=78,
        linespacing=1.25,
    )
    add_image(ax, PDF_ASSETS / "pdf_slide_01.png", (0.46, 0.14, 0.47, 0.54), border=False)
    pill(ax, 0.058, 0.23, "Без облака и подписок")
    pill(ax, 0.245, 0.23, "Полный цикл обучения")
    pill(ax, 0.455, 0.23, "Старт за 5 минут")
    footer(ax, "Академическая защита · май 2026")
    save(pdf, fig, previews, index)


def full_image_slide(pdf: PdfPages, previews: list[Path] | None, index: int, heading: str, subtitle: str, image_path: Path) -> None:
    fig, ax = new_slide()
    title(ax, heading, subtitle)
    add_image(ax, image_path, (0.055, 0.125, 0.89, 0.62), border=True)
    footer(ax)
    save(pdf, fig, previews, index)


def hero_image_slide(
    pdf: PdfPages,
    previews: list[Path] | None,
    index: int,
    heading: str,
    subtitle: str,
    image_name: str,
    takeaways: list[str],
) -> None:
    fig, ax = new_slide()
    title(ax, heading, subtitle)
    add_image(ax, PDF_ASSETS / image_name, (0.075, 0.245, 0.85, 0.475), border=True)
    x = 0.095
    for item in takeaways:
        ax.text(
            x,
            0.165,
            clean(item),
            transform=ax.transAxes,
            ha="left",
            va="center",
            color=DARK,
            fontproperties=font(BOLD, 11.5),
            bbox=dict(boxstyle="round,pad=0.42,rounding_size=0.14", fc=SOFT, ec=LINE, lw=1),
        )
        x += 0.29
    footer(ax)
    save(pdf, fig, previews, index)


def product_screenshot_slide(
    pdf: PdfPages,
    previews: list[Path] | None,
    index: int,
    heading: str,
    subtitle: str,
    screenshot: Path,
    points: list[str],
) -> None:
    fig, ax = new_slide()
    title(ax, heading, subtitle)
    add_image(ax, screenshot, (0.07, 0.22, 0.86, 0.49), border=True)
    bullet_list(ax, points, 0.085, 0.18, width=76, size=12.4, gap=0.044)
    footer(ax)
    save(pdf, fig, previews, index)


def architecture_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "Архитектура: единое локальное состояние", "Streamlit, CLI и Telegram работают с одной SQLite/Chroma базой.")
    layers = [
        ("Интерфейсный слой", "Streamlit UI · CLI · Telegram Bot", "#e3f2fd"),
        ("API слой", "FastAPI :8000 · /ask · /flashcards · /kb · /admin", "#fff3e0"),
        ("Сервисный слой", "query_service · tutor_orchestrator · knowledge_graph", "#f3e5f5"),
        ("Persistence слой", "SQLite · Chroma · provider.py", "#e8f5e9"),
    ]
    x, w = 0.09, 0.82
    top = 0.705
    box_h = 0.105
    for i, (name, desc, color) in enumerate(layers):
        y = top - i * 0.125
        ax.add_patch(plt.Rectangle((x, y), w, box_h, transform=ax.transAxes, fc=color, ec=LINE, lw=1.4))
        ax_text(ax, x + w / 2, y + box_h * 0.66, name, size=14, bold=True, color=DARK, ha="center", va="center")
        ax_text(ax, x + w / 2, y + box_h * 0.32, desc, size=11.5, color=TEXT, ha="center", va="center")
        if i < len(layers) - 1:
            ax.annotate("", xy=(x + w / 2, y - 0.018), xytext=(x + w / 2, y - 0.002), xycoords=ax.transAxes, textcoords=ax.transAxes, arrowprops=dict(arrowstyle="->", lw=1.8, color=GREEN))
    bullet_list(
        ax,
        [
            "Все входы используют одни сервисы: без дублирования логики.",
            "LLM и embeddings подключаются только через provider.py.",
            "Приватность обеспечивается архитектурой, а не обещанием.",
        ],
        0.10,
        0.20,
        width=82,
        size=13.6,
        gap=0.052,
    )
    footer(ax)
    save(pdf, fig, previews, index)


def boundary_contracts_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "Архитектурные границы: меньше магии, больше контрактов", "Запреты в проекте удерживают систему расширяемой и проверяемой.")
    columns = [
        ("Config", "Только get_settings()\nи get_retrieval_settings()", BLUE),
        ("LLM / Embed", "Только app/provider.py\nOllama/cloud через конфиг", GREEN),
        ("Prompts", "Только app/prompts.py\nбез хардкода в UI/routers", AMBER),
        ("HTTP", "Только app/routers/*\nрегистрация через include_router", PURPLE),
    ]
    for i, (name, desc, color) in enumerate(columns):
        x = 0.065 + i * 0.225
        ax.add_patch(plt.Rectangle((x, 0.47), 0.19, 0.23, transform=ax.transAxes, fc="#f8fbfa", ec=color, lw=2))
        ax_text(ax, x + 0.095, 0.645, name, size=15, bold=True, color=color, ha="center", va="center")
        ax_text(ax, x + 0.095, 0.555, desc, size=10.7, color=TEXT, ha="center", va="center", width=25)
    bullet_list(
        ax,
        [
            "Guardrails проходят через API, CLI и Telegram: одна политика на все входы.",
            "Pipeline шаги имеют контракт process(QueryContext) -> QueryContext.",
            "User-state живет за _with_db() и CRUD-хелперами user_state.py.",
        ],
        0.08,
        0.31,
        width=86,
        size=15.2,
        gap=0.07,
    )
    footer(ax, "expert lens: architecture invariants")
    save(pdf, fig, previews, index)


def query_state_machine_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "Query pipeline как typed state machine", "Каждый шаг обогащает QueryContext: trace, metadata, sources, timings, cost и guardrails.")
    steps = [
        ("Input\nvalidation", "#e3f2fd"),
        ("Classify\nquery type", "#fff3e0"),
        ("Rewrite\nquery", "#f3e5f5"),
        ("Retrieve\nChroma/BM25", "#e8f5e9"),
        ("Rerank\noptional", "#edf7f2"),
        ("Generate\nanswer", "#e8eefb"),
        ("Output\nguardrails", "#fdeeed"),
    ]
    x0, y, w = 0.045, 0.535, 0.118
    for i, (label, color) in enumerate(steps):
        x = x0 + i * 0.135
        ax.add_patch(plt.Rectangle((x, y), w, 0.16, transform=ax.transAxes, fc=color, ec=LINE, lw=1.5))
        ax_text(ax, x + w / 2, y + 0.08, label, size=10.8, bold=True, color=DARK, ha="center", va="center")
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + 0.017, y + 0.08), xytext=(x + w + 0.002, y + 0.08), xycoords=ax.transAxes, textcoords=ax.transAxes, arrowprops=dict(arrowstyle="->", lw=1.8, color=GREEN))
    code_box(
        ax,
        ["QueryContext {", "  query, query_type, retrieval_mode,", "  sources, answer, metadata, trace,", "  timings, usage, cost, guardrails", "}"],
        (0.075, 0.205, 0.40, 0.23),
    )
    bullet_list(
        ax,
        [
            "Новые возможности добавляются как шаги, а не как ветвление в роутере.",
            "Debug trace делает поведение пайплайна объяснимым для eval и защиты.",
            "Graph expansion и tutor orchestration живут как расширения контекста.",
        ],
        0.535,
        0.39,
        width=38,
        size=13.4,
        gap=0.078,
    )
    footer(ax, "expert lens: observability and pipeline contracts")
    save(pdf, fig, previews, index)


def persistence_lifecycle_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "Persistence и index lifecycle", "Локальность не означает хаос файлов: индекс, прогресс и метрики имеют владельцев.")
    stores = [
        ("SQLite\nuser_state.db", "learner model\nflashcards\nSRS\nsync bundle", GREEN),
        ("Chroma\nchroma_db/", "chunks\nembeddings\nactive generation", BLUE),
        ("index_registry.json", "blue-green\nactivation\nindex_version", AMBER),
        ("metrics\nJSONL/SQLite", "latency\nquality\ncost/debug", PURPLE),
    ]
    for i, (name, body, color) in enumerate(stores):
        x = 0.08 + i * 0.225
        ax.add_patch(plt.Rectangle((x, 0.45), 0.18, 0.24, transform=ax.transAxes, fc="#f8fbfa", ec=color, lw=2))
        ax_text(ax, x + 0.09, 0.63, name, size=13.2, bold=True, color=color, ha="center", va="center")
        ax_text(ax, x + 0.09, 0.525, body, size=10.5, color=TEXT, ha="center", va="center")
    ax.text(
        0.50,
        0.36,
        "reindex: staging -> validation -> activate",
        transform=ax.transAxes,
        ha="center",
        va="center",
        color=DARK,
        fontproperties=font(BOLD, 15),
        bbox=dict(boxstyle="round,pad=0.42,rounding_size=0.14", fc=SOFT, ec=LINE),
    )
    bullet_list(
        ax,
        [
            "User-state таблицы не открываются напрямую: только owner wrapper.",
            "Chroma backend generation-aware: staging можно собрать без разрушения active.",
            "Backup/sync отделены от query path, поэтому деградация локализована.",
        ],
        0.10,
        0.25,
        width=82,
        size=14.4,
        gap=0.066,
    )
    footer(ax, "expert lens: data ownership and local-first reliability")
    save(pdf, fig, previews, index)


def rag_pipeline_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "RAG pipeline: 5 шагов до проверяемого ответа", "От вопроса студента до ответа с источниками.")
    steps = [
        ("Classify", "тип запроса", BLUE),
        ("Rewrite", "улучшение", AMBER),
        ("Retrieve", "BM25 + vector", PURPLE),
        ("Rerank", "точная оценка", GREEN),
        ("Generate", "ответ + sources", "#4d8dcb"),
    ]
    y, x0, step_w = 0.51, 0.075, 0.155
    for i, (name, desc, color) in enumerate(steps):
        x = x0 + i * 0.18
        ax.add_patch(plt.Rectangle((x, y), step_w, 0.17, transform=ax.transAxes, fc="#f7fbf9", ec=color, lw=2))
        ax_text(ax, x + step_w / 2, y + 0.115, name, size=13, bold=True, color=color, ha="center", va="center")
        ax_text(ax, x + step_w / 2, y + 0.055, desc, size=10.5, color=TEXT, ha="center", va="center")
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + step_w + 0.022, y + 0.085), xytext=(x + step_w + 0.002, y + 0.085), xycoords=ax.transAxes, textcoords=ax.transAxes, arrowprops=dict(arrowstyle="->", lw=2, color=GREEN))
    bullet_list(
        ax,
        [
            "Classify выбирает режим: qa, overview или synthesis.",
            "Rewrite расширяет формулировку для лучшего поиска.",
            "Retrieve и Rerank находят и сортируют доказательства.",
            "Generate отвечает строго по найденному контексту.",
        ],
        0.09,
        0.36,
        width=76,
        size=14.2,
        gap=0.06,
    )
    footer(ax)
    save(pdf, fig, previews, index)


def process_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "Процесс разработки: управляемый агентный цикл", "Backlog SSoT, role prompts, audit chain и воспроизводимые проверки.")
    code_box(
        ax,
        ["plan_next -> accepted package", "orchestration -> worker prompts + DoD", "audit_closed_packages -> evidence replay", "coverage_prompt -> missing tests"],
        (0.075, 0.37, 0.42, 0.30),
    )
    bullet_list(
        ax,
        [
            "Каждая итерация оставляет след: backlog, changelog, tests, artifacts.",
            "Агенты работают по контрактам, а не по памяти.",
            "Качество результата можно пересобрать и проверить заново.",
        ],
        0.56,
        0.67,
        width=36,
        size=16.3,
        gap=0.102,
    )
    footer(ax)
    save(pdf, fig, previews, index)


def final_slide(pdf: PdfPages, previews: list[Path] | None, index: int) -> None:
    fig, ax = new_slide()
    title(ax, "Финальный результат", "Проект оформлен как инженерный продукт, а не только учебный прототип.")
    bullet_list(
        ax,
        [
            "FastAPI + Streamlit + CLI + Telegram поверх общего ядра.",
            "RAG pipeline с citation grounding, trust panel и guardrails.",
            "Учебный цикл: tutor, quiz, SRS, mastery tracking, adaptive plan.",
            "Документация, backlog registry и воспроизводимые команды сборки.",
        ],
        0.085,
        0.70,
        width=74,
        size=17.2,
        gap=0.09,
    )
    ax_text(ax, 0.085, 0.20, "Команда пересборки PDF:", size=13, color=MUTED)
    code_box(ax, ["npm run docs:defense-pdf:visual"], (0.085, 0.10, 0.42, 0.085))
    footer(ax, "source: doc/presentations/defense_presentation.md + doc/screenshots/")
    save(pdf, fig, previews, index)


def build(output: Path, preview_dir: Path | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    previews: list[Path] | None = None
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)
        previews = [preview_dir / f"slide_{i:02d}.png" for i in range(1, 32)]

    slide_no = 1
    with PdfPages(output) as pdf:
        cover(pdf, previews, slide_no); slide_no += 1
        full_image_slide(pdf, previews, slide_no, "Обзор продукта: проблема и решение", "Из разрозненной папки материалов — в персонального AI-тьютора.", ASSETS / "slide_01_product_overview.png"); slide_no += 1
        hero_image_slide(pdf, previews, slide_no, "Один инструмент для полного цикла обучения", "Ingest -> Quick Answer -> Tutor -> Micro-quiz -> Flashcards -> Mastery.", "pdf_slide_03.png", ["Контекст не теряется", "State хранится локально", "Каждый шаг учит модель ученика"]); slide_no += 1
        architecture_slide(pdf, previews, slide_no); slide_no += 1
        boundary_contracts_slide(pdf, previews, slide_no); slide_no += 1
        query_state_machine_slide(pdf, previews, slide_no); slide_no += 1
        persistence_lifecycle_slide(pdf, previews, slide_no); slide_no += 1
        product_screenshot_slide(pdf, previews, slide_no, "Быстрый ответ с источниками", "RAG retrieval находит фрагменты, LLM отвечает с проверяемой атрибуцией.", FINAL_ASSETS / "scenario_01/03_quick_answer_with_sources.png", ["Ответ привязан к источникам из ваших документов.", "Retrieval confidence показывает качество найденного контекста.", "CTA запускает полный учебный цикл по теме."]); slide_no += 1
        product_screenshot_slide(pdf, previews, slide_no, "Переход к тьютору без потери контекста", "Быстрый ответ становится стартовой точкой для глубокого разбора.", FINAL_ASSETS / "scenario_03/02_tutor_context_handoff.png", ["Тьютор знает тему, вопрос и источники предыдущего ответа.", "Сократический диалог вытаскивает понимание через вопросы.", "Quiz и карточки создаются из только что разобранного материала."]); slide_no += 1
        rag_pipeline_slide(pdf, previews, slide_no); slide_no += 1
        hero_image_slide(pdf, previews, slide_no, "Trust RAG: ответы можно проверять", "Guardrails, citation grounding и confidence не дают модели говорить из воздуха.", "pdf_slide_08.png", ["Sources first", "Trust-панель", "Guardrails"]); slide_no += 1
        hero_image_slide(pdf, previews, slide_no, "Course Workspace: папка становится курсом", "Отдельный scope, синтез курса, flashcards и изолированный прогресс.", "pdf_slide_04.png", ["Один клик", "Изолированный прогресс", "Course synthesis"]); slide_no += 1
        hero_image_slide(pdf, previews, slide_no, "Модель ученика ведет следующий шаг", "Adaptive Daily Plan выбирает gap, review или новую тему.", "pdf_slide_07.png", ["Gap -> review -> new", "Graduation", "Streak"]); slide_no += 1
        hero_image_slide(pdf, previews, slide_no, "Offline и приватность как архитектурное свойство", "Ollama/OpenAI-compatible provider переключается конфигом, без правок логики.", "pdf_slide_10.png", ["Данные локально", "Безопасная переиндексация", "Cloud optional"]); slide_no += 1
        process_slide(pdf, previews, slide_no); slide_no += 1
        hero_image_slide(pdf, previews, slide_no, "Для кого проект", "Лучший fit: студенты, power users, корпоративные пользователи и offline-сценарий.", "pdf_slide_01.png", ["Студенты", "Power users", "Локальные корпоративные знания"]); slide_no += 1
        final_slide(pdf, previews, slide_no)


def make_contact_sheet(preview_dir: Path) -> Path:
    files = sorted(preview_dir.glob("slide_*.png"))
    thumbs: list[Image.Image] = []
    for file in files:
        im = Image.open(file).convert("RGB")
        im.thumbnail((360, 203))
        tile = Image.new("RGB", (380, 245), "white")
        tile.paste(im, ((380 - im.width) // 2, 16))
        ImageDraw.Draw(tile).text((16, 220), file.stem, fill=(0, 0, 0))
        thumbs.append(tile)
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 380, rows * 245), (242, 245, 243))
    for index, tile in enumerate(thumbs):
        sheet.paste(tile, ((index % cols) * 380, (index // cols) * 245))
    out = preview_dir / "contact_sheet.png"
    sheet.save(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the visual defense deck PDF.")
    parser.add_argument("output", nargs="?", default=str(DOC / "defense_presentation.pdf"))
    parser.add_argument("--preview-dir", default=None, help="Optional directory for PNG slide previews.")
    args = parser.parse_args()
    preview_dir = Path(args.preview_dir) if args.preview_dir else None
    build(Path(args.output), preview_dir=preview_dir)
    if preview_dir:
        print(f"Preview sheet: {make_contact_sheet(preview_dir)}")
    print(f"Rendered {args.output}")


if __name__ == "__main__":
    main()
