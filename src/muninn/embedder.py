"""Embedding engine for Muninn semantic search.

Gracefully degrades when ``fastembed`` is not installed (optional dependency).
All public functions return ``None`` instead of raising when unavailable.

Install semantic search support::

    pip install muninn-mcp[semantic]
"""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

_FASTEMBED_AVAILABLE = False
_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_EMBEDDING_DIM = 384

try:
    from fastembed import TextEmbedding  # noqa: F401

    _FASTEMBED_AVAILABLE = True
except ImportError:
    pass


def is_available() -> bool:
    """Return True if semantic search dependencies are installed."""
    return _FASTEMBED_AVAILABLE


@lru_cache(maxsize=1)
def _get_model() -> object | None:
    """Lazy-load and cache the embedding model singleton.

    First call downloads the model (~100 MB) if not cached locally.
    Returns ``None`` if fastembed is not installed.
    """
    if not _FASTEMBED_AVAILABLE:
        return None
    try:
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=_MODEL_NAME)
    except Exception as exc:
        logger.warning("Failed to load embedding model: %s", exc)
        return None


def embedding_dim() -> int:
    """Return the dimensionality of the embedding model (384)."""
    return _EMBEDDING_DIM


def embed_text(text: str) -> bytes | None:
    """Embed a single text string into a float32 byte blob.

    Returns ``None`` if fastembed is unavailable or embedding fails.
    The returned bytes are a numpy ``float32`` array serialised via
    ``ndarray.tobytes()``.
    """
    model = _get_model()
    if model is None:
        return None
    try:
        import numpy as np

        embeddings = list(model.embed([text]))
        vector = np.array(embeddings[0], dtype=np.float32)
        return vector.tobytes()
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None


def embed_texts(texts: list[str]) -> list[bytes | None]:
    """Batch-embed multiple texts.

    Returns a list aligned with the input.  Each element is a float32
    byte blob, or ``None`` if embedding failed for that text.
    """
    model = _get_model()
    if model is None:
        return [None] * len(texts)
    try:
        import numpy as np

        embeddings = list(model.embed(texts))
        return [
            np.array(vec, dtype=np.float32).tobytes() for vec in embeddings
        ]
    except Exception as exc:
        logger.warning("Batch embedding failed: %s", exc)
        return [None] * len(texts)


def cosine_similarity_search(
    query_blob: bytes,
    candidate_blobs: list[tuple[str, bytes]],
    top_k: int = 10,
    threshold: float = 0.3,
) -> list[tuple[str, float]]:
    """Compute cosine similarity between *query_blob* and each candidate.

    Parameters
    ----------
    query_blob:
        The query embedding as raw float32 bytes.
    candidate_blobs:
        List of ``(memory_id, embedding_bytes)`` tuples.
    top_k:
        Maximum number of results to return.
    threshold:
        Minimum cosine similarity (0–1) to include a result.

    Returns
    -------
    List of ``(memory_id, similarity_score)`` sorted by score descending.
    """
    import numpy as np

    query_vec = np.frombuffer(query_blob, dtype=np.float32).copy()
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []
    query_vec = query_vec / query_norm

    results: list[tuple[str, float]] = []
    for memory_id, blob in candidate_blobs:
        candidate_vec = np.frombuffer(blob, dtype=np.float32).copy()
        candidate_norm = np.linalg.norm(candidate_vec)
        if candidate_norm == 0:
            continue
        similarity = float(np.dot(query_vec, candidate_vec / candidate_norm))
        if similarity >= threshold:
            results.append((memory_id, similarity))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
