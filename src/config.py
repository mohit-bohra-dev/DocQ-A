"""Configuration management for the RAG system."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class RAGConfig:
    """Configuration settings for the RAG system."""
    
    # Document processing settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # Retrieval settings
    top_k_results: int = 5
    
    # Vector store settings
    vector_store_backend: str = "faiss"  # "faiss" or "qdrant"
    vector_store_path: str = "data/vector_store"
    metadata_path: str = "data/metadata.json"
    uploads_dir: str = "data/uploads"

    # Qdrant settings (used when vector_store_backend = "qdrant")
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: Optional[str] = None        # Qdrant Cloud URL (overrides host/port)
    qdrant_api_key: Optional[str] = None    # Qdrant Cloud API key
    qdrant_collection_name: str = "documents"
    
    # Embedding settings
    embedding_provider: str = "sentence-transformers"  # "sentence-transformers" or "gemini"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # LLM settings
    llm_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"
    
    # File upload settings
    max_file_size_mb: int = 50
    allowed_file_types: list = None
    
    def __post_init__(self) -> None:
        """Initialize configuration from environment variables."""
        # Override with environment variables if present
        self.chunk_size = int(os.getenv("CHUNK_SIZE", self.chunk_size))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", self.chunk_overlap))
        self.top_k_results = int(os.getenv("TOP_K_RESULTS", self.top_k_results))
        
        self.vector_store_backend = os.getenv("VECTOR_STORE_BACKEND", self.vector_store_backend)
        self.vector_store_path = os.getenv("VECTOR_STORE_PATH", self.vector_store_path)
        self.metadata_path = os.getenv("METADATA_PATH", self.metadata_path)
        self.uploads_dir = os.getenv("UPLOADS_DIR", self.uploads_dir)

        self.qdrant_host = os.getenv("QDRANT_HOST", self.qdrant_host)
        self.qdrant_port = int(os.getenv("QDRANT_PORT", self.qdrant_port))
        self.qdrant_url = os.getenv("QDRANT_URL", self.qdrant_url)
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", self.qdrant_api_key)
        self.qdrant_collection_name = os.getenv("QDRANT_COLLECTION_NAME", self.qdrant_collection_name)
        
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", self.embedding_provider)
        self.embedding_model = os.getenv("EMBEDDING_MODEL", self.embedding_model)
        self.embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", self.embedding_dimension))
        
        self.llm_provider = os.getenv("LLM_PROVIDER", self.llm_provider)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", self.gemini_api_key)
        self.gemini_model = os.getenv("GEMINI_MODEL", self.gemini_model)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.openai_model = os.getenv("OPENAI_MODEL", self.openai_model)
        
        self.api_host = os.getenv("API_HOST", self.api_host)
        self.api_port = int(os.getenv("API_PORT", self.api_port))
        
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        self.log_format = os.getenv("LOG_FORMAT", self.log_format)
        
        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", self.max_file_size_mb))
        
        if self.allowed_file_types is None:
            self.allowed_file_types = [".pdf"]
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        if self.top_k_results <= 0:
            raise ValueError("top_k_results must be positive")
        
        if self.embedding_dimension <= 0:
            raise ValueError("embedding_dimension must be positive")
        
        if self.embedding_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("gemini_api_key is required when using Gemini embedding provider")

        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("gemini_api_key is required when using Gemini provider")

        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("openai_api_key is required when using OpenAI provider")

        if self.vector_store_backend not in ("faiss", "qdrant"):
            raise ValueError(f"vector_store_backend must be 'faiss' or 'qdrant', got '{self.vector_store_backend}'")

        if self.vector_store_backend == "qdrant" and self.qdrant_url and not self.qdrant_api_key:
            raise ValueError("qdrant_api_key is required when connecting to Qdrant Cloud (qdrant_url set)")

        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")


# Global configuration instance
config = RAGConfig()