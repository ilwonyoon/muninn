"""Tests for memory hierarchy (parent_memory_id, title, resolved)."""

import pytest
from muninn.store import MuninnStore
from muninn.models import validate_parent_depth


class TestValidateParentDepth:
    """Tests for the validate_parent_depth validator."""

    def test_valid_parent_child(self):
        """Parent depth 0 < child depth 1 should pass."""
        validate_parent_depth(0, 1)  # should not raise

    def test_valid_l1_to_l2(self):
        validate_parent_depth(1, 2)

    def test_valid_l1_to_l3(self):
        validate_parent_depth(1, 3)

    def test_valid_l2_to_l3(self):
        validate_parent_depth(2, 3)

    def test_invalid_same_depth(self):
        with pytest.raises(ValueError, match="strictly less than"):
            validate_parent_depth(1, 1)

    def test_invalid_parent_deeper(self):
        with pytest.raises(ValueError, match="strictly less than"):
            validate_parent_depth(2, 1)


class TestSaveMemoryWithParent:
    """Tests for save_memory with parent_memory_id."""

    def test_save_with_parent(self, store: MuninnStore):
        """Save L1, then L2 under it."""
        proj = store.create_project(id="test-proj", name="Test")
        l1 = store.save_memory(proj.id, "Topic heading", depth=1, title="Auth system")
        l2 = store.save_memory(
            proj.id, "Detail content", depth=2,
            parent_memory_id=l1.id, title="OAuth removed"
        )
        assert l2.parent_memory_id == l1.id
        assert l2.title == "OAuth removed"
        assert l2.depth == 2

    def test_save_with_invalid_parent(self, store: MuninnStore):
        """Parent that doesn't exist should raise."""
        proj = store.create_project(id="test-proj", name="Test")
        with pytest.raises(ValueError, match="not found"):
            store.save_memory(
                proj.id, "Content", depth=2,
                parent_memory_id="nonexistent"
            )

    def test_save_with_depth_violation(self, store: MuninnStore):
        """L1 parent -> L1 child should fail (same depth)."""
        proj = store.create_project(id="test-proj", name="Test")
        l1 = store.save_memory(proj.id, "Topic", depth=1)
        with pytest.raises(ValueError, match="strictly less than"):
            store.save_memory(
                proj.id, "Content", depth=1,
                parent_memory_id=l1.id
            )

    def test_save_with_reverse_depth(self, store: MuninnStore):
        """L2 parent -> L1 child should fail."""
        proj = store.create_project(id="test-proj", name="Test")
        l2 = store.save_memory(proj.id, "Deep content", depth=2)
        with pytest.raises(ValueError, match="strictly less than"):
            store.save_memory(
                proj.id, "Content", depth=1,
                parent_memory_id=l2.id
            )

    def test_save_with_superseded_parent(self, store: MuninnStore):
        """Superseded parent should fail."""
        proj = store.create_project(id="test-proj", name="Test")
        l1 = store.save_memory(proj.id, "Topic", depth=1)
        store.delete_memory(l1.id)  # soft-delete sets superseded_by='_deleted'
        with pytest.raises(ValueError, match="superseded"):
            store.save_memory(
                proj.id, "Content", depth=2,
                parent_memory_id=l1.id
            )

    def test_l3_under_l1(self, store: MuninnStore):
        """L3 can have L1 as parent."""
        proj = store.create_project(id="test-proj", name="Test")
        l1 = store.save_memory(proj.id, "Topic", depth=1)
        l3 = store.save_memory(
            proj.id, "Archived data", depth=3,
            parent_memory_id=l1.id
        )
        assert l3.parent_memory_id == l1.id

    def test_l3_under_l2(self, store: MuninnStore):
        """L3 can have L2 as parent."""
        proj = store.create_project(id="test-proj", name="Test")
        l1 = store.save_memory(proj.id, "Topic", depth=1)
        l2 = store.save_memory(
            proj.id, "Working", depth=2,
            parent_memory_id=l1.id
        )
        l3 = store.save_memory(
            proj.id, "Archive", depth=3,
            parent_memory_id=l2.id
        )
        assert l3.parent_memory_id == l2.id


class TestTitleField:
    """Tests for the title field."""

    def test_save_with_title(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Body content", title="My Title")
        assert mem.title == "My Title"

    def test_save_without_title(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Body content")
        assert mem.title is None

    def test_update_title(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Content", title="Old Title")
        updated = store.update_memory(mem.id, title="New Title")
        assert updated is not None
        assert updated.title == "New Title"

    def test_get_memory_has_title(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Content", title="Persisted Title")
        fetched = store.get_memory(mem.id)
        assert fetched is not None
        assert fetched.title == "Persisted Title"


class TestResolvedFlag:
    """Tests for the resolved field."""

    def test_default_not_resolved(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Content")
        assert mem.resolved is False

    def test_update_resolved(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Bug report")
        updated = store.update_memory(mem.id, resolved=True)
        assert updated is not None
        assert updated.resolved is True

    def test_unresolved(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Bug report")
        store.update_memory(mem.id, resolved=True)
        updated = store.update_memory(mem.id, resolved=False)
        assert updated is not None
        assert updated.resolved is False


class TestRecallDrillDown:
    """Tests for recall with parent_id filter."""

    def test_recall_with_parent_id(self, store: MuninnStore):
        """Recall with parent_id should only return children of that parent."""
        proj = store.create_project(id="test-proj", name="Test")
        l1a = store.save_memory(proj.id, "Topic A", depth=1, title="Topic A")
        l1b = store.save_memory(proj.id, "Topic B", depth=1, title="Topic B")
        l2a = store.save_memory(
            proj.id, "Under A", depth=2,
            parent_memory_id=l1a.id, title="Detail A"
        )
        l2b = store.save_memory(
            proj.id, "Under B", depth=2,
            parent_memory_id=l1b.id, title="Detail B"
        )

        memories_map, stats = store.recall(project_id=proj.id, parent_id=l1a.id)
        memories = memories_map.get(proj.id, [])
        ids = [m.id for m in memories]
        assert l2a.id in ids
        assert l2b.id not in ids

    def test_recall_without_parent_loads_all(self, store: MuninnStore):
        """Normal recall without parent_id loads all depths."""
        proj = store.create_project(id="test-proj", name="Test")
        l0 = store.save_memory(proj.id, "Identity", depth=0)
        l1 = store.save_memory(proj.id, "Topic", depth=1)
        l2 = store.save_memory(
            proj.id, "Detail", depth=2,
            parent_memory_id=l1.id
        )

        memories_map, _ = store.recall(project_id=proj.id, depth=2)
        memories = memories_map.get(proj.id, [])
        ids = [m.id for m in memories]
        assert l0.id in ids
        assert l1.id in ids
        assert l2.id in ids


class TestDefaultDepth:
    """Tests that the default depth is now 2."""

    def test_save_default_depth(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        mem = store.save_memory(proj.id, "Content without explicit depth")
        assert mem.depth == 2

    def test_recall_default_depth(self, store: MuninnStore):
        """Default recall depth=2 should include L0, L1, L2 but not L3."""
        proj = store.create_project(id="test-proj", name="Test")
        l0 = store.save_memory(proj.id, "Identity", depth=0)
        l1 = store.save_memory(proj.id, "Topic", depth=1)
        l2 = store.save_memory(proj.id, "Working", depth=2)
        l3 = store.save_memory(proj.id, "Archive", depth=3)

        memories_map, _ = store.recall(project_id=proj.id)  # default depth=2
        memories = memories_map.get(proj.id, [])
        ids = [m.id for m in memories]
        assert l0.id in ids
        assert l1.id in ids
        assert l2.id in ids
        assert l3.id not in ids


class TestMemoryTree:
    """Tests for get_memory_tree."""

    def test_tree_structure(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        l0 = store.save_memory(proj.id, "Identity", depth=0, title="Project ID")
        l1 = store.save_memory(proj.id, "Topic", depth=1, title="Auth")
        l2 = store.save_memory(
            proj.id, "Detail", depth=2,
            parent_memory_id=l1.id, title="OAuth removed"
        )

        tree = store.get_memory_tree(proj.id)
        root_ids = [m.id for m in tree["roots"]]
        assert l0.id in root_ids
        assert l1.id in root_ids  # L1 has no parent, so it's a root
        assert l2.id not in root_ids  # L2 has parent, not a root

        children = tree["children"].get(l1.id, [])
        child_ids = [m.id for m in children]
        assert l2.id in child_ids

        assert len(tree["edges"]) == 1
        assert tree["edges"][0]["source"] == l1.id
        assert tree["edges"][0]["target"] == l2.id

    def test_tree_empty_project(self, store: MuninnStore):
        proj = store.create_project(id="test-proj", name="Test")
        tree = store.get_memory_tree(proj.id)
        assert tree["roots"] == []
        assert tree["children"] == {}
        assert tree["edges"] == []
