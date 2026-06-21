"""Check PDF quality: pages, dimensions, metadata, and embedded fonts."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


def check_pdf(pdf_path: Path) -> None:
    reader = PdfReader(str(pdf_path))
    print(f"\nAnalyzing: {pdf_path.name}")
    print("=" * 60)

    print("\nBasic info:")
    print(f"  Pages: {len(reader.pages)}")
    print(f"  Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

    if reader.metadata:
        print("\nMetadata:")
        for key, value in reader.metadata.items():
            if value:
                print(f"  {key}: {value}")

    font_counter: Counter[tuple[str, str]] = Counter()
    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for font in fonts.values():
            font_obj = font.get_object()
            subtype = str(font_obj.get("/Subtype", "Unknown"))
            base_font = str(font_obj.get("/BaseFont", "Unknown"))
            font_counter[(subtype, base_font)] += 1

    print("\nFont analysis:")
    if not font_counter:
        print("  No fonts found in resources")
    else:
        for (subtype, base_font), count in font_counter.most_common():
            status = "OK" if subtype in {"/Type0", "/Type1"} else "WARN"
            print(f"  [{status}] {count}x {subtype} - {base_font}")

    page = reader.pages[0]
    media_box = page.mediabox
    width = float(media_box.width)
    height = float(media_box.height)
    aspect_ratio = width / height
    print("\nPage dimensions:")
    print(f"  Width: {width:.2f} pt ({width / 72:.2f} in)")
    print(f"  Height: {height:.2f} pt ({height / 72:.2f} in)")
    print(f"  Aspect ratio: {aspect_ratio:.2f}:1")
    if 1.76 <= aspect_ratio <= 1.79:
        print("  OK 16:9 presentation format")
    else:
        print("  WARN non-16:9 aspect ratio")

    print("\n" + "=" * 60)
    print("Analysis complete\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check PDF quality")
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"File not found: {args.pdf}")

    check_pdf(args.pdf)


if __name__ == "__main__":
    main()
