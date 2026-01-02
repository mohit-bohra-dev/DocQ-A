"""Tests for the FAISS vector store implementation."""

import pytest
import tempfile
import os
from datetime import datetime
from typing import List

from src.vector_store import FAISSVectorStore
from src.models import TextChunk, ChunkMetadata, SearchResult


class TestFAISSVectorStore:
    """Test cases for the FAISS vector store."""
    
    def test_initialization(self):
        """Test vector store initialization."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        assert store.dimension == dimension
        assert store.get_chunk_count() == 0
        assert store.get_document_count() == 0
    
    def test_add_chunks_with_embeddings(self):
        """Test adding chunks with embeddings."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        # Create test data
        chunks = [
            TextChunk(
                chunk_id="chunk-1",
                text="This is the first test chunk.",
                page_number=1,
                document_name="test.pdf",
                start_char=0,
                end_char=30
            ),
            TextChunk(
                chunk_id="chunk-2", 
                text="This is the second test chunk.",
                page_number=1,
                document_name="test.pdf",
                start_char=31,
                end_char=62
            )
        ]
        
        embeddings = [
            [0.1] * dimension,  # Simple test embedding
            [0.2] * dimension   # Different test embedding
        ]
        
        metadata = [
            ChunkMetadata(
                chunk_id="chunk-1",
                document_name="test.pdf",
                page_number=1,
                chunk_index=0,
                created_at=datetime.now()
            ),
            ChunkMetadata(
                chunk_id="chunk-2",
                document_name="test.pdf", 
                page_number=1,
                chunk_index=1,
                created_at=datetime.now()
            )
        ]
        
        # Add to store
        store.add_chunks_with_embeddings(chunks, embeddings, metadata)
        
        # Verify
        assert store.get_chunk_count() == 2
        assert store.get_document_count() == 1
    
    def test_search_similar(self):
        """Test similarity search functionality."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        # Add test data
        chunks = [
            TextChunk(
                chunk_id="chunk-1",
                text="Machine learning is fascinating.",
                page_number=1,
                document_name="ml.pdf",
                start_char=0,
                end_char=30
            ),
            TextChunk(
                chunk_id="chunk-2",
                text="Deep learning uses neural networks.",
                page_number=2,
                document_name="ml.pdf", 
                start_char=0,
                end_char=35
            )
        ]
        
        # Create embeddings with clear similarity differences
        # First embedding: mostly 1.0 values
        embedding1 = [1.0] * dimension
        # Second embedding: mostly 0.0 values  
        embedding2 = [0.0] * dimension
        
        embeddings = [embedding1, embedding2]
        
        metadata = [
            ChunkMetadata(
                chunk_id="chunk-1",
                document_name="ml.pdf",
                page_number=1,
                chunk_index=0,
                created_at=datetime.now()
            ),
            ChunkMetadata(
                chunk_id="chunk-2",
                document_name="ml.pdf",
                page_number=2,
                chunk_index=1,
                created_at=datetime.now()
            )
        ]
        
        store.add_chunks_with_embeddings(chunks, embeddings, metadata)
        
        # Search with a query very similar to the first embedding
        query_embedding = [0.9] * dimension
        results = store.search_similar(query_embedding, top_k=2)
        
        # Verify results
        assert len(results) == 2
        assert all(isinstance(result, SearchResult) for result in results)
        
        # Results should be ordered by similarity (higher scores first)
        assert results[0].similarity_score >= results[1].similarity_score
        
        # First result should be most similar to our query (chunk-1 with embedding of all 1.0s)
        assert results[0].chunk.chunk_id == "chunk-1"
    
    def test_search_empty_store(self):
        """Test search on empty store."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        query_embedding = [0.1] * dimension
        results = store.search_similar(query_embedding, top_k=5)
        
        assert results == []
    
    def test_save_and_load_index(self):
        """Test saving and loading the index."""
        dimension = 384
        
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "test_index.index")
            metadata_path = os.path.join(temp_dir, "test_metadata.json")
            
            # Create and populate store
            store1 = FAISSVectorStore(dimension, index_path, metadata_path)
            
            chunks = [
                TextChunk(
                    chunk_id="save-test-1",
                    text="Test content for save/load.",
                    page_number=1,
                    document_name="save_test.pdf",
                    start_char=0,
                    end_char=25
                )
            ]
            
            embeddings = [[0.7] * dimension]
            
            metadata = [
                ChunkMetadata(
                    chunk_id="save-test-1",
                    document_name="save_test.pdf",
                    page_number=1,
                    chunk_index=0,
                    created_at=datetime.now()
                )
            ]
            
            store1.add_chunks_with_embeddings(chunks, embeddings, metadata)
            
            # Save the index
            store1.save_index()
            
            # Create new store and load
            store2 = FAISSVectorStore(dimension, index_path, metadata_path)
            store2.load_index()
            
            # Verify loaded data
            assert store2.get_chunk_count() == 1
            assert store2.get_document_count() == 1
            
            # Test search works on loaded store
            query_embedding = [0.7] * dimension
            results = store2.search_similar(query_embedding, top_k=1)
            
            assert len(results) == 1
            assert results[0].chunk.chunk_id == "save-test-1"
            assert results[0].chunk.text == "Test content for save/load."
    
    def test_load_nonexistent_index(self):
        """Test loading from nonexistent files."""
        dimension = 384
        
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "nonexistent.index")
            metadata_path = os.path.join(temp_dir, "nonexistent.json")
            
            store = FAISSVectorStore(dimension, index_path, metadata_path)
            
            # Should not raise an error
            store.load_index()
            
            # Should initialize empty store
            assert store.get_chunk_count() == 0
            assert store.get_document_count() == 0
    
    def test_clear_store(self):
        """Test clearing the vector store."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        # Add some data
        chunks = [
            TextChunk(
                chunk_id="clear-test",
                text="Content to be cleared.",
                page_number=1,
                document_name="clear.pdf",
                start_char=0,
                end_char=21
            )
        ]
        
        embeddings = [[0.8] * dimension]
        
        metadata = [
            ChunkMetadata(
                chunk_id="clear-test",
                document_name="clear.pdf",
                page_number=1,
                chunk_index=0,
                created_at=datetime.now()
            )
        ]
        
        store.add_chunks_with_embeddings(chunks, embeddings, metadata)
        
        # Verify data exists
        assert store.get_chunk_count() == 1
        
        # Clear the store
        store.clear()
        
        # Verify store is empty
        assert store.get_chunk_count() == 0
        assert store.get_document_count() == 0
    
    def test_add_embeddings_validation(self):
        """Test validation of input parameters."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        # Test mismatched lengths
        embeddings = [[0.1] * dimension, [0.2] * dimension]
        metadata = [
            ChunkMetadata(
                chunk_id="test",
                document_name="test.pdf",
                page_number=1,
                chunk_index=0,
                created_at=datetime.now()
            )
        ]  # Only one metadata item for two embeddings
        
        with pytest.raises(ValueError, match="Number of embeddings must match"):
            store.add_embeddings(embeddings, metadata)
    
    def test_add_chunks_validation(self):
        """Test validation of chunks, embeddings, and metadata."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        chunks = [
            TextChunk(
                chunk_id="test",
                text="Test",
                page_number=1,
                document_name="test.pdf",
                start_char=0,
                end_char=4
            )
        ]
        
        embeddings = [[0.1] * dimension, [0.2] * dimension]  # Two embeddings
        
        metadata = [
            ChunkMetadata(
                chunk_id="test",
                document_name="test.pdf",
                page_number=1,
                chunk_index=0,
                created_at=datetime.now()
            )
        ]  # One metadata item
        
        with pytest.raises(ValueError, match="Number of chunks, embeddings, and metadata must match"):
            store.add_chunks_with_embeddings(chunks, embeddings, metadata)
    
    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        dimension = 384
        store = FAISSVectorStore(dimension)
        
        # Empty lists should not cause errors
        store.add_embeddings([], [])
        store.add_chunks_with_embeddings([], [], [])
        
        assert store.get_chunk_count() == 0
        assert store.get_document_count() == 0