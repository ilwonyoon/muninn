# Muninn

[![PyPI version](https://badge.fury.io/py/muninn-mcp.svg)](https://pypi.org/project/muninn-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> *"Odin feared losing Muninn more than Huginn — losing memory is worse than losing thought."*

**Cross-tool project memory for AI assistants.** Muninn (MOO-nin) is an MCP server that gives Claude, ChatGPT, Cursor, and other AI tools shared, persistent, project-structured memory.

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

## Quick Start

### Install

```bash
# From PyPI (recommended)
pip install muninn-mcp            # basic (stdio only)
pip install muninn-mcp[http]      # with HTTP transport
pip install muninn-mcp[all]       # everything

# From source (development)
git clone https://github.com/ilwonyoon/muninn.git
cd muninn
pip install -e ".[dev]"
```

### Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "muninn": {
      "command": "/path/to/muninn/.venv/bin/python",
      "args": ["-m", "muninn.server"]
    }
  }
}
```

Restart Claude Desktop. Start saving memories.

### Connect to Claude Code

```bash
claude mcp add muninn -- /path/to/muninn/.venv/bin/python -m muninn.server
```

## Remote Access (HTTP Transport)

For Claude Web/Mobile, ChatGPT, or remote access:

```bash
# Basic (no auth — local dev only)
muninn --transport http --port 8000

# With authentication (recommended)
export MUNINN_API_KEY="your-secret-key"
muninn --transport http --host 0.0.0.0 --port 8000
```

Endpoint: `http://localhost:8000/mcp`

For public access, expose via [ngrok](https://ngrok.com/) or [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/):

```bash
ngrok http 8000
# Then add the HTTPS URL to claude.ai or ChatGPT as a remote MCP server
```

## Tools

| Tool | Purpose |
|------|---------|
| `muninn_save` | Save memory to a project |
| `muninn_recall` | Load project context with depth filtering |
| `muninn_search` | Full-text search across all memories |
| `muninn_status` | List all projects with overview |
| `muninn_manage` | Delete/update memories, manage projects |

## Depth System

Muninn uses a 4-level depth system that works for any project type:

| Depth | Question | Use For |
|-------|----------|---------|
| 0 | "What is this?" | 10-second project overview. Always loaded. Create first. |
| 1 | "To continue" | Resume work next session. Key decisions, current state. |
| 2 | "To go deeper" | Detailed analysis, specs, research. Loaded on request. |
| 3 | "Just in case" | Archive, raw data, logs. Rarely loaded. |

```
muninn_recall(depth=0)  →  Project summaries only (~500 chars)
muninn_recall(depth=1)  →  Above + working context (default)
muninn_recall(depth=2)  →  Above + deep details
muninn_recall(depth=3)  →  Everything
```

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

## Data Storage

```
Default: ~/.local/share/muninn/muninn.db
Override: MUNINN_DB_PATH=/path/to/custom.db
```

SQLite with WAL mode. Single file. Back up with `cp muninn.db muninn.db.bak`.

## Development

```bash
# Install with dev deps
pip install -e ".[dev]"

# Run tests (132+ tests)
python -m pytest tests/ -v

# Run the server (stdio)
python -m muninn.server

# Run the server (HTTP)
python -m muninn.server --transport http --port 8000
```

## Architecture

```
src/muninn/
  server.py      # MCP entry point (stdio + HTTP)
  auth.py        # Bearer token auth middleware
  tools.py       # 5 MCP tool functions
  store.py       # SQLite with FTS5 full-text search
  models.py      # Frozen dataclasses
  formatter.py   # LLM-readable output formatting
```

## Platform Support

| Platform | Transport | Status |
|----------|-----------|--------|
| Claude Desktop (Mac) | stdio | Working |
| Claude Code | stdio | Working |
| Cursor | stdio | Working |
| Claude Web/Mobile | HTTP | Ready (needs hosting) |
| ChatGPT Web | HTTP | Ready (needs hosting) |
| ChatGPT Mac | — | No MCP support yet |

## License

MIT
