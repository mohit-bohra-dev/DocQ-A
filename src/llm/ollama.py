"""Ollama LLM provider — supports both local and cloud Ollama instances."""

import logging
from typing import Optional

import requests

from src.interfaces import LLMProvider

logger = logging.getLogger(__name__)

# Default endpoints
_LOCAL_DEFAULT_URL = "http://localhost:11434"
_CLOUD_DEFAULT_URL = "https://ollama.com"


class OllamaProvider(LLMProvider):
    """LLM provider that talks to a local *or* cloud Ollama instance via its HTTP API.

    **Local mode** (default):
        No API key required. Talks to a locally running Ollama server.

    **Cloud mode**:
        Supply an ``api_key`` (or set ``OLLAMA_API_KEY`` env-var in the factory).
        Requests are sent to ``https://ollama.com`` with Bearer auth.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "qwen3:8b",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Ollama LLM provider.

        Args:
            base_url: Base URL of the Ollama server.
                      Defaults to ``http://localhost:11434`` for local mode
                      or ``https://ollama.com`` when an ``api_key`` is provided.
            model: Name of the model to use (must already be pulled locally,
                   or available on Ollama Cloud).
            api_key: Ollama Cloud API key.  When set, the provider operates in
                     cloud mode and authenticates with a Bearer token.
        """
        self.api_key = api_key

        # Detect cloud mode from model name suffix (e.g. "deepseek-v4-flash:cloud")
        parts = model.rsplit(":", 1)
        if len(parts) == 2 and parts[1] == "cloud":
            self.is_cloud = True
            self.model = parts[0]  # strip the :cloud tag before sending to API
        else:
            self.is_cloud = bool(api_key)  # fallback: API key triggers cloud mode
            self.model = model

        if base_url is None:
            base_url = _CLOUD_DEFAULT_URL if self.is_cloud else _LOCAL_DEFAULT_URL

        self.base_url = base_url.rstrip("/")

        mode_label = "cloud" if self.is_cloud else "local"
        logger.info(
            f"Initializing Ollama LLM provider ({mode_label}) "
            f"with model: {self.model} at {self.base_url}"
        )

    # ── internal helpers ────────────────────────────────────────────────

    def _headers(self) -> dict:
        """Return request headers, including auth for cloud mode."""
        headers: dict = {"Content-Type": "application/json"}
        if self.is_cloud and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ── LLMProvider interface ───────────────────────────────────────────

    def generate_answer(self, prompt: str) -> str:
        """
        Generate an answer from a prompt using the Ollama generate API.

        Args:
            prompt: Input prompt for the LLM.

        Returns:
            Generated answer as string.
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1500,
                    },
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("response", "")
            logger.debug(f"Generated answer of length: {len(answer)}")
            return answer.strip()
        except requests.RequestException as e:
            logger.error(f"Failed to generate answer with Ollama: {e}")
            raise

    def is_available(self) -> bool:
        """Check if the Ollama server is reachable and the model is loaded."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/tags",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            available = any(self.model in m for m in models)
            if not available:
                logger.warning(
                    f"Ollama server is reachable but model '{self.model}' not found. "
                    f"Available models: {models}"
                )
            return available
        except Exception as e:
            logger.warning(f"Ollama provider not available: {e}")
            return False