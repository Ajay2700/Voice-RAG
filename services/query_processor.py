"""Query processing service for handling user queries."""

from typing import Dict
import os
import tempfile
import uuid
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer
from agents import Runner
from config.settings import COLLECTION_NAME, SEARCH_LIMIT


async def process_query(
    query: str,
    client: QdrantClient,
    embedding_model: TextEmbedding,
    processor_agent,
    tts_agent,
    openai_api_key: str,
    voice: str,
    collection_name: str = COLLECTION_NAME,
    search_limit: int = SEARCH_LIMIT
) -> Dict:
    """Process user query and generate voice response.
    
    Args:
        query: User's question
        client: Qdrant client instance
        embedding_model: Text embedding model
        processor_agent: Documentation processor agent
        tts_agent: Text-to-speech agent
        openai_api_key: OpenAI API key
        voice: Voice name for TTS
        collection_name: Qdrant collection name
        search_limit: Maximum number of documents to retrieve
        
    Returns:
        Dictionary with status, response text, audio path, and sources
    """
    try:
        # Step 1: Generate query embedding and search
        query_embedding = list(embedding_model.embed([query]))[0]
        
        search_response = client.query_points(
            collection_name=collection_name,
            query=query_embedding.tolist(),
            limit=search_limit,
            with_payload=True
        )
        
        search_results = search_response.points if hasattr(search_response, 'points') else []
        
        if not search_results:
            raise Exception("No relevant documents found in the vector database")
        
        # Step 2: Prepare context from search results
        context = "Based on the following documentation:\n\n"
        for i, result in enumerate(search_results, 1):
            payload = result.payload
            if not payload:
                continue
            content = payload.get('content', '')
            source = payload.get('file_name', 'Unknown Source')
            context += f"From {source}:\n{content}\n\n"
        
        context += f"\nUser Question: {query}\n\n"
        context += "Please provide a clear, concise answer that can be easily spoken out loud."
        
        # Step 3: Generate text response using processor agent
        processor_result = await Runner.run(processor_agent, context)
        text_response = processor_result.final_output
        
        # Step 4: Generate voice instructions using TTS agent
        tts_result = await Runner.run(tts_agent, text_response)
        voice_instructions = tts_result.final_output
        
        # Step 5: Generate and play audio with streaming
        async_openai = AsyncOpenAI(api_key=openai_api_key)
        
        # Create streaming response and play
        async with async_openai.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text_response,
            instructions=voice_instructions,
            response_format="pcm",
        ) as stream_response:
            # Play audio directly using LocalAudioPlayer
            await LocalAudioPlayer().play(stream_response)
            
            # Also save as MP3 for download
            audio_response = await async_openai.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=voice,
                input=text_response,
                instructions=voice_instructions,
                response_format="mp3"
            )
            
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"response_{uuid.uuid4()}.mp3")
            
            with open(audio_path, "wb") as f:
                f.write(audio_response.content)
        
        return {
            "status": "success",
            "text_response": text_response,
            "voice_instructions": voice_instructions,
            "audio_path": audio_path,
            "sources": [r.payload.get('file_name', 'Unknown Source') for r in search_results if r.payload]
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }
