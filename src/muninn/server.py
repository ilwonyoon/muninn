"""Muninn MCP server entry point.

Supports two transports:
  - stdio (default): for Claude Desktop, Claude Code, Cursor, Codex, ChatGPT
  - streamable-http: for dashboard + remote access (claude.ai, iPhone)

Authentication modes (HTTP only):
  - MUNINN_OWNER_PASSWORD: OAuth 2.0 (for claude.ai, iPhone)
  - MUNINN_API_KEY: Bearer token (for direct API access)
  - Neither: no auth (local dev only)

Usage:
  muninn                          # stdio (default)
  muninn --transport http         # HTTP on 127.0.0.1:8000
  muninn --transport http --port 9000 --host 0.0.0.0
  muninn --transport http --public-url https://muninn.ilwonyoon.com
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from muninn.store import MuninnStore
from muninn.tools import (
    init_store,
    muninn_manage,
    muninn_recall,
    muninn_save,
    muninn_save_memory,
    muninn_search,
    muninn_status,
    muninn_sync,
)

_INSTRUCTIONS = (
    "Muninn is a personal memory bridge across AI tools.\n"
    "\n"
    "## Core Concept: Project Documents\n"
    "Each project has a DOCUMENT — a markdown one-pager that captures what\n"
    "the project IS, key decisions, current direction, and open questions.\n"
    "\n"
    "## How to use\n"
    "1. When user mentions a project, call muninn_recall first.\n"
    "2. At session end, update the document:\n"
    '   - muninn_recall(project="xxx") to load current document\n'
    "   - Merge new info from this session\n"
    '   - muninn_save(project="xxx", content="<full markdown one-pager>")\n'
    "3. Organize by LOGIC, not chronology.\n"
    "\n"
    "## CRITICAL: Document Format\n"
    "The content parameter of muninn_save MUST be a full markdown document.\n"
    "NEVER save a single-line summary. Always use this structure:\n"
    "\n"
    "```\n"
    "# Project Name\n"
    "\n"
    "## Overview\n"
    "(What this project is, who it's for, core value proposition)\n"
    "\n"
    "## Key Decisions\n"
    "(Important choices made and why)\n"
    "\n"
    "## Current Status\n"
    "(What's done, what's next)\n"
    "\n"
    "## Open Questions\n"
    "(Unresolved decisions, things to explore)\n"
    "```\n"
    "\n"
    "Adapt sections to fit the project — add or rename as needed.\n"
    "Use headers (##), bullet points, and tables for readability.\n"
    "Minimum 200 characters. Aim for a comprehensive one-pager.\n"
    "\n"
    "## What goes in the document\n"
    "- What this project IS (user/product perspective)\n"
    "- Key decisions and why\n"
    "- Direction changes and reasoning\n"
    "- Current status and what's next\n"
    "- Open questions\n"
    "\n"
    "## What NOT to save\n"
    "- Code changes, function names, test results\n"
    "- Implementation details\n"
    "- Raw conversation logs\n"
    "\n"
    "## Project status values\n"
    "- active: currently working on\n"
    "- paused: temporarily on hold\n"
    "- idea: exploring, not started yet\n"
    "- archived: completed or past project\n"
)

_LOGGER = logging.getLogger("muninn")


def _instructions_path() -> Path:
    """Return the path to the user-editable instructions file."""
    return Path(MuninnStore.default_db_path()).parent / "instructions.md"


def _load_instructions(store: MuninnStore) -> str:
    """Load instructions from DB, seeding from file/default when empty."""
    try:
        content = store.get_instructions()
    except Exception as exc:
        _LOGGER.warning("Failed to read instructions from DB: %s", exc)
        content = ""

    if content:
        return content

    # Legacy fallback: seed DB from the previous instructions file once.
    path = _instructions_path()
    try:
        if path.exists():
            seeded = path.read_text(encoding="utf-8")
            try:
                store.update_instructions(seeded)
            except Exception as exc:
                _LOGGER.warning("Failed to seed instructions from file into DB: %s", exc)
            return seeded
    except Exception as exc:
        _LOGGER.warning("Failed to load legacy instructions file: %s", exc)

    # Fresh install fallback: seed DB with bundled defaults.
    try:
        store.update_instructions(_INSTRUCTIONS)
    except Exception as exc:
        _LOGGER.warning("Failed to seed default instructions into DB: %s", exc)
    return _INSTRUCTIONS


def _enable_dynamic_instructions(mcp: FastMCP, store: MuninnStore) -> None:
    """Refresh MCP instructions from DB on each initialization request."""
    original_create = mcp._mcp_server.create_initialization_options

    def _create_initialization_options(*args, **kwargs):
        mcp._mcp_server.instructions = _load_instructions(store)
        return original_create(*args, **kwargs)

    mcp._mcp_server.create_initialization_options = _create_initialization_options  # type: ignore[method-assign]


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
    parser.add_argument(
        "--public-url",
        default=None,
        help="Public URL for OAuth issuer (e.g. https://muninn.ilwonyoon.com)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe all memories, tags, revisions and clear project summaries, then exit.",
    )
    return parser


def _create_mcp(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    public_url: str | None = None,
    store: MuninnStore | None = None,
) -> FastMCP:
    """Create and configure the FastMCP instance with all tools registered.

    When ``MUNINN_OWNER_PASSWORD`` is set, configures the MCP SDK's built-in
    OAuth 2.0 authorization server for claude.ai / iPhone remote access.
    """
    oauth_kwargs: dict = {}
    owner_password = os.environ.get("MUNINN_OWNER_PASSWORD")

    if owner_password:
        from mcp.server.auth.settings import (
            AuthSettings,
            ClientRegistrationOptions,
            RevocationOptions,
        )
        from pydantic import AnyHttpUrl

        from muninn.oauth_provider import MuninnOAuthProvider

        issuer = public_url or f"http://{host}:{port}"
        db_path = MuninnStore.default_db_path()

        oauth_kwargs["auth_server_provider"] = MuninnOAuthProvider(
            db_path=db_path,
            owner_password=owner_password,
        )
        oauth_kwargs["auth"] = AuthSettings(
            issuer_url=AnyHttpUrl(issuer),
            resource_server_url=AnyHttpUrl(issuer),
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=["muninn"],
                default_scopes=["muninn"],
            ),
            revocation_options=RevocationOptions(enabled=True),
            required_scopes=["muninn"],
        )

    # When behind a reverse proxy (Cloudflare Tunnel), allow the public
    # hostname in addition to localhost so DNS-rebinding protection passes.
    transport_security = None
    if public_url:
        from urllib.parse import urlparse

        public_host = urlparse(public_url).hostname or ""
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                f"127.0.0.1:{port}",
                f"localhost:{port}",
                public_host,
            ],
        )

    resolved_store = store or MuninnStore()
    instructions = _load_instructions(resolved_store)

    mcp = FastMCP(
        "muninn",
        instructions=instructions,
        host=host,
        port=port,
        streamable_http_path="/",
        transport_security=transport_security,
        **oauth_kwargs,
    )
    _enable_dynamic_instructions(mcp, resolved_store)
    mcp.tool()(muninn_save)
    mcp.tool()(muninn_save_memory)
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

    Auth mode priority:
      1. MUNINN_OWNER_PASSWORD → OAuth 2.0 (already wired into FastMCP)
      2. MUNINN_API_KEY → Bearer token middleware
      3. Neither → no auth (warning)
    """
    import uvicorn

    owner_password = os.environ.get("MUNINN_OWNER_PASSWORD")
    api_key = os.environ.get("MUNINN_API_KEY")
    api_mount = _create_api_mount(store)

    if owner_password:
        from muninn.oauth_login import create_login_routes

        login_routes = create_login_routes(
            mcp._auth_server_provider,  # type: ignore[arg-type]
        )
        mcp._custom_starlette_routes.extend(login_routes)
        mcp._custom_starlette_routes.append(api_mount)
        app = mcp.streamable_http_app()
        print(
            "OAuth 2.0 mode enabled. PIN required for authorization.",
            file=sys.stderr,
        )
        uvicorn.run(app, host=host, port=port)
    elif api_key:
        from muninn.auth import create_authenticated_app

        app = create_authenticated_app(mcp, api_key, extra_routes=[api_mount])
        uvicorn.run(app, host=host, port=port)
    else:
        effective_host = "127.0.0.1" if host == "0.0.0.0" else host
        print(
            "WARNING: No MUNINN_OWNER_PASSWORD or MUNINN_API_KEY set. "
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

    if args.reset:
        store.reset_data()
        store.update_instructions(_INSTRUCTIONS)
        # Clean up legacy file; DB is now canonical.
        inst_path = _instructions_path()
        if inst_path.exists():
            inst_path.unlink()
        print("Reset complete. All memories, tags, revisions wiped. Summaries cleared.", file=sys.stderr)
        return

    init_store(store)

    mcp = _create_mcp(
        host=args.host,
        port=args.port,
        public_url=args.public_url,
        store=store,
    )

    if args.transport == "http":
        _run_http(mcp, args.host, args.port, store=store)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
