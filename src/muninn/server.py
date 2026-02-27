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
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

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
    "Muninn is a personal memory bridge across AI tools.\n"
    "The user works on multiple projects (apps, tools, ideas) and switches\n"
    "between Claude Code, Claude Desktop, ChatGPT, and Codex. Muninn keeps\n"
    "context alive across all of them.\n"
    "\n"
    "## How to use\n"
    "1. When the user mentions a project by name, call muninn_recall first.\n"
    "2. When important conclusions emerge, save them immediately.\n"
    "3. At the end of a meaningful session, update the project summary.\n"
    "\n"
    "## What to save\n"
    "Save the user's THINKING, not the technical output:\n"
    "- Decisions made and why: '계층 구조 제거. 단순할수록 좋다는 결론.'\n"
    "- Direction changes: '처음엔 React Native였는데 Swift로 전환. 퍼포먼스 이유.'\n"
    "- Current status: '로그인까지 구현됨. 다음은 결제 연동.'\n"
    "- Open questions: 'DB를 Supabase로 갈지 SQLite로 갈지 미정.'\n"
    "- Feature descriptions (user perspective): '사용자가 포커스 시간을 설정하면 앱이 방해 알림을 차단해줌'\n"
    "\n"
    "## What NOT to save\n"
    "- Code changes, function names, test results (git handles this)\n"
    "- Raw conversation logs\n"
    "- Implementation details like 'added WAL mode to SQLite'\n"
    "\n"
    "## Save format\n"
    "- One topic per memory. Split unrelated facts into separate saves.\n"
    "- Use 1-3 tags: ['decision', 'direction'], ['feature', 'payment'], ['idea'].\n"
    "- Update stale memories with muninn_manage update_memory, don't duplicate.\n"
    "\n"
    "## Project summary\n"
    "After each session, update summary to describe what this project IS\n"
    "from the user's perspective (not how it's built):\n"
    '  muninn_manage(action="update_project", project="xxx", field="summary", value="...")\n'
    "Good: '포커스 시간 관리 앱. 집중 모드에서 알림 차단 + 통계 대시보드.'\n"
    "Bad: 'Swift + CoreData + CloudKit으로 구현된 iOS 앱'\n"
    "\n"
    "## Project types the user works on\n"
    "- Active side projects (apps, developer tools)\n"
    "- Past work / portfolio projects\n"
    "- Personal interests and ideas being explored\n"
    "\n"
    "## Project status values\n"
    "- active: currently working on\n"
    "- paused: temporarily on hold\n"
    "- idea: exploring, not started yet\n"
    "- archived: completed or past project\n"
)


def _instructions_path() -> Path:
    """Return the path to the user-editable instructions file."""
    return Path(MuninnStore.default_db_path()).parent / "instructions.md"


def _load_instructions() -> str:
    """Load instructions from file, writing the default if the file doesn't exist."""
    path = _instructions_path()
    if path.exists():
        return path.read_text(encoding="utf-8")
    # File doesn't exist — write the default so the user has a starting point.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_INSTRUCTIONS, encoding="utf-8")
    return _INSTRUCTIONS


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

    mcp = FastMCP(
        "muninn",
        instructions=_load_instructions(),
        host=host,
        port=port,
        streamable_http_path="/",
        transport_security=transport_security,
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
