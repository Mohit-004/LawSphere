"""Batch text embeddings through the local Ollama HTTP API."""

import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class EmbeddingError(RuntimeError):
    """Raised when the local embedding model cannot produce valid vectors."""


class OllamaEmbeddingProvider:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.embedding_model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed text batches, checking order, dimensions, and finite values."""
        if not texts:
            return []
        batch_size = settings.embedding_batch_size
        if batch_size < 1:
            raise EmbeddingError("Embedding batch size must be greater than zero.")

        result: list[list[float]] = []
        expected_dimension: int | None = None
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            embeddings = self._embed_batch(batch)
            if len(embeddings) != len(batch):
                raise EmbeddingError("Ollama returned an unexpected number of embeddings.")

            for vector in embeddings:
                if not vector or any(not math.isfinite(value) for value in vector):
                    raise EmbeddingError("Ollama returned an empty or invalid embedding vector.")
                if expected_dimension is None:
                    expected_dimension = len(vector)
                elif len(vector) != expected_dimension:
                    raise EmbeddingError("Ollama returned vectors with inconsistent dimensions.")
                result.append(vector)
        return result

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/embed"
        request = Request(
            url,
            data=json.dumps({"model": self.model, "input": texts}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=settings.embedding_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exception:
            detail = exception.read().decode("utf-8", errors="replace")[:400]
            raise EmbeddingError(
                f"Ollama embedding request failed with HTTP {exception.code}: {detail}"
            ) from exception
        except (URLError, TimeoutError, OSError, ValueError) as exception:
            raise EmbeddingError("Could not reach the configured local Ollama embedding endpoint.") from exception

        raw_embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        if not isinstance(raw_embeddings, list):
            raise EmbeddingError("Ollama returned a response without an embeddings list.")

        vectors: list[list[float]] = []
        for raw_vector in raw_embeddings:
            if not isinstance(raw_vector, list):
                raise EmbeddingError("Ollama returned an invalid embedding vector.")
            try:
                vectors.append([float(value) for value in raw_vector])
            except (TypeError, ValueError) as exception:
                raise EmbeddingError("Ollama returned a non-numeric embedding value.") from exception
        return vectors
