"""Tests verifying that both vector store backends implement the common VectorStore ABC.

These tests use FAISS (real) and a mocked Qdrant client to confirm:
  - Both classes are concrete implementations of the VectorStore ABC.
  - search_similar results are ordered by descending similarity score.
  - Both backends share the same API contract (method signatures).
"""

import pytest
from datetime import datetime
from typing import List
from unittest.mock import MagicMock, patch
from abc import ABC

from src.interfaces import VectorStore
from src.vector_store import FAISSVectorStore
from src.models import TextChunk, ChunkMetadata, SearchResult


DIM = 8


def _chunk(chunk_id: str = "c1", text: str = "Some text",
           doc: str = "doc.pdf", page: int = 1) -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        text=text,
        page_number=page,
        document_name=doc,
        start_char=0,
        end_char=len(text),
    )


def _meta(chunk_id: str = "c1", doc: str = "doc.pdf",
          page: int = 1, idx: int = 0) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_id=chunk_id,
        document_name=doc,
        page_number=page,
        chunk_index=idx,
        created_at=datetime(2024, 6, 1),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def faiss_store():
    return FAISSVectorStore(dimension=DIM)


@pytest.fixture()
def qdrant_store():
    """QdrantVectorStore backed by a mocked client."""
    with patch("src.qdrant_vector_store.QdrantClient") as MockClient:
        instance = MockClient.return_value
        instance.get_collections.return_value = MagicMock(collections=[])

        from src.qdrant_vector_store import QdrantVectorStore
        store = QdrantVectorStore(dimension=DIM, collection_name="test")

        # Configure scroll to return empty by default (for get_all_document_names etc.)
        instance.scroll.return_value = ([], None)

        # Configure count to return 0 by default
        count_result = MagicMock()
        count_result.count = 0
        instance.count.return_value = count_result

        yield store


# ---------------------------------------------------------------------------
# ABC compliance
# ---------------------------------------------------------------------------

class TestVectorStoreABCCompliance:
    """Both backends must be concrete subclasses of VectorStore."""

    def test_faiss_is_subclass_of_vector_store(self):
        assert issubclass(FAISSVectorStore, VectorStore)

    def test_faiss_is_not_abstract(self):
        """FAISSVectorStore must be instantiable (all abstract methods implemented)."""
        store = FAISSVectorStore(dimension=DIM)
        assert isinstance(store, VectorStore)

    def test_qdrant_is_subclass_of_vector_store(self, qdrant_store):
        assert isinstance(qdrant_store, VectorStore)

    def test_vector_store_is_abstract(self):
        assert issubclass(VectorStore, ABC)
        with pytest.raises(TypeError):
            VectorStore()  # type: ignore[abstract]

    def test_both_have_required_methods(self, faiss_store, qdrant_store):
        required_methods = [
            "add_embeddings",
            "add_chunks_with_embeddings",
            "search_similar",
            "save_index",
            "load_index",
            "get_document_count",
            "get_chunk_count",
            "clear",
            "get_all_document_names",
            "delete_document_by_name",
            "document_exists",
            "get_document_info",
        ]
        for method in required_methods:
            assert hasattr(faiss_store, method), f"FAISSVectorStore missing: {method}"
            assert callable(getattr(faiss_store, method)), f"Not callable on FAISS: {method}"
            assert hasattr(qdrant_store, method), f"QdrantVectorStore missing: {method}"
            assert callable(getattr(qdrant_store, method)), f"Not callable on Qdrant: {method}"


# ---------------------------------------------------------------------------
# FAISS-specific: search result ordering
# ---------------------------------------------------------------------------

class TestFAISSSearchOrdering:
    """Property: search_similar results are ordered by descending similarity."""

    def test_results_ordered_descending(self, faiss_store):
        # Two embeddings: chunk-A points along [1,0,0,...], chunk-B along [0,1,0,...]
        emb_a = [1.0] + [0.0] * (DIM - 1)
        emb_b = [0.0, 1.0] + [0.0] * (DIM - 2)

        chunks = [_chunk("a"), _chunk("b")]
        embeddings = [emb_a, emb_b]
        metas = [_meta("a", idx=0), _meta("b", idx=1)]

        faiss_store.add_chunks_with_embeddings(chunks, embeddings, metas)

        # Query closer to emb_a
        query = [0.9, 0.1] + [0.0] * (DIM - 2)
        results = faiss_store.search_similar(query, top_k=2)

        assert len(results) == 2
        assert results[0].similarity_score >= results[1].similarity_score

    def test_most_similar_chunk_first(self, faiss_store):
        emb_a = [1.0] + [0.0] * (DIM - 1)
        emb_b = [0.0, 1.0] + [0.0] * (DIM - 2)

        chunks = [_chunk("a"), _chunk("b")]
        embeddings = [emb_a, emb_b]
        metas = [_meta("a", idx=0), _meta("b", idx=1)]

        faiss_store.add_chunks_with_embeddings(chunks, embeddings, metas)

        # Exact query along emb_a direction → chunk-a should be first
        query = [1.0] + [0.0] * (DIM - 1)
        results = faiss_store.search_similar(query, top_k=2)

        assert results[0].chunk.chunk_id == "a"

    def test_empty_store_returns_empty_list(self, faiss_store):
        results = faiss_store.search_similar([0.1] * DIM, top_k=5)
        assert results == []


# ---------------------------------------------------------------------------
# Shared contract: document lifecycle
# ---------------------------------------------------------------------------

class TestFAISSDocumentLifecycle:
    """Test the full document lifecycle on the FAISS backend."""

    def test_document_not_present_initially(self, faiss_store):
        assert not faiss_store.document_exists("doc.pdf")

    def test_document_present_after_add(self, faiss_store):
        faiss_store.add_chunks_with_embeddings(
            [_chunk("c1")], [[0.5] * DIM], [_meta("c1")]
        )
        assert faiss_store.document_exists("doc.pdf")

    def test_chunk_count_increases_after_add(self, faiss_store):
        assert faiss_store.get_chunk_count() == 0
        faiss_store.add_chunks_with_embeddings(
            [_chunk("c1"), _chunk("c2")],
            [[0.1] * DIM, [0.2] * DIM],
            [_meta("c1", idx=0), _meta("c2", idx=1)],
        )
        assert faiss_store.get_chunk_count() == 2

    def test_document_count_after_add(self, faiss_store):
        faiss_store.add_chunks_with_embeddings(
            [_chunk("c1", doc="a.pdf"), _chunk("c2", doc="b.pdf")],
            [[0.1] * DIM, [0.2] * DIM],
            [_meta("c1", doc="a.pdf", idx=0), _meta("c2", doc="b.pdf", idx=1)],
        )
        assert faiss_store.get_document_count() == 2

    def test_delete_removes_document(self, faiss_store):
        faiss_store.add_chunks_with_embeddings(
            [_chunk()], [[0.5] * DIM], [_meta()]
        )
        assert faiss_store.document_exists("doc.pdf")
        deleted = faiss_store.delete_document_by_name("doc.pdf")
        assert deleted == 1
        assert not faiss_store.document_exists("doc.pdf")

    def test_clear_empties_store(self, faiss_store):
        faiss_store.add_chunks_with_embeddings(
            [_chunk()], [[0.5] * DIM], [_meta()]
        )
        faiss_store.clear()
        assert faiss_store.get_chunk_count() == 0
        assert faiss_store.get_document_count() == 0

    def test_get_document_info_returns_correct_data(self, faiss_store):
        chunks = [
            _chunk("c1", doc="book.pdf", page=1),
            _chunk("c2", doc="book.pdf", page=2),
        ]
        metas = [_meta("c1", doc="book.pdf", page=1, idx=0), _meta("c2", doc="book.pdf", page=2, idx=1)]
        embeddings = [[0.1] * DIM, [0.2] * DIM]
        faiss_store.add_chunks_with_embeddings(chunks, embeddings, metas)

        info = faiss_store.get_document_info("book.pdf")
        assert info is not None
        assert info["document_name"] == "book.pdf"
        assert info["chunks_count"] == 2
        assert info["pages_count"] == 2

    def test_get_document_info_returns_none_for_unknown(self, faiss_store):
        assert faiss_store.get_document_info("ghost.pdf") is None

    def test_get_all_document_names_sorted(self, faiss_store):
        for name, cid in [("z.pdf", "z1"), ("a.pdf", "a1"), ("m.pdf", "m1")]:
            faiss_store.add_chunks_with_embeddings(
                [_chunk(cid, doc=name)],
                [[0.1] * DIM],
                [_meta(cid, doc=name)],
            )
        names = faiss_store.get_all_document_names()
        assert names == sorted(names)
        assert set(names) == {"a.pdf", "m.pdf", "z.pdf"}
