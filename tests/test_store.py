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
    tags: list[str] | None = None,
) -> object:
    return store.save_memory(
        project_id=project_id,
        content=content,
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
            source=MemorySource.MANUAL,
        )

        assert memory.id is not None
        assert len(memory.id) == 32  # uuid4().hex is 32 hex chars
        assert memory.project_id == "proj-1"
        assert memory.content == "Important decision"
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

        result, stats = store.recall(project_id="proj-a")

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

        result, stats = store.recall()

        assert "proj-a" in result
        assert "proj-b" in result

    def test_recall_excludes_paused(self, store):
        """Paused project memories are not included in a no-project recall."""
        store.create_project(id="proj-active", name="Active")
        store.create_project(id="proj-paused", name="Paused")
        store.update_project("proj-paused", status="paused")
        store.save_memory(project_id="proj-active", content="Active mem")
        store.save_memory(project_id="proj-paused", content="Paused mem")

        result, stats = store.recall()

        assert "proj-active" in result
        assert "proj-paused" not in result

    def test_recall_character_budget(self, store):
        """Memories are truncated when max_chars is exceeded."""
        _make_project(store)
        # Each memory is ~50 chars; budget forces truncation.
        for i in range(10):
            store.save_memory(project_id="proj-1", content="A" * 50)

        result, stats = store.recall(project_id="proj-1", max_chars=100)

        # Should return at most 2 memories (100 / 50 = 2).
        memories = result.get("proj-1", [])
        assert len(memories) <= 2
        assert stats["memories_dropped"] > 0

    def test_recall_tag_filter(self, store):
        """Only memories with all requested tags are returned."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="Tagged", tags=["auth", "security"])
        store.save_memory(project_id="proj-1", content="Only auth", tags=["auth"])
        store.save_memory(project_id="proj-1", content="No tags")

        result, stats = store.recall(project_id="proj-1", tags=["auth", "security"])

        memories = result.get("proj-1", [])
        assert len(memories) == 1
        assert memories[0].content == "Tagged"

    def test_recall_excludes_superseded(self, store):
        """Superseded memories are not returned by recall."""
        _make_project(store)
        old = store.save_memory(project_id="proj-1", content="Old memory")
        new = store.save_memory(project_id="proj-1", content="New memory")
        store.supersede_memory(old.id, new.id)

        result, stats = store.recall(project_id="proj-1")

        memories = result.get("proj-1", [])
        contents = [m.content for m in memories]
        assert "Old memory" not in contents
        assert "New memory" in contents

    def test_recall_sort_order(self, store):
        """Memories are sorted by updated_at DESC."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="First saved")
        time.sleep(0.01)
        store.save_memory(project_id="proj-1", content="Second saved")
        time.sleep(0.01)
        store.save_memory(project_id="proj-1", content="Third saved")

        result, stats = store.recall(project_id="proj-1", max_chars=99999)

        memories = result.get("proj-1", [])
        # Newest first (updated_at DESC)
        assert memories[0].content == "Third saved"
        assert memories[1].content == "Second saved"
        assert memories[2].content == "First saved"


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
        recalled, _stats = store.recall(project_id="proj-1")
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


class TestUpdateMemory:
    def test_update_content(self, store):
        """update_memory changes content and updated_at."""
        _make_project(store)
        mem = _save_memory(store, content="Old content")
        updated = store.update_memory(mem.id, content="New content")
        assert updated is not None
        assert updated.content == "New content"
        assert updated.id == mem.id

    def test_update_tags(self, store):
        """update_memory replaces tags."""
        _make_project(store)
        mem = _save_memory(store, content="Tagged", tags=["old-tag"])
        updated = store.update_memory(mem.id, tags=["new-tag-a", "new-tag-b"])
        assert updated is not None
        assert sorted(updated.tags) == ["new-tag-a", "new-tag-b"]

    def test_update_not_found(self, store):
        """update_memory returns None for non-existent ID."""
        _make_project(store)
        result = store.update_memory("nonexistent", content="x")
        assert result is None

    def test_update_superseded_returns_none(self, store):
        """update_memory returns None for superseded memory."""
        _make_project(store)
        old = _save_memory(store, content="Old")
        new = _save_memory(store, content="New")
        store.supersede_memory(old.id, new.id)
        result = store.update_memory(old.id, content="Try update")
        assert result is None

    def test_update_content_updates_fts(self, store):
        """After updating content, FTS search finds new text."""
        _make_project(store)
        mem = _save_memory(store, content="alpha bravo")
        store.update_memory(mem.id, content="charlie delta")
        # Old content should not be found
        old_results = store.search("alpha")
        assert len(old_results) == 0
        # New content should be found
        new_results = store.search("charlie")
        assert len(new_results) == 1
        assert new_results[0].id == mem.id


class TestPrefixIdMatching:
    def test_delete_memory_with_prefix(self, store):
        """delete_memory accepts a unique prefix of the memory ID."""
        _make_project(store)
        mem = _save_memory(store, content="Delete me by prefix")
        prefix = mem.id[:8]

        result = store.delete_memory(prefix)

        assert result is True
        recalled, _ = store.recall(project_id="proj-1")
        memories = recalled.get("proj-1", [])
        assert all(m.id != mem.id for m in memories)

    def test_update_memory_with_prefix(self, store):
        """update_memory accepts a unique prefix of the memory ID."""
        _make_project(store)
        mem = _save_memory(store, content="Update me by prefix")
        prefix = mem.id[:8]

        updated = store.update_memory(prefix, content="Updated via prefix")

        assert updated is not None
        assert updated.content == "Updated via prefix"
        assert updated.id == mem.id

    def test_prefix_returns_none_for_no_match(self, store):
        """Prefix that matches nothing returns None/False."""
        _make_project(store)
        _save_memory(store, content="Some content")

        assert store.delete_memory("zzzzzzzz") is False
        assert store.update_memory("zzzzzzzz", content="x") is None

    def test_full_id_still_works(self, store):
        """Full UUID still works for delete and update."""
        _make_project(store)
        mem = _save_memory(store, content="Full ID test")

        updated = store.update_memory(mem.id, content="Updated with full ID")
        assert updated is not None
        assert updated.content == "Updated with full ID"


class TestSupersedeMemory:
    def test_supersede_memory(self, store):
        """supersede_memory links old memory to new memory via superseded_by."""
        _make_project(store)
        old = _save_memory(store, content="Old version")
        new = _save_memory(store, content="New version")

        result = store.supersede_memory(old.id, new.id)

        assert result is True
        # Old memory should no longer appear in recall.
        recalled, _stats = store.recall(project_id="proj-1")
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
    import time
    try:
        s = MuninnStore(db_path=db_path)
        for i in range(n):
            for attempt in range(5):
                try:
                    s.save_memory(project_id=project_id, content=f"Worker {project_id} memory {i}")
                    break
                except Exception as e:
                    if "locked" in str(e) and attempt < 4:
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    raise
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


# ---------------------------------------------------------------------------
# Edge cases: Content validation
# ---------------------------------------------------------------------------

class TestContentValidation:
    def test_save_empty_content_raises(self, store):
        """save_memory raises ValueError for empty content."""
        _make_project(store)
        with pytest.raises(ValueError, match="empty"):
            store.save_memory(project_id="proj-1", content="")

    def test_save_whitespace_only_content_raises(self, store):
        """save_memory raises ValueError for whitespace-only content."""
        _make_project(store)
        with pytest.raises(ValueError, match="empty"):
            store.save_memory(project_id="proj-1", content="   \n\t  ")

    def test_update_memory_empty_content_raises(self, store):
        """update_memory raises ValueError for empty content."""
        _make_project(store)
        mem = _save_memory(store, content="Valid content")
        with pytest.raises(ValueError, match="empty"):
            store.update_memory(mem.id, content="")

    def test_update_memory_whitespace_content_raises(self, store):
        """update_memory raises ValueError for whitespace-only content."""
        _make_project(store)
        mem = _save_memory(store, content="Valid content")
        with pytest.raises(ValueError, match="empty"):
            store.update_memory(mem.id, content="   ")


# ---------------------------------------------------------------------------
# Edge cases: Tag validation
# ---------------------------------------------------------------------------

class TestTagValidation:
    def test_save_memory_empty_tag_raises(self, store):
        """save_memory with an empty-string tag raises ValueError."""
        _make_project(store)
        with pytest.raises(ValueError, match="non-empty"):
            store.save_memory(project_id="proj-1", content="Tagged", tags=[""])

    def test_save_memory_whitespace_tag_raises(self, store):
        """save_memory with a whitespace-only tag raises ValueError."""
        _make_project(store)
        with pytest.raises(ValueError, match="non-empty"):
            store.save_memory(project_id="proj-1", content="Tagged", tags=["   "])

    def test_memory_tags_are_tuples(self, store):
        """Memory.tags should be a tuple, not a list."""
        _make_project(store)
        mem = store.save_memory(project_id="proj-1", content="Tuple tags", tags=["a", "b"])
        assert isinstance(mem.tags, tuple)

    def test_recalled_memory_tags_are_tuples(self, store):
        """Tags returned from recall are tuples."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="Recall tuple", tags=["x"])
        result, _ = store.recall(project_id="proj-1")
        for mems in result.values():
            for mem in mems:
                assert isinstance(mem.tags, tuple)


# ---------------------------------------------------------------------------
# Edge cases: Duplicate project ID
# ---------------------------------------------------------------------------

class TestDuplicateProject:
    def test_create_duplicate_project_raises(self, store):
        """Creating a project with an existing ID raises an error."""
        store.create_project(id="dup-proj", name="First")
        with pytest.raises(Exception):
            store.create_project(id="dup-proj", name="Second")


# ---------------------------------------------------------------------------
# Edge cases: Unicode content
# ---------------------------------------------------------------------------

class TestUnicodeSupport:
    def test_save_and_recall_korean(self, store):
        """Korean text is saved and recalled correctly."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="한국어 메모리 테스트")
        result, _ = store.recall(project_id="proj-1")
        memories = result.get("proj-1", [])
        assert any("한국어" in m.content for m in memories)

    def test_save_and_recall_emoji(self, store):
        """Emoji content is saved and recalled correctly."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="🚀 Launch day! 🎉")
        result, _ = store.recall(project_id="proj-1")
        memories = result.get("proj-1", [])
        assert any("🚀" in m.content for m in memories)

    def test_search_korean(self, store):
        """FTS search works with Korean text."""
        _make_project(store)
        store.save_memory(project_id="proj-1", content="음성 저널링 앱 개발")
        results = store.search("저널링")
        assert len(results) >= 1

    def test_unicode_tags(self, store):
        """Unicode characters work in tags."""
        _make_project(store)
        mem = store.save_memory(project_id="proj-1", content="Unicode tagged", tags=["개발", "テスト"])
        assert "개발" in mem.tags
        assert "テスト" in mem.tags


# ---------------------------------------------------------------------------
# Edge cases: Search LIMIT
# ---------------------------------------------------------------------------

class TestSearchLimit:
    def test_search_respects_limit(self, store):
        """search() returns at most `limit` results."""
        _make_project(store)
        for i in range(20):
            store.save_memory(project_id="proj-1", content=f"searchable item number {i}")

        results = store.search("searchable", limit=5)
        assert len(results) <= 5

    def test_search_default_limit_is_50(self, store):
        """search() default limit allows up to 50 results."""
        _make_project(store)
        for i in range(60):
            store.save_memory(project_id="proj-1", content=f"findme entry {i}")

        results = store.search("findme")
        assert len(results) <= 50


# ---------------------------------------------------------------------------
# Edge cases: LIKE wildcard escaping in prefix matching
# ---------------------------------------------------------------------------

class TestLikeWildcardEscaping:
    def test_percent_in_prefix_does_not_match_all(self, store):
        """A memory_id containing '%' should not match everything."""
        _make_project(store)
        _save_memory(store, content="Should not be found")
        # '%' as prefix should match nothing (no ID starts with literal %)
        result = store.delete_memory("%")
        assert result is False

    def test_underscore_in_prefix_does_not_wildcard(self, store):
        """A memory_id containing '_' should not act as single-char wildcard."""
        _make_project(store)
        _save_memory(store, content="Not a wildcard match")
        result = store.delete_memory("_")
        assert result is False


# ---------------------------------------------------------------------------
# Edge cases: Recall on non-existent project
# ---------------------------------------------------------------------------

class TestRecallNonExistentProject:
    def test_recall_nonexistent_project_returns_empty(self, store):
        """Recall with a non-existent project_id returns empty dict."""
        result, stats = store.recall(project_id="no-such-project")
        assert result == {}
        assert stats["memories_loaded"] == 0

    def test_recall_nonexistent_project_stats_zeroed(self, store):
        """Stats are all zero for a non-existent project recall."""
        _, stats = store.recall(project_id="no-such-project")
        assert stats["chars_loaded"] == 0
        assert stats["memories_dropped"] == 0


# ---------------------------------------------------------------------------
# Edge cases: Unknown kwargs in update_project
# ---------------------------------------------------------------------------

class TestUpdateProjectUnknownKwargs:
    def test_unknown_kwargs_raises_valueerror(self, store):
        """update_project with unknown field names raises ValueError."""
        store.create_project(id="kwargs-test", name="KW Test")
        with pytest.raises(ValueError, match="Unknown"):
            store.update_project("kwargs-test", nonexistent_field="value")

    def test_typo_field_raises_valueerror(self, store):
        """update_project with a typo'd field name raises ValueError."""
        store.create_project(id="typo-test", name="Typo Test")
        with pytest.raises(ValueError, match="Unknown"):
            store.update_project("typo-test", summry="oops")


# ---------------------------------------------------------------------------
# search_projects — keyword search on project summaries
# ---------------------------------------------------------------------------

class TestSearchProjects:
    def test_search_finds_matching_project(self, store):
        """search_projects returns projects whose summary matches the query."""
        store.create_project(id="sp-1", name="SP1")
        store.update_project("sp-1", summary="This project uses React and TypeScript")

        results = store.search_projects("React")

        assert len(results) == 1
        assert results[0].id == "sp-1"

    def test_search_case_insensitive(self, store):
        """search_projects is case-insensitive."""
        store.create_project(id="sp-ci", name="CI")
        store.update_project("sp-ci", summary="Using POSTGRESQL for data storage")

        results = store.search_projects("postgresql")

        assert len(results) == 1
        assert results[0].id == "sp-ci"

    def test_search_excludes_null_summaries(self, store):
        """search_projects does not return projects with null summaries."""
        store.create_project(id="sp-null", name="Null")
        # no summary set

        results = store.search_projects("Null")

        assert len(results) == 0

    def test_search_no_matches(self, store):
        """search_projects returns empty list when no matches."""
        store.create_project(id="sp-none", name="None")
        store.update_project("sp-none", summary="A simple todo app")

        results = store.search_projects("xyzzy_no_match")

        assert results == []

    def test_search_multiple_matches(self, store):
        """search_projects returns multiple matching projects."""
        store.create_project(id="sp-a", name="A")
        store.create_project(id="sp-b", name="B")
        store.update_project("sp-a", summary="Building a dashboard with charts")
        store.update_project("sp-b", summary="Dashboard analytics tool")

        results = store.search_projects("dashboard")

        assert len(results) == 2

    def test_search_respects_limit(self, store):
        """search_projects respects the limit parameter."""
        for i in range(5):
            store.create_project(id=f"sp-lim-{i}", name=f"Lim{i}")
            store.update_project(f"sp-lim-{i}", summary=f"Project about widgets number {i}")

        results = store.search_projects("widgets", limit=2)

        assert len(results) <= 2


# ---------------------------------------------------------------------------
# reset_data — wipe memories, tags, revisions, clear summaries
# ---------------------------------------------------------------------------

class TestResetData:
    def test_reset_clears_memories(self, store):
        """reset_data removes all memories."""
        store.create_project(id="reset-p", name="Reset")
        store.save_memory(project_id="reset-p", content="Memory 1")
        store.save_memory(project_id="reset-p", content="Memory 2")

        store.reset_data()

        project = store.get_project("reset-p")
        assert project is not None
        assert project.memory_count == 0

    def test_reset_clears_summaries(self, store):
        """reset_data sets all project summaries to NULL."""
        store.create_project(id="reset-s", name="Reset Summary")
        store.update_project("reset-s", summary="Some document")

        store.reset_data()

        project = store.get_project("reset-s")
        assert project is not None
        assert project.summary is None

    def test_reset_preserves_projects(self, store):
        """reset_data does not delete projects themselves."""
        store.create_project(id="reset-keep", name="Keep Me")

        store.reset_data()

        project = store.get_project("reset-keep")
        assert project is not None
        assert project.id == "reset-keep"

    def test_reset_clears_revisions(self, store):
        """reset_data removes all summary revisions."""
        store.create_project(id="reset-rev", name="Rev")
        store.update_project("reset-rev", summary="V1")
        store.update_project("reset-rev", summary="V2")

        store.reset_data()

        # After reset, saving a new summary should work without issues
        store.update_project("reset-rev", summary="Fresh start")
        project = store.get_project("reset-rev")
        assert project is not None
        assert project.summary == "Fresh start"
