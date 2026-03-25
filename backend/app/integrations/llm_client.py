"""OpenAI client for LLM extraction, summarization, querying, and embeddings."""

import json
import logging
from typing import Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 100


class LLMClient:
    """Client for OpenAI LLM and embedding operations."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        """Lazy-initialize the OpenAI client on first use."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def chat_completion_json(
        self, messages: list[dict], retry_on_parse_error: bool = True
    ) -> dict:
        """Call OpenAI chat completion and parse JSON response.

        Args:
            messages: List of message dicts with "role" and "content".
            retry_on_parse_error: If True, retry once on malformed JSON.

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            ValueError: If the response is not valid JSON after retries.
        """
        for attempt in range(2 if retry_on_parse_error else 1):
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content
            if content is None:
                if attempt == 0 and retry_on_parse_error:
                    logger.warning("Empty LLM response, retrying")
                    continue
                raise ValueError("LLM returned empty response")

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                if attempt == 0 and retry_on_parse_error:
                    logger.warning("Malformed JSON from LLM, retrying")
                    continue
                raise ValueError(f"LLM returned invalid JSON: {content[:200]}")

        raise ValueError("LLM failed to return valid JSON after retries")

    def extract(
        self,
        messages: list[dict],
    ) -> dict:
        """Run extraction via chat completion with JSON output.

        Args:
            messages: Pre-built extraction prompt messages.

        Returns:
            Parsed dict with "records" key.
        """
        return self.chat_completion_json(messages)

    def summarize(
        self,
        messages: list[dict],
    ) -> dict:
        """Run summarization via chat completion with JSON output.

        Args:
            messages: Pre-built summarization prompt messages.

        Returns:
            Parsed dict with "title" and "content" keys.
        """
        return self.chat_completion_json(messages)

    def query(
        self,
        messages: list[dict],
    ) -> dict:
        """Run RAG query via chat completion with JSON output.

        Args:
            messages: Pre-built query prompt messages.

        Returns:
            Parsed dict with "answer" and "citations" keys.
        """
        return self.chat_completion_json(messages)

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of texts.

        Batches at EMBEDDING_BATCH_SIZE (100) texts per API call.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 1536-dim embedding vectors, one per input text.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            response = self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=batch,
            )
            # Response data is ordered by index
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings


llm_client = LLMClient(settings.OPENAI_API_KEY)
