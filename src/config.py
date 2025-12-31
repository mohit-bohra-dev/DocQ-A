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
    vector_store_path: str = "data/vector_store"
    metadata_path: str = "data/metadata.json"
    
    # Embedding settings
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
        
        self.vector_store_path = os.getenv("VECTOR_STORE_PATH", self.vector_store_path)
        self.metadata_path = os.getenv("METADATA_PATH", self.metadata_path)
        
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
        
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("gemini_api_key is required when using Gemini provider")
        
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("openai_api_key is required when using OpenAI provider")
        
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")


# Global configuration instance
config = RAGConfig()