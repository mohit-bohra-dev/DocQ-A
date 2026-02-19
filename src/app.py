"""FastAPI application for the Document QA RAG Agent."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Dict, Any
import os
import tempfile
import uuid

from .config import config
from .logging_config import configure_logging, get_logger
from .models import QueryResult, SourceReference
from .query_engine import QueryEngine
from .answer_generator import AnswerGenerator
from .embeddings import EmbeddingService
from .vector_store import FAISSVectorStore
from .ingestion import DocumentIngestionService

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Document QA RAG Agent",
    description="A Document Question-Answering AI Agent using Retrieval-Augmented Generation",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning("Request validation failed", extra={"errors": exc.errors()})
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors()
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors."""
    logger.error("Value error occurred", extra={"error": str(exc)})
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "error_code": "VALUE_ERROR"
        }
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle file not found errors."""
    logger.error("File not found", extra={"error": str(exc)})
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Requested file not found",
            "error_code": "FILE_NOT_FOUND"
        }
    )


# Request/Response models
class QueryRequest(BaseModel):
    """Request model for querying documents."""
    question: str
    top_k: Optional[int] = None
    document_name: Optional[str] = None  # NEW: Filter by specific document
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the main topic of the document?",
                "top_k": 5,
                "document_name": "report.pdf"
            }
        }


class QueryResponse(BaseModel):
    """Response model for query results."""
    answer: str
    source_references: List[SourceReference]
    confidence_score: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The main topic is...",
                "source_references": [
                    {
                        "document_name": "example.pdf",
                        "page_number": 1,
                        "chunk_id": "abc123"
                    }
                ],
                "confidence_score": 0.85
            }
        }


class UploadResponse(BaseModel):
    """Response model for document upload."""
    message: str
    document_id: str
    chunks_created: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Document uploaded and processed successfully",
                "document_id": "abc123-def456",
                "chunks_created": 15
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    components: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "components": {
                    "vector_store": "ready",
                    "embedding_service": "ready (sentence-transformers)",
                    "llm_service": "ready (gemini)",
                    "documents_indexed": 5
                }
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: str
    error_code: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Error description",
                "error_code": "VALIDATION_ERROR"
            }
        }


# Global service instances
_ingestion_service = None


def get_ingestion_service() -> DocumentIngestionService:
    """Get the document ingestion service singleton."""
    global _ingestion_service
    if _ingestion_service is None:
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()
        _ingestion_service = DocumentIngestionService(
            config=config,
            embedding_service=embedding_service,
            vector_store=vector_store
        )
    return _ingestion_service


# Global service instances
_embedding_service = None
_vector_store = None
_answer_generator = None
_query_engine = None


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(config)
    return _embedding_service


def get_vector_store() -> FAISSVectorStore:
    """Get the vector store singleton."""
    global _vector_store
    if _vector_store is None:
        embedding_service = get_embedding_service()
        dimension = embedding_service.get_embedding_dimension()
        _vector_store = FAISSVectorStore(
            dimension=dimension,
            index_path=config.vector_store_path,
            metadata_path=config.metadata_path
        )
        # Load existing index if available
        _vector_store.load_index()
    return _vector_store


def get_answer_generator() -> AnswerGenerator:
    """Get the answer generator singleton."""
    global _answer_generator
    if _answer_generator is None:
        _answer_generator = AnswerGenerator(config)
    return _answer_generator


def get_query_engine() -> QueryEngine:
    """Get the query engine singleton."""
    global _query_engine
    if _query_engine is None:
        vector_store = get_vector_store()
        embedding_service = get_embedding_service()
        answer_generator = get_answer_generator()
        _query_engine = QueryEngine(
            vector_store=vector_store,
            embedding_service=embedding_service,
            answer_generator=answer_generator,
            config=config
        )
    return _query_engine

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/documents",
         summary="List Documents",
         description="Get list of all uploaded documents")
async def list_documents() -> Dict[str, Any]:
    """Get list of all documents in the system."""
    logger.info("Document list requested")
    
    try:
        vector_store = get_vector_store()
        document_names = vector_store.get_all_document_names()
        
        documents = []
        for doc_name in document_names:
            doc_info = vector_store.get_document_info(doc_name)
            if doc_info:
                documents.append(doc_info)
        
        return {
            "total_documents": len(documents),
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/documents/{document_name}",
            summary="Delete Document",
            description="Delete a specific document and all its chunks")
async def delete_document(document_name: str) -> Dict[str, Any]:
    """Delete a document from the system."""
    logger.info(f"Document deletion requested", extra={"document_name": document_name})
    
    try:
        vector_store = get_vector_store()
        
        if not vector_store.document_exists(document_name):
            raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found")
        
        deleted_count = vector_store.delete_document_by_name(document_name)
        vector_store.save_index()
        
        logger.info(f"Document deleted successfully", extra={"document_name": document_name, "chunks_deleted": deleted_count})
        
        return {
            "message": f"Document '{document_name}' deleted successfully",
            "chunks_deleted": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.get("/health", 
         response_model=HealthResponse,
         summary="Health Check",
         description="Check the health status of all system components")
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.info("Health check requested")
    
    try:
        # Check component status
        components = {}
        
        try:
            embedding_service = get_embedding_service()
            embedding_info = embedding_service.get_provider_info()
            components["embedding_service"] = f"ready ({embedding_info['provider_type']})"
        except Exception as e:
            components["embedding_service"] = f"error: {str(e)}"
        
        try:
            vector_store = get_vector_store()
            components["vector_store"] = "ready"
            components["documents_indexed"] = vector_store.get_document_count()
        except Exception as e:
            components["vector_store"] = f"error: {str(e)}"
            components["documents_indexed"] = 0
        
        try:
            answer_generator = get_answer_generator()
            provider_info = answer_generator.get_provider_info()
            components["llm_service"] = f"ready ({provider_info['provider_type']})" if provider_info['is_available'] else "unavailable"
        except Exception as e:
            components["llm_service"] = f"error: {str(e)}"
        
        # Determine overall status
        has_errors = any("error:" in str(status) for status in components.values())
        overall_status = "unhealthy" if has_errors else "healthy"
        
        return HealthResponse(
            status=overall_status,
            version="0.1.0",
            components=components
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version="0.1.0",
            components={
                "error": str(e)
            }
        )


@app.post("/upload", 
          response_model=UploadResponse,
          status_code=201,
          summary="Upload Document",
          description="Upload and process a PDF document for querying",
          responses={
              201: {"description": "Document uploaded and processed successfully"},
              400: {"description": "Invalid file or request", "model": ErrorResponse},
              409: {"description": "Document already exists", "model": ErrorResponse},
              413: {"description": "File too large", "model": ErrorResponse},
              422: {"description": "Document processing failed", "model": ErrorResponse},
              500: {"description": "Internal server error", "model": ErrorResponse},
              507: {"description": "Insufficient storage space", "model": ErrorResponse}
          })
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload and process"),
    replace_existing: bool = False,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
) -> UploadResponse:
    """Upload and process a PDF document."""
    logger.info("Document upload requested", extra={"filename": file.filename, "replace_existing": replace_existing})
    
    # Validate file is provided
    if not file.filename:
        logger.warning("No filename provided")
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        logger.warning("Invalid file type uploaded", extra={"filename": file.filename})
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check for duplicate document
    vector_store = get_vector_store()
    document_name = file.filename
    
    # Check if document already exists
    if vector_store.document_exists(document_name):
        if not replace_existing:
            logger.warning("Duplicate document upload attempted", extra={"filename": file.filename})
            raise HTTPException(
                status_code=409,
                detail=f"Document '{file.filename}' already exists. Set replace_existing=true to replace it."
            )
        else:
            # Delete existing document
            deleted_count = vector_store.delete_document_by_name(document_name)
            logger.info(f"Deleted existing document", extra={"filename": file.filename, "chunks_deleted": deleted_count})
            # Save the updated index
            vector_store.save_index()
    
    # Validate file size (if available)
    if hasattr(file, 'size') and file.size is not None:
        if file.size == 0:
            logger.warning("Empty file uploaded", extra={"filename": file.filename})
            raise HTTPException(status_code=400, detail="File is empty")
        
        if file.size > config.max_file_size_mb * 1024 * 1024:
            logger.warning("File too large", extra={"filename": file.filename, "size": file.size})
            raise HTTPException(
                status_code=413, 
                detail=f"File size exceeds {config.max_file_size_mb}MB limit"
            )
    
    temp_file_path = None
    try:
        # Read file content
        content = await file.read()
        
        # Validate content is not empty
        if not content:
            logger.warning("Empty file content", extra={"filename": file.filename})
            raise HTTPException(status_code=400, detail="File content is empty")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Use simple document name without UUID
        document_id = document_name  # Use filename as ID for clarity
        
        # Process document
        success = ingestion_service.process_document(temp_file_path, document_name)
        
        if not success:
            logger.error("Document processing failed", extra={"filename": file.filename})
            raise HTTPException(status_code=422, detail="Failed to process document content")
        
        # Get processing stats to determine chunks created
        stats = ingestion_service.get_processing_stats()
        total_chunks = stats.get("total_chunks", 0)
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        logger.info(
            "Document processed successfully",
            extra={
                "filename": file.filename,
                "document_id": document_id,
                "document_name": document_name,
                "total_chunks": total_chunks,
                "replaced": replace_existing
            }
        )
        
        return UploadResponse(
            message="Document uploaded and processed successfully" if not replace_existing else "Document replaced successfully",
            document_id=document_id,
            chunks_created=total_chunks
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        raise
    except Exception as e:
        # Clean up temporary file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        
        logger.error("Document processing failed", extra={"filename": file.filename, "error": str(e)})
        
        # Provide more specific error messages based on exception type
        if "PDF" in str(e) and ("encrypted" in str(e).lower() or "password" in str(e).lower()):
            raise HTTPException(status_code=422, detail="Cannot process encrypted or password-protected PDF files")
        elif "PDF" in str(e) and "corrupted" in str(e).lower():
            raise HTTPException(status_code=422, detail="PDF file appears to be corrupted or invalid")
        elif "No space left" in str(e) or "Disk full" in str(e):
            raise HTTPException(status_code=507, detail="Insufficient storage space")
        else:
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@app.post("/query", 
          response_model=QueryResponse,
          summary="Query Documents",
          description="Ask a natural language question about uploaded documents",
          responses={
              200: {"description": "Query processed successfully"},
              400: {"description": "Invalid query or parameters", "model": ErrorResponse},
              401: {"description": "LLM service authentication failed", "model": ErrorResponse},
              404: {"description": "No documents available", "model": ErrorResponse},
              429: {"description": "Rate limit exceeded", "model": ErrorResponse},
              500: {"description": "Internal server error", "model": ErrorResponse},
              504: {"description": "Query processing timeout", "model": ErrorResponse}
          })
async def query_documents(
    request: QueryRequest,
    query_engine: QueryEngine = Depends(get_query_engine)
) -> QueryResponse:
    """Query uploaded documents with a natural language question."""
    logger.info("Query requested", extra={"question": request.question})
    
    # Validate input
    if not request.question or not request.question.strip():
        logger.warning("Empty query submitted")
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Validate question length (reasonable limit)
    if len(request.question.strip()) > 1000:
        logger.warning("Query too long", extra={"question_length": len(request.question)})
        raise HTTPException(status_code=400, detail="Question is too long (maximum 1000 characters)")
    
    # Validate top_k parameter if provided
    if request.top_k is not None:
        if request.top_k <= 0:
            raise HTTPException(status_code=400, detail="top_k must be positive")
        if request.top_k > 50:  # Reasonable upper limit
            raise HTTPException(status_code=400, detail="top_k cannot exceed 50")
    
    try:
        # Use configured top_k if not provided in request
        top_k = request.top_k or config.top_k_results
        
        # Check if any documents are indexed
        vector_store = get_vector_store()
        if vector_store.get_document_count() == 0:
            logger.warning("No documents indexed for query")
            raise HTTPException(
                status_code=404, 
                detail="No documents have been uploaded yet. Please upload documents before querying."
            )
        
        # Process query with optional document filter
        result = await query_engine.process_query(
            request.question.strip(), 
            top_k, 
            document_name=request.document_name
        )
        
        logger.info(
            "Query processed successfully",
            extra={
                "question": request.question,
                "document_filter": request.document_name,
                "confidence_score": result.confidence_score,
                "sources_count": len(result.source_references)
            }
        )
        
        return QueryResponse(
            answer=result.answer,
            source_references=result.source_references,
            confidence_score=result.confidence_score
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("Query processing failed", extra={"question": request.question, "error": str(e)})
        
        # Provide more specific error messages based on exception type
        if "API" in str(e) and ("rate limit" in str(e).lower() or "quota" in str(e).lower()):
            raise HTTPException(status_code=429, detail="API rate limit exceeded. Please try again later.")
        elif "API" in str(e) and ("authentication" in str(e).lower() or "unauthorized" in str(e).lower()):
            raise HTTPException(status_code=401, detail="LLM service authentication failed")
        elif "timeout" in str(e).lower():
            raise HTTPException(status_code=504, detail="Query processing timed out")
        else:
            raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Document QA RAG Agent", version="0.1.0")
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error("Configuration validation failed", error=str(e))
        raise
    
    # Create data directories
    os.makedirs(os.path.dirname(config.vector_store_path), exist_ok=True)
    os.makedirs(os.path.dirname(config.metadata_path), exist_ok=True)
    
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Document QA RAG Agent")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.app:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        log_level=config.log_level.lower()
    )