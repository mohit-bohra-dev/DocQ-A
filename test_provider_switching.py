#!/usr/bin/env python3
"""Test provider switching in EmbeddingService."""

import sys
import os
sys.path.insert(0, 'src')

from embeddings import EmbeddingService
from config import RAGConfig

def test_sentence_transformers():
    """Test with Sentence Transformers provider."""
    config = RAGConfig()
    config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    
    service = EmbeddingService(config)
    info = service.get_provider_info()
    
    print(f"🤖 Sentence Transformers Provider:")
    print(f"   Type: {info['provider_type']}")
    print(f"   Model: {info['model_name']}")
    print(f"   Dimension: {info['embedding_dimension']}")
    
    text = "Test with Sentence Transformers"
    embedding = service.generate_embedding(text)
    print(f"   Embedding length: {len(embedding)}")
    print(f"   First 3 values: {embedding[:3]}")
    print()

def test_gemini():
    """Test with Gemini provider."""
    config = RAGConfig()
    config.embedding_model = "models/text-embedding-004"
    config.gemini_api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
    
    service = EmbeddingService(config)
    info = service.get_provider_info()
    
    print(f"🧠 Gemini Provider:")
    print(f"   Type: {info['provider_type']}")
    print(f"   Model: {info['model_name']}")
    print(f"   Dimension: {info['embedding_dimension']}")
    
    text = "Test with Gemini"
    embedding = service.generate_embedding(text)
    print(f"   Embedding length: {len(embedding)}")
    print(f"   First 3 values: {embedding[:3]}")
    print()

def main():
    print("🔄 Testing Provider Switching")
    print("=" * 35)
    
    test_sentence_transformers()
    test_gemini()
    
    print("✅ Provider switching test completed successfully!")
    print("Both providers work correctly through the EmbeddingService abstraction.")

if __name__ == "__main__":
    main()