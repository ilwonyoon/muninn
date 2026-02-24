# Muninn — Project Instructions

## What This Is

Muninn is a cross-tool MCP (Model Context Protocol) memory server for solo builders. It provides persistent project memory that works across AI tools (Claude Code, Claude Desktop, Cursor, Codex, ChatGPT).

## Tech Stack

- **Language:** Python 3.11+
- **MCP SDK:** `mcp>=1.25,<2` (FastMCP)
- **Database:** SQLite with WAL mode, FTS5 full-text search
- **Transport:** stdio (Phase 1)
- **Build:** hatchling
- **Tests:** pytest

## Project Structure

```
src/muninn/
  __init__.py     # Package init
  models.py       # Frozen dataclasses: Project, Memory, validators
  store.py        # SQLite operations: CRUD, recall, search, FTS5
  formatter.py    # LLM-readable output formatting
  tools.py        # MCP tool functions (5 tools)
  server.py       # FastMCP entry point
tests/
  conftest.py     # Shared fixtures (tmp_path store)
  test_store.py   # Store unit tests
  test_tools.py   # Tool function tests
docs/
  PRD.md          # Product Requirements Document
```

## Key Commands

```bash
# Install (editable with dev deps)
uv pip install -e ".[dev]"

# Run tests
.venv/bin/python -m pytest tests/ -v

# Run the MCP server (stdio)
.venv/bin/python -m muninn.server
```

## Architecture Decisions

- **Frozen dataclasses** — All models are immutable (`@dataclass(frozen=True)`)
- **No FK on superseded_by** — `superseded_by` is a plain TEXT column (not a foreign key) because soft-delete uses the sentinel value `'_deleted'`
- **Character budget** — `max_chars` instead of token budget (no tokenizer dependency)
- **Module-level store** — `tools.py` uses a module-level `_store` initialized once by `server.py` via `init_store()`
- **Junction table for tags** — `memory_tags` table instead of JSON TEXT column for proper FTS indexing
- **FTS5 sync triggers** — INSERT/UPDATE/DELETE triggers keep `memories_fts` in sync automatically
- **WAL + busy_timeout** — Handles concurrent access from multiple MCP clients

## MCP Tools (5 total)

| Tool | Purpose |
|------|---------|
| `muninn_save` | Save memory to a project (auto-creates project if needed) |
| `muninn_recall` | Load project context with depth/char budget filtering |
| `muninn_search` | Full-text search across memories |
| `muninn_status` | List all projects with status overview |
| `muninn_manage` | Project/memory management (set_status, delete, update, create) |

## Depth System

| Depth | Label | Use For |
|-------|-------|---------|
| 0 | summary | Project overview, always loaded |
| 1 | context | Key decisions, default recall level |
| 2 | detailed | Implementation details |
| 3 | full | Complete history, debug info |

## Database

- **Location:** `~/.local/share/muninn/muninn.db` (default), override with `MUNINN_DB_PATH`
- **Schema version:** Tracked in `schema_version` table for future migrations

## Coding Conventions

- All tool functions return strings (never raise — catch exceptions internally)
- Immutable patterns: frozen dataclasses, no mutation
- Small focused files (<400 lines each)
- Validators in models.py, not in store or tools
