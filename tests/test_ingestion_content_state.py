"""Tests for content hashing and partial reindex planning."""


class _Doc:
    __slots__ = ("text", "metadata")

    def __init__(self, text: str, metadata: dict) -> None:
        self.text = text
        self.metadata = metadata


from app.ingestion_content_state import (
    build_file_manifest,
    can_skip_ingest_without_parsing,
    copy_chroma_vectors_by_doc_ids,
    compute_doc_content_hashes,
    compute_retrieval_fingerprint,
    fetch_merge_metadata_for_doc_ids,
    file_manifest_matches,
    plan_partial_reindex,
)


class _FakeTargetCollection:
    def __init__(self) -> None:
        self.added: list[dict] = []

    def add(self, **kwargs) -> None:
        self.added.append(kwargs)


class _FakeSourceCollection:
    def count(self) -> int:
        return 2

    def get(self, **kwargs):
        if "where" in kwargs:
            return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}
        return {
            "ids": ["node-a", "node-b"],
            "embeddings": [[0.1], [0.2]],
            "documents": ["A", "B"],
            "metadatas": [
                {
                    "doc_id": "uuid-a",
                    "relative_path": "course/a.md",
                    "_node_content": '{"metadata":{"doc_id":"course/a.md"}}',
                },
                {
                    "doc_id": "uuid-b",
                    "relative_path": "course/b.md",
                    "_node_content": '{"metadata":{"doc_id":"course/b.md"}}',
                },
            ],
        }


class _FakeClient:
    def __init__(self, source) -> None:
        self.source = source

    def get_collection(self, _name):
        return self.source


def test_copy_chroma_vectors_falls_back_to_llamaindex_node_metadata():
    target = _FakeTargetCollection()
    copied, covered = copy_chroma_vectors_by_doc_ids(
        _FakeClient(_FakeSourceCollection()),
        "active",
        target,
        {"course/b.md"},
    )

    assert copied == 1
    assert covered == {"course/b.md"}
    assert target.added[0]["ids"] == ["node-b"]


class _FakeMixedSourceCollection:
    """Doc a is filterable via top-level relative_path; doc b lives only in _node_content."""

    def count(self) -> int:
        return 2

    def get(self, **kwargs):
        if "where" in kwargs:
            return {
                "ids": ["node-a"],
                "embeddings": [[0.1]],
                "documents": ["A"],
                "metadatas": [{"doc_id": "uuid-a", "relative_path": "course/a.md"}],
            }
        return {
            "ids": ["node-a", "node-b"],
            "embeddings": [[0.1], [0.2]],
            "documents": ["A", "B"],
            "metadatas": [
                {"doc_id": "uuid-a", "relative_path": "course/a.md"},
                {
                    "doc_id": "uuid-b",
                    "_node_content": '{"metadata":{"relative_path":"course/b.md"}}',
                },
            ],
        }


def test_copy_chroma_vectors_scans_for_docs_missed_by_where_filter():
    target = _FakeTargetCollection()
    copied, covered = copy_chroma_vectors_by_doc_ids(
        _FakeClient(_FakeMixedSourceCollection()),
        "active",
        target,
        {"course/a.md", "course/b.md"},
    )

    assert copied == 2
    assert covered == {"course/a.md", "course/b.md"}
    all_ids = [i for call in target.added for i in call["ids"]]
    assert sorted(all_ids) == ["node-a", "node-b"]


class _FakeMergeMetaCollection:
    """Merge metadata reachable only through the _node_content payload."""

    def count(self) -> int:
        return 1

    def get(self, **kwargs):
        if "where" in kwargs:
            return {"ids": [], "metadatas": []}
        return {
            "ids": ["node-b"],
            "metadatas": [
                {
                    "doc_id": "uuid-b",
                    "_node_content": (
                        '{"metadata":{"relative_path":"course/b.md",'
                        '"topic":"Agents","concepts":"planning"}}'
                    ),
                }
            ],
        }


def test_fetch_merge_metadata_falls_back_to_llamaindex_node_metadata():
    out = fetch_merge_metadata_for_doc_ids(
        _FakeClient(_FakeMergeMetaCollection()),
        "active",
        {"course/b.md"},
    )

    assert out == {"course/b.md": {"topic": "Agents", "concepts": "planning"}}


def test_compute_doc_content_hashes_stable_per_doc_id():
    docs = [
        _Doc(
            text="First section",
            metadata={"doc_id": "a/b.md", "section_path": "Intro", "section_title": "Intro"},
        ),
        _Doc(
            text="Second",
            metadata={"doc_id": "a/b.md", "section_path": "Body", "section_title": "Body"},
        ),
    ]
    h1 = compute_doc_content_hashes(docs)
    # Same texts, different section order in list should still sort by section_path
    docs2 = list(reversed(docs))
    h2 = compute_doc_content_hashes(docs2)
    assert h1 == h2
    assert h1["a/b.md"] == h2["a/b.md"]


def test_plan_partial_reindex_requires_stored_match():
    current = {"x.md": "aaa", "y.md": "bbb"}
    stored = {
        "schema_version": 1,
        "embed_model": "text-embedding-3-small",
        "retrieval_fingerprint": "fp",
        "hashes": {"x.md": "aaa", "y.md": "bbb"},
    }
    use, _, dirty = plan_partial_reindex(
        reset=False,
        build_to_staging=True,
        enable_partial_reindex=True,
        embed_model="text-embedding-3-small",
        retrieval_fingerprint="fp",
        current_hashes=current,
        stored=stored,
    )
    assert use is True
    assert dirty == set()

    use2, _, dirty2 = plan_partial_reindex(
        reset=False,
        build_to_staging=True,
        enable_partial_reindex=True,
        embed_model="text-embedding-3-small",
        retrieval_fingerprint="fp",
        current_hashes={"x.md": "changed", "y.md": "bbb"},
        stored=stored,
    )
    assert use2 is True
    assert dirty2 == {"x.md"}


def test_plan_partial_disabled_or_reset():
    current = {"x.md": "a"}
    stored = {
        "schema_version": 1,
        "embed_model": "m",
        "retrieval_fingerprint": "fp",
        "hashes": {"x.md": "a"},
    }
    use, _, dirty = plan_partial_reindex(
        reset=True,
        build_to_staging=True,
        enable_partial_reindex=True,
        embed_model="m",
        retrieval_fingerprint="fp",
        current_hashes=current,
        stored=stored,
    )
    assert use is False
    assert dirty == {"x.md"}

    use2, _, _ = plan_partial_reindex(
        reset=False,
        build_to_staging=True,
        enable_partial_reindex=False,
        embed_model="m",
        retrieval_fingerprint="fp",
        current_hashes=current,
        stored=stored,
    )
    assert use2 is False


def test_compute_retrieval_fingerprint_changes_with_chunk_settings():
    a = compute_retrieval_fingerprint("sentence_window", 700, 100, 2)
    b = compute_retrieval_fingerprint("sentence_window", 701, 100, 2)
    assert a != b


def test_file_manifest_and_noop_candidate(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.md").write_text("hello", encoding="utf-8")
    (data / "ignore.bin").write_text("x", encoding="utf-8")

    manifest = build_file_manifest(data, frozenset({".md"}))
    assert sorted(manifest["files"]) == ["a.md"]
    assert file_manifest_matches(manifest, manifest)

    stored = {
        "schema_version": 1,
        "embed_model": "m",
        "retrieval_fingerprint": "fp",
        "hashes": {"a.md": "hash"},
        "file_manifest": manifest,
    }
    assert can_skip_ingest_without_parsing(
        reset=False,
        build_to_staging=True,
        enable_partial_reindex=True,
        embed_model="m",
        retrieval_fingerprint="fp",
        current_file_manifest=manifest,
        stored=stored,
    )
    assert not can_skip_ingest_without_parsing(
        reset=True,
        build_to_staging=True,
        enable_partial_reindex=True,
        embed_model="m",
        retrieval_fingerprint="fp",
        current_file_manifest=manifest,
        stored=stored,
    )
