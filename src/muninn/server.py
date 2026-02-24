"""Muninn MCP server entry point.

Creates a FastMCP stdio server and registers all Muninn tools.
"""

from __future__ import annotations

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

mcp = FastMCP(
    "muninn",
    instructions=(
        "Muninn is persistent project memory for AI assistants. "
        "When saving memories, ALWAYS choose the appropriate depth: "
        "0=project summary (create first for new projects), "
        "1=key decisions (default), 2=detailed specs, 3=full history. "
        "Keep each memory focused on one topic, 200-500 chars for depth 0-1. "
        "When recalling, start with depth=1 for general context. "
        "Use depth=0 for quick project overview, depth=2+ for deep dives."
    ),
)

mcp.tool()(muninn_save)
mcp.tool()(muninn_recall)
mcp.tool()(muninn_search)
mcp.tool()(muninn_status)
mcp.tool()(muninn_manage)


def main() -> None:
    """Initialise the store and run the MCP server over stdio."""
    init_store(MuninnStore())
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
