"""Core data models for the Document QA RAG Agent."""

from dataclasses import dataclass
from datetime import datetime
from typing import List
from enum import Enum


@dataclass
class TextChunk:
    """Represents a chunk of text from a document."""
    chunk_id: str
    text: str
    page_number: int
    document_name: str
    start_char: int
    end_char: int


@dataclass
class ChunkMetadata:
    """Metadata associated with a text chunk."""
    chunk_id: str
    document_name: str
    page_number: int
    chunk_index: int
    created_at: datetime


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    chunk: TextChunk
    similarity_score: float
    metadata: ChunkMetadata


@dataclass
class SourceReference:
    """Reference to source document location."""
    document_name: str
    page_number: int
    chunk_id: str
    content_snippet: str = ""  # Excerpt of the chunk text for frontend highlighting


@dataclass
class QueryResult:
    """Complete result from a query operation."""
    answer: str
    source_references: List[SourceReference]
    confidence_score: float
    retrieved_chunks: List[TextChunk]


@dataclass
class AnswerResult:
    """Result from answer generation."""
    answer: str
    confidence_score: float
    source_references: List[SourceReference]


class ProcessingStatus(Enum):
    """Processing status enumeration for UI."""
    IDLE = "idle"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    QUERYING = "querying"
    ERROR = "error"


@dataclass
class ConversationEntry:
    """Represents a conversation entry in the UI."""
    question: str
    answer: str
    source_references: List[SourceReference]
    timestamp: datetime
    confidence_score: float


@dataclass
class UIState:
    """UI state management."""
    uploaded_documents: List[str]
    conversation_history: List[ConversationEntry]
    current_question: str
    processing_status: ProcessingStatus