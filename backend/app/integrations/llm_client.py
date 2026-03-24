"""LLM client stub for AI-powered extraction, summarization, and querying.

This module will be implemented in Phase 2 with OpenAI integration.
All methods currently raise NotImplementedError.
"""

from typing import Optional

from app.core.config import settings


class LLMClient:
    """Client for LLM operations (extraction, summarization, querying, embeddings)."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Store the API key for future use. Does NOT initialize an OpenAI client yet.

        Args:
            api_key: OpenAI API key. Stored for when the client is implemented.
        """
        self.api_key = api_key

    async def extract(self, content: str, source_type: str) -> dict:
        """Extract structured memory records from raw source content.

        Will parse unstructured text and return categorized facts, decisions,
        insights, and other memory record candidates.

        Args:
            content: Raw text content from a source.
            source_type: Type of source (e.g. "note", "transcript", "document").

        Returns:
            A dict containing extracted memory records and metadata.
        """
        raise NotImplementedError("LLM extraction not yet implemented")

    async def summarize(self, records: list[dict], summary_type: str) -> dict:
        """Generate a summary from a list of memory records.

        Will produce project one-pagers, recent update summaries, or
        topic-specific summaries from structured memory records.

        Args:
            records: List of memory record dicts to summarize.
            summary_type: Type of summary (e.g. "one_pager", "recent_updates").

        Returns:
            A dict containing the generated summary and metadata.
        """
        raise NotImplementedError("LLM summarization not yet implemented")

    async def query(self, question: str, context: list[dict]) -> dict:
        """Answer a natural language question using memory records as context.

        Will use retrieval-augmented generation to answer user queries
        based on stored memory records.

        Args:
            question: The user's natural language question.
            context: List of relevant memory record dicts for context.

        Returns:
            A dict containing the answer and source attributions.
        """
        raise NotImplementedError("LLM query not yet implemented")

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of text strings.

        Will produce embeddings for semantic search and similarity matching
        across memory records.

        Args:
            texts: List of text strings to embed.

        Returns:
            A list of embedding vectors (each a list of floats).
        """
        raise NotImplementedError("LLM embedding generation not yet implemented")


llm_client = LLMClient(settings.OPENAI_API_KEY)
