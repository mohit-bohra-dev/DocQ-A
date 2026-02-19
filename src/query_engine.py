"""Query engine for processing questions and retrieving context."""

import logging
from typing import List, Optional

try:
    from .interfaces import VectorStore
    from .models import QueryResult, TextChunk, SourceReference
    from .embeddings import EmbeddingService
    from .answer_generator import AnswerGenerator
    from .config import RAGConfig
except ImportError:
    from interfaces import VectorStore
    from models import QueryResult, TextChunk, SourceReference
    from embeddings import EmbeddingService
    from answer_generator import AnswerGenerator
    from config import RAGConfig

logger = logging.getLogger(__name__)


class QueryEngine:
    """Main query processing engine that coordinates retrieval and answer generation."""
    
    def __init__(self, vector_store: VectorStore, embedding_service: EmbeddingService, 
                 answer_generator: AnswerGenerator, config: RAGConfig):
        """
        Initialize the query engine.
        
        Args:
            vector_store: Vector store for similarity search
            embedding_service: Service for generating query embeddings
            answer_generator: Service for generating answers from context
            config: RAG system configuration
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.answer_generator = answer_generator
        self.config = config
        logger.info("Query engine initialized")
    
    async def process_query(self, question: str, top_k: Optional[int] = None, document_name: Optional[str] = None) -> QueryResult:
        """
        Process a user question and return a complete query result.
        
        Args:
            question: User's natural language question
            top_k: Number of top results to retrieve (uses config default if None)
            document_name: Optional document name to filter results (None = search all documents)
            
        Returns:
            QueryResult containing answer, sources, and metadata
        """
        logger.info(f"Processing query: {question[:100]}... (document_filter: {document_name})")
        
        # Use configured top_k if not provided
        if top_k is None:
            top_k = self.config.top_k_results
        
        try:
            # Step 1: Convert question to embedding
            query_embedding = self._generate_query_embedding(question)
            logger.debug(f"Generated query embedding with dimension: {len(query_embedding)}")
            
            # Step 2: Retrieve relevant context
            retrieved_chunks = self._retrieve_context(query_embedding, top_k, document_name)
            logger.info(f"Retrieved {len(retrieved_chunks)} relevant chunks")
            
            # Step 3: Generate answer if context is available
            if not retrieved_chunks:
                if document_name:
                    logger.info(f"No relevant context found in document '{document_name}'")
                    return QueryResult(
                        answer=f"I don't know. I couldn't find relevant information in the document '{document_name}' to answer your question.",
                        source_references=[],
                        confidence_score=0.0,
                        retrieved_chunks=[]
                    )
                else:
                    logger.info("No relevant context found, returning 'I don't know' response")
                    return QueryResult(
                        answer="I don't know. I couldn't find relevant information in the uploaded documents to answer your question.",
                        source_references=[],
                        confidence_score=0.0,
                        retrieved_chunks=[]
                    )
            
            # Step 4: Generate grounded answer
            answer_result = self.answer_generator.generate_answer(question, retrieved_chunks)
            logger.info(f"Generated answer with confidence: {answer_result.confidence_score}")
            
            # Step 5: Create complete query result
            result = QueryResult(
                answer=answer_result.answer,
                source_references=answer_result.source_references,
                confidence_score=answer_result.confidence_score,
                retrieved_chunks=retrieved_chunks
            )
            
            logger.info("Query processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
    
    def _generate_query_embedding(self, question: str) -> List[float]:
        """
        Generate embedding for the user question.
        
        Args:
            question: User's question
            
        Returns:
            Embedding vector as list of floats
        """
        if not question.strip():
            raise ValueError("Question cannot be empty")
        
        try:
            embedding = self.embedding_service.generate_embedding(question)
            logger.debug(f"Generated embedding for question with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise
    
    def _retrieve_context(self, query_embedding: List[float], top_k: int, document_name: Optional[str] = None) -> List[TextChunk]:
        """
        Retrieve relevant context using vector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to retrieve
            document_name: Optional document name to filter results (None = search all documents)
            
        Returns:
            List of relevant text chunks ordered by similarity
        """
        try:
            # Perform similarity search
            search_results = self.vector_store.search_similar(query_embedding, top_k)
            
            # Filter by document name if specified
            if document_name:
                search_results = [
                    result for result in search_results 
                    if result.metadata.document_name == document_name
                ]
                logger.debug(f"Filtered to {len(search_results)} chunks from document '{document_name}'")
            
            # Extract chunks from search results
            chunks = [result.chunk for result in search_results]
            
            # Log similarity scores for debugging
            if search_results:
                scores = [result.similarity_score for result in search_results]
                logger.debug(f"Retrieved chunks with similarity scores: {scores}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            raise
    
    def get_status(self) -> dict:
        """
        Get the current status of the query engine.
        
        Returns:
            Dictionary with status information
        """
        try:
            document_count = self.vector_store.get_document_count()
            embedding_info = self.embedding_service.get_provider_info()
            
            return {
                "status": "ready",
                "documents_indexed": document_count,
                "embedding_provider": embedding_info,
                "top_k_results": self.config.top_k_results
            }
        except Exception as e:
            logger.error(f"Failed to get query engine status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }