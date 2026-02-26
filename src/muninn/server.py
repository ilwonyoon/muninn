"""Muninn MCP server entry point.

Supports two transports:
  - stdio (default): for Claude Desktop, Claude Code, Cursor, Codex, ChatGPT
  - streamable-http: for dashboard access on localhost

Authentication (HTTP only):
  - MUNINN_API_KEY: Bearer token
  - No key: no auth (localhost only)

Usage:
  muninn                          # stdio (default)
  muninn --transport http         # HTTP on 127.0.0.1:8000
  muninn --transport http --port 9000
"""

from __future__ import annotations

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from muninn.store import MuninnStore
from muninn.tools import (
    init_store,
    muninn_manage,
    muninn_recall,
    muninn_save,
    muninn_search,
    muninn_status,
    muninn_sync,
)

_INSTRUCTIONS = (
    "Muninn is persistent project memory for AI assistants. "
    "\n\n"
    "## When to use Muninn\n"
    "- SESSION START: Call muninn_recall immediately when the user mentions a project. "
    "Do not wait for explicit instruction — if a project name appears, recall it.\n"
    "- AFTER SIGNIFICANT WORK: Save key decisions, conclusions, and state before the session ends.\n"
    "- NEVER save raw conversation. Always distill: extract the decision or fact, discard the dialog.\n"
    "\n"
    "## Depth selection (works for any project type)\n"
    "depth=0  'What is this?'  — 2-3 sentence project summary. "
    "Create this FIRST for every new project. Max 300 chars. Always loaded.\n"
    "depth=1  'To continue'    — What's needed to resume next session: current direction, "
    "key decisions, open questions. 200-400 chars each, one topic per memory. DEFAULT depth.\n"
    "depth=2  'To go deeper'   — Detailed analysis, full research, implementation plans. "
    "Only when user asks to dive into specifics.\n"
    "depth=3  'Just in case'   — Archives, old versions, raw logs. Rarely loaded.\n"
    "\n"
    "## Depth examples\n"
    "depth=0: 'Muninn: MCP memory server in Python/SQLite. Provides 5 tools for save/recall/search.'\n"
    "depth=1: 'Decided to use FTS5 triggers over manual sync. WAL mode for concurrent access.'\n"
    "depth=1: 'Open: OAuth flow needs testing on mobile. Auth middleware incomplete.'\n"
    "depth=2: 'Full schema design with junction table for tags, migration strategy for v2...'\n"
    "depth=3: 'Raw benchmark results from 2024-01 load test...'\n"
    "\n"
    "## Category selection\n"
    "Pick the category that best describes what the memory IS, not what it's about:\n"
    "  vision         — 'Why does this exist?' Project motivation, target users, market.\n"
    "  product        — 'What are we building?' Scope, UX, feature tradeoffs.\n"
    "  insight        — 'What did we learn?' User observations, usage patterns.\n"
    "  status         — 'Where are we now?' Milestones, progress, next steps. DEFAULT.\n"
    "  architecture   — 'How is it built?' Tech stack, modules, data models.\n"
    "  decision       — 'Why this way?' Engineering rationale, tradeoffs.\n"
    "  implementation — 'How do I run it?' Config, commands, paths, API contracts.\n"
    "  issue          — 'What's broken?' Bugs, errors, blockers.\n"
    "\n"
    "## Tag usage\n"
    "Tags make memories filterable. Always tag memories with relevant categories.\n"
    "Examples: ['decision', 'architecture'], ['bug', 'auth'], ['todo', 'api'], "
    "['research', 'performance'], ['milestone', 'shipped']\n"
    "Use 1-3 tags per memory. Prefer nouns and states over verbs.\n"
    "\n"
    "## Content formatting\n"
    "Always write the FIRST LINE as a concise title (max 60 chars, no markdown formatting).\n"
    "The rest is the body — use markdown freely.\n"
    "Example:\n"
    "  'OAuth removed — local-only scope\\n\\nWe decided to strip OAuth to keep scope minimal...'\n"
    "  NOT: '## **OAuth Decision**\\n\\nWe decided...'\n"
    "\n"
    "## Save quality rules\n"
    "- One memory per topic. Split unrelated facts into separate saves.\n"
    "- Depth 0-1 must be skimmable in under 5 seconds. Cut anything redundant.\n"
    "- Prefer concrete over vague: 'Using hatchling, not setuptools' beats 'build system chosen'.\n"
    "- Update stale memories with muninn_manage update_memory rather than adding duplicates.\n"
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="muninn",
        description="Muninn MCP memory server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP host to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port to bind (default: 8000)",
    )
    return parser


def _create_mcp(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    """Create and configure the FastMCP instance with all tools registered."""
    mcp = FastMCP(
        "muninn",
        instructions=_INSTRUCTIONS,
        host=host,
        port=port,
        streamable_http_path="/",
    )
    mcp.tool()(muninn_save)
    mcp.tool()(muninn_recall)
    mcp.tool()(muninn_search)
    mcp.tool()(muninn_status)
    mcp.tool()(muninn_manage)
    mcp.tool()(muninn_sync)
    return mcp


def _create_api_mount(store: MuninnStore):
    """Create the /api Mount with dashboard REST routes.

    Dashboard API routes are always unauthenticated — they are local-only
    and consumed by the Next.js frontend proxy.  MCP endpoints carry their
    own Bearer token middleware separately.
    """
    from starlette.routing import Mount

    from muninn.api import create_api_routes

    api_routes = create_api_routes(store)
    return Mount("/api", routes=api_routes)


def _run_http(mcp: FastMCP, host: str, port: int, store: MuninnStore) -> None:
    """Run the server with Streamable HTTP transport.

    Auth mode:
      - MUNINN_API_KEY → Bearer token middleware on everything
      - No key → no auth (localhost only, warning)
    """
    import uvicorn

    api_key = os.environ.get("MUNINN_API_KEY")
    api_mount = _create_api_mount(store)

    if api_key:
        from muninn.auth import create_authenticated_app

        app = create_authenticated_app(mcp, api_key, extra_routes=[api_mount])
        uvicorn.run(app, host=host, port=port)
    else:
        effective_host = "127.0.0.1" if host == "0.0.0.0" else host
        print(
            "WARNING: No MUNINN_API_KEY set. "
            "HTTP server running without authentication. "
            "Dashboard API bound to localhost only.",
            file=sys.stderr,
        )
        mcp._custom_starlette_routes.append(api_mount)
        mcp_asgi = mcp.streamable_http_app()
        uvicorn.run(mcp_asgi, host=effective_host, port=port)


def main() -> None:
    """Initialise the store and run the MCP server."""
    parser = _build_parser()
    args = parser.parse_args()

    store = MuninnStore()
    init_store(store)

    mcp = _create_mcp(
        host=args.host,
        port=args.port,
    )

    if args.transport == "http":
        _run_http(mcp, args.host, args.port, store=store)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
