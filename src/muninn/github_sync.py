"""GitHub synchronisation for Muninn.

Fetches recent commits, open issues, and open PRs from a GitHub repository
using the REST API (stdlib ``urllib`` only — no third-party HTTP dependency).
Results are saved as a depth-1 memory with ``source='github'``, superseding
any previous GitHub-sourced memories for the same project.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from muninn.models import MemorySource
from muninn.store import MuninnStore


# ---------------------------------------------------------------------------
# Data containers (immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommitInfo:
    sha: str
    message: str
    author: str
    date: str
    files_changed: int


@dataclass(frozen=True)
class IssueInfo:
    number: int
    title: str
    labels: tuple[str, ...]
    created_at: str


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    title: str
    state: str
    created_at: str


@dataclass(frozen=True)
class SyncResult:
    commits: tuple[CommitInfo, ...]
    issues: tuple[IssueInfo, ...]
    pull_requests: tuple[PullRequestInfo, ...]
    memory_id: str
    superseded_ids: tuple[str, ...]


# ---------------------------------------------------------------------------
# GitHub REST API helpers
# ---------------------------------------------------------------------------

_GITHUB_API = "https://api.github.com"


def _build_headers(token: str | None) -> dict[str, str]:
    """Build HTTP headers for the GitHub API request."""
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "muninn-mcp",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_json(url: str, headers: dict[str, str]) -> Any:
    """Fetch a URL and decode JSON. Raises on HTTP/network errors."""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_commits(
    repo: str, headers: dict[str, str], *, limit: int = 10
) -> tuple[CommitInfo, ...]:
    """Fetch the most recent commits from ``/repos/{repo}/commits``."""
    url = f"{_GITHUB_API}/repos/{repo}/commits?per_page={limit}"
    items = _fetch_json(url, headers)
    results: list[CommitInfo] = []
    for item in items:
        commit_data = item.get("commit", {})
        author_data = commit_data.get("author", {})
        results.append(CommitInfo(
            sha=item.get("sha", "")[:7],
            message=commit_data.get("message", "").split("\n")[0][:120],
            author=author_data.get("name", "unknown"),
            date=author_data.get("date", ""),
            files_changed=len(item.get("files", [])),
        ))
    return tuple(results)


def _fetch_issues(
    repo: str, headers: dict[str, str], *, limit: int = 10
) -> tuple[IssueInfo, ...]:
    """Fetch open issues (excluding PRs) from ``/repos/{repo}/issues``."""
    url = (
        f"{_GITHUB_API}/repos/{repo}/issues"
        f"?state=open&per_page={limit}&sort=created&direction=desc"
    )
    items = _fetch_json(url, headers)
    results: list[IssueInfo] = []
    for item in items:
        # The issues endpoint also returns PRs; skip them.
        if "pull_request" in item:
            continue
        labels = tuple(
            label.get("name", "") for label in item.get("labels", [])
        )
        results.append(IssueInfo(
            number=item.get("number", 0),
            title=item.get("title", "")[:120],
            labels=labels,
            created_at=item.get("created_at", ""),
        ))
    return tuple(results)


def _fetch_pull_requests(
    repo: str, headers: dict[str, str], *, limit: int = 5
) -> tuple[PullRequestInfo, ...]:
    """Fetch open pull requests from ``/repos/{repo}/pulls``."""
    url = (
        f"{_GITHUB_API}/repos/{repo}/pulls"
        f"?state=open&per_page={limit}&sort=created&direction=desc"
    )
    items = _fetch_json(url, headers)
    results: list[PullRequestInfo] = []
    for item in items:
        results.append(PullRequestInfo(
            number=item.get("number", 0),
            title=item.get("title", "")[:120],
            state=item.get("state", "open"),
            created_at=item.get("created_at", ""),
        ))
    return tuple(results)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _format_sync_summary(
    repo: str,
    commits: tuple[CommitInfo, ...],
    issues: tuple[IssueInfo, ...],
    prs: tuple[PullRequestInfo, ...],
) -> str:
    """Format fetched GitHub data into a structured summary string."""
    lines: list[str] = [f"GitHub sync: {repo}"]

    # Commits section
    lines.append(f"\n## Recent commits ({len(commits)})")
    if commits:
        for c in commits:
            lines.append(f"- {c.sha} {c.message} ({c.author}, {c.date[:10]})")
    else:
        lines.append("- No recent commits")

    # Issues section
    lines.append(f"\n## Open issues ({len(issues)})")
    if issues:
        for i in issues:
            label_str = f" [{', '.join(i.labels)}]" if i.labels else ""
            lines.append(f"- #{i.number} {i.title}{label_str}")
    else:
        lines.append("- No open issues")

    # PRs section
    lines.append(f"\n## Open PRs ({len(prs)})")
    if prs:
        for pr in prs:
            lines.append(f"- #{pr.number} {pr.title} ({pr.state})")
    else:
        lines.append("- No open PRs")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sync_github(
    store: MuninnStore,
    project_id: str,
    github_repo: str,
    token: str | None = None,
) -> SyncResult:
    """Fetch GitHub data and save as a memory, superseding previous syncs.

    Parameters
    ----------
    store:
        The initialised MuninnStore.
    project_id:
        Muninn project ID to save the memory under.
    github_repo:
        GitHub repo in ``owner/repo`` format.
    token:
        Optional GitHub personal access token. Falls back to
        ``GITHUB_TOKEN`` environment variable.

    Returns
    -------
    SyncResult with fetched data and the new memory ID.

    Raises
    ------
    urllib.error.HTTPError
        On API errors (rate limiting, auth failures, etc.).
    """
    resolved_token = token or os.environ.get("GITHUB_TOKEN")
    headers = _build_headers(resolved_token)

    commits = _fetch_commits(github_repo, headers)
    issues = _fetch_issues(github_repo, headers)
    prs = _fetch_pull_requests(github_repo, headers)

    summary = _format_sync_summary(github_repo, commits, issues, prs)

    # Find and supersede previous github-sourced memories for this project.
    existing = store.search(query="GitHub sync", project_id=project_id, limit=100)
    superseded_ids: list[str] = []
    for mem in existing:
        if mem.source == MemorySource.GITHUB and mem.superseded_by is None:
            superseded_ids.append(mem.id)

    # Save the new memory.
    new_memory = store.save_memory(
        project_id=project_id,
        content=summary,
        source=MemorySource.GITHUB,
        tags=["github", "sync"],
    )

    # Supersede old github memories.
    for old_id in superseded_ids:
        store.supersede_memory(old_id, new_memory.id)

    return SyncResult(
        commits=commits,
        issues=issues,
        pull_requests=prs,
        memory_id=new_memory.id,
        superseded_ids=tuple(superseded_ids),
    )
