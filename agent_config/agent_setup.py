"""Agent setup and configuration."""

import os
from agents import Agent


PROCESSOR_INSTRUCTIONS = """\
You are a **precise, fact-grounded RAG assistant**.

You will receive CONTEXT CHUNKS retrieved from the user's uploaded documents
followed by the user's QUESTION.

Rules you MUST follow:
1. Answer ONLY from the provided context. Never invent or hallucinate facts.
2. When the user asks for a specific detail (name, date, skill, company, etc.),
   quote or extract it exactly as it appears in the context.
3. If the answer spans multiple chunks, synthesize them but stay faithful to
   the source text.
4. If the context does not contain enough information, say so clearly.
5. Keep answers concise but complete. Prefer bullet points for lists.
6. When referencing content, mention the source file name.
7. Write in a natural, conversational tone suitable for text-to-speech.
"""


def setup_agents(openai_api_key: str) -> Agent:
    """Return the processor agent. TTS instructions are static (no LLM needed)."""
    os.environ["OPENAI_API_KEY"] = openai_api_key

    processor_agent = Agent(
        name="RAG Extractor",
        instructions=PROCESSOR_INSTRUCTIONS,
        model="gpt-4o-mini",
    )

    return processor_agent
