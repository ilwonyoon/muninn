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
    "Muninn is persistent project memory for AI assistants.\n"
    "\n"
    "## When to use\n"
    "- SESSION START: Call muninn_recall when the user mentions a project.\n"
    "- AFTER SIGNIFICANT WORK: Save key decisions, conclusions, and state.\n"
    "- Never save raw conversation. Distill into facts and decisions.\n"
    "\n"
    "## Save tips\n"
    "- One topic per memory. Split unrelated facts into separate saves.\n"
    "- Use 1-3 tags per memory for filtering: ['decision', 'auth'], ['bug', 'api'].\n"
    "- Update stale memories with muninn_manage update_memory, don't duplicate.\n"
    "\n"
    "## Project summary\n"
    "- After each session, update the project summary via:\n"
    '  muninn_manage(action="update_project", project="xxx", field="summary", value="...")\n'
    "- Write from USER/PRODUCT perspective, not engineer perspective.\n"
    "- This is NOT technical documentation. Record thoughts, decisions, and direction.\n"
    '  Good: "복잡한 분류 체계 제거 결정. 단순할수록 좋다는 결론."\n'
    '  Bad: "SQLite WAL + FTS5 with bearer token middleware 구현 완료"\n'
    "- Record: what was decided, why, what changed in thinking, what's next.\n"
    "- Do NOT record: what code was written, what tests pass, what functions were added.\n"
    "\n"
    "## Project status\n"
    "- active: 진행 중인 프로젝트\n"
    "- paused: 일시 중단\n"
    "- idea: 관심사, 탐구 중\n"
    "- archived: 완료된 과거 프로젝트\n"
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
        help="Public URL for OAuth issuer (e.g. https://muninn.ilwonyoon.com)",
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
            required_scopes=["muninn"],
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
