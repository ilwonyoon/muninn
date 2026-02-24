"""Unit tests for MuninnStore (SQLite backend)."""

from __future__ import annotations

import multiprocessing
import time

import pytest

from muninn.models import MemorySource, ProjectStatus
from muninn.store import MuninnStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(store: MuninnStore, id: str = "proj-1", name: str = "Test Project") -> object:
    return store.create_project(id=id, name=name)


def _save_memory(
    store: MuninnStore,
    project_id: str = "proj-1",
    content: str = "A memory",
    depth: int = 1,
    tags: list[str] | None = None,
) -> object:
    return store.save_memory(
        project_id=project_id,
        content=content,
        depth=depth,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

class TestCreateProject:
    def test_create_project(self, store):
        """Create a project and verify all fields are stored correctly."""
        project = store.create_project(
            id="proj-abc",
            name="My Project",
            summary="A summary",
            github_repo="https://github.com/user/repo",
        )

        assert project.id == "proj-abc"
        assert project.name == "My Project"
        assert project.summary == "A summary"
        assert project.github_repo == "https://github.com/user/repo"
        assert project.memory_count == 0
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_create_project_default_status(self, store):
        """A newly created project defaults to 'active' status."""
        project = store.create_project(id="proj-1", name="Active Project")

        assert project.status == ProjectStatus.ACTIVE

    def test_create_project_persists(self, store):
        """A created project can be retrieved via get_project."""
        store.create_project(id="proj-persist", name="Persistent")
        fetched = store.get_project("proj-persist")

        assert fetched is not None
        assert fetched.id == "proj-persist"
        assert fetched.name == "Persistent"


class TestGetProject:
    def test_get_project_not_found(self, store):
        """get_project returns None for a non-existent project id."""
        result = store.get_project("does-not-exist")

        assert result is None

    def test_get_project_returns_correct_project(self, store):
        """get_project returns the exact project that was created."""
        store.create_project(id="proj-x", name="X")
        store.create_project(id="proj-y", name="Y")

        result = store.get_project("proj-x")

        assert result is not None
        assert result.id == "proj-x"
        assert result.name == "X"


class TestListProjects:
    def test_list_projects_all(self, store):
        """list_projects returns all projects when no filter is given."""
        store.create_project(id="p1", name="One")
        store.create_project(id="p2", name="Two")
        store.create_project(id="p3", name="Three")

        projects = store.list_projects()

        assert len(projects) == 3
        ids = {p.id for p in projects}
        assert ids == {"p1", "p2", "p3"}

    def test_list_projects_filter_by_status(self, store):
        """list_projects with a status filter returns only matching projects."""
        store.create_project(id="p-active", name="Active")
        store.create_project(id="p-paused", name="Paused")
        store.update_project("p-paused", status="paused")

        active = store.list_projects(status="active")
        paused = store.list_projects(status="paused")

        assert len(active) == 1
        assert active[0].id == "p-active"
        assert len(paused) == 1
        assert paused[0].id == "p-paused"

    def test_list_projects_empty(self, store):
        """list_projects returns an empty list when no projects exist."""
        assert store.list_projects() == []


class TestUpdateProject:
    def test_update_project_status(self, store):
        """Update project status from active to paused."""
        store.create_project(id="proj-upd", name="Updatable")

        updated = store.update_project("proj-upd", status="paused")

        assert updated.status == "paused"
        fetched = store.get_project("proj-upd")
        assert fetched is not None
        assert fetched.status == "paused"

    def test_update_project_name(self, store):
        """update_project can change the name field."""
        store.create_project(id="proj-name", name="Old Name")

        updated = store.update_project("proj-name", name="New Name")

        assert updated.name == "New Name"

    def test_update_project_not_found(self, store):
        """update_project raises ValueError when project does not exist."""
        with pytest.raises(ValueError, match="not found"):
            store.update_project("no-such-project", status="paused")

    def test_update_project_invalid_status(self, store):
        """update_project raises ValueError for an unrecognised status value."""
        store.create_project(id="proj-bad", name="Bad Status")

        with pytest.raises(ValueError):
            store.update_project("proj-bad", status="flying")

    def test_update_project_refreshes_updated_at(self, store):
        """update_project refreshes the updated_at timestamp."""
        store.create_project(id="proj-ts", name="Timestamp")
        original = store.get_project("proj-ts")
        assert original is not None

        # Sleep a tiny bit so timestamps differ.
        time.sleep(0.01)
        updated = store.update_project("proj-ts", name="Timestamp Updated")

        # updated_at should be >= original (could be equal in the same second)
        assert updated.updated_at >= original.updated_at


# ---------------------------------------------------------------------------
# Memory CRUD
# ---------------------------------------------------------------------------

class TestSaveMemory:
    def test_save_memory(self, store):
        """Save a memory and verify it has a UUID id and correct fields."""
        _make_project(store)
        memory = store.save_memory(
            project_id="proj-1",
            content="Important decision",
            depth=2,
            source=MemorySource.MANUAL,
        )

        assert memory.id is not None
        assert len(memory.id) == 32  # uuid4().hex is 32 hex chars
        assert memory.project_id == "proj-1"
        assert memory.content == "Important decision"
        assert memory.depth == 2
        assert memory.source == MemorySource.MANUAL
        assert memory.superseded_by is None
        assert memory.created_at is not None
        assert memory.updated_at is not None

    def test_save_memory_with_tags(self, store):
        """Save a memory with tags; verify they are stored and returned."""
        _make_project(store)
        memory = store.save_memory(
            project_id="proj-1",
            content="Tagged memory",
            tags=["architecture", "backend"],
        )

        assert sorted(memory.tags) == ["architecture", "backend"]

    def test_save_memory_default_source_is_conversation(self, store):
        """Default memory source is 'conversation'."""
        _make_project(store)
        memory = store.save_memory(project_id="proj-1", content="Default source")

        assert memory.source == MemorySource.CONVERSATION

    def test_save_memory_updates_project_timestamp(self, store):
        """Saving a memory bumps the parent project's updated_at."""
        _make_project(store)
        original = store.get_project("proj-1")
        assert original is not None

        time.sleep(0.01)
        store.save_memory(project_id="proj-1", content="Bump timestamp")
        refreshed = store.get_project("proj-1")
        assert refreshed is not None

        assert refreshed.updated_at >= original.updated_at

    def test_save_memory_invalid_depth_negative(self, store):
        """save_memory raises ValueError for depth < 0."""
        _make_project(store)

        with pytest.raises(ValueError):
            store.save_memory(project_id="proj-1", content="Bad depth", depth=-1)

    def test_save_memory_invalid_depth_too_high(self, store):
        """save_memory raises ValueError for depth > 3."""
        _make_project(store)

        with pytest.raises(ValueError):
            store.save_memory(project_id="proj-1", content="Bad depth", depth=4)

    def test_save_memory_valid_depths(self, store):
        """save_memory accepts all valid depths 0-3."""
        _make_project(store)

        for depth in range(4):
            memory = store.save_memory(
                project_id="proj-1",
                content=f"Depth {depth}",
                depth=depth,
            )
            assert memory.depth == depth


# ---------------------------------------------------------------------------
# Recall
# ---------------------------------------------------------------------------

class TestRecall:
    def test_recall_single_project(self, store):
        """Recall memories for a specific project returns only that project's memories."""
        store.create_project(id="proj-a", name="A")
        store.create_project(id="proj-b", name="B")
        store.save_memory(project_id="proj-a", content="Memory A")
        store.save_memory(project_id="proj-b", content="Memory B")

        result = store.recall(project_id="proj-a")

        assert "proj-a" in result
        assert "proj-b" not in result
        assert len(result["proj-a"]) == 1
        assert result["proj-a"][0].content == "Memory A"

    def test_recall_all_active(self, store):
        """Recall with no project_id returns memories from all active projects."""
        store.create_project(id="proj-a", name="A")
        store.create_project(id="proj-b", name="B")
        store.save_memory(project_id="proj-a", content="A mem")
        store.save_memory(project_id="proj-b", content="B mem")

        result = store.recall()

        assert "proj-a" in result
        assert "proj-b" in result

    def test_recall_excludes_paused(self, store):
        """Paused project memories are not included in a no-project recall."""
        store.create_project(id="proj-active", name="Active")
        store.create_project(id="proj-paused", name="Paused")
        store.update_project("proj-paused", status="paused")
        store.save_memory(project_id="proj-active", content="Active mem")
        store.save_memory(project_id="proj-paused", content="Paused mem")

        result = store.recall()

        assert "proj-active" in result
        assert "proj-paused" not in result

    def test_recall_depth_filter(self, store):
        """Only memories with depth <= requested depth are returned."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="Depth 0", depth=0)
        store.save_memory(project_id="proj-1", content="Depth 1", depth=1)
        store.save_memory(project_id="proj-1", content="Depth 2", depth=2)
        store.save_memory(project_id="proj-1", content="Depth 3", depth=3)

        result = store.recall(project_id="proj-1", depth=1)

        contents = [m.content for m in result.get("proj-1", [])]
        assert "Depth 0" in contents
        assert "Depth 1" in contents
        assert "Depth 2" not in contents
        assert "Depth 3" not in contents

    def test_recall_character_budget(self, store):
        """Memories are truncated when max_chars is exceeded."""
        _make_project(store)
        # Each memory is ~50 chars; budget forces truncation.
        for i in range(10):
            store.save_memory(project_id="proj-1", content="A" * 50, depth=1)

        result = store.recall(project_id="proj-1", depth=1, max_chars=100)

        # Should return at most 2 memories (100 / 50 = 2).
        memories = result.get("proj-1", [])
        assert len(memories) <= 2

    def test_recall_tag_filter(self, store):
        """Only memories with all requested tags are returned."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="Tagged", tags=["auth", "security"])
        store.save_memory(project_id="proj-1", content="Only auth", tags=["auth"])
        store.save_memory(project_id="proj-1", content="No tags")

        result = store.recall(project_id="proj-1", depth=3, tags=["auth", "security"])

        memories = result.get("proj-1", [])
        assert len(memories) == 1
        assert memories[0].content == "Tagged"

    def test_recall_excludes_superseded(self, store):
        """Superseded memories are not returned by recall."""
        _make_project(store)
        old = store.save_memory(project_id="proj-1", content="Old memory")
        new = store.save_memory(project_id="proj-1", content="New memory")
        store.supersede_memory(old.id, new.id)

        result = store.recall(project_id="proj-1", depth=3)

        memories = result.get("proj-1", [])
        contents = [m.content for m in memories]
        assert "Old memory" not in contents
        assert "New memory" in contents

    def test_recall_sort_order(self, store):
        """Memories are sorted depth ASC, updated_at DESC."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="D2 first", depth=2)
        store.save_memory(project_id="proj-1", content="D1 later", depth=1)
        store.save_memory(project_id="proj-1", content="D1 earliest", depth=1)

        result = store.recall(project_id="proj-1", depth=3, max_chars=99999)

        memories = result.get("proj-1", [])
        depths = [m.depth for m in memories]
        # All depth-1 memories should come before depth-2.
        d1_indices = [i for i, d in enumerate(depths) if d == 1]
        d2_indices = [i for i, d in enumerate(depths) if d == 2]
        assert max(d1_indices) < min(d2_indices)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_fts(self, store):
        """FTS5 search finds memories matching the query term."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="The quick brown fox")
        store.save_memory(project_id="proj-1", content="Completely unrelated content")

        results = store.search("fox")

        contents = [m.content for m in results]
        assert "The quick brown fox" in contents

    def test_search_no_results(self, store):
        """Search with a term that matches nothing returns an empty list."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="Hello world")

        results = store.search("xyzzy_no_match_123")

        assert results == []

    def test_search_excludes_superseded(self, store):
        """Superseded memories are not returned in search results."""
        _make_project(store)
        old = store.save_memory(project_id="proj-1", content="superseded delta memory")
        new = store.save_memory(project_id="proj-1", content="replacement delta memory")
        store.supersede_memory(old.id, new.id)

        results = store.search("delta")

        contents = [m.content for m in results]
        # Old superseded memory must not appear.
        for m in results:
            assert m.superseded_by is None
        assert any("replacement" in c for c in contents)

    def test_search_filter_by_project(self, store):
        """Search with a project filter only returns memories from that project."""
        store.create_project(id="proj-a", name="A")
        store.create_project(id="proj-b", name="B")
        store.save_memory(project_id="proj-a", content="alpha search term")
        store.save_memory(project_id="proj-b", content="alpha search term")

        results = store.search("alpha", project_id="proj-a")

        assert all(m.project_id == "proj-a" for m in results)
        assert len(results) == 1

    def test_search_filter_by_tag(self, store):
        """Search with a tag filter returns only memories with that tag."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="beta tagged memory", tags=["important"])
        store.save_memory(project_id="proj-1", content="beta untagged memory")

        results = store.search("beta", tags=["important"])

        assert len(results) == 1
        assert "important" in results[0].tags


# ---------------------------------------------------------------------------
# Delete / Supersede
# ---------------------------------------------------------------------------

class TestDeleteMemory:
    def test_delete_memory_soft(self, store):
        """delete_memory sets superseded_by to '_deleted'."""
        _make_project(store)
        memory = _save_memory(store)

        result = store.delete_memory(memory.id)

        assert result is True
        # Verify via recall: the deleted memory should not appear.
        recalled = store.recall(project_id="proj-1", depth=3)
        memories = recalled.get("proj-1", [])
        assert all(m.id != memory.id for m in memories)

    def test_delete_memory_not_found(self, store):
        """delete_memory returns False for a missing memory id."""
        result = store.delete_memory("nonexistent-id")

        assert result is False

    def test_delete_memory_already_deleted_is_idempotent(self, store):
        """delete_memory returns False if the memory is already deleted."""
        _make_project(store)
        memory = _save_memory(store)

        first = store.delete_memory(memory.id)
        second = store.delete_memory(memory.id)

        assert first is True
        assert second is False


class TestSupersedeMemory:
    def test_supersede_memory(self, store):
        """supersede_memory links old memory to new memory via superseded_by."""
        _make_project(store)
        old = _save_memory(store, content="Old version")
        new = _save_memory(store, content="New version")

        result = store.supersede_memory(old.id, new.id)

        assert result is True
        # Old memory should no longer appear in recall.
        recalled = store.recall(project_id="proj-1", depth=3)
        memories = recalled.get("proj-1", [])
        ids = [m.id for m in memories]
        assert old.id not in ids
        assert new.id in ids

    def test_supersede_memory_returns_false_for_missing(self, store):
        """supersede_memory returns False when old_id does not exist."""
        _make_project(store)
        new = _save_memory(store, content="New")

        result = store.supersede_memory("no-such-id", new.id)

        assert result is False

    def test_supersede_already_superseded_returns_false(self, store):
        """supersede_memory returns False if old memory is already superseded."""
        _make_project(store)
        a = _save_memory(store, content="A")
        b = _save_memory(store, content="B")
        c = _save_memory(store, content="C")

        store.supersede_memory(a.id, b.id)
        result = store.supersede_memory(a.id, c.id)

        assert result is False


# ---------------------------------------------------------------------------
# Schema / DB creation
# ---------------------------------------------------------------------------

class TestDbAutoCreation:
    def test_db_auto_creation(self, tmp_path):
        """MuninnStore creates the DB file and any missing parent directories."""
        nested = tmp_path / "a" / "b" / "c"
        db_path = str(nested / "test.db")

        # Directory does not yet exist.
        assert not nested.exists()

        store = MuninnStore(db_path=db_path)

        assert nested.exists()
        assert (nested / "test.db").exists()
        # Basic sanity: can create a project.
        store.create_project(id="p1", name="P1")
        assert store.get_project("p1") is not None


# ---------------------------------------------------------------------------
# Memory count on Project
# ---------------------------------------------------------------------------

class TestMemoryCountInProject:
    def test_memory_count_in_project(self, store):
        """Project.memory_count reflects non-superseded memory count."""
        _make_project(store)
        m1 = _save_memory(store, content="One")
        m2 = _save_memory(store, content="Two")
        _save_memory(store, content="Three")

        # Supersede one, delete another.
        store.supersede_memory(m1.id, m2.id)
        store.delete_memory(m2.id)

        project = store.get_project("proj-1")
        assert project is not None
        # Only "Three" is non-superseded.
        assert project.memory_count == 1

    def test_memory_count_zero_on_new_project(self, store):
        """A fresh project has memory_count == 0."""
        _make_project(store)
        project = store.get_project("proj-1")
        assert project is not None
        assert project.memory_count == 0

    def test_memory_count_in_list_projects(self, store):
        """list_projects includes the correct memory_count for each project."""
        _make_project(store)
        _save_memory(store, content="Mem 1")
        _save_memory(store, content="Mem 2")

        projects = store.list_projects()
        assert len(projects) == 1
        assert projects[0].memory_count == 2


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

def _worker_write(db_path: str, project_id: str, n: int, results: list) -> None:
    """Write *n* memories to the store; append True/error message to results."""
    try:
        s = MuninnStore(db_path=db_path)
        for i in range(n):
            s.save_memory(project_id=project_id, content=f"Worker {project_id} memory {i}")
        results.append(True)
    except Exception as exc:
        results.append(str(exc))


class TestConcurrentWrites:
    def test_concurrent_writes(self, tmp_path):
        """Two processes writing simultaneously do not crash (WAL mode)."""
        db_path = str(tmp_path / "concurrent.db")

        # Create the project before spawning workers.
        setup_store = MuninnStore(db_path=db_path)
        setup_store.create_project(id="shared-proj", name="Shared")

        manager = multiprocessing.Manager()
        results: list = manager.list()

        p1 = multiprocessing.Process(
            target=_worker_write,
            args=(db_path, "shared-proj", 10, results),
        )
        p2 = multiprocessing.Process(
            target=_worker_write,
            args=(db_path, "shared-proj", 10, results),
        )

        p1.start()
        p2.start()
        p1.join(timeout=30)
        p2.join(timeout=30)

        result_list = list(results)
        assert len(result_list) == 2, f"Expected 2 results, got: {result_list}"
        for r in result_list:
            assert r is True, f"Worker failed: {r}"

        # Both workers wrote 10 memories each = 20 total.
        final_store = MuninnStore(db_path=db_path)
        project = final_store.get_project("shared-proj")
        assert project is not None
        assert project.memory_count == 20
