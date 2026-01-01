#!/usr/bin/env python3
"""Test Gemini integration with EmbeddingService."""

import sys
import os
sys.path.insert(0, 'src')

from embeddings import EmbeddingService
from config import RAGConfig

def main():
    print("🧪 Testing Gemini Integration with EmbeddingService")
    print("=" * 55)
    
    # Configure for Gemini
    config = RAGConfig()
    config.embedding_model = "models/text-embedding-004"
    config.gemini_api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
    
    print(f"📋 Configuration:")
    print(f"   Model: {config.embedding_model}")
    print(f"   API Key: {config.gemini_api_key[:20]}...")
    print()
    
    # Initialize service
    service = EmbeddingService(config)
    
    # Get provider info
    info = service.get_provider_info()
    print(f"✅ Service initialized:")
    print(f"   Provider Type: {info['provider_type']}")
    print(f"   Model Name: {info['model_name']}")
    print(f"   Embedding Dimension: {info['embedding_dimension']}")
    print()
    
    # Test single embedding
    text = "This is a test document about artificial intelligence and machine learning."
    print(f"📝 Testing single embedding:")
    print(f"   Text: '{text}'")
    
    embedding = service.generate_embedding(text)
    print(f"   Generated embedding: {len(embedding)} dimensions")
    print(f"   First 5 values: {embedding[:5]}")
    print(f"   Embedding norm: {sum(x*x for x in embedding)**0.5:.4f}")
    print()
    
    # Test batch embeddings
    texts = [
        "Natural language processing with transformers.",
        "Computer vision and deep learning techniques.",
        "Reinforcement learning for autonomous systems."
    ]
    
    print(f"📚 Testing batch embeddings:")
    batch_embeddings = service.generate_batch_embeddings(texts)
    
    for i, (text, emb) in enumerate(zip(texts, batch_embeddings)):
        norm = sum(x*x for x in emb)**0.5
        print(f"   Doc {i+1}: {len(emb)} dims, norm: {norm:.4f}")
        print(f"     Text: '{text}'")
    print()
    
    # Test semantic similarity
    def cosine_similarity(a, b):
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)
    
    sim = cosine_similarity(batch_embeddings[0], batch_embeddings[1])
    print(f"🔍 Semantic similarity test:")
    print(f"   Similarity between AI texts: {sim:.4f}")
    print(f"   Text 1: '{texts[0]}'")
    print(f"   Text 2: '{texts[1]}'")
    print()
    
    # Test with different domain
    different_text = "The weather is beautiful today with sunshine."
    different_embedding = service.generate_embedding(different_text)
    sim_different = cosine_similarity(batch_embeddings[0], different_embedding)
    
    print(f"   Similarity with different domain: {sim_different:.4f}")
    print(f"   AI text: '{texts[0]}'")
    print(f"   Weather text: '{different_text}'")
    print()
    
    print("✨ Gemini integration test completed successfully!")
    print("The GeminiEmbeddingProvider is working correctly with the EmbeddingService.")

if __name__ == "__main__":
    main()