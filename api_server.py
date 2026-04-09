"""FastAPI backend for Voice RAG web UI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_config.agent_setup import setup_agents
from config.settings import AVAILABLE_VOICES, COLLECTION_NAME, DEFAULT_VOICE
from services.pdf_processor import process_pdf
from services.query_processor import process_query
from services.vector_store import setup_qdrant, store_embeddings

load_dotenv()

WEB_DIR = Path(__file__).parent / "web"


@dataclass
class AppState:
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    openai_api_key: str = ""
    selected_voice: str = DEFAULT_VOICE
    client: Optional[object] = None
    embedding_model: Optional[object] = None
    processor_agent: Optional[object] = None
    processed_documents: List[str] = field(default_factory=list)

    @property
    def has_credentials(self) -> bool:
        return bool(self.qdrant_url and self.qdrant_api_key and self.openai_api_key)


state = AppState()
app = FastAPI(title="Voice RAG Web API")
app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")


class ConfigPayload(BaseModel):
    qdrant_url: str
    qdrant_api_key: str
    openai_api_key: str
    selected_voice: str = DEFAULT_VOICE


class QueryPayload(BaseModel):
    query: str
    search_scope: Optional[str] = None


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/status")
async def get_status() -> dict:
    return {
        "ready": bool(state.client and state.embedding_model),
        "has_credentials": state.has_credentials,
        "documents": state.processed_documents,
        "selected_voice": state.selected_voice,
        "voices": AVAILABLE_VOICES,
        "embed_backend": getattr(state.embedding_model, "backend", None) if state.embedding_model else None,
    }


@app.post("/api/config")
async def set_config(payload: ConfigPayload) -> dict:
    if payload.selected_voice not in AVAILABLE_VOICES:
        raise HTTPException(status_code=400, detail="Invalid voice selected.")

    state.qdrant_url = payload.qdrant_url.strip()
    state.qdrant_api_key = payload.qdrant_api_key.strip()
    state.openai_api_key = payload.openai_api_key.strip()
    state.selected_voice = payload.selected_voice

    try:
        state.client, state.embedding_model = setup_qdrant(
            state.qdrant_url,
            state.qdrant_api_key,
            state.openai_api_key,
        )
        state.processor_agent = None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "message": "Configuration saved and backend initialized."}


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
) -> dict:
    if not state.has_credentials:
        raise HTTPException(status_code=400, detail="Please configure credentials first.")
    if not state.client or not state.embedding_model:
        raise HTTPException(status_code=400, detail="Backend not initialized. Save config first.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if file.filename in state.processed_documents:
        return {"ok": True, "message": f"{file.filename} already indexed.", "chunks": 0}

    content = await file.read()

    class _InMemoryFile:
        def __init__(self, name: str, data: bytes):
            self.name = name
            self._data = data

        def getvalue(self) -> bytes:
            return self._data

    try:
        documents = process_pdf(_InMemoryFile(file.filename, content))
        if not documents:
            raise HTTPException(status_code=400, detail="No extractable text found in PDF.")

        store_embeddings(
            state.client,
            state.embedding_model,
            documents,
            COLLECTION_NAME,
        )
        state.processed_documents.append(file.filename)
        return {"ok": True, "message": f"Indexed {file.filename}", "chunks": len(documents)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/query")
async def query_docs(payload: QueryPayload) -> dict:
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if not state.client or not state.embedding_model:
        raise HTTPException(status_code=400, detail="Please configure and upload a document first.")

    if not state.processor_agent:
        state.processor_agent = setup_agents(state.openai_api_key)

    target_file = payload.search_scope if payload.search_scope and payload.search_scope != "All documents" else None

    result = await process_query(
        query,
        state.client,
        state.embedding_model,
        state.processor_agent,
        state.openai_api_key,
        state.selected_voice,
        target_file,
        COLLECTION_NAME,
    )
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown query error"))
    return result


@app.get("/api/audio")
async def fetch_audio(path: str) -> FileResponse:
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(file_path, media_type="audio/mpeg", filename=file_path.name)

