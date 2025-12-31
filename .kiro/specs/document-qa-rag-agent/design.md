# Design Document

## Overview

The Document Question-Answering AI Agent implements a Retrieval-Augmented Generation (RAG) pipeline that enables users to upload PDF documents and ask natural language questions with grounded, accurate responses. The system follows a modular architecture with clear separation between document ingestion, vector storage, retrieval, and answer generation components.

The RAG pipeline consists of two main phases:
1. **Ingestion Phase**: PDF → Text Extraction → Chunking → Embeddings → Vector Database
2. **Query Phase**: User Question → Embedding → Similarity Search → Context Retrieval → LLM Answer Generation

## Architecture

The system follows a layered architecture with the following components:

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Query Engine  │
└─────────────────┘    └─────────────────┘
         │                       │
┌─────────────────┐    ┌─────────────────┐
│ Ingestion Svc   │    │ Answer Generator│
└─────────────────┘    └─────────────────┘
         │                       │
┌─────────────────┐    ┌─────────────────┐
│ Embedding Svc   │    │   Vector Store  │
└─────────────────┘    └─────────────────┘
```

### Key Architectural Principles

- **Stateless Design**: API endpoints are stateless where possible, with state managed in the vector store
- **Modular Components**: Each component has a single responsibility and clear interfaces
- **Provider Abstraction**: LLM and embedding providers are abstracted for easy switching
- **Local Persistence**: All data is stored locally using FAISS for vector operations and file system for metadata

## Components and Interfaces

### FastAPI Application (`app.py`)
- **Purpose**: HTTP API layer and request routing
- **Endpoints**:
  - `POST /upload`: Upload and process PDF documents
  - `POST /query`: Ask questions about uploaded documents
  - `GET /health`: System health check
- **Dependencies**: Ingestion Service, Query Engine

### Document Ingestion Service (`ingest.py`)
- **Purpose**: PDF processing and document indexing
- **Key Functions**:
  - `extract_text_from_pdf(file_path: str) -> str`
  - `chunk_text(text: str, chunk_size: int, overlap: int) -> List[TextChunk]`
  - `process_document(file_path: str, doc_name: str) -> bool`
- **Dependencies**: Embedding Service, Vector Store

### Query Engine (`query.py`)
- **Purpose**: Question processing and context retrieval
- **Key Functions**:
  - `process_query(question: str, top_k: int) -> QueryResult`
  - `retrieve_context(query_embedding: List[float], top_k: int) -> List[TextChunk]`
- **Dependencies**: Embedding Service, Vector Store, Answer Generator

### Vector Store (`vector_store.py`)
- **Purpose**: FAISS-based vector operations and persistence
- **Key Functions**:
  - `add_embeddings(embeddings: List[List[float]], metadata: List[ChunkMetadata]) -> None`
  - `search_similar(query_embedding: List[float], top_k: int) -> List[SearchResult]`
  - `save_index(file_path: str) -> None`
  - `load_index(file_path: str) -> None`
- **Storage**: Local FAISS index files and JSON metadata

### Embedding Service (`embeddings.py`)
- **Purpose**: Text-to-vector conversion using consistent embedding models
- **Key Functions**:
  - `generate_embedding(text: str) -> List[float]`
  - `generate_batch_embeddings(texts: List[str]) -> List[List[float]]`
- **Provider Support**: Configurable embedding models (OpenAI, Sentence Transformers, etc.)

### Answer Generator (`prompts.py`)
- **Purpose**: LLM-powered response generation with grounding
- **Key Functions**:
  - `generate_answer(question: str, context: List[TextChunk]) -> AnswerResult`
  - `construct_grounded_prompt(question: str, context: List[TextChunk]) -> str`
- **Provider Support**: Abstracted LLM interface (Gemini, OpenAI, etc.)

## Data Models

### TextChunk
```python
@dataclass
class TextChunk:
    chunk_id: str
    text: str
    page_number: int
    document_name: str
    start_char: int
    end_char: int
```

### ChunkMetadata
```python
@dataclass
class ChunkMetadata:
    chunk_id: str
    document_name: str
    page_number: int
    chunk_index: int
    created_at: datetime
```

### SearchResult
```python
@dataclass
class SearchResult:
    chunk: TextChunk
    similarity_score: float
    metadata: ChunkMetadata
```

### QueryResult
```python
@dataclass
class QueryResult:
    answer: str
    source_references: List[SourceReference]
    confidence_score: float
    retrieved_chunks: List[TextChunk]
```

### SourceReference
```python
@dataclass
class SourceReference:
    document_name: str
    page_number: int
    chunk_id: str
```
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, several properties can be consolidated to eliminate redundancy:
- Properties 1.4 and 5.1 both test persistence functionality and can be combined into a comprehensive persistence property
- Properties 3.1, 3.2, and 3.3 all relate to source reference handling and can be combined
- Properties 5.2 and 5.4 both test data integrity and can be consolidated

### Core Properties

**Property 1: Text extraction completeness**
*For any* valid PDF document, text extraction should capture all readable text content from every page
**Validates: Requirements 1.1**

**Property 2: Chunking consistency**
*For any* text input and chunking parameters, the chunking algorithm should produce chunks that respect size limits and overlap requirements
**Validates: Requirements 1.2**

**Property 3: Embedding generation consistency**
*For any* set of text chunks, the embedding generation should produce vectors with consistent dimensions and one embedding per chunk
**Validates: Requirements 1.3**

**Property 4: Persistence round-trip integrity**
*For any* set of embeddings and metadata, storing and then retrieving the data should yield identical results
**Validates: Requirements 1.4, 5.1, 5.2, 5.4**

**Property 5: Error handling completeness**
*For any* invalid input or system error condition, the system should log appropriate error information and return proper error responses
**Validates: Requirements 1.5, 4.2, 5.3**

**Property 6: Query embedding consistency**
*For any* user question, the generated embedding should have the same dimensions as document chunk embeddings
**Validates: Requirements 2.1**

**Property 7: Retrieval result ordering**
*For any* similarity search with parameter k, the system should return exactly k results ordered by similarity score
**Validates: Requirements 2.2**

**Property 8: Prompt construction completeness**
*For any* question and retrieved context, the generated prompt should contain both the original question and all retrieved chunk content
**Validates: Requirements 2.3**

**Property 9: Source reference completeness**
*For any* generated answer with retrieved chunks, the response should include properly formatted source references for all contributing chunks
**Validates: Requirements 3.1, 3.2, 3.3**

**Property 10: Configuration parameter effectiveness**
*For any* valid configuration change (chunk size, overlap, retrieval count), the system behavior should reflect the new parameters
**Validates: Requirements 4.5**

**Property 11: Provider abstraction compatibility**
*For any* supported LLM or embedding provider, swapping providers should not break core functionality
**Validates: Requirements 7.2**

**Property 12: Logging operation coverage**
*For any* system operation, appropriate log entries should be generated with sufficient detail for debugging
**Validates: Requirements 4.3**

## Error Handling

The system implements comprehensive error handling across all components:

### PDF Processing Errors
- **Invalid PDF files**: Return HTTP 400 with descriptive error message
- **Corrupted files**: Log error details and return HTTP 422
- **Large files**: Implement size limits and return HTTP 413 if exceeded
- **Text extraction failures**: Log specific error and return HTTP 500

### Vector Store Errors
- **FAISS index corruption**: Attempt recovery, log error, return HTTP 500
- **Disk space issues**: Check available space, log warning, return HTTP 507
- **Permission errors**: Log security error, return HTTP 500
- **Index not found**: Initialize new index, log info message

### LLM Provider Errors
- **API rate limits**: Implement exponential backoff, return HTTP 429
- **Authentication failures**: Log security error, return HTTP 401
- **Service unavailable**: Log provider error, return HTTP 503
- **Invalid responses**: Log response details, return HTTP 502

### Input Validation Errors
- **Empty questions**: Return HTTP 400 with validation message
- **Malformed requests**: Return HTTP 400 with specific field errors
- **Missing parameters**: Return HTTP 422 with required field list

## Testing Strategy

The system employs a dual testing approach combining unit tests and property-based tests:

### Unit Testing Approach
- **Component isolation**: Test individual functions and classes in isolation
- **Integration points**: Verify correct interaction between components
- **Error conditions**: Test specific error scenarios and edge cases
- **API endpoints**: Validate request/response handling and status codes

### Property-Based Testing Approach
- **Framework**: Use Hypothesis for Python property-based testing
- **Test iterations**: Configure minimum 100 iterations per property test
- **Smart generators**: Create constrained generators for valid PDF content, text chunks, and embeddings
- **Universal properties**: Verify properties hold across all valid inputs

### Testing Framework Configuration
- **Unit tests**: pytest with coverage reporting
- **Property tests**: Hypothesis with custom strategies
- **Integration tests**: FastAPI TestClient for end-to-end API testing
- **Performance tests**: Basic load testing for key operations

### Test Data Management
- **Sample PDFs**: Curated set of test documents with known content
- **Synthetic data**: Generated text content for property testing
- **Edge cases**: Empty documents, single-page PDFs, large documents
- **Error scenarios**: Corrupted files, invalid formats, network failures

The testing strategy ensures both specific functionality works correctly (unit tests) and general system properties hold across all inputs (property tests), providing comprehensive validation of system correctness.