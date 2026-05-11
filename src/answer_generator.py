"""Answer generation with LLM provider abstraction."""

import json
import logging
from typing import List, Dict, Any, Optional

from src.llm.factory import get_llm_provider


try:
    from .interfaces import LLMProvider
    from .models import TextChunk, AnswerResult, SourceReference
    from .config import RAGConfig
except ImportError:
    from interfaces import LLMProvider
    from models import TextChunk, AnswerResult, SourceReference
    from config import RAGConfig

logger = logging.getLogger(__name__)


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
        logger.info(
            f"Initializing answer generator with provider: {config.llm_provider}")


    def generate_answer(self, question: str, context: List[TextChunk]) -> AnswerResult:
        """
        Generate an answer based on question and retrieved context.

        The LLM is asked to return structured JSON containing the answer and
        exact verbatim quotes for each source it cites.  Those quotes are
        used as ``content_snippet`` in SourceReference so the frontend can
        highlight a short, precise passage instead of the first 300 chars of
        the chunk.

        If the LLM response cannot be parsed as JSON, the method falls back
        to the legacy behaviour (plain text answer + 300-char snippet).
        """
        logger.info(
            f"Generating answer for question with {len(context)} context chunks")

        if not context:
            logger.warning("No context provided for answer generation")
            return AnswerResult(
                answer="I don't know. I couldn't find relevant information in the uploaded documents to answer your question.",
                confidence_score=0.0,
                source_references=[]
            )

        try:

            import jsonpickle
            decoded_list = jsonpickle.encode(context)
            # Construct grounded prompt (asks for JSON)
            prompt = self.construct_grounded_prompt(question, context)
            logger.debug(f"Constructed prompt of length: {len(prompt)}")

            # Generate answer using LLM
            provider = get_llm_provider()
            raw_response = provider.generate_answer(prompt)

            # Try to parse the structured JSON response
            parsed = self._parse_structured_response(raw_response)

            if parsed is not None:
                answer_text, citation_quotes = parsed
                source_references = self._generate_source_references(
                    context, citation_quotes=citation_quotes
                )
                logger.info("Parsed structured JSON response with %d citation quotes", len(
                    citation_quotes))
            else:
                # Fallback: treat the whole response as plain-text answer
                logger.warning(
                    "Could not parse JSON from LLM response — falling back to plain text")
                answer_text = raw_response
                source_references = self._generate_source_references(context)

            confidence_score = self._calculate_confidence_score(context)

            result = AnswerResult(
                answer=answer_text,
                confidence_score=confidence_score,
                source_references=source_references
            )

            logger.info(
                f"Answer generated successfully with confidence: {confidence_score}")
            return result

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def construct_grounded_prompt(self, question: str, context: List[TextChunk]) -> str:
        """
        Build a prompt that asks the LLM for a **structured JSON** response
        containing the answer and per-source verbatim quotes.
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

        prompt = f"""You are a helpful AI assistant that answers questions based strictly on the provided context.

IMPORTANT INSTRUCTIONS:
- Only use information from the provided context to answer the question.
- If the context doesn't contain enough information, set the answer to "I don't know".
- Do NOT make up or infer information that isn't explicitly stated in the context.
- Be concise and accurate.
- Cite sources in the answer as [Source 1], [Source 2], etc.

CONTEXT:
{context_text}

QUESTION: {question}

Respond with a JSON object in EXACTLY this format (no extra keys, no markdown fences):
{{{{
  "answer": "Your concise answer in markdown. Cite sources as [Source 1], [Source 2] etc.",
  "citations": [
    {{{{
      "source": 1,
      "quote": "The EXACT verbatim sentence(s) from Source 1 that support your answer. Copy word-for-word, 1-2 sentences max."
    }}}}
  ]
}}}}

Rules for the citations array:
- Include one entry for EACH source you actually referenced in your answer.
- The "quote" MUST be copied word-for-word from the source text. Do NOT paraphrase.
- Keep each quote short: 1-2 sentences (under 200 characters ideally).
- If the answer is "I don't know", set citations to an empty array []."""

        logger.debug(
            f"Constructed grounded prompt with {len(context)} sources")
        return prompt

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_structured_response(
        self, raw: str
    ) -> Optional[tuple]:
        """
        Try to parse the LLM response as structured JSON.

        Returns:
            (answer_text, citation_quotes) on success, where
            citation_quotes is a dict mapping 1-based source index → quote str.
            None if parsing fails.
        """
        text = raw.strip()

        # Strip optional markdown fences that LLMs sometimes add
        if text.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = text.index("\n") if "\n" in text else 3
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.debug("LLM response is not valid JSON")
            return None

        if not isinstance(data, dict) or "answer" not in data:
            logger.debug("JSON response missing 'answer' key")
            return None

        answer_text = str(data["answer"]).strip()
        citation_quotes: Dict[int, str] = {}

        for entry in data.get("citations", []):
            if isinstance(entry, dict) and "source" in entry and "quote" in entry:
                try:
                    src_idx = int(entry["source"])
                    quote = str(entry["quote"]).strip()
                    if quote:
                        citation_quotes[src_idx] = quote
                except (ValueError, TypeError):
                    continue

        return answer_text, citation_quotes

    def _generate_source_references(
        self,
        context: List[TextChunk],
        citation_quotes: Optional[Dict[int, str]] = None,
    ) -> List[SourceReference]:
        """
        Generate source references from context chunks.

        If *citation_quotes* is provided (from the structured JSON response),
        the LLM's short verbatim quote is used as ``content_snippet``.
        Otherwise falls back to the first SNIPPET_LEN characters of the chunk.
        """
        SNIPPET_LEN = 300  # fallback length

        references = []
        seen_sources = set()

        for i, chunk in enumerate(context):
            source_key = (chunk.document_name,
                          chunk.page_number, chunk.chunk_id)

            if source_key not in seen_sources:
                # Prefer LLM-provided quote; fall back to first N chars
                llm_quote = (
                    citation_quotes.get(i + 1)  # 1-based source index
                    if citation_quotes
                    else None
                )

                if llm_quote:
                    snippet = llm_quote
                else:
                    raw = chunk.text.strip()
                    if len(raw) > SNIPPET_LEN:
                        clipped = raw[:SNIPPET_LEN]
                        last_space = clipped.rfind(" ")
                        snippet = clipped[:last_space] if last_space > 0 else clipped
                    else:
                        snippet = raw

                references.append(SourceReference(
                    document_name=chunk.document_name,
                    page_number=chunk.page_number,
                    chunk_id=chunk.chunk_id,
                    content_snippet=snippet
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
        avg_chunk_length = sum(len(chunk.text)
                               for chunk in context) / num_chunks

        # Normalize factors
        chunk_factor = min(num_chunks / self.config.top_k_results, 1.0)
        # Assume 500 chars is good length
        length_factor = min(avg_chunk_length / 500, 1.0)

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
            provider = get_llm_provider()
            return {
                "provider_type": type(provider).__name__,
                "model_name": getattr(provider, "model_name", getattr(provider, "model", "unknown")),
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
