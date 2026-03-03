"""Formatting functions for LLM-readable Muninn output."""

from __future__ import annotations

from datetime import datetime, timezone

from muninn.models import Project, ProjectStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_EMOJI = {
    ProjectStatus.ACTIVE: "\U0001f7e2",
    ProjectStatus.PAUSED: "\u23f8\ufe0f",
    ProjectStatus.IDEA: "\U0001f4a4",
    ProjectStatus.ARCHIVED: "\U0001f4e6",
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


def _extract_snippet(text: str, query: str, max_len: int = 200) -> str:
    """Extract a snippet from *text* around the first occurrence of *query*."""
    lower_text = text.lower()
    lower_query = query.lower()
    idx = lower_text.find(lower_query)
    if idx == -1:
        return text[:max_len] + ("..." if len(text) > max_len else "")
    start = max(0, idx - 60)
    end = min(len(text), idx + len(query) + 60)
    snippet = text[start:end].replace("\n", " ")
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


# ---------------------------------------------------------------------------
# Public formatters — Document-first
# ---------------------------------------------------------------------------


def format_document_saved(project: Project) -> str:
    """Format a confirmation after saving/updating a project document.

    Args:
        project: The Project whose document was just saved.

    Returns:
        Plain-text confirmation string.
    """
    chars = len(project.summary) if project.summary else 0
    return f"\u2705 Saved {project.id} document ({chars:,} chars)"


def format_document_recall(projects: list[Project]) -> str:
    """Format project documents for LLM consumption.

    Args:
        projects: List of Project instances to display.

    Returns:
        Plain-text string with each project's document.
    """
    if not projects:
        return "No projects found."

    sections: list[str] = []

    for project in projects:
        emoji = _STATUS_EMOJI.get(project.status, "")
        header = f"## {project.id} ({emoji} {project.status})"

        if project.summary:
            sections.append(f"{header}\n\n{project.summary}")
        else:
            sections.append(f"{header}\n\nNo document yet.")

    return "\n\n---\n\n".join(sections)


def format_document_search(projects: list[Project], query: str) -> str:
    """Format document search results.

    Args:
        projects: List of matching Project instances.
        query: The search query string.

    Returns:
        Plain-text formatted search results.
    """
    if not projects:
        return f'No projects found matching "{query}".'

    lines: list[str] = [f'\U0001f50d Projects matching "{query}"', ""]

    for p in projects:
        snippet = _extract_snippet(p.summary or "", query)
        lines.append(f"- {p.id} ({p.status}): {snippet}")

    lines.append("")
    count = len(projects)
    lines.append(f"{count} project{'s' if count != 1 else ''} found.")

    return "\n".join(lines)


def format_status(projects: list[Project]) -> str:
    """Format a project status overview table.

    Args:
        projects: List of Project instances to display.

    Returns:
        Plain-text status table.
    """
    if not projects:
        return "No projects found."

    lines: list[str] = ["\U0001f4cb Your Projects", ""]

    # Pre-compute display values for alignment.
    rows: list[tuple[str, str, str, str, str, str]] = []

    for project in projects:
        stale = project.status == ProjectStatus.ACTIVE and _is_stale(project.updated_at)
        emoji = "\U0001f7e1" if stale else _STATUS_EMOJI.get(project.status, "")
        status_label = project.status
        updated = relative_time(project.updated_at)
        doc_status = "has document" if project.summary else "no document"
        warning = "stale" if stale else ""
        rows.append((emoji, project.id, status_label, updated, doc_status, warning))

    # Column widths for alignment.
    id_w = max(len(r[1]) for r in rows)
    status_w = max(len(r[2]) for r in rows)
    updated_prefix = "updated: "
    updated_w = max(len(updated_prefix + r[3]) for r in rows)

    for emoji, proj_id, status_label, updated, doc_status, warning in rows:
        id_col = proj_id.ljust(id_w)
        status_col = status_label.ljust(status_w)
        updated_col = (updated_prefix + updated).ljust(updated_w)
        line = f"{emoji} {id_col}  {status_col}  {updated_col}  {doc_status}"
        if warning:
            line += "  \u26a0\ufe0f stale"
        lines.append(line)

    return "\n".join(lines)


def format_manage_result(action: str, details: str) -> str:
    """Format a simple confirmation for manage actions.

    Args:
        action: The action that was performed (e.g. "deleted", "updated").
        details: Human-readable details about what changed.

    Returns:
        Plain-text confirmation string.
    """
    return f"\u2705 {action}: {details}"
