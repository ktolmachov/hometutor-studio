#!/usr/bin/env python3
"""Экспорт ключевых слайдов презентации лекции в PNG-файлы assets/ курса.

Зачем: cloud-промпт умного конспекта (`## 🖼 Визуальная выжимка`) может
вставлять реальные изображения слайдов только если они существуют как файлы.
Скрипт рендерит выбранные страницы PDF-презентации из папки лекции
(``materials/<курс>/<лекция>/``) в папку курса с умными конспектами:
``data/<курс>/assets/<префикс>_slide_NN.png`` — так относительные ссылки
``assets/...`` работают прямо из конспекта.

Usage:
    python scripts/export_slide_assets.py "ИИ Агенты/урок 4" --course "ИИ Агенты" --slides 3,7,17-19
    python scripts/export_slide_assets.py "ИИ Агенты/урок 4" --course "ИИ Агенты" --from-konspekt "data/ИИ Агенты/Урок_4_конспект.md"
    python scripts/export_slide_assets.py "D:/path/урок 4" --course "D:/path/data/ИИ Агенты" --slides 3 --dpi 200 --force

Относительный путь лекции разрешается от ``<repo>/materials``,
относительное имя курса — от ``<repo>/data``.
Номера слайдов — это номера страниц PDF (1-based), поддерживаются диапазоны.
Префикс по умолчанию — имя папки лекции (пробелы заменяются на ``_``).

``--from-konspekt`` вычитывает номера слайдов из готового конспекта:
заголовки ``### Слайд N`` в разделе визуальной выжимки и ссылки вида
``assets/<префикс>_slide_NN.png``. Удобно, когда конспект уже сгенерирован
с visual brief, и осталось доложить реальные картинки по тем же путям.

Exit codes:
    0 = OK (все запрошенные слайды экспортированы или уже существуют)
    1 = ошибка входных данных (нет папки/PDF, кривой список слайдов)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover - окружение без optional-зависимости
    pymupdf = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
MATERIALS_ROOT = REPO_ROOT / "materials"
DATA_ROOT = REPO_ROOT / "data"

# ### Слайд 26: ... / ### Слайд 12 (стр. 12–14): ... / ### Слайды 8–12: ...
KONSPEKT_SLIDE_HEADING_RE = re.compile(
    r"^###\s+Слайд(?:ы)?\s+(\d+)(?:\s*[–—-]\s*(\d+))?", re.MULTILINE
)
# ![...](assets/урок_4_slide_26.png)
ASSET_LINK_RE = re.compile(r"\(assets/(.+?)_slide_(\d+)\.png\)")


def parse_slides_spec(spec: str, page_count: int) -> list[int]:
    """Разобрать строку вида ``3,5-7,19`` в отсортированный список страниц."""
    pages: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_s, _, end_s = token.partition("-")
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(token)
        if start > end:
            raise ValueError(f"диапазон задом наперед: {token!r}")
        if start < 1 or end > page_count:
            raise ValueError(f"{token!r} вне диапазона 1–{page_count}")
        pages.update(range(start, end + 1))
    if not pages:
        raise ValueError("список слайдов пуст")
    return sorted(pages)


def parse_konspekt_slides(text: str) -> tuple[list[int], set[str]]:
    """Извлечь из конспекта номера слайдов выжимки и префиксы asset-ссылок.

    Возвращает (отсортированные номера страниц, множество префиксов из ссылок).
    """
    pages: set[int] = set()
    prefixes: set[str] = set()
    for m in KONSPEKT_SLIDE_HEADING_RE.finditer(text):
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        if start <= end:
            pages.update(range(start, end + 1))
        else:
            pages.add(start)
    for m in ASSET_LINK_RE.finditer(text):
        prefixes.add(m.group(1))
        pages.add(int(m.group(2)))
    if not pages:
        raise ValueError(
            "в конспекте не найдено ни заголовков '### Слайд N', "
            "ни ссылок 'assets/<префикс>_slide_NN.png'; укажите --slides"
        )
    return sorted(pages), prefixes


def sanitize_prefix(raw: str) -> str:
    """Превратить имя лекции в безопасный префикс файла."""
    prefix = re.sub(r"[\s]+", "_", raw.strip())
    prefix = re.sub(r'[<>:"/\\|?*]', "", prefix).strip("._")
    if not prefix:
        raise ValueError(f"из {raw!r} не получился префикс имени файла")
    return prefix


def resolve_lecture_dir(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = MATERIALS_ROOT / path
    return path.resolve()


def resolve_course_dir(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = DATA_ROOT / path
    return path.resolve()


def find_presentation(lecture_dir: Path, pdf_name: str | None) -> Path:
    pdfs = sorted(lecture_dir.glob("*.pdf"), key=lambda p: p.name.lower())
    if pdf_name:
        target = lecture_dir / pdf_name
        if not target.is_file():
            raise FileNotFoundError(f"PDF не найден: {target}")
        return target
    if not pdfs:
        raise FileNotFoundError(f"В папке лекции нет PDF-презентаций: {lecture_dir}")
    if len(pdfs) > 1:
        names = ", ".join(p.name for p in pdfs)
        raise ValueError(f"В папке несколько PDF ({names}); укажите --pdf <имя>")
    return pdfs[0]


def export_slides(
    pdf_path: Path,
    pages: list[int],
    assets_dir: Path,
    prefix: str,
    *,
    dpi: int,
    force: bool,
) -> list[tuple[int, Path, str]]:
    """Отрендерить страницы в PNG. Возвращает (номер, путь, exported|skipped)."""
    results: list[tuple[int, Path, str]] = []
    pad = max(2, len(str(max(pages))))
    zoom = dpi / 72.0
    with pymupdf.open(pdf_path) as doc:
        for num in pages:
            out = assets_dir / f"{prefix}_slide_{num:0{pad}d}.png"
            if out.exists() and not force:
                results.append((num, out, "skipped"))
                continue
            pix = doc[num - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            assets_dir.mkdir(parents=True, exist_ok=True)
            pix.save(out)
            results.append((num, out, "exported"))
    return results


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() not in {"utf-8", "utf8"}:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    parser = argparse.ArgumentParser(
        description="Экспорт ключевых слайдов PDF-презентации лекции в data/<курс>/assets/*.png"
    )
    parser.add_argument(
        "lecture_dir",
        help="Папка лекции с PDF (абсолютный путь или относительный от materials/)",
    )
    parser.add_argument(
        "--course",
        required=True,
        help="Папка курса с умными конспектами (абсолютный путь или имя относительно data/)",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--slides",
        help="Номера страниц PDF, например: 3,7,8,17-19,26",
    )
    source.add_argument(
        "--from-konspekt",
        help="Путь к конспекту .md: номера слайдов берутся из визуальной выжимки и assets-ссылок",
    )
    parser.add_argument(
        "--prefix",
        help="Префикс имен файлов (default: из assets-ссылок конспекта или имя папки лекции)",
    )
    parser.add_argument("--pdf", help="Имя PDF-файла, если в папке их несколько")
    parser.add_argument("--dpi", type=int, default=150, help="Разрешение рендера (default: 150)")
    parser.add_argument("--force", action="store_true", help="Перезаписывать существующие PNG")
    args = parser.parse_args()

    if pymupdf is None:
        print("ERROR: pymupdf не установлен. Установите: pip install pymupdf", file=sys.stderr)
        return 1

    try:
        lecture_dir = resolve_lecture_dir(args.lecture_dir)
        if not lecture_dir.is_dir():
            raise FileNotFoundError(f"Папка лекции не найдена: {lecture_dir}")
        course_dir = resolve_course_dir(args.course)
        if not course_dir.is_dir():
            raise FileNotFoundError(f"Папка курса не найдена: {course_dir}")
        pdf_path = find_presentation(lecture_dir, args.pdf)
        with pymupdf.open(pdf_path) as doc:
            page_count = doc.page_count

        link_prefixes: set[str] = set()
        if args.from_konspekt:
            konspekt_path = Path(args.from_konspekt)
            if not konspekt_path.is_absolute():
                konspekt_path = (REPO_ROOT / konspekt_path).resolve()
            if not konspekt_path.is_file():
                raise FileNotFoundError(f"Конспект не найден: {konspekt_path}")
            text = konspekt_path.read_text(encoding="utf-8", errors="replace")
            pages, link_prefixes = parse_konspekt_slides(text)
            bad = [n for n in pages if n < 1 or n > page_count]
            if bad:
                raise ValueError(
                    f"в конспекте указаны слайды вне диапазона 1–{page_count}: {bad}; "
                    "проверьте карту презентации (возможно, номера выдуманы)"
                )
        else:
            pages = parse_slides_spec(args.slides, page_count)

        if args.prefix:
            prefix = sanitize_prefix(args.prefix)
        elif len(link_prefixes) == 1:
            prefix = next(iter(link_prefixes))
        else:
            prefix = sanitize_prefix(lecture_dir.name)
        if len(link_prefixes) > 1:
            print(
                f"WARNING: в конспекте разные префиксы asset-ссылок: {sorted(link_prefixes)}; "
                f"использую {prefix!r}",
                file=sys.stderr,
            )
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    assets_dir = course_dir / "assets"
    results = export_slides(pdf_path, pages, assets_dir, prefix, dpi=args.dpi, force=args.force)

    exported = sum(1 for _, _, status in results if status == "exported")
    skipped = len(results) - exported
    print(f"PDF: {pdf_path.name} ({page_count} стр.)")
    print(f"Assets: {assets_dir}")
    print(f"Экспортировано: {exported}, пропущено (уже есть): {skipped}\n")
    print("Markdown-вставки для конспекта:\n")
    for num, out, _status in results:
        print(f"![Слайд {num}](assets/{out.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
