"""Qdrant-based vector store implementation for the RAG system."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    from qdrant_client.http.exceptions import UnexpectedResponse
    QDRANT_AVAILABLE = True
except ImportError:  # pragma: no cover
    QDRANT_AVAILABLE = False

try:
    from .interfaces import VectorStore
    from .models import ChunkMetadata, SearchResult, TextChunk
except ImportError:
    from interfaces import VectorStore
    from models import ChunkMetadata, SearchResult, TextChunk

logger = logging.getLogger(__name__)

# Payload field names stored in Qdrant
_FIELD_CHUNK_ID = "chunk_id"
_FIELD_DOCUMENT_NAME = "document_name"
_FIELD_PAGE_NUMBER = "page_number"
_FIELD_CHUNK_INDEX = "chunk_index"
_FIELD_CHUNK_TEXT = "chunk_text"
_FIELD_START_CHAR = "start_char"
_FIELD_END_CHAR = "end_char"
_FIELD_CREATED_AT = "created_at"


class QdrantVectorStore(VectorStore):
    """Qdrant-based implementation of the VectorStore interface.

    Supports both local Qdrant instances and Qdrant Cloud:
    - Local: set ``host`` and ``port`` (defaults: localhost:6333)
    - Cloud: set ``url`` (https://...) and ``api_key``

    The collection is created automatically on first use with Cosine
    distance so that normalised embeddings produce the same ranking as
    FAISS IndexFlatIP.
    """

    def __init__(
        self,
        dimension: int,
        collection_name: str = "documents",
        host: str = "localhost",
        port: int = 6333,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialise the Qdrant vector store.

        Args:
            dimension: Dimensionality of the embeddings.
            collection_name: Name of the Qdrant collection to use.
            host: Hostname of a local Qdrant instance.
            port: Port of a local Qdrant instance.
            url: Full URL for Qdrant Cloud (overrides host/port).
            api_key: API key for Qdrant Cloud.
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client is not installed. "
                "Run: uv add qdrant-client"
            )

        self.dimension = dimension
        self.collection_name = collection_name

        try:
            if url:
                logger.info("Connecting to Qdrant Cloud at %s", url)
                self.client = QdrantClient(url=url, api_key=api_key)
            else:
                logger.info("Connecting to local Qdrant at %s:%s", host, port)
                self.client = QdrantClient(host=host, port=port)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialise Qdrant client: {exc}"
            ) from exc

        self._ensure_collection()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist, and ensure
        the payload index on document_name is present (idempotent)."""
        try:
            existing = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in existing:
                logger.info(
                    "Creating Qdrant collection '%s' (dim=%d, Cosine)",
                    self.collection_name,
                    self.dimension,
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.dimension,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            else:
                logger.debug("Qdrant collection '%s' already exists.", self.collection_name)

            # Always ensure the payload index exists — Qdrant Cloud requires
            # indexed fields for filtered queries (count, scroll, delete).
            # This call is idempotent: it is a no-op if the index already exists.
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=_FIELD_DOCUMENT_NAME,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                logger.debug(
                    "Payload index on '%s' ensured for collection '%s'.",
                    _FIELD_DOCUMENT_NAME,
                    self.collection_name,
                )
            except Exception as idx_exc:
                # Non-fatal: log and continue — worst case filtered queries are slower
                logger.warning("Could not ensure payload index: %s", idx_exc)

        except Exception as exc:
            raise RuntimeError(
                f"Failed to ensure Qdrant collection '{self.collection_name}': {exc}"
            ) from exc


    def _collection_exists(self) -> bool:
        """Return True if the collection exists in Qdrant."""
        try:
            existing = [c.name for c in self.client.get_collections().collections]
            return self.collection_name in existing
        except Exception:
            return False


    @staticmethod
    def _point_id(chunk_id: str) -> str:
        """Convert a chunk_id string to a Qdrant-compatible UUID-like string.

        Qdrant accepts arbitrary *unsigned int* IDs or UUID strings.
        We use the chunk_id directly since it is already a UUID.
        """
        return chunk_id

    # ------------------------------------------------------------------
    # VectorStore interface implementation
    # ------------------------------------------------------------------

    def add_embeddings(
        self,
        embeddings: List[List[float]],
        metadata: List[ChunkMetadata],
    ) -> None:
        """Add embeddings with metadata (without full chunk text)."""
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings must match number of metadata items")
        if not embeddings:
            return

        # Build minimal TextChunk objects so we can reuse add_chunks_with_embeddings
        chunks = [
            TextChunk(
                chunk_id=meta.chunk_id,
                text="",
                page_number=meta.page_number,
                document_name=meta.document_name,
                start_char=0,
                end_char=0,
            )
            for meta in metadata
        ]
        self.add_chunks_with_embeddings(chunks, embeddings, metadata)

    def add_chunks_with_embeddings(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]],
        metadata: List[ChunkMetadata],
    ) -> None:
        """Upsert chunks with their embeddings into Qdrant."""
        if len(chunks) != len(embeddings) or len(embeddings) != len(metadata):
            raise ValueError(
                "Number of chunks, embeddings, and metadata must match"
            )
        if not embeddings:
            return

        points = [
            qmodels.PointStruct(
                id=self._point_id(chunk.chunk_id),
                vector=embedding,
                payload={
                    _FIELD_CHUNK_ID: chunk.chunk_id,
                    _FIELD_DOCUMENT_NAME: chunk.document_name,
                    _FIELD_PAGE_NUMBER: chunk.page_number,
                    _FIELD_CHUNK_INDEX: meta.chunk_index,
                    _FIELD_CHUNK_TEXT: chunk.text,
                    _FIELD_START_CHAR: chunk.start_char,
                    _FIELD_END_CHAR: chunk.end_char,
                    _FIELD_CREATED_AT: meta.created_at.isoformat(),
                },
            )
            for chunk, embedding, meta in zip(chunks, embeddings, metadata)
        ]

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            logger.debug(
                "Upserted %d points into collection '%s'.",
                len(points),
                self.collection_name,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to upsert embeddings into Qdrant: {exc}"
            ) from exc

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
    ) -> List[SearchResult]:
        """Query Qdrant for the top-k most similar chunks."""
        try:
            hits = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=top_k,
                with_payload=True,
            ).points
        except Exception as exc:
            raise RuntimeError(
                f"Qdrant search failed: {exc}"
            ) from exc

        results: List[SearchResult] = []
        for hit in hits:
            payload = hit.payload or {}
            chunk = TextChunk(
                chunk_id=payload.get(_FIELD_CHUNK_ID, ""),
                text=payload.get(_FIELD_CHUNK_TEXT, ""),
                page_number=payload.get(_FIELD_PAGE_NUMBER, 0),
                document_name=payload.get(_FIELD_DOCUMENT_NAME, ""),
                start_char=payload.get(_FIELD_START_CHAR, 0),
                end_char=payload.get(_FIELD_END_CHAR, 0),
            )
            created_at_str = payload.get(_FIELD_CREATED_AT, "")
            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                created_at = datetime.now()

            meta = ChunkMetadata(
                chunk_id=payload.get(_FIELD_CHUNK_ID, ""),
                document_name=payload.get(_FIELD_DOCUMENT_NAME, ""),
                page_number=payload.get(_FIELD_PAGE_NUMBER, 0),
                chunk_index=payload.get(_FIELD_CHUNK_INDEX, 0),
                created_at=created_at,
            )
            results.append(
                SearchResult(chunk=chunk, similarity_score=float(hit.score), metadata=meta)
            )

        return results

    def save_index(self, file_path: Optional[str] = None) -> None:
        """No-op: Qdrant persists data automatically."""
        logger.info(
            "save_index called on QdrantVectorStore (Qdrant persists automatically; nothing to do)."
        )

    def load_index(self, file_path: Optional[str] = None) -> None:
        """No-op: Qdrant persists data automatically."""
        logger.info(
            "load_index called on QdrantVectorStore (Qdrant persists automatically; nothing to do)."
        )

    def get_document_count(self) -> int:
        """Count unique document names by scrolling through all payloads."""
        return len(self.get_all_document_names())

    def get_chunk_count(self) -> int:
        """Return the total number of vectors in the collection."""
        try:
            result = self.client.count(
                collection_name=self.collection_name,
                exact=True,
            )
            return result.count
        except Exception as exc:
            raise RuntimeError(
                f"Failed to count chunks in Qdrant: {exc}"
            ) from exc

    def clear(self) -> None:
        """Delete and recreate the collection, removing all data."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Deleted Qdrant collection '%s'.", self.collection_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to clear Qdrant collection '{self.collection_name}': {exc}"
            ) from exc
        self._ensure_collection()

    def get_all_document_names(self) -> List[str]:
        """Return a sorted list of all unique document names."""
        unique_names: set = set()
        offset = None

        try:
            while True:
                records, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    offset=offset,
                    limit=1000,
                    with_payload=[_FIELD_DOCUMENT_NAME],
                    with_vectors=False,
                )
                for record in records:
                    name = (record.payload or {}).get(_FIELD_DOCUMENT_NAME)
                    if name:
                        unique_names.add(name)
                if next_offset is None:
                    break
                offset = next_offset
        except Exception as exc:
            raise RuntimeError(
                f"Failed to list document names from Qdrant: {exc}"
            ) from exc

        return sorted(unique_names)

    def delete_document_by_name(self, document_name: str) -> int:
        """Delete all chunks belonging to a document and return the count deleted."""
        if not self._collection_exists():
            return 0
        # Count before deletion
        try:
            before = self.client.count(
                collection_name=self.collection_name,
                count_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key=_FIELD_DOCUMENT_NAME,
                            match=qmodels.MatchValue(value=document_name),
                        )
                    ]
                ),
                exact=True,
            ).count

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key=_FIELD_DOCUMENT_NAME,
                                match=qmodels.MatchValue(value=document_name),
                            )
                        ]
                    )
                ),
            )
            logger.info(
                "Deleted %d chunks for document '%s' from Qdrant.",
                before,
                document_name,
            )
            return before
        except Exception as exc:
            raise RuntimeError(
                f"Failed to delete document '{document_name}' from Qdrant: {exc}"
            ) from exc

    def document_exists(self, document_name: str) -> bool:
        """Return True if at least one chunk for the document is stored."""
        if not self._collection_exists():
            return False
        try:
            result = self.client.count(
                collection_name=self.collection_name,
                count_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key=_FIELD_DOCUMENT_NAME,
                            match=qmodels.MatchValue(value=document_name),
                        )
                    ]
                ),
                exact=True,
            )
            return result.count > 0
        except Exception as exc:
            raise RuntimeError(
                f"Failed to check document existence in Qdrant: {exc}"
            ) from exc

    def get_document_info(self, document_name: str) -> Optional[Dict[str, Any]]:
        """Return stats for a document, or None if not found."""
        chunks_count = 0
        pages: set = set()
        offset = None

        try:
            doc_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key=_FIELD_DOCUMENT_NAME,
                        match=qmodels.MatchValue(value=document_name),
                    )
                ]
            )
            while True:
                records, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=doc_filter,
                    offset=offset,
                    limit=1000,
                    with_payload=[_FIELD_PAGE_NUMBER],
                    with_vectors=False,
                )
                for record in records:
                    chunks_count += 1
                    page = (record.payload or {}).get(_FIELD_PAGE_NUMBER)
                    if page is not None:
                        pages.add(page)
                if next_offset is None:
                    break
                offset = next_offset
        except Exception as exc:
            raise RuntimeError(
                f"Failed to get document info from Qdrant: {exc}"
            ) from exc

        if chunks_count == 0:
            return None

        return {
            "document_name": document_name,
            "chunks_count": chunks_count,
            "pages_count": len(pages),
            "pages": sorted(pages),
        }

    # ------------------------------------------------------------------
    # Extra helpers
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        """Return True if the Qdrant instance is reachable."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
