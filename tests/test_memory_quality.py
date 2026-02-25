"""Memory quality auto-tests for Muninn.

Validates that the storage layer enforces quality constraints:
- Depth 0 is always loaded on recall (and should be kept short)
- Content validation rejects empty/whitespace
- Tag hygiene (non-empty tags)
- Recall respects character budget and depth ordering
- Supersede chains hide old memories from recall
- Deduplication awareness (search finds near-duplicates)
"""

from __future__ import annotations

import pytest

from muninn.models import Memory, validate_memory_content, validate_memory_depth
from muninn.store import MuninnStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project(store: MuninnStore) -> str:
    """Create a test project and return its ID."""
    store.create_project(id="qtest", name="Quality Test")
    return "qtest"


# ---------------------------------------------------------------------------
# Depth 0: always loaded, should be concise
# ---------------------------------------------------------------------------


class TestDepthZeroAlwaysLoaded:
    """Depth-0 memories must always appear in recall regardless of depth filter."""

    def test_depth_zero_loaded_at_depth_zero(self, store, project):
        store.save_memory(project, "Short summary of the project.", depth=0)
        memories, _ = store.recall(project_id=project, depth=0)
        assert len(memories.get(project, [])) == 1

    def test_depth_zero_loaded_at_depth_one(self, store, project):
        store.save_memory(project, "Short summary.", depth=0)
        store.save_memory(project, "Current direction.", depth=1)
        memories, _ = store.recall(project_id=project, depth=1)
        mems = memories.get(project, [])
        depths = [m.depth for m in mems]
        assert 0 in depths
        assert 1 in depths

    def test_depth_zero_loaded_at_depth_three(self, store, project):
        store.save_memory(project, "Summary.", depth=0)
        store.save_memory(project, "Archive data.", depth=3)
        memories, _ = store.recall(project_id=project, depth=3)
        mems = memories.get(project, [])
        depths = [m.depth for m in mems]
        assert 0 in depths
        assert 3 in depths


# ---------------------------------------------------------------------------
# Depth ordering: lower depth first, newest first within depth
# ---------------------------------------------------------------------------


class TestRecallOrdering:
    """Recall returns memories ordered depth ASC, then updated_at DESC."""

    def test_depth_ordering(self, store, project):
        store.save_memory(project, "Deep archive.", depth=3)
        store.save_memory(project, "Project identity.", depth=0)
        store.save_memory(project, "Resume context.", depth=1)

        memories, _ = store.recall(project_id=project, depth=3)
        mems = memories.get(project, [])
        depths = [m.depth for m in mems]
        assert depths == sorted(depths), f"Expected ascending depth order, got {depths}"

    def test_newest_first_within_same_depth(self, store, project):
        import time

        store.save_memory(project, "First decision.", depth=1, tags=["decision"])
        time.sleep(0.05)  # Ensure distinct updated_at timestamps
        store.save_memory(project, "Second decision.", depth=1, tags=["decision"])

        memories, _ = store.recall(project_id=project, depth=1)
        mems = [m for m in memories.get(project, []) if m.depth == 1]
        assert len(mems) == 2
        # Newest first within same depth
        assert mems[0].content == "Second decision."
        assert mems[1].content == "First decision."


# ---------------------------------------------------------------------------
# Character budget enforcement
# ---------------------------------------------------------------------------


class TestCharacterBudget:
    """Recall must respect max_chars budget."""

    def test_budget_drops_excess_memories(self, store, project):
        store.save_memory(project, "A" * 100, depth=0)
        store.save_memory(project, "B" * 100, depth=1)
        store.save_memory(project, "C" * 100, depth=1)

        # Budget of 250 should fit first two (200 chars) but drop the third
        memories, stats = store.recall(project_id=project, depth=1, max_chars=250)
        mems = memories.get(project, [])
        assert stats["memories_loaded"] == 2
        assert stats["memories_dropped"] == 1
        assert stats["chars_loaded"] <= 250

    def test_budget_zero_loads_nothing(self, store, project):
        store.save_memory(project, "Some content.", depth=0)
        memories, stats = store.recall(project_id=project, depth=0, max_chars=0)
        assert stats["memories_loaded"] == 0

    def test_large_budget_loads_all(self, store, project):
        for i in range(10):
            store.save_memory(project, f"Memory {i}", depth=1)

        memories, stats = store.recall(project_id=project, depth=1, max_chars=100_000)
        assert stats["memories_loaded"] == 10
        assert stats["memories_dropped"] == 0


# ---------------------------------------------------------------------------
# Content validation
# ---------------------------------------------------------------------------


class TestContentValidation:
    """Store must reject empty or whitespace-only content."""

    def test_empty_content_rejected(self, store, project):
        with pytest.raises(ValueError, match="empty"):
            store.save_memory(project, "", depth=1)

    def test_whitespace_only_rejected(self, store, project):
        with pytest.raises(ValueError, match="empty"):
            store.save_memory(project, "   \n\t  ", depth=1)

    def test_valid_content_accepted(self, store, project):
        mem = store.save_memory(project, "Valid content.", depth=1)
        assert mem.content == "Valid content."


# ---------------------------------------------------------------------------
# Depth validation
# ---------------------------------------------------------------------------


class TestDepthValidation:
    """Depth must be 0-3."""

    def test_negative_depth_rejected(self):
        with pytest.raises(ValueError):
            validate_memory_depth(-1)

    def test_depth_four_rejected(self):
        with pytest.raises(ValueError):
            validate_memory_depth(4)

    def test_valid_depths_accepted(self):
        for d in range(4):
            validate_memory_depth(d)  # should not raise


# ---------------------------------------------------------------------------
# Tag hygiene
# ---------------------------------------------------------------------------


class TestTagHygiene:
    """Tags must be non-empty strings."""

    def test_empty_tag_rejected_in_model(self):
        with pytest.raises(ValueError, match="non-empty"):
            Memory(
                id="test",
                project_id="test",
                content="test",
                created_at="now",
                updated_at="now",
                tags=("valid", ""),
            )

    def test_whitespace_tag_rejected_in_model(self):
        with pytest.raises(ValueError, match="non-empty"):
            Memory(
                id="test",
                project_id="test",
                content="test",
                created_at="now",
                updated_at="now",
                tags=("  ",),
            )

    def test_valid_tags_stored_and_recalled(self, store, project):
        store.save_memory(project, "Tagged memory.", depth=1, tags=["decision", "api"])
        memories, _ = store.recall(project_id=project, depth=1)
        mems = memories.get(project, [])
        assert len(mems) == 1
        assert set(mems[0].tags) == {"decision", "api"}

    def test_tag_filter_recall(self, store, project):
        store.save_memory(project, "About auth.", depth=1, tags=["decision", "auth"])
        store.save_memory(project, "About api.", depth=1, tags=["decision", "api"])

        memories, _ = store.recall(project_id=project, depth=1, tags=["auth"])
        mems = memories.get(project, [])
        assert len(mems) == 1
        assert "auth" in mems[0].tags


# ---------------------------------------------------------------------------
# Supersede chains
# ---------------------------------------------------------------------------


class TestSupersedeChains:
    """Superseded memories must not appear in recall or search."""

    def test_superseded_memory_hidden_from_recall(self, store, project):
        old = store.save_memory(project, "Old decision.", depth=1)
        new = store.save_memory(project, "Updated decision.", depth=1)
        store.supersede_memory(old.id, new.id)

        memories, _ = store.recall(project_id=project, depth=1)
        mems = memories.get(project, [])
        ids = [m.id for m in mems]
        assert old.id not in ids
        assert new.id in ids

    def test_superseded_memory_hidden_from_search(self, store, project):
        old = store.save_memory(project, "SQLite WAL mode chosen.", depth=1)
        new = store.save_memory(project, "SQLite WAL mode confirmed.", depth=1)
        store.supersede_memory(old.id, new.id)

        results = store.search("SQLite WAL", project_id=project)
        ids = [m.id for m in results]
        assert old.id not in ids
        assert new.id in ids

    def test_deleted_memory_hidden(self, store, project):
        mem = store.save_memory(project, "To be deleted.", depth=1)
        store.delete_memory(mem.id)

        memories, _ = store.recall(project_id=project, depth=1)
        mems = memories.get(project, [])
        assert all(m.id != mem.id for m in mems)


# ---------------------------------------------------------------------------
# Deduplication awareness via search
# ---------------------------------------------------------------------------


class TestDeduplicationAwareness:
    """Search should find similar memories so callers can avoid duplicates."""

    def test_search_finds_similar_content(self, store, project):
        store.save_memory(project, "Using SQLite with WAL mode for concurrency.", depth=1)
        store.save_memory(project, "Database: PostgreSQL for production.", depth=1)

        # FTS5 phrase search — use a term present in the content
        results = store.search("SQLite", project_id=project)
        assert len(results) >= 1
        assert any("SQLite" in m.content for m in results)
        # Ensure PostgreSQL memory is NOT returned
        assert all("PostgreSQL" not in m.content for m in results)

    def test_search_across_projects(self, store):
        store.create_project(id="proj1", name="Project 1")
        store.create_project(id="proj2", name="Project 2")
        store.save_memory("proj1", "OAuth 2.0 implementation.", depth=1)
        store.save_memory("proj2", "OAuth token rotation.", depth=1)

        # Search without project filter finds both
        results = store.search("OAuth")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Multi-project recall
# ---------------------------------------------------------------------------


class TestMultiProjectRecall:
    """Recall without project_id loads all active projects."""

    def test_recall_all_active_projects(self, store):
        store.create_project(id="active1", name="Active 1")
        store.create_project(id="active2", name="Active 2")
        store.save_memory("active1", "Memory A.", depth=1)
        store.save_memory("active2", "Memory B.", depth=1)

        memories, stats = store.recall(depth=1)
        assert "active1" in memories
        assert "active2" in memories
        assert stats["memories_loaded"] == 2

    def test_recall_excludes_archived_projects(self, store):
        store.create_project(id="live", name="Live")
        store.create_project(id="dead", name="Dead")
        store.save_memory("live", "Active memory.", depth=1)
        store.save_memory("dead", "Archived memory.", depth=1)
        store.update_project("dead", status="archived")

        memories, _ = store.recall(depth=1)
        assert "live" in memories
        assert "dead" not in memories

    def test_recall_specific_project_ignores_status(self, store):
        """Explicit project_id recall should work even for archived projects."""
        store.create_project(id="arch", name="Archived")
        store.save_memory("arch", "Still accessible.", depth=1)
        store.update_project("arch", status="archived")

        memories, _ = store.recall(project_id="arch", depth=1)
        assert "arch" in memories
        assert len(memories["arch"]) == 1


# ---------------------------------------------------------------------------
# FTS5 search quality
# ---------------------------------------------------------------------------


class TestFTSSearchQuality:
    """Full-text search should handle various query patterns."""

    def test_partial_word_match_via_porter_stemming(self, store, project):
        store.save_memory(project, "Implementing authentication flow.", depth=1)
        # Porter stemmer should match "authenticat*" variants
        results = store.search("authentication", project_id=project)
        assert len(results) >= 1

    def test_search_no_results(self, store, project):
        store.save_memory(project, "Python web framework.", depth=1)
        results = store.search("kubernetes", project_id=project)
        assert len(results) == 0

    def test_search_respects_limit(self, store, project):
        for i in range(20):
            store.save_memory(project, f"Memory about testing item {i}.", depth=1)

        results = store.search("testing", project_id=project, limit=5)
        assert len(results) <= 5
