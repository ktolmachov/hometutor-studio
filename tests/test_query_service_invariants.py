import ast

from tests.studio_layout import product_app_path


def test_no_function_over_100_lines():
    tree = ast.parse(product_app_path("query_service.py").read_bytes())
    oversized = [
        (node.name, node.end_lineno - node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (node.end_lineno - node.lineno) > 100
    ]
    assert oversized == []
