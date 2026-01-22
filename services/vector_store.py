"""Vector store service for Qdrant operations."""

from typing import Tuple
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from fastembed import TextEmbedding
from config.settings import COLLECTION_NAME


def setup_qdrant(qdrant_url: str, qdrant_api_key: str) -> Tuple[QdrantClient, TextEmbedding]:
    """Initialize Qdrant client and embedding model.
    
    Args:
        qdrant_url: Qdrant server URL
        qdrant_api_key: Qdrant API key
        
    Returns:
        Tuple of (QdrantClient, TextEmbedding model)
        
    Raises:
        ValueError: If credentials are not provided
    """
    if not qdrant_url or not qdrant_api_key:
        raise ValueError(
            "Qdrant credentials not provided. Please enter your Qdrant URL and API key in the sidebar."
        )
    
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key
    )
    
    embedding_model = TextEmbedding()
    test_embedding = list(embedding_model.embed(["test"]))[0]
    embedding_dim = len(test_embedding)
    
    try:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE
            )
        )
    except Exception as e:
        if "already exists" not in str(e):
            raise e
    
    return client, embedding_model


def store_embeddings(
    client: QdrantClient,
    embedding_model: TextEmbedding,
    documents: list,
    collection_name: str = COLLECTION_NAME
) -> None:
    """Store document embeddings in Qdrant.
    
    Args:
        client: Qdrant client instance
        embedding_model: Text embedding model
        documents: List of document chunks to embed and store
        collection_name: Name of the Qdrant collection
    """
    from qdrant_client.http import models
    import uuid
    
    for doc in documents:
        embedding = list(embedding_model.embed([doc.page_content]))[0]
        client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding.tolist(),
                    payload={
                        "content": doc.page_content,
                        **doc.metadata
                    }
                )
            ]
        )


def search_documents(
    client: QdrantClient,
    embedding_model: TextEmbedding,
    query: str,
    collection_name: str = COLLECTION_NAME,
    limit: int = 3
) -> list:
    """Search for relevant documents in the vector store.
    
    Args:
        client: Qdrant client instance
        embedding_model: Text embedding model
        query: Search query text
        collection_name: Name of the Qdrant collection
        limit: Maximum number of results to return
        
    Returns:
        List of search results (points with payloads)
    """
    query_embedding = list(embedding_model.embed([query]))[0]
    
    search_response = client.query_points(
        collection_name=collection_name,
        query=query_embedding.tolist(),
        limit=limit,
        with_payload=True
    )
    
    return search_response.points if hasattr(search_response, 'points') else []
