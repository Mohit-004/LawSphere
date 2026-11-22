"""Persistent Qdrant local-mode storage for document chunk vectors."""

import hashlib
import re
from pathlib import Path
from threading import Lock
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.database.models import Document, DocumentChunk

_client: QdrantClient | None = None
_client_lock = Lock()


class VectorStoreError(RuntimeError):
    """Raised when a vector collection cannot be created or updated."""


class VectorSearchHit:
    """A ranked vector result and its stored citation metadata."""

    def __init__(self, payload: dict, score: float) -> None:
        self.payload = payload
        self.score = score


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                Path(settings.vector_store_path).mkdir(parents=True, exist_ok=True)
                _client = QdrantClient(path=str(settings.vector_store_path))
    return _client


def get_embedding_collection_name(model_name: str | None = None) -> str:
    """Return a stable, model-specific collection name."""
    model = model_name or settings.embedding_model
    safe_model = re.sub(r"[^a-zA-Z0-9_-]+", "_", model).strip("_").lower() or "model"
    suffix = hashlib.sha1(model.encode("utf-8")).hexdigest()[:8]
    prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", settings.vector_collection_prefix).strip("_")
    return f"{prefix}_{safe_model[:40]}_{suffix}"


def index_document_chunks(
    document: Document,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
    model_name: str | None = None,
) -> None:
    """Create the model's collection if needed and upsert chunks idempotently."""
    if not chunks or len(chunks) != len(embeddings):
        raise VectorStoreError("Chunk and embedding counts must match and cannot be empty.")
    dimensions = len(embeddings[0])
    if dimensions == 0 or any(len(vector) != dimensions for vector in embeddings):
        raise VectorStoreError("Embedding vectors must share one non-zero dimension.")

    model = model_name or settings.embedding_model
    collection_name = get_embedding_collection_name(model)
    client = _get_client()
    try:
        if client.collection_exists(collection_name):
            info = client.get_collection(collection_name)
            vector_config = info.config.params.vectors
            existing_dimensions = getattr(vector_config, "size", None)
            if existing_dimensions != dimensions:
                raise VectorStoreError(
                    "The configured embedding model returned a different vector size than its existing collection."
                )
        else:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=dimensions, distance=models.Distance.COSINE),
            )

        points = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            point_id = str(uuid5(
                NAMESPACE_URL,
                f"lawsphere:{model}:{document.id}:{chunk.id}",
            ))
            payload = {
                "document_id": document.id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "title": document.title,
                "document_type": document.document_type,
                "text": chunk.text,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "embedding_model": model,
            }
            if document.source is not None:
                payload["source"] = document.source
            if chunk.page_number is not None:
                payload["page_number"] = chunk.page_number
            points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

        client.upsert(collection_name=collection_name, points=points, wait=True)
    except VectorStoreError:
        raise
    except Exception as exception:
        raise VectorStoreError("Could not persist document vectors in local Qdrant storage.") from exception


def search_chunks(
    embedding: list[float],
    limit: int,
    model_name: str | None = None,
) -> list[VectorSearchHit]:
    """Search the configured model collection and return ranked payloads."""
    collection_name = get_embedding_collection_name(model_name)
    try:
        client = _get_client()
        if not client.collection_exists(collection_name):
            return []
        response = client.query_points(
            collection_name=collection_name,
            query=embedding,
            limit=limit,
            with_payload=True,
        )
        return [
            VectorSearchHit(payload=point.payload or {}, score=float(point.score))
            for point in response.points
        ]
    except Exception as exception:
        raise VectorStoreError("Could not search local Qdrant vectors.") from exception


def close_vector_store() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None
