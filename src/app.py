"""FastAPI application for the Document QA RAG Agent."""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import config
from .logging_config import configure_logging, get_logger
from .routes import router

# Configure logging
configure_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Document QA RAG Agent",
    description="A Document Question-Answering AI Agent using Retrieval-Augmented Generation",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning("Request validation failed", extra={"errors": exc.errors()})
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors."""
    logger.error("Value error occurred", extra={"error": str(exc)})
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_code": "VALUE_ERROR"},
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle file not found errors."""
    logger.error("File not found", extra={"error": str(exc)})
    return JSONResponse(
        status_code=404,
        content={"detail": "Requested file not found", "error_code": "FILE_NOT_FOUND"},
    )


# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Document QA RAG Agent", version="0.1.0")

    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error("Configuration validation failed", error=str(e))
        raise

    os.makedirs(os.path.dirname(config.vector_store_path), exist_ok=True)
    os.makedirs(os.path.dirname(config.metadata_path), exist_ok=True)
    os.makedirs(config.uploads_dir, exist_ok=True)

    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Document QA RAG Agent")


# ---------------------------------------------------------------------------
# Register routes
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.app:app",
        host=config.api_host,
        port=config.api_port,
        reload=True,
        log_level=config.log_level.lower(),
    )