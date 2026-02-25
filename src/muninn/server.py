"""Muninn MCP server entry point.

Supports two transports:
  - stdio (default): for Claude Desktop, Claude Code, Cursor, Codex
  - streamable-http: for Claude Web/Mobile, ChatGPT, remote access

Authentication modes (HTTP only):
  - MUNINN_OWNER_PASSWORD: OAuth 2.0 (for claude.ai, iPhone)
  - MUNINN_API_KEY: Bearer token (for direct API access)
  - Neither: no auth (local dev only)

Usage:
  muninn                          # stdio (default)
  muninn --transport http         # HTTP on 127.0.0.1:8000
  muninn --transport http --port 9000 --host 0.0.0.0
  muninn --transport http --public-url https://abc.ngrok-free.dev
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
    "## Tag usage\n"
    "Tags make memories filterable. Always tag memories with relevant categories.\n"
    "Examples: ['decision', 'architecture'], ['bug', 'auth'], ['todo', 'api'], "
    "['research', 'performance'], ['milestone', 'shipped']\n"
    "Use 1-3 tags per memory. Prefer nouns and states over verbs.\n"
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
    parser.add_argument(
        "--public-url",
        default=None,
        help="Public URL for OAuth issuer (e.g. https://abc.ngrok-free.dev)",
    )
    return parser


def _create_mcp(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    public_url: str | None = None,
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
            required_scopes=[],
        )

    mcp = FastMCP(
        "muninn",
        instructions=_INSTRUCTIONS,
        host=host,
        port=port,
        streamable_http_path="/",
        **oauth_kwargs,
    )
    mcp.tool()(muninn_save)
    mcp.tool()(muninn_recall)
    mcp.tool()(muninn_search)
    mcp.tool()(muninn_status)
    mcp.tool()(muninn_manage)
    mcp.tool()(muninn_sync)
    return mcp


def _create_api_mount():
    """Create the /api Mount with dashboard REST routes."""
    from starlette.routing import Mount

    from muninn.api import create_api_routes
    from muninn.tools import _get_store

    api_routes = create_api_routes(_get_store())
    return Mount("/api", routes=api_routes)


def _run_http(mcp: FastMCP, host: str, port: int) -> None:
    """Run the server with Streamable HTTP transport.

    Auth mode priority:
      1. MUNINN_OWNER_PASSWORD → OAuth 2.0 (already wired into FastMCP)
      2. MUNINN_API_KEY → Bearer token middleware
      3. Neither → no auth (warning)
    """
    import uvicorn

    owner_password = os.environ.get("MUNINN_OWNER_PASSWORD")
    api_key = os.environ.get("MUNINN_API_KEY")

    api_mount = _create_api_mount()

    if owner_password:
        # OAuth mode — FastMCP already has auth routes via constructor.
        # Inject login routes into the MCP app via _custom_starlette_routes.
        from muninn.oauth_login import create_login_routes

        login_routes = create_login_routes(
            mcp._auth_server_provider,  # type: ignore[arg-type]
        )
        mcp._custom_starlette_routes.extend(login_routes)

        from contextlib import asynccontextmanager

        from starlette.applications import Starlette
        from starlette.routing import Mount

        mcp_asgi = mcp.streamable_http_app()

        @asynccontextmanager
        async def lifespan(app: object):  # type: ignore[override]
            async with mcp_asgi.router.lifespan_context(app):
                yield

        app = Starlette(
            routes=[api_mount, Mount("/", app=mcp_asgi)],
            lifespan=lifespan,
        )

        print(
            "OAuth 2.0 mode enabled. PIN required for authorization.",
            file=sys.stderr,
        )
        uvicorn.run(app, host=host, port=port)
    elif api_key:
        # Legacy Bearer token mode.
        from muninn.auth import create_authenticated_app

        app = create_authenticated_app(mcp, api_key, extra_routes=[api_mount])
        uvicorn.run(app, host=host, port=port)
    else:
        from contextlib import asynccontextmanager

        from starlette.applications import Starlette
        from starlette.routing import Mount

        print(
            "WARNING: No MUNINN_OWNER_PASSWORD or MUNINN_API_KEY set. "
            "HTTP server running without authentication.",
            file=sys.stderr,
        )

        mcp_asgi = mcp.streamable_http_app()

        @asynccontextmanager
        async def lifespan(app: object):  # type: ignore[override]
            async with mcp_asgi.router.lifespan_context(app):
                yield

        app = Starlette(
            routes=[api_mount, Mount("/", app=mcp_asgi)],
            lifespan=lifespan,
        )
        uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Initialise the store and run the MCP server."""
    parser = _build_parser()
    args = parser.parse_args()

    init_store(MuninnStore())

    mcp = _create_mcp(
        host=args.host,
        port=args.port,
        public_url=args.public_url,
    )

    if args.transport == "http":
        _run_http(mcp, args.host, args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
