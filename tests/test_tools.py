"""Unit tests for MCP tool functions in muninn.tools."""

from __future__ import annotations

import json
import os

import pytest

import muninn.tools as tools_module
from muninn.models import MemorySource
from muninn.tools import (
    _get_store,
    init_store,
    muninn_manage,
    muninn_recall,
    muninn_save,
    muninn_save_memory,
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
        with pytest.raises(RuntimeError, match="not initialized"):
            _get_store()

    def test_returns_store_after_init(self, initialized_store):
        """_get_store returns the store after init_store has been called."""
        result = _get_store()
        assert result is initialized_store


# ---------------------------------------------------------------------------
# muninn_save — content saving
# ---------------------------------------------------------------------------


class TestMuninnSave:
    def test_save_content_to_existing_project(self, initialized_store):
        """Save a content to an existing project returns confirmation."""
        initialized_store.create_project(id="myproject", name="My Project")
        result = muninn_save(project="myproject", content="# My Project\n\n## Overview\nA cool app.")
        assert "Saved" in result
        assert "myproject" in result

    def test_save_auto_creates_project(self, initialized_store):
        """Save to a non-existing project auto-creates it."""
        result = muninn_save(project="newproject", content="# New\n\n## Overview\nBrand new project.")
        assert "Saved" in result
        project = initialized_store.get_project("newproject")
        assert project is not None
        assert project.summary == "# New\n\n## Overview\nBrand new project."

    def test_save_updates_summary(self, initialized_store):
        """Save replaces the entire project summary."""
        initialized_store.create_project(id="upd", name="Updatable")
        muninn_save(project="upd", content="## Overview\nVersion 1")
        muninn_save(project="upd", content="## Overview\nVersion 2")
        project = initialized_store.get_project("upd")
        assert project is not None
        assert project.summary == "## Overview\nVersion 2"

    def test_save_empty_content_returns_error(self, initialized_store):
        """Saving empty content returns error."""
        result = muninn_save(project="val-proj", content="")
        assert "Error" in result

    def test_save_whitespace_content_returns_error(self, initialized_store):
        """Saving whitespace-only content returns error."""
        result = muninn_save(project="val-proj", content="   \n  ")
        assert "Error" in result

    def test_save_plain_text_returns_error(self, initialized_store):
        """Saving plain text without markdown headers returns error."""
        result = muninn_save(project="val-proj", content="This is a plain text summary without any headers.")
        assert "Error" in result
        assert "## headers" in result

    def test_save_with_markdown_headers_succeeds(self, initialized_store):
        """Saving content with ## headers succeeds."""
        content = "# My Project\n\n## Overview\nA cool app.\n\n## Status\nIn progress."
        result = muninn_save(project="md-proj", content=content)
        assert "Saved" in result

    def test_save_shows_char_count(self, initialized_store):
        """Save confirmation includes character count."""
        initialized_store.create_project(id="chars", name="Chars")
        result = muninn_save(project="chars", content="## Overview\nHello world")
        assert "23" in result  # len("## Overview\nHello world") == 23


# ---------------------------------------------------------------------------
# muninn_recall — content loading
# ---------------------------------------------------------------------------


class TestMuninnRecall:
    def test_recall_no_projects_returns_not_found(self, initialized_store):
        """Recall with no projects returns 'No projects found.'"""
        result = muninn_recall()
        assert "No projects found." in result

    def test_recall_specific_project_with_content(self, initialized_store):
        """Recall a specific project returns its content."""
        initialized_store.create_project(id="alpha", name="Alpha")
        initialized_store.update_project("alpha", summary="# Alpha\n\nAlpha project doc.")

        result = muninn_recall(project="alpha")

        assert "alpha" in result
        assert "Alpha project doc." in result

    def test_recall_specific_project_no_content(self, initialized_store):
        """Recall a project with no content shows 'No content yet.'"""
        initialized_store.create_project(id="empty", name="Empty")

        result = muninn_recall(project="empty")

        assert "No document yet." in result

    def test_recall_all_active_projects(self, initialized_store):
        """Recall with project=None returns all active project contents."""
        initialized_store.create_project(id="proj-a", name="A")
        initialized_store.create_project(id="proj-b", name="B")
        initialized_store.update_project("proj-a", summary="Doc A")
        initialized_store.update_project("proj-b", summary="Doc B")

        result = muninn_recall(project=None)

        assert "proj-a" in result
        assert "proj-b" in result

    def test_recall_excludes_paused(self, initialized_store):
        """Recall with no project excludes paused projects."""
        initialized_store.create_project(id="active-p", name="Active")
        initialized_store.create_project(id="paused-p", name="Paused")
        initialized_store.update_project("active-p", summary="Active doc")
        initialized_store.update_project("paused-p", status="paused", summary="Paused doc")

        result = muninn_recall(project=None)

        assert "active-p" in result
        assert "paused-p" not in result

    def test_recall_nonexistent_project_returns_error(self, initialized_store):
        """Recall a non-existent project returns error."""
        result = muninn_recall(project="no-such-project")
        assert "Error" in result
        assert "not found" in result

    def test_recall_includes_latest_github_activity(self, initialized_store):
        """Recall appends latest GitHub sync content to the document."""
        initialized_store.create_project(id="sync-doc", name="Sync Doc")
        initialized_store.update_project("sync-doc", summary="## Overview\nBase document")
        initialized_store.save_memory(
            project_id="sync-doc",
            content="GitHub sync summary content",
            source=MemorySource.GITHUB,
            tags=["github-sync"],
        )

        result = muninn_recall(project="sync-doc")

        assert "## Overview\nBase document" in result
        assert "## GitHub Activity" in result
        assert "GitHub sync summary content" in result


# ---------------------------------------------------------------------------
# muninn_search — content search
# ---------------------------------------------------------------------------


class TestMuninnSearch:
    def test_search_no_results(self, initialized_store):
        """Search that matches nothing returns 'No projects found matching'."""
        initialized_store.create_project(id="s-proj", name="Search Proj")
        initialized_store.update_project("s-proj", summary="Hello world")

        result = muninn_search(query="xyzzy_nomatch_zork")

        assert "No projects found matching" in result

    def test_search_with_results(self, initialized_store):
        """Search that matches returns project with snippet."""
        initialized_store.create_project(id="s-proj", name="Search Proj")
        initialized_store.update_project("s-proj", summary="The quick brown fox jumps over the lazy dog")

        result = muninn_search(query="fox")

        assert "fox" in result
        assert "s-proj" in result

    def test_search_case_insensitive(self, initialized_store):
        """Search is case-insensitive."""
        initialized_store.create_project(id="case-proj", name="Case")
        initialized_store.update_project("case-proj", summary="Important Decision Made")

        result = muninn_search(query="decision")

        assert "case-proj" in result

    def test_search_skips_null_summaries(self, initialized_store):
        """Search does not return projects with null summaries."""
        initialized_store.create_project(id="no-doc", name="No Doc")
        # no summary set

        result = muninn_search(query="unrelated_keyword")

        assert "No projects found matching" in result

    def test_search_multi_term_fts(self, initialized_store):
        """Multi-term query requires both terms and returns an FTS snippet."""
        initialized_store.create_project(id="s-both", name="Both")
        initialized_store.create_project(id="s-one", name="One")
        initialized_store.update_project("s-both", summary="Auth implementation includes OAuth callback flow")
        initialized_store.update_project("s-one", summary="Auth implementation only")

        result = muninn_search(query="auth oauth")

        assert "s-both" in result
        assert "s-one" not in result
        assert "[Auth]" in result or "[OAuth]" in result


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

    def test_status_shows_document_status(self, initialized_store):
        """Status shows 'has document' or 'no document' per project."""
        initialized_store.create_project(id="with-doc", name="With")
        initialized_store.create_project(id="no-doc", name="Without")
        initialized_store.update_project("with-doc", summary="Some doc")

        result = muninn_status()

        assert "has document" in result
        assert "no document" in result


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

    def test_create_duplicate_project_returns_error(self, initialized_store):
        """create_project with existing ID returns error."""
        initialized_store.create_project(id="dup-proj", name="First")
        result = muninn_manage(
            action="create_project",
            project="dup-proj",
            value="Second",
        )
        assert "Error" in result
        assert "already exists" in result


class TestMuninnManageDeleteProject:
    def test_delete_project(self, initialized_store):
        """delete_project action returns 'Project deleted'."""
        initialized_store.create_project(id="del-proj", name="To Delete")
        result = muninn_manage(action="delete_project", project="del-proj")

        assert "Project deleted" in result
        assert initialized_store.get_project("del-proj") is None

    def test_delete_nonexistent_project_returns_error(self, initialized_store):
        """delete_project for non-existent project returns error."""
        result = muninn_manage(action="delete_project", project="no-such")
        assert "Error" in result


class TestMuninnManageSetGithubRepo:
    def test_set_github_repo(self, initialized_store):
        """set_github_repo stores owner/repo on the project."""
        initialized_store.create_project(id="repo-proj", name="Repo Project")

        result = muninn_manage(
            action="set_github_repo",
            project="repo-proj",
            value="owner/repo",
        )

        assert "GitHub repo updated" in result
        project = initialized_store.get_project("repo-proj")
        assert project is not None
        assert project.github_repo == "owner/repo"

    def test_set_github_repo_missing_value(self, initialized_store):
        """set_github_repo requires value parameter."""
        initialized_store.create_project(id="repo-proj-2", name="Repo Project 2")

        result = muninn_manage(
            action="set_github_repo",
            project="repo-proj-2",
            value=None,
        )

        assert "Error" in result
        assert "value" in result.lower()


class TestMuninnManageUnknownAction:
    def test_unknown_action_returns_error(self, initialized_store):
        """Unknown action returns an error message."""
        result = muninn_manage(action="teleport", project="any-proj")

        assert "Error" in result
        assert "teleport" in result


# ---------------------------------------------------------------------------
# muninn_save_memory
# ---------------------------------------------------------------------------


class TestMuninnSaveMemory:
    def test_save_memory_to_existing_project(self, initialized_store):
        """Saving a memory to an existing project succeeds."""
        initialized_store.create_project(id="proj", name="P")
        result = muninn_save_memory(project="proj", content="milestone reached")
        assert "Memory saved" in result
        assert "proj" in result

    def test_save_memory_with_tags(self, initialized_store):
        """Saving a memory with tags succeeds."""
        initialized_store.create_project(id="proj", name="P")
        result = muninn_save_memory(project="proj", content="v1 release", tags=["release"])
        assert "Memory saved" in result

    def test_save_memory_project_not_found(self, initialized_store):
        """Saving a memory to a nonexistent project returns an error."""
        result = muninn_save_memory(project="nonexistent", content="hello")
        assert "Error" in result
        assert "not found" in result

    def test_save_memory_empty_content(self, initialized_store):
        """Saving a memory with empty content returns an error."""
        initialized_store.create_project(id="proj", name="P")
        result = muninn_save_memory(project="proj", content="")
        assert "Error" in result

    def test_save_memory_whitespace_content(self, initialized_store):
        """Saving a memory with whitespace-only content returns an error."""
        initialized_store.create_project(id="proj", name="P")
        result = muninn_save_memory(project="proj", content="   ")
        assert "Error" in result


# ---------------------------------------------------------------------------
# Usage logging
# ---------------------------------------------------------------------------


class TestUsageLogging:
    def test_usage_logging(self, initialized_store, tmp_path, monkeypatch):
        """Calling a tool appends a valid JSON entry to usage.jsonl."""
        monkeypatch.setenv("MUNINN_DATA_DIR", str(tmp_path))

        muninn_save(project="log-test", content="## Overview\nLogging check doc")

        log_path = tmp_path / "usage.jsonl"
        assert log_path.exists(), "usage.jsonl was not created"

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1, "No log entries written"

        entry = json.loads(lines[0])
        assert entry["tool"] == "muninn_save"
        assert entry["project"] == "log-test"
        assert "ts" in entry
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
