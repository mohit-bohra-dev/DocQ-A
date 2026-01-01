"""Integration tests for the embedding service."""

from src.embeddings import EmbeddingService
from src.config import RAGConfig


def test_embedding_service_integration():
    """Test the embedding service with real configuration."""
    # Create a configuration for sentence transformers
    config = RAGConfig()
    config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Initialize the service
    service = EmbeddingService(config)
    
    # Test single embedding
    text = "This is a test document about machine learning and artificial intelligence."
    embedding = service.generate_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == service.get_embedding_dimension()
    assert all(isinstance(x, float) for x in embedding)
    
    # Test batch embeddings
    texts = [
        "Document about natural language processing.",
        "Article on computer vision techniques.",
        "Research paper on deep learning algorithms."
    ]
    
    batch_embeddings = service.generate_batch_embeddings(texts)
    
    assert len(batch_embeddings) == len(texts)
    assert all(len(emb) == service.get_embedding_dimension() for emb in batch_embeddings)
    
    # Test that similar texts have similar embeddings (basic semantic test)
    similar_text = "This is a test document about AI and machine learning."
    similar_embedding = service.generate_embedding(similar_text)
    
    # Calculate cosine similarity (basic check)
    def cosine_similarity(a, b):
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)
    
    similarity = cosine_similarity(embedding, similar_embedding)
    
    # Similar texts should have high similarity (> 0.7)
    assert similarity > 0.7, f"Similarity too low: {similarity}"
    
    # Test provider info
    info = service.get_provider_info()
    assert info["provider_type"] == "SentenceTransformerProvider"
    assert info["model_name"] == config.embedding_model
    assert info["embedding_dimension"] > 0


def test_embedding_consistency():
    """Test that the same text produces the same embedding."""
    config = RAGConfig()
    config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    
    service = EmbeddingService(config)
    
    text = "Consistency test for embedding generation."
    
    # Generate embedding twice
    embedding1 = service.generate_embedding(text)
    embedding2 = service.generate_embedding(text)
    
    # Should be identical (or very close due to floating point precision)
    assert len(embedding1) == len(embedding2)
    for i, (a, b) in enumerate(zip(embedding1, embedding2)):
        assert abs(a - b) < 1e-6, f"Embeddings differ at index {i}: {a} vs {b}"
    
    # Test with batch processing - batch processing might have slight differences
    # due to internal optimizations, so we'll test that they're very similar
    texts = [text]
    batch_embeddings = service.generate_batch_embeddings(texts)
    
    # Should be very similar (allowing for small numerical differences)
    batch_embedding = batch_embeddings[0]
    assert len(batch_embedding) == len(embedding1)
    for i, (a, b) in enumerate(zip(embedding1, batch_embedding)):
        assert abs(a - b) < 1e-5, f"Single vs batch embeddings differ at index {i}: {a} vs {b}"


def test_empty_and_whitespace_handling():
    """Test handling of empty and whitespace-only texts."""
    config = RAGConfig()
    config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    
    service = EmbeddingService(config)
    
    # Test empty string
    empty_embedding = service.generate_embedding("")
    assert len(empty_embedding) == service.get_embedding_dimension()
    assert all(x == 0.0 for x in empty_embedding)
    
    # Test whitespace-only string
    whitespace_embedding = service.generate_embedding("   \n\t  ")
    assert len(whitespace_embedding) == service.get_embedding_dimension()
    assert all(x == 0.0 for x in whitespace_embedding)
    
    # Test batch with mixed content
    texts = ["Real content", "", "   ", "More content"]
    batch_embeddings = service.generate_batch_embeddings(texts)
    
    assert len(batch_embeddings) == 4
    assert all(x == 0.0 for x in batch_embeddings[1])  # Empty string
    assert all(x == 0.0 for x in batch_embeddings[2])  # Whitespace only
    assert not all(x == 0.0 for x in batch_embeddings[0])  # Real content
    assert not all(x == 0.0 for x in batch_embeddings[3])  # Real content