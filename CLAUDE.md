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

Muninn is a cross-tool MCP (Model Context Protocol) memory server for solo builders. It provides persistent project memory that works across AI tools (Claude Code, Claude Desktop, Cursor, Codex, ChatGPT).

## Tech Stack

- **Language:** Python 3.11+
- **MCP SDK:** `mcp>=1.25,<2` (FastMCP)
- **Database:** SQLite with WAL mode, FTS5 full-text search, optional semantic search (fastembed)
- **Transport:** stdio + Streamable HTTP (with Bearer auth)
- **Build:** hatchling
- **Tests:** pytest

## Project Structure

```
src/muninn/
  __init__.py     # Package init
  models.py       # Frozen dataclasses: Project, Memory, validators
  store.py        # SQLite operations: CRUD, recall, search, FTS5, semantic
  formatter.py    # LLM-readable output formatting
  tools.py        # MCP tool functions (6 tools)
  server.py       # FastMCP entry point (stdio + HTTP, CLI args)
  auth.py         # Bearer token middleware for HTTP transport
  embedder.py     # Embedding engine (fastembed, graceful degradation)
tests/
  conftest.py             # Shared fixtures (tmp_path store)
  test_store.py           # Store unit tests
  test_tools.py           # Tool function tests
  test_server.py          # CLI parsing, MCP instance creation
  test_auth.py            # Bearer token middleware tests
  test_embedder.py        # Embedding engine unit tests
  test_semantic_search.py # Semantic search integration tests
  test_memory_quality.py  # Memory quality validation tests
  test_github_sync.py     # GitHub sync tests
docs/
  PRD.md          # Product Requirements Document
```

## Key Commands

```bash
# Install (editable with dev deps)
uv pip install -e ".[dev]"

# Run tests (239 tests)
.venv/bin/python -m pytest tests/ -v

# Run the MCP server (stdio — default)
.venv/bin/python -m muninn.server

# Run the MCP server (HTTP with auth)
MUNINN_API_KEY=secret .venv/bin/python -m muninn.server --transport http --port 8000
```

## Architecture Decisions

- **Frozen dataclasses** — All models are immutable (`@dataclass(frozen=True)`)
- **No FK on superseded_by** — `superseded_by` is a plain TEXT column (not a foreign key) because soft-delete uses the sentinel value `'_deleted'`
- **Character budget** — `max_chars` instead of token budget (no tokenizer dependency)
- **Module-level store** — `tools.py` uses a module-level `_store` initialized once by `server.py` via `init_store()`
- **Junction table for tags** — `memory_tags` table instead of JSON TEXT column for proper FTS indexing
- **FTS5 sync triggers** — INSERT/UPDATE/DELETE triggers keep `memories_fts` in sync automatically
- **WAL + busy_timeout** — Handles concurrent access from multiple MCP clients
- **Dual transport** — stdio for local tools, Streamable HTTP for remote (Claude Web/Mobile, ChatGPT)
- **Bearer token auth** — ASGI middleware on HTTP transport, key via `MUNINN_API_KEY` env var
- **Prefix ID matching** — `delete_memory`/`update_memory` accept 6-8 char prefixes, not just full UUIDs
- **Literal enum on action** — `muninn_manage` uses `Literal[...]` so JSON schema includes enum for LLM discovery
- **BLOB embeddings** — Semantic search stores float32 vectors as BLOB in `embedding` column (no sqlite-vec needed at <1000 memories)
- **Graceful degradation** — `embedder.py` returns `None` when fastembed is not installed; all code paths handle this
- **FTS5-first fallback** — `muninn_search` tries keyword search first, falls back to semantic only when FTS5 returns empty

## MCP Tools (6 total)

| Tool | Purpose |
|------|---------|
| `muninn_save` | Save memory to a project (auto-creates project if needed) |
| `muninn_recall` | Load project context with depth/char budget filtering |
| `muninn_search` | Full-text + semantic search across memories |
| `muninn_status` | List all projects with status overview |
| `muninn_manage` | Project/memory management (set_status, delete, update, create) |
| `muninn_sync` | Sync GitHub repo data (commits, issues, PRs) into memory |

## Depth System (Universal — works for any project type)

| Depth | Question | Use For |
|-------|----------|---------|
| 0 | "What is this?" | 10-second overview, always loaded |
| 1 | "To continue" | Resume work next session (default recall) |
| 2 | "To go deeper" | Dive into a specific area on request |
| 3 | "Just in case" | Archive, reference, raw data |

## Database

- **Location:** `~/.local/share/muninn/muninn.db` (default), override with `MUNINN_DB_PATH`
- **Schema version:** v3 (tracked in `schema_version` table). v2→v3 added `embedding BLOB` column.

## Coding Conventions

- All tool functions return strings (never raise — catch exceptions internally)
- Immutable patterns: frozen dataclasses, no mutation
- Small focused files (<400 lines each)
- Validators in models.py, not in store or tools
