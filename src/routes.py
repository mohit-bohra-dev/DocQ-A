"""API routes for the Document QA RAG Agent."""

import os
import shutil
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from .config import config
from .logging_config import get_logger
from .models import SourceReference
from .query_engine import QueryEngine
from .answer_generator import AnswerGenerator
from .embeddings import EmbeddingService
from .interfaces import VectorStore
from .vector_store import FAISSVectorStore
from .qdrant_vector_store import QdrantVectorStore
from .ingestion import DocumentIngestionService

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request model for querying documents."""
    question: str
    top_k: Optional[int] = None
    document_name: Optional[str] = None  # Filter by specific document

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


# ---------------------------------------------------------------------------
# Service singletons / dependency providers
# ---------------------------------------------------------------------------

_embedding_service = None
_vector_store = None
_answer_generator = None
_query_engine = None
_ingestion_service = None


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(config)
    return _embedding_service


def get_vector_store() -> VectorStore:
    """Get the vector store singleton (FAISS or Qdrant based on config)."""
    global _vector_store
    if _vector_store is None:
        backend = config.vector_store_backend
        if backend == "qdrant":
            logger.info("Initialising Qdrant vector store", extra={"collection": config.qdrant_collection_name})
            embedding_service = get_embedding_service()
            dimension = embedding_service.get_embedding_dimension()
            _vector_store = QdrantVectorStore(
                dimension=dimension,
                collection_name=config.qdrant_collection_name,
                host=config.qdrant_host,
                port=config.qdrant_port,
                url=config.qdrant_url,
                api_key=config.qdrant_api_key,
            )
        else:
            logger.info("Initialising FAISS vector store")
            embedding_service = get_embedding_service()
            dimension = embedding_service.get_embedding_dimension()
            _vector_store = FAISSVectorStore(
                dimension=dimension,
                index_path=config.vector_store_path,
                metadata_path=config.metadata_path,
            )
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of all system components",
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.info("Health check requested")

    try:
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
            components["vector_store_backend"] = config.vector_store_backend
            components["documents_indexed"] = vector_store.get_document_count()
        except Exception as e:
            components["vector_store"] = f"error: {str(e)}"
            components["vector_store_backend"] = config.vector_store_backend
            components["documents_indexed"] = 0

        try:
            answer_generator = get_answer_generator()
            provider_info = answer_generator.get_provider_info()
            components["llm_service"] = (
                f"ready ({provider_info['provider_type']})"
                if provider_info["is_available"]
                else "unavailable"
            )
        except Exception as e:
            components["llm_service"] = f"error: {str(e)}"

        has_errors = any("error:" in str(status) for status in components.values())
        overall_status = "unhealthy" if has_errors else "healthy"

        return HealthResponse(status=overall_status, version="0.1.0", components=components)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(status="unhealthy", version="0.1.0", components={"error": str(e)})


@router.get(
    "/documents",
    summary="List Documents",
    description="Get list of all uploaded documents",
)
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

        return {"total_documents": len(documents), "documents": documents}
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.delete(
    "/documents/{document_name}",
    summary="Delete Document",
    description="Delete a specific document and all its chunks",
)
async def delete_document(document_name: str) -> Dict[str, Any]:
    """Delete a document from the system."""
    logger.info("Document deletion requested", extra={"document_name": document_name})

    try:
        vector_store = get_vector_store()

        if not vector_store.document_exists(document_name):
            raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found")

        deleted_count = vector_store.delete_document_by_name(document_name)
        vector_store.save_index()

        logger.info(
            "Document deleted successfully",
            extra={"document_name": document_name, "chunks_deleted": deleted_count},
        )

        return {
            "message": f"Document '{document_name}' deleted successfully",
            "chunks_deleted": deleted_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post(
    "/upload",
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
        507: {"description": "Insufficient storage space", "model": ErrorResponse},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload and process"),
    replace_existing: bool = False,
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service),
) -> UploadResponse:
    """Upload and process a PDF document."""
    logger.info(
        "Document upload requested",
        extra={"filename": file.filename, "replace_existing": replace_existing},
    )

    if not file.filename:
        logger.warning("No filename provided")
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".pdf"):
        logger.warning("Invalid file type uploaded", extra={"filename": file.filename})
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    vector_store = get_vector_store()
    document_name = file.filename

    if vector_store.document_exists(document_name):
        if not replace_existing:
            logger.warning("Duplicate document upload attempted", extra={"filename": file.filename})
            raise HTTPException(
                status_code=409,
                detail=f"Document '{file.filename}' already exists. Set replace_existing=true to replace it.",
            )
        else:
            deleted_count = vector_store.delete_document_by_name(document_name)
            logger.info(
                "Deleted existing document",
                extra={"filename": file.filename, "chunks_deleted": deleted_count},
            )
            vector_store.save_index()

    if hasattr(file, "size") and file.size is not None:
        if file.size == 0:
            logger.warning("Empty file uploaded", extra={"filename": file.filename})
            raise HTTPException(status_code=400, detail="File is empty")

        if file.size > config.max_file_size_mb * 1024 * 1024:
            logger.warning("File too large", extra={"filename": file.filename, "size": file.size})
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds {config.max_file_size_mb}MB limit",
            )

    temp_file_path = None
    try:
        content = await file.read()

        if not content:
            logger.warning("Empty file content", extra={"filename": file.filename})
            raise HTTPException(status_code=400, detail="File content is empty")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        os.makedirs(config.uploads_dir, exist_ok=True)
        upload_dest = os.path.join(config.uploads_dir, document_name)
        shutil.copy2(temp_file_path, upload_dest)

        document_id = document_name

        success = ingestion_service.process_document(temp_file_path, document_name)

        if not success:
            logger.error("Document processing failed", extra={"filename": file.filename})
            raise HTTPException(status_code=422, detail="Failed to process document content")

        stats = ingestion_service.get_processing_stats()
        total_chunks = stats.get("total_chunks", 0)

        os.unlink(temp_file_path)

        logger.info(
            "Document processed successfully",
            extra={
                "filename": file.filename,
                "document_id": document_id,
                "document_name": document_name,
                "total_chunks": total_chunks,
                "replaced": replace_existing,
            },
        )

        return UploadResponse(
            message=(
                "Document uploaded and processed successfully"
                if not replace_existing
                else "Document replaced successfully"
            ),
            document_id=document_id,
            chunks_created=total_chunks,
        )

    except HTTPException:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
        raise
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

        logger.error("Document processing failed", extra={"filename": file.filename, "error": str(e)})

        if "PDF" in str(e) and ("encrypted" in str(e).lower() or "password" in str(e).lower()):
            raise HTTPException(status_code=422, detail="Cannot process encrypted or password-protected PDF files")
        elif "PDF" in str(e) and "corrupted" in str(e).lower():
            raise HTTPException(status_code=422, detail="PDF file appears to be corrupted or invalid")
        elif "No space left" in str(e) or "Disk full" in str(e):
            raise HTTPException(status_code=507, detail="Insufficient storage space")
        else:
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.get(
    "/documents/{document_name}/file",
    summary="Download Document",
    description="Serve the original PDF file for a given document",
)
async def get_document_file(document_name: str):
    """Return the original PDF file for browser viewing."""
    file_path = os.path.join(config.uploads_dir, document_name)
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Original file for '{document_name}' is not available. "
                "Only documents uploaded after this feature was enabled can be viewed."
            ),
        )
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=document_name,
        headers={"Content-Disposition": "inline"},
    )


@router.post(
    "/query",
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
        504: {"description": "Query processing timeout", "model": ErrorResponse},
    },
)
async def query_documents(
    request: QueryRequest,
    query_engine: QueryEngine = Depends(get_query_engine),
) -> QueryResponse:
    """Query uploaded documents with a natural language question."""
    logger.info("Query requested", extra={"question": request.question})

    if not request.question or not request.question.strip():
        logger.warning("Empty query submitted")
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if len(request.question.strip()) > 1000:
        logger.warning("Query too long", extra={"question_length": len(request.question)})
        raise HTTPException(status_code=400, detail="Question is too long (maximum 1000 characters)")

    if request.top_k is not None:
        if request.top_k <= 0:
            raise HTTPException(status_code=400, detail="top_k must be positive")
        if request.top_k > 50:
            raise HTTPException(status_code=400, detail="top_k cannot exceed 50")

    try:
        top_k = request.top_k or config.top_k_results

        vector_store = get_vector_store()
        if vector_store.get_document_count() == 0:
            logger.warning("No documents indexed for query")
            raise HTTPException(
                status_code=404,
                detail="No documents have been uploaded yet. Please upload documents before querying.",
            )

        result = await query_engine.process_query(
            request.question.strip(),
            top_k,
            document_name=request.document_name,
        )

        logger.info(
            "Query processed successfully",
            extra={
                "question": request.question,
                "document_filter": request.document_name,
                "confidence_score": result.confidence_score,
                "sources_count": len(result.source_references),
            },
        )

        return QueryResponse(
            answer=result.answer,
            source_references=result.source_references,
            confidence_score=result.confidence_score,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query processing failed", extra={"question": request.question, "error": str(e)})

        if "API" in str(e) and ("rate limit" in str(e).lower() or "quota" in str(e).lower()):
            raise HTTPException(status_code=429, detail="API rate limit exceeded. Please try again later.")
        elif "API" in str(e) and ("authentication" in str(e).lower() or "unauthorized" in str(e).lower()):
            raise HTTPException(status_code=401, detail="LLM service authentication failed")
        elif "timeout" in str(e).lower():
            raise HTTPException(status_code=504, detail="Query processing timed out")
        else:
            raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")
