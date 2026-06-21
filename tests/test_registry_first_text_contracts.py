from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_live_workflow_texts_do_not_promote_tasklist_as_source_of_truth():
    texts = {
        ".cursor/rules/workflow.mdc": _read(".cursor/rules/workflow.mdc"),
        "doc/current_task.md": _read("doc/current_task.md"),
        "doc/team_workflow/archive/zero_click_delivery_analysis.md": _read(
            "doc/team_workflow/archive/zero_click_delivery_analysis.md"
        ),
        "scripts/start_workflow.py": _read("scripts/start_workflow.py"),
    }

    forbidden = [
        "\u00a7Now empty",
        "\u00a7Now is empty",
        "tasklist.md \u00a7Now",
        "tasklist.md" + " not found",
        "\u043a\u0440\u0438\u0442\u0435\u0440\u0438\u0438 \u0438\u0437 tasklist",
        "DoD \u0438\u0437 tasklist",
        "\u041e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435 \u00a7Now",
        "\u0424\u043e\u0440\u043c\u0430\u0442 \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u0430 \u0432 \u00a7Now",
    ]
    for path, text in texts.items():
        for phrase in forbidden:
            assert phrase not in text, f"{path} still contains stale phrase: {phrase}"


def test_tasklist_now_section_declares_generated_deprecated_view():
    tasklist = _read("doc/tasklist.md")

    assert "Deprecated display" in tasklist
    assert "doc/backlog_registry.yaml" in tasklist
