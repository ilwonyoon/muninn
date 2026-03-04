# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

# Run tests (250 tests)
.venv/bin/python -m pytest tests/ -v

# Run a single test file
.venv/bin/python -m pytest tests/test_tools.py -v

# Run a single test
.venv/bin/python -m pytest tests/test_tools.py::TestMuninnSave::test_save_auto_creates_project -v

# Run the MCP server (stdio — default, used by all 4 clients)
.venv/bin/python -m muninn.server

# Run with dashboard API (localhost only)
.venv/bin/python -m muninn.server --transport http --port 8000

# Run dashboard frontend (separate terminal)
cd web && npm run dev

# Reset all data (wipe memories, tags, revisions, clear summaries)
.venv/bin/python -m muninn.server --reset

# Restart the HTTP server (managed by launchd)
launchctl kickstart -k gui/$(id -u)/com.muninn.server
```

## Architecture Decisions

- **Frozen dataclasses** — All models are immutable (`@dataclass(frozen=True)`)
- **No FK on superseded_by** — `superseded_by` is a plain TEXT column (not a foreign key) because soft-delete uses the sentinel value `'_deleted'`
- **Document-first architecture** — MCP tools save/recall project documents (markdown one-pagers) directly to `project.summary`, not atomic memories. Memories remain in DB for dashboard Progress/Timeline tabs only.
- **Markdown validation** — `muninn_save` rejects content without `## ` headers, forcing LLM clients to format as structured markdown
- **Module-level store** — `tools.py` uses a module-level `_store` initialized once by `server.py` via `init_store()`
- **Junction table for tags** — `memory_tags` table instead of JSON TEXT column for proper FTS indexing
- **FTS5 sync triggers** — INSERT/UPDATE/DELETE triggers keep `memories_fts` in sync automatically
- **WAL + busy_timeout** — Handles concurrent access from multiple MCP clients
- **Dual transport** — stdio for AI clients, Streamable HTTP for dashboard REST API (localhost)
- **Bearer token auth** — ASGI middleware on HTTP transport, key via `MUNINN_API_KEY` env var
- **OAuth 2.0** — `MUNINN_OWNER_PASSWORD` enables OAuth for remote access (claude.ai, ChatGPT)
- **Literal enum on action** — `muninn_manage` uses `Literal[...]` so JSON schema includes enum for LLM discovery
- **Editable instructions** — MCP instructions are read from `~/.local/share/muninn/instructions.md` (auto-created with defaults on first run, `--reset` deletes it)

## MCP Tools (6 total)

| Tool | Purpose |
|------|---------|
| `muninn_save` | Save/update a project document (structured markdown one-pager) |
| `muninn_recall` | Load project document(s) — one project or all active |
| `muninn_search` | Keyword search across project documents |
| `muninn_status` | List all projects with status overview |
| `muninn_manage` | Project lifecycle (set_status, create_project, delete_project) |
| `muninn_sync` | Sync GitHub repo data (commits, issues, PRs) |

## Document Philosophy

Muninn is a **bridge between AI clients**, not technical documentation. Each project has a single **document** — a markdown one-pager stored in `project.summary`.

**Save:** what the project IS, key decisions, direction, current status, open questions.
**Don't save:** code changes, test results, function names, implementation details (git handles that).

Documents must be structured markdown with `## ` headers. Plain text is rejected by `muninn_save`.

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

## Muninn Auto-Save

git commit 후 commit 메시지가 `feat:` 또는 `refactor:`이면:
1. `muninn_recall(project="muninn")` → 현재 문서 확인
2. git에 없는 정보(why, topology, ops, state)만 문서에 머지
3. `muninn_save(project="muninn", content="<머지된 문서>")`로 업데이트

세부 규칙은 Muninn MCP instructions 참조.

## Coding Conventions

- All tool functions return strings (never raise — catch exceptions internally)
- Immutable patterns: frozen dataclasses, no mutation
- Small focused files (<400 lines each)
- DB schema unchanged — deprecated columns (depth, category, parent_memory_id) remain but are ignored by code
- Memory CRUD is dashboard-only (REST API in `api.py`) — MCP tools operate on project documents only

## Codex Delegation

Claude = 관리자 (계획, 리뷰, 검증). Codex = 실행자 (구현, 테스트). `codex-collab` 스킬로 위임.

### Role Split

| Role | Owner | Scope |
|------|-------|-------|
| Planning & Design | Claude | Architecture, API design, DB schema |
| Code Review | Claude | PR review, quality gates |
| Implementation | Codex | Code changes, new files, refactoring |
| Test Writing | Codex | Unit/integration tests |
| Verification | Claude | Review Codex output, run tests |

### Delegation Protocol

1. Claude plans → delegates via `codex-collab run`
2. Codex implements → returns results
3. Claude reviews → accepts or re-delegates with specific feedback

### Never Delegate to Codex

- DB schema migrations
- Architecture / design decisions
- Security-critical code (`auth.py`, token handling)
- CLAUDE.md / project config changes
