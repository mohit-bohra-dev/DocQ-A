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
│  Streamlit UI   │    │   FastAPI App   │    ┌─────────────────┐
└─────────────────┘    └─────────────────┘    │   Query Engine  │
         │                       │             └─────────────────┘
         │              ┌─────────────────┐             │
         │              │ Ingestion Svc   │    ┌─────────────────┐
         │              └─────────────────┘    │ Answer Generator│
         │                       │             └─────────────────┘
         │              ┌─────────────────┐             │
         └──────────────│ Embedding Svc   │    ┌─────────────────┐
                        └─────────────────┘    │   Vector Store  │
                                               └─────────────────┘
```

### Key Architectural Principles

- **Stateless Design**: API endpoints are stateless where possible, with state managed in the vector store
- **Modular Components**: Each component has a single responsibility and clear interfaces
- **Provider Abstraction**: LLM and embedding providers are abstracted for easy switching
- **Vector Store Abstraction**: Vector database backends (FAISS, Qdrant) are abstracted through a unified interface
- **Flexible Persistence**: Support for both local persistence (FAISS) and cloud-native vector databases (Qdrant)

## Components and Interfaces

### FastAPI Application (`app.py`)
- **Purpose**: HTTP API layer and request routing
- **Endpoints**:
  - `POST /upload`: Upload and process PDF documents
  - `POST /query`: Ask questions about uploaded documents
  - `GET /health`: System health check
- **Dependencies**: Ingestion Service, Query Engine

### Streamlit UI (`streamlit_app.py`)
- **Purpose**: Web-based user interface for document upload and querying
- **Key Features**:
  - File upload widget for PDF documents
  - Text input for questions with submit button
  - Real-time processing status and progress indicators
  - Formatted display of answers with source references
  - Session-based conversation history
  - Document management interface
- **Dependencies**: FastAPI backend via HTTP requests

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
- **Purpose**: Abstract interface for vector database operations with multiple backend support
- **Key Functions**:
  - `add_embeddings(embeddings: List[List[float]], metadata: List[ChunkMetadata]) -> None`
  - `search_similar(query_embedding: List[float], top_k: int) -> List[SearchResult]`
  - `save_index(file_path: str) -> None` (FAISS only)
  - `load_index(file_path: str) -> None` (FAISS only)
- **Implementations**:
  - **FAISSVectorStore**: Local FAISS index files and JSON metadata
  - **QdrantVectorStore**: Qdrant client with collection management and cloud support

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

### VectorStoreConfig
```python
@dataclass
class VectorStoreConfig:
    backend: str  # "faiss" or "qdrant"
    # FAISS-specific
    index_path: Optional[str] = None
    metadata_path: Optional[str] = None
    # Qdrant-specific
    host: Optional[str] = None
    port: Optional[int] = None
    api_key: Optional[str] = None
    collection_name: Optional[str] = None
    use_cloud: bool = False
    vector_dimension: int = 768
    distance_metric: str = "cosine"
```

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

### UIState
```python
@dataclass
class UIState:
    uploaded_documents: List[str]
    conversation_history: List[ConversationEntry]
    current_question: str
    processing_status: ProcessingStatus
```

### ConversationEntry
```python
@dataclass
class ConversationEntry:
    question: str
    answer: str
    source_references: List[SourceReference]
    timestamp: datetime
```

### ProcessingStatus
```python
class ProcessingStatus(Enum):
    IDLE = "idle"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    QUERYING = "querying"
    ERROR = "error"
```

## Vector Store Architecture

The system implements a pluggable vector store architecture that supports multiple backends through a unified interface. This design allows seamless switching between FAISS (local, file-based) and Qdrant (cloud-native, scalable) without changing application code.

### Abstract Vector Store Interface

```python
class VectorStore(ABC):
    @abstractmethod
    def add_embeddings(self, embeddings: List[List[float]], metadata: List[ChunkMetadata]) -> None:
        """Add embeddings with metadata to the vector store"""
        pass
    
    @abstractmethod
    def search_similar(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """Search for similar vectors and return top-k results"""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the vector store (create collections, load indices, etc.)"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the vector store is accessible and healthy"""
        pass
```

### FAISS Implementation

The FAISS implementation provides local, file-based vector storage suitable for development and single-machine deployments:

- **Index Type**: Uses FAISS IndexFlatL2 for exact similarity search
- **Metadata Storage**: Separate JSON file for chunk metadata
- **Persistence**: Manual save/load operations to disk
- **Advantages**: No external dependencies, fast for small-to-medium datasets, simple setup
- **Limitations**: Single-machine only, manual scaling, limited query features

### Qdrant Implementation

The Qdrant implementation provides cloud-native vector storage with advanced features:

- **Connection Modes**: 
  - Local Qdrant instance (Docker or standalone)
  - Qdrant Cloud with API key authentication
- **Collection Management**:
  - Automatic collection creation with configurable vector dimensions
  - Distance metric configuration (cosine, euclidean, dot product)
  - Payload schema for metadata storage
- **Metadata Storage**: Stored as payload within Qdrant (chunk_id, page_number, document_name, chunk_text)
- **Advantages**: Horizontal scaling, advanced filtering, cloud-native, production-ready
- **Features**: Built-in replication, snapshots, filtering by metadata, hybrid search capabilities

### Configuration Strategy

Vector store selection is determined at runtime through configuration:

```python
# Environment variables
VECTOR_STORE_BACKEND=qdrant  # or "faiss"

# Qdrant-specific
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key  # Optional, for Qdrant Cloud
QDRANT_COLLECTION=document_qa
QDRANT_USE_CLOUD=false

# FAISS-specific
FAISS_INDEX_PATH=./data/faiss_index
FAISS_METADATA_PATH=./data/metadata.json
```

### Migration Path

The abstraction enables smooth migration between backends:

1. **Development**: Start with FAISS for simplicity
2. **Testing**: Switch to local Qdrant for production-like testing
3. **Production**: Deploy with Qdrant Cloud for scalability
4. **Data Migration**: Export embeddings from FAISS, import to Qdrant using the same metadata structure

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

**Property 13: UI feedback consistency**
*For any* user action in the Streamlit interface, appropriate visual feedback should be provided during processing
**Validates: Requirements 8.2, 8.4**

**Property 14: UI error handling completeness**
*For any* error condition, the Streamlit interface should display user-friendly error messages and maintain system stability
**Validates: Requirements 8.4**

**Property 15: Conversation history persistence**
*For any* question-answer interaction within a session, the conversation should be maintained in the UI history
**Validates: Requirements 8.7**

**Property 16: Source reference formatting**
*For any* generated answer with source references, the UI should display properly formatted and accessible reference information
**Validates: Requirements 8.6**

**Property 17: Vector store backend interchangeability**
*For any* vector store operation (add, search, initialize), both FAISS and Qdrant backends should produce equivalent results and maintain consistent API contracts
**Validates: Requirements 9.1, 9.6**

**Property 18: Qdrant configuration flexibility**
*For any* valid Qdrant configuration (local instance, cloud instance, different connection parameters), the system should successfully connect and operate correctly
**Validates: Requirements 9.2, 9.8, 9.9**

**Property 19: Qdrant collection management**
*For any* document ingestion operation with Qdrant, collections should be created or updated with correct vector dimensions and distance metrics matching the embedding model
**Validates: Requirements 9.3**

**Property 20: Qdrant metadata persistence**
*For any* embedding stored in Qdrant with metadata, retrieving the embedding should return all metadata fields (chunk_id, page_number, document_name, chunk_text) intact
**Validates: Requirements 9.4**

**Property 21: Qdrant search consistency**
*For any* similarity search with parameter k using Qdrant, the system should return exactly k results with complete metadata, ordered by similarity score
**Validates: Requirements 9.5**

**Property 22: Qdrant error handling**
*For any* Qdrant-specific error condition (connection failure, timeout, API error), the system should handle the error gracefully, log appropriate information, and return proper error responses
**Validates: Requirements 9.7**

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
- **Qdrant connection failures**: Retry with exponential backoff, log connection details, return HTTP 503
- **Qdrant timeout errors**: Log timeout duration, return HTTP 504
- **Qdrant API errors**: Log error response, return HTTP 502
- **Qdrant authentication failures**: Log security error, return HTTP 401
- **Collection not found**: Create collection automatically, log info message

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