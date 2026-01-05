"""Document ingestion service for PDF processing and indexing."""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pypdf

try:
    from .interfaces import DocumentProcessor
    from .models import TextChunk, ChunkMetadata
    from .config import RAGConfig
    from .embeddings import EmbeddingService
    from .vector_store import FAISSVectorStore
except ImportError:
    from interfaces import DocumentProcessor
    from models import TextChunk, ChunkMetadata
    from config import RAGConfig
    from embeddings import EmbeddingService
    from vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class PDFProcessor(DocumentProcessor):
    """PDF document processor implementation."""
    
    def __init__(self, config: RAGConfig):
        """Initialize the PDF processor with configuration.
        
        Args:
            config: RAG system configuration
        """
        self.config = config
        logger.info("Initialized PDF processor")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content from all pages
            
        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            ValueError: If the file is not a valid PDF or is corrupted
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        if not file_path.lower().endswith('.pdf'):
            raise ValueError(f"File is not a PDF: {file_path}")
        
        try:
            extracted_text = ""
            
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    logger.warning(f"PDF is encrypted: {file_path}")
                    raise ValueError(f"Cannot process encrypted PDF: {file_path}")
                
                num_pages = len(pdf_reader.pages)
                logger.info(f"Processing PDF with {num_pages} pages: {file_path}")
                
                if num_pages == 0:
                    logger.warning(f"PDF has no pages: {file_path}")
                    return ""
                
                # Extract text from each page
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            extracted_text += f"\n--- Page {page_num} ---\n"
                            extracted_text += page_text
                        else:
                            logger.warning(f"No text found on page {page_num} of {file_path}")
                    except Exception as e:
                        logger.error(f"Error extracting text from page {page_num} of {file_path}: {e}")
                        continue
                
                if not extracted_text.strip():
                    logger.warning(f"No text content extracted from PDF: {file_path}")
                    return ""
                
                logger.info(f"Successfully extracted {len(extracted_text)} characters from {file_path}")
                return extracted_text.strip()
                
        except pypdf.errors.PdfReadError as e:
            logger.error(f"PDF read error for {file_path}: {e}")
            raise ValueError(f"Invalid or corrupted PDF file: {file_path}")
        except Exception as e:
            logger.error(f"Unexpected error processing PDF {file_path}: {e}")
            raise ValueError(f"Failed to process PDF file: {file_path}")
    
    def chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[TextChunk]:
        """Split text into chunks with specified size and overlap.
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of TextChunk objects
            
        Raises:
            ValueError: If chunk_size <= 0 or overlap < 0 or overlap >= chunk_size
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap cannot be negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        
        if not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        chunks = []
        text_length = len(text)
        start = 0
        chunk_index = 0
        
        logger.info(f"Chunking text of length {text_length} with chunk_size={chunk_size}, overlap={overlap}")
        
        while start < text_length:
            # Calculate end position for this chunk
            end = min(start + chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = text[start:end]
            
            # Skip empty chunks
            if not chunk_text.strip():
                start = end
                continue
            
            # Try to break at word boundaries if we're not at the end of text
            if end < text_length and chunk_size > 100:  # Only for reasonably sized chunks
                # Look for the last space within the last 10% of the chunk
                search_start = max(start, end - chunk_size // 10)
                last_space = chunk_text.rfind(' ', search_start - start)
                
                if last_space > 0:
                    # Adjust end to break at word boundary
                    end = start + last_space
                    chunk_text = text[start:end]
            
            # Parse page number from chunk text (look for page markers)
            page_number = self._extract_page_number(chunk_text, start, text)
            
            # Create chunk with unique ID
            chunk_id = str(uuid.uuid4())
            chunk = TextChunk(
                chunk_id=chunk_id,
                text=chunk_text.strip(),
                page_number=page_number,
                document_name="",  # Will be set by the caller
                start_char=start,
                end_char=end
            )
            
            chunks.append(chunk)
            chunk_index += 1
            
            # Move start position for next chunk (with overlap)
            if end >= text_length:
                break
            
            start = end - overlap
            
            # Ensure we make progress even with large overlaps
            if start <= chunks[-1].start_char:
                start = chunks[-1].end_char
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def _extract_page_number(self, chunk_text: str, chunk_start: int, full_text: str) -> int:
        """Extract page number from chunk text or position.
        
        Args:
            chunk_text: The text of the current chunk
            chunk_start: Starting position of chunk in full text
            full_text: The complete document text
            
        Returns:
            Page number (1-based)
        """
        # Look for page markers in the chunk text
        lines = chunk_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('--- Page ') and line.endswith(' ---'):
                try:
                    page_num = int(line.split(' ')[2])
                    return page_num
                except (IndexError, ValueError):
                    continue
        
        # If no page marker found, estimate based on position
        # Count page markers before this chunk
        text_before_chunk = full_text[:chunk_start]
        page_markers = text_before_chunk.count('--- Page ')
        
        # Return the last page number found, or 1 if none
        return max(1, page_markers)


class DocumentIngestionService:
    """Main service for document ingestion and processing."""
    
    def __init__(self, config: RAGConfig, embedding_service: EmbeddingService, 
                 vector_store: FAISSVectorStore):
        """Initialize the document ingestion service.
        
        Args:
            config: RAG system configuration
            embedding_service: Service for generating embeddings
            vector_store: Vector store for persistence
        """
        self.config = config
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.pdf_processor = PDFProcessor(config)
        
        logger.info("Initialized document ingestion service")
    
    def process_document(self, file_path: str, document_name: Optional[str] = None) -> bool:
        """Process a document through the complete ingestion pipeline.
        
        Args:
            file_path: Path to the document file
            document_name: Optional custom name for the document
            
        Returns:
            True if processing was successful, False otherwise
        """
        if document_name is None:
            document_name = Path(file_path).stem
        
        logger.info(f"Starting document processing: {document_name} from {file_path}")
        
        try:
            # Step 1: Extract text from PDF
            logger.info(f"Extracting text from PDF: {file_path}")
            extracted_text = self.pdf_processor.extract_text_from_pdf(file_path)
            
            if not extracted_text.strip():
                logger.warning(f"No text extracted from document: {file_path}")
                return False
            
            # Step 2: Chunk the text
            logger.info(f"Chunking text with size={self.config.chunk_size}, overlap={self.config.chunk_overlap}")
            chunks = self.pdf_processor.chunk_text(
                extracted_text, 
                self.config.chunk_size, 
                self.config.chunk_overlap
            )
            
            if not chunks:
                logger.warning(f"No chunks created from document: {file_path}")
                return False
            
            # Update document name in chunks
            for chunk in chunks:
                chunk.document_name = document_name
            
            # Step 3: Generate embeddings for chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.generate_batch_embeddings(chunk_texts)
            
            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)} chunks")
                return False
            
            # Step 4: Create metadata for chunks
            metadata_list = []
            for i, chunk in enumerate(chunks):
                metadata = ChunkMetadata(
                    chunk_id=chunk.chunk_id,
                    document_name=document_name,
                    page_number=chunk.page_number,
                    chunk_index=i,
                    created_at=datetime.now()
                )
                metadata_list.append(metadata)
            
            # Step 5: Store in vector database
            logger.info(f"Storing {len(chunks)} chunks in vector store")
            self.vector_store.add_chunks_with_embeddings(chunks, embeddings, metadata_list)
            
            # Step 6: Save the index
            logger.info("Saving vector store index")
            self.vector_store.save_index()
            
            logger.info(f"Successfully processed document: {document_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return False
    
    def process_multiple_documents(self, file_paths: List[str], 
                                 document_names: Optional[List[str]] = None) -> Tuple[int, int]:
        """Process multiple documents in batch.
        
        Args:
            file_paths: List of paths to document files
            document_names: Optional list of custom names for documents
            
        Returns:
            Tuple of (successful_count, total_count)
        """
        if document_names and len(document_names) != len(file_paths):
            raise ValueError("Number of document names must match number of file paths")
        
        successful_count = 0
        total_count = len(file_paths)
        
        logger.info(f"Processing {total_count} documents in batch")
        
        for i, file_path in enumerate(file_paths):
            doc_name = document_names[i] if document_names else None
            
            try:
                if self.process_document(file_path, doc_name):
                    successful_count += 1
                    logger.info(f"Successfully processed document {i+1}/{total_count}: {file_path}")
                else:
                    logger.warning(f"Failed to process document {i+1}/{total_count}: {file_path}")
            except Exception as e:
                logger.error(f"Error processing document {i+1}/{total_count} ({file_path}): {e}")
        
        logger.info(f"Batch processing complete: {successful_count}/{total_count} documents successful")
        return successful_count, total_count
    
    def get_processing_stats(self) -> dict:
        """Get statistics about processed documents.
        
        Returns:
            Dictionary with processing statistics
        """
        return {
            "total_documents": self.vector_store.get_document_count(),
            "total_chunks": self.vector_store.get_chunk_count(),
            "embedding_dimension": self.embedding_service.get_embedding_dimension(),
            "provider_info": self.embedding_service.get_provider_info()
        }