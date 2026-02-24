"""SQLite-backed memory store for Muninn."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from muninn.models import Memory, MemorySource, Project, ProjectStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DB_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "muninn")
_DEFAULT_DB_NAME = "muninn.db"

_CURRENT_SCHEMA_VERSION = 1

_SCHEMA_SQL = """\
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'idea', 'archived')),
    summary TEXT,
    github_repo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    content TEXT NOT NULL,
    depth INTEGER DEFAULT 1 CHECK(depth BETWEEN 0 AND 3),
    source TEXT DEFAULT 'conversation' CHECK(source IN ('conversation', 'github', 'manual')),
    superseded_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_tags (
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (memory_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    content=memories,
    content_rowid=rowid,
    tokenize='porter'
);

-- FTS sync triggers
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_db_path(db_path: str | None) -> str:
    """Determine the database file path.

    Priority:
      1. Explicit *db_path* argument
      2. ``MUNINN_DB_PATH`` environment variable
      3. ``~/.local/share/muninn/muninn.db``
    """
    if db_path is not None:
        return db_path
    env = os.environ.get("MUNINN_DB_PATH")
    if env:
        return env
    return os.path.join(_DEFAULT_DB_DIR, _DEFAULT_DB_NAME)


def _row_to_project(row: sqlite3.Row, *, memory_count: int = 0) -> Project:
    """Convert a sqlite3.Row from the projects table into a Project."""
    return Project(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        summary=row["summary"],
        github_repo=row["github_repo"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        memory_count=memory_count,
    )


def _row_to_memory(row: sqlite3.Row, *, tags: list[str] | None = None) -> Memory:
    """Convert a sqlite3.Row from the memories table into a Memory."""
    return Memory(
        id=row["id"],
        project_id=row["project_id"],
        content=row["content"],
        depth=row["depth"],
        source=row["source"],
        superseded_by=row["superseded_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tags=tags if tags is not None else [],
    )


def _fetch_tags_for_memory(conn: sqlite3.Connection, memory_id: str) -> list[str]:
    """Return all tags for a given memory id."""
    rows = conn.execute(
        "SELECT tag FROM memory_tags WHERE memory_id = ? ORDER BY tag",
        (memory_id,),
    ).fetchall()
    return [r["tag"] for r in rows]


def _fetch_tags_for_memories(
    conn: sqlite3.Connection, memory_ids: list[str]
) -> dict[str, list[str]]:
    """Batch-fetch tags for multiple memory ids."""
    if not memory_ids:
        return {}
    placeholders = ",".join("?" for _ in memory_ids)
    rows = conn.execute(
        f"SELECT memory_id, tag FROM memory_tags WHERE memory_id IN ({placeholders}) ORDER BY tag",
        memory_ids,
    ).fetchall()
    tags_map: dict[str, list[str]] = {}
    for r in rows:
        tags_map.setdefault(r["memory_id"], []).append(r["tag"])
    return tags_map


# ---------------------------------------------------------------------------
# MuninnStore
# ---------------------------------------------------------------------------

class MuninnStore:
    """SQLite-backed store for Muninn projects and memories."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = _resolve_db_path(db_path)

        # Ensure parent directory exists.
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialise schema on first run.
        with self._get_connection() as conn:
            conn.executescript(_SCHEMA_SQL)
            self._run_migrations(conn)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Open a new connection with ``Row`` factory and foreign keys enabled."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        """Apply any pending schema migrations."""
        row = conn.execute(
            "SELECT MAX(version) AS v FROM schema_version"
        ).fetchone()
        current_version: int = row["v"] if row and row["v"] is not None else 0

        # Future migrations go here as:
        #   if current_version < 2:
        #       conn.executescript(MIGRATION_V2_SQL)
        #       conn.execute("INSERT INTO schema_version (version) VALUES (2)")

        _ = current_version  # Suppress unused-variable lint.

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------

    def create_project(
        self,
        id: str,
        name: str,
        summary: str | None = None,
        github_repo: str | None = None,
    ) -> Project:
        """Insert a new project and return the created ``Project``."""
        now = _now_iso()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, summary, github_repo, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (id, name, summary, github_repo, now, now),
            )
        return Project(
            id=id,
            name=name,
            status=ProjectStatus.ACTIVE,
            summary=summary,
            github_repo=github_repo,
            created_at=now,
            updated_at=now,
            memory_count=0,
        )

    def get_project(self, id: str) -> Project | None:
        """Fetch a single project by *id*, or ``None`` if not found."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                return None

            count_row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM memories
                WHERE project_id = ? AND superseded_by IS NULL
                """,
                (id,),
            ).fetchone()
            memory_count = count_row["cnt"] if count_row else 0

        return _row_to_project(row, memory_count=memory_count)

    def list_projects(self, status: str | None = None) -> list[Project]:
        """Return all projects, optionally filtered by *status*.

        Each returned ``Project`` includes the count of active (non-superseded)
        memories as ``memory_count``.
        """
        with self._get_connection() as conn:
            if status is not None:
                rows = conn.execute(
                    """
                    SELECT p.*,
                           (SELECT COUNT(*) FROM memories m
                            WHERE m.project_id = p.id AND m.superseded_by IS NULL) AS memory_count
                    FROM projects p
                    WHERE p.status = ?
                    ORDER BY p.updated_at DESC
                    """,
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT p.*,
                           (SELECT COUNT(*) FROM memories m
                            WHERE m.project_id = p.id AND m.superseded_by IS NULL) AS memory_count
                    FROM projects p
                    ORDER BY p.updated_at DESC
                    """
                ).fetchall()

        return [
            _row_to_project(r, memory_count=r["memory_count"]) for r in rows
        ]

    def update_project(self, id: str, **kwargs: object) -> Project:
        """Update one or more fields on an existing project.

        Accepted keyword arguments: ``name``, ``status``, ``summary``,
        ``github_repo``.  Any field not provided is left unchanged.
        ``updated_at`` is always refreshed.

        Returns the updated ``Project``.
        Raises ``ValueError`` if the project does not exist.
        """
        allowed = {"name", "status", "summary", "github_repo"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if "status" in updates:
            from muninn.models import validate_project_status
            validate_project_status(str(updates["status"]))

        now = _now_iso()
        updates["updated_at"] = now

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        values = list(updates.values()) + [id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                values,
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Project {id!r} not found")

        project = self.get_project(id)
        if project is None:
            raise ValueError(f"Project {id!r} not found after update")
        return project

    # ------------------------------------------------------------------
    # Memory operations
    # ------------------------------------------------------------------

    def save_memory(
        self,
        project_id: str,
        content: str,
        depth: int = 1,
        source: str = MemorySource.CONVERSATION,
        tags: list[str] | None = None,
    ) -> Memory:
        """Create a new memory and return it.

        Generates a UUID for the memory id, inserts it with optional tags,
        and bumps the parent project's ``updated_at``.
        """
        from muninn.models import validate_memory_depth, validate_memory_source

        validate_memory_depth(depth)
        validate_memory_source(source)

        memory_id = uuid.uuid4().hex
        now = _now_iso()
        tag_list = tags or []

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, project_id, content, depth, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, project_id, content, depth, source, now, now),
            )

            for tag in tag_list:
                conn.execute(
                    "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (memory_id, tag),
                )

            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (now, project_id),
            )

        return Memory(
            id=memory_id,
            project_id=project_id,
            content=content,
            depth=depth,
            source=source,
            tags=tag_list,
            superseded_by=None,
            created_at=now,
            updated_at=now,
        )

    def recall(
        self,
        project_id: str | None = None,
        depth: int = 1,
        max_chars: int = 8000,
        tags: list[str] | None = None,
    ) -> dict[str, list[Memory]]:
        """Load memories grouped by project, respecting a character budget.

        Parameters
        ----------
        project_id:
            If given, only load memories for this project. Otherwise load
            memories for all **active** projects.
        depth:
            Maximum depth to include (0-3). Memories with ``depth <= depth``
            are included.
        max_chars:
            Character budget.  Memories are accumulated sorted by
            ``depth ASC, updated_at DESC``.  Once the budget is exceeded the
            remaining memories are dropped.
        tags:
            Optional tag filter — only memories having *all* listed tags are
            returned.

        Returns
        -------
        dict mapping project_id to its list of memories (ordered
        depth ASC, updated_at DESC).
        """
        with self._get_connection() as conn:
            # Determine which projects to load.
            if project_id is not None:
                project_ids = [project_id]
            else:
                rows = conn.execute(
                    "SELECT id FROM projects WHERE status = 'active'"
                ).fetchall()
                project_ids = [r["id"] for r in rows]

            if not project_ids:
                return {}

            placeholders = ",".join("?" for _ in project_ids)

            # Base query.
            query = f"""
                SELECT * FROM memories
                WHERE project_id IN ({placeholders})
                  AND superseded_by IS NULL
                  AND depth <= ?
            """
            params: list[object] = list(project_ids) + [depth]

            # Tag filter: require ALL tags present.
            if tags:
                for tag in tags:
                    query += """
                        AND id IN (
                            SELECT memory_id FROM memory_tags WHERE tag = ?
                        )
                    """
                    params.append(tag)

            query += " ORDER BY depth ASC, updated_at DESC"

            mem_rows = conn.execute(query, params).fetchall()

            # Batch-fetch tags.
            mem_ids = [r["id"] for r in mem_rows]
            tags_map = _fetch_tags_for_memories(conn, mem_ids)

        # Accumulate within character budget.
        result: dict[str, list[Memory]] = {}
        char_count = 0

        for r in mem_rows:
            content_len = len(r["content"])
            if char_count + content_len > max_chars:
                break
            char_count += content_len
            memory = _row_to_memory(r, tags=tags_map.get(r["id"], []))
            result.setdefault(memory.project_id, []).append(memory)

        return result

    def search(
        self,
        query: str,
        project_id: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Memory]:
        """Full-text search over non-superseded memories.

        Results are sorted by FTS5 relevance (``rank``), then ``updated_at``
        descending.
        """
        with self._get_connection() as conn:
            sql = """
                SELECT m.*
                FROM memories m
                JOIN memories_fts f ON m.rowid = f.rowid
                WHERE memories_fts MATCH ?
                  AND m.superseded_by IS NULL
            """
            # Wrap query in double-quotes to treat it as a literal phrase
            # and avoid FTS5 syntax errors from special characters.
            safe_query = '"' + query.replace('"', '""') + '"'
            params: list[object] = [safe_query]

            if project_id is not None:
                sql += " AND m.project_id = ?"
                params.append(project_id)

            if tags:
                for tag in tags:
                    sql += """
                        AND m.id IN (
                            SELECT memory_id FROM memory_tags WHERE tag = ?
                        )
                    """
                    params.append(tag)

            sql += " ORDER BY f.rank, m.updated_at DESC"

            rows = conn.execute(sql, params).fetchall()

            mem_ids = [r["id"] for r in rows]
            tags_map = _fetch_tags_for_memories(conn, mem_ids)

        return [
            _row_to_memory(r, tags=tags_map.get(r["id"], []))
            for r in rows
        ]

    def delete_memory(self, memory_id: str) -> bool:
        """Soft-delete a memory by setting ``superseded_by`` to ``'_deleted'``.

        Returns ``True`` if the memory existed and was updated.
        """
        now = _now_iso()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE memories
                SET superseded_by = '_deleted', updated_at = ?
                WHERE id = ? AND superseded_by IS NULL
                """,
                (now, memory_id),
            )
        return cursor.rowcount > 0

    def supersede_memory(self, old_id: str, new_id: str) -> bool:
        """Mark the old memory as superseded by the new memory.

        Returns ``True`` if the old memory existed and was updated.
        """
        now = _now_iso()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE memories
                SET superseded_by = ?, updated_at = ?
                WHERE id = ? AND superseded_by IS NULL
                """,
                (new_id, now, old_id),
            )
        return cursor.rowcount > 0
