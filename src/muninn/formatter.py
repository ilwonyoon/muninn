"""Formatting functions for LLM-readable Muninn output."""

from __future__ import annotations

from datetime import datetime, timezone

from muninn.models import Memory, Project, ProjectStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_EMOJI = {
    ProjectStatus.ACTIVE: "🟢",
    ProjectStatus.PAUSED: "⏸️",
    ProjectStatus.IDEA: "💤",
    ProjectStatus.ARCHIVED: "📦",
}

_STALE_DAYS = 7


def relative_time(iso_timestamp: str) -> str:
    """Convert an ISO 8601 timestamp to a human-readable relative time string."""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return iso_timestamp

    # Normalise to UTC-aware datetime for comparison.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(tz=timezone.utc)
    delta = now - dt
    days = delta.days

    if days < 0:
        return "just now"
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 14:
        return "1 week ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks} weeks ago"
    if days < 60:
        return "1 month ago"
    if days < 365:
        months = days // 30
        return f"{months} months ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def _date_label(iso_timestamp: str) -> str:
    """Return a short YYYY-MM-DD date string from an ISO timestamp."""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return iso_timestamp


def _is_stale(updated_at: str) -> bool:
    """Return True if the timestamp is older than _STALE_DAYS days."""
    try:
        dt = datetime.fromisoformat(updated_at)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    return (now - dt).days > _STALE_DAYS


# ---------------------------------------------------------------------------
# Public formatters
# ---------------------------------------------------------------------------


def format_recall(
    projects_memories: dict[str, tuple[Project, list[Memory]]],
    stats: dict[str, int] | None = None,
) -> str:
    """Format recall output for LLM consumption as a flat chronological list.

    Args:
        projects_memories: Mapping of project_id to (Project, list[Memory]).
        stats: Optional dict with keys chars_loaded, chars_budget,
            memories_loaded, memories_dropped. When provided, a footer
            summarising character and memory usage is appended.

    Returns:
        Plain-text string suitable for LLM context injection.
    """
    if not projects_memories:
        return "No memories found."

    sections: list[str] = []

    for _project_id, (project, memories) in projects_memories.items():
        emoji = _STATUS_EMOJI.get(project.status, "")
        header = f"## {project.id} ({emoji} {project.status})"

        lines: list[str] = [header]

        if project.summary:
            lines.append(project.summary)

        lines.append("")

        for mem in memories:
            short_id = mem.id[:8] if len(mem.id) >= 8 else mem.id
            date = relative_time(mem.updated_at)
            lines.append(f"- [{short_id}] {mem.content} ({date})")
            if mem.tags:
                lines.append(f"  tags: {', '.join(mem.tags)}")

        sections.append("\n".join(lines))

    # Add stats footer if available.
    if stats is not None:
        chars = stats.get("chars_loaded", 0)
        budget = stats.get("chars_budget", 0)
        loaded = stats.get("memories_loaded", 0)
        dropped = stats.get("memories_dropped", 0)
        footer = f"\n---\n📊 Context: {chars:,} / {budget:,} chars | {loaded} memories loaded"
        if dropped > 0:
            footer += f" | {dropped} dropped (budget exceeded)"
        sections.append(footer)

    return "\n\n".join(sections)


def format_status(projects: list[Project]) -> str:
    """Format a project status overview table.

    Args:
        projects: List of Project instances to display.

    Returns:
        Plain-text status table.
    """
    if not projects:
        return "No projects found."

    lines: list[str] = ["📋 Your Projects", ""]

    # Pre-compute display values for alignment.
    rows: list[tuple[str, str, str, str, str, str]] = []

    for project in projects:
        stale = project.status == ProjectStatus.ACTIVE and _is_stale(project.updated_at)
        emoji = "🟡" if stale else _STATUS_EMOJI.get(project.status, "")
        status_label = project.status
        updated = relative_time(project.updated_at)
        memories = str(project.memory_count)
        warning = "stale" if stale else ""
        rows.append((emoji, project.id, status_label, updated, memories, warning))

    # Column widths for alignment.
    id_w = max(len(r[1]) for r in rows)
    status_w = max(len(r[2]) for r in rows)
    updated_prefix = "updated: "
    updated_w = max(len(updated_prefix + r[3]) for r in rows)

    for emoji, proj_id, status_label, updated, memories, warning in rows:
        id_col = proj_id.ljust(id_w)
        status_col = status_label.ljust(status_w)
        updated_col = (updated_prefix + updated).ljust(updated_w)
        memories_col = f"memories: {memories}"
        line = f"{emoji} {id_col}  {status_col}  {updated_col}  {memories_col}"
        if warning:
            line += "  ⚠️ stale"
        lines.append(line)

    return "\n".join(lines)


def format_search_results(
    memories: list[Memory],
    query: str,
) -> str:
    """Format search results for a given query.

    Args:
        memories: List of Memory instances matching the query.
        query: The search query string.

    Returns:
        Plain-text formatted search results.
    """
    lines: list[str] = [f'🔍 Search results for "{query}"', ""]

    if not memories:
        lines.append("No results found.")
        return "\n".join(lines)

    for mem in memories:
        date = relative_time(mem.updated_at)
        short_id = mem.id[:8] if len(mem.id) >= 8 else mem.id
        lines.append(f"[{mem.project_id}] ({short_id}) {mem.content} — {date}")
        if mem.tags:
            lines.append(f"  tags: {', '.join(mem.tags)}")

    lines.append("")
    count = len(memories)
    lines.append(f"{count} result{'s' if count != 1 else ''} found.")

    return "\n".join(lines)


def format_save_confirmation(memory: Memory, project: Project) -> str:
    """Format a save confirmation message.

    Args:
        memory: The Memory that was just saved.
        project: The Project the memory belongs to.

    Returns:
        Plain-text confirmation string.
    """
    tags_display = ", ".join(memory.tags) if memory.tags else "none"
    short_id = memory.id[:8] if len(memory.id) >= 8 else memory.id

    base = f"✅ Saved to {project.id} (memory: {short_id})\nTags: {tags_display} | Project memories: {project.memory_count}"

    hint = _summary_hint(project)
    if hint:
        return f"{base}\n\n{hint}"
    return base


def _summary_hint(project: Project) -> str | None:
    """Return a conditional hint nudging the LLM to update the project summary.

    Returns None when no hint is needed.
    """
    if not project.summary:
        return (
            "⚠️ Project document is empty — this is the human-readable one-pager for this project.\n"
            "Action required:\n"
            f'  1. muninn_recall(project="{project.id}") to load all memories\n'
            "  2. Reorganize them by LOGIC (not chronology) into a markdown one-pager.\n"
            "     No fixed template — let the discussed topics shape the structure.\n"
            "     Use headers, tables, and lists for readability.\n"
            f'  3. muninn_manage(action="update_project", project="{project.id}",\n'
            '     field="summary", value="<full markdown one-pager>")'
        )

    if project.memory_count > 0 and project.memory_count % 5 == 0:
        return (
            f"💡 {project.memory_count} memories accumulated. The project one-pager may be outdated.\n"
            f"Recall memories for {project.id}, then update the document to reflect recent discussions."
        )

    return None


def format_manage_result(action: str, details: str) -> str:
    """Format a simple confirmation for manage actions.

    Args:
        action: The action that was performed (e.g. "deleted", "updated").
        details: Human-readable details about what changed.

    Returns:
        Plain-text confirmation string.
    """
    return f"✅ {action}: {details}"
