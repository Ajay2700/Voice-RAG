"""Vector store service for Qdrant operations."""

import uuid
from typing import List, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from openai import OpenAI

from config.settings import COLLECTION_NAME, SCORE_THRESHOLD

_UPSERT_BATCH = 64


def _vector_size_from_collection(client: QdrantClient, collection_name: str) -> int:
    """Read existing vector size from a collection."""
    info = client.get_collection(collection_name=collection_name)
    vectors_cfg = info.config.params.vectors

    # Single-vector collection
    if hasattr(vectors_cfg, "size"):
        return int(vectors_cfg.size)

    # Named vectors collection (dict-like)
    if isinstance(vectors_cfg, dict):
        first_key = next(iter(vectors_cfg))
        return int(vectors_cfg[first_key].size)

    raise ValueError("Unable to determine vector dimension from existing collection config.")


def _ensure_collection_dim(
    client: QdrantClient,
    collection_name: str,
    embedding_dim: int,
) -> None:
    """Ensure collection dimension matches embedder; recreate if mismatched."""
    try:
        existing_dim = _vector_size_from_collection(client, collection_name)
        if existing_dim == embedding_dim:
            return

        # Existing collection is incompatible with current embedder (e.g. 384 vs 1536).
        # Recreate so new vectors can be inserted successfully.
        client.delete_collection(collection_name=collection_name)
    except Exception as e:
        # If collection does not exist, create below.
        if "not found" not in str(e).lower():
            raise

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embedding_dim,
            distance=Distance.COSINE,
        ),
    )


def _ensure_payload_indexes(client: QdrantClient, collection_name: str) -> None:
    """Create payload indexes required for filtered search."""
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="file_name",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        # Safe to ignore if index already exists.
        if "already exists" not in str(e).lower():
            raise


class AdaptiveEmbedder:
    """Use FastEmbed when available; fall back to OpenAI embeddings."""

    def __init__(self, openai_api_key: str) -> None:
        self.backend = "fastembed"
        self._fastembed = None
        self._openai = None
        self._openai_model = "text-embedding-3-small"

        try:
            # Import lazily so deployments can run without fastembed installed.
            from fastembed import TextEmbedding  # type: ignore

            self._fastembed = TextEmbedding()
            _ = self.embed(["test"])
        except Exception:
            if not openai_api_key:
                raise ValueError(
                    "Could not initialize local embedding model and no OpenAI key was provided "
                    "for fallback embeddings."
                )
            self.backend = "openai"
            self._openai = OpenAI(api_key=openai_api_key)

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self.backend == "fastembed":
            vectors = list(self._fastembed.embed(texts))
            return [v.tolist() for v in vectors]

        response = self._openai.embeddings.create(model=self._openai_model, input=texts)
        return [item.embedding for item in response.data]


def setup_qdrant(
    qdrant_url: str,
    qdrant_api_key: str,
    openai_api_key: str,
) -> Tuple[QdrantClient, AdaptiveEmbedder]:
    """Initialize Qdrant client and embedding model."""
    if not qdrant_url or not qdrant_api_key:
        raise ValueError(
            "Qdrant credentials not provided. "
            "Please enter your Qdrant URL and API key in the sidebar."
        )

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    embedding_model = AdaptiveEmbedder(openai_api_key=openai_api_key)
    test_embedding = embedding_model.embed(["test"])[0]
    embedding_dim = len(test_embedding)

    _ensure_collection_dim(client, COLLECTION_NAME, embedding_dim)

    _ensure_payload_indexes(client, COLLECTION_NAME)

    return client, embedding_model


def store_embeddings(
    client: QdrantClient,
    embedding_model: AdaptiveEmbedder,
    documents: list,
    collection_name: str = COLLECTION_NAME,
) -> None:
    """Batch-upsert document embeddings into Qdrant."""
    texts = [doc.page_content for doc in documents]
    embeddings = embedding_model.embed(texts)

    points: List[models.PointStruct] = []
    for doc, emb in zip(documents, embeddings):
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={"content": doc.page_content, **doc.metadata},
            )
        )

    for start in range(0, len(points), _UPSERT_BATCH):
        batch = points[start : start + _UPSERT_BATCH]
        client.upsert(collection_name=collection_name, points=batch)


def search_documents(
    client: QdrantClient,
    embedding_model: AdaptiveEmbedder,
    query: str,
    collection_name: str = COLLECTION_NAME,
    limit: int = 8,
    score_threshold: float = SCORE_THRESHOLD,
) -> list:
    """Search for relevant documents, filtering by score threshold."""
    query_embedding = embedding_model.embed([query])[0]

    search_response = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        limit=limit,
        with_payload=True,
        score_threshold=score_threshold,
    )

    return search_response.points if hasattr(search_response, "points") else []
