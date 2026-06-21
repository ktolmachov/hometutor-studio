"""Render a Markdown file to an image-only PDF.

This is intentionally conservative: pages are raster images, so Adobe Acrobat
does not need to extract embedded fonts. It is useful for presentation PDFs
with screenshots and emoji-heavy Markdown.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAGE_W = 1600
PAGE_H = 1131
MARGIN_X = 92
MARGIN_Y = 68
BG = (255, 255, 255)
TEXT = (23, 32, 28)
GREEN = (47, 143, 103)
DARK_GREEN = (18, 54, 43)
SOFT_GREEN = (237, 247, 242)
LINE = (205, 216, 210)
CODE_BG = (17, 24, 39)
CODE_FG = (229, 243, 236)


def font_path(name: str) -> str:
    candidate = Path("C:/Windows/Fonts") / name
    if candidate.exists():
        return str(candidate)
    return name


FONTS = {
    "regular": font_path("arial.ttf"),
    "bold": font_path("arialbd.ttf"),
    "italic": font_path("ariali.ttf"),
    "mono": font_path("consola.ttf"),
}


def load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONTS[kind], size)
    except OSError:
        return ImageFont.load_default(size=size)


def clean_text(value: str) -> str:
    replacements = {
        "→": "->",
        "↔": "<->",
        "⇒": "=>",
        "✅": "Да",
        "✔": "Да",
        "✓": "Да",
        "❌": "Нет",
        "✖": "Нет",
        "✗": "Нет",
        "⚠": "Внимание:",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[\U0001F000-\U0001FAFF\uFE0F\u200D]", "", value)
    value = re.sub(r"[\u2190-\u21FF\u2300-\u23FF\u2460-\u24FF\u25A0-\u27BF\u2900-\u297F\u2B00-\u2BFF]", "", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    if not text:
        return 0, 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


class Renderer:
    def __init__(self, md_path: Path, output_path: Path, scale: float) -> None:
        self.md_path = md_path
        self.output_path = output_path
        self.scale = scale
        self.pages: list[Image.Image] = []
        self.page = self.new_page()
        self.draw = ImageDraw.Draw(self.page)
        self.x = MARGIN_X
        self.y = MARGIN_Y
        self.max_w = PAGE_W - 2 * MARGIN_X
        self.fonts = {
            "h1": load_font("bold", int(48 * scale)),
            "h2": load_font("bold", int(40 * scale)),
            "h3": load_font("bold", int(28 * scale)),
            "body": load_font("regular", int(23 * scale)),
            "bold": load_font("bold", int(23 * scale)),
            "small": load_font("regular", int(18 * scale)),
            "code": load_font("mono", int(17 * scale)),
        }

    def new_page(self) -> Image.Image:
        return Image.new("RGB", (PAGE_W, PAGE_H), BG)

    def finish_page(self) -> None:
        self.pages.append(self.page)
        self.page = self.new_page()
        self.draw = ImageDraw.Draw(self.page)
        self.x = MARGIN_X
        self.y = MARGIN_Y

    def ensure_space(self, height: int) -> None:
        if self.y + height > PAGE_H - MARGIN_Y:
            self.finish_page()

    def line_height(self, font: ImageFont.FreeTypeFont, factor: float = 1.35) -> int:
        _, height = text_size(self.draw, "Ag", font)
        return max(1, int(height * factor))

    def wrap(self, text: str, font: ImageFont.FreeTypeFont, width: int | None = None) -> list[str]:
        width = width or self.max_w
        words = clean_text(text).split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if text_size(self.draw, candidate, font)[0] <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def paragraph(self, text: str, font: ImageFont.FreeTypeFont | None = None, color=TEXT, indent: int = 0) -> None:
        font = font or self.fonts["body"]
        lines = self.wrap(text, font, self.max_w - indent)
        line_h = self.line_height(font)
        self.ensure_space(line_h * len(lines) + 10)
        for line in lines:
            self.draw.text((self.x + indent, self.y), line, font=font, fill=color)
            self.y += line_h
        self.y += 8

    def heading(self, level: int, text: str) -> None:
        if level == 2 and self.y > MARGIN_Y + 40:
            self.finish_page()
        font = self.fonts["h1" if level == 1 else "h2" if level == 2 else "h3"]
        color = DARK_GREEN
        lines = self.wrap(text, font)
        line_h = self.line_height(font, 1.22)
        self.ensure_space(line_h * len(lines) + 28)
        for line in lines:
            self.draw.text((self.x, self.y), line, font=font, fill=color)
            self.y += line_h
        if level == 1:
            self.draw.line((self.x, self.y + 8, PAGE_W - MARGIN_X, self.y + 8), fill=GREEN, width=5)
            self.y += 30
        else:
            self.y += 14

    def bullet(self, text: str, ordered: bool = False, number: str = "") -> None:
        marker = f"{number}." if ordered else "-"
        self.paragraph(f"{marker} {text}", indent=18)

    def quote(self, text: str) -> None:
        font = self.fonts["body"]
        lines = self.wrap(text, font, self.max_w - 42)
        line_h = self.line_height(font)
        height = line_h * len(lines) + 30
        self.ensure_space(height)
        self.draw.rectangle((self.x, self.y, PAGE_W - MARGIN_X, self.y + height), fill=SOFT_GREEN)
        self.draw.rectangle((self.x, self.y, self.x + 8, self.y + height), fill=GREEN)
        y = self.y + 14
        for line in lines:
            self.draw.text((self.x + 24, y), line, font=font, fill=TEXT)
            y += line_h
        self.y += height + 12

    def code_block(self, lines: list[str]) -> None:
        font = self.fonts["code"]
        line_h = self.line_height(font, 1.25)
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(self.wrap(line, font, self.max_w - 36))
        height = line_h * max(1, len(wrapped)) + 28
        self.ensure_space(height)
        self.draw.rounded_rectangle((self.x, self.y, PAGE_W - MARGIN_X, self.y + height), radius=12, fill=CODE_BG)
        y = self.y + 14
        for line in wrapped:
            self.draw.text((self.x + 18, y), line, font=font, fill=CODE_FG)
            y += line_h
        self.y += height + 14

    def image(self, src: str) -> None:
        image_path = (self.md_path.parent / src).resolve()
        if not image_path.exists():
            self.paragraph(f"[missing image: {src}]", color=(160, 40, 40))
            return
        with Image.open(image_path) as raw:
            img = raw.convert("RGB")
            max_h = int(PAGE_H * 0.58)
            scale = min(self.max_w / img.width, max_h / img.height, 1.0)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            self.ensure_space(img.height + 24)
            x = self.x + (self.max_w - img.width) // 2
            self.page.paste(img, (x, self.y))
            self.y += img.height + 22

    def table(self, rows: list[list[str]]) -> None:
        for row_index, row in enumerate(rows):
            prefix = " | ".join(clean_text(cell) for cell in row)
            font = self.fonts["bold"] if row_index == 0 else self.fonts["small"]
            self.paragraph(prefix, font=font)

    def render(self) -> None:
        lines = self.md_path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                self.y += 6
                i += 1
                continue
            if stripped.startswith("```"):
                code: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i])
                    i += 1
                self.code_block(code)
            elif stripped.startswith("!["):
                match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", stripped)
                if match:
                    self.image(match.group(1))
            elif re.match(r"^#{1,6}\s+", stripped):
                hashes, title = stripped.split(" ", 1)
                self.heading(len(hashes), title)
            elif stripped.startswith(">"):
                quote_lines = [stripped.lstrip(">").strip()]
                while i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                    i += 1
                    quote_lines.append(lines[i].strip().lstrip(">").strip())
                self.quote(" ".join(quote_lines))
            elif stripped == "---":
                self.y += 12
                self.draw.line((self.x, self.y, PAGE_W - MARGIN_X, self.y), fill=LINE, width=2)
                self.y += 18
            elif "|" in stripped and i + 1 < len(lines) and re.search(r"\|\s*:?-{3,}", lines[i + 1]):
                rows = [split_table_row(stripped)]
                i += 2
                while i < len(lines) and "|" in lines[i] and lines[i].strip():
                    rows.append(split_table_row(lines[i]))
                    i += 1
                i -= 1
                self.table(rows)
            elif match := re.match(r"^(\d+)\.\s+(.*)$", stripped):
                self.bullet(match.group(2), ordered=True, number=match.group(1))
            elif match := re.match(r"^[-*]\s+(.*)$", stripped):
                self.bullet(match.group(1))
            else:
                paragraph = [stripped]
                while i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if not nxt or nxt.startswith(("#", ">", "```", "![", "-", "*")) or re.match(r"^\d+\.\s+", nxt):
                        break
                    if "|" in nxt and i + 2 < len(lines) and re.search(r"\|\s*:?-{3,}", lines[i + 2]):
                        break
                    i += 1
                    paragraph.append(nxt)
                self.paragraph(" ".join(paragraph))
            i += 1

        self.pages.append(self.page)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        first, *rest = self.pages
        first.save(self.output_path, "PDF", resolution=150.0, save_all=True, append_images=rest)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Markdown to an image-only PDF.")
    parser.add_argument("input", nargs="?", default="doc/presentations/defense_presentation.md")
    parser.add_argument("output", nargs="?", default="doc/defense_presentation.pdf")
    parser.add_argument("--font-scale", type=float, default=1.0)
    args = parser.parse_args()

    renderer = Renderer(Path(args.input), Path(args.output), args.font_scale)
    renderer.render()
    print(f"Rendered {args.output} ({len(renderer.pages)} pages)")


if __name__ == "__main__":
    main()
