"""Unit tests for the embedding engine.

All tests use synthetic numpy embeddings — fastembed is NOT required.
"""

from __future__ import annotations

import numpy as np
import pytest

from muninn.embedder import cosine_similarity_search, embedding_dim


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_embedding(seed: int = 42, dim: int = 384) -> bytes:
    """Create a deterministic normalised fake embedding."""
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tobytes()


def _make_similar_embedding(base_seed: int, noise_seed: int, dim: int = 384) -> bytes:
    """Create an embedding similar to the base (cosine > 0.8)."""
    rng_base = np.random.RandomState(base_seed)
    base = rng_base.randn(dim).astype(np.float32)

    rng_noise = np.random.RandomState(noise_seed)
    noise = rng_noise.randn(dim).astype(np.float32) * 0.1

    vec = (base + noise).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tobytes()


def _make_orthogonal_embedding(seed: int, dim: int = 384) -> bytes:
    """Create an embedding that is roughly orthogonal to seed=42."""
    rng = np.random.RandomState(seed + 1000)
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tobytes()


# ---------------------------------------------------------------------------
# Tests: cosine_similarity_search
# ---------------------------------------------------------------------------


class TestCosineSimilaritySearch:
    """Tests for the cosine similarity search function."""

    def test_returns_sorted_by_similarity(self):
        query = _make_embedding(seed=42)
        similar = _make_similar_embedding(base_seed=42, noise_seed=1)
        different = _make_orthogonal_embedding(seed=99)

        candidates = [
            ("mem-different", different),
            ("mem-similar", similar),
        ]

        # Use negative threshold to include all results (cosine can be negative)
        results = cosine_similarity_search(query, candidates, top_k=10, threshold=-1.0)
        assert len(results) == 2
        # Similar should rank first
        assert results[0][0] == "mem-similar"
        assert results[0][1] > results[1][1]

    def test_respects_threshold(self):
        query = _make_embedding(seed=42)
        similar = _make_similar_embedding(base_seed=42, noise_seed=1)
        different = _make_orthogonal_embedding(seed=99)

        candidates = [
            ("mem-similar", similar),
            ("mem-different", different),
        ]

        # High threshold should only return the similar one
        results = cosine_similarity_search(query, candidates, top_k=10, threshold=0.7)
        assert all(score >= 0.7 for _, score in results)
        if results:
            assert results[0][0] == "mem-similar"

    def test_respects_top_k(self):
        query = _make_embedding(seed=42)
        candidates = [
            (f"mem-{i}", _make_similar_embedding(base_seed=42, noise_seed=i))
            for i in range(20)
        ]

        results = cosine_similarity_search(query, candidates, top_k=5, threshold=0.0)
        assert len(results) <= 5

    def test_empty_candidates(self):
        query = _make_embedding(seed=42)
        results = cosine_similarity_search(query, [], top_k=10, threshold=0.0)
        assert results == []

    def test_zero_query_vector(self):
        zero_blob = np.zeros(384, dtype=np.float32).tobytes()
        candidate = _make_embedding(seed=1)

        results = cosine_similarity_search(
            zero_blob, [("mem-1", candidate)], top_k=10, threshold=0.0
        )
        assert results == []

    def test_zero_candidate_vector_skipped(self):
        query = _make_embedding(seed=42)
        zero_blob = np.zeros(384, dtype=np.float32).tobytes()
        normal = _make_embedding(seed=1)

        candidates = [
            ("mem-zero", zero_blob),
            ("mem-normal", normal),
        ]

        results = cosine_similarity_search(query, candidates, top_k=10, threshold=0.0)
        ids = [r[0] for r in results]
        assert "mem-zero" not in ids
        assert "mem-normal" in ids

    def test_identical_vectors_score_one(self):
        embedding = _make_embedding(seed=42)
        results = cosine_similarity_search(
            embedding, [("mem-same", embedding)], top_k=10, threshold=0.0
        )
        assert len(results) == 1
        assert abs(results[0][1] - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# Tests: embedding_dim
# ---------------------------------------------------------------------------


class TestEmbeddingDim:
    def test_returns_384(self):
        assert embedding_dim() == 384


# ---------------------------------------------------------------------------
# Tests: graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Tests for behavior when fastembed is not installed."""

    def test_embed_text_returns_none_without_fastembed(self):
        from muninn.embedder import embed_text

        # fastembed is not installed in test env, so this should return None
        result = embed_text("test text")
        assert result is None

    def test_embed_texts_returns_nones_without_fastembed(self):
        from muninn.embedder import embed_texts

        results = embed_texts(["text1", "text2"])
        assert results == [None, None]

    def test_is_available_returns_false_without_fastembed(self):
        from muninn.embedder import is_available

        # In test env, fastembed is not installed
        assert is_available() is False
