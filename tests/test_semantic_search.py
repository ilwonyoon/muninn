"""Integration tests for semantic search.

Uses synthetic numpy embeddings injected directly into the BLOB column.
No fastembed dependency required.
"""

from __future__ import annotations

import numpy as np
import pytest

from muninn.store import MuninnStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_embedding(seed: int, dim: int = 384) -> bytes:
    """Create a deterministic normalised embedding."""
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tobytes()


def _make_similar(base_seed: int, noise_seed: int, dim: int = 384) -> bytes:
    """Create an embedding similar to the base (cosine > 0.8)."""
    rng_base = np.random.RandomState(base_seed)
    base = rng_base.randn(dim).astype(np.float32)
    rng_noise = np.random.RandomState(noise_seed)
    noise = rng_noise.randn(dim).astype(np.float32) * 0.1
    vec = (base + noise).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tobytes()


def _inject_embedding(store: MuninnStore, memory_id: str, embedding: bytes) -> None:
    """Directly update the embedding BLOB for a memory."""
    conn = store._get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE memories SET embedding = ? WHERE id = ?",
                (embedding, memory_id),
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def semantic_store(store: MuninnStore):
    """Store with project and memories pre-loaded with synthetic embeddings."""
    store.create_project(id="semproj", name="Semantic Project")

    # "auth cluster" — seeds 10 and 12 are similar
    mem_auth = store.save_memory("semproj", "OAuth 2.0 authentication flow.", depth=1, tags=["auth"])
    mem_login = store.save_memory("semproj", "Login page needs testing.", depth=1, tags=["auth"])

    # "database cluster" — seed 50 is different
    mem_db = store.save_memory("semproj", "PostgreSQL with WAL mode.", depth=1, tags=["database"])

    # Inject synthetic embeddings
    auth_base = _make_embedding(seed=10)
    _inject_embedding(store, mem_auth.id, auth_base)
    _inject_embedding(store, mem_login.id, _make_similar(base_seed=10, noise_seed=12))
    _inject_embedding(store, mem_db.id, _make_embedding(seed=50))

    return store, {
        "auth": mem_auth,
        "login": mem_login,
        "db": mem_db,
        "auth_embedding": auth_base,
    }


# ---------------------------------------------------------------------------
# Tests: semantic_search returns similar memories
# ---------------------------------------------------------------------------


class TestSemanticSearchResults:
    """Test that semantic_search returns memories by vector similarity."""

    def test_returns_similar_memories(self, semantic_store):
        store, refs = semantic_store
        query = refs["auth_embedding"]  # Should match auth cluster

        results = store.semantic_search(query, project_id="semproj", threshold=0.3)
        ids = [m.id for m, _ in results]

        # Auth and login should be in results (similar embeddings)
        assert refs["auth"].id in ids
        assert refs["login"].id in ids

    def test_results_sorted_by_similarity(self, semantic_store):
        store, refs = semantic_store
        query = refs["auth_embedding"]

        results = store.semantic_search(query, project_id="semproj", threshold=-1.0)
        scores = [score for _, score in results]

        # Should be in descending order
        assert scores == sorted(scores, reverse=True)

    def test_exact_match_scores_highest(self, semantic_store):
        store, refs = semantic_store
        query = refs["auth_embedding"]

        results = store.semantic_search(query, project_id="semproj", threshold=-1.0)
        # The auth memory has the exact same embedding as query
        assert results[0][0].id == refs["auth"].id
        assert results[0][1] > 0.99


# ---------------------------------------------------------------------------
# Tests: filters
# ---------------------------------------------------------------------------


class TestSemanticSearchFilters:
    """Test that semantic_search respects project and tag filters."""

    def test_respects_project_filter(self, store):
        store.create_project(id="proj-a", name="A")
        store.create_project(id="proj-b", name="B")

        mem_a = store.save_memory("proj-a", "Memory in A.", depth=1)
        mem_b = store.save_memory("proj-b", "Memory in B.", depth=1)

        emb = _make_embedding(seed=1)
        _inject_embedding(store, mem_a.id, emb)
        _inject_embedding(store, mem_b.id, _make_similar(base_seed=1, noise_seed=2))

        results = store.semantic_search(emb, project_id="proj-a", threshold=-1.0)
        ids = [m.id for m, _ in results]
        assert mem_a.id in ids
        assert mem_b.id not in ids

    def test_respects_tag_filter(self, semantic_store):
        store, refs = semantic_store
        query = refs["auth_embedding"]

        results = store.semantic_search(
            query, project_id="semproj", tags=["database"], threshold=-1.0,
        )
        ids = [m.id for m, _ in results]
        # Only the db memory has the "database" tag
        assert refs["db"].id in ids
        assert refs["auth"].id not in ids

    def test_respects_limit(self, semantic_store):
        store, refs = semantic_store
        query = refs["auth_embedding"]

        results = store.semantic_search(
            query, project_id="semproj", limit=1, threshold=-1.0,
        )
        assert len(results) <= 1


# ---------------------------------------------------------------------------
# Tests: superseded exclusion
# ---------------------------------------------------------------------------


class TestSemanticSearchSuperseded:
    """Superseded memories must not appear in semantic search."""

    def test_excludes_superseded(self, store):
        store.create_project(id="supproj", name="Sup")

        old = store.save_memory("supproj", "Old auth decision.", depth=1)
        new = store.save_memory("supproj", "New auth decision.", depth=1)

        emb = _make_embedding(seed=1)
        _inject_embedding(store, old.id, emb)
        _inject_embedding(store, new.id, _make_similar(base_seed=1, noise_seed=2))

        store.supersede_memory(old.id, new.id)

        results = store.semantic_search(emb, project_id="supproj", threshold=-1.0)
        ids = [m.id for m, _ in results]
        assert old.id not in ids
        assert new.id in ids


# ---------------------------------------------------------------------------
# Tests: no embeddings
# ---------------------------------------------------------------------------


class TestSemanticSearchNoEmbeddings:
    """Semantic search should return empty when no embeddings exist."""

    def test_returns_empty_without_embeddings(self, store):
        store.create_project(id="noemb", name="No Embeddings")
        store.save_memory("noemb", "No embedding here.", depth=1)

        query = _make_embedding(seed=1)
        results = store.semantic_search(query, project_id="noemb")
        assert results == []


# ---------------------------------------------------------------------------
# Tests: schema v3 migration
# ---------------------------------------------------------------------------


class TestSchemaV3:
    """Test that the embedding column exists after migration."""

    def test_embedding_column_exists(self, store):
        store.create_project(id="v3test", name="V3 Test")
        mem = store.save_memory("v3test", "Test content.", depth=1)

        # Verify the column exists by querying it
        conn = store._get_connection()
        try:
            row = conn.execute(
                "SELECT embedding FROM memories WHERE id = ?",
                (mem.id,),
            ).fetchone()
            # fastembed not installed, so embedding should be NULL
            assert row["embedding"] is None
        finally:
            conn.close()

    def test_schema_version_is_3(self, store):
        conn = store._get_connection()
        try:
            row = conn.execute(
                "SELECT MAX(version) AS v FROM schema_version"
            ).fetchone()
            assert row["v"] == 3
        finally:
            conn.close()
