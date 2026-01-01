"""Tests for the embedding service and providers."""

import pytest


from src.embeddings import (
    EmbeddingService, 
    SentenceTransformerProvider, 
    GeminiEmbeddingProvider
)
from src.config import RAGConfig


class TestSentenceTransformerProvider:
    """Test cases for SentenceTransformer embedding provider."""
    
    def test_generate_embedding_basic(self):
        """Test basic embedding generation."""
        provider = SentenceTransformerProvider("sentence-transformers/all-MiniLM-L6-v2")
        
        text = "This is a test sentence."
        embedding = provider.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_embedding_empty_text(self):
        """Test embedding generation with empty text."""
        provider = SentenceTransformerProvider("sentence-transformers/all-MiniLM-L6-v2")
        
        embedding = provider.generate_embedding("")
        dimension = provider.get_embedding_dimension()
        
        assert isinstance(embedding, list)
        assert len(embedding) == dimension
        assert all(x == 0.0 for x in embedding)
    
    def test_generate_batch_embeddings(self):
        """Test batch embedding generation."""
        provider = SentenceTransformerProvider("sentence-transformers/all-MiniLM-L6-v2")
        
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = provider.generate_batch_embeddings(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == provider.get_embedding_dimension() for emb in embeddings)
    
    def test_generate_batch_embeddings_with_empty_texts(self):
        """Test batch embedding generation with some empty texts."""
        provider = SentenceTransformerProvider("sentence-transformers/all-MiniLM-L6-v2")
        
        texts = ["First sentence.", "", "Third sentence."]
        embeddings = provider.generate_batch_embeddings(texts)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == provider.get_embedding_dimension() for emb in embeddings)
        # Empty text should produce zero embedding
        assert all(x == 0.0 for x in embeddings[1])
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension."""
        provider = SentenceTransformerProvider("sentence-transformers/all-MiniLM-L6-v2")
        
        dimension = provider.get_embedding_dimension()
        
        assert isinstance(dimension, int)
        assert dimension > 0


class TestEmbeddingService:
    """Test cases for the main embedding service."""
    
    def test_initialization_with_sentence_transformers(self):
        """Test service initialization with sentence transformers."""
        config = RAGConfig()
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        service = EmbeddingService(config)
        
        assert service.config == config
        assert service._provider is None  # Lazy loading
    
    def test_generate_embedding(self):
        """Test embedding generation through service."""
        config = RAGConfig()
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        service = EmbeddingService(config)
        
        text = "Test sentence for embedding."
        embedding = service.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_batch_embeddings(self):
        """Test batch embedding generation through service."""
        config = RAGConfig()
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        service = EmbeddingService(config)
        
        texts = ["First test.", "Second test.", "Third test."]
        embeddings = service.generate_batch_embeddings(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension through service."""
        config = RAGConfig()
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        service = EmbeddingService(config)
        
        dimension = service.get_embedding_dimension()
        
        assert isinstance(dimension, int)
        assert dimension > 0
    
    def test_get_provider_info(self):
        """Test getting provider information."""
        config = RAGConfig()
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        service = EmbeddingService(config)
        
        info = service.get_provider_info()
        
        assert isinstance(info, dict)
        assert "provider_type" in info
        assert "model_name" in info
        assert "embedding_dimension" in info
        assert info["provider_type"] == "SentenceTransformerProvider"
    
    def test_provider_creation_sentence_transformers(self):
        """Test provider creation for sentence transformers."""
        config = RAGConfig()
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        
        service = EmbeddingService(config)
        provider = service._create_provider()
        
        assert isinstance(provider, SentenceTransformerProvider)
    
    def test_provider_creation_unknown_model_defaults_to_sentence_transformers(self):
        """Test that unknown models default to sentence transformers."""
        config = RAGConfig()
        config.embedding_model = "unknown-model"
        
        service = EmbeddingService(config)
        provider = service._create_provider()
        
        assert isinstance(provider, SentenceTransformerProvider)


class TestGeminiEmbeddingProvider:
    """Test cases for Gemini embedding provider."""
    
    def test_generate_embedding_basic(self):
        """Test basic embedding generation with Gemini."""
        # This test requires a real API key and would make actual API calls
        # Skip by default to avoid API costs and dependencies
        api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
        provider = GeminiEmbeddingProvider(api_key)
        
        text = "This is a test sentence."
        embedding = provider.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_embedding_empty_text(self):
        """Test embedding generation with empty text."""
        api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
        provider = GeminiEmbeddingProvider(api_key)
        
        embedding = provider.generate_embedding("")
        dimension = provider.get_embedding_dimension()
        
        assert isinstance(embedding, list)
        assert len(embedding) == dimension
        assert all(x == 0.0 for x in embedding)
    
    def test_generate_batch_embeddings(self):
        """Test batch embedding generation."""
        api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
        provider = GeminiEmbeddingProvider(api_key)
        
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = provider.generate_batch_embeddings(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == provider.get_embedding_dimension() for emb in embeddings)
        assert all(all(isinstance(x, float) for x in emb) for emb in embeddings)
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension."""
        api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
        provider = GeminiEmbeddingProvider(api_key)
        
        dimension = provider.get_embedding_dimension()
        
        assert isinstance(dimension, int)
        assert dimension > 0
        # text-embedding-004 should have 768 dimensions
        assert dimension == 768
    
    def test_initialization(self):
        """Test Gemini provider initialization."""
        api_key = "test-api-key"
        model_name = "models/text-embedding-004"
        
        provider = GeminiEmbeddingProvider(api_key, model_name)
        
        assert provider.api_key == api_key
        assert provider.model_name == model_name
        assert provider._dimension is None