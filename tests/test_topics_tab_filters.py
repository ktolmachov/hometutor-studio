from app.ui.topics_tab_filters import filter_topics_by_active_scope


def test_filter_topics_by_active_scope_keeps_only_course_documents() -> None:
    topics = [
        {
            "topic_id": "agents",
            "topic_name": "Agents",
            "document_count": 2,
            "documents": [
                {"relative_path": "ИИ Агенты/intro.md", "summary": "course"},
                {
                    "relative_path": "doc/team_workflow/generate_audit_closed_packages_prompt.md",
                    "summary": "workflow prompt",
                },
            ],
        },
        {
            "topic_id": "workflow",
            "topic_name": "Workflow",
            "document_count": 1,
            "documents": [
                {
                    "relative_path": "doc/team_workflow/generate_audit_closed_packages_prompt.md",
                    "summary": "workflow prompt",
                }
            ],
        },
    ]
    scope = {
        "folder_rel": "ИИ Агенты",
        "source_paths": ["ИИ Агенты/intro.md"],
        "active": True,
    }

    filtered = filter_topics_by_active_scope(topics, scope)

    assert [topic["topic_id"] for topic in filtered] == ["agents"]
    assert filtered[0]["document_count"] == 1
    assert [doc["relative_path"] for doc in filtered[0]["documents"]] == ["ИИ Агенты/intro.md"]
    assert topics[0]["document_count"] == 2


def test_filter_topics_by_active_scope_falls_back_to_folder_prefix() -> None:
    topics = [
        {
            "topic_id": "agents",
            "topic_name": "Agents",
            "document_count": 2,
            "documents": [
                {"relative_path": "ИИ Агенты\\intro.md"},
                {"relative_path": "other/intro.md"},
            ],
        },
    ]

    filtered = filter_topics_by_active_scope(topics, {"folder_rel": "ИИ Агенты", "source_paths": []})

    assert filtered[0]["document_count"] == 1
    assert filtered[0]["documents"][0]["relative_path"] == "ИИ Агенты\\intro.md"


def test_filter_topics_by_active_scope_builds_course_topic_when_catalog_has_no_course_docs() -> None:
    topics = [
        {
            "topic_id": "team-workflow-audit-closed-packages",
            "topic_name": "Team workflow: audit закрытых пакетов (monthly)",
            "document_count": 1,
            "documents": [
                {"relative_path": "doc/team_workflow/generate_audit_closed_packages_prompt.md"}
            ],
        }
    ]
    scope = {
        "id": "abc123",
        "folder_rel": "ИИ Агенты",
        "title": "Курс: ИИ Агенты",
        "source_paths": [
            "ИИ Агенты/Введение в концепцию агентовts.txt",
            "ИИ Агенты/урок 2 Как агент думает и дейс.txt",
        ],
        "active": True,
    }

    filtered = filter_topics_by_active_scope(topics, scope)

    assert [topic["topic_id"] for topic in filtered] == ["course_abc123"]
    assert filtered[0]["topic_name"] == "Курс: ИИ Агенты"
    assert filtered[0]["document_count"] == 2
    assert [doc["relative_path"] for doc in filtered[0]["documents"]] == scope["source_paths"]


def test_filter_topics_by_active_scope_passthrough_without_scope() -> None:
    topics = [{"topic_id": "x", "documents": []}]

    assert filter_topics_by_active_scope(topics, None) == topics


def test_filter_topics_by_active_scope_cyrillic_folder_prefix() -> None:
    topics = [
        {
            "topic_id": "t1",
            "document_count": 2,
            "documents": [
                {"relative_path": "ИИ Агенты/лек1.md"},
                {"relative_path": "Python/func.md"},
            ],
        },
    ]
    scope = {"folder_rel": "ИИ Агенты", "source_paths": [], "active": True}
    filtered = filter_topics_by_active_scope(topics, scope)
    assert [t["topic_id"] for t in filtered] == ["t1"]
    assert filtered[0]["document_count"] == 1
    assert filtered[0]["documents"][0]["relative_path"] == "ИИ Агенты/лек1.md"


def test_filter_topics_empty_docs_after_scope_drops_topic() -> None:
    topics = [
        {"topic_id": "t1", "document_count": 1, "documents": [{"relative_path": "other/doc.md"}]},
    ]
    scope = {"folder_rel": "ИИ Агенты", "source_paths": [], "active": True}
    assert filter_topics_by_active_scope(topics, scope) == []


def test_folder_source_paths_from_index_extracts_correctly() -> None:
    from app.ui.topics_tab_right_column import _folder_source_paths_from_index

    index_stats = {
        "files": [
            "ИИ Агенты/лек1.md",
            "ИИ Агенты/лек2.pdf",
            "Python/basics.md",
            "ИИ Агенты",
        ]
    }
    result = _folder_source_paths_from_index("ИИ Агенты", index_stats)
    assert sorted(result) == sorted(["ИИ Агенты/лек1.md", "ИИ Агенты/лек2.pdf", "ИИ Агенты"])


def test_folder_source_paths_from_index_returns_empty_without_stats() -> None:
    from app.ui.topics_tab_right_column import _folder_source_paths_from_index

    assert _folder_source_paths_from_index("ml", None) == []
    assert _folder_source_paths_from_index("", {"files": ["ml/doc.md"]}) == []
