# Muninn

[![PyPI version](https://badge.fury.io/py/muninn-mcp.svg)](https://pypi.org/project/muninn-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> *"Odin feared losing Muninn more than Huginn — losing memory is worse than losing thought."*

**Cross-tool project memory for AI assistants.** Muninn (MOO-nin, Odin's raven of memory) is an MCP server that gives Claude, ChatGPT, Cursor, and other AI tools shared, persistent, project-structured memory.

## The Problem

Every tool switch = context reset. Every session = re-explanation from scratch.

- 2 hours brainstorming in Claude Desktop → switch to Claude Code → blank slate
- Research in ChatGPT → switch to Cursor → copy-paste everything
- Come back tomorrow → "this project is X, tech stack is Y, we're at Z..." again

## How Muninn Solves It

```
Save in Claude Desktop    →  "Save this to ouri-app"
Switch to Claude Code     →  muninn_recall("ouri-app") → full context loaded
Research in ChatGPT       →  "Save findings to ouri-app"
Come back next week       →  Everything remembered
```

Zero copy-paste. Zero re-explanation. Works across any MCP-compatible tool.

---

## Quick Start

### Install

```bash
# From PyPI (recommended)
pip install muninn-mcp            # basic (stdio only)
pip install muninn-mcp[http]      # with HTTP transport
pip install muninn-mcp[semantic]  # with semantic search (~200MB model)
pip install muninn-mcp[all]       # everything

# Or use uvx (no install needed)
uvx muninn-mcp
```

---

## Client Setup

### Claude Code

```bash
claude mcp add muninn -- uvx muninn-mcp
```

Or with a local install:

```bash
claude mcp add muninn -- python -m muninn.server
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Restart Claude Desktop. Start saving memories.

### Cursor

Add to `.cursor/mcp.json` in your project (or `~/.cursor/mcp.json` globally):

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

### claude.ai / Claude iPhone (Remote)

Claude Web and the iPhone app require an HTTP server with OAuth. See [Remote Access — OAuth](#oauth-for-claudeai--iphone) below.

### ChatGPT

ChatGPT requires an HTTP endpoint. See [Remote Access — Bearer Token](#bearer-token-for-chatgpt--direct-api) below, then add the URL as a custom connector in ChatGPT settings.

---

## Remote Access (HTTP Transport)

### Basic (local dev only — no auth)

```bash
muninn --transport http --port 8000
# Endpoint: http://localhost:8000/
```

### OAuth (for claude.ai / iPhone)

OAuth lets claude.ai and the Claude iPhone app connect to your Muninn instance. You set a PIN; Claude prompts users to enter it on first connection.

**Step 1 — Expose a public URL with ngrok:**

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
# Copy the HTTPS URL, e.g. https://abc123.ngrok-free.app
```

**Step 2 — Start Muninn with OAuth:**

```bash
MUNINN_OWNER_PASSWORD=yourpin muninn \
  --transport http \
  --host 0.0.0.0 \
  --port 8000 \
  --public-url https://abc123.ngrok-free.app
```

**Step 3 — Add to claude.ai:**

In Claude settings → Integrations → Add MCP server → enter `https://abc123.ngrok-free.app`. Claude will prompt for your PIN on first authorization.

### Bearer Token (for ChatGPT / direct API)

```bash
MUNINN_API_KEY=your-secret-key muninn \
  --transport http \
  --host 0.0.0.0 \
  --port 8000
```

Clients send `Authorization: Bearer your-secret-key` with each request. Use ngrok (same as above) to expose publicly.

### Auth Mode Priority

| Priority | Env Var | Auth Type | Use For |
|----------|---------|-----------|---------|
| 1 | `MUNINN_OWNER_PASSWORD` | OAuth 2.0 | claude.ai, iPhone |
| 2 | `MUNINN_API_KEY` | Bearer token | ChatGPT, direct API |
| 3 | (neither) | None | Local dev only |

---

## Tools Reference

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `muninn_save` | Save a memory to a project | `project`, `content`, `depth` (0-3), `tags` |
| `muninn_recall` | Load project context | `project`, `depth` (default 1), `max_chars` (default 8000), `tags` |
| `muninn_search` | Full-text + semantic search across all memories | `query`, `project`, `tags`, `limit`, `semantic` |
| `muninn_status` | List all projects with memory counts | — |
| `muninn_manage` | Delete/update memories, manage projects | `action`, `project`, `memory_id`, `field`, `value` |

### `muninn_manage` Actions

| Action | What It Does | Required Params |
|--------|-------------|-----------------|
| `set_status` | Set project status (active/paused/idea/archived) | `project`, `status` |
| `delete_memory` | Remove a memory by ID | `project`, `memory_id` |
| `update_memory` | Edit content, depth, or tags of a memory | `project`, `memory_id`, `field`, `value` |
| `update_project` | Update name, summary, or github_repo | `project`, `field`, `value` |
| `create_project` | Explicitly create a project | `project` |

---

## Depth System

Muninn uses a 4-level depth system that works for any project type — app, research, content, etc.

| Depth | Question | Use For |
|-------|----------|---------|
| 0 | "What is this?" | 10-second project overview. Always loaded on recall. Create this first. |
| 1 | "To continue" | Resume work next session. Key decisions, current state. (default) |
| 2 | "To go deeper" | Detailed analysis, specs, research. Loaded on request. |
| 3 | "Just in case" | Archive, raw data, logs. Rarely loaded. |

```
muninn_recall(depth=0)  →  Project summaries only (~500 chars)
muninn_recall(depth=1)  →  Above + working context (default)
muninn_recall(depth=2)  →  Above + deep details
muninn_recall(depth=3)  →  Everything
```

**Best practice:** Always create a `depth=0` summary first for every new project. Keep `depth=0` and `depth=1` memories short (200–500 chars), one topic each.

---

## Example Usage

In any AI tool connected to Muninn:

```
User: "Save this to ouri-app: voice journaling app for Korean millennials,
       React Native + Whisper API, freemium model"

→ muninn_save(project="ouri-app", content="...", depth=0)
→ Saved to ouri-app (memory: a1b2c3d4)
```

```
User: "What are my projects?"

→ muninn_status()
→ ouri-app    active  today       memories: 9
   muninn     active  today       memories: 15
   glpuri     paused  2 weeks ago memories: 23
```

```
User: "Load ouri-app context"

→ muninn_recall(project="ouri-app")
→ ## ouri-app (active)
  - [summary] (a1b2c3d4) Voice journaling app for Korean millennials...
  - [context] (b2c3d4e5) Tech stack: React Native + Whisper API...
  - [context] (c3d4e5f6) Revenue model: freemium with 5min/day limit...
  Context: 2,341 / 8,000 chars | 9 memories loaded
```

---

## Semantic Search (Optional)

When keyword search misses related memories (e.g. searching "login" doesn't find "OAuth authentication flow"), semantic search finds them by meaning similarity.

```bash
pip install muninn-mcp[semantic]   # adds fastembed + bge-small-en-v1.5 (~200MB)
```

**How it works:**
- Embeddings are generated automatically on `muninn_save` and `muninn_manage(update_memory)`
- `muninn_search` tries FTS5 keyword search first. If no results, falls back to semantic search automatically
- Use `semantic=True` to skip FTS5 and search by meaning only
- Existing memories are backfilled on first semantic search

**Without `[semantic]` installed:** Everything works exactly the same — FTS5 keyword search only, no errors.

---

## Data Storage

```
Default: ~/.local/share/muninn/muninn.db
Override: MUNINN_DB_PATH=/path/to/custom.db
```

SQLite with WAL mode. Single file. Back up with `cp muninn.db muninn.db.bak`.

---

## Platform Support

| Platform | Transport | Auth | Status |
|----------|-----------|------|--------|
| Claude Desktop (Mac) | stdio | — | Working |
| Claude Code | stdio | — | Working |
| Cursor | stdio | — | Working |
| claude.ai / iPhone | HTTP | OAuth (`MUNINN_OWNER_PASSWORD`) | Working (needs public URL) |
| ChatGPT Web | HTTP | Bearer (`MUNINN_API_KEY`) | Working (needs public URL) |
| ChatGPT Mac | — | — | No MCP support yet |

---

## Development

```bash
# Install with dev deps
pip install -e ".[dev]"

# Run tests (239 tests)
python -m pytest tests/ -v

# Run the server (stdio)
python -m muninn.server

# Run the server (HTTP)
python -m muninn.server --transport http --port 8000
```

## Architecture

```
src/muninn/
  server.py          # MCP entry point (stdio + HTTP), CLI args
  auth.py            # Bearer token auth middleware
  oauth_provider.py  # OAuth 2.0 provider (PIN-based)
  oauth_login.py     # OAuth login routes
  tools.py           # 6 MCP tool functions
  store.py           # SQLite with FTS5 + semantic search
  models.py          # Frozen dataclasses
  formatter.py       # LLM-readable output formatting
  embedder.py        # Embedding engine (fastembed, graceful degradation)
```

## License

MIT
