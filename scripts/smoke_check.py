#!/usr/bin/env python3
"""
Smoke-check после setup: быстрая проверка, что окружение и тесты работают.
Запуск: python scripts/smoke_check.py
Из корня репозитория (или с путём к корню в PYTHONPATH).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_config.py",
            "tests/test_guardrails.py",
            "tests/test_index_backup.py",
            "-q",
            "--tb=short",
        ],
        cwd=ROOT,
    )
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
