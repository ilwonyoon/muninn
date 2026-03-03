"""Unit tests for MCP tool functions in muninn.tools."""

from __future__ import annotations

import json
import os

import pytest

import muninn.tools as tools_module
from muninn.tools import (
    _get_store,
    init_store,
    muninn_manage,
    muninn_recall,
    muninn_save,
    muninn_search,
    muninn_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the module-level _store to None before and after each test."""
    tools_module._store = None
    yield
    tools_module._store = None


@pytest.fixture
def initialized_store(store):
    """Return a MuninnStore that has been registered with init_store()."""
    init_store(store)
    return store


# ---------------------------------------------------------------------------
# _get_store — error when not initialized
# ---------------------------------------------------------------------------


class TestGetStore:
    def test_raises_when_not_initialized(self):
        """_get_store raises RuntimeError before init_store is called."""
        # reset_store autouse fixture ensures _store is None here
        with pytest.raises(RuntimeError, match="not initialized"):
            _get_store()

    def test_returns_store_after_init(self, initialized_store):
        """_get_store returns the store after init_store has been called."""
        result = _get_store()
        assert result is initialized_store


# ---------------------------------------------------------------------------
# muninn_save
# ---------------------------------------------------------------------------


class TestMuninnSave:
    def test_save_to_existing_project(self, initialized_store):
        """Save to an existing project returns confirmation with checkmark."""
        initialized_store.create_project(id="myproject", name="My Project")
        result = muninn_save(project="myproject", content="Decision made")
        assert "✅" in result

    def test_save_auto_creates_project(self, initialized_store):
        """Save to a non-existing project auto-creates it and returns confirmation."""
        result = muninn_save(project="newproject", content="Some content")
        assert "✅" in result
        # Project was actually created
        project = initialized_store.get_project("newproject")
        assert project is not None

    def test_save_with_tags_shows_tags(self, initialized_store):
        """Save with tags — tags appear in the confirmation output."""
        initialized_store.create_project(id="tagged-proj", name="Tagged")
        result = muninn_save(
            project="tagged-proj",
            content="Tagged memory",
            tags=["backend", "auth"],
        )
        assert "backend" in result or "auth" in result



# ---------------------------------------------------------------------------
# muninn_recall
# ---------------------------------------------------------------------------


class TestMuninnRecall:
    def test_recall_no_memories_returns_not_found(self, initialized_store):
        """Recall with no memories stored returns 'No memories found.'"""
        result = muninn_recall()
        assert "No memories found." in result

    def test_recall_specific_project(self, initialized_store):
        """Recall a specific project returns its header and memories."""
        initialized_store.create_project(id="alpha", name="Alpha")
        initialized_store.save_memory(project_id="alpha", content="Alpha decision")

        result = muninn_recall(project="alpha")

        assert "alpha" in result
        assert "Alpha decision" in result

    def test_recall_shows_memory_ids(self, initialized_store):
        """Recall output includes short memory IDs for use with delete/update."""
        initialized_store.create_project(id="idtest", name="ID Test")
        mem = initialized_store.save_memory(project_id="idtest", content="ID visible memory")

        result = muninn_recall(project="idtest")

        short_id = mem.id[:8]
        assert short_id in result

    def test_recall_all_active_projects(self, initialized_store):
        """Recall with project=None returns memories from all active projects."""
        initialized_store.create_project(id="proj-a", name="A")
        initialized_store.create_project(id="proj-b", name="B")
        initialized_store.save_memory(project_id="proj-a", content="Memory A")
        initialized_store.save_memory(project_id="proj-b", content="Memory B")

        result = muninn_recall(project=None)

        assert "proj-a" in result
        assert "proj-b" in result


# ---------------------------------------------------------------------------
# muninn_search
# ---------------------------------------------------------------------------


class TestMuninnSearch:
    def test_search_no_results(self, initialized_store):
        """Search that matches nothing returns 'No results found.'"""
        initialized_store.create_project(id="s-proj", name="Search Proj")
        initialized_store.save_memory(project_id="s-proj", content="Hello world")

        result = muninn_search(query="xyzzy_nomatch_zork")

        assert "No results found." in result

    def test_search_with_results(self, initialized_store):
        """Search that matches returns formatted results including the query."""
        initialized_store.create_project(id="s-proj", name="Search Proj")
        initialized_store.save_memory(project_id="s-proj", content="The quick brown fox")

        result = muninn_search(query="fox")

        assert "fox" in result
        assert "quick brown fox" in result

    def test_search_filtered_by_project(self, initialized_store):
        """Search filtered by project only returns that project's memories."""
        initialized_store.create_project(id="pa", name="PA")
        initialized_store.create_project(id="pb", name="PB")
        initialized_store.save_memory(project_id="pa", content="orange sunset")
        initialized_store.save_memory(project_id="pb", content="orange sunrise")

        result = muninn_search(query="orange", project="pa")

        assert "pa" in result
        assert "pb" not in result

    def test_search_filtered_by_tags(self, initialized_store):
        """Search filtered by tags only returns tagged memories."""
        initialized_store.create_project(id="tag-proj", name="Tag Proj")
        initialized_store.save_memory(
            project_id="tag-proj",
            content="critical event alpha",
            tags=["critical"],
        )
        initialized_store.save_memory(
            project_id="tag-proj",
            content="normal event alpha",
        )

        result = muninn_search(query="alpha", tags=["critical"])

        assert "critical event alpha" in result
        assert "normal event alpha" not in result


# ---------------------------------------------------------------------------
# muninn_status
# ---------------------------------------------------------------------------


class TestMuninnStatus:
    def test_status_no_projects(self, initialized_store):
        """Status with no projects returns 'No projects found.'"""
        result = muninn_status()
        assert "No projects found." in result

    def test_status_multiple_projects(self, initialized_store):
        """Status with multiple projects returns a table with all project ids."""
        initialized_store.create_project(id="alpha-p", name="Alpha")
        initialized_store.create_project(id="beta-p", name="Beta")
        initialized_store.create_project(id="gamma-p", name="Gamma")

        result = muninn_status()

        assert "alpha-p" in result
        assert "beta-p" in result
        assert "gamma-p" in result


# ---------------------------------------------------------------------------
# muninn_manage
# ---------------------------------------------------------------------------


class TestMuninnManageSetStatus:
    def test_set_status_valid(self, initialized_store):
        """set_status with a valid status returns 'Status updated'."""
        initialized_store.create_project(id="mp", name="Managed")

        result = muninn_manage(action="set_status", project="mp", status="paused")

        assert "Status updated" in result

    def test_set_status_missing_status_param(self, initialized_store):
        """set_status without status param returns an error message."""
        initialized_store.create_project(id="mp2", name="Managed2")

        result = muninn_manage(action="set_status", project="mp2")

        assert "Error" in result
        assert "status" in result.lower()

    def test_set_status_invalid_status(self, initialized_store):
        """set_status with an invalid status value returns an error message."""
        initialized_store.create_project(id="mp3", name="Managed3")

        result = muninn_manage(action="set_status", project="mp3", status="flying")

        assert "Error" in result


class TestMuninnManageDeleteMemory:
    def test_delete_memory_valid(self, initialized_store):
        """delete_memory with a valid id returns 'Memory deleted'."""
        initialized_store.create_project(id="dm-proj", name="DM")
        memory = initialized_store.save_memory(project_id="dm-proj", content="To delete")

        result = muninn_manage(
            action="delete_memory",
            project="dm-proj",
            memory_id=memory.id,
        )

        assert "Memory deleted" in result

    def test_delete_memory_missing_id(self, initialized_store):
        """delete_memory without memory_id returns an error message."""
        initialized_store.create_project(id="dm-proj2", name="DM2")

        result = muninn_manage(action="delete_memory", project="dm-proj2")

        assert "Error" in result
        assert "memory_id" in result.lower()

    def test_delete_memory_nonexistent_id(self, initialized_store):
        """delete_memory with a non-existent id returns an error message."""
        initialized_store.create_project(id="dm-proj3", name="DM3")

        result = muninn_manage(
            action="delete_memory",
            project="dm-proj3",
            memory_id="does-not-exist",
        )

        assert "Error" in result


class TestMuninnManageUpdateMemory:
    def test_update_memory_content(self, initialized_store):
        """update_memory with content returns 'Memory updated'."""
        initialized_store.create_project(id="um-proj", name="UM")
        memory = initialized_store.save_memory(project_id="um-proj", content="Old text")
        result = muninn_manage(
            action="update_memory",
            project="um-proj",
            memory_id=memory.id,
            field="content",
            value="New text",
        )
        assert "Memory updated" in result

    def test_update_memory_missing_id(self, initialized_store):
        """update_memory without memory_id returns error."""
        initialized_store.create_project(id="um-proj2", name="UM2")
        result = muninn_manage(action="update_memory", project="um-proj2", value="x")
        assert "Error" in result
        assert "memory_id" in result.lower()

    def test_update_memory_nonexistent(self, initialized_store):
        """update_memory with non-existent id returns error."""
        initialized_store.create_project(id="um-proj3", name="UM3")
        result = muninn_manage(
            action="update_memory",
            project="um-proj3",
            memory_id="does-not-exist",
            value="New content",
        )
        assert "Error" in result


class TestMuninnManageUpdateProject:
    def test_update_project_valid_field(self, initialized_store):
        """update_project with a valid field returns 'Project updated'."""
        initialized_store.create_project(id="up-proj", name="Original")

        result = muninn_manage(
            action="update_project",
            project="up-proj",
            field="name",
            value="Updated Name",
        )

        assert "Project updated" in result

    def test_update_project_invalid_field(self, initialized_store):
        """update_project with an invalid field returns an error message."""
        initialized_store.create_project(id="up-proj2", name="Original2")

        result = muninn_manage(
            action="update_project",
            project="up-proj2",
            field="nonexistent_field",
            value="some value",
        )

        assert "Error" in result


class TestMuninnManageCreateProject:
    def test_create_project(self, initialized_store):
        """create_project action returns 'Project created'."""
        result = muninn_manage(
            action="create_project",
            project="brand-new",
            value="Brand New Project",
        )

        assert "Project created" in result
        project = initialized_store.get_project("brand-new")
        assert project is not None


class TestMuninnManageUnknownAction:
    def test_unknown_action_returns_error(self, initialized_store):
        """Unknown action returns an error message."""
        result = muninn_manage(action="teleport", project="any-proj")

        assert "Error" in result
        assert "teleport" in result


# ---------------------------------------------------------------------------
# Edge cases: Content validation via tools
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Save confirmation hints
# ---------------------------------------------------------------------------


class TestSaveConfirmationHints:
    def test_hint_when_summary_empty(self, initialized_store):
        """Save to a project with no summary includes ⚠️ hint with call example."""
        initialized_store.create_project(id="no-summary", name="No Summary")
        result = muninn_save(project="no-summary", content="First memory")
        assert "IMMEDIATE ACTION REQUIRED" in result
        assert "one-pager" in result
        assert "muninn_recall" in result
        assert 'muninn_manage(action="update_project"' in result

    def test_no_hint_when_summary_present(self, initialized_store):
        """Save to a project with a summary does not include ⚠️ hint."""
        initialized_store.create_project(id="has-summary", name="Has Summary")
        initialized_store.update_project("has-summary", summary="A cool project.")
        result = muninn_save(project="has-summary", content="Second memory")
        assert "⚠️" not in result

    def test_reminder_at_five_memories(self, initialized_store):
        """Save that brings memory_count to a multiple of 5 shows 💡 reminder."""
        initialized_store.create_project(id="five-proj", name="Five")
        initialized_store.update_project("five-proj", summary="Existing summary.")
        for i in range(4):
            initialized_store.save_memory(project_id="five-proj", content=f"mem {i}")
        # 5th memory via tool
        result = muninn_save(project="five-proj", content="fifth memory")
        assert "💡" in result
        assert "5 memories accumulated" in result
        assert "one-pager may be outdated" in result

    def test_no_reminder_at_non_multiple_of_five(self, initialized_store):
        """Save that brings memory_count to 3 (not multiple of 5) has no 💡."""
        initialized_store.create_project(id="three-proj", name="Three")
        initialized_store.update_project("three-proj", summary="Has summary.")
        for i in range(2):
            initialized_store.save_memory(project_id="three-proj", content=f"mem {i}")
        result = muninn_save(project="three-proj", content="third memory")
        assert "💡" not in result
        assert "⚠️" not in result


class TestSaveContentValidation:
    def test_save_empty_content_returns_error(self, initialized_store):
        """Saving empty content via muninn_save returns an error message."""
        result = muninn_save(project="val-proj", content="")
        assert "Error" in result

    def test_save_whitespace_content_returns_error(self, initialized_store):
        """Saving whitespace-only content via muninn_save returns error."""
        result = muninn_save(project="val-proj", content="   \n  ")
        assert "Error" in result


# ---------------------------------------------------------------------------
# Edge cases: Search limit via tools
# ---------------------------------------------------------------------------


class TestSearchLimit:
    def test_search_with_custom_limit(self, initialized_store):
        """muninn_search respects the limit parameter."""
        initialized_store.create_project(id="lim-proj", name="Limit")
        for i in range(20):
            initialized_store.save_memory(
                project_id="lim-proj", content=f"limitquery item {i}"
            )

        result = muninn_search(query="limitquery", limit=3)
        # The result should contain "3 results found" or fewer
        assert "3 result" in result or "2 result" in result or "1 result" in result


# ---------------------------------------------------------------------------
# Edge cases: Update memory via manage with empty content
# ---------------------------------------------------------------------------


class TestManageUpdateMemoryValidation:
    def test_update_memory_empty_content_returns_error(self, initialized_store):
        """update_memory with empty content via muninn_manage returns error."""
        initialized_store.create_project(id="um-val", name="UM Val")
        mem = initialized_store.save_memory(project_id="um-val", content="Original")
        result = muninn_manage(
            action="update_memory",
            project="um-val",
            memory_id=mem.id,
            field="content",
            value="",
        )
        assert "Error" in result

    def test_update_memory_whitespace_content_returns_error(self, initialized_store):
        """update_memory with whitespace content returns error."""
        initialized_store.create_project(id="um-val2", name="UM Val2")
        mem = initialized_store.save_memory(project_id="um-val2", content="Original")
        result = muninn_manage(
            action="update_memory",
            project="um-val2",
            memory_id=mem.id,
            field="content",
            value="   ",
        )
        assert "Error" in result


# ---------------------------------------------------------------------------
# Edge cases: Duplicate project via manage
# ---------------------------------------------------------------------------


class TestManageCreateDuplicateProject:
    def test_create_duplicate_project_returns_error(self, initialized_store):
        """create_project with existing ID returns error, not crash."""
        initialized_store.create_project(id="dup-proj", name="First")
        result = muninn_manage(
            action="create_project",
            project="dup-proj",
            value="Second",
        )
        assert "Error" in result
        assert "already exists" in result


# ---------------------------------------------------------------------------
# Edge cases: Update project with unknown kwargs via manage
# ---------------------------------------------------------------------------


class TestManageUpdateProjectUnknownField:
    def test_update_project_unknown_field_returns_error(self, initialized_store):
        """update_project with an invalid field returns a clear error."""
        initialized_store.create_project(id="unk-proj", name="Unknown Field")
        result = muninn_manage(
            action="update_project",
            project="unk-proj",
            field="nonexistent",
            value="something",
        )
        assert "Error" in result


# ---------------------------------------------------------------------------
# Usage logging
# ---------------------------------------------------------------------------


class TestUsageLogging:
    def test_usage_logging(self, initialized_store, tmp_path, monkeypatch):
        """Calling a tool appends a valid JSON entry to usage.jsonl."""
        monkeypatch.setenv("MUNINN_DATA_DIR", str(tmp_path))

        muninn_save(project="log-test", content="Logging check")

        log_path = tmp_path / "usage.jsonl"
        assert log_path.exists(), "usage.jsonl was not created"

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1, "No log entries written"

        entry = json.loads(lines[0])
        assert entry["tool"] == "muninn_save"
        assert entry["project"] == "log-test"
        assert "ts" in entry
        # ts must be a valid ISO 8601 string
        from datetime import datetime
        datetime.fromisoformat(entry["ts"])  # raises if invalid

    def test_usage_logging_null_project(self, initialized_store, tmp_path, monkeypatch):
        """muninn_status logs project=null."""
        monkeypatch.setenv("MUNINN_DATA_DIR", str(tmp_path))

        muninn_status()

        log_path = tmp_path / "usage.jsonl"
        assert log_path.exists()
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["tool"] == "muninn_status"
        assert entry["project"] is None

    def test_usage_logging_appends_multiple_calls(self, initialized_store, tmp_path, monkeypatch):
        """Multiple tool calls each append a separate log entry."""
        monkeypatch.setenv("MUNINN_DATA_DIR", str(tmp_path))

        muninn_status()
        muninn_status()
        muninn_status()

        log_path = tmp_path / "usage.jsonl"
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
