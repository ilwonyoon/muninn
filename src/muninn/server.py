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
    "Muninn is persistent project memory for AI assistants. "
    "Memories form a hierarchy: L0 identity → L1 topic index → L2 working → L3 archive.\n"
    "\n"
    "## When to use Muninn\n"
    "- SESSION START: Call muninn_recall immediately when the user mentions a project. "
    "Do not wait for explicit instruction — if a project name appears, recall it.\n"
    "- AFTER SIGNIFICANT WORK: Save key decisions, conclusions, and state before the session ends.\n"
    "- NEVER save raw conversation. Always distill: extract the decision or fact, discard the dialog.\n"
    "\n"
    "## Hierarchy levels\n"
    "depth=0  L0:identity  — 2-3 sentence project identity. One per project. Create FIRST. Max 300 chars. Always loaded.\n"
    "depth=1  L1:index     — Topic index entry. One per major topic area (auth, storage, api, etc.).\n"
    "depth=2  L2:working   — Working memory under a topic. Decisions, findings, current state. DEFAULT.\n"
    "depth=3  L3:archive   — Archives, old versions, raw logs. Rarely loaded.\n"
    "\n"
    "## Save pattern\n"
    "1. Check existing L1 index: muninn_recall(project, depth=1)\n"
    "2. If topic L1 exists, save L2 under it: parent_memory_id=<l1_id>\n"
    "3. If topic L1 is new, create it first (depth=1), then save L2 under it.\n"
    "4. Always set title= (max 60 chars, plain text, no markdown).\n"
    "\n"
    "## Recall drill-down\n"
    "1. Start with depth=1 to get the topic index.\n"
    "2. Find the relevant L1 topic memory id.\n"
    "3. Call again with parent_id=<l1_id>, depth=2 to load working memories under it.\n"
    "\n"
    "## Category selection\n"
    "Pick the category that best describes what the memory IS, not what it's about:\n"
    "  brainstorm     — 'What if...?' Raw ideation, voice chat dumps, early-stage exploration. Set resolved=true when ideas graduate.\n"
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
    "## Save quality rules\n"
    "- One memory per topic. Split unrelated facts into separate saves.\n"
    "- L0-L1 must be skimmable in under 5 seconds. Cut anything redundant.\n"
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
            required_scopes=[],
        )

    mcp = FastMCP(
        "muninn",
        instructions=_INSTRUCTIONS,
        host=host,
        port=port,
        streamable_http_path="/mcp",
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
