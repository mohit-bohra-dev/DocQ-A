#!/usr/bin/env python3
"""Debug script to test Gemini embedding provider."""

import sys
import os
sys.path.insert(0, 'src')

from embeddings import GeminiEmbeddingProvider

def main():
    api_key = "AIzaSyCZwEZnd4NQxZwYlDkz4W5_ew2S21gbGN0"
    provider = GeminiEmbeddingProvider(api_key)
    
    text = "This is a test sentence."
    print(f"Testing with text: '{text}'")
    
    try:
        embedding = provider.generate_embedding(text)
        print(f"Embedding type: {type(embedding)}")
        print(f"Embedding length: {len(embedding)}")
        if embedding:
            print(f"First element type: {type(embedding[0])}")
            print(f"First 5 elements: {embedding[:5]}")
            print(f"All elements are floats: {all(isinstance(x, float) for x in embedding)}")
            print(f"All elements are numbers: {all(isinstance(x, (int, float)) for x in embedding)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()