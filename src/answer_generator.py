"""Answer generation with LLM provider abstraction."""

import logging
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from google import genai

try:
    from .interfaces import LLMProvider
    from .models import TextChunk, AnswerResult, SourceReference
    from .config import RAGConfig
except ImportError:
    from interfaces import LLMProvider
    from models import TextChunk, AnswerResult, SourceReference
    from config import RAGConfig

logger = logging.getLogger(__name__)


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM provider implementation."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the Gemini LLM provider.
        
        Args:
            api_key: Google API key for Gemini
            model_name: Name of the Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        self._client = None
        logger.info(f"Initializing Gemini LLM provider with model: {model_name}")
    
    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client
    
    def generate_answer(self, prompt: str) -> str:
        """
        Generate an answer from a prompt using Gemini.
        
        Args:
            prompt: Input prompt for the LLM
            
        Returns:
            Generated answer as string
        """
        try:
            client = self._get_client()
            
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": 0.1,  # Low temperature for more consistent answers
                    "max_output_tokens": 1000,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            if response.candidates and len(response.candidates) > 0:
                answer = response.candidates[0].content.parts[0].text
                logger.debug(f"Generated answer of length: {len(answer)}")
                return answer.strip()
            else:
                raise ValueError("No response generated from Gemini API")
                
        except Exception as e:
            logger.error(f"Failed to generate answer with Gemini: {e}")
            raise
    
    def is_available(self) -> bool:
        """
        Check if the Gemini provider is available.
        
        Returns:
            True if provider is available, False otherwise
        """
        try:
            client = self._get_client()
            # Try a simple test request
            response = client.models.generate_content(
                model=self.model_name,
                contents="Test",
                config={"max_output_tokens": 1}
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini provider not available: {e}")
            return False


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM provider implementation (placeholder for future implementation)."""
    
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        """
        Initialize the OpenAI LLM provider.
        
        Args:
            api_key: OpenAI API key
            model_name: Name of the OpenAI model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        logger.info(f"Initializing OpenAI LLM provider with model: {model_name}")
        logger.warning("OpenAI provider is not yet implemented")
    
    def generate_answer(self, prompt: str) -> str:
        """Generate an answer from a prompt using OpenAI."""
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    def is_available(self) -> bool:
        """Check if the OpenAI provider is available."""
        return False


class AnswerGenerator:
    """Main answer generator that manages LLM providers and prompt construction."""
    
    def __init__(self, config: RAGConfig):
        """
        Initialize the answer generator with configuration.
        
        Args:
            config: RAG system configuration
        """
        self.config = config
        self._provider = None
        logger.info(f"Initializing answer generator with provider: {config.llm_provider}")
    
    def _get_provider(self) -> LLMProvider:
        """
        Get the configured LLM provider.
        
        Returns:
            Configured LLM provider instance
        """
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider
    
    def _create_provider(self) -> LLMProvider:
        """
        Create the appropriate LLM provider based on configuration.
        
        Returns:
            Configured LLM provider instance
        """
        provider_name = self.config.llm_provider.lower()
        
        if provider_name == "gemini":
            if not self.config.gemini_api_key:
                raise ValueError("Gemini API key is required for Gemini provider")
            return GeminiLLMProvider(self.config.gemini_api_key, self.config.gemini_model)
        elif provider_name == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI provider")
            return OpenAILLMProvider(self.config.openai_api_key, self.config.openai_model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
    
    def generate_answer(self, question: str, context: List[TextChunk]) -> AnswerResult:
        """
        Generate an answer based on question and retrieved context.
        
        Args:
            question: User's question
            context: List of relevant text chunks
            
        Returns:
            AnswerResult with generated answer and metadata
        """
        logger.info(f"Generating answer for question with {len(context)} context chunks")
        
        if not context:
            logger.warning("No context provided for answer generation")
            return AnswerResult(
                answer="I don't know. I couldn't find relevant information in the uploaded documents to answer your question.",
                confidence_score=0.0,
                source_references=[]
            )
        
        try:
            # Construct grounded prompt
            prompt = self.construct_grounded_prompt(question, context)
            logger.debug(f"Constructed prompt of length: {len(prompt)}")
            
            # Generate answer using LLM
            provider = self._get_provider()
            answer = provider.generate_answer(prompt)
            
            # Generate source references
            source_references = self._generate_source_references(context)
            
            # Calculate confidence score based on context relevance
            confidence_score = self._calculate_confidence_score(context)
            
            result = AnswerResult(
                answer=answer,
                confidence_score=confidence_score,
                source_references=source_references
            )
            
            logger.info(f"Answer generated successfully with confidence: {confidence_score}")
            return result
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            raise
    
    def construct_grounded_prompt(self, question: str, context: List[TextChunk]) -> str:
        """
        Construct a grounded prompt from question and context.
        
        Args:
            question: User's question
            context: List of relevant text chunks
            
        Returns:
            Formatted prompt string
        """
        if not context:
            raise ValueError("Context cannot be empty for prompt construction")
        
        # Build context section
        context_parts = []
        for i, chunk in enumerate(context, 1):
            context_parts.append(
                f"[Source {i} - {chunk.document_name}, Page {chunk.page_number}]\n"
                f"{chunk.text}\n"
            )
        
        context_text = "\n".join(context_parts)
        
        # Construct the grounded prompt
        prompt = f"""You are a helpful AI assistant that answers questions based strictly on the provided context. 

IMPORTANT INSTRUCTIONS:
- Only use information from the provided context to answer the question
- If the context doesn't contain enough information to answer the question, say "I don't know"
- Do not make up or infer information that isn't explicitly stated in the context
- Be concise and accurate in your response
- Reference the source documents when possible

CONTEXT:
{context_text}

QUESTION: {question}

ANSWER:"""
        
        logger.debug(f"Constructed grounded prompt with {len(context)} sources")
        return prompt
    
    def _generate_source_references(self, context: List[TextChunk]) -> List[SourceReference]:
        """
        Generate source references from context chunks.
        
        Args:
            context: List of text chunks used in answer generation
            
        Returns:
            List of source references with content snippets for highlighting
        """
        SNIPPET_LEN = 300  # characters — long enough to be unique, short enough for regex
        
        references = []
        seen_sources = set()
        
        for chunk in context:
            # Create a unique identifier for this source
            source_key = (chunk.document_name, chunk.page_number, chunk.chunk_id)
            
            if source_key not in seen_sources:
                # Build a clean snippet: first SNIPPET_LEN chars, clipped at last whitespace
                raw = chunk.text.strip()
                if len(raw) > SNIPPET_LEN:
                    clipped = raw[:SNIPPET_LEN]
                    # Step back to the last word boundary
                    last_space = clipped.rfind(" ")
                    clipped = clipped[:last_space] if last_space > 0 else clipped
                else:
                    clipped = raw

                references.append(SourceReference(
                    document_name=chunk.document_name,
                    page_number=chunk.page_number,
                    chunk_id=chunk.chunk_id,
                    content_snippet=clipped
                ))
                seen_sources.add(source_key)
        
        logger.debug(f"Generated {len(references)} unique source references")
        return references

    
    def _calculate_confidence_score(self, context: List[TextChunk]) -> float:
        """
        Calculate confidence score based on context quality.
        
        Args:
            context: List of text chunks used for answer generation
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not context:
            return 0.0
        
        # Simple confidence calculation based on:
        # - Number of context chunks (more context = higher confidence)
        # - Average chunk length (longer chunks = more information)
        
        num_chunks = len(context)
        avg_chunk_length = sum(len(chunk.text) for chunk in context) / num_chunks
        
        # Normalize factors
        chunk_factor = min(num_chunks / self.config.top_k_results, 1.0)
        length_factor = min(avg_chunk_length / 500, 1.0)  # Assume 500 chars is good length
        
        # Combine factors (weighted average)
        confidence = (chunk_factor * 0.6) + (length_factor * 0.4)
        
        # Ensure confidence is between 0.1 and 0.9 (never completely certain or uncertain)
        confidence = max(0.1, min(0.9, confidence))
        
        logger.debug(f"Calculated confidence score: {confidence}")
        return confidence
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the current LLM provider.
        
        Returns:
            Dictionary with provider information
        """
        try:
            provider = self._get_provider()
            return {
                "provider_type": type(provider).__name__,
                "model_name": self.config.gemini_model if self.config.llm_provider == "gemini" else self.config.openai_model,
                "is_available": provider.is_available()
            }
        except Exception as e:
            logger.error(f"Failed to get provider info: {e}")
            return {
                "provider_type": "unknown",
                "model_name": "unknown",
                "is_available": False,
                "error": str(e)
            }