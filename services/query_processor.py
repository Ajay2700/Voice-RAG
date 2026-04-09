"""Query processing service — retrieval, generation, and TTS in one pass."""

from typing import Dict, Optional
import os
import re
import tempfile
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import AsyncOpenAI
from agents import Runner

from config.settings import COLLECTION_NAME, SEARCH_LIMIT, SCORE_THRESHOLD

# Static TTS voice instructions (no LLM call needed).
_TTS_INSTRUCTIONS = (
    "Speak clearly, at a natural conversational pace. "
    "Pronounce technical terms and proper nouns carefully. "
    "Use slight pauses between sentences for comprehension."
)


def _is_name_question(query: str) -> bool:
    text = query.lower()
    return ("name" in text) and (
        "candidate" in text or "person" in text or "resume" in text or "cv" in text or "what is" in text
    )


def _extract_name_from_context(search_results: list) -> Optional[str]:
    """Heuristic fallback for resume headers when LLM misses name extraction."""
    keywords = {"email", "phone", "github", "linkedin", "summary", "experience", "education", "skills"}

    # Prefer full-page chunks because resume header fields are usually there.
    sorted_results = sorted(
        search_results,
        key=lambda r: 0 if (r.payload or {}).get("chunk_type") == "full_page" else 1,
    )

    for result in sorted_results:
        payload = result.payload or {}
        content = payload.get("content", "")
        if not content:
            continue
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        for line in lines[:12]:
            normalized = re.sub(r"[^A-Za-z .'-]", "", line).strip()
            words = [w for w in normalized.split() if w]
            lower = normalized.lower()
            if any(k in lower for k in keywords):
                continue
            # Candidate name heuristic: 2-4 alphabetic words, mostly title case.
            if 2 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", w) for w in words):
                title_case_ratio = sum(1 for w in words if w[0].isupper()) / len(words)
                if title_case_ratio >= 0.75:
                    return " ".join(words)
    return None


def _extract_name_from_file(
    client: QdrantClient,
    collection_name: str,
    target_file: str,
) -> Optional[str]:
    """Directly scan stored chunks for a file and extract probable name."""
    file_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="file_name",
                match=models.MatchValue(value=target_file),
            )
        ]
    )

    points, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=file_filter,
        with_payload=True,
        limit=256,
    )

    if not points:
        return None
    return _extract_name_from_context(points)


async def process_query(
    query: str,
    client: QdrantClient,
    embedding_model,
    processor_agent,
    openai_api_key: str,
    voice: str,
    target_file: Optional[str] = None,
    collection_name: str = COLLECTION_NAME,
    search_limit: int = SEARCH_LIMIT,
    score_threshold: float = SCORE_THRESHOLD,
) -> Dict:
    """Retrieve context, generate answer, produce audio — single async call."""
    try:
        # --- Step 1: embed query & search ---
        query_embedding = embedding_model.embed([query])[0]

        query_filter = None
        if target_file:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="file_name",
                        match=models.MatchValue(value=target_file),
                    )
                ]
            )

        try:
            search_response = client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=search_limit,
                with_payload=True,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )
        except Exception as e:
            # Backward compatibility: if payload index is missing, retry without filter.
            # setup_qdrant now creates this index automatically, so this path should
            # be temporary for existing collections.
            if (
                query_filter is not None
                and "index required but not found" in str(e).lower()
                and "file_name" in str(e)
            ):
                search_response = client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=search_limit,
                    with_payload=True,
                    score_threshold=score_threshold,
                )
            else:
                raise

        search_results = (
            search_response.points
            if hasattr(search_response, "points")
            else []
        )

        # Fallback 1: same filter, but remove score threshold.
        if not search_results:
            search_response = client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=search_limit,
                with_payload=True,
                query_filter=query_filter,
            )
            search_results = (
                search_response.points
                if hasattr(search_response, "points")
                else []
            )

        # Fallback 2: global search without threshold/filter for maximum recall.
        if not search_results:
            search_response = client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=search_limit,
                with_payload=True,
            )
            search_results = (
                search_response.points
                if hasattr(search_response, "points")
                else []
            )

        if not search_results:
            # Fallback 3: direct header scan for name queries on selected file.
            if target_file and _is_name_question(query):
                direct_name = _extract_name_from_file(client, collection_name, target_file)
                if direct_name:
                    text_response = (
                        f"The candidate's name appears to be **{direct_name}** "
                        f"(extracted directly from `{target_file}`)."
                    )
                    async_openai = AsyncOpenAI(api_key=openai_api_key)
                    audio_response = await async_openai.audio.speech.create(
                        model="gpt-4o-mini-tts",
                        voice=voice,
                        input=text_response,
                        instructions=_TTS_INSTRUCTIONS,
                        response_format="mp3",
                    )
                    audio_path = os.path.join(
                        tempfile.gettempdir(), f"response_{uuid.uuid4()}.mp3"
                    )
                    with open(audio_path, "wb") as f:
                        f.write(audio_response.content)

                    return {
                        "status": "success",
                        "text_response": text_response,
                        "audio_path": audio_path,
                        "sources": [target_file],
                        "chunks_used": 0,
                    }

            raise Exception(
                "No relevant documents found. "
                "Please upload a PDF first or rephrase your question."
            )

        # --- Step 2: assemble numbered context ---
        context_parts = []
        for i, result in enumerate(search_results, 1):
            payload = result.payload or {}
            content = payload.get("content", "").strip()
            source = payload.get("file_name", "Unknown")
            score = round(result.score, 3) if hasattr(result, "score") else "?"
            if content:
                context_parts.append(
                    f"[Chunk {i} | {source} | relevance {score}]\n{content}"
                )

        context_block = "\n\n---\n\n".join(context_parts)

        prompt = (
            f"CONTEXT CHUNKS:\n\n{context_block}\n\n"
            f"---\n\n"
            f"QUESTION: {query}\n\n"
            f"Answer the question using ONLY the context above. "
            f"Extract exact details when asked for specific facts. "
            f"Format the response clearly with short paragraphs and bullet points where useful."
        )

        # --- Step 3: generate text answer (gpt-4o-mini via agent) ---
        result = await Runner.run(processor_agent, prompt)
        text_response = result.final_output

        # Fallback name extraction for resume/CV header-style PDFs.
        if _is_name_question(query):
            lower_resp = text_response.lower()
            if "does not mention the name" in lower_resp or "not mention the name" in lower_resp:
                extracted_name = _extract_name_from_context(search_results)
                if extracted_name:
                    source_file = (search_results[0].payload or {}).get("file_name", "the uploaded resume")
                    text_response = (
                        f"The candidate's name appears to be **{extracted_name}** "
                        f"(extracted from the header of `{source_file}`)."
                    )

        # --- Step 4: generate MP3 audio ---
        async_openai = AsyncOpenAI(api_key=openai_api_key)

        audio_response = await async_openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text_response,
            instructions=_TTS_INSTRUCTIONS,
            response_format="mp3",
        )

        audio_path = os.path.join(
            tempfile.gettempdir(), f"response_{uuid.uuid4()}.mp3"
        )
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)

        sources = list(
            dict.fromkeys(
                r.payload.get("file_name", "Unknown")
                for r in search_results
                if r.payload
            )
        )

        return {
            "status": "success",
            "text_response": text_response,
            "audio_path": audio_path,
            "sources": sources,
            "chunks_used": len(search_results),
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "query": query}
