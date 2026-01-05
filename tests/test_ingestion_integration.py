"""Integration tests for the document ingestion service."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
import pypdf
from io import BytesIO

from src.ingestion import DocumentIngestionService, PDFProcessor
from src.config import RAGConfig
from src.embeddings import EmbeddingService, SentenceTransformerProvider
from src.vector_store import FAISSVectorStore
from src.models import TextChunk, ChunkMetadata


class TestDocumentIngestionIntegration:
    """Integration tests for the complete document ingestion pipeline."""
    
    def setup_method(self):
        """Set up test fixtures with real components."""
        # Use a temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.config = RAGConfig(
            chunk_size=200,
            chunk_overlap=50,
            vector_store_path=os.path.join(self.temp_dir, "test_index"),
            metadata_path=os.path.join(self.temp_dir, "test_metadata.json"),
            embedding_dimension=384
        )
        
        # Initialize real components
        self.embedding_service = EmbeddingService(config=self.config)
        
        self.vector_store = FAISSVectorStore(
            dimension=self.config.embedding_dimension,
            index_path=self.config.vector_store_path,
            metadata_path=self.config.metadata_path
        )
        
        self.ingestion_service = DocumentIngestionService(
            config=self.config,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_pdf(self, content: str, filename: str = "test.pdf") -> str:
        """Create a test PDF file with the given content using pypdf.
        
        Args:
            content: Text content to include in the PDF
            filename: Name of the PDF file
            
        Returns:
            Path to the created PDF file
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            pdf_path = os.path.join(self.temp_dir, filename)
            
            # Create PDF using reportlab
            c = canvas.Canvas(pdf_path, pagesize=letter)
            
            # Split content into lines and add to PDF
            lines = content.split('\n')
            y_position = 750  # Start near top of page
            
            for line in lines:
                if y_position < 50:  # Start new page if near bottom
                    c.showPage()
                    y_position = 750
                
                c.drawString(50, y_position, line)
                y_position -= 20
            
            c.save()

            return pdf_path

        except ImportError as e:
            print("The error" ,e)
            # Fallback: create a minimal PDF using pypdf and io
            from pypdf import PdfWriter
            from io import BytesIO
            
            pdf_path = os.path.join(self.temp_dir, filename)
            
            # Create a simple PDF with basic structure
            # This is a minimal PDF that pypdf can read
            pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length """ + str(len(content.encode('utf-8')) + 50).encode() + b"""
>>
stream
BT
/F1 12 Tf
50 750 Td
(""" + content.replace('\n', ') Tj 0 -15 Td (').encode('utf-8') + b""") Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
""" + str(300 + len(content)).encode() + b"""
%%EOF"""
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            return pdf_path
    
    def test_complete_ingestion_pipeline(self):
        """Test the complete document ingestion pipeline with real components."""
        # Create test content
        test_content = """
        This is a test document for integration testing.
        It contains multiple sentences and paragraphs.
        
        The document should be processed through the complete pipeline:
        1. PDF text extraction
        2. Text chunking with overlap
        3. Embedding generation
        4. Vector store persistence
        
        This content is long enough to create multiple chunks
        when processed with the configured chunk size and overlap.
        Each chunk should be properly embedded and stored.
        """
        
        # Create test PDF
        pdf_path = self.create_test_pdf(test_content)
        
        # Process the document
        result = self.ingestion_service.process_document(pdf_path, "test_document")
        
        # Verify processing was successful
        assert result is True
        
        # Verify chunks were created and stored
        stats = self.ingestion_service.get_processing_stats()
        assert stats["total_documents"] == 1
        assert stats["total_chunks"] > 0
        assert stats["embedding_dimension"] == 384
        
        # Verify vector store contains data
        assert self.vector_store.get_document_count() == 1
        assert self.vector_store.get_chunk_count() > 0
    
    def test_multiple_document_processing(self):
        """Test processing multiple documents in sequence."""
        # Create multiple test documents
        documents = [
            ("Document about artificial intelligence and machine learning.", "ai_doc.pdf"),
            ("Document about natural language processing and embeddings.", "nlp_doc.pdf"),
            ("Document about vector databases and similarity search.", "vector_doc.pdf")
        ]
        
        pdf_paths = []
        for content, filename in documents:
            pdf_path = self.create_test_pdf(content, filename)
            pdf_paths.append(pdf_path)
        
        # Process all documents
        doc_names = ["AI Document", "NLP Document", "Vector Document"]
        successful, total = self.ingestion_service.process_multiple_documents(pdf_paths, doc_names)
        
        # Verify all documents were processed
        assert successful == 3
        assert total == 3
        
        # Verify stats reflect multiple documents
        stats = self.ingestion_service.get_processing_stats()
        assert stats["total_documents"] == 3
        assert stats["total_chunks"] > 3  # Should have multiple chunks across documents
    
    def test_vector_search_after_ingestion(self):
        """Test that ingested documents can be searched via vector similarity."""
        # Create test document with specific content
        test_content = """
        Machine learning is a subset of artificial intelligence.
        Neural networks are used for deep learning applications.
        Natural language processing helps computers understand text.
        Vector embeddings represent text in high-dimensional space.
        """
        
        pdf_path = self.create_test_pdf(test_content)
        
        # Process the document
        result = self.ingestion_service.process_document(pdf_path, "ml_document")
        assert result is True
        
        # Generate query embedding
        query = "What is machine learning?"
        query_embedding = self.embedding_service.generate_embedding(query)
        
        # Search for similar chunks
        search_results = self.vector_store.search_similar(query_embedding, top_k=3)
        
        # Verify search returns results
        assert len(search_results) > 0
        
        # Verify results contain relevant content
        found_ml_content = False
        for result in search_results:
            if "machine learning" in result.chunk.text.lower():
                found_ml_content = True
                break
        
        assert found_ml_content, "Search should return chunks containing 'machine learning'"
    
    def test_persistence_and_reload(self):
        """Test that ingested data persists and can be reloaded."""
        # Create and process test document
        test_content = "This is test content for persistence testing."
        pdf_path = self.create_test_pdf(test_content)
        
        result = self.ingestion_service.process_document(pdf_path, "persistence_test")
        assert result is True
        
        # Get initial stats
        initial_stats = self.ingestion_service.get_processing_stats()
        initial_chunk_count = initial_stats["total_chunks"]
        
        # Create new vector store instance and load from disk
        new_vector_store = FAISSVectorStore(
            dimension=self.config.embedding_dimension,
            index_path=self.config.vector_store_path,
            metadata_path=self.config.metadata_path
        )
        new_vector_store.load_index()
        
        # Verify data was loaded correctly
        assert new_vector_store.get_document_count() == 1
        assert new_vector_store.get_chunk_count() == initial_chunk_count
    
    def test_error_handling_integration(self):
        """Test error handling in the integration pipeline."""
        # Test with non-existent file
        result = self.ingestion_service.process_document("nonexistent.pdf", "missing_doc")
        assert result is False
        
        # Test with invalid file (create a text file with .pdf extension)
        invalid_pdf_path = os.path.join(self.temp_dir, "invalid.pdf")
        with open(invalid_pdf_path, 'w') as f:
            f.write("This is not a PDF file")
        
        result = self.ingestion_service.process_document(invalid_pdf_path, "invalid_doc")
        assert result is False
        
        # Verify no data was added to vector store
        assert self.vector_store.get_document_count() == 0
        assert self.vector_store.get_chunk_count() == 0
    
    def test_empty_pdf_handling(self):
        """Test handling of empty or content-less PDFs."""
        # Create an empty PDF
        empty_pdf_path = os.path.join(self.temp_dir, "empty.pdf")
        
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            c = canvas.Canvas(empty_pdf_path, pagesize=letter)
            c.save()  # Save without adding any content
            
        except ImportError:
            # Fallback: create minimal empty PDF
            pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj

xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
180
%%EOF"""
            
            with open(empty_pdf_path, 'wb') as f:
                f.write(pdf_content)
        
        # Process the empty PDF
        result = self.ingestion_service.process_document(empty_pdf_path, "empty_doc")
        
        # Should handle gracefully and return False
        assert result is False
        
        # Verify no data was added
        assert self.vector_store.get_document_count() == 0
    
    def test_chunking_with_different_sizes(self):
        """Test that different chunk sizes produce different results."""
        test_content = "This is a test document. " * 50  # Long content
        pdf_path = self.create_test_pdf(test_content)
        
        # Process with small chunks
        small_config = RAGConfig(chunk_size=100, chunk_overlap=20)
        small_vector_store = FAISSVectorStore(
            dimension=384,
            index_path=os.path.join(self.temp_dir, "small_index"),
            metadata_path=os.path.join(self.temp_dir, "small_metadata.json")
        )
        
        small_service = DocumentIngestionService(
            config=small_config,
            embedding_service=self.embedding_service,
            vector_store=small_vector_store
        )
        
        result = small_service.process_document(pdf_path, "small_chunks_doc")
        assert result is True
        
        small_chunk_count = small_vector_store.get_chunk_count()
        
        # Process with large chunks
        large_config = RAGConfig(chunk_size=500, chunk_overlap=50)
        large_vector_store = FAISSVectorStore(
            dimension=384,
            index_path=os.path.join(self.temp_dir, "large_index"),
            metadata_path=os.path.join(self.temp_dir, "large_metadata.json")
        )
        
        large_service = DocumentIngestionService(
            config=large_config,
            embedding_service=self.embedding_service,
            vector_store=large_vector_store
        )
        
        result = large_service.process_document(pdf_path, "large_chunks_doc")
        assert result is True
        
        large_chunk_count = large_vector_store.get_chunk_count()
        
        # Small chunks should produce more chunks than large chunks
        assert small_chunk_count > large_chunk_count


@pytest.mark.skipif(not os.getenv("RUN_SLOW_TESTS"), reason="Slow integration test")
class TestLargeDocumentIntegration:
    """Integration tests for large document processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = RAGConfig(
            chunk_size=1000,
            chunk_overlap=200,
            vector_store_path=os.path.join(self.temp_dir, "large_test_index"),
            metadata_path=os.path.join(self.temp_dir, "large_test_metadata.json"),
            embedding_dimension=384
        )
        
        self.embedding_service = EmbeddingService(config=self.config)
        
        self.vector_store = FAISSVectorStore(
            dimension=self.config.embedding_dimension,
            index_path=self.config.vector_store_path,
            metadata_path=self.config.metadata_path
        )
        
        self.ingestion_service = DocumentIngestionService(
            config=self.config,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_large_document_processing(self):
        """Test processing of a large document with many pages."""
        # Create a large document with multiple pages
        large_content = ""
        for page in range(5):  # Reduced for testing
            page_content = f"""
            Page {page + 1} Content
            
            This is page {page + 1} of a large test document.
            It contains substantial content to test the system's ability
            to handle larger documents with multiple pages and sections.
            
            The content includes various topics and information that should
            be properly chunked, embedded, and stored in the vector database.
            Each page has unique content that can be distinguished during
            retrieval and search operations.
            
            """ + ("Additional content. " * 10)  # Add more content per page
            
            large_content += page_content
        
        # Create PDF with the large content using the same method as other tests
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            pdf_path = os.path.join(self.temp_dir, "large_document.pdf")
            c = canvas.Canvas(pdf_path, pagesize=letter)
            
            lines = large_content.split('\n')
            y_position = 750
            
            for line in lines:
                if y_position < 50:
                    c.showPage()
                    y_position = 750
                
                if line.strip():  # Only draw non-empty lines
                    c.drawString(50, y_position, line[:80])  # Limit line length
                    y_position -= 15
            
            c.save()
            
        except ImportError:
            # Fallback: create using the same method as create_test_pdf
            pdf_path = os.path.join(self.temp_dir, "large_document.pdf")
            
            # Create a simple PDF with basic structure
            pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length """ + str(len(large_content.encode('utf-8')) + 50).encode() + b"""
>>
stream
BT
/F1 12 Tf
50 750 Td
(""" + large_content.replace('\n', ') Tj 0 -15 Td (').encode('utf-8') + b""") Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
""" + str(300 + len(large_content)).encode() + b"""
%%EOF"""
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
        
        # Process the large document
        result = self.ingestion_service.process_document(pdf_path, "large_test_document")
        assert result is True
        
        # Verify substantial number of chunks were created
        stats = self.ingestion_service.get_processing_stats()
        assert stats["total_chunks"] > 5  # Should have many chunks
        assert stats["total_documents"] == 1