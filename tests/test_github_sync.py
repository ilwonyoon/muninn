"""Unit tests for GitHub sync functionality."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import muninn.tools as tools_module
from muninn.github_sync import sync_github
from muninn.models import MemorySource
from muninn.tools import init_store, muninn_sync


# ---------------------------------------------------------------------------
# Mock GitHub API responses
# ---------------------------------------------------------------------------

_MOCK_COMMITS = [
    {
        "sha": "abc1234567890",
        "commit": {
            "message": "feat: add sync tool\nDetailed description here",
            "author": {"name": "Alice", "date": "2026-02-20T10:00:00Z"},
        },
        "files": [{"filename": "tools.py"}, {"filename": "server.py"}],
    },
    {
        "sha": "def4567890123",
        "commit": {
            "message": "fix: handle rate limiting",
            "author": {"name": "Bob", "date": "2026-02-19T08:00:00Z"},
        },
        "files": [{"filename": "github_sync.py"}],
    },
]

_MOCK_ISSUES = [
    {
        "number": 42,
        "title": "Add search filtering by date",
        "labels": [{"name": "enhancement"}, {"name": "good first issue"}],
        "created_at": "2026-02-18T12:00:00Z",
    },
    {
        "number": 43,
        "title": "Memory recall is slow for large projects",
        "labels": [{"name": "bug"}],
        "created_at": "2026-02-17T09:00:00Z",
        "pull_request": {"url": "https://api.github.com/pulls/43"},
    },
]

_MOCK_PRS = [
    {
        "number": 10,
        "title": "Add OAuth support",
        "state": "open",
        "created_at": "2026-02-16T15:00:00Z",
    },
]


def _mock_urlopen(responses: dict[str, list]):
    """Create a mock for urllib.request.urlopen that returns different data per URL."""

    def _side_effect(req, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        for pattern, data in responses.items():
            if pattern in url:
                mock_resp = MagicMock()
                mock_resp.read.return_value = json.dumps(data).encode("utf-8")
                mock_resp.__enter__ = lambda s: s
                mock_resp.__exit__ = MagicMock(return_value=False)
                return mock_resp
        raise ValueError(f"Unmocked URL: {url}")

    return _side_effect


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the module-level _store before and after each test."""
    tools_module._store = None
    yield
    tools_module._store = None


@pytest.fixture
def initialized_store(store):
    """Return a MuninnStore registered with init_store()."""
    init_store(store)
    return store


# ---------------------------------------------------------------------------
# Tests: sync_github (low-level function)
# ---------------------------------------------------------------------------


class TestSyncFormatsCommits:
    """Test that sync_github fetches and formats commit data correctly."""

    @patch("muninn.github_sync.urllib.request.urlopen")
    def test_sync_formats_commits(self, mock_urlopen_fn, initialized_store):
        mock_urlopen_fn.side_effect = _mock_urlopen({
            "/commits": _MOCK_COMMITS,
            "/issues": [_MOCK_ISSUES[0]],
            "/pulls": _MOCK_PRS,
        })

        initialized_store.create_project(
            id="myproj", name="My Project", github_repo="owner/repo"
        )

        result = sync_github(
            store=initialized_store,
            project_id="myproj",
            github_repo="owner/repo",
            token="fake-token",
        )

        assert len(result.commits) == 2
        assert result.commits[0].sha == "abc1234"
        assert result.commits[0].message == "feat: add sync tool"
        assert result.commits[0].author == "Alice"
        assert result.commits[1].sha == "def4567"

    @patch("muninn.github_sync.urllib.request.urlopen")
    def test_sync_formats_issues_excludes_prs(self, mock_urlopen_fn, initialized_store):
        """Issues endpoint returns PRs too; sync should filter them out."""
        mock_urlopen_fn.side_effect = _mock_urlopen({
            "/commits": [],
            "/issues": _MOCK_ISSUES,
            "/pulls": [],
        })

        initialized_store.create_project(
            id="issueproj", name="Issue Project", github_repo="owner/repo"
        )

        result = sync_github(
            store=initialized_store,
            project_id="issueproj",
            github_repo="owner/repo",
        )

        # Issue #43 has pull_request key and should be excluded
        assert len(result.issues) == 1
        assert result.issues[0].number == 42
        assert result.issues[0].title == "Add search filtering by date"
        assert "enhancement" in result.issues[0].labels


# ---------------------------------------------------------------------------
# Tests: muninn_sync tool (no repo linked)
# ---------------------------------------------------------------------------


class TestSyncNoRepo:
    """Test that muninn_sync returns a helpful error when no repo is linked."""

    def test_sync_no_repo_returns_error(self, initialized_store):
        initialized_store.create_project(id="norepo", name="No Repo")

        result = muninn_sync(project="norepo")

        assert "Error" in result
        assert "no linked GitHub repository" in result
        assert "github_repo" in result

    def test_sync_nonexistent_project_returns_error(self, initialized_store):
        result = muninn_sync(project="ghost")

        assert "Error" in result
        assert "not found" in result


# ---------------------------------------------------------------------------
# Tests: memory is saved with source='github'
# ---------------------------------------------------------------------------


class TestSyncSavesMemory:
    """Test that sync_github saves a memory with the correct source."""

    @patch("muninn.github_sync.urllib.request.urlopen")
    def test_sync_saves_memory_with_github_source(self, mock_urlopen_fn, initialized_store):
        mock_urlopen_fn.side_effect = _mock_urlopen({
            "/commits": _MOCK_COMMITS,
            "/issues": [],
            "/pulls": [],
        })

        initialized_store.create_project(
            id="savproj", name="Save Project", github_repo="owner/repo"
        )

        result = sync_github(
            store=initialized_store,
            project_id="savproj",
            github_repo="owner/repo",
        )

        # Verify memory was saved
        assert result.memory_id

        # Recall and check the memory exists with correct source
        memories_by_project, _ = initialized_store.recall(
            project_id="savproj", depth=1
        )
        memories = memories_by_project.get("savproj", [])
        github_memories = [m for m in memories if m.source == MemorySource.GITHUB]

        assert len(github_memories) == 1
        assert "GitHub sync" in github_memories[0].content
        assert "owner/repo" in github_memories[0].content


# ---------------------------------------------------------------------------
# Tests: second sync supersedes first
# ---------------------------------------------------------------------------


class TestSyncSupersedesOld:
    """Test that a second sync supersedes the first github memory."""

    @patch("muninn.github_sync.urllib.request.urlopen")
    def test_second_sync_supersedes_first(self, mock_urlopen_fn, initialized_store):
        mock_urlopen_fn.side_effect = _mock_urlopen({
            "/commits": _MOCK_COMMITS[:1],
            "/issues": [],
            "/pulls": [],
        })

        initialized_store.create_project(
            id="supproj", name="Supersede Project", github_repo="owner/repo"
        )

        # First sync
        result1 = sync_github(
            store=initialized_store,
            project_id="supproj",
            github_repo="owner/repo",
        )
        first_memory_id = result1.memory_id
        assert len(result1.superseded_ids) == 0

        # Second sync — should supersede the first
        result2 = sync_github(
            store=initialized_store,
            project_id="supproj",
            github_repo="owner/repo",
        )
        assert first_memory_id in result2.superseded_ids

        # Only the second memory should be active (non-superseded)
        memories_by_project, _ = initialized_store.recall(
            project_id="supproj", depth=1
        )
        memories = memories_by_project.get("supproj", [])
        github_memories = [m for m in memories if m.source == MemorySource.GITHUB]

        assert len(github_memories) == 1
        assert github_memories[0].id == result2.memory_id


# ---------------------------------------------------------------------------
# Tests: muninn_sync tool (end-to-end via tool function)
# ---------------------------------------------------------------------------


class TestSyncToolEndToEnd:
    """Test the muninn_sync tool function returns formatted output."""

    @patch("muninn.github_sync.urllib.request.urlopen")
    def test_sync_tool_returns_formatted_result(self, mock_urlopen_fn, initialized_store):
        mock_urlopen_fn.side_effect = _mock_urlopen({
            "/commits": _MOCK_COMMITS,
            "/issues": [_MOCK_ISSUES[0]],
            "/pulls": _MOCK_PRS,
        })

        initialized_store.create_project(
            id="toolproj", name="Tool Project", github_repo="owner/repo"
        )

        result = muninn_sync(project="toolproj")

        assert "\u2705" in result  # checkmark
        assert "Synced owner/repo" in result
        assert "Commits: 2" in result
        assert "Issues: 1" in result
        assert "PRs: 1" in result
