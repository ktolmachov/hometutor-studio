"""
Общая настройка stdout/stderr для CLI-скриптов на Windows (cp1252 по умолчанию).

Использование: в начале main() после parse_args вызвать configure_stdio_utf8();
для финального JSON в stdout — write_stdout_utf8_line (обходит TextIO, если reconfigure недоступен).
"""

from __future__ import annotations

import sys


def configure_stdio_utf8() -> None:
    """Перевести stdout/stderr в UTF-8 где возможно (Python 3.7+ TextIOWrapper.reconfigure)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def write_stdout_utf8_line(text: str) -> None:
    """
    Одна строка UTF-8 в stdout (обычно JSON с ensure_ascii=False).

    Сначала пишем в binary buffer — не зависит от кодировки TextIO и от подмены builtins.print
    в app/__init__.py. Запасной путь — print после configure_stdio_utf8().
    """
    data = text.encode("utf-8", errors="replace") + b"\n"
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        buf.write(data)
        buf.flush()
        return
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))
