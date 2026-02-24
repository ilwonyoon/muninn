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

mcp = FastMCP("muninn", instructions="Persistent project memory for AI assistants.")

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
