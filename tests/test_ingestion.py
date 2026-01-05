"""Tests for the document ingestion service."""

import os
import tempfile
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.ingestion import PDFProcessor, DocumentIngestionService
from src.config import RAGConfig
from src.models import TextChunk, ChunkMetadata


class TestPDFProcessor:
    """Test cases for PDFProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RAGConfig(chunk_size=100, chunk_overlap=20)
        self.processor = PDFProcessor(self.config)
    
    def test_chunk_text_basic(self):
        """Test basic text chunking functionality."""
        text = "This is a test document. " * 10  # 250 characters
        chunks = self.processor.chunk_text(text, chunk_size=100, overlap=20)
        
        assert len(chunks) > 1
        assert all(len(chunk.text) <= 100 for chunk in chunks)
        assert all(chunk.chunk_id for chunk in chunks)
        assert all(chunk.start_char < chunk.end_char for chunk in chunks)
    
    def test_chunk_text_with_overlap(self):
        """Test that chunking respects overlap parameter."""
        text = "A" * 200
        chunks = self.processor.chunk_text(text, chunk_size=100, overlap=20)
        
        # Should have at least 2 chunks
        assert len(chunks) >= 2
        
        # Check overlap between consecutive chunks
        if len(chunks) > 1:
            # The second chunk should start before the first chunk ends
            assert chunks[1].start_char < chunks[0].end_char
    
    def test_chunk_text_empty_input(self):
        """Test chunking with empty input."""
        chunks = self.processor.chunk_text("", chunk_size=100, overlap=20)
        assert chunks == []
        
        chunks = self.processor.chunk_text("   ", chunk_size=100, overlap=20)
        assert chunks == []
    
    def test_chunk_text_invalid_parameters(self):
        """Test chunking with invalid parameters."""
        text = "Test text"
        
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            self.processor.chunk_text(text, chunk_size=0, overlap=20)
        
        with pytest.raises(ValueError, match="overlap cannot be negative"):
            self.processor.chunk_text(text, chunk_size=100, overlap=-1)
        
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            self.processor.chunk_text(text, chunk_size=100, overlap=100)
    
    def test_extract_page_number(self):
        """Test page number extraction from chunk text."""
        # Test with page marker
        chunk_text = "--- Page 3 ---\nSome content here"
        page_num = self.processor._extract_page_number(chunk_text, 0, chunk_text)
        assert page_num == 3
        
        # Test without page marker
        full_text = "--- Page 1 ---\nContent\n--- Page 2 ---\nMore content"
        chunk_text = "More content"
        chunk_start = full_text.find("More content")
        page_num = self.processor._extract_page_number(chunk_text, chunk_start, full_text)
        assert page_num == 2
    
    def test_extract_text_from_pdf_file_not_found(self):
        """Test PDF extraction with non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.processor.extract_text_from_pdf("nonexistent.pdf")
    
    def test_extract_text_from_pdf_invalid_extension(self):
        """Test PDF extraction with non-PDF file."""
        # Create a temporary file with wrong extension
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="File is not a PDF"):
                self.processor.extract_text_from_pdf(tmp_file_path)
        finally:
            os.unlink(tmp_file_path)


class TestDocumentIngestionService:
    """Test cases for DocumentIngestionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RAGConfig(chunk_size=100, chunk_overlap=20)
        self.mock_embedding_service = Mock()
        self.mock_vector_store = Mock()
        
        self.service = DocumentIngestionService(
            self.config, 
            self.mock_embedding_service, 
            self.mock_vector_store
        )
    
    @patch('src.ingestion.PDFProcessor.extract_text_from_pdf')
    def test_process_document_success(self, mock_extract):
        """Test successful document processing."""
        # Mock PDF text extraction
        test_text = "This is test content. " * 20  # Long enough to create chunks
        mock_extract.return_value = test_text
        
        # Mock vector store methods
        self.mock_vector_store.add_chunks_with_embeddings.return_value = None
        self.mock_vector_store.save_index.return_value = None
        
        # Calculate expected chunks using the same parameters as the service
        processor = PDFProcessor(self.config)
        chunks = processor.chunk_text(test_text, self.config.chunk_size, self.config.chunk_overlap)
        expected_chunk_count = len(chunks)
        
        # Mock the correct number of embeddings
        self.mock_embedding_service.generate_batch_embeddings.return_value = [
            [0.1, 0.2, 0.3] for _ in range(expected_chunk_count)
        ]
        
        result = self.service.process_document("test.pdf", "test_doc")
        
        assert result is True
        mock_extract.assert_called_once_with("test.pdf")
        self.mock_embedding_service.generate_batch_embeddings.assert_called_once()
        self.mock_vector_store.add_chunks_with_embeddings.assert_called_once()
        self.mock_vector_store.save_index.assert_called_once()
    
    @patch('src.ingestion.PDFProcessor.extract_text_from_pdf')
    def test_process_document_empty_text(self, mock_extract):
        """Test document processing with empty text."""
        mock_extract.return_value = ""
        
        result = self.service.process_document("test.pdf", "test_doc")
        
        assert result is False
        self.mock_embedding_service.generate_batch_embeddings.assert_not_called()
        self.mock_vector_store.add_chunks_with_embeddings.assert_not_called()
    
    @patch('src.ingestion.PDFProcessor.extract_text_from_pdf')
    def test_process_document_extraction_error(self, mock_extract):
        """Test document processing with extraction error."""
        mock_extract.side_effect = ValueError("PDF extraction failed")
        
        result = self.service.process_document("test.pdf", "test_doc")
        
        assert result is False
    
    def test_get_processing_stats(self):
        """Test getting processing statistics."""
        # Mock vector store stats
        self.mock_vector_store.get_document_count.return_value = 5
        self.mock_vector_store.get_chunk_count.return_value = 50
        
        # Mock embedding service stats
        self.mock_embedding_service.get_embedding_dimension.return_value = 384
        self.mock_embedding_service.get_provider_info.return_value = {
            "provider_type": "SentenceTransformerProvider",
            "model_name": "test-model"
        }
        
        stats = self.service.get_processing_stats()
        
        assert stats["total_documents"] == 5
        assert stats["total_chunks"] == 50
        assert stats["embedding_dimension"] == 384
        assert "provider_info" in stats
    
    @patch('src.ingestion.PDFProcessor.extract_text_from_pdf')
    def test_process_multiple_documents(self, mock_extract):
        """Test processing multiple documents."""
        test_text = "Test content. " * 10
        mock_extract.return_value = test_text
        
        # Mock vector store methods
        self.mock_vector_store.add_chunks_with_embeddings.return_value = None
        self.mock_vector_store.save_index.return_value = None
        
        # Mock the correct number of embeddings for each call
        processor = PDFProcessor(self.config)
        chunks = processor.chunk_text(test_text, self.config.chunk_size, self.config.chunk_overlap)
        expected_chunk_count = len(chunks)
        
        # Set up side_effect to return correct embeddings for each call
        self.mock_embedding_service.generate_batch_embeddings.side_effect = [
            [[0.1, 0.2, 0.3] for _ in range(expected_chunk_count)],  # First document
            [[0.4, 0.5, 0.6] for _ in range(expected_chunk_count)]   # Second document
        ]
        
        file_paths = ["doc1.pdf", "doc2.pdf"]
        doc_names = ["Document 1", "Document 2"]
        
        successful, total = self.service.process_multiple_documents(file_paths, doc_names)
        
        assert successful == 2
        assert total == 2
        assert mock_extract.call_count == 2