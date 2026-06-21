from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_ml_package_scaffold.py"
LINT_SCRIPT = ROOT / "scripts" / "backlog_registry_lint.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_registry_item_has_required_lint_fields() -> None:
    module = _load_module(SCRIPT, "generate_ml_package_scaffold")
    item = module.build_registry_item(
        "ml-synthetic-package",
        "Measure a synthetic ML package before implementation.",
        created="2026-05-12",
    )
    assert item["id"] == "ml-synthetic-package"
    assert item["status"] == "proposed"
    assert item["impact"] == "eval"
    assert item["created"] == "2026-05-12"
    assert item["last_review"] == "2026-05-12"


def test_generated_item_is_registry_lint_clean() -> None:
    scaffold = _load_module(SCRIPT, "generate_ml_package_scaffold")
    lint = _load_module(LINT_SCRIPT, "backlog_registry_lint_for_scaffold_test")
    item = scaffold.build_registry_item(
        "ml-synthetic-package",
        "Measure a synthetic ML package before implementation.",
        created="2026-05-12",
    )
    errors, _warnings = lint.lint({"schema_version": 2, "items": [item]})
    assert errors == []


def test_cli_prints_yaml_stanza(capsys) -> None:
    module = _load_module(SCRIPT, "generate_ml_package_scaffold")
    rc = module.main(
        [
            "--package-id",
            "ml-synthetic-package",
            "--goal",
            "Measure a synthetic ML package before implementation.",
            "--created",
            "2026-05-12",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "id: ml-synthetic-package" in out
    assert "status: proposed" in out
