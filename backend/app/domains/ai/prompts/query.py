"""Query/RAG prompt template for answering natural language questions from memory records."""

QUERY_PROMPT_VERSION = "query-v1"

QUERY_SYSTEM_PROMPT = """\
You are a project knowledge assistant. Your job is to answer questions using ONLY the provided context from memory records and source content. You must never fabricate information.

## Task

Answer the user's question based on the context provided below. The context contains two types of information:

1. **Memory Records** — Structured, curated knowledge extracted from project sources. These are the primary and most reliable source of information. Each record has an ID, type, content, and importance level.
2. **Source Chunks** — Raw excerpts from original source documents. These provide additional detail when memory records don't fully cover the question.

## Output Format

Return a JSON object with this exact structure:

```json
{
  "answer": "Your answer in markdown format",
  "citations": [
    {
      "record_id": "uuid-of-the-record-or-null",
      "chunk_id": "uuid-of-the-source-chunk-or-null",
      "excerpt": "The specific part of the record or chunk that supports this point"
    }
  ]
}
```

Use `record_id` when citing a memory record, `chunk_id` when citing a source chunk. At least one must be non-null.

Return ONLY valid JSON. No markdown fences, no commentary outside the JSON.

## Rules

1. **Answer ONLY from the provided context.** If the context does not contain enough information to answer the question, say so explicitly: "I don't have enough information in the current memory to answer this question."
2. **Cite your sources.** For each claim in your answer, include a citation referencing the record ID and the relevant excerpt. Aim for at least one citation per key point.
3. **Prefer memory records over source chunks.** Memory records are curated and structured — prioritize them. Only fall back to source chunks for details not captured in records.
4. **Be direct and concise.** Answer the question first, then provide supporting detail. Don't pad the response.
5. **Use markdown** for readability — bullet points, bold text, and headers where appropriate.
6. **Distinguish certainty levels.** If the context strongly supports an answer, state it confidently. If it only partially addresses the question, qualify your answer.\
"""


def build_query_prompt(
    question: str,
    records: list[dict],
    chunks: list[dict],
) -> list[dict]:
    """Assemble the RAG query prompt as a list of OpenAI chat messages.

    Args:
        question: The user's natural language question.
        records: List of memory record dicts (primary context) with id, record_type,
            content, importance.
        chunks: List of source chunk dicts (fallback context) with id, content,
            source_id.

    Returns:
        List of message dicts with "role" and "content" keys.
    """
    # Build context sections
    context_parts = []

    if records:
        record_lines = []
        for rec in records:
            rec_id = rec.get("id", "unknown")
            rec_type = rec.get("record_type", "unknown")
            importance = rec.get("importance", "medium")
            content = rec.get("content", "")
            record_lines.append(
                f"- [record_id={rec_id}, type={rec_type}, importance={importance}] {content}"
            )
        context_parts.append(
            "## Memory Records\n\n" + "\n".join(record_lines)
        )

    if chunks:
        chunk_lines = []
        for chunk in chunks:
            chunk_id = chunk.get("id", "unknown")
            content = chunk.get("content", "")
            chunk_lines.append(
                f"- [chunk_id={chunk_id}] {content}"
            )
        context_parts.append(
            "## Source Chunks\n\n" + "\n".join(chunk_lines)
        )

    if not context_parts:
        context_parts.append("No context available.")

    user_content = (
        "\n\n".join(context_parts)
        + f"\n\n## Question\n\n{question}"
    )

    return [
        {"role": "system", "content": QUERY_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
