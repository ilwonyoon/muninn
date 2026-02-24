"""Data models for the Muninn MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# String enum constants
# ---------------------------------------------------------------------------

class ProjectStatus:
    ACTIVE = "active"
    PAUSED = "paused"
    IDEA = "idea"
    ARCHIVED = "archived"

    _valid: frozenset[str] = frozenset({"active", "paused", "idea", "archived"})

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._valid

    @classmethod
    def values(cls) -> frozenset[str]:
        return cls._valid


class MemorySource:
    CONVERSATION = "conversation"
    GITHUB = "github"
    MANUAL = "manual"

    _valid: frozenset[str] = frozenset({"conversation", "github", "manual"})

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._valid

    @classmethod
    def values(cls) -> frozenset[str]:
        return cls._valid


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_project_status(status: str) -> None:
    """Raise ValueError if *status* is not a valid ProjectStatus."""
    if not ProjectStatus.is_valid(status):
        raise ValueError(
            f"Invalid project status {status!r}. "
            f"Must be one of: {sorted(ProjectStatus.values())}"
        )


def validate_memory_depth(depth: int) -> None:
    """Raise ValueError if *depth* is outside the 0-3 range."""
    if depth not in range(4):
        raise ValueError(
            f"Invalid memory depth {depth!r}. Must be an integer between 0 and 3."
        )


def validate_memory_source(source: str) -> None:
    """Raise ValueError if *source* is not a valid MemorySource."""
    if not MemorySource.is_valid(source):
        raise ValueError(
            f"Invalid memory source {source!r}. "
            f"Must be one of: {sorted(MemorySource.values())}"
        )


def validate_memory_content(content: str) -> None:
    """Raise ValueError if *content* is empty or whitespace-only."""
    if not content or not content.strip():
        raise ValueError("Memory content must not be empty or whitespace-only.")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Project:
    """Represents a tracked project in Muninn."""

    id: str
    name: str
    created_at: str
    updated_at: str
    status: str = ProjectStatus.ACTIVE
    summary: str | None = None
    github_repo: str | None = None
    # Not stored in DB — computed on read.
    memory_count: int = 0

    def __post_init__(self) -> None:
        validate_project_status(self.status)


@dataclass(frozen=True)
class Memory:
    """Represents a single memory entry attached to a project."""

    id: str
    project_id: str
    content: str
    created_at: str
    updated_at: str
    depth: int = 1
    source: str = MemorySource.CONVERSATION
    tags: tuple[str, ...] = field(default_factory=tuple)
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        validate_memory_depth(self.depth)
        validate_memory_source(self.source)
        for tag in self.tags:
            if not tag or not tag.strip():
                raise ValueError("Tags must be non-empty strings.")
