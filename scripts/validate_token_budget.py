#!/usr/bin/env python3
"""
Interactive token budget validator for Claude Code sessions.
Runs check_readset.py and formats warnings + recommendations to console.
"""

import subprocess
import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_utils import budget_profile_choices, get_budget_profile  # noqa: E402

def run_validator(files: list, *, budget_profile: str) -> int:
    """Run check_readset.py and return exit code."""
    cmd = [sys.executable, "scripts/check_readset.py", "--profile", budget_profile] + files
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    except FileNotFoundError:
        print("❌ check_readset.py не найден. Убедитесь что вы в корне проекта.")
        return 2

def get_files_from_user() -> list:
    """Ask user for read-set files interactively."""
    print("\n" + "="*60)
    print("🔍 ВАЛИДАЦИЯ БЮДЖЕТА ТОКЕНОВ")
    print("="*60)
    print("\nВыпишите файлы вашего read-set (по одному на строку).")
    print("Оставьте пустую строку для завершения.\n")

    files = []
    count = 1
    while True:
        try:
            f = input(f"Файл {count}: ").strip()
            if not f:
                if not files:
                    print("❌ Нужно указать хотя бы один файл.")
                    continue
                break
            files.append(f)
            count += 1
        except KeyboardInterrupt:
            print("\n⚠️ Отмена. Отправка промпта запрещена.")
            sys.exit(1)

    return files

def print_warning_safe(code: int):
    """Print warning for SAFE exit code (0)."""
    print("\n" + "="*60)
    print("✅ SAFE — Бюджет в норме")
    print("="*60)
    print("Входные токены < 12k. Отправляйте промпт смело.\n")

def print_warning_warn(code: int):
    """Print warning for WARN exit code (1)."""
    print("\n" + "="*60)
    print("⚠️ WARN — Мягкое превышение")
    print("="*60)
    print("Входные токены между 12k и 20k (soft-limit превышен).")
    print("\n📝 Рекомендации по сжатию:")
    print("  1) Убрать 1–2 файла с наименьшей информацией")
    print("  2) Заменить полное чтение на grep/signatures")
    print("  3) Читать только нужную секцию файла")
    print("  4) Сжать историю (убрать старые результаты)")
    print("\n🔧 Команда с рекомендациями:")
    print("  python scripts/check_readset.py <файлы> --signatures\n")
    print("⛔ Не отправляйте так, сжимайте read-set!\n")

def print_warning_block(code: int):
    """Print warning for BLOCK exit code (2)."""
    print("\n" + "="*60)
    print("🔴 BLOCK — Критическое превышение")
    print("="*60)
    print("Входные токены > 20k (hard-limit) ИЛИ запрещённые файлы.")
    print("\n📋 Действия:")
    print("  1) Запустите с флагом --signatures:")
    print("     python scripts/check_readset.py <файлы> --signatures")
    print("\n  2) Проверьте таблицу запрещённых файлов:")
    print("     doc/token_safety.md или doc/TOKEN_OPTIMIZATION_CARD.md")
    print("\n  3) Используйте safe-метод для больших файлов:")
    print("     grep \"^class\\|^def \" app/query_service.py")
    print("     grep \"def test_\" tests/test_api.py")
    print("\n  4) Переделайте read-set (макс 3–5 файлов)")
    print("  5) Повторите валидацию\n")
    print("⛔ ЗАПРЕЩЕНО отправлять prompts с exit code 2!\n")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Interactive token budget validator")
    parser.add_argument(
        "--budget-profile",
        choices=budget_profile_choices(),
        default="strict",
        help="Budget profile passed through to check_readset.py (default: strict)",
    )
    args = parser.parse_args()
    budget_profile = get_budget_profile(args.budget_profile)
    files = get_files_from_user()

    print("\n🔄 Запуск check_readset.py...\n")
    print(f"Активный профиль бюджета: {budget_profile['name']}")
    code = run_validator(files, budget_profile=str(budget_profile["name"]))

    print()
    if code == 0:
        print_warning_safe(code)
    elif code == 1:
        print_warning_warn(code)
    elif code == 2:
        print_warning_block(code)
        sys.exit(1)  # Block submission

if __name__ == "__main__":
    main()
