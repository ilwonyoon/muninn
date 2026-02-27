# Muninn — Project Instructions

## Feedback Persona

When reviewing designs, giving feedback, or evaluating decisions in this project, adopt the perspective of a **senior AI Research Engineer with 10+ years of experience at Anthropic/DeepMind-level labs**.

This means:
- **Challenge assumptions first** — Ask "why might this be wrong?" before "how to improve"
- **Be direct, not diplomatic** — Skip "great approach!" and go straight to the analysis
- **Cite reasoning** — Back claims with technical principles, research patterns, or empirical evidence, not intuition
- **Name the tradeoffs honestly** — Every design choice has a cost. State it.
- **Distinguish shipping vs ideal** — "Ship this now, but here's what the data will tell you to change"
- **Use precise language** — "orthogonal", "arbitrary", "temperature-dependent" over "nice", "interesting", "could be better"

What this persona does NOT do:
- Sugarcoat problems to avoid discomfort
- Default to "looks good" without evidence
- Add qualifiers like "just my opinion" or "you might consider"

## What This Is

Muninn is a personal MCP (Model Context Protocol) memory server. Persistent project memory across local AI tools — one user, multiple clients.

**Clients:** Claude Code CLI, Claude Desktop, ChatGPT Mac App, Codex CLI

## Tech Stack

- **Language:** Python 3.11+
- **MCP SDK:** `mcp>=1.25,<2` (FastMCP)
- **Database:** SQLite with WAL mode, FTS5 full-text search
- **Transport:** stdio (primary) + Streamable HTTP (dashboard only)
- **Dashboard:** Next.js 16 + React 19 + Tailwind 4 (localhost)
- **Build:** hatchling
- **Tests:** pytest

## Project Structure

```
src/muninn/
  __init__.py     # Package init
  models.py       # Frozen dataclasses: Project, Memory
  store.py        # SQLite operations: CRUD, recall, search, FTS5
  formatter.py    # LLM-readable output formatting
  tools.py        # MCP tool functions (6 tools)
  server.py       # FastMCP entry point (stdio + HTTP, CLI args)
  auth.py         # Bearer token middleware for HTTP transport
  api.py          # REST API routes for dashboard
  github_sync.py  # GitHub repo sync (commits, issues, PRs)
tests/
  conftest.py            # Shared fixtures (tmp_path store)
  test_store.py          # Store unit tests
  test_tools.py          # Tool function tests
  test_server.py         # CLI parsing, MCP instance creation
  test_auth.py           # Bearer token middleware tests
  test_api.py            # REST API endpoint tests
  test_memory_quality.py # Memory quality tests
  test_github_sync.py    # GitHub sync tests
web/                     # Next.js dashboard (localhost:3000 → API proxy to :8000)
docs/
  PRD.md                 # Product Requirements Document
```

## Key Commands

```bash
# Install (editable with dev deps)
uv pip install -e ".[dev]"

# Run tests (244 tests)
.venv/bin/python -m pytest tests/ -v

# Run the MCP server (stdio — default, used by all 4 clients)
.venv/bin/python -m muninn.server

# Run with dashboard API (localhost only)
.venv/bin/python -m muninn.server --transport http --port 8000

# Run dashboard frontend (separate terminal)
cd web && npm run dev
```

## Architecture Decisions

- **Frozen dataclasses** — All models are immutable (`@dataclass(frozen=True)`)
- **No FK on superseded_by** — `superseded_by` is a plain TEXT column (not a foreign key) because soft-delete uses the sentinel value `'_deleted'`
- **Character budget** — `max_chars` instead of token budget (no tokenizer dependency)
- **Module-level store** — `tools.py` uses a module-level `_store` initialized once by `server.py` via `init_store()`
- **Junction table for tags** — `memory_tags` table instead of JSON TEXT column for proper FTS indexing
- **FTS5 sync triggers** — INSERT/UPDATE/DELETE triggers keep `memories_fts` in sync automatically
- **WAL + busy_timeout** — Handles concurrent access from multiple MCP clients
- **Dual transport** — stdio for AI clients, Streamable HTTP for dashboard REST API (localhost)
- **Bearer token auth** — ASGI middleware on HTTP transport, key via `MUNINN_API_KEY` env var
- **Prefix ID matching** — `delete_memory`/`update_memory` accept 6-8 char prefixes, not just full UUIDs
- **Literal enum on action** — `muninn_manage` uses `Literal[...]` so JSON schema includes enum for LLM discovery

## MCP Tools (6 total)

| Tool | Purpose |
|------|---------|
| `muninn_save` | Save memory to a project (content + optional tags) |
| `muninn_recall` | Load project memories (chronological, char budget) |
| `muninn_search` | FTS5 full-text search across memories |
| `muninn_status` | List all projects with status overview |
| `muninn_manage` | Project/memory management (set_status, delete, update, create) |
| `muninn_sync` | Sync GitHub repo data (commits, issues, PRs) into memory |

## Memory Philosophy

Muninn is a **bridge between AI clients**, not technical documentation.

**Save:** thoughts, decisions, direction changes, what's next, product-level summaries.
**Don't save:** code changes, test results, function names, implementation details (git handles that).

Project summaries should describe what the project does from a **user/product perspective**, not an engineer perspective.

## Project Status

| Status | Meaning |
|--------|---------|
| `active` | Currently in progress |
| `paused` | Temporarily on hold |
| `idea` | Interest, exploration, not yet started |
| `archived` | Completed / past project |

## Database

- **Location:** `~/.local/share/muninn/muninn.db` (default), override with `MUNINN_DB_PATH`
- **Schema version:** v3 (tracked in `schema_version` table). v2→v3 added `embedding BLOB` column.

## Coding Conventions

- All tool functions return strings (never raise — catch exceptions internally)
- Immutable patterns: frozen dataclasses, no mutation
- Small focused files (<400 lines each)
- DB schema unchanged — deprecated columns (depth, category, parent_memory_id) remain but are ignored by code
