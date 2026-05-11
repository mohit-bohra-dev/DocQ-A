from google import genai
import logging


from src.interfaces import LLMProvider
logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
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
        logger.info(
            f"Initializing Gemini LLM provider with model: {model_name}")

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
                    "max_output_tokens": 1500,
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
