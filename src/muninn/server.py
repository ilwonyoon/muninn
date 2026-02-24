"""Muninn MCP server entry point.

Supports two transports:
  - stdio (default): for Claude Desktop, Claude Code, Cursor, Codex
  - streamable-http: for Claude Web/Mobile, ChatGPT, remote access

Usage:
  muninn                          # stdio (default)
  muninn --transport http         # HTTP on 127.0.0.1:8000
  muninn --transport http --port 9000 --host 0.0.0.0
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
)

_INSTRUCTIONS = (
    "Muninn is persistent project memory for AI assistants. "
    "When saving, ALWAYS choose depth carefully: "
    "0='What is this?' (project summary, create FIRST), "
    "1='To continue' (resume next session, default), "
    "2='To go deeper' (detailed analysis), "
    "3='Just in case' (archive/logs). "
    "Keep depth 0-1 memories short (200-500 chars), one topic each. "
    "These depth meanings work for ANY project type: app, content, research, etc."
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
    )
    mcp.tool()(muninn_save)
    mcp.tool()(muninn_recall)
    mcp.tool()(muninn_search)
    mcp.tool()(muninn_status)
    mcp.tool()(muninn_manage)
    return mcp


def _run_http(mcp: FastMCP, host: str, port: int) -> None:
    """Run the server with Streamable HTTP transport.

    If ``MUNINN_API_KEY`` is set, wraps the ASGI app with Bearer token
    authentication middleware.
    """
    api_key = os.environ.get("MUNINN_API_KEY")

    if api_key:
        # Wrap with auth middleware
        from muninn.auth import create_authenticated_app

        app = create_authenticated_app(mcp, api_key)

        import uvicorn

        uvicorn.run(app, host=host, port=port)
    else:
        print(
            "WARNING: No MUNINN_API_KEY set. HTTP server running without authentication.",
            file=sys.stderr,
        )
        mcp.run(transport="streamable-http")


def main() -> None:
    """Initialise the store and run the MCP server."""
    parser = _build_parser()
    args = parser.parse_args()

    init_store(MuninnStore())

    mcp = _create_mcp(host=args.host, port=args.port)

    if args.transport == "http":
        _run_http(mcp, args.host, args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
