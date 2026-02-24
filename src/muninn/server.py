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
        "When saving, ALWAYS choose depth carefully: "
        "0='What is this?' (project summary, create FIRST), "
        "1='To continue' (resume next session, default), "
        "2='To go deeper' (detailed analysis), "
        "3='Just in case' (archive/logs). "
        "Keep depth 0-1 memories short (200-500 chars), one topic each. "
        "These depth meanings work for ANY project type: app, content, research, etc."
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
