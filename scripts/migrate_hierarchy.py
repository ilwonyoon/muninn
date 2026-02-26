#!/usr/bin/env python3
"""One-shot migration: reorganize existing memories into L0/L1/L2 hierarchy.

Adds title, resolved columns if missing, then assigns parent_memory_id
and titles to existing memories based on their category and content.

Run:  python scripts/migrate_hierarchy.py [--dry-run]
"""

import os
import re
import sqlite3
import sys

DB_PATH = os.environ.get(
    "MUNINN_DB_PATH",
    os.path.expanduser("~/.local/share/muninn/muninn.db"),
)

DRY_RUN = "--dry-run" in sys.argv


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_columns(conn: sqlite3.Connection) -> None:
    """Add title and resolved columns if they don't exist."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(memories)")}
    if "title" not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN title TEXT DEFAULT NULL")
        print("  Added 'title' column")
    if "resolved" not in cols:
        conn.execute("ALTER TABLE memories ADD COLUMN resolved INTEGER DEFAULT 0")
        print("  Added 'resolved' column")


def extract_title(content: str) -> str:
    """Extract a clean title from content (first meaningful line, <=60 chars)."""
    for line in content.split("\n"):
        line = line.strip()
        # Skip empty lines and markdown headers
        line = re.sub(r"^#{1,4}\s*", "", line)
        line = line.strip()
        if not line:
            continue
        if len(line) > 60:
            return line[:57] + "..."
        return line
    return content[:57] + "..." if len(content) > 60 else content


# ── Per-project hierarchy mapping ──────────────────────────────────────────
# For each project, define which L1 topic buckets exist and how to assign
# existing memories to them.

# Category → L1 topic mapping per project
PROJECT_TOPICS = {
    "Muninn": {
        # L1 topic titles (will be created or matched)
        "topics": {
            "Architecture & Stack": ["architecture", "implementation"],
            "Design Decisions": ["decision"],
            "Issues & Bugs": ["issue"],
            "Insights & Research": ["insight", "vision"],
            "Status & Progress": ["status"],
        },
    },
    "Aido": {
        "topics": {
            "Product Strategy": ["product"],
            "Market Insights": ["insight"],
            "Technical Decisions": ["decision"],
        },
    },
    "Focus-knob": {
        "topics": {
            "Product & Pricing": ["product"],
            "Implementation": ["implementation"],
        },
    },
    "Slow-letter": {
        "topics": {
            "Product Design": ["product"],
            "Technical Decisions": ["decision"],
            "Architecture": ["architecture"],
        },
    },
}


def migrate_project(conn: sqlite3.Connection, project_id: str, project_name: str) -> int:
    """Migrate a single project's memories into hierarchy. Returns count of changes."""
    changes = 0

    # Get all active memories for this project
    mems = conn.execute(
        """SELECT id, depth, category, content, parent_memory_id, title
           FROM memories
           WHERE project_id = ? AND superseded_by IS NULL
           ORDER BY depth, created_at""",
        (project_id,),
    ).fetchall()

    if not mems:
        return 0

    # Step 1: Set titles for all memories that don't have one
    for m in mems:
        if m["title"] is None:
            title = extract_title(m["content"])
            if not DRY_RUN:
                conn.execute(
                    "UPDATE memories SET title = ? WHERE id = ?",
                    (title, m["id"]),
                )
            print(f"    title [{m['id'][:8]}] → {title}")
            changes += 1

    # Step 2: Find L0 (vision) memory — should already exist
    l0_mems = [m for m in mems if m["depth"] == 0]
    if not l0_mems:
        print(f"    WARNING: No L0 memory found for {project_name}")
        return changes

    l0_id = l0_mems[0]["id"]

    # Step 3: Get topic config for this project
    config = PROJECT_TOPICS.get(project_name)
    if not config:
        # Generic: all L1 memories become children of L0, L2 stay as-is
        l1_mems = [m for m in mems if m["depth"] == 1 and m["parent_memory_id"] is None]
        for m in l1_mems:
            if not DRY_RUN:
                conn.execute(
                    "UPDATE memories SET parent_memory_id = ? WHERE id = ?",
                    (l0_id, m["id"]),
                )
            print(f"    parent [{m['id'][:8]}] L1 → L0 [{l0_id[:8]}]")
            changes += 1

        l2_mems = [m for m in mems if m["depth"] == 2 and m["parent_memory_id"] is None]
        # Attach L2 to the first matching L1 by category, or first L1
        for m in l2_mems:
            # Find an L1 with matching category
            parent = next(
                (l1 for l1 in l1_mems if l1["category"] == m["category"]),
                l1_mems[0] if l1_mems else None,
            )
            if parent:
                if not DRY_RUN:
                    conn.execute(
                        "UPDATE memories SET parent_memory_id = ? WHERE id = ?",
                        (parent["id"], m["id"]),
                    )
                print(f"    parent [{m['id'][:8]}] L2 → L1 [{parent['id'][:8]}]")
                changes += 1
        return changes

    # Step 4: For configured projects, create topic-based L1 grouping
    topics = config["topics"]

    # Build category → topic name mapping
    cat_to_topic: dict[str, str] = {}
    for topic_name, categories in topics.items():
        for cat in categories:
            cat_to_topic[cat] = topic_name

    # Group L1 memories by topic
    topic_to_l1: dict[str, list[dict]] = {}
    l1_mems = [m for m in mems if m["depth"] == 1 and m["parent_memory_id"] is None]
    for m in l1_mems:
        topic = cat_to_topic.get(m["category"], "Other")
        topic_to_l1.setdefault(topic, []).append(m)

    # For each L1 memory, set parent to L0
    for m in l1_mems:
        if not DRY_RUN:
            conn.execute(
                "UPDATE memories SET parent_memory_id = ? WHERE id = ?",
                (l0_id, m["id"]),
            )
        print(f"    parent [{m['id'][:8]}] L1 → L0 [{l0_id[:8]}]")
        changes += 1

    # For each L2 memory, find best L1 parent by category match
    l2_mems = [m for m in mems if m["depth"] == 2 and m["parent_memory_id"] is None]
    for m in l2_mems:
        topic = cat_to_topic.get(m["category"])
        candidates = topic_to_l1.get(topic, []) if topic else []
        if not candidates:
            # Fallback: first L1
            candidates = l1_mems[:1]
        if candidates:
            parent = candidates[0]
            if not DRY_RUN:
                conn.execute(
                    "UPDATE memories SET parent_memory_id = ? WHERE id = ?",
                    (parent["id"], m["id"]),
                )
            print(f"    parent [{m['id'][:8]}] L2 → L1 [{parent['id'][:8]}]")
            changes += 1

    return changes


def main() -> None:
    print(f"DB: {DB_PATH}")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print()

    conn = connect()

    # Ensure schema has required columns
    print("Checking schema...")
    ensure_columns(conn)
    conn.commit()

    # Get all projects
    projects = conn.execute("SELECT id, name FROM projects WHERE status = 'active'").fetchall()
    print(f"\nFound {len(projects)} active projects\n")

    total_changes = 0
    for p in projects:
        print(f"Project: {p['name']}")
        changes = migrate_project(conn, p["id"], p["name"])
        total_changes += changes
        print(f"  → {changes} changes\n")

    if not DRY_RUN:
        conn.commit()
        print(f"Committed {total_changes} total changes.")
    else:
        print(f"DRY RUN: {total_changes} changes would be made.")

    conn.close()


if __name__ == "__main__":
    main()
