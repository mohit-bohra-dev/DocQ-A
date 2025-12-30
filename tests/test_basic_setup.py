"""Basic tests to verify project setup."""

import pytest
from datetime import datetime
from src.models import TextChunk, ChunkMetadata, QueryResult, SourceReference
from src.config import RAGConfig
from src.logging_config import configure_logging, get_logger


def test_text_chunk_creation():
    """Test that TextChunk can be created with all required fields."""
    chunk = TextChunk(
        chunk_id="test-chunk-1",
        text="This is a test chunk of text.",
        page_number=1,
        document_name="test.pdf",
        start_char=0,
        end_char=29
    )
    
    assert chunk.chunk_id == "test-chunk-1"
    assert chunk.text == "This is a test chunk of text."
    assert chunk.page_number == 1
    assert chunk.document_name == "test.pdf"
    assert chunk.start_char == 0
    assert chunk.end_char == 29


def test_chunk_metadata_creation():
    """Test that ChunkMetadata can be created with all required fields."""
    now = datetime.now()
    metadata = ChunkMetadata(
        chunk_id="test-chunk-1",
        document_name="test.pdf",
        page_number=1,
        chunk_index=0,
        created_at=now
    )
    
    assert metadata.chunk_id == "test-chunk-1"
    assert metadata.document_name == "test.pdf"
    assert metadata.page_number == 1
    assert metadata.chunk_index == 0
    assert metadata.created_at == now


def test_query_result_creation():
    """Test that QueryResult can be created with all required fields."""
    source_ref = SourceReference(
        document_name="test.pdf",
        page_number=1,
        chunk_id="test-chunk-1"
    )
    
    chunk = TextChunk(
        chunk_id="test-chunk-1",
        text="Test text",
        page_number=1,
        document_name="test.pdf",
        start_char=0,
        end_char=9
    )
    
    result = QueryResult(
        answer="This is a test answer.",
        source_references=[source_ref],
        confidence_score=0.85,
        retrieved_chunks=[chunk]
    )
    
    assert result.answer == "This is a test answer."
    assert len(result.source_references) == 1
    assert result.confidence_score == 0.85
    assert len(result.retrieved_chunks) == 1


def test_config_validation():
    """Test that configuration validation works correctly."""
    # Test valid configuration
    config = RAGConfig(
        chunk_size=1000,
        chunk_overlap=200,
        top_k_results=5,
        llm_provider="test"  # Use test provider to avoid API key requirement
    )
    config.validate()  # Should not raise
    
    # Test invalid chunk size
    config_invalid = RAGConfig(chunk_size=0)
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        config_invalid.validate()
    
    # Test invalid overlap
    config_invalid = RAGConfig(chunk_size=100, chunk_overlap=150)
    with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
        config_invalid.validate()


def test_logging_configuration():
    """Test that logging can be configured without errors."""
    configure_logging()
    logger = get_logger("test")
    
    # This should not raise any exceptions
    logger.info("Test log message")
    logger.warning("Test warning message")
    logger.error("Test error message")