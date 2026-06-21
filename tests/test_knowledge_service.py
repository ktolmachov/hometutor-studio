from app.knowledge_service import (
    build_learning_plan,
    compute_source_coverage,
    get_kb_overview,
    get_proactive_suggestions,
    get_topics_catalog,
    search_knowledge_base,
    synthesize_topic,
)
from app.api_models import LearningPlanResponse


class _FakeSummaryCollection:
    def get(self, include=None):
        return {
            "ids": ["s1", "s2", "s3"],
            "documents": [
                "Intro to retrieval and ranking.",
                "Hybrid search and BM25 tradeoffs.",
                "Prompting and generation patterns.",
            ],
            "metadatas": [
                {
                    "doc_id": "doc-1",
                    "relative_path": "lectures/retrieval_intro.md",
                    "file_name": "retrieval_intro.md",
                    "folder_name": "lectures",
                    "topic": "Retrieval",
                    "key_concepts": "retrieval, ranking, recall",
                    "doc_type": "lecture",
                    "difficulty": "beginner",
                },
                {
                    "doc_id": "doc-2",
                    "relative_path": "lectures/hybrid_search.md",
                    "file_name": "hybrid_search.md",
                    "folder_name": "lectures",
                    "topic": "Retrieval",
                    "key_concepts": "hybrid search, bm25, retrieval",
                    "doc_type": "lecture",
                    "difficulty": "intermediate",
                },
                {
                    "doc_id": "doc-3",
                    "relative_path": "lectures/prompting.md",
                    "file_name": "prompting.md",
                    "folder_name": "lectures",
                    "topic": "Prompting",
                    "key_concepts": "prompting, synthesis",
                    "doc_type": "lecture",
                    "difficulty": "beginner",
                },
            ],
            "embeddings": [
                [1.0, 0.0],
                [0.95, 0.05],
                [0.0, 1.0],
            ],
        }


class _FakeChunkCollection:
    def get(self, include=None):
        return {
            "documents": [
                "Course logistics and grading overview.",
                "Ranking improves precision.",
                "Hybrid search combines sparse and dense signals.",
                "Prompting controls output shape.",
                "Retrieval finds relevant chunks and improves recall.",
            ],
            "metadatas": [
                {"relative_path": "lectures/retrieval_intro.md", "file_name": "retrieval_intro.md", "folder_name": "lectures"},
                {"relative_path": "lectures/retrieval_intro.md", "file_name": "retrieval_intro.md", "folder_name": "lectures"},
                {"relative_path": "lectures/hybrid_search.md", "file_name": "hybrid_search.md", "folder_name": "lectures"},
                {"relative_path": "lectures/prompting.md", "file_name": "prompting.md", "folder_name": "lectures"},
                {"relative_path": "lectures/retrieval_intro.md", "file_name": "retrieval_intro.md", "folder_name": "lectures"},
            ]
        }


class _EmptySummaryCollection:
    def get(self, include=None, ids=None):
        return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}


class _CourseChunkCollection:
    def get(self, include=None):
        return {
            "documents": [
                "Агент получает цель, планирует шаги и вызывает инструменты.",
                "Цикл агента включает наблюдение, размышление, действие и проверку результата.",
            ],
            "metadatas": [
                {
                    "relative_path": "ИИ Агенты/Введение в концепцию агентовts.txt",
                    "file_name": "Введение в концепцию агентовts.txt",
                    "folder_name": "ИИ Агенты",
                },
                {
                    "relative_path": "ИИ Агенты/урок 2 Как агент думает и дейс.txt",
                    "file_name": "урок 2 Как агент думает и дейс.txt",
                    "folder_name": "ИИ Агенты",
                },
            ],
        }


class _FakeLLM:
    def complete(self, prompt):
        return type("Response", (), {"text": "Structured synthesis result"})()


def _services():
    return {
        "summary_collection": _FakeSummaryCollection(),
        "collection": _FakeChunkCollection(),
        "llm": _FakeLLM(),
    }


def _course_services_without_summary_catalog():
    return {
        "summary_collection": _EmptySummaryCollection(),
        "collection": _CourseChunkCollection(),
        "llm": _FakeLLM(),
    }


def test_get_topics_catalog_groups_documents_by_topic():
    result = get_topics_catalog(services=_services())

    assert result["total_topics"] == 2
    assert result["total_documents"] == 3
    assert result["topics"][0]["topic_name"] == "Retrieval"
    assert result["topics"][0]["document_count"] == 2
    assert "retrieval" in [item.lower() for item in result["topics"][0]["key_concepts"]]


def test_synthesize_topic_uses_topic_documents_and_chunks():
    result = synthesize_topic(topic="Retrieval", services=_services())

    assert result["topic"] == "Retrieval"
    assert result["summary"] == "Structured synthesis result"
    assert len(result["documents"]) == 2
    assert len(result["sections"]) == 2
    assert any(item["relative_path"] == "lectures/retrieval_intro.md" for item in result["sources"])
    assert "coverage" in result
    assert result["coverage"]["covered"] == 2


def test_synthesize_topic_prefers_more_relevant_chunks_over_first_seen():
    result = synthesize_topic(topic="Retrieval", services=_services())
    retrieval_section = next(item for item in result["sections"] if item["relative_path"] == "lectures/retrieval_intro.md")

    assert any("Retrieval finds relevant chunks" in chunk for chunk in retrieval_section["chunks"])
    assert not all("Course logistics and grading overview." == chunk for chunk in retrieval_section["chunks"])


def test_build_learning_plan_returns_plan_and_missing_topics():
    result = build_learning_plan(
        topic="Retrieval",
        goal="Подготовиться к домашнему заданию",
        level="beginner",
        time_budget_hours=4,
        known_topics=["ranking"],
        services=_services(),
    )

    assert result["topic"] == "Retrieval"
    assert result["goal"] == "Подготовиться к домашнему заданию"
    assert result["level"] == "beginner"
    assert result["time_budget_hours"] == 4
    assert result["plan"] == "Structured synthesis result"
    assert len(result["documents"]) == 2
    assert "coverage" in result
    assert "retrieval" in [item.lower() for item in result["missing_topics"]]


def test_build_learning_plan_document_fallback_satisfies_response_contract():
    docs = [
        "ИИ Агенты/Введение в концепцию агентовts.txt",
        "ИИ Агенты/урок 2 Как агент думает и дейс.txt",
    ]

    result = build_learning_plan(
        topic="Курс: ИИ Агенты",
        documents=docs,
        goal="Изучить курс",
        level="beginner",
        services=_course_services_without_summary_catalog(),
    )

    assert result["topic"] == "Курс: ИИ Агенты"
    assert [doc["relative_path"] for doc in result["documents"]] == docs
    assert [doc["doc_id"] for doc in result["documents"]] == docs
    assert result["documents"][0]["file_name"] == "Введение в концепцию агентовts.txt"
    assert result["documents"][0]["folder_name"] == "ИИ Агенты"
    assert result["documents"][0]["doc_type"] == "txt"
    assert LearningPlanResponse.model_validate(result).documents[0].doc_id == docs[0]


def test_build_learning_plan_user_progress_adds_dynamic_plan():
    result = build_learning_plan(
        topic="Retrieval",
        goal="Подготовиться к домашнему заданию",
        level="beginner",
        time_budget_hours=4,
        user_progress=True,
        services=_services(),
    )
    assert "dynamic_plan" in result
    dp = result["dynamic_plan"]
    assert dp["enabled"] is True
    assert "mastery_percentage" in dp


def test_synthesize_topic_raises_for_unknown_topic():
    try:
        synthesize_topic(topic="Missing", services=_services())
    except ValueError as exc:
        assert "Unknown topic" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown topic")


def test_compute_source_coverage_full():
    coverage = compute_source_coverage(
        source_paths=["lectures/retrieval_intro.md", "lectures/hybrid_search.md"],
        services=_services(),
    )
    assert coverage["covered"] == 2
    assert coverage["total"] == 2
    assert coverage["ratio"] == 1.0
    assert coverage["label"] == "Высокое покрытие"
    assert coverage["missing"] == []


def test_compute_source_coverage_partial():
    coverage = compute_source_coverage(
        source_paths=["lectures/retrieval_intro.md"],
        services=_services(),
    )
    assert coverage["covered"] == 1
    assert coverage["total"] == 2
    assert coverage["ratio"] == 0.5
    assert coverage["label"] == "Среднее покрытие"
    assert "lectures/hybrid_search.md" in coverage["missing"]


def test_compute_source_coverage_empty():
    coverage = compute_source_coverage(source_paths=[], services=_services())
    assert coverage["covered"] == 0
    assert coverage["label"] == "Нет источников"


def test_get_kb_overview():
    overview = get_kb_overview(services=_services())
    assert overview["total_topics"] == 2
    assert overview["total_documents"] == 3
    assert len(overview["top_concepts"]) > 0
    assert len(overview["topic_sizes"]) == 2


def test_get_proactive_suggestions():
    suggestions = get_proactive_suggestions(
        source_paths=["lectures/retrieval_intro.md"],
        services=_services(),
    )
    assert len(suggestions["related_topics"]) > 0
    assert suggestions["related_topics"][0]["topic_name"] == "Retrieval"
    assert suggestions["related_topics"][0]["unexplored_count"] == 1
    assert "lectures/hybrid_search.md" in suggestions["unexplored_documents"]


def test_search_knowledge_base_by_topic():
    results = search_knowledge_base("Retrieval", services=_services())
    assert len(results["topics"]) >= 1
    assert results["topics"][0]["topic_name"] == "Retrieval"


def test_search_knowledge_base_by_document():
    results = search_knowledge_base("hybrid", services=_services())
    assert len(results["documents"]) >= 1


def test_search_knowledge_base_by_concept():
    results = search_knowledge_base("bm25", services=_services())
    assert len(results["concepts"]) >= 1


def test_search_knowledge_base_empty():
    results = search_knowledge_base("", services=_services())
    assert results["topics"] == []
    assert results["documents"] == []
    assert results["concepts"] == []
