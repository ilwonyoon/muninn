# Muninn

[![PyPI version](https://badge.fury.io/py/muninn-mcp.svg)](https://pypi.org/project/muninn-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> *"Odin feared losing Muninn more than Huginn — losing memory is worse than losing thought."*

Muninn is a personal MCP memory server for cross-client project continuity.

It is **document-first**: each project has one structured markdown document
stored in `projects.summary`, and MCP tools save/recall/search those project
documents directly.

**Primary clients:** Claude Code CLI, Claude Desktop, ChatGPT Mac App, Codex CLI

## 5-Minute Quickstart

### 1) Install

```bash
pip install muninn-mcp
```

Optional extras:

```bash
pip install "muninn-mcp[http]"    # HTTP transport support
pip install "muninn-mcp[github]"  # GitHub sync dependencies
pip install "muninn-mcp[all]"     # all optional deps
```

### 2) Configure one client (Claude Code example)

```bash
claude mcp add muninn -- uvx muninn-mcp
```

If you prefer local Python instead of `uvx`:

```bash
claude mcp add muninn -- muninn
```

### 3) First save (must be structured markdown)

In the client chat, send:

```text
Save this to project "muninn-demo":

# Muninn Demo

## Overview
Personal MCP memory server for project continuity across tools.

## Key Decisions
- Use project-level markdown one-pager, not atomic memory writes.

## Current Status
- Initial setup complete.

## Open Questions
- What sections should be mandatory in every project document?
```

`muninn_save` rejects plain text without `##` headers.

### 4) Recall it

Ask:

```text
Recall muninn-demo
```

You should get the saved project document back.

## Current Architecture

- **Document-first MCP model:** `muninn_save` replaces the entire
  `projects.summary` document for a project.
- **6 MCP tools:** `muninn_save`, `muninn_recall`, `muninn_search`,
  `muninn_status`, `muninn_manage`, `muninn_sync`.
- **Search is keyword-only:** no semantic/vector search path in MCP tools.
- **Storage:** SQLite/libSQL with WAL mode; FTS5 tables are present in schema.
- **Transport:** stdio (default) and streamable HTTP.
- **Dashboard:** Next.js + React + Tailwind app in `web/` (localhost workflow).

## MCP Tools Reference (Actual Signatures)

| Tool | Signature | Behavior |
|------|-----------|----------|
| `muninn_save` | `muninn_save(project: str, content: str) -> str` | Save or replace a project's markdown document. Auto-creates project if missing. Requires markdown with `##` headers. |
| `muninn_recall` | `muninn_recall(project: str \| None = None) -> str` | Recall one project's document, or all **active** project documents when `project` is omitted. |
| `muninn_search` | `muninn_search(query: str) -> str` | Keyword search across project documents. |
| `muninn_status` | `muninn_status() -> str` | Status overview of projects. |
| `muninn_manage` | `muninn_manage(action: Literal["set_status", "create_project", "delete_project"], project: str, status: str \| None = None, value: str \| None = None) -> str` | Manage project lifecycle. |
| `muninn_sync` | `muninn_sync(project: str) -> str` | Sync linked GitHub repo (commits/issues/PRs) into memory for that project. |

### `muninn_manage` actions

| Action | Required | Notes |
|--------|----------|-------|
| `set_status` | `project`, `status` | `status` must be one of `active`, `paused`, `idea`, `archived`. |
| `create_project` | `project` | Optional `value` sets display name. |
| `delete_project` | `project` | Irreversible delete of project and its data. |

### `muninn_sync` prerequisites

- Project must exist.
- Project must have `github_repo` set (via dashboard or REST API).
- `GITHUB_TOKEN` is recommended for private repos and rate limits.

## Client Configuration Examples

### Claude Code CLI

```bash
claude mcp add muninn -- uvx muninn-mcp
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "muninn": {
      "command": "uvx",
      "args": ["muninn-mcp"]
    }
  }
}
```

### Codex CLI

```bash
codex mcp add muninn -- uvx muninn-mcp
codex mcp list
```

### ChatGPT Mac App (HTTP connector)

1. Start Muninn in HTTP mode:

```bash
MUNINN_API_KEY=your-secret-key muninn --transport http --host 127.0.0.1 --port 8000
```

2. In ChatGPT Mac App, add a custom MCP connector to:

```text
http://127.0.0.1:8000/
```

3. Use bearer auth with the same key.

For remote/public access, run with a public URL and appropriate auth settings.

## Running The Server

```bash
# stdio (default)
muninn

# HTTP
muninn --transport http --host 127.0.0.1 --port 8000

# HTTP with public URL (OAuth issuer host)
muninn --transport http --host 0.0.0.0 --port 8000 --public-url https://your-domain.example

# Reset data and instructions file
muninn --reset
```

HTTP auth mode priority:

1. `MUNINN_OWNER_PASSWORD` → OAuth 2.0
2. `MUNINN_API_KEY` → Bearer token
3. Neither set → no auth (local dev only)

## Dashboard (Localhost)

```bash
# terminal 1: Muninn server
muninn --transport http --port 8000

# terminal 2: dashboard
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Data & Environment

- Default DB path: `~/.local/share/muninn/muninn.db`
- Override DB path: `MUNINN_DB_PATH=/path/to/muninn.db`
- OAuth PIN auth: `MUNINN_OWNER_PASSWORD`
- Bearer auth: `MUNINN_API_KEY`
- GitHub sync auth: `GITHUB_TOKEN`

## Development

```bash
# Install dev deps
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run server module directly
python -m muninn.server
python -m muninn.server --transport http --port 8000
```

## Architecture

```text
src/muninn/
  server.py       # FastMCP entry point (stdio + HTTP, CLI args)
  tools.py        # 6 MCP tool functions (document-first)
  store.py        # SQLite/libSQL store, WAL, FTS5 tables
  formatter.py    # LLM-readable formatter output
  models.py       # Dataclasses and validation
  auth.py         # Bearer middleware (HTTP)
  api.py          # Dashboard REST routes
  github_sync.py  # GitHub commits/issues/PR sync
```

## License

MIT
