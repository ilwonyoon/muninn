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


def _create_api_mount(store: MuninnStore, api_key: str | None = None):
    """Create the /api Mount with dashboard REST routes.

    When *api_key* is provided, the mount is wrapped with Bearer token
    authentication middleware so the dashboard API is never exposed
    without credentials.
    """
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.routing import Mount

    from muninn.api import create_api_routes

    api_routes = create_api_routes(store)

    if api_key:
        from muninn.auth import BearerTokenMiddleware

        api_app = Starlette(
            routes=api_routes,
            middleware=[Middleware(BearerTokenMiddleware, api_key=api_key)],
        )
        return Mount("/api", app=api_app)

    return Mount("/api", routes=api_routes)


def _run_http(mcp: FastMCP, host: str, port: int, store: MuninnStore) -> None:
    """Run the server with Streamable HTTP transport.

    Auth mode priority:
      1. MUNINN_OWNER_PASSWORD → OAuth 2.0 (already wired into FastMCP)
      2. MUNINN_API_KEY → Bearer token middleware
      3. Neither → no auth (localhost only, warning)

    Dashboard API (/api/*) protection:
      - If MUNINN_API_KEY is set: /api protected with Bearer token in ALL modes
      - If only MUNINN_OWNER_PASSWORD: /api NOT mounted (use MUNINN_API_KEY too)
      - If neither: /api mounted unprotected (localhost-only warning)
    """
    import uvicorn

    owner_password = os.environ.get("MUNINN_OWNER_PASSWORD")
    api_key = os.environ.get("MUNINN_API_KEY")

    # Build API mount — protected with Bearer token when api_key is set.
    api_mount = _create_api_mount(store, api_key=api_key)

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

        routes = [Mount("/", app=mcp_asgi)]
        if api_key:
            routes.insert(0, api_mount)
            print(
                "OAuth 2.0 mode enabled. Dashboard API protected with MUNINN_API_KEY.",
                file=sys.stderr,
            )
        else:
            print(
                "OAuth 2.0 mode enabled. Dashboard API disabled "
                "(set MUNINN_API_KEY to enable /api routes).",
                file=sys.stderr,
            )

        app = Starlette(routes=routes, lifespan=lifespan)
        uvicorn.run(app, host=host, port=port)
    elif api_key:
        # Bearer token mode — everything protected.
        from muninn.auth import create_authenticated_app

        app = create_authenticated_app(mcp, api_key, extra_routes=[api_mount])
        uvicorn.run(app, host=host, port=port)
    else:
        # No auth — localhost only with warning.
        from contextlib import asynccontextmanager

        from starlette.applications import Starlette
        from starlette.routing import Mount

        effective_host = "127.0.0.1" if host == "0.0.0.0" else host
        print(
            "WARNING: No MUNINN_OWNER_PASSWORD or MUNINN_API_KEY set. "
            "HTTP server running without authentication. "
            "Dashboard API bound to localhost only.",
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
        uvicorn.run(app, host=effective_host, port=port)


def main() -> None:
    """Initialise the store and run the MCP server."""
    parser = _build_parser()
    args = parser.parse_args()

    store = MuninnStore()
    init_store(store)

    mcp = _create_mcp(
        host=args.host,
        port=args.port,
        public_url=args.public_url,
    )

    if args.transport == "http":
        _run_http(mcp, args.host, args.port, store=store)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
