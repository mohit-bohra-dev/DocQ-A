#!/usr/bin/env python3
"""
Demo script showing the embedding service functionality.

This script demonstrates:
1. Basic embedding generation
2. Batch embedding processing
3. Provider abstraction
4. Configuration management
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import embeddings
import config


def main():
    """Demonstrate embedding service functionality."""
    print("🚀 Embedding Service Demo")
    print("=" * 50)
    
    # Initialize configuration
    config_obj = config.RAGConfig()
    config_obj.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    
    print(f"📋 Configuration:")
    print(f"   Model: {config_obj.embedding_model}")
    print(f"   Provider: {config_obj.embedding_provider}")
    print()
    
    # Initialize embedding service
    print("🔧 Initializing embedding service...")
    service = embeddings.EmbeddingService(config_obj)
    
    # Get provider information
    info = service.get_provider_info()
    print(f"✅ Service initialized successfully!")
    print(f"   Provider Type: {info['provider_type']}")
    print(f"   Embedding Dimension: {info['embedding_dimension']}")
    print()
    
    # Demo 1: Single text embedding
    print("📝 Demo 1: Single Text Embedding")
    print("-" * 30)
    
    text = "This is a sample document about machine learning and artificial intelligence."
    print(f"Input text: '{text}'")
    
    embedding = service.generate_embedding(text)
    print(f"Generated embedding with {len(embedding)} dimensions")
    print(f"First 5 values: {embedding[:5]}")
    print(f"Embedding norm: {sum(x*x for x in embedding)**0.5:.4f}")
    print()
    
    # Demo 2: Batch embedding generation
    print("📚 Demo 2: Batch Embedding Generation")
    print("-" * 35)
    
    documents = [
        "Natural language processing is a subfield of AI.",
        "Computer vision deals with image and video analysis.",
        "Deep learning uses neural networks with multiple layers.",
        "Machine learning algorithms learn from data patterns.",
        "Artificial intelligence aims to create intelligent machines."
    ]
    
    print(f"Processing {len(documents)} documents...")
    batch_embeddings = service.generate_batch_embeddings(documents)
    
    print(f"Generated {len(batch_embeddings)} embeddings")
    for i, (doc, emb) in enumerate(zip(documents, batch_embeddings)):
        norm = sum(x*x for x in emb)**0.5
        print(f"  Doc {i+1}: {len(emb)} dims, norm: {norm:.4f}")
        print(f"    Text: '{doc[:50]}...'")
    print()
    
    # Demo 3: Semantic similarity
    print("🔍 Demo 3: Semantic Similarity")
    print("-" * 28)
    
    def cosine_similarity(a, b):
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)
    
    # Compare first two documents (both about AI/ML)
    sim_1_2 = cosine_similarity(batch_embeddings[0], batch_embeddings[1])
    print(f"Similarity between docs 1 & 2: {sim_1_2:.4f}")
    print(f"  Doc 1: '{documents[0]}'")
    print(f"  Doc 2: '{documents[1]}'")
    print()
    
    # Compare doc 1 with a very different text
    different_text = "The weather is sunny today with clear blue skies."
    different_embedding = service.generate_embedding(different_text)
    sim_different = cosine_similarity(batch_embeddings[0], different_embedding)
    
    print(f"Similarity between doc 1 & different text: {sim_different:.4f}")
    print(f"  Doc 1: '{documents[0]}'")
    print(f"  Different: '{different_text}'")
    print()
    
    # Demo 4: Edge cases
    print("⚠️  Demo 4: Edge Case Handling")
    print("-" * 28)
    
    # Empty text
    empty_embedding = service.generate_embedding("")
    print(f"Empty text embedding: {len(empty_embedding)} dims, all zeros: {all(x == 0.0 for x in empty_embedding)}")
    
    # Whitespace only
    whitespace_embedding = service.generate_embedding("   \n\t  ")
    print(f"Whitespace embedding: {len(whitespace_embedding)} dims, all zeros: {all(x == 0.0 for x in whitespace_embedding)}")
    
    # Mixed batch with empty texts
    mixed_texts = ["Real content", "", "   ", "More real content"]
    mixed_embeddings = service.generate_batch_embeddings(mixed_texts)
    print(f"Mixed batch: {len(mixed_embeddings)} embeddings generated")
    for i, emb in enumerate(mixed_embeddings):
        is_zero = all(x == 0.0 for x in emb)
        print(f"  Embedding {i+1}: {'zero vector' if is_zero else 'non-zero vector'}")
    print()
    
    print("✨ Demo completed successfully!")
    print("The embedding service is ready for use in the RAG pipeline.")


if __name__ == "__main__":
    main()