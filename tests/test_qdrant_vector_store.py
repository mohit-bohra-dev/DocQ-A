"""Unit tests for the QdrantVectorStore using a mocked Qdrant client."""

import pytest
from datetime import datetime
from typing import List
from unittest.mock import MagicMock, patch, PropertyMock

from src.models import TextChunk, ChunkMetadata, SearchResult


def _make_chunk(chunk_id: str = "chunk-1", text: str = "Hello world",
                page: int = 1, doc: str = "test.pdf") -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        text=text,
        page_number=page,
        document_name=doc,
        start_char=0,
        end_char=len(text),
    )


def _make_meta(chunk_id: str = "chunk-1", doc: str = "test.pdf",
               page: int = 1, idx: int = 0) -> ChunkMetadata:
    return ChunkMetadata(
        chunk_id=chunk_id,
        document_name=doc,
        page_number=page,
        chunk_index=idx,
        created_at=datetime(2024, 1, 1),
    )


DIM = 4  # Small dimension for tests


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_qdrant_client():
    """Patch QdrantClient so no real network call is made."""
    with patch("src.qdrant_vector_store.QdrantClient") as MockClient:
        instance = MockClient.return_value
        # get_collections returns an empty list by default
        instance.get_collections.return_value = MagicMock(collections=[])
        yield instance


@pytest.fixture()
def store(mock_qdrant_client):
    """QdrantVectorStore using the mocked client."""
    from src.qdrant_vector_store import QdrantVectorStore
    return QdrantVectorStore(dimension=DIM, collection_name="test_col")


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestQdrantInit:
    def test_creates_collection_when_missing(self, mock_qdrant_client):
        """Collection is created if it does not already exist."""
        from src.qdrant_vector_store import QdrantVectorStore
        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        QdrantVectorStore(dimension=DIM, collection_name="new_col")
        mock_qdrant_client.create_collection.assert_called_once()

    def test_skips_creation_when_collection_exists(self, mock_qdrant_client):
        """Collection creation is skipped when it already exists."""
        from src.qdrant_vector_store import QdrantVectorStore
        existing = MagicMock()
        existing.name = "existing_col"
        mock_qdrant_client.get_collections.return_value = MagicMock(
            collections=[existing]
        )
        QdrantVectorStore(dimension=DIM, collection_name="existing_col")
        mock_qdrant_client.create_collection.assert_not_called()

    def test_local_connection(self, mock_qdrant_client):
        """Local connection uses host/port."""
        from src.qdrant_vector_store import QdrantVectorStore
        with patch("src.qdrant_vector_store.QdrantClient") as MockClient:
            MockClient.return_value.get_collections.return_value = MagicMock(collections=[])
            QdrantVectorStore(dimension=DIM, host="myhost", port=7777)
            MockClient.assert_called_once_with(host="myhost", port=7777)

    def test_cloud_connection(self, mock_qdrant_client):
        """Cloud connection uses url + api_key."""
        from src.qdrant_vector_store import QdrantVectorStore
        with patch("src.qdrant_vector_store.QdrantClient") as MockClient:
            MockClient.return_value.get_collections.return_value = MagicMock(collections=[])
            QdrantVectorStore(
                dimension=DIM,
                url="https://my.qdrant.io",
                api_key="secret",
            )
            MockClient.assert_called_once_with(
                url="https://my.qdrant.io", api_key="secret"
            )

    def test_connection_failure_raises_runtime_error(self):
        """Client constructor failure is wrapped in RuntimeError."""
        from src.qdrant_vector_store import QdrantVectorStore
        with patch("src.qdrant_vector_store.QdrantClient", side_effect=Exception("conn refused")):
            with pytest.raises(RuntimeError, match="Failed to initialise Qdrant client"):
                QdrantVectorStore(dimension=DIM)


# ---------------------------------------------------------------------------
# add_chunks_with_embeddings
# ---------------------------------------------------------------------------

class TestAddChunks:
    def test_upsert_called_with_correct_count(self, store, mock_qdrant_client):
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        embeddings = [[0.1] * DIM, [0.2] * DIM]
        metadata = [_make_meta("c1", idx=0), _make_meta("c2", idx=1)]

        store.add_chunks_with_embeddings(chunks, embeddings, metadata)

        mock_qdrant_client.upsert.assert_called_once()
        call_kwargs = mock_qdrant_client.upsert.call_args[1]
        assert len(call_kwargs["points"]) == 2

    def test_payload_contains_chunk_text(self, store, mock_qdrant_client):
        chunk = _make_chunk("c1", text="My text")
        store.add_chunks_with_embeddings([chunk], [[0.5] * DIM], [_make_meta("c1")])

        points = mock_qdrant_client.upsert.call_args[1]["points"]
        assert points[0].payload["chunk_text"] == "My text"

    def test_payload_contains_document_name(self, store, mock_qdrant_client):
        chunk = _make_chunk("c1", doc="sample.pdf")
        store.add_chunks_with_embeddings([chunk], [[0.5] * DIM], [_make_meta("c1", doc="sample.pdf")])

        points = mock_qdrant_client.upsert.call_args[1]["points"]
        assert points[0].payload["document_name"] == "sample.pdf"

    def test_mismatched_lengths_raises_value_error(self, store):
        with pytest.raises(ValueError, match="must match"):
            store.add_chunks_with_embeddings(
                [_make_chunk()], [[0.1] * DIM, [0.2] * DIM], [_make_meta()]
            )

    def test_empty_input_does_not_call_upsert(self, store, mock_qdrant_client):
        store.add_chunks_with_embeddings([], [], [])
        mock_qdrant_client.upsert.assert_not_called()

    def test_upsert_failure_raises_runtime_error(self, store, mock_qdrant_client):
        mock_qdrant_client.upsert.side_effect = Exception("network error")
        with pytest.raises(RuntimeError, match="Failed to upsert"):
            store.add_chunks_with_embeddings(
                [_make_chunk()], [[0.1] * DIM], [_make_meta()]
            )


# ---------------------------------------------------------------------------
# add_embeddings (thin wrapper)
# ---------------------------------------------------------------------------

class TestAddEmbeddings:
    def test_delegates_to_add_chunks(self, store, mock_qdrant_client):
        store.add_embeddings([[0.1] * DIM], [_make_meta()])
        mock_qdrant_client.upsert.assert_called_once()

    def test_mismatched_raises_value_error(self, store):
        with pytest.raises(ValueError, match="must match number of metadata"):
            store.add_embeddings([[0.1] * DIM, [0.2] * DIM], [_make_meta()])


# ---------------------------------------------------------------------------
# search_similar
# ---------------------------------------------------------------------------

class TestSearchSimilar:
    def _make_search_hit(self, chunk_id: str, doc: str, score: float,
                         text: str = "hello", page: int = 1):
        hit = MagicMock()
        hit.score = score
        hit.payload = {
            "chunk_id": chunk_id,
            "document_name": doc,
            "page_number": page,
            "chunk_index": 0,
            "chunk_text": text,
            "start_char": 0,
            "end_char": len(text),
            "created_at": "2024-01-01T00:00:00",
        }
        return hit

    def test_returns_search_results(self, store, mock_qdrant_client):
        mock_qdrant_client.search.return_value = [
            self._make_search_hit("c1", "doc.pdf", 0.9),
            self._make_search_hit("c2", "doc.pdf", 0.7),
        ]
        results = store.search_similar([0.1] * DIM, top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_results_carry_correct_metadata(self, store, mock_qdrant_client):
        mock_qdrant_client.search.return_value = [
            self._make_search_hit("c99", "report.pdf", 0.85, text="Test text", page=3),
        ]
        results = store.search_similar([0.0] * DIM, top_k=1)
        r = results[0]
        assert r.chunk.chunk_id == "c99"
        assert r.chunk.document_name == "report.pdf"
        assert r.chunk.page_number == 3
        assert r.chunk.text == "Test text"
        assert r.similarity_score == pytest.approx(0.85)

    def test_search_failure_raises_runtime_error(self, store, mock_qdrant_client):
        mock_qdrant_client.search.side_effect = Exception("timeout")
        with pytest.raises(RuntimeError, match="Qdrant search failed"):
            store.search_similar([0.1] * DIM, top_k=5)

    def test_empty_results_returns_empty_list(self, store, mock_qdrant_client):
        mock_qdrant_client.search.return_value = []
        results = store.search_similar([0.1] * DIM, top_k=5)
        assert results == []


# ---------------------------------------------------------------------------
# save_index / load_index (no-ops)
# ---------------------------------------------------------------------------

class TestPersistenceNoOps:
    def test_save_index_does_not_raise(self, store):
        store.save_index()  # should be a no-op

    def test_load_index_does_not_raise(self, store):
        store.load_index()  # should be a no-op

    def test_save_index_with_path_does_not_raise(self, store):
        store.save_index(file_path="/some/path.index")

    def test_load_index_with_path_does_not_raise(self, store):
        store.load_index(file_path="/some/path.index")


# ---------------------------------------------------------------------------
# get_chunk_count
# ---------------------------------------------------------------------------

class TestGetChunkCount:
    def test_returns_count(self, store, mock_qdrant_client):
        count_result = MagicMock()
        count_result.count = 42
        mock_qdrant_client.count.return_value = count_result
        assert store.get_chunk_count() == 42

    def test_failure_raises_runtime_error(self, store, mock_qdrant_client):
        mock_qdrant_client.count.side_effect = Exception("error")
        with pytest.raises(RuntimeError, match="Failed to count chunks"):
            store.get_chunk_count()


# ---------------------------------------------------------------------------
# get_all_document_names
# ---------------------------------------------------------------------------

class TestGetAllDocumentNames:
    def _make_record(self, doc_name: str):
        rec = MagicMock()
        rec.payload = {"document_name": doc_name}
        return rec

    def test_returns_sorted_unique_names(self, store, mock_qdrant_client):
        # Single-page scroll
        mock_qdrant_client.scroll.return_value = (
            [self._make_record("b.pdf"), self._make_record("a.pdf"), self._make_record("b.pdf")],
            None,
        )
        names = store.get_all_document_names()
        assert names == ["a.pdf", "b.pdf"]

    def test_empty_collection(self, store, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)
        assert store.get_all_document_names() == []


# ---------------------------------------------------------------------------
# delete_document_by_name
# ---------------------------------------------------------------------------

class TestDeleteDocument:
    def test_calls_delete_and_returns_count(self, store, mock_qdrant_client):
        before = MagicMock()
        before.count = 5
        mock_qdrant_client.count.return_value = before

        deleted = store.delete_document_by_name("old.pdf")
        assert deleted == 5
        mock_qdrant_client.delete.assert_called_once()

    def test_failure_raises_runtime_error(self, store, mock_qdrant_client):
        mock_qdrant_client.count.side_effect = Exception("oops")
        with pytest.raises(RuntimeError, match="Failed to delete document"):
            store.delete_document_by_name("doc.pdf")


# ---------------------------------------------------------------------------
# document_exists
# ---------------------------------------------------------------------------

class TestDocumentExists:
    def test_returns_true_when_count_positive(self, store, mock_qdrant_client):
        result = MagicMock()
        result.count = 3
        mock_qdrant_client.count.return_value = result
        assert store.document_exists("doc.pdf") is True

    def test_returns_false_when_count_zero(self, store, mock_qdrant_client):
        result = MagicMock()
        result.count = 0
        mock_qdrant_client.count.return_value = result
        assert store.document_exists("missing.pdf") is False

    def test_failure_raises_runtime_error(self, store, mock_qdrant_client):
        mock_qdrant_client.count.side_effect = Exception("error")
        with pytest.raises(RuntimeError, match="Failed to check document existence"):
            store.document_exists("doc.pdf")


# ---------------------------------------------------------------------------
# get_document_info
# ---------------------------------------------------------------------------

class TestGetDocumentInfo:
    def _make_record(self, page: int):
        rec = MagicMock()
        rec.payload = {"page_number": page}
        return rec

    def test_returns_info_dict(self, store, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = (
            [self._make_record(1), self._make_record(2), self._make_record(1)],
            None,
        )
        info = store.get_document_info("report.pdf")
        assert info is not None
        assert info["document_name"] == "report.pdf"
        assert info["chunks_count"] == 3
        assert info["pages_count"] == 2
        assert sorted(info["pages"]) == [1, 2]

    def test_returns_none_when_not_found(self, store, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)
        assert store.get_document_info("ghost.pdf") is None


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

class TestClear:
    def test_deletes_and_recreates_collection(self, store, mock_qdrant_client):
        store.clear()
        mock_qdrant_client.delete_collection.assert_called_once_with(store.collection_name)
        # create_collection called during init + clear
        assert mock_qdrant_client.create_collection.call_count >= 1

    def test_failure_raises_runtime_error(self, store, mock_qdrant_client):
        mock_qdrant_client.delete_collection.side_effect = Exception("error")
        with pytest.raises(RuntimeError, match="Failed to clear Qdrant collection"):
            store.clear()


# ---------------------------------------------------------------------------
# is_healthy
# ---------------------------------------------------------------------------

class TestIsHealthy:
    def test_returns_true_on_success(self, store, mock_qdrant_client):
        assert store.is_healthy() is True

    def test_returns_false_on_exception(self, store, mock_qdrant_client):
        mock_qdrant_client.get_collections.side_effect = Exception("unreachable")
        assert store.is_healthy() is False
