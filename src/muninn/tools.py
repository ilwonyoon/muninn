"""MCP tool definitions for the Muninn memory server.

Each function is a standalone tool that will be registered with FastMCP by
server.py.  The module-level ``_store`` is initialised once at startup via
``init_store()``.
"""

from __future__ import annotations

from typing import Literal

from muninn.formatter import (
    format_manage_result,
    format_recall,
    format_save_confirmation,
    format_search_results,
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


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def muninn_save(
    project: str,
    content: str,
    depth: int = 1,
    tags: list[str] | None = None,
) -> str:
    """Save important information to a project's memory.

    Distill conversation into structured, reusable context.
    Do NOT save raw conversation — summarize into key points.

    Depth guide — works for ANY project type (app, content, research, etc.):
      depth=0  "What is this?"    — Grasp the project in 10 seconds.
                                    Max 3 sentences. Always loaded on recall.
                                    Create this FIRST for every new project.
      depth=1  "To continue"      — What you need to resume work next session.
                                    Key decisions, current direction, open questions.
                                    200-500 chars each. One memory per topic.
      depth=2  "To go deeper"     — Details needed when diving into a specific area.
                                    Deep analysis, full research, detailed plans.
                                    Loaded only when explicitly requested.
      depth=3  "Just in case"     — Archive and reference. Raw data, old versions,
                                    logs. Rarely loaded.

    Best practices:
      - Always create a depth=0 summary first for new projects.
      - Keep each memory focused on ONE topic (don't combine unrelated info).
      - Prefer multiple short memories over one long memory.
      - Tag memories for easy filtering later.
    """
    try:
        store = _get_store()

        # Auto-create project if it does not exist yet.
        existing = store.get_project(project)
        if existing is None:
            store.create_project(id=project, name=project.capitalize())

        memory = store.save_memory(
            project_id=project,
            content=content,
            depth=depth,
            tags=tags,
        )

        # Re-fetch project so memory_count is up-to-date.
        updated_project = store.get_project(project)
        if updated_project is None:
            return f"Error: project '{project}' disappeared after save."

        return format_save_confirmation(memory, updated_project)

    except Exception as exc:
        return f"Error saving memory: {exc}"


def muninn_recall(
    project: str | None = None,
    depth: int = 1,
    max_chars: int = 8000,
    tags: list[str] | None = None,
) -> str:
    """Load project context from Muninn memory.

    Call this at session start or when the user mentions a project.  If no
    project specified, loads all active projects.

    Depth controls how much to load:
      depth=0  — "What is this?" summaries only (quick project overview)
      depth=1  — Above + "To continue" context (default, resume work)
      depth=2  — Above + "To go deeper" details (dive into specifics)
      depth=3  — Everything including archives (rarely needed)

    max_chars limits total output to avoid flooding the context window.
    Memories are loaded lowest-depth-first, newest-first within each depth.
    If the budget is exceeded, deeper/older memories are dropped.
    """
    try:
        store = _get_store()

        memories_by_project, recall_stats = store.recall(
            project_id=project,
            depth=depth,
            max_chars=max_chars,
            tags=tags,
        )

        # Build the dict[str, tuple[Project, list[Memory]]] that
        # format_recall expects.
        projects_memories: dict[str, tuple[Project, list]] = {}
        for project_id, memories in memories_by_project.items():
            proj = store.get_project(project_id)
            if proj is None:
                continue
            projects_memories[project_id] = (proj, memories)

        return format_recall(projects_memories, stats=recall_stats)

    except Exception as exc:
        return f"Error recalling memories: {exc}"


def muninn_search(
    query: str,
    project: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Search across all project memories by keyword.

    Use when the user asks about a specific topic or wants to find a previously
    saved memory.
    """
    try:
        store = _get_store()

        memories = store.search(
            query=query,
            project_id=project,
            tags=tags,
        )

        return format_search_results(memories, query)

    except Exception as exc:
        return f"Error searching memories: {exc}"


def muninn_status() -> str:
    """Show all projects with their status, last update time, and memory count.

    Use when the user asks about their projects or what they're working on.
    """
    try:
        store = _get_store()
        projects = store.list_projects()
        return format_status(projects)

    except Exception as exc:
        return f"Error fetching status: {exc}"


def muninn_manage(
    action: Literal["set_status", "delete_memory", "update_memory", "update_project", "create_project"],
    project: str,
    status: str | None = None,
    memory_id: str | None = None,
    field: str | None = None,
    value: str | None = None,
) -> str:
    """Manage projects and memories.

    Actions: set_status (active/paused/idea/archived), delete_memory,
    update_memory (field: content/depth, or tags via value as comma-separated),
    update_project (field: summary/github_repo/name), create_project.
    """
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

        if action == "delete_memory":
            if memory_id is None:
                return "Error: 'memory_id' parameter is required for delete_memory action."
            deleted = store.delete_memory(memory_id)
            if deleted:
                return format_manage_result(
                    "Memory deleted",
                    f"memory {memory_id[:8]} removed from {project}",
                )
            return f"Error: memory '{memory_id}' not found or already deleted."

        if action == "update_project":
            allowed_fields = {"summary", "github_repo", "name"}
            if field is None:
                return "Error: 'field' parameter is required for update_project action."
            if field not in allowed_fields:
                return (
                    f"Error: invalid field '{field}'. "
                    f"Must be one of: {sorted(allowed_fields)}"
                )
            if value is None:
                return "Error: 'value' parameter is required for update_project action."
            updated = store.update_project(project, **{field: value})
            return format_manage_result(
                "Project updated",
                f"{updated.id}.{field} = {value!r}",
            )

        if action == "update_memory":
            if memory_id is None:
                return "Error: 'memory_id' parameter is required for update_memory action."

            update_kwargs: dict[str, object] = {}
            if field == "content" and value is not None:
                update_kwargs["content"] = value
            elif field == "depth" and value is not None:
                try:
                    update_kwargs["depth"] = int(value)
                except ValueError:
                    return f"Error: depth must be an integer, got '{value}'."
            elif field == "tags" and value is not None:
                update_kwargs["tags"] = [t.strip() for t in value.split(",") if t.strip()]
            elif field is not None:
                return f"Error: invalid field '{field}' for update_memory. Must be one of: content, depth, tags."
            elif value is not None:
                # No field specified but value given — default to content update
                update_kwargs["content"] = value
            else:
                return "Error: 'value' parameter is required for update_memory action."

            updated = store.update_memory(memory_id, **update_kwargs)
            if updated is None:
                return f"Error: memory '{memory_id}' not found or already superseded."
            return format_manage_result(
                "Memory updated",
                f"memory {memory_id[:8]} in {project}",
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

        return f"Error: unknown action '{action}'. Valid actions: set_status, delete_memory, update_project, create_project."

    except Exception as exc:
        return f"Error in manage ({action}): {exc}"
