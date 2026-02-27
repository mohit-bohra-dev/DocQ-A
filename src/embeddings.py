"""Embedding service with provider abstraction for the RAG system."""

import logging
from typing import List, Dict, Any

from google import genai

try:
    from .interfaces import EmbeddingProvider
    from .config import RAGConfig
except ImportError:
    # Handle case when running as standalone module
    from interfaces import EmbeddingProvider
    from config import RAGConfig

logger = logging.getLogger(__name__)

# Optional heavy dependency — only needed for sentence-transformers backend
try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    _SentenceTransformer = None
    _SENTENCE_TRANSFORMERS_AVAILABLE = False


class SentenceTransformerProvider(EmbeddingProvider):
    """Sentence Transformers embedding provider."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the Sentence Transformers provider.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self._model = None
        self._dimension = None
        logger.info(f"Initializing SentenceTransformer provider with model: {model_name}")
    
    def _load_model(self):
        """Lazy load the model to avoid loading during initialization."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: pip install -e \".[local]\""
            )
        if self._model is None:
            try:
                self._model = _SentenceTransformer(self.model_name)
                logger.info(f"Successfully loaded SentenceTransformer model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model {self.model_name}: {e}")
                raise
        return self._model
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding
        """
        if not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return [0.0] * self.get_embedding_dimension()
        
        try:
            model = self._load_model()
            embedding = model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embeddings, each as a list of floats
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding generation")
            return []
        
        # Filter out empty texts and keep track of original indices
        non_empty_texts = []
        text_indices = []
        for i, text in enumerate(texts):
            if text.strip():
                non_empty_texts.append(text)
                text_indices.append(i)
        
        if not non_empty_texts:
            logger.warning("All texts are empty, returning zero embeddings")
            dimension = self.get_embedding_dimension()
            return [[0.0] * dimension for _ in texts]
        
        try:
            model = self._load_model()
            embeddings = model.encode(non_empty_texts, convert_to_tensor=False)
            
            # Reconstruct full embedding list with zeros for empty texts
            result = []
            dimension = self.get_embedding_dimension()
            non_empty_idx = 0
            
            for i in range(len(texts)):
                if i in text_indices:
                    result.append(embeddings[non_empty_idx].tolist())
                    non_empty_idx += 1
                else:
                    result.append([0.0] * dimension)
            
            return result
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider.
        
        Returns:
            Embedding dimension as integer
        """
        if self._dimension is None:
            try:
                model = self._load_model()
                # Get dimension from model configuration
                self._dimension = model.get_sentence_embedding_dimension()
                logger.info(f"Embedding dimension for {self.model_name}: {self._dimension}")
            except Exception as e:
                logger.error(f"Failed to get embedding dimension: {e}")
                raise
        return self._dimension


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embedding provider."""
    
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        """Initialize the Gemini embedding provider.
        
        Args:
            api_key: Google API key for Gemini
            model_name: Name of the Gemini embedding model
        """
        self.api_key = api_key
        self.model_name = model_name
        self._dimension = None
        self._client = None
        
        logger.info(f"Initializing Gemini embedding provider with model: {model_name}")
    
    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding
        """
        if not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return [0.0] * self.get_embedding_dimension()
        
        try:
            client = self._get_client()
            response = client.models.embed_content(
                model=self.model_name,
                contents=text
            )
            # Extract the values from the ContentEmbedding object
            if response.embeddings and len(response.embeddings) > 0:
                return list(response.embeddings[0].values)
            else:
                raise ValueError("No embeddings returned from Gemini API")
        except Exception as e:
            logger.error(f"Failed to generate Gemini embedding for text: {e}")
            raise
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embeddings, each as a list of floats
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding generation")
            return []
        
        # Process texts individually for now (check if batch support is available)
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider.
        
        Returns:
            Embedding dimension as integer
        """
        if self._dimension is None:
            try:
                # Generate a test embedding to determine dimension
                test_embedding = self.generate_embedding("test")
                self._dimension = len(test_embedding)
                logger.info(f"Embedding dimension for {self.model_name}: {self._dimension}")
            except Exception as e:
                logger.error(f"Failed to get embedding dimension: {e}")
                # Default dimension for text-embedding-004 model
                self._dimension = 768
                logger.warning(f"Using default dimension: {self._dimension}")
        return self._dimension


class EmbeddingService:
    """Main embedding service that manages providers and configuration."""
    
    def __init__(self, config: RAGConfig):
        """Initialize the embedding service with configuration.
        
        Args:
            config: RAG system configuration
        """
        self.config = config
        self._provider = None
        logger.info(f"Initializing embedding service with model: {config.embedding_model}")
    
    def _get_provider(self) -> EmbeddingProvider:
        """Get the configured embedding provider.
        
        Returns:
            Configured embedding provider instance
        """
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider
    
    def _create_provider(self) -> EmbeddingProvider:
        """Create the appropriate embedding provider based on configuration.
        
        Returns:
            Configured embedding provider instance
        """
        model_name = self.config.embedding_model
        
        if model_name.startswith("sentence-transformers/") or model_name in [
            "all-MiniLM-L6-v2", "all-mpnet-base-v2", "all-distilroberta-v1"
        ]:
            return SentenceTransformerProvider(model_name)
        elif model_name.startswith("models/text-embedding") or model_name.startswith("models/embedding") or "gemini" in model_name.lower():
            if not self.config.gemini_api_key:
                raise ValueError("Gemini API key is required for Gemini embedding provider")
            return GeminiEmbeddingProvider(self.config.gemini_api_key, model_name)
        else:
            # Default to sentence transformers
            logger.warning(f"Unknown model {model_name}, defaulting to SentenceTransformer")
            return SentenceTransformerProvider(model_name)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding
        """
        provider = self._get_provider()
        return provider.generate_embedding(text)
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embeddings, each as a list of floats
        """
        provider = self._get_provider()
        return provider.generate_batch_embeddings(texts)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by the current provider.
        
        Returns:
            Embedding dimension as integer
        """
        provider = self._get_provider()
        return provider.get_embedding_dimension()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider.
        
        Returns:
            Dictionary with provider information
        """
        provider = self._get_provider()
        return {
            "provider_type": type(provider).__name__,
            "model_name": self.config.embedding_model,
            "embedding_dimension": provider.get_embedding_dimension()
        }