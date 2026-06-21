import ast
from pathlib import Path


def test_adaptive_plan_card_stays_facade_sized() -> None:
    path = Path("app/ui/adaptive_plan_card.py")
    assert len(path.read_text(encoding="utf-8").splitlines()) <= 1000


def test_adaptive_plan_card_function_lengths_are_bounded() -> None:
    path = Path("app/ui/adaptive_plan_card.py")
    tree = ast.parse(path.read_bytes())
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            size = (node.end_lineno or node.lineno) - node.lineno + 1
            if size > 120:
                offenders.append((node.name, size))
    assert offenders == []
