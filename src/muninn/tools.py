"""MCP tool definitions for the Muninn memory server.

Each function is a standalone tool that will be registered with FastMCP by
server.py.  The module-level ``_store`` is initialised once at startup via
``init_store()``.
"""

from __future__ import annotations

import json
import os
import urllib.error
from datetime import datetime, timezone
from typing import Literal

from muninn.formatter import (
    format_document_recall,
    format_document_saved,
    format_document_search,
    format_manage_result,
    format_status,
)
from muninn.models import Project, ProjectStatus, validate_project_status
from muninn.store import MuninnStore

# ---------------------------------------------------------------------------
# Module-level store — set once by server.py at startup
# ---------------------------------------------------------------------------

_store: MuninnStore | None = None


def init_store(store: MuninnStore) -> None:
    """Initialise the module-level store.  Called once by server.py."""
    global _store
    _store = store


def _get_store() -> MuninnStore:
    """Return the initialised store or raise if not yet set."""
    if _store is None:
        raise RuntimeError("Store not initialized. Call init_store() first.")
    return _store


def _log_usage(
    tool: str,
    project: str | None = None,
) -> None:
    """Append a usage log entry to ~/.local/share/muninn/usage.jsonl.

    Fails silently — logging must never break tool functionality.
    """
    try:
        data_dir = os.environ.get(
            "MUNINN_DATA_DIR",
            os.path.expanduser("~/.local/share/muninn"),
        )
        os.makedirs(data_dir, exist_ok=True)
        log_path = os.path.join(data_dir, "usage.jsonl")
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "project": project,
        }
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def muninn_save(
    project: str,
    content: str,
) -> str:
    """Save or update the project document (one-pager).

    Always pass the FULL document in the content parameter.
    If updating, recall first, merge new info, then save.
    This replaces the entire project summary — partial updates will
    lose existing content.

    Auto-creates the project if it does not exist.
    """
    _log_usage("muninn_save", project=project)
    try:
        if not content or not content.strip():
            return "Error: 'content' must not be empty or whitespace."

        store = _get_store()

        existing = store.get_project(project)
        if existing is None:
            store.create_project(id=project, name=project.capitalize())

        updated = store.update_project(project, summary=content)

        return format_document_saved(updated)

    except Exception as exc:
        return f"Error saving document: {exc}"


def muninn_recall(
    project: str | None = None,
) -> str:
    """Load the project document.

    If no project is specified, loads all active project documents.
    Call at session start when the user mentions a project, or when switching
    focus to a different project. Do not wait to be asked — proactive recall
    prevents re-explaining context.
    """
    _log_usage("muninn_recall", project=project)
    try:
        store = _get_store()

        if project is not None:
            proj = store.get_project(project)
            if proj is None:
                return f"Error: project '{project}' not found."
            projects = [proj]
        else:
            projects = store.list_projects(status="active")

        return format_document_recall(projects)

    except Exception as exc:
        return f"Error recalling document: {exc}"


def muninn_search(
    query: str,
) -> str:
    """Search across all project documents by keyword.

    Use when the user asks about a topic and you don't know which project it's
    in, or to check if something was already documented before saving.
    """
    _log_usage("muninn_search")
    try:
        store = _get_store()
        projects = store.search_projects(query)
        return format_document_search(projects, query)

    except Exception as exc:
        return f"Error searching documents: {exc}"


def muninn_status() -> str:
    """List all projects with status, memory count, and last update time.

    USE WHEN:
      - The user asks "what projects do I have?" or "what am I working on?".
      - You want a quick inventory before deciding which project to recall.
      - The user wants to review or clean up stale/archived projects.

    Returns one line per project with: id, status (active/paused/idea/archived),
    memory count, and last updated timestamp. Does not load memory content —
    call muninn_recall on a specific project for that.
    """
    _log_usage("muninn_status")
    try:
        store = _get_store()
        projects = store.list_projects()
        return format_status(projects)

    except Exception as exc:
        return f"Error fetching status: {exc}"


def muninn_manage(
    action: Literal["set_status", "create_project", "delete_project"],
    project: str,
    status: str | None = None,
    value: str | None = None,
) -> str:
    """Manage projects: change status, create, or delete.

    ACTIONS:

    set_status — Change a project's lifecycle status.
      Required: status = one of: active | paused | idea | archived
      Use 'paused' for projects on hold, 'archived' for completed/abandoned.
      Example: action="set_status", project="muninn", status="paused"

    create_project — Explicitly create a project with a display name.
      Optional: value = display name (defaults to project id if omitted)
      Note: muninn_save auto-creates projects, so only use this when you want
      to set a specific display name upfront before saving a document.
      Example: action="create_project", project="myapp", value="My App"

    delete_project — Permanently delete a project and its document.
      This is irreversible. The project and all associated data are removed.
      Example: action="delete_project", project="old-project"
    """
    _log_usage("muninn_manage", project=project)
    try:
        store = _get_store()

        if action == "set_status":
            if status is None:
                return "Error: 'status' parameter is required for set_status action."
            try:
                validate_project_status(status)
            except ValueError as exc:
                return f"Error: {exc}"
            updated = store.update_project(project, status=status)
            return format_manage_result(
                "Status updated",
                f"{updated.id} is now '{updated.status}'",
            )

        if action == "create_project":
            existing = store.get_project(project)
            if existing is not None:
                return f"Error: project '{project}' already exists."
            name = value if value else project
            created = store.create_project(id=project, name=name)
            return format_manage_result(
                "Project created",
                f"{created.id} ({created.name})",
            )

        if action == "delete_project":
            deleted = store.delete_project(project)
            if deleted:
                return format_manage_result(
                    "Project deleted",
                    f"{project} and its document have been permanently removed",
                )
            return f"Error: project '{project}' not found."

        return (
            f"Error: unknown action '{action}'. "
            "Valid actions: set_status, create_project, delete_project."
        )

    except Exception as exc:
        return f"Error in manage ({action}): {exc}"


def muninn_sync(project: str) -> str:
    """Sync a project's GitHub repository data into Muninn memory.

    Fetches recent commits, open issues, and open PRs from the linked GitHub
    repo and saves a structured summary as a depth-1 memory with
    source='github'.  Previous GitHub sync memories are automatically
    superseded.

    The project must have a ``github_repo`` field set (e.g. ``owner/repo``).
    Set it via the dashboard or REST API before syncing.

    Authentication: set the ``GITHUB_TOKEN`` environment variable for private
    repos or to avoid rate limits.
    """
    _log_usage("muninn_sync", project=project)
    try:
        store = _get_store()

        proj = store.get_project(project)
        if proj is None:
            return (
                f"Error: project '{project}' not found. "
                "Create it first with muninn_save or muninn_manage."
            )

        if not proj.github_repo:
            return (
                f"Error: project '{project}' has no linked GitHub repository. "
                "Set github_repo via the dashboard or REST API first."
            )

        from muninn.github_sync import sync_github

        result = sync_github(
            store=store,
            project_id=project,
            github_repo=proj.github_repo,
        )

        parts: list[str] = [
            f"Synced {proj.github_repo} into {project}",
            f"  Commits: {len(result.commits)}",
            f"  Issues: {len(result.issues)}",
            f"  PRs: {len(result.pull_requests)}",
            f"  Memory: {result.memory_id[:8]}",
        ]
        if result.superseded_ids:
            parts.append(
                f"  Superseded: {len(result.superseded_ids)} previous sync(s)"
            )

        return f"\u2705 {chr(10).join(parts)}"

    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return (
                "Error: GitHub API rate limit exceeded or access denied. "
                "Set GITHUB_TOKEN environment variable for authentication."
            )
        if exc.code == 404:
            return (
                f"Error: GitHub repository '{proj.github_repo}' not found. "
                "Check the owner/repo format and repository visibility."
            )
        return f"Error syncing GitHub: HTTP {exc.code} — {exc.reason}"

    except urllib.error.URLError as exc:
        return f"Error syncing GitHub: network error — {exc.reason}"

    except Exception as exc:
        return f"Error syncing GitHub: {exc}"
