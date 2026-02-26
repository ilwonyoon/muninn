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


def _log_usage(
    tool: str,
    project: str | None = None,
    depth: int | None = None,
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
            "depth": depth,
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
    depth: int = 2,
    tags: tuple[str, ...] | list[str] | None = None,
    category: str = "status",
    parent_memory_id: str | None = None,
    title: str | None = None,
) -> str:
    """Save a distilled memory to a project. Auto-creates the project if it does not exist.

    HIERARCHY — memories are organized in a parent-child tree:
      L0 (depth=0) — Project identity. One per project. Create FIRST.
                     Example: "Muninn: Python MCP memory server. SQLite + FTS5."
      L1 (depth=1) — Topic index entries. One per major topic area.
                     Example: "Auth: Bearer token via MUNINN_API_KEY."
      L2 (depth=2) — Working memories under a topic. DEFAULT depth.
                     Example: "Decided to remove OAuth — local-only scope."
      L3 (depth=3) — Archive / raw data under a working memory.
                     Example: Raw benchmark results, old schema versions.

    SAVE PATTERN:
      1. Check existing L1 index: muninn_recall(project, depth=1)
      2. If topic L1 exists, save L2 under it: parent_memory_id=<l1_id>
      3. If topic L1 is new, create it first, then save L2 under it.
      4. Always set title= for skimmability (max 60 chars, plain text).

    CATEGORY — classifies the type of content being stored:
      ## Exploration
      category="brainstorm"     — Unfiltered ideation: voice chat dumps, what-if explorations, early-stage thinking. Mark resolved=true when ideas graduate to decision/product.
      ## Product categories
      category="vision"         — Why this project exists: motivation, target users, market, business model
      category="product"        — What to build: scope decisions, UX principles, feature tradeoffs
      category="insight"        — User observations, usage patterns, discovered behaviors, feedback
      category="status"         — Current state: milestones, progress, what's next (DEFAULT)
      ## Engineering categories
      category="architecture"   — System structure: tech stack, modules, data models, schemas
      category="decision"       — Engineering rationale: why this approach, tradeoffs considered
      category="implementation" — Code-level facts: config, commands, file paths, API contracts
      category="issue"          — Bugs, errors, blockers, unresolved hurdles

    TAGS — always set 1-3 tags per memory to enable later filtering:
      Decisions:    ['decision', 'architecture'] or ['decision', 'api']
      Bugs/issues:  ['bug', 'auth'] or ['bug', 'performance']
      Pending work: ['todo', 'api'] or ['todo', 'testing']
      Research:     ['research', 'benchmarks'] or ['research', 'ux']
      Milestones:   ['milestone', 'shipped'] or ['milestone', 'v1']
      Config/infra: ['config', 'infra'] or ['config', 'deploy']

    RULES:
      - One topic per memory. Split unrelated facts into separate muninn_save calls.
      - L0-L1 must be skimmable in under 5 seconds — cut anything redundant.
      - Prefer concrete over vague: 'Using hatchling' beats 'build system chosen'.
      - Update stale memories via muninn_manage update_memory instead of adding duplicates.
    """
    _log_usage("muninn_save", project=project, depth=depth)
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
            category=category,
            parent_memory_id=parent_memory_id,
            title=title,
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
    depth: int = 2,
    max_chars: int = 8000,
    tags: list[str] | None = None,
    parent_id: str | None = None,
) -> str:
    """Load project context from Muninn memory.

    WHEN TO CALL:
      - Session start: call immediately when the user mentions any project by name.
        Do not wait to be asked — proactive recall prevents re-explaining context.
      - Switching focus: call when the conversation shifts to a different project.
      - After search: call after muninn_search to load full context for a found project.

    DRILL-DOWN PATTERN:
      1. Start with depth=1 to get the topic index (L1 entries).
      2. Find the relevant L1 topic memory id.
      3. Call again with parent_id=<l1_id>, depth=2 to load working memories under it.
      4. Use depth=3 only for archives.

    DEPTH — controls how much to load (cumulative, each level includes all above):
      depth=0  — L0 identity only. Quick project identity, always 1-2 sentences.
                 Use when you just need to know if a project exists.
      depth=1  — L0 + L1 topic index. Resumes work from last session.
                 Use this at session start for any active project.
      depth=2  — Above + L2 working memories. Full current context. DEFAULT.
                 Use when the user explicitly asks to dive into a specific area.
      depth=3  — Everything including L3 archives. Rarely needed.

    If no project is specified, loads all active projects (useful at session start
    when you don't yet know which project the user will work on).

    max_chars caps total output to protect context window. Memories load
    lowest-depth-first, newest-first within each depth. If the budget is hit,
    deeper and older memories are dropped silently.
    """
    _log_usage("muninn_recall", project=project, depth=depth)
    try:
        store = _get_store()

        memories_by_project, recall_stats = store.recall(
            project_id=project,
            depth=depth,
            max_chars=max_chars,
            tags=tags,
            parent_id=parent_id,
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
    limit: int = 50,
) -> str:
    """Full-text search across project memories by keyword or phrase.

    USE SEARCH WHEN:
      - The user asks about a specific topic and you don't know which project it's in.
      - You need to find a particular decision, bug, or fact by keyword.
      - You want to check if something was already saved before saving a duplicate.
      - The user asks "did we decide..." or "what did we say about...".

    USE RECALL INSTEAD WHEN:
      - You know the project name and want full session context — recall is faster.
      - Session just started and you want everything for a project (use muninn_recall).

    Narrows results with optional filters:
      project  — limit to one project's memories
      tags     — filter to memories with specific tags (e.g. ['decision', 'bug'])
      limit    — max memories returned (default 50, lower for faster scans)

    Results are ranked by FTS5 relevance. Inspect the project field on each result
    to identify which project owns the memory, then call muninn_recall on that
    project if you need full context.
    """
    _log_usage("muninn_search", project=project)
    try:
        store = _get_store()

        memories = store.search(
            query=query,
            project_id=project,
            tags=tags,
            limit=limit,
        )

        return format_search_results(memories, query)

    except Exception as exc:
        return f"Error searching memories: {exc}"


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
    action: Literal["set_status", "delete_memory", "update_memory", "update_project", "create_project"],
    project: str,
    status: str | None = None,
    memory_id: str | None = None,
    field: str | None = None,
    value: str | None = None,
) -> str:
    """Manage projects and memories: update, delete, or change status.

    ACTIONS:

    set_status — Change a project's lifecycle status.
      Required: status = one of: active | paused | idea | archived
      Use 'paused' for projects on hold, 'archived' for completed/abandoned.
      Example: action="set_status", project="muninn", status="paused"

    delete_memory — Permanently remove a single memory by ID.
      Required: memory_id (full UUID from recall/search output)
      Use when a memory is stale, wrong, or superseded and update won't help.
      Example: action="delete_memory", project="muninn", memory_id="abc123..."

    update_memory — Edit an existing memory in place.
      Required: memory_id
      Optional: field = content | depth | tags
        field="content", value="new text"           — rewrite the memory
        field="depth", value="2"                    — change depth level
        field="tags", value="decision,architecture" — replace all tags (comma-separated)
      Prefer this over delete + re-save to preserve memory history.
      Example: action="update_memory", project="muninn", memory_id="abc123...",
               field="content", value="Auth: switched to API key only. OAuth removed."

    update_project — Edit project metadata.
      Required: field = name | summary | github_repo
      Required: value = new field value
      Example: action="update_project", project="muninn", field="name", value="Muninn v2"

    create_project — Explicitly create a project with a display name.
      Optional: value = display name (defaults to project id if omitted)
      Note: muninn_save auto-creates projects, so only use this when you want
      to set a specific display name upfront before saving any memories.
      Example: action="create_project", project="myapp", value="My App"
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
            elif field == "category" and value is not None:
                update_kwargs["category"] = value
            elif field == "parent_memory_id":
                update_kwargs["parent_memory_id"] = value  # None clears the parent
            elif field == "title":
                update_kwargs["title"] = value  # None clears the title
            elif field == "resolved" and value is not None:
                update_kwargs["resolved"] = value.lower() in ("true", "1", "yes")
            elif field is not None:
                return f"Error: invalid field '{field}' for update_memory. Must be one of: content, depth, tags, category, parent_memory_id, title, resolved."
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


def muninn_sync(project: str) -> str:
    """Sync a project's GitHub repository data into Muninn memory.

    Fetches recent commits, open issues, and open PRs from the linked GitHub
    repo and saves a structured summary as a depth-1 memory with
    source='github'.  Previous GitHub sync memories are automatically
    superseded.

    The project must have a ``github_repo`` field set (e.g. ``owner/repo``).
    Use ``muninn_manage(action='update_project', field='github_repo', ...)``
    to link a repo first.

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
                "Set one with: muninn_manage(action='update_project', "
                f"project='{project}', field='github_repo', value='owner/repo')"
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
