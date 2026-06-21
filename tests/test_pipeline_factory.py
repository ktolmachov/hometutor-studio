import app.config as config
import app.pipeline_factory as pipeline_factory
from app.config import RetrievalSettings
from app.models import PipelineOverrides, QueryOptions


def test_resolve_pipeline_params_uses_fast_profile():
    """Профиль fast берётся из переданного retrieval_settings (без подмены env)."""
    retrieval = RetrievalSettings(rag_profile="fast", retrieval_mode="vector_only")
    params = pipeline_factory.resolve_pipeline_params(retrieval_settings=retrieval)

    assert params["profile"] == "fast"
    assert params["similarity_top_k"] <= 4
    assert params["enable_reranker"] is False
    assert params["retrieval_mode"] == "vector_only"


def test_resolve_pipeline_params_includes_retrieval_mode():
    retrieval = RetrievalSettings(rag_profile="quality", retrieval_mode="hybrid")
    params = pipeline_factory.resolve_pipeline_params(retrieval_settings=retrieval)

    assert params["retrieval_mode"] == "hybrid"


def test_resolve_pipeline_params_applies_overrides():
    """Overrides применяются поверх retrieval_settings."""
    retrieval = RetrievalSettings(rag_profile="quality")
    params = pipeline_factory.resolve_pipeline_params(
        overrides=PipelineOverrides(
            similarity_top_k=2,
            enable_reranker=False,
            split_strategy="sentence_splitter",
        ),
        retrieval_settings=retrieval,
    )

    assert params["profile"] == "quality"
    assert params["similarity_top_k"] == 2
    assert params["enable_reranker"] is False
    assert params["split_strategy"] == "sentence_splitter"


def test_build_filters_maps_query_options():
    filters = pipeline_factory.build_filters(
        QueryOptions(
            folder="docs",
            relative_path="docs/a.md",
            topic="security",
            logical_folder="lectures/security",
            file="a.md",
        )
    )

    assert filters is not None
    # 2 старых + 3 новых фильтра
    assert len(filters.filters) == 5
    keys = [f.key for f in filters.filters]
    assert "folder_name" in keys
    assert "relative_path" in keys
    assert "topic" in keys
    assert "folder" in keys
    assert "file" in keys


def test_build_tutor_pipeline_returns_three_callables():
    pipeline = pipeline_factory.build_tutor_pipeline()
    assert len(pipeline) == 3
    assert all(callable(f) for f in pipeline)
