import ast
from pathlib import Path


def test_no_function_over_100_lines():
    tree = ast.parse(Path("app/query_service.py").read_bytes())
    oversized = [
        (node.name, node.end_lineno - node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (node.end_lineno - node.lineno) > 100
    ]
    assert oversized == []
