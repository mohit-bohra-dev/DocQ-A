"""OpenAI LLM provider implementation."""

import logging

try:
    from openai import OpenAI
except ImportError:
    raise ImportError(
        "The 'openai' package is required for the OpenAI provider. "
        "Install it with: pip install -e \".[openai]\""
    )

from src.interfaces import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider using the chat completions API."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        """
        Initialize the OpenAI LLM provider.

        Args:
            api_key: OpenAI API key.
            model_name: Name of the OpenAI model to use.
        """
        self.api_key = api_key
        self.model_name = model_name
        self._client = None
        logger.info(f"Initializing OpenAI LLM provider with model: {model_name}")

    def _get_client(self) -> OpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate_answer(self, prompt: str) -> str:
        """
        Generate an answer from a prompt using OpenAI chat completions.

        Args:
            prompt: Input prompt for the LLM.

        Returns:
            Generated answer as string.
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,
                top_p=0.8,
            )

            answer = response.choices[0].message.content
            if not answer:
                raise ValueError("No response generated from OpenAI API")

            logger.debug(f"Generated answer of length: {len(answer)}")
            return answer.strip()

        except Exception as e:
            logger.error(f"Failed to generate answer with OpenAI: {e}")
            raise

    def is_available(self) -> bool:
        """Check if the OpenAI provider is available."""
        try:
            client = self._get_client()
            # Lightweight check — list models to verify the API key works
            client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI provider not available: {e}")
            return False
