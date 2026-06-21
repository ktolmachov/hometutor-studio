"""Guard: app/ must not import from Factory namespaces (scripts, eval, policies, schemas)."""
import pathlib
import re


def test_app_does_not_import_factory():
    root = pathlib.Path(__file__).resolve().parents[1] / "app"
    bad = re.compile(r"^\s*(from|import)\s+(scripts|eval|policies|schemas)\b", re.M)
    offenders = [p for p in root.rglob("*.py") if bad.search(p.read_text(encoding="utf-8"))]
    assert not offenders, f"app/ must not import Factory: {offenders}"
