"""Summarization prompt templates for generating one-pagers and recent update summaries."""

SUMMARIZATION_PROMPT_VERSION = "summarization-v1"

SUMMARIZATION_SYSTEM_PROMPT = """\
You are a project knowledge summarizer. Your job is to synthesize a collection of structured memory records into a clear, well-organized summary document.

## Task

Read the provided memory records and produce a **coherent narrative summary** in markdown format. Do NOT simply list the records — synthesize them into readable prose with logical grouping and flow.

## Output Format

Return a JSON object with this exact structure:

```json
{
  "title": "A concise, descriptive title for the summary",
  "content": "The full summary in markdown format"
}
```

Return ONLY valid JSON. No markdown fences, no commentary outside the JSON.

## General Guidelines

- Use **well-structured markdown** with section headings (##), bullet points, and bold text for emphasis.
- **Prioritize high-importance records** — decisions, issues, and tasks should feature prominently.
- **Group related records logically** — by topic, theme, or timeline rather than by record type.
- When many records exist, **summarize and group** rather than enumerate every one.
- Write in a **neutral, professional tone** — as if briefing someone who needs to get up to speed quickly.
- Each section heading should be descriptive and meaningful, not generic (e.g., "Infrastructure Decision: Postgres + pgvector" not "Decision 1").\
"""

SUMMARY_TYPE_INSTRUCTIONS = {
    "one_pager": """
## Summary Type: One-Pager

Produce a comprehensive project overview covering:

1. **Overview** — What is this project/client/topic about? Key context in 2-3 sentences.
2. **Key Facts** — Important names, numbers, relationships, and attributes.
3. **Decisions Made** — Major choices and their rationale (if known).
4. **Open Issues & Questions** — Unresolved problems, risks, and unanswered questions.
5. **Current Status & Next Steps** — Where things stand and what's coming next (tasks, upcoming events).

Use these sections as a guide but adapt to the actual content — skip empty sections, merge where it makes sense. The goal is a one-page briefing document that gives a newcomer full context.""",

    "recent_updates": """
## Summary Type: Recent Updates

Produce a summary focused on **what changed recently**:

The records provided represent the recent time window.

1. **New Decisions** — Choices made recently.
2. **Resolved Issues** — Problems that were addressed or closed.
3. **New Issues & Risks** — Problems or concerns that emerged.
4. **New Questions** — Open items that surfaced.
5. **Action Items** — Tasks assigned or completed.

Focus on change and delta — what's different now versus before. Be concise. If there are few recent changes, say so rather than padding.""",
}


def build_summarization_prompt(
    records: list[dict],
    summary_type: str,
) -> list[dict]:
    """Assemble the summarization prompt as a list of OpenAI chat messages.

    Args:
        records: List of memory record dicts, each with record_type, content,
            importance, and optionally id/confidence.
        summary_type: One of "one_pager", "recent_updates".

    Returns:
        List of message dicts with "role" and "content" keys.
    """
    system_parts = [SUMMARIZATION_SYSTEM_PROMPT]

    type_instruction = SUMMARY_TYPE_INSTRUCTIONS.get(summary_type)
    if type_instruction:
        system_parts.append(type_instruction)

    # Format records as structured context for the LLM
    record_lines = []
    for i, rec in enumerate(records, 1):
        rec_id = rec.get("id", "unknown")
        rec_type = rec.get("record_type", "unknown")
        importance = rec.get("importance", "medium")
        content = rec.get("content", "")
        record_lines.append(
            f"[{i}] (id={rec_id}, type={rec_type}, importance={importance})\n{content}"
        )

    user_content = (
        f"## Memory Records ({len(records)} total)\n\n"
        + "\n\n".join(record_lines)
    )

    return [
        {"role": "system", "content": "\n".join(system_parts)},
        {"role": "user", "content": user_content},
    ]
