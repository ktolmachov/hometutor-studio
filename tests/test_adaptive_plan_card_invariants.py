import ast

from tests.studio_layout import product_app_path


def test_adaptive_plan_card_stays_facade_sized() -> None:
    path = product_app_path("ui", "adaptive_plan_card.py")
    assert len(path.read_text(encoding="utf-8").splitlines()) <= 1000


def test_adaptive_plan_card_function_lengths_are_bounded() -> None:
    path = product_app_path("ui", "adaptive_plan_card.py")
    tree = ast.parse(path.read_bytes())
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            size = (node.end_lineno or node.lineno) - node.lineno + 1
            if size > 120:
                offenders.append((node.name, size))
    assert offenders == []
