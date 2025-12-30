"""FastAPI application for the Document QA RAG Agent."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import tempfile
import uuid

from .config import config
from .logging_config import configure_logging, get_logger
from .models import QueryResult, SourceReference

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


# Request/Response models
class QueryRequest(BaseModel):
    """Request model for querying documents."""
    question: str
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    """Response model for query results."""
    answer: str
    source_references: List[SourceReference]
    confidence_score: float


class UploadResponse(BaseModel):
    """Response model for document upload."""
    message: str
    document_id: str
    chunks_created: int


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    components: dict


# Dependency injection placeholders
# These will be implemented in later tasks
def get_ingestion_service():
    """Get the document ingestion service."""
    # TODO: Implement in task 4
    raise HTTPException(status_code=501, detail="Ingestion service not implemented yet")


def get_query_engine():
    """Get the query engine."""
    # TODO: Implement in task 5
    raise HTTPException(status_code=501, detail="Query engine not implemented yet")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    logger.info("Health check requested")
    
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        components={
            "vector_store": "not_implemented",
            "embedding_service": "not_implemented",
            "llm_service": "not_implemented",
        }
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    ingestion_service=Depends(get_ingestion_service)
) -> UploadResponse:
    """Upload and process a PDF document."""
    logger.info("Document upload requested", filename=file.filename)
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        logger.warning("Invalid file type uploaded", filename=file.filename)
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Validate file size
    if file.size and file.size > config.max_file_size_mb * 1024 * 1024:
        logger.warning("File too large", filename=file.filename, size=file.size)
        raise HTTPException(
            status_code=413, 
            detail=f"File size exceeds {config.max_file_size_mb}MB limit"
        )
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Process document (will be implemented in task 4)
        chunks_created = await ingestion_service.process_document(
            temp_file_path, 
            file.filename, 
            document_id
        )
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        logger.info(
            "Document processed successfully",
            filename=file.filename,
            document_id=document_id,
            chunks_created=chunks_created
        )
        
        return UploadResponse(
            message="Document uploaded and processed successfully",
            document_id=document_id,
            chunks_created=chunks_created
        )
    
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        logger.error("Document processing failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    query_engine=Depends(get_query_engine)
) -> QueryResponse:
    """Query uploaded documents with a natural language question."""
    logger.info("Query requested", question=request.question)
    
    # Validate input
    if not request.question or not request.question.strip():
        logger.warning("Empty query submitted")
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Use configured top_k if not provided in request
        top_k = request.top_k or config.top_k_results
        
        # Process query (will be implemented in task 5)
        result = await query_engine.process_query(request.question, top_k)
        
        logger.info(
            "Query processed successfully",
            question=request.question,
            confidence_score=result.confidence_score,
            sources_count=len(result.source_references)
        )
        
        return QueryResponse(
            answer=result.answer,
            source_references=result.source_references,
            confidence_score=result.confidence_score
        )
    
    except Exception as e:
        logger.error("Query processing failed", question=request.question, error=str(e))
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