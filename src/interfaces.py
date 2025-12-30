"""Core interfaces and abstract base classes for the RAG system."""

from abc import ABC, abstractmethod
from typing import List, Optional
from .models import TextChunk, SearchResult, ChunkMetadata, AnswerResult


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation providers."""
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass
    
    @abstractmethod
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass


class VectorStore(ABC):
    """Abstract interface for vector storage and retrieval."""
    
    @abstractmethod
    def add_embeddings(self, embeddings: List[List[float]], metadata: List[ChunkMetadata]) -> None:
        """Add embeddings with metadata to the store."""
        pass
    
    @abstractmethod
    def search_similar(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """Search for similar embeddings."""
        pass
    
    @abstractmethod
    def save_index(self, file_path: str) -> None:
        """Save the index to disk."""
        pass
    
    @abstractmethod
    def load_index(self, file_path: str) -> None:
        """Load the index from disk."""
        pass
    
    @abstractmethod
    def get_document_count(self) -> int:
        """Get the number of documents in the store."""
        pass


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    def generate_answer(self, prompt: str) -> str:
        """Generate an answer from a prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass


class DocumentProcessor(ABC):
    """Abstract interface for document processing."""
    
    @abstractmethod
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        pass
    
    @abstractmethod
    def chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[TextChunk]:
        """Split text into chunks with specified size and overlap."""
        pass


class AnswerGenerator(ABC):
    """Abstract interface for answer generation."""
    
    @abstractmethod
    def generate_answer(self, question: str, context: List[TextChunk]) -> AnswerResult:
        """Generate an answer based on question and context."""
        pass
    
    @abstractmethod
    def construct_grounded_prompt(self, question: str, context: List[TextChunk]) -> str:
        """Construct a grounded prompt from question and context."""
        pass