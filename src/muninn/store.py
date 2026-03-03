"""SQLite-backed memory store for Muninn (libSQL/Turso compatible)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import libsql_experimental as libsql

from muninn.models import Memory, MemorySource, Project, ProjectCategory, ProjectStatus, validate_memory_content, validate_tags

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DB_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "muninn")
_DEFAULT_DB_NAME = "muninn.db"

_CURRENT_SCHEMA_VERSION = 8

_UNSET = object()

# Schema SQL split into individual statements (libsql has no executescript).
_SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'idea', 'archived')),
        summary TEXT,
        github_repo TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        content TEXT NOT NULL,
        depth INTEGER DEFAULT 1 CHECK(depth BETWEEN 0 AND 3),
        source TEXT DEFAULT 'conversation' CHECK(source IN ('conversation', 'github', 'manual')),
        embedding BLOB DEFAULT NULL,
        superseded_by TEXT,
        parent_memory_id TEXT DEFAULT NULL,
        title TEXT DEFAULT NULL,
        resolved INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS memory_tags (
        memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
        tag TEXT NOT NULL,
        PRIMARY KEY (memory_id, tag)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag)",
    "CREATE INDEX IF NOT EXISTS idx_memories_project_id ON memories(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_memories_superseded_by ON memories(superseded_by)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
        content,
        title,
        content=memories,
        content_rowid=rowid,
        tokenize='porter'
    )""",
    # FTS sync triggers
    """CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
        INSERT INTO memories_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
    END""",
    """CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
        INSERT INTO memories_fts(memories_fts, rowid, content, title) VALUES('delete', old.rowid, old.content, old.title);
    END""",
    """CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
        INSERT INTO memories_fts(memories_fts, rowid, content, title) VALUES('delete', old.rowid, old.content, old.title);
        INSERT INTO memories_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
    END""",
    """CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    "INSERT OR IGNORE INTO schema_version (version) VALUES (6)",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with millisecond precision."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


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


def _execute_statements(conn: Any, statements: list[str]) -> None:
    """Execute a list of SQL statements sequentially (executescript replacement)."""
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)


def _execute_sql_script(conn: Any, script: str) -> None:
    """Split a SQL script by semicolons and execute each statement."""
    for stmt in script.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)


def _rows_to_dicts(cursor: Any) -> list[dict[str, Any]]:
    """Convert cursor results to list of dicts (row_factory replacement)."""
    if cursor.description is None:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _row_to_dict(cursor: Any) -> dict[str, Any] | None:
    """Convert single cursor result to dict."""
    if cursor.description is None:
        return None
    cols = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(cols, row)) if row else None


def _row_to_project(row: dict[str, Any], *, memory_count: int = 0) -> Project:
    """Convert a dict row from the projects table into a Project."""
    keys = row.keys()
    return Project(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        category=row["category"] if "category" in keys else ProjectCategory.PROJECT,
        summary=row["summary"],
        github_repo=row["github_repo"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        memory_count=memory_count,
    )


def _row_to_memory(row: dict[str, Any], *, tags: tuple[str, ...] | None = None) -> Memory:
    """Convert a dict row from the memories table into a Memory."""
    keys = row.keys()
    return Memory(
        id=row["id"],
        project_id=row["project_id"],
        content=row["content"],
        depth=row["depth"],
        source=row["source"],
        superseded_by=row["superseded_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tags=tags if tags is not None else (),
        category=row["category"] if "category" in keys else "status",
        parent_memory_id=row["parent_memory_id"] if "parent_memory_id" in keys else None,
        title=row["title"] if "title" in keys else None,
        resolved=bool(row["resolved"]) if "resolved" in keys else False,
    )


def _fetch_tags_for_memory(conn: Any, memory_id: str) -> tuple[str, ...]:
    """Return all tags for a given memory id."""
    rows = _rows_to_dicts(conn.execute(
        "SELECT tag FROM memory_tags WHERE memory_id = ? ORDER BY tag",
        (memory_id,),
    ))
    return tuple(r["tag"] for r in rows)


def _fetch_tags_for_memories(
    conn: Any, memory_ids: list[str]
) -> dict[str, tuple[str, ...]]:
    """Batch-fetch tags for multiple memory ids."""
    if not memory_ids:
        return {}
    placeholders = ",".join("?" for _ in memory_ids)
    rows = _rows_to_dicts(conn.execute(
        f"SELECT memory_id, tag FROM memory_tags WHERE memory_id IN ({placeholders}) ORDER BY tag",
        tuple(memory_ids),
    ))
    tags_map: dict[str, list[str]] = {}
    for r in rows:
        tags_map.setdefault(r["memory_id"], []).append(r["tag"])
    return {mid: tuple(tags) for mid, tags in tags_map.items()}


# ---------------------------------------------------------------------------
# MuninnStore
# ---------------------------------------------------------------------------

class MuninnStore:
    """SQLite-backed store for Muninn projects and memories (libSQL/Turso compatible)."""

    @staticmethod
    def default_db_path() -> str:
        """Return the resolved database path (without creating a store)."""
        return _resolve_db_path(None)

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = _resolve_db_path(db_path)
        self._turso_url = os.environ.get("TURSO_DATABASE_URL")
        self._turso_token = os.environ.get("TURSO_AUTH_TOKEN")

        # Ensure parent directory exists.
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialise schema on first run.
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            _execute_statements(conn, _SCHEMA_STATEMENTS)
            self._run_migrations(conn)
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _get_connection(self) -> Any:
        """Open a new connection with foreign keys enabled.

        If TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are set, uses embedded
        replica mode (local file as read cache, Turso cloud as source of truth).
        Otherwise, opens a plain local SQLite connection via libsql.
        """
        if self._turso_url and self._turso_token:
            conn = libsql.connect(
                self._db_path,
                sync_url=self._turso_url,
                auth_token=self._turso_token,
            )
            conn.sync()
        else:
            conn = libsql.connect(self._db_path)

        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _sync(self, conn: Any) -> None:
        """Sync embedded replica if in Turso mode (no-op for local)."""
        if self._turso_url and self._turso_token:
            conn.sync()

    # ------------------------------------------------------------------
    # Migrations
    # ------------------------------------------------------------------

    def _run_migrations(self, conn: Any) -> None:
        """Apply any pending schema migrations."""
        row = _row_to_dict(conn.execute(
            "SELECT MAX(version) AS v FROM schema_version"
        ))
        current_version: int = row["v"] if row and row["v"] is not None else 0

        if current_version < 2:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_project_id ON memories(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_superseded_by ON memories(superseded_by)")
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (2)")

        if current_version < 3:
            try:
                conn.execute(
                    "ALTER TABLE memories ADD COLUMN embedding BLOB DEFAULT NULL"
                )
            except Exception:
                pass
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (3)")

        # v4: add category column for content type classification.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()}

        if current_version < 4 or "category" not in cols:
            if "category" not in cols:
                try:
                    conn.execute(
                        "ALTER TABLE memories ADD COLUMN category TEXT DEFAULT 'context'"
                    )
                except Exception:
                    pass
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)"
            )
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (4)")

        # v5: expand category from 3 values to 8.
        if current_version < 5:
            conn.execute(
                "UPDATE memories SET category='vision' "
                "WHERE category='context' AND id IN "
                "(SELECT memory_id FROM memory_tags WHERE tag IN ('identity','overview','project'))"
            )
            conn.execute(
                "UPDATE memories SET category='product' "
                "WHERE category='context' AND id IN "
                "(SELECT memory_id FROM memory_tags WHERE tag IN ('decision','scope','principles','ux','design'))"
            )
            conn.execute("UPDATE memories SET category='status' WHERE category='context'")

            conn.execute(
                "UPDATE memories SET category='issue' "
                "WHERE category='code' AND id IN "
                "(SELECT memory_id FROM memory_tags WHERE tag IN ('bug'))"
            )
            conn.execute(
                "UPDATE memories SET category='implementation' "
                "WHERE category='code' AND id IN "
                "(SELECT memory_id FROM memory_tags WHERE tag IN ('config','milestone','development'))"
            )
            conn.execute(
                "UPDATE memories SET category='decision' "
                "WHERE category='code' AND id IN "
                "(SELECT memory_id FROM memory_tags WHERE tag IN ('decision'))"
            )
            conn.execute("UPDATE memories SET category='architecture' WHERE category='code'")

            conn.execute(
                "UPDATE memories SET category='implementation' "
                "WHERE category='reference' AND id IN "
                "(SELECT memory_id FROM memory_tags WHERE tag IN ('github','sync'))"
            )
            conn.execute("UPDATE memories SET category='insight' WHERE category='reference'")

            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (5)")

        if current_version < 6:
            for col_sql in [
                "ALTER TABLE memories ADD COLUMN parent_memory_id TEXT DEFAULT NULL",
                "ALTER TABLE memories ADD COLUMN title TEXT DEFAULT NULL",
                "ALTER TABLE memories ADD COLUMN resolved INTEGER DEFAULT 0",
            ]:
                try:
                    conn.execute(col_sql)
                except Exception:
                    pass
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_parent ON memories(parent_memory_id)"
            )
            for stmt in [
                "DROP TRIGGER IF EXISTS memories_ai",
                "DROP TRIGGER IF EXISTS memories_ad",
                "DROP TRIGGER IF EXISTS memories_au",
                "DROP TABLE IF EXISTS memories_fts",
                """CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content, title, content=memories, content_rowid=rowid, tokenize='porter'
                )""",
                """CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
                END""",
                """CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, title) VALUES('delete', old.rowid, old.content, old.title);
                END""",
                """CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content, title) VALUES('delete', old.rowid, old.content, old.title);
                    INSERT INTO memories_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
                END""",
                "INSERT INTO memories_fts(rowid, content, title) SELECT rowid, content, title FROM memories",
            ]:
                conn.execute(stmt)
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (6)")

        # v7: add category column to projects (project / personal).
        if current_version < 7:
            proj_cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()}
            if "category" not in proj_cols:
                try:
                    conn.execute(
                        "ALTER TABLE projects ADD COLUMN category TEXT DEFAULT 'project'"
                    )
                except Exception:
                    pass
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (7)")

        # v8: add project_summary_revisions table for diff tracking.
        if current_version < 8:
            conn.execute("""CREATE TABLE IF NOT EXISTS project_summary_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES projects(id),
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_summary_revisions_project "
                "ON project_summary_revisions(project_id, created_at)"
            )
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (8)")

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------

    def create_project(
        self,
        id: str,
        name: str,
        summary: str | None = None,
        github_repo: str | None = None,
        category: str = ProjectCategory.PROJECT,
    ) -> Project:
        """Insert a new project and return the created ``Project``."""
        from muninn.models import validate_project_category
        validate_project_category(category)
        now = _now_iso()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO projects (id, name, summary, github_repo, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (id, name, summary, github_repo, category, now, now),
            )
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()
        return Project(
            id=id,
            name=name,
            status=ProjectStatus.ACTIVE,
            category=category,
            summary=summary,
            github_repo=github_repo,
            created_at=now,
            updated_at=now,
            memory_count=0,
        )

    def get_project(self, id: str) -> Project | None:
        """Fetch a single project by *id*, or ``None`` if not found."""
        conn = self._get_connection()
        try:
            row = _row_to_dict(conn.execute(
                "SELECT * FROM projects WHERE id = ?", (id,)
            ))
            if row is None:
                return None

            count_row = _row_to_dict(conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM memories
                WHERE project_id = ? AND superseded_by IS NULL
                """,
                (id,),
            ))
            memory_count = count_row["cnt"] if count_row else 0
        finally:
            conn.close()

        return _row_to_project(row, memory_count=memory_count)

    def list_projects(self, status: str | None = None) -> list[Project]:
        """Return all projects, optionally filtered by *status*.

        Each returned ``Project`` includes the count of active (non-superseded)
        memories as ``memory_count``.
        """
        conn = self._get_connection()
        try:
            if status is not None:
                rows = _rows_to_dicts(conn.execute(
                    """
                    SELECT p.*,
                           (SELECT COUNT(*) FROM memories m
                            WHERE m.project_id = p.id AND m.superseded_by IS NULL) AS memory_count
                    FROM projects p
                    WHERE p.status = ?
                    ORDER BY p.updated_at DESC
                    """,
                    (status,),
                ))
            else:
                rows = _rows_to_dicts(conn.execute(
                    """
                    SELECT p.*,
                           (SELECT COUNT(*) FROM memories m
                            WHERE m.project_id = p.id AND m.superseded_by IS NULL) AS memory_count
                    FROM projects p
                    ORDER BY p.updated_at DESC
                    """
                ))
        finally:
            conn.close()

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
        allowed = {"name", "status", "summary", "github_repo", "category"}
        unknown = set(kwargs.keys()) - allowed
        if unknown:
            raise ValueError(
                f"Unknown fields: {sorted(unknown)}. "
                f"Allowed: {sorted(allowed)}"
            )
        updates = dict(kwargs)

        if "status" in updates:
            from muninn.models import validate_project_status
            validate_project_status(str(updates["status"]))

        if "category" in updates:
            from muninn.models import validate_project_category
            validate_project_category(str(updates["category"]))

        now = _now_iso()
        updates["updated_at"] = now

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        values = tuple(updates.values()) + (id,)

        conn = self._get_connection()
        try:
            # Save current summary to revisions before updating
            if "summary" in updates:
                old_row = _row_to_dict(conn.execute(
                    "SELECT summary FROM projects WHERE id = ?", (id,)
                ))
                if old_row is not None and old_row["summary"] is not None:
                    conn.execute(
                        "DELETE FROM project_summary_revisions WHERE project_id = ?",
                        (id,),
                    )
                    conn.execute(
                        "INSERT INTO project_summary_revisions (project_id, summary) VALUES (?, ?)",
                        (id, old_row["summary"]),
                    )

            cursor = conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                tuple(values),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Project {id!r} not found")
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()

        project = self.get_project(id)
        if project is None:
            raise ValueError(f"Project {id!r} not found after update")
        return project

    def get_summary_revision(self, project_id: str) -> dict | None:
        """Return the previous summary revision (before latest update)."""
        conn = self._get_connection()
        try:
            row = _row_to_dict(conn.execute(
                "SELECT summary, created_at FROM project_summary_revisions "
                "WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ))
        finally:
            conn.close()
        if row is None:
            return None
        return {"previous_summary": row["summary"], "updated_at": row["created_at"]}

    def clear_summary_revision(self, project_id: str) -> None:
        """Clear revision (user acknowledged changes)."""
        conn = self._get_connection()
        try:
            conn.execute(
                "DELETE FROM project_summary_revisions WHERE project_id = ?",
                (project_id,),
            )
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Memory operations
    # ------------------------------------------------------------------

    def save_memory(
        self,
        project_id: str,
        content: str,
        source: str = MemorySource.CONVERSATION,
        tags: list[str] | tuple[str, ...] | None = None,
    ) -> Memory:
        """Create a new memory and return it.

        Generates a UUID for the memory id, inserts it with optional tags,
        and bumps the parent project's ``updated_at``.
        """
        from muninn.models import validate_memory_source

        validate_memory_source(source)
        validate_memory_content(content)

        memory_id = uuid.uuid4().hex
        now = _now_iso()
        tag_list = validate_tags(tags)

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO memories (id, project_id, content, depth, source, category, parent_memory_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, project_id, content, 1, source, 'status', None, None, now, now),
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
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()

        return Memory(
            id=memory_id,
            project_id=project_id,
            content=content,
            depth=1,
            source=source,
            tags=tuple(tag_list),
            category='status',
            superseded_by=None,
            parent_memory_id=None,
            title=None,
            resolved=False,
            created_at=now,
            updated_at=now,
        )

    def recall(
        self,
        project_id: str | None = None,
        max_chars: int = 50000,
        tags: list[str] | None = None,
    ) -> tuple[dict[str, list[Memory]], dict[str, int]]:
        """Load memories grouped by project, respecting a character budget.

        Parameters
        ----------
        project_id:
            If given, only load memories for this project. Otherwise load
            memories for all **active** projects.
        max_chars:
            Character budget.  Memories are accumulated sorted by
            ``updated_at DESC``.  Once the budget is exceeded the
            remaining memories are dropped.
        tags:
            Optional tag filter — only memories having *all* listed tags are
            returned.

        Returns
        -------
        Tuple of (memories_by_project, stats) where memories_by_project maps
        project_id to its list of memories (ordered updated_at DESC)
        and stats is a dict with keys: chars_loaded, chars_budget,
        memories_loaded, memories_dropped.
        """
        conn = self._get_connection()
        try:
            # Determine which projects to load.
            if project_id is not None:
                project_ids = [project_id]
            else:
                rows = _rows_to_dicts(conn.execute(
                    "SELECT id FROM projects WHERE status = 'active'"
                ))
                project_ids = [r["id"] for r in rows]

            if not project_ids:
                return {}, {"chars_loaded": 0, "chars_budget": max_chars, "memories_loaded": 0, "memories_dropped": 0}

            placeholders = ",".join("?" for _ in project_ids)

            # Base query.
            query = f"""
                SELECT * FROM memories
                WHERE project_id IN ({placeholders})
                  AND superseded_by IS NULL
            """
            params: list[object] = list(project_ids)

            # Tag filter: require ALL tags present.
            if tags:
                for tag in tags:
                    query += """
                        AND id IN (
                            SELECT memory_id FROM memory_tags WHERE tag = ?
                        )
                    """
                    params.append(tag)

            query += " ORDER BY updated_at DESC"

            mem_rows = _rows_to_dicts(conn.execute(query, tuple(params)))

            # Batch-fetch tags.
            mem_ids = [r["id"] for r in mem_rows]
            tags_map = _fetch_tags_for_memories(conn, mem_ids)
        finally:
            conn.close()

        # Accumulate within character budget.
        result: dict[str, list[Memory]] = {}
        char_count = 0
        loaded_count = 0
        dropped_count = 0

        for r in mem_rows:
            content_len = len(r["content"])
            if char_count + content_len > max_chars:
                dropped_count += 1
                continue  # count ALL dropped, don't break
            char_count += content_len
            loaded_count += 1
            memory = _row_to_memory(r, tags=tags_map.get(r["id"], ()))
            result.setdefault(memory.project_id, []).append(memory)

        stats = {
            "chars_loaded": char_count,
            "chars_budget": max_chars,
            "memories_loaded": loaded_count,
            "memories_dropped": dropped_count,
        }

        return result, stats

    def search(
        self,
        query: str,
        project_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        """Full-text search over non-superseded memories.

        Results are sorted by FTS5 relevance (``rank``), then ``updated_at``
        descending.
        """
        conn = self._get_connection()
        try:
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
            sql += " LIMIT ?"
            params.append(limit)

            rows = _rows_to_dicts(conn.execute(sql, tuple(params)))

            mem_ids = [r["id"] for r in rows]
            tags_map = _fetch_tags_for_memories(conn, mem_ids)
        finally:
            conn.close()

        return [
            _row_to_memory(r, tags=tags_map.get(r["id"], ()))
            for r in rows
        ]

    def _resolve_memory_id(self, conn: Any, memory_id: str) -> str | None:
        """Resolve a full or prefix memory ID to the actual full ID.

        If *memory_id* is an exact match, return it directly.  Otherwise treat
        it as a prefix and return the unique match.  Returns ``None`` when no
        match or ambiguous (multiple matches).
        """
        # Try exact match first.
        row = _row_to_dict(conn.execute(
            "SELECT id FROM memories WHERE id = ?", (memory_id,)
        ))
        if row is not None:
            return row["id"]

        # Prefix match — escape LIKE metacharacters to prevent logic injection.
        escaped = memory_id.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = _rows_to_dicts(conn.execute(
            "SELECT id FROM memories WHERE id LIKE ? ESCAPE '\\'",
            (escaped + "%",),
        ))
        if len(rows) == 1:
            return rows[0]["id"]
        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Soft-delete a memory by setting ``superseded_by`` to ``'_deleted'``.

        Accepts full UUIDs or unique prefixes (e.g. first 6-8 chars).
        Returns ``True`` if the memory existed and was updated.
        """
        now = _now_iso()
        conn = self._get_connection()
        try:
            resolved = self._resolve_memory_id(conn, memory_id)
            if resolved is None:
                return False
            cursor = conn.execute(
                """
                UPDATE memories
                SET superseded_by = '_deleted', updated_at = ?
                WHERE id = ? AND superseded_by IS NULL
                """,
                (now, resolved),
            )
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()
        return cursor.rowcount > 0

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        tags: list[str] | tuple[str, ...] | None = None,
    ) -> "Memory | None":
        """Update an existing memory's content and/or tags.

        Accepts full UUIDs or unique prefixes (e.g. first 6-8 chars).
        Only non-None parameters are updated. Returns the updated Memory,
        or None if the memory was not found or is superseded.
        """
        now = _now_iso()
        conn = self._get_connection()
        try:
            # Resolve prefix to full ID
            resolved_id = self._resolve_memory_id(conn, memory_id)
            if resolved_id is None:
                return None
            memory_id = resolved_id

            # Check memory exists and is not superseded
            row = _row_to_dict(conn.execute(
                "SELECT * FROM memories WHERE id = ? AND superseded_by IS NULL",
                (memory_id,),
            ))
            if row is None:
                return None

            # Build update SET clause
            updates: dict[str, object] = {"updated_at": now}
            if content is not None:
                validate_memory_content(content)
                updates["content"] = content

            set_clause = ", ".join(f"{col} = ?" for col in updates)
            values = tuple(updates.values()) + (memory_id,)
            conn.execute(
                f"UPDATE memories SET {set_clause} WHERE id = ?",
                values,
            )

            # Update tags if provided
            if tags is not None:
                validated_tags = validate_tags(tags)
                conn.execute(
                    "DELETE FROM memory_tags WHERE memory_id = ?",
                    (memory_id,),
                )
                for tag in validated_tags:
                    conn.execute(
                        "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                        (memory_id, tag),
                    )

            # Bump project updated_at
            conn.execute(
                "UPDATE projects SET updated_at = ? WHERE id = ?",
                (now, row["project_id"]),
            )

            conn.commit()
            self._sync(conn)

            # Re-fetch to get final state
            updated_row = _row_to_dict(conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            ))
            final_tags = _fetch_tags_for_memory(conn, memory_id)
        finally:
            conn.close()

        return _row_to_memory(updated_row, tags=final_tags)

    def supersede_memory(self, old_id: str, new_id: str) -> bool:
        """Mark the old memory as superseded by the new memory.

        Returns ``True`` if the old memory existed and was updated.
        """
        now = _now_iso()
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                UPDATE memories
                SET superseded_by = ?, updated_at = ?
                WHERE id = ? AND superseded_by IS NULL
                """,
                (new_id, now, old_id),
            )
            conn.commit()
            self._sync(conn)
        finally:
            conn.close()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Dashboard queries
    # ------------------------------------------------------------------

    def get_memory(self, memory_id: str) -> Memory | None:
        """Fetch a single memory by full or prefix ID, including tags."""
        conn = self._get_connection()
        try:
            resolved = self._resolve_memory_id(conn, memory_id)
            if resolved is None:
                return None
            row = _row_to_dict(conn.execute(
                "SELECT * FROM memories WHERE id = ?", (resolved,)
            ))
            if row is None:
                return None
            tags = _fetch_tags_for_memory(conn, resolved)
        finally:
            conn.close()
        return _row_to_memory(row, tags=tags)

    def get_all_tags(self, project_id: str | None = None) -> list[str]:
        """Return all distinct tags, optionally scoped to a project."""
        conn = self._get_connection()
        try:
            if project_id is not None:
                rows = _rows_to_dicts(conn.execute(
                    """
                    SELECT DISTINCT mt.tag FROM memory_tags mt
                    JOIN memories m ON mt.memory_id = m.id
                    WHERE m.project_id = ? AND m.superseded_by IS NULL
                    ORDER BY mt.tag
                    """,
                    (project_id,),
                ))
            else:
                rows = _rows_to_dicts(conn.execute(
                    """
                    SELECT DISTINCT mt.tag FROM memory_tags mt
                    JOIN memories m ON mt.memory_id = m.id
                    WHERE m.superseded_by IS NULL
                    ORDER BY mt.tag
                    """
                ))
        finally:
            conn.close()
        return [r["tag"] for r in rows]

    def get_supersede_chain(self, memory_id: str) -> list[Memory]:
        """Return the full supersede chain for a memory (oldest first).

        Traces backward (who did this memory supersede?) and forward
        (who superseded this memory?) to build the complete chain.
        """
        conn = self._get_connection()
        try:
            resolved = self._resolve_memory_id(conn, memory_id)
            if resolved is None:
                return []

            # Collect all related memory IDs by walking the chain.
            visited: set[str] = set()
            queue = [resolved]

            while queue:
                current = queue.pop()
                if current in visited or current == "_deleted":
                    continue
                visited.add(current)

                row = _row_to_dict(conn.execute(
                    "SELECT id, superseded_by FROM memories WHERE id = ?",
                    (current,),
                ))
                if row is None:
                    continue

                # Forward: this memory was superseded by another.
                if row["superseded_by"] and row["superseded_by"] != "_deleted":
                    queue.append(row["superseded_by"])

                # Backward: find memories that were superseded by this one.
                back_rows = _rows_to_dicts(conn.execute(
                    "SELECT id FROM memories WHERE superseded_by = ?",
                    (current,),
                ))
                for br in back_rows:
                    queue.append(br["id"])

            if not visited:
                return []

            # Fetch full memory objects for all chain members.
            placeholders = ",".join("?" for _ in visited)
            rows = _rows_to_dicts(conn.execute(
                f"SELECT * FROM memories WHERE id IN ({placeholders}) ORDER BY created_at ASC",
                tuple(visited),
            ))
            mem_ids = [r["id"] for r in rows]
            tags_map = _fetch_tags_for_memories(conn, mem_ids)
        finally:
            conn.close()

        return [
            _row_to_memory(r, tags=tags_map.get(r["id"], ()))
            for r in rows
        ]

    def get_dashboard_stats(self) -> dict[str, int]:
        """Return aggregate statistics for the dashboard overview."""
        conn = self._get_connection()
        try:
            proj_row = _row_to_dict(conn.execute(
                "SELECT COUNT(*) AS cnt FROM projects"
            ))
            active_row = _row_to_dict(conn.execute(
                "SELECT COUNT(*) AS cnt FROM projects WHERE status = 'active'"
            ))
            mem_row = _row_to_dict(conn.execute(
                "SELECT COUNT(*) AS cnt FROM memories WHERE superseded_by IS NULL"
            ))
            stale_row = _row_to_dict(conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM projects
                WHERE status = 'active'
                  AND updated_at < datetime('now', '-7 days')
                """,
            ))
        finally:
            conn.close()

        return {
            "total_projects": proj_row["cnt"] if proj_row else 0,
            "active_projects": active_row["cnt"] if active_row else 0,
            "total_memories": mem_row["cnt"] if mem_row else 0,
            "stale_projects": stale_row["cnt"] if stale_row else 0,
        }
