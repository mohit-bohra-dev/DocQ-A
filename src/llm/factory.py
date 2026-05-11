

import os

from src.interfaces import LLMProvider


def get_llm_provider() -> LLMProvider:
    """
    Return a singleton LLM provider based on the LLM_PROVIDER environment variable.
    All providers are automatically wrapped with a PII scrubbing proxy.

    Supported values: gemini (default), openai, anthropic, ollama, mock
    """
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()

    provider: LLMProvider

    match provider_name:
        case "openai":
            from .openai import OpenAIProvider
            api_key = os.environ["OPENAI_API_KEY"]
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            provider = OpenAIProvider(api_key=api_key, model_name=model)

        case "ollama":
            from .ollama import OllamaProvider
            api_key = os.getenv("OLLAMA_API_KEY")
            base_url = os.getenv("OLLAMA_BASE_URL")  # None → auto-select
            model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
            provider = OllamaProvider(base_url=base_url, model=model, api_key=api_key)

        case "gemini":
            from .gemini import GeminiProvider
            api_key = os.environ.get("GEMINI_API_KEY", "")
            model = os.getenv("GEMINI_MODEL", "gemini-3-flash")
            provider = GeminiProvider(api_key=api_key, model_name=model)

        case _:
            raise ValueError(
                f"Unsupported LLM provider: '{provider_name}'. "
                f"Supported providers: gemini, openai, ollama"
            )

    return provider
