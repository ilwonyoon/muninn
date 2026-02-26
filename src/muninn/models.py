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


class MemoryCategory:
    # Exploration
    BRAINSTORM = "brainstorm"
    # Product axis
    VISION = "vision"
    PRODUCT = "product"
    INSIGHT = "insight"
    STATUS = "status"
    # Engineering axis
    ARCHITECTURE = "architecture"
    DECISION = "decision"
    IMPLEMENTATION = "implementation"
    ISSUE = "issue"

    _valid: frozenset[str] = frozenset({
        "brainstorm",
        "vision", "product", "insight", "status",
        "architecture", "decision", "implementation", "issue",
    })

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


def validate_memory_category(category: str) -> None:
    """Raise ValueError if *category* is not a valid MemoryCategory."""
    if not MemoryCategory.is_valid(category):
        raise ValueError(
            f"Invalid memory category {category!r}. "
            f"Must be one of: {sorted(MemoryCategory.values())}"
        )


def validate_memory_content(content: str) -> None:
    """Raise ValueError if *content* is empty or whitespace-only."""
    if not content or not content.strip():
        raise ValueError("Memory content must not be empty or whitespace-only.")


def validate_parent_depth(parent_depth: int, child_depth: int) -> None:
    """Raise ValueError if parent depth is not strictly less than child depth."""
    if parent_depth >= child_depth:
        raise ValueError(
            f"Parent depth ({parent_depth}) must be strictly less than "
            f"child depth ({child_depth})."
        )


def validate_tags(tags: list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalise and validate tags, returning a clean list.

    Handles common LLM mistakes:
      - String instead of list: ``"bug,auth"`` → ``["bug", "auth"]``
      - Single string: ``"bug"`` → ``["bug"]``
      - None → ``[]``

    Raises ValueError for empty/whitespace tags after splitting.
    """
    if tags is None:
        return []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    result = list(tags)
    for tag in result:
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError("Tags must be non-empty strings.")
    return result


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
    depth: int = 2
    source: str = MemorySource.CONVERSATION
    tags: tuple[str, ...] = field(default_factory=tuple)
    category: str = MemoryCategory.STATUS
    superseded_by: str | None = None
    parent_memory_id: str | None = None
    title: str | None = None
    resolved: bool = False

    def __post_init__(self) -> None:
        validate_memory_depth(self.depth)
        validate_memory_source(self.source)
        validate_memory_category(self.category)
        for tag in self.tags:
            if not tag or not tag.strip():
                raise ValueError("Tags must be non-empty strings.")
